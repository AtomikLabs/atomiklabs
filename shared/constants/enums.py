#!/usr/bin/env python3
"""
Enumeration constants for the arXiv data layer.

This module provides standardized enumeration types for use across services,
ensuring consistent status tracking and categorization.
"""

from enum import Enum, auto


class IngestionStatus(str, Enum):
    """Status values for ingestion jobs"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    TIMEOUT = "timeout"


class PaperFormat(str, Enum):
    """Format types for papers"""
    PDF = "pdf"
    TEX = "tex"
    OTHER = "other"


class ApiSortOrder(str, Enum):
    """Sort order for API responses"""
    DATE_DESC = "date_desc"
    DATE_ASC = "date_asc"
    RELEVANCE = "relevance"
    TITLE_ASC = "title_asc"
    TITLE_DESC = "title_desc"


class CategoryGroup(str, Enum):
    """Major arXiv category groups"""
    CS = "cs"  # Computer Science
    MATH = "math"  # Mathematics
    PHYSICS = "physics"  # Physics
    ECON = "econ"  # Economics
    Q_BIO = "q-bio"  # Quantitative Biology
    STAT = "stat"  # Statistics
    EESS = "eess"  # Electrical Engineering and Systems Science
    Q_FIN = "q-fin"  # Quantitative Finance


# Computer Science subcategories with their codes
# Based on the notebook conversion codes
class CSCategory(str, Enum):
    """Computer Science category codes"""
    AI = "AI"  # Artificial Intelligence
    AR = "AR"  # Hardware Architecture
    CC = "CC"  # Computational Complexity
    CE = "CE"  # Computational Engineering, Finance, and Science
    CG = "CG"  # Computational Geometry
    CL = "CL"  # Computation and Language
    CR = "CR"  # Cryptography and Security
    CV = "CV"  # Computer Vision and Pattern Recognition
    CY = "CY"  # Computers and Society
    DB = "DB"  # Databases
    DC = "DC"  # Distributed, Parallel, and Cluster Computing
    DL = "DL"  # Digital Libraries
    DM = "DM"  # Discrete Mathematics
    DS = "DS"  # Data Structures and Algorithms
    ET = "ET"  # Emerging Technologies
    FL = "FL"  # Formal Languages and Automata Theory
    GL = "GL"  # General Literature
    GR = "GR"  # Graphics
    GT = "GT"  # Computer Science and Game Theory
    HC = "HC"  # Human-Computer Interaction
    IR = "IR"  # Information Retrieval
    IT = "IT"  # Information Theory
    LG = "LG"  # Machine Learning
    LO = "LO"  # Logic in Computer Science
    MA = "MA"  # Multiagent Systems
    MM = "MM"  # Multimedia
    MS = "MS"  # Mathematical Software
    NA = "NA"  # Numerical Analysis
    NE = "NE"  # Neural and Evolutionary Computing
    NI = "NI"  # Networking and Internet Architecture
    OH = "OH"  # Other Computer Science
    OS = "OS"  # Operating Systems
    PF = "PF"  # Performance
    PL = "PL"  # Programming Languages
    RO = "RO"  # Robotics
    SC = "SC"  # Symbolic Computation
    SD = "SD"  # Sound
    SE = "SE"  # Software Engineering
    SI = "SI"  # Social and Information Networks
    SY = "SY"  # Systems and Control


# Category names to codes mapping (based on the notebook sample)
CS_CATEGORY_NAMES = {
    "Computer Science - Artifical Intelligence": CSCategory.AI,
    "Computer Science - Hardware Architecture": CSCategory.AR,
    "Computer Science - Computational Complexity": CSCategory.CC,
    "Computer Science - Computational Engineering, Finance, and Science": CSCategory.CE,
    "Computer Science - Computational Geometry": CSCategory.CG,
    "Computer Science - Computation and Language": CSCategory.CL,
    "Computer Science - Cryptography and Security": CSCategory.CR,
    "Computer Science - Computer Vision and Pattern Recognition": CSCategory.CV,
    "Computer Science - Computers and Society": CSCategory.CY,
    "Computer Science - Databases": CSCategory.DB,
    "Computer Science - Distributed, Parallel, and Cluster Computing": CSCategory.DC,
    "Computer Science - Digital Libraries": CSCategory.DL,
    "Computer Science - Discrete Mathematics": CSCategory.DM,
    "Computer Science - Data Structures and Algorithms": CSCategory.DS,
    "Computer Science - Emerging Technologies": CSCategory.ET,
    "Computer Science - Formal Languages and Automata Theory": CSCategory.FL,
    "Computer Science - General Literature": CSCategory.GL,
    "Computer Science - Graphics": CSCategory.GR,
    "Computer Science - Computer Science and Game Theory": CSCategory.GT,
    "Computer Science - Human-Computer Interaction": CSCategory.HC,
    "Computer Science - Information Retrieval": CSCategory.IR,
    "Computer Science - Information Theory": CSCategory.IT,
    "Computer Science - Machine Learning": CSCategory.LG,
    "Computer Science - Logic in Computer Science": CSCategory.LO,
    "Computer Science - Multiagent Systems": CSCategory.MA,
    "Computer Science - Multimedia": CSCategory.MM,
    "Computer Science - Mathematical Software": CSCategory.MS,
    "Computer Science - Numerical Analysis": CSCategory.NA,
    "Computer Science - Neural and Evolutionary Computing": CSCategory.NE,
    "Computer Science - Networking and Internet Architecture": CSCategory.NI,
    "Computer Science - Other Computer Science": CSCategory.OH,
    "Computer Science - Operating Systems": CSCategory.OS,
    "Computer Science - Performance": CSCategory.PF,
    "Computer Science - Programming Languages": CSCategory.PL,
    "Computer Science - Robotics": CSCategory.RO,
    "Computer Science - Symbolic Computation": CSCategory.SC,
    "Computer Science - Sound": CSCategory.SD,
    "Computer Science - Software Engineering": CSCategory.SE,
    "Computer Science - Social and Information Networks": CSCategory.SI,
    "Computer Science - Systems and Control": CSCategory.SY,
}
