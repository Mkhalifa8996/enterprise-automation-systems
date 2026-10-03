# -*- coding: utf-8 -*-
"""طبقة الوصول إلى البيانات: القراءة والكتابة على قاعدة البيانات.

كل دوال القراءة/الكتابة في المشروع تمر من هنا، فلا تعرف واجهة المستخدم
شيئاً عن SQL ولا عن ملف إكسل. بعد كل تعديل تُحدَّث نسخة إكسل المرآة
تلقائياً (انظر excel_mirror.py).

قاعدة الاتصال تُفتح عند الحاجة وتُغلق في كل الأحوال؛ ويمرّر المستدعي
``conn`` اختيارياً ليُعيد استخدام اتصال واحد داخل عملية مركّبة.
"""

import sqlite3

from ..constants import META_FIELDS, SERVICE_ITEMS
from ..utils import normalize_company_code, safe_float, safe_int, safe_str
from . import excel_mirror
from .db import SaveError, ensure_database


# ------------------------------------------------------------------
# المزامنة مع ملف إكسل المرآة
# ------------------------------------------------------------------
def sync_excel():
    """يعيد كتابة ملف data.xlsx من محتوى قاعدة البيانات.

    لا تُفشل العملية إن تعذّرت الكتابة (مثل فتح الملف في إكسل)، لأن بيانات
    قاعدة البيانات محفوظة وسليمة؛ نسجّل التحذير فقط لأنها نسخة ثانوية.
    """
    try:
        excel_mirror.export_to_excel(
            load_invoices(), load_customers(), load_payments()
        )
    except Exception as exc:
        print(f"[تحذير] تعذّر تحديث نسخة إكسل المرآة: {exc}")


# ------------------------------------------------------------------
# الفواتير
# ------------------------------------------------------------------
def _invoice_items_to_rows(invno, items):
    """يحوّل بنود الفاتورة إلى صفوف جاهزة لجدول invoice_items."""
    rows = []
    total = len(items or [])
    for idx, (default_ar, default_en) in enumerate(SERVICE_ITEMS):
        item = items[idx] if items and idx < len(items) else {}
        rows.append((
            invno, idx,
            safe_str(item.get("label")) or default_ar,
            safe_str(item.get("labelEn")) or default_en,
            safe_int(item.get("dinar")),
            safe_int(item.get("fils")),
        ))
    # بنود إضافية قد يضيفها المستخدم خارج القائمة الافتراضية
    for idx in range(len(SERVICE_ITEMS), total):
        item = items[idx]
        rows.append((
            invno, idx, safe_str(item.get("label")), safe_str(item.get("labelEn")),
            safe_int(item.get("dinar")), safe_int(item.get("fils")),
        ))
    return rows


def load_invoices(conn=None):
    """يقرأ جميع الفواتير من قاعدة البيانات ويعيدها كقائمة قواميس."""
    own = conn is None
    conn = conn or ensure_database()
    try:
        rows = conn.execute(
            "SELECT " + ", ".join(key for key, _ in META_FIELDS)
            + ", notes, total FROM invoices ORDER BY date, invno"
        ).fetchall()
        items_by_invno = {}
        for item_row in conn.execute(
            "SELECT invno, idx, label_ar, label_en, dinar, fils "
            "FROM invoice_items ORDER BY invno, idx"
        ):
            items_by_invno.setdefault(item_row["invno"], []).append({
                "label": item_row["label_ar"],
                "labelEn": item_row["label_en"],
                "dinar": item_row["dinar"],
                "fils": item_row["fils"],
            })

        invoices = []
        for row in rows:
            d = {key: row[key] for key, _ in META_FIELDS}
            # `notes` ليست ضمن META_FIELDS (لأنها تأتي بعد أعمدة البنود في
            # ملف إكسل)، فتُقرأ من عمودها وتُضاف صراحةً.
            d["notes"] = row["notes"]
            d["items"] = items_by_invno.get(row["invno"], [])
            d["total"] = safe_float(row["total"])
            invoices.append(d)
        return invoices
    finally:
        if own:
            conn.close()


def get_invoice(invno, conn=None):
    """يقرأ فاتورة واحدة برقمها، أو None إن لم توجد."""
    target = safe_str(invno)
    for inv in load_invoices(conn=conn):
        if safe_str(inv.get("invno")) == target:
            return inv
    return None


