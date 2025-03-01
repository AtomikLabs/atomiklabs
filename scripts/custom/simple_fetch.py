import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from html import unescape

import defusedxml.ElementTree as ET
import docx
import requests
from docx import Document
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

CATEGORIES = ["CL", "CV", "RO", "CR", "AI"]  # Categories to process
BACK_DATE = 3  # Number of days to look back

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


def fetch_data(base_url: str, from_date: str) -> list:
    """Fetches data from arXiv API with proper 503 handling"""
    full_xml_responses = []
    params = {"verb": "ListRecords", "set": "cs", "metadataPrefix": "oai_dc", "from": from_date}

    while True:
        try:
            logging.info(f"Fetching data with parameters: {params}")
            response = requests.get(base_url, params=params)

            # Check specifically for 503 before raise_for_status
            if response.status_code == 503:
                # Get retry time from header or use default
                retry_after = int(response.headers.get("Retry-After", 30))
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
        ns = {"oai": "http://www.openarchives.org/OAI/2.0/", "dc": "http://purl.org/dc/elements/1.1/"}

        for record in root.findall(".//oai:record", ns):
            # Extract basic metadata
            identifier = record.find(".//oai:identifier", ns).text
            abstract_url = record.find(".//dc:identifier", ns).text
            title = record.find(".//dc:title", ns).text.replace("\n", "")
            abstract = record.find(".//dc:description", ns).text.replace("\n", " ")
            date = record.find(".//dc:date", ns).text

            # Extract authors
            authors = []
            for creator in record.findall(".//dc:creator", ns):
                name_parts = creator.text.split(", ", 1)
                authors.append({"last_name": name_parts[0], "first_name": name_parts[1] if len(name_parts) > 1 else ""})

            # Extract categories
            subjects = record.findall(".//dc:subject", ns)
            categories = [cs_categories_inverted.get(subject.text, "") for subject in subjects]
            categories = list(filter(None, categories))
            primary_category = categories[0] if categories else ""

            extracted_data["records"].append(
                {
                    "identifier": identifier,
                    "abstract_url": abstract_url,
                    "authors": authors,
                    "primary_category": primary_category,
                    "categories": categories,
                    "abstract": abstract,
                    "title": title,
                    "date": date,
                }
            )

    except ET.ParseError as e:
        logging.error(f"Error parsing XML: {e}")

    return extracted_data


def latex_to_human_readable(latex_str: str) -> str:
    """Converts LaTeX to human readable text"""
    # Remove math mode delimiters
    latex_str = re.sub(r"\$(.*?)\$", r"\1", latex_str)

    # Replace common LaTeX symbols
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

    # Remove any remaining LaTeX commands
    latex_str = re.sub(r"\\[a-zA-Z]+", "", latex_str)

    # Clean up any remaining LaTeX artifacts
    latex_str = latex_str.replace("  ", " ")
    latex_str = latex_str.replace("{", "").replace("}", "")

    return unescape(latex_str)


def add_hyperlink(paragraph, text, url):
    """Add a hyperlink to a paragraph"""
    part = paragraph.part
    r_id = part.relate_to(url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)

    hyperlink = docx.oxml.shared.OxmlElement("w:hyperlink")
    hyperlink.set(docx.oxml.shared.qn("r:id"), r_id)

    new_run = docx.oxml.shared.OxmlElement("w:r")
    rPr = docx.oxml.shared.OxmlElement("w:rPr")

    # Add styling
    rStyle = docx.oxml.shared.OxmlElement("w:rStyle")
    rStyle.set(docx.oxml.shared.qn("w:val"), "Hyperlink")
    rPr.append(rStyle)

    new_run.append(rPr)
    new_run.text = text
    hyperlink.append(new_run)

    paragraph._p.append(hyperlink)

    return hyperlink


def create_research_summary(records: list, date: str, output_dir: str = "summaries"):
    """Creates research summary document"""
    os.makedirs(output_dir, exist_ok=True)

    for category in CATEGORIES:
        doc = Document()

        # Add title
        doc.add_heading(f"arXiv {category} Research Summaries - {date}", 0)

        # Add papers
        for record in records:
            if record["primary_category"] == category and record["date"] == date:
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

                # Add spacing between papers
                doc.add_paragraph()

        # Save document if it contains any papers
        filename = f"{date}_{category}_research_summary.docx"
        doc.save(os.path.join(output_dir, filename))
        logging.info(f"Created summary document: {filename}")


def main():
    base_url = "http://export.arxiv.org/oai2"
    today = datetime.today()

    # Process last BACK_DATE days
    for i in range(BACK_DATE):
        date = (today - timedelta(days=i + 1)).strftime("%Y-%m-%d")

        # Fetch and parse data
        xml_responses = fetch_data(base_url, date)

        if not xml_responses:
            logging.warning(f"No data retrieved for {date}. Skipping...")
            continue

        all_records = []
        for xml in xml_responses:
            data = parse_xml_data(xml)
            all_records.extend(data["records"])

        if all_records:
            # Create summary document
            create_research_summary(all_records, date)
        else:
            logging.warning(f"No records found for {date}")


if __name__ == "__main__":
    main()
