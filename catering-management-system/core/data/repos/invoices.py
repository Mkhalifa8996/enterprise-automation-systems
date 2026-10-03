# -*- coding: utf-8 -*-
"""
core.data.repos.invoices — الفاتورر، المدفوعات، وكشف حساب العميل.
"""

import json
from datetime import date

from core.data import storage
from core.data.repos import orders
from core.data.validation import invoice_items, is_iso_date, safe_float, safe_int
from core.money import ZERO, add, money, sub, to_float


def load_invoices():
    return storage.load_rows("invoices", "invoice_no")


def next_invoice_no():
    rows = load_invoices()
    nums = [safe_int(r["invoice_no"]) for r in rows if str(r["invoice_no"]).isdigit()]
    return str((max(nums) if nums else 1000) + 1)


def save_invoice(data, editing_invno=None):
    storage.save_row_by_name("invoices", data, editing_invno)


def delete_invoice(invoice_no):
    storage.delete_row("invoices", "invoice_no", invoice_no)


def create_invoice_for_customer(customer, order_ids, event_ids, extra_notes=""):
    """ينشئ فاتورة جديدة تجمع طلبات مؤسسات ومناسبات محددة لعميل معيّن، ويعلّمها كمفوترة."""
    customer = str(customer or "").strip()
    if not customer:
        raise ValueError("الرجاء اختيار عميل أولاً.")
    orders_by_id = {str(o["id"]): o for o in orders.load_institutional_orders()}
    events_by_id = {str(e["id"]): e for e in orders.load_events()}
    items = []
    total = ZERO
    for oid in order_ids:
        o = orders_by_id.get(str(oid))
        if not o:
            continue
        amount = safe_float(o.get("total"))
        desc = (f"وجبات {o.get('meal_type','')} بتاريخ {o.get('date','')} - "
                f"الكمية {o.get('quantity','')} - {o.get('delivery_location','')}").strip()
        items.append({"desc": desc, "amount": to_float(amount)})
        total = add(total, amount)
    for eid in event_ids:
        e = events_by_id.get(str(eid))
        if not e:
            continue
        amount = safe_float(e.get("total"))
        deposit = safe_float(e.get("deposit"))
        desc = (f"{e.get('event_type','')} بتاريخ {e.get('event_date','')} - "
                f"عدد الأشخاص {e.get('guests_count','')}"
                + (f" (بعد خصم عربون {deposit:.3f} د.ك)" if deposit else ""))
        amount = to_float(sub(amount, deposit))
        items.append({"desc": desc, "amount": amount})
        total = add(total, amount)

    if not items:
        raise ValueError("لا توجد بنود صالحة للفاتورة.")

    invno = next_invoice_no()
    invoice = {
        "invoice_no": invno,
        "date": date.today().isoformat(),
        "customer": customer,
        "items_json": json.dumps(items, ensure_ascii=False),
        "total": to_float(total),
        "notes": extra_notes,
        "paid_amount": 0.0,
        "status": "غير مدفوعة",
    }
    save_invoice(invoice)
    for oid in order_ids:
        orders.mark_institutional_order_invoiced(oid, invno)
    for eid in event_ids:
        orders.mark_event_invoiced(eid, invno)
    storage.log_action("إصدار فاتورة", "invoices", invno,
               "العميل %s — %.3f د.ك" % (customer, safe_float(invoice["total"])))
    return invoice


def unbilled_institutional_orders_for_customer(customer):
    return [o for o in orders.load_institutional_orders()
            if o.get("customer") == customer and o.get("invoiced") != "نعم"]


def unbilled_events_for_customer(customer):
    return [e for e in orders.load_events()
            if e.get("customer") == customer and e.get("invoiced") != "نعم"]


def load_payments():
    return storage.load_rows("payments", "id")


