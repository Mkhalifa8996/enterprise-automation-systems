# -*- coding: utf-8 -*-
"""
core.data.repos.reporting — التقارير المالية وملخص المشتريات والمستحقات.
"""

from core.data.repos import expenses, invoices, salaries
from core.data.validation import month_bounds
from core.money import ZERO, add, money, sub, to_float


def financial_summary(date_from=None, date_to=None):
    """
    ملخص مالي تشغيلي عن فترة محددة:
      الإيرادات = مجموع الفواتير الصادرة خلال الفترة.
      المصروفات التشغيلية = المشتريات اليومية + الرواتب الصافية + المصاريف الشهرية الثابتة.
    مصاريف التأسيس تُحسب وتُعرض بشكل تراكمي منفصل (لأنها مصاريف لمرة واحدة
    لا تتكرر كل شهر ولا ترتبط بفترة تشغيلية معينة).
    """

    def date_in_range(d):
        text = str(d or "").strip()
        if not text:
            return True          # سجل بلا تاريخ لا يمكن استبعاده من الفترة
        if date_from and text < date_from:
            return False
        if date_to and text > date_to:
            return False
        return True

    def month_overlaps(month_value):
        """
        يُحتسب الراتب/المصروف الشهري إذا تقاطع أي يوم من الشهر مع الفترة المطلوبة.
        (سابقاً كان الشهر يُستبعد كاملاً إذا بدأت الفترة بعد أول يوم من الشهر.)
        """
        first, last = month_bounds(month_value)
        if first is None:
            return True
        if date_from and last < date_from:
            return False
        if date_to and first > date_to:
            return False
        return True

    revenue = float(add(*[i["total"] for i in invoices.load_invoices()
                          if date_in_range(i.get("date"))]))
    purchases_cost = float(add(*[p["total_cost"] for p in expenses.load_purchases()
                                 if date_in_range(p.get("date"))]))
    salaries_cost = float(add(*[s["net_salary"] for s in salaries.load_salaries()
                                if month_overlaps(s.get("month"))]))
    monthly_expenses_cost = float(add(*[m["amount"] for m in expenses.load_monthly_expenses()
                                        if month_overlaps(m.get("month"))]))
    petty_cash_cost = float(add(*[p["amount"] for p in expenses.load_petty_cash()
                                  if date_in_range(p.get("date"))]))
    operating_expenses = to_float(add(purchases_cost, salaries_cost,
                                      monthly_expenses_cost, petty_cash_cost))
    setup_expenses_total = float(add(*[s["cost"] for s in expenses.load_setup_expenses()]))
    # مستحقات العملاء غير المحصلة (تراكمي، بغض النظر عن فترة التقرير)
    outstanding = [sub(money(i.get("total")), money(i.get("paid_amount")))
                   for i in invoices.load_invoices()]
    outstanding = [b for b in outstanding if b > ZERO]
    receivables = to_float(add(*outstanding))

    return {
        "revenue": round(revenue, 3),
        "purchases_cost": round(purchases_cost, 3),
        "salaries_cost": round(salaries_cost, 3),
        "monthly_expenses_cost": round(monthly_expenses_cost, 3),
        "petty_cash_cost": round(petty_cash_cost, 3),
        "operating_expenses": to_float(operating_expenses),
        "operating_profit": to_float(sub(revenue, operating_expenses)),
        "setup_expenses_total": to_float(setup_expenses_total),
        "net_profit_after_setup": to_float(
            sub(sub(revenue, operating_expenses), setup_expenses_total)),
        "receivables": receivables,
    }
