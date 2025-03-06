#!/usr/bin/env python3
"""
Constants package for arXiv data layer.

This package provides shared constant values and enumerations used
throughout the arXiv data layer services.
"""

from shared.constants.enums import (
    IngestionStatus,
    PaperFormat,
    ApiSortOrder,
    CategoryGroup,
    CSCategory,
    CS_CATEGORY_NAMES
)

from shared.constants.paths import (
    # S3 prefixes
    S3_ABSTRACT_PREFIX,
    S3_PAPER_PREFIX,
    S3_METADATA_PREFIX,
    S3_INGESTION_LOGS_PREFIX,
    
    # S3 path templates
    S3_ABSTRACT_PATH_TEMPLATE,
    S3_PAPER_PATH_TEMPLATE,
    S3_METADATA_PATH_TEMPLATE,
    S3_INGESTION_LOG_PATH_TEMPLATE,
    
    # API paths
    API_PAPERS_PATH,
    API_AUTHORS_PATH,
    API_CATEGORIES_PATH,
    API_SETS_PATH,
    API_INGESTION_PATH,
    
    # API params
    API_PAPER_ID_PARAM,
    API_AUTHOR_ID_PARAM,
    API_CATEGORY_ID_PARAM,
    API_SET_ID_PARAM,
    API_INGESTION_ID_PARAM
)

__all__ = [
    # Enums
    'IngestionStatus',
    'PaperFormat',
    'ApiSortOrder',
    'CategoryGroup',
    'CSCategory',
    'CS_CATEGORY_NAMES',
    
    # S3 Paths
    'S3_ABSTRACT_PREFIX',
    'S3_PAPER_PREFIX',
    'S3_METADATA_PREFIX',
    'S3_INGESTION_LOGS_PREFIX',
    'S3_ABSTRACT_PATH_TEMPLATE',
    'S3_PAPER_PATH_TEMPLATE',
    'S3_METADATA_PATH_TEMPLATE',
    'S3_INGESTION_LOG_PATH_TEMPLATE',
    
    # API Paths
    'API_PAPERS_PATH',
    'API_AUTHORS_PATH',
    'API_CATEGORIES_PATH',
    'API_SETS_PATH',
    'API_INGESTION_PATH',
    'API_PAPER_ID_PARAM',
    'API_AUTHOR_ID_PARAM',
    'API_CATEGORY_ID_PARAM',
    'API_SET_ID_PARAM',
    'API_INGESTION_ID_PARAM'
]
