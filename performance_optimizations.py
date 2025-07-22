#!/usr/bin/env python3
"""
GlobePiloT Performance Optimization Module
Provides middleware and utilities for improved Flask application performance
"""

import time
import gzip
import io
from flask import Flask, request, current_app, g
from functools import wraps
import logging
from cache_manager import cache_manager

logger = logging.getLogger(__name__)

class PerformanceMiddleware:
    """Middleware for performance optimizations"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_appcontext(self.cleanup)
        
        # Add custom headers for performance
        @app.after_request
        def add_performance_headers(response):
            # Cache control for static assets
            if request.endpoint == 'static' or '/static/' in request.path:
                response.cache_control.max_age = 31536000  # 1 year
                response.cache_control.public = True
                
                # Add version-based etag for cache busting
                if hasattr(g, 'asset_version'):
                    response.set_etag(g.asset_version)
            
            # Security headers
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # Performance hints
            if request.endpoint in ['index', 'results']:
                response.headers['Link'] = (
                    '</static/css/bundle.min.css>; rel=preload; as=style, '
                    '</static/js/bundle.min.js>; rel=preload; as=script'
                )
            
            return response
        
        logger.info("Performance middleware initialized")
    
    def before_request(self):
        """Execute before each request"""
        g.start_time = time.time()
        
        # Check for cached responses
        if request.method == 'GET' and not request.args.get('no_cache'):
            # Create safe cache key using hash
            cache_data = {'path': request.path, 'query': request.query_string.decode()}
            cache_key = cache_manager.generate_cache_key(cache_data)
            cached_response = cache_manager.get('api_responses', cache_key)
            
            if cached_response:
                logger.debug(f"Serving cached response for {request.path}")
                return cached_response
    
    def after_request(self, response):
        """Execute after each request"""
        # Add timing header
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
        
        # Cache GET responses that are successful (but not compressed ones)
        if (request.method == 'GET' and 
            response.status_code == 200 and
            'text/html' in response.content_type and
            not request.args.get('no_cache') and
            not response.headers.get('Content-Encoding')):  # Don't cache compressed responses
            
            # Create safe cache key using hash
            cache_data = {'path': request.path, 'query': request.query_string.decode()}
            cache_key = cache_manager.generate_cache_key(cache_data)
            try:
                # Cache for 5 minutes for HTML responses
                response_data = response.get_data(as_text=True)
                cache_manager.set('api_responses', cache_key, response_data, ttl=300)
            except UnicodeDecodeError:
                # Skip caching if we can't decode the response as text
                logger.debug(f"Skipping cache for {cache_key} - binary response")
        
        return response
    
    def cleanup(self, error):
        """Cleanup after request"""
        pass

def gzip_middleware(app):
    """Add gzip compression middleware"""
    
    @app.after_request
    def compress_response(response):
        # Only compress if client accepts gzip
        if 'gzip' not in request.headers.get('Accept-Encoding', '').lower():
            return response
        
        # Only compress certain content types
        if not response.content_type.startswith(('text/', 'application/json', 'application/javascript')):
            return response
        
        # Skip if already compressed
        if response.headers.get('Content-Encoding'):
            return response
        
        try:
            # Try to get response data - will fail for direct passthrough responses
            response_data = response.get_data()
            
            # Skip if response is too small
            if len(response_data) < 500:
                return response
            
            # Compress the response
            gzip_buffer = io.BytesIO()
            with gzip.GzipFile(fileobj=gzip_buffer, mode='wb') as gzip_file:
                gzip_file.write(response_data)
            
            response.set_data(gzip_buffer.getvalue())
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Content-Length'] = len(response.get_data())
            
        except RuntimeError as e:
            # Handle direct passthrough responses (static files)
            if "direct passthrough mode" in str(e):
                logger.debug(f"Skipping compression for direct passthrough response: {request.path}")
                return response
            else:
                # Re-raise other RuntimeErrors
                raise
        
        return response

def async_task_decorator(timeout=300):
    """Decorator for handling long-running tasks asynchronously"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import threading
            
            # Create a result container
            result_container = {'result': None, 'error': None, 'completed': False}
            
            def run_task():
                try:
                    result_container['result'] = func(*args, **kwargs)
                except Exception as e:
                    result_container['error'] = str(e)
                finally:
                    result_container['completed'] = True
            
            # Start the task in a separate thread
            thread = threading.Thread(target=run_task)
            thread.daemon = True
            thread.start()
            
            # Wait for completion or timeout
            thread.join(timeout)
            
            if not result_container['completed']:
                logger.warning(f"Task {func.__name__} timed out after {timeout}s")
                return {'error': 'Task timed out', 'timeout': True}
            
            if result_container['error']:
                logger.error(f"Task {func.__name__} failed: {result_container['error']}")
                return {'error': result_container['error']}
            
            return result_container['result']
        
        return wrapper
    return decorator

