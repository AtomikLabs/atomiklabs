# Description: Lambda function to fetch daily summaries from arXiv.

import logging
import os
import re
import time
from datetime import timedelta, datetime, date
from typing import List
import json

import boto3
import defusedxml.ElementTree as ET
import requests
from botocore.exceptions import NoRegionError

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

INTERNAL_SERVER_ERROR = "Internal server error"
NO_REGION_SPECIFIED = "No region specified"
NO_UNFETCHED_DATES_FOUND = "No unfetched dates found"


def lambda_handler(event: dict, context) -> dict:
    """
    The main entry point for the Lambda function.

    Args:
        event (dict): The event data.
        context: The context data.

    Returns:
        dict: A dict with the status code and body.
    """
    try:
        log_initial_info(event)

        today = calculate_from_date()

        aurora_cluster_arn = os.environ.get("RESOURCE_ARN")
        base_url = os.environ.get("BASE_URL")
        bucket_name = os.environ.get("BUCKET_NAME")
        db_credentials_secret_arn = os.environ.get("SECRET_ARN")
        database = os.environ.get("DATABASE_NAME")
        summary_set = os.environ.get("SUMMARY_SET")

        if not all([aurora_cluster_arn, db_credentials_secret_arn, database, base_url, bucket_name, summary_set]):
            message = ""
            if not aurora_cluster_arn:
                message += "RESOURCE_ARN "
            if not db_credentials_secret_arn:
                message += "SECRET_ARN "
            if not database:
                message += "DATABASE_NAME "
            if not base_url:
                message += "BASE_URL "
            if not bucket_name:
                message += "BUCKET_NAME "
            if not summary_set:
                message += "SUMMARY_SET "

            return {"statusCode": 500, "body": f"Missing environment variables: {message}"}

        try:
            insert_fetch_status(today, aurora_cluster_arn, db_credentials_secret_arn, database)
        except Exception as e:
            logger.error(f"Error inserting fetch status: {str(e)}")
            return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR}

        try:
            earliest_unfetched_date = get_earliest_unfetched_date(
                aurora_cluster_arn, db_credentials_secret_arn, database
            )
        except Exception as e:
            logger.error(f"Error fetching earliest unfetched date: {str(e)}")
            return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR}

        if not earliest_unfetched_date:
            message = NO_UNFETCHED_DATES_FOUND
            logger.info(message)
            return {"statusCode": 200, "body": message}

        if not earliest_unfetched_date:
            logger.info(NO_UNFETCHED_DATES_FOUND)
            return {"statusCode": 200, "body": NO_UNFETCHED_DATES_FOUND}

        logger.info(f"Earliest unfetched date: {earliest_unfetched_date}")

        try:
            last_success_date = attempt_fetch_for_dates(
                base_url,
                summary_set,
                bucket_name,
                aurora_cluster_arn,
                db_credentials_secret_arn,
                database,
                today,
                earliest_unfetched_date,
            )
        except Exception as e:
            logger.error(f"Error fetching summaries: {str(e)}")
            return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR}

        if last_success_date:
            message = f"Last successful fetch date: {last_success_date}"
        else:
            message = "No new data fetched"

        return {"statusCode": 200, "body": message}
    except NoRegionError:
        logger.error(NO_REGION_SPECIFIED)
        return {"statusCode": 500, "body": NO_REGION_SPECIFIED}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR}


def log_initial_info(event: dict) -> None:
    """
    Logs initial info.

    Args:
        event (dict): Event.
    """
    logger.info(f"Received event: {event}")
    logger.info("Starting to fetch arXiv daily summaries")


def calculate_from_date() -> date:
    """Calculates from date for fetching summaries.

    Returns:
        date: From date.
    """
    today = datetime.today()
    yesterday = today - timedelta(days=1)
    return yesterday.date()


def insert_fetch_status(date, aurora_cluster_arn, db_credentials_secret_arn, database):
    """
    Inserts fetch status as 'pending' for the given date using
    AWS RDSDataService.

    Args:
        date (date): Date for which to insert fetch status.
        aurora_cluster_arn (str): The ARN of the Aurora Serverless DB cluster.
        db_credentials_secret_arn (str): The ARN of the secret containing
                                         credentials to access the DB.
        database (str): Database name.
    """
    client = boto3.client("rds-data")
    formatted_date = date.strftime("%Y-%m-%d")

    sql_statement = """
    INSERT INTO research_fetch_status (fetch_date, status)
    VALUES (CAST(:date AS DATE), 'pending') ON CONFLICT (fetch_date) DO NOTHING
    """

    parameters = [{"name": "date", "value": {"stringValue": formatted_date}}]

    response = client.execute_statement(
        resourceArn=aurora_cluster_arn,
        secretArn=db_credentials_secret_arn,
        database=database,
        sql=sql_statement,
        parameters=parameters,
    )
    return response


