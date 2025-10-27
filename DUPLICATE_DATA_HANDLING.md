# Duplicate Data Handling - Import dengan Tanggal yang Sama

## 🔄 Situasi: Data dengan Tanggal yang Sama

### **Skenario Umum:**
1. **HRD sudah input data** untuk tanggal 27 Oktober 2025
2. **Ada file Excel baru** untuk tanggal yang sama (misal: data tambahan, koreksi, atau file dari mesin lain)
3. **Aplikasi mendeteksi duplikasi** dan memberikan pilihan kepada user

---

## 🎯 Solusi: 3 Mode Penyimpanan

### **1. 🔴 Timpa Semua (Replace)**
- **Fungsi**: Hapus semua data lama, ganti dengan data baru
- **Kapan Digunakan**: 
  - File Excel baru adalah versi terbaru dan paling akurat
  - Data lama ada kesalahan dan perlu diganti total
  - Ingin "reset" data untuk tanggal tersebut

**Contoh:**
```
Data Lama: RAKA (08:00-17:00), NISA (07:30-16:30)
Data Baru: RAKA (08:07-16:13), HENDRI (08:50-18:08)
Hasil: RAKA (08:07-16:13), HENDRI (08:50-18:08)  ← NISA hilang
```

### **2. 🟡 Gabung/Update (Merge)**
- **Fungsi**: Update data yang ada, tambah data baru
- **Kapan Digunakan**: 
  - File Excel berisi update untuk karyawan tertentu
  - Ada karyawan baru yang perlu ditambahkan
  - Ingin mempertahankan data lama yang tidak ada di file baru

**Contoh:**
```
Data Lama: RAKA (08:00-17:00), NISA (07:30-16:30)
Data Baru: RAKA (08:07-16:13), HENDRI (08:50-18:08)
Hasil: RAKA (08:07-16:13), NISA (07:30-16:30), HENDRI (08:50-18:08)  ← Semua ada
```

### **3. 🟢 Tambah Baru Saja (Insert Only)**
- **Fungsi**: Hanya tambah karyawan yang belum ada
- **Kapan Digunakan**: 
  - File Excel berisi data karyawan baru saja
  - Tidak ingin mengubah data yang sudah ada
  - File dari mesin absensi tambahan/cabang

**Contoh:**
```
Data Lama: RAKA (08:00-17:00), NISA (07:30-16:30)
Data Baru: RAKA (08:07-16:13), HENDRI (08:50-18:08)
Hasil: RAKA (08:00-17:00), NISA (07:30-16:30), HENDRI (08:50-18:08)  ← RAKA tidak berubah
```

---

## 🖥️ User Interface

### **Dialog Konfirmasi:**
```
┌─────────────────────────────────────────────────┐
│                Data Sudah Ada                   │
├─────────────────────────────────────────────────┤
│ Data absensi untuk tanggal 2025-10-27 sudah ada!│
│                                                 │
│ Data yang ada: 15 karyawan (12 hadir, 3 tidak  │
│ hadir, 8 lembur)                                │
│ Data baru: 18 karyawan                          │
│                                                 │
│ Pilih cara penyimpanan:                         │
│                                                 │
│ [Timpa Semua] [Gabung/Update] [Tambah Baru Saja] [Batal] │
└─────────────────────────────────────────────────┘
```

### **Informasi yang Ditampilkan:**
- **Tanggal** yang bentrok
- **Jumlah karyawan** di data lama vs baru
- **Statistik** data lama (hadir, tidak hadir, lembur)
- **4 pilihan** dengan penjelasan yang jelas

---

## ⚙️ Technical Implementation

### **Database Method:**
```python
def save_attendance_data(self, date, attendance_list, mode='replace'):
    """
    mode options:
    - 'replace': DELETE existing + INSERT new
    - 'merge': INSERT OR REPLACE (update existing, add new)
    - 'insert_only': INSERT OR IGNORE (only add new)
    """
```

### **SQL Operations:**

