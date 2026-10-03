# -*- coding: utf-8 -*-
"""
core.data.repos.orders — الطلبات، المناسبات، عروض الأسعار، وجدولة التوصيل.
"""

from core.data import storage
from core.data.validation import is_iso_date
from core.money import mul, to_float


def load_institutional_orders():
    return storage.load_rows("institutional_orders", "id")


def save_institutional_order(data, editing_id=None):
    if not is_iso_date(data.get("date")):
        raise ValueError("تاريخ التسليم يجب أن يكون بصيغة YYYY-MM-DD.")
    rows = load_institutional_orders()
    if editing_id is None:
        data["id"] = str(storage.next_id(rows))
    else:
        data["id"] = str(editing_id)
    qty = data.get("quantity")
    price = data.get("unit_price")
    data["total"] = to_float(mul(qty, price))
    if not str(data.get("invoiced", "")).strip():
        data["invoiced"] = "لا"
    data.setdefault("invoice_no", "")
    storage.save_row("institutional_orders", "id", data, editing_id)


def delete_institutional_order(row_id):
    storage.delete_row("institutional_orders", "id", row_id)


def institutional_orders_for_date(day_iso):
    return [o for o in load_institutional_orders() if str(o.get("date", "")) == day_iso]


def mark_institutional_order_invoiced(row_id, invoice_no):
    rows = load_institutional_orders()
    for r in rows:
        if str(r["id"]) == str(row_id):
            r["invoiced"] = "نعم"
            r["invoice_no"] = invoice_no
            storage.save_row("institutional_orders", "id", r, row_id)
            return


def load_events():
    return storage.load_rows("events", "id")


def save_event(data, editing_id=None):
    if not is_iso_date(data.get("event_date")):
        raise ValueError("تاريخ المناسبة يجب أن يكون بصيغة YYYY-MM-DD.")
    rows = load_events()
    if editing_id is None:
        data["id"] = str(storage.next_id(rows))
    else:
        data["id"] = str(editing_id)
    guests = data.get("guests_count")
    price = data.get("unit_price")
    data["total"] = to_float(mul(guests, price))
    if not str(data.get("invoiced", "")).strip():
        data["invoiced"] = "لا"
    data.setdefault("invoice_no", "")
    storage.save_row("events", "id", data, editing_id)


def delete_event(row_id):
    storage.delete_row("events", "id", row_id)


def upcoming_events(from_date_iso):
    return [e for e in load_events() if str(e.get("event_date", "")) >= from_date_iso]


def mark_event_invoiced(row_id, invoice_no):
    rows = load_events()
    for r in rows:
        if str(r["id"]) == str(row_id):
            r["invoiced"] = "نعم"
            r["invoice_no"] = invoice_no
            storage.save_row("events", "id", r, row_id)
            return


def load_quotations():
    return storage.load_rows("quotations", "id")


def save_quotation(data, editing_id=None):
    if not is_iso_date(data.get("date")):
        raise ValueError("تاريخ العرض يجب أن يكون بصيغة YYYY-MM-DD.")
    if not str(data.get("customer", "")).strip():
        raise ValueError("الرجاء اختيار العميل.")
    proposed = str(data.get("event_date", "")).strip()
    if proposed and not is_iso_date(proposed):
        raise ValueError("تاريخ المناسبة المقترح يجب أن يكون بصيغة YYYY-MM-DD.")
    rows = load_quotations()
    data["id"] = str(editing_id if editing_id is not None else storage.next_id(rows))
    data["total"] = to_float(mul(data.get("guests_count"), data.get("unit_price")))
    if not str(data.get("status", "")).strip():
        data["status"] = "معلق"
    data.setdefault("converted_id", "")
    storage.save_row("quotations", "id", data, editing_id)


def delete_quotation(row_id):
    storage.delete_row("quotations", "id", row_id)


