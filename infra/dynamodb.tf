resource "aws_dynamodb_table" "terraform_state_lock" {
  name           = "terraform-state-lock"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = merge(local.common_tags, {
    Name      = "terraform-state-lock"
    Component = "state-management"
  })
}

resource "aws_dynamodb_table" "newsletter_metadata" {
  name           = local.metadata_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"
  range_key      = "date"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "date"
    type = "S"
  }

  tags = merge(local.common_tags, {
    Name      = "newsletter-metadata"
    Component = "metadata"
  })
} 