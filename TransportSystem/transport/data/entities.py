# -*- coding: utf-8 -*-
"""السائقون والسيارات والعملاء والشركاء وأماكن التحميل والتنزيل."""

from .schema import TRIP_CATEGORIES, _normalized_driver_name, partner_share_percentage

# ------------------------------------------------------------------
# السائقون
# ------------------------------------------------------------------
def load_drivers():
    from .core import _load_rows
    return _load_rows("drivers", "name")

def save_driver(data, editing_name=None):
    from .core import _save_row_by_name
    data = data.copy()
    # السيارة لا تُثبت على السائق؛ سجل التكليف الزمني هو المرجع الوحيد.
    data["car_no"] = ""
    rows = load_drivers()
    if editing_name is None:
        existing = [str(r["name"]) for r in rows]
        if data["name"] in existing:
            raise ValueError("اسم السائق موجود بالفعل")
    _save_row_by_name("drivers", data, editing_name)

def delete_driver(name):
    from .core import _delete_row
    _delete_row("drivers", "name", name)

# ------------------------------------------------------------------
# السيارات
# ------------------------------------------------------------------
def load_vehicles():
    from .core import _load_rows
    return _load_rows("vehicles", "car_no")

def save_vehicle(data, editing_car_no=None):
    from .core import _save_row_by_name
    previous = None
    if editing_car_no is not None:
        previous = next((row for row in load_vehicles()
                         if str(row.get("car_no", "")) == str(editing_car_no)), None)
    if editing_car_no is not None:
        if previous:
            merged = previous.copy()
            merged.update(data)
            data = merged
    _save_row_by_name("vehicles", data, editing_car_no)

    # Keep the driver master record synchronized with the truck assignment.
    old_driver = str((previous or {}).get("driver", "")).strip()
    new_driver = str(data.get("driver", "")).strip()
    car_no = str(data.get("car_no", "")).strip()
    if old_driver and old_driver != new_driver:
        old_row = next((row for row in load_drivers()
                        if str(row.get("name", "")).strip() == old_driver), None)
        if old_row and str(old_row.get("car_no", "")).strip() == car_no:
            old_row["car_no"] = ""
            _save_row_by_name("drivers", old_row, old_driver)
    if new_driver:
        driver_row = next((row for row in load_drivers()
                           if str(row.get("name", "")).strip() == new_driver), None)
        if driver_row:
            driver_row["car_no"] = car_no
            _save_row_by_name("drivers", driver_row, new_driver)

def delete_vehicle(car_no):
    from .core import _delete_row
    _delete_row("vehicles", "car_no", car_no)

# ------------------------------------------------------------------
# تكليفات السائقين وشركاء السيارات
# ------------------------------------------------------------------
def load_vehicle_assignments():
    from .core import _load_rows
    return _load_rows("vehicle_assignments", "id")

def save_vehicle_assignment(data, editing_id=None):
    from .core import _next_id, _save_row
    rows = load_vehicle_assignments()
    data = data.copy()
    data["id"] = str(editing_id) if editing_id is not None else str(_next_id(rows))
    start = str(data.get("start_date", "")).strip()
    end = str(data.get("end_date", "")).strip()
    if not data.get("car_no", "").strip() or not data.get("driver", "").strip() or not start:
        raise ValueError("رقم السيارة والسائق وتاريخ البداية حقول مطلوبة.")
    if end and end < start:
        raise ValueError("تاريخ نهاية التكليف يجب أن يساوي أو يلي تاريخ البداية.")
    _save_row("vehicle_assignments", "id", data, editing_id)

def delete_vehicle_assignment(row_id):
    from .core import _delete_row
    _delete_row("vehicle_assignments", "id", row_id)

def load_vehicle_partners():
    from .core import _load_rows
    return _load_rows("vehicle_partners", "id")

def save_vehicle_partner(data, editing_id=None):
    from .core import _next_id, _save_row
    from .reports import _periods_overlap
    rows = load_vehicle_partners()
    data = data.copy()
    data["id"] = str(editing_id) if editing_id is not None else str(_next_id(rows))
    car_no = str(data.get("car_no", "")).strip()
    partner = str(data.get("partner", "")).strip()
    start = str(data.get("start_date", "")).strip()
    end = str(data.get("end_date", "")).strip()
    percentage = partner_share_percentage(data.get("ownership_pct"))
    if not car_no or not partner or not start:
        raise ValueError("رقم السيارة والشريك وتاريخ البداية حقول مطلوبة.")
    if percentage <= 0 or percentage > 100:
        raise ValueError("نسبة الشريك يجب أن تكون أكبر من صفر وأقل أو تساوي 100.")
    if end and end < start:
        raise ValueError("تاريخ نهاية الشراكة يجب أن يساوي أو يلي تاريخ البداية.")
    data["ownership_pct"] = round(percentage, 3)
    # النسبة المثبتة لا تُعدَّل إلا بإلغاء التثبيت أولاً، حتى لا تختلف
    # كشوف الحساب المُسلَّمة عن النسبة المعتمدة اليوم.
    if editing_id is not None:
        previous = next((row for row in rows if str(row.get("id")) == str(editing_id)), None)
        if (previous and str(previous.get("locked", "")).strip() == "نعم"
                and str(data.get("locked", "")).strip() == "نعم"
                and round(partner_share_percentage(previous.get("ownership_pct")), 3) != round(percentage, 3)):
            raise ValueError("النسبة مثبتة لهذه الشراكة. ألغِ التثبيت من مصفوفة النسب قبل التعديل.")
    overlapping = [
        row for row in rows
        if str(row.get("id")) != str(data["id"])
        and str(row.get("car_no", "")).strip() == car_no
        and _periods_overlap(start, end, str(row.get("start_date", "")), str(row.get("end_date", "")))
    ]
    if sum(partner_share_percentage(row.get("ownership_pct")) for row in overlapping) + percentage > 100.001:
        raise ValueError("مجموع نسب الشركاء المتداخلة لنفس السيارة يتجاوز 100%.")
    _save_row("vehicle_partners", "id", data, editing_id)

def set_partner_share_lock(row_id, locked=True):
    from .core import _save_row
    """تثبيت أو إلغاء تثبيت نسبة شريك بعد اعتماد كشوف حسابه."""
    rows = load_vehicle_partners()
    row = next((item for item in rows if str(item.get("id")) == str(row_id)), None)
    if not row:
        raise ValueError("سجل الشراكة غير موجود.")
    row = row.copy()
    row["locked"] = "نعم" if locked else "لا"
    _save_row("vehicle_partners", "id", row, row_id)

def partner_share_matrix(car_no=""):
    """مصفوفة نسب الشركاء لكل سيارة مع مجموع النسب وحالة اكتمال التوزيع."""
    target = str(car_no or "").strip()
    groups = {}
    for row in load_vehicle_partners():
        car = str(row.get("car_no", "")).strip()
        if not car or (target and car != target):
            continue
        groups.setdefault(car, []).append(row)
    matrix = []
    for car in sorted(groups):
        rows = sorted(groups[car], key=lambda item: str(item.get("id", "")))
        total = sum(partner_share_percentage(item.get("ownership_pct")) for item in rows)
        matrix.append({
            "car_no": car,
            "partners": [
                {
                    "id": str(item.get("id", "")),
                    "partner": str(item.get("partner", "")).strip(),
                    "ownership_pct": partner_share_percentage(item.get("ownership_pct")),
                    "start_date": str(item.get("start_date", "")),
                    "end_date": str(item.get("end_date", "")),
                    "locked": str(item.get("locked", "")).strip() == "نعم",
                }
                for item in rows
            ],
            "total_pct": round(total, 3),
            # التوزيع مكتمل عندما تغطي النسب كامل السيارة بلا زيادة أو نقص.
            "complete": abs(total - 100.0) < 0.001,
        })
    return matrix

def delete_vehicle_partner(row_id):
    from .core import _delete_row
    _delete_row("vehicle_partners", "id", row_id)

def driver_type_of(driver_name):
    """نوع السائق (داخلي/خارجي) من سجل السائقين مع تجاهل المسافات والتشكيل."""
    name = _normalized_driver_name(driver_name)
    for row in load_drivers():
        if _normalized_driver_name(row.get("name")) == name:
            return str(row.get("driver_type", "")).strip()
    return ""

def driver_names_by_type(driver_type=""):
    """أسماء السائقين المسجّلين، مصفّاة بنوعهم (داخلي/خارجي) وبترتيب بلا تكرار.

    تُستخدم لتغذية قائمة اختيار السائق في كل شاشة تحوي حقل «نوع السائق»،
    فتعتمد نفس تعريف السائق الداخلي/الخارجي في كل مكان.
    """
    wanted = str(driver_type or "").strip()
    names, seen = [], set()
    for row in load_drivers():
        name = str(row.get("name", "")).strip()
        if not name or name in seen:
            continue
        # السائق بلا نوع مسجّل يظهر في القائمتين حتى لا يختفي من الإدخال.
        kind = str(row.get("driver_type", "")).strip()
        if wanted and kind and kind != wanted:
            continue
        seen.add(name)
        names.append(name)
    return names

def driver_car_map():
    """خريطة {اسم السائق: السيارة المكلَّفة} اعتماداً على جدول تكليفات السائقين.

    عند تعدد التكليفات تُختار الأحدث 시작اً، وتُغذّى من حقل السائق في سجل
    السيارات عندما لا يوجد تكليف مسجّل، حتى لا يبقى حقل السيارة فارغاً بلا سبب.
    """
    mapping, starts = {}, {}
    for row in load_vehicle_assignments():
        driver = str(row.get("driver", "")).strip()
        car_no = str(row.get("car_no", "")).strip()
        if not driver or not car_no:
            continue
        start = str(row.get("start_date", "")).strip()
        if driver not in mapping or start >= starts.get(driver, ""):
            mapping[driver] = car_no
            starts[driver] = start
    for row in load_vehicles():
        car_no = str(row.get("car_no", "")).strip()
        driver = str(row.get("driver", "")).strip()
        if driver and car_no and driver not in mapping:
            mapping[driver] = car_no
    return mapping

def car_for_driver(driver, day=""):
    """السيارة المكلَّفة للسائق (تكليفات السائقين أولاً، ثم سجل السيارات)."""
    driver = str(driver or "").strip()
    if not driver:
        return ""
    assigned = assigned_car_for_driver(driver, day)
    if assigned:
        return assigned
    mapping = driver_car_map()
    if driver in mapping:
        return mapping[driver]
    # مطابقة متساهلة كما في driver_type_of: نتجاهل المسافات والتشكيل.
    wanted = _normalized_driver_name(driver)
    for name, car_no in mapping.items():
        if _normalized_driver_name(name) == wanted:
            return car_no
    return ""

def partner_names():
    """قائمة الشركاء المسجلين مرتبة بلا تكرار."""
    return sorted({str(row.get("partner", "")).strip() for row in load_vehicle_partners()
                   if str(row.get("partner", "")).strip()})

def vehicle_driver_for_date(car_no, day):
    from .reports import _periods_overlap
    """Return the driver assigned to a vehicle on a specific date."""
    candidates = [
        row for row in load_vehicle_assignments()
        if str(row.get("car_no", "")).strip() == str(car_no).strip()
        and _periods_overlap(str(day), str(day), row.get("start_date"), row.get("end_date"))
    ]
    candidates.sort(key=lambda row: str(row.get("start_date", "")), reverse=True)
    return str(candidates[0].get("driver", "")).strip() if candidates else ""

def assigned_car_for_driver(driver, day=""):
    from .reports import _periods_overlap
    """السيارة المكلَّفة للسائق من جدول تكليفات السائقين (المرجع المعتمد)."""
    name = _normalized_driver_name(driver)
    if not name:
        return ""
    day = str(day or "").strip()
    candidates = [
        row for row in load_vehicle_assignments()
        if _normalized_driver_name(row.get("driver")) == name
        and (not day or _periods_overlap(day, day, row.get("start_date"), row.get("end_date")))
    ]
    if not candidates and day:
        # عند غياب فترة سارية نستخدم أحدث تكليف مسجل.
        candidates = [row for row in load_vehicle_assignments()
                      if _normalized_driver_name(row.get("driver")) == name]
    if not candidates:
        return ""
    candidates.sort(key=lambda row: str(row.get("start_date", "")), reverse=True)
    return str(candidates[0].get("car_no", "")).strip()

