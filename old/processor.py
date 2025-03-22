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
import requests
from docx import Document
from botocore.exceptions import ClientError

from src.constants import *
from atomiklabs.neo4j.client import Neo4jClient
from atomiklabs.neo4j.models import Paper, Author, Category, Set
from atomiklabs.neo4j.exceptions import Neo4jError, Neo4jNodeNotFoundError

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
                f"{config_path}/arxiv/dynamodb_table",
                f"{config_path}/neo4j/uri",
                f"{config_path}/neo4j/username",
                f"{config_path}/neo4j/password",
                f"{config_path}/neo4j/database"
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

def check_existing_metadata(record: dict, dynamodb_table):
    """Check if paper already exists in DynamoDB and return the item if found
    
    Args:
        record: Paper record dictionary
        dynamodb_table: DynamoDB table instance
        
    Returns:
        The DynamoDB item if found, None otherwise
    """
    existing_item = dynamodb_table.get_item(
            Key={
                "id": record["identifier"],
                "date": record["date"]
            }
        ).get("Item")
    
    return existing_item

def put_paper_metadata(item: dict, dynamodb_table, existing_item_exists: bool):
    """Put paper metadata in DynamoDB
    
    Args:
        item: Item to put in DynamoDB
        dynamodb_table: DynamoDB table instance
        existing_item_exists: Whether the item already exists in DynamoDB
    """
    try:
        if existing_item_exists:
            dynamodb_table.put_item(
                Item=item,
                ConditionExpression="attribute_exists(id) AND attribute_exists(#date)",
                ExpressionAttributeNames={"#date": "date"}
            )
        else:
            dynamodb_table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(id) OR attribute_not_exists(#date)",
                ExpressionAttributeNames={"#date": "date"}
            )
    except ClientError as e:
        logger.error(f"Error storing metadata: {e}")
        raise        

def check_existing_node(record: dict, neo4j_client: Neo4jClient) -> bool:
    """Check if paper already exists in Neo4j
    
    Args:
        record: Paper record dictionary
        neo4j_client: Neo4j client instance
        
    Returns:
        True if paper exists, False otherwise
    """
    try:
        paper_id = record["identifier"]
        neo4j_client.get_node_by_id(Paper, paper_id)
        logger.debug(f"Paper {paper_id} exists in Neo4j")
        return True
    except Neo4jNodeNotFoundError:
        logger.debug(f"Paper {paper_id} does not exist in Neo4j")
        return False
    except Neo4jError as e:
        logger.error(f"Error checking Neo4j for {record['identifier']}: {e}")
        return False

def put_paper_node(record: dict, neo4j_client: Neo4jClient) -> bool:
    """Put paper node in Neo4j
    
    Creates a complete graph structure for an arXiv paper, including:
    - Paper node
    - Author nodes with relationships
    - Category nodes with relationships
    - Set node with relationship
    
    Args:
        record: Paper record dictionary
        neo4j_client: Neo4j client instance
        
    Returns:
        True if successful, False otherwise
    """
    try:
        paper = neo4j_client.create_arxiv_paper_graph(record)
        logger.info(f"Created/updated Neo4j graph for paper {record['identifier']}")
        return True
    except Neo4jError as e:
        logger.error(f"Error creating Neo4j graph for {record['identifier']}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error creating Neo4j graph for {record['identifier']}: {e}")
        return False

def store_paper_metadata(record: dict, dynamodb_table, neo4j_client: Neo4jClient = None, set_name: str = None):
    """Store paper metadata in DynamoDB with proper history tracking and Neo4j sync
    
    Args:
        record: Paper record dictionary
        dynamodb_table: DynamoDB table instance
        neo4j_client: Neo4j client instance (optional)
        set_name: arXiv set name (optional)
    """
    try:
        set_value = record.get("set", set_name)
        
        arxiv_id = record["identifier"].split('/')[-1] if '/' in record["identifier"] else record["identifier"]
        category = record["primary_category"]
        abstract_s3_key = f"papers/{set_value}/{category}/{arxiv_id}.json" if category else None
        
        existing_item = check_existing_metadata(record, dynamodb_table)
        
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
        
        neo4j_status = "pending"
        
        if neo4j_client:
            neo4j_exists = check_existing_node(record, neo4j_client)
            
            if neo4j_exists:
                logger.debug(f"Paper {record['identifier']} exists in Neo4j, will update")
            
            neo4j_success = put_paper_node(record, neo4j_client)
            
            if neo4j_success:
                neo4j_status = "synced"
                logger.info(f"Paper {record['identifier']} synced to Neo4j")
            else:
                neo4j_status = "failed"
                logger.warning(f"Failed to sync paper {record['identifier']} to Neo4j")
        
        if not existing_item:
            item["created_date"] = current_time
            item["neo4j_status"] = neo4j_status
            
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
                item["neo4j_status"] = neo4j_status
                logger.info(f"Paper updated: {record['identifier']}")
            else:
                if neo4j_client:
                    item["neo4j_status"] = neo4j_status
                else:
                    item["neo4j_status"] = existing_item.get("neo4j_status", "pending")
                logger.debug(f"Paper unchanged: {record['identifier']}")

        put_paper_metadata(item, dynamodb_table, existing_item is not None)
            
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
    
    neo4j_client = None
    try:
        if all(key in config for key in ["uri", "username", "password"]):
            neo4j_client = Neo4jClient(
                uri=config["uri"],
                username=config["username"],
                password=config["password"],
                database=config.get("database", "neo4j")
            )
            schema_status = neo4j_client.verify_schema()
            logger.info(f"Neo4j schema status: {schema_status}")
            if not all(schema_status["constraints"].values()) or not all(schema_status["indexes"].values()):
                logger.warning("Neo4j schema is not fully set up. Setting up now...")
                neo4j_client.setup_schema()
            logger.info("Neo4j client initialized")
        else:
            logger.warning("Neo4j configuration incomplete, skipping Neo4j integration")
    except Exception as e:
        logger.error(f"Failed to initialize Neo4j client: {e}")
        neo4j_client = None
    
    try:
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
                        store_paper_metadata(record, dynamodb_client, neo4j_client, set_name)
    
                else:
                    logging.warning(f"No records found for {set_name}/{date}")
    finally:
        if neo4j_client:
            neo4j_client.close()
            logger.info("Neo4j connection closed")
    
    print(json.dumps({"status": "Processing complete"}))

if __name__ == "__main__":
    main()
