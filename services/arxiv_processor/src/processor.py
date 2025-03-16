import json
import logging
import os
import re
import time
from datetime import datetime, timezone, timedelta
from html import unescape
from io import BytesIO

import boto3
import defusedxml.ElementTree as ET
import docx
import requests
from docx import Document
from botocore.exceptions import ClientError

from constants import *

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

ssm = boto3.client('ssm')

def get_config():
    """Get configuration from SSM Parameter Store"""
    config_path = os.getenv("CONFIG_PATH")
    try:
        sets_param = ssm.get_parameter(Name=f"{config_path}/arxiv/sets")
        set_names = json.loads(sets_param['Parameter']['Value'])

        global_params = ssm.get_parameters(
            Names=[
                f"{config_path}/arxiv/s3_bucket",
                f"{config_path}/arxiv/dynamodb_table"
            ]
        )
        
        config = {}
        for param in global_params['Parameters']:
            name = param['Name'].split('/')[-1]
            config[name] = param['Value']
        
        config["sets"] = {}
        
        for set_name in set_names:
            set_params = ssm.get_parameters(
                Names=[
                    f"{config_path}/arxiv/{set_name}/categories",
                    f"{config_path}/arxiv/{set_name}/back_date"
                ]
            )
            
            set_config = {}
            for param in set_params['Parameters']:
                name = param['Name'].split('/')[-1]
                if name == 'categories':
                    set_config[name] = param['Value'].split(',')
                elif name == 'back_date':
                    set_config[name] = int(param['Value'])
            
            config["sets"][set_name] = set_config
            
        if set_names and set_names[0] in config["sets"]:
            default_set = set_names[0]
            config["categories"] = config["sets"][default_set]["categories"]
            config["back_date"] = config["sets"][default_set]["back_date"]
            config["set"] = default_set
            
        return config
    except ClientError as e:
        logger.error(f"Error fetching config: {e}")
        raise

config = get_config()
CATEGORIES = config['categories']
BACK_DATE = config['back_date']
ARXIV_SET = config['set']
S3_BUCKET = config['s3_bucket']
DYNAMODB_TABLE = config['dynamodb_table']

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb').Table(DYNAMODB_TABLE)

def store_paper_metadata(record: dict, dynamodb_table, set_name: str = None):
    """Store paper metadata in DynamoDB with proper history tracking"""
    try:
        set_value = record.get("set", set_name)
        
        arxiv_id = record["identifier"].split('/')[-1] if '/' in record["identifier"] else record["identifier"]
        category = record["primary_category"]
        abstract_s3_key = f"papers/{set_value}/{category}/{arxiv_id}.json" if category else None
        
        existing_item = dynamodb_table.get_item(Key={"id": record["identifier"]}).get("Item")
        
        current_time = datetime.now(timezone.utc).isoformat()
        
        item = {
            "id": record["identifier"],
            "date": record["date"],
            "title": record["title"],
            "authors": record["authors"],
            "categories": record["categories"],
            "primary_category": record["primary_category"],
            "abstract_url": record["abstract_url"],
            "pdf_url": record["abstract_url"].replace("abs", "pdf"),
            "set": set_value,
            "abstract_s3_key": abstract_s3_key,
            "modified_date": current_time
        }
        
        if not existing_item:
            item["created_date"] = current_time
            item["neo4j_status"] = "pending"
            
            logger.info(f"New paper added: {record['identifier']}")
        else:
            item["created_date"] = existing_item.get("created_date", current_time)
            
            content_changed = (
                existing_item.get("title") != item["title"] or
                existing_item.get("abstract_s3_key") != abstract_s3_key or
                existing_item.get("primary_category") != item["primary_category"] or
                existing_item.get("categories") != item["categories"] or
                existing_item.get("authors") != item["authors"]
            )
            
            if content_changed:
                item["neo4j_status"] = "pending"
                logger.info(f"Paper updated: {record['identifier']}")
            else:
                item["neo4j_status"] = existing_item.get("neo4j_status", "pending")
                logger.debug(f"Paper unchanged: {record['identifier']}")
        
        if existing_item:
            dynamodb_table.put_item(
                Item=item,
                ConditionExpression="attribute_exists(id)"
            )
        else:
            dynamodb_table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(id)"
            )
            
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            logger.warning(f"Concurrent update detected for {record['identifier']}")
        else:
            logger.error(f"Error storing metadata: {e}")
            raise

