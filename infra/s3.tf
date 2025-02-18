resource "aws_s3_bucket" "newsletters" {
  bucket = local.newsletter_bucket_name

  tags = merge(local.common_tags, {
    Name      = "newsletters"
    Component = "storage"
  })
}

resource "aws_s3_bucket_versioning" "newsletters" {
  bucket = aws_s3_bucket.newsletters.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "newsletters" {
  bucket = aws_s3_bucket.newsletters.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
} 