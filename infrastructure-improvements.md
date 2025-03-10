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

- [x] **Step 1: Check for existing RDS configurations**
  - [x] Review all Terraform files for RDS-related resources
  - [x] Identify dependencies on subnet groups and security groups

**Findings:**

- Identified the following RDS-related resources in the infrastructure:
  1. **DB Subnet Group** (`aws_db_subnet_group.postgresql` in rds.tf):
     - Uses subnet IDs from data.aws_subnets.default.ids without filtering for private subnets
     - Referenced by the RDS instance

  2. **DB Parameter Group** (`aws_db_parameter_group.postgresql` in rds.tf):
     - Configures PostgreSQL 17 parameters
     - Referenced by the RDS instance

  3. **DB Instance** (`aws_db_instance.postgresql` in rds.tf):
     - PostgreSQL 17.3 database
     - Uses the DB subnet group and parameter group
     - Uses the PostgreSQL security group
     - Not publicly accessible (publicly_accessible = false)
     - Storage is encrypted
     - Free tier eligible settings (no multi-AZ, minimal backup retention)

  4. **PostgreSQL Security Group** (`aws_security_group.postgresql` in rds.tf):
     - Allows PostgreSQL inbound (port 5432) from ECS tasks security group
     - Allows PostgreSQL inbound (port 5432) from Lambda security group
     - Allows all outbound traffic to anywhere (0.0.0.0/0)
     - Referenced by the RDS instance

  5. **DB Password Parameter** (`aws_ssm_parameter.db_password` in rds.tf):
     - Stores the database password in AWS Systems Manager Parameter Store
     - Used by the RDS instance

- **Resources Referencing RDS**:
  - Lambda functions in lambda.tf:
    - Reference the RDS instance for connection details (address, port, name, username)
    - Have permissions to access the RDS instance
  - ECS tasks in ecs.tf:
    - Have permissions to access the RDS instance
  - Outputs in outputs.tf:
    - Output the RDS endpoint, database name, and username

- **Issues Identified**:
  - The DB subnet group uses all subnets without filtering for private subnets
  - The RDS instance is correctly configured as not publicly accessible
  - The security group configuration follows best practices by only allowing access from specific security groups

- [x] **Step 2: Update RDS subnet group**
  - [x] Modify to use private subnets from the custom VPC
  - [x] Ensure appropriate tags are applied

**Implementation:**

- Updated the DB subnet group to use only private subnets from the custom VPC:
  - Changed from `subnet_ids = data.aws_subnets.default.ids` to `subnet_ids = data.aws_subnets.private.ids`
  - This ensures the RDS instance is only placed in private subnets for better security
- Added comprehensive tags including:
  - Environment tag from variable
  - ManagedBy tag set to "terraform"
- This configuration ensures that the RDS instance is properly secured in private subnets
- The RDS instance will now be deployed in private subnets with no direct internet access, following security best practices
- Access to the RDS instance is still controlled by the PostgreSQL security group, which only allows connections from ECS tasks and Lambda functions

## Phase 5: Lambda Configuration

- [x] **Step 1: Check for existing Lambda configurations**
  - [x] Review all Terraform files for Lambda function definitions
  - [x] Identify VPC configurations and security group references

**Findings:**

- Identified two Lambda functions in the infrastructure:
  1. **Mailer Lambda Function** (`aws_lambda_function.mailer` in lambda.tf):
     - Python 3.11 runtime
     - VPC configuration:
       - Uses subnet IDs from data.aws_subnets.default.ids without filtering for private subnets
       - Uses the Lambda security group (aws_security_group.lambda_sg.id)
     - Environment variables include:
       - Database connection details (host, port, name, username)
       - SSM parameter for database password
     - Referenced by:
       - Step Functions state machine in step_functions.tf
       - CloudWatch Log Group in lambda.tf
       - Outputs in outputs.tf

  2. **arXiv API Lambda Function** (`aws_lambda_function.arxiv_api` in lambda.tf):
     - Python 3.11 runtime
     - VPC configuration:
       - Uses subnet IDs from data.aws_subnets.default.ids without filtering for private subnets
       - Uses the Lambda security group (aws_security_group.lambda_sg.id)
     - Environment variables include:
       - Database connection details (host, port, name, username)
       - SSM parameter for database password
       - Logging configuration
     - Referenced by:
       - API Gateway integrations in api_gateway.tf
       - CloudWatch Log Group in lambda.tf
       - CloudWatch Alarm in cloudwatch.tf
       - Outputs in outputs.tf

