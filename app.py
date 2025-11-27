import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                               QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                               QPushButton, QDateEdit, QLabel, QFileDialog, QMessageBox,
                               QHeaderView, QComboBox, QTimeEdit, QTextEdit, QDialog,
                               QFormLayout, QDialogButtonBox, QGroupBox, QRadioButton,
                               QSpinBox, QSplitter, QLineEdit, QCalendarWidget)
from PySide6.QtCore import Qt, QDate, QTime, QLocale, Signal
from PySide6.QtGui import QFont, QTextCharFormat, QColor
from datetime import datetime, date, timedelta
import traceback

from database import DatabaseManager
from main import ExcelProcessor
from database_utils import check_database_status, force_unlock_database, diagnose_database_lock
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

class IndonesianCalendar(QCalendarWidget):
    """Kalender custom dengan bahasa Indonesia dan tanggal merah untuk hari Minggu"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set locale ke Indonesia
        locale = QLocale(QLocale.Indonesian, QLocale.Indonesia)
        self.setLocale(locale)
        
        # Nama hari dalam bahasa Indonesia
        self.setHorizontalHeaderFormat(QCalendarWidget.LongDayNames)
        
        # Format untuk hari Minggu (tanggal merah)
        sunday_format = QTextCharFormat()
        sunday_format.setForeground(QColor(255, 0, 0))  # Merah
        sunday_format.setBackground(QColor(255, 230, 230))  # Background pink muda
        self.setWeekdayTextFormat(Qt.Sunday, sunday_format)

class IndonesianDateEdit(QDateEdit):
    """DateEdit dengan kalender bahasa Indonesia dan tanggal merah"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        
        # Buat custom calendar popup
        calendar = IndonesianCalendar(self)
        self.setCalendarWidget(calendar)
        
        # Set format tampilan tanggal
        self.setDisplayFormat("dd MMMM yyyy")
        
        # Set locale ke Indonesia untuk format tanggal
        locale = QLocale(QLocale.Indonesian, QLocale.Indonesia)
        self.setLocale(locale)

