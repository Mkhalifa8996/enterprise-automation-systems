# -*- coding: utf-8 -*-
"""كل الحسابات والتقارير المالية وتوزيع الأرباح وحساب الرواتب."""

import json
from datetime import date, datetime
from .schema import FIXED_PLUS_REVENUE_DRIVERS, REVENUE_AFTER_DIESEL_DRIVERS, REVENUE_SALARY_TYPE, SALARY_METHOD_DESCRIPTIONS, SALARY_METHOD_LABELS, SALARY_REVENUE_FRACTIONS, _normalized_driver_name, partner_share_percentage, safe_float

def driver_salary_for_car_period(car_no, date_from="", date_to=""):
    """راتب السائق المحقق للسيارة خلال فترة — يُستخدم لحساب نصيب الشركاء."""
    car_no = str(car_no or "").strip()
    total = 0.0
    for row in load_salaries():
        if car_no and str(row.get("car_no", "")).strip() != car_no:
            continue
        stamp = str(row.get("date") or (str(row.get("month", "")) + "-01"))
        if date_from and stamp < date_from:
            continue
        if date_to and stamp > date_to:
            continue
        total += safe_float(row.get("net_salary"))
    return round(total, 3)

def partner_share_details(partner, date_from="", date_to=""):
    from .entities import load_vehicle_partners
    """صافي إيراد كل سيارة يشارك فيها الشريك ونصيبه خلال فترة محددة.

    نصيب الشريك = نسبة الشريك × (إيراد الرحلات + العطل − مصاريف السيارة − راتب السائق).
    """
    partner = str(partner or "").strip()
    shares = []
    total_share = 0.0
    for row in load_vehicle_partners():
        if str(row.get("partner", "")).strip() != partner:
            continue
        if not _periods_overlap(date_from, date_to, row.get("start_date"), row.get("end_date")):
            continue
        car_no = str(row.get("car_no", "")).strip()
        percentage = partner_share_percentage(row.get("ownership_pct"))
        result = vehicle_profit_distribution(
            car_no, date_from, date_to,
            driver_salary_for_car_period(car_no, date_from, date_to))
        amount = next((item["amount"] for item in result["partners"]
                       if str(item.get("partner", "")).strip() == partner), 0.0)
        shares.append({
            "car_no": car_no,
            "ownership_pct": percentage,
            "revenue": result["revenue"],
            "vehicle_expenses": result["vehicle_expenses"],
            "driver_salary": result["driver_salary"],
            "distributable": result["distributable"],
            "amount": round(amount, 3),
        })
        total_share += amount
    return {"partner": partner, "shares": shares, "total": round(total_share, 3)}

def partner_statement(partner, date_from="", date_to=""):
    from .finance import is_voided, load_partner_payments
    """كشف حساب الشريك: الدفعات المسجلة + نصيبه عن الفترة كدفعة مستحقة."""
    partner = str(partner or "").strip()
    share_details = partner_share_details(partner, date_from, date_to)
    movements = []
    for row in load_partner_payments():
        if str(row.get("partner", "")).strip() != partner:
            continue
        stamp = str(row.get("date", ""))
        if date_from and stamp < date_from:
            continue
        if date_to and stamp > date_to:
            continue
        amount = safe_float(row.get("amount"))
        is_debit = str(row.get("payment_type", "")).strip() == "مدين"
        movements.append({
            "date": stamp,
            "kind": "payment",
            "label": "دفعة " + str(row.get("payment_type", "")).strip(),
            "car_no": str(row.get("car_no", "")),
            # «مدين» دفعة للشركة تُنقص رصيده، و«دائن» استرداد يزيد رصيده.
            "debit": amount if is_debit else 0.0,
            "credit": 0.0 if is_debit else amount,
            "notes": str(row.get("notes", "")),
            "voided": is_voided(row),
            "void_reason": str(row.get("void_reason", "")),
        })
    if share_details["total"]:
        # نصيبه يُقيَّد كدفعة مستحقة لصالح حسابه.
        movements.append({
            "date": date_to or date.today().isoformat(),
            "kind": "share",
            "label": "نصيب مستحق من صافي إيراد السيارات",
            "car_no": "، ".join(share["car_no"] for share in share_details["shares"]),
            "debit": 0.0,
            "credit": share_details["total"],
            "notes": "",
        })
    movements.sort(key=lambda item: (item["date"], 0 if item["kind"] == "share" else 1))
    for item in movements:
        # كل حركة تحمل حالة الإشطب صراحةً لتفادي KeyError عند الفرز والطباعة.
        item.setdefault("voided", False)
        item.setdefault("void_reason", "")
    balance = 0.0
    for item in movements:
        if not item["voided"]:
            balance += item["debit"] - item["credit"]
        item["balance"] = round(balance, 3)
    return {"partner": partner, "movements": movements,
            "shares": share_details["shares"],
            "total_share": share_details["total"],
            "balance": round(balance, 3)}

def driver_wage_for_trip(trip):
    """أجرة السائق المستحقة عن رحلة واحدة.

    الحقل «أجرة السائق» اختياري، فلو تُرك فارغاً نرجع لمبلغ الرحلة نفسه حتى لا
    يظهر كشف حساب السائق الخارجي بأجرة صفرية لكل الرحلات.
    """
    wage = safe_float(trip.get("driver_wage"))
    return wage if wage else safe_float(trip.get("fee"))

def driver_wages_total(trips):
    """إجمالي أجرة السائق عن مجموعة رحلات."""
    return round(sum(driver_wage_for_trip(trip) for trip in trips), 3)

