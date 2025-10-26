from kv_store import DistributedKVStore
import time
import threading


def worker_with_lock(store: DistributedKVStore, worker_id: str, key: str):
    print(f"\n[{worker_id}] Attempting to acquire lock for '{key}'...")
    
    if store.acquire_lock(key, owner=worker_id, lease_duration=5.0):
        print(f"[{worker_id}] Lock acquired! Working on protected resource...")
        
        current_val = store.get(key) or 0
        store.set(key, current_val + 1)
        
        time.sleep(2)
        
        print(f"[{worker_id}] Work complete. Releasing lock...")
        store.release_lock(key, owner=worker_id)
    else:
        print(f"[{worker_id}] Failed to acquire lock. Key is locked by another owner.")


def main():
    print("=== Distributed KV Store with Locking Demo ===\n")
    
    store = DistributedKVStore()
    
    print("\n--- Basic KV Operations ---")
    store.set("user:1", {"name": "Alice", "age": 30})
    print(f"Retrieved: {store.get('user:1')}")
    
    store.set("counter", 0)
    
    print("\n--- Lock Acquisition ---")
    key = "counter"
    
    success = store.acquire_lock(key, owner="client-1", lease_duration=10.0)
    print(f"Client-1 lock acquisition: {success}")
    
    lock_info = store.get_lock_info(key)
    print(f"Lock info: {lock_info}")
    
    print("\n--- Attempting duplicate lock from different owner ---")
    success = store.acquire_lock(key, owner="client-2", lease_duration=5.0)
    print(f"Client-2 lock acquisition (should fail): {success}")
    
    print("\n--- Renewing lease ---")
    renewed = store.renew_lease(key, owner="client-1", lease_duration=15.0)
    print(f"Lease renewal: {renewed}")
    
    print("\n--- Releasing lock ---")
    store.release_lock(key, owner="client-1")
    print(f"Is locked after release: {store.is_locked(key)}")
    
    print("\n--- Concurrent workers with locking ---")
    store.set("shared_counter", 0)
    
    threads = []
    for i in range(3):
        t = threading.Thread(target=worker_with_lock, args=(store, f"worker-{i}", "shared_counter"))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    print(f"\nFinal counter value: {store.get('shared_counter')}")
    
    print("\n--- Testing lease expiration ---")
    store.acquire_lock("temp_key", owner="temp-client", lease_duration=2.0)
    print(f"Lock acquired, is_locked: {store.is_locked('temp_key')}")
    
    print("Waiting 3 seconds for lease to expire...")
    time.sleep(3)
    
    print(f"After expiration, is_locked: {store.is_locked('temp_key')}")
    
    print("\n--- Cleanup test ---")
    store.acquire_lock("cleanup_test_1", owner="client-x", lease_duration=1.0)
    store.acquire_lock("cleanup_test_2", owner="client-y", lease_duration=1.0)
    time.sleep(1.5)
    
    cleaned = store.cleanup_expired_locks()
    print(f"Cleaned up {cleaned} expired locks")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()
