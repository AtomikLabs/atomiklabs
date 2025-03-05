#!/usr/bin/env python3
"""
Constants for paths and storage locations for the arXiv data layer.

This module contains standardized paths for S3 storage organization,
ensuring consistent access patterns across services.
"""

# S3 path structure for arXiv content
S3_ABSTRACT_PREFIX = "abstracts"
S3_PAPER_PREFIX = "papers"
S3_METADATA_PREFIX = "metadata"
S3_INGESTION_LOGS_PREFIX = "ingestion_logs"

# Path format templates - these define the structure within each prefix
# Format: {set_code}/{YYYY}/{MM}/{DD}/{arxiv_identifier}
S3_ABSTRACT_PATH_TEMPLATE = f"{S3_ABSTRACT_PREFIX}/{{set_code}}/{{year}}/{{month}}/{{day}}/{{arxiv_id}}.txt"
S3_PAPER_PATH_TEMPLATE = f"{S3_PAPER_PREFIX}/{{set_code}}/{{year}}/{{month}}/{{day}}/{{arxiv_id}}.pdf"
S3_METADATA_PATH_TEMPLATE = f"{S3_METADATA_PREFIX}/{{set_code}}/{{year}}/{{month}}/{{day}}/{{batch_id}}.json"
S3_INGESTION_LOG_PATH_TEMPLATE = f"{S3_INGESTION_LOGS_PREFIX}/{{year}}/{{month}}/{{day}}/{{ingestion_id}}.json"

# API endpoint paths
API_PAPERS_PATH = "papers"
API_AUTHORS_PATH = "authors"
API_CATEGORIES_PATH = "categories"
API_SETS_PATH = "sets"
API_INGESTION_PATH = "ingestion"

# Common API path parameters
API_PAPER_ID_PARAM = "{paper_id}"
API_AUTHOR_ID_PARAM = "{author_id}"
API_CATEGORY_ID_PARAM = "{category_id}"
API_SET_ID_PARAM = "{set_id}"
API_INGESTION_ID_PARAM = "{ingestion_id}"