def driver_statement(driver, date_from="", date_to="", driver_type=""):
    from .entities import driver_type_of
    from .finance import is_voided, load_driver_payments
    from .trips import daily_expense_owner, load_daily_expenses, load_trips
    """كشف حساب السائق: الرحلات والمصروفات والسلف والدفعات خلال فترة.

    يشمل الكشف السائقين الداخليين والخارجيين على السواء، ويعيد تفصيل كل بند
    (الرحلات، المصروفات، السلف، الدفعات) إضافةً إلى الرصيد النهائي، فتصلح
    لكشف حساب أي سائق خارجي يُستعян من جهة أخرى لتوصيل بعض الرحلات.
    """
    driver = str(driver or "").strip()
    if not driver_type:
        driver_type = driver_type_of(driver)

    def in_range(value):
        value = str(value or "")
        return (not date_from or value >= date_from) and (not date_to or value <= date_to)

    movements = []
    trips = [row for row in load_trips()
             if _normalized_driver_name(row.get("driver")) == _normalized_driver_name(driver)
             and in_range(row.get("date"))]
    for row in trips:
        movements.append({
            "date": str(row.get("date", "")), "kind": "trip",
            "label": "رحلة " + (str(row.get("declaration_trip_no", "")).strip() or str(row.get("id"))),
            "car_no": str(row.get("car_no", "")),
            "debit": 0.0,
            "credit": safe_float(row.get("fee")) + safe_float(row.get("holiday_price")),
            "notes": str(row.get("customer", "")),
        })
        # مصاريف السيارة تكلفة على السيارة لا على السائق، فلا تدخل في حسابه.
        # مصروف السائق فقط هو ما يُحمَّل على حسابه مع السلف.
        driver_trip_expense = safe_float(row.get("driver_expense"))
        if driver_trip_expense:
            movements.append({
                "date": str(row.get("date", "")), "kind": "expense",
                "label": "مصروف سائق بالرحلة", "car_no": str(row.get("car_no", "")),
                "debit": driver_trip_expense, "credit": 0.0, "notes": "",
            })
    for row in load_daily_expenses():
        if not in_range(row.get("date")) or str(row.get("driver", "")).strip() != driver:
            continue
        if daily_expense_owner(row) != "سائق":
            continue
        amount = safe_float(row.get("amount"))
        if amount:
            movements.append({
                "date": str(row.get("date", "")), "kind": "expense",
                "label": str(row.get("category", "")) or "مصروف سائق",
                "car_no": str(row.get("car_no", "")), "debit": amount, "credit": 0.0,
                "notes": str(row.get("description", "")),
            })
        advance = safe_float(row.get("driver_advance"))
        if advance:
            movements.append({
                "date": str(row.get("date", "")), "kind": "advance", "label": "سلفة للسائق",
                "car_no": str(row.get("car_no", "")), "debit": advance, "credit": 0.0,
                "notes": str(row.get("description", "")),
            })
    for row in load_driver_payments():
        if str(row.get("driver", "")).strip() != driver or not in_range(row.get("date")):
            continue
        amount = safe_float(row.get("amount"))
        is_debit = str(row.get("payment_type", "")).strip() == "مدين"
        movements.append({
            "date": str(row.get("date", "")), "kind": "payment",
            "label": "دفعة " + str(row.get("payment_type", "")).strip(),
            "car_no": str(row.get("car_no", "")),
            "debit": amount if is_debit else 0.0,
            "credit": 0.0 if is_debit else amount,
            "notes": str(row.get("notes", "")),
            "voided": is_voided(row),
            "void_reason": str(row.get("void_reason", "")),
        })
    movements.sort(key=lambda item: (item["date"], item["kind"]))
    # كل حركة تحمل حالة الإشطب صراحةً لتفادي KeyError عند الفرز والطباعة.
    for item in movements:
        item.setdefault("voided", False)
        item.setdefault("void_reason", "")
    balance = 0.0
    for item in movements:
        if not item["voided"]:
            balance += item["credit"] - item["debit"]
        item["balance"] = round(balance, 3)

    def _sum(kind, field):
        return round(sum(safe_float(item.get(field)) for item in movements
                         if item["kind"] == kind and not item["voided"]), 3)

    return {"driver": driver, "driver_type": driver_type, "date_from": date_from,
            "date_to": date_to, "trips": trips, "movements": movements,
            "trips_count": len(trips),
            "trips_revenue": _sum("trip", "credit"),
            "driver_wages": driver_wages_total(trips),
            "driver_expenses": _sum("expense", "debit"),
            "advances": _sum("advance", "debit"),
            "payments_total": _sum("payment", "debit"),
            "receipts_total": _sum("payment", "credit"),
            "voided_count": sum(1 for item in movements if item["voided"]),
            "balance": round(balance, 3)}

def next_statement_number(prefix):
    from .core import _load_metadata, _mark_local_change, _save_metadata
    """رقم مستند تسلسلي لكشوف الحساب يستمر عبر الجلسات."""
    token = f"{prefix}-{date.today().strftime('%Y%m')}-"
    counters = _load_metadata("statement_counters")
    highest = 0
    for key, value in counters.items():
        if str(key).startswith(token):
            try:
                highest = max(highest, int(str(value)))
            except (TypeError, ValueError):
                continue
    number = highest + 1
    counters[token] = str(number)
    _save_metadata("statement_counters", counters)
    _mark_local_change()
    return f"{token}{number:04d}"

def partner_profit_report(date_from="", date_to=""):
    from .entities import partner_share_matrix
    """تقرير أرباح الشركاء: نصيب كل شريك من كل سيارة خلال فترة."""
    rows = []
    grand_total = 0.0
    for matrix_row in partner_share_matrix():
        car_no = matrix_row["car_no"]
        result = vehicle_profit_distribution(
            car_no, date_from, date_to,
            driver_salary_for_car_period(car_no, date_from, date_to))
        for share in matrix_row["partners"]:
            amount = next((item["amount"] for item in result["partners"]
                           if str(item.get("partner", "")).strip() == share["partner"]), 0.0)
            rows.append({
                "partner": share["partner"],
                "car_no": car_no,
                "ownership_pct": share["ownership_pct"],
                "revenue": result["revenue"],
                "vehicle_expenses": result["vehicle_expenses"],
                "driver_salary": result["driver_salary"],
                "distributable": result["distributable"],
                "amount": round(amount, 3),
            })
            grand_total += amount
    by_partner = {}
    for row in rows:
        entry = by_partner.setdefault(row["partner"], {"partner": row["partner"],
                                                       "amount": 0.0, "cars": 0})
        entry["amount"] = round(entry["amount"] + row["amount"], 3)
        entry["cars"] += 1
    return {"rows": rows, "by_partner": sorted(by_partner.values(),
                                               key=lambda item: -item["amount"]),
            "total": round(grand_total, 3)}

def partner_payments_report(date_from="", date_to=""):
    from .finance import is_voided, load_partner_payments
    """تقرير دفعات الشركاء مع تمييز المشطوبة."""
    def in_range(value):
        value = str(value or "")
        return (not date_from or value >= date_from) and (not date_to or value <= date_to)

    rows = [row for row in load_partner_payments() if in_range(row.get("date"))]
    rows.sort(key=lambda row: str(row.get("date", "")))
    total = sum(safe_float(row.get("amount")) for row in rows if not is_voided(row))
    by_partner = {}
    for row in rows:
        if is_voided(row):
            continue
        entry = by_partner.setdefault(str(row.get("partner", "")).strip(),
                                      {"partner": str(row.get("partner", "")).strip(),
                                       "total": 0.0, "count": 0})
        entry["total"] = round(entry["total"] + safe_float(row.get("amount")), 3)
        entry["count"] += 1
    return {"rows": rows, "total": round(total, 3),
            "by_partner": sorted(by_partner.values(), key=lambda item: -item["total"]),
            "voided_count": sum(1 for row in rows if is_voided(row))}

def driver_payments_report(date_from="", date_to=""):
    from .finance import is_voided, load_driver_payments
    """تقرير دفعات السائقين مع تمييز المشطوبة."""
    def in_range(value):
        value = str(value or "")
        return (not date_from or value >= date_from) and (not date_to or value <= date_to)

    rows = [row for row in load_driver_payments() if in_range(row.get("date"))]
    rows.sort(key=lambda row: str(row.get("date", "")))
    total = sum(safe_float(row.get("amount")) for row in rows if not is_voided(row))
    by_driver = {}
    for row in rows:
        name = str(row.get("driver", "")).strip()
        if is_voided(row):
            continue
        entry = by_driver.setdefault(name, {"driver": name, "total": 0.0, "count": 0,
                                            "driver_type": str(row.get("driver_type", ""))})
        entry["total"] = round(entry["total"] + safe_float(row.get("amount")), 3)
        entry["count"] += 1
    return {"rows": rows, "total": round(total, 3),
            "by_driver": sorted(by_driver.values(), key=lambda item: -item["total"]),
            "voided_count": sum(1 for row in rows if is_voided(row))}

def _periods_overlap(start_a, end_a, start_b, end_b):
    start_a = str(start_a or "0000-01-01")
    start_b = str(start_b or "0000-01-01")
    end_a = str(end_a or "9999-12-31")
    end_b = str(end_b or "9999-12-31")
    return max(start_a, start_b) <= min(end_a, end_b)

