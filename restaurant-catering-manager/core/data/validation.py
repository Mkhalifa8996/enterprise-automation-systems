# -*- coding: utf-8 -*-
"""
core.data.validation — أدوات التحقق وتحويل القيم (بلا اعتماد على محرك التخزين).

كل دوالها ترجع False أو قيمة آمنة بدل رفع استثناء، لأن طبقة البيانات تُستدعى من
شاشات يُدخل فيها المستخدم نصاً حراً؛ فالهدف منع البيانات الفاسدة من التسرب إلى
التقارير بدل إيقاف البرنامج.
"""

import json
from datetime import date, datetime, timedelta


def safe_float(v):
    """رقم عشري مقرَّب لثلاث خانات، و0.000 عند أي قيمة غير صالحة."""
    try:
        if v in (None, ""):
            return 0.0
        return round(float(v), 3)
    except (ValueError, TypeError):
        return 0.0


def safe_int(v):
    """عدد صحيح، و0 عند أي قيمة غير صالحة."""
    try:
        if v in (None, ""):
            return 0
        return int(float(v))
    except (ValueError, TypeError):
        return 0


def is_iso_date(value):
    """التحقق من صيغة التاريخ YYYY-MM-DD (تعود False عند أي خلل بدل رفع استثناء)."""
    text = str(value or "").strip()
    if not text:
        return False
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_month(value):
    """التحقق من صيغة الشهر YYYY-MM."""
    text = str(value or "").strip()
    if not text:
        return False
    try:
        datetime.strptime(text, "%Y-%m")
        return True
    except ValueError:
        return False


def month_bounds(month_value):
    """
    يعيد (أول يوم, آخر يوم) لشهر بصيغة YYYY-MM على شكل YYYY-MM-DD، أو
    (None, None) إذا كانت القيمة غير صالحة. تُستخدم لاحتساب الرواتب والمصاريف
    الشهرية عند تقاطع الفترة مع الشهر.
    """
    text = str(month_value or "").strip()
    if not is_month(text):
        return None, None
    year, month = int(text[:4]), int(text[5:7])
    first = date(year, month, 1)
    last = date(year + (month == 12), (month % 12) + 1, 1) - timedelta(days=1)
    return first.isoformat(), last.isoformat()


def invoice_items(inv):
    """يقرأ بنود الفاتورة المخزّنة بصيغة JSON بأمان (قائمة فارغة عند أي تلف)."""
    raw = inv.get("items_json") if isinstance(inv, dict) else None
    if not raw:
        return []
    try:
        items = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return items if isinstance(items, list) else []