def get_earliest_unfetched_date(aurora_cluster_arn, db_credentials_secret_arn, database, days=5) -> date:
    """
    Gets the earliest unfetched date using AWS RDSDataService.

    Args:
        aurora_cluster_arn (str): The ARN of the Aurora Serverless DB cluster.
        db_credentials_secret_arn (str): The ARN of the secret containing
                                         credentials to access the DB.
        database (str): Database name.
        days (int): Number of days to check for unfetched dates.

    Returns:
        date: Earliest unfetched date.
    """
    client = boto3.client("rds-data")
    today = datetime.today().date()
    past_dates = [(today - timedelta(days=i)) for i in range(1, days + 1)]
    logger.info(f"Past dates: {past_dates}")
    logger.info(f"Today's date: {today}")

    placeholders = [f":date{i}" for i in range(len(past_dates))]
    placeholder_string = ", ".join(placeholders)
    sql_statement = f"""
    SELECT fetch_date FROM research_fetch_status
    WHERE fetch_date = ANY(ARRAY[{placeholder_string}]::DATE[]) AND status = 'success'
    """

    parameters = [
        {"name": f"date{i}", "value": {"stringValue": date.strftime("%Y-%m-%d")}} for i, date in enumerate(past_dates)
    ]

    try:
        response = client.execute_statement(
            resourceArn=aurora_cluster_arn,
            secretArn=db_credentials_secret_arn,
            database=database,
            sql=sql_statement,
            parameters=parameters,
        )

        fetched_dates = [
            datetime.strptime(result[0]["stringValue"], "%Y-%m-%d").date() for result in response["records"]
        ]
        unfetched_dates = list(set(past_dates) - set(fetched_dates))
        logger.info(f"Unfetched dates: {unfetched_dates}")

        earliest_date = min(unfetched_dates) if unfetched_dates else None
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")
        earliest_date = None

    return earliest_date


def attempt_fetch_for_dates(
    base_url: str,
    summary_set: str,
    bucket_name: str,
    aurora_cluster_arn: str,
    db_credentials_secret_arn: str,
    database: str,
    today: date,
    earliest_unfetched_date: date,
) -> date:
    """
    Fetches arXiv daily summaries for the given dates using AWS RDSDataService.

    Args:
        base_url (str): Base URL for the API.
        summary_set (str): Summary set.
        bucket_name (str): S3 bucket name.
        aurora_cluster_arn (str): The ARN of the Aurora Serverless DB cluster.
        db_credentials_secret_arn (str): The ARN of the secret containing
        credentials to access the DB.
        database (str): Database name.
        today (date): Today's date.
        earliest_unfetched_date (date): Earliest unfetched date.

    Returns:
    date: The last date for which fetch was successful.
    """
    last_success_date = None

    if earliest_unfetched_date:
        full_xml_responses = fetch_data(base_url, earliest_unfetched_date, summary_set)
        date_list = generate_date_list(earliest_unfetched_date, today)
        for list_date in date_list:
            status = get_fetch_status(list_date, aurora_cluster_arn, db_credentials_secret_arn, database)

            if status == "success":
                date_list.remove(list_date)
        logger.info(f"Date list: {date_list}")

        for date_to_fetch in date_list:
            logger.info(f"Fetching for date: {date_to_fetch}")
            insert_fetch_status(date_to_fetch, aurora_cluster_arn, db_credentials_secret_arn, database)
            success = update_research_fetch_status(
                date_to_fetch,
                summary_set,
                bucket_name,
                aurora_cluster_arn,
                db_credentials_secret_arn,
                database,
                full_xml_responses,
            )
            if success:
                logger.info(f"Fetch successful for date: {date_to_fetch}")
                last_success_date = date_to_fetch
            else:
                logger.error(f"Fetch failed for date: {date_to_fetch}")
        filename = f"arxiv/raw_summaries/{summary_set}-{earliest_unfetched_date.strftime('%Y-%m-%d')}.xml"
        lambda_name = os.environ.get("PARSE_LAMBDA_FUNCTION_NAME")
        filenames = upload_to_s3(filename, bucket_name, full_xml_responses)
        call_parse_summaries(bucket_name, filenames, lambda_name)
    else:
        logger.warning(NO_UNFETCHED_DATES_FOUND)

    return last_success_date


