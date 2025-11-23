import json
import os
import boto3
from typing import Dict, Any

def get_athena_client():
    return boto3.client('athena')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Weekly maintenance tasks for stock data"""
    
    athena_db = os.environ['ATHENA_DB']
    athena_output = os.environ['ATHENA_OUTPUT']
    
    results = {}
    
    try:
        # Repair table to sync new partitions
        repair_result = repair_table(athena_db, athena_output)
        results['repair_table'] = repair_result
        
        # Optional: Compact recent data to Parquet (commented for week-1)
        # compact_result = compact_to_parquet(athena_db, athena_output)
        # results['compact_parquet'] = compact_result
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'timestamp': context.aws_request_id,
                'results': results
            })
        }
        
    except Exception as e:
        print(f"Maintenance error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def repair_table(athena_db: str, athena_output: str) -> Dict[str, Any]:
    """Run MSCK REPAIR TABLE to sync new partitions"""
    
    sql = "MSCK REPAIR TABLE stox.prices"
    
    athena_client = get_athena_client()
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
            raise Exception(f"MSCK REPAIR failed: {error_reason}")
        
        import time
        time.sleep(2)
    
    return {
        'status': 'success',
        'query_id': query_execution_id,
        'message': 'Partitions synced successfully'
    }

def compact_to_parquet(athena_db: str, athena_output: str) -> Dict[str, Any]:
    """Compact last 90 days of data to Parquet format (optional)"""
    
    sql = """
    CREATE TABLE stox.prices_parquet
    WITH (
        format = 'PARQUET',
        external_location = 's3://stox-curated-demo-1234/prices_parquet/'
    )
    AS
    SELECT date, open, high, low, close, volume, adj_close, ticker, year, month, day
    FROM stox.prices
    WHERE date >= current_date - interval '90' day
    """
    
    athena_client = get_athena_client()
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
            raise Exception(f"Parquet compaction failed: {error_reason}")
        
        import time
        time.sleep(5)
    
    return {
        'status': 'success',
        'query_id': query_execution_id,
        'message': 'Data compacted to Parquet successfully'
    }
