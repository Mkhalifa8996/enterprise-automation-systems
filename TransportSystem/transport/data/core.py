# -*- coding: utf-8 -*-
"""الاتصال بقاعدة البيانات، التهيئة، الذاكرة المؤقتة، وعمليات الصف الأساسية."""

import hashlib, json, os, secrets, shutil, sqlite3
from openpyxl.styles import Alignment
from openpyxl import Workbook
from datetime import datetime
from openpyxl import load_workbook
from .paths import APP_DIR, BACKUP_FILE, DATA_FILE, DB_FILE, _get_resource_path
from .schema import CASH_LEDGER_FIELDS, COMPANY_FIELDS, CONTRACT_FIELDS, CUSTOMER_FIELDS, DAILY_EXPENSE_FIELDS, DRIVER_FIELDS, DRIVER_PAYMENT_FIELDS, DRIVER_TYPES, FUEL_FIELDS, HEADER_FILL, HEADER_FONT, INVOICE_FIELDS, MAINTENANCE_FIELDS, MAINTENANCE_PLAN_FIELDS, PARTNER_PAYMENT_FIELDS, PART_FIELDS, PAYMENT_FIELDS, PLACES_FIELDS, QUOTATION_FIELDS, SALARY_FIELDS, SERVICE_FIELDS, SHEETS, TRIP_FIELDS, VEHICLE_ASSIGNMENT_FIELDS, VEHICLE_FIELDS, VEHICLE_PARTNER_FIELDS, VEHICLE_SETUP_FIELDS, _normalized_driver_name, safe_int

def _connect():
    """فتح اتصال محمي بقاعدة البيانات.

    يفعّل وضع WAL ودوام متزامن قوي وانتظار عند الانشغال، مما يحمي البيانات
    من فقدانها عند انقطاع الكهرباء أو إغلاق البرنامج فجأة، ويمنع خطأ
    «قاعدة البيانات مقفلة» عند تشغيل نسختين في نفس الوقت.
    """
    connection = sqlite3.connect(DB_FILE, timeout=30.0)
    try:
        connection.execute("PRAGMA busy_timeout = 30000")
        current = connection.execute("PRAGMA journal_mode").fetchone()[0]
        if str(current).lower() != "wal":
            try:
                connection.execute("PRAGMA journal_mode = WAL")
            except sqlite3.DatabaseError:
                # بعض الأنظمة (شبكة أو قرص للقراءة فقط) لا تدعم WAL،
                # فنكمل بالإعدادات الأخرى دون إسقاط العملية.
                pass
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA foreign_keys = ON")
    except sqlite3.DatabaseError:
        pass
    return connection

def _initialize_database():
    """نسخ قاعدة البيانات من المجلد المضمّن إلى مجلد البرنامج عند التشغيل الأول."""
    db_path = os.path.join(APP_DIR, "transport_data.db")
    if not os.path.exists(db_path):
        # إذا لم تكن قاعدة البيانات موجودة، نسخها من الملف المضمّن
        bundled_db = _get_resource_path("transport_data.db")
        if os.path.exists(bundled_db):
            try:
                shutil.copy2(bundled_db, db_path)
                print(f"[INFO] تم نسخ قاعدة البيانات إلى: {db_path}")
            except Exception as e:
                print(f"[ERROR] فشل في نسخ قاعدة البيانات: {e}")

# The UI refreshes several related screens after one change. Re-opening the
# workbook for every list makes those refreshes unnecessarily expensive.
_rows_cache = {}

_workbook_checked = False

_database_checked = False

_local_change_revision = 0

_current_user = "مدير النظام"

_current_role = "مدير"

def _headers_for(sheet_key):
    return {
        "drivers": DRIVER_FIELDS, "vehicles": VEHICLE_FIELDS, "maintenance": MAINTENANCE_FIELDS,
        "customers": CUSTOMER_FIELDS, "companies": COMPANY_FIELDS, "places": PLACES_FIELDS, "daily_expenses": DAILY_EXPENSE_FIELDS, "vehicle_setup_expenses": VEHICLE_SETUP_FIELDS, "trips": TRIP_FIELDS, "services": SERVICE_FIELDS,
        "invoices": INVOICE_FIELDS, "payments": PAYMENT_FIELDS, "salaries": SALARY_FIELDS,
        "vehicle_assignments": VEHICLE_ASSIGNMENT_FIELDS,
        "vehicle_partners": VEHICLE_PARTNER_FIELDS,
        "partner_payments": PARTNER_PAYMENT_FIELDS,
        "driver_payments": DRIVER_PAYMENT_FIELDS,
        "cash_ledger": CASH_LEDGER_FIELDS,
        "fuel": FUEL_FIELDS,
        "contracts": CONTRACT_FIELDS,
        "quotations": QUOTATION_FIELDS,
        "maintenance_plans": MAINTENANCE_PLAN_FIELDS,
        "parts": PART_FIELDS,
    }[sheet_key]

