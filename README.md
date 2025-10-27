# Aplikasi Absensi Desktop

Aplikasi desktop untuk mengelola data absensi karyawan dengan fitur import Excel, edit data, dan generate laporan.

## Fitur Utama

### Tab 1: Input Absensi Harian
- **Import Excel**: Import file log absensi dari mesin absensi (format .xls/.xlsx)
- **Edit Data**: Edit jam masuk, keluar, lembur secara manual di tabel
- **Tambah Pelanggaran**: Tambah pelanggaran dengan rentang waktu dan keterangan
- **Save Database**: Simpan data absensi ke database SQLite lokal
- **Load by Date**: Muat data absensi berdasarkan tanggal yang dipilih

### Tab 2: Generate Laporan
- **Pengaturan Shift**: Konfigurasi jam kerja, lembur, overtime, toleransi keterlambatan
- **Mode Overtime**: Pilih perhitungan per menit atau per jam (≥60 menit)
- **Laporan Karyawan**: Generate laporan per karyawan dengan periode tertentu
- **Summary**: Ringkasan total jam kerja, lembur, overtime, keterlambatan

## Instalasi

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Jalankan Aplikasi**:
```bash
python app.py
```

## Struktur Database

Aplikasi menggunakan SQLite dengan 4 tabel utama:

- **employees**: Data karyawan
- **attendance**: Data absensi harian
- **violations**: Data pelanggaran
- **shift_settings**: Pengaturan shift kerja

## Cara Penggunaan

### 1. Import Data Absensi
1. Pilih tanggal di Tab "Input Absensi Harian"
2. Klik "Import Excel" dan pilih file log absensi
3. Data akan ditampilkan di tabel dan dapat diedit
4. Klik "Save to Database" untuk menyimpan

### 2. Edit Data Manual
- Klik cell di kolom jam untuk mengedit
- Kolom yang dapat diedit: Jam Masuk Kerja, Jam Keluar Kerja, Jam Masuk Lembur, Jam Keluar Lembur
- Perubahan otomatis tersimpan saat pindah cell

### 3. Tambah Pelanggaran
1. Pastikan ada data absensi untuk tanggal yang dipilih
2. Klik "Tambah Pelanggaran"
3. Pilih karyawan, isi rentang waktu dan keterangan
4. Klik OK untuk menyimpan

### 4. Generate Laporan
1. Buka Tab "Generate Laporan"
2. Atur pengaturan shift di panel kiri
3. Pilih karyawan dan periode di panel kanan
4. Klik "Generate Laporan" untuk melihat hasil

## Format File Excel

File Excel harus memiliki format standar dari mesin absensi dengan struktur:
- Baris dengan "Work No" dan "Name" untuk identifikasi karyawan
- Baris berikutnya berisi data jam (dipisah dengan newline)
- Urutan jam: Masuk Kerja, Keluar Kerja, Masuk Lembur, Keluar Lembur, Anomali...

## Logika Perhitungan

### Overtime
- **Per Menit**: Setiap menit setelah batas overtime dihitung
- **Per Jam**: Hanya dihitung jika ≥60 menit, dibulatkan ke jam
- **Gap Lembur**: Jika ada gap antara jam keluar kerja dan jam masuk lembur, dihitung sebagai overtime

### Keterlambatan
- Dihitung dari selisih jam masuk aktual dengan jam masuk yang dijadwalkan
- Ada toleransi keterlambatan yang dapat dikonfigurasi

## Teknologi

- **Frontend**: PySide6 (Qt6)
- **Database**: SQLite
- **Data Processing**: Pandas
- **File Support**: Excel (.xls, .xlsx) via openpyxl dan xlrd

## Troubleshooting

### Error Import Excel
- Pastikan file Excel tidak sedang dibuka di aplikasi lain
- Pastikan format file sesuai dengan yang diharapkan
- Install ulang dependencies jika ada error pandas/openpyxl

### Database Error
- File database `absensi.db` akan dibuat otomatis di folder aplikasi
- Jika ada error database, hapus file `absensi.db` untuk reset

### UI Issues
- Pastikan menggunakan Python 3.8+ dengan PySide6
- Coba jalankan dengan `python -m app` jika ada import error