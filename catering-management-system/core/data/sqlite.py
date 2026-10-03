# -*- coding: utf-8 -*-
"""
core.data.sqlite — محرك تخزين SQLite، بديل لملف Excel وبنفس واجهة العمليات.

يُفعَّل عبر متغير البيئة RESTAURANT_BACKEND=sqlite، ويُدار مساره عبر
RESTAURANT_DB_FILE (افتراضياً restaurant.db بجوار البرنامج).

لا يستورد طبقة البيانات إطلاقاً (تفادياً للتدوير): يتسلّم وصف الجداول عبر
configure() عند إقلاع core.data، ويُسجّل الحركات عبر نفس دالة log_action
المُمرَّرة له.

المزايا على Excel:
  - تعديل صف واحد لا يعيد كتابة الملف كله (ولا يحتاج حفظاً آمناً مؤقتاً).
  - معاملات (transactions) حقيقية: إما تُكتمل العملية أو تُلغى.
  - جاهز للمرحلة متعددة المستخدمين (Phase 5) دون تغيير الواجهة.
"""
import os
import shutil
import sqlite3
from datetime import date

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

# مجلد جذر المشروع (ثلاثة مستويات أعلى: core/data/sqlite.py) — حتى يبقى
# restaurant.db بجوار restaurant_desktop_app.py لا داخل الحزمة.
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_FILE = (os.environ.get("RESTAURANT_DB_FILE")
           or os.path.join(APP_DIR, "restaurant.db"))

BACKUP_DIR_NAME = "backups"
MAX_BACKUPS = 30

# الأعمدة الرقمية (كميات ومبالغ) — تُخزَّن REAL، وما عداها TEXT.
REAL_FIELDS = {
    "base_salary", "cost", "unit_cost", "total_cost", "total", "amount",
    "quantity", "guests_count", "unit_price", "deposit", "net_salary",
    "bonuses", "advances", "deductions", "sale_price", "paid_amount",
}

# وصف الجداول يُمرَّر من restaurant_data (المصدر الوحيد للحقيقة)
_SHEETS = {}          # key -> الاسم العربي (اسم الورقة في Excel)
_FIELDS_FOR = None    # callable: key -> [(field, label), ...]
_LOGGER = None        # callable: log_action(action, sheet_key, key, details)


def configure(sheet_names, fields_for, logger=None):
    """تسجيل وصف الجداول ودالة السجل — يُستدعى مرة واحدة من restaurant_data."""
    global _SHEETS, _FIELDS_FOR, _LOGGER
    _SHEETS = dict(sheet_names)
    _FIELDS_FOR = fields_for
    _LOGGER = logger


# ------------------------------------------------------------------
# الاتصال وإنشاء المخطط
# ------------------------------------------------------------------
def _connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _fields(sheet_key):
    if _FIELDS_FOR is None:
        raise RuntimeError("لم تُستدعَ configure() بعد.")
    return _FIELDS_FOR(sheet_key)


def _ddl(sheet_key):
    """عبارة إنشاء الجدول من قائمة الحقول: العمود الأول هو المفتاح."""
    fields = _fields(sheet_key)
    pk = fields[0][0]
    cols = []
    for key, _ in fields:
        if key == pk:
            kind = "INTEGER PRIMARY KEY" if pk == "id" else "TEXT PRIMARY KEY"
        else:
            kind = "REAL" if key in REAL_FIELDS else "TEXT"
        cols.append('"%s" %s' % (key, kind))
    return 'CREATE TABLE IF NOT EXISTS "%s" (%s)' % (sheet_key, ", ".join(cols))


def _migrate_columns(conn, sheet_key):
    """يضيف الأعمدة الناقصة لجدول قديم (نفس مبدأ _add_missing_sheets في Excel)."""
    existing = {row[1] for row in conn.execute(
        'PRAGMA table_info("%s")' % sheet_key)}
    added = 0
    for key, _ in _fields(sheet_key):
        if key not in existing:
            kind = "REAL" if key in REAL_FIELDS else "TEXT"
            conn.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s'
                         % (sheet_key, key, kind))
            added += 1
    return added


