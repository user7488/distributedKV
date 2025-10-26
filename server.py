import socket
import json
import logging
import threading
from kv_store import DistributedKVStore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class KVStoreServer:
    def __init__(self, host: str = '0.0.0.0', port: int = 5555):
        self.host = host
        self.port = port
        self.store = DistributedKVStore()
        self.server_socket = None
        self.running = False
        logger.info(f"KVStoreServer initialized on {host}:{port}")

    def handle_client(self, client_socket: socket.socket, addr):
        logger.info(f"Client connected from {addr}")
        
        try:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                try:
                    request = json.loads(data.decode('utf-8'))
                    logger.info(f"Request from {addr}: {request.get('operation')}")
                    
                    response = self.process_request(request)
                    
                    client_socket.sendall(json.dumps(response).encode('utf-8'))
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from {addr}: {e}")
                    error_response = {'success': False, 'error': 'Invalid JSON'}
                    client_socket.sendall(json.dumps(error_response).encode('utf-8'))
                    
        except Exception as e:
            logger.error(f"Error handling client {addr}: {e}")
        finally:
            client_socket.close()
            logger.info(f"Client disconnected: {addr}")

    def process_request(self, request: dict) -> dict:
        operation = request.get('operation')
        
        try:
            if operation == 'get':
                value = self.store.get(request['key'])
                return {'success': True, 'value': value}
            
            elif operation == 'set':
                success = self.store.set(request['key'], request['value'])
                return {'success': success}
            
            elif operation == 'delete':
                success = self.store.delete(request['key'])
                return {'success': success}
            
            elif operation == 'acquire_lock':
                success = self.store.acquire_lock(
                    request['key'],
                    request['owner'],
                    request.get('lease_duration', 30.0)
                )
                return {'success': success}
            
            elif operation == 'release_lock':
                success = self.store.release_lock(request['key'], request['owner'])
                return {'success': success}
            
            elif operation == 'renew_lease':
                success = self.store.renew_lease(
                    request['key'],
                    request['owner'],
                    request.get('lease_duration', 30.0)
                )
                return {'success': success}
            
            elif operation == 'is_locked':
                locked = self.store.is_locked(request['key'])
                return {'success': True, 'locked': locked}
            
            elif operation == 'get_lock_info':
                info = self.store.get_lock_info(request['key'])
                return {'success': True, 'lock_info': info}
            
            elif operation == 'cleanup_expired_locks':
                count = self.store.cleanup_expired_locks()
                return {'success': True, 'cleaned': count}
            
            else:
                return {'success': False, 'error': f'Unknown operation: {operation}'}
                
        except KeyError as e:
            return {'success': False, 'error': f'Missing parameter: {e}'}
        except Exception as e:
            logger.error(f"Error processing {operation}: {e}")
            return {'success': False, 'error': str(e)}

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        logger.info(f"Server listening on {self.host}:{self.port}")
        
        try:
            while self.running:
                client_socket, addr = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, addr)
                )
                client_thread.daemon = True
                client_thread.start()
        except KeyboardInterrupt:
            logger.info("Server shutting down...")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("Server stopped")


if __name__ == "__main__":
    server = KVStoreServer(host='0.0.0.0', port=5555)
    server.start()