def vehicle_partner_distribution(car_no, date_from, date_to, distributable_amount):
    from .entities import load_vehicle_partners
    """Return partner shares for a vehicle and period after driver pay/expenses."""
    amount = max(0.0, safe_float(distributable_amount))
    rows = [
        row for row in load_vehicle_partners()
        if str(row.get("car_no", "")).strip() == str(car_no).strip()
        and _periods_overlap(date_from, date_to, row.get("start_date"), row.get("end_date"))
    ]
    if not rows:
        return []
    return [
        {
            "partner": str(row.get("partner", "")).strip(),
            "ownership_pct": partner_share_percentage(row.get("ownership_pct")),
            "amount": round(amount * partner_share_percentage(row.get("ownership_pct")) / 100.0, 3),
        }
        for row in rows
    ]

# ------------------------------------------------------------------
# الرواتب
# ------------------------------------------------------------------
def load_salaries():
    from .core import _load_rows
    return _load_rows("salaries", "id")

def revenue_salary_rule(driver):
    """Return the agreed revenue-sharing rule for a driver, if any."""
    name = _normalized_driver_name(driver)
    if name in FIXED_PLUS_REVENUE_DRIVERS:
        return "fixed_plus_revenue"
    if name in REVENUE_AFTER_DIESEL_DRIVERS:
        return "revenue_after_diesel"
    return ""

def vehicle_revenue_salary_details(driver, month, car_no=""):
    from .finance import load_maintenance
    from .trips import daily_expense_owner, deduplicate_trips, load_daily_expenses, load_trips
    """Calculate a driver's monthly car-revenue share from recorded data.

    Revenue is the sum of trip fees for the driver's assigned vehicle(s), while
    holiday revenue is kept separate.  The first group shares revenue after all
    vehicle expenses; the second group shares it after diesel expenses only.
    """
    rule = revenue_salary_rule(driver)
    if not month:
        return {"rule": rule, "base_salary": 0.0, "vehicle_revenue": 0.0,
                "holiday_revenue": 0.0, "vehicle_expenses": 0.0,
                "diesel_expenses": 0.0, "net_revenue": 0.0,
                "revenue_after_deductible": 0.0}

    driver_name = str(driver or "").strip()
    car_no = str(car_no or "").strip()
    # الرحلات تحفظ السائق الفعلي، لذلك لا نعتمد على سيارة ثابتة في سجل السائق.
    cars = {
        str(row.get("car_no", "")).strip() for row in load_trips()
        if str(row.get("date", "")).startswith(month)
        and _normalized_driver_name(row.get("driver")) == _normalized_driver_name(driver_name)
        and str(row.get("car_no", "")).strip()
    }
    if car_no:
        cars = {car_no}

    trips = [
        row for row in load_trips()
        if str(row.get("date", "")).startswith(month)
        and _normalized_driver_name(row.get("driver")) == _normalized_driver_name(driver_name)
        and ((cars and str(row.get("car_no", "")).strip() in cars)
             or (not cars and not str(row.get("car_no", "")).strip()))
    ]
    # إسقاط الرحلات المكرّرة: كانت تدخل الإيراد والمصاريف مرتين.
    trips, _duplicates = deduplicate_trips(trips)
    if not cars:
        cars = {str(row.get("car_no", "")).strip() for row in trips if str(row.get("car_no", "")).strip()}

    vehicle_revenue = sum(safe_float(row.get("fee")) for row in trips)
    holiday_revenue = sum(safe_float(row.get("holiday_price")) for row in trips)
    trip_expenses = sum(safe_float(row.get("car_expense_amount")) for row in trips)

    car_expenses = [row for row in load_daily_expenses()
                    if str(row.get("date", "")).startswith(month)
                    and str(row.get("car_no", "")).strip() in cars
                    and daily_expense_owner(row) == "سيارة"]
    daily_total = sum(safe_float(row.get("amount")) for row in car_expenses)
    diesel_daily = sum(safe_float(row.get("amount")) for row in car_expenses
                       if "ديزل" in str(row.get("category", "")))
    maintenance = [row for row in load_maintenance()
                   if str(row.get("date", "")).startswith(month)
                   and str(row.get("car_no", "")).strip() in cars]
    maintenance_total = sum(safe_float(row.get("cost")) for row in maintenance)
    diesel_maintenance = sum(safe_float(row.get("cost")) for row in maintenance
                             if "ديزل" in str(row.get("type", "")))
    diesel_trip = sum(safe_float(row.get("car_expense_amount")) for row in trips
                      if "ديزل" in str(row.get("car_expense_type", "")))

    vehicle_expenses = trip_expenses + daily_total + maintenance_total
    diesel_expenses = diesel_trip + diesel_daily + diesel_maintenance
    deductible = vehicle_expenses if rule == "fixed_plus_revenue" else diesel_expenses if rule == "revenue_after_diesel" else 0.0
    # صافي الإيراد بنفس تعريف «طريقة الحساب»: (إيراد الرحلات + العطل − مصاريف السيارة).
    # كان يُحسب هنا نصيب من النصف (/2) بينما بقية النظام يقسم الكسر المذكور في
    # الطريقة على الصافي، فنصير لنصف المبلغ بدل الربع. توحّدنا على صافي الإيراد.
    net_revenue = max(0.0, vehicle_revenue + holiday_revenue - vehicle_expenses)
    revenue_after_rule = max(0.0, vehicle_revenue - deductible)
    return {"rule": rule, "base_salary": 350.0 if rule == "fixed_plus_revenue" else 0.0,
            "vehicle_revenue": round(vehicle_revenue, 3),
            "holiday_revenue": round(holiday_revenue, 3),
            "vehicle_expenses": round(vehicle_expenses, 3),
            "diesel_expenses": round(diesel_expenses, 3),
            "net_revenue": round(net_revenue, 3),
            "revenue_after_deductible": round(revenue_after_rule, 3)}

