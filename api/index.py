"""
PolicySetu — Vercel Serverless Entry Point
=========================================
Exposes the Flask WSGI application instance for Vercel Serverless execution.
"""

import sys
import os

# Ensure root directory is on Python module search path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import create_app

# Instantiate Flask application in production mode
app = create_app(os.environ.get("FLASK_ENV", "production"))

# Export WSGI application callable for Vercel
handler = app
