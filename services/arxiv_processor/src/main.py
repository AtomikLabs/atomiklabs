#!/usr/bin/env python3
"""
ArXiv Processor ECS Task

This ECS task fetches papers from ArXiv, processes them into our data models,
and stores them in the database and S3 via the API Gateway.
"""

import logging
import os
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from .config import load_config
from .arxiv_fetcher import fetch_papers_for_date_range
from .paper_processor import process_papers
from .api_client import ApiClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def chunk_list(input_list: list, chunk_size: int) -> List[list]:
    """Split a list into chunks of a specified size."""
    return [input_list[i:i + chunk_size] for i in range(0, len(input_list), chunk_size)]


def process_batch(
    batch_data: Dict[str, list],
    api_client: ApiClient
) -> Dict[str, int]:
    """
    Process a batch of papers and store via API.
    
    Args:
        batch_data: Processed paper data
        api_client: API client instance
        
    Returns:
        Dictionary with counts of created, updated, and failed items
    """
    results = {
        "papers_created": 0,
        "papers_updated": 0,
        "papers_failed": 0,
        "abstracts_stored": 0,
        "abstracts_failed": 0
    }
    
    # Process each paper
    for paper in batch_data["papers"]:
        try:
            paper_dict = paper.model_dump()
            arxiv_id = paper_dict["arxiv_identifier"]
            
            # Check if paper exists
            exists = api_client.check_paper_exists(arxiv_id)
            
            if exists:
                # Get the paper ID
                paper_id = api_client.get_paper_id(arxiv_id)
                if paper_id:
                    # Update paper
                    api_client.update_paper(paper_id, paper_dict)
                    results["papers_updated"] += 1
                    logger.info(f"Updated paper: {arxiv_id}")
                else:
                    # This shouldn't happen, but just in case
                    logger.error(f"Paper exists but ID not found: {arxiv_id}")
                    results["papers_failed"] += 1
            else:
                # Create new paper
                response = api_client.create_paper(paper_dict)
                if response and 'paper_id' in response:
                    results["papers_created"] += 1
                    logger.info(f"Created paper: {arxiv_id}")
                else:
                    logger.error(f"Failed to create paper: {arxiv_id}")
                    results["papers_failed"] += 1
                    continue  # Skip abstract upload if paper creation failed
            
            # Find the abstract for this paper
            paper_id_str = str(paper.paper_id)
            abstract = next((a["abstract"] for a in batch_data["abstracts"] if a["paper_id"] == paper_id_str), None)
            
            if abstract:
                # Upload abstract to S3
                try:
                    api_client.upload_abstract(paper_id_str, abstract)
                    results["abstracts_stored"] += 1
                    
                    # Update the paper with the S3 key
                    paper_dict["full_abstract_s3_key"] = f"abstracts/{paper_id_str}"
                    if exists:
                        paper_id = api_client.get_paper_id(arxiv_id)
                        api_client.update_paper(paper_id, paper_dict)
                    
                except Exception as e:
                    logger.error(f"Error uploading abstract: {e}")
                    results["abstracts_failed"] += 1
        
        except Exception as e:
            logger.error(f"Error processing paper: {e}")
            results["papers_failed"] += 1
    
    return results


def main():
    """Main entry point for the ECS task."""
    logger.info("ArXiv processor starting...")
    
    try:
        # Load configuration
        config = load_config()
        logger.info(f"Using configuration: {config}")
        
        # Initialize API client
        api_client = ApiClient(base_url=config.api_endpoint)
        
        # Fetch papers from ArXiv
        logger.info(f"Fetching papers for sets: {config.arxiv_sets}, categories: {config.arxiv_categories}")
        papers = fetch_papers_for_date_range(
            sets=config.arxiv_sets,
            categories=config.arxiv_categories,
            days_lookback=config.days_lookback
        )
        
        if not papers:
            logger.warning("No papers found. Exiting.")
            return
        
        logger.info(f"Fetched {len(papers)} papers")
        
        # Process papers
        processed_data = process_papers(papers)
        
        # Process papers in batches
        total_results = {
            "papers_created": 0,
            "papers_updated": 0,
            "papers_failed": 0,
            "abstracts_stored": 0,
            "abstracts_failed": 0
        }
        
        # Group papers and abstracts together
        paper_batches = chunk_list(processed_data["papers"], config.batch_size)
        abstract_batches = chunk_list(processed_data["abstracts"], config.batch_size)
        
        for i, paper_batch in enumerate(paper_batches):
            abstract_batch = abstract_batches[i] if i < len(abstract_batches) else []
            
            batch_data = {
                "papers": paper_batch,
                "abstracts": abstract_batch
            }
            
            logger.info(f"Processing batch {i+1}/{len(paper_batches)} ({len(paper_batch)} papers)")
            batch_results = process_batch(batch_data, api_client)
            
            # Update total results
            for key, value in batch_results.items():
                total_results[key] += value
            
            # Sleep between batches to avoid rate limiting
            if i < len(paper_batches) - 1:
                time.sleep(1)
        
        # Log results
        logger.info("ArXiv processor completed successfully")
        logger.info(f"Results: {json.dumps(total_results)}")
        
    except Exception as e:
        logger.error(f"Error in ArXiv processor: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main() 