def convert_quotation_to_event(quotation_id):
    """
    يحوّل عرض سعر إلى مناسبة فعلية في جدول المناسبات، ويوسم العرض بأنه
    مقبول ويربطه برقم المناسبة. يرفض التحويل مرتين لنفس العرض.
    """
    q = next((r for r in load_quotations() if str(r.get("id")) == str(quotation_id)), None)
    if not q:
        raise ValueError("لم يتم العثور على عرض السعر رقم %s." % quotation_id)
    if str(q.get("converted_id", "")).strip():
        raise ValueError("تم تحويل هذا العرض مسبقاً إلى مناسبة رقم %s." % q["converted_id"])
    if not is_iso_date(q.get("event_date")):
        raise ValueError("لا يمكن التحويل قبل تحديد تاريخ المناسبة المقترح في العرض.")
    event = {
        "event_date": q.get("event_date"),
        "customer": q.get("customer"),
        "event_type": q.get("event_type") or "أخرى",
        "guests_count": q.get("guests_count"),
        "menu_description": q.get("menu_description"),
        "unit_price": q.get("unit_price"),
        "location": "",
        "delivery_time": "",
        "deposit": "",
        "notes": "محوّل من عرض سعر رقم %s" % q.get("id", ""),
    }
    save_event(event)                     # يُضيف رقم المناسبة تلقائياً
    q["status"] = "مقبول"
    q["converted_id"] = str(event["id"])
    storage.save_row("quotations", "id", q, q.get("id"))
    storage.log_action("تحويل عرض سعر", "quotations", q.get("id"),
               "إلى مناسبة رقم %s" % event["id"])
    return event


def deliveries_for_date(day_iso):
    """
    كل التسليمات المطلوبة في يوم محدد (طلبات المؤسسات + المناسبات) مع بيانات
    إسناد السائق والسيارة وحالة التسليم — لشاشة جدولة التوصيل.
    """
    day_iso = str(day_iso or "").strip()
    result = []
    for o in load_institutional_orders():
        if str(o.get("date", "")) != day_iso:
            continue
        result.append({
            "kind": "institutional",
            "kind_label": "طلب مؤسسة",
            "id": o.get("id"),
            "customer": o.get("customer"),
            "details": "وجبات %s" % o.get("meal_type", ""),
            "qty": "%s وجبة" % o.get("quantity", ""),
            "time": o.get("delivery_time", ""),
            "location": o.get("delivery_location", ""),
            "driver": o.get("driver", ""),
            "vehicle": o.get("vehicle", ""),
            "delivered": o.get("delivered", ""),
        })
    for e in load_events():
        if str(e.get("event_date", "")) != day_iso:
            continue
        result.append({
            "kind": "event",
            "kind_label": "مناسبة",
            "id": e.get("id"),
            "customer": e.get("customer"),
            "details": e.get("event_type", ""),
            "qty": "%s فرد" % e.get("guests_count", ""),
            "time": e.get("delivery_time", ""),
            "location": e.get("location", ""),
            "driver": e.get("driver", ""),
            "vehicle": e.get("vehicle", ""),
            "delivered": e.get("delivered", ""),
        })
    return result


def save_delivery_assignment(kind, row_id, driver="", vehicle="", delivered=None):
    """
    يحدّث إسناد السائق والسيارة وحالة التسليم على الطلب أو المناسبة.
    kind: "institutional" لطلب مؤسسة أو "event" لمناسبة.
    """
    driver = str(driver or "").strip()
    vehicle = str(vehicle or "").strip()
    if kind == "institutional":
        row = next((r for r in load_institutional_orders()
                    if str(r.get("id")) == str(row_id)), None)
        if row is None:
            raise ValueError("الطلب رقم %s غير موجود." % row_id)
        row["driver"], row["vehicle"] = driver, vehicle
        if delivered is not None:
            row["delivered"] = "نعم" if delivered else "لا"
        save_institutional_order(row, editing_id=row.get("id"))
    elif kind == "event":
        row = next((r for r in load_events()
                    if str(r.get("id")) == str(row_id)), None)
        if row is None:
            raise ValueError("المناسبة رقم %s غير موجودة." % row_id)
        row["driver"], row["vehicle"] = driver, vehicle
        if delivered is not None:
            row["delivered"] = "نعم" if delivered else "لا"
        save_event(row, editing_id=row.get("id"))
    else:
        raise ValueError("نوع تسليم غير معروف: %s" % kind)
    storage.log_action("إسناد توصيل",
               "institutional_orders" if kind == "institutional" else "events",
               row_id, "السائق: %s — السيارة: %s" % (driver or "—", vehicle or "—"))
