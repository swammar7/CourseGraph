"""
Pytest configuration and shared fixtures for CourseGraph tests.
"""

import sys
import os
import pytest

# Make sure the app module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app as flask_app


@pytest.fixture
def app():
    """Create the Flask application for testing."""
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
    })
    yield flask_app


@pytest.fixture
def client(app):
    """A Flask test client for sending requests."""
    return app.test_client()
