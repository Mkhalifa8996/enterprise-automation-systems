"""بيانات تجريبية شاملة لتجربة البرنامج قبل التشغيل الفعلي.

تولّد سجلات مترابطة في جميع جداول النظام (عشرة سجلات فأكثر لكل جدول)،
وتحفظ مفاتيحها في جدول البيانات المحلي ليتم حذفها لاحقاً دون المساس
بأي بيانات حقيقية أدخلها المستخدم.
"""
import json
import random
from datetime import date, timedelta

from .. import data as td

# علامة تظهر داخل النظام ليسهل تمييز السجلات التجريبية.
DEMO_TAG = "بيانات تجريبية"
META_KEY = "demo_record_keys"
MINIMUM_ROWS = 10

DRIVERS = [
    ("عبد الله السالم", "داخلي"), ("محمد العتيبي", "داخلي"), ("فهد الدوسري", "داخلي"),
    ("يوسف إبراهيم", "داخلي"), ("خالد المطيري", "داخلي"), ("سالم الزعبي", "داخلي"),
    ("ناصر العنزي", "داخلي"), ("بدر الصالح", "داخلي"),
    ("راشد الخالدي", "خارجي"), ("ماجد الحربي", "خارجي"),
    ("وليد شاهين", "خارجي"), ("أنس الغامدي", "خارجي"),
]
VEHICLES = [
    "فورد F450", "مرسيدس أكتروس", "مان TGS", "إيفيكو Eurocargo", "سكانيا R450",
    "فoton Auman", "جاك ساحر", "دايافو", "إيفيكو كورو", "فولفو FH",
    "رينو ميتسيسي", "هيونداي HD78",
]
CUSTOMERS = [
    "شركة الخليج للتجارة", "مؤسسة النور", "شركة البناء الحديث", "مجموعة الديار",
    "شركة أمواج للتجارة", "شركة الأمل", "مؤسسة الفجر", "شركة المشرق",
    "مؤسسة البركة", "شركة الصفا", "مؤسسة روضة", "شركة الواحة",
]
COMPANIES = [
    "شركة الخدمات اللوجستية الأولى", "شركة النقل السريع", "مؤسسة التوزيع المتحدة",
    "شركة الصقور للشحن", "مؤسسة إينيو للتجارة", "شركة دلتا", "مؤسسة واحة",
    "شركة زهرة", "مؤسسة حمل", "شركة طيبة",
]
CARS = [f"DEMO-{i:03d}" for i in range(1, 13)]

random.seed(20260928)


def _ago(days):
    return (date.today() - timedelta(days=days)).isoformat()


def _rows(sheet_key):
    loaders = {
        "drivers": td.load_drivers, "vehicles": td.load_vehicles,
        "customers": td.load_customers, "companies": td.load_companies,
        "places": td.load_places, "trips": td.load_trips,
        "vehicle_assignments": td.load_vehicle_assignments,
        "vehicle_partners": td.load_vehicle_partners,
        "maintenance": td.load_maintenance, "services": td.load_services,
        "invoices": td.load_invoices, "payments": td.load_payments,
        "salaries": td.load_salaries, "cash_ledger": td.load_cash_ledger,
        "fuel": td.load_fuel, "contracts": td.load_contracts,
        "quotations": td.load_quotations, "maintenance_plans": td.load_maintenance_plans,
        "parts": td.load_parts, "daily_expenses": td.load_daily_expenses,
        "partner_payments": td.load_partner_payments,
        "driver_payments": td.load_driver_payments,
    }
    return loaders.get(sheet_key, list)()


def _keyed(sheet_key, key_field):
    return {str(row.get(key_field, "")) for row in _rows(sheet_key)}


