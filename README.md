# Serverless AI Stock Analytics on AWS

A production-ready, minimal-cost AWS project that ingests daily stock prices, queries them with Athena, and exposes a Bedrock-powered AI agent that answers natural-language questions by generating SQL.

## 🚀 **LIVE DEMO**

**🌐 Web App**: [http://stox-site-demo-852902711883.s3-website-us-east-1.amazonaws.com](http://stox-site-demo-852902711883.s3-website-us-east-1.amazonaws.com)

**🔗 API Endpoint**: `https://dw0ry2vj4m.execute-api.us-east-1.amazonaws.com/prod/chat`

**📊 Current Data**: AAPL, MSFT, AMZN, GOOGL, TSLA (updated daily)

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Alpha Vantage │───▶│   stox-ingest    │───▶│   S3 Curated    │
│   (Daily Data)  │    │   (Lambda)       │    │   (Partitioned)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐             │
│   Web Frontend  │───▶│   API Gateway    │───▶         │
│   (S3 Static)   │    │   /chat endpoint │             │
└─────────────────┘    └──────────────────┘             │
                                │                       │
                                ▼                       ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   stox-agent     │───▶│   Athena + Glue │
                       │   (Bedrock AI)   │    │   (SQL Engine)  │
                       └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Bedrock LLM    │
                       │   (Claude Haiku) │
                       └──────────────────┘
```

## 🚀 **Quick Start**

### Prerequisites

- **AWS CLI** configured (`aws configure`)
- **SAM CLI** installed (`pip install aws-sam-cli`)
- **Alpha Vantage API key** (free at [alphavantage.co](https://www.alphavantage.co/support/#api-key))
- **Docker** running (for SAM local development)

### 🎯 **One-Command Deployment**

```bash
# Windows
dev.bat build
sam deploy --parameter-overrides AlphaVantageApiKey=YOUR_API_KEY --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --region us-east-1

# Linux/Mac
make build
make deploy
```

### 📋 **Step-by-Step Deployment**

**1. Build the Application**
```bash
cd infra
sam build
```

**2. Deploy to AWS**
```bash
sam deploy --parameter-overrides AlphaVantageApiKey=YOUR_API_KEY --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --region us-east-1
```

**3. Set Up Athena Database**
```bash
aws athena start-query-execution --query-string "CREATE DATABASE IF NOT EXISTS stox;" --result-configuration OutputLocation=s3://YOUR_ATHENA_BUCKET/
```

**4. Create Athena Table**
```bash
aws athena start-query-execution --query-string "CREATE EXTERNAL TABLE IF NOT EXISTS stox.prices (date DATE, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT, adj_close DOUBLE) PARTITIONED BY (ticker STRING, year INT, month INT, day INT) STORED AS TEXTFILE LOCATION 's3://YOUR_CURATED_BUCKET/prices/' TBLPROPERTIES ('skip.header.line.count' = '1', 'serialization.format' = ',', 'field.delim' = ',');" --result-configuration OutputLocation=s3://YOUR_ATHENA_BUCKET/
```

**5. Deploy Web Interface**
```bash
aws s3 sync web/ s3://YOUR_SITE_BUCKET/ --delete
```

**6. Test Data Ingestion**
```bash
aws lambda invoke --function-name stox-ingest --region us-east-1 ingest-response.json
```

**7. Repair Athena Partitions**
```bash
aws lambda invoke --function-name stox-maint --region us-east-1 maint-response.json
```

### 🔧 **Get Your Bucket Names**

After deployment, get your bucket names:
```bash
aws cloudformation describe-stacks --stack-name stox-ai-demo --region us-east-1 --query 'Stacks[0].Outputs' --output table
```

## Components

### Lambda Functions

- **stox-ingest**: Daily OHLCV updates from Alpha Vantage into partitioned CSV in S3
- **stox-agent**: Bedrock LLM → generate SQL → run Athena → summarize results  
- **stox-maint**: Weekly MSCK REPAIR TABLE and optional compaction

### Data Model

**Athena Table**: `stox.prices`
```sql
CREATE EXTERNAL TABLE stox.prices (
    date DATE,
    open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
    volume BIGINT, adj_close DOUBLE
)
PARTITIONED BY (ticker STRING, year INT, month INT, day INT)
```

**S3 Layout**:
```
s3://stox-curated-demo-1234/prices/
  ticker=AAPL/year=2025/month=01/day=15/data.csv
  ticker=MSFT/year=2025/month=01/day=15/data.csv
  ...
```

### SQL Views

- `v_returns`: Daily returns per ticker
- `v_sma`: 7/20-day moving averages
- `v_vol20`: 20-day rolling volatility
- `v_drawdown`: Running peak vs close analysis
- `v_corr`: 60-day rolling correlation between tickers

## 🎮 **Usage**

### 🌐 **Web Interface**

Visit your deployed website and ask questions like:
- **"7-day SMA of AAPL for last 30 days"**
- **"Best performer YTD on my watchlist"**
- **"Max drawdown of TSLA YTD"**
- **"Show me GOOGL price trend for last 60 days"**
- **"Compare AAPL vs MSFT performance"**
- **"What's the volatility of AMZN?"**

### 🔗 **API Usage**

```bash
curl -X POST https://dw0ry2vj4m.execute-api.us-east-1.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me AAPL price for last 7 days"}'
```

**Response:**
```json
{
  "question": "Show me AAPL price for last 7 days",
  "sql": "SELECT date, close FROM stox.prices WHERE ticker='AAPL' AND date >= current_date - interval '7' day ORDER BY date;",
  "columns": ["date", "close"],
  "rows": [["2025-10-17", "178.85"], ...],
  "answer": "AAPL closed at $178.85 on 2025-10-17, showing recent price movements over the past week."
}
```

### 📊 **Sample Questions to Try**

**Basic Analysis:**
- "Show me AAPL price for last 7 days"
- "What was GOOGL's closing price yesterday?"
- "Display MSFT stock prices for the past month"

**Technical Analysis:**
- "7-day SMA of AAPL for last 30 days"
- "20-day moving average of TSLA"
- "Show me GOOGL price trend for last 60 days"

**Performance Analysis:**
- "Best performer YTD on my watchlist"
- "Which stock had the highest return last week?"
- "Compare AAPL vs MSFT performance this month"

**Risk Analysis:**
- "Max drawdown of TSLA YTD"
- "What's the volatility of AMZN over the last 30 days?"
- "Show me the worst performing day for each stock"

## Configuration

### Environment Variables

- `ALPHAVANTAGE_API_KEY`: Your Alpha Vantage API key
- `WATCHLIST`: Comma-separated stock symbols (default: AAPL,MSFT,AMZN,GOOGL,TSLA)
- `ATHENA_DB`: Database name (default: stox)
- `BEDROCK_REGION`: AWS region for Bedrock (default: us-east-1)

### Cost Management

Set up budget alerts:
```bash
chmod +x infra/budget.sh
./infra/budget.sh
```

**Free Tier Usage**:
- Lambda: 1M requests/month free
- S3: 5GB storage free
- Athena: 1TB data scanned free/month
- Bedrock: Pay per token (very low cost)

## 🛠️ **Development**

### 🧪 **Running Tests**

```bash
# Run all tests
python -m pytest tests/ -v

# Windows
dev.bat test

# Linux/Mac
make test
```

### 🏠 **Local Development**

**Windows:**
```bash
# Build application
dev.bat build

# Start local API Gateway (port 3000)
dev.bat start

# Serve web interface (port 8000)
dev.bat web

# Test individual functions
dev.bat ingest
dev.bat agent
dev.bat maint
```

**Linux/Mac:**
```bash
# Build application
make build

# Start local API Gateway (port 3000)
make local-start

# Serve web interface (port 8000)
make local-web

# Test individual functions
make local-ingest
make local-agent
make local-maint
```

### 📝 **Adding New Features**

1. **New SQL Views**: Add to `sql/views.sql`
2. **New Lambda**: Create in `lambdas/` directory
3. **New Endpoints**: Update `infra/template.yaml`
4. **New Questions**: Add to web interface presets

### 🔍 **Debugging**

**View Lambda Logs:**
```bash
aws logs tail /aws/lambda/stox-ingest --follow
aws logs tail /aws/lambda/stox-agent --follow
aws logs tail /aws/lambda/stox-maint --follow
```

**Test Functions Locally:**
```bash
# Test with sample data
sam local invoke StoxIngestFunction --event ../test-payload.json
sam local invoke StoxAgentFunction --event ../agent-payload.json
```

## 🚨 **Troubleshooting**

### 🔧 **Common Issues**

**1. API Key Not Set**
```bash
# Update Lambda environment variable
aws lambda update-function-configuration \
  --function-name stox-ingest \
  --environment Variables='{ALPHAVANTAGE_API_KEY=YOUR_KEY}' \
  --region us-east-1
```

**2. Athena Query Fails**
- Check S3 bucket permissions
- Verify table exists: `aws athena start-query-execution --query-string "SHOW TABLES IN stox;"`
- Repair partitions: `aws lambda invoke --function-name stox-maint --region us-east-1`

**3. Bedrock Access Denied**
- Ensure Bedrock is enabled in us-east-1 region
- Check IAM permissions for `bedrock:InvokeModel`
- Verify Claude Haiku model access

**4. Website Not Loading**
- Check S3 bucket policy allows public read
- Verify `index.html` is uploaded: `aws s3 ls s3://YOUR_SITE_BUCKET/`
- Check API URL in `web/index.html`

**5. Deployment Fails**
- Ensure Docker is running (for SAM local)
- Check AWS credentials: `aws sts get-caller-identity`
- Verify region permissions

### 📊 **Monitoring**

**View Stack Outputs:**
```bash
aws cloudformation describe-stacks --stack-name stox-ai-demo --region us-east-1 --query 'Stacks[0].Outputs' --output table
```

**Check Function Logs:**
```bash
aws logs tail /aws/lambda/stox-ingest --follow
aws logs tail /aws/lambda/stox-agent --follow
aws logs tail /aws/lambda/stox-maint --follow
```

**Monitor Costs:**
```bash
aws budgets describe-budgets --account-id $(aws sts get-caller-identity --query Account --output text)
```

**Test Individual Components:**
```bash
# Test data ingestion
aws lambda invoke --function-name stox-ingest --region us-east-1 ingest-response.json

# Test maintenance
aws lambda invoke --function-name stox-maint --region us-east-1 maint-response.json

# Check S3 data
aws s3 ls s3://YOUR_CURATED_BUCKET/prices/ --recursive
```

## 🔒 **Security & Cleanup**

### 🛡️ **Security Notes**

- **API Gateway**: Allows CORS from any origin (demo only)
- **S3 Buckets**: Public read for website only, private for data
- **IAM Roles**: Least-privilege access for Lambda functions
- **Secrets**: No hardcoded secrets, uses environment variables
- **Bedrock**: Secure AI model access with proper permissions

### 🧹 **Cleanup**

**Delete Entire Stack:**
```bash
# Windows
aws cloudformation delete-stack --stack-name stox-ai-demo --region us-east-1

# Linux/Mac
make clean
```

**Manual Cleanup:**
```bash
# Delete S3 buckets (replace with your bucket names)
aws s3 rm s3://stox-curated-demo-852902711883 --recursive
aws s3 rm s3://stox-athena-demo-852902711883 --recursive  
aws s3 rm s3://stox-site-demo-852902711883 --recursive

# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name stox-ai-demo --region us-east-1
```

**Verify Cleanup:**
```bash
aws cloudformation describe-stacks --stack-name stox-ai-demo --region us-east-1
# Should return "Stack does not exist"
```

## 💰 **Cost Optimization**

### 📊 **Free Tier Usage**
- **Lambda**: 1M requests/month free
- **S3**: 5GB storage free
- **Athena**: 1TB data scanned free/month
- **Bedrock**: Pay per token (very low cost)

### 🎯 **Cost-Saving Tips**
- **Data Retention**: Consider lifecycle policies for old data
- **Query Optimization**: Use LIMIT clauses, filter by date/ticker
- **Bedrock Usage**: Claude Haiku is cost-effective for simple queries
- **Lambda Memory**: 256MB is sufficient for most workloads
- **Scheduled Jobs**: Daily ingestion vs real-time updates

### 📈 **Estimated Monthly Costs**
- **Small Usage** (< 100 queries/day): ~$5-10/month
- **Medium Usage** (100-1000 queries/day): ~$20-50/month
- **Heavy Usage** (1000+ queries/day): ~$50-100/month

## 📄 **License**

MIT License - see LICENSE file for details.

## 🆘 **Support**

**For issues and questions:**
1. Check AWS CloudWatch logs
2. Verify all prerequisites are met
3. Test individual components with `dev.bat` or `make` commands
4. Review IAM permissions and resource policies
5. Check the troubleshooting section above

**Getting Help:**
- **AWS Documentation**: [Lambda](https://docs.aws.amazon.com/lambda/), [Athena](https://docs.aws.amazon.com/athena/), [Bedrock](https://docs.aws.amazon.com/bedrock/)
- **SAM CLI**: [Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- **Alpha Vantage**: [API Documentation](https://www.alphavantage.co/documentation/)

---

## 🎉 **You're Ready!**

Your ServerlessDataAgent is now a fully functional, production-ready AI stock analytics platform! 

**🌐 Live Demo**: [http://stox-site-demo-852902711883.s3-website-us-east-1.amazonaws.com](http://stox-site-demo-852902711883.s3-website-us-east-1.amazonaws.com)

**🚀 Start asking questions about your stock data!**