def _write_header(ws, fields):
    for i, field in enumerate(fields, start=1):
        label = field[1]
        c = ws.cell(row=1, column=i, value=label)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "A2"

def _header_token(value):
    """Return a stable comparison value for an Excel header."""
    return " ".join(str(value or "").strip().casefold().split())

def _migrate_sheet_columns(ws, fields, rewrite_rows=False):
    """Align existing rows with the current field definitions by header name.

    Older versions of the application could change the field order while the
    workbook still contained the old order. Reading/writing by position then
    associates existing values with the wrong input controls. Build the new
    row from the old header names before replacing the headers.
    """
    # بعض الإصدارات القديمة قد تحتوي على بيانات وصفية إضافية في تعريف الحقل؛
    # الترحيل يحتاج فقط إلى المفتاح والتسمية.
    target_labels = [field[1] for field in fields]
    old_headers = [ws.cell(row=1, column=i).value for i in range(1, ws.max_column + 1)]
    old_by_header = {}
    for index, header in enumerate(old_headers, start=1):
        token = _header_token(header)
        if token and token not in old_by_header:
            old_by_header[token] = index

    header_aliases = {
        "كود الرحلة": ["رقم البيان-رقم الرحلة"],
    }
    source_columns = [
        old_by_header.get(_header_token(label))
        or next((old_by_header.get(_header_token(alias))
                 for alias in header_aliases.get(label, [])
                 if old_by_header.get(_header_token(alias)) is not None), None)
        for label in target_labels
    ]
    matched = sum(source is not None for source in source_columns)
    headers_match = (old_headers[:len(target_labels)] == target_labels
                     and len(old_headers) == len(target_labels))
    if headers_match and not rewrite_rows:
        return False

    # If an old workbook has no recognizable headers, preserve its positional
    # values rather than silently discarding them.
    if matched == 0:
        source_columns = [i if i <= len(old_headers) else None
                          for i in range(1, len(target_labels) + 1)]

    old_rows = []
    for row in range(2, ws.max_row + 1):
        old_rows.append([ws.cell(row=row, column=i).value for i in range(1, ws.max_column + 1)])

    changed = not headers_match
    for row_index, values in enumerate(old_rows, start=2):
        for column, source in enumerate(source_columns, start=1):
            value = values[source - 1] if source is not None and source <= len(values) else ""
            cell = ws.cell(row=row_index, column=column)
            if cell.value != value:
                cell.value = value
                changed = True

    for column, label in enumerate(target_labels, start=1):
        ws.cell(row=1, column=column, value=label)
    return changed

def ensure_workbook():
    """Ensure the workbook file exists and contains all required sheets with headers.

    If the file doesn't exist, create it with all sheets. If it exists, add any missing
    sheets and ensure new columns are present in existing sheets.
    """
    global _workbook_checked
    if _workbook_checked and os.path.exists(DATA_FILE):
        return
    if not os.path.exists(DATA_FILE):
        wb = Workbook()
        first = True
        for key, sheet_name in SHEETS.items():
            ws = wb.active if first else wb.create_sheet(sheet_name)
            if first:
                ws.title = sheet_name
                first = False
            _write_header(ws, _headers_for(key))
        wb.save(DATA_FILE)
        _workbook_checked = True
        return

    wb = load_workbook(DATA_FILE)
    modified = False
    for key, sheet_name in SHEETS.items():
        if sheet_name not in wb.sheetnames:
            ws = wb.create_sheet(sheet_name)
            _write_header(ws, _headers_for(key))
            modified = True
            continue

        ws = wb[sheet_name]
        fields = _headers_for(key)
        # Header migration is enough for normal reads. Rewriting every trip
        # and salary row on every refresh made the entire UI slow.
        if _migrate_sheet_columns(ws, fields):
            modified = True
    if modified:
        wb.save(DATA_FILE)
        shutil.copy2(DATA_FILE, BACKUP_FILE)
    _workbook_checked = True

