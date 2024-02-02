# Description: Parse arXiv research summaries and send them to be persisted.
import json
import logging
import os
from collections import defaultdict

import boto3
import defusedxml.ElementTree as ET

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

INTERNAL_SERVER_ERROR = "Internal server error"
NO_REGION_SPECIFIED = "No region specified"

cs_categories_inverted = {
    "Computer Science - Artificial Intelligence": "AI",
    "Computer Science - Hardware Architecture": "AR",
    "Computer Science - Computational Complexity": "CC",
    "Computer Science - Computational Engineering, Finance, and Science": "CE",
    "Computer Science - Computational Geometry": "CG",
    "Computer Science - Computation and Language": "CL",
    "Computer Science - Cryptography and Security": "CR",
    "Computer Science - Computer Vision and Pattern Recognition": "CV",
    "Computer Science - Computers and Society": "CY",
    "Computer Science - Databases": "DB",
    "Computer Science - Distributed, Parallel, and Cluster Computing": "DC",
    "Computer Science - Digital Libraries": "DL",
    "Computer Science - Discrete Mathematics": "DM",
    "Computer Science - Data Structures and Algorithms": "DS",
    "Computer Science - Emerging Technologies": "ET",
    "Computer Science - Formal Languages and Automata Theory": "FL",
    "Computer Science - General Literature": "GL",
    "Computer Science - Graphics": "GR",
    "Computer Science - Computer Science and Game Theory": "GT",
    "Computer Science - Human-Computer Interaction": "HC",
    "Computer Science - Information Retrieval": "IR",
    "Computer Science - Information Theory": "IT",
    "Computer Science - Machine Learning": "LG",
    "Computer Science - Logic in Computer Science": "LO",
    "Computer Science - Multiagent Systems": "MA",
    "Computer Science - Multimedia": "MM",
    "Computer Science - Mathematical Software": "MS",
    "Computer Science - Numerical Analysis": "NA",
    "Computer Science - Neural and Evolutionary Computing": "NE",
    "Computer Science - Networking and Internet Architecture": "NI",
    "Computer Science - Other Computer Science": "OH",
    "Computer Science - Operating Systems": "OS",
    "Computer Science - Performance": "PF",
    "Computer Science - Programming Languages": "PL",
    "Computer Science - Robotics": "RO",
    "Computer Science - Symbolic Computation": "SC",
    "Computer Science - Sound": "SD",
    "Computer Science - Software Engineering": "SE",
    "Computer Science - Social and Information Networks": "SI",
    "Computer Science - Systems and Control": "SY",
}


def lambda_handler(event, context):
    """
    The main entry point for the Lambda function.

    Args:
        event: The event passed to the Lambda function.
        context: The context passed to the Lambda function.

    Returns:
        The response to be returned to the client.
    """
    try:
        log_initial_info(event)

        bucket_name = event.get("bucket_name")
        key = event.get("key")
        logger.info(f"Bucket name: {bucket_name}")
        if not bucket_name:
            logger.error("No bucket name specified")
            return {"statusCode": 500, "body": "No bucket name specified"}

        if not key:
            logger.error("No key specified")
            return {"statusCode": 500, "body": "No key specified"}

            # persist_lambda_name = os.environ.get("PERSIST_LAMBDA_FUNCTION_NAME")
            # logger.info(f"Persist lambda function name: {persist_lambda_name}")
            # if not persist_lambda_name:
            return {"statusCode": 500, "body": "No persist lambda function name specified"}

        xml_data = load_xml_from_s3(bucket_name, key)
        parsed_data = parse_xml(xml_data)
        upload_to_s3(key, bucket_name, parsed_data)
        # call_persist_summaries(persist_lambda_name, bucket_name, parsed_data)
        logger.info("Finished parsing arXiv daily summaries")
        return {"statusCode": 200, "body": "Success"}

    except Exception as e:
        logger.error(e)
        return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR}


def log_initial_info(event: dict) -> None:
    """
    Logs initial info.

    Args:
        event (dict): Event.
    """
    try:
        logger.info("## ENVIRONMENT VARIABLE")
        logger.info(os.environ["AWS_LAMBDA_LOG_GROUP_NAME"])
        logger.info(os.environ["AWS_LAMBDA_LOG_STREAM_NAME"])
    except KeyError:
        # If the environment variables are not set, the function is being run in CI/CD or locally
        pass
    logger.info("## EVENT")
    logger.info(event)
    logger.info(f"## {__name__} STARTED")


def load_xml_from_s3(bucket_name: str, key: str) -> str:
    """
    Loads a list of XML strings from a JSON file in S3.

    Args:
        bucket_name (str): Bucket name.
        key (str): Key.

    Returns:
        List of XML strings.
    """
    logger.info(f"Loading XML data from S3 bucket {bucket_name} with key {key}")
    if not bucket_name:
        raise ValueError("Must provide a bucket name")
    if not key:
        raise ValueError("Must provide a key")

    try:
        s3 = boto3.resource("s3")
        obj = s3.Object(bucket_name, key)
        body = obj.get()["Body"].read()

        xml_data_list = body

        return xml_data_list
    except Exception as e:
        logger.error(f"Failed to load XML data from S3 bucket {bucket_name} with key {key}: {e}")
        raise


