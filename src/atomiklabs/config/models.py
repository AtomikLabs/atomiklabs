from pydantic import BaseModel, Field, AnyHttpUrl, validator
from typing import List, Optional, Dict, Union
from datetime import datetime, timedelta

class Neo4jSettings(BaseModel):
    uri: str = Field(..., description="Neo4j connection URI")
    username: str = Field(..., description="Neo4j username")
    password: str = Field(..., description="Neo4j password", exclude=True)  # Mark sensitive
    database: str = Field("neo4j", description="Neo4j database name")
    
class ArxivSettings(BaseModel):
    categories: List[str] = Field(
        default=["cs.AI", "cs.LG"], 
        description="Arxiv categories to fetch"
    )
    sets: List[str] = Field(
        default=[], 
        description="Arxiv sets to fetch"
    )
    date_from: Optional[datetime] = Field(
        default=None, 
        description="Start date for papers (default: 30 days ago)"
    )
    date_to: Optional[datetime] = Field(
        default=None, 
        description="End date for papers (default: today)"
    )
    max_results: int = Field(
        default=1000,
        description="Maximum results to retrieve per category"
    )
    
    @validator("date_from", pre=True, always=True)
    def set_date_from_default(cls, v):
        if v is None:
            return datetime.now() - timedelta(days=30)
        return v
    
    @validator("date_to", pre=True, always=True)
    def set_date_to_default(cls, v):
        if v is None:
            return datetime.now()
        return v

class StorageSettings(BaseModel):
    abstracts_dir: str = Field(
        default="data/abstracts",
        description="Directory to store paper abstracts"
    )
    metadata_dir: str = Field(
        default="data/metadata",
        description="Directory to store paper metadata"
    )

class LoggingSettings(BaseModel):
    level: str = Field(
        default="INFO",
        description="Logging level"
    )
    file: Optional[str] = Field(
        default="logs/app.log",
        description="Log file path"
    )

class AppConfig(BaseModel):
    """Main application configuration."""
    app_name: str = Field(default="arxiv-fetcher", description="Application name")
    environment: str = Field(default="development", description="Environment (development, production)")
    neo4j: Neo4jSettings
    arxiv: ArxivSettings = Field(default_factory=ArxivSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
