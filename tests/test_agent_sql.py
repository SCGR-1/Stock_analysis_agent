import pytest
import json
from unittest.mock import patch, MagicMock
from lambdas.stox_agent.lambda_function import lambda_handler, generate_sql, execute_athena_query, summarize_results

class TestStoxAgent:
    
    @patch.dict('os.environ', {
        'ATHENA_DB': 'stox',
        'ATHENA_OUTPUT': 's3://test-bucket/',
        'BEDROCK_REGION': 'us-east-1'
    })
    @patch('lambdas.stox_agent.lambda_function.summarize_results')
    @patch('lambdas.stox_agent.lambda_function.execute_athena_query')
    @patch('lambdas.stox_agent.lambda_function.generate_sql')
    def test_lambda_handler_success(self, mock_generate_sql, mock_execute_athena, mock_summarize):
        """Test successful agent execution"""
        mock_generate_sql.return_value = "SELECT * FROM stox.prices LIMIT 10"
        mock_execute_athena.return_value = (['date', 'close'], [['2024-01-15', '100.0']])
        mock_summarize.return_value = "AAPL closed at $100 on 2024-01-15"
        
        event = {
            'body': json.dumps({'question': 'Show me AAPL price'})
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['question'] == 'Show me AAPL price'
        assert body['sql'] == "SELECT * FROM stox.prices LIMIT 10"
        assert len(body['rows']) == 1
        assert body['answer'] == "AAPL closed at $100 on 2024-01-15"
    
    def test_lambda_handler_missing_question(self):
        """Test handling of missing question"""
        event = {'body': json.dumps({})}
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'error' in body
    
    @patch('lambdas.stox_agent.lambda_function.get_bedrock_client')
    def test_generate_sql_success(self, mock_get_bedrock):
        """Test SQL generation from natural language"""
        mock_response = MagicMock()
        mock_response['body'].read.return_value = json.dumps({
            'completion': 'Here is the SQL: <SQL>SELECT * FROM stox.prices WHERE ticker=\'AAPL\' LIMIT 10</SQL>'
        }).encode()
        mock_bedrock = MagicMock()
        mock_bedrock.invoke_model.return_value = mock_response
        mock_get_bedrock.return_value = mock_bedrock
        
        result = generate_sql('Show me AAPL data')
        
        assert result == "SELECT * FROM stox.prices WHERE ticker='AAPL' LIMIT 10"
    
    @patch('lambdas.stox_agent.lambda_function.get_bedrock_client')
    def test_generate_sql_no_sql_tags(self, mock_get_bedrock):
        """Test handling when no SQL tags are found"""
        mock_response = MagicMock()
        mock_response['body'].read.return_value = json.dumps({
            'completion': 'I cannot generate SQL for this question.'
        }).encode()
        mock_bedrock = MagicMock()
        mock_bedrock.invoke_model.return_value = mock_response
        mock_get_bedrock.return_value = mock_bedrock
        
        with pytest.raises(Exception, match="No SQL found in response"):
            generate_sql('Invalid question')
    
    @patch.dict('os.environ', {
        'ATHENA_DB': 'stox',
        'ATHENA_OUTPUT': 's3://test-bucket/'
    })
    @patch('lambdas.stox_agent.lambda_function.get_athena_client')
    def test_execute_athena_query_success(self, mock_get_athena):
        """Test successful Athena query execution"""
        # Mock start query execution
        mock_athena = MagicMock()
        mock_athena.start_query_execution.return_value = {
            'QueryExecutionId': 'test-query-id'
        }
        
        # Mock get query execution (success)
        mock_athena.get_query_execution.return_value = {
            'QueryExecution': {
                'Status': {'State': 'SUCCEEDED'}
            }
        }
        
        # Mock get query results
        mock_athena.get_query_results.return_value = {
            'ResultSet': {
                'ResultSetMetadata': {
                    'ColumnInfo': [
                        {'Name': 'date'},
                        {'Name': 'close'}
                    ]
                },
                'Rows': [
                    {'Data': [{'VarCharValue': 'date'}, {'VarCharValue': 'close'}]},  # Header
                    {'Data': [{'VarCharValue': '2024-01-15'}, {'VarCharValue': '100.0'}]}
                ]
            }
        }
        mock_get_athena.return_value = mock_athena
        
        columns, rows = execute_athena_query("SELECT * FROM stox.prices LIMIT 1")
        
        assert columns == ['date', 'close']
        assert rows == [['2024-01-15', '100.0']]
    
    @patch.dict('os.environ', {
        'ATHENA_DB': 'stox',
        'ATHENA_OUTPUT': 's3://test-bucket/'
    })
    @patch('lambdas.stox_agent.lambda_function.get_athena_client')
    def test_execute_athena_query_failure(self, mock_get_athena):
        """Test Athena query failure handling"""
        mock_athena = MagicMock()
        mock_athena.start_query_execution.return_value = {
            'QueryExecutionId': 'test-query-id'
        }
        
        mock_athena.get_query_execution.return_value = {
            'QueryExecution': {
                'Status': {
                    'State': 'FAILED',
                    'StateChangeReason': 'Syntax error'
                }
            }
        }
        mock_get_athena.return_value = mock_athena
        
        with pytest.raises(Exception, match="Athena query failed"):
            execute_athena_query("INVALID SQL")
    
    @patch('lambdas.stox_agent.lambda_function.get_bedrock_client')
    def test_summarize_results(self, mock_get_bedrock):
        """Test result summarization"""
        mock_response = MagicMock()
        mock_response['body'].read.return_value = json.dumps({
            'completion': 'The data shows AAPL closed at $100 on 2024-01-15. This represents a typical trading day.'
        }).encode()
        mock_bedrock = MagicMock()
        mock_bedrock.invoke_model.return_value = mock_response
        mock_get_bedrock.return_value = mock_bedrock
        
        result = summarize_results(
            'Show me AAPL price',
            ['date', 'close'],
            [['2024-01-15', '100.0']]
        )
        
        assert 'AAPL closed at $100' in result
    
    def test_summarize_results_empty(self):
        """Test summarization with no data"""
        result = summarize_results('Test question', [], [])
        
        assert result == "No data found for the given criteria."
