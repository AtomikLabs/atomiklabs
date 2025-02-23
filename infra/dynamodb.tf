resource "aws_dynamodb_table" "newsletter_metadata" {
  name           = local.metadata_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"
  range_key      = "processed_date"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "processed_date"
    type = "S"
  }

  attribute {
    name = "primary_category"
    type = "S"
  }

  global_secondary_index {
    name               = "CategoryDateIndex"
    hash_key           = "primary_category"
    range_key         = "processed_date"
    projection_type    = "ALL"
  }

  tags = merge(local.common_tags, {
    Name      = "newsletter-metadata"
    Component = "metadata"
  })
}
