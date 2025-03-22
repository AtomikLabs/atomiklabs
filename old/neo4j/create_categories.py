import argparse
import json
import uuid
from datetime import datetime

import boto3
import pytz
import structlog
from neo4j import GraphDatabase

structlog.configure(
    [
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

CS_CATEGORIES_INVERTED = {
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

DEFAULT_TIMEZONE = "US/Pacific"
S3_KEY_DATE_FORMAT = "%Y-%m-%dT%H-%M-%S"
DEFAULT_NEO4J_DB = "neo4j"
# get args from cli: -e <environment> -n <neo4j_uri>, env MUST be dev, prod, stage, or test
parser = argparse.ArgumentParser()
parser.add_argument("-e", "--env", help="Environment", required=True)
parser.add_argument("-n", "--neo4j_uri", help="Neo4j URI", required=True)
args = parser.parse_args()

env = args.env
if env not in ["dev", "prod", "stage", "test"]:
    raise ValueError("Invalid environment: must be dev, prod, stage, or test")

neo4j_uri = args.neo4j_uri


def get_storage_key_datetime(date: str = "") -> datetime:
    """
    Get the date in the format used for S3 keys.

    Args:
        date: The date to format.

    Returns:
        The date in the format used for S3 keys.
    """
    if not date:
        return datetime.now().astimezone(pytz.timezone(DEFAULT_TIMEZONE))
    return datetime.strptime(date, S3_KEY_DATE_FORMAT).astimezone(pytz.timezone(DEFAULT_TIMEZONE))


secret = boto3.client("secretsmanager").get_secret_value(SecretId=f"{env}/neo4j-credentials")
neo4j_creds = json.loads(secret["SecretString"])
print(neo4j_creds)

with GraphDatabase.driver(neo4j_uri, auth=(neo4j_creds["neo4j_username"], neo4j_creds["neo4j_password"])) as driver:
    with driver.session() as session:
        driver.verify_connectivity()
        logger.info("Connected to Neo4j")

        category_nodes = []
        for category, code in CS_CATEGORIES_INVERTED.items():
            q = f"MERGE (c:ArxivCategory {{name: '{category}', code: '{code}'}})"
            category_nodes.append({"name": category, "code": code})
        category_query = "\n".join(
            [
                f"""
                                    MERGE ({category['code']}:ArxivCategory {{uuid: '{uuid.uuid4().__str__()}', name: '{category['name']}', code: '{category['code']}'}})
                                    MERGE (s)-[:CATEGORIZED_BY {{uuid: '{uuid.uuid4().__str__()}'}}]->({category['code']})
                                    MERGE ({category['code']})-[:CATEGORIZED_IN {{uuid: '{uuid.uuid4().__str__()}'}}]->(s)"""
                for category in category_nodes
            ]
        )

        print(category_query)
        driver = driver.execute_query(
            f"""
            MERGE (s:ArxivSet {{uuid: $set_uuid, name: $set_name, code: $set_code, created: $set_created, last_modified: $set_last_modified}})
            {category_query}
            """,
            set_uuid=str(uuid.uuid4().__str__()),
            set_name="Computer Science",
            set_code="CS",
            set_created=get_storage_key_datetime(),
            set_last_modified=get_storage_key_datetime(),
            database_="neo4j",
        )
