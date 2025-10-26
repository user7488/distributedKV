# Distributed Key-Value Store with Locking

A Python-based distributed key-value store with explicit locking and lease management, designed for multi-machine coordination.

## Features

- **Key-Value Storage**: Standard get/set/delete operations with any JSON-serializable values
- **Distributed Locking**: Explicit lock acquisition with ownership enforcement
- **Lease Management**: Time-based leases with automatic expiration and renewal capabilities
- **Thread-Safe**: All operations protected with RLock for concurrent access
- **Network Protocol**: TCP socket-based client-server architecture for multi-machine deployment
- **Comprehensive Logging**: All operations logged for debugging and monitoring

## Architecture

- **Server** ([server.py](server.py)): Central KV store instance handling requests from multiple clients
- **Client** ([client.py](client.py)): Network client for remote access to the KV store
- **Core Store** ([kv_store.py](kv_store.py)): Thread-safe in-memory storage with lock management

## Usage

```python
from kv_store import DistributedKVStore

store = DistributedKVStore()

# Basic KV operations
store.set("key", "value")
value = store.get("key")
store.delete("key")

# Acquire lock with 30-second lease
if store.acquire_lock("resource", owner="client-1", lease_duration=30.0):
    # Do work with exclusive access
    store.set("resource", "new_value")
    
    # Renew lease if needed
    store.renew_lease("resource", owner="client-1", lease_duration=30.0)
    
    # Release when done
    store.release_lock("resource", owner="client-1")

# Check lock status
is_locked = store.is_locked("resource")
lock_info = store.get_lock_info("resource")

# Cleanup expired locks
store.cleanup_expired_locks()
```

## Running Examples

### Local (single machine)
```bash
python example.py
```

### Distributed (multiple machines)

**On the server machine:**
```bash
python server.py
```

**On client machine(s):**
```bash
# Update host in example_network.py or client.py to point to server IP
python example_network.py
```

**Or use the client directly:**
```python
from client import KVStoreClient

client = KVStoreClient(host='192.168.1.100', port=5555)
client.acquire_lock("my_resource", owner="client-1", lease_duration=30.0)
# ... do work ...
client.release_lock("my_resource", owner="client-1")
```

## API

### KV Operations
- `get(key)` → `Optional[Any]` - Retrieve value for a key
- `set(key, value)` → `bool` - Store value (any JSON-serializable type)
- `delete(key)` → `bool` - Remove key from store

### Lock Operations
- `acquire_lock(key, owner, lease_duration=30.0)` → `bool` - Acquire exclusive lock with lease
- `release_lock(key, owner)` → `bool` - Release lock (must be owner)
- `renew_lease(key, owner, lease_duration=30.0)` → `bool` - Extend lease before expiration
- `is_locked(key)` → `bool` - Check if key is currently locked
- `get_lock_info(key)` → `Optional[Dict]` - Get lease details (owner, expiry, time remaining)
- `cleanup_expired_locks()` → `int` - Remove expired leases and return count

## Network Protocol

Communication uses JSON over TCP sockets. Request format:
```json
{
  "operation": "acquire_lock",
  "key": "resource_name",
  "owner": "client_id",
  "lease_duration": 30.0
}
```

Response format:
```json
{
  "success": true,
  "value": null
}
```

## Files

- `kv_store.py` - Core storage and locking implementation
- `server.py` - TCP server exposing KV store over network
- `client.py` - Client library for remote access
- `example.py` - Local usage example
- `example_network.py` - Distributed usage example
- `README.md` - This file
- `TODO.md` - Future improvements and tasks
- `HighLevelOverview.md` - Architecture and design documentation

## Requirements

- Python 3.7+
- Standard library only (no external dependencies)

## Port Configuration

Default port: 5555 (configurable in server.py and client.py)
