#!/usr/bin/env python3
"""
Script untuk membuat executable dari Aplikasi Absensi
"""

import os
import sys
import subprocess
import shutil

def create_executable():
    """Create executable using PyInstaller"""
    
    print("🚀 Membuat executable untuk Aplikasi Absensi...")
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",                    # Single executable file
        "--windowed",                   # No console window (GUI only)
        "--name=AplikasiAbsensi",       # Executable name
        "--icon=icon.ico",              # Icon (if exists)
        "--add-data=absensi.db:.",      # Include database
        "--hidden-import=openpyxl",     # Include openpyxl
        "--hidden-import=xlrd",         # Include xlrd
        "--hidden-import=pandas",       # Include pandas
        "--hidden-import=PySide6",      # Include PySide6
        "app.py"                        # Main script
    ]
    
    # Remove icon parameter if icon doesn't exist
    if not os.path.exists("icon.ico"):
        cmd.remove("--icon=icon.ico")
    
    try:
        # Run PyInstaller
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Executable berhasil dibuat!")
        
        # Show output location
        exe_path = os.path.join("dist", "AplikasiAbsensi.exe" if sys.platform == "win32" else "AplikasiAbsensi")
        print(f"📁 Lokasi executable: {exe_path}")
        
        # Create deployment folder
        deployment_folder = "AplikasiAbsensi_Deployment"
        if os.path.exists(deployment_folder):
            shutil.rmtree(deployment_folder)
        os.makedirs(deployment_folder)
        
        # Copy executable
        if os.path.exists(exe_path):
            shutil.copy2(exe_path, deployment_folder)
            print(f"✅ Executable disalin ke folder: {deployment_folder}")
        
        # Copy database if exists
        if os.path.exists("absensi.db"):
            shutil.copy2("absensi.db", deployment_folder)
            print("✅ Database disalin ke deployment folder")
        
        # Create README for deployment
        create_deployment_readme(deployment_folder)
        
        print(f"\n🎉 Deployment siap di folder: {deployment_folder}")
        print("📋 Folder berisi:")
        for item in os.listdir(deployment_folder):
            print(f"   - {item}")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error saat membuat executable: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False
    
    return True

def create_deployment_readme(folder):
    """Create README file for deployment"""
    readme_content = """# Aplikasi Absensi - Panduan Penggunaan

## Cara Menjalankan Aplikasi

1. **Double-click** file `AplikasiAbsensi` (atau `AplikasiAbsensi.exe` di Windows)
2. Aplikasi akan terbuka secara otomatis
3. Database `absensi.db` akan dibuat otomatis jika belum ada

## Fitur Aplikasi

### 1. Input Absensi
- Upload file Excel absensi harian
- Edit data absensi secara manual
- Tambah pelanggaran dengan rentang waktu dan keterangan
- Validasi data sebelum menyimpan

### 2. Manajemen Shift
- Buat shift baru dengan pengaturan khusus
- Edit shift yang sudah ada
- Hapus shift (jika tidak digunakan karyawan)
- Assign karyawan ke shift tertentu

### 3. Generate Laporan
- Pilih karyawan dan periode laporan
- Laporan otomatis menggunakan shift karyawan
- Export ke Excel dengan format lengkap
- Summary total jam kerja, lembur, overtime, keterlambatan

## Pengaturan Shift

### Senin - Jumat
- Jam kerja reguler
- Jam lembur
- Batas overtime
- Toleransi keterlambatan

### Sabtu
- Jam kerja khusus Sabtu
- Jam lembur khusus Sabtu
- Batas overtime berbeda

### Minggu
- Hanya hitung durasi kerja
- Tidak ada lembur/overtime

## Format Waktu

Aplikasi menampilkan waktu dalam format yang mudah dibaca:
- **Jam Kerja**: "8 jam 30 menit"
- **Jam Lembur**: "2 jam 15 menit"
- **Overtime**: "45 menit"
- **Keterlambatan**: "15 menit"

## Troubleshooting

### Aplikasi tidak bisa dibuka
1. Pastikan file `absensi.db` ada di folder yang sama
2. Coba jalankan sebagai Administrator (Windows)
3. Periksa antivirus tidak memblokir aplikasi

### Error saat import Excel
1. Pastikan file Excel dalam format .xlsx atau .xls
2. Periksa struktur data sesuai template
3. Tutup file Excel sebelum import

### Database error
1. Pastikan file `absensi.db` tidak sedang dibuka aplikasi lain
2. Backup database secara berkala
3. Jika rusak, hapus `absensi.db` untuk reset (data akan hilang)

## Kontak Support

Jika ada masalah atau pertanyaan, hubungi tim IT untuk bantuan teknis.

---
Aplikasi Absensi v1.0
Dibuat dengan Python & PySide6
"""
    
    readme_path = os.path.join(folder, "README.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("✅ README.txt dibuat untuk panduan pengguna")

if __name__ == "__main__":
    success = create_executable()
    if success:
        print("\n🎯 Executable siap untuk deployment!")
    else:
        print("\n❌ Gagal membuat executable")
        sys.exit(1)
