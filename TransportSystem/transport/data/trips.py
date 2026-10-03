# -*- coding: utf-8 -*-
"""الرحلات اليومية والخدمات والمصروفات اليومية."""

import calendar, json
from datetime import date
from .schema import SERVICE_TYPES, TRIP_CATEGORIES, _normalized_driver_name, safe_float

# ------------------------------------------------------------------
# الرحلات والتوصيل
# ------------------------------------------------------------------
def load_trips():
    from .core import _load_rows
    return _load_rows("trips", "id")

def save_trip(data, editing_id=None):
    from .core import _next_id, _save_row
    rows = load_trips()
    if editing_id is None:
        data["id"] = str(_next_id(rows))
    else:
        data["id"] = str(editing_id)
    data.setdefault("trip_category", TRIP_CATEGORIES[0])
    data.setdefault("invoiced", "لا")
    data.setdefault("invoice_no", "")
    _save_row("trips", "id", data, editing_id)

def delete_trip(row_id):
    from .core import _delete_row
    _delete_row("trips", "id", row_id)

def trips_for_date(day_iso):
    """يرجع كل رحلات اليوم المحدد (YYYY-MM-DD) - تُستخدم في شاشة الرحلات اليومية."""
    return [t for t in load_trips() if str(t.get("date", "")) == day_iso]

def trips_by_category(category):
    return [t for t in load_trips() if t.get("trip_category") == category]

def mark_trip_invoiced(row_id, invoice_no):
    from .core import _save_row
    rows = load_trips()
    for r in rows:
        if str(r["id"]) == str(row_id):
            r["invoiced"] = "نعم"
            r["invoice_no"] = invoice_no
            _save_row("trips", "id", r, row_id)
            return

# ------------------------------------------------------------------
# الخدمات الإضافية (عمال / رافعة / كرين)
# ------------------------------------------------------------------
def load_services():
    from .core import _load_rows
    return _load_rows("services", "id")

def save_service(data, editing_id=None):
    from .core import _next_id, _save_row
    rows = load_services()
    if editing_id is not None:
        previous = next((r for r in rows if str(r.get("id")) == str(editing_id)), None)
        if previous and "trip_ids" not in data:
            data["trip_ids"] = previous.get("trip_ids", "")
        if previous and "record_type" not in data:
            data["record_type"] = previous.get("record_type", "catalog")
    if editing_id is None:
        data["id"] = str(_next_id(rows))
    else:
        data["id"] = str(editing_id)
    if not str(data.get("service_type", "")).strip():
        data["service_type"] = SERVICE_TYPES[0]
    if not str(data.get("unit", "")).strip():
        data["unit"] = "\u0633\u0627\u0639\u0629"
    data.setdefault("quantity", "1")
    qty = safe_float(data.get("quantity"))
    price = safe_float(data.get("unit_price"))
    data["total"] = round(qty * price, 3)
    data.setdefault("invoiced", "لا")
    data.setdefault("invoice_no", "")
    data.setdefault("record_type", "catalog" if not data.get("date") and not data.get("customer") else "usage")
    _save_row("services", "id", data, editing_id)

def assign_service_to_trips(service_id, trip_ids):
    from .core import _save_row
    """Link an existing additional service to one or more trips."""
    rows = load_services()
    service = next((r for r in rows if str(r.get("id")) == str(service_id)), None)
    if not service:
        raise ValueError("الخدمة المحددة غير موجودة.")
    current = {part.strip() for part in str(service.get("trip_ids", "")).split(",") if part.strip()}
    current.update(str(tid).strip() for tid in trip_ids if str(tid).strip())
    service["trip_ids"] = ",".join(sorted(current, key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value)))
    _save_row("services", "id", service, service_id)

def delete_service(row_id):
    from .core import _delete_row
    from .finance import build_invoice_form_items, load_invoices, save_invoice
    """Delete a service and keep a linked invoice total in sync."""
    service = next((row for row in load_services()
                    if str(row.get("id")) == str(row_id)), None)
    invoice_no = str(service.get("invoice_no", "")).strip() if service else ""
    _delete_row("services", "id", row_id)
    if not invoice_no:
        return
    invoice = next((row for row in load_invoices()
                    if str(row.get("invoice_no")) == invoice_no), None)
    if not invoice:
        return
    trip_ids = [row.get("id") for row in load_trips()
                if str(row.get("invoice_no", "")) == invoice_no]
    service_ids = [row.get("id") for row in load_services()
                   if str(row.get("invoice_no", "")) == invoice_no]
    items = build_invoice_form_items(trip_ids, service_ids)
    invoice["items_json"] = json.dumps(items, ensure_ascii=False)
    invoice["total"] = round(sum(safe_float(item.get("amount")) for item in items), 3)
    save_invoice(invoice, editing_invno=invoice_no)

