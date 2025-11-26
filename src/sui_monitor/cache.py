"""
Cache management for SUI Monitor using DiskCache
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
import diskcache

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages transaction cache using DiskCache"""

    def __init__(self, cache_config: Dict):
        self.cache_dir = cache_config.get("cache_directory", "./cache")
        self.max_transactions = cache_config.get("max_transactions_per_protocol", 10)
        self.ttl_hours = cache_config.get("cache_ttl_hours", 24)

        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)

        # Initialize cache
        self.cache = diskcache.Cache(self.cache_dir)

    def get_cached_transactions(self, protocol_name: str) -> List[Dict]:
        """Retrieve cached transactions for a protocol"""
        cache_key = f"transactions_{protocol_name}"
        cached_data = self.cache.get(cache_key, [])
        return cached_data if cached_data else []

    def save_transactions(self, protocol_name: str, transactions: List[Dict]):
        """Save transactions to cache"""
        cache_key = f"transactions_{protocol_name}"
        # Keep only the last N transactions
        limited_transactions = transactions[:self.max_transactions]
        self.cache.set(cache_key, limited_transactions, expire=self.ttl_hours * 3600)

    def get_last_check_time(self, protocol_name: str) -> Optional[datetime]:
        """Retrieve timestamp of last check"""
        cache_key = f"last_check_{protocol_name}"
        timestamp = self.cache.get(cache_key)
        return datetime.fromisoformat(timestamp) if timestamp else None

    def save_last_check_time(self, protocol_name: str, timestamp: datetime):
        """Save timestamp of last check"""
        cache_key = f"last_check_{protocol_name}"
        self.cache.set(cache_key, timestamp.isoformat(), expire=self.ttl_hours * 3600)

    # Account monitoring cache methods
    def get_cached_packages(self, account_address: str) -> List[Dict]:
        """Retrieve cached packages for an account"""
        cache_key = f"packages_{account_address}"
        cached_data = self.cache.get(cache_key, [])
        return cached_data if cached_data else []

    def save_packages(self, account_address: str, packages: List[Dict]):
        """Save packages to cache"""
        cache_key = f"packages_{account_address}"
        self.cache.set(cache_key, packages, expire=self.ttl_hours * 3600)

    def get_last_package(self, account_address: str) -> Optional[Dict]:
        """Get the last reported package for an account"""
        cache_key = f"last_package_{account_address}"
        return self.cache.get(cache_key)

    def save_last_package(self, account_address: str, package: Dict):
        """Save the last reported package"""
        cache_key = f"last_package_{account_address}"
        self.cache.set(cache_key, package, expire=self.ttl_hours * 3600)

    def get_cached_objects(self, account_address: str) -> List[Dict]:
        """Retrieve cached objects created by an account"""
        cache_key = f"objects_{account_address}"
        cached_data = self.cache.get(cache_key, [])
        return cached_data if cached_data else []

    def save_objects(self, account_address: str, objects: List[Dict]):
        """Save objects to cache"""
        cache_key = f"objects_{account_address}"
        self.cache.set(cache_key, objects, expire=self.ttl_hours * 3600)

    def get_last_check_time_account(self, account_address: str) -> Optional[datetime]:
        """Retrieve timestamp of last check for account"""
        cache_key = f"last_check_account_{account_address}"
        timestamp = self.cache.get(cache_key)
        return datetime.fromisoformat(timestamp) if timestamp else None

    def save_last_check_time_account(self, account_address: str, timestamp: datetime):
        """Save timestamp of last check for account"""
        cache_key = f"last_check_account_{account_address}"
        self.cache.set(cache_key, timestamp.isoformat(), expire=self.ttl_hours * 3600)

    def close(self):
        """Close the cache"""
        self.cache.close()