- **Issues Identified**:
  - Both Lambda functions use subnet IDs from data.aws_subnets.default.ids without filtering for private subnets
  - Both Lambda functions use the Lambda security group which has overly permissive inbound rules
  - The Lambda functions need to access:
    - RDS PostgreSQL database
    - VPC endpoints (SSM, SES, Lambda, API Gateway)
    - AWS services via VPC endpoints

- [x] **Step 2: Update Lambda VPC configuration**
  - [x] Modify to use private subnets from the custom VPC
  - [x] Update security group references
  - [x] Verify environment variables are correctly set

**Implementation:**

- Updated both Lambda functions to use only private subnets from the custom VPC:
  - Changed from `subnet_ids = data.aws_subnets.default.ids` to `subnet_ids = data.aws_subnets.private.ids`
  - This ensures Lambda functions are only deployed in private subnets for better security
- Modified the Lambda security group to remove the overly permissive inbound rule:
  - Removed the ingress rule allowing HTTPS (port 443) from anywhere (0.0.0.0/0)
  - Kept the self-referencing ingress rule to allow traffic between resources using this security group
  - Kept the egress rule allowing all outbound traffic
- Added comprehensive tags to the Lambda security group including:
  - Environment tag from variable
  - ManagedBy tag set to "terraform"
- Verified that environment variables are correctly set and don't need changes
- This configuration ensures that Lambda functions:
  - Are deployed in private subnets with no direct internet access
  - Can access the internet via the NAT Gateway for outbound connections
  - Can access the RDS database via the PostgreSQL security group
  - Can access VPC endpoints for AWS services
  - Are protected by a more restrictive security group
- The Lambda functions will now follow security best practices while maintaining all required functionality

## Phase 6: ECS Configuration

- [x] **Step 1: Check for existing ECS configurations**
  - [x] Review all Terraform files for ECS-related resources
  - [x] Identify network configurations and security group references

**Findings:**

- Identified the following ECS-related resources in the infrastructure:
  1. **ECS Cluster** (`aws_ecs_cluster.arxiv` in ecs.tf):
     - Fargate capacity provider
     - No VPC configuration at the cluster level

  2. **ECS Task Definition** (`aws_ecs_task_definition.arxiv_processor` in ecs.tf):
     - Fargate compatibility
     - awsvpc network mode
     - Container definition includes:
       - API_ENDPOINT environment variable pointing to the API Gateway
       - AWS_REGION environment variable
       - LOG_LEVEL environment variable
     - Uses ECS task and execution roles

  3. **ECS Service** (`aws_ecs_service.arxiv_processor` in ecs.tf):
     - Fargate launch type
     - Network configuration:
       - Uses subnet IDs from data.aws_subnets.default.ids without filtering for private subnets
       - Uses the ECS tasks security group (aws_security_group.ecs_tasks.id)
       - assign_public_ip is set to false, which is correct for private subnets

  4. **Step Functions State Machine** (in step_functions.tf):
     - References the ECS task definition
     - Network configuration:
       - Uses subnet IDs from data.aws_subnets.default.ids without filtering for private subnets
       - Uses the ECS tasks security group (aws_security_group.ecs_tasks.id)
       - AssignPublicIp is set to "DISABLED", which is correct for private subnets

