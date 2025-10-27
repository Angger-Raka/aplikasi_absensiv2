#!/bin/bash
# Shell script untuk menjalankan Aplikasi Absensi di macOS/Linux
# Double-click atau jalankan: ./AplikasiAbsensi.sh

echo "========================================"
echo "   APLIKASI ABSENSI - STARTING..."
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "ERROR: Python tidak terinstall!"
        echo "Silakan install Python terlebih dahulu"
        read -p "Tekan Enter untuk keluar..."
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo "ERROR: File app.py tidak ditemukan!"
    echo "Pastikan file ini berada di folder yang sama dengan app.py"
    read -p "Tekan Enter untuk keluar..."
    exit 1
fi

# Run the launcher
echo "Memulai aplikasi..."
$PYTHON_CMD run_aplikasi.py

# Check exit status
if [ $? -ne 0 ]; then
    echo
    echo "Aplikasi berhenti dengan error."
    read -p "Tekan Enter untuk keluar..."
fi

echo
echo "Aplikasi selesai."
