# -*- coding: utf-8 -*-
"""دوال مساعدة عامة صغيرة تُستخدم في كل الشاشات."""

import os, sys, traceback
from datetime import datetime
from . import data as td


def safe_str(v):
    return "" if v is None else str(v)

def _split_multiselect(value):
    """تفكيك القيمة المخزنة لحقل متعدد الاختيار (مثل محتويات السيارة) إلى خيارات."""
    text = safe_str(value).replace(",", "،")
    return [part.strip() for part in text.split("،") if part.strip()]

def _join_multiselect(options):
    """دمج خيارات حقل متعدد الاختيار في قيمة واحدة تُخزن بشكل سليم."""
    return "، ".join(sorted({str(option).strip() for option in options if str(option).strip()}))

def get_trip_place_options(trip_category):
    return td.get_places_for_trip_category(trip_category)

def is_international_trip_category(category):
    return category == td.TRIP_CATEGORIES[1]

# سجل أخطاء التطبيق: يمنع ابتلاع الاستثناءات بصمت في المواضع الحرجة.
ERROR_LOG_FILE = os.path.join(td.APP_DIR, "app_errors.log")

_ERROR_LOG_MAX_BYTES = 512 * 1024

def log_exception(context, exc=None):
    """تسجيل استثناء مع سياقه بدل ابتلاعه، مع تدوير الملف عند حجمه."""
    if exc is None:
        exc = sys.exc_info()[1]
    if exc is None:
        return ""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {context}: {type(exc).__name__}: {exc}"
    try:
        # نُبقي آخر سجل فقط حتى لا يتضخّم المجلد.
        if (os.path.isfile(ERROR_LOG_FILE)
                and os.path.getsize(ERROR_LOG_FILE) > _ERROR_LOG_MAX_BYTES):
            os.replace(ERROR_LOG_FILE, ERROR_LOG_FILE + ".1")
    except OSError as _log_exc: log_exception("log_exception", _log_exc)
    try:
        trace = traceback.format_exc()
        detail = trace if "NoneType: None" not in trace else ""
        with open(ERROR_LOG_FILE, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            if detail:
                handle.write(detail)
    except OSError as _log_exc: log_exception("log_exception", _log_exc)
    print(f"[ERROR] {line}")
    return line
