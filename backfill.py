#!/usr/bin/env python3
"""
Historical data backfill script using Stooq API
Run this once to populate historical data before daily ingestion starts
"""

import requests
import boto3
import os
from datetime import datetime, timedelta
import time

def backfill_stock_data(ticker, start_date, end_date, bucket_name):
    """Backfill historical data for a ticker"""
    
    s3_client = boto3.client('s3')
    
    # Convert dates to Stooq format
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')
    
    # Stooq API URL
    url = f"https://stooq.com/q/d/l/?s={ticker}&i=d&f=csv"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        lines = response.text.strip().split('\n')
        header = lines[0]
        
        # Process each day's data
        for line in lines[1:]:
            if not line.strip():
                continue
                
            parts = line.split(',')
            if len(parts) < 6:
                continue
                
            date_str = parts[0]
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                continue
                
            # Skip if outside date range
            if date_obj < start_date or date_obj > end_date:
                continue
                
            # Skip weekends (optional)
            if date_obj.weekday() >= 5:
                continue
                
            open_price = float(parts[1]) if parts[1] else 0
            high_price = float(parts[2]) if parts[2] else 0
            low_price = float(parts[3]) if parts[3] else 0
            close_price = float(parts[4]) if parts[4] else 0
            volume = int(float(parts[5])) if parts[5] else 0
            
            # Create CSV content
            csv_content = f"date,open,high,low,close,volume,adj_close\n"
            csv_content += f"{date_str},{open_price},{high_price},{low_price},{close_price},{volume},{close_price}\n"
            
            # S3 key with partitioning
            s3_key = f"prices/ticker={ticker}/year={date_obj.year}/month={date_obj.month:02d}/day={date_obj.day:02d}/data.csv"
            
            # Upload to S3
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=csv_content,
                ContentType='text/csv'
            )
            
            print(f"Uploaded {ticker} data for {date_str}")
            
        return True
        
    except Exception as e:
        print(f"Error backfilling {ticker}: {str(e)}")
        return False

def main():
    """Main backfill function"""
    
    # Configuration
    tickers = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'TSLA']
    start_date = datetime(2024, 1, 1)  # Adjust as needed
    end_date = datetime.now() - timedelta(days=1)
    
    # Get bucket name from environment or use default
    bucket_name = os.environ.get('CURATED_BUCKET', 'stox-curated-demo-1234')
    
    print(f"Backfilling data from {start_date.date()} to {end_date.date()}")
    print(f"Tickers: {', '.join(tickers)}")
    print(f"Bucket: {bucket_name}")
    
    success_count = 0
    for ticker in tickers:
        print(f"\nBackfilling {ticker}...")
        if backfill_stock_data(ticker, start_date, end_date, bucket_name):
            success_count += 1
        time.sleep(1)  # Rate limiting
    
    print(f"\nBackfill complete: {success_count}/{len(tickers)} tickers successful")
    
    if success_count > 0:
        print("\nNext steps:")
        print("1. Run MSCK REPAIR TABLE to sync partitions:")
        print("   aws athena start-query-execution --query-string 'MSCK REPAIR TABLE stox.prices;'")
        print("2. Test queries in Athena console")
        print("3. Start daily ingestion with Lambda function")

if __name__ == "__main__":
    main()
