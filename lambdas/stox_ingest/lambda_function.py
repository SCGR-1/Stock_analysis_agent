import json
import os
import boto3
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any

s3_client = boto3.client('s3')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Daily stock data ingestion from Alpha Vantage API"""
    
    curated_bucket = os.environ['CURATED_BUCKET']
    watchlist = os.environ['WATCHLIST'].split(',')
    api_key = os.environ['ALPHAVANTAGE_API_KEY']
    
    results = {}
    
    for ticker in watchlist:
        ticker = ticker.strip().upper()
        try:
            data = fetch_stock_data(ticker, api_key)
            if data:
                s3_key = write_to_s3(data, ticker, curated_bucket)
                results[ticker] = {'status': 'success', 's3_key': s3_key}
            else:
                results[ticker] = {'status': 'no_data'}
        except Exception as e:
            print(f"Error processing {ticker}: {str(e)}")
            results[ticker] = {'status': 'error', 'error': str(e)}
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'timestamp': datetime.now().isoformat(),
            'results': results
        })
    }

def fetch_stock_data(ticker: str, api_key: str) -> Dict[str, Any]:
    """Fetch latest stock data from Alpha Vantage"""
    
    url = f"https://www.alphavantage.co/query"
    params = {
        'function': 'TIME_SERIES_DAILY_ADJUSTED',
        'symbol': ticker,
        'apikey': api_key,
        'outputsize': 'compact'
    }
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    if 'Error Message' in data:
        raise Exception(f"Alpha Vantage error: {data['Error Message']}")
    
    if 'Note' in data:
        raise Exception(f"API limit reached: {data['Note']}")
    
    time_series = data.get('Time Series (Daily)', {})
    if not time_series:
        return None
    
    latest_date = max(time_series.keys())
    latest_data = time_series[latest_date]
    
    return {
        'date': latest_date,
        'open': float(latest_data['1. open']),
        'high': float(latest_data['2. high']),
        'low': float(latest_data['3. low']),
        'close': float(latest_data['4. close']),
        'volume': int(latest_data['5. volume']),
        'adj_close': float(latest_data['5. adjusted close'])
    }

def write_to_s3(data: Dict[str, Any], ticker: str, bucket: str) -> str:
    """Write stock data to S3 with proper partitioning"""
    
    date_obj = datetime.strptime(data['date'], '%Y-%m-%d')
    
    csv_content = f"date,open,high,low,close,volume,adj_close\n"
    csv_content += f"{data['date']},{data['open']},{data['high']},{data['low']},{data['close']},{data['volume']},{data['adj_close']}\n"
    
    s3_key = f"prices/ticker={ticker}/year={date_obj.year}/month={date_obj.month:02d}/day={date_obj.day:02d}/data.csv"
    
    s3_client.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=csv_content,
        ContentType='text/csv'
    )
    
    return s3_key