def get_fetch_status(date: date, aurora_cluster_arn, db_credentials_secret_arn, database):
    """
    Gets fetch status for the given date using AWS RDSDataService.

    Args:
        date (date): Date for which to get fetch status.
        aurora_cluster_arn (str): The ARN of the Aurora Serverless DB cluster.
        db_credentials_secret_arn (str): The ARN of the secret containing
        credentials to access the DB.
        database (str): Database name.

    Returns:
        str: Fetch status.
    """
    client = boto3.client("rds-data")
    formatted_date = date.strftime("%Y-%m-%d")

    sql_statement = """
    SELECT status FROM research_fetch_status
    WHERE fetch_date = CAST(:date AS DATE)
    """

    parameters = [{"name": "date", "value": {"stringValue": formatted_date}}]

    response = client.execute_statement(
        resourceArn=aurora_cluster_arn,
        secretArn=db_credentials_secret_arn,
        database=database,
        sql=sql_statement,
        parameters=parameters,
    )
    logger.info(f"Fetch status response: {response} for date: {date}")
    if response["records"]:
        return response["records"][0][0]["stringValue"]
    else:
        return None


def generate_date_list(start_date: date, end_date: date) -> List[date]:
    """
    Generates a list of dates between the given start and end dates.

    Args:
        start_date (date): Start date.
        end_date (date): End date.

    Returns:
        List[date]: List of dates.
    """
    delta = end_date - start_date
    if delta.days < 0:
        raise ValueError("End date must be after start date")
    return [(start_date + timedelta(days=i)) for i in range((delta.days) + 1)]


def fetch_data(base_url: str, from_date: date, summary_set: str) -> List[str]:
    """
    Fetches data from the API.

    Args:
        base_url (str): Base URL for the API.
        from_date (date): Summary date.
        summary_set (str): Summary set.

    Returns:
        List[str]: List of XML responses.
    """
    full_xml_responses = []
    str_date = from_date.strftime("%Y-%m-%d")
    logger.info(f"Fetching data for date: {str_date}")
    params = {
        "verb": "ListRecords",
        "set": summary_set,
        "metadataPrefix": "oai_dc",
        "from": str_date,
    }
    retry_count = 0
    while True:
        if retry_count > 5:
            break
        status_code, xml_content = fetch_http_response(base_url, params)
        if status_code != 200:
            logger.error(f"HTTP error, probably told to back off: {status_code}")
            backoff_time = handle_http_error(status_code, xml_content, retry_count)
            if backoff_time:
                time.sleep(backoff_time)
                retry_count += 1
                continue
            else:
                break

        if xml_content.strip():
            full_xml_responses.append(xml_content)

        resumption_token = extract_resumption_token(xml_content)
        logger.info(f"Response: {xml_content.splitlines()[-3:]}")
        if resumption_token:
            logger.info(f"Resumption token: {resumption_token}")
            params = {"verb": "ListRecords", "resumptionToken": resumption_token}
            time.sleep(5)
        else:
            break

    return full_xml_responses


def extract_resumption_token(xml_content: str) -> str:
    """Extracts resumption token from XML content.

    Args:
        xml_content (str): XML content.

    Returns:
        str: Resumption token.
    """
    try:
        logger.info("Extracting resumption token")
        root = ET.fromstring(xml_content)
        token_element = root.find(".//resumptionToken")
        logger.info(f"Resumption token element: {token_element}")
        return token_element.text if token_element is not None else None
    except ET.ParseError:
        return ""


def fetch_http_response(base_url: str, params: dict) -> tuple[int, str]:
    """Fetches HTTP response.

    Args:
        base_url (str): Base URL for the API.
        params (dict): Request parameters.

    Returns:
        requests.Response: Response object.
    """
    response = requests.get(base_url, params=params, timeout=60)
    return response.status_code, response.text


def handle_http_error(status_code: int, response_text: str, retry_count: int) -> int:
    """
    Handles HTTP error.

    Args:
        status_code (int): HTTP status code.~
        response_text (str): Response text.
        retry_count (int): Retry count.

    Returns:
        int: Backoff time.
    """
    if "maintenance" in response_text.lower():
        schedule_for_later()
        return 0
    backoff_times = [30, 120]
    if status_code == 503 and retry_count < len(backoff_times):
        logger.info(
            f"Received 503, retrying after \
                {backoff_times[retry_count]} seconds"
        )
        return backoff_times[retry_count]
    return 0


def extract_resumption_token_from_last_lines(xml_content: str) -> str or None:
    """
    Extracts resumption token from the last few lines of XML content.

    Args:
        xml_content (str): XML content.

    Returns:
        str: Resumption token or None if not found.
    """
    last_lines = xml_content.splitlines()[-3:]
    last_lines_str = "\n".join(last_lines)
    match = re.search(r'<resumptionToken[^>]*>([^<]+)</resumptionToken>', last_lines_str)
    if match:
        return match.group(1)
    else:
        logger.info("No resumption token found in the last lines.")
        return None


