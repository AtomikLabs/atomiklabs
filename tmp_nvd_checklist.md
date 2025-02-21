# Actual Issues That Matter

1. S3 Bucket
   - Have specific 'newsletters' bucket name when it stores multiple types of content
   - Have redundant 'reports' bucket
   - Need single bucket with generic name but keep unique identifier

2. Parameter Paths
   - NVD checker code expects wrong paths
   - Step Function CONFIG_PATH override is wrong
   - Should match arxiv processor pattern

3. Python Dependencies
   - Need requirements.txt with:
     - requests (for NVD API)
     - python-docx (for report generation)
     - boto3 (AWS SDK)

# Fix Plan

1. Fix S3 setup:
   - Change bucket name in main.tf from `newsletter_bucket_name` to `storage_bucket_name`
   - Update name to `${local.resource_prefix}-storage-${local.resource_suffix}`
   - Remove 'reports' bucket
   - Update all references to use new bucket name
   - Keep existing path structure inside bucket:
     - newsletters/{date}/...
     - reports/daily/{date}/...

2. Fix paths:
   - Update NVD checker code to use correct SSM paths
   - Remove Step Function override
   - Update SSM parameters to use new bucket name

3. Create requirements.txt
   - Copy versions from arxiv processor
   - Use same version pattern

Keep everything simple, just use better names with proper resource prefix/suffix pattern.

# Issues Found in Code

1. NVD Checker Code
   - Gets bucket name from SSM param `{config_path}/s3_bucket`
   - Uses that bucket to write to `reports/daily/{date}/nvd_vulnerabilities.docx`
   - Needs requirements.txt with:
     - requests (for NVD API)
     - python-docx (for report generation)
     - boto3 (AWS SDK)

2. Parameter Path Issues
   - Code expects `{config_path}/nvd_api_key` etc.
   - Step Function sets `CONFIG_PATH=/${var.project}/${var.environment}/nvd`
   - ECS task sets `CONFIG_PATH=/${var.project}/${var.environment}`

3. References to Non-Existent Resources
   - Code references `aws_s3_bucket.reports` but bucket isn't defined
   - Several IAM policies reference this non-existent bucket

# Fix Plan

1. Fix parameter paths:
   - Make NVD checker match arxiv pattern: `{config_path}/nvd/*`
   - Remove `/nvd` from Step Function CONFIG_PATH

2. Fix S3 references:
   - Remove references to non-existent reports bucket
   - Update NVD checker to use newsletters bucket
   - Update SSM parameter to point to newsletters bucket

3. Add requirements.txt with exact versions from arxiv processor

Let me know if you want me to check anything else in the code first.