def upload_to_s3(file_data: BytesIO, key: str, s3_bucket: str, s3_client):
    """Upload file to S3"""
    try:
        s3_client.upload_fileobj(file_data, s3_bucket, key)
        logger.info(f"Uploaded {key} to S3")
    except ClientError as e:
        logger.error(f"Error uploading to S3: {e}")
        raise

def fetch_data(base_url: str, from_date: str, set_name: str) -> list:
    """Fetches data from arXiv API with proper retry handling"""
    full_xml_responses = []
    params = {"verb": "ListRecords", "set": set_name, "metadataPrefix": "oai_dc", "from": from_date}
    
    max_retries = 5
    base_wait_time = 5  # seconds
    
    retry_count = 0
    while True:
        try:
            logging.info(f"Fetching data with parameters: {params}")
            response = requests.get(base_url, params=params, timeout=30)
            
            if response.status_code == 503:
                retry_after = int(response.headers.get('Retry-After', 30))
                logging.info(f"Server busy (503). Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            
            response.raise_for_status()
            full_xml_responses.append(response.text)
            
            root = ET.fromstring(response.content)
            resumption_token = root.find(".//{http://www.openarchives.org/OAI/2.0/}resumptionToken")

            if resumption_token is not None and resumption_token.text:
                logging.info(f"Found resumption token: {resumption_token.text}")
                time.sleep(5)  # Be nice to the server
                params = {"verb": "ListRecords", "resumptionToken": resumption_token.text}
                retry_count = 0
            else:
                break

        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error occurred: {e}")
            if retry_count < max_retries:
                wait_time = base_wait_time * (2 ** retry_count)
                logging.info(f"Retrying in {wait_time} seconds (attempt {retry_count+1}/{max_retries})...")
                time.sleep(wait_time)
                retry_count += 1
            else:
                logging.error(f"Maximum retry attempts reached ({max_retries}). Giving up.")
                break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logging.error(f"Connection error occurred: {e}")
            if retry_count < max_retries:
                wait_time = base_wait_time * (2 ** retry_count)
                logging.info(f"Retrying in {wait_time} seconds (attempt {retry_count+1}/{max_retries})...")
                time.sleep(wait_time)
                retry_count += 1
            else:
                logging.error(f"Maximum retry attempts reached ({max_retries}). Giving up.")
                break
        except ET.ParseError as e:
            logging.error(f"Parse error occurred: {e}")
            if retry_count < max_retries:
                wait_time = base_wait_time * (2 ** retry_count)
                logging.info(f"Retrying in {wait_time} seconds (attempt {retry_count+1}/{max_retries})...")
                time.sleep(wait_time)
                retry_count += 1
            else:
                logging.error(f"Maximum retry attempts reached ({max_retries}). Giving up.")
                break
        except Exception as e:
            logging.error(f"Unexpected error occurred: {e}")
            if retry_count < max_retries:
                wait_time = base_wait_time * (2 ** retry_count)
                logging.info(f"Retrying in {wait_time} seconds (attempt {retry_count+1}/{max_retries})...")
                time.sleep(wait_time)
                retry_count += 1
            else:
                logging.error(f"Maximum retry attempts reached ({max_retries}). Giving up.")
                break

    return full_xml_responses

def parse_xml_data(xml_data: str, set_name: str) -> dict:
    """Parses XML data from arXiv"""
    extracted_data = {"records": []}

    category_dict = {
        "cs": cs_categories_inverted,
        "math": math_categories_inverted,
        "econ": econ_categories_inverted,
        "physics": physics_categories_inverted,
        "q-bio": qbio_categories_inverted,
        "q-fin": qfin_categories_inverted,
        "stat": stat_categories_inverted,
        "eess": eess_categories_inverted
    }.get(set_name, cs_categories_inverted)

    try:
        root = ET.fromstring(xml_data)
        ns = {
            "oai": "http://www.openarchives.org/OAI/2.0/",
            "dc": "http://purl.org/dc/elements/1.1/"
        }

        for record in root.findall(".//oai:record", ns):
            identifier = record.find(".//oai:identifier", ns).text
            abstract_url = record.find(".//dc:identifier", ns).text
            title = record.find(".//dc:title", ns).text.replace("\n", "")
            abstract = record.find(".//dc:description", ns).text.replace("\n", " ")
            date = record.find(".//dc:date", ns).text

            authors = []
            for creator in record.findall(".//dc:creator", ns):
                name_parts = creator.text.split(", ", 1)
                authors.append({
                    "last_name": name_parts[0],
                    "first_name": name_parts[1] if len(name_parts) > 1 else ""
                })

            subjects = record.findall(".//dc:subject", ns)
            categories = [category_dict.get(subject.text, "") for subject in subjects]
            categories = list(filter(None, categories))
            primary_category = categories[0] if categories else ""

            extracted_data["records"].append({
                "identifier": identifier,
                "abstract_url": abstract_url,
                "authors": authors,
                "primary_category": primary_category,
                "categories": categories,
                "abstract": abstract,
                "title": title,
                "date": date,
                "set": set_name
            })

    except ET.ParseError as e:
        logging.error(f"Error parsing XML: {e}")

    return extracted_data

def latex_to_human_readable(latex_str: str) -> str:
    """Converts LaTeX to human readable text"""
    latex_str = re.sub(r"\$(.*?)\$", r"\1", latex_str)
    
    replacements = {
        "\\alpha": "alpha",
        "\\beta": "beta",
        "\\gamma": "gamma",
        "\\delta": "delta",
        "\\epsilon": "epsilon",
        "\\zeta": "zeta",
        "\\eta": "eta",
        "\\theta": "theta",
        "\\iota": "iota",
        "\\kappa": "kappa",
        "\\lambda": "lambda",
        "\\mu": "mu",
        "\\nu": "nu",
        "\\xi": "xi",
        "\\pi": "pi",
        "\\rho": "rho",
        "\\sigma": "sigma",
        "\\tau": "tau",
        "\\upsilon": "upsilon",
        "\\phi": "phi",
        "\\chi": "chi",
        "\\psi": "psi",
        "\\omega": "omega",
        "\\leq": "<=",
        "\\geq": ">=",
        "\\neq": "!=",
        "\\approx": "≈",
        "\\times": "×",
        "\\rightarrow": "→",
        "\\leftarrow": "←",
        "\\infty": "∞",
        "\\pm": "±",
        "\\sum": "∑",
        "\\prod": "∏",
        "\\int": "∫",
    }
    
    for latex, text in replacements.items():
        latex_str = latex_str.replace(latex, text)

    latex_str = re.sub(r'\\[a-zA-Z]+', '', latex_str)
    latex_str = latex_str.replace('  ', ' ')
    latex_str = latex_str.replace('{', '').replace('}', '')
    
    return unescape(latex_str)

def store_paper_json(record: dict, s3_bucket: str, s3_client, set_name: str):
    """Store individual paper abstract as JSON in S3"""
    try:
        arxiv_id = record["identifier"].split('/')[-1] if '/' in record["identifier"] else record["identifier"]
        
        category = record["primary_category"]
        
        if not category:
            logging.warning(f"Paper {arxiv_id} has no primary category, skipping S3 storage")
            return None
            
        paper_data = {
            "abstract": record["abstract"]
        }
        
        json_data = json.dumps(paper_data, indent=2)
        
        s3_key = f"papers/{set_name}/{category}/{arxiv_id}.json"
        
        json_buffer = BytesIO(json_data.encode('utf-8'))
        upload_to_s3(json_buffer, s3_key, s3_bucket, s3_client)
        
        return s3_key
        
    except Exception as e:
        logging.error(f"Error storing paper JSON: {e}")
        return None

def main():
    config = get_config()
    
    base_url = "http://export.arxiv.org/oai2"
    today = datetime.today()
    
    s3_client = boto3.client('s3')
    dynamodb_client = boto3.resource('dynamodb').Table(config["dynamodb_table"])
    
    for set_name, set_config in config["sets"].items():
        logging.info(f"Processing set: {set_name}")
        
        categories = set_config["categories"]
        back_date = set_config["back_date"]
        
        for i in range(back_date):
            date = (today - timedelta(days=i+1)).strftime("%Y-%m-%d")
            logging.info(f"Processing papers for {set_name}/{date}")
            
            xml_responses = fetch_data(base_url, date, set_name)
            
            if not xml_responses:
                logging.warning(f"No data retrieved for {set_name}/{date}. Skipping...")
                continue
                
            all_records = []
            for xml in xml_responses:
                data = parse_xml_data(xml, set_name)
                all_records.extend(data["records"])
                
            if all_records:
                for record in all_records:
                    store_paper_json(record, config["s3_bucket"], s3_client, set_name)
                
                for record in all_records:
                    store_paper_metadata(record, dynamodb_client, set_name)

            else:
                logging.warning(f"No records found for {set_name}/{date}")
    
    print(json.dumps({"status": "Processing complete"}))

if __name__ == "__main__":
    main()