def mark_service_invoiced(row_id, invoice_no):
    from .core import _save_row
    rows = load_services()
    for r in rows:
        if str(r["id"]) == str(row_id):
            r["invoiced"] = "نعم"
            r["invoice_no"] = invoice_no
            _save_row("services", "id", r, row_id)
            return

# ------------------------------------------------------------------
# المصاريف اليومية والسلف
# ------------------------------------------------------------------
def load_daily_expenses():
    from .core import _load_rows
    return _load_rows("daily_expenses", "id")

def save_daily_expense(data, editing_id=None):
    from .core import _next_id, _save_row
    rows = load_daily_expenses()
    data = data.copy()
    if editing_id is None:
        data["id"] = str(_next_id(rows))
    else:
        data["id"] = str(editing_id)
    amount = safe_float(data.get("amount"))
    advance = safe_float(data.get("driver_advance"))
    if amount <= 0 and advance <= 0:
        raise ValueError("أدخل مبلغ مصروف أو سلفة للسائق أكبر من صفر.")
    data["amount"] = round(amount, 3)
    data["driver_advance"] = round(advance, 3)
    _save_row("daily_expenses", "id", data, editing_id)

def delete_daily_expense(row_id):
    from .core import _delete_row
    _delete_row("daily_expenses", "id", row_id)

def daily_expense_owner(expense):
    """يعيد جهة السجل، مع تصنيف السجلات القديمة التي لا تحتوي الحقل الجديد."""
    owner = str(expense.get("expense_owner", "")).strip()
    if owner:
        return owner
    if (safe_float(expense.get("driver_advance")) > 0
            or str(expense.get("category", "")) in {"مخالفة سائق", "سلفة يومية للسائق"}):
        return "سائق"
    return "سيارة"

def daily_expense_driver_type(expense):
    from .entities import driver_type_of
    """نوع سائق المصروف، ويشتقّه من سجل السائق إن كان الحقل المحفوظ فارغًا.

    المصاريف المسجّلة قبل إضافة حقل «نوع السائق» تحتفظ بقيمة فارغة، فلو
    صُفّينا عليها بالحقل المحفوظ وحده لاختفت كلها من الفلتر. نستند إلى سجل
    السائق في هذه الحالة، فيطابق فلتر النوع جدول الشاشة والطباعة معاً.
    """
    stored = str(expense.get("driver_type", "")).strip()
    if stored:
        return stored
    return driver_type_of(expense.get("driver", ""))

def driver_advances_for_month(driver, month):
    return round(sum(
        safe_float(expense.get("driver_advance"))
        # دعم السلف التي سُجلت قبل إضافة الحقل المنفصل.
        + (safe_float(expense.get("amount")) if str(expense.get("category", "")) == "سلفة يومية للسائق" else 0.0)
        for expense in load_daily_expenses()
        if str(expense.get("driver", "")) == str(driver)
        and str(expense.get("date", "")).startswith(month)
    ), 3)

def friday_work_bonus_for_driver_month(driver, month, base_salary):
    """يضيف راتب يوم واحد لكل Friday عمله السائق في الشهر إذا كان راتبه شهريًا."""
    if not driver or not month or base_salary <= 0:
        return 0.0
    try:
        year, month_no = map(int, month.split("-"))
    except Exception:
        return 0.0
    days_in_month = calendar.monthrange(year, month_no)[1]
    worked_fridays = 0
    # نُعدّ أيام عمل الجمعة على الرحلات بعد إسقاط المكرّر، وإلا احتُسب اليوم
    # الواحد مرتين لمن سجّل رحلتين له.
    friday_dates = set()
    for trip in deduplicate_trips([
            t for t in load_trips()
            if str(t.get("date", "")).startswith(month)
            and _normalized_driver_name(t.get("driver")) == _normalized_driver_name(driver)])[0]:
        if str(trip.get("date", "")).strip():
            friday_dates.add(str(trip.get("date", "")).strip())
    for day in range(1, days_in_month + 1):
        try:
            d = date(year, month_no, day)
        except ValueError:
            continue
        if d.weekday() != 4:
            continue
        if d.isoformat() in friday_dates:
            worked_fridays += 1
    daily_rate = base_salary / 30.0
    return round(worked_fridays * daily_rate, 3)

def trip_commission_for_driver_month(driver, month):
    from .entities import load_drivers
    """يحسب العمولة حسب الرحلات عند التعامل مع السائق على أساس رحلة/رحلة."""
    if not driver or not month:
        return 0.0
    driver_rows = [d for d in load_drivers() if str(d.get("name", "")) == str(driver)]
    if not driver_rows:
        return 0.0
    rate = safe_float(driver_rows[0].get("commission_per_trip"))
    trip_count = 0
    for t in load_trips():
        if str(t.get("driver", "")) != str(driver):
            continue
        if str(t.get("date", "")).startswith(month):
            trip_count += 1
    return round(trip_count * rate, 3)

