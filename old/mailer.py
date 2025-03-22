import logging
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

ssm = boto3.client('ssm')
s3 = boto3.client('s3')
ses = boto3.client('ses')

def get_config(ssm_client=None):
    """Get configuration from SSM Parameter Store"""
    ssm_client = ssm_client or ssm
    config_path = os.getenv("CONFIG_PATH")
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

def send_email_with_attachments(recipients: list, subject: str, body: str, attachments: list, ses_client=None):
    """Send email with DOCX attachments using SES"""
    ses_client = ses_client or ses
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = recipients[0]
        msg['To'] = ', '.join(recipients)
        
        msg.attach(MIMEText(body, 'plain'))
        
        for attachment in attachments:
            part = MIMEApplication(attachment['data'])
            part.add_header('Content-Disposition', 'attachment', filename=attachment['filename'])
            msg.attach(part)
        
        response = ses_client.send_raw_email(
            Source=recipients[0],
            Destinations=recipients,
            RawMessage={'Data': msg.as_string()}
        )
        logger.info(f"Email sent! Message ID: {response['MessageId']}")
    except ClientError as e:
        logger.error(f"Error sending email: {e}")
        raise

def get_s3_files(bucket: str, prefix: str, s3_client=None) -> list:
    """Get files from S3 with given prefix"""
    s3_client = s3_client or s3
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
                    'filename': filename
                })
            return files
        logger.warning(f"No files found in s3://{bucket}/{prefix}")
        return []
    except Exception as e:
        logger.error(f"Error getting files from S3: {e}")
        return []

def lambda_handler(event, context, *, ssm_client=None, s3_client=None, ses_client=None):
    """Lambda handler to email daily summaries"""
    ssm_client = ssm_client or ssm
    s3_client = s3_client or s3
    ses_client = ses_client or ses
    
    try:
        config = get_config(ssm_client=ssm_client)
        logger.info(f"Using S3 bucket: {config['s3_bucket']}")
        
        pst = ZoneInfo('America/Los_Angeles')
        today = datetime.now(pst)
        logger.info(f"Current time (PST): {today}")
        
        today_str = today.strftime("%Y-%m-%d")
        logger.info(f"Looking for ArXiv summaries from: {today_str}")
        logger.info(f"Looking for NVD reports from: {today_str}")
        
        arxiv_path = f"newsletters/{today_str}/"
        logger.info(f"ArXiv path: {arxiv_path}")
        arxiv_files = get_s3_files(config['s3_bucket'], arxiv_path, s3_client=s3_client)
        logger.info(f"Found {len(arxiv_files)} arxiv files: {[f['filename'] for f in arxiv_files]}")
        
        nvd_path = f"reports/daily/{today_str}/"
        logger.info(f"NVD path: {nvd_path}")
        nvd_files = get_s3_files(config['s3_bucket'], nvd_path, s3_client=s3_client)
        logger.info(f"Found {len(nvd_files)} nvd files: {[f['filename'] for f in nvd_files]}")
        
        all_files = arxiv_files + nvd_files
        logger.info(f"Total files to send: {len(all_files)}")
        
        if not all_files:
            logger.warning(f"No reports found for arxiv({today_str}) or nvd({today_str})")
            return {
                'statusCode': 200,
                'body': 'No reports to send'
            }
        
        body = f"Daily Summary for {today_str}\n\n"
        
        if arxiv_files:
            body += f"Attached are your arXiv research summaries from {today_str}.\n"
        if nvd_files:
            body += "Attached is today's NVD vulnerability report.\n"
            
        body += "\nBest regards,\nAtomikLabs Daily Summary"
        
        send_email_with_attachments(
            recipients=config['recipients'],
            subject=f"AtomikLabs Daily Summary - {today_str}",
            body=body,
            attachments=all_files,
            ses_client=ses_client
        )
        
        return {
            'statusCode': 200,
            'body': 'Email sent successfully'
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}")
        raise
