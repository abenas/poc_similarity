# Makefile for Person Matching Solution

.PHONY: help local-up local-down local-logs test-data deploy-infra deploy-full clean

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Local Development
local-up: ## Start local Docker environment
	@echo "🚀 Starting local environment..."
	docker-compose up -d
	@echo "✅ Environment started!"
	@echo "Spark Master UI: http://localhost:8080"
	@echo "OpenSearch: http://localhost:9200"
	@echo "Kibana: http://localhost:5601"
	@echo "Jupyter: http://localhost:8888"

local-down: ## Stop local Docker environment
	@echo "🛑 Stopping local environment..."
	docker-compose down
	@echo "✅ Environment stopped"

local-clean: ## Stop and remove all volumes
	@echo "🧹 Cleaning local environment..."
	docker-compose down -v
	@echo "✅ Environment cleaned"

local-logs: ## Show logs from all containers
	docker-compose logs -f

local-restart: ## Restart local environment
	@make local-down
	@make local-up

# Data Generation
test-data-small: ## Generate 10k test records
	@echo "📊 Generating small test dataset (10k records)..."
	python app/generate_test_data.py --records 10000 --output ./data
	@echo "✅ Test data generated in ./data/"

test-data-medium: ## Generate 100k test records
	@echo "📊 Generating medium test dataset (100k records)..."
	python app/generate_test_data.py --records 100000 --output ./data
	@echo "✅ Test data generated in ./data/"

test-data-large: ## Generate 1M test records
	@echo "📊 Generating large test dataset (1M records)..."
	python app/generate_test_data.py --records 1000000 --output ./data
	@echo "✅ Test data generated in ./data/"

# Terraform
terraform-init: ## Initialize Terraform
	@echo "🔧 Initializing Terraform..."
	cd terraform && terraform init
	@echo "✅ Terraform initialized"

terraform-plan: ## Plan Terraform changes
	@echo "📋 Planning Terraform changes..."
	cd terraform && terraform plan
	@echo "✅ Plan complete"

terraform-apply: ## Apply Terraform changes
	@echo "🚀 Applying Terraform changes..."
	cd terraform && terraform apply
	@echo "✅ Infrastructure deployed"

terraform-destroy: ## Destroy all Terraform resources
	@echo "⚠️  This will destroy all infrastructure!"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds..."
	@sleep 5
	cd terraform && terraform destroy
	@echo "✅ Infrastructure destroyed"

terraform-output: ## Show Terraform outputs
	cd terraform && terraform output

# AWS Deployment
deploy-full: ## Full deployment (Terraform + scripts upload)
	@echo "🚀 Starting full deployment..."
	./deploy.sh
	@echo "✅ Deployment complete"

upload-scripts: ## Upload scripts to S3
	@echo "📤 Uploading scripts..."
	$(eval BUCKET := $(shell cd terraform && terraform output -raw s3_bucket_scripts))
	aws s3 cp app/person_matcher.py s3://$(BUCKET)/
	aws s3 cp app/opensearch_indexer.py s3://$(BUCKET)/
	aws s3 cp app/requirements.txt s3://$(BUCKET)/
	@echo "✅ Scripts uploaded"

upload-data: ## Upload test data to S3
	@echo "📤 Uploading test data..."
	$(eval BUCKET1 := $(shell cd terraform && terraform output -raw s3_bucket_data_source1))
	$(eval BUCKET2 := $(shell cd terraform && terraform output -raw s3_bucket_data_source2))
	aws s3 cp data/dataset1.parquet s3://$(BUCKET1)/
	aws s3 cp data/dataset2.parquet s3://$(BUCKET2)/
	@echo "✅ Data uploaded"

# AWS Operations
trigger-lambda: ## Manually trigger Lambda function
	@echo "⚡ Triggering Lambda..."
	aws lambda invoke --function-name person-matching-delta-detector output.json
	@cat output.json
	@rm output.json
	@echo "✅ Lambda triggered"

start-crawlers: ## Start Glue crawlers
	@echo "🕷️  Starting Glue crawlers..."
	aws glue start-crawler --name person-matching-dataset1-crawler
	aws glue start-crawler --name person-matching-dataset2-crawler
	@echo "✅ Crawlers started"

check-crawlers: ## Check crawler status
	@echo "📊 Crawler status:"
	@aws glue get-crawler --name person-matching-dataset1-crawler --query 'Crawler.State' --output text
	@aws glue get-crawler --name person-matching-dataset2-crawler --query 'Crawler.State' --output text

emr-steps: ## List EMR steps
	$(eval CLUSTER := $(shell cd terraform && terraform output -raw emr_cluster_id))
	@echo "📊 EMR Steps for cluster $(CLUSTER):"
	aws emr list-steps --cluster-id $(CLUSTER)

# Testing
test-matching-local: ## Run matching locally
	@echo "🧪 Running matching locally..."
	docker-compose exec app spark-submit \
		--master spark://spark-master:7077 \
		/app/person_matcher.py \
		person_data dataset1 dataset2 /data/output 0.7
	@echo "✅ Matching complete. Results in ./data/output/"

test-opensearch: ## Test OpenSearch connection
	@echo "🔍 Testing OpenSearch..."
	curl -s http://localhost:9200/_cluster/health | jq .
	@echo "✅ OpenSearch OK"

# Monitoring
logs-lambda: ## Tail Lambda logs
	aws logs tail /aws/lambda/person-matching-delta-detector --follow

logs-emr: ## Tail EMR logs (requires cluster ID)
	$(eval CLUSTER := $(shell cd terraform && terraform output -raw emr_cluster_id))
	@echo "📋 EMR logs for cluster $(CLUSTER)"
	aws logs tail /aws/emr/$(CLUSTER) --follow

metrics-emr: ## Show EMR metrics
	$(eval CLUSTER := $(shell cd terraform && terraform output -raw emr_cluster_id))
	@echo "📊 EMR Metrics for cluster $(CLUSTER)"
	aws cloudwatch get-metric-statistics \
		--namespace AWS/ElasticMapReduce \
		--metric-name YARNMemoryAvailablePercentage \
		--dimensions Name=JobFlowId,Value=$(CLUSTER) \
		--start-time $(shell date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
		--end-time $(shell date -u +%Y-%m-%dT%H:%M:%S) \
		--period 300 \
		--statistics Average

# Utilities
clean-data: ## Clean generated data files
	@echo "🧹 Cleaning data files..."
	rm -rf data/*.parquet data/*.csv
	@echo "✅ Data cleaned"

format-python: ## Format Python code with black
	@echo "🎨 Formatting Python code..."
	black app/ lambdas/
	@echo "✅ Code formatted"

lint-python: ## Lint Python code
	@echo "🔍 Linting Python code..."
	pylint app/ lambdas/
	@echo "✅ Linting complete"

check-aws: ## Check AWS credentials
	@echo "🔐 Checking AWS credentials..."
	@aws sts get-caller-identity
	@echo "✅ AWS credentials OK"

validate-terraform: ## Validate Terraform configuration
	@echo "✅ Validating Terraform..."
	cd terraform && terraform validate
	@echo "✅ Terraform configuration valid"

# Documentation
docs: ## Generate documentation
	@echo "📚 Documentation available in:"
	@echo "  - README.md"
	@echo "  - SOLUTION_SUMMARY.md"
	@echo "  - docs/architecture.md"
	@echo "  - docs/quick-reference.md"

# Quick Start
quickstart: local-up test-data-small test-matching-local ## Quick start: up + data + test
	@echo "🎉 Quick start complete!"
