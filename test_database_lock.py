#!/usr/bin/env python3
"""
Script untuk test dan simulasi database lock
"""

import sqlite3
import time
import threading
from database_utils import check_database_status, force_unlock_database, diagnose_database_lock

def simulate_database_lock(db_path="absensi.db", duration=10):
    """Simulasi database lock dengan menahan transaksi"""
    print(f"🔒 Memulai simulasi database lock selama {duration} detik...")
    
    def lock_database():
        try:
            conn = sqlite3.connect(db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # Start exclusive transaction (ini akan mengunci database)
            cursor.execute("BEGIN EXCLUSIVE")
            print("🔒 Database dikunci dengan EXCLUSIVE transaction")
            
            # Hold the lock for specified duration
            time.sleep(duration)
            
            # Rollback to release lock
            cursor.execute("ROLLBACK")
            conn.close()
            print("🔓 Database lock dilepas")
            
        except Exception as e:
            print(f"❌ Error dalam simulasi lock: {e}")
    
    # Run lock in separate thread
    lock_thread = threading.Thread(target=lock_database)
    lock_thread.daemon = True
    lock_thread.start()
    
    # Wait a bit for lock to take effect
    time.sleep(0.5)
    
    return lock_thread

def test_database_operations():
    """Test operasi database normal"""
    print("\n=== Testing Normal Database Operations ===")
    
    try:
        from database import DatabaseManager
        db = DatabaseManager()
        
        # Test basic operations
        print("✅ DatabaseManager initialized")
        
        # Test get employees
        employees = db.get_all_employees()
        print(f"✅ Retrieved {len(employees)} employees")
        
        # Test get shift settings
        settings = db.get_shift_settings()
        print(f"✅ Retrieved shift settings: {settings['name'] if settings else 'None'}")
        
        print("✅ All database operations successful")
        
    except Exception as e:
        print(f"❌ Database operation failed: {e}")

def test_database_lock_handling():
    """Test handling database lock"""
    print("\n=== Testing Database Lock Handling ===")
    
    # First check normal status
    print("1. Checking normal database status...")
    status = check_database_status()
    print(f"   Status: {status['status']}, Locked: {status.get('locked', False)}")
    
    # Simulate lock
    print("\n2. Simulating database lock...")
    lock_thread = simulate_database_lock(duration=5)
    
    # Test operations during lock
    print("\n3. Testing operations during lock...")
    time.sleep(1)  # Ensure lock is active
    
    status = check_database_status()
    print(f"   Status during lock: {status['status']}, Locked: {status.get('locked', False)}")
    
    if status.get('locked'):
        print("   🔒 Database is locked as expected")
        
        # Test force unlock
        print("\n4. Testing force unlock...")
        if force_unlock_database():
            print("   ✅ Force unlock successful")
            
            # Check status after unlock
            new_status = check_database_status()
            print(f"   Status after unlock: {new_status['status']}, Locked: {new_status.get('locked', False)}")
        else:
            print("   ❌ Force unlock failed")
    
    # Wait for simulation to complete
    lock_thread.join()
    print("\n5. Lock simulation completed")

def main():
    print("🧪 Database Lock Testing Suite")
    print("=" * 50)
    
    # Initial diagnosis
    diagnose_database_lock()
    
    # Test normal operations
    test_database_operations()
    
    # Test lock handling
    test_database_lock_handling()
    
    # Final diagnosis
    print("\n=== Final Database Status ===")
    diagnose_database_lock()

if __name__ == "__main__":
    main()