def vehicle_financial_details(date_from=None, date_to=None, car_no="",
                              driver_type="", include_setup=True):
    from .entities import driver_type_of, load_vehicle_assignments, load_vehicles, vehicle_driver_for_date
    from .finance import load_maintenance, vehicle_setup_expenses_for_car
    from .trips import daily_expense_owner, deduplicate_trips, load_daily_expenses, load_trips
    """Return income and categorized vehicle/driver costs for each vehicle.

    This is intentionally based on operational records, not invoices, so the
    manager can determine driver pay before an invoice has been issued.

    `driver_type` يصفّي النتائج بنوع السائق («داخلي» أو «خارجي»)، و`include_setup`
    يضيف مصاريف تجهيز السيارة في حقول مستقلة لأنها رأس مال لا مصروف جارٍ.
    """
    def in_range(value):
        value = str(value or "")
        return (not date_from or value >= date_from) and (not date_to or value <= date_to)

    wanted_type = str(driver_type or "").strip()
    target = str(car_no or "").strip()
    vehicle_rows = load_vehicles()
    # Load each Excel sheet once; this summary may contain many cars.
    all_trips = load_trips()
    all_expenses = load_daily_expenses()
    all_maintenance = load_maintenance()
    cars = {str(row.get("car_no", "")).strip() for row in vehicle_rows if row.get("car_no")}
    cars.update(str(row.get("car_no", "")).strip() for row in all_trips if row.get("car_no"))
    cars.update(str(row.get("car_no", "")).strip() for row in all_expenses if row.get("car_no"))
    if target:
        cars = {target}
    assigned_drivers = {str(row.get("car_no", "")).strip(): str(row.get("driver", "")).strip()
                        for row in vehicle_rows}
    # جدول تكليفات السائقين هو المرجع الذي يربط كل سائق بسيارة، فيغلب على حقل السيارة.
    for assignment in load_vehicle_assignments():
        car = str(assignment.get("car_no", "")).strip()
        driver_name = str(assignment.get("driver", "")).strip()
        if not car or not driver_name:
            continue
        current = vehicle_driver_for_date(car, date_to or date.today().isoformat())
        assigned_drivers[car] = current or driver_name
    result = []
    for car in sorted(cars):
        raw_trips = [row for row in all_trips if str(row.get("car_no", "")).strip() == car
                     and in_range(row.get("date"))]
        # إسقاط الرحلات المكرّرة: كانت تدخل الإيراد والأجرة مرتين فيتضاعف
        # صافي السيارة بلا سبب ظاهر.
        trips, duplicates = deduplicate_trips(raw_trips)
        driver = assigned_drivers.get(car) or next(
            (str(row.get("driver", "")).strip() for row in trips if row.get("driver")), "")
        # نوع السائق: من جدول السائقين، ومن رحلات السيارة عند غياب سجل.
        kind = driver_type_of(driver) if driver else ""
        if not kind:
            kind = next((str(row.get("driver_type", "")).strip() for row in trips
                         if str(row.get("driver_type", "")).strip()), "")
        if wanted_type and kind != wanted_type:
            continue
        car_costs = {}
        driver_costs = {}
        revenue_records = []
        car_expense_records = []
        driver_expense_records = []

        def add(bucket, category, amount):
            amount = safe_float(amount)
            if amount:
                bucket[category or "أخرى"] = round(bucket.get(category or "أخرى", 0.0) + amount, 3)

        for row in trips:
            fee = safe_float(row.get("fee"))
            holiday = safe_float(row.get("holiday_price"))
            revenue_records.append({"date": str(row.get("date", "")),
                                    "reference": str(row.get("declaration_trip_no", "")),
                                    "customer": str(row.get("customer", "")),
                                    "revenue": fee, "holiday": holiday,
                                    "total": round(fee + holiday, 3)})
            add(car_costs, str(row.get("car_expense_type", "")).strip() or "مصاريف رحلة",
                row.get("car_expense_amount"))
            add(driver_costs, "مصروف سائق (رحلة)", row.get("driver_expense"))
            if safe_float(row.get("car_expense_amount")):
                car_expense_records.append({"date": str(row.get("date", "")), "category": str(row.get("car_expense_type", "")).strip() or "مصاريف رحلة", "source": "الرحلات", "amount": safe_float(row.get("car_expense_amount"))})
            if safe_float(row.get("driver_expense")):
                driver_expense_records.append({"date": str(row.get("date", "")), "category": "مصروف سائق (رحلة)", "source": "الرحلات", "amount": safe_float(row.get("driver_expense"))})
        for row in all_expenses:
            if not in_range(row.get("date")):
                continue
            category = str(row.get("category", "")).strip()
            owner = daily_expense_owner(row)
            belongs_to_car = str(row.get("car_no", "")).strip() == car
            belongs_to_driver = (driver and str(row.get("driver", "")).strip() == driver)
            if owner == "سيارة" and belongs_to_car:
                add(car_costs, category, row.get("amount"))
                if safe_float(row.get("amount")):
                    car_expense_records.append({"date": str(row.get("date", "")), "category": category or "أخرى", "source": "المصاريف اليومية", "amount": safe_float(row.get("amount"))})
            elif owner == "سائق" and belongs_to_driver:
                add(driver_costs, category, row.get("amount"))
                add(driver_costs, "سلفة للسائق", row.get("driver_advance"))
                if safe_float(row.get("amount")):
                    driver_expense_records.append({"date": str(row.get("date", "")), "category": category or "أخرى", "source": "مصاريف السائق", "amount": safe_float(row.get("amount"))})
                if safe_float(row.get("driver_advance")):
                    driver_expense_records.append({"date": str(row.get("date", "")), "category": "سلفة للسائق", "source": "مصاريف السائق", "amount": safe_float(row.get("driver_advance"))})
        for row in all_maintenance:
            if str(row.get("car_no", "")).strip() == car and in_range(row.get("date")):
                category = "صيانة - " + (str(row.get("type", "")).strip() or "أخرى")
                add(car_costs, category, row.get("cost"))
                if safe_float(row.get("cost")):
                    car_expense_records.append({"date": str(row.get("date", "")), "category": category, "source": "صيانة السيارات", "amount": safe_float(row.get("cost"))})

        revenue = sum(safe_float(row.get("fee")) for row in trips)
        holiday = sum(safe_float(row.get("holiday_price")) for row in trips)
        car_total = round(sum(car_costs.values()), 3)
        driver_total = round(sum(driver_costs.values()), 3)
        # راتب السائق من أجور الرحلات نفسها، وهو المبلغ الذي تدفعه الشركة عنه.
        driver_wages = driver_wages_total(trips)
        income = round(revenue + holiday, 3)
        # صافي السيارة بالتعريف المطلوب: الإيراد ناقص مصاريف السيارة وراتب السائق.
        operating = round(car_total + driver_wages, 3)
        net_revenue = round(income - operating, 3)
        setup = vehicle_setup_expenses_for_car(car) if include_setup else {"total": 0.0, "totals": {}}
        result.append({"car_no": car, "driver": driver, "driver_type": kind,
                       "trips_count": len(trips), "duplicates": duplicates,
                       "revenue": round(revenue, 3),
                       "holiday": round(holiday, 3), "income_total": income,
                       "car_expenses": car_total, "driver_expenses": driver_total,
                       "driver_wages": driver_wages,
                       "operating_expenses": operating,
                       "net_revenue": net_revenue,
                       "setup_total": setup["total"], "setup_items": setup["totals"],
                       "state": salary_balance_state(net_revenue),
                       # نُبقي `net_vehicle` كما هو لأن توزيع الأرباح يعتمد عليه،
                       # وهو صافي بعد خصم مصاريف السيارة فقط دون راتب السائق.
                       "net_vehicle": round(income - car_total, 3),
                       "car_cost_breakdown": car_costs, "driver_cost_breakdown": driver_costs,
                       "revenue_records": revenue_records, "car_expense_records": car_expense_records,
                       "driver_expense_records": driver_expense_records})
    result.sort(key=lambda r: (-r["trips_count"], r["car_no"]))
    return result

def vehicle_profit_distribution(car_no, date_from, date_to, driver_salary=0.0):
    """Calculate vehicle net profit and distribute it among its partners."""
    record = next(iter(vehicle_financial_details(date_from, date_to, car_no)), None)
    if not record:
        return {
            "car_no": car_no, "revenue": 0.0, "vehicle_expenses": 0.0,
            "driver_salary": round(safe_float(driver_salary), 3),
            "distributable": 0.0, "partners": [],
        }
    revenue = safe_float(record.get("income_total"))
    expenses = safe_float(record.get("car_expenses"))
    salary = safe_float(driver_salary)
    distributable = max(0.0, revenue - expenses - salary)
    return {
        "car_no": car_no,
        "revenue": round(revenue, 3),
        "vehicle_expenses": round(expenses, 3),
        "driver_salary": round(salary, 3),
        "distributable": round(distributable, 3),
        "partners": vehicle_partner_distribution(car_no, date_from, date_to, distributable),
    }

def save_profit_snapshots(snapshot_month, distributions):
    from .core import _connect, _ensure_database
    """Persist one monthly distribution result per vehicle for audit history."""
    month = str(snapshot_month or "").strip()
    if not month:
        raise ValueError("حدد شهر اللقطة قبل الحفظ.")
    _ensure_database()
    connection = _connect()
    try:
        now = datetime.now().isoformat(timespec="seconds")
        for distribution in distributions:
            car_no = str(distribution.get("car_no", "")).strip()
            if car_no:
                connection.execute(
                    "INSERT OR REPLACE INTO profit_snapshots "
                    "(snapshot_month, car_no, data_json, created_at) VALUES (?, ?, ?, ?)",
                    (month, car_no, json.dumps(distribution, ensure_ascii=False), now),
                )
        connection.commit()
    finally:
        connection.close()