def ensure():
    """ينشئ قاعدة البيانات وكل الجداول، ويضيف أي أعمدة ناقصة."""
    os.makedirs(os.path.dirname(os.path.abspath(DB_FILE)) or ".", exist_ok=True)
    with _connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        for sheet_key in _SHEETS:
            conn.execute(_ddl(sheet_key))
            _migrate_columns(conn, sheet_key)


# ------------------------------------------------------------------
# تحويل القيم بين بايثون وSQL
# ------------------------------------------------------------------
def _coerce(sheet_key, key, value):
    pk = _fields(sheet_key)[0][0]
    if key == pk and pk == "id":
        try:
            text = str(value).strip()
            return int(float(text)) if text else None
        except (TypeError, ValueError):
            return None
    if key in REAL_FIELDS:
        try:
            text = str(value).strip() if value is not None else ""
            return float(text) if text else None
        except (TypeError, ValueError):
            return None
    return "" if value is None else str(value)


def load_rows(sheet_key):
    """كل صفوف الجدول كقواميس — None يصبح "" كما تفعل قراءة Excel."""
    ensure()
    with _connect() as conn:
        cursor = conn.execute('SELECT * FROM "%s" ORDER BY rowid' % sheet_key)
        names = [d[0] for d in cursor.description]
        rows = []
        for record in cursor.fetchall():
            row = {}
            for name, value in zip(names, record):
                row[name] = "" if value is None else value
            rows.append(row)
    return rows


def save_row(sheet_key, data, pk_field, editing_key=None):
    """
    إدراج أو استبدال صف. البحث عن الصف القديم يتم على المفتاح بنفس دلالات
    Excel (مقارنة نصية)، فلا يتغير سلوك أي دالة أعلى.
    """
    ensure()
    fields = _fields(sheet_key)
    pk = fields[0][0]
    record_key = editing_key if editing_key is not None else data.get(pk)
    keys = [k for k, _ in fields]
    values = [_coerce(sheet_key, key, data.get(key, "")) for key in keys]
    pk_index = keys.index(pk)
    # المفتاح النصي الفارغ غير مسموح (كما في Excel حيث العمود الأول لا يكون فارغاً)
    if not (pk == "id" and values[pk_index] is None) \
            and not str(values[pk_index] or "").strip():
        raise ValueError("قيمة المفتاح (%s) مطلوبة." % pk)
    columns = ", ".join('"%s"' % k for k in keys)
    marks = ", ".join("?" for _ in keys)
    with _connect() as conn:
        conn.execute('INSERT OR REPLACE INTO "%s" (%s) VALUES (%s)'
                     % (sheet_key, columns, marks), values)
    if _LOGGER is not None:
        _LOGGER("تعديل" if editing_key is not None else "إضافة",
                sheet_key, data.get(pk, ""))
    return record_key


def delete_row(sheet_key, key_value):
    """حذف بالمفتاح مع مقارنة نصية (str(key) == str(value)) كطبقة Excel."""
    ensure()
    pk = _fields(sheet_key)[0][0]
    with _connect() as conn:
        cursor = conn.execute(
            'DELETE FROM "%s" WHERE CAST("%s" AS TEXT) = ?'
            % (sheet_key, pk), (str(key_value),))
        deleted = cursor.rowcount > 0
    if deleted and _LOGGER is not None:
        _LOGGER("حذف", sheet_key, key_value)
    return deleted


def count_rows(sheet_key):
    ensure()
    with _connect() as conn:
        return conn.execute('SELECT COUNT(*) FROM "%s"' % sheet_key).fetchone()[0]


def is_empty():
    """True إذا كانت كل جداول القاعدة فارغة (يُستخدم للاستيراد التلقائي الأول)."""
    ensure()
    with _connect() as conn:
        for sheet_key in _SHEETS:
            try:
                n = conn.execute('SELECT COUNT(*) FROM "%s"' % sheet_key).fetchone()[0]
            except Exception:
                return True
            if n:
                return False
    return True


