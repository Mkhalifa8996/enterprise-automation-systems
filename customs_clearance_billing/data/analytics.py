# -*- coding: utf-8 -*-
"""حسابات التحصيل: أرصدة العملاء، حالة السداد لكل فاتورة، ومؤشرات لوحة المعلومات."""

from .repository import load_customers, load_invoices, load_payments


def customer_balances(invoices=None, payments=None):
    """يحسب لكل عميل: إجمالي الفواتير، إجمالي المدفوع، والرصيد المستحق.
    يعيد قائمة مرتبة أبجدياً: {customer, invoiced, paid, balance}."""
    invoices = invoices if invoices is not None else load_invoices()
    payments = payments if payments is not None else load_payments()

    invoiced_by_customer = {}
    for inv in invoices:
        name = inv.get("customer") or ""
        if not name:
            continue
        invoiced_by_customer[name] = invoiced_by_customer.get(name, 0.0) + float(inv.get("total") or 0)

    paid_by_customer = {}
    for p in payments:
        name = p.get("customer") or ""
        if not name:
            continue
        paid_by_customer[name] = paid_by_customer.get(name, 0.0) + float(p.get("amount") or 0)

    result = []
    for name in sorted(set(invoiced_by_customer) | set(paid_by_customer)):
        invoiced = round(invoiced_by_customer.get(name, 0.0), 3)
        paid = round(paid_by_customer.get(name, 0.0), 3)
        result.append({
            "customer": name,
            "invoiced": invoiced,
            "paid": paid,
            "balance": round(invoiced - paid, 3),
        })
    return result


def allocate_payment_to_invoices(inv_by_no, amount, applied_invoice_numbers):
    """يوزّع مبلغ دفعة على فواتير محددة بالترتيب المعطى، ويعيد (المتبقي، التخصيصات).

    كل فاتورة تُخصم منها ما يلزم من المبلغ حتى ينفد المبلغ أو تُسدَّد بالكامل.
    """
    remaining = round(float(amount or 0), 3)
    allocations = []
    for no in applied_invoice_numbers:
        if remaining <= 0.0005:
            break
        inv = inv_by_no.get(no)
        if not inv:
            continue
        due = round(float(inv.get("total", 0) or 0) - float(inv.get("paid", 0) or 0), 3)
        if due <= 0.0005:
            continue
        pay_amt = round(min(due, remaining), 3)
        inv["paid"] = round(float(inv.get("paid", 0) or 0) + pay_amt, 3)
        remaining = round(remaining - pay_amt, 3)
        allocations.append((no, pay_amt))
    return remaining, allocations


def invoice_payment_status(invoices=None, payments=None):
    """يحسب لكل فاتورة: الإجمالي، المدفوع، المتبقي، والحالة (مسددة/جزئية/غير مسددة).

    آلية التوزيع:
      - إن حدّدت الدفعة فواتير معيّنة، يُطبَّق مبلغها عليها بالترتيب الذي
        اختارها به المستخدم حتى ينفد المبلغ أو تُسدَّد الفواتير المحددة بالكامل،
        وأي مبلغ متبقٍ يُضاف إلى «الرصيد العام» لهذا العميل.
      - الدفعات التي لا تحدد فواتير تُضاف مباشرة إلى «الرصيد العام».
      - يُطبَّق «الرصيد العام» لكل عميل تلقائياً على أقدم فواتيره غير المسددة
        أولاً (FIFO) حسب التاريخ، وهذا يحاكي تسديد جزء من دفعة مجمّلة.

    يعيد قاموساً: {رقم_الفاتورة: {"total", "paid", "balance", "status"}}.
    """
    invoices = invoices if invoices is not None else load_invoices()
    payments = payments if payments is not None else load_payments()

    inv_by_no = {}
    by_customer = {}
    for inv in invoices:
        no = str(inv.get("invno", ""))
        if not no:
            continue
        inv_by_no[no] = {"total": float(inv.get("total") or 0), "paid": 0.0,
                         "customer": inv.get("customer", ""), "date": str(inv.get("date", ""))}
        by_customer.setdefault(inv.get("customer", ""), []).append(no)

    for name in by_customer:
        by_customer[name].sort(key=lambda no: (inv_by_no[no]["date"], no))

    general_pool = {}
    for p in payments:
        amount = float(p.get("amount") or 0)
        customer = p.get("customer", "")
        applied = [str(a).strip() for a in (p.get("applied_invoices") or []) if str(a).strip()]
        if applied:
            remaining, _ = allocate_payment_to_invoices(inv_by_no, amount, applied)
            if remaining > 0.0005:
                general_pool[customer] = general_pool.get(customer, 0.0) + remaining
        else:
            general_pool[customer] = general_pool.get(customer, 0.0) + amount

    for customer, pool in general_pool.items():
        remaining = pool
        for no in by_customer.get(customer, []):
            if remaining <= 0.0005:
                break
            inv = inv_by_no[no]
            due = inv["total"] - inv["paid"]
            if due <= 0.0005:
                continue
            pay_amt = min(due, remaining)
            inv["paid"] += pay_amt
            remaining -= pay_amt

    result = {}
    for no, inv in inv_by_no.items():
        total = round(inv["total"], 3)
        paid = round(inv["paid"], 3)
        balance = round(total - paid, 3)
        if balance <= 0.0005:
            status = "paid"
        elif paid > 0.0005:
            status = "partial"
        else:
            status = "unpaid"
        result[no] = {"total": total, "paid": paid, "balance": balance, "status": status}
    return result


def get_dashboard_stats(invoices=None, payments=None, customers=None):
    """يحسب مؤشرات الأداء الرئيسية للوحة المعلومات، وأكبر خمسة مدينين."""
    invoices = invoices if invoices is not None else load_invoices()
    payments = payments if payments is not None else load_payments()
    customers = customers if customers is not None else load_customers()

    total_invoiced = round(sum(float(i.get("total") or 0) for i in invoices), 3)
    total_paid = round(sum(float(p.get("amount") or 0) for p in payments), 3)
    total_outstanding = round(total_invoiced - total_paid, 3)

    status_map = invoice_payment_status(invoices, payments)
    balances = customer_balances(invoices, payments)
    top_debtors = sorted([b for b in balances if b["balance"] > 0.0005],
                         key=lambda b: -b["balance"])[:5]

    return {
        "invoice_count": len(invoices),
        "customer_count": len(customers),
        "payment_count": len(payments),
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "total_outstanding": total_outstanding,
        "paid_count": sum(1 for v in status_map.values() if v["status"] == "paid"),
        "partial_count": sum(1 for v in status_map.values() if v["status"] == "partial"),
        "unpaid_count": sum(1 for v in status_map.values() if v["status"] == "unpaid"),
        "top_debtors": top_debtors,
        "avg_invoice": round(total_invoiced / len(invoices), 3) if invoices else 0.0,
    }