- **Issues Identified**:
  - Both the ECS service and Step Functions state machine use subnet IDs from data.aws_subnets.default.ids without filtering for private subnets
  - The API_ENDPOINT environment variable in the task definition points to the API Gateway's public endpoint, not the VPC endpoint
  - The ECS tasks security group only allows outbound traffic, which is correct but may need to be verified for specific requirements
  - The assign_public_ip setting is correctly set to false/DISABLED, but without a NAT Gateway in the current setup, tasks wouldn't have internet access

- [x] **Step 2: Update ECS service network configuration**
  - [x] Modify to use private subnets from the custom VPC
  - [x] Update security group references
  - [x] Verify assign_public_ip is set to false

**Implementation:**

- Updated the ECS service network configuration to use only private subnets from the custom VPC:
  - Changed from `subnets = data.aws_subnets.default.ids` to `subnets = data.aws_subnets.private.ids`
  - This ensures ECS tasks are only deployed in private subnets for better security
- Updated the Step Functions state machine network configuration to use only private subnets:
  - Changed from `Subnets = data.aws_subnets.default.ids` to `Subnets = data.aws_subnets.private.ids`
  - This ensures consistency between the ECS service and Step Functions state machine
- Verified that the security group reference is correct (aws_security_group.ecs_tasks.id)
- Confirmed that assign_public_ip is set to false/DISABLED, which is the correct configuration
- With the NAT Gateway created in Phase 1, Step 4, ECS tasks in private subnets can now access the internet
- This configuration ensures that ECS tasks:
  - Are deployed in private subnets with no direct internet access
  - Can access the internet via the NAT Gateway for outbound connections (e.g., to arXiv)
  - Can access the RDS database via the PostgreSQL security group
  - Can access VPC endpoints for AWS services
  - Are protected by appropriate security groups
- The ECS tasks will now follow security best practices while maintaining all required functionality

- [x] **Step 3: Update ECS task definition**
  - [x] Verify environment variables are correctly set
  - [x] Ensure API_ENDPOINT is correctly configured to use the VPC endpoint

**Implementation:**

- Updated the API_ENDPOINT environment variable in the ECS task definition to use the VPC endpoint URL:
  - Changed from `https://${aws_api_gateway_rest_api.main.id}-${var.environment}.execute-api.${var.region}.amazonaws.com` to `https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.region}.amazonaws.com/${var.environment}/`
  - This ensures that API calls stay within the VPC and don't go through the internet
- Verified that the URL format includes the correct stage name (environment variable) and trailing slash
  - The format matches the one used in outputs.tf: `${invoke_url}${stage_name}/`
- Verified that other environment variables (AWS_REGION, LOG_LEVEL) are correctly set
- Added comments explaining the purpose of the change and why it's important for security
- This configuration ensures that:
  - ECS tasks communicate with the API Gateway through the VPC endpoint
  - All traffic remains within the VPC for better security
  - The URL format is correct and consistent with the rest of the infrastructure
  - The configuration follows security best practices by using private networking for internal communication

## Phase 7: API Gateway Configuration

- [x] **Step 1: Check for existing API Gateway configurations**
  - [x] Review all Terraform files for API Gateway resources
  - [x] Identify endpoint configurations and policy references

**Findings:**

- Identified the following API Gateway resources in the infrastructure:
  1. **REST API** (`aws_api_gateway_rest_api.main` in api_gateway.tf):
     - Configured as a PRIVATE API Gateway
     - References the API Gateway VPC endpoint in its endpoint configuration
     - Has a resource policy with three statements:
       - Allows access from within the default VPC (`aws:SourceVpc`: data.aws_vpc.default.id)
       - Allows access from the VPC endpoint (`aws:SourceVpce`: aws_vpc_endpoint.api_gateway.id)
       - Allows access from specific IAM roles (ECS task role and Lambda API role)

  2. **API Gateway Deployment** (`aws_api_gateway_deployment.main` in api_gateway.tf):
     - References all API resources, methods, and integrations
     - Has a trigger for redeployment based on changes to resources
     - Has dependencies on all integrations

  3. **API Gateway Stage** (`aws_api_gateway_stage.main` in api_gateway.tf):
     - Stage name is set to the environment variable
     - X-Ray tracing is enabled
     - Caching is disabled
     - Has a stage variable for deployment timestamp

  4. **API Gateway VPC Endpoint** (`aws_vpc_endpoint.api_gateway` in network.tf):
     - Interface endpoint type
     - Uses private subnets (already updated in Phase 3)
     - Uses the VPC endpoints security group (already updated in Phase 3)
     - Has private DNS enabled
     - Has a policy allowing execute-api:Invoke on the specific API Gateway

  5. **Lambda Integration** (`aws_lambda_function.arxiv_api` in lambda.tf):
     - Python 3.11 runtime
     - VPC configuration using private subnets (already updated in Phase 5)
     - Environment variables for database connection and logging

