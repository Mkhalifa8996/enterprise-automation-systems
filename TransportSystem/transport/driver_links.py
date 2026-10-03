# -*- coding: utf-8 -*-
"""الربط المتسلسل لحقول السائق: النوع ← السائق ← السيارة."""

from . import data as td
from .ui_helpers import log_exception


# ==================================================================
# ربط متسلسل لحقول السائق: نوع السائق ← السائق ← السيارة
# ==================================================================
DRIVER_LINK_KEYS = ("driver_type", "driver", "car_no")

# عرض قائمة كل حقل في رأس البيان اليومي. «الشركة» و«العميل» أضيق لأن
# الصف يحوي أيضاً زر «حذف البيان» و«مسح الحقول» على اليسار.
_BATCH_HEADER_COMBO_WIDTHS = {"company": 10, "customer": 10, "trip_category": 12}

DRIVER_LINK_LABELS = {
    "driver_type": "نوع السائق",
    "driver": "السائق",
    "car_no": "رقم السيارة",
}

def driver_link_keys_in(fields):
    """مفاتيح الحقول المتسلسلة داخل تعريف شاشة، إن وُجدت كلها."""
    keys = {field[0] for field in fields}
    return DRIVER_LINK_KEYS if set(DRIVER_LINK_KEYS) <= keys else ()

def ensure_driver_link_fields(fields):
    """ترتيب حقول السائق الثلاثة وإكمال الناقص منها في تعريف شاشة.

    المطلوب في كل شاشة فيها أيّ واحد من الحقول الثلاثة: «نوع السائق» ثم
    «السائق» ثم «السيارة». الشاشة التي تحوي «السائق» و«السيارة» بلا نوع
    كانت بلا تصفية، والتي تحوي النوع بلا السائق كانت لا تربط السائق بالسيارة.
    هنا نُكمل النقص ونثبتّها ككتلة واحدة بهذا الترتيب في كل مكان.
    """
    fields = list(fields)
    keys = [key for key, _label in fields]
    present = set(keys)
    if not present.intersection(DRIVER_LINK_KEYS):
        return fields
    # الترتيب ثابت: نوع السائق ← السائق ← السيارة، والثلاثة متجاورة.
    block = [(key, DRIVER_LINK_LABELS[key]) for key in DRIVER_LINK_KEYS]
    # موضع الكتلة = أسبق موقع لأي حقل منها في الشاشة الأصلية.
    positions = [keys.index(key) for key in DRIVER_LINK_KEYS if key in present]
    start = min(positions) if positions else len(keys)
    result = [field for field in fields if field[0] not in DRIVER_LINK_KEYS]
    for offset, field in enumerate(block):
        result.insert(start + offset, field)
    return result

def apply_driver_car_to(vars_map, driver, day=""):
    """يملأ حقل السيارة بالسيارة المكلَّفة بالسائق المختار (بلا مسح اختيار يدوي)."""
    car_var = vars_map.get("car_no")
    if car_var is None:
        return ""
    car_no = td.car_for_driver(driver, day)
    if car_no:
        car_var.set(car_no)
    return car_no

def bind_driver_type_cascade(vars_map, combos_map, get_day=None, on_change=None):
    """يربط «نوع السائق» بقائمة «السائق» ثم «السائق» بقائمة «السيارة».

    - اختيار «داخلي» يعرض أسماء السائقين الداخليين فقط، و«خارجي» يعرض
      الخارجيين فقط، والقائمة الفارغة تعرض الجميع.
    - بعد اختيار السائق لا تبقى في قائمة «السيارة» إلا سيارته هو، فلم يكن
      يختار سائق سيارة غير مكلَّفة به. وتُختار له سيارته تلقائياً إن كانت
      واحدة، وتبقى القائمة فارغة إن كان بلا سيارة.
    - عند حذف السائق تعود قائمة السيارات إلى كل السيارات، لأن التقييد
      بالملكية لم يعد ذا معنى.
    """
    type_var = vars_map.get("driver_type")
    driver_var = vars_map.get("driver")
    if type_var is None or driver_var is None:
        return
    driver_combo = combos_map.get("driver")
    car_combo = combos_map.get("car_no")
    state = {"busy": False}
    all_cars = list(td.load_vehicles()) if car_combo is not None else []

    def _day():
        if callable(get_day):
            try:
                return get_day() or ""
            except Exception as exc:
                log_exception("تحديد يوم تكليف السيارة", exc)
        return ""

    def _all_car_numbers():
        return [str(v.get("car_no", "")).strip() for v in all_cars
                if str(v.get("car_no", "")).strip()]

    def _set_car_values(values):
        if car_combo is None:
            return
        try:
            car_combo.config(values=values)
        except Exception as exc:
            log_exception("تحديث قائمة السيارات", exc)

    def _fill_car(*_args):
        if state["busy"]:
            return
        state["busy"] = True
        try:
            driver = driver_var.get().strip()
            car_var = vars_map.get("car_no")
            if not driver:
                # بلا سائق تعود كل السيارات ولا يُمسح ما اختاره المستخدم: كان
                # الحقل يُفرَّغ هنا، فاختيار السيارة قبل السائق يضيع بلا سبب
                # (وعند تغيير النوع يُفرَّغ السائق فتضيع السيارة معه).
                _set_car_values(_all_car_numbers())
                if car_var is not None:
                    current = car_var.get().strip()
                    if current and current not in _all_car_numbers():
                        car_var.set("")
            else:
                cars = td.cars_for_driver(driver, _day())
                # نحتفظ بالسيارة المختارة إن كانت له فعلاً، وإلا نختار له
                # سيارته المعتمدة، فالخانة لا تبقى على سيارة ليست له.
                current = car_var.get().strip() if car_var is not None else ""
                if current and current in cars:
                    car_var.set(current)
                else:
                    preferred = apply_driver_car_to(vars_map, driver, _day())
                    if car_var is not None and not preferred and cars:
                        car_var.set(cars[0])
                _set_car_values(cars)
        finally:
            state["busy"] = False
        if callable(on_change):
            on_change()

    def _on_type_changed(*_args):
        if state["busy"]:
            return
        state["busy"] = True
        try:
            current = driver_var.get().strip()
            names = td.driver_names_by_type(type_var.get().strip())
            if driver_combo is not None:
                try:
                    driver_combo.config(values=names)
                except Exception as exc:
                    log_exception("تحديث قائمة السائقين", exc)
            # نُبقي السائق المختار إن كان ما زال ضمن القائمة الجديدة، وإلا نفرّغ
            # السائق وحده. كانت السيارة تُفرَّغ معه أيضاً، فتضيع سيارة اختارها
            # المستخدم لمجرد تغيير النوع.
            if current and current in names:
                driver_var.set(current)
            else:
                driver_var.set("")
                _set_car_values(_all_car_numbers())
        finally:
            state["busy"] = False
        _fill_car()

    type_var.trace_add("write", _on_type_changed)
    driver_var.trace_add("write", _fill_car)
    # القيمة الابتدائية قد تكون مضبوطة قبل الربط، لذا نُطبّق الترتيب مرة واحدة.
    _on_type_changed()