def _invalidate_rows_cache():
    _rows_cache.clear()

def _mark_local_change():
    """Record a local change so the desktop UI can queue cloud sync safely."""
    global _local_change_revision
    _local_change_revision += 1

def local_change_revision():
    """Monotonic revision of locally edited synchronizable records."""
    return _local_change_revision

def _read_workbook_rows(sheet_key):
    """Read one Excel sheet during the one-time SQLite migration."""
    wb = load_workbook(DATA_FILE, read_only=True, data_only=True)
    ws = wb[SHEETS[sheet_key]]
    fields = _headers_for(sheet_key)
    rows = []
    for values in ws.iter_rows(min_row=2, values_only=True):
        if not values or values[0] in (None, ""):
            continue
        rows.append({
            field[0]: values[index] if index < len(values) and values[index] is not None else ""
            for index, field in enumerate(fields)
        })
    wb.close()
    return rows

def _recover_orphan_declaration_links(connection):
    from .attachments import declaration_key
    """إصلاح بيانات قديمة: إعادة ربط الملفات والمواقع المتيمة تحت مفاتيح temp_batch_.

    سابقاً كانت ملفات البيان ومواقع التنزيل تُحفظ تحت مفتاح مؤقت ولا تُنقل إلى
    مفتاح ثابت عند حفظ البيان، فتختفي عند إعادة فتحه. تُستدعى هذه الدالة مرة
    عند بدء التشغيل وترحّل أي بيانات متيمة إلى مفتاح البيان الثابت عندما يكون
    الربط واضحاً بدون أي التباس.
    """
    prefix = "temp_batch_"
    orphan_keys = [
        row[0] for row in connection.execute(
            "SELECT DISTINCT record_key FROM attachments "
            "WHERE entity_type = 'trips' AND record_key LIKE ?",
            (prefix + "%",),
        )
    ]
    orphan_keys += [
        row[0] for row in connection.execute(
            "SELECT DISTINCT record_key FROM locations WHERE record_key LIKE ?",
            (prefix + "%",),
        )
    ]
    orphan_keys = list(dict.fromkeys(key for key in orphan_keys if key))
    if not orphan_keys:
        return
    trips = []
    for row in connection.execute(
        "SELECT data_json, updated_at FROM records WHERE sheet_key = 'trips'"
    ):
        try:
            trip = json.loads(row[0])
        except (TypeError, ValueError):
            continue
        trip["updated_at"] = row[1] or ""
        trips.append(trip)
    moves = []
    for old_key in orphan_keys:
        stamp = old_key[len(prefix):]
        if not stamp.isdigit():
            continue
        try:
            created = datetime.fromtimestamp(int(stamp) / 1000.0)
        except (OSError, OverflowError, ValueError):
            continue
        day_iso = created.date().isoformat()
        candidates = [
            t for t in trips
            if str(t.get("date") or "").strip() == day_iso
        ]
        if not candidates:
            continue
        declarations = {str(t.get("declaration_no") or "").strip() for t in candidates}
        if len(declarations) != 1:
            continue
        new_key = declaration_key(day_iso, declarations.pop())
        if not new_key or new_key == old_key:
            continue
        moves.append((old_key, new_key))
    for old_key, new_key in moves:
        connection.execute(
            "UPDATE attachments SET record_key = ? "
            "WHERE entity_type = 'trips' AND record_key = ?",
            (new_key, old_key),
        )
        connection.execute(
            "UPDATE locations SET record_key = ? WHERE record_key = ?",
            (new_key, old_key),
        )
    if moves:
        connection.commit()