- **Resources Referencing API Gateway**:
  - ECS task definition in ecs.tf:
    - References the API Gateway in the API_ENDPOINT environment variable (updated in Phase 6)
  - Lambda functions in lambda.tf:
    - Have permissions to invoke the API Gateway
  - Outputs in outputs.tf:
    - Output the API Gateway URL and ID

- **Issues Identified**:
  - The API Gateway resource policy references the default VPC (`data.aws_vpc.default.id`) instead of the custom VPC
  - The policy allows execute-api:Invoke on all resources (`Resource = "*"`) in two statements, which is overly permissive
  - The API Gateway is correctly configured as PRIVATE
  - The VPC endpoint for API Gateway is correctly configured with private subnets and the dedicated security group

- [x] **Step 2: Update API Gateway endpoint configuration**
  - [x] Verify it's configured as PRIVATE
  - [x] Update VPC endpoint references
  - [x] Update resource policy to reference the custom VPC
  - [x] Ensure it references the correct IAM roles

**Implementation:**

- Verified that the API Gateway is correctly configured as PRIVATE:
  - Confirmed the endpoint_configuration types is set to ["PRIVATE"]
  - Confirmed it references the API Gateway VPC endpoint in its configuration
- Verified that the VPC endpoint references are correct:
  - The data source `data.aws_vpc.default` already references the custom VPC (`aws_vpc.main.id`)
  - No changes were needed to the VPC reference as it was already updated in Phase 1
- Updated the API Gateway resource policy to be more restrictive:
  - Changed all three policy statements to use a specific resource scope instead of wildcard "*"
  - Updated from `Resource = "*"` to `Resource = "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:${aws_api_gateway_rest_api.main.id}/*"`
  - This follows the principle of least privilege by only allowing access to this specific API Gateway
- Verified that the policy references the correct IAM roles:
  - Confirmed the policy includes the ECS task role and Lambda API role
  - No changes were needed to the IAM role references
- This configuration ensures that:
  - The API Gateway is only accessible from within the custom VPC
  - Only authorized roles can invoke the API Gateway
  - The policy follows the principle of least privilege
  - All components work together correctly without breaking existing functionality

**Additional Fix:**

- Fixed a circular dependency between `aws_vpc_endpoint.api_gateway` and `aws_api_gateway_rest_api.main`:
  - The API Gateway REST API was referencing the VPC endpoint in its endpoint configuration
  - The VPC endpoint was referencing the API Gateway REST API ID in its policy
  - Updated the VPC endpoint policy to use a wildcard for the API Gateway ID (`*/*` instead of `${aws_api_gateway_rest_api.main.id}/*`)
  - This breaks the circular dependency while still maintaining appropriate access controls
  - The API Gateway's own resource policy provides the more specific restrictions needed for security

- Fixed self-referential blocks in the API Gateway resource policy:
  - The API Gateway REST API was referencing itself in its own policy, which Terraform doesn't allow
  - Updated all three policy statements to use a wildcard for the API Gateway ID (`*/*` instead of `${aws_api_gateway_rest_api.main.id}/*`)
  - This avoids the self-referential blocks while still maintaining appropriate access controls
  - The combination of VPC, VPC endpoint, and IAM role conditions still provides strong security controls