def schedule_for_later() -> None:
    """
    Schedules the Lambda function for later.
    """
    future_time = datetime.today() + timedelta(hours=5)

    cron_time = future_time.strftime("%M %H %d %m ? %Y")

    client = boto3.client("events")

    client.put_rule(Name="DynamicRule", ScheduleExpression=f"cron({cron_time})", State="ENABLED")

    lambda_arn = f"arn:aws:lambda:{os.environ['AWS_REGION']}:\
        {os.environ['AWS_ACCOUNT_ID']}:function:\
            {os.environ['AWS_LAMBDA_FUNCTION_NAME']}"

    client.put_targets(
        Rule="DynamicRule",
        Targets=[{"Id": "reschedule-{os.environ['AWS_LAMBDA_FUNCTION_NAME']}}", "Arn": lambda_arn}],
    )


def update_research_fetch_status(
    from_date: date,
    summary_set: str,
    bucket_name: str,
    aurora_cluster_arn: str,
    db_credentials_secret_arn: str,
    database: str,
    fetched_data: List[str],
) -> bool:
    """
    Checks if research was found for a given date and updates that
    date's research fetch status

    Args:
        from_date (date): Summary date.
        summary_set (str): Summary set.
        bucket_name (str): S3 bucket name.
        aurora_cluster_arn (str): The ARN of the Aurora Serverless DB cluster.
        db_credentials_secret_arn (str): The ARN of the secret containing
        credentials to access the DB.
        database (str): Database name.
        fetched_data (List[str]): List of XML responses.

    Returns:
        bool: True if fetch was successful, False otherwise.
    """
    pattern = r"<dc:description>.*?<dc:date>" + re.escape(from_date.strftime("%Y-%m-%d")) + r"</dc:date>"

    success = any(re.search(pattern, xml, re.DOTALL) for xml in fetched_data)

    if success:
        set_fetch_status(from_date, "success", aurora_cluster_arn, db_credentials_secret_arn, database)
    else:
        set_fetch_status(from_date, "failure", aurora_cluster_arn, db_credentials_secret_arn, database)

    return success


def set_fetch_status(date: date, status, aurora_cluster_arn, db_credentials_secret_arn, database):
    """
    Sets fetch status in the database using AWS RDSDataService.

    Args:
        date (date): Date for which to set fetch status.
        status (str): Status to set ('success' or 'failure').
        aurora_cluster_arn (str): The ARN of the Aurora Serverless DB cluster.
        db_credentials_secret_arn (str): The ARN of the secret containing
        credentials to access the DB.
        database (str): Database name.
    """
    client = boto3.client("rds-data")

    try:
        sql_statement = "UPDATE research_fetch_status SET status = :status \
            WHERE fetch_date = CAST(:date AS DATE)"

        parameters = [
            {"name": "date", "value": {"stringValue": date.strftime("%Y-%m-%d")}},
            {"name": "status", "value": {"stringValue": status}},
        ]

        client.execute_statement(
            resourceArn=aurora_cluster_arn,
            secretArn=db_credentials_secret_arn,
            database=database,
            sql=sql_statement,
            parameters=parameters,
        )
        return True
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")
        return False


def upload_to_s3(filename: str, bucket_name: str, full_xml_responses: List[str]):
    """Uploads XML responses to S3.

    Args:
        filename (str): Filename.
        bucket_name (str): S3 bucket name.
        full_xml_responses (List[str]): XML responses.
    """
    if not full_xml_responses:
        raise ValueError("No XML responses to upload")
    if not bucket_name:
        raise ValueError("No bucket name specified")
    if not filename:
        raise ValueError("No filename specified")

    logger.info(f"Uploading {len(full_xml_responses)} XML responses to S3")
    s3 = boto3.client("s3")
    filenames = []
    for idx, xml_response in enumerate(full_xml_responses):
        iteration_filename = f"{filename}_{idx}.xml"
        s3.put_object(
            Body=xml_response,
            Bucket=bucket_name,
            Key=iteration_filename,
        )
        filenames.append(iteration_filename)

    return filenames


def call_parse_summaries(bucket_name: str, filenames: List[str], lambda_name: str):
    """
    Calls parse summaries.

    Args:
        bucket_name (str): S3 bucket name.
        filename (str): Filename.
        lambda_name (str): Lambda name.
    """
    if not bucket_name:
        raise ValueError("No bucket name specified")
    if not filenames:
        raise ValueError("No filename specified")
    if not lambda_name:
        raise ValueError("No lambda name specified")

    logger.info("Calling parse summaries function for " + filenames + " in bucket " + bucket_name)
    lambda_client = boto3.client("lambda")
    for filename in filenames:
        event_payload = {"bucket_name": bucket_name, "filename": filename}
        lambda_client.invoke(
            FunctionName=lambda_name,
            InvocationType="Event",
            Payload=json.dumps(event_payload),
        )
