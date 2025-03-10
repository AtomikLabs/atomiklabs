# Infrastructure Improvement Checklist

This document outlines the step-by-step plan to address the infrastructure limitations identified in our review. The plan focuses on creating a custom VPC, properly configuring security groups, and ensuring all components work together correctly without creating duplicates.

## Phase 1: VPC Infrastructure Improvements

- [x] **Step 1: Check for existing VPC resources**
  - [x] Review all Terraform files for existing VPC definitions
  - [x] Check for any data sources referencing VPC components
  - [x] Identify any resources that depend on the current VPC setup

**Findings:**

- The infrastructure currently uses the default VPC (`data "aws_vpc" "default" { default = true }`) in network.tf
- All subnets are retrieved using `data.aws_subnets.default.ids` without filtering for private/public
- Multiple resources depend on the default VPC:
  - 5 VPC endpoints (S3, SSM, SES, Lambda, API Gateway) in network.tf
  - Security groups in rds.tf and network.tf
  - API Gateway policy in api_gateway.tf
  - Lambda functions in lambda.tf have VPC configurations using default subnets
  - Step Functions state machine in step_functions.tf references default subnets for ECS tasks
  - RDS instance in rds.tf uses default VPC and subnets
- No Internet Gateway or NAT Gateway is currently defined
- No VPC Flow Logs are configured (not found in cloudwatch.tf)
- data.tf contains only the AWS caller identity data source
- Route tables are referenced via `data.aws_route_tables.default.ids`
- All VPC endpoints use the same Lambda security group, which has overly permissive inbound rules
- The ECS task in step_functions.tf has `AssignPublicIp = "DISABLED"`, which means it can't access the internet without a NAT Gateway

- [x] **Step 2: Update network.tf with custom VPC**
  - [x] Replace default VPC data sources with custom VPC resources
  - [x] Define VPC with appropriate CIDR block (e.g., 10.0.0.0/16)
  - [x] Enable DNS support and hostnames
  - [x] Add appropriate tags

**Implementation:**

- Created a new custom VPC resource in network.tf with configurable CIDR block
- Added a vpc_cidr_block variable in variables.tf with default value of 10.0.0.0/16
- Enabled DNS support and DNS hostnames for the VPC
- Added comprehensive tags including Environment and ManagedBy tags
- Set instance tenancy to "default" for cost efficiency
- Added IPv6 configuration option (disabled by default but configurable)
- Implemented VPC Flow Logs with CloudWatch Log Group for security monitoring
- Created IAM role and policy for VPC Flow Logs with appropriate permissions
- Modified the existing data source to reference the new VPC instead of the default VPC
- Maintained backward compatibility by keeping the data source name the same
- Added comments to data sources noting that they will return empty lists until later steps are completed

- [x] **Step 3: Create public and private subnets**
  - [x] Create 2 public subnets in different availability zones
  - [x] Create 2 private subnets in different availability zones
  - [x] Add appropriate tags including a "Type" tag for filtering

**Implementation:**

- Created public and private subnets with a configurable count (default: 2 of each type)
- Added subnet_count and private_subnet_offset variables for flexibility
- Used AWS availability_zones data source to dynamically discover available AZs
- Used modulo operation to distribute subnets across AZs even if more subnets than AZs
- Used cidrsubnet function to automatically calculate appropriate CIDR blocks:
  - Public subnets: First n /24 blocks of the VPC CIDR
  - Private subnets: Next n /24 blocks with configurable offset to avoid overlap
- Configured public subnets with map_public_ip_on_launch = true for internet access
- Configured private subnets with map_public_ip_on_launch = false for security
- Added comprehensive tags to all subnets including:
  - Name tag with subnet number
  - Type tag ("Public" or "Private") for filtering
  - Environment and ManagedBy tags for consistency
  - AWS Load Balancer Controller tags for potential future use
- Added detailed comments explaining the purpose and configuration of each subnet type
- Created dedicated data sources for public and private subnets with appropriate filters
- Updated the default subnets data source to include both public and private subnets
- Added explicit dependencies to ensure data sources are only evaluated after subnets are created

- [x] **Step 4: Create Internet Gateway and NAT Gateway**
  - [x] Create Internet Gateway for the VPC
  - [x] Create Elastic IP for NAT Gateway
  - [x] Create NAT Gateway in one of the public subnets
  - [x] Ensure proper dependencies between resources

**Implementation:**

