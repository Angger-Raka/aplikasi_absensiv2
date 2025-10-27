# Changelog - Aplikasi Absensi

## [Fixed] Database Lock Issue - 27 Oktober 2025

### Masalah yang Diperbaiki
- **Error "database is locked"** yang terjadi saat menggunakan aplikasi

### Perbaikan yang Dilakukan

#### 1. Improved Database Connection Management
- Menambahkan **timeout 20 detik** pada koneksi SQLite
- Mengaktifkan **WAL mode** (Write-Ahead Logging) untuk concurrency yang lebih baik
- Implementasi **proper connection handling** dengan try-catch-finally pattern

#### 2. Consistent Error Handling
Semua method database sekarang menggunakan pattern yang konsisten:
```python
def method_name(self):
    conn = None
    try:
        conn = self.get_connection()
        cursor = conn.cursor()
        # database operations
        conn.commit()
        return result
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()
```

#### 3. Methods yang Diperbaiki
- `add_or_get_employee()`
- `save_attendance_data()`
- `get_attendance_by_date()`
- `update_attendance_field()`
- `add_violation()`
- `get_violations_by_attendance()`
- `get_shift_settings()`
- `update_shift_settings()`
- `get_all_employees()`
- `get_attendance_by_employee_period()`
- `init_database()`

#### 4. Database Configuration Improvements
```python
def get_connection(self):
    conn = sqlite3.connect(self.db_path, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
    return conn
```

### Hasil
- ✅ Tidak ada lagi error "database is locked"
- ✅ Aplikasi berjalan stabil
- ✅ Koneksi database selalu ditutup dengan benar
- ✅ Error handling yang lebih robust
- ✅ Better performance dengan WAL mode

### Testing
Aplikasi telah ditest dan berjalan dengan baik tanpa error database lock.
