import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, UTC, date as date_type
from html import unescape
from io import BytesIO

import boto3
import defusedxml.ElementTree as ET
import docx
import requests
from docx import Document
from botocore.exceptions import ClientError

# Import data layer components
from atomiklabs_data import (
    init_db, get_session, 
    ArticleRepository, AuthorRepository, CategoryRepository, 
    ProcessingEventRepository, NewsletterRepository
)

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

ssm = boto3.client('ssm')

def get_config():
    """Get configuration from SSM Parameter Store"""
    config_path = os.getenv("CONFIG_PATH")
    try:
        params = ssm.get_parameters(
            Names=[
                f"{config_path}/arxiv/categories",
                f"{config_path}/arxiv/back_date",
                f"{config_path}/arxiv/set",
                f"{config_path}/arxiv/s3_bucket"
            ]
        )
        config = {}
        for param in params['Parameters']:
            name = param['Name'].split('/')[-1]
            if name == 'categories':
                config[name] = param['Value'].split(',')
            elif name == 'back_date':
                config[name] = int(param['Value'])
            else:
                config[name] = param['Value']
        return config
    except ClientError as e:
        logger.error(f"Error fetching config: {e}")
        raise

# Initialize the database connection
init_db()

config = get_config()
CATEGORIES = config['categories']
BACK_DATE = config['back_date']
ARXIV_SET = config['set']
S3_BUCKET = config['s3_bucket']

s3 = boto3.client('s3')