- Created an Internet Gateway and attached it to the custom VPC
- Added appropriate tags to the Internet Gateway for identification and management
- Created an Elastic IP for the NAT Gateway with a conditional count based on subnet_count
- Added a dependency to ensure the Internet Gateway exists before creating the Elastic IP
- Created a NAT Gateway in the first public subnet with a conditional count based on subnet_count
- Allocated the Elastic IP to the NAT Gateway for a static public IP address
- Added comprehensive tags to both resources including Environment and ManagedBy tags
- Implemented proper dependencies to ensure resources are created in the correct order:
  - Internet Gateway must exist before Elastic IP
  - Internet Gateway must exist before NAT Gateway (as NAT Gateway needs internet access)
  - Public subnet must exist before NAT Gateway (as NAT Gateway is placed in a public subnet)
- Added detailed comments explaining the purpose of each resource
- Used a single NAT Gateway for cost efficiency while still providing internet access to private subnets

- [x] **Step 5: Create and associate route tables**
  - [x] Create public route table with route to Internet Gateway
  - [x] Create private route table with route to NAT Gateway
  - [x] Associate public subnets with public route table
  - [x] Associate private subnets with private route table

**Implementation:**

- Created a public route table for subnets that need direct internet access
- Added a route in the public route table to direct all internet-bound traffic (0.0.0.0/0) through the Internet Gateway
- Created a private route table for subnets that need indirect internet access via NAT
- Used a dynamic block to conditionally add a route in the private route table to direct internet-bound traffic through the NAT Gateway
- Added comprehensive tags to both route tables including a "Type" tag for identification
- Created route table associations to link each public subnet to the public route table
- Created route table associations to link each private subnet to the private route table
- Used count parameter to create the appropriate number of associations based on subnet_count
- Created a new data source for all route tables in the VPC
- Updated the default route tables data source to depend on the new route tables and associations
- This ensures the S3 Gateway endpoint uses the correct route tables
- Added detailed comments explaining the purpose of each resource

- [x] **Step 6: Check for existing VPC Flow Logs**
  - [x] Review cloudwatch.tf and other files for existing flow log configurations
  - [x] If not found, add VPC Flow Logs for network monitoring
  - [x] Create CloudWatch Log Group for VPC Flow Logs if needed
  - [x] Create IAM Role for VPC Flow Logs if needed

**Implementation:**

- Verified that VPC Flow Logs were already implemented in Step 2 of Phase 1
- Confirmed the following components are properly configured:
  - aws_flow_log resource directing all VPC traffic logs to CloudWatch
  - CloudWatch Log Group with 30-day retention for storing the logs
  - IAM role with appropriate trust policy for vpc-flow-logs.amazonaws.com
  - IAM policy granting necessary CloudWatch Logs permissions
- No additional changes were needed as the implementation is complete and follows best practices
- The existing implementation captures all traffic (ingress and egress) for comprehensive monitoring
- The logs will help with troubleshooting network connectivity issues and security monitoring

## Phase 2: Security Group Improvements

- [x] **Step 1: Check for existing security groups**
  - [x] Review all Terraform files for security group definitions
  - [x] Identify all resources that reference existing security groups
  - [x] Document the required access patterns between resources

**Findings:**

- Identified three security groups in the infrastructure:
  1. **ECS Tasks Security Group** (`aws_security_group.ecs_tasks` in network.tf):
     - Only allows outbound traffic to anywhere (0.0.0.0/0)
     - No inbound rules defined
     - Used by:
       - ECS tasks in ecs.tf
       - Step Functions state machine in step_functions.tf
       - PostgreSQL security group ingress rule in rds.tf

  2. **Lambda Security Group** (`aws_security_group.lambda_sg` in rds.tf):
     - Allows all traffic within the security group itself (self-referencing)
     - Allows HTTPS inbound (port 443) from anywhere (0.0.0.0/0) - overly permissive
     - Allows all outbound traffic to anywhere (0.0.0.0/0)
     - Used by:
       - Lambda functions in lambda.tf
       - PostgreSQL security group ingress rule in rds.tf
       - All VPC endpoints (S3, SSM, SES, Lambda, API Gateway) in network.tf

  3. **PostgreSQL Security Group** (`aws_security_group.postgresql` in rds.tf):
     - Allows PostgreSQL inbound (port 5432) from ECS tasks security group
     - Allows PostgreSQL inbound (port 5432) from Lambda security group
     - Allows all outbound traffic to anywhere (0.0.0.0/0)
     - Used by:
       - RDS PostgreSQL instance in rds.tf