def _backfill_daily_expense_driver_type(connection):
    """يملأ «نوع السائق» في المصاريف المسجّلة قبل إضافة الحقل (مرة واحدة).

    عند إضافة الحقل لم تُملأ القيم القديمة، فظهر عمود «نوع السائق» فارغاً في
    كل سجل قديم. كان الفلتر والطباعة يتجاوزان ذلك بالاشتقاق من سجل السائق،
    لكن الجدول نفسه يعرض القيمة المحفوظة فيبقى العمود فارغاً على الشاشة.
    """
    done = connection.execute(
        "SELECT value FROM metadata WHERE key = 'driver_type_backfilled'"
    ).fetchone()
    if done:
        return
    try:
        rows = connection.execute(
            "SELECT record_key, data_json FROM records WHERE sheet_key = 'daily_expenses'"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    # خريطة اسم السائق -> نوعه، مطابقة لقواعد المطابقة المستعملة في البرنامج.
    kind_by_name = {}
    for row in connection.execute("SELECT data_json FROM records WHERE sheet_key = 'drivers'"):
        try:
            driver = json.loads(row[0])
        except (TypeError, ValueError):
            continue
        name = str(driver.get("name", "")).strip()
        kind = str(driver.get("driver_type", "")).strip()
        if name and kind in DRIVER_TYPES:
            kind_by_name[_normalized_driver_name(name)] = kind
    updated = 0
    for record_key, payload in rows:
        try:
            record = json.loads(payload)
        except (TypeError, ValueError):
            continue
        if str(record.get("driver_type", "")).strip():
            continue
        kind = kind_by_name.get(_normalized_driver_name(record.get("driver", "")))
        if not kind:
            continue
        record["driver_type"] = kind
        connection.execute(
            "UPDATE records SET data_json = ? WHERE sheet_key = 'daily_expenses' "
            "AND record_key = ?",
            (json.dumps(record, ensure_ascii=False), record_key),
        )
        updated += 1
    connection.execute(
        "INSERT OR REPLACE INTO metadata (key, value) VALUES ('driver_type_backfilled', ?)",
        (datetime.now().isoformat(timespec="seconds"),),
    )
    connection.commit()
    if updated:
        print(f"[INFO] تم ملء نوع السائق في {updated} مصروفاً قديماً.")

def _ensure_database():
    """Create SQLite and migrate the existing workbook exactly once."""
    global _database_checked
    if _database_checked and os.path.exists(DB_FILE):
        return
    connection = _connect()
    try:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS records ("
            "sheet_key TEXT NOT NULL, record_key TEXT NOT NULL, data_json TEXT NOT NULL, "
            "updated_at TEXT NOT NULL, PRIMARY KEY (sheet_key, record_key))"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS profit_snapshots ("
            "snapshot_month TEXT NOT NULL, car_no TEXT NOT NULL, data_json TEXT NOT NULL, "
            "created_at TEXT NOT NULL, PRIMARY KEY (snapshot_month, car_no))"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS audit_logs ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL, "
            "sheet_key TEXT NOT NULL, record_key TEXT NOT NULL, details_json TEXT NOT NULL, "
            "actor TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS closed_periods ("
            "period_month TEXT PRIMARY KEY, closed_by TEXT NOT NULL, closed_at TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS app_users ("
            "username TEXT PRIMARY KEY, role TEXT NOT NULL, password_hash TEXT NOT NULL DEFAULT '', "
            "active INTEGER NOT NULL DEFAULT 1)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS attachments ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, "
            "record_key TEXT NOT NULL, file_name TEXT NOT NULL, path TEXT NOT NULL, "
            "notes TEXT NOT NULL DEFAULT '', created_by TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS sync_tombstones ("
            "sheet_key TEXT NOT NULL, record_key TEXT NOT NULL, deleted_at TEXT NOT NULL, "
            "PRIMARY KEY (sheet_key, record_key))"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS financial_approvals ("
            "period_key TEXT PRIMARY KEY, summary_json TEXT NOT NULL, "
            "approved_by TEXT NOT NULL, approved_at TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS locations ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, record_key TEXT NOT NULL DEFAULT '', "
            "name TEXT NOT NULL DEFAULT '', google_maps_url TEXT NOT NULL DEFAULT '', "
            "notes TEXT NOT NULL DEFAULT '', created_by TEXT NOT NULL DEFAULT '', "
            "created_at TEXT NOT NULL)"
        )
        location_columns = {row[1] for row in connection.execute("PRAGMA table_info(locations)")}
        if "record_key" not in location_columns:
            connection.execute("ALTER TABLE locations ADD COLUMN record_key TEXT NOT NULL DEFAULT ''")
        if "created_by" not in location_columns:
            connection.execute("ALTER TABLE locations ADD COLUMN created_by TEXT NOT NULL DEFAULT ''")
        user_columns = {row[1] for row in connection.execute("PRAGMA table_info(app_users)")}
        if "password_hash" not in user_columns:
            connection.execute("ALTER TABLE app_users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")
        # كلمة مرور المدير: تُنشأ مرة واحدة فقط عند الحاجة.
        # كان يُولَّد ويُطبع في السجل في كل تشغيل حتى لو كان الحساب موجوداً
        # بكلمة مرور سليمة، فيظهر في السجل رقم غير صالح فعلاً.
        admin_row = connection.execute(
            "SELECT password_hash FROM app_users WHERE username = ?",
            ("مدير النظام",),
        ).fetchone()
        if not admin_row or not str(admin_row[0] or "").strip():
            default_password = os.environ.get("TRANSPORT_ADMIN_PASSWORD", "").strip()
            if not default_password:
                default_password = secrets.token_urlsafe(16)
                # لا نكتب كلمة المرور في السجل، بل ننبّه إلى كيفية ضبطها.
                import logging
                logging.warning(
                    "لم تُضبط كلمة مرور المدير. تم إنشاء واحدة عشوائية؛ "
                    "يُنصح بتعيين TRANSPORT_ADMIN_PASSWORD أو تغييرها من شاشة المستخدمين.")
            default_hash = _hash_password(default_password)
            if not admin_row:
                connection.execute(
                    "INSERT OR IGNORE INTO app_users "
                    "(username, role, password_hash, active) VALUES (?, ?, ?, 1)",
                    ("مدير النظام", "مدير", default_hash),
                )
            connection.execute(
                "UPDATE app_users SET password_hash = ? "
                "WHERE username = ? AND (password_hash IS NULL OR password_hash = '')",
                (default_hash, "مدير النظام"),
            )
        for index_sql in (
            "CREATE INDEX IF NOT EXISTS idx_records_sheet_updated ON records(sheet_key, updated_at)",
            "CREATE INDEX IF NOT EXISTS idx_records_data_date ON records(sheet_key, record_key)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_snapshots_month ON profit_snapshots(snapshot_month)",
        ):
            connection.execute(index_sql)
        _recover_orphan_declaration_links(connection)
        _backfill_daily_expense_driver_type(connection)
        # SQLite هو المصدر الوحيد للبيانات - لا يتم الترحيل من Excel
        # Excel يستخدم فقط للنسخ الاحتياطية الدورية
        connection.execute(
            "INSERT OR IGNORE INTO metadata (key, value) VALUES ('workbook_migrated', ?)",
            (datetime.now().isoformat(timespec="seconds"),),
        )
        connection.commit()
    finally:
        connection.close()
    _database_checked = True

# الجداول الجوهرية التي يجب أن يحتويها أي ملف نسخة احتياطية صالح.
# باقي الجداول قد تكون أُضيفت في إصدارات أقدم، فغيابها لا يُبطل النسخة.
CORE_SHEET_KEYS = ("drivers", "vehicles", "trips", "invoices")

def missing_sheets_in_workbook(path):
    """أسماء جداول التطبيق الغائبة عن ملف نسخة احتياطية."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        names = set(workbook.sheetnames)
    finally:
        workbook.close()
    return [name for name in SHEETS.values() if name not in names]

def _next_id(rows):
    ids = [safe_int(r.get("id")) for r in rows if str(r.get("id", "")).strip() != ""]
    return (max(ids) if ids else 0) + 1

def _hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", str(password).encode("utf-8"),
                                 salt.encode("ascii"), 180000).hex()
    return f"{salt}${digest}"

def set_current_user(username, role):
    global _current_user, _current_role
    _current_user, _current_role = str(username), str(role)

def current_user():
    return {"username": _current_user, "role": _current_role}

def _period_from_data(data):
    for key in ("date", "trip_date", "month", "start_date"):
        value = str(data.get(key, "") or "").strip()
        if len(value) >= 7 and value[:4].isdigit() and value[4] == "-":
            return value[:7]
    return ""

def is_period_closed(period_month):
    _ensure_database()
    connection = _connect()
    try:
        return connection.execute(
            "SELECT 1 FROM closed_periods WHERE period_month = ?",
            (str(period_month).strip()[:7],),
        ).fetchone() is not None
    finally:
        connection.close()

def _log_audit(connection, action, sheet_key, record_key, details):
    connection.execute(
        "INSERT INTO audit_logs "
        "(action, sheet_key, record_key, details_json, actor, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (action, sheet_key, str(record_key), json.dumps(details, ensure_ascii=False),
         _current_user, datetime.now().isoformat(timespec="seconds")),
    )

# ------------------------------------------------------------------
# عمليات عامة (قراءة/كتابة/حذف صف) تُستخدم لكل الجداول البسيطة
# ------------------------------------------------------------------
def _load_rows(sheet_key, key_field):
    cached = _rows_cache.get(sheet_key)
    if cached is not None:
        return [row.copy() for row in cached]
    ensure_workbook()
    _ensure_database()
    connection = _connect()
    try:
        rows = [
            json.loads(item[0]) for item in connection.execute(
                "SELECT data_json FROM records WHERE sheet_key = ? ORDER BY rowid",
                (sheet_key,),
            )
        ]
    finally:
        connection.close()
    _rows_cache[sheet_key] = [row.copy() for row in rows]
    return rows

def _save_row(sheet_key, key_field, data, editing_key=None):
    ensure_workbook()
    _ensure_database()
    search_val = editing_key if editing_key is not None else data.get(key_field)
    record_key = str(data.get(key_field, ""))
    period = _period_from_data(data)
    if period and is_period_closed(period) and _current_role != "مدير":
        raise PermissionError(f"الفترة {period} مغلقة ولا يمكن تعديلها.")
    connection = _connect()
    try:
        previous = connection.execute(
            "SELECT data_json FROM records WHERE sheet_key = ? AND record_key = ?",
            (sheet_key, str(search_val)),
        ).fetchone()
        if editing_key is not None and str(search_val) != record_key:
            existing = connection.execute(
                "SELECT data_json FROM records WHERE sheet_key = ? AND record_key = ?",
                (sheet_key, record_key),
            ).fetchone()
            if existing and str(search_val) != record_key:
                raise ValueError("المفتاح الجديد مستخدم بالفعل.")
            connection.execute(
                "DELETE FROM records WHERE sheet_key = ? AND record_key = ?",
                (sheet_key, str(search_val)),
            )
        connection.execute(
            "INSERT OR REPLACE INTO records "
            "(sheet_key, record_key, data_json, updated_at) VALUES (?, ?, ?, ?)",
            (sheet_key, record_key, json.dumps(data, ensure_ascii=False),
             datetime.now().isoformat(timespec="seconds")),
        )
        _log_audit(connection, "تعديل" if previous else "إضافة", sheet_key, record_key,
                   {"before": json.loads(previous[0]) if previous else None, "after": data})
        connection.commit()
    finally:
        connection.close()
    _invalidate_rows_cache()
    _mark_local_change()

def _delete_row(sheet_key, key_field, key_value):
    ensure_workbook()
    _ensure_database()
    connection = _connect()
    try:
        previous = connection.execute(
            "SELECT data_json FROM records WHERE sheet_key = ? AND record_key = ?",
            (sheet_key, str(key_value)),
        ).fetchone()
        if previous:
            period = _period_from_data(json.loads(previous[0]))
            if period and is_period_closed(period) and _current_role != "مدير":
                raise PermissionError(f"الفترة {period} مغلقة ولا يمكن حذفها.")
        connection.execute(
            "DELETE FROM records WHERE sheet_key = ? AND record_key = ?",
            (sheet_key, str(key_value)),
        )
        if previous:
            _log_audit(connection, "حذف", sheet_key, str(key_value),
                       {"before": json.loads(previous[0])})
            connection.execute(
                "INSERT OR REPLACE INTO sync_tombstones "
                "(sheet_key, record_key, deleted_at) VALUES (?, ?, ?)",
                (sheet_key, str(key_value), datetime.now().isoformat(timespec="seconds")),
            )
        connection.commit()
    finally:
        connection.close()
    _invalidate_rows_cache()
    if previous:
        _mark_local_change()

def _save_row_by_name(sheet_key, data, editing_name):
    """حفظ صف يستخدم فيه أول عمود (الاسم) كمفتاح نصي بدل رقم تسلسلي."""
    fields = _headers_for(sheet_key)
    _save_row(sheet_key, fields[0][0], data, editing_name)

def _load_metadata(counter_key):
    """قراءة عدّاد محفوظ داخل جدول البيانات (لا حسابي)."""
    _ensure_database()
    connection = _connect()
    try:
        row = connection.execute("SELECT value FROM metadata WHERE key = ?",
                                (str(counter_key),)).fetchone()
        if not row:
            return {}
        try:
            value = json.loads(row[0])
        except (TypeError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}
    finally:
        connection.close()

def _save_metadata(counter_key, values):
    _ensure_database()
    connection = _connect()
    try:
        connection.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                           (str(counter_key), json.dumps(values, ensure_ascii=False)))
        connection.commit()
    finally:
        connection.close()