def load_profit_snapshots(snapshot_month):
    from .core import _connect, _ensure_database
    _ensure_database()
    connection = _connect()
    try:
        return [
            json.loads(row[0]) for row in connection.execute(
                "SELECT data_json FROM profit_snapshots WHERE snapshot_month = ? ORDER BY car_no",
                (str(snapshot_month).strip(),),
            )
        ]
    finally:
        connection.close()

def _empty_revenue_row(car_no, model=""):
    return {"car_no": car_no, "model": model, "trips": [], "trip_revenue": 0.0,
            "holiday_revenue": 0.0, "driver_wages": 0.0, "car_expenses": 0.0,
            "expense_items": {}}

def counted_salary_periods(driver, exclude_id=None):
    """فترات راتب محفوظة لسائق، كقائمة (من، إلى) لكل سجل راتب.

    تُستعمل لاستبعاد ما سبق احتسابه: بنفس الفكرة التي يستبعد بها البرنامج
    الرحلة المكرّرة، لكن بين راتب محفوظ وراتب جديد لنفس السائق.
    """
    name = _normalized_driver_name(driver)
    periods = []
    for row in load_salaries():
        if _normalized_driver_name(row.get("driver")) != name:
            continue
        if exclude_id and str(row.get("id")) == str(exclude_id):
            continue
        start = str(row.get("period_from", "")).strip()
        end = str(row.get("period_to", "")).strip()
        if start or end:
            periods.append((start, end))
    return periods

def driver_carry_balance(driver, before_date, exclude_id=None):
    """الرصيد المرحّل من رواتب سابقة: ما تبقى للسائق أو عليه قبل تاريخ معيّن.

    عند دفع جزء من راتب الشهر يبقى الباقي للشهر التالي، وإذا طلع الراتب
    سالباً كان على السائق مبلغ زائد. نجمع الحالتين في رصيد واحد: موجب يعني
    مستحقاً له، وسالب يعني مديناً له، فيُطرح أو يُضاف إلى راتب الشهر الحالي.
    """
    name = _normalized_driver_name(driver)
    limit = str(before_date or "").strip()
    total = 0.0
    parts = []
    for row in load_salaries():
        if _normalized_driver_name(row.get("driver")) != name:
            continue
        if exclude_id and str(row.get("id")) == str(exclude_id):
            continue
        period_end = (str(row.get("period_to", "")).strip()
                      or (str(row.get("month", "")).strip() + "-28"))
        if not limit or not period_end or period_end >= limit:
            continue
        # الباقي المرحّل محفوظ في السجل عند الحفظ، ونحسبه عند غيابه.
        remaining = safe_float(row.get("carry_forward"))
        if not remaining:
            net = safe_float(row.get("net_salary"))
            settled = safe_float(row.get("settled_amount"))
            if not settled:
                settled = net if str(row.get("paid", "")).strip() == "نعم" else 0.0
            remaining = round(net - settled, 3)
        if remaining:
            total = round(total + remaining, 3)
            parts.append({"id": row.get("id"), "month": row.get("month"),
                          "net": safe_float(row.get("net_salary")),
                          "settled": safe_float(row.get("settled_amount")),
                          "remaining": remaining})
    return {"balance": total, "state": salary_balance_state(total), "items": parts}

def _in_counted_period(value, periods):
    """هل يقع هذا التاريخ داخل فترة راتب محفوظة سابقاً؟"""
    value = str(value or "").strip()
    if not value or not periods:
        return False
    for start, end in periods:
        if start and value < start:
            continue
        if end and value > end:
            continue
        return True
    return False

def driver_salary_period_details(driver, date_from=None, date_to=None, car_no="",
                                  exclude_counted=True, exclude_salary_id=None):
    from .entities import load_drivers
    from .finance import load_maintenance
    from .trips import daily_expense_owner, deduplicate_trips, load_daily_expenses, load_trips
    """Operational totals used by the interactive salary calculator.

    عند `exclude_counted` نستبعد ما سبق احتسابه في راتب محفوظ لنفس السائق
    ونفس الفترة، فلا تُحتسب الرحلة أو المصروف مرتين عند إعادة الحساب.
    """
    def in_range(value):
        value = str(value or "")
        return (not date_from or value >= date_from) and (not date_to or value <= date_to)

    driver = str(driver or "").strip()
    car_no = str(car_no or "").strip()
    # الفترات التي سبق احتسابها في راتب محفوظ: نستبعد تواريخها حتى لا تدخل
    # الرحلات والمصاريف نفسها في راتب جديد لنفس السائق في الفترة نفسها.
    counted = (counted_salary_periods(driver, exclude_salary_id)
               if exclude_counted else [])

    def fresh(value):
        return in_range(value) and not _in_counted_period(value, counted)

    raw_trips = [row for row in load_trips()
                 if _normalized_driver_name(row.get("driver")) == _normalized_driver_name(driver)
                 and (not car_no or str(row.get("car_no", "")).strip() == car_no)
                 and fresh(row.get("date"))]
    # إسقاط الرحلات المكرّرة: الرحلة المسجّلة مرتين كانت تدخل الإيراد والأجرة
    # مرتين فيتضاعف الراتب بلا سبب ظاهر.
    trips, duplicates = deduplicate_trips(raw_trips)
    cars = {str(row.get("car_no", "")).strip() for row in trips if row.get("car_no")}
    car_costs, driver_costs = {}, {}
    car_expense_records, driver_expense_records = [], []
    def add(bucket, category, amount):
        amount = safe_float(amount)
        if amount:
            bucket[category or "أخرى"] = round(bucket.get(category or "أخرى", 0.0) + amount, 3)
    def add_record(records, date, car_no, category, amount, notes, source):
        amount = safe_float(amount)
        if amount:
            records.append({"date": date, "car_no": car_no, "category": category or "أخرى", "amount": amount, "notes": notes or "", "source": source})
    for row in trips:
        add(car_costs, str(row.get("car_expense_type", "")).strip() or "مصاريف رحلة", row.get("car_expense_amount"))
        add_record(car_expense_records, row.get("date"), row.get("car_no"), str(row.get("car_expense_type", "")).strip() or "مصاريف رحلة", row.get("car_expense_amount"), row.get("notes"), "رحلة")
        add(driver_costs, "مصروف سائق (رحلة)", row.get("driver_expense"))
        add_record(driver_expense_records, row.get("date"), row.get("car_no"), "مصروف سائق (رحلة)", row.get("driver_expense"), row.get("notes"), "رحلة")
    for row in load_daily_expenses():
        if not fresh(row.get("date")):
            continue
        owner = daily_expense_owner(row)
        if owner == "سيارة" and str(row.get("car_no", "")).strip() in cars:
            add(car_costs, str(row.get("category", "")).strip(), row.get("amount"))
            add_record(car_expense_records, row.get("date"), row.get("car_no"), str(row.get("category", "")).strip(), row.get("amount"), row.get("notes"), "مصروف يومي")
        elif owner == "سائق" and str(row.get("driver", "")).strip() == driver:
            add(driver_costs, str(row.get("category", "")).strip(), row.get("amount"))
            add_record(driver_expense_records, row.get("date"), row.get("car_no"), str(row.get("category", "")).strip(), row.get("amount"), row.get("notes"), "مصروف يومي")
            add(driver_costs, "سلفة للسائق", row.get("driver_advance"))
            add_record(driver_expense_records, row.get("date"), row.get("car_no"), "سلفة للسائق", row.get("driver_advance"), row.get("notes"), "سلفة")
    for row in load_maintenance():
        if str(row.get("car_no", "")).strip() in cars and fresh(row.get("date")):
            add(car_costs, "صيانة - " + (str(row.get("type", "")).strip() or "أخرى"), row.get("cost"))
            add_record(car_expense_records, row.get("date"), row.get("car_no"), "صيانة - " + (str(row.get("type", "")).strip() or "أخرى"), row.get("cost"), row.get("notes"), "صيانة")
    base = next((safe_float(row.get("base_salary")) for row in load_drivers()
                 if str(row.get("name", "")).strip() == driver), 0.0)
    # رصيد مرحّل من رواتب سابقة: ما لم يُسدّد يبقى للشهر التالي، والمبلغ
    # الزائد على السائق يُطرح من راتب هذا الشهر.
    carry = driver_carry_balance(driver, date_from, exclude_salary_id)
    return {"driver": driver, "car_no": car_no, "base_salary": base, "trips": trips,
            "cars": sorted(cars), "duplicates": duplicates,
            "counted_periods": counted, "carry": carry,
            "revenue": round(sum(safe_float(row.get("fee")) for row in trips), 3),
            "holiday": round(sum(safe_float(row.get("holiday_price")) for row in trips), 3),
            "car_costs": car_costs, "driver_costs": driver_costs,
            # السلف جزء من مصاريف السائق هنا، فلا تُطرح مرتين في الحساب.
            "advances": safe_float(driver_costs.get("سلفة للسائق", 0.0)),
            "car_expense_records": car_expense_records,
            "driver_expense_records": driver_expense_records}

