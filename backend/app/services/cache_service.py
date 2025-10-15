from app import redis_client
import json
import pickle
from functools import wraps

class CacheService:
    @staticmethod
    def get(key):
        try:
            value = redis_client.get(key)
            if value:
                return pickle.loads(value)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    @staticmethod
    def set(key, value, expire=3600):
        try:
            redis_client.setex(key, expire, pickle.dumps(value))
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    @staticmethod
    def delete(key):
        try:
            redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    @staticmethod
    def delete_pattern(pattern):
        try:
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
            return True
        except Exception as e:
            print(f"Cache delete pattern error: {e}")
            return False

def cache_response(expire=300, key_prefix="cache"):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{f.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_result = CacheService.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            CacheService.set(cache_key, result, expire)
            
            return result
        return decorated_function
    return decorator