- **Security Issues Identified**:
  - Lambda security group has overly permissive inbound rule allowing HTTPS from anywhere
  - All VPC endpoints use the same Lambda security group instead of a dedicated security group
  - No specific ingress rules for ECS tasks security group, which may be needed for task communication
  - No security group for API Gateway VPC endpoint with specific rules

- **Required Access Patterns**:
  1. ECS tasks → Internet (via NAT Gateway) → arXiv
  2. ECS tasks → API Gateway VPC endpoint
  3. ECS tasks → PostgreSQL RDS
  4. Lambda functions → PostgreSQL RDS
  5. Lambda functions → VPC endpoints (S3, SSM, SES, Lambda, API Gateway)
  6. API Gateway → Lambda functions

- [x] **Step 2: Create or update VPC endpoints security group**
  - [x] Create a dedicated security group for VPC endpoints if not exists
  - [x] Configure ingress rules to allow HTTPS (443) from ECS tasks and Lambda functions only
  - [x] Configure egress rules to allow all outbound traffic

**Implementation:**

- Created a dedicated security group for VPC endpoints named `aws_security_group.vpc_endpoints`
- Configured specific ingress rules to restrict access to only necessary sources:
  - Added an ingress rule allowing HTTPS (port 443) from the ECS tasks security group
  - Added an ingress rule allowing HTTPS (port 443) from the Lambda security group
- Configured egress rules to allow all outbound traffic (0.0.0.0/0)
- Added comprehensive tags including:
  - Name tag with resource prefix
  - Environment tag from variable
  - ManagedBy tag set to "terraform"
- Added detailed comments explaining the purpose of the security group and its rules
- This security group will be used for all VPC endpoints in Phase 3, replacing the overly permissive Lambda security group
- The new configuration follows the principle of least privilege by only allowing access from specific security groups

## Phase 3: VPC Endpoints Configuration

- [x] **Step 1: Check for existing VPC endpoints**
  - [x] Review all Terraform files for VPC endpoint definitions
  - [x] Identify all resources that reference existing VPC endpoints

**Findings:**

- Identified five VPC endpoints in the infrastructure:
  1. **S3 Gateway Endpoint** (`aws_vpc_endpoint.s3` in network.tf):
     - Type: Gateway
     - Uses route table IDs from data.aws_route_tables.default.ids
     - No security group (not required for Gateway type)
     - No policy defined

  2. **SSM Interface Endpoint** (`aws_vpc_endpoint.ssm` in network.tf):
     - Type: Interface
     - Uses subnet IDs from data.aws_subnets.default.ids
     - Uses Lambda security group (overly permissive)
     - Private DNS enabled
     - No policy defined

  3. **SES Interface Endpoint** (`aws_vpc_endpoint.ses` in network.tf):
     - Type: Interface
     - Uses subnet IDs from data.aws_subnets.default.ids
     - Uses Lambda security group (overly permissive)
     - Private DNS enabled
     - No policy defined

  4. **Lambda Interface Endpoint** (`aws_vpc_endpoint.lambda` in network.tf):
     - Type: Interface
     - Uses subnet IDs from data.aws_subnets.default.ids
     - Uses Lambda security group (overly permissive)
     - Private DNS enabled
     - No policy defined

  5. **API Gateway Interface Endpoint** (`aws_vpc_endpoint.api_gateway` in network.tf):
     - Type: Interface
     - Uses subnet IDs from data.aws_subnets.default.ids
     - Uses Lambda security group (overly permissive)
     - Private DNS enabled
     - Has a policy allowing all API Gateway operations to any principal

- **Resources Referencing VPC Endpoints**:
  - API Gateway (`aws_api_gateway_rest_api.main` in api_gateway.tf):
    - References the API Gateway VPC endpoint in its endpoint configuration
    - References the API Gateway VPC endpoint in its resource policy
  - Outputs (`outputs.tf`):
    - Outputs the API Gateway VPC endpoint ID

- **Issues Identified**:
  - All Interface endpoints use subnet IDs from data.aws_subnets.default.ids without filtering for private subnets
  - All Interface endpoints use the Lambda security group which has overly permissive inbound rules
  - The S3 Gateway endpoint uses route table IDs from data.aws_route_tables.default.ids
  - The API Gateway VPC endpoint policy is overly permissive, allowing all operations to any principal

