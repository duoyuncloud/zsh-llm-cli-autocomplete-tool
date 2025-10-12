import unittest
from unittest.mock import patch, MagicMock
from src.model_completer.client import OllamaClient

class TestOllamaClient(unittest.TestCase):
    
    @patch('requests.get')
    def test_is_server_available(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        client = OllamaClient()
        result = client.is_server_available()
        
        self.assertTrue(result)
        mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=2)
    
    @patch('requests.post')
    def test_generate_completion(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "git commit -m \"message\""}
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        result = client.generate_completion("git comm", "test-model")
        
        self.assertEqual(result, "git commit -m \"message\"")
        mock_post.assert_called_once()