def salary_method_description(method):
    """شرح نصي لطريقة الحساب، يُعرض في شاشة الرواتب أسفل الحقل."""
    method = str(method or "").strip()
    if not method:
        return "اختر طريقة الحساب لعرض شرح طريقة الاحتساب."
    return SALARY_METHOD_DESCRIPTIONS.get(
        method, f"طريقة غير معرّفة: {method}")

def default_salary_method_for_driver(driver):
    from .entities import load_drivers
    """طريقة الحساب المقترحة لسائق حسب سجله وقواعد الإيراد المتفق عليها.

    سائقو «إيراد السيارة» لهم قاعدة خاصة في البرنامج، ومن لا قاعدة له يبدأ
    بالطريقة «شهري» (الراتب الأساسي بعد خصم المصاريف والمرحّل) إلا إن كان
    راتبه الأساسي فارغاً فيلجأ إلى «رحلة» لأن الأجرة المدوّنة على كل رحلة هي الأوضح.
    """
    if revenue_salary_rule(driver):
        return REVENUE_SALARY_TYPE
    row = next((d for d in load_drivers()
                if _normalized_driver_name(d.get("name")) == _normalized_driver_name(driver)), None)
    if row is None:
        return SALARY_METHOD_LABELS[0]
    return SALARY_METHOD_LABELS[0] if safe_float(row.get("base_salary")) else "رحلة"

def driver_salary_inputs(driver, date_from="", date_to="", car_no="",
                         exclude_counted=True, exclude_salary_id=None):
    from .entities import car_for_driver, load_drivers
    from .finance import load_maintenance
    from .trips import daily_expense_owner, deduplicate_trips, load_daily_expenses, load_trips
    """كل مدخلات راتب سائق خلال فترة، مجمّعة من نفس المصادر التي تعتمدها
    دالة `calculate_salary`. تستخدمها شاشة الرواتب وميزة إعادة الحساب الجماعي
    حتى لا تختلف الأرقام المعروضة عن المحفوظة.
    """
    driver = str(driver or "").strip()
    date_from = str(date_from or "").strip()
    date_to = str(date_to or "").strip()

    def in_range(value):
        value = str(value or "")
        return (not date_from or value >= date_from) and (not date_to or value <= date_to)

    # استبعاد ما سبق احتسابه في راتب محفوظ لنفس السائق.
    counted = (counted_salary_periods(driver, exclude_salary_id)
               if exclude_counted else [])

    def fresh(value):
        return in_range(value) and not _in_counted_period(value, counted)

    month = (date_from or date_to)[:7]
    raw_trips = [row for row in load_trips()
                 if _normalized_driver_name(row.get("driver")) == _normalized_driver_name(driver)
                 and fresh(row.get("date"))]
    # إسقاط الرحلات المكرّرة قبل أي جمع حتى لا يتضاعف الراتب.
    trips, duplicates = deduplicate_trips(raw_trips)
    cars = {str(row.get("car_no", "")).strip() for row in trips if row.get("car_no")}
    car_costs, driver_costs = {}, {}

    def _add(bucket, category, amount):
        amount = safe_float(amount)
        if amount:
            bucket[category or "أخرى"] = round(bucket.get(category or "أخرى", 0.0) + amount, 3)

    for row in trips:
        _add(car_costs, str(row.get("car_expense_type", "")).strip() or "مصاريف رحلة",
             row.get("car_expense_amount"))
        _add(driver_costs, "مصروف سائق (رحلة)", row.get("driver_expense"))
    for row in load_daily_expenses():
        if not fresh(row.get("date")):
            continue
        if (daily_expense_owner(row) == "سيارة"
                and str(row.get("car_no", "")).strip() in cars):
            _add(car_costs, str(row.get("category", "")).strip(), row.get("amount"))
        elif (daily_expense_owner(row) == "سائق"
              and _normalized_driver_name(row.get("driver")) == _normalized_driver_name(driver)):
            _add(driver_costs, str(row.get("category", "")).strip(), row.get("amount"))
            _add(driver_costs, "سلفة للسائق", row.get("driver_advance"))
    for row in load_maintenance():
        if str(row.get("car_no", "")).strip() in cars and fresh(row.get("date")):
            _add(car_costs, "صيانة - " + (str(row.get("type", "")).strip() or "أخرى"),
                 row.get("cost"))

    car_no = str(car_no or "").strip()
    if not car_no:
        car_no = car_for_driver(driver, date_to or date_from)
    driver_row = next((d for d in load_drivers()
                       if _normalized_driver_name(d.get("name")) == _normalized_driver_name(driver)), None)
    base = safe_float((driver_row or {}).get("base_salary"))
    rule = revenue_salary_rule(driver)
    # رصيد مرحّل من رواتب سابقة: ما لم يُسدّد يبقى للشهر التالي، والمبلغ
    # الزائد على السائق يُطرح من راتب هذا الشهر.
    carry = driver_carry_balance(driver, date_from, exclude_salary_id)
    return {"driver": driver, "car_no": car_no, "month": month, "rule": rule,
            "counted_periods": counted, "carry": carry,
            "base_salary": base, "trips": trips, "cars": sorted(cars),
            "duplicates": duplicates,
            "trip_revenue": round(sum(safe_float(row.get("fee")) for row in trips), 3),
            "holiday_revenue": round(sum(safe_float(row.get("holiday_price")) for row in trips), 3),
            # نفس دالة الأجرة المستعملة في كشف الحساب، فلا يختلف الرقم بينهما.
            "driver_wages": driver_wages_total(trips),
            "car_costs": car_costs, "driver_costs": driver_costs,
            "car_expenses": round(sum(car_costs.values()), 3),
            "driver_expenses": round(sum(driver_costs.values()), 3),
            # السلف جزء من `driver_costs` هنا ضمن مصاريف السائق، فتُخصم مرة واحدة.
            "advances": safe_float(driver_costs.get("سلفة للسائق", 0.0))}

