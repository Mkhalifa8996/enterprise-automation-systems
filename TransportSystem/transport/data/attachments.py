# -*- coding: utf-8 -*-
"""المرفقات ومواقع التحميل والتنزيل المرتبطة بالسجلات."""

import os, shutil
from datetime import datetime
from .paths import APP_DIR

def add_attachment(entity_type, record_key, source_path, notes=""):
    from .core import _connect, _current_user, _ensure_database
    if not source_path or not os.path.isfile(source_path):
        raise ValueError("ملف المرفق غير موجود.")
    attachment_dir = os.path.join(APP_DIR, "attachments", str(entity_type))
    os.makedirs(attachment_dir, exist_ok=True)
    filename = os.path.basename(source_path)
    target = os.path.join(attachment_dir, filename)
    stem, extension = os.path.splitext(filename)
    suffix = 2
    while os.path.exists(target):
        filename = f"{stem}_{suffix}{extension}"
        target = os.path.join(attachment_dir, filename)
        suffix += 1
    shutil.copy2(source_path, target)
    _ensure_database()
    connection = _connect()
    try:
        connection.execute(
            "INSERT INTO attachments "
            "(entity_type, record_key, file_name, path, notes, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(entity_type), str(record_key), filename, target, str(notes),
             _current_user, datetime.now().isoformat(timespec="seconds")),
        )
        connection.commit()
    except Exception:
        try:
            if os.path.isfile(target):
                os.remove(target)
        except OSError:
            pass
        raise
    finally:
        connection.close()
    return {"entity_type": str(entity_type), "record_key": str(record_key),
            "file_name": filename, "path": target, "notes": str(notes)}

def load_attachments(entity_type="", record_key=""):
    from .core import _connect, _ensure_database
    _ensure_database()
    connection = _connect()
    try:
        query = "SELECT id, entity_type, record_key, file_name, path, notes, created_by, created_at FROM attachments WHERE 1=1"
        params = []
        if entity_type:
            query += " AND entity_type = ?"
            params.append(str(entity_type))
        if record_key:
            query += " AND record_key = ?"
            params.append(str(record_key))
        query += " ORDER BY id DESC"
        return [
            {"id": row[0], "entity_type": row[1], "record_key": row[2],
             "file_name": row[3], "path": row[4], "notes": row[5],
             "created_by": row[6], "created_at": row[7]}
            for row in connection.execute(query, params)
        ]
    finally:
        connection.close()

def delete_attachment(attachment_id):
    from .core import _connect, _ensure_database
    _ensure_database()
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT path FROM attachments WHERE id = ?", (str(attachment_id),)
        ).fetchone()
        if row is None:
            raise ValueError("المرفق غير موجود.")
        path = row[0]
        connection.execute("DELETE FROM attachments WHERE id = ?", (str(attachment_id),))
        connection.commit()
        if path and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass
    finally:
        connection.close()

def move_attachments(entity_type, old_record_key, new_record_key):
    from .core import _connect, _ensure_database
    if not str(old_record_key).strip() or not str(new_record_key).strip():
        return 0
    if str(old_record_key) == str(new_record_key):
        return 0
    _ensure_database()
    connection = _connect()
    try:
        cursor = connection.execute(
            "UPDATE attachments SET record_key = ? WHERE entity_type = ? AND record_key = ?",
            (str(new_record_key), str(entity_type), str(old_record_key)),
        )
        connection.commit()
        return cursor.rowcount
    finally:
        connection.close()

def move_locations(old_record_key, new_record_key):
    from .core import _connect, _ensure_database
    """نقل مواقع التنزيل من مفتاح قديم إلى مفتاح جديد (نفس فكرة move_attachments)."""
    if not str(old_record_key).strip() or not str(new_record_key).strip():
        return 0
    if str(old_record_key) == str(new_record_key):
        return 0
    _ensure_database()
    connection = _connect()
    try:
        cursor = connection.execute(
            "UPDATE locations SET record_key = ? WHERE record_key = ?",
            (str(new_record_key), str(old_record_key)),
        )
        connection.commit()
        return cursor.rowcount
    finally:
        connection.close()

