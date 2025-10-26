from client import KVStoreClient
import time


def main():
    print("=== Distributed KV Store Network Client Demo ===\n")
    
    client = KVStoreClient(host='localhost', port=5555)
    
    print("--- Basic KV Operations ---")
    client.set("user:1", {"name": "Alice", "age": 30})
    print(f"Retrieved: {client.get('user:1')}")
    
    client.set("counter", 0)
    
    print("\n--- Distributed Lock Acquisition ---")
    key = "shared_resource"
    
    if client.acquire_lock(key, owner="machine-1", lease_duration=10.0):
        print(f"✓ Lock acquired on '{key}'")
        
        current = client.get(key) or 0
        client.set(key, current + 1)
        
        print("\n--- Renewing lease ---")
        if client.renew_lease(key, owner="machine-1", lease_duration=15.0):
            print("✓ Lease renewed")
        
        lock_info = client.get_lock_info(key)
        print(f"Lock info: {lock_info}")
        
        time.sleep(2)
        
        print("\n--- Releasing lock ---")
        if client.release_lock(key, owner="machine-1"):
            print("✓ Lock released")
    else:
        print("✗ Failed to acquire lock (already held by another client)")
    
    print(f"\nIs locked: {client.is_locked(key)}")
    
    print("\n--- Testing from different 'machine' identity ---")
    if client.acquire_lock("resource_2", owner="machine-2", lease_duration=5.0):
        print("✓ Machine-2 acquired lock on resource_2")
        client.release_lock("resource_2", owner="machine-2")
    
    print("\n=== Demo Complete ===")
    print("\nTo test from another machine:")
    print("1. Start server: python server.py")
    print("2. On another machine: python example_network.py")
    print("   (Update host in example_network.py to server's IP)")


if __name__ == "__main__":
    main()