def lazy_loading_decorator(template_name):
    """Decorator for lazy loading template sections"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if this is a lazy load request
            if request.args.get('lazy_load'):
                section = request.args.get('section')
                
                # Get the full data
                data = func(*args, **kwargs)
                
                # Return only the requested section
                if section and section in data:
                    return data[section]
                
                return data
            
            # Normal request - return full data
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def optimize_db_queries():
    """Optimization utilities for database queries"""
    # This would be expanded when adding a database
    pass

def setup_performance_monitoring(app):
    """Setup performance monitoring and logging"""
    
    @app.before_request
    def log_request_info():
        logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
    
    @app.after_request
    def log_response_info(response):
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            logger.info(f"Response: {response.status_code} in {duration:.3f}s")
        return response
    
    # Periodic cache cleanup
    import threading
    import time
    
    def periodic_cleanup():
        while True:
            time.sleep(3600)  # Run every hour
            try:
                cleaned = cache_manager.cleanup_expired()
                logger.info(f"Periodic cleanup: removed {cleaned} expired cache entries")
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    cleanup_thread = threading.Thread(target=periodic_cleanup)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    logger.info("Performance monitoring setup complete")

def configure_static_file_serving(app):
    """Configure optimized static file serving"""
    
    @app.route('/static/<path:filename>')
    def optimized_static(filename):
        """Serve optimized static files with proper caching"""
        from flask import send_from_directory, abort
        import os
        
        static_folder = app.static_folder
        
        # Security check
        if '..' in filename or filename.startswith('/'):
            abort(404)
        
        # Try to serve bundled version in production
        if not app.debug:
            if filename.endswith('.css') and not filename.startswith('bundle'):
                # Try to serve from bundle
                manifest_path = os.path.join(static_folder, 'manifest.json')
                if os.path.exists(manifest_path):
                    import json
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                    
                    # Look for bundled version
                    for asset_path in manifest.get('assets', {}):
                        if asset_path.startswith('css/bundle') and asset_path.endswith('.min.css'):
                            return send_from_directory(
                                static_folder, 
                                asset_path,
                                max_age=31536000,  # 1 year cache
                                conditional=True
                            )
            
            elif filename.endswith('.js') and not filename.startswith('bundle'):
                # Try to serve bundled JS
                manifest_path = os.path.join(static_folder, 'manifest.json')
                if os.path.exists(manifest_path):
                    import json
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                    
                    for asset_path in manifest.get('assets', {}):
                        if asset_path.startswith('js/bundle') and asset_path.endswith('.min.js'):
                            return send_from_directory(
                                static_folder,
                                asset_path,
                                max_age=31536000,
                                conditional=True
                            )
        
        # Fallback to original file
        return send_from_directory(
            static_folder,
            filename,
            max_age=31536000 if not app.debug else 0,
            conditional=True
        )

def initialize_performance_optimizations(app):
    """Initialize all performance optimizations"""
    
    # Setup gzip compression first (runs last in after_request chain)
    gzip_middleware(app)
    
    # Add performance middleware second (runs before compression)
    PerformanceMiddleware(app)
    
    # Configure static file serving
    configure_static_file_serving(app)
    
    # Setup monitoring
    setup_performance_monitoring(app)
    
    # Configure caching headers
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year
    
    logger.info("All performance optimizations initialized")
    
    return app 