def _remember_all(sheet_key, key_field, before):
    """يسجّل كل المفاتيح التي أُضيفت حديثاً لهذه الورقة."""
    new = sorted(_keyed(sheet_key, key_field) - before)
    if not new:
        return []
    keys = td._load_metadata(META_KEY)
    stored = set(keys.get(sheet_key) or [])
    stored.update(new)
    keys[sheet_key] = sorted(stored)
    td._save_metadata(META_KEY, keys)
    return new


def _seed_drivers():
    before = _keyed("drivers", "name")
    for index, (name, kind) in enumerate(DRIVERS):
        td.save_driver({
            "name": name, "national_id": f"2900{index:04d}",
            "license_no": f"LIC-{index + 1:04d}", "phone": f"9659{index:02d}12345",
            "driver_type": kind, "car_no": "",
            "base_salary": 250 + index * 10, "commission_per_trip": 5,
            "notes": DEMO_TAG})
    return _remember_all("drivers", "name", before)


def _seed_vehicles():
    before = _keyed("vehicles", "car_no")
    for index, car in enumerate(CARS):
        td.save_vehicle({
            "car_no": car, "model": VEHICLES[index], "year": str(2018 + index % 6),
            "driver": "", "work_type": td.VEHICLE_WORK_TYPES[index % 3],
            "contents": "، ".join(["ساطحة", "مولد"] if index % 2 else ["مقطورة مبردة", "لوبد"]),
            "license_expiry": _ago(-120 - index * 10),
            "notes": DEMO_TAG})
    return _remember_all("vehicles", "car_no", before)


def _seed_customers():
    before = _keyed("customers", "name")
    for index, name in enumerate(CUSTOMERS):
        td.save_customer({
            "name": name, "phone": f"9655{index:02d}44321",
            "address": f"الكويت - حولي - شارع {index + 1}", "notes": DEMO_TAG})
    return _remember_all("customers", "name", before)


def _seed_companies():
    before = _keyed("companies", "name")
    customers = _rows("customers")
    for index, name in enumerate(COMPANIES):
        td.save_company({
            "name": name,
            "customs_broker": customers[index % len(customers)]["name"] if customers else "",
            "phone": f"9656{index:02d}99887", "address": f"الكويت - الصناعية {index}",
            "notes": DEMO_TAG})
    return _remember_all("companies", "name", before)


def _seed_assignments():
    before = _keyed("vehicle_assignments", "id")
    drivers = _rows("drivers")
    for index, car in enumerate(CARS):
        driver = drivers[index % len(drivers)]["name"] if drivers else ""
        td.save_vehicle_assignment({
            "car_no": car, "driver": driver, "start_date": _ago(400),
            "end_date": "", "notes": DEMO_TAG})
    return _remember_all("vehicle_assignments", "id", before)


def _seed_partners():
    before = _keyed("vehicle_partners", "id")
    # شريك واحد لكل سيارة بنسبة 50% حتى لا تتجاوز النسب 100% عند الدمج.
    partner_names = ["الشريك الأول", "الشريك الثاني", "الشريك الثالث", "الشريك الرابع"]
    for index, car in enumerate(CARS):
        first = partner_names[index % len(partner_names)]
        td.save_vehicle_partner({
            "car_no": car, "partner": first,
            "ownership_pct": "نصف الإيراد (50%)", "start_date": _ago(400),
            "end_date": "", "locked": "نعم" if index % 3 == 0 else "لا",
            "notes": DEMO_TAG})
    return _remember_all("vehicle_partners", "id", before)


