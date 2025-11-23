# Local Development Guide

## Prerequisites for Local Development

1. **Python 3.12+** installed
2. **AWS CLI** configured (`aws configure`)
3. **SAM CLI** installed (`pip install aws-sam-cli`)
4. **Docker** running (required for SAM local)
5. **Alpha Vantage API Key** (free from https://www.alphavantage.co/support/#api-key)

## Quick Start - Local Development

### 1. Build the Application
```bash
make build
```

### 2. Start Local API Gateway
```bash
make local-start
```
This starts the API Gateway locally on `http://localhost:3000`

### 3. Test Individual Functions

**Test Ingestion Function:**
```bash
make local-ingest
```

**Test Agent Function:**
```bash
make local-agent
```

**Test Maintenance Function:**
```bash
make local-maint
```

### 4. Serve Web Interface Locally
```bash
make local-web
```
This serves the web interface on `http://localhost:8000`

## Environment Variables for Local Development

Create a `.env.local` file with:
```bash
ALPHAVANTAGE_API_KEY=your_api_key_here
AWS_REGION=us-east-1
```

## Local Development Workflow

### Option 1: Full Local Stack (Recommended)
1. **Start API Gateway**: `make local-start`
2. **Update web/index.html**: Change API_URL to `http://localhost:3000/chat`
3. **Serve web interface**: `make local-web`
4. **Test**: Visit `http://localhost:8000`

### Option 2: Individual Function Testing
1. **Test ingestion**: `make local-ingest`
2. **Test agent**: `make local-agent`
3. **Run unit tests**: `make test`

## Local Development Notes

### AWS Services Required
- **S3**: For data storage (uses real AWS S3)
- **Athena**: For SQL queries (uses real AWS Athena)
- **Bedrock**: For AI (uses real AWS Bedrock)

### Mocking Options
For completely offline development, you can:
1. Mock AWS services in tests
2. Use local SQLite instead of Athena
3. Use local LLM instead of Bedrock

### Debugging
- **View logs**: SAM local shows logs in terminal
- **Debug mode**: Add `--debug` to sam commands
- **Hot reload**: SAM local automatically reloads on code changes

## Troubleshooting Local Development

### Common Issues

1. **Docker not running**
   ```bash
   # Start Docker Desktop
   # Or install Docker and start service
   ```

2. **Port conflicts**
   ```bash
   # Use different ports
   sam local start-api --port 3001
   ```

3. **AWS credentials not found**
   ```bash
   aws configure
   # Or set environment variables
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   ```

4. **Bedrock access denied**
   - Ensure Bedrock is enabled in us-east-1
   - Check IAM permissions

### Performance Tips

1. **Use local caching** for repeated API calls
2. **Mock external APIs** during development
3. **Use smaller datasets** for testing
4. **Enable debug logging** for troubleshooting

## Development Commands Reference

```bash
# Build and test
make build          # Build SAM application
make test           # Run unit tests

# Local development
make local-start    # Start API Gateway (port 3000)
make local-ingest   # Test ingestion function
make local-agent    # Test agent function
make local-maint    # Test maintenance function
make local-web      # Serve web interface (port 8000)

# Production deployment
make deploy         # Deploy to AWS
make bootstrap      # Full setup and deployment
```