def salary_balance_state(net):
    """تصنيف رصيد السائق: «دائن» إن كان له مبلغ، و«مدين» إن كان عليه.

    الرقم الموجب في حساب الرواتب يعني أن للشركة عليه رصيد، والسالب يعني أن
    عليه مديونية. كنّا نعرض الرقم وحده فيُقرأ الرقم السالب بلا معنى.
    """
    amount = safe_float(net)
    if amount > 0:
        return "دائن"
    if amount < 0:
        return "مدين"
    return "متعادل"

def calculate_salary(method, base_salary=0.0, trip_revenue=0.0, holiday_revenue=0.0,
                     driver_wages=0.0, car_expenses=0.0, driver_expenses=0.0,
                     carry_balance=0.0):
    """حساب راتب السائق بطريقة واحدة معتمدة لكل الواجهات.

    كانت كل واجهة (النموذج، حاسبة التفاصيل، الحفظ) تحسب بطريقتها الخاصة فتختلف
    الأرقام المعروضة عن المحفوظة. هذه الدالة هي المرجع الوحيد.

    أُبطلت العمولة وبدل عمل الجمعة والسلف والخصومات من المعادلة بناءً على
    الطلب: السلف أصلاً بند داخل «مصاريف السائق» فكان تُخصم مرتين، والعمولة
    والبدل والخصومات كانت بنوداً لا يعرفها المحاسب عند الإدخال.
    المعادلة الآن: الراتب الأساسي (أو أجرة الرحلات) − مصاريف السائق
    + الرصيد المرحّل من الشهر السابق.
    """
    method = str(method or "شهري").strip() or "شهري"
    base_salary = safe_float(base_salary)
    trip_revenue = safe_float(trip_revenue)
    holiday_revenue = safe_float(holiday_revenue)
    driver_wages = safe_float(driver_wages)
    car_expenses = safe_float(car_expenses)
    driver_expenses = safe_float(driver_expenses)
    carry_balance = safe_float(carry_balance)

    if method in SALARY_REVENUE_FRACTIONS:
        # حصة الإيراد: صافي الإيراد (إيراد الرحلات والعطل) بعد خصم مصاريف السيارة.
        net_revenue = max(0.0, trip_revenue + holiday_revenue - car_expenses)
        share = round(net_revenue * SALARY_REVENUE_FRACTIONS[method], 3)
        # «راتب + ...» يجمع الراتب الأساسي، أما الحصة المجردة فلا تضيفه.
        base = base_salary if method.startswith("راتب +") or method == REVENUE_SALARY_TYPE else 0.0
    elif method == "رحلة":
        # أجرة السائق تُؤخذ من ما هو مدوّن فعلاً على كل رحلة في الفترة.
        share = driver_wages
        base = 0.0
    elif method == "الراتب الأساسي فقط":
        share = 0.0
        base = base_salary
    else:
        # «شهري»: الراتب الأساسي فقط بعد إبطال العمولة وبدل الجمعة.
        share = 0.0
        base = base_salary
    # الرصيد المرحّل: موجب فيُضاف (باقي من شهر سابق)، وسالب فيُطرح
    # (مبلغ زائد على السائق من شهر سابق).
    net = round(base + share - driver_expenses + carry_balance, 3)
    return {"method": method, "base": round(base, 3), "share": round(share, 3),
            "trip_revenue": round(trip_revenue, 3),
            "holiday_revenue": round(holiday_revenue, 3),
            "driver_wages": round(driver_wages, 3),
            "car_expenses": round(car_expenses, 3),
            "driver_expenses": round(driver_expenses, 3),
            "carry_balance": round(carry_balance, 3),
            "net": net,
            # رصيد السائق: موجب يعني مستحقاً له، وسالب يعني عليه مديونية.
            "balance": net, "state": salary_balance_state(net)}

def save_salary(data, editing_id=None):
    from .core import _next_id, _save_row
    from .trips import deduplicate_trips, load_trips
    rows = load_salaries()
    if editing_id is None:
        data["id"] = str(_next_id(rows))
    else:
        data["id"] = str(editing_id)
    salary_type = (data.get("salary_type") or "شهري").strip() or "شهري"
    data["salary_type"] = salary_type
    driver_name = (data.get("driver") or "").strip()
    month = (data.get("month") or "").strip()
    # نحفظ الفترة المحسوبة لتعرف الشاشة لاحقاً أي الرحلات والمصاريف
    # استُعملت، فلا تدخل في راتب جديد لنفس السائق في الفترة نفسها.
    data["period_from"] = str(data.get("period_from", "") or "").strip()
    data["period_to"] = str(data.get("period_to", "") or "").strip()
    # الرصيد المرحّل من الشهر السابق: ما تبقى للسائق أو عليه قبل هذه الفترة،
    # ونحفظه مع السجل ليبقى ظاهراً في سجل الرواتب وفي كشف الشهر.
    carry_in = safe_float(data.get("carry_in"))
    if not carry_in:
        carry_in = driver_carry_balance(driver_name, data["period_from"])["balance"]
    data["carry_in"] = round(carry_in, 3)
    calculated = data.get("_calculated_details") or {}
    if calculated:
        result = calculate_salary(
            salary_type,
            base_salary=calculated.get("base"),
            trip_revenue=calculated.get("trip_revenue"),
            holiday_revenue=calculated.get("holiday_revenue"),
            driver_wages=calculated.get("driver_wages"),
            car_expenses=calculated.get("car_expenses"),
            driver_expenses=calculated.get("driver_expenses"),
            carry_balance=carry_in)
    elif salary_type in SALARY_REVENUE_FRACTIONS:
        # صيغ إيراد السيارة تُشتق من قاعدة «إيراد السيارة» المعتمدة لكل سائق.
        details = vehicle_revenue_salary_details(driver_name, month, data.get("car_no", ""))
        result = calculate_salary(
            salary_type,
            base_salary=details.get("base_salary"),
            trip_revenue=details.get("vehicle_revenue"),
            holiday_revenue=details.get("holiday_revenue"),
            car_expenses=details.get("vehicle_expenses"),
            carry_balance=carry_in)
    else:
        # «شهري» و«رحلة» تُحسبان من رحلات الشهر نفسها بعد إسقاط المكرّر.
        trips = deduplicate_trips([
            row for row in load_trips()
            if _normalized_driver_name(row.get("driver")) == _normalized_driver_name(driver_name)
            and str(row.get("date", "")).startswith(month)])[0]
        base = safe_float(data.get("base_salary"))
        if salary_type == "رحلة":
            base = 0.0
        result = calculate_salary(
            salary_type,
            base_salary=base,
            trip_revenue=sum(safe_float(row.get("fee")) for row in trips),
            holiday_revenue=sum(safe_float(row.get("holiday_price")) for row in trips),
            driver_wages=driver_wages_total(trips),
            driver_expenses=sum(driver_salary_inputs(
                driver_name, month, month, data.get("car_no", "")
            )["driver_costs"].values()),
            carry_balance=carry_in)
    data["base_salary"] = round(result["base"], 3)
    data["commission_total"] = round(result["share"], 3)
    data["trip_revenue"] = round(result["trip_revenue"], 3)
    data["holiday_revenue"] = round(result["holiday_revenue"], 3)
    data["driver_wages"] = round(result["driver_wages"], 3)
    data["car_expenses"] = round(result["car_expenses"], 3)
    data["driver_expenses"] = round(result["driver_expenses"], 3)
    data["net_salary"] = round(result["net"], 3)
    data["balance_state"] = result["state"]
    # ما سُدّد من الراتب: إن ترك فارغاً نعتبره مسدّداً بالكامل حسب حالة زر
    # «مدفوع؟». الفرق بين الصافي والمسدّد هو الباقي المرحّل: موجب يعني مستحقاً
    # له في الشهر التالي، وسالب يعني مبلغاً زائداً دفعه فيُطرح من راتبه.
    settled = safe_float(data.get("settled_amount"))
    if settled == 0 and str(data.get("paid", "")).strip() == "نعم":
        settled = result["net"]
    data["settled_amount"] = round(settled, 3)
    data["carry_forward"] = round(result["net"] - settled, 3)
    data.pop("_calculated_details", None)
    data.setdefault("paid", "لا")
    _save_row("salaries", "id", data, editing_id)

