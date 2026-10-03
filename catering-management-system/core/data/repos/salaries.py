# -*- coding: utf-8 -*-
"""
core.data.repos.salaries — رواتب العمال شهرية عبر تفاوزة تمامًا (upsert).
"""

from core.data import storage
from core.data.validation import is_month, safe_float
from core.money import add, sub, to_float


def load_salaries():
    return storage.load_rows("salaries", "id")


def save_salary(data, editing_id=None):
    """
    يحفظ راتب شهر واحد لموظف واحد. إذا كان للموظف سجل بنفس الشهر يُحدَّث بدل
    إنشاء صف جديد، حتى لا يُحتسب راتب الشهر مرتين في التقارير المالية.
    """
    staff = str(data.get("staff", "")).strip()
    month = str(data.get("month", "")).strip()
    if not staff:
        raise ValueError("الرجاء اختيار الموظف.")
    if not is_month(month):
        raise ValueError("الشهر يجب أن يكون بصيغة YYYY-MM.")
    data["staff"], data["month"] = staff, month

    rows = load_salaries()
    existing = None
    if editing_id is None:
        existing = next((r for r in rows
                         if str(r.get("staff", "")).strip() == staff
                         and str(r.get("month", "")).strip() == month), None)
        if existing:
            editing_id = existing.get("id")
    else:
        existing = next((r for r in rows if str(r.get("id", "")) == str(editing_id)), None)

    data["id"] = str(editing_id if editing_id is not None else storage.next_id(rows))
    base = safe_float(data.get("base_salary"))
    bonus = safe_float(data.get("bonuses"))
    adv = safe_float(data.get("advances"))
    ded = safe_float(data.get("deductions"))
    data["net_salary"] = to_float(sub(add(base, bonus), add(adv, ded)))
    if not str(data.get("paid", "")).strip():
        # الحفاظ على حالة الدفع السابقة عند التعديل، وإلا فالقيمة الافتراضية "لا"
        data["paid"] = (existing or {}).get("paid") or "لا"
    storage.save_row("salaries", "id", data, editing_id)


def delete_salary(row_id):
    storage.delete_row("salaries", "id", row_id)
