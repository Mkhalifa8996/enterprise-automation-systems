# -*- coding: utf-8 -*-
"""طبقة البيانات: الواجهة الوحيدة التي تتعامل معها بقية أجزاء البرنامج.

تتكوّن من:
    db            الاتصال بقاعدة البيانات وإنشاء الجداول.
    excel_mirror  نسخة data.xlsx المرآة (قراءة قديمة/كتابة محدَّثة).
    repository    عمليات القراءة والكتابة (فواتير/عملاء/دفعات).
    numbering     الترقيم التلقائي حسب رمز الشركة.
    analytics     حسابات الأرصدة وحالة السداد ولوحة المعلومات.
"""

from ..constants import META_FIELDS
from ..utils import safe_float, safe_int, safe_str
from . import analytics, excel_mirror, numbering
from .analytics import (
    allocate_payment_to_invoices,
    customer_balances,
    get_dashboard_stats,
    invoice_payment_status,
)
from .db import SaveError, ensure_database
from .excel_mirror import invoice_dict_to_row, row_to_invoice_dict
from .numbering import (
    find_customer_by_company_code,
    next_available_company_code,
    next_invoice_number,
    next_receipt_number,
    normalize_company_code,
)
from .repository import (
    delete_customer,
    delete_invoice,
    delete_payment,
    get_customer,
    get_invoice,
    get_payment,
    load_customers,
    load_invoices,
    load_payments,
    save_customer,
    save_invoice,
    save_payment,
    sync_excel,
)

_migration_done = False


def _database_is_empty():
    """هل قاعدة البيانات خالية من أي بيانات؟"""
    conn = ensure_database()
    try:
        for table in ("invoices", "customers", "payments"):
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if count:
                return False
        return True
    finally:
        conn.close()


def migrate_excel_to_database():
    """ينقل بيانات `data.xlsx` القديمة إلى قاعدة البيانات (مرة واحدة عند أول تشغيل).

    يعمل فقط إذا كانت قاعدة البيانات فارغة وكان ملف إكسل يحوي بيانات، فلا
    يُكرّر الاستيراد ولا يمسّ بيانات المستخدم الحالية إطلاقاً.
    """
    global _migration_done
    if _migration_done:
        return False
    try:
        if not _database_is_empty():
            _migration_done = True
            return False
        invoices, customers, payments = excel_mirror.read_workbook_data()
        if not (invoices or customers or payments):
            return False

        conn = ensure_database()
        try:
            for c in customers:
                conn.execute(
                    "INSERT OR REPLACE INTO customers (name, phone, address, notes, company_code) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [safe_str(c.get("name")), safe_str(c.get("phone")),
                     safe_str(c.get("address")), safe_str(c.get("notes")),
                     normalize_company_code(c.get("company_code"))],
                )
            for inv in invoices:
                items = inv.get("items") or []
                total_fils = sum(safe_int(it.get("dinar")) * 1000 + safe_int(it.get("fils"))
                                 for it in items)
                conn.execute(
                    "INSERT OR REPLACE INTO invoices ("
                    + ", ".join(key for key, _ in META_FIELDS)
                    + ", notes, total) VALUES ("
                    + ", ".join(["?"] * (len(META_FIELDS) + 2)) + ")",
                    [safe_str(inv.get(key)) for key, _ in META_FIELDS]
                    + [safe_str(inv.get("notes")), round(total_fils / 1000, 3)],
                )
                conn.executemany(
                    "INSERT OR REPLACE INTO invoice_items "
                    "(invno, idx, label_ar, label_en, dinar, fils) VALUES (?, ?, ?, ?, ?, ?)",
                    [(safe_str(inv.get("invno")), idx,
                      safe_str(it.get("label")), safe_str(it.get("labelEn")),
                      safe_int(it.get("dinar")), safe_int(it.get("fils")))
                     for idx, it in enumerate(items)],
                )
            for p in payments:
                conn.execute(
                    "INSERT OR REPLACE INTO payments (id, customer, date, amount, notes) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [safe_str(p.get("id")), safe_str(p.get("customer")), safe_str(p.get("date")),
                     round(safe_float(p.get("amount")), 3), safe_str(p.get("notes"))],
                )
                conn.executemany(
                    "INSERT OR REPLACE INTO payment_invoices (payment_id, invno, position) "
                    "VALUES (?, ?, ?)",
                    [(safe_str(p.get("id")), safe_str(inv), pos)
                     for pos, inv in enumerate(p.get("applied_invoices") or []) if safe_str(inv)],
                )
            conn.commit()
        finally:
            conn.close()
        _migration_done = True
        return True
    except Exception as exc:
        print(f"[تحذير] تعذّر استيراد بيانات data.xlsx: {exc}")
        return False


def ensure_storage():
    """تهيئة التخزين عند بدء التشغيل: إنشاء قاعدة البيانات ثم استيراد الإكسل عند الحاجة."""
    ensure_database()
    migrate_excel_to_database()


__all__ = [
    "SaveError", "ensure_storage", "ensure_database", "sync_excel",
    "load_invoices", "save_invoice", "delete_invoice", "get_invoice",
    "load_customers", "save_customer", "delete_customer", "get_customer",
    "load_payments", "save_payment", "delete_payment", "get_payment",
    "invoice_dict_to_row", "row_to_invoice_dict",
    "normalize_company_code", "find_customer_by_company_code",
    "next_available_company_code", "next_invoice_number", "next_receipt_number",
    "customer_balances", "allocate_payment_to_invoices", "invoice_payment_status",
    "get_dashboard_stats", "safe_int", "safe_float", "safe_str",
]