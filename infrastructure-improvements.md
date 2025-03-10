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

- [ ] **Step 1: Check for existing security groups**
  - [ ] Review all Terraform files for security group definitions
  - [ ] Identify all resources that reference existing security groups
  - [ ] Document the required access patterns between resources

- [ ] **Step 2: Create or update VPC endpoints security group**
  - [ ] Create a dedicated security group for VPC endpoints if not exists
  - [ ] Configure ingress rules to allow HTTPS (443) from ECS tasks and Lambda functions only
  - [ ] Configure egress rules to allow all outbound traffic

- [ ] **Step 3: Update Lambda security group**
  - [ ] Remove overly permissive inbound rules
  - [ ] Ensure self-referencing ingress rule is maintained
  - [ ] Verify egress rules allow necessary outbound traffic

- [ ] **Step 4: Update ECS tasks security group**
  - [ ] Verify egress rules allow outbound internet access
  - [ ] Add specific ingress rules if needed for task communication

- [ ] **Step 5: Update RDS security group**
  - [ ] Ensure ingress rules only allow traffic from appropriate security groups
  - [ ] Verify egress rules are properly configured

## Phase 3: VPC Endpoints Configuration

- [ ] **Step 1: Check for existing VPC endpoints**
  - [ ] Review all Terraform files for VPC endpoint definitions
  - [ ] Identify all resources that reference existing VPC endpoints

- [ ] **Step 2: Update S3 Gateway endpoint**
  - [ ] Update to use the custom VPC
  - [ ] Configure to use private route table
  - [ ] Ensure appropriate tags are applied

- [ ] **Step 3: Update Interface endpoints (SSM, SES, Lambda, API Gateway)**
  - [ ] Update to use the custom VPC
  - [ ] Configure to use private subnets only
  - [ ] Update security group to use the dedicated VPC endpoints security group
  - [ ] Ensure private DNS is enabled
  - [ ] Verify endpoint policies are properly configured

## Phase 4: Database Configuration

- [ ] **Step 1: Check for existing RDS configurations**
  - [ ] Review all Terraform files for RDS-related resources
  - [ ] Identify dependencies on subnet groups and security groups

- [ ] **Step 2: Update RDS subnet group**
  - [ ] Modify to use private subnets from the custom VPC
  - [ ] Ensure appropriate tags are applied

- [ ] **Step 3: Verify RDS instance configuration**
  - [ ] Ensure it's using the updated subnet group
  - [ ] Verify it's using the appropriate security group
  - [ ] Check for any other VPC-related configurations that need updating

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

## Phase 8: Testing and Validation

- [ ] **Step 1: Create a validation plan**
  - [ ] Define tests for VPC and subnet connectivity
  - [ ] Define tests for NAT Gateway functionality
  - [ ] Define tests for VPC endpoint accessibility
  - [ ] Define tests for security group rules

- [ ] **Step 2: Implement changes incrementally**
  - [ ] Apply VPC infrastructure changes first
  - [ ] Apply security group changes
  - [ ] Apply VPC endpoint changes
  - [ ] Apply service-specific changes (RDS, Lambda, ECS, API Gateway)

- [ ] **Step 3: Monitor and troubleshoot**
  - [ ] Set up CloudWatch alarms for critical resources
  - [ ] Monitor VPC Flow Logs for unexpected traffic patterns
  - [ ] Prepare rollback plan in case of issues