def _seed_trips():
    before = _keyed("trips", "id")
    drivers = _rows("drivers")
    customers = _rows("customers")
    if not drivers or not customers:
        return []
    for index in range(60):
        car = CARS[index % len(CARS)]
        driver = drivers[index % len(drivers)]["name"]
        kind = td.TRIP_CATEGORIES[index % 2]
        fee = 180 + (index % 7) * 40
        holiday = 25 + (index % 4) * 15
        data = {
            "date": _ago(index * 2 + 1),
            "driver": driver, "driver_type": td.driver_type_of(driver),
            "car_no": car,
            "customer": customers[index % len(customers)]["name"],
            "company": customers[(index + 1) % len(customers)]["name"],
            "trip_category": kind,
            "direction": (td.INTERNAL_DIRECTIONS[index % 2] if index % 2 == 0
                          else td.INTERNATIONAL_DIRECTIONS[index % 2]),
            "country": "السعودية" if index % 2 else "",
            "declaration_no": f"DEC-{1000 + index}",
            "declaration_trip_no": f"{1000 + index}",
            "container_size": ["20", "40", "45"][index % 3],
            "fee": fee, "holiday_price": holiday,
            "car_expense_type": ["ديزل السيارة", "إطارات السيارة", "صيانة عامة"][index % 3],
            "car_expense_amount": 20 + (index % 5) * 10,
            "driver_expense": 5 + (index % 3) * 5,
            "invoiced": "نعم" if index < 12 else "لا",
            "invoice_no": f"DEMO-INV-{index + 1:03d}" if index < 12 else "",
            "notes": DEMO_TAG}
        td.save_trip(data)
    return _remember_all("trips", "id", before)


def _seed_daily_expenses():
    before = _keyed("daily_expenses", "id")
    drivers = _rows("drivers")
    for index in range(24):
        is_driver_cost = index % 4 == 3
        category = (td.DRIVER_EXPENSE_CATEGORIES[index % len(td.DRIVER_EXPENSE_CATEGORIES)]
                    if is_driver_cost
                    else td.VEHICLE_EXPENSE_CATEGORIES[index % len(td.VEHICLE_EXPENSE_CATEGORIES)])
        td.save_daily_expense({
            "date": _ago(index * 2 + 1), "car_no": CARS[index % len(CARS)],
            "driver": drivers[index % len(drivers)]["name"] if drivers else "",
            "category": category, "amount": 15 + (index % 6) * 12,
            "driver_advance": 20 if is_driver_cost else 0,
            "expense_owner": "سائق" if is_driver_cost else "سيارة",
            "description": DEMO_TAG})
    return _remember_all("daily_expenses", "id", before)


def _seed_maintenance():
    before = _keyed("maintenance", "id")
    for index in range(12):
        td.save_maintenance({
            "date": _ago(index * 7 + 2), "car_no": CARS[index % len(CARS)],
            "type": td.MAINTENANCE_TYPES[index % len(td.MAINTENANCE_TYPES)],
            "cost": 90 + index * 30, "notes": DEMO_TAG})
    return _remember_all("maintenance", "id", before)


def _seed_invoices():
    before = _keyed("invoices", "invoice_no")
    customers = _rows("customers")
    if not customers:
        return []
    items = [{"desc": "TRANSPORTATION CHARGES — أجور نقل", "amount": 250.0},
             {"desc": "DEMURRAGE — تأخير", "amount": 50.0},
             {"desc": "CUSTOMS — تخليص", "amount": 35.0}]
    for index in range(12):
        customer = customers[index % len(customers)]["name"]
        total = 300 + index * 45
        td.save_invoice({
            "invoice_no": f"DEMO-INV-{index + 1:03d}", "date": _ago(index * 5 + 3),
            "customer": customer, "paid": "نعم" if index % 3 == 0 else "لا",
            "awb_no": f"AWB-{index + 1:04d}", "container_count": 1 + index % 3,
            "items_json": json.dumps(items, ensure_ascii=False),
            "total": total, "declaration_no": f"DEC-{1000 + index}", "notes": DEMO_TAG})
    return _remember_all("invoices", "invoice_no", before)


