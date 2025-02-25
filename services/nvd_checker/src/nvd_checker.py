import json
import os
from datetime import datetime, timedelta, UTC
import logging
import requests
import boto3
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from io import BytesIO
from shared.db import PostgresDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NVDChecker:
    def __init__(self):
        self.ssm = boto3.client('ssm')
        self.config = self._get_config()
        self.api_key = self.config['nvd_api_key']
        self.systems = self.config['monitored_systems']
        self.s3_bucket = self.config['s3_bucket']
        self.base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        self.headers = {
            "apiKey": self.api_key,
            "User-Agent": "AtomikLabs-VulnChecker/1.0"
        }
        self.s3 = boto3.client('s3')
        self.db = PostgresDB()

    def _get_config(self):
        """Get configuration from SSM Parameter Store"""
        config_path = os.getenv("CONFIG_PATH")
        try:
            params = self.ssm.get_parameters(
                Names=[
                    f"{config_path}/nvd/nvd_api_key",
                    f"{config_path}/nvd/monitored_systems",
                    f"{config_path}/nvd/s3_bucket"
                ],
                WithDecryption=True
            )
            config = {}
            for param in params['Parameters']:
                name = param['Name'].split('/')[-1]
                if name == 'monitored_systems':
                    config[name] = json.loads(param['Value'])
                else:
                    config[name] = param['Value']
            return config
        except Exception as e:
            logger.error(f"Error fetching config: {e}")
            raise

    def _init_database(self):
        """Initialize the vulnerabilities database tables if they don't exist"""
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            
            # Create vulnerabilities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vulnerabilities (
                    id SERIAL PRIMARY KEY,
                    cve_id TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL,
                    vendor TEXT NOT NULL,
                    product TEXT NOT NULL,
                    cvss_score FLOAT,
                    cvss_severity TEXT,
                    discovered_date DATE NOT NULL,
                    report_s3_key TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index on CVE ID for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vulnerabilities_cve_id 
                ON vulnerabilities(cve_id)
            """)
            
            # Create index on vendor and product for faster filtering
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vulnerabilities_vendor_product 
                ON vulnerabilities(vendor, product)
            """)
            
            logger.info("Vulnerability database tables initialized")

    def get_last_modified_date(self):
        """Get vulnerabilities from the last 24 hours"""
        return (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000")

    def search_vulnerabilities(self):
        """Search for vulnerabilities related to monitored systems"""
        findings = {}
        
        for vendor, info in self.systems.items():
            findings[vendor] = {
                "criticality": info["criticality"],
                "vulnerabilities": []
            }
            
            for product in info["products"]:
                params = {
                    "lastModStartDate": self.get_last_modified_date(),
                    "keywordSearch": f"cpe:2.3:*:{vendor}:{product}"
                }

                try:
                    response = requests.get(
                        self.base_url,
                        headers=self.headers,
                        params=params
                    )
                    response.raise_for_status()
                    
                    vulns = response.json().get("vulnerabilities", [])
                    for vuln in vulns:
                        cve = vuln["cve"]
                        findings[vendor]["vulnerabilities"].append({
                            "id": cve["id"],
                            "description": cve["descriptions"][0]["value"],
                            "metrics": cve.get("metrics", {}).get("cvssMetricV31", [{}])[0].get("cvssData", {}),
                            "product": product
                        })
                        
                except (requests.exceptions.RequestException, requests.exceptions.JSONDecodeError) as e:
                    logger.error(f"Error fetching vulnerabilities for {vendor} {product}: {e}")
                    continue

        return findings

    def store_vulnerabilities(self, findings, report_s3_key):
        """Store vulnerability findings in the PostgreSQL database"""
        # Initialize database tables if they don't exist
        self._init_database()
        
        today = datetime.now().date()
        stored_count = 0
        
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            
            for vendor, info in findings.items():
                for vuln in info["vulnerabilities"]:
                    # Extract CVSS metrics if available
                    cvss_score = None
                    cvss_severity = None
                    if "baseScore" in vuln.get("metrics", {}):
                        cvss_score = vuln["metrics"]["baseScore"]
                        cvss_severity = vuln["metrics"]["baseSeverity"]
                    
                    # Check if this vulnerability already exists
                    cursor.execute(
                        "SELECT id FROM vulnerabilities WHERE cve_id = %s",
                        (vuln["id"],)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        # Update existing vulnerability
                        cursor.execute("""
                            UPDATE vulnerabilities 
                            SET description = %s, 
                                cvss_score = %s, 
                                cvss_severity = %s,
                                report_s3_key = %s
                            WHERE cve_id = %s
                        """, (
                            vuln["description"],
                            cvss_score,
                            cvss_severity,
                            report_s3_key,
                            vuln["id"]
                        ))
                    else:
                        # Insert new vulnerability
                        cursor.execute("""
                            INSERT INTO vulnerabilities 
                            (cve_id, description, vendor, product, cvss_score, cvss_severity, discovered_date, report_s3_key)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            vuln["id"],
                            vuln["description"],
                            vendor,
                            vuln["product"],
                            cvss_score,
                            cvss_severity,
                            today,
                            report_s3_key
                        ))
                        stored_count += 1
                        
        logger.info(f"Stored {stored_count} new vulnerabilities in the database")
        return stored_count

    def generate_report(self, findings):
        """Generate a DOCX report from the findings and store in S3"""
        doc = Document()
        
        # Add title
        title = doc.add_heading("NVD Vulnerability Report", 0)
        title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        
        # Add date
        date_paragraph = doc.add_paragraph()
        current_time = datetime.now()
        date_run = date_paragraph.add_run(f"Report generated on {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        date_run.font.size = Pt(10)
        date_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        
        for vendor, info in findings.items():
            if not info["vulnerabilities"]:
                continue
                
            # Add vendor section
            doc.add_heading(f"{vendor} ({info['criticality'].upper()})", level=1)
            
            for vuln in info["vulnerabilities"]:
                # Add vulnerability details
                h = doc.add_heading(level=2)
                h.add_run(f"{vuln['id']} - {vuln['product']}")
                
                if "baseScore" in vuln.get("metrics", {}):
                    score = vuln["metrics"]["baseScore"]
                    severity = vuln["metrics"]["baseSeverity"]
                    p = doc.add_paragraph()
                    p.add_run(f"CVSS Score: {score} ({severity})")
                
                doc.add_paragraph(vuln["description"])
        
        # Save to memory buffer
        docx_buffer = BytesIO()
        doc.save(docx_buffer)
        docx_buffer.seek(0)
        
        # Upload to S3 in a consistent location
        date_str = current_time.strftime("%Y-%m-%d")
        s3_key = f"reports/daily/{date_str}/nvd_vulnerabilities.docx"
        
        try:
            self.s3.upload_fileobj(docx_buffer, self.s3_bucket, s3_key)
            logger.info(f"Report saved to s3://{self.s3_bucket}/{s3_key}")
            return s3_key
        except Exception as e:
            logger.error(f"Error uploading report to S3: {e}")
            raise

def main():
    try:
        checker = NVDChecker()
        findings = checker.search_vulnerabilities()
        s3_key = checker.generate_report(findings)
        
        # Store vulnerabilities in PostgreSQL
        stored_count = checker.store_vulnerabilities(findings, s3_key)
        
        return {
            "statusCode": 200, 
            "body": "Success", 
            "s3_key": s3_key,
            "stored_vulnerabilities": stored_count
        }
    except Exception as e:
        logger.error(f"Error in NVD checker: {e}")
        return {"statusCode": 500, "body": "Internal server error", "error": str(e)}

if __name__ == "__main__":
    main() 