cs_categories_inverted = {
    "Computer Science - Artifical Intelligence": "AI",
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

def store_paper_metadata(record: dict, job_id: str = None):
    """
    Store paper metadata in the database using repository pattern.
    
    Args:
        record: The paper record containing metadata
        job_id: Optional job ID for tracking
    
    Returns:
        Article: The created or updated article
    """
    try:
        # Convert date string to date object
        publication_date = datetime.fromisoformat(record["date"]).date()
        
        # Create or get article
        with get_session() as session:
            # Check if article already exists
            article = ArticleRepository.get_article_by_source_id(
                session=session,
                source="arxiv",
                source_id=record["identifier"]
            )
            
            # If article doesn't exist, create it
            if not article:
                article = ArticleRepository.create_article(
                    session=session,
                    source_id=record["identifier"],
                    source="arxiv",
                    title=record["title"],
                    publication_date=publication_date,
                    abstract_text=record["abstract"],
                    url=record["abstract_url"],
                    s3_abstract_path=f"articles/arxiv/{publication_date.year}/{publication_date.month:02d}/{publication_date.day:02d}/{record['identifier']}/abstract.txt"
                )
                
                # Create processing event for new article
                ProcessingEventRepository.create_event(
                    session=session,
                    article_id=article.id,
                    event_type="ingested",
                    details={"source": "arxiv_processor"},
                    source_job_id=job_id
                )
                
                # Process categories
                primary_cat_code = record["primary_category"]
                
                # Get or create categories
                for cat_code in record["categories"]:
                    # Get the category if it exists, or create it
                    category = CategoryRepository.get_category_by_code(session, f"cs.{cat_code}")
                    if not category:
                        # Find the full name from the inverted map
                        cat_name = next((k for k, v in cs_categories_inverted.items() if v == cat_code), None)
                        if not cat_name:
                            cat_name = f"Computer Science - {cat_code}"
                        
                        # Create the category
                        category = CategoryRepository.create_category(
                            session=session,
                            name=cat_name,
                            code=f"cs.{cat_code}",
                            parent_id=None  # We'll need to get the parent ID from the database
                        )
                    
                    # Add category to article
                    is_primary = (cat_code == primary_cat_code)
                    ArticleRepository.add_category_to_article(
                        session=session,
                        article_id=article.id,
                        category_id=category.id,
                        is_primary=is_primary
                    )
                
                # Process authors
                for idx, author_data in enumerate(record["authors"]):
                    # Create author if doesn't exist
                    author = AuthorRepository.create_author(
                        session=session,
                        name=f"{author_data['first_name']} {author_data['last_name']}"
                    )
                    
                    # Add author to article with order
                    ArticleRepository.add_author_to_article(
                        session=session,
                        article_id=article.id,
                        author_id=author.id,
                        order=idx
                    )
            
            return article
            
    except Exception as e:
        logger.error(f"Error storing metadata: {e}")
        raise

def upload_to_s3(file_data: BytesIO, key: str):
    """Upload file to S3"""
    try:
        s3.upload_fileobj(file_data, S3_BUCKET, key)
        logger.info(f"Uploaded {key} to S3")
    except ClientError as e:
        logger.error(f"Error uploading to S3: {e}")
        raise

def fetch_data(base_url: str, from_date: str) -> list:
    """Fetches data from arXiv API with proper 503 handling"""
    full_xml_responses = []
    params = {"verb": "ListRecords", "set": "cs", "metadataPrefix": "oai_dc", "from": from_date}
    
    while True:
        try:
            logging.info(f"Fetching data with parameters: {params}")
            response = requests.get(base_url, params=params)
            
            if response.status_code == 503:
                retry_after = int(response.headers.get('Retry-After', 30))
                logging.info(f"Server busy (503). Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            
            response.raise_for_status()
            full_xml_responses.append(response.text)
            
            # Check for resumption token
            tree = ET.fromstring(response.text)
            namespaces = {"ns": "http://www.openarchives.org/OAI/2.0/"}
            token = tree.find(".//ns:resumptionToken", namespaces)
            
            if token is None or not token.text:
                break
                
            # Use resumption token for next request
            params = {"verb": "ListRecords", "resumptionToken": token.text}
            
            # Be nice to the API - sleep between requests
            time.sleep(3)
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data: {e}")
            break
            
    return full_xml_responses

def parse_xml_data(xml_content: str) -> dict:
    """Parses the OAI XML response and extracts relevant data"""
    try:
        root = ET.fromstring(xml_content)
        namespaces = {
            "oai": "http://www.openarchives.org/OAI/2.0/",
            "dc": "http://purl.org/dc/elements/1.1/",
            "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/"
        }
        
        records_data = []
        records = root.findall(".//oai:record", namespaces)
        
        for record in records:
            # Extract header data
            header = record.find("oai:header", namespaces)
            identifier = header.find("oai:identifier", namespaces).text
            
            # arxiv identifiers are in format oai:arXiv.org:2301.12345
            arxiv_id = identifier.split(':')[-1]
            
            datestamp = header.find("oai:datestamp", namespaces).text[:10]  # YYYY-MM-DD
            
            # Extract subject categories
            primary_category = None
            categories = []
            
            setSpec_elements = header.findall("oai:setSpec", namespaces)
            for setSpec in setSpec_elements:
                if setSpec.text.startswith("cs."):
                    category = setSpec.text.replace("cs.", "")
                    categories.append(category)
                    
                    # Assume the first one is primary (or override if marked as cs)
                    if primary_category is None or setSpec.text == "cs":
                        primary_category = category
            
            # Skip if no CS categories
            if not categories:
                continue
                
            # Extract metadata
            metadata = record.find("oai:metadata/oai_dc:dc", namespaces)
            if metadata is None:
                continue
                
            title = metadata.find("dc:title", namespaces)
            title = title.text if title is not None else "No Title"
            title = unescape(title).replace('\n', ' ').strip()
            
            # Extract authors
            creators = metadata.findall("dc:creator", namespaces)
            authors = []
            
            for creator in creators:
                author_text = creator.text if creator is not None else ""
                if author_text:
                    # Common format: "Last Name, First Name"
                    parts = author_text.split(',', 1)
                    if len(parts) > 1:
                        last_name = parts[0].strip()
                        first_name = parts[1].strip()
                    else:
                        # Handle cases without commas: "First Name Last Name"
                        name_parts = author_text.split()
                        if len(name_parts) > 1:
                            first_name = " ".join(name_parts[:-1])
                            last_name = name_parts[-1]
                        else:
                            first_name = author_text
                            last_name = ""
                            
                    authors.append({
                        "first_name": first_name,
                        "last_name": last_name
                    })
            
            # Extract abstract
            description = metadata.find("dc:description", namespaces)
            abstract = description.text if description is not None else ""
            abstract = abstract.strip()
            
            # ArXiv URL
            abstract_url = f"https://arxiv.org/abs/{arxiv_id}"
            
            record_data = {
                "identifier": arxiv_id,
                "date": datestamp,
                "title": title,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "abstract": abstract,
                "abstract_url": abstract_url
            }
            
            records_data.append(record_data)
        
        return {
            "records": records_data
        }
    except Exception as e:
        logging.error(f"Error parsing XML data: {e}")
        raise

def latex_to_human_readable(text: str) -> str:
    """Convert LaTeX-styled text to human readable format"""
    # Replace common LaTeX commands
    text = re.sub(r'\\emph{([^}]*)}', r'*\1*', text)
    text = re.sub(r'\\textbf{([^}]*)}', r'**\1**', text)
    text = re.sub(r'\\textit{([^}]*)}', r'*\1*', text)
    
    # Replace math environments
    text = re.sub(r'\$([^$]*)\$', r'\1', text)
    text = re.sub(r'\\\[(.*?)\\\]', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'\1', text, flags=re.DOTALL)
    
    # Replace LaTeX characters
    latex_replacements = {
        '\\&': '&',
        '\\%': '%',
        '\\_': '_',
        '\\$': '$',
        '\\#': '#',
        '{': '',
        '}': ''
    }
    
    for latex, char in latex_replacements.items():
        text = text.replace(latex, char)
    
    return text

def add_hyperlink(paragraph, text, url):
    """Add a hyperlink to a paragraph"""
    part = paragraph.part
    r_id = part.relate_to(url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    
    # Create the hyperlink XML element
    hyperlink = docx.oxml.shared.OxmlElement('w:hyperlink')
    hyperlink.set(docx.oxml.shared.qn('r:id'), r_id)
    
    # Create a new run
    new_run = docx.oxml.shared.OxmlElement('w:r')
    
    # Create a run properties element
    rPr = docx.oxml.shared.OxmlElement('w:rPr')
    
    # Create style element
    rStyle = docx.oxml.shared.OxmlElement('w:rStyle')
    rStyle.set(docx.oxml.shared.qn('w:val'), 'Hyperlink')
    
    rPr.append(rStyle)
    
    new_run.append(rPr)
    new_run.text = text
    hyperlink.append(new_run)
    
    paragraph._p.append(hyperlink)
    
    return hyperlink

def create_research_summary(records: list, date: str, job_id: str = None) -> dict:
    """Creates research summary documents and returns file info"""
    summary_files = {}
    
    # Parse date string to date object
    date_obj = datetime.fromisoformat(date).date()
    
    for category in CATEGORIES:
        doc = Document()
        doc.add_heading(f"arXiv {category} Research Summaries - {date}", 0)
        
        category_papers = []
        for record in records:
            if record["primary_category"] == category and record["date"] == date:
                # Store paper info for metadata
                category_papers.append(record)
                
                # Add title with link
                title_para = doc.add_paragraph()
                add_hyperlink(title_para, record["title"], record["abstract_url"])
                
                # Add PDF link
                pdf_link = record["abstract_url"].replace("abs", "pdf")
                title_para.add_run(" [")
                add_hyperlink(title_para, "PDF", pdf_link)
                title_para.add_run("]")
                
                # Add authors
                authors = [f"{author['first_name']} {author['last_name']}" for author in record["authors"]]
                doc.add_paragraph(f"Authors: {', '.join(authors)}")
                
                # Add abstract
                abstract = latex_to_human_readable(record["abstract"])
                doc.add_paragraph(abstract)
                
                # Add spacing
                doc.add_paragraph()

        if category_papers:
            # Save to memory
            docx_buffer = BytesIO()
            doc.save(docx_buffer)
            docx_buffer.seek(0)
            
            # Upload to S3
            s3_key = f"newsletters/{date}/{category}_research_summary.docx"
            upload_to_s3(docx_buffer, s3_key)  # Let the ClientError propagate up
            summary_files[category] = {
                "s3_key": s3_key,
                "papers": category_papers
            }
            logging.info(f"Created and uploaded summary for {category}")
            
            # Create newsletter record
            with get_session() as session:
                # Create newsletter entry
                newsletter = NewsletterRepository.create_newsletter(
                    session=session,
                    title=f"arXiv {category} Research Summary",
                    issue_date=date_obj,
                    s3_path=s3_key
                )
                
                # Add articles to newsletter
                for paper in category_papers:
                    # Get article
                    article = ArticleRepository.get_article_by_source_id(
                        session=session,
                        source="arxiv",
                        source_id=paper["identifier"]
                    )
                    
                    if article:
                        # Add to newsletter
                        NewsletterRepository.add_article_to_newsletter(
                            session=session,
                            newsletter_id=newsletter.id,
                            article_id=article.id
                        )
                        
                        # Create processing event for inclusion in newsletter
                        ProcessingEventRepository.create_event(
                            session=session,
                            article_id=article.id,
                            event_type="included_in_newsletter",
                            details={
                                "newsletter_id": newsletter.id,
                                "newsletter_title": newsletter.title,
                                "newsletter_date": newsletter.issue_date.isoformat()
                            },
                            source_job_id=job_id
                        )

    return summary_files

def main():
    """Main function to process papers"""
    today = datetime.today()
    job_id = f"arxiv-processor-{today.strftime('%Y%m%d%H%M%S')}"
    logging.info(f"Starting job: {job_id}")
    
    for i in range(BACK_DATE):
        date = (today - timedelta(days=i+1)).strftime("%Y-%m-%d")
        logging.info(f"Processing papers for {date}")
        
        xml_responses = fetch_data("http://export.arxiv.org/oai2", date)
        
        if not xml_responses:
            logging.warning(f"No records found for {date}")
            continue
            
        all_records = []
        for xml in xml_responses:
            data = parse_xml_data(xml)
            all_records.extend(data["records"])
            
        if all_records:
            # Store metadata for each paper
            for record in all_records:
                # Store in database with job ID for lineage tracking
                store_paper_metadata(record, job_id)
            
            # Create and upload summary documents
            summary_files = create_research_summary(all_records, date, job_id)
            
            if summary_files:
                logging.info(f"Successfully processed {len(all_records)} papers for {date}")
                return
            else:
                logging.warning(f"No papers in selected categories for {date}")
        else:
            logging.warning(f"No records found for {date}")
    
    # If we get here, no papers were processed
    return {"error": "No papers were processed"}

if __name__ == "__main__":
    main()
