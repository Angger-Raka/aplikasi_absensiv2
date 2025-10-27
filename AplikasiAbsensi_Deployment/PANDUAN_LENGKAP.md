# 📋 APLIKASI ABSENSI - PANDUAN LENGKAP

## 🚀 CARA MENJALANKAN (UNTUK HRD)

### Windows
**Double-click** file `AplikasiAbsensi.bat`

### macOS/Linux  
**Double-click** file `AplikasiAbsensi.sh`

⏳ **Tunggu beberapa detik, aplikasi akan terbuka otomatis**

---

## 📱 FITUR APLIKASI

### 1. 📝 INPUT ABSENSI
- **Upload Excel**: Import file absensi harian (.xlsx/.xls)
- **Edit Manual**: Koreksi data jika ada yang salah/kurang
- **Tambah Pelanggaran**: Input waktu + keterangan (contoh: "12:00:30-13:00:45 Main HP")

### 2. ⚙️ KELOLA SHIFT
- **Buat Shift Baru**: Shift 1, Shift 2, dll dengan aturan berbeda
- **Edit Shift**: Ubah jam kerja, lembur, toleransi keterlambatan
- **Assign Karyawan**: Tentukan karyawan pakai shift mana

**Pengaturan Shift:**
- **Senin-Jumat**: Jam kerja reguler + lembur + overtime
- **Sabtu**: Jam kerja khusus (biasanya lebih pendek)
- **Minggu**: Hanya hitung durasi kerja (tanpa lembur/overtime)

### 3. 📊 BUAT LAPORAN
- **Pilih Karyawan**: Dari dropdown
- **Pilih Periode**: Tanggal mulai - selesai
- **Generate**: Otomatis pakai shift karyawan
- **Export Excel**: Laporan lengkap dengan peraturan shift

**Format Waktu**: "8 jam 30 menit" (mudah dibaca)

---

## 🔧 TROUBLESHOOTING

### ❌ Aplikasi tidak bisa dibuka
1. **Cek Python**: Pastikan Python terinstall
   - Windows: Download dari https://python.org
   - Centang "Add Python to PATH"
2. **Hubungi IT**: Jika masih error

### ❌ Error saat import Excel
1. **Tutup Excel**: File harus ditutup dulu sebelum import
2. **Format File**: Pastikan .xlsx atau .xls
3. **Struktur Data**: Cek kolom sesuai template

### ❌ Data hilang/rusak
1. **File Database**: `absensi.db` berisi semua data
2. **Backup**: Copy file `absensi.db` secara berkala
3. **Reset**: Hapus `absensi.db` untuk mulai fresh (data hilang!)

---

## 📁 TEMPLATE EXCEL IMPORT

File Excel harus punya kolom:
```
Tanggal          | Nama Karyawan | Jam Masuk | Jam Keluar | Jam Masuk Lembur | Jam Keluar Lembur
2024-10-27       | John Doe      | 08:00     | 16:00      | 16:00            | 18:00
```

**Format:**
- **Tanggal**: YYYY-MM-DD (2024-10-27)
- **Jam**: HH:MM (08:00, 16:30)
- **Lembur**: Opsional, kosongkan jika tidak ada

---

## 🎯 TIPS PENGGUNAAN

### Workflow Harian HRD:
1. **Pagi**: Download file absensi dari mesin
2. **Import**: Upload ke aplikasi
3. **Validasi**: Cek data, tambah pelanggaran jika perlu
4. **Simpan**: Data tersimpan otomatis

### Workflow Laporan:
1. **Pilih Karyawan**: Yang mau dilaporkan
2. **Set Periode**: Mingguan/bulanan
3. **Generate**: Lihat preview di aplikasi
4. **Export**: Simpan ke Excel untuk arsip

### Kelola Shift:
1. **Setup Awal**: Buat shift sesuai kebijakan perusahaan
2. **Assign**: Tentukan karyawan pakai shift mana
3. **Update**: Edit jika ada perubahan kebijakan

---

## 📞 BANTUAN

**Jika ada masalah, hubungi Tim IT dengan info:**
- Screenshot error message
- Langkah yang dilakukan sebelum error
- File yang sedang diproses (jika ada)

**File Penting (JANGAN DIHAPUS):**
- `absensi.db` - Database utama
- `app.py` - Program utama
- `AplikasiAbsensi.bat/.sh` - Launcher

---

## 🔄 UPDATE APLIKASI

1. **Backup**: Copy file `absensi.db`
2. **Replace**: Ganti semua file aplikasi dengan versi baru
3. **Restore**: Copy kembali file `absensi.db`
4. **Test**: Jalankan aplikasi untuk memastikan OK

---

**Aplikasi Absensi v1.0**  
*Dibuat dengan Python & PySide6*  
*Support: Tim IT*
