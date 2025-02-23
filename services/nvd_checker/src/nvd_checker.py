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
        return {"statusCode": 200, "body": "Success", "s3_key": s3_key}
    except Exception as e:
        logger.error(f"Error in NVD checker: {e}")
        return {"statusCode": 500, "body": "Internal server error", "error": str(e)}

if __name__ == "__main__":
    main() 