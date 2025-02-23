import logging
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
from docx import Document
from io import BytesIO

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

ssm = boto3.client('ssm')
s3 = boto3.client('s3')
ses = boto3.client('ses')

def get_config():
    """Get configuration from SSM Parameter Store"""
    config_path = os.getenv("CONFIG_PATH")
    try:
        params = ssm.get_parameters(
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

def send_email_with_attachments(recipients: list, subject: str, body: str, attachments: list):
    """Send email with DOCX attachments using SES"""
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
        
        response = ses.send_raw_email(
            Source=recipients[0],  # Use first recipient as sender
            Destinations=recipients,
            RawMessage={'Data': msg.as_string()}
        )
        logger.info(f"Email sent! Message ID: {response['MessageId']}")
    except ClientError as e:
        logger.error(f"Error sending email: {e}")
        raise

def get_s3_files(bucket: str, prefix: str) -> list:
    """Get files from S3 with given prefix"""
    try:
        logger.info(f"Looking for files in s3://{bucket}/{prefix}")
        response = s3.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )
        if 'Contents' in response:
            logger.info(f"Found {len(response['Contents'])} files")
            files = []
            for obj in response['Contents']:
                logger.info(f"Getting file: {obj['Key']}")
                file_response = s3.get_object(Bucket=bucket, Key=obj['Key'])
                filename = obj['Key'].split('/')[-1]
                data = file_response['Body'].read()
                logger.info(f"Read {len(data)} bytes from {filename}")
                files.append({
                    'data': data,
                    'filename': filename
                })
            return files
        logger.warning(f"No files found in s3://{bucket}/{prefix}")
        return []
    except Exception as e:
        logger.error(f"Error getting files from S3: {e}")
        return []

def lambda_handler(event, context):
    """Lambda handler to email daily summaries"""
    try:
        config = get_config()
        logger.info(f"Using S3 bucket: {config['s3_bucket']}")
        
        # Use PST timezone
        pst = ZoneInfo('America/Los_Angeles')
        today = datetime.now(pst)
        logger.info(f"Current time (PST): {today}")
        
        arxiv_date = (today - timedelta(days=config['back_date'])).strftime("%Y-%m-%d")  # Use back_date from SSM
        today_str = today.strftime("%Y-%m-%d")  # NVD reports from today
        logger.info(f"Looking for ArXiv summaries from: {arxiv_date}")
        logger.info(f"Looking for NVD reports from: {today_str}")
        
        # Get ArXiv summaries using back_date from SSM
        arxiv_path = f"newsletters/{arxiv_date}/"
        logger.info(f"ArXiv path: {arxiv_path}")
        arxiv_files = get_s3_files(config['s3_bucket'], arxiv_path)
        logger.info(f"Found {len(arxiv_files)} arxiv files: {[f['filename'] for f in arxiv_files]}")
        
        # Get NVD report (from today for immediate vulnerability reporting)
        nvd_path = f"reports/daily/{today_str}/"
        logger.info(f"NVD path: {nvd_path}")
        nvd_files = get_s3_files(config['s3_bucket'], nvd_path)
        logger.info(f"Found {len(nvd_files)} nvd files: {[f['filename'] for f in nvd_files]}")
        
        all_files = arxiv_files + nvd_files
        logger.info(f"Total files to send: {len(all_files)}")
        
        if not all_files:
            logger.warning(f"No reports found for arxiv({arxiv_date}) or nvd({today_str})")
            return {
                'statusCode': 200,
                'body': 'No reports to send'
            }
        
        body = f"Daily Summary for {today_str}\n\n"
        
        categories = {}
        for file in arxiv_files:
            # Extract category from filename (e.g. "AI_research_summary.docx" -> "AI")
            category = file['filename'].split('_')[0]
            if category not in categories:
                categories[category] = []
            
            doc = Document(BytesIO(file['data']))
            
            # Extract only title lines with PDF links
            for para in doc.paragraphs:
                text = para.text.strip()
                if '[PDF]' in text:  # This is a title line
                    categories[category].append(text)
        
        # Add categorized papers to email body
        if arxiv_files:
            body += f"ArXiv Research Summaries from {arxiv_date}:\n\n"
            for category, titles in categories.items():
                if titles:  # Only add categories that have papers
                    body += f"{category}:\n"
                    for title in titles:
                        body += f"{title}\n"
                    body += "\n"
            body += "Full summaries are attached.\n\n"
            
        if nvd_files:
            body += "Today's NVD vulnerability report is attached.\n"
            
        body += "\nBest regards,\nAtomikLabs Daily Summary"
        
        send_email_with_attachments(
            recipients=config['recipients'],
            subject=f"AtomikLabs Daily Summary - {today_str}",
            body=body,
            attachments=all_files
        )
        
        return {
            'statusCode': 200,
            'body': 'Email sent successfully'
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}")
        raise
