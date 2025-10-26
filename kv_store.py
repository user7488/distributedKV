import logging
import threading
import time
from typing import Any, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class Lease:
    owner: str
    key: str
    acquired_at: float
    expires_at: float
    lease_duration: float


class DistributedKVStore:
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._locks: Dict[str, Lease] = {}
        self._lock = threading.RLock()
        logger.info("DistributedKVStore initialized")

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            value = self._store.get(key)
            logger.info(f"GET key='{key}' value={value}")
            return value

    def set(self, key: str, value: Any) -> bool:
        with self._lock:
            self._store[key] = value
            logger.info(f"SET key='{key}' value={value}")
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                logger.info(f"DELETE key='{key}' success")
                return True
            logger.warning(f"DELETE key='{key}' failed - key not found")
            return False

    def acquire_lock(self, key: str, owner: str, lease_duration: float = 30.0) -> bool:
        with self._lock:
            now = time.time()
            
            if key in self._locks:
                lease = self._locks[key]
                if now < lease.expires_at:
                    if lease.owner == owner:
                        logger.info(f"LOCK key='{key}' owner='{owner}' already held by same owner")
                        return True
                    logger.warning(f"LOCK key='{key}' owner='{owner}' failed - held by '{lease.owner}'")
                    return False
                else:
                    logger.info(f"LOCK key='{key}' lease expired, removing stale lock from '{lease.owner}'")
                    del self._locks[key]
            
            expires_at = now + lease_duration
            self._locks[key] = Lease(
                owner=owner,
                key=key,
                acquired_at=now,
                expires_at=expires_at,
                lease_duration=lease_duration
            )
            logger.info(f"LOCK ACQUIRED key='{key}' owner='{owner}' duration={lease_duration}s")
            return True

    def release_lock(self, key: str, owner: str) -> bool:
        with self._lock:
            if key not in self._locks:
                logger.warning(f"UNLOCK key='{key}' owner='{owner}' failed - no lock exists")
                return False
            
            lease = self._locks[key]
            if lease.owner != owner:
                logger.warning(f"UNLOCK key='{key}' owner='{owner}' failed - owned by '{lease.owner}'")
                return False
            
            del self._locks[key]
            logger.info(f"LOCK RELEASED key='{key}' owner='{owner}'")
            return True

    def renew_lease(self, key: str, owner: str, lease_duration: float = 30.0) -> bool:
        with self._lock:
            if key not in self._locks:
                logger.warning(f"RENEW LEASE key='{key}' owner='{owner}' failed - no lock exists")
                return False
            
            lease = self._locks[key]
            if lease.owner != owner:
                logger.warning(f"RENEW LEASE key='{key}' owner='{owner}' failed - owned by '{lease.owner}'")
                return False
            
            now = time.time()
            if now > lease.expires_at:
                logger.warning(f"RENEW LEASE key='{key}' owner='{owner}' failed - lease expired")
                return False
            
            lease.expires_at = now + lease_duration
            lease.lease_duration = lease_duration
            logger.info(f"LEASE RENEWED key='{key}' owner='{owner}' new_expiry={lease.expires_at}")
            return True

    def get_lock_info(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if key not in self._locks:
                return None
            
            lease = self._locks[key]
            now = time.time()
            
            if now > lease.expires_at:
                logger.info(f"LOCK INFO key='{key}' - lease expired, cleaning up")
                del self._locks[key]
                return None
            
            return {
                'owner': lease.owner,
                'acquired_at': lease.acquired_at,
                'expires_at': lease.expires_at,
                'time_remaining': lease.expires_at - now,
                'lease_duration': lease.lease_duration
            }

    def is_locked(self, key: str) -> bool:
        with self._lock:
            if key not in self._locks:
                return False
            
            lease = self._locks[key]
            now = time.time()
            
            if now > lease.expires_at:
                del self._locks[key]
                return False
            
            return True

    def cleanup_expired_locks(self) -> int:
        with self._lock:
            now = time.time()
            expired = [key for key, lease in self._locks.items() if now > lease.expires_at]
            
            for key in expired:
                logger.info(f"CLEANUP expired lock key='{key}' owner='{self._locks[key].owner}'")
                del self._locks[key]
            
            if expired:
                logger.info(f"CLEANUP removed {len(expired)} expired locks")
            
            return len(expired)