def _seed_payments():
    before = _keyed("payments", "id")
    customers = _rows("customers")
    invoices = _rows("invoices")
    for index in range(12):
        customer = customers[index % len(customers)]["name"] if customers else ""
        invoice = invoices[index % len(invoices)] if invoices else None
        td.save_payment({
            "date": _ago(index * 5 + 2), "customer": customer,
            "amount": 200 + index * 55,
            "reference": f"REC-{index + 1:04d}",
            "invoice_no": invoice["invoice_no"] if invoice else "",
            "notes": DEMO_TAG})
    return _remember_all("payments", "id", before)


def _seed_salaries():
    before = _keyed("salaries", "id")
    drivers = _rows("drivers")
    for index, driver in enumerate(drivers[:12]):
        car = CARS[index % len(CARS)]
        month = (date.today() - timedelta(days=30 * (index % 3) + 32)).strftime("%Y-%m")
        td.save_salary({
            "driver": driver["name"], "car_no": car, "month": month,
            "salary_type": "إيراد السيارة" if index % 3 == 0 else "شهري",
            "date": f"{month}-28", "paid": "نعم" if index % 2 == 0 else "لا",
            "notes": DEMO_TAG,
            "_calculated_details": {"base": 200 + index * 15, "share": 40 + index * 5,
                                    "trip_revenue": 900 + index * 60, "holiday_revenue": 120,
                                    "driver_wages": 0, "car_expenses": 300 + index * 20,
                                    "driver_expenses": 60, "net": 150 + index * 12}})
    return _remember_all("salaries", "id", before)


def _seed_partner_payments():
    before = _keyed("partner_payments", "id")
    shares = _rows("vehicle_partners")
    if not shares:
        return []
    for index in range(12):
        share = shares[index % len(shares)]
        td.save_partner_payment({
            "date": _ago(index * 6 + 4), "partner": share["partner"],
            "car_no": share["car_no"],
            "payment_type": "مدين" if index % 3 else "دائن",
            "amount": 150 + index * 40, "notes": DEMO_TAG})
    return _remember_all("partner_payments", "id", before)


def _seed_driver_payments():
    before = _keyed("driver_payments", "id")
    drivers = _rows("drivers")
    for index in range(12):
        driver = drivers[index % len(drivers)]["name"] if drivers else ""
        td.save_driver_payment({
            "date": _ago(index * 6 + 5), "driver": driver,
            "driver_type": td.driver_type_of(driver),
            "car_no": CARS[index % len(CARS)],
            "payment_type": "مدين" if index % 3 else "دائن",
            "amount": 120 + index * 35, "notes": DEMO_TAG})
    return _remember_all("driver_payments", "id", before)


def _seed_cash_ledger():
    before = _keyed("cash_ledger", "id")
    for index in range(16):
        incoming = index % 2 == 0
        td.save_cash_ledger({
            "date": _ago(index * 4 + 1),
            "transaction_type": "قبض" if incoming else "صرف",
            "account": td.CASH_LEDGER_ACCOUNTS[index % 2],
            "category": "تحصيل عميل" if incoming else "مصاريف تشغيل",
            "party": "عميل تجريبي" if incoming else "مورد",
            "amount": 100 + index * 45, "reference": f"CASH-{index + 1:04d}",
            "notes": DEMO_TAG})
    return _remember_all("cash_ledger", "id", before)


def _seed_fuel():
    before = _keyed("fuel", "id")
    drivers = _rows("drivers")
    for index in range(14):
        liters = 80 + (index % 6) * 25
        price = 0.28
        td.save_fuel({
            "date": _ago(index * 3 + 1), "car_no": CARS[index % len(CARS)],
            "driver": drivers[index % len(drivers)]["name"] if drivers else "",
            "odometer": 100000 + index * 1500, "liters": liters,
            "price_per_liter": price, "total": round(liters * price, 3),
            "station": ["Shell", "Zaid", "Alshaya"][index % 3], "notes": DEMO_TAG})
    return _remember_all("fuel", "id", before)


