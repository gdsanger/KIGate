"""
Redis Cache Service for KIGate Agent Execution

Implements cache-aside strategy with:
- SHA256 fingerprint-based cache keys
- Concurrency handling with locks
- Configurable TTL
- Cache hit/miss tracking
"""
import hashlib
import json
import time
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone

import redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

import config

logger = logging.getLogger(__name__)


class CacheService:
    """Service for managing Redis cache for agent executions"""
    
    _redis_client: Optional[redis.Redis] = None
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Initialize Redis connection"""
        if cls._initialized:
            return
        
        try:
            if not config.REDIS_ENABLED:
                logger.info("Redis cache is disabled via configuration")
                cls._initialized = True
                return
            
            cls._redis_client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                password=config.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            cls._redis_client.ping()
            logger.info(f"Redis cache initialized successfully at {config.REDIS_HOST}:{config.REDIS_PORT}")
            cls._initialized = True
            
        except (RedisConnectionError, RedisError) as e:
            logger.warning(f"Redis connection failed: {str(e)}. Cache will be disabled.")
            cls._redis_client = None
            cls._initialized = True
        except Exception as e:
            logger.error(f"Unexpected error initializing Redis: {str(e)}")
            cls._redis_client = None
            cls._initialized = True
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if Redis cache is available"""
        if not cls._initialized:
            cls.initialize()
        return cls._redis_client is not None
    
    @classmethod
    def _generate_cache_key(
        cls,
        agent_name: str,
        provider: str,
        model: str,
        user_id: str,
        message: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a unique cache key based on the request parameters
        
        Format: kigate:v1:agent-exec:{agent_name}:{provider}:{model}:u:{user_id}:h:{hash}
        """
        # Create canonical JSON representation for hashing
        cache_data = {
            "message": message,
            "parameters": parameters or {}
        }
        
        # Sort keys for consistent hashing
        canonical_json = json.dumps(cache_data, sort_keys=True, ensure_ascii=True)
        
        # Generate SHA256 hash
        hash_digest = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        
        # Build cache key
        cache_key = f"kigate:v1:agent-exec:{agent_name}:{provider}:{model}:u:{user_id}:h:{hash_digest}"
        
        return cache_key
    
    @classmethod
    def _get_lock_key(cls, cache_key: str) -> str:
        """Generate lock key for concurrency control"""
        return f"lock:{cache_key}"
    
    @classmethod
    async def get_cached_result(
        cls,
        agent_name: str,
        provider: str,
        model: str,
        user_id: str,
        message: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Retrieve cached result if available
        
        Returns:
            Tuple of (result, metadata) if cache hit, None if cache miss
        """
        if not cls.is_available():
            return None
        
        try:
            cache_key = cls._generate_cache_key(
                agent_name, provider, model, user_id, message, parameters
            )
            
            # Try to get from cache
            cached_data = cls._redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                result = data.get("result")
                metadata = data.get("metadata", {})
                
                # Get TTL
                ttl = cls._redis_client.ttl(cache_key)
                metadata["ttl"] = ttl if ttl > 0 else None
                
                logger.info(f"Cache HIT for key: {cache_key[:80]}...")
                return (result, metadata)
            
            logger.info(f"Cache MISS for key: {cache_key[:80]}...")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None
    
    @classmethod
    async def set_cached_result(
        cls,
        agent_name: str,
        provider: str,
        model: str,
        user_id: str,
        message: str,
        result: str,
        status: str,
        job_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store result in cache with TTL
        
        Args:
            ttl: Time to live in seconds. If None, uses default from config
        
        Returns:
            True if successfully cached, False otherwise
        """
        if not cls.is_available():
            return False
        
        try:
            cache_key = cls._generate_cache_key(
                agent_name, provider, model, user_id, message, parameters
            )
            
            # Determine TTL based on status
            if ttl is None:
                if status == "failed":
                    ttl = config.CACHE_ERROR_TTL
                else:
                    ttl = config.CACHE_DEFAULT_TTL
            
            # Prepare cache data
            cache_data = {
                "result": result,
                "status": status,
                "job_id": job_id,
                "metadata": {
                    "cached_at": datetime.now(timezone.utc).isoformat(),
                    "agent_name": agent_name,
                    "provider": provider,
                    "model": model
                }
            }
            
            # Store in cache with TTL
            cls._redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cache_data)
            )
            
            logger.info(f"Cached result for key: {cache_key[:80]}... (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error storing in cache: {str(e)}")
            return False
    
    @classmethod
    async def acquire_lock(cls, cache_key: str, timeout: int = 30) -> bool:
        """
        Acquire a lock for the cache key to prevent concurrent executions
        
        Args:
            cache_key: The cache key to lock
            timeout: Lock timeout in seconds
        
        Returns:
            True if lock acquired, False otherwise
        """
        if not cls.is_available():
            return False
        
        try:
            lock_key = cls._get_lock_key(cache_key)
            # Use SETNX (SET if Not eXists) with expiration
            acquired = cls._redis_client.set(
                lock_key, 
                "1", 
                nx=True,  # Only set if not exists
                ex=timeout  # Expire after timeout seconds
            )
            
            if acquired:
                logger.debug(f"Lock acquired for key: {cache_key[:80]}...")
            else:
                logger.debug(f"Lock already held for key: {cache_key[:80]}...")
            
            return bool(acquired)
            
        except Exception as e:
            logger.error(f"Error acquiring lock: {str(e)}")
            return False
    
    @classmethod
    async def release_lock(cls, cache_key: str) -> bool:
        """
        Release a lock for the cache key
        
        Args:
            cache_key: The cache key to unlock
        
        Returns:
            True if lock released, False otherwise
        """
        if not cls.is_available():
            return False
        
        try:
            lock_key = cls._get_lock_key(cache_key)
            cls._redis_client.delete(lock_key)
            logger.debug(f"Lock released for key: {cache_key[:80]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error releasing lock: {str(e)}")
            return False
    
    @classmethod
    async def wait_for_lock_release(cls, cache_key: str, max_wait: int = 60, check_interval: float = 0.5):
        """
        Wait for a lock to be released, checking periodically
        
        Args:
            cache_key: The cache key being locked
            max_wait: Maximum time to wait in seconds
            check_interval: How often to check in seconds
        """
        if not cls.is_available():
            return
        
        lock_key = cls._get_lock_key(cache_key)
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if not cls._redis_client.exists(lock_key):
                logger.debug(f"Lock released for key: {cache_key[:80]}...")
                return
            
            await asyncio.sleep(check_interval)
        
        logger.warning(f"Timeout waiting for lock release: {cache_key[:80]}...")
    
    @classmethod
    def clear_cache(cls, pattern: Optional[str] = None) -> int:
        """
        Clear cache entries matching pattern
        
        Args:
            pattern: Redis key pattern (e.g., "kigate:v1:agent-exec:*")
                    If None, clears all KIGate cache entries
        
        Returns:
            Number of keys deleted
        """
        if not cls.is_available():
            return 0
        
        try:
            if pattern is None:
                pattern = "kigate:v1:agent-exec:*"
            
            # Find all matching keys
            keys = list(cls._redis_client.scan_iter(match=pattern))
            
            if keys:
                deleted = cls._redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries matching pattern: {pattern}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return 0


# Import asyncio for wait_for_lock_release
import asyncio