def parse_xml(xml_data: ET) -> dict:
    """
    Parses arXiv XML into a list of dictionaries of research summaries.

    Args:
        xml_data (ET.Element): XML element.

    Returns:
        Dictionary of research summaries.
    """
    extracted_data_chunk = defaultdict(list)
    for data in xml_data:
        try:
            root = ET.fromstring(data)
            ns = {"oai": "http://www.openarchives.org/OAI/2.0/", "dc": "http://purl.org/dc/elements/1.1/"}

            for record in root.findall(".//oai:record", ns):
                date_elements = record.findall(".//dc:date", ns)
                if len(date_elements) != 1:
                    continue

                identifier = record.find(".//oai:identifier", ns).text
                abstract_url = record.find(".//dc:identifier", ns).text

                creators_elements = record.findall(".//dc:creator", ns)
                authors = []
                for creator in creators_elements:
                    name_parts = creator.text.split(", ", 1)
                    last_name = name_parts[0]
                    first_name = name_parts[1] if len(name_parts) > 1 else ""
                    authors.append({"last_name": last_name, "first_name": first_name})

                # Find all subjects
                subjects_elements = record.findall(".//dc:subject", ns)
                categories = [cs_categories_inverted.get(subject.text) for subject in subjects_elements]
                # Remove empty strings
                categories = list(filter(None, categories))
                primary_category = categories[0] if categories else ""

                abstract = record.find(".//dc:description", ns).text.replace("\n", " ")
                title = record.find(".//dc:title", ns).text.replace("\n", "")
                date = date_elements[0].text
                group = "cs"

                extracted_data_chunk["records"].append(
                    {
                        "identifier": identifier,
                        "abstract_url": abstract_url,
                        "authors": authors,
                        "primary_category": primary_category,
                        "categories": categories,  # All categories
                        "abstract": abstract,
                        "title": title,
                        "date": date,
                        "group": group,
                    }
                )
        except ET.ParseError as e:
            print(f"Parse error: {e}")
    print(len(extracted_data_chunk["records"]))
    print(extracted_data_chunk["records"][0])
    return extracted_data_chunk


def upload_to_s3(original_filename: str, bucket_name: str, xml: dict) -> None:
    """
    Uploads XML to S3.

    Args:
        original_filename (str): Original filename.
        bucket_name (str): Bucket name.
        xml (dict): XML.
    """
    logger.info("Uploading to S3 bucket " + bucket_name + " as " + original_filename + "_parsed.json")
    try:
        key = (original_filename + "_parsed.json")
        s3 = boto3.client("s3")
        s3.put_object(Body=json.dumps(xml), Bucket=bucket_name, Key=key)
    except Exception as e:
        logger.error(f"Failed to upload to S3 at {bucket_name} with key {key}: {e}")
        raise


def call_persist_summaries(persist_lambda_name: str, bucket_name: str, filename: str) -> None:
    """
    Calls persist summaries.

    Args:
        persist_lambda_name (str): Persist lambda name.
        bucket_name (str): Bucket name.
        filename (str): Filename of the parsed summaries saved as xml.
    """
    logger.info(
        "Calling persist summaries function {persist_lambda_name} \
                 for {filename} in {bucket_name}"
    )
    event_payload = {"bucket_name": bucket_name, "filename": filename}
    try:
        lambda_client = boto3.client("lambda")
        lambda_client.invoke(FunctionName=persist_lambda_name, InvocationType="Event", Payload=event_payload)
    except Exception as e:
        logger.error(f"Failed to call persist summaries function {persist_lambda_name}: {e}")
        raise


def config_for_test():
    global AURORA_CLUSTER_ARN, BASE_URL, BUCKET_NAME, DB_CREDENTIALS_SECRET_ARN, DATABASE, SUMMARY_SET
    AURORA_CLUSTER_ARN = "arn:aws:rds:us-east-1:758145997264:cluster:atomiklabs-dev-aurora-cluster"
    BASE_URL = "http://export.arxiv.org/oai2"
    BUCKET_NAME = "atomiklabs-data-bucket-dev"
    DB_CREDENTIALS_SECRET_ARN = "arn:aws:secretsmanager:us-east-1:758145997264:secret:dev/database-credentials-TuF8OS"
    DATABASE = "atomiklabs_dev_database"
    SUMMARY_SET = "cs"


if __name__ == "__main__":
    lambda_handler(
        {"bucket_name": "atomiklabs-data-bucket-dev", "key": "arxiv_daily_summaries/20240131-072844.json"}, None
    )
