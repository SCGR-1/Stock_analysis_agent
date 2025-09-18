# Serverless AI Stock Analytics on AWS

A production-ready, minimal-cost AWS project that ingests daily stock prices, queries them with Athena, and exposes a Bedrock-powered AI agent that answers natural-language questions by generating SQL.

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

## Quick Start

### Prerequisites

- AWS CLI configured (`aws configure`)
- SAM CLI installed (`pip install aws-sam-cli`)
- Alpha Vantage API key (free at [alphavantage.co](https://www.alphavantage.co/support/#api-key))

### One-Command Setup

```bash
make bootstrap
```

This will:
1. Build and deploy the SAM application
2. Create all AWS resources (S3, Lambda, API Gateway, etc.)
3. Set up Athena database and tables
4. Deploy the static website
5. Provide next steps

### Manual Setup

```bash
# Build and deploy
make build
make deploy

# Set your API key
make set-api-key

# Test ingestion
make test-ingest

# Visit your website
make outputs  # Get the website URL
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

## Usage

### Web Interface

Visit your deployed website and ask questions like:
- "7-day SMA of AAPL for last 30 days"
- "Best performer YTD on my watchlist"
- "Max drawdown of TSLA YTD"
- "Show me GOOGL price trend for last 60 days"

### API Usage

```bash
curl -X POST https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me AAPL price for last 7 days"}'
```

Response:
```json
{
  "question": "Show me AAPL price for last 7 days",
  "sql": "SELECT date, close FROM stox.prices WHERE ticker='AAPL' AND date >= current_date - interval '7' day ORDER BY date;",
  "columns": ["date", "close"],
  "rows": [["2024-01-15", "100.0"], ...],
  "answer": "AAPL closed at $100 on 2024-01-15, showing a steady upward trend over the past week."
}
```

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

## Development

### Running Tests

```bash
make test
```

### Local Development

```bash
# Test individual functions
make test-ingest
make test-agent

# View logs
aws logs tail /aws/lambda/stox-ingest --follow
aws logs tail /aws/lambda/stox-agent --follow
```

### Adding New Features

1. **New SQL Views**: Add to `sql/views.sql`
2. **New Lambda**: Create in `lambdas/` directory
3. **New Endpoints**: Update `infra/template.yaml`

## Troubleshooting

### Common Issues

1. **API Key Not Set**
   ```bash
   make set-api-key
   ```

2. **Athena Query Fails**
   - Check S3 bucket permissions
   - Verify table exists: `aws athena start-query-execution --query-string "SHOW TABLES IN stox;"`

3. **Bedrock Access Denied**
   - Ensure Bedrock is enabled in us-east-1
   - Check IAM permissions for `bedrock:InvokeModel`

4. **Website Not Loading**
   - Check S3 bucket policy allows public read
   - Verify `index.html` is uploaded

### Monitoring

```bash
# View stack outputs
make outputs

# Check function logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/stox-

# Monitor costs
aws budgets describe-budgets --account-id $(aws sts get-caller-identity --query Account --output text)
```

## Security & Cleanup

### Security Notes

- API Gateway allows CORS from any origin (demo only)
- S3 buckets have public read for website only
- Lambda functions use least-privilege IAM roles
- No secrets stored in code (use environment variables)

### Cleanup

```bash
# Delete entire stack
make clean

# Manual cleanup if needed
aws s3 rm s3://stox-curated-demo-1234 --recursive
aws s3 rm s3://stox-athena-demo-1234 --recursive  
aws s3 rm s3://stox-site-demo-1234 --recursive
aws cloudformation delete-stack --stack-name stox-ai-demo
```

## Cost Optimization

- **Data Retention**: Consider lifecycle policies for old data
- **Query Optimization**: Use LIMIT clauses, filter by date/ticker
- **Bedrock Usage**: Claude Haiku is cost-effective for simple queries
- **Lambda Memory**: 256MB is sufficient for most workloads

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
1. Check AWS CloudWatch logs
2. Verify all prerequisites are met
3. Test individual components with `make test-*` commands
4. Review IAM permissions and resource policies
