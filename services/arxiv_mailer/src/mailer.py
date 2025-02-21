import logging
import os
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
                f"{config_path}/s3_bucket",
                f"{config_path}/email/recipients"
            ]
        )
        config = {}
        for param in params['Parameters']:
            name = param['Name'].split('/')[-1]
            if name == 'recipients':
                config[name] = param['Value'].split(',')
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

def lambda_handler(event, context):
    """Lambda handler to email research summaries"""
    try:
        config = get_config()
        today = datetime.today()
        date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # List objects in the newsletters folder for yesterday
        prefix = f"newsletters/{date}/"
        response = s3.list_objects_v2(
            Bucket=config['s3_bucket'],
            Prefix=prefix
        )
        
        if 'Contents' not in response:
            logger.warning(f"No summaries found for {date}")
            return {
                'statusCode': 200,
                'body': 'No summaries to send'
            }
        
        # Get each file's contents
        attachments = []
        for obj in response['Contents']:
            file_response = s3.get_object(Bucket=config['s3_bucket'], Key=obj['Key'])
            filename = obj['Key'].split('/')[-1]  # Get just the filename
            attachments.append({
                'data': file_response['Body'].read(),
                'filename': filename
            })
        
        if attachments:
            body = f"Here are your arXiv research summaries for {date}.\n\nBest regards,\nArXiv Summarizer"
            send_email_with_attachments(
                recipients=config['recipients'],
                subject=f"ArXiv Research Summaries - {date}",
                body=body,
                attachments=attachments
            )
            return {
                'statusCode': 200,
                'body': 'Email sent successfully'
            }
        else:
            return {
                'statusCode': 200,
                'body': 'No summaries to send'
            }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}")
        raise
