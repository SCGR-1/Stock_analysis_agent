import pytest
import json
from unittest.mock import patch, MagicMock
from lambdas.stox_ingest.lambda_function import lambda_handler, fetch_stock_data, write_to_s3

class TestStoxIngest:
    
    @patch.dict('os.environ', {
        'CURATED_BUCKET': 'test-bucket',
        'WATCHLIST': 'AAPL,MSFT',
        'ALPHAVANTAGE_API_KEY': 'test-key'
    })
    @patch('lambdas.stox_ingest.lambda_function.s3_client')
    @patch('lambdas.stox_ingest.lambda_function.fetch_stock_data')
    def test_lambda_handler_success(self, mock_fetch, mock_s3):
        """Test successful lambda execution"""
        mock_fetch.return_value = {
            'date': '2024-01-15',
            'open': 100.0,
            'high': 105.0,
            'low': 99.0,
            'close': 103.0,
            'volume': 1000000,
            'adj_close': 103.0
        }
        
        result = lambda_handler({}, {})
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert 'AAPL' in body['results']
        assert 'MSFT' in body['results']
        assert body['results']['AAPL']['status'] == 'success'
    
    @patch('lambdas.stox_ingest.lambda_function.requests.get')
    def test_fetch_stock_data_success(self, mock_get):
        """Test successful API data fetch"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'Time Series (Daily)': {
                '2024-01-15': {
                    '1. open': '100.00',
                    '2. high': '105.00',
                    '3. low': '99.00',
                    '4. close': '103.00',
                    '5. volume': '1000000',
                    '5. adjusted close': '103.00'
                }
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = fetch_stock_data('AAPL', 'test-key')
        
        assert result['date'] == '2024-01-15'
        assert result['open'] == 100.0
        assert result['close'] == 103.0
        assert result['volume'] == 1000000
    
    @patch('lambdas.stox_ingest.lambda_function.requests.get')
    def test_fetch_stock_data_api_error(self, mock_get):
        """Test API error handling"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'Error Message': 'Invalid API call'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with pytest.raises(Exception, match="Alpha Vantage error"):
            fetch_stock_data('INVALID', 'test-key')
    
    @patch('lambdas.stox_ingest.lambda_function.s3_client')
    def test_write_to_s3(self, mock_s3):
        """Test S3 write functionality"""
        data = {
            'date': '2024-01-15',
            'open': 100.0,
            'high': 105.0,
            'low': 99.0,
            'close': 103.0,
            'volume': 1000000,
            'adj_close': 103.0
        }
        
        result = write_to_s3(data, 'AAPL', 'test-bucket')
        
        expected_key = 'prices/ticker=AAPL/year=2024/month=01/day=15/data.csv'
        assert result == expected_key
        
        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args
        assert call_args[1]['Bucket'] == 'test-bucket'
        assert call_args[1]['Key'] == expected_key
        assert call_args[1]['ContentType'] == 'text/csv'
        assert 'date,open,high,low,close,volume,adj_close' in call_args[1]['Body']
