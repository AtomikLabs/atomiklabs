import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json

import boto3
from botocore.exceptions import ClientError
from shared.db import SQLiteDB

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

def get_config(ssm_client):
    """Get configuration from SSM Parameter Store
    
    Args:
        ssm_client: boto3 SSM client
    """
    config_path = os.getenv("CONFIG_PATH")
    if not config_path:
        raise ValueError("CONFIG_PATH environment variable is required")
        
    try:
        params = ssm_client.get_parameters(
            Names=[
                f"{config_path}/arxiv/s3_bucket",
                f"{config_path}/arxiv/email/recipients",
                f"{config_path}/arxiv/back_date"
            ]
        )
        config = {}
        for param in params['Parameters']:
            name = param['Name'].split('/')[-1]
            if name == 'recipients':
                config[name] = param['Value'].split(',')
            elif name == 'back_date':
                config[name] = int(param['Value'])
            else:
                config[name] = param['Value']
        return config
    except ClientError as e:
        logger.error(f"Error fetching config: {e}")
        raise

def send_email_with_attachments(ses_client, recipients: list, subject: str, body: str, attachments: list):
    """Send email with DOCX attachments using SES
    
    Args:
        ses_client: boto3 SES client
        recipients: List of email addresses
        subject: Email subject
        body: Email body text
        attachments: List of dicts with 'data' and 'filename' keys
    """
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = recipients[0]  # Use first recipient as sender
        msg['To'] = ', '.join(recipients)
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
        # Add attachments
        for attachment in attachments:
            part = MIMEApplication(attachment['data'])
            part.add_header('Content-Disposition', 'attachment', filename=attachment['filename'])
            msg.attach(part)
        
        response = ses_client.send_raw_email(
            Source=recipients[0],  # Use first recipient as sender
            Destinations=recipients,
            RawMessage={'Data': msg.as_string()}
        )
        logger.info(f"Email sent! Message ID: {response['MessageId']}")
        return response['MessageId']
    except ClientError as e:
        logger.error(f"Error sending email: {e}")
        raise

def get_s3_files(s3_client, bucket: str, prefix: str) -> list:
    """Get files from S3 with given prefix
    
    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name
        prefix: S3 key prefix to search
    """
    try:
        logger.info(f"Looking for files in s3://{bucket}/{prefix}")
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )
        if 'Contents' in response:
            logger.info(f"Found {len(response['Contents'])} files")
            files = []
            for obj in response['Contents']:
                logger.info(f"Getting file: {obj['Key']}")
                file_response = s3_client.get_object(Bucket=bucket, Key=obj['Key'])
                filename = obj['Key'].split('/')[-1]
                data = file_response['Body'].read()
                logger.info(f"Read {len(data)} bytes from {filename}")
                files.append({
                    'data': data,
                    'filename': filename,
                    's3_key': obj['Key']
                })
            return files
        logger.warning(f"No files found in s3://{bucket}/{prefix}")
        return []
    except Exception as e:
        logger.error(f"Error getting files from S3: {e}")
        return []

def get_unsent_newsletters(db: SQLiteDB, date: str) -> list:
    """Get newsletters that haven't been sent yet
    
    Args:
        db: SQLiteDB instance
        date: Date string in YYYY-MM-DD format
    """
    return db.execute("""
        SELECT n.id, n.category_code, n.s3_key
        FROM newsletters n
        LEFT JOIN newsletter_emails ne ON n.id = ne.newsletter_id
        WHERE n.date = ? AND ne.newsletter_id IS NULL
    """, (date,)).fetchall()