- [x] **Step 2: Update S3 Gateway endpoint**
  - [x] Update to use the custom VPC
  - [x] Configure to use private route table
  - [x] Ensure appropriate tags are applied

**Implementation:**

- Updated the S3 Gateway endpoint to use the custom VPC (already configured via the data source)
- Modified the endpoint to use only the private route table instead of all route tables
  - Changed from `route_table_ids = data.aws_route_tables.default.ids` to `route_table_ids = [aws_route_table.private.id]`
  - This ensures S3 traffic from private subnets goes directly to S3 without going through the NAT Gateway
- Added comprehensive tags including:
  - Environment tag from variable
  - ManagedBy tag set to "terraform"
- The S3 Gateway endpoint doesn't require a security group as it's a Gateway type endpoint
- This configuration ensures that resources in private subnets can access S3 efficiently without internet access

- [x] **Step 3: Update Interface endpoints (SSM, SES, Lambda, API Gateway)**
  - [x] Update to use the custom VPC
  - [x] Configure to use private subnets only
  - [x] Update security group to use the dedicated VPC endpoints security group
  - [x] Ensure private DNS is enabled
  - [x] Verify and update endpoint policies as needed
  - [x] Add appropriate tags for consistency

**Implementation:**

- Updated all Interface endpoints to use the custom VPC (already configured via the data source)
- Modified all Interface endpoints to use private subnets only:
  - Changed from `subnet_ids = data.aws_subnets.default.ids` to `subnet_ids = data.aws_subnets.private.ids`
  - This ensures VPC endpoints are only placed in private subnets for better security
- Updated all Interface endpoints to use the dedicated VPC endpoints security group:
  - Changed from `security_group_ids = [aws_security_group.lambda_sg.id]` to `security_group_ids = [aws_security_group.vpc_endpoints.id]`
  - This replaces the overly permissive Lambda security group with the more restrictive VPC endpoints security group
- Verified that private DNS is enabled for all Interface endpoints
- Updated the API Gateway VPC endpoint policy to be more restrictive:
  - Changed from allowing all API Gateway operations on all resources to only allowing the Invoke action on specific resources
  - Changed from `Action = "execute-api:*"` and `Resource = "*"` to `Action = "execute-api:Invoke"` and `Resource = "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:${aws_api_gateway_rest_api.main.id}/*"`
  - This follows the principle of least privilege by only allowing the necessary actions on specific resources
- Added comprehensive tags to all Interface endpoints including:
  - Environment tag from variable
  - ManagedBy tag set to "terraform"
- This configuration ensures that VPC endpoints are properly secured and follow best practices

## Phase 4: Database Configuration

- [ ] **Step 1: Check for existing RDS configurations**
  - [ ] Review all Terraform files for RDS-related resources
  - [ ] Identify dependencies on subnet groups and security groups

## Phase 5: Lambda Configuration

- [ ] **Step 1: Check for existing Lambda configurations**
  - [ ] Review all Terraform files for Lambda function definitions
  - [ ] Identify VPC configurations and security group references

- [ ] **Step 2: Update Lambda VPC configuration**
  - [ ] Modify to use private subnets from the custom VPC
  - [ ] Update security group references
  - [ ] Verify environment variables are correctly set

## Phase 6: ECS Configuration

- [ ] **Step 1: Check for existing ECS configurations**
  - [ ] Review all Terraform files for ECS-related resources
  - [ ] Identify network configurations and security group references

- [ ] **Step 2: Update ECS service network configuration**
  - [ ] Modify to use private subnets from the custom VPC
  - [ ] Update security group references
  - [ ] Verify assign_public_ip is set to false

- [ ] **Step 3: Update ECS task definition**
  - [ ] Verify environment variables are correctly set
  - [ ] Ensure API_ENDPOINT is correctly configured to use the VPC endpoint

## Phase 7: API Gateway Configuration

- [ ] **Step 1: Check for existing API Gateway configurations**
  - [ ] Review all Terraform files for API Gateway resources
  - [ ] Identify endpoint configurations and policy references

- [ ] **Step 2: Update API Gateway endpoint configuration**
  - [ ] Verify it's configured as PRIVATE
  - [ ] Update VPC endpoint references
  - [ ] Update resource policy to reference the custom VPC
  - [ ] Ensure it references the correct IAM roles
