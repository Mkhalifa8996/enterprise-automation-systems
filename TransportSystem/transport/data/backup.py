# -*- coding: utf-8 -*-
"""النسخ الاحتياطي والاستعادة ومزامنة ملف Excel."""

import json, os, shutil
from datetime import date
from datetime import datetime
from openpyxl import load_workbook
from .paths import BACKUP_DIR, BACKUP_FILE, DATA_FILE
from .core import CORE_SHEET_KEYS, _connect, _current_role, _ensure_database, _headers_for, _invalidate_rows_cache, _mark_local_change, ensure_workbook, missing_sheets_in_workbook
from .schema import SHEETS

def _export_database_to_excel():
    """Refresh the workbook and its backup from the fast SQLite store."""
    ensure_workbook()
    connection = _connect()
    try:
        rows_by_sheet = {}
        for sheet_key in SHEETS:
            rows_by_sheet[sheet_key] = [
                json.loads(item[0]) for item in connection.execute(
                    "SELECT data_json FROM records WHERE sheet_key = ? ORDER BY rowid",
                    (sheet_key,),
                )
            ]
    finally:
        connection.close()

    wb = load_workbook(DATA_FILE)
    for sheet_key, sheet_name in SHEETS.items():
        ws = wb[sheet_name]
        if ws.max_row > 1:
            ws.delete_rows(2, ws.max_row - 1)
        fields = _headers_for(sheet_key)
        for row in rows_by_sheet[sheet_key]:
            ws.append([row.get(field[0], "") for field in fields])
    wb.save(DATA_FILE)
    shutil.copy2(DATA_FILE, BACKUP_FILE)

def _daily_snapshot_path(day=None):
    """مسار نسخة Excel اليومية في مجلد backups."""
    d = day or date.today()
    return os.path.join(BACKUP_DIR, f"transport_data_{d.isoformat()}.xlsx")

def _last_excel_snapshot_date():
    """التحقق من تاريخ آخر نسخة يومية في مجلد backups. تُرجع التاريخ أو None."""
    snapshot_path = _daily_snapshot_path()
    if os.path.exists(snapshot_path):
        mod_time = os.path.getmtime(snapshot_path)
        return datetime.fromtimestamp(mod_time).date()
    return None

def _export_database_to_excel():
    """احفظ نسخة قابلة للقراءة من البيانات في الملفات العاملة DFATA_FILE و BACKUP_FILE،
    وانسخ نسخة إضافية مُرقمة بالتواريخ في مجلد backups."""
    ensure_workbook()
    connection = _connect()
    try:
        rows_by_sheet = {}
        for sheet_key in SHEETS:
            rows_by_sheet[sheet_key] = [
                json.loads(item[0]) for item in connection.execute(
                    "SELECT data_json FROM records WHERE sheet_key = ? ORDER BY rowid",
                    (sheet_key,),
                )
            ]
    finally:
        connection.close()

    wb = load_workbook(DATA_FILE)
    for sheet_key, sheet_name in SHEETS.items():
        ws = wb[sheet_name]
        if ws.max_row > 1:
            ws.delete_rows(2, ws.max_row - 1)
        fields = _headers_for(sheet_key)
        for row in rows_by_sheet[sheet_key]:
            ws.append([row.get(field[0], "") for field in fields])
    wb.save(DATA_FILE)
    shutil.copy2(DATA_FILE, BACKUP_FILE)

def sync_excel(force=False):
    """Synchronize the human-readable Excel copy on demand.

    تُنشئ نسخة يومية واحدة فقط في مجلد backups لكل يوم.
    إذا كان هناك نسخة بالفعل اليوم وليس force=True، تعود دون فعل أي شيء.
    """
    if not force:
        last_snapshot = _last_excel_snapshot_date()
        if last_snapshot == date.today():
            return  # تم إنشاء النسخة اليومية بالفعل

    _ensure_database()
    _export_database_to_excel()

def create_timestamped_backup():
    """Create a dated Excel backup without changing the active database."""
    sync_excel(force=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(BACKUP_DIR, f"transport_data_{stamp}.xlsx")
    shutil.copy2(DATA_FILE, path)
    for old_path in list_timestamped_backups()[30:]:
        try:
            os.remove(old_path)
        except OSError:
            pass
    return path

def list_timestamped_backups():
    if not os.path.isdir(BACKUP_DIR):
        return []
    return sorted(
        (os.path.join(BACKUP_DIR, name) for name in os.listdir(BACKUP_DIR)
         if name.lower().endswith(".xlsx")),
        reverse=True,
    )

def restore_from_excel(path):
    """Replace SQLite records from a selected Excel backup after validation."""
    if _current_role != "مدير":
        raise PermissionError("استعادة النسخ الاحتياطية متاحة للمدير فقط.")
    if not path or not os.path.isfile(path):
        raise ValueError("ملف النسخة الاحتياطية غير موجود.")
    try:
        missing = missing_sheets_in_workbook(path)
    except Exception as exc:
        raise ValueError("ملف النسخة الاحتياطية تالف أو غير صالح.") from exc
    # النسخ الأقدم لا تحتوي الجداول التي أُضيفت لاحقاً؛ نتحقق من الجداول
    # الجوهرية فقط، ونتعامل مع الغائبة كجداول فارغة.
    core_missing = [SHEETS[key] for key in CORE_SHEET_KEYS if SHEETS[key] in missing]
    if core_missing:
        raise ValueError("ملف النسخة لا يحتوي على الجداول المطلوبة.")
    connection = _connect()
    try:
        connection.execute("DELETE FROM records")
        connection.execute("DELETE FROM profit_snapshots")
        connection.execute("DELETE FROM financial_approvals")
        now = datetime.now().isoformat(timespec="seconds")
        for sheet_key in SHEETS:
            if SHEETS[sheet_key] in missing:
                continue
            fields = _headers_for(sheet_key)
            key_field = fields[0][0]
            for row in _read_workbook_rows_from(path, sheet_key):
                connection.execute(
                    "INSERT OR REPLACE INTO records "
                    "(sheet_key, record_key, data_json, updated_at) VALUES (?, ?, ?, ?)",
                    (sheet_key, str(row.get(key_field, "")),
                     json.dumps(row, ensure_ascii=False), now),
                )
        connection.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('workbook_migrated', ?)",
            (now,),
        )
        connection.commit()
    finally:
        connection.close()
    _invalidate_rows_cache()
    _mark_local_change()
    sync_excel(force=True)
    return [name for name in missing if name not in core_missing]

def _read_workbook_rows_from(path, sheet_key):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = workbook[SHEETS[sheet_key]]
        fields = _headers_for(sheet_key)
        return [
            {field[0]: values[index] if index < len(values) and values[index] is not None else ""
             for index, field in enumerate(fields)}
            for values in worksheet.iter_rows(min_row=2, values_only=True)
            if values and values[0] not in (None, "")
        ]
    finally:
        workbook.close()