def declaration_key(date_str, declaration_no):
    """مفتاح ثابت للبيان مشتق من (التاريخ + رقم البيان) بدلاً من مفتاح مؤقت.

    يُستخدم لربط ملفات البيان ومواقع التنزيل بالبيان نفسه، فيبقى كل شيء ظاهراً
    عند إعادة فتح البيان بعد الحفظ مهما تغيّر معرّف المجموعة المؤقت في الواجهة.
    """
    date_part = str(date_str or "").strip()
    decl_part = str(declaration_no or "").strip()
    if not date_part and not decl_part:
        return ""
    return "decl:" + date_part + "|" + decl_part

# ------------------------------------------------------------------
# مواقع التنزيل — روابط Google Maps محفوظة كنص أصلي بدون أي تحليل.
# ------------------------------------------------------------------
def _ensure_locations_columns(connection):
    columns = {row[1] for row in connection.execute("PRAGMA table_info(locations)")}
    if "record_key" not in columns:
        connection.execute("ALTER TABLE locations ADD COLUMN record_key TEXT NOT NULL DEFAULT ''")
    if "created_by" not in columns:
        connection.execute("ALTER TABLE locations ADD COLUMN created_by TEXT NOT NULL DEFAULT ''")

def load_locations(record_key=""):
    from .core import _connect, _ensure_database
    """إرجاع كل مواقع التنزيل المحفوظة (الرابط الأصلي كما أُدخل تماماً)."""
    _ensure_database()
    connection = _connect()
    try:
        _ensure_locations_columns(connection)
        query = ("SELECT id, record_key, name, google_maps_url, notes, created_by, created_at "
                 "FROM locations WHERE 1=1")
        params = []
        if str(record_key or "").strip():
            query += " AND record_key = ?"
            params.append(str(record_key).strip())
        query += " ORDER BY id DESC"
        return [
            {"id": row[0], "record_key": row[1], "name": row[2] or "",
             "google_maps_url": row[3] or "", "notes": row[4] or "",
             "created_by": row[5] or "", "created_at": row[6] or ""}
            for row in connection.execute(query, params)
        ]
    finally:
        connection.close()

def save_location(name, google_maps_url, notes="", record_key="", location_id=None):
    from .core import _connect, _current_user, _ensure_database
    """حفظ رابط Google Maps كما هو تماماً بدون أي تعديل أو تحليل."""
    url = str(google_maps_url or "")
    if not url.strip():
        raise ValueError("الصق رابط Google Maps أولاً.")
    _ensure_database()
    connection = _connect()
    try:
        _ensure_locations_columns(connection)
        now = datetime.now().isoformat(timespec="seconds")
        if location_id not in (None, ""):
            connection.execute(
                "UPDATE locations SET record_key = ?, name = ?, google_maps_url = ?, notes = ? "
                "WHERE id = ?",
                (str(record_key or "").strip(), str(name or "").strip(), url,
                 str(notes or "").strip(), str(location_id)),
            )
            if connection.total_changes == 0:
                raise ValueError("الموقع غير موجود.")
            connection.commit()
            return str(location_id)
        cursor = connection.execute(
            "INSERT INTO locations (record_key, name, google_maps_url, notes, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(record_key or "").strip(), str(name or "").strip(), url,
             str(notes or "").strip(), _current_user, now),
        )
        connection.commit()
        return str(cursor.lastrowid)
    finally:
        connection.close()

def delete_location(location_id):
    from .core import _connect, _ensure_database
    _ensure_database()
    connection = _connect()
    try:
        connection.execute("DELETE FROM locations WHERE id = ?", (str(location_id),))
        connection.commit()
    finally:
        connection.close()

def delete_attachments_for_record(entity_type, record_key):
    items = load_attachments(entity_type, record_key)
    errors = []
    for item in items:
        try:
            delete_attachment(item["id"])
        except Exception as exc:
            errors.append(str(exc))
    if errors:
        raise ValueError("تعذر حذف بعض المرفقات:\n" + "\n".join(errors))
    return len(items)
