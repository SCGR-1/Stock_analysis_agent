import json
import os
import boto3
import re
from typing import Dict, Any, List

bedrock_client = boto3.client('bedrock-runtime', region_name=os.environ['BEDROCK_REGION'])
athena_client = boto3.client('athena')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AI agent that converts natural language to SQL and executes it"""
    
    try:
        body = json.loads(event.get('body', '{}'))
        question = body.get('question', '')
        
        if not question:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Question is required'})
            }
        
        # Generate SQL using Bedrock
        sql = generate_sql(question)
        
        # Execute SQL in Athena
        columns, rows = execute_athena_query(sql)
        
        # Summarize results using Bedrock
        answer = summarize_results(question, columns, rows)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'question': question,
                'sql': sql,
                'columns': columns,
                'rows': rows[:50],  # Limit to 50 rows
                'answer': answer
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

def generate_sql(question: str) -> str:
    """Generate SQL from natural language using Bedrock"""
    
    few_shot_examples = """
Examples:
Q: "7-day SMA of AAPL for last 30 days"
A: <SQL>SELECT date, close, AVG(close) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as sma_7 FROM stox.prices WHERE ticker='AAPL' AND date >= current_date - interval '30' day ORDER BY date;</SQL>

Q: "Best performer YTD on my watchlist"
A: <SQL>WITH ytd_returns AS (SELECT ticker, (close - LAG(close) OVER (PARTITION BY ticker ORDER BY date)) / LAG(close) OVER (PARTITION BY ticker ORDER BY date) as daily_return FROM stox.prices WHERE date >= date_trunc('year', current_date)) SELECT ticker, SUM(daily_return) as ytd_return FROM ytd_returns GROUP BY ticker ORDER BY ytd_return DESC LIMIT 1;</SQL>

Q: "Max drawdown of TSLA YTD"
A: <SQL>WITH running_peak AS (SELECT date, close, MAX(close) OVER (ORDER BY date) as peak FROM stox.prices WHERE ticker='TSLA' AND date >= date_trunc('year', current_date)) SELECT MIN((close - peak) / peak) as max_drawdown FROM running_peak;</SQL>
"""
    
    prompt = f"""You are a SQL expert. Convert the natural language question to SQL for Athena against the stox.prices table.

Table schema:
- date DATE
- open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE
- volume BIGINT, adj_close DOUBLE
- PARTITIONED BY (ticker STRING, year INT, month INT, day INT)

{few_shot_examples}

Question: {question}

Rules:
1. Return ONLY the SQL query wrapped in <SQL>...</SQL> tags
2. Use only SELECT statements, no DDL/DML
3. Always filter by ticker when specific stock mentioned
4. Limit date ranges to reasonable defaults (last 90 days if not specified)
5. Use proper Athena SQL syntax
6. Add LIMIT 200 to prevent large result sets

SQL:"""
    
    response = bedrock_client.invoke_model(
        modelId='anthropic.claude-3-haiku-20240307-v1:0',
        body=json.dumps({
            'prompt': prompt,
            'max_tokens_to_sample': 500,
            'temperature': 0
        }),
        contentType='application/json'
    )
    
    response_body = json.loads(response['body'].read())
    sql_text = response_body['completion']
    
    # Extract SQL from <SQL> tags
    sql_match = re.search(r'<SQL>(.*?)</SQL>', sql_text, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
    else:
        raise Exception("No SQL found in response")

def execute_athena_query(sql: str) -> tuple[List[str], List[List[Any]]]:
    """Execute SQL query in Athena and return results"""
    
    athena_db = os.environ['ATHENA_DB']
    athena_output = os.environ['ATHENA_OUTPUT']
    
    # Start query execution
    response = athena_client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={'Database': athena_db},
        ResultConfiguration={'OutputLocation': athena_output}
    )
    
    query_execution_id = response['QueryExecutionId']
    
    # Poll for completion
    while True:
        response = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
        status = response['QueryExecution']['Status']['State']
        
        if status == 'SUCCEEDED':
            break
        elif status == 'FAILED':
            error_reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
            raise Exception(f"Athena query failed: {error_reason}")
        
        import time
        time.sleep(2)
    
    # Get results
    response = athena_client.get_query_results(QueryExecutionId=query_execution_id)
    
    # Parse column names
    columns = []
    if 'ResultSet' in response and 'ResultSetMetadata' in response['ResultSet']:
        columns = [col['Name'] for col in response['ResultSet']['ResultSetMetadata']['ColumnInfo']]
    
    # Parse rows
    rows = []
    if 'ResultSet' in response and 'Rows' in response['ResultSet']:
        for row in response['ResultSet']['Rows'][1:]:  # Skip header row
            row_data = []
            for field in row['Data']:
                if 'VarCharValue' in field:
                    row_data.append(field['VarCharValue'])
                else:
                    row_data.append(None)
            rows.append(row_data)
    
    return columns, rows

def summarize_results(question: str, columns: List[str], rows: List[List[Any]]) -> str:
    """Summarize query results using Bedrock"""
    
    if not rows:
        return "No data found for the given criteria."
    
    # Prepare data summary
    data_summary = f"Columns: {', '.join(columns)}\n"
    data_summary += f"Rows returned: {len(rows)}\n"
    data_summary += f"Sample data (first 3 rows):\n"
    for i, row in enumerate(rows[:3]):
        data_summary += f"Row {i+1}: {dict(zip(columns, row))}\n"
    
    prompt = f"""Summarize the following SQL query results in 2-3 sentences. If the data appears to be time series, suggest a chart mapping (x-axis, y-axis, series) in plain words.

Original question: {question}

Query results:
{data_summary}

Provide a concise summary and chart suggestion if applicable:"""
    
    response = bedrock_client.invoke_model(
        modelId='anthropic.claude-3-haiku-20240307-v1:0',
        body=json.dumps({
            'prompt': prompt,
            'max_tokens_to_sample': 300,
            'temperature': 0.3
        }),
        contentType='application/json'
    )
    
    response_body = json.loads(response['body'].read())
    return response_body['completion'].strip()
