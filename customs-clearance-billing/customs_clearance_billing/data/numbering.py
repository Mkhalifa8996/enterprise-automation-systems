# -*- coding: utf-8 -*-
"""ترقيم الفواتير وسندات القبض تلقائياً حسب رمز الشركة."""

from ..utils import safe_str
from .repository import load_customers, load_invoices, load_payments
from ..utils import normalize_company_code

__all__ = [
    "normalize_company_code", "find_customer_by_company_code",
    "next_available_company_code", "next_invoice_number", "next_receipt_number",
]


def find_customer_by_company_code(company_code, exclude_name=None):
    """يعيد اسم أول عميل آخر يستخدم نفس رمز الشركة (لمنع التكرار)، أو None."""
    code = normalize_company_code(company_code)
    if not code:
        return None
    for c in load_customers():
        if c["company_code"] == code and c["name"] != exclude_name:
            return c["name"]
    return None


def next_available_company_code():
    """يعيد أصغر رمز شركة غير مستخدم (من 01 إلى 99) لتيُعيَّن تلقائياً لعميل جديد."""
    used = {c["company_code"] for c in load_customers() if c["company_code"]}
    for n in range(1, 100):
        code = f"{n:02d}"
        if code not in used:
            return code
    raise ValueError("تم الوصول للحد الأقصى لعدد الشركات (99)؛ لا يوجد رمز شركة متاح.")


def _next_sequence(code, existing_numbers):
    """يعيد أعلى رقم تسلسلي مستخدم للرمز المعطى، مضافاً إليه واحداً."""
    max_seq = 0
    for number in existing_numbers:
        number = safe_str(number).strip()
        if len(number) == 6 and number.isdigit() and number[:2] == code:
            max_seq = max(max_seq, int(number[2:]))
    next_seq = max_seq + 1
    if next_seq > 9999:
        raise ValueError("تم الوصول للحد الأقصى للترقيم (9999) لهذه الشركة.")
    return f"{code}{next_seq:04d}"


def next_invoice_number(company_code):
    """يولّد رقم الفاتورة التالي لعميل بصيغة: رمز الشركة (رقمان) + تسلسلي (4 أرقام).
    مثال: الرمز 25 مع الفاتورة الثانية لهذه الشركة تعطي 250002."""
    code = normalize_company_code(company_code)
    if not code:
        raise ValueError("رمز الشركة غير صالح؛ يجب أن يكون رقماً بين 01 و 99.")
    return _next_sequence(code, [inv.get("invno") for inv in load_invoices()])


def next_receipt_number(company_code):
    """يولّد رقم سند القبض التالي لعميل بنفس أسلوب ترقيم الفواتير."""
    code = normalize_company_code(company_code)
    if not code:
        raise ValueError("رمز الشركة غير صالح؛ يجب أن يكون رقماً بين 01 و 99.")
    return _next_sequence(code, [p.get("id") for p in load_payments()])