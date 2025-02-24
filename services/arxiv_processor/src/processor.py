import logging
import os
import re
import time
from datetime import datetime, timedelta, UTC
from html import unescape
from io import BytesIO

import boto3
import defusedxml.ElementTree as ET
import docx
import requests
from docx import Document
from botocore.exceptions import ClientError
from shared.db import SQLiteDB

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

def store_paper_metadata(record: dict):
    """Store paper metadata in SQLite DB"""
    try:
        db = SQLiteDB('/mnt/sqlite/arxiv.db')
        with db.transaction() as conn:
            # Insert paper with S3 keys
            abstract_key = f"papers/{record['date']}/{record['identifier']}/abstract.txt"
            pdf_key = f"papers/{record['date']}/{record['identifier']}/paper.pdf"
            db.execute(
                "INSERT INTO papers (arxiv_id, s3_abstract_key, s3_pdf_key) VALUES (?, ?, ?)",
                (record["identifier"], abstract_key, pdf_key)
            )
            paper_id = conn.lastrowid

            # Insert authors and relationships
            for author in record["authors"]:
                db.execute(
                    "INSERT INTO authors (surname, given_names) VALUES (?, ?)",
                    (author["last_name"], author["first_name"])
                )
                author_id = conn.lastrowid
                db.execute(
                    "INSERT INTO paper_authors (paper_id, author_id, author_order) VALUES (?, ?, ?)",
                    (paper_id, author_id, record["authors"].index(author) + 1)
                )

            # Insert categories and relationships
            for category in record["categories"]:
                db.execute(
                    "INSERT INTO arxiv_categories (category_code, category_name) VALUES (?, ?)",
                    (category, cs_categories_inverted.get(category, category))
                )
                category_id = conn.lastrowid
                db.execute(
                    "INSERT INTO paper_categories (paper_id, category_id) VALUES (?, ?)",
                    (paper_id, category_id)
                )

            # Insert set and relationship
            db.execute(
                "INSERT INTO arxiv_sets (set_name) VALUES (?)",
                ("cs",)
            )
            set_id = conn.lastrowid
            db.execute(
                "INSERT INTO paper_sets (paper_id, set_id) VALUES (?, ?)",
                (paper_id, set_id)
            )

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
            
            root = ET.fromstring(response.content)
            resumption_token = root.find(".//{http://www.openarchives.org/OAI/2.0/}resumptionToken")

            if resumption_token is not None and resumption_token.text:
                logging.info(f"Found resumption token: {resumption_token.text}")
                time.sleep(5)  # Be nice to the server
                params = {"verb": "ListRecords", "resumptionToken": resumption_token.text}
            else:
                break

        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error occurred: {e}")
            break
        except ET.ParseError as e:
            logging.error(f"Parse error occurred: {e}")
            break
        except Exception as e:
            logging.error(f"Unexpected error occurred: {e}")
            break

    return full_xml_responses

def parse_xml_data(xml_data: str) -> dict:
    """Parses XML data from arXiv"""
    extracted_data = {"records": []}

    try:
        root = ET.fromstring(xml_data)
        ns = {
            "oai": "http://www.openarchives.org/OAI/2.0/",
            "dc": "http://purl.org/dc/elements/1.1/"
        }

        for record in root.findall(".//oai:record", ns):
            try:
                # Get required fields, skip record if any are missing
                identifier_elem = record.find(".//oai:identifier", ns)
                abstract_url_elem = record.find(".//dc:identifier", ns)
                title_elem = record.find(".//dc:title", ns)
                abstract_elem = record.find(".//dc:description", ns)
                date_elem = record.find(".//dc:date", ns)
                
                if not all([e is not None and e.text is not None for e in [identifier_elem, abstract_url_elem, title_elem, abstract_elem, date_elem]]):
                    logger.warning("Skipping record due to missing required fields")
                    continue
                
                identifier = identifier_elem.text
                abstract_url = abstract_url_elem.text
                title = title_elem.text.replace("\n", "")
                abstract = abstract_elem.text.replace("\n", " ")
                date = date_elem.text

                authors = []
                for creator in record.findall(".//dc:creator", ns):
                    if creator.text:
                        name_parts = creator.text.split(", ", 1)
                        authors.append({
                            "last_name": name_parts[0],
                            "first_name": name_parts[1] if len(name_parts) > 1 else ""
                        })

                subjects = record.findall(".//dc:subject", ns)
                categories = [cs_categories_inverted.get(subject.text, "") for subject in subjects if subject.text]
                categories = list(filter(None, categories))
                primary_category = categories[0] if categories else ""

                extracted_data["records"].append({
                    "identifier": identifier,
                    "abstract_url": abstract_url,
                    "authors": authors,
                    "primary_category": primary_category,
                    "categories": categories,
                    "abstract": abstract,
                    "title": title,
                    "date": date
                })
            except (AttributeError, IndexError) as e:
                logger.warning(f"Error processing record: {e}")
                continue

    except ET.ParseError as e:
        logger.error(f"Error parsing XML: {e}")

    return extracted_data

