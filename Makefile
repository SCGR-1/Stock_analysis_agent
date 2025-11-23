.PHONY: build deploy bootstrap test site clean

# Build the SAM application
build:
	cd infra && sam build

# Deploy with guided setup
deploy: build
	cd infra && sam deploy --guided

# Run bootstrap script
bootstrap:
	@if command -v chmod >/dev/null 2>&1; then \
		chmod +x infra/bootstrap.sh; \
	fi
	bash infra/bootstrap.sh

# Run tests
test:
	python -m pytest tests/ -v

# Sync website to S3 bucket
site:
	@echo "Getting site bucket name..."
	@SITE_BUCKET=$$(aws cloudformation describe-stacks --stack-name stox-ai-demo --region us-east-1 --query 'Stacks[0].Outputs[?OutputKey==`SiteBucketName`].OutputValue' --output text 2>/dev/null || echo "stox-site-demo-1234"); \
	echo "Syncing to bucket: $$SITE_BUCKET"; \
	aws s3 sync web/ s3://$$SITE_BUCKET/ --delete

# Clean up resources
clean:
	@echo "⚠️  This will delete the entire stack and all data!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	aws cloudformation delete-stack --stack-name stox-ai-demo --region us-east-1
	@echo "Stack deletion initiated. Check AWS Console for progress."

# Set Alpha Vantage API key
set-api-key:
	@read -p "Enter your Alpha Vantage API key: " key; \
	aws lambda update-function-configuration \
		--function-name stox-ingest \
		--environment Variables='{ALPHAVANTAGE_API_KEY=$$key}' \
		--region us-east-1

# Test ingestion function
test-ingest:
	aws lambda invoke --function-name stox-ingest /tmp/ingest-response.json --region us-east-1
	cat /tmp/ingest-response.json | jq '.'

# Test agent function
test-agent:
	@echo '{"question": "Show me AAPL price for last 7 days"}' | \
	aws lambda invoke --function-name stox-agent --payload file:///dev/stdin /tmp/agent-response.json --region us-east-1
	cat /tmp/agent-response.json | jq '.'

# Show stack outputs
outputs:
	aws cloudformation describe-stacks --stack-name stox-ai-demo --region us-east-1 --query 'Stacks[0].Outputs' --output table

# Local development
local-start:
	cd infra && sam local start-api --port 3000 --env-vars ../sam-env.json

local-ingest:
	cd infra && sam local invoke StoxIngestFunction --event ../test-payload.json --env-vars ../sam-env.json

local-agent:
	cd infra && sam local invoke StoxAgentFunction --event ../agent-payload.json --env-vars ../sam-env.json

local-maint:
	cd infra && sam local invoke StoxMaintFunction --event ../maint-event.json --env-vars ../sam-env.json

# Local web interface
local-web:
	python -m http.server 8000 --directory web

# Help
help:
	@echo "Available targets:"
	@echo "  build       - Build SAM application"
	@echo "  deploy      - Deploy with guided setup"
	@echo "  bootstrap   - Complete setup (build, deploy, configure)"
	@echo "  test        - Run unit tests"
	@echo "  site        - Sync website to S3"
	@echo "  clean       - Delete entire stack"
	@echo "  set-api-key - Set Alpha Vantage API key"
	@echo "  test-ingest - Test ingestion function"
	@echo "  test-agent  - Test agent function"
	@echo "  outputs     - Show stack outputs"
	@echo ""
	@echo "Local Development:"
	@echo "  local-start   - Start local API Gateway on port 3000"
	@echo "  local-ingest  - Test ingestion function locally"
	@echo "  local-agent   - Test agent function locally"
	@echo "  local-maint   - Test maintenance function locally"
	@echo "  local-web     - Serve web interface on port 8000"
	@echo "  help          - Show this help"
