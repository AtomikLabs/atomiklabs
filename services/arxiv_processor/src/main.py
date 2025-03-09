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
from datetime import datetime, UTC, timedelta
import uuid
import requests

# Change relative imports to absolute imports
from config import load_config
from arxiv_fetcher import fetch_papers_for_date_range
from paper_processor import process_papers
from api_client import ApiClient, CircuitBreakerOpenError

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
            # Convert model to dict and ensure UUIDs are properly serialized
            paper_dict = paper.model_dump()
            
            # The API client now handles UUID serialization, so we don't need to do it here anymore
            arxiv_id = paper_dict["arxiv_identifier"]
            
            # Check if paper exists
            try:
                exists = api_client.check_paper_exists(arxiv_id)
            except CircuitBreakerOpenError as e:
                logger.error(f"API circuit breaker open: {e}")
                raise  # Re-raise to be handled by the main loop
            except Exception as e:
                logger.error(f"Error checking if paper exists: {e}")
                results["papers_failed"] += 1
                continue
                
            if exists:
                # Get the paper ID
                try:
                    paper_id = api_client.get_paper_id(arxiv_id)
                except CircuitBreakerOpenError as e:
                    logger.error(f"API circuit breaker open: {e}")
                    raise  # Re-raise to be handled by the main loop
                except Exception as e:
                    logger.error(f"Error getting paper ID: {e}")
                    results["papers_failed"] += 1
                    continue
                    
                if paper_id:
                    # Update paper
                    try:
                        api_client.update_paper(paper_id, paper_dict)
                        results["papers_updated"] += 1
                        logger.info(f"Updated paper: {arxiv_id}")
                    except CircuitBreakerOpenError as e:
                        logger.error(f"API circuit breaker open: {e}")
                        raise  # Re-raise to be handled by the main loop
                    except Exception as e:
                        logger.error(f"Error updating paper: {e}")
                        results["papers_failed"] += 1
                        continue
                else:
                    # This shouldn't happen, but just in case
                    logger.error(f"Paper exists but ID not found: {arxiv_id}")
                    results["papers_failed"] += 1
                    continue
            else:
                # Create new paper
                try:
                    response = api_client.create_paper(paper_dict)
                    if response and 'paper_id' in response:
                        results["papers_created"] += 1
                        logger.info(f"Created paper: {arxiv_id}")
                        # Use the paper_id from the response
                        paper_id = response['paper_id']
                    else:
                        logger.error(f"Failed to create paper: {arxiv_id} - Invalid response: {response}")
                        results["papers_failed"] += 1
                        continue  # Skip abstract upload if paper creation failed
                except CircuitBreakerOpenError as e:
                    logger.error(f"API circuit breaker open: {e}")
                    raise  # Re-raise to be handled by the main loop
                except Exception as e:
                    logger.error(f"Error creating paper: {e}")
                    results["papers_failed"] += 1
                    continue
            
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
                        
                except CircuitBreakerOpenError as e:
                    logger.error(f"API circuit breaker open: {e}")
                    raise  # Re-raise to be handled by the main loop
                except Exception as e:
                    logger.error(f"Error uploading abstract: {e}")
                    results["abstracts_failed"] += 1
        
        except CircuitBreakerOpenError as e:
            # Re-raise circuit breaker errors to be handled by the main loop
            raise
        except Exception as e:
            logger.error(f"Error processing paper: {e}")
            results["papers_failed"] += 1
    
    return results


