import unittest
import json
import sys
import os

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../docker')))

from app import app

class TestSysEndpoint(unittest.TestCase):
    """Test cases for the /sys endpoint"""

    def setUp(self):
        """Set up test client"""
        self.app = app.test_client()
        self.app.testing = True

    def test_sys_endpoint_returns_200(self):
        """Test that the /sys endpoint returns a 200 status code"""
        response = self.app.get('/sys')
        self.assertEqual(response.status_code, 200)

    def test_sys_endpoint_returns_json(self):
        """Test that the /sys endpoint returns valid JSON"""
        response = self.app.get('/sys')
        try:
            json_data = json.loads(response.data)
            self.assertTrue(True)
        except ValueError:
            self.fail("Response is not valid JSON")

    def test_sys_endpoint_contains_required_fields(self):
        """Test that the /sys endpoint returns the required fields"""
        response = self.app.get('/sys')
        json_data = json.loads(response.data)
        
        # Check that all required sections are present
        self.assertIn('cpu', json_data)
        self.assertIn('memory', json_data)
        self.assertIn('network', json_data)
        self.assertIn('disk', json_data)
        self.assertIn('timestamp', json_data)
        
        # Check CPU section
        self.assertIn('cpu_count', json_data['cpu'])
        self.assertIn('cpu_percent', json_data['cpu'])
        self.assertIn('per_cpu_percent', json_data['cpu'])
        
        # Check memory section
        self.assertIn('total', json_data['memory'])
        self.assertIn('available', json_data['memory'])
        self.assertIn('percent', json_data['memory'])
        self.assertIn('used', json_data['memory'])
        self.assertIn('free', json_data['memory'])
        
        # Check network section
        self.assertIn('bytes_sent', json_data['network'])
        self.assertIn('bytes_recv', json_data['network'])
        self.assertIn('packets_sent', json_data['network'])
        self.assertIn('packets_recv', json_data['network'])
        
        # Check disk section
        self.assertIn('total', json_data['disk'])
        self.assertIn('used', json_data['disk'])
        self.assertIn('free', json_data['disk'])
        self.assertIn('percent', json_data['disk'])

if __name__ == '__main__':
    unittest.main()