def cars_for_driver(driver, day=""):
    from .reports import _periods_overlap
    """كل السيارات المرتبطة بسائق، لا سيارة واحدة فقط.

    كان حقل «السيارة» يُملأ بسيارة واحدة تُختار من أحدث تكليف، وبقيت قائمته
    تعرض كل السيارات في البرنامج. فكان السائق قد يختار سيارة ليست له. هنا نُعِد
    كل سيارته السارية في الفترة المطلوبة (وكل تكليفاته إن لم تنطبق فترة)،
    ونضيف سيارة سجل السيارات حين لا يوجد تكليف، ثم نختار السيارة الأنسب تلقائياً.
    """
    name = _normalized_driver_name(driver)
    if not name:
        return []
    day = str(day or "").strip()
    rows = load_vehicle_assignments()
    active = [row for row in rows
              if _normalized_driver_name(row.get("driver")) == name
              and (not day or _periods_overlap(day, day, row.get("start_date"),
                                               row.get("end_date")))]
    if not active and day:
        active = [row for row in rows
                  if _normalized_driver_name(row.get("driver")) == name]
    cars, seen = [], set()
    for row in active:
        car_no = str(row.get("car_no", "")).strip()
        if car_no and car_no not in seen:
            seen.add(car_no)
            cars.append(car_no)
    for row in load_vehicles():
        car_no = str(row.get("car_no", "")).strip()
        row_driver = _normalized_driver_name(row.get("driver"))
        if car_no and row_driver == name and car_no not in seen:
            seen.add(car_no)
            cars.append(car_no)
    return cars

# ------------------------------------------------------------------
# العملاء والمخلصون الجمركيون
# ------------------------------------------------------------------
def load_customers():
    from .core import _load_rows
    return _load_rows("customers", "name")

def save_customer(data, editing_name=None):
    from .core import _save_row_by_name
    _save_row_by_name("customers", data, editing_name)

def delete_customer(name):
    from .core import _delete_row
    _delete_row("customers", "name", name)

# ------------------------------------------------------------------
# شركات (CRUD بسيط مشابه للعملاء)
# ------------------------------------------------------------------
def load_companies():
    from .core import _load_rows
    return _load_rows("companies", "name")

def save_company(data, editing_name=None):
    from .core import _save_row_by_name
    _save_row_by_name("companies", data, editing_name)

def delete_company(name):
    from .core import _delete_row
    _delete_row("companies", "name", name)

# ------------------------------------------------------------------
# أماكن التحميل/التفريغ
# ------------------------------------------------------------------
def load_places():
    from .core import _load_rows
    return _load_rows("places", "name")

def load_places_by_type(place_type):
    return [p for p in load_places() if str(p.get("type", "")).strip() == str(place_type)]

def get_places_for_trip_category(category):
    scope = "دولي" if category == TRIP_CATEGORIES[1] else "محلي"
    return [p.get("name", "") for p in load_places_by_type(scope)
            if str(p.get("name", "")).strip()]

def get_places_for_trip_category_and_usage(category, usage):
    """يعيد أماكن التحميل أو التفريغ المناسبة، مع دعم السجلات القديمة."""
    scope = "دولي" if category == TRIP_CATEGORIES[1] else "محلي"
    places = []
    for place in load_places_by_type(scope):
        place_usage = str(place.get("usage", "")).strip()
        if not place_usage or place_usage == "تحميل وتفريغ" or place_usage == usage:
            name = str(place.get("name", "")).strip()
            if name:
                places.append(name)
    return places

def save_place(data, editing_name=None):
    from .core import _save_row_by_name
    if editing_name is not None:
        existing = next((row for row in load_places()
                         if str(row.get("name", "")) == str(editing_name)), None)
        if existing:
            merged = existing.copy()
            merged.update(data)
            data = merged
    _save_row_by_name("places", data, editing_name)

def delete_place(name):
    from .core import _delete_row
    _delete_row("places", "name", name)