def save_invoice(d, editing_invno=None, conn=None):
    """يضيف فاتورة جديدة أو يحدّث فاتورة موجودة (برقمها)، ويعيد رقمها."""
    own = conn is None
    conn = conn or ensure_database()
    try:
        invno = safe_str(d.get("invno"))
        if not invno:
            raise SaveError("رقم الفاتورة مطلوب ولا يمكن تركه فارغاً.")
        meta_values = [safe_str(d.get(key)) for key, _ in META_FIELDS]
        items = d.get("items") or []
        # الإجمالي يُحسب من البنود دائماً (ألف دينار + 1000 فلس) لضمان التطابق.
        total_fils = sum(safe_int(it.get("dinar")) * 1000 + safe_int(it.get("fils"))
                         for it in items)

        conn.execute(
            f"INSERT INTO invoices ({', '.join(k for k, _ in META_FIELDS)}, notes, total) "
            f"VALUES ({', '.join(['?'] * (len(META_FIELDS) + 2))}) "
            f"ON CONFLICT(invno) DO UPDATE SET "
            + ", ".join(f"{key}=excluded.{key}" for key, _ in META_FIELDS)
            + ", notes=excluded.notes, total=excluded.total",
            meta_values + [safe_str(d.get("notes")), round(total_fils / 1000, 3)],
        )
        conn.execute("DELETE FROM invoice_items WHERE invno = ?", (invno,))
        conn.executemany(
            "INSERT INTO invoice_items (invno, idx, label_ar, label_en, dinar, fils) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            _invoice_items_to_rows(invno, items),
        )
        # إذا غيّر المستخدم رقم الفاتورة عند التعديل لزم حذف الرقم القديم،
        # وإلا بقيت نسختان من الفاتورة نفسها في قاعدة البيانات.
        if editing_invno is not None and safe_str(editing_invno) != invno:
            conn.execute("DELETE FROM invoices WHERE invno = ?", (safe_str(editing_invno),))
            conn.execute("DELETE FROM invoice_items WHERE invno = ?", (safe_str(editing_invno),))
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise SaveError(f"تعذّر حفظ الفاتورة في قاعدة البيانات:\n{exc}")
    finally:
        if own:
            conn.close()

    sync_excel()
    return invno


def delete_invoice(invno, conn=None):
    """يحذف فاتورة بنودها (تُحذف البنود تلقائياً عبر المفتاح الخارجي)."""
    own = conn is None
    conn = conn or ensure_database()
    try:
        target = safe_str(invno)
        conn.execute("DELETE FROM invoices WHERE invno = ?", (target,))
        conn.execute("DELETE FROM invoice_items WHERE invno = ?", (target,))
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise SaveError(f"تعذّر حذف الفاتورة:\n{exc}")
    finally:
        if own:
            conn.close()
    sync_excel()