def _seed_contracts():
    before = _keyed("contracts", "id")
    parties = _rows("companies") or _rows("customers")
    for index in range(10):
        party = parties[index % len(parties)]["name"] if parties else "طرف تجريبي"
        td.save_contract({
            "contract_no": f"CON-{index + 1:04d}", "party": party,
            "contract_type": ["نقل", "تأجير", "خدمات لوجستية"][index % 3],
            "start_date": _ago(300 - index * 10), "end_date": _ago(-60 + index * 10),
            "value": 5000 + index * 1200,
            "status": "نشط" if index % 4 else "منتهي", "notes": DEMO_TAG})
    return _remember_all("contracts", "id", before)


def _seed_quotations():
    before = _keyed("quotations", "id")
    customers = _rows("customers")
    for index in range(10):
        customer = customers[index % len(customers)]["name"] if customers else "عميل تجريبي"
        td.save_quotation({
            "quotation_no": f"QUO-{index + 1:04d}", "date": _ago(index * 8 + 4),
            "customer": customer, "description": "نقل حاويات برمي",
            "amount": 800 + index * 180,
            "status": ["مسودة", "تم الإرسال", "مقبول", "مرفوض"][index % 4],
            "invoice_no": "", "notes": DEMO_TAG})
    return _remember_all("quotations", "id", before)


def _seed_maintenance_plans():
    before = _keyed("maintenance_plans", "id")
    for index in range(10):
        td.save_maintenance_plan({
            "car_no": CARS[index % len(CARS)],
            "service_type": ["زيت", "إطارات", "صيانة دورية", "فحص سنوي"][index % 4],
            "due_date": _ago(-(index * 6 + 3)), "due_odometer": 100000 + index * 2000,
            "interval_km": 10000, "status": "مجدول" if index % 2 else "منجز",
            "notes": DEMO_TAG})
    return _remember_all("maintenance_plans", "id", before)


def _seed_parts():
    before = _keyed("parts", "id")
    for index in range(10):
        td.save_part({
            "car_no": CARS[index % len(CARS)],
            "part_type": ["زيت", "إطارات", "فلتر", "بطارية", "فحمات"][index % 5],
            "part_name": f"قطعة {index + 1}", "serial_no": f"SN-{index + 1:05d}",
            "install_date": _ago(index * 15 + 5), "expiry_date": _ago(-120 + index * 10),
            "cost": 40 + index * 25, "notes": DEMO_TAG})
    return _remember_all("parts", "id", before)


def _seed_services():
    before = _keyed("services", "id")
    customers = _rows("customers")
    for index in range(12):
        td.save_service({
            "date": _ago(index * 4 + 2), "company": "شركة تجريبية",
            "customer": customers[index % len(customers)]["name"] if customers else "",
            "declaration_no": f"DEC-{2000 + index}",
            "declaration_trip_no": f"{2000 + index}", "unit": "حاوية",
            "service_type": td.SERVICE_TYPES[index % len(td.SERVICE_TYPES)],
            "quantity": 1 + index % 5, "unit_price": 25 + index * 5,
            "total": (1 + index % 5) * (25 + index * 5),
            "invoiced": "نعم" if index < 6 else "لا",
            "invoice_no": f"DEMO-INV-{index % 6 + 1:03d}" if index < 6 else "",
            "notes": DEMO_TAG})
    return _remember_all("services", "id", before)


# ترتيب التعبئة: من البيانات الأساسية إلى المعاملات المعتمدة عليها.
SEED_STEPS = [
    ("السائقون", _seed_drivers), ("السيارات", _seed_vehicles),
    ("العملاء", _seed_customers), ("الشركات", _seed_companies),
    ("تكليفات السائقين", _seed_assignments), ("شركاء السيارات", _seed_partners),
    ("الرحلات", _seed_trips), ("المصاريف اليومية", _seed_daily_expenses),
    ("الصيانة", _seed_maintenance), ("الفواتير", _seed_invoices),
    ("دفعات العملاء", _seed_payments), ("الرواتب", _seed_salaries),
    ("دفعات الشركاء", _seed_partner_payments), ("دفعات السائقين", _seed_driver_payments),
    ("النقد والبنك", _seed_cash_ledger), ("الوقود", _seed_fuel),
    ("العقود", _seed_contracts), ("عروض الأسعار", _seed_quotations),
    ("خطط الصيانة", _seed_maintenance_plans), ("قطع الغيار", _seed_parts),
    ("الخدمات", _seed_services),
]