def latex_to_human_readable(latex_str: str) -> str:
    """Converts LaTeX to human readable text"""
    latex_str = re.sub(r"\$(.*?)\$", r"\1", latex_str)
    
    replacements = {
        "\\alpha": "alpha",
        "\\beta": "beta",
        "\\gamma": "gamma",
        "\\delta": "delta",
        "\\epsilon": "epsilon",
        "\\zeta": "zeta",
        "\\eta": "eta",
        "\\theta": "theta",
        "\\iota": "iota",
        "\\kappa": "kappa",
        "\\lambda": "lambda",
        "\\mu": "mu",
        "\\nu": "nu",
        "\\xi": "xi",
        "\\pi": "pi",
        "\\rho": "rho",
        "\\sigma": "sigma",
        "\\tau": "tau",
        "\\upsilon": "upsilon",
        "\\phi": "phi",
        "\\chi": "chi",
        "\\psi": "psi",
        "\\omega": "omega",
        "\\leq": "<=",
        "\\geq": ">=",
        "\\neq": "!=",
        "\\approx": "≈",
        "\\times": "×",
        "\\rightarrow": "→",
        "\\leftarrow": "←",
        "\\infty": "∞",
        "\\pm": "±",
        "\\sum": "∑",
        "\\prod": "∏",
        "\\int": "∫",
    }
    
    for latex, text in replacements.items():
        latex_str = latex_str.replace(latex, text)

    latex_str = re.sub(r'\\[a-zA-Z]+', '', latex_str)
    latex_str = latex_str.replace('  ', ' ')
    latex_str = latex_str.replace('{', '').replace('}', '')
    
    return unescape(latex_str)

def add_hyperlink(paragraph, text, url):
    """Add a hyperlink to a paragraph"""
    part = paragraph.part
    r_id = part.relate_to(url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    
    hyperlink = docx.oxml.shared.OxmlElement('w:hyperlink')
    hyperlink.set(docx.oxml.shared.qn('r:id'), r_id)
    
    new_run = docx.oxml.shared.OxmlElement('w:r')
    rPr = docx.oxml.shared.OxmlElement('w:rPr')
    
    rStyle = docx.oxml.shared.OxmlElement('w:rStyle')
    rStyle.set(docx.oxml.shared.qn('w:val'), 'Hyperlink')
    rPr.append(rStyle)
    
    new_run.append(rPr)
    new_run.text = text
    hyperlink.append(new_run)
    
    paragraph._p.append(hyperlink)
    
    return hyperlink

def create_research_summary(records: list, date: str) -> dict:
    """Creates research summary documents and returns file info"""
    summary_files = {}
    
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

    return summary_files

def main():
    """Main function to process papers"""
    today = datetime.today()
    
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
                store_paper_metadata(record)
            
            # Create and upload summary documents
            summary_files = create_research_summary(all_records, date)
            
            if summary_files:
                # Record newsletters in database
                db = SQLiteDB('/mnt/sqlite/arxiv.db')
                with db.transaction() as conn:
                    for category, info in summary_files.items():
                        s3_key = f"newsletters/{date}/{category}_research_summary.docx"
                        # Insert newsletter
                        db.execute(
                            "INSERT INTO newsletters (date, category_code, s3_key) VALUES (?, ?, ?)",
                            (date, category, s3_key)
                        )
                        newsletter_id = conn.lastrowid

                        # Link papers to newsletter
                        for paper in info['papers']:
                            paper_id = db.execute(
                                "SELECT id FROM papers WHERE arxiv_id = ?",
                                (paper['identifier'],)
                            ).fetchone()[0]
                            db.execute(
                                "INSERT INTO newsletter_papers (newsletter_id, paper_id) VALUES (?, ?)",
                                (newsletter_id, paper_id)
                            )

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
