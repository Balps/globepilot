"""
WSGI entry point for GlobePiloT Flask application
Use this for production deployment with gunicorn, uWSGI, etc.
"""
import os
from app import app
from config import config

# Get configuration environment
config_name = os.environ.get('FLASK_ENV', 'production')
app.config.from_object(config[config_name])

# Initialize app with production config if needed
if config_name == 'production':
    config[config_name].init_app(app)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000))) 