# ------------------------------------------------------------------
# النسخ الاحتياطية (ملف .db كامل)
# ------------------------------------------------------------------
def _backup_dir():
    path = os.path.join(os.path.dirname(os.path.abspath(DB_FILE)),
                        BACKUP_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def _prune_backups(keep=MAX_BACKUPS):
    files = sorted(name for name in os.listdir(_backup_dir())
                   if name.startswith("restaurant_db_") and name.endswith(".db"))
    removed = 0
    for name in files[:-keep] if keep > 0 else files:
        try:
            os.remove(os.path.join(_backup_dir(), name))
            removed += 1
        except OSError:
            pass
    return removed


def backup_data_file(force=False):
    """نسخة يومية من ملف قاعدة البيانات داخل backups/ (تعيد المسار أو None)."""
    if not os.path.exists(DB_FILE):
        return None
    target = os.path.join(_backup_dir(),
                          "restaurant_db_%s.db" % date.today().strftime("%Y-%m-%d"))
    if os.path.exists(target) and not force:
        return None
    # نسخة متناسقة: نقطة تحقق (checkpoint) ثم نسخ الملف الرئيسي وملفات WAL
    with _connect() as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    shutil.copy2(DB_FILE, target)
    _prune_backups()
    if _LOGGER is not None:
        _LOGGER("نسخة احتياطية", "", "", os.path.basename(target))
    return target


# ------------------------------------------------------------------
# Excel: تصدير/استيراد (يصبح Excel صيغة تبادل فقط)
# ------------------------------------------------------------------
def export_excel(path=None):
    """يكتب كل الجداول إلى ملف Excel بنفس أسماء الأوراق وترتيب الأعمدة."""
    if not _SHEETS:
        raise RuntimeError("لم تُستدعَ configure() بعد.")
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(DB_FILE)),
                            "restaurant_export_%s.xlsx"
                            % date.today().strftime("%Y-%m-%d"))
    wb = Workbook()
    first = True
    for sheet_key, sheet_name in _SHEETS.items():
        ws = wb.active if first else wb.create_sheet(sheet_name)
        if first:
            ws.title = sheet_name
            first = False
        fields = _fields(sheet_key)
        for i, (_, label) in enumerate(fields, start=1):
            ws.cell(row=1, column=i, value=label).font = Font(bold=True)
        for r, row in enumerate(load_rows(sheet_key), start=2):
            for i, (key, _) in enumerate(fields, start=1):
                ws.cell(row=r, column=i, value=row.get(key, ""))
    wb.save(path)
    return path


def import_excel(path):
    """
    يقرأ ملف Excel (بنفس مخطط الأوراق) ويستبدل به محتوى الجداول — أداة الترحيل
    من نسخة Excel إلى SQLite. تعيد قاموساً: مفتاح الجدول -> عدد الصفوف.
    """
    if not _SHEETS:
        raise RuntimeError("لم تُستدعَ configure() بعد.")
    wb = load_workbook(path, data_only=True)
    counts = {}
    with _connect() as conn:
        for sheet_key, sheet_name in _SHEETS.items():
            if sheet_name not in wb.sheetnames:
                continue
            ws = wb[sheet_name]
            fields = _fields(sheet_key)
            rows = []
            for r in range(2, ws.max_row + 1):
                values = [ws.cell(row=r, column=c).value
                          for c in range(1, len(fields) + 1)]
                if all(v in (None, "") for v in values):
                    continue
                rows.append({key: value
                             for (key, _), value in zip(fields, values)})
            conn.execute('DELETE FROM "%s"' % sheet_key)
            columns = ", ".join('"%s"' % k for k, _ in fields)
            marks = ", ".join("?" for _ in fields)
            for row in rows:
                conn.execute(
                    'INSERT OR REPLACE INTO "%s" (%s) VALUES (%s)'
                    % (sheet_key, columns, marks),
                    [_coerce(sheet_key, k, row.get(k, ""))
                     for k, _ in fields])
            counts[sheet_key] = len(rows)
            if _LOGGER is not None:
                _LOGGER("استيراد", sheet_key, "", "%d صف" % len(rows))
    return counts
