# Database Troubleshooting Guide

## 🔒 Mengatasi "Database is Locked" Error

### **Penyebab Umum Database Lock:**
1. **Koneksi tidak ditutup dengan benar** - Aplikasi crash tanpa menutup koneksi
2. **Multiple connections** - Beberapa aplikasi mengakses database bersamaan  
3. **Long-running transactions** - Transaksi yang berjalan terlalu lama
4. **File system issues** - Masalah permission atau disk space

---

## 🛠️ Cara Mengecek Status Database

### **1. Menggunakan Aplikasi (Recommended)**
1. Buka aplikasi absensi
2. Di Tab "Input Absensi Harian", klik tombol **"Check DB Status"**
3. Akan muncul dialog dengan informasi:
   - ✅ **OK**: Database normal
   - 🔒 **LOCKED**: Database terkunci
   - ❌ **ERROR**: Ada masalah lain

### **2. Menggunakan Command Line**
```bash
# Masuk ke folder aplikasi
cd /path/to/aplikasi_absensiv2

# Jalankan diagnostic tool
python database_utils.py
```

### **3. Menggunakan Test Suite**
```bash
# Test lengkap database operations
python test_database_lock.py
```

---

## 🔧 Cara Mengatasi Database Lock

### **Method 1: Melalui Aplikasi (Paling Mudah)**

#### **Saat Save Data:**
1. Jika muncul error "database is locked" saat save
2. Aplikasi akan otomatis menanyakan: **"Apakah ingin mencoba force unlock?"**
3. Klik **"Yes"** untuk mencoba unlock otomatis
4. Aplikasi akan retry save setelah unlock berhasil

#### **Manual Check:**
1. Klik tombol **"Check DB Status"**
2. Jika database locked, klik **"Yes"** untuk force unlock
3. Database akan di-unlock otomatis

### **Method 2: Command Line**
```bash
# Diagnosis lengkap
python database_utils.py

# Jika locked, script akan otomatis mencoba force unlock
```

### **Method 3: Manual Reset (Last Resort)**
```bash
# Hapus database dan buat ulang
rm absensi.db
python app.py  # Database baru akan dibuat otomatis
```

---

## 🔍 Fitur Diagnostic yang Tersedia

### **1. Database Status Check**
- **Tables count**: Jumlah tabel dalam database
- **Journal mode**: Mode journaling (seharusnya WAL)
- **Lock status**: Apakah database terkunci atau tidak

### **2. Auto-Retry Mechanism**
- **3x retry** dengan exponential backoff
- **30 detik timeout** per koneksi
- **Automatic unlock** jika terdeteksi lock

### **3. Improved Error Handling**
- **User-friendly messages** untuk setiap jenis error
- **Auto-recovery options** dengan konfirmasi user
- **Detailed error logging** untuk debugging

---

## ⚙️ Konfigurasi Database yang Sudah Diperbaiki

### **Connection Settings:**
```python
# Timeout 30 detik (sebelumnya 20)
conn = sqlite3.connect(db_path, timeout=30.0)

# WAL mode untuk better concurrency
conn.execute("PRAGMA journal_mode=WAL")

# Performance optimizations
conn.execute("PRAGMA synchronous=NORMAL")
conn.execute("PRAGMA cache_size=10000")
conn.execute("PRAGMA temp_store=MEMORY")
```

### **Error Handling Pattern:**
```python
conn = None
try:
    conn = self.get_connection()
    # database operations
    conn.commit()
except Exception as e:
    if conn:
        conn.rollback()
    raise e
finally:
    if conn:
        conn.close()  # ALWAYS close connection
```

---

## 🚨 Troubleshooting Steps

### **Jika Masih Ada Database Lock:**

#### **Step 1: Check Process**
```bash
# Pastikan tidak ada instance aplikasi lain yang berjalan
ps aux | grep python
```

#### **Step 2: File Permissions**
```bash
# Check permission file database
ls -la absensi.db*
```

#### **Step 3: Disk Space**
```bash
# Check disk space
df -h .
```

#### **Step 4: Force Reset**
```bash
# Backup data (jika ada)
cp absensi.db absensi.db.backup

# Reset database
rm absensi.db absensi.db-wal absensi.db-shm

# Restart aplikasi
python app.py
```

---

## 📊 Monitoring Database Health

### **Regular Checks:**
1. **Setiap hari**: Klik "Check DB Status" sebelum mulai kerja
2. **Setelah import besar**: Check status setelah import file Excel besar
3. **Jika aplikasi crash**: Selalu check status setelah aplikasi crash

### **Performance Indicators:**
- ✅ **Journal mode: WAL** - Optimal
- ✅ **Status: OK** - Normal operation
- ✅ **Tables: 4** - All tables present
- ❌ **Locked: True** - Needs attention

---

## 🆘 Emergency Recovery

### **Jika Database Corrupt:**
```bash
# 1. Stop aplikasi
# 2. Backup current database
cp absensi.db absensi.db.corrupt

# 3. Try SQLite recovery
sqlite3 absensi.db ".recover" > recovered.sql
sqlite3 new_absensi.db < recovered.sql

# 4. Replace database
mv new_absensi.db absensi.db

# 5. Restart aplikasi
python app.py
```

### **Jika Kehilangan Data:**
1. Check file backup: `absensi.db.backup`
2. Check WAL files: `absensi.db-wal`
3. Re-import Excel files dari tanggal terakhir

---

## 📞 Support

Jika masih mengalami masalah database lock setelah mengikuti panduan ini:

1. **Jalankan diagnostic**: `python test_database_lock.py`
2. **Screenshot error message** yang muncul
3. **Check log files** untuk error details
4. **Coba method reset** sebagai solusi terakhir

**Remember**: Aplikasi sekarang sudah memiliki **auto-recovery mechanism**, jadi sebagian besar masalah database lock akan teratasi otomatis! 🎉