# ------------------------------------------------------------------
# العملاء
# ------------------------------------------------------------------
def load_customers(conn=None):
    """يقرأ جميع العملاء ويعيدهم كقائمة قواميس."""
    own = conn is None
    conn = conn or ensure_database()
    try:
        rows = conn.execute(
            "SELECT name, phone, address, notes, company_code FROM customers ORDER BY name"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        if own:
            conn.close()


def get_customer(name, conn=None):
    """يقرأ عميلاً واحداً باسمه، أو None إن لم يوجد."""
    target = safe_str(name)
    for c in load_customers(conn=conn):
        if safe_str(c.get("name")) == target:
            return c
    return None


def save_customer(c, editing_name=None, conn=None):
    """يضيف عميلاً جديداً أو يحدّث عميلاً موجوداً (باسمه)، ويعيد اسمه."""
    own = conn is None
    conn = conn or ensure_database()
    try:
        name = safe_str(c.get("name"))
        if not name:
            raise SaveError("اسم العميل مطلوب ولا يمكن تركه فارغاً.")
        conn.execute(
            "INSERT INTO customers (name, phone, address, notes, company_code) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(name) DO UPDATE SET phone=excluded.phone, "
            "address=excluded.address, notes=excluded.notes, "
            "company_code=excluded.company_code",
            [name, safe_str(c.get("phone")), safe_str(c.get("address")),
             safe_str(c.get("notes")), normalize_company_code(c.get("company_code"))],
        )
        # عند تغيير اسم العميل ننقل فواتيره ودفعاته معه حتى لا تنقطع الصلة.
        if editing_name is not None and safe_str(editing_name) != name:
            old = safe_str(editing_name)
            conn.execute("DELETE FROM customers WHERE name = ?", (old,))
            conn.execute("UPDATE invoices SET customer = ? WHERE customer = ?", (name, old))
            conn.execute("UPDATE payments SET customer = ? WHERE customer = ?", (name, old))
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise SaveError(f"تعذّر حفظ العميل في قاعدة البيانات:\n{exc}")
    finally:
        if own:
            conn.close()
    sync_excel()
    return name


def delete_customer(name, conn=None):
    """يحذف عميلاً. فواتيره ودفعاته تبقى محفوظة في السجلات."""
    own = conn is None
    conn = conn or ensure_database()
    try:
        conn.execute("DELETE FROM customers WHERE name = ?", (safe_str(name),))
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise SaveError(f"تعذّر حذف العميل:\n{exc}")
    finally:
        if own:
            conn.close()
    sync_excel()


# ------------------------------------------------------------------
# الدفعات
# ------------------------------------------------------------------
def load_payments(conn=None):
    """يقرأ جميع الدفعات المسجّلة مع الفواتير المسدَّدة لكل منها."""
    own = conn is None
    conn = conn or ensure_database()
    try:
        applied = {}
        for row in conn.execute(
            "SELECT payment_id, invno FROM payment_invoices ORDER BY payment_id, position"
        ):
            applied.setdefault(row["payment_id"], []).append(row["invno"])
        payments = []
        for row in conn.execute(
            "SELECT id, customer, date, amount, notes FROM payments ORDER BY date, id"
        ):
            p = dict(row)
            p["amount"] = safe_float(row["amount"])
            p["applied_invoices"] = applied.get(row["id"], [])
            payments.append(p)
        return payments
    finally:
        if own:
            conn.close()


def get_payment(payment_id, conn=None):
    """يقرأ دفعة واحدة برقم سندها، أو None إن لم توجد."""
    target = safe_str(payment_id)
    for p in load_payments(conn=conn):
        if safe_str(p.get("id")) == target:
            return p
    return None


def _receipt_number_for_customer(customer_name):
    """يولّد رقم سند القبض التالي لعميل، من رمز شركته.

    يُرفع خطأ `ValueError` إن كان العميل بلا رمز شركة، لأن الترقيم التلقائي
    يتعذّر بدونه (وهو ما كان سلوك الإصدار السابق).
    """
    # استيراد مؤجل لتفادي الاستيراد الدائري: numbering يعتمد على repository.
    from .numbering import next_receipt_number

    for c in load_customers():
        if safe_str(c.get("name")) == safe_str(customer_name):
            code = normalize_company_code(c.get("company_code"))
            if code:
                return next_receipt_number(code)
            break
    raise ValueError(
        f'العميل "{customer_name}" ليس له رمز شركة؛ '
        "لا يمكن توليد رقم سند القبض تلقائياً."
    )


def save_payment(p, editing_id=None, conn=None):
    """يضيف دفعة جديدة أو يحدّث دفعة موجودة، ويعيد رقم السند.

    إذا لم يُمرَّر رقم سند، يُولَّد تلقائياً من رمز شركة العميل (رمز الشركة
    + رقم تسلسلي من 4 أرقام)، تماماً كما كان في الإصدار السابق.
    """
    own = conn is None
    conn = conn or ensure_database()
    try:
        customer_name = safe_str(p.get("customer"))
        pid = safe_str(p.get("id"))
        if not pid:
            # دفعة جديدة، أو العميل تغيّر أثناء التعديل ⇒ سند جديد للعميل الجديد.
            original_customer = None
            if editing_id is not None:
                row = conn.execute(
                    "SELECT customer FROM payments WHERE id = ?", (safe_str(editing_id),)
                ).fetchone()
                original_customer = safe_str(row["customer"]) if row else None
            if editing_id is not None and original_customer == customer_name:
                pid = safe_str(editing_id)
            else:
                pid = _receipt_number_for_customer(customer_name)

        conn.execute(
            "INSERT INTO payments (id, customer, date, amount, notes) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET customer=excluded.customer, date=excluded.date, "
            "amount=excluded.amount, notes=excluded.notes",
            [pid, safe_str(p.get("customer")), safe_str(p.get("date")),
             round(safe_float(p.get("amount")), 3), safe_str(p.get("notes"))],
        )
        conn.execute("DELETE FROM payment_invoices WHERE payment_id = ?", (pid,))
        conn.executemany(
            "INSERT INTO payment_invoices (payment_id, invno, position) VALUES (?, ?, ?)",
            [(pid, safe_str(inv), pos)
             for pos, inv in enumerate(p.get("applied_invoices") or []) if safe_str(inv)],
        )
        if editing_id is not None and safe_str(editing_id) != pid:
            old = safe_str(editing_id)
            conn.execute("DELETE FROM payments WHERE id = ?", (old,))
            conn.execute("DELETE FROM payment_invoices WHERE payment_id = ?", (old,))
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise SaveError(f"تعذّر حفظ الدفعة في قاعدة البيانات:\n{exc}")
    finally:
        if own:
            conn.close()
    sync_excel()
    return pid


def delete_payment(payment_id, conn=None):
    """يحذف دفعة وتخصيصاتها."""
    own = conn is None
    conn = conn or ensure_database()
    try:
        target = safe_str(payment_id)
        conn.execute("DELETE FROM payments WHERE id = ?", (target,))
        conn.execute("DELETE FROM payment_invoices WHERE payment_id = ?", (target,))
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise SaveError(f"تعذّر حذف الدفعة:\n{exc}")
    finally:
        if own:
            conn.close()
    sync_excel()