#### **Replace Mode:**
```sql
-- 1. Delete existing data
DELETE FROM attendance WHERE date = '2025-10-27';

-- 2. Insert new data
INSERT INTO attendance (...) VALUES (...);
```

#### **Merge Mode:**
```sql
-- Insert or replace (update if exists, insert if new)
INSERT OR REPLACE INTO attendance (...) VALUES (...);
```

#### **Insert Only Mode:**
```sql
-- Insert only if not exists (ignore duplicates)
INSERT OR IGNORE INTO attendance (...) VALUES (...);
```

---

## 📊 Contoh Skenario Nyata

### **Skenario 1: File Koreksi**
**Situasi**: HRD sudah input data pagi, sore dapat file koreksi dari mesin absensi
**Solusi**: **Timpa Semua** - File dari mesin lebih akurat

### **Skenario 2: Data Tambahan**
**Situasi**: Data dari mesin utama sudah diinput, ada file dari mesin cabang
**Solusi**: **Gabung/Update** - Kombinasi data dari kedua mesin

### **Skenario 3: Karyawan Baru**
**Situasi**: Data harian sudah lengkap, ada file khusus karyawan baru/lembur
**Solusi**: **Tambah Baru Saja** - Jangan ubah data yang sudah ada

### **Skenario 4: Import Ulang**
**Situasi**: HRD tidak sengaja import file yang sama dua kali
**Solusi**: **Batal** - Tidak perlu import ulang

---

## 🔍 Monitoring & Feedback

### **Pesan Sukses yang Informatif:**
- ✅ "Data berhasil **ditimpa seluruhnya** ke database"
- ✅ "Data berhasil **digabung/diupdate** ke database" 
- ✅ "Data berhasil **ditambahkan (data baru saja)** ke database"
- ✅ "Data berhasil **disimpan** ke database" (untuk data baru)

### **Summary Information:**
- Jumlah karyawan sebelum dan sesudah
- Statistik kehadiran (hadir, tidak hadir, lembur)
- Mode penyimpanan yang dipilih

---

## 🛡️ Data Safety

### **Backup Otomatis:**
- Database menggunakan **WAL mode** - ada backup otomatis
- **Rollback** jika terjadi error saat penyimpanan
- **Transaction-based** - semua data tersimpan atau tidak sama sekali

### **Validasi:**
- Cek format data sebelum penyimpanan
- Validasi tanggal dan jam
- Error handling untuk data corrupt

### **Audit Trail:**
- Semua operasi tercatat dengan timestamp
- Bisa trace kapan data diubah
- History perubahan tersimpan

---

## 📋 Best Practices

### **Untuk HRD:**
1. **Selalu backup** sebelum import data besar
2. **Pilih mode yang tepat** sesuai situasi
3. **Cek hasil** setelah import di tab Generate Laporan
4. **Gunakan "Tambah Baru Saja"** jika ragu-ragu

### **Workflow yang Disarankan:**
```
1. Import file Excel → Muncul dialog duplikasi
2. Baca informasi dengan teliti
3. Pilih mode yang sesuai:
   - File baru lebih akurat → Timpa Semua
   - Ada data tambahan → Gabung/Update  
   - Hanya karyawan baru → Tambah Baru Saja
4. Cek hasil di Generate Laporan
5. Jika salah, bisa import ulang dengan mode berbeda
```

---

## 🎉 Keuntungan Fitur Ini

### **Fleksibilitas:**
- ✅ **3 pilihan** sesuai kebutuhan berbeda
- ✅ **Informasi lengkap** sebelum memutuskan
- ✅ **Bisa dibatalkan** jika ragu

### **Data Integrity:**
- ✅ **Tidak ada data hilang** tanpa konfirmasi
- ✅ **Rollback otomatis** jika error
- ✅ **Audit trail** untuk tracking

### **User Experience:**
- ✅ **Dialog informatif** dengan statistik
- ✅ **Pesan sukses** yang jelas
- ✅ **Default pilihan** yang aman (Gabung/Update)

**Aplikasi sekarang sudah handle semua skenario duplicate data dengan aman dan fleksibel!** 🚀