class ViolationDialog(QDialog):
    def __init__(self, employees, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tambah Pelanggaran")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QFormLayout()
        
        # Dropdown karyawan
        self.employee_combo = QComboBox()
        for emp in employees:
            self.employee_combo.addItem(emp['Nama'], emp.get('id'))
        layout.addRow("Karyawan:", self.employee_combo)
        
        # Waktu mulai dan selesai dengan detik
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm:ss")
        layout.addRow("Jam Mulai:", self.start_time)
        
        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm:ss")
        layout.addRow("Jam Selesai:", self.end_time)
        
        # Keterangan
        self.description = QTextEdit()
        self.description.setMaximumHeight(100)
        layout.addRow("Keterangan:", self.description)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.setLayout(layout)
    
    def get_violation_data(self):
        return {
            'employee_name': self.employee_combo.currentText(),
            'attendance_id': self.employee_combo.currentData(),
            'start_time': self.start_time.time().toString("HH:mm:ss"),
            'end_time': self.end_time.time().toString("HH:mm:ss"),
            'description': self.description.toPlainText()
        }

class ViolationManagementDialog(QDialog):
    def __init__(self, db_manager, attendance_id, employee_name, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.attendance_id = attendance_id
        self.employee_name = employee_name
        
        self.setWindowTitle(f"Kelola Pelanggaran - {employee_name}")
        self.setModal(True)
        self.resize(800, 500)
        self.init_ui()
        self.load_violations()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header info
        info_label = QLabel(f"Kelola Pelanggaran untuk: {self.employee_name}")
        info_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Tambah Pelanggaran")
        self.add_btn.clicked.connect(self.add_violation)
        button_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("✏️ Edit Pelanggaran")
        self.edit_btn.clicked.connect(self.edit_violation)
        self.edit_btn.setEnabled(False)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ Hapus Pelanggaran")
        self.delete_btn.clicked.connect(self.delete_violation)
        self.delete_btn.setEnabled(False)
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Jam Mulai", "Jam Selesai", "Keterangan", "Dibuat"])
        
        # Table settings - ubah ke Interactive agar pengguna dapat mengubah ukuran kolom
        header = self.table.horizontalHeader()
        
        # Set semua kolom ke Interactive (bisa diubah ukurannya oleh user)
        for i in range(4):  # Semua kolom
            header.setSectionResizeMode(i, QHeaderView.Interactive)
        
        # Set default width untuk kolom
        self.table.setColumnWidth(0, 100)  # Jam Mulai
        self.table.setColumnWidth(1, 100)  # Jam Selesai
        self.table.setColumnWidth(2, 400)  # Keterangan
        self.table.setColumnWidth(3, 150)  # Dibuat
        
        # Enable stretching table to fill available space
        self.table.horizontalHeader().setStretchLastSection(True)
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.table)
        
        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("Tutup")
        close_btn.clicked.connect(self.accept)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)
        
        self.setLayout(layout)
    
    def load_violations(self):
        """Load violations data into table"""
        try:
            violations = self.db_manager.get_violations_by_attendance(self.attendance_id)
            self.table.setRowCount(len(violations))
            
            for row, violation in enumerate(violations):
                # Store violation ID in first column as hidden data
                start_item = QTableWidgetItem(violation['start_time'])
                start_item.setData(Qt.UserRole, violation['id'])  # Store violation ID
                self.table.setItem(row, 0, start_item)
                
                self.table.setItem(row, 1, QTableWidgetItem(violation['end_time']))
                self.table.setItem(row, 2, QTableWidgetItem(violation['description']))
                
                # Format created_at timestamp
                created_at = violation['created_at']
                if created_at:
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        formatted_date = dt.strftime("%d/%m/%Y %H:%M")
                    except:
                        formatted_date = created_at
                else:
                    formatted_date = "-"
                
                self.table.setItem(row, 3, QTableWidgetItem(formatted_date))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal memuat data pelanggaran:\n{str(e)}")
    
    def on_selection_changed(self):
        """Handle table selection change"""
        has_selection = len(self.table.selectionModel().selectedRows()) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
    
    def add_violation(self):
        """Add new violation"""
        dialog = ViolationEditDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            violation_data = dialog.get_violation_data()
            try:
                self.db_manager.add_violation(
                    self.attendance_id,
                    violation_data['start_time'],
                    violation_data['end_time'],
                    violation_data['description']
                )
                QMessageBox.information(self, "Sukses", "Pelanggaran berhasil ditambahkan")
                self.load_violations()  # Refresh table
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal menambah pelanggaran:\n{str(e)}")
    
    def edit_violation(self):
        """Edit selected violation"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        violation_id = self.table.item(row, 0).data(Qt.UserRole)
        
        # Get current data
        start_time = self.table.item(row, 0).text()
        end_time = self.table.item(row, 1).text()
        description = self.table.item(row, 2).text()
        
        dialog = ViolationEditDialog(start_time, end_time, description, self)
        if dialog.exec() == QDialog.Accepted:
            violation_data = dialog.get_violation_data()
            try:
                self.db_manager.update_violation(
                    violation_id,
                    violation_data['start_time'],
                    violation_data['end_time'],
                    violation_data['description']
                )
                QMessageBox.information(self, "Sukses", "Pelanggaran berhasil diupdate")
                self.load_violations()  # Refresh table
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal mengupdate pelanggaran:\n{str(e)}")
    
    def delete_violation(self):
        """Delete selected violation"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        violation_id = self.table.item(row, 0).data(Qt.UserRole)
        start_time = self.table.item(row, 0).text()
        end_time = self.table.item(row, 1).text()
        description = self.table.item(row, 2).text()
        
        reply = QMessageBox.question(
            self, "Konfirmasi Hapus",
            f"Apakah Anda yakin ingin menghapus pelanggaran ini?\n\n"
            f"Waktu: {start_time} - {end_time}\n"
            f"Keterangan: {description}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.delete_violation(violation_id)
                QMessageBox.information(self, "Sukses", "Pelanggaran berhasil dihapus")
                self.load_violations()  # Refresh table
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal menghapus pelanggaran:\n{str(e)}")

class ViolationEditDialog(QDialog):
    def __init__(self, start_time="", end_time="", description="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Pelanggaran" if start_time else "Tambah Pelanggaran")
        self.setModal(True)
        self.resize(400, 250)
        
        layout = QFormLayout()
        
        # Waktu mulai dan selesai dengan detik
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm:ss")
        if start_time:
            from PySide6.QtCore import QTime
            self.start_time.setTime(QTime.fromString(start_time, "HH:mm:ss"))
        layout.addRow("Jam Mulai:", self.start_time)
        
        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm:ss")
        if end_time:
            from PySide6.QtCore import QTime
            self.end_time.setTime(QTime.fromString(end_time, "HH:mm:ss"))
        layout.addRow("Jam Selesai:", self.end_time)
        
        # Keterangan
        self.description = QTextEdit()
        self.description.setMaximumHeight(100)
        self.description.setPlainText(description)
        layout.addRow("Keterangan:", self.description)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.setLayout(layout)
    
    def get_violation_data(self):
        return {
            'start_time': self.start_time.time().toString("HH:mm:ss"),
            'end_time': self.end_time.time().toString("HH:mm:ss"),
            'description': self.description.toPlainText()
        }

class AttendanceInputTab(QWidget):
    def __init__(self, db_manager, main_window=None):
        super().__init__()
        self.db_manager = db_manager
        self.main_window = main_window
        self.current_data = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        # Date picker dengan format Indonesia
        controls_layout.addWidget(QLabel("Tanggal:"))
        self.date_edit = IndonesianDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.dateChanged.connect(self.load_attendance_data)
        controls_layout.addWidget(self.date_edit)
        
        controls_layout.addStretch()
        
        # Import button
        self.import_btn = QPushButton("Import Excel")
        self.import_btn.clicked.connect(self.import_excel)
        controls_layout.addWidget(self.import_btn)
        
        # Refresh button
        self.refresh_btn = QPushButton("🔄 Refresh Data")
        self.refresh_btn.setToolTip("Muat ulang data dari database untuk tanggal yang dipilih")
        self.refresh_btn.clicked.connect(self.refresh_data)
        controls_layout.addWidget(self.refresh_btn)
        
        # Save button - ganti dengan Save/Update
        self.save_btn = QPushButton("Save/Update Data")
        self.save_btn.setToolTip("Simpan data baru atau update data yang sudah ada")
        self.save_btn.clicked.connect(self.save_to_database)
        self.save_btn.setEnabled(False)
        controls_layout.addWidget(self.save_btn)
        
        # Database status button
        self.db_status_btn = QPushButton("Check DB Status")
        self.db_status_btn.clicked.connect(self.check_database_status)
        controls_layout.addWidget(self.db_status_btn)
        
        layout.addLayout(controls_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Nama Karyawan", "Shift", "Jam Masuk Kerja", "Jam Keluar Kerja", 
            "Jam Masuk Lembur", "Jam Keluar Lembur", "Jam Anomali", "Kelola Pelanggaran"
        ])
        
        # Make table editable
        self.table.itemChanged.connect(self.on_item_changed)
        
        # Resize columns - ubah ke Interactive agar pengguna dapat mengubah ukuran kolom
        header = self.table.horizontalHeader()
        
        # Set semua kolom ke Interactive (bisa diubah ukurannya oleh user)
        for i in range(8):  # Semua kolom termasuk Shift dan Kelola Pelanggaran
            header.setSectionResizeMode(i, QHeaderView.Interactive)
        
        # Set default width untuk kolom
        self.table.setColumnWidth(0, 180)  # Nama Karyawan
        self.table.setColumnWidth(1, 120)  # Shift
        self.table.setColumnWidth(2, 100)  # Jam Masuk Kerja
        self.table.setColumnWidth(3, 100)  # Jam Keluar Kerja
        self.table.setColumnWidth(4, 120)  # Jam Masuk Lembur
        self.table.setColumnWidth(5, 120)  # Jam Keluar Lembur
        self.table.setColumnWidth(6, 150)  # Jam Anomali
        self.table.setColumnWidth(7, 120)  # Kelola Pelanggaran
        
        # Enable stretching table to fill available space
        self.table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.table)
        
        # Bottom controls
        bottom_layout = QHBoxLayout()
        
        self.add_violation_btn = QPushButton("Tambah Pelanggaran")
        self.add_violation_btn.clicked.connect(self.add_violation)
        self.add_violation_btn.setEnabled(False)
        bottom_layout.addWidget(self.add_violation_btn)
        
        bottom_layout.addStretch()
        
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
        
        # Load data for current date
        self.load_attendance_data()
    
    def import_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Pilih File Excel", "", "Excel Files (*.xls *.xlsx)"
        )
        
        if file_path:
            # Show loading cursor
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            try:
                processor = ExcelProcessor()
                data = processor.process_excel_log(file_path)
                
                if data:
                    self.current_data = data
                    self.populate_table(data)
                    self.save_btn.setEnabled(True)
                    self.save_btn.setText("Save Data")  # Ubah teks tombol menjadi Save Data
                    self.add_violation_btn.setEnabled(True)
                    QMessageBox.information(self, "Sukses", f"Berhasil import {len(data)} data karyawan")
                else:
                    QMessageBox.warning(self, "Warning", "Tidak ada data yang berhasil diproses dari file Excel")
                    
            except FileNotFoundError as e:
                QMessageBox.critical(self, "File Tidak Ditemukan", str(e))
            except Exception as e:
                error_msg = str(e)
                if "OLE2 inconsistency" in error_msg or "file size" in error_msg:
                    QMessageBox.critical(
                        self, "Error Format Excel", 
                        f"File Excel memiliki format yang tidak standar (umum pada file dari alat presensi lama).\n\n"
                        f"Solusi yang bisa dicoba:\n"
                        f"1. Buka file Excel dan Save As dengan format .xlsx\n"
                        f"2. Gunakan Excel versi terbaru untuk menyimpan file\n"
                        f"3. Export ulang dari alat presensi dengan format yang lebih baru\n\n"
                        f"Catatan: File mungkin masih bisa diproses meskipun ada warning.\n\n"
                        f"Detail error: {error_msg}"
                    )
                elif "DATA KOSONG" in error_msg or "tidak mengandung data" in error_msg:
                    QMessageBox.warning(
                        self, "Data Kosong",
                        f"File Excel berhasil dibaca tapi tidak mengandung data absensi yang dapat diproses.\n\n"
                        f"Kemungkinan penyebab:\n"
                        f"1. Format file berbeda dari yang diharapkan\n"
                        f"2. File kosong atau tidak mengandung data karyawan\n"
                        f"3. Struktur data dalam file berubah\n\n"
                        f"Pastikan file Excel berisi data absensi dengan format yang benar."
                    )
                else:
                    QMessageBox.critical(self, "Error", f"Gagal membaca file Excel:\n{error_msg}")
            finally:
                # Restore normal cursor
                QApplication.restoreOverrideCursor()
    
    def populate_table(self, data):
        self.table.setRowCount(len(data))
        
        # Get all shifts for dropdown
        shifts = self.db_manager.get_all_shifts()
        
        for row, item in enumerate(data):
            # Nama (read-only)
            name_item = QTableWidgetItem(item['Nama'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, name_item)
            
            # Shift dropdown
            shift_combo = QComboBox()
            for shift in shifts:
                shift_combo.addItem(shift['name'], shift['id'])
            
            # Set current shift - prioritas: shift_id dari data, lalu shift default karyawan, lalu shift 1
            current_shift_id = item.get('shift_id')
            if not current_shift_id:
                # Cari shift default karyawan dari database
                try:
                    employee_data = self.db_manager.get_employee_by_name(item['Nama'])
                    if employee_data:
                        current_shift_id = employee_data.get('shift_id', 1)
                    else:
                        current_shift_id = 1
                except:
                    current_shift_id = 1
            
            shift_index = shift_combo.findData(current_shift_id)
            if shift_index >= 0:
                shift_combo.setCurrentIndex(shift_index)
            
            # Update current_data dengan shift_id yang benar
            item['shift_id'] = current_shift_id
            
            # Connect change event
            shift_combo.currentIndexChanged.connect(
                lambda idx, r=row, combo=shift_combo: self.on_shift_changed(r, combo)
            )
            self.table.setCellWidget(row, 1, shift_combo)
            
            # Jam fields (editable)
            self.table.setItem(row, 2, QTableWidgetItem(item['Jam Masuk'] or ""))
            self.table.setItem(row, 3, QTableWidgetItem(item['Jam Keluar'] or ""))
            self.table.setItem(row, 4, QTableWidgetItem(item['Jam Masuk Lembur'] or ""))
            self.table.setItem(row, 5, QTableWidgetItem(item['Jam Keluar Lembur'] or ""))
            
            # Jam Anomali (read-only, display as comma-separated)
            anomali_text = ", ".join(item['Jam Anomali']) if item['Jam Anomali'] else ""
            anomali_item = QTableWidgetItem(anomali_text)
            anomali_item.setFlags(anomali_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 6, anomali_item)
            
            # Kelola Pelanggaran button dengan info total pelanggaran
            violations_widget = QWidget()
            violations_layout = QHBoxLayout(violations_widget)
            violations_layout.setContentsMargins(2, 2, 2, 2)
            violations_layout.setSpacing(5)
            
            # Tombol Kelola
            manage_btn = QPushButton("Kelola")
            manage_btn.setMaximumWidth(80)
            manage_btn.clicked.connect(lambda checked, r=row: self.manage_violations(r))
            violations_layout.addWidget(manage_btn)
            
            # Label total pelanggaran
            violations_count = 0
            if 'id' in item and item['id']:
                try:
                    violations = self.db_manager.get_violations_by_attendance(item['id'])
                    violations_count = len(violations) if violations else 0
                except:
                    pass
            
            count_label = QLabel(f"({violations_count} pelanggaran)")
            if violations_count > 0:
                count_label.setStyleSheet("color: red; font-weight: bold;")
            else:
                count_label.setStyleSheet("color: gray;")
            violations_layout.addWidget(count_label)
            
            violations_layout.addStretch()
            self.table.setCellWidget(row, 7, violations_widget)
    
    def on_item_changed(self, item):
        # Update current_data when table is edited
        row = item.row()
        col = item.column()
        
        if row < len(self.current_data):
            field_map = {
                2: 'Jam Masuk',
                3: 'Jam Keluar', 
                4: 'Jam Masuk Lembur',
                5: 'Jam Keluar Lembur'
            }
            
            if col in field_map:
                value = item.text().strip() if item.text().strip() else None
                self.current_data[row][field_map[col]] = value
    
    def on_shift_changed(self, row, combo):
        """Handle shift change for a specific row"""
        if row < len(self.current_data):
            shift_id = combo.currentData()
            shift_name = combo.currentText()
            
            # Update current_data
            self.current_data[row]['shift_id'] = shift_id
            self.current_data[row]['shift_name'] = shift_name
            
            # If this is existing data (has id), update database immediately
            if 'id' in self.current_data[row] and self.current_data[row]['id']:
                try:
                    self.db_manager.update_attendance_shift(self.current_data[row]['id'], shift_id)
                    print(f"✅ Shift updated for {self.current_data[row]['Nama']}: {shift_name}")
                except Exception as e:
                    print(f"❌ Failed to update shift: {e}")
                    QMessageBox.warning(self, "Warning", f"Gagal update shift: {str(e)}")
    
    def save_to_database(self):
        try:
            # Check database status first
            status = check_database_status()
            if status['locked']:
                reply = QMessageBox.question(
                    self, "Database Locked", 
                    "Database sedang terkunci. Apakah ingin mencoba force unlock?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    if force_unlock_database():
                        QMessageBox.information(self, "Success", "Database berhasil di-unlock!")
                    else:
                        QMessageBox.critical(self, "Error", "Gagal unlock database!")
                        return
                else:
                    return
            
            selected_date = self.date_edit.date().toString("yyyy-MM-dd")
            
            # Check if data already exists for this date
            existing_data = self.db_manager.get_attendance_by_date(selected_date)
            save_mode = 'replace'  # Default mode
            
            if existing_data:
                # Get summary of existing data
                summary = self.db_manager.get_attendance_summary_by_date(selected_date)
                
                # Create custom dialog for save options
                msg = QMessageBox()
                msg.setWindowTitle("Data Sudah Ada")
                msg.setIcon(QMessageBox.Question)
                msg.setText(f"Data absensi untuk tanggal {selected_date} sudah ada!\n\n"
                           f"Data yang ada: {summary['total_employees']} karyawan "
                           f"({summary['hadir']} hadir, {summary['tidak_hadir']} tidak hadir, {summary['lembur']} lembur)\n"
                           f"Data baru: {len(self.current_data)} karyawan\n\n"
                           "Pilih cara penyimpanan:")
                
                # Add custom buttons
                replace_btn = msg.addButton("Timpa Semua", QMessageBox.DestructiveRole)
                merge_btn = msg.addButton("Gabung/Update", QMessageBox.AcceptRole)
                add_only_btn = msg.addButton("Tambah Baru Saja", QMessageBox.AcceptRole)
                cancel_btn = msg.addButton("Batal", QMessageBox.RejectRole)
                
                msg.setDefaultButton(merge_btn)
                msg.exec()
                
                clicked_button = msg.clickedButton()
                
                if clicked_button == replace_btn:
                    save_mode = 'replace'
                elif clicked_button == merge_btn:
                    save_mode = 'merge'
                elif clicked_button == add_only_btn:
                    save_mode = 'insert_only'
                else:  # cancel_btn
                    return
            
            self.db_manager.save_attendance_data(selected_date, self.current_data, save_mode)
            
            # Show appropriate success message
            if existing_data:
                if save_mode == 'replace':
                    action = "ditimpa seluruhnya"
                elif save_mode == 'merge':
                    action = "digabung/diupdate"
                else:  # insert_only
                    action = "ditambahkan (data baru saja)"
            else:
                action = "disimpan"
                
            QMessageBox.information(self, "Sukses", f"Data berhasil {action} ke database")
            self.save_btn.setEnabled(False)
            
            # Refresh report tab
            if self.main_window:
                self.main_window.refresh_report_tab()
            
        except Exception as e:
            error_msg = str(e)
            if "database is locked" in error_msg.lower():
                reply = QMessageBox.question(
                    self, "Database Locked", 
                    f"Database terkunci: {error_msg}\n\nApakah ingin mencoba force unlock dan retry?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    if force_unlock_database():
                        # Retry save with default mode
                        try:
                            selected_date = self.date_edit.date().toString("yyyy-MM-dd")
                            self.db_manager.save_attendance_data(selected_date, self.current_data, 'replace')
                            QMessageBox.information(self, "Sukses", "Data berhasil disimpan setelah unlock database")
                            self.save_btn.setEnabled(False)
                            
                            # Refresh report tab
                            if self.main_window:
                                self.main_window.refresh_report_tab()
                        except Exception as retry_e:
                            QMessageBox.critical(self, "Error", f"Gagal menyimpan data setelah unlock:\n{str(retry_e)}")
                    else:
                        QMessageBox.critical(self, "Error", "Gagal unlock database!")
            else:
                QMessageBox.critical(self, "Error", f"Gagal menyimpan data:\n{error_msg}")
    
    def load_attendance_data(self):
        # Load existing data from database for selected date
        selected_date = self.date_edit.date().toString("yyyy-MM-dd")
        data = self.db_manager.get_attendance_by_date(selected_date)
        
        if data:
            self.current_data = data
            self.populate_table(data)
            self.add_violation_btn.setEnabled(True)
            # Aktifkan tombol Save/Update jika data sudah ada
            self.save_btn.setEnabled(True)
            self.save_btn.setText("Update Data")
        else:
            self.table.setRowCount(0)
            self.current_data = []
            self.add_violation_btn.setEnabled(False)
            # Reset tombol Save/Update
            self.save_btn.setEnabled(False)
            self.save_btn.setText("Save/Update Data")
    
    def refresh_data(self):
        """Refresh data dari database untuk tanggal yang dipilih"""
        try:
            # Simpan posisi scroll saat ini
            scroll_pos = self.table.verticalScrollBar().value()
            
            # Ambil tanggal yang dipilih
            selected_date = self.date_edit.date().toString("yyyy-MM-dd")
            
            # Tampilkan loading indicator
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            # Ambil data terbaru dari database
            data = self.db_manager.get_attendance_by_date(selected_date)
            
            if data:
                self.current_data = data
                self.populate_table(data)
                self.add_violation_btn.setEnabled(True)
                self.save_btn.setEnabled(True)
                self.save_btn.setText("Update Data")
                
                # Kembalikan posisi scroll
                self.table.verticalScrollBar().setValue(scroll_pos)
                
                # Tampilkan pesan sukses
                QMessageBox.information(self, "Refresh Berhasil", 
                                       f"Data untuk tanggal {self.date_edit.date().toString('dd MMMM yyyy')} berhasil dimuat ulang.\n\n"
                                       f"Total data: {len(data)} karyawan")
            else:
                self.table.setRowCount(0)
                self.current_data = []
                self.add_violation_btn.setEnabled(False)
                self.save_btn.setEnabled(False)
                self.save_btn.setText("Save/Update Data")
                
                # Tampilkan pesan tidak ada data
                QMessageBox.information(self, "Tidak Ada Data", 
                                       f"Tidak ada data absensi untuk tanggal {self.date_edit.date().toString('dd MMMM yyyy')}.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal memuat data:\n{str(e)}")
        finally:
            # Kembalikan cursor normal
            QApplication.restoreOverrideCursor()
    
    def add_violation(self):
        if not self.current_data:
            QMessageBox.warning(self, "Warning", "Tidak ada data karyawan untuk ditambahkan pelanggaran")
            return
        
        dialog = ViolationDialog(self.current_data, self)
        if dialog.exec() == QDialog.Accepted:
            violation_data = dialog.get_violation_data()
            
            # Find attendance_id based on employee name and date
            selected_date = self.date_edit.date().toString("yyyy-MM-dd")
            attendance_data = self.db_manager.get_attendance_by_date(selected_date)
            
            attendance_id = None
            for att in attendance_data:
                if att['Nama'] == violation_data['employee_name']:
                    attendance_id = att['id']
                    break
            
            if attendance_id:
                try:
                    self.db_manager.add_violation(
                        attendance_id,
                        violation_data['start_time'],
                        violation_data['end_time'], 
                        violation_data['description']
                    )
                    QMessageBox.information(self, "Sukses", "Pelanggaran berhasil ditambahkan")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Gagal menambah pelanggaran:\n{str(e)}")
            else:
                QMessageBox.warning(self, "Warning", "Data absensi karyawan tidak ditemukan")
    
    def manage_violations(self, row):
        """Open violation management dialog for selected employee"""
        if row >= len(self.current_data):
            QMessageBox.warning(self, "Warning", "Data karyawan tidak valid")
            return
        
        employee_data = self.current_data[row]
        employee_name = employee_data['Nama']
        
        # Get attendance_id from database
        selected_date = self.date_edit.date().toString("yyyy-MM-dd")
        attendance_data = self.db_manager.get_attendance_by_date(selected_date)
        
        attendance_id = None
        for att in attendance_data:
            if att['Nama'] == employee_name:
                attendance_id = att['id']
                break
        
        if attendance_id:
            dialog = ViolationManagementDialog(self.db_manager, attendance_id, employee_name, self)
            dialog.exec()
        else:
            QMessageBox.warning(self, "Warning", "Data absensi karyawan tidak ditemukan di database")
    
    def check_database_status(self):
        """Check dan tampilkan status database"""
        status = check_database_status()
        
        if status['status'] == 'OK':
            msg = f"✅ Database Status: OK\n"
            msg += f"📊 Tables: {status.get('table_count', 0)}\n"
            msg += f"📝 Journal Mode: {status.get('journal_mode', 'unknown')}\n"
            msg += f"🔓 Locked: No"
            QMessageBox.information(self, "Database Status", msg)
            
        elif status['locked']:
            msg = f"🔒 Database Status: LOCKED\n"
            msg += f"❌ Error: {status.get('error', 'Unknown')}\n\n"
            msg += "Apakah ingin mencoba force unlock?"
            
            reply = QMessageBox.question(
                self, "Database Locked", msg,
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                if force_unlock_database():
                    QMessageBox.information(self, "Success", "✅ Database berhasil di-unlock!")
                else:
                    QMessageBox.critical(self, "Error", "❌ Gagal unlock database!")
        else:
            msg = f"❌ Database Status: ERROR\n"
            msg += f"Error: {status.get('error', 'Unknown')}"
            QMessageBox.critical(self, "Database Error", msg)

class ReportTab(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
    
    def init_ui(self):
        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Settings
        left_panel = self.create_settings_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Reports
        right_panel = self.create_report_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([300, 500])
        
        layout = QVBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # Load employees
        self.load_employees()
    
    def create_settings_panel(self):
        group = QGroupBox("Info Shift Karyawan")
        layout = QVBoxLayout()
        
        # Info label
        info_label = QLabel("Shift akan otomatis diambil berdasarkan karyawan yang dipilih di panel laporan.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("QLabel { color: #666; font-style: italic; }")
        layout.addWidget(info_label)
        
        # Shift info display
        self.shift_info_display = QTextEdit()
        self.shift_info_display.setReadOnly(True)
        self.shift_info_display.setMaximumHeight(400)
        self.shift_info_display.setText("Pilih karyawan di panel laporan untuk melihat info shift")
        layout.addWidget(self.shift_info_display)
        
        group.setLayout(layout)
        return group
    
    def create_report_panel(self):
        group = QGroupBox("Generate Laporan")
        layout = QVBoxLayout()
        
        # Employee selection
        form_layout = QFormLayout()
        
        self.employee_combo = QComboBox()
        self.employee_combo.currentIndexChanged.connect(self.on_employee_changed)
        self.load_employees()
        form_layout.addRow("Pilih Karyawan:", self.employee_combo)
        
        # Date range dengan format Indonesia
        date_layout = QHBoxLayout()
        
        # Tanggal mulai dengan format Indonesia
        self.start_date = IndonesianDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        date_layout.addWidget(self.start_date)
        
        date_layout.addWidget(QLabel(" - "))
        
        # Tanggal akhir dengan format Indonesia
        self.end_date = IndonesianDateEdit()
        self.end_date.setDate(QDate.currentDate())
        date_layout.addWidget(self.end_date)
        
        form_layout.addRow("Periode:", date_layout)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh Data")
        self.refresh_btn.clicked.connect(self.refresh_employees)
        buttons_layout.addWidget(self.refresh_btn)
        
        # Generate button
        self.generate_btn = QPushButton("Generate Laporan")
        self.generate_btn.clicked.connect(self.generate_report)
        buttons_layout.addWidget(self.generate_btn)
        
        # Export button
        self.export_btn = QPushButton("Export Excel")
        self.export_btn.clicked.connect(self.export_to_excel)
        self.export_btn.setEnabled(False)  # Enable after generate
        buttons_layout.addWidget(self.export_btn)
        
        form_layout.addRow(buttons_layout)
        
        layout.addLayout(form_layout)
        
        # Report table
        self.report_table = QTableWidget()
        self.report_table.setColumnCount(13)  # Tambah kolom Loyalitas
        self.report_table.setHorizontalHeaderLabels([
            "Tanggal", "Jam Masuk", "Jam Keluar", "Jam Masuk Lembur", "Jam Keluar Lembur",
            "Jam Kerja", "Jam Lembur", "Loyalitas", "Overtime", "Keterlambatan", "Status", "Keterangan", "Pelanggaran"
        ])
        
        # Resize columns - ubah ke Interactive agar pengguna dapat mengubah ukuran kolom
        header = self.report_table.horizontalHeader()
        
        # Set semua kolom ke Interactive (bisa diubah ukurannya oleh user)
        for i in range(13):  # Semua kolom termasuk Loyalitas, keterangan dan pelanggaran
            header.setSectionResizeMode(i, QHeaderView.Interactive)
        
        # Set default width untuk kolom
        self.report_table.setColumnWidth(0, 100)  # Tanggal
        self.report_table.setColumnWidth(1, 80)   # Jam Masuk
        self.report_table.setColumnWidth(2, 80)   # Jam Keluar
        self.report_table.setColumnWidth(3, 120)  # Jam Masuk Lembur
        self.report_table.setColumnWidth(4, 120)  # Jam Keluar Lembur
        self.report_table.setColumnWidth(5, 100)  # Jam Kerja
        self.report_table.setColumnWidth(6, 100)  # Jam Lembur
        self.report_table.setColumnWidth(7, 100)  # Loyalitas
        self.report_table.setColumnWidth(8, 100)  # Overtime
        self.report_table.setColumnWidth(9, 100)  # Keterlambatan
        self.report_table.setColumnWidth(10, 80)  # Status
        self.report_table.setColumnWidth(11, 200) # Keterangan
        self.report_table.setColumnWidth(12, 300) # Pelanggaran
        
        # Enable stretching table to fill available space
        self.report_table.horizontalHeader().setStretchLastSection(True)
        
        # Enable sorting when clicking on headers
        self.report_table.setSortingEnabled(True)
        
        # Enable word wrap untuk semua cells
        self.report_table.setWordWrap(True)
        
        # Set row height yang cukup untuk multiple lines
        self.report_table.verticalHeader().setDefaultSectionSize(60)
        
        layout.addWidget(self.report_table)
        
        # Summary
        self.summary_label = QLabel("Pilih karyawan dan periode untuk melihat laporan")
        self.summary_label.setStyleSheet("font-weight: bold; padding: 10px;")
        layout.addWidget(self.summary_label)
        
        group.setLayout(layout)
        return group
    
    def format_time_duration(self, hours, unit_type="jam"):
        """Format time duration to 'X jam Y menit' or 'X menit' format"""
        if hours == 0:
            return "0 menit"
        
        total_minutes = int(hours * 60)
        jam = total_minutes // 60
        menit = total_minutes % 60
        
        if unit_type == "menit_only":
            return f"{total_minutes} menit"
        
        if jam > 0 and menit > 0:
            return f"{jam} jam {menit} menit"
        elif jam > 0:
            return f"{jam} jam"
        else:
            return f"{menit} menit"
    
    def update_shift_info_display(self, employee_id):
        """Update shift info display based on selected employee"""
        if not employee_id:
            self.shift_info_display.setText("Pilih karyawan untuk melihat info shift")
            return
        
        try:
            employees = self.db_manager.get_employees_with_shifts()
            employee_info = None
            for emp in employees:
                if emp['id'] == employee_id:
                    employee_info = emp
                    break
            
            if not employee_info or not employee_info['shift_id']:
                self.shift_info_display.setText(f"Karyawan {employee_info['name'] if employee_info else 'Unknown'} belum di-assign ke shift!")
                return
            
            shift_settings = self.db_manager.get_shift_by_id(employee_info['shift_id'])
            if not shift_settings:
                self.shift_info_display.setText("Data shift tidak ditemukan!")
                return
            
            # Format shift info
            shift_info = f"""KARYAWAN: {employee_info['name']}
SHIFT: {shift_settings['name']}

SENIN - JUMAT:
• Jam Kerja: {shift_settings['weekday_work_start']} - {shift_settings['weekday_work_end']}
• Jam Lembur: {shift_settings['weekday_overtime_start']} - {shift_settings['weekday_overtime_end']}
• Batas Overtime: {shift_settings['weekday_overtime_limit']}

SABTU:
• Jam Kerja: {shift_settings['saturday_work_start']} - {shift_settings['saturday_work_end']}
• Jam Lembur: {shift_settings['saturday_overtime_start']} - {shift_settings['saturday_overtime_end']}
• Batas Overtime: {shift_settings['saturday_overtime_limit']}

MINGGU:
• Hitung durasi kerja saja (tidak ada lembur/overtime)

PENGATURAN:
• Toleransi Terlambat: {shift_settings['late_tolerance']} menit
• Mode Overtime: {shift_settings['overtime_mode'].replace('_', ' ').title()}"""
            
            self.shift_info_display.setText(shift_info)
            
        except Exception as e:
            self.shift_info_display.setText(f"Error: {str(e)}")
    
    def load_employees(self):
        self.employee_combo.clear()
        employees = self.db_manager.get_all_employees()
        for emp in employees:
            self.employee_combo.addItem(emp['name'], emp['id'])
        
        # Update shift info for first employee if any
        if employees:
            self.update_shift_info_display(employees[0]['id'])
    
    def on_employee_changed(self):
        """Handle employee selection change"""
        employee_id = self.employee_combo.currentData()
        self.update_shift_info_display(employee_id)
    
    def refresh_employees(self):
        """Refresh employee list - dipanggil setelah save data baru"""
        current_selection = self.employee_combo.currentData()
        self.load_employees()
        
        # Restore selection if possible
        if current_selection:
            for i in range(self.employee_combo.count()):
                if self.employee_combo.itemData(i) == current_selection:
                    self.employee_combo.setCurrentIndex(i)
                    break
    
    def generate_report(self):
        if self.employee_combo.count() == 0:
            QMessageBox.warning(self, "Warning", "Tidak ada data karyawan")
            return
        
        employee_id = self.employee_combo.currentData()
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        
        # Get attendance data
        attendance_data = self.db_manager.get_attendance_by_employee_period(
            employee_id, start_date, end_date
        )
        
        if not attendance_data:
            QMessageBox.information(self, "Info", "Tidak ada data absensi untuk periode yang dipilih")
            return
        
        # Calculate and populate report
        self.calculate_and_populate_report(attendance_data)
    
    def calculate_and_populate_report(self, attendance_data):
        # Sekarang menggunakan shift per hari, bukan shift per karyawan
        employee_id = self.employee_combo.currentData()
        employee_name = self.employee_combo.currentText()
        
        self.report_table.setRowCount(len(attendance_data))
        
        total_jam_kerja = 0
        total_jam_lembur = 0
        total_loyalitas = 0
        total_overtime = 0
        total_terlambat = 0
        
        for row, data in enumerate(attendance_data):
            # Populate raw attendance data first
            self.report_table.setItem(row, 0, QTableWidgetItem(data['date']))
            self.report_table.setItem(row, 1, QTableWidgetItem(data['jam_masuk'] or "-"))
            self.report_table.setItem(row, 2, QTableWidgetItem(data['jam_keluar'] or "-"))
            self.report_table.setItem(row, 3, QTableWidgetItem(data['jam_masuk_lembur'] or "-"))
            self.report_table.setItem(row, 4, QTableWidgetItem(data['jam_keluar_lembur'] or "-"))
            
            # Get shift settings for this specific day (shift per hari)
            shift_id = data.get('shift_id', 1)  # Default to shift 1 if not set
            try:
                shift_settings = self.db_manager.get_shift_by_id(shift_id)
                if not shift_settings:
                    # Fallback to default shift
                    shift_settings = self.db_manager.get_shift_by_id(1)
            except:
                # Fallback to default shift
                shift_settings = self.db_manager.get_shift_by_id(1)
            
            # Calculate work hours, overtime, etc. with day detection
            from datetime import datetime
            date_obj = datetime.strptime(data['date'], '%Y-%m-%d')
            day_of_week = date_obj.weekday()  # 0=Monday, 6=Sunday
            
            jam_kerja = self.calculate_work_hours(data, shift_settings, day_of_week)
            jam_lembur = self.calculate_overtime_hours(data, shift_settings, day_of_week)
            loyalitas = self.calculate_loyalitas(data, shift_settings, day_of_week)
            overtime = self.calculate_overtime(data, shift_settings, day_of_week)
            terlambat = self.calculate_lateness(data, shift_settings, day_of_week)
            
            # Populate calculated data with new format "X jam Y menit"
            if day_of_week == 6:  # Sunday - only work duration
                jam_kerja_text = self.format_time_duration(jam_kerja)
                self.report_table.setItem(row, 5, QTableWidgetItem(jam_kerja_text))
                self.report_table.setItem(row, 6, QTableWidgetItem("-"))  # No lembur on Sunday
                self.report_table.setItem(row, 7, QTableWidgetItem("-"))  # No loyalitas on Sunday
                self.report_table.setItem(row, 8, QTableWidgetItem("-"))  # No overtime on Sunday
                self.report_table.setItem(row, 9, QTableWidgetItem("-"))  # No lateness on Sunday
            else:
                # Regular format for other days with new time format
                jam_kerja_text = self.format_time_duration(jam_kerja)
                jam_lembur_text = self.format_time_duration(jam_lembur)
                loyalitas_text = self.format_time_duration(loyalitas / 60, "menit_only") if loyalitas > 0 else "-"  # loyalitas is in minutes
                overtime_text = self.format_time_duration(overtime, "menit_only")
                terlambat_text = self.format_time_duration(terlambat / 60, "menit_only")  # terlambat is in minutes
                
                self.report_table.setItem(row, 5, QTableWidgetItem(jam_kerja_text))
                self.report_table.setItem(row, 6, QTableWidgetItem(jam_lembur_text))
                self.report_table.setItem(row, 7, QTableWidgetItem(loyalitas_text))
                self.report_table.setItem(row, 8, QTableWidgetItem(overtime_text))
                self.report_table.setItem(row, 9, QTableWidgetItem(terlambat_text))
            
            # Status
            status = "Hadir" if data['jam_masuk'] else "Tidak Hadir"
            self.report_table.setItem(row, 10, QTableWidgetItem(status))
            
            # Keterangan (catatan umum)
            keterangan = "-"  # Default kosong
            
            # Kolom Pelanggaran (khusus pelanggaran)
            pelanggaran = "-"  # Default kosong
            
            # Get violations for this attendance record
            if 'id' in data and data['id']:
                violations = self.db_manager.get_violations_by_attendance(data['id'])
                if violations:
                    # Format: setiap pelanggaran dalam baris terpisah (newline)
                    # "12:30:00-23:00:00 Tidur\n14:30:00-15:00:00 makan"
                    violation_details = []
                    for violation in violations:
                        start_time = violation['start_time']  # Already in HH:mm:ss format
                        end_time = violation['end_time']      # Already in HH:mm:ss format
                        description = violation['description']
                        violation_details.append(f"{start_time}-{end_time} {description}")
                    
                    # Untuk kolom keterangan tetap kosong atau bisa diisi catatan lain
                    # Untuk kolom pelanggaran diisi dengan detail pelanggaran
                    pelanggaran = "\n".join(violation_details)  # Use newline instead of " | "
            
            # Set keterangan dengan word wrap untuk text panjang
            keterangan_item = QTableWidgetItem(keterangan)
            keterangan_item.setToolTip(keterangan)  # Tooltip untuk text panjang
            self.report_table.setItem(row, 11, keterangan_item)
            
            # Set pelanggaran dengan word wrap untuk text panjang
            pelanggaran_item = QTableWidgetItem(pelanggaran)
            pelanggaran_item.setToolTip(pelanggaran)  # Tooltip untuk text panjang
            if pelanggaran != "-":
                pelanggaran_item.setForeground(QColor(255, 0, 0))  # Warna merah untuk pelanggaran
            self.report_table.setItem(row, 12, pelanggaran_item)
            
            # Add to totals (exclude Sunday from lembur, loyalitas, overtime, lateness)
            total_jam_kerja += jam_kerja
            if day_of_week != 6:  # Not Sunday
                total_jam_lembur += jam_lembur
                total_loyalitas += loyalitas
                total_overtime += overtime
                total_terlambat += terlambat
        
        # Update summary with new format including loyalitas
        employee_name = self.employee_combo.currentText()
        
        # Format totals using the new time format
        total_kerja_text = self.format_time_duration(total_jam_kerja)
        total_lembur_text = self.format_time_duration(total_jam_lembur)
        total_loyalitas_text = self.format_time_duration(total_loyalitas / 60, "menit_only") if total_loyalitas > 0 else "0 menit"  # loyalitas is in minutes
        total_overtime_text = self.format_time_duration(total_overtime, "menit_only")
        total_terlambat_text = self.format_time_duration(total_terlambat / 60, "menit_only")  # terlambat is in minutes
        
        summary_text = (f"Laporan: {employee_name} | "
                       f"Total Kerja: {total_kerja_text} | "
                       f"Total Lembur: {total_lembur_text} | "
                       f"Total Loyalitas: {total_loyalitas_text} | "
                       f"Total Overtime: {total_overtime_text} | "
                       f"Total Terlambat: {total_terlambat_text}")
        
        self.summary_label.setText(summary_text)
        
        # Enable export button after successful report generation
        self.export_btn.setEnabled(True)
    
    def calculate_work_hours(self, data, shift_settings, day_of_week):
        """Calculate work hours based on shift and day"""
        if not data['jam_masuk'] or not data['jam_keluar']:
            return 0.0
        
        try:
            masuk = datetime.strptime(data['jam_masuk'], "%H:%M")
            keluar = datetime.strptime(data['jam_keluar'], "%H:%M")
            
            if keluar > masuk:
                diff = keluar - masuk
                hours = diff.total_seconds() / 3600
                
                # For Sunday (6), just return actual hours worked
                if day_of_week == 6:
                    return hours
                
                # For other days, return calculated hours
                return hours
        except:
            pass
        
        return 0.0
    
    def calculate_overtime_hours(self, data, shift_settings, day_of_week):
        """Calculate overtime hours based on shift and day"""
        # Sunday has no overtime, only work duration
        if day_of_week == 6:
            return 0.0
            
        if not data['jam_masuk_lembur'] or not data['jam_keluar_lembur']:
            return 0.0
        
        try:
            masuk = datetime.strptime(data['jam_masuk_lembur'], "%H:%M")
            keluar = datetime.strptime(data['jam_keluar_lembur'], "%H:%M")
            
            if keluar > masuk:
                diff = keluar - masuk
                return diff.total_seconds() / 3600
        except:
            pass
        
        return 0.0
    
    def calculate_overtime(self, data, shift_settings, day_of_week):
        """Calculate overtime based on shift settings and day"""
        # Sunday has no overtime
        if day_of_week == 6:
            return 0.0
            
        if not data['jam_keluar']:
            return 0.0
        
        try:
            keluar = datetime.strptime(data['jam_keluar'], "%H:%M")
            
            # Get overtime limit based on day
            if day_of_week == 5:  # Saturday
                batas = datetime.strptime(shift_settings['saturday_overtime_limit'], "%H:%M")
            else:  # Monday-Friday
                batas = datetime.strptime(shift_settings['weekday_overtime_limit'], "%H:%M")
            
            # If there's lembur time, calculate overtime until jam_masuk_lembur
            if data['jam_masuk_lembur']:
                try:
                    jam_masuk_lembur = datetime.strptime(data['jam_masuk_lembur'], "%H:%M")
                    
                    # Overtime is from batas_overtime to jam_masuk_lembur (if keluar > batas)
                    if keluar > batas:
                        # Use the earlier time between jam_keluar and jam_masuk_lembur
                        end_overtime = min(keluar, jam_masuk_lembur)
                        
                        if end_overtime > batas:
                            diff = end_overtime - batas
                            minutes = diff.total_seconds() / 60
                            
                            if shift_settings['overtime_mode'] == 'per_jam':
                                return minutes // 60  # Only count full hours
                            else:
                                return minutes / 60  # Count all minutes
                except:
                    pass
            else:
                # No lembur, calculate normal overtime
                if keluar > batas:
                    diff = keluar - batas
                    minutes = diff.total_seconds() / 60
                    
                    if shift_settings['overtime_mode'] == 'per_jam':
                        return minutes // 60  # Only count full hours
                    else:
                        return minutes / 60  # Count all minutes
        except:
            pass
        
        return 0.0
    
    def calculate_loyalitas(self, data, shift_settings, day_of_week):
        """Calculate loyalitas: 30 menit - 1 jam lebih dari jam kerja normal"""
        # Sunday has no loyalitas calculation
        if day_of_week == 6:
            return 0.0
            
        if not data['jam_keluar']:
            return 0.0
        
        try:
            keluar = datetime.strptime(data['jam_keluar'], "%H:%M")
            
            # Get scheduled work end time based on day
            if day_of_week == 5:  # Saturday
                jadwal_selesai = datetime.strptime(shift_settings['saturday_work_end'], "%H:%M")
            else:  # Monday-Friday
                jadwal_selesai = datetime.strptime(shift_settings['weekday_work_end'], "%H:%M")
            
            # Calculate extra time worked
            if keluar > jadwal_selesai:
                extra_minutes = (keluar - jadwal_selesai).total_seconds() / 60
                
                # Loyalitas: 30 menit sampai 1 jam (60 menit)
                if 30 <= extra_minutes <= 60:
                    return extra_minutes
                # Jika lebih dari 1 jam, tidak ada loyalitas (sudah masuk overtime)
                elif extra_minutes > 60:
                    return 0.0
                    
        except:
            pass
        
        return 0.0
    
    def calculate_lateness(self, data, shift_settings, day_of_week):
        """Calculate lateness based on shift settings and day"""
        if not data['jam_masuk']:
            return 0.0
        
        try:
            masuk = datetime.strptime(data['jam_masuk'], "%H:%M")
            
            # Get scheduled start time based on day
            if day_of_week == 5:  # Saturday
                jadwal = datetime.strptime(shift_settings['saturday_work_start'], "%H:%M")
            elif day_of_week == 6:  # Sunday - no lateness calculation
                return 0.0
            else:  # Monday-Friday
                jadwal = datetime.strptime(shift_settings['weekday_work_start'], "%H:%M")
            
            # Apply tolerance
            tolerance_minutes = shift_settings['late_tolerance']
            jadwal_with_tolerance = jadwal + timedelta(minutes=tolerance_minutes)
            
            if masuk > jadwal_with_tolerance:
                diff = masuk - jadwal
                return diff.total_seconds() / 60
        except:
            pass
        
        return 0.0
    
    def calculate_loyalitas(self, data, shift_settings, day_of_week):
        """Calculate loyalitas (30 menit - 1 jam lebih dari jam kerja normal)"""
        if not data['jam_keluar'] or day_of_week == 6:  # No loyalitas on Sunday
            return 0.0
        
        try:
            keluar = datetime.strptime(data['jam_keluar'], "%H:%M")
            
            # Get scheduled end time based on day
            if day_of_week == 5:  # Saturday
                jadwal_keluar = datetime.strptime(shift_settings['saturday_work_end'], "%H:%M")
            else:  # Monday-Friday
                jadwal_keluar = datetime.strptime(shift_settings['weekday_work_end'], "%H:%M")
            
            if keluar > jadwal_keluar:
                # Calculate extra time in minutes
                extra_minutes = (keluar - jadwal_keluar).total_seconds() / 60
                
                # Loyalitas: 30 menit - 1 jam (60 menit)
                if 30 <= extra_minutes <= 60:
                    return extra_minutes
                # Jika lebih dari 1 jam, tidak ada loyalitas (sudah masuk overtime)
                elif extra_minutes > 60:
                    return 0.0
        except:
            pass
        
        return 0.0
    
    def generate_complete_date_range(self, start_date, end_date, attendance_data):
        """Generate complete date range with empty entries for missing dates"""
        from datetime import datetime, timedelta
        
        # Convert string dates to datetime objects
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Create dictionary of existing attendance data
        attendance_dict = {}
        for data in attendance_data:
            attendance_dict[data['date']] = data
        
        # Generate complete date range
        complete_data = []
        current_date = start_dt
        
        while current_date <= end_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
            
            if date_str in attendance_dict:
                # Use existing data
                complete_data.append(attendance_dict[date_str])
            else:
                # Create empty entry for missing date
                empty_entry = {
                    'id': None,
                    'date': date_str,
                    'jam_masuk': None,
                    'jam_keluar': None,
                    'jam_masuk_lembur': None,
                    'jam_keluar_lembur': None,
                    'shift_id': 1,  # Default shift
                    'day_name': current_date.strftime("%A"),  # Day name for reference
                    'is_sunday': day_of_week == 6  # Mark Sunday
                }
                complete_data.append(empty_entry)
            
            current_date += timedelta(days=1)
        
        return complete_data
    
    def export_to_excel(self):
        """Export laporan ke file Excel dengan tanggal lengkap termasuk hari kosong"""
        if self.report_table.rowCount() == 0:
            QMessageBox.warning(self, "Warning", "Tidak ada data untuk diekspor. Generate laporan terlebih dahulu.")
            return
        
        # Get file path from user
        employee_name = self.employee_combo.currentText()
        employee_id = self.employee_combo.currentData()
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        
        # Get attendance data with complete date range
        attendance_data = self.db_manager.get_attendance_by_employee_period(
            employee_id, start_date, end_date
        )
        complete_data = self.generate_complete_date_range(start_date, end_date, attendance_data)
        
        default_filename = f"Laporan_Absensi_{employee_name}_{start_date}_to_{end_date}.xlsx"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Laporan ke Excel", default_filename, "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            # Create workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Laporan Absensi"
            
            # Define styles
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"), 
                top=Side(style="thin"),
                bottom=Side(style="thin")
            )
            
            # Add title
            ws.merge_cells("A1:M1")  # Tambahkan kolom M untuk loyalitas dan pelanggaran
            title_cell = ws["A1"]
            title_cell.value = f"LAPORAN ABSENSI - {employee_name.upper()}"
            title_cell.font = Font(bold=True, size=14)
            title_cell.alignment = Alignment(horizontal="center")
            
            # Add period info
            ws.merge_cells("A2:M2")  # Tambahkan kolom M untuk loyalitas dan pelanggaran
            period_cell = ws["A2"]
            period_cell.value = f"Periode: {start_date} s/d {end_date} (Termasuk hari kosong)"
            period_cell.font = Font(bold=True)
            period_cell.alignment = Alignment(horizontal="center")
            
            # Add headers
            headers = [
                "Tanggal", "Jam Masuk", "Jam Keluar", "Jam Masuk Lembur", "Jam Keluar Lembur",
                "Jam Kerja", "Jam Lembur", "Loyalitas", "Overtime", "Keterlambatan", "Status", "Keterangan", "Pelanggaran"
            ]
            
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=4, column=col)
                cell.value = header
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = border
            
            # Add data using complete_data (includes empty dates)
            for row, data in enumerate(complete_data):
                # Get shift settings for this day
                shift_id = data.get('shift_id', 1)
                try:
                    shift_settings = self.db_manager.get_shift_by_id(shift_id)
                    if not shift_settings:
                        shift_settings = self.db_manager.get_shift_by_id(1)
                except:
                    shift_settings = self.db_manager.get_shift_by_id(1)
                
                # Calculate values for this day
                from datetime import datetime
                date_obj = datetime.strptime(data['date'], '%Y-%m-%d')
                day_of_week = date_obj.weekday()  # 0=Monday, 6=Sunday
                
                # Basic data
                excel_row = row + 5
                ws.cell(row=excel_row, column=1).value = data['date']
                ws.cell(row=excel_row, column=2).value = data['jam_masuk'] or "-"
                ws.cell(row=excel_row, column=3).value = data['jam_keluar'] or "-"
                ws.cell(row=excel_row, column=4).value = data['jam_masuk_lembur'] or "-"
                ws.cell(row=excel_row, column=5).value = data['jam_keluar_lembur'] or "-"
                
                # Calculate derived values only if there's attendance data
                if data['jam_masuk'] or data['jam_keluar']:
                    jam_kerja = self.calculate_work_hours(data, shift_settings, day_of_week)
                    jam_lembur = self.calculate_overtime_hours(data, shift_settings, day_of_week)
                    loyalitas = self.calculate_loyalitas(data, shift_settings, day_of_week)
                    overtime = self.calculate_overtime(data, shift_settings, day_of_week)
                    terlambat = self.calculate_lateness(data, shift_settings, day_of_week)
                    
                    ws.cell(row=excel_row, column=6).value = self.format_time_duration(jam_kerja)
                    ws.cell(row=excel_row, column=7).value = self.format_time_duration(jam_lembur) if jam_lembur > 0 else "-"
                    ws.cell(row=excel_row, column=8).value = self.format_time_duration(loyalitas / 60, "menit_only") if loyalitas > 0 else "-"
                    ws.cell(row=excel_row, column=9).value = self.format_time_duration(overtime, "menit_only") if overtime > 0 else "-"
                    ws.cell(row=excel_row, column=10).value = self.format_time_duration(terlambat / 60, "menit_only") if terlambat > 0 else "-"
                    ws.cell(row=excel_row, column=11).value = "Hadir"
                else:
                    # Empty day
                    ws.cell(row=excel_row, column=6).value = "-"
                    ws.cell(row=excel_row, column=7).value = "-"
                    ws.cell(row=excel_row, column=8).value = "-"
                    ws.cell(row=excel_row, column=9).value = "-"
                    ws.cell(row=excel_row, column=10).value = "-"
                    
                    # Mark Sunday or empty day
                    if day_of_week == 6:  # Sunday
                        ws.cell(row=excel_row, column=11).value = "Minggu"
                        # Color Sunday rows differently
                        for col in range(1, 14):
                            ws.cell(row=excel_row, column=col).fill = PatternFill(start_color="F0F0F0", end_color="F0F0F0", fill_type="solid")
                    else:
                        ws.cell(row=excel_row, column=11).value = "Tidak Hadir"
                
                # Keterangan and Pelanggaran
                ws.cell(row=excel_row, column=12).value = "-"  # Keterangan
                
                # Get violations if data exists
                pelanggaran = "-"
                if data.get('id'):
                    violations = self.db_manager.get_violations_by_attendance(data['id'])
                    if violations:
                        violation_details = []
                        for violation in violations:
                            violation_details.append(f"{violation['start_time']}-{violation['end_time']} {violation['description']}")
                        pelanggaran = "\n".join(violation_details)
                
                pelanggaran_cell = ws.cell(row=excel_row, column=13)
                pelanggaran_cell.value = pelanggaran
                if pelanggaran != "-":
                    pelanggaran_cell.font = Font(color="FF0000")  # Red color for violations
                
                # Apply borders to all cells
                for col in range(1, 14):
                    ws.cell(row=excel_row, column=col).border = border
                    
                    # Center align for certain columns
                    if col in [1, 2, 3, 4, 5, 11]:  # Date, time columns, status
                        ws.cell(row=excel_row, column=col).alignment = Alignment(horizontal="center")
                    elif col == 13:  # Pelanggaran column
                        ws.cell(row=excel_row, column=col).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
                        if '\n' in pelanggaran:
                            line_count = pelanggaran.count('\n') + 1
                            ws.row_dimensions[excel_row].height = max(15 * line_count, 30)
                    else:
                        ws.cell(row=excel_row, column=col).alignment = Alignment(horizontal="left", vertical="center")
            
            # Add summary
            summary_row = len(complete_data) + 6
            ws.merge_cells(f"A{summary_row}:M{summary_row}")  # Tambahkan kolom M untuk loyalitas
            summary_cell = ws[f"A{summary_row}"]
            summary_cell.value = f"Laporan lengkap periode {start_date} s/d {end_date} - Total {len(complete_data)} hari (termasuk hari kosong)"
            summary_cell.font = Font(bold=True)
            summary_cell.alignment = Alignment(horizontal="center")
            
            # Add shift rules section
            self.add_shift_rules_to_excel(ws, summary_row + 2)
            
            # Auto-adjust column widths
            from openpyxl.utils import get_column_letter
            for col_num in range(1, 14):  # Columns A to M (1 to 13)
                column_letter = get_column_letter(col_num)
                max_length = 0
                
                # Check all cells in this column
                for row_num in range(1, ws.max_row + 1):
                    cell = ws.cell(row=row_num, column=col_num)
                    # Skip merged cells
                    if hasattr(cell, 'coordinate') and cell.coordinate in ws.merged_cells:
                        continue
                    try:
                        if cell.value and len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                # Set column width (minimum 10, maximum 25, except for Pelanggaran column)
                if col_num == 13:  # Kolom Pelanggaran (index 13 dalam Excel)
                    # Kolom pelanggaran dibuat lebih lebar untuk menampung detail pelanggaran
                    adjusted_width = min(max(max_length + 2, 40), 60)
                else:
                    adjusted_width = min(max(max_length + 2, 10), 25)
                
                ws.column_dimensions[column_letter].width = adjusted_width
            
            # Save workbook
            wb.save(file_path)
            
            QMessageBox.information(
                self, "Export Berhasil", 
                f"Laporan berhasil diekspor ke:\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal mengekspor laporan:\n{str(e)}")
    
    def add_shift_rules_to_excel(self, ws, start_row):
        """Add shift rules section to Excel"""
        try:
            # Get employee shift info
            employee_id = self.employee_combo.currentData()
            employees = self.db_manager.get_employees_with_shifts()
            employee_info = None
            for emp in employees:
                if emp['id'] == employee_id:
                    employee_info = emp
                    break
            
            if not employee_info or not employee_info['shift_id']:
                return
            
            shift_settings = self.db_manager.get_shift_by_id(employee_info['shift_id'])
            if not shift_settings:
                return
            
            # Title
            ws.merge_cells(f"A{start_row}:M{start_row}")  # Tambahkan kolom M untuk loyalitas
            title_cell = ws[f"A{start_row}"]
            title_cell.value = "PERATURAN SHIFT"
            title_cell.font = Font(bold=True, size=12)
            title_cell.alignment = Alignment(horizontal="center")
            
            current_row = start_row + 2
            
            # Shift name
            ws.merge_cells(f"A{current_row}:M{current_row}")  # Tambahkan kolom M untuk loyalitas
            shift_name_cell = ws[f"A{current_row}"]
            shift_name_cell.value = f"SHIFT: {shift_settings['name']}"
            shift_name_cell.font = Font(bold=True)
            shift_name_cell.alignment = Alignment(horizontal="center")
            
            current_row += 2
            
            # Weekday rules
            ws.merge_cells(f"A{current_row}:L{current_row}")  # Tambahkan kolom L untuk pelanggaran
            weekday_title = ws[f"A{current_row}"]
            weekday_title.value = "SENIN - JUMAT:"
            weekday_title.font = Font(bold=True)
            
            current_row += 1
            
            weekday_rules = [
                f"• Jam Masuk Kerja: {shift_settings['weekday_work_start']}",
                f"• Jam Keluar Kerja: {shift_settings['weekday_work_end']}",
                f"• Jam Masuk Lembur: {shift_settings['weekday_overtime_start']}",
                f"• Jam Keluar Lembur: {shift_settings['weekday_overtime_end']}",
                f"• Batas Overtime: {shift_settings['weekday_overtime_limit']}"
            ]
            
            for rule in weekday_rules:
                ws.merge_cells(f"A{current_row}:M{current_row}")  # Tambahkan kolom M untuk loyalitas
                rule_cell = ws[f"A{current_row}"]
                rule_cell.value = rule
                current_row += 1
            
            current_row += 1
            
            # Saturday rules
            ws.merge_cells(f"A{current_row}:L{current_row}")  # Tambahkan kolom L untuk pelanggaran
            saturday_title = ws[f"A{current_row}"]
            saturday_title.value = "SABTU:"
            saturday_title.font = Font(bold=True)
            
            current_row += 1
            
            saturday_rules = [
                f"• Jam Masuk Kerja: {shift_settings['saturday_work_start']}",
                f"• Jam Keluar Kerja: {shift_settings['saturday_work_end']}",
                f"• Jam Masuk Lembur: {shift_settings['saturday_overtime_start']}",
                f"• Jam Keluar Lembur: {shift_settings['saturday_overtime_end']}",
                f"• Batas Overtime: {shift_settings['saturday_overtime_limit']}"
            ]
            
            for rule in saturday_rules:
                ws.merge_cells(f"A{current_row}:M{current_row}")  # Tambahkan kolom M untuk loyalitas
                rule_cell = ws[f"A{current_row}"]
                rule_cell.value = rule
                current_row += 1
            
            current_row += 1
            
            # Sunday and general rules
            ws.merge_cells(f"A{current_row}:L{current_row}")  # Tambahkan kolom L untuk pelanggaran
            sunday_title = ws[f"A{current_row}"]
            sunday_title.value = "MINGGU:"
            sunday_title.font = Font(bold=True)
            
            current_row += 1
            
            ws.merge_cells(f"A{current_row}:L{current_row}")  # Tambahkan kolom L untuk pelanggaran
            sunday_rule = ws[f"A{current_row}"]
            sunday_rule.value = "• Hitung durasi kerja saja (tidak ada lembur/overtime)"
            
            current_row += 2
            
            # General settings
            ws.merge_cells(f"A{current_row}:L{current_row}")  # Tambahkan kolom L untuk pelanggaran
            general_title = ws[f"A{current_row}"]
            general_title.value = "PENGATURAN UMUM:"
            general_title.font = Font(bold=True)
            
            current_row += 1
            
            general_rules = [
                f"• Toleransi Keterlambatan: {shift_settings['late_tolerance']} menit",
                f"• Mode Overtime: {shift_settings['overtime_mode'].replace('_', ' ').title()}"
            ]
            
            for rule in general_rules:
                ws.merge_cells(f"A{current_row}:M{current_row}")  # Tambahkan kolom M untuk loyalitas
                rule_cell = ws[f"A{current_row}"]
                rule_cell.value = rule
                current_row += 1
                
        except Exception as e:
            print(f"Error adding shift rules: {e}")

class ShiftManagementTab(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout()
        
        # Left panel: Shift Settings
        left_panel = QGroupBox("Pengaturan Shift")
        left_layout = QVBoxLayout(left_panel)
        
        # Shift selector and CRUD buttons
        shift_selector_layout = QHBoxLayout()
        shift_selector_layout.addWidget(QLabel("Pilih Shift:"))
        self.shift_combo = QComboBox()
        self.shift_combo.currentIndexChanged.connect(self.load_shift_settings)
        shift_selector_layout.addWidget(self.shift_combo)
        
        left_layout.addLayout(shift_selector_layout)
        
        # CRUD buttons
        crud_layout = QHBoxLayout()
        
        create_shift_btn = QPushButton("➕ Buat Shift Baru")
        create_shift_btn.clicked.connect(self.create_shift)
        crud_layout.addWidget(create_shift_btn)
        
        edit_shift_btn = QPushButton("✏️ Edit Shift")
        edit_shift_btn.clicked.connect(self.edit_shift)
        crud_layout.addWidget(edit_shift_btn)
        
        delete_shift_btn = QPushButton("🗑️ Hapus Shift")
        delete_shift_btn.clicked.connect(self.delete_shift)
        crud_layout.addWidget(delete_shift_btn)
        
        left_layout.addLayout(crud_layout)
        
        # Shift details display
        self.shift_details = QTextEdit()
        self.shift_details.setReadOnly(True)
        self.shift_details.setMaximumHeight(300)
        left_layout.addWidget(self.shift_details)
        
        # Right panel: Employee Assignment
        right_panel = QGroupBox("Assignment Karyawan ke Shift")
        right_layout = QVBoxLayout(right_panel)
        
        # Employee table
        self.employee_table = QTableWidget()
        self.employee_table.setColumnCount(3)
        self.employee_table.setHorizontalHeaderLabels(["Nama Karyawan", "Shift Saat Ini", "Aksi"])
        
        # Table settings - ubah ke Interactive agar pengguna dapat mengubah ukuran kolom
        header = self.employee_table.horizontalHeader()
        
        # Set semua kolom ke Interactive (bisa diubah ukurannya oleh user)
        for i in range(3):  # Semua kolom
            header.setSectionResizeMode(i, QHeaderView.Interactive)
        
        # Set default width untuk kolom
        self.employee_table.setColumnWidth(0, 250)  # Nama Karyawan
        self.employee_table.setColumnWidth(1, 150)  # Shift Saat Ini
        self.employee_table.setColumnWidth(2, 150)  # Aksi
        
        # Enable stretching table to fill available space
        self.employee_table.horizontalHeader().setStretchLastSection(True)
        
        right_layout.addWidget(self.employee_table)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh Data")
        refresh_btn.clicked.connect(self.load_data)
        right_layout.addWidget(refresh_btn)
        
        # Add panels to main layout
        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
        
        self.setLayout(layout)
        
        # Load initial data
        self.load_data()
    
    def load_data(self):
        """Load shifts and employees data"""
        self.load_shifts()
        self.load_employees()
    
    def load_shifts(self):
        """Load all shifts to combo box"""
        self.shift_combo.clear()
        try:
            shifts = self.db_manager.get_all_shifts()
            for shift in shifts:
                self.shift_combo.addItem(shift['name'], shift['id'])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal memuat data shift: {str(e)}")
    
    def load_shift_settings(self):
        """Load and display shift settings"""
        shift_id = self.shift_combo.currentData()
        if not shift_id:
            return
        
        try:
            shift = self.db_manager.get_shift_by_id(shift_id)
            if shift:
                details = f"""
SHIFT: {shift['name']}

SENIN - JUMAT:
• Jam Kerja: {shift['weekday_work_start']} - {shift['weekday_work_end']}
• Jam Lembur: {shift['weekday_overtime_start']} - {shift['weekday_overtime_end']}
• Batas Overtime: {shift['weekday_overtime_limit']}

SABTU:
• Jam Kerja: {shift['saturday_work_start']} - {shift['saturday_work_end']}
• Jam Lembur: {shift['saturday_overtime_start']} - {shift['saturday_overtime_end']}
• Batas Overtime: {shift['saturday_overtime_limit']}

PENGATURAN:
• Toleransi Terlambat: {shift['late_tolerance']} menit
• Mode Overtime: {shift['overtime_mode']}
                """.strip()
                
                self.shift_details.setText(details)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal memuat pengaturan shift: {str(e)}")
    
    def load_employees(self):
        """Load employees with their shift assignments"""
        try:
            employees = self.db_manager.get_employees_with_shifts()
            shifts = self.db_manager.get_all_shifts()
            
            self.employee_table.setRowCount(len(employees))
            
            for row, emp in enumerate(employees):
                # Name
                self.employee_table.setItem(row, 0, QTableWidgetItem(emp['name']))
                
                # Current shift
                self.employee_table.setItem(row, 1, QTableWidgetItem(emp['shift_name']))
                
                # Action: Change shift combo
                shift_combo = QComboBox()
                for shift in shifts:
                    shift_combo.addItem(shift['name'], shift['id'])
                
                # Set current shift
                if emp['shift_id']:
                    index = shift_combo.findData(emp['shift_id'])
                    if index >= 0:
                        shift_combo.setCurrentIndex(index)
                
                # Connect change event
                shift_combo.currentIndexChanged.connect(
                    lambda idx, emp_id=emp['id'], combo=shift_combo: self.change_employee_shift(emp_id, combo)
                )
                
                self.employee_table.setCellWidget(row, 2, shift_combo)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal memuat data karyawan: {str(e)}")
    
    def change_employee_shift(self, employee_id, combo):
        """Change employee shift assignment"""
        new_shift_id = combo.currentData()
        if new_shift_id:
            try:
                self.db_manager.assign_employee_shift(employee_id, new_shift_id)
                QMessageBox.information(self, "Sukses", "Shift karyawan berhasil diubah!")
                self.load_employees()  # Refresh
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal mengubah shift karyawan: {str(e)}")
    
    def create_shift(self):
        """Buat shift baru"""
        # Default data untuk shift baru
        default_data = {
            'name': 'Shift Baru',
            'weekday_work_start': '08:00',
            'weekday_work_end': '16:00',
            'weekday_overtime_start': '16:00',
            'weekday_overtime_end': '20:00',
            'weekday_overtime_limit': '17:00',
            'saturday_work_start': '08:00',
            'saturday_work_end': '12:00',
            'saturday_overtime_start': '12:00',
            'saturday_overtime_end': '16:00',
            'saturday_overtime_limit': '13:00',
            'late_tolerance': 15,
            'overtime_mode': 'per_jam'
        }
        
        dialog = ShiftEditDialog(default_data, self, is_create=True)
        if dialog.exec() == QDialog.Accepted:
            try:
                shift_data = dialog.get_shift_data()
                shift_id = self.db_manager.create_shift(shift_data)
                
                QMessageBox.information(self, "Success", f"Shift '{shift_data['name']}' berhasil dibuat!")
                self.load_shifts()
                
                # Select the newly created shift
                for i in range(self.shift_combo.count()):
                    if self.shift_combo.itemData(i) == shift_id:
                        self.shift_combo.setCurrentIndex(i)
                        break
                        
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal membuat shift: {str(e)}")

    def edit_shift(self):
        """Open shift edit dialog"""
        shift_id = self.shift_combo.currentData()
        if not shift_id:
            QMessageBox.warning(self, "Warning", "Pilih shift terlebih dahulu!")
            return
        
        try:
            shift = self.db_manager.get_shift_by_id(shift_id)
            if shift:
                dialog = ShiftEditDialog(shift, self, is_create=False)
                if dialog.exec() == QDialog.Accepted:
                    updated_shift = dialog.get_shift_data()
                    self.db_manager.update_shift(shift_id, updated_shift)
                    QMessageBox.information(self, "Sukses", "Pengaturan shift berhasil diupdate!")
                    self.load_shifts()  # Refresh combo
                    self.load_shift_settings()  # Refresh display
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal mengedit shift: {str(e)}")
    
    def delete_shift(self):
        """Hapus shift yang dipilih"""
        current_shift_id = self.shift_combo.currentData()
        if not current_shift_id:
            QMessageBox.warning(self, "Warning", "Pilih shift terlebih dahulu!")
            return
        
        shift_name = self.shift_combo.currentText()
        
        reply = QMessageBox.question(
            self, 
            "Konfirmasi Hapus", 
            f"Apakah Anda yakin ingin menghapus shift '{shift_name}'?\n\nShift yang sedang digunakan karyawan tidak dapat dihapus.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.delete_shift(current_shift_id)
                QMessageBox.information(self, "Success", f"Shift '{shift_name}' berhasil dihapus!")
                self.load_shifts()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal menghapus shift: {str(e)}")


class ShiftEditDialog(QDialog):
    def __init__(self, shift_data, parent=None, is_create=False):
        super().__init__(parent)
        self.shift_data = shift_data
        self.is_create = is_create
        
        if is_create:
            self.setWindowTitle("Buat Shift Baru")
        else:
            self.setWindowTitle(f"Edit {shift_data['name']}")
            
        self.setModal(True)
        self.resize(500, 600)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Shift name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nama Shift:"))
        self.name_edit = QLineEdit(self.shift_data['name'])
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Weekday settings
        weekday_group = QGroupBox("Pengaturan Senin - Jumat")
        weekday_layout = QFormLayout()
        
        self.weekday_work_start = QTimeEdit()
        self.weekday_work_start.setDisplayFormat("HH:mm")
        self.weekday_work_start.setTime(QTime.fromString(self.shift_data['weekday_work_start'], "HH:mm"))
        weekday_layout.addRow("Jam Masuk Kerja:", self.weekday_work_start)
        
        self.weekday_work_end = QTimeEdit()
        self.weekday_work_end.setDisplayFormat("HH:mm")
        self.weekday_work_end.setTime(QTime.fromString(self.shift_data['weekday_work_end'], "HH:mm"))
        weekday_layout.addRow("Jam Keluar Kerja:", self.weekday_work_end)
        
        self.weekday_overtime_start = QTimeEdit()
        self.weekday_overtime_start.setDisplayFormat("HH:mm")
        self.weekday_overtime_start.setTime(QTime.fromString(self.shift_data['weekday_overtime_start'], "HH:mm"))
        weekday_layout.addRow("Jam Masuk Lembur:", self.weekday_overtime_start)
        
        self.weekday_overtime_end = QTimeEdit()
        self.weekday_overtime_end.setDisplayFormat("HH:mm")
        self.weekday_overtime_end.setTime(QTime.fromString(self.shift_data['weekday_overtime_end'], "HH:mm"))
        weekday_layout.addRow("Jam Keluar Lembur:", self.weekday_overtime_end)
        
        self.weekday_overtime_limit = QTimeEdit()
        self.weekday_overtime_limit.setDisplayFormat("HH:mm")
        self.weekday_overtime_limit.setTime(QTime.fromString(self.shift_data['weekday_overtime_limit'], "HH:mm"))
        weekday_layout.addRow("Batas Overtime:", self.weekday_overtime_limit)
        
        weekday_group.setLayout(weekday_layout)
        layout.addWidget(weekday_group)
        
        # Saturday settings
        saturday_group = QGroupBox("Pengaturan Sabtu")
        saturday_layout = QFormLayout()
        
        self.saturday_work_start = QTimeEdit()
        self.saturday_work_start.setDisplayFormat("HH:mm")
        self.saturday_work_start.setTime(QTime.fromString(self.shift_data['saturday_work_start'], "HH:mm"))
        saturday_layout.addRow("Jam Masuk Kerja:", self.saturday_work_start)
        
        self.saturday_work_end = QTimeEdit()
        self.saturday_work_end.setDisplayFormat("HH:mm")
        self.saturday_work_end.setTime(QTime.fromString(self.shift_data['saturday_work_end'], "HH:mm"))
        saturday_layout.addRow("Jam Keluar Kerja:", self.saturday_work_end)
        
        self.saturday_overtime_start = QTimeEdit()
        self.saturday_overtime_start.setDisplayFormat("HH:mm")
        self.saturday_overtime_start.setTime(QTime.fromString(self.shift_data['saturday_overtime_start'], "HH:mm"))
        saturday_layout.addRow("Jam Masuk Lembur:", self.saturday_overtime_start)
        
        self.saturday_overtime_end = QTimeEdit()
        self.saturday_overtime_end.setDisplayFormat("HH:mm")
        self.saturday_overtime_end.setTime(QTime.fromString(self.shift_data['saturday_overtime_end'], "HH:mm"))
        saturday_layout.addRow("Jam Keluar Lembur:", self.saturday_overtime_end)
        
        self.saturday_overtime_limit = QTimeEdit()
        self.saturday_overtime_limit.setDisplayFormat("HH:mm")
        self.saturday_overtime_limit.setTime(QTime.fromString(self.shift_data['saturday_overtime_limit'], "HH:mm"))
        saturday_layout.addRow("Batas Overtime:", self.saturday_overtime_limit)
        
        saturday_group.setLayout(saturday_layout)
        layout.addWidget(saturday_group)
        
        # General settings
        general_group = QGroupBox("Pengaturan Umum")
        general_layout = QFormLayout()
        
        self.late_tolerance = QSpinBox()
        self.late_tolerance.setRange(0, 120)
        self.late_tolerance.setValue(self.shift_data['late_tolerance'])
        general_layout.addRow("Toleransi Terlambat (menit):", self.late_tolerance)
        
        overtime_group = QGroupBox("Mode Overtime")
        overtime_layout = QVBoxLayout()
        
        self.overtime_per_menit = QRadioButton("Per Menit")
        self.overtime_per_jam = QRadioButton("Per Jam (≥60 menit)")
        
        if self.shift_data['overtime_mode'] == 'per_menit':
            self.overtime_per_menit.setChecked(True)
        else:
            self.overtime_per_jam.setChecked(True)
        
        overtime_layout.addWidget(self.overtime_per_menit)
        overtime_layout.addWidget(self.overtime_per_jam)
        overtime_group.setLayout(overtime_layout)
        
        general_layout.addRow(overtime_group)
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_shift_data(self):
        return {
            'name': self.name_edit.text(),
            'weekday_work_start': self.weekday_work_start.time().toString("HH:mm"),
            'weekday_work_end': self.weekday_work_end.time().toString("HH:mm"),
            'weekday_overtime_start': self.weekday_overtime_start.time().toString("HH:mm"),
            'weekday_overtime_end': self.weekday_overtime_end.time().toString("HH:mm"),
            'weekday_overtime_limit': self.weekday_overtime_limit.time().toString("HH:mm"),
            'saturday_work_start': self.saturday_work_start.time().toString("HH:mm"),
            'saturday_work_end': self.saturday_work_end.time().toString("HH:mm"),
            'saturday_overtime_start': self.saturday_overtime_start.time().toString("HH:mm"),
            'saturday_overtime_end': self.saturday_overtime_end.time().toString("HH:mm"),
            'saturday_overtime_limit': self.saturday_overtime_limit.time().toString("HH:mm"),
            'late_tolerance': self.late_tolerance.value(),
            'overtime_mode': 'per_menit' if self.overtime_per_menit.isChecked() else 'per_jam'
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Aplikasi Absensi")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Add tabs
        self.attendance_tab = AttendanceInputTab(self.db_manager, self)
        self.report_tab = ReportTab(self.db_manager)
        self.shift_tab = ShiftManagementTab(self.db_manager)
        
        self.tab_widget.addTab(self.attendance_tab, "Input Absensi Harian")
        self.tab_widget.addTab(self.report_tab, "Generate Laporan")
        self.tab_widget.addTab(self.shift_tab, "Management Shift")
        
        self.setCentralWidget(self.tab_widget)
    
    def refresh_report_tab(self):
        """Refresh report tab setelah data baru disimpan"""
        self.report_tab.refresh_employees()

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
