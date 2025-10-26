# High Level Overview

## System Architecture

The Distributed KV Store is a client-server system that provides distributed key-value storage with explicit locking and lease management across multiple machines.

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Client A   │         │  Client B   │         │  Client C   │
│ (Machine 1) │         │ (Machine 2) │         │ (Machine 3) │
└──────┬──────┘         └──────┬──────┘         └──────┬──────┘
       │                       │                       │
       │   TCP/JSON over       │                       │
       │   port 5555           │                       │
       └───────────────────────┼───────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │                     │
                    │   KV Store Server   │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │  KV Storage   │  │
                    │  └───────────────┘  │
                    │  ┌───────────────┐  │
                    │  │ Lock Manager  │  │
                    │  └───────────────┘  │
                    │                     │
                    └─────────────────────┘
```

## Core Components

### 1. KV Store (kv_store.py)

**Purpose**: Thread-safe in-memory storage with locking capabilities.

**Key Components**:
- `_store: Dict[str, Any]` - Main key-value storage
- `_locks: Dict[str, Lease]` - Active locks and leases
- `_lock: RLock` - Thread synchronization primitive

**Responsibilities**:
- Store and retrieve key-value pairs
- Manage lock acquisition and release
- Track lease expiration
- Enforce ownership rules

### 2. Server (server.py)

**Purpose**: Network layer exposing KV store to remote clients.

**Key Components**:
- TCP socket listener (port 5555)
- Request handler threads (one per client connection)
- JSON protocol parser
- Operation dispatcher

**Responsibilities**:
- Accept client connections
- Parse JSON requests
- Route operations to KV store
- Return JSON responses
- Handle concurrent clients

### 3. Client (client.py)

**Purpose**: Client library for accessing remote KV store.

**Key Components**:
- Socket connection manager
- JSON request builder
- Response parser
- API wrapper methods

**Responsibilities**:
- Connect to server
- Serialize operations to JSON
- Deserialize responses
- Provide clean API to applications

## Lock Mechanism

### Lease-Based Locking

The system implements **explicit distributed locks** with time-based leases:

```
┌──────────────────────────────────────────────────┐
│              Lock Lifecycle                      │
└──────────────────────────────────────────────────┘

1. ACQUIRE
   Client A: acquire_lock("resource", "client-A", 30s)
   → Lock granted with 30-second lease

2. WORK PHASE
   Client A performs operations on "resource"
   
3. RENEWAL (optional)
   Client A: renew_lease("resource", "client-A", 30s)
   → Lease extended for another 30 seconds

4. RELEASE
   Client A: release_lock("resource", "client-A")
   → Lock released, available to others

OR

4. EXPIRATION (if not released)
   After 30 seconds: lease expires automatically
   → Lock becomes available to others
```

### Lock Properties

- **Exclusive**: Only one owner per key at a time
- **Ownership**: Only the owner can release or renew
- **Time-Bounded**: Automatic expiration prevents deadlocks
- **Reentrant**: Same owner can re-acquire (no-op)

### Expiration Handling

Leases expire automatically using timestamps:

```python
now = time.time()
expires_at = now + lease_duration

# On subsequent operations:
if now > lease.expires_at:
    # Lease expired, lock is invalid
    del self._locks[key]
```

**Benefits**:
- No need for client to clean up after crash
- Prevents indefinite deadlocks
- Self-healing in failure scenarios

## Data Flow

### Example: Distributed Lock Acquisition

```
Client A (Machine 1)                 Server                Client B (Machine 2)
     │                                 │                          │
     │ acquire_lock("db", "A", 30s)    │                          │
     ├────────────────────────────────►│                          │
     │                                 │                          │
     │         {"success": true}       │                          │
     │◄────────────────────────────────┤                          │
     │                                 │                          │
     │                                 │  acquire_lock("db", "B") │
     │                                 │◄─────────────────────────┤
     │                                 │                          │
     │                                 │     {"success": false}   │
     │                                 ├─────────────────────────►│
     │                                 │                          │
     │  [Client A does work...]        │                          │
     │                                 │                          │
     │ release_lock("db", "A")         │                          │
     ├────────────────────────────────►│                          │
     │                                 │                          │
     │         {"success": true}       │                          │
     │◄────────────────────────────────┤                          │
     │                                 │                          │
     │                                 │  acquire_lock("db", "B") │
     │                                 │◄─────────────────────────┤
     │                                 │                          │
     │                                 │     {"success": true}    │
     │                                 ├─────────────────────────►│
