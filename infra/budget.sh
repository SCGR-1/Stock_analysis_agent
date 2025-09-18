#!/bin/bash

set -e

echo "💰 Setting up AWS Budget for cost monitoring..."

# Get current account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create budget JSON
cat > /tmp/budget.json << EOF
{
    "BudgetName": "stox-ai-demo-budget",
    "BudgetLimit": {
        "Amount": "5.00",
        "Unit": "USD"
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "CostFilters": {
        "TagKey": [],
        "Service": []
    },
    "TimePeriod": {
        "Start": "$(date -u +%Y-%m-01T00:00:00Z)",
        "End": "2025-12-31T23:59:59Z"
    },
    "CalculatedSpend": {
        "ActualSpend": {
            "Amount": "0.00",
            "Unit": "USD"
        },
        "ForecastedSpend": {
            "Amount": "0.00",
            "Unit": "USD"
        }
    },
    "BudgetLimit": {
        "Amount": "5.00",
        "Unit": "USD"
    }
}
EOF

# Create budget
aws budgets create-budget \
    --account-id $ACCOUNT_ID \
    --budget file:///tmp/budget.json

# Create notification
cat > /tmp/notification.json << EOF
{
    "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE",
        "NotificationState": "ALARM"
    },
    "Subscribers": [
        {
            "SubscriptionType": "EMAIL",
            "Address": "$(aws sts get-caller-identity --query 'Account' --output text)@example.com"
        }
    ]
}
EOF

echo "📧 Budget created with 80% threshold alert"
echo "   Note: Update the email address in AWS Budgets console"
echo "   Budget name: stox-ai-demo-budget"
echo "   Limit: $5.00/month"

# Clean up
rm -f /tmp/budget.json /tmp/notification.json