def record_email_batch(db: SQLiteDB, date: str, recipients: list, newsletter_ids: list, message_id: str):
    """Record that newsletters were sent in an email batch
    
    Args:
        db: SQLiteDB instance
        date: Date string in YYYY-MM-DD format
        recipients: List of email addresses
        newsletter_ids: List of newsletter IDs that were sent
        message_id: SES message ID
    """
    with db.transaction() as conn:
        # Record email batch
        db.execute(
            "INSERT INTO email_batches (date, recipient_list, message_id) VALUES (?, ?, ?)",
            (date, ','.join(recipients), message_id)
        )
        batch_id = conn.lastrowid

        # Link newsletters to batch
        for newsletter_id in newsletter_ids:
            db.execute(
                "INSERT INTO newsletter_emails (newsletter_id, email_batch_id) VALUES (?, ?)",
                (newsletter_id, batch_id)
            )

def lambda_handler(event, context):
    """Lambda handler to email daily summaries
    
    Args:
        event: Lambda event
        context: Lambda context
    """
    try:
        # Initialize AWS clients
        ssm_client = boto3.client('ssm')
        s3_client = boto3.client('s3')
        ses_client = boto3.client('ses')
        
        config = get_config(ssm_client)
        logger.info(f"Using S3 bucket: {config['s3_bucket']}")
        
        # Use PST timezone
        pst = ZoneInfo('America/Los_Angeles')
        today = datetime.now(pst)
        logger.info(f"Current time (PST): {today}")
        
        arxiv_date = (today - timedelta(days=config['back_date'])).strftime("%Y-%m-%d")  # Use back_date from SSM
        today_str = today.strftime("%Y-%m-%d")  # NVD reports from today
        logger.info(f"Looking for ArXiv summaries from: {arxiv_date}")
        logger.info(f"Looking for NVD reports from: {today_str}")
        
        # Get unsent newsletters
        db = SQLiteDB('/mnt/sqlite/arxiv.db')
        unsent = get_unsent_newsletters(db, arxiv_date)
        if not unsent:
            logger.info(f"No unsent newsletters found for {arxiv_date}")
            return {
                'statusCode': 200,
                'body': 'No newsletters to send'
            }

        # Get newsletter files directly from S3 using keys from DB
        all_files = []
        newsletter_ids = []
        for newsletter_id, category, s3_key in unsent:
            try:
                file_response = s3_client.get_object(Bucket=config['s3_bucket'], Key=s3_key)
                filename = s3_key.split('/')[-1]
                data = file_response['Body'].read()
                logger.info(f"Read {len(data)} bytes from {filename}")
                all_files.append({
                    'data': data,
                    'filename': filename,
                    's3_key': s3_key
                })
                newsletter_ids.append(newsletter_id)
            except ClientError as e:
                logger.error(f"Error getting newsletter {s3_key}: {e}")
                continue

        # Get NVD report (from today for immediate vulnerability reporting)
        nvd_path = f"reports/daily/{today_str}/"
        logger.info(f"NVD path: {nvd_path}")
        nvd_files = get_s3_files(s3_client, config['s3_bucket'], nvd_path)
        logger.info(f"Found {len(nvd_files)} nvd files")
        all_files.extend(nvd_files)
        logger.info(f"Total files to send: {len(all_files)}")
        
        if not all_files:
            logger.warning(f"No reports found for arxiv({arxiv_date}) or nvd({today_str})")
            return {
                'statusCode': 200,
                'body': 'No reports to send'
            }
        
        body = f"Daily Summary for {today_str}\n\n"
        
        if newsletter_ids:
            body += f"Attached are your arXiv research summaries from {arxiv_date}.\n\n"
        if nvd_files:
            body += "Attached is today's NVD vulnerability report.\n"
            
        body += "\nBest regards,\nAtomikLabs Daily Summary"
        
        # Send email and record batch
        message_id = send_email_with_attachments(
            ses_client=ses_client,
            recipients=config['recipients'],
            subject=f"AtomikLabs Daily Summary - {today_str}",
            body=body,
            attachments=all_files
        )

        record_email_batch(
            db=db,
            date=arxiv_date,
            recipients=config['recipients'],
            newsletter_ids=newsletter_ids,
            message_id=message_id
        )
        
        return {
            'statusCode': 200,
            'body': 'Email sent successfully'
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}")
        raise