def delete_salary(row_id):
    from .core import _delete_row
    _delete_row("salaries", "id", row_id)

def recalculate_driver_salary(driver, date_from="", date_to="", car_no="",
                              method="", save=True,
                              exclude_counted=True, editing_id=None):
    """حساب راتب سائق واحد بالطريقة المطلوبة وإرجاع تفاصيل النتيجة.

    توحيد المصدر هنا يضمن أن ما تعرضه شاشة الرواتب، وما يُطبع في كشف الحساب،
    وما يُحفظ في السجل، كلها أرقام واحدة محسوبة بالطريقة نفسها.
    """
    driver = str(driver or "").strip()
    if not driver:
        raise ValueError("الرجاء اختيار السائق أولاً.")
    inputs = driver_salary_inputs(driver, date_from, date_to, car_no,
                                  exclude_counted=exclude_counted,
                                  exclude_salary_id=editing_id)
    method = str(method or "").strip() or default_salary_method_for_driver(driver)
    if method not in SALARY_METHOD_LABELS:
        raise ValueError(f"طريقة حساب غير معروفة: {method}")
    base = inputs["base_salary"]
    # الرصيد المرحّل: ما تبقى للسائق أو عليه من رواتب سابقة.
    carry = inputs.get("carry", {}).get("balance", 0.0)
    # قواعد «إيراد السيارة» المتفق عليها تغيّر مصدر الأرقام: بعض السائقين
    # يأخذون راتباً ثابتاً فوق حصتهم من الإيراد، والآخرون حصتهم بعد خصم
    # الديزل فقط، فنستدعي دالة التفاصيل المخصّصة لهم بدل المدخلات العامة.
    if method == REVENUE_SALARY_TYPE and inputs["rule"]:
        details = vehicle_revenue_salary_details(driver, inputs["month"],
                                                 inputs["car_no"])
        base = details["base_salary"]
        result = calculate_salary(
            method, base_salary=base,
            trip_revenue=details["vehicle_revenue"],
            holiday_revenue=details["holiday_revenue"],
            driver_wages=inputs["driver_wages"],
            car_expenses=details["vehicle_expenses"],
            driver_expenses=inputs["driver_expenses"],
            carry_balance=carry)
    else:
        result = calculate_salary(
            method, base_salary=base,
            trip_revenue=inputs["trip_revenue"],
            holiday_revenue=inputs["holiday_revenue"],
            driver_wages=inputs["driver_wages"],
            car_expenses=inputs["car_expenses"],
            driver_expenses=inputs["driver_expenses"],
            carry_balance=carry)
    details = dict(inputs)
    details.update(result)
    details["method"] = method
    if save:
        save_salary({
            "driver": driver, "car_no": inputs["car_no"], "month": inputs["month"],
            "salary_type": method, "base_salary": result["base"],
            "trip_revenue": result["trip_revenue"],
            "holiday_revenue": result["holiday_revenue"], "driver_wages": result["driver_wages"],
            "car_expenses": result["car_expenses"], "driver_expenses": result["driver_expenses"],
            "carry_in": result["carry_balance"],
            "net_salary": result["net"],
        })
    return details

def recalculate_all_driver_salaries(date_from="", date_to="", method="", save=True):
    from .entities import load_drivers
    """إعادة حساب رواتب جميع السائقين في فترة واحدة.

    الوضع الافتراضي يحسب لكل سائق بطريقته المعتادة (المقترحة من سجله).
    وعند تمرير `method="كل الطرق"` يُحسب لكل سائق بجميع الطرق المتاحة، فتُختبر
    كل صيغة على بيانات حقيقية قبل الاعتماد عليها.
    """
    date_from = str(date_from or "").strip()
    date_to = str(date_to or "").strip()
    every_method = str(method or "").strip() in ("", "كل الطرق", "الكل")
    rows, errors = [], []
    for row in load_drivers():
        driver = str(row.get("name", "")).strip()
        if not driver:
            continue
        if every_method:
            wanted = list(SALARY_METHOD_LABELS)
        elif method:
            wanted = [method]
        else:
            wanted = [default_salary_method_for_driver(driver)]
        for one in wanted:
            try:
                details = recalculate_driver_salary(driver, date_from, date_to,
                                                    method=one, save=save)
                rows.append(details)
            except Exception as exc:
                errors.append((driver, one, str(exc)))
    return {"rows": rows, "errors": errors,
            "total_net": round(sum(safe_float(r["net"]) for r in rows), 3),
            "drivers": len({r["driver"] for r in rows}),
            "records": len(rows)}

def synchronize_existing_records():
    from .core import ensure_workbook
    from .trips import load_trips, save_trip
    """Rewrite legacy trips and salaries using the current input fields."""
    ensure_workbook()

    # Re-save every trip so missing current fields receive their defaults and
    # the complete current TRIP_FIELDS layout is written back to Excel.
    for trip in load_trips():
        save_trip(dict(trip), editing_id=trip.get("id"))

    # Salary totals and daily advances are derived fields in the current form;
    # recalculating them also upgrades older salary rows to the current model.
    for salary in load_salaries():
        save_salary(dict(salary), editing_id=salary.get("id"))

# ------------------------------------------------------------------
# التقارير المالية
# ------------------------------------------------------------------
def financial_summary(date_from=None, date_to=None):
    from .finance import load_invoices, load_maintenance
    from .trips import load_daily_expenses
    """ملخص مالي: الإيرادات (من الفواتير)، المصروفات (الصيانة + الرواتب الصافية)، صافي الربح."""

    def in_range(d):
        if not d:
            return True
        if date_from and d < date_from:
            return False
        if date_to and d > date_to:
            return False
        return True

    revenue = sum(safe_float(i["total"]) for i in load_invoices() if in_range(str(i.get("date", ""))))
    maintenance_cost = sum(safe_float(m["cost"]) for m in load_maintenance() if in_range(str(m.get("date", ""))))
    daily_expenses_cost = sum(safe_float(e["amount"]) for e in load_daily_expenses()
                              if in_range(str(e.get("date", ""))) and e.get("category") != "سلفة يومية للسائق")
    advances_cost = sum(
        safe_float(e.get("driver_advance"))
        + (safe_float(e.get("amount")) if e.get("category") == "سلفة يومية للسائق" else 0.0)
        for e in load_daily_expenses() if in_range(str(e.get("date", "")))
    )
    salaries_cost = sum(
        safe_float(s["net_salary"])
        for s in load_salaries()
        if in_range(str(s.get("date") or (str(s.get("month", "")) + "-01")))
    )
    expenses = maintenance_cost + daily_expenses_cost + advances_cost + salaries_cost
    return {
        "revenue": round(revenue, 3),
        "maintenance_cost": round(maintenance_cost, 3),
        "daily_expenses_cost": round(daily_expenses_cost, 3),
        "advances_cost": round(advances_cost, 3),
        "salaries_cost": round(salaries_cost, 3),
        "expenses": round(expenses, 3),
        "net_profit": round(revenue - expenses, 3),
    }