def save_payment(data, editing_id=None):
    """
    يسجل دفعة على فاتورة موجودة ثم يعيد حساب المدفوع وحالة التحصيل للفاتورة.
    اسم العميل يُملأ تلقائياً من الفاتورة إذا تُرك فارغاً.
    """
    if not is_iso_date(data.get("date")):
        raise ValueError("تاريخ الدفعة يجب أن يكون بصيغة YYYY-MM-DD.")
    invno = str(data.get("invoice_no", "")).strip()
    if not invno:
        raise ValueError("الرجاء اختيار رقم الفاتورة.")
    invoice = next((i for i in load_invoices()
                    if str(i.get("invoice_no", "")).strip() == invno), None)
    if invoice is None:
        raise ValueError("رقم الفاتورة غير موجود: %s" % invno)
    amount = safe_float(data.get("amount"))
    if amount <= 0:
        raise ValueError("مبلغ الدفعة يجب أن يكون أكبر من صفر.")
    rows = load_payments()
    data["id"] = str(editing_id if editing_id is not None else storage.next_id(rows))
    data["invoice_no"] = invno
    data["amount"] = to_float(amount)
    if not str(data.get("customer", "")).strip():
        data["customer"] = invoice.get("customer", "")
    if not str(data.get("method", "")).strip():
        data["method"] = "نقداً"
    storage.save_row("payments", "id", data, editing_id)
    _recalc_invoice_payment(invno)
    return data


def delete_payment(row_id):
    """يحذف دفعة ثم يعيد حساب حالة الفاتورة المرتبطة بها."""
    row = next((r for r in load_payments() if str(r.get("id")) == str(row_id)), None)
    storage.delete_row("payments", "id", row_id)
    if row:
        _recalc_invoice_payment(row.get("invoice_no"))


def _recalc_invoice_payment(invoice_no):
    """يعيد حساب (المدفوع) و(حالة التحصيل) لفاتورة من مجموع دفعاتها."""
    invoice = next((i for i in load_invoices()
                    if str(i.get("invoice_no", "")).strip() == str(invoice_no).strip()), None)
    if invoice is None:
        return
    paid = add(*[p["amount"] for p in load_payments()
                 if str(p.get("invoice_no", "")).strip() == str(invoice_no).strip()])
    invoice["paid_amount"] = to_float(paid)
    remaining = sub(money(invoice.get("total")), paid)
    if remaining <= ZERO:
        status = "مدفوعة"
    elif paid <= ZERO:
        status = "غير مدفوعة"
    else:
        status = "جزئية"
    invoice["status"] = status
    save_invoice(invoice, editing_invno=invoice.get("invoice_no"))


def invoice_balance(inv):
    """المتبقي على الفاتورة (لا يعيد قيماً سالبة عند الدفع الزائد)."""
    balance = sub(money(inv.get("total")), money(inv.get("paid_amount")))
    return to_float(balance) if balance > ZERO else 0.0


def customer_statement(customer, date_from=None, date_to=None):
    """
    كشف حساب عميل (مثل كشوف حساب الشركات): الفواتير مدين عليها والمدفوعات
    دائن له، مع رصيد متحرك. عربون المناسبة غير مدرج كسطر مستقل لأنه مطروح
    أصلاً من إجمالي الفاتورة عند إصدارها.
    """
    customer = str(customer or "").strip()
    if not customer:
        raise ValueError("الرجاء اختيار العميل.")

    def in_range(d):
        text = str(d or "").strip()
        if not text:
            return True
        if date_from and text < date_from:
            return False
        if date_to and text > date_to:
            return False
        return True

    entries = []
    for inv in load_invoices():
        if inv.get("customer") != customer or not in_range(inv.get("date")):
            continue
        items = invoice_items(inv)
        entries.append({
            "date": str(inv.get("date", "")),
            "doc": "فاتورة %s" % inv.get("invoice_no", ""),
            "description": ("%d بنود" % len(items)) if items else "",
            "debit": to_float(money(inv.get("total"))),
            "credit": 0.0,
        })
    for p in load_payments():
        if p.get("customer") != customer or not in_range(p.get("date")):
            continue
        entries.append({
            "date": str(p.get("date", "")),
            "doc": "دفعة على فاتورة %s" % p.get("invoice_no", ""),
            "description": p.get("method", ""),
            "debit": 0.0,
            "credit": to_float(money(p.get("amount"))),
        })
    entries.sort(key=lambda e: (e["date"], e["doc"]))
    balance = ZERO
    for e in entries:
        balance = add(balance, e["debit"], -e["credit"])
        e["balance"] = to_float(balance)
    return {
        "customer": customer,
        "rows": entries,
        "total_invoiced": to_float(add(*[e["debit"] for e in entries])),
        "total_paid": to_float(add(*[e["credit"] for e in entries])),
        # الرصيد النهائي هو آخر رصيد متحرك (وليس مجموع الأرصدة)
        "balance": entries[-1]["balance"] if entries else 0.0,
    }
