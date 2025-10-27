import pandas as pd
import json

class ExcelProcessor:
    @staticmethod
    def process_excel_log(file_path):
        """
        Memproses file log absensi Excel (.xls atau .xlsx) yang memiliki format laporan
        untuk mengekstrak nama, empat stempel waktu pertama, dan anomali.
        """
        hasil_data = []
        
        try:
            # Baca file Excel, tanpa baris header
            # 'engine=None' akan otomatis memilih 'xlrd' untuk .xls dan 'openpyxl' untuk .xlsx
            df = pd.read_excel(file_path, header=None, engine=None)
            
        except FileNotFoundError:
            raise FileNotFoundError(f"File tidak ditemukan di '{file_path}'")
        except Exception as e:
            raise Exception(f"Terjadi error saat membaca file Excel: {e}")

        i = 0
        while i < len(df):
            try:
                row = df.iloc[i] # Ambil baris berdasarkan indeks integer
                
                # Cek apakah baris ini adalah baris info karyawan
                # pd.notna() penting untuk mengecek sel kosong (NaN) sebelum membandingkan string
                if (pd.notna(row[0]) and pd.notna(row[4]) and
                    str(row[0]).strip() == 'Work No' and str(row[4]).strip() == 'Name'):
                    
                    nama = str(row[6]).strip()
                    
                    # Inisialisasi data karyawan
                    data_karyawan = {
                        "Nama": nama,
                        "Jam Masuk": None,
                        "Jam Keluar": None,
                        "Jam Masuk Lembur": None,
                        "Jam Keluar Lembur": None,
                        "Jam Anomali": []
                    }
                    
                    # Cek baris berikutnya untuk data jam
                    if i + 1 < len(df):
                        next_row = df.iloc[i+1]
                        
                        # Cek apakah sel data jam (kolom 1) tidak kosong
                        if pd.notna(next_row[1]):
                            times_string = str(next_row[1])
                            
                            # Bersihkan dan pisahkan data jam
                            cleaned_times = [t.strip() for t in times_string.split('\n') if t.strip()]
                            
                            # Tetapkan 4 data jam pertama
                            if len(cleaned_times) > 0:
                                data_karyawan["Jam Masuk"] = cleaned_times[0]
                            if len(cleaned_times) > 1:
                                data_karyawan["Jam Keluar"] = cleaned_times[1]
                            if len(cleaned_times) > 2:
                                data_karyawan["Jam Masuk Lembur"] = cleaned_times[2]
                            if len(cleaned_times) > 3:
                                data_karyawan["Jam Keluar Lembur"] = cleaned_times[3]
                            
                            # Masukkan sisanya ke "Jam Anomali"
                            if len(cleaned_times) > 4:
                                data_karyawan["Jam Anomali"] = cleaned_times[4:]
                    
                    hasil_data.append(data_karyawan)
                    
                    # Loncat ke baris setelah data jam (i + 2)
                    i += 2
                else:
                    # Jika baris ini bukan baris info, lanjut ke baris berikutnya
                    i += 1
            except Exception as e:
                # Menangani error jika ada baris yang formatnya aneh
                # print(f"Skipping row {i} due to error: {e}")
                i += 1
                
        return hasil_data

# --- Eksekusi untuk testing ---
if __name__ == "__main__":
    # Ganti ini dengan nama file Excel ANDA yang sebenarnya
    # Pastikan file ini ada di folder yang sama dengan skrip Python Anda
    file_path = "Attendance log-anomali.xls" # Ganti .xls atau .xlsx sesuai file Anda

    processor = ExcelProcessor()
    data_absensi = processor.process_excel_log(file_path)

    # Print hasilnya sebagai "Array" (list of dictionaries)
    if data_absensi:
        print(json.dumps(data_absensi, indent=2))
    else:
        print("Tidak ada data yang berhasil diproses.")
