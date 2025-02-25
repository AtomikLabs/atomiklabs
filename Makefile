# Development environment setup and management
.PHONY: setup start stop restart clean test logs tf-local shell check-health aws-setup run-service

# Colors for pretty output
YELLOW := \033[33m
BLUE := \033[34m
GREEN := \033[32m
RED := \033[31m
RESET := \033[0m

# Docker Compose files and profiles
DC_FILE := docker/docker-compose.yml
DC_TEST_FILE := docker/docker-compose.test.yml
DC := docker-compose -f $(DC_FILE)
DC_TEST := docker-compose -f $(DC_FILE) -f $(DC_TEST_FILE)
PROFILES := processor db nvd all

# Help command
help:
	@echo "$(BLUE)Available commands:$(RESET)"
	@echo "$(BLUE)Setup and Management:$(RESET)"
	@echo "  $(GREEN)make setup$(RESET)        - Initial setup of local development environment"
	@echo "  $(GREEN)make aws-setup$(RESET)    - Set up AWS CLI local alias"
	@echo "  $(GREEN)make check-health$(RESET) - Check LocalStack services health"
	@echo "\n$(BLUE)Service Control:$(RESET)"
	@echo "  $(GREEN)make start$(RESET)        - Start all services"
	@echo "  $(GREEN)make stop$(RESET)         - Stop all services"
	@echo "  $(GREEN)make restart$(RESET)      - Restart all services"
	@echo "  $(GREEN)make run-service$(RESET)  - Run specific service profile (e.g., make run-service PROFILE=processor)"
	@echo "\n$(BLUE)Development Tools:$(RESET)"
	@echo "  $(GREEN)make shell$(RESET)        - Open shell in service container (e.g., make shell SERVICE=arxiv-processor)"
	@echo "  $(GREEN)make logs$(RESET)         - View logs from all services"
	@echo "  $(GREEN)make logs-service$(RESET) - View logs from specific service"
	@echo "\n$(BLUE)Testing:$(RESET)"
	@echo "  $(GREEN)make test$(RESET)         - Run all tests"
	@echo "  $(GREEN)make test-service$(RESET) - Run tests for specific service"
	@echo "\n$(BLUE)Cleanup:$(RESET)"
	@echo "  $(GREEN)make clean$(RESET)        - Clean up all containers and volumes"
	@echo "\n$(BLUE)Terraform:$(RESET)"
	@echo "  $(GREEN)make tf-local$(RESET)     - Run Terraform commands for local workspace"
	@echo "\n$(YELLOW)Available Profiles:$(RESET) processor, db, nvd, all"

# Setup commands
setup:
	@echo "$(BLUE)Setting up local development environment...$(RESET)"
	@./scripts/local/setup-localstack.sh

aws-setup:
	@echo "$(BLUE)Setting up AWS CLI local alias...$(RESET)"
	@./scripts/local/aws-local-setup.sh

check-health:
	@echo "$(BLUE)Checking LocalStack health...$(RESET)"
	@./scripts/local/check-localstack.sh

# Service control commands
start:
	@echo "$(BLUE)Starting all services...$(RESET)"
	@$(DC) --profile all up -d

run-service:
	@if [ "$(PROFILE)" = "" ]; then \
		echo "$(RED)Please specify a profile: make run-service PROFILE=<profile>$(RESET)"; \
		echo "$(YELLOW)Available profiles: $(PROFILES)$(RESET)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Starting services with profile: $(PROFILE)$(RESET)"
	@$(DC) --profile $(PROFILE) up -d

# Stop all services
stop:
	@echo "$(BLUE)Stopping services...$(RESET)"
	@$(DC) down

# Restart all services
restart: stop start

# Clean up everything
clean:
	@echo "$(RED)Cleaning up all containers and volumes...$(RESET)"
	@$(DC) down -v

# Run all tests
test:
	@echo "$(BLUE)Running all tests...$(RESET)"
	@$(DC_TEST) up \
		arxiv-processor \
		db-init \
		nvd-checker

# Run tests for a specific service
test-service:
	@if [ "$(SERVICE)" = "" ]; then \
		echo "$(RED)Please specify a service: make test-service SERVICE=<service-name>$(RESET)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Running tests for $(SERVICE)...$(RESET)"
	@$(DC_TEST) up $(SERVICE)

# Development commands
shell:
	@if [ "$(SERVICE)" = "" ]; then \
		echo "$(RED)Please specify a service: make shell SERVICE=<service-name>$(RESET)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Opening shell in $(SERVICE)...$(RESET)"
	@$(DC) exec $(SERVICE) /bin/bash

logs:
	@echo "$(BLUE)Viewing all logs...$(RESET)"
	@$(DC) logs -f

# View logs for a specific service
logs-service:
	@if [ "$(SERVICE)" = "" ]; then \
		echo "$(RED)Please specify a service: make logs-service SERVICE=<service-name>$(RESET)"; \
		exit 1; \
	fi
	@$(DC) logs -f $(SERVICE)

# Terraform local workspace commands
tf-local:
	@if [ "$(CMD)" = "" ]; then \
		echo "$(RED)Please specify a Terraform command: make tf-local CMD=<command>$(RESET)"; \
		exit 1; \
	fi
	@cd infra && \
	terraform workspace select local && \
	terraform $(CMD)

# Default target
.DEFAULT_GOAL := help
