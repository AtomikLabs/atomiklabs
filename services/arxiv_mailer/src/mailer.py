import logging
import os
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import boto3
from botocore.exceptions import ClientError

# Import data layer components
from atomiklabs_data import (
    init_db, get_session,
    NewsletterRepository, EmailRepository
)

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

def send_email_with_attachments(ses_client, recipients: list, subject: str, body: str, attachments: list, newsletter_id: int = None):
    """Send email with DOCX attachments using SES
    
    Args:
        ses_client: boto3 SES client
        recipients: List of email addresses
        subject: Email subject
        body: Email body text
        attachments: List of dicts with 'data' and 'filename' keys
        newsletter_id: ID of newsletter in database (optional)
    
    Returns:
        Email record ID if newsletter_id is provided, otherwise None
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
        
        # Record email in database if newsletter_id is provided
        if newsletter_id:
            try:
                # Initialize the database
                init_db()
                
                with get_session() as session:
                    s3_path = f"emails/{datetime.now().strftime('%Y-%m-%d')}/{response['MessageId']}"
                    
                    # Create email record
                    email = EmailRepository.create_email(
                        session=session,
                        subject=subject,
                        newsletter_id=newsletter_id,
                        recipient_count=len(recipients),
                        s3_path=s3_path
                    )
                    logger.info(f"Email record created with ID: {email.id}")
                    return email.id
            except Exception as e:
                logger.error(f"Error recording email in database: {e}")
                # Continue even if database recording fails
                
        return None
        
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

def get_newsletters_for_date(date_obj: date) -> list:
    """Get newsletters from database for a specific date
    
    Args:
        date_obj: Date object to filter newsletters
    
    Returns:
        List of newsletter objects
    """
    try:
        # Initialize the database
        init_db()
        
        with get_session() as session:
            # Query for newsletters with the given issue date
            newsletters = []
            
            # We don't have a direct method to get newsletters by date
            # For real implementation, add this method to NewsletterRepository
            # For now, we'll work with what we have
            newsletter = NewsletterRepository.get_newsletter_by_date(
                session=session,
                issue_date=date_obj
            )
            
            if newsletter:
                newsletters.append(newsletter)
                logger.info(f"Found newsletter: {newsletter.title} (ID: {newsletter.id})")
                
            return newsletters
    except Exception as e:
        logger.error(f"Error getting newsletters from database: {e}")
        return []

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
        arxiv_date_obj = datetime.strptime(arxiv_date, "%Y-%m-%d").date()
        
        today_str = today.strftime("%Y-%m-%d")  # NVD reports from today
        logger.info(f"Looking for ArXiv summaries from: {arxiv_date}")
        logger.info(f"Looking for NVD reports from: {today_str}")
        
        # Initialize DB connection
        init_db()
        
        # Get newsletters from database
        newsletters = get_newsletters_for_date(arxiv_date_obj)
        logger.info(f"Found {len(newsletters)} newsletters in database for {arxiv_date}")
        
        # Get ArXiv summaries using back_date from SSM
        # Even with DB integration, we still need to get the actual files from S3
        arxiv_path = f"newsletters/{arxiv_date}/"
        logger.info(f"ArXiv path: {arxiv_path}")
        arxiv_files = get_s3_files(s3_client, config['s3_bucket'], arxiv_path)
        logger.info(f"Found {len(arxiv_files)} arxiv files: {[f['filename'] for f in arxiv_files]}")
        
        # Match S3 files with database records
        if newsletters and arxiv_files:
            # Create a map of S3 keys to files
            s3_key_to_file = {file['s3_key']: file for file in arxiv_files}
            
            # Match newsletters with their files
            for newsletter in newsletters:
                if newsletter.s3_path in s3_key_to_file:
                    logger.info(f"Matched newsletter ID {newsletter.id} with S3 file {newsletter.s3_path}")
                    # Mark this file as linked to a newsletter
                    s3_key_to_file[newsletter.s3_path]['newsletter_id'] = newsletter.id
        
        # Get NVD report (from today for immediate vulnerability reporting)
        nvd_path = f"reports/daily/{today_str}/"
        logger.info(f"NVD path: {nvd_path}")
        nvd_files = get_s3_files(s3_client, config['s3_bucket'], nvd_path)
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
        
        if arxiv_files:
            # Get newsletter titles from database if available
            if newsletters:
                newsletter_titles = [n.title for n in newsletters]
                titles_text = ", ".join(newsletter_titles)
                body += f"Attached are your arXiv research summaries ({titles_text}) from {arxiv_date}.\n"
            else:
                body += f"Attached are your arXiv research summaries from {arxiv_date}.\n"
        
        if nvd_files:
            body += "Attached is today's NVD vulnerability report.\n"
            
        body += "\nBest regards,\nAtomikLabs Daily Summary"
        
        # Find a newsletter ID to associate with this email
        newsletter_id = None
        for file in arxiv_files:
            if 'newsletter_id' in file:
                newsletter_id = file['newsletter_id']
                logger.info(f"Using newsletter ID {newsletter_id} for email record")
                break
        
        email_id = send_email_with_attachments(
            ses_client=ses_client,
            recipients=config['recipients'],
            subject=f"AtomikLabs Daily Summary - {today_str}",
            body=body,
            attachments=all_files,
            newsletter_id=newsletter_id
        )
        
        result = {
            'statusCode': 200,
            'body': 'Email sent successfully'
        }
        
        if email_id:
            result['emailId'] = email_id
            
        return result
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}")
        raise