def main():
    """Main entry point for the ArXiv processor."""
    logger.info("ArXiv processor starting...")
    
    try:
        # 1. Load configuration
        config = load_config()
        
        # Convert config to a dictionary for logging
        config_dict = {
            "arxiv_categories": config.arxiv_categories,
            "arxiv_sets": config.arxiv_sets,
            "days_lookback": config.days_lookback,
            "batch_size": config.batch_size,
            "api_endpoint": config.api_endpoint,
            "s3_abstract_prefix": config.s3_abstract_prefix
        }
        logger.info(f"Using configuration: {json.dumps(config_dict, indent=2)}")
        
        # 2. Fetch papers from ArXiv for specified date range
        logger.info(f"Fetching papers for sets: {config.arxiv_sets}, categories: {config.arxiv_categories}")
        papers = fetch_papers_for_date_range(
            date_from=datetime.now(UTC) - timedelta(days=config.days_lookback),
            arxiv_sets=config.arxiv_sets,
            categories=config.arxiv_categories
        )
        logger.info(f"Fetched {len(papers)} papers")
        
        # 3. Process papers (extract metadata and abstracts)
        batch_data = process_papers(papers)
        logger.info(f"Processed {len(batch_data['papers'])} papers")
        
        # 4. Create API client
        api_client = ApiClient(config.api_endpoint)
        
        # 5. Verify API connectivity before starting batch processing
        try:
            # Simple test request to see if the API is accessible
            response = api_client._make_request('GET', 'papers', params={"limit": 1})
            logger.info("API connectivity test successful")
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to API Gateway. Check network connectivity and VPC endpoints.")
            if 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
                logger.error("Running in Lambda - make sure the Lambda function has proper networking setup:")
                logger.error("1. Check VPC endpoints for API Gateway and Lambda")
                logger.error("2. Check security groups allowing outbound traffic")
                logger.error("3. Check Lambda execution role has permissions to execute-api:Invoke")
            return
        except requests.exceptions.HTTPError as e:
            if "403" in str(e):
                logger.error("API Gateway returned 403 Forbidden. Likely an IAM permissions issue:")
                logger.error("1. Check Lambda execution role has execute-api:Invoke permission")
                logger.error("2. Check VPC endpoint policy for API Gateway allows access")
                logger.error("3. Verify API Gateway resource policy allows access from your VPC")
                return
            logger.warning(f"API test request failed with HTTP error: {e}")
            # Continue anyway - might be a temporary issue
        except Exception as e:
            logger.warning(f"API test request failed: {e}")
            # Continue anyway - might be a temporary issue
        
        # 6. Process in batches
        batches = chunk_list(batch_data["papers"], config.batch_size)
        
        results = {
            "papers_created": 0,
            "papers_updated": 0,
            "papers_failed": 0,
            "abstracts_stored": 0,
            "abstracts_failed": 0,
        }
        
        for i, batch in enumerate(batches):
            logger.info(f"Processing batch {i+1}/{len(batches)} ({len(batch)} papers)")
            
            batch_data_subset = {
                "papers": batch,
                "abstracts": batch_data["abstracts"]
            }
            
            try:
                batch_results = process_batch(batch_data_subset, api_client)
                
                # Accumulate results
                for key in results:
                    results[key] += batch_results.get(key, 0)
                    
            except CircuitBreakerOpenError as e:
                logger.error(f"Circuit breaker open, API is not responding: {e}")
                logger.error("Stopping batch processing as API is unresponsive")
                break
            except requests.exceptions.ConnectionError:
                logger.error("Network connection error when calling API Gateway")
                logger.error("Stopping batch processing due to network issues")
                break
            except Exception as e:
                logger.error(f"Error processing batch: {e}")
                
                # Check for 403 Forbidden error specifically
                if "403" in str(e) and "Forbidden" in str(e):
                    logger.error("API Gateway returned 403 Forbidden. Likely an IAM permissions issue.")
                    logger.error("Check that the Lambda execution role has permission to invoke the API Gateway.")
                    break
            
            # Sleep between batches to avoid rate limiting
            if i < len(batches) - 1:
                time.sleep(1)
        
        # Log results
        logger.info("ArXiv processor completed successfully")
        logger.info(f"Results: {json.dumps(results)}")
        
    except Exception as e:
        logger.error(f"Error in ArXiv processor: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main() 