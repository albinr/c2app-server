# tests/test_server.py

import unittest
from quart import Quart
from quart.testing import QuartClient
from unittest.mock import patch, AsyncMock
from server import create_app
from config import Config

class TestServer(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        """Set up the app for testing."""
        self.app = create_app()
        self.client = self.app.test_client()

    async def test_app_creation(self):
        """Test if the app is created correctly."""
        self.assertIsInstance(self.app, Quart, "App is not an instance of Quart.")
        self.assertEqual(self.app.config['DATABASE_URL'], Config.DATABASE_URL, "Database URI does not match the config.")

    async def test_home_route(self):
        """Test the home route to check if it returns a 200 status code."""
        async with self.client as client:
            response = await client.get("/")
            self.assertEqual(response.status_code, 200, "Home route did not return status 200.")

    async def test_routes_registration(self):
        """Test if routes are correctly registered in the app."""
        async with self.client as client:
            response = await client.get("/nonexistent")
            self.assertEqual(response.status_code, 404, "Nonexistent route did not return 404 as expected.")

    @patch("server.Config.async_engine")
    async def test_init_db(self, mock_async_engine):
        """Test if the database init function runs properly."""
        mock_conn = AsyncMock()
        mock_async_engine.begin.return_value.__aenter__.return_value = mock_conn

        async with self.app.app_context():
            await self.app.before_serving_funcs[0]()
            mock_conn.run_sync.assert_called_once()

    async def test_before_serving(self):
        """Test if the init_db function is registered as a before_serving function."""
        self.assertEqual(len(self.app.before_serving_funcs), 1, "There should be exactly one before_serving function registered.")

if __name__ == '__main__':
    unittest.main()
