# -*- coding: utf-8 -*-
"""
core.analytics — حسابات التحليلات والرسوم البيانية (إيراد شهري، مصروفات،
أعلى العملاء، هامش الربح).

تعمل فوق دوال التحميل في restaurant_data (تدعم محركي Excel وSQLite دون
تغيير) وتُرجع قواميس/قوائم جاهزة للعرض في matplotlib أو في واجهة الويب.
"""

from collections import defaultdict

import restaurant_data as rd
from core.money import add, money, sub, to_float, ZERO


def _month_key(date_text):
    """يستخرج YYYY-MM من تاريخ YYYY-MM-DD، أو None إذا كان غير صالح."""
    text = str(date_text or "").strip()[:7]
    if len(text) == 7 and text[4] == "-" and rd.is_month(text):
        return text
    return None


def monthly_series(months=12):
    """
    سلسلة آخر N شهراً (بما فيها الشهر الحالي): لكل شهر
    الإيرادات، المشتريات، الرواتب، المصاريف الثابتة، النثريات،
    إجمالي المصروفات، وصافي الربح التشغيلي.
    """
    from datetime import date as _date

    today = _date.today()
    keys = []
    y, m = today.year, today.month
    for _ in range(max(int(months or 12), 1)):
        keys.append("%04d-%02d" % (y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    keys.reverse()

    rev = defaultdict(lambda: ZERO)
    pur = defaultdict(lambda: ZERO)
    sal = defaultdict(lambda: ZERO)
    fix = defaultdict(lambda: ZERO)
    petty = defaultdict(lambda: ZERO)

    for inv in rd.load_invoices():
        k = _month_key(inv.get("date"))
        if k in keys or k is None and False:
            pass
        if k:
            rev[k] = add(rev[k], money(inv.get("total")))
    for p in rd.load_purchases():
        k = _month_key(p.get("date"))
        if k:
            pur[k] = add(pur[k], money(p.get("total_cost")))
    for s in rd.load_salaries():
        k = str(s.get("month") or "").strip()[:7]
        if k in keys and rd.is_month(k):
            sal[k] = add(sal[k], money(s.get("net_salary")))
    for e in rd.load_monthly_expenses():
        k = str(e.get("month") or "").strip()[:7]
        if k in keys and rd.is_month(k):
            fix[k] = add(fix[k], money(e.get("amount")))
    for p in rd.load_petty_cash():
        k = _month_key(p.get("date"))
        if k:
            petty[k] = add(petty[k], money(p.get("amount")))

    rows = []
    for k in keys:
        op = add(pur[k], sal[k], fix[k], petty[k])
        rows.append({
            "month": k,
            "revenue": to_float(rev[k]),
            "purchases": to_float(pur[k]),
            "salaries": to_float(sal[k]),
            "fixed": to_float(fix[k]),
            "petty": to_float(petty[k]),
            "expenses": to_float(op),
            "profit": to_float(sub(rev[k], op)),
        })
    return rows


def top_clients(limit=5):
    """أعلى العملاء إيراداً (من الفواتير): [(الاسم، الإجمالي)] مرتبة تنازلياً."""
    totals = defaultdict(lambda: ZERO)
    for inv in rd.load_invoices():
        name = str(inv.get("customer") or "").strip()
        if name:
            totals[name] = add(totals[name], money(inv.get("total")))
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    return [(name, to_float(total)) for name, total in ranked[: max(int(limit or 5), 1)]]


def receivables_by_client():
    """المستحقات غير المحصلة لكل عميل: [(الاسم، المتبقي)] مرتبة تنازلياً."""
    totals = defaultdict(lambda: ZERO)
    for inv in rd.load_invoices():
        name = str(inv.get("customer") or "").strip()
        if not name:
            continue
        rest = sub(money(inv.get("total")), money(inv.get("paid_amount")))
        if rest > ZERO:
            totals[name] = add(totals[name], rest)
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    return [(name, to_float(total)) for name, total in ranked]
