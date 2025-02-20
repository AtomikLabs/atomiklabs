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

  global_secondary_index {
    name               = "DateIndex"
    hash_key           = "date"
    projection_type    = "ALL"
  }

  tags = merge(local.common_tags, {
    Name      = "newsletter-metadata"
    Component = "metadata"
  })
}
