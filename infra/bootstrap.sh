#!/bin/bash

set -e

echo "🚀 Bootstrapping Serverless AI Stock Analytics..."

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo "❌ SAM CLI not found. Please install it first:"
    echo "   pip install aws-sam-cli"
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

echo "📦 Building and deploying with SAM..."
cd "$(dirname "$0")"

# Build the application
sam build

# Deploy with guided setup
echo "🔧 Starting guided deployment..."
sam deploy --guided \
    --stack-name stox-ai-demo \
    --region us-east-1 \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides AlphaVantageApiKey="YOUR_API_KEY_HERE"

echo "⏳ Waiting for deployment to complete..."
aws cloudformation wait stack-create-complete \
    --stack-name stox-ai-demo \
    --region us-east-1

echo "📊 Setting up Athena database and tables..."

# Get stack outputs
API_URL=$(aws cloudformation describe-stacks \
    --stack-name stox-ai-demo \
    --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiInvokeUrl`].OutputValue' \
    --output text)

SITE_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name stox-ai-demo \
    --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`SiteBucketName`].OutputValue' \
    --output text)

CURATED_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name stox-ai-demo \
    --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`CuratedBucketName`].OutputValue' \
    --output text)

ATHENA_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name stox-ai-demo \
    --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`AthenaResultsBucketName`].OutputValue' \
    --output text)

echo "🗄️ Creating Athena database..."
aws athena start-query-execution \
    --query-string "CREATE DATABASE IF NOT EXISTS stox;" \
    --result-configuration "OutputLocation=s3://$ATHENA_BUCKET/" \
    --region us-east-1

# Update table location with actual bucket name
sed "s/stox-curated-demo-1234/$CURATED_BUCKET/g" ../sql/create_table_prices.sql > /tmp/create_table_prices.sql

echo "📋 Creating Athena table..."
aws athena start-query-execution \
    --query-string "$(cat /tmp/create_table_prices.sql)" \
    --result-configuration "OutputLocation=s3://$ATHENA_BUCKET/" \
    --region us-east-1

echo "👁️ Creating Athena views..."
aws athena start-query-execution \
    --query-string "$(cat ../sql/views.sql)" \
    --result-configuration "OutputLocation=s3://$ATHENA_BUCKET/" \
    --region us-east-1

echo "🌐 Setting up static website..."

# Update index.html with actual API URL
sed "s|https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/chat|$API_URL|g" ../web/index.html > /tmp/index.html

# Upload to S3
aws s3 cp /tmp/index.html s3://$SITE_BUCKET/index.html

echo "✅ Bootstrap complete!"
echo ""
echo "📋 Summary:"
echo "   API URL: $API_URL"
echo "   Website: http://$SITE_BUCKET.s3-website-us-east-1.amazonaws.com"
echo "   Curated Bucket: $CURATED_BUCKET"
echo "   Athena Results: $ATHENA_BUCKET"
echo ""
echo "🔑 Next steps:"
echo "   1. Set your Alpha Vantage API key:"
echo "      aws lambda update-function-configuration \\"
echo "        --function-name stox-ingest \\"
echo "        --environment Variables='{ALPHAVANTAGE_API_KEY=your_key_here}'"
echo ""
echo "   2. Test the ingestion:"
echo "      aws lambda invoke --function-name stox-ingest /tmp/response.json"
echo ""
echo "   3. Visit your website: http://$SITE_BUCKET.s3-website-us-east-1.amazonaws.com"
echo ""
echo "💰 Cost monitoring: Run './budget.sh' to set up $5 budget alerts"
