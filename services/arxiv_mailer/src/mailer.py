import json
import logging
import os
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

# Initialize AWS clients
ssm = boto3.client('ssm')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

def get_config():
    """Get configuration from SSM Parameter Store"""
    config_path = os.getenv("CONFIG_PATH")
    try:
        params = ssm.get_parameters(
            Names=[
                f"{config_path}/categories",
                f"{config_path}/s3_bucket",
                f"{config_path}/dynamodb_table",
                f"{config_path}/email/recipients"
            ]
        )
        config = {}
        for param in params['Parameters']:
            name = param['Name'].split('/')[-1]
            if name == 'categories':
                config[name] = param['Value'].split(',')
            elif name == 'recipients':
                config[name] = param['Value'].split(',')
            else:
                config[name] = param['Value']
        return config
    except ClientError as e:
        logger.error(f"Error fetching config: {e}")
        raise

def format_html_email(date: str, summaries: dict) -> str:
    """Format HTML email with research summaries"""
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            h1 {{ color: #2c5282; }}
            h2 {{ color: #2b6cb0; margin-top: 20px; }}
            .paper {{ margin: 15px 0; padding: 10px; border-left: 3px solid #4299e1; }}
            .title {{ font-weight: bold; color: #2b6cb0; }}
            .authors {{ font-style: italic; color: #4a5568; }}
            .abstract {{ margin-top: 10px; }}
            .links {{ margin-top: 5px; }}
            a {{ color: #3182ce; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <h1>ArXiv Research Summaries - {date}</h1>
    """

    for category, data in summaries.items():
        html += f"<h2>{category} Papers</h2>"
        for paper in data['papers']:
            html += f"""
            <div class="paper">
                <div class="title">{paper['title']}</div>
                <div class="authors">By: {', '.join([f"{a['first_name']} {a['last_name']}" for a in paper['authors']])}</div>
                <div class="abstract">{paper['abstract']}</div>
                <div class="links">
                    <a href="{paper['abstract_url']}">Abstract</a> | 
                    <a href="{paper['abstract_url'].replace('abs', 'pdf')}">PDF</a>
                </div>
            </div>
            """

    html += """
    </body>
    </html>
    """
    return html

def send_email(recipients: list, subject: str, html_content: str):
    """Send email using SES"""
    try:
        response = ses.send_email(
            Source=f"no-reply@{ses.meta.region_name}.amazonses.com",
            Destination={
                'ToAddresses': recipients
            },
            Message={
                'Subject': {
                    'Data': subject
                },
                'Body': {
                    'Html': {
                        'Data': html_content
                    }
                }
            }
        )
        logger.info(f"Email sent! Message ID: {response['MessageId']}")
    except ClientError as e:
        logger.error(f"Error sending email: {e}")
        raise

def lambda_handler(event, context):
    """Lambda handler to process and email research summaries"""
    try:
        # Get configuration
        config = get_config()
        
        # Get the date from the Step Functions input
        date = event.get('date', datetime.today().strftime('%Y-%m-%d'))
        
        # Initialize DynamoDB table
        table = dynamodb.Table(config['dynamodb_table'])
        
        # Get the daily summary record
        response = table.get_item(
            Key={
                'id': 'daily-summary',
                'date': date
            }
        )
        
        if 'Item' not in response:
            logger.warning(f"No summary found for date {date}")
            return {
                'statusCode': 200,
                'body': 'No papers to process'
            }
        
        # Get the summaries from the daily summary record
        summaries = response['Item']['summaries']
        
        if not summaries:
            logger.warning(f"No papers found for date {date}")
            return {
                'statusCode': 200,
                'body': 'No papers to process'
            }
        
        # Format and send email
        html_content = format_html_email(date, summaries)
        send_email(
            recipients=config['recipients'],
            subject=f"ArXiv Research Summaries - {date}",
            html_content=html_content
        )
        
        return {
            'statusCode': 200,
            'body': 'Email sent successfully'
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}")
        raise