def commission_total_for_driver_month(driver, month):
    from .entities import load_drivers
    """مجموع عمولات الرحلات للسائق خلال شهر معيّن (YYYY-MM).

    كانت تقرأ حقل «عمولة السائق» المدوّن داخل كل رحلة، وهو حقل لا يُملأ في
    الإدخال اليومي، فكانت نتيجة كل سائق صفراً دائماً ويعطي راتب «شهري» بلا
    عمولة. المصدر الصحيح لعمولة السائق هو «عمولة كل رحلة» من سجل السائقين
    مضروباً في عدد رحلاته، مع احترام العمولة اليدوية إن كانت مدوّنة على الرحلة.
    """
    if not driver or not month:
        return 0.0
    trips = [t for t in load_trips()
             if _normalized_driver_name(t.get("driver")) == _normalized_driver_name(driver)
             and str(t.get("date", "")).startswith(month)]
    # الرحلات المكرّرة كانت تُحسب عمولتها مرتين.
    trips, _duplicates = deduplicate_trips(trips)
    if not trips:
        return 0.0
    # العمولة اليدوية المسجّلة على الرحلة لها الأولوية، والباقي يُحسب بالسعر
    # الثابت لكل رحلة من سجل السائق حتى لا يبقى الراتب بلا عمولة.
    manual = sum(safe_float(t.get("driver_commission")) for t in trips)
    rate = 0.0
    for row in load_drivers():
        if _normalized_driver_name(row.get("name")) == _normalized_driver_name(driver):
            rate = safe_float(row.get("commission_per_trip"))
            break
    per_trip = round(len(trips) * rate, 3)
    return round(max(manual, per_trip), 3)

# ------------------------------------------------------------------
# منع ازدواج احتساب الرحلات والمصاريف في راتب السائق
# ------------------------------------------------------------------
def trip_identity_key(trip):
    """معرّف ثابت للرحلة يسمح بالتعرّف عليها رغم اختلاف طريقة إدخالها.

    كود الرحلة (رقم الضرب) هو الهوية الرسمية، فإن وُجد فهو المعتمد. وإن لم
    يوجد نركّب بديلاً من التاريخ والسيارة والسائق والشركة والعقدة، فتبقى
    الرحلة نفسها واحدة مهما اختلف ترتيب إدخال حقولها أو تغيّر رقمها الداخلي.
    """
    code = str(trip.get("declaration_trip_no", "")).strip()
    if code:
        return f"code:{code}"
    parts = [
        str(trip.get("date", "")).strip(),
        str(trip.get("car_no", "")).strip(),
        _normalized_driver_name(trip.get("driver")),
        str(trip.get("company", "")).strip(),
        str(trip.get("customer", "")).strip(),
        str(trip.get("declaration_no", "")).strip(),
        str(trip.get("container_size", "")).strip(),
    ]
    return "mix:" + "|".join(parts)

def deduplicate_trips(trips):
    """يرجع الرحلات بعد إسقاط المكرّر منها، مع إبقاء أول نسخة والأصغر مبلغاً.

    كانت الرحلة المسجّلة مرتين تدخل في الإيراد والأجرة مرتين فيُضخّم الراتب.
    نُبقي السجل الأول، فإذا اختلف مبلغ السجلات المكرّرة نأخذ الأصغر تحسّباً
    لأن الأكبر هو نتيجة خطأ في التسجيل، ونُبلّغ عن المكرر ليصحّحه المستخدم.
    """
    unique, seen = [], {}
    duplicates = 0
    for trip in trips:
        key = trip_identity_key(trip)
        if key in seen:
            first = seen[key]
            if (safe_float(trip.get("driver_wage")) > 0
                    and safe_float(trip.get("driver_wage")) < safe_float(first.get("driver_wage"))):
                first.update(trip)
            duplicates += 1
            continue
        seen[key] = trip
        unique.append(trip)
    unique.sort(key=lambda t: (str(t.get("date", "")), str(t.get("id", ""))))
    return unique, duplicates

def deduplicate_expense_records(records):
    """نفس المنطق للمصاريف: بند واحد مكرّر لا يُحتسب مرتين.

    البند تحدّده هويته من تاريخه وسيارته واسمه. نُبقي أول نسخة، ونجمع كل
    المبالغ المتطابقة لنفس الهوية في سجل واحد حتى لا يضيع أي مبلغ.
    """
    unique, seen = [], {}
    for record in records:
        key = (str(record.get("date", "")).strip(),
               str(record.get("car_no", "")).strip(),
               str(record.get("category", "")).strip())
        if key in seen:
            seen[key]["amount"] = round(
                seen[key]["amount"] + safe_float(record.get("amount")), 3)
            continue
        record = dict(record)
        record["amount"] = safe_float(record.get("amount"))
        seen[key] = record
        unique.append(record)
    return unique
