#!/usr/bin/env python3
"""
Module for fetching papers from ArXiv OAI-PMH API
Adapted from simple_fetch.py
"""

import logging
import time
import re
from datetime import datetime, timezone, UTC, timedelta
from html import unescape
from typing import List, Dict, Any, Optional

import requests
import defusedxml.ElementTree as ET

logger = logging.getLogger(__name__)

# ArXiv categories mapping (CS categories)
CS_CATEGORIES_INVERTED = {
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


def fetch_papers_for_date_range(
    sets: List[str], 
    categories: List[str], 
    days_lookback: int
) -> List[Dict[str, Any]]:
    """
    Fetch papers from ArXiv for a given date range.
    
    Args:
        sets: List of ArXiv sets to fetch (e.g., ['cs', 'math'])
        categories: List of categories to filter by (e.g., ['cs.AI', 'cs.CL'])
        days_lookback: Number of days to look back
        
    Returns:
        List of paper records
    """
    base_url = "http://export.arxiv.org/oai2"
    today = datetime.now(UTC)
    all_papers = []
    
    # Extract the raw category codes (e.g., 'AI', 'CL') from the full category specs (e.g., 'cs.AI', 'cs.CL')
    category_codes = []
    for category in categories:
        parts = category.split('.')
        if len(parts) > 1:
            category_codes.append(parts[1])
    
    # Process each day in the lookback range
    for i in range(days_lookback):
        from_date = (today - timedelta(days=i + 1)).strftime("%Y-%m-%d")
        
        # Process each ArXiv set
        for arxiv_set in sets:
            logger.info(f"Fetching papers for set '{arxiv_set}' from date '{from_date}'")
            xml_responses = fetch_data(base_url, from_date, arxiv_set)
            
            if not xml_responses:
                logger.warning(f"No data retrieved for {arxiv_set} on {from_date}. Skipping...")
                continue
                
            # Process the XML responses
            for xml in xml_responses:
                data = parse_xml_data(xml, category_codes)
                if data["records"]:
                    logger.info(f"Found {len(data['records'])} papers for {arxiv_set} on {from_date}")
                    all_papers.extend(data["records"])
                    
    logger.info(f"Total papers fetched: {len(all_papers)}")
    return all_papers


def fetch_data(base_url: str, from_date: str, arxiv_set: str) -> List[str]:
    """
    Fetches data from arXiv API with proper 503 handling.
    
    Args:
        base_url: Base URL for the ArXiv OAI-PMH API
        from_date: Date to fetch papers from (YYYY-MM-DD)
        arxiv_set: ArXiv set to fetch papers from
        
    Returns:
        List of XML responses
    """
    full_xml_responses = []
    params = {"verb": "ListRecords", "set": arxiv_set, "metadataPrefix": "oai_dc", "from": from_date}

    while True:
        try:
            logger.info(f"Fetching data with parameters: {params}")
            response = requests.get(base_url, params=params)

            # Check specifically for 503 before raise_for_status
            if response.status_code == 503:
                # Get retry time from header or use default
                retry_after = int(response.headers.get("Retry-After", 30))
                logger.info(f"Server busy (503). Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            full_xml_responses.append(response.text)

            root = ET.fromstring(response.content)
            resumption_token = root.find(".//{http://www.openarchives.org/OAI/2.0/}resumptionToken")

            if resumption_token is not None and resumption_token.text:
                logger.info(f"Found resumption token: {resumption_token.text}")
                time.sleep(5)  # Be nice to the server
                params = {"verb": "ListRecords", "resumptionToken": resumption_token.text}
            else:
                break

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occurred: {e}")
            break

        except ET.ParseError as e:
            logger.error(f"Parse error occurred: {e}")
            break

        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")
            break

    return full_xml_responses


def parse_xml_data(xml_data: str, filter_categories: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parses XML data from arXiv.
    
    Args:
        xml_data: XML data from ArXiv
        filter_categories: List of categories to filter by (e.g., ['AI', 'CL'])
        
    Returns:
        Dictionary containing a list of extracted paper records
    """
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

            # Parse the date into datetime
            pub_date = None
            try:
                pub_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                # Try to extract a valid date format
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date)
                if date_match:
                    try:
                        pub_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                    except ValueError:
                        logger.error(f"Could not parse date: {date}")
                        pub_date = datetime.now(UTC)
                else:
                    logger.error(f"Could not parse date: {date}")
                    pub_date = datetime.now(UTC)

            # Extract authors
            authors = []
            for creator in record.findall(".//dc:creator", ns):
                name_parts = creator.text.split(", ", 1)
                authors.append({
                    "last_name": name_parts[0], 
                    "first_name": name_parts[1] if len(name_parts) > 1 else ""
                })

            # Extract categories
            subjects = record.findall(".//dc:subject", ns)
            categories = [CS_CATEGORIES_INVERTED.get(subject.text, "") for subject in subjects]
            categories = list(filter(None, categories))
            primary_category = categories[0] if categories else ""
            
            # Filter by categories if specified
            if filter_categories and primary_category not in filter_categories:
                continue
                
            # Create the paper record
            paper_record = {
                "identifier": identifier,
                "abstract_url": abstract_url,
                "authors": authors,
                "primary_category": primary_category,
                "categories": categories,
                "abstract": abstract,
                "title": title,
                "date": date,
                "publication_date": pub_date.isoformat() if pub_date else datetime.now(UTC).isoformat()
            }
            
            # Extract the arXiv ID from the identifier
            arxiv_id_match = re.search(r'arxiv.org\/abs\/(.+)', abstract_url)
            if arxiv_id_match:
                paper_record["arxiv_id"] = arxiv_id_match.group(1)
            else:
                # Alternative method to extract arXiv ID
                arxiv_id_match = re.search(r'([\d\.]+v\d+|\d+\.\d+)', identifier)
                if arxiv_id_match:
                    paper_record["arxiv_id"] = arxiv_id_match.group(1)
                else:
                    paper_record["arxiv_id"] = identifier.split(':')[-1]
            
            extracted_data["records"].append(paper_record)

    except ET.ParseError as e:
        logger.error(f"Error parsing XML: {e}")

    return extracted_data


def latex_to_human_readable(latex_str: str) -> str:
    """
    Converts LaTeX to human readable text.
    
    Args:
        latex_str: LaTeX string to convert
        
    Returns:
        Human readable text
    """
    if not latex_str:
        return ""
        
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