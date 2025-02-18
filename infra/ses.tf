resource "aws_ses_email_identity" "recipients" {
  for_each = toset(var.email_config.recipients)
  email    = each.value
}

output "ses_verification_status" {
  value = "Verification emails have been sent to: ${join(", ", var.email_config.recipients)}"
} 