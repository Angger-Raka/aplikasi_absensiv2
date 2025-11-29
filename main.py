import pandas as pd
import json
import os
import warnings
import sys
import contextlib

# --- BAGIAN 1: KONFIGURASI MEMBISUKAN WARNING ---
@contextlib.contextmanager
def suppress_output():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            sys.stdout = devnull
            sys.stderr = devnull
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

warnings.filterwarnings("ignore")

class ExcelProcessor:
    @staticmethod
    def _extract_from_dataframe(df):
        """
        Helper function: Mencari data absensi dari DataFrame.
        Disodorkan untuk struktur file Grid++Report CSV.
        """
        results = []
        if df.empty:
            return results

        # Normalisasi seluruh DataFrame menjadi string uppercase
        df_str = df.astype(str).apply(lambda x: x.str.strip().str.upper())

        for i in range(len(df)):
            row = df.iloc[i]
            row_upper = df_str.iloc[i].tolist()
            
            # --- TAHAP 1: MENCARI BARIS HEADER NAMA ---
            found_index = -1
            
            # Kata kunci yang mungkin muncul di header
            possible_keywords = ["NAME", "NAMA", "ENM NO", "PEGAWAI", "KARYAWAN"]
            
            for keyword in possible_keywords:
                if keyword in row_upper:
                    found_index = row_upper.index(keyword)
                    break
            
            # Jika ketemu label "NAME" atau sejenisnya
            if found_index != -1:
                try:
                    # --- TAHAP 2: MENGAMBIL VALUE NAMA ---
                    nama_karyawan = "Unknown"
                    
                    # Cek kolom di sebelah kanan label (index + 1)
                    if found_index + 1 < len(row):
                        val = str(row.iloc[found_index + 1]).strip()
                        if val and val.lower() not in ['nan', 'none', ':', '=', '']:
                            nama_karyawan = val
                        # Jika +1 kosong, coba +2 (kadang ada spasi kosong diantaranya)
                        elif found_index + 2 < len(row):
                            val2 = str(row.iloc[found_index + 2]).strip()
                            if val2 and val2.lower() not in ['nan', 'none']:
                                nama_karyawan = val2

                    # Validasi nama (skip jika tidak valid)
                    if nama_karyawan in ["Unknown", "nan", "None", ""]:
                        continue
                    
                    # --- TAHAP 3: MENGAMBIL JAM (LOGIKA BARU) ---
                    # Data jam ada di baris tepat di bawah nama (i + 1)
                    jam_list = []
                    
                    if i + 1 < len(df):
                        next_row = df.iloc[i+1]
                        
                        # Gabungkan semua sel di baris bawah menjadi satu string panjang
                        # Ini penting karena format CSV Anda menumpuk jam dengan \n di satu sel
                        clean_values = [str(x).strip() for x in next_row if str(x).lower() not in ['nan', 'none', '']]
                        full_row_str = "\n".join(clean_values)
                        
                        if full_row_str:
                            # Split berdasarkan baris baru atau spasi, lalu bersihkan
                            raw_tokens = full_row_str.replace('\n', ' ').split()
                            
                            jam_list = [
                                t.strip().replace('.', ':') 
                                for t in raw_tokens
                                if (':' in str(t) or '.' in str(t)) and len(t) >= 4 # Validasi format jam
                            ]

                    # --- TAHAP 4: MAPPING JAM KE STRUKTUR (SESUAI REQUEST) ---
                    entry = {
                        "Nama": str(nama_karyawan).strip(),
                        "Jam Masuk": None,            # Data ke-1
                        "Jam Keluar": None,           # Data ke-2
                        "Jam Masuk Lembur": None,     # Data ke-3
                        "Jam Keluar Lembur": None,    # Data ke-4
                        "Jam Anomali": [],            # Data ke-5 dst
                        "Total Scan": len(jam_list)
                    }

                    # Logika Mapping Urutan (Opsi B: Ganjil dibiarkan kosong di akhir)
                    if len(jam_list) > 0:
                        entry["Jam Masuk"] = jam_list[0]
                    
                    if len(jam_list) > 1:
                        entry["Jam Keluar"] = jam_list[1]
                        
                    if len(jam_list) > 2:
                        entry["Jam Masuk Lembur"] = jam_list[2]
                        
                    if len(jam_list) > 3:
                        entry["Jam Keluar Lembur"] = jam_list[3]
                        
                    # Jika ada lebih dari 4 kali scan, sisanya masuk anomali
                    if len(jam_list) > 4:
                        entry["Jam Anomali"] = jam_list[4:]

                    results.append(entry)

                except Exception:
                    continue
        return results

    @staticmethod
    def process_excel_log(file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File tidak ditemukan: '{file_path}'")
        
        final_results = []
        file_read_success = False
        temp_file_path = None
        
        # Clear any pandas cache/state and reset pandas
        try:
            import gc
            
            # Clear pandas cache
            if hasattr(pd, '_cache'):
                pd._cache.clear()
            
            # Force garbage collection
            gc.collect()
            
            # Reset pandas options to default (in case something changed)
            pd.reset_option('all')
            
        except Exception as e:
            print(f"   ⚠️  Cache cleanup warning: {e}")
            pass
        
        print(f"📂 Processing file: {os.path.basename(file_path)}")
        
        # Create a temporary copy to avoid file handle conflicts
        try:
            import shutil
            import tempfile
            
            # Create temp file with same extension
            file_ext = os.path.splitext(file_path)[1]
            temp_fd, temp_file_path = tempfile.mkstemp(suffix=file_ext)
            os.close(temp_fd)  # Close the file descriptor
            
            # Copy original file to temp location
            shutil.copy2(file_path, temp_file_path)
            working_file_path = temp_file_path
            print(f"   📋 Using temporary file for processing")
            
        except Exception as e:
            print(f"   ⚠️  Could not create temp file: {e}, using original")
            working_file_path = file_path
        
        # --- STRATEGI BACA FILE ---
        # Karena file Anda sebenarnya adalah CSV (meski ekstensi .xls), 
        # kita prioritaskan pembacaan teks/csv.
        
        separators = [',', '\t', ';', '|']

        # Coba baca sebagai CSV (Prioritas Utama untuk format Grid++Report)
        print("🔍 Trying CSV reading strategies...")
        for i, sep in enumerate(separators):
            try:
                print(f"   Trying separator {i+1}/{len(separators)}: '{sep}'")
                # Header=None penting agar baris pertama tidak dianggap judul kolom
                df_csv = pd.read_csv(working_file_path, header=None, sep=sep, encoding='latin1', engine='python', on_bad_lines='skip')
                
                # Cek sekilas apakah dataframe masuk akal (punya cukup kolom/baris)
                if not df_csv.empty and len(df_csv) > 1:
                    print(f"   📊 DataFrame shape: {df_csv.shape}")
                    res = ExcelProcessor._extract_from_dataframe(df_csv)
                    if res:
                        print(f"   ✅ Found {len(res)} records with separator '{sep}'")
                        final_results.extend(res)
                        file_read_success = True
                        break
                    else:
                        print(f"   ⚠️  DataFrame loaded but no data extracted")
                else:
                    print(f"   ❌ DataFrame empty or too small")
            except Exception as e:
                print(f"   ❌ CSV reading failed: {type(e).__name__}")
                continue

        # Jika gagal baca sebagai CSV, coba baca sebagai Excel biasa (Fallback)
        if not file_read_success and not final_results:
            print("🔍 Trying Excel reading strategy...")
            
            # Try multiple Excel engines with proper file handle management
            excel_engines = ['openpyxl', 'xlrd', None]  # None = auto-detect
            
            for engine in excel_engines:
                try:
                    print(f"   🔧 Trying engine: {engine if engine else 'auto'}")
                    
                    with suppress_output():
                        # Use context manager or explicit close for better file handle management
                        if engine:
                            all_sheets = pd.read_excel(working_file_path, header=None, sheet_name=None, engine=engine)
                        else:
                            all_sheets = pd.read_excel(working_file_path, header=None, sheet_name=None)
                        
                        print(f"   📊 Found {len(all_sheets)} sheets")
                        
                        for sheet_name, df in all_sheets.items():
                            print(f"   📄 Processing sheet: {sheet_name}, shape: {df.shape}")
                            sheet_results = ExcelProcessor._extract_from_dataframe(df)
                            if sheet_results:
                                print(f"   ✅ Found {len(sheet_results)} records in sheet '{sheet_name}'")
                                final_results.extend(sheet_results)
                                file_read_success = True
                            else:
                                print(f"   ⚠️  No data extracted from sheet '{sheet_name}'")
                        
                        # Explicitly clear the sheets data to free file handles
                        del all_sheets
                        
                        # If we got results, break out of engine loop
                        if file_read_success:
                            print(f"   ✅ Success with engine: {engine if engine else 'auto'}")
                            break
                            
                except Exception as e:
                    print(f"   ❌ Engine {engine if engine else 'auto'} failed: {type(e).__name__}: {str(e)}")
                    continue

        # Final cleanup - comprehensive cleanup to prevent file handle issues
        try:
            import gc
            
            # Force close any remaining file handles
            try:
                # Clear pandas internal caches
                if hasattr(pd, '_cache'):
                    pd._cache.clear()
                
                # Clear pandas parsers cache
                if hasattr(pd.io, 'parsers'):
                    if hasattr(pd.io.parsers, '_parser_defaults'):
                        pd.io.parsers._parser_defaults.clear()
                
                # Clear any Excel file handles in pandas
                if hasattr(pd.io, 'excel'):
                    if hasattr(pd.io.excel, '_writers'):
                        pd.io.excel._writers.clear()
                        
            except Exception as cleanup_e:
                print(f"   ⚠️  Advanced cleanup warning: {cleanup_e}")
            
            # Force garbage collection multiple times to ensure cleanup
            for _ in range(3):
                gc.collect()
                
        except Exception as e:
            print(f"   ⚠️  Final cleanup warning: {e}")
            pass
        
        # Cleanup temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                print(f"   🗑️  Temporary file cleaned up")
            except Exception as e:
                print(f"   ⚠️  Could not cleanup temp file: {e}")
        
        print(f"📋 Final result: {len(final_results)} records processed")
        return final_results

# --- Bagian Eksekusi ---
if __name__ == "__main__":
    # Ganti nama file di sini sesuai kebutuhan
    file_name = "./DATA TEST/Attendance log 26.xls" 

    print(f"Sedang memproses: {file_name} ...")
    
    try:
        processor = ExcelProcessor()
        data_json = processor.process_excel_log(file_name)
        
        if not data_json:
            print("\n[INFO] Tidak ditemukan data yang cocok.")
            print("Pastikan file memiliki header 'Name' atau 'Nama' dan format jam di baris bawahnya.")
        else:
            print(f"\n[SUKSES] Ditemukan {len(data_json)} data karyawan.\n")
            print(json.dumps(data_json, indent=4))
            
    except Exception as e:
        print(f"Error: {e}")
