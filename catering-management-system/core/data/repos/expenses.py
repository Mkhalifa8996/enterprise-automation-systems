# -*- coding: utf-8 -*-
"""
core.data.repos.expenses — المصاريف والمشتريات: تأسيس، شهري، يومي، ونثريات يومية.
"""

from core.data import storage
from core.data.validation import is_iso_date, is_month, safe_float


def load_setup_expenses():
    return storage.load_rows("setup_expenses", "id")


def save_setup_expense(data, editing_id=None):
    if not is_iso_date(data.get("date")):
        raise ValueError("تاريخ المصروف يجب أن يكون بصيغة YYYY-MM-DD.")
    rows = load_setup_expenses()
    if editing_id is None:
        data["id"] = str(storage.next_id(rows))
    else:
        data["id"] = str(editing_id)
    storage.save_row("setup_expenses", "id", data, editing_id)


def delete_setup_expense(row_id):
    storage.delete_row("setup_expenses", "id", row_id)


def load_monthly_expenses():
    return storage.load_rows("monthly_expenses", "id")


def save_monthly_expense(data, editing_id=None):
    if not is_month(data.get("month")):
        raise ValueError("الشهر يجب أن يكون بصيغة YYYY-MM.")
    rows = load_monthly_expenses()
    if editing_id is None:
        data["id"] = str(storage.next_id(rows))
    else:
        data["id"] = str(editing_id)
    storage.save_row("monthly_expenses", "id", data, editing_id)


def delete_monthly_expense(row_id):
    storage.delete_row("monthly_expenses", "id", row_id)


def load_purchases():
    return storage.load_rows("purchases", "id")


def save_purchase(data, editing_id=None):
    if not is_iso_date(data.get("date")):
        raise ValueError("تاريخ الشراء يجب أن يكون بصيغة YYYY-MM-DD.")
    rows = load_purchases()
    if editing_id is None:
        data["id"] = str(storage.next_id(rows))
    else:
        data["id"] = str(editing_id)
    qty = safe_float(data.get("quantity"))
    cost = safe_float(data.get("unit_cost"))
    data["total_cost"] = round(qty * cost, 3)
    storage.save_row("purchases", "id", data, editing_id)


def delete_purchase(row_id):
    storage.delete_row("purchases", "id", row_id)


def purchases_for_date(day_iso):
    return [p for p in load_purchases() if str(p.get("date", "")) == day_iso]


def load_petty_cash():
    return storage.load_rows("petty_cash", "id")


def save_petty_cash(data, editing_id=None):
    if not is_iso_date(data.get("date")):
        raise ValueError("التاريخ يجب أن يكون بصيغة YYYY-MM-DD.")
    rows = load_petty_cash()
    data["id"] = str(editing_id if editing_id is not None else storage.next_id(rows))
    storage.save_row("petty_cash", "id", data, editing_id)


def delete_petty_cash(row_id):
    storage.delete_row("petty_cash", "id", row_id)


def petty_cash_for_date(day_iso):
    return [p for p in load_petty_cash() if str(p.get("date", "")) == day_iso]
