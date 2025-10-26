import socket
import json
import logging
from typing import Any, Optional, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class KVStoreClient:
    def __init__(self, host: str = 'localhost', port: int = 5555):
        self.host = host
        self.port = port
        logger.info(f"KVStoreClient initialized for {host}:{port}")

    def _send_request(self, request: dict) -> dict:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.host, self.port))
                
                request_data = json.dumps(request).encode('utf-8')
                sock.sendall(request_data)
                
                response_data = sock.recv(4096)
                response = json.loads(response_data.decode('utf-8'))
                
                return response
                
        except ConnectionRefusedError:
            logger.error(f"Connection refused to {self.host}:{self.port}")
            return {'success': False, 'error': 'Connection refused'}
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return {'success': False, 'error': str(e)}

    def get(self, key: str) -> Optional[Any]:
        request = {'operation': 'get', 'key': key}
        response = self._send_request(request)
        
        if response.get('success'):
            logger.info(f"GET key='{key}' value={response.get('value')}")
            return response.get('value')
        else:
            logger.error(f"GET failed: {response.get('error')}")
            return None

    def set(self, key: str, value: Any) -> bool:
        request = {'operation': 'set', 'key': key, 'value': value}
        response = self._send_request(request)
        
        success = response.get('success', False)
        if success:
            logger.info(f"SET key='{key}' value={value}")
        else:
            logger.error(f"SET failed: {response.get('error')}")
        
        return success

    def delete(self, key: str) -> bool:
        request = {'operation': 'delete', 'key': key}
        response = self._send_request(request)
        
        success = response.get('success', False)
        if success:
            logger.info(f"DELETE key='{key}'")
        else:
            logger.error(f"DELETE failed: {response.get('error')}")
        
        return success

    def acquire_lock(self, key: str, owner: str, lease_duration: float = 30.0) -> bool:
        request = {
            'operation': 'acquire_lock',
            'key': key,
            'owner': owner,
            'lease_duration': lease_duration
        }
        response = self._send_request(request)
        
        success = response.get('success', False)
        if success:
            logger.info(f"LOCK ACQUIRED key='{key}' owner='{owner}' duration={lease_duration}s")
        else:
            logger.warning(f"LOCK FAILED key='{key}' owner='{owner}'")
        
        return success

    def release_lock(self, key: str, owner: str) -> bool:
        request = {
            'operation': 'release_lock',
            'key': key,
            'owner': owner
        }
        response = self._send_request(request)
        
        success = response.get('success', False)
        if success:
            logger.info(f"LOCK RELEASED key='{key}' owner='{owner}'")
        else:
            logger.warning(f"UNLOCK FAILED key='{key}' owner='{owner}'")
        
        return success

    def renew_lease(self, key: str, owner: str, lease_duration: float = 30.0) -> bool:
        request = {
            'operation': 'renew_lease',
            'key': key,
            'owner': owner,
            'lease_duration': lease_duration
        }
        response = self._send_request(request)
        
        success = response.get('success', False)
        if success:
            logger.info(f"LEASE RENEWED key='{key}' owner='{owner}'")
        else:
            logger.warning(f"RENEW FAILED key='{key}' owner='{owner}'")
        
        return success

    def is_locked(self, key: str) -> bool:
        request = {'operation': 'is_locked', 'key': key}
        response = self._send_request(request)
        
        if response.get('success'):
            return response.get('locked', False)
        return False

    def get_lock_info(self, key: str) -> Optional[Dict[str, Any]]:
        request = {'operation': 'get_lock_info', 'key': key}
        response = self._send_request(request)
        
        if response.get('success'):
            return response.get('lock_info')
        return None

    def cleanup_expired_locks(self) -> int:
        request = {'operation': 'cleanup_expired_locks'}
        response = self._send_request(request)
        
        if response.get('success'):
            count = response.get('cleaned', 0)
            logger.info(f"CLEANUP removed {count} expired locks")
            return count
        return 0
