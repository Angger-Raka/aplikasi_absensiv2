import sqlite3
import os
from datetime import datetime
import json
import time

class DatabaseManager:
    def __init__(self, db_path="absensi.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Membuat koneksi ke database"""
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency
                conn.execute("PRAGMA synchronous=NORMAL")  # Better performance
                conn.execute("PRAGMA cache_size=10000")  # Increase cache
                conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
                return conn
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    print(f"Database locked, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise e
    
    def init_database(self):
        """Inisialisasi database dan tabel"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Tabel karyawan dengan shift assignment
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                shift_id INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shift_id) REFERENCES shifts (id)
            )
        ''')
        
            # Tabel absensi harian
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                date DATE NOT NULL,
                jam_masuk TEXT,
                jam_keluar TEXT,
                jam_masuk_lembur TEXT,
                jam_keluar_lembur TEXT,
                jam_anomali TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees (id),
                UNIQUE(employee_id, date)
            )
        ''')
        
            # Tabel shifts dengan pengaturan per hari
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                
                -- Senin-Jumat
                weekday_work_start TEXT NOT NULL,
                weekday_work_end TEXT NOT NULL,
                weekday_overtime_start TEXT NOT NULL,
                weekday_overtime_end TEXT NOT NULL,
                weekday_overtime_limit TEXT NOT NULL,
                
                -- Sabtu
                saturday_work_start TEXT NOT NULL,
                saturday_work_end TEXT NOT NULL,
                saturday_overtime_start TEXT NOT NULL,
                saturday_overtime_end TEXT NOT NULL,
                saturday_overtime_limit TEXT NOT NULL,
                
                -- Pengaturan umum
                late_tolerance INTEGER DEFAULT 15,
                overtime_mode TEXT DEFAULT 'per_jam',
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
            # Tabel pelanggaran dengan format detik
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attendance_id INTEGER,
                start_time TEXT NOT NULL,  -- Format HH:mm:ss
                end_time TEXT NOT NULL,    -- Format HH:mm:ss
                description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (attendance_id) REFERENCES attendance (id)
            )
        ''')
        
            # Tabel pengaturan shift
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS shift_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT 'Default',
                jam_masuk_kerja TEXT NOT NULL DEFAULT '08:00',
                jam_keluar_kerja TEXT NOT NULL DEFAULT '17:00',
                jam_masuk_lembur TEXT NOT NULL DEFAULT '18:00',
                jam_keluar_lembur TEXT NOT NULL DEFAULT '22:00',
                batas_overtime TEXT NOT NULL DEFAULT '17:30',
                toleransi_terlambat INTEGER NOT NULL DEFAULT 15,
                overtime_mode TEXT NOT NULL DEFAULT 'per_jam',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
            # Insert default shifts jika belum ada
            cursor.execute('SELECT COUNT(*) FROM shifts')
            if cursor.fetchone()[0] == 0:
                # Shift 1: Jam 8
                cursor.execute('''
                INSERT INTO shifts (
                    name, 
                    weekday_work_start, weekday_work_end, weekday_overtime_start, weekday_overtime_end, weekday_overtime_limit,
                    saturday_work_start, saturday_work_end, saturday_overtime_start, saturday_overtime_end, saturday_overtime_limit,
                    late_tolerance, overtime_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    'Shift 1 (Jam 8)', 
                    '08:00', '16:00', '18:00', '23:00', '17:00',  # Senin-Jumat
                    '08:00', '12:00', '13:00', '17:00', '13:00',  # Sabtu
                    15, 'per_jam'
                ))
                
                # Shift 2: Jam 9
                cursor.execute('''
                INSERT INTO shifts (
                    name, 
                    weekday_work_start, weekday_work_end, weekday_overtime_start, weekday_overtime_end, weekday_overtime_limit,
                    saturday_work_start, saturday_work_end, saturday_overtime_start, saturday_overtime_end, saturday_overtime_limit,
                    late_tolerance, overtime_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    'Shift 2 (Jam 9)', 
                    '09:00', '17:00', '19:00', '23:00', '18:00',  # Senin-Jumat
                    '09:00', '13:00', '14:00', '18:00', '14:00',  # Sabtu
                    15, 'per_jam'
                ))
            
            # Insert default shift setting jika belum ada (backward compatibility)
            cursor.execute('SELECT COUNT(*) FROM shift_settings')
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                INSERT INTO shift_settings (name, jam_masuk_kerja, jam_keluar_kerja, 
                                          jam_masuk_lembur, jam_keluar_lembur, batas_overtime, 
                                          toleransi_terlambat, overtime_mode)
                VALUES ('Default', '08:00', '17:00', '18:00', '22:00', '17:30', 15, 'per_jam')
            ''')
        
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def add_or_get_employee(self, name):
        """Menambah karyawan baru atau mengambil ID karyawan yang sudah ada"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Cek apakah karyawan sudah ada
            cursor.execute('SELECT id FROM employees WHERE name = ?', (name,))
            result = cursor.fetchone()
            
            if result:
                employee_id = result[0]
            else:
                # Tambah karyawan baru
                cursor.execute('INSERT INTO employees (name) VALUES (?)', (name,))
                employee_id = cursor.lastrowid
            
            conn.commit()
            return employee_id
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def save_attendance_data(self, date, attendance_list, mode='replace'):
        """Menyimpan data absensi untuk tanggal tertentu
        
        Args:
            date: Tanggal absensi
            attendance_list: List data absensi
            mode: 'replace' (timpa semua), 'merge' (tambah/update), 'insert_only' (hanya tambah baru)
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # If replace mode, delete existing data for this date first
            if mode == 'replace':
                cursor.execute('DELETE FROM attendance WHERE date = ?', (date,))
            
            for data in attendance_list:
                # Get or create employee within the same connection
                cursor.execute('SELECT id FROM employees WHERE name = ?', (data['Nama'],))
                result = cursor.fetchone()
                
                if result:
                    employee_id = result[0]
                else:
                    # Add new employee
                    cursor.execute('INSERT INTO employees (name) VALUES (?)', (data['Nama'],))
                    employee_id = cursor.lastrowid
                
                # Convert jam_anomali list to JSON string
                jam_anomali_json = json.dumps(data['Jam Anomali']) if data['Jam Anomali'] else None
                
                if mode == 'insert_only':
                    # Only insert if not exists
                    cursor.execute('''
                        INSERT OR IGNORE INTO attendance 
                        (employee_id, date, jam_masuk, jam_keluar, jam_masuk_lembur, jam_keluar_lembur, jam_anomali)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        employee_id, date, 
                        data['Jam Masuk'], data['Jam Keluar'],
                        data['Jam Masuk Lembur'], data['Jam Keluar Lembur'],
                        jam_anomali_json
                    ))
                else:
                    # Insert or replace (for both 'replace' and 'merge' modes)
                    cursor.execute('''
                        INSERT OR REPLACE INTO attendance 
                        (employee_id, date, jam_masuk, jam_keluar, jam_masuk_lembur, jam_keluar_lembur, jam_anomali)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        employee_id, date, 
                        data['Jam Masuk'], data['Jam Keluar'],
                        data['Jam Masuk Lembur'], data['Jam Keluar Lembur'],
                        jam_anomali_json
                    ))
            
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def get_attendance_summary_by_date(self, date):
        """Mengambil ringkasan data absensi untuk tanggal tertentu"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) as total_employees,
                       COUNT(CASE WHEN a.jam_masuk IS NOT NULL THEN 1 END) as hadir,
                       COUNT(CASE WHEN a.jam_masuk IS NULL THEN 1 END) as tidak_hadir,
                       COUNT(CASE WHEN a.jam_masuk_lembur IS NOT NULL THEN 1 END) as lembur
                FROM attendance a
                WHERE a.date = ?
            ''', (date,))
            
            result = cursor.fetchone()
            
            if result:
                return {
                    'total_employees': result[0],
                    'hadir': result[1], 
                    'tidak_hadir': result[2],
                    'lembur': result[3]
                }
            return None
        except Exception as e:
            raise e
        finally:
            if conn:
                conn.close()
    
    def get_attendance_by_date(self, date):
        """Mengambil data absensi berdasarkan tanggal"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT a.id, e.name, a.jam_masuk, a.jam_keluar, 
                       a.jam_masuk_lembur, a.jam_keluar_lembur, a.jam_anomali
                FROM attendance a
                JOIN employees e ON a.employee_id = e.id
                WHERE a.date = ?
                ORDER BY e.name
            ''', (date,))
            
            results = cursor.fetchall()
            
            attendance_data = []
            for row in results:
                jam_anomali = json.loads(row[6]) if row[6] else []
                attendance_data.append({
                    'id': row[0],
                    'Nama': row[1],
                    'Jam Masuk': row[2],
                    'Jam Keluar': row[3],
                    'Jam Masuk Lembur': row[4],
                    'Jam Keluar Lembur': row[5],
                    'Jam Anomali': jam_anomali
                })
            
            return attendance_data
        except Exception as e:
            raise e
        finally:
            if conn:
                conn.close()
    
    def update_attendance_field(self, attendance_id, field, value):
        """Update field tertentu pada data absensi"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(f'UPDATE attendance SET {field} = ? WHERE id = ?', (value, attendance_id))
            
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def add_violation(self, attendance_id, start_time, end_time, description):
        """Menambah pelanggaran untuk attendance tertentu"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO violations (attendance_id, start_time, end_time, description)
                VALUES (?, ?, ?, ?)
            ''', (attendance_id, start_time, end_time, description))
            
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def get_violations_by_attendance(self, attendance_id):
        """Mengambil pelanggaran berdasarkan attendance_id"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, start_time, end_time, description, created_at
                FROM violations
                WHERE attendance_id = ?
                ORDER BY created_at
            ''', (attendance_id,))
            
            results = cursor.fetchall()
            
            return [{'id': row[0], 'start_time': row[1], 'end_time': row[2], 
                    'description': row[3], 'created_at': row[4]} for row in results]
        except Exception as e:
            raise e
        finally:
            if conn:
                conn.close()
    
    def update_violation(self, violation_id, start_time, end_time, description):
        """Update pelanggaran berdasarkan ID"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE violations 
                SET start_time = ?, end_time = ?, description = ?
                WHERE id = ?
            ''', (start_time, end_time, description, violation_id))
            
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def delete_violation(self, violation_id):
        """Hapus pelanggaran berdasarkan ID"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM violations WHERE id = ?', (violation_id,))
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def get_shift_settings(self):
        """Mengambil pengaturan shift"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM shift_settings ORDER BY id DESC LIMIT 1')
            result = cursor.fetchone()
            
            if result:
                return {
                    'id': result[0],
                    'name': result[1],
                    'jam_masuk_kerja': result[2],
                    'jam_keluar_kerja': result[3],
                    'jam_masuk_lembur': result[4],
                    'jam_keluar_lembur': result[5],
                    'batas_overtime': result[6],
                    'toleransi_terlambat': result[7],
                    'overtime_mode': result[8]
                }
            return None
        except Exception as e:
            raise e
        finally:
            if conn:
                conn.close()
    
    def update_shift_settings(self, settings):
        """Update pengaturan shift"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE shift_settings SET
                    jam_masuk_kerja = ?, jam_keluar_kerja = ?, jam_masuk_lembur = ?,
                    jam_keluar_lembur = ?, batas_overtime = ?, toleransi_terlambat = ?,
                    overtime_mode = ?
                WHERE id = ?
            ''', (
                settings['jam_masuk_kerja'], settings['jam_keluar_kerja'],
                settings['jam_masuk_lembur'], settings['jam_keluar_lembur'],
                settings['batas_overtime'], settings['toleransi_terlambat'],
                settings['overtime_mode'], settings['id']
            ))
            
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def get_all_employees(self):
        """Mengambil semua karyawan"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, name FROM employees ORDER BY name')
            results = cursor.fetchall()
            
            return [{'id': row[0], 'name': row[1]} for row in results]
        except Exception as e:
            raise e
        finally:
            if conn:
                conn.close()
    
    def get_attendance_by_employee_period(self, employee_id, start_date, end_date):
        """Mengambil data absensi karyawan dalam periode tertentu"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT a.id, a.date, a.jam_masuk, a.jam_keluar, 
                       a.jam_masuk_lembur, a.jam_keluar_lembur, a.jam_anomali
                FROM attendance a
                WHERE a.employee_id = ? AND a.date BETWEEN ? AND ?
                ORDER BY a.date
            ''', (employee_id, start_date, end_date))
            
            results = cursor.fetchall()
            
            attendance_data = []
            for row in results:
                jam_anomali = json.loads(row[6]) if row[6] else []
                attendance_data.append({
                    'id': row[0],
                    'date': row[1],
                    'jam_masuk': row[2],
                    'jam_keluar': row[3],
                    'jam_masuk_lembur': row[4],
                    'jam_keluar_lembur': row[5],
                    'jam_anomali': jam_anomali
                })
            
            return attendance_data
        except Exception as e:
            raise e
        finally:
            if conn:
                conn.close()
    
    # ==================== SHIFT MANAGEMENT FUNCTIONS ====================
    
    def get_all_shifts(self):
        """Mengambil semua shifts"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM shifts ORDER BY id')
            results = cursor.fetchall()
            
            shifts = []
            for row in results:
                shifts.append({
                    'id': row[0],
                    'name': row[1],
                    'weekday_work_start': row[2],
                    'weekday_work_end': row[3],
                    'weekday_overtime_start': row[4],
                    'weekday_overtime_end': row[5],
                    'weekday_overtime_limit': row[6],
                    'saturday_work_start': row[7],
                    'saturday_work_end': row[8],
                    'saturday_overtime_start': row[9],
                    'saturday_overtime_end': row[10],
                    'saturday_overtime_limit': row[11],
                    'late_tolerance': row[12],
                    'overtime_mode': row[13]
                })
            
            return shifts
        except Exception as e:
            raise e
        finally:
            if conn:
                conn.close()
    
    def get_shift_by_id(self, shift_id):
        """Mengambil shift berdasarkan ID"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM shifts WHERE id = ?', (shift_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'weekday_work_start': row[2],
                    'weekday_work_end': row[3],
                    'weekday_overtime_start': row[4],
                    'weekday_overtime_end': row[5],
                    'weekday_overtime_limit': row[6],
                    'saturday_work_start': row[7],
                    'saturday_work_end': row[8],
                    'saturday_overtime_start': row[9],
                    'saturday_overtime_end': row[10],
                    'saturday_overtime_limit': row[11],
                    'late_tolerance': row[12],
                    'overtime_mode': row[13]
                }
            return None
        except Exception as e:
            raise e
        finally:
            if conn:
                conn.close()
    
    def update_shift(self, shift_id, shift_data):
        """Update data shift"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE shifts SET
                    name = ?,
                    weekday_work_start = ?, weekday_work_end = ?, 
                    weekday_overtime_start = ?, weekday_overtime_end = ?, weekday_overtime_limit = ?,
                    saturday_work_start = ?, saturday_work_end = ?, 
                    saturday_overtime_start = ?, saturday_overtime_end = ?, saturday_overtime_limit = ?,
                    late_tolerance = ?, overtime_mode = ?
                WHERE id = ?
            ''', (
                shift_data['name'],
                shift_data['weekday_work_start'], shift_data['weekday_work_end'],
                shift_data['weekday_overtime_start'], shift_data['weekday_overtime_end'], shift_data['weekday_overtime_limit'],
                shift_data['saturday_work_start'], shift_data['saturday_work_end'],
                shift_data['saturday_overtime_start'], shift_data['saturday_overtime_end'], shift_data['saturday_overtime_limit'],
                shift_data['late_tolerance'], shift_data['overtime_mode'],
                shift_id
            ))
            
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def assign_employee_shift(self, employee_id, shift_id):
        """Assign shift ke karyawan"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('UPDATE employees SET shift_id = ? WHERE id = ?', (shift_id, employee_id))
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def get_employees_with_shifts(self):
        """Mengambil semua karyawan dengan info shift"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT e.id, e.name, e.shift_id, s.name as shift_name
                FROM employees e
                LEFT JOIN shifts s ON e.shift_id = s.id
                ORDER BY e.name
            ''')
            
            results = cursor.fetchall()
            employees = []
            for row in results:
                employees.append({
                    'id': row[0],
                    'name': row[1],
                    'shift_id': row[2],
                    'shift_name': row[3] or 'No Shift'
                })
            
            return employees
        except Exception as e:
            raise e
        finally:
            if conn:
                conn.close()
    
    def create_shift(self, shift_data):
        """Create shift baru"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO shifts (
                    name, 
                    weekday_work_start, weekday_work_end, weekday_overtime_start, weekday_overtime_end, weekday_overtime_limit,
                    saturday_work_start, saturday_work_end, saturday_overtime_start, saturday_overtime_end, saturday_overtime_limit,
                    late_tolerance, overtime_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                shift_data['name'],
                shift_data['weekday_work_start'], shift_data['weekday_work_end'],
                shift_data['weekday_overtime_start'], shift_data['weekday_overtime_end'], shift_data['weekday_overtime_limit'],
                shift_data['saturday_work_start'], shift_data['saturday_work_end'],
                shift_data['saturday_overtime_start'], shift_data['saturday_overtime_end'], shift_data['saturday_overtime_limit'],
                shift_data['late_tolerance'], shift_data['overtime_mode']
            ))
            
            shift_id = cursor.lastrowid
            conn.commit()
            return shift_id
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def delete_shift(self, shift_id):
        """Delete shift"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if shift is being used by employees
            cursor.execute('SELECT COUNT(*) FROM employees WHERE shift_id = ?', (shift_id,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                raise Exception(f"Tidak dapat menghapus shift. Masih ada {count} karyawan yang menggunakan shift ini.")
            
            cursor.execute('DELETE FROM shifts WHERE id = ?', (shift_id,))
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