```

## Threading Model

### Server-Side Concurrency

```
Main Thread: Accept connections
     │
     ├─► Client Thread 1 (handles Client A)
     │        └─► Acquires _lock, performs operation, releases _lock
     │
     ├─► Client Thread 2 (handles Client B)
     │        └─► Acquires _lock, performs operation, releases _lock
     │
     └─► Client Thread 3 (handles Client C)
              └─► Acquires _lock, performs operation, releases _lock
```

**Synchronization**: All operations on `_store` and `_locks` are protected by `RLock`.

### Client-Side

Each client operation creates a new TCP connection (stateless).

#ASSUMPTIONLLM: Connection-per-operation model is acceptable for current use case.  
#LLMTODO: Implement connection pooling for better performance.

## Protocol Specification

### Request Format

```json
{
  "operation": "acquire_lock|release_lock|renew_lease|get|set|delete|...",
  "key": "resource_name",
  "owner": "client_identifier",
  "value": <any JSON-serializable>,
  "lease_duration": 30.0
}
```

### Response Format

```json
{
  "success": true|false,
  "value": <any JSON-serializable>,
  "error": "error message if success=false",
  "locked": true|false,
  "lock_info": {
    "owner": "client_id",
    "acquired_at": 1234567890.123,
    "expires_at": 1234567920.123,
    "time_remaining": 29.5,
    "lease_duration": 30.0
  },
  "cleaned": 5
}
```

## Use Cases

### 1. Distributed Job Coordination

```python
# Multiple workers compete for jobs
if client.acquire_lock(f"job:{job_id}", owner=worker_id):
    try:
        process_job(job_id)
    finally:
        client.release_lock(f"job:{job_id}", owner=worker_id)
```

### 2. Leader Election

```python
# First to acquire becomes leader
if client.acquire_lock("leader", owner=node_id, lease_duration=10.0):
    while True:
        perform_leader_duties()
        client.renew_lease("leader", owner=node_id, lease_duration=10.0)
```

### 3. Resource Coordination

```python
# Ensure exclusive access to shared resource
if client.acquire_lock("database_migration", owner="migrator-1"):
    run_migrations()
    client.release_lock("database_migration", owner="migrator-1")
```

### 4. Configuration Management

```python
# Store and retrieve distributed configuration
client.set("config:database", {"host": "db.example.com", "port": 5432})
config = client.get("config:database")
```

## Design Decisions

### Why Explicit Locks?

✓ **Clarity**: Application explicitly requests locks  
✓ **Control**: Application decides lease duration  
✓ **Flexibility**: Can implement various patterns (leader election, job queue, etc.)  

vs. Implicit locking with optimistic concurrency control.

### Why Time-Based Leases?

✓ **Fault Tolerance**: Crashes don't leave locks held forever  
✓ **Simplicity**: No need for heartbeat protocol  
✓ **Self-Healing**: System recovers automatically  

#ASSUMPTIONLLM: Clock synchronization across machines is reasonable (NTP).

### Why In-Memory Storage?

✓ **Performance**: Fast reads and writes  
✓ **Simplicity**: No disk I/O complexity  

✗ **Limitation**: Data lost on server restart  
#LLMTODO: Add persistence layer.

### Why TCP Sockets?

✓ **Reliable**: Guaranteed delivery and ordering  
✓ **Simple**: Standard library support  
✓ **Universal**: Works across any network  

vs. HTTP (more overhead) or UDP (unreliable).

## Limitations & Future Work

See [TODO.md](TODO.md) for detailed list.

**Current Limitations**:
1. No data persistence
2. Single point of failure (no replication)
3. No authentication/encryption
4. Connection-per-operation (no pooling)
5. In-memory only (limited by RAM)

**Scalability Considerations**:
- Single-threaded lock contention on high load
- Network bandwidth for large values
- Memory limits for number of keys

## Monitoring & Operations

### Logging

All operations are logged with INFO level:
```
2024-01-01 12:00:00 - __main__ - INFO - LOCK ACQUIRED key='resource' owner='client-1' duration=30.0s
2024-01-01 12:00:05 - __main__ - INFO - SET key='data' value={'x': 1}
2024-01-01 12:00:30 - __main__ - INFO - LOCK RELEASED key='resource' owner='client-1'
```

### Health Checks

#LLMTODO: Implement health check endpoint for monitoring systems.

### Metrics

#LLMTODO: Add metrics for:
- Lock acquisition success/failure rate
- Lock hold duration
- Operation latency
- Active connections
- Keys/locks count