# دوال الحذف لكل جدول مع مفتاح السجل.
DELETE_BY_SHEET = {
    "driver_payments": (td.delete_driver_payment, "id"),
    "partner_payments": (td.delete_partner_payment, "id"),
    "trips": (td.delete_trip, "id"),
    "daily_expenses": (td.delete_daily_expense, "id"),
    "salaries": (td.delete_salary, "id"),
    "payments": (td.delete_payment, "id"),
    "invoices": (td.delete_invoice, "invoice_no"),
    "services": (td.delete_service, "id"),
    "vehicle_partners": (td.delete_vehicle_partner, "id"),
    "vehicle_assignments": (td.delete_vehicle_assignment, "id"),
    "maintenance": (td.delete_maintenance, "id"),
    "maintenance_plans": (td.delete_maintenance_plan, "id"),
    "parts": (td.delete_part, "id"),
    "fuel": (td.delete_fuel, "id"),
    "cash_ledger": (td.delete_cash_ledger, "id"),
    "contracts": (td.delete_contract, "id"),
    "quotations": (td.delete_quotation, "id"),
    "vehicles": (td.delete_vehicle, "car_no"),
    "drivers": (td.delete_driver, "name"),
    "customers": (td.delete_customer, "name"),
    "companies": (td.delete_company, "name"),
}


def seed(verbose=True):
    """يملأ جميع الجداول ببيانات تجريبية مترابطة. يعيد تقريراً بعدد السجلات."""
    report = {}
    for label, step in SEED_STEPS:
        try:
            report[label] = len(step())
        except Exception as exc:
            report[label] = f"خطأ: {exc}"
            if verbose:
                print(f"[demo] فشل {label}: {exc}")
    if verbose:
        total = sum(v for v in report.values() if isinstance(v, int))
        print(f"[demo] تمت تعبئة {total} سجلاً تجريبياً")
    return report


def demo_counts():
    """عدد السجلات التجريبية المسجلة في كل جدول."""
    keys = td._load_metadata(META_KEY)
    return {sheet: len(keys.get(sheet) or []) for sheet in DELETE_BY_SHEET}


def clear(verbose=True):
    """يحذف السجلات التجريبية فقط دون المساس ببيانات المستخدم."""
    keys = td._load_metadata(META_KEY)
    removed = 0
    errors = []
    # نبدأ من الجداول الأبناء حتى لا تترك سجلات يتيمة.
    for sheet, (delete_fn, key_field) in DELETE_BY_SHEET.items():
        stored = {str(k) for k in (keys.get(sheet) or [])}
        if not stored:
            continue
        for row in list(_rows(sheet)):
            if str(row.get(key_field, "")) not in stored:
                continue
            try:
                delete_fn(row.get(key_field))
                removed += 1
            except Exception as exc:
                errors.append(f"{sheet}: {exc}")
    td._save_metadata(META_KEY, {})
    if verbose:
        print(f"[demo] تم حذف {removed} سجلاً تجريبياً")
    return {"removed": removed, "errors": errors}


def ensure_minimum():
    """يعبئ البيانات التجريبية فقط إذا كان أحد الجداول تحت الحد الأدنى."""
    counts = demo_counts()
    missing = [sheet for sheet, count in counts.items() if count < MINIMUM_ROWS]
    if not missing:
        return {"seeded": False, "counts": counts}
    report = seed()
    return {"seeded": True, "counts": demo_counts(), "report": report}
