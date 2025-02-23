from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import List, Optional

class Author(BaseModel):
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)

class ArxivPaper(BaseModel):
    id: str = Field(..., regex=r"^oai:arXiv\.org:")
    date: datetime
    abstract: str = Field(..., min_length=10)
    abstract_url: HttpUrl
    authors: List[Author]
    categories: List[str]
    pdf_url: HttpUrl
    primary_category: str
    processed_date: datetime
    set: str
    title: str = Field(..., min_length=1)

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d")
        } 