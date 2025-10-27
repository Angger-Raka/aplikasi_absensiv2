# 📋 Panduan Deployment Aplikasi Absensi

## 🎯 Untuk HRD - Cara Menjalankan Aplikasi

### Windows
1. **Double-click** file `AplikasiAbsensi.bat`
2. Tunggu aplikasi loading (akan install dependencies otomatis jika diperlukan)
3. Aplikasi akan terbuka secara otomatis

### macOS/Linux
1. **Double-click** file `AplikasiAbsensi.sh` atau
2. Buka Terminal dan jalankan: `./AplikasiAbsensi.sh`
3. Tunggu aplikasi loading
4. Aplikasi akan terbuka secara otomatis

## 📁 File yang Diperlukan

Pastikan folder deployment berisi file-file berikut:
```
AplikasiAbsensi_Deployment/
├── app.py                    # File utama aplikasi
├── database.py               # Database manager
├── run_aplikasi.py           # Launcher script
├── AplikasiAbsensi.bat       # Windows launcher
├── AplikasiAbsensi.sh        # macOS/Linux launcher
├── requirements.txt          # Dependencies list
├── absensi.db               # Database (akan dibuat otomatis)
└── PANDUAN_DEPLOYMENT.md    # File ini
```

## 🔧 Instalasi untuk Tim IT

### 1. Persiapan Environment
```bash
# Clone atau copy semua file aplikasi
# Pastikan Python 3.8+ terinstall

# Install dependencies
pip install -r requirements.txt
```

### 2. Test Aplikasi
```bash
# Test manual
python app.py

# Test via launcher
python run_aplikasi.py
```

### 3. Deployment ke Komputer HRD
1. Copy seluruh folder ke komputer HRD
2. Pastikan Python terinstall (minimal 3.8)
3. Jalankan launcher sesuai OS

## 🚀 Fitur Aplikasi

### 1. Input Absensi
- Upload file Excel absensi harian
- Edit data absensi secara manual
- Tambah pelanggaran dengan rentang waktu dan keterangan
- Validasi data sebelum menyimpan

### 2. Manajemen Shift
- **CRUD Shift**: Buat, Edit, Hapus shift
- **Assignment**: Assign karyawan ke shift tertentu
- **Pengaturan Fleksibel**: 
  - Senin-Jumat: Jam kerja reguler
  - Sabtu: Jam kerja khusus
  - Minggu: Hanya hitung durasi kerja

### 3. Generate Laporan
- Pilih karyawan dan periode
- Laporan otomatis menggunakan shift karyawan
- Export ke Excel dengan format lengkap
- Format waktu: "8 jam 30 menit" (user-friendly)

## 🛠️ Troubleshooting

### Aplikasi tidak bisa dibuka
**Windows:**
```cmd
# Buka Command Prompt dan jalankan:
cd "path\to\aplikasi"
python run_aplikasi.py
```

**macOS/Linux:**
```bash
# Buka Terminal dan jalankan:
cd /path/to/aplikasi
python3 run_aplikasi.py
```

### Error "Python tidak ditemukan"
1. **Windows**: Install Python dari https://python.org
   - Centang "Add Python to PATH" saat install
2. **macOS**: Install via Homebrew: `brew install python3`
3. **Linux**: `sudo apt install python3 python3-pip`

### Error "Module tidak ditemukan"
```bash
# Install dependencies manual:
pip install PySide6 pandas openpyxl xlrd
```

### Database error
1. Tutup aplikasi
2. Backup file `absensi.db` (jika ada)
3. Hapus `absensi.db` untuk reset database
4. Jalankan aplikasi lagi (database baru akan dibuat)

### File Excel tidak bisa diimport
1. Pastikan file dalam format `.xlsx` atau `.xls`
2. Tutup file Excel sebelum import
3. Periksa struktur data sesuai template

## 📞 Support

Jika ada masalah yang tidak bisa diselesaikan:
1. Screenshot error message
2. Hubungi tim IT dengan informasi:
   - OS yang digunakan (Windows/macOS/Linux)
   - Error message lengkap
   - Langkah yang dilakukan sebelum error

## 🔄 Update Aplikasi

Untuk update aplikasi:
1. Backup database: copy file `absensi.db`
2. Replace semua file aplikasi dengan versi baru
3. Restore database: copy kembali `absensi.db`
4. Test aplikasi

## 📊 Format Data Excel

### Template Import Absensi
File Excel harus memiliki kolom:
- **Tanggal**: Format YYYY-MM-DD
- **Nama**: Nama karyawan
- **Jam Masuk**: Format HH:MM
- **Jam Keluar**: Format HH:MM
- **Jam Masuk Lembur**: Format HH:MM (opsional)
- **Jam Keluar Lembur**: Format HH:MM (opsional)

### Export Laporan
Laporan yang diexport akan berisi:
- Data absensi lengkap
- Perhitungan jam kerja, lembur, overtime
- Detail pelanggaran
- Peraturan shift yang digunakan
- Summary total

---

**Aplikasi Absensi v1.0**  
*Dibuat dengan Python & PySide6*  
*Support: Tim IT*
