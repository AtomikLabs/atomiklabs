resource "aws_codeartifact_domain" "domain" {
  domain = local.resource_prefix

  tags = local.common_tags
}

resource "aws_codeartifact_repository" "neo4j_client" {
  repository  = "neo4j-client"
  domain      = aws_codeartifact_domain.domain.domain
  description = "Private repository for atomiklabs Neo4j client"

  upstream {
    repository_name = aws_codeartifact_repository.python_public.repository
  }

  tags = local.common_tags
}

# Update neo4j client repository upstream configuration
resource "aws_codeartifact_repository_upstream_configuration" "allow_upstream_deps" {
  repository      = aws_codeartifact_repository.neo4j_client.repository
  domain          = aws_codeartifact_domain.domain.domain
  upstream_configuration {
    allow_upstream_dependencies = true
  }
}

resource "aws_codeartifact_repository" "python_public" {
  repository  = "python-public"
  domain      = aws_codeartifact_domain.domain.domain
  description = "Public PyPI mirror"
  
  external_connections {
    external_connection_name = "public:pypi"
  }

  tags = local.common_tags
}

resource "aws_codeartifact_repository_permissions_policy" "neo4j_client_policy" {
  domain      = aws_codeartifact_domain.domain.domain
  repository  = aws_codeartifact_repository.neo4j_client.repository
  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["codeartifact:ReadFromRepository"]
        Effect   = "Allow"
        Principal = "*"
        Resource = "*"
      }
    ]
  })
}

output "codeartifact_repository" {
  value = aws_codeartifact_repository.neo4j_client.repository
  description = "CodeArtifact repository name"
}

output "codeartifact_domain" {
  value = aws_codeartifact_domain.domain.domain
  description = "CodeArtifact domain name"
}

resource "aws_ssm_parameter" "codeartifact_repo" {
  name  = "/${var.project}/${var.environment}/codeartifact/neo4j_client_repo"
  type  = "String"
  value = "${aws_codeartifact_domain.domain.domain}/${aws_codeartifact_repository.neo4j_client.repository}"
  
  tags = local.common_tags
}
