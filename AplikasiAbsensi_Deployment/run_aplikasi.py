#!/usr/bin/env python3
"""
Launcher script untuk Aplikasi Absensi
Script ini akan menjalankan aplikasi dengan error handling yang baik
"""

import sys
import os
import subprocess
import tkinter as tk
from tkinter import messagebox

def check_dependencies():
    """Check if all required packages are installed"""
    required_packages = [
        'PySide6',
        'pandas', 
        'openpyxl',
        'xlrd'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_packages(packages):
    """Install missing packages"""
    try:
        for package in packages:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def show_error_dialog(title, message):
    """Show error dialog"""
    root = tk.Tk()
    root.withdraw()  # Hide main window
    messagebox.showerror(title, message)
    root.destroy()

def main():
    """Main launcher function"""
    print("🚀 Memulai Aplikasi Absensi...")
    
    # Check if app.py exists
    if not os.path.exists("app.py"):
        error_msg = "File app.py tidak ditemukan!\nPastikan Anda menjalankan script ini di folder yang benar."
        show_error_dialog("File Tidak Ditemukan", error_msg)
        return False
    
    # Check dependencies
    print("🔍 Memeriksa dependencies...")
    missing = check_dependencies()
    
    if missing:
        print(f"❌ Package yang hilang: {', '.join(missing)}")
        print("📦 Mencoba install package yang hilang...")
        
        if install_packages(missing):
            print("✅ Semua package berhasil diinstall!")
        else:
            error_msg = f"""Gagal menginstall package yang diperlukan: {', '.join(missing)}

Silakan install manual dengan command:
pip install {' '.join(missing)}

Atau hubungi tim IT untuk bantuan."""
            show_error_dialog("Error Dependencies", error_msg)
            return False
    
    # Try to run the application
    try:
        print("✅ Dependencies OK, menjalankan aplikasi...")
        
        # Import and run the app
        import app
        app.main()
        
    except Exception as e:
        error_msg = f"""Terjadi error saat menjalankan aplikasi:

{str(e)}

Silakan hubungi tim IT untuk bantuan."""
        show_error_dialog("Error Aplikasi", error_msg)
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            input("Tekan Enter untuk keluar...")
    except KeyboardInterrupt:
        print("\n👋 Aplikasi dihentikan oleh user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        input("Tekan Enter untuk keluar...")
