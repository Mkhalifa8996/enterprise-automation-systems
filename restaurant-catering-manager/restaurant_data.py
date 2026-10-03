# -*- coding: utf-8 -*-
"""
restaurant_data — الواجهة العامة لطبقة بيانات نظام إدارة مطعم التموين والولائم.

نشاط المطعم: تجهيز وجبات لجهتين رئيسيتين:
  1) مؤسسات (شركات / مستشفيات / مدارس) بشكل دائم أو دوري.
  2) عزائم ومناسبات (أفراح، عزائم عائلية، مناسبات رسمية) في تاريخ محدد.

هذا الملف واجهة تصدير فقط (facade): كل المنطق يعيش الآن داخل حزمة core/data
مقسّمة إلى وحدات حسب المسؤولية، وهذا الملف يجمعها في مكان واحد حتى تبقى بقية
الواجهة (restaurant_desktop_app.py و ui/) تعمل دون أي تغيير:

    core/data/config.py     ثوابت النظام ومخطط الجداول
    core/data/validation.py أدوات التحقق وتحويل القيم
    core/data/runtime.py    الحالة المتغيّرة (المحرك والمسارات وقفل النسخة)
    core/data/sqlite.py     محرك SQLite
    core/data/storage.py    القراءة/الكتابة العامة + الحماية من فقدان البيانات
    core/data/repos/*.py    قواعد العمل مجمّعة حسب المجال

طريقة التشغيل:
    pip install openpyxl
    python restaurant_desktop_app.py

التخزين: SQLite افتراضياً (restaurant.db بجوار البرنامج)، وعند أول إقلاع ووجود
ملف Excel القديم تُستورد بياناته تلقائياً مع نسخة احتياطية — بلا خطوات يدوية.
وضع Excel القديم متاح عبر RESTAURANT_BACKEND=excel، والتصدير عبر export_excel().
"""

import sys as _sys
import types as _types


def runtime_module():
    """وحدة الحالة المتغيّرة (مروراً بها Lazy لتفادي أي استيراد دائري)."""
    from core.data import runtime
    return runtime


def _make_facade():
    """
    يبني قاموس الواجهة العامة: كل ما كان معرّفاً في الملف الواحد قبل التقسيم.

    القيم المتغيّرة (DATA_FILE / BACKEND) تُقرأ من runtime عند بناء القاموس،
    أما القراءة اللاحقة لها فتمر عبر __getattr__ الذي يفحص runtime أولاً.
    """
    from core.data import config, storage, validation
    from core.data.repos import expenses, invoices, masterdata, orders, reporting, salaries

    table = {}

    # ثوابت النظام ومخطط الجداول
    for name in dir(config):
        if name.isupper():
            table[name] = getattr(config, name)
    for name in ("headers_for", "attachments_dir", "attachment_path"):
        table[name] = getattr(config, name)

    # أدوات التحقق وتحويل القيم
    for name in ("safe_float", "safe_int", "is_iso_date", "is_month",
                 "month_bounds", "invoice_items"):
        table[name] = getattr(validation, name)

    # الحماية من فقدان البيانات + التبادل مع Excel
    for name in ("ensure_workbook", "save_workbook", "log_action", "backup_data_file",
                 "startup_maintenance", "acquire_instance_lock", "release_instance_lock",
                 "export_excel", "import_excel"):
        table[name] = getattr(storage, name)

    # قواعد العمل: كل الدوال العامة في المستودعات
    for module in (masterdata, expenses, orders, invoices, salaries, reporting):
        for name in dir(module):
            if not name.startswith("_") and callable(getattr(module, name)):
                table[name] = getattr(module, name)

    # أسماء داخلية تستخدمها الاختبارات وأداة الترحيل
    table["_db"] = storage.sqlite
    table["_prune_backups"] = storage._prune_backups
    table["_next_id"] = storage.next_id
    table["_recalc_invoice_payment"] = invoices._recalc_invoice_payment
    table["date"] = validation.date

    # أسماء داخلية كانت في الملف الواحد وتُستخدم من الاختبارات
    table["_headers_for"] = config.headers_for
    table["_write_header"] = storage._write_header
    table["_add_missing_sheets"] = storage._add_missing_sheets
    table["_add_missing_columns"] = storage._add_missing_columns
    table["_auto_import_excel_once"] = storage._auto_import_excel_once
    table["_app_data_dir"] = runtime_module().app_data_dir
    table["_sub_dir"] = runtime_module().sub_dir
    table["_load_rows"] = storage._load_rows
    table["_save_row"] = storage._save_row
    table["_save_row_by_name"] = storage._save_row_by_name
    table["_delete_row"] = storage._delete_row
    table["_ensure_unique_name"] = masterdata._ensure_unique_name
    return table
class _DataFacade(_types.ModuleType):
    """
    وحدة تعيد توجيه كل قراءة/كتابة اسم إلى المصدر الصحيح داخل core/data.

    تقرأ بالترتيب: قاموس الواجهة ← runtime (للمسارات والمحرك) ← خطأ.
    وتكتب القيم المتغيّرة إلى runtime حتى تظل مصدراً واحداً للحقيقة، فأي
    تعديل من الاختبارات أو الأدوات (rd.BAK_FILE = ...) يصل إلى الكود الفعلي
    بدل أن يضيع في نسخة محلية.
    """

    def __getattr__(self, name):
        table = self.__dict__.setdefault("_table", _make_facade())
        runtime = runtime_module()
        if name in ("DATA_FILE", "BAK_FILE", "BACKEND", "_schema_checked", "_lock_handle"):
            return getattr(runtime, name)
        try:
            return table[name]
        except KeyError:
            raise AttributeError(
                "module %r has no attribute %r" % (self.__name__, name)) from None

    def __setattr__(self, name, value):
        # لا تُسجَّل الدوال كسمات على الوحدة (وإلا حجبت __getattr__)
        if name in ("DATA_FILE", "BAK_FILE", "BACKEND", "_schema_checked", "_lock_handle"):
            setattr(runtime_module(), name, value)
            return
        _make_table(self)[name] = value

    def __dir__(self):
        return sorted(set(list(self.__dict__) + list(_make_table(self))))


def _make_table(module):
    table = module.__dict__.get("_table")
    if table is None:
        table = _make_facade()
        module.__dict__["_table"] = table
    return table


_module = _sys.modules[__name__]
_module.__class__ = _DataFacade
_module._table = _make_facade()
