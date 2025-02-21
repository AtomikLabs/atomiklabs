resource "aws_s3_bucket" "storage" {
  bucket = local.storage_bucket_name

  tags = merge(local.common_tags, {
    Name      = "storage"
    Component = "storage"
  })
}

resource "aws_s3_bucket_versioning" "storage" {
  bucket = aws_s3_bucket.storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "storage" {
  bucket = aws_s3_bucket.storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
} 