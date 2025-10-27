import sqlite3
import time
import gc

def check_database_status(db_path="absensi.db"):
    """Mengecek status database dan koneksi"""
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        
        # Check WAL mode
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        
        # Check if database is locked
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("ROLLBACK")
        
        conn.close()
        
        return {
            'status': 'OK',
            'table_count': table_count,
            'journal_mode': journal_mode,
            'locked': False
        }
        
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e).lower():
            return {
                'status': 'LOCKED',
                'error': str(e),
                'locked': True
            }
        else:
            return {
                'status': 'ERROR',
                'error': str(e),
                'locked': False
            }
    except Exception as e:
        return {
            'status': 'ERROR',
            'error': str(e),
            'locked': False
        }

def force_unlock_database(db_path="absensi.db"):
    """Force unlock database jika terkunci"""
    try:
        # Close all connections first
        gc.collect()
        
        # Try to connect and force unlock
        conn = sqlite3.connect(db_path, timeout=1.0)
        conn.execute("PRAGMA journal_mode=DELETE")  # Switch to DELETE mode temporarily
        conn.execute("PRAGMA journal_mode=WAL")     # Switch back to WAL
        conn.close()
        
        return True
    except Exception as e:
        print(f"Failed to force unlock: {e}")
        return False

def diagnose_database_lock(db_path="absensi.db"):
    """Diagnosa lengkap masalah database lock"""
    print(f"=== Database Diagnosis: {db_path} ===")
    
    # Check file existence
    import os
    if not os.path.exists(db_path):
        print("❌ Database file tidak ditemukan!")
        return
    
    print(f"✅ Database file exists: {os.path.getsize(db_path)} bytes")
    
    # Check status
    status = check_database_status(db_path)
    print(f"📊 Status: {status['status']}")
    
    if status['locked']:
        print("🔒 Database TERKUNCI!")
        print(f"   Error: {status.get('error', 'Unknown')}")
        
        print("\n🔧 Mencoba force unlock...")
        if force_unlock_database(db_path):
            print("✅ Force unlock berhasil!")
            
            # Check again
            new_status = check_database_status(db_path)
            print(f"📊 Status setelah unlock: {new_status['status']}")
        else:
            print("❌ Force unlock gagal!")
            
    else:
        print("✅ Database tidak terkunci")
        print(f"   Tables: {status.get('table_count', 0)}")
        print(f"   Journal mode: {status.get('journal_mode', 'unknown')}")

if __name__ == "__main__":
    # Test the functions
    diagnose_database_lock()
