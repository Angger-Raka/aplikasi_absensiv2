import pandas as pd
import json
import os
import warnings

# Abaikan warning format Excel lama agar output bersih
warnings.filterwarnings("ignore")

# Suppress specific warnings untuk file Excel dengan OLE2 inconsistency
import sys
if not sys.warnoptions:
    warnings.simplefilter("ignore")
    
# Suppress xlrd warnings specifically
warnings.filterwarnings("ignore", category=UserWarning, module="xlrd")
warnings.filterwarnings("ignore", message=".*OLE2 inconsistency.*")
warnings.filterwarnings("ignore", message=".*file size.*not.*multiple of sector size.*")

class ExcelProcessor:
    @staticmethod
    def _extract_from_dataframe(df):
        """
        Helper function: Mencari data absensi dari DataFrame apapun (Excel/CSV/HTML)
        """
        results = []
        if df.empty:
            return results

        for i in range(len(df)):
            row = df.iloc[i]
            
            # Konversi baris jadi list string, bersihkan NaN, dan strip spasi
            # Gunakan .upper() untuk normalisasi pencarian
            row_str_list = [str(x).strip() if pd.notna(x) else "" for x in row.tolist()]
            row_str_upper = [x.upper() for x in row_str_list]
            
            # Cari kata kunci "NAME" (Case Insensitive)
            if "NAME" in row_str_upper:
                try:
                    # Ambil index kolom "Name"
                    name_index = row_str_upper.index("NAME")
                    
                    # Logika: Nama karyawan ada di 2 kolom sebelah kanannya
                    if name_index + 2 < len(row):
                        nama_karyawan = row.iloc[name_index + 2]
                    else:
                        nama_karyawan = "Unknown"
                    
                    # Validasi nama
                    if pd.isna(nama_karyawan) or str(nama_karyawan).strip() in ['', 'nan', 'None']:
                        continue
                    
                    # Ambil Data Jam di baris bawahnya (i + 1), kolom yang sama dengan kolom awal (biasanya 0)
                    # Note: Di Grid++Report, jam seringkali di kolom paling kiri (index 0), 
                    # tapi kita coba ambil dari kolom 0 dulu sebagai default.
                    if i + 1 < len(df):
                        raw_time_data = df.iloc[i+1, 0] 
                        
                        if pd.isna(raw_time_data):
                            jam_list = []
                        else:
                            raw_time_str = str(raw_time_data)
                            if not raw_time_str.strip():
                                jam_list = []
                            else:
                                jam_list = [
                                    t.strip().replace('.', ':') 
                                    for t in raw_time_str.splitlines() 
                                    if t.strip()
                                ]
                    else:
                        jam_list = []

                    # Mapping ke JSON
                    entry = {
                        "Nama": str(nama_karyawan).strip(),
                        "Jam Masuk": None,
                        "Jam Keluar": None,
                        "Jam Masuk Lembur": None,
                        "Jam Keluar Lembur": None,
                        "Jam Anomali": []
                    }

                    if len(jam_list) >= 1: entry["Jam Masuk"] = jam_list[0]
                    if len(jam_list) >= 2: entry["Jam Keluar"] = jam_list[1]
                    if len(jam_list) >= 3: entry["Jam Masuk Lembur"] = jam_list[2]
                    if len(jam_list) >= 4: entry["Jam Keluar Lembur"] = jam_list[3]
                    if len(jam_list) > 4:  entry["Jam Anomali"] = jam_list[4:]

                    results.append(entry)

                except Exception as e:
                    # print(f"Warning: Lewati baris {i} karena error logic: {e}")
                    continue
        return results

    @staticmethod
    def process_excel_log(file_path):
        """
        Fungsi Hybrid Ultra-Robust: 
        Mencoba segala cara (Excel All Sheets -> HTML -> CSV) untuk mendapatkan data.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"FATAL ERROR: File tidak ditemukan di lokasi: '{file_path}'")
        
        final_results = []
        
        # --- STRATEGI 1: BACA SEBAGAI EXCEL (SEMUA SHEET) ---
        # Ini menangani file .xls binary (OLE2) meskipun ada warning
        try:
            # sheet_name=None artinya baca SEMUA sheet menjadi dictionary
            all_sheets = pd.read_excel(file_path, header=None, sheet_name=None)
            for sheet_name, df in all_sheets.items():
                # print(f"Mencoba scan sheet: {sheet_name}...")
                sheet_results = ExcelProcessor._extract_from_dataframe(df)
                final_results.extend(sheet_results)
        except Exception as e:
            # print(f"Mode Excel gagal: {e}")
            pass
            
        # Jika Strategi 1 berhasil dapat data, langsung return
        if final_results:
            return final_results

        # --- STRATEGI 2: BACA SEBAGAI HTML ---
        # Banyak file .xls "palsu" dari sistem report sebenarnya adalah HTML Table
        try:
            dfs_html = pd.read_html(file_path)
            for df in dfs_html:
                html_results = ExcelProcessor._extract_from_dataframe(df)
                final_results.extend(html_results)
        except Exception:
            pass

        if final_results:
            return final_results

        # --- STRATEGI 3: BACA SEBAGAI TEXT/CSV (Fallback Terakhir) ---
        # Menangani file text yang dipaksa jadi .xls atau file yang sangat corrupt header-nya
        try:
            df_csv = pd.read_csv(file_path, header=None, encoding='latin1', names=range(50))
            csv_results = ExcelProcessor._extract_from_dataframe(df_csv)
            final_results.extend(csv_results)
        except Exception:
            pass

        return final_results

# --- Bagian Eksekusi ---
if __name__ == "__main__":
    # Path file sesuai request user
    file_name = "./DATA TEST/Attendance log 21 Nov.xls"

    try:
        processor = ExcelProcessor()
        data_json = processor.process_excel_log(file_name)
        
        if not data_json:
            print("Peringatan: File terbaca tapi DATA KOSONG. Kemungkinan format isi file berubah total atau file corrupt parah.")
        else:
            print(json.dumps(data_json, indent=4))
            
    except FileNotFoundError as e:
        print("!!!" * 10)
        print(e)
        print("!!!" * 10)