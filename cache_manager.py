#!/usr/bin/env python3
"""
GlobePiloT Cache Manager
Handles caching for travel planning results and performance optimization
"""

import os
import json
import hashlib
import pickle
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Intelligent caching system for travel planning results"""
    
    def __init__(self, cache_dir='cache', default_ttl=3600):
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        self.cache_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different cache types
        (self.cache_dir / 'results').mkdir(exist_ok=True)
        (self.cache_dir / 'api_responses').mkdir(exist_ok=True)
        (self.cache_dir / 'templates').mkdir(exist_ok=True)
        
        logger.info(f"Cache manager initialized with directory: {self.cache_dir}")
    
    def generate_cache_key(self, data):
        """Generate a unique cache key from data"""
        if isinstance(data, dict):
            # Sort dict keys for consistent hashing
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    def get_cache_path(self, cache_type, key):
        """Get the file path for a cache entry"""
        return self.cache_dir / cache_type / f"{key}.cache"
    
    def set(self, cache_type, key, data, ttl=None):
        """Store data in cache with TTL"""
        try:
            ttl = ttl or self.default_ttl
            cache_data = {
                'data': data,
                'created': time.time(),
                'ttl': ttl,
                'expires': time.time() + ttl
            }
            
            cache_path = self.get_cache_path(cache_type, key)
            
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            logger.debug(f"Cached {cache_type}/{key} with TTL {ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache {cache_type}/{key}: {e}")
            return False
    
    def get(self, cache_type, key):
        """Retrieve data from cache if valid"""
        try:
            cache_path = self.get_cache_path(cache_type, key)
            
            if not cache_path.exists():
                return None
            
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Check if cache has expired
            if time.time() > cache_data['expires']:
                self.delete(cache_type, key)
                logger.debug(f"Cache {cache_type}/{key} expired")
                return None
            
            logger.debug(f"Cache hit for {cache_type}/{key}")
            return cache_data['data']
            
        except Exception as e:
            logger.error(f"Failed to retrieve cache {cache_type}/{key}: {e}")
            return None
    
    def delete(self, cache_type, key):
        """Delete a specific cache entry"""
        try:
            cache_path = self.get_cache_path(cache_type, key)
            if cache_path.exists():
                cache_path.unlink()
                logger.debug(f"Deleted cache {cache_type}/{key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache {cache_type}/{key}: {e}")
            return False
    
    def cache_travel_results(self, request_params, results):
        """Cache travel planning results"""
        key = self.generate_cache_key(request_params)
        # Cache for 1 hour by default
        return self.set('results', key, results, ttl=3600)
    
    def get_cached_travel_results(self, request_params):
        """Get cached travel planning results"""
        key = self.generate_cache_key(request_params)
        return self.get('results', key)
    
    def cache_api_response(self, endpoint, params, response):
        """Cache API responses for faster repeated requests"""
        cache_key = self.generate_cache_key({'endpoint': endpoint, 'params': params})
        # Cache API responses for 30 minutes
        return self.set('api_responses', cache_key, response, ttl=1800)
    
    def get_cached_api_response(self, endpoint, params):
        """Get cached API response"""
        cache_key = self.generate_cache_key({'endpoint': endpoint, 'params': params})
        return self.get('api_responses', cache_key)
    
    def cleanup_expired(self):
        """Clean up expired cache entries"""
        cleaned = 0
        
        for cache_type in ['results', 'api_responses', 'templates']:
            cache_dir = self.cache_dir / cache_type
            if not cache_dir.exists():
                continue
                
            for cache_file in cache_dir.glob('*.cache'):
                try:
                    with open(cache_file, 'rb') as f:
                        cache_data = pickle.load(f)
                    
                    if time.time() > cache_data['expires']:
                        cache_file.unlink()
                        cleaned += 1
                        
                except Exception as e:
                    logger.warning(f"Error checking cache file {cache_file}: {e}")
                    # Remove corrupted cache files
                    cache_file.unlink()
                    cleaned += 1
        
        logger.info(f"Cleaned up {cleaned} expired cache entries")
        return cleaned
    
    def get_cache_stats(self):
        """Get cache usage statistics"""
        stats = {
            'total_files': 0,
            'total_size': 0,
            'by_type': {}
        }
        
        for cache_type in ['results', 'api_responses', 'templates']:
            cache_dir = self.cache_dir / cache_type
            if not cache_dir.exists():
                continue
            
            files = list(cache_dir.glob('*.cache'))
            size = sum(f.stat().st_size for f in files)
            
            stats['by_type'][cache_type] = {
                'files': len(files),
                'size': size
            }
            
            stats['total_files'] += len(files)
            stats['total_size'] += size
        
        return stats
    
    def clear_all(self):
        """Clear all cache entries"""
        try:
            import shutil
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(exist_ok=True)
            (self.cache_dir / 'results').mkdir(exist_ok=True)
            (self.cache_dir / 'api_responses').mkdir(exist_ok=True)
            (self.cache_dir / 'templates').mkdir(exist_ok=True)
            logger.info("Cleared all cache entries")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

# Global cache manager instance
cache_manager = CacheManager()

def cache_decorator(cache_type, ttl=None, key_func=None):
    """Decorator for caching function results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_manager.generate_cache_key({
                    'func': func.__name__,
                    'args': args,
                    'kwargs': kwargs
                })
            
            # Try to get from cache
            result = cache_manager.get(cache_type, cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_type, cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator 