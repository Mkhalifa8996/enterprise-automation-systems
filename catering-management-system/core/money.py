# -*- coding: utf-8 -*-
"""
core.money — الحسابات النقدية بدقة عشرية (Decimal) بدل أرقام الفاصلة العائمة.

الدينار الكويتي له 3 منازل عشرية، و`float` يُدخل أخطاء تقريب (0.1+0.2 != 0.3)
تتراكم في التقارير. كل دوال هذه الوحدة تعمل على Decimal وتُرجع قيماً جاهزة
للعرض أو للتخزين.
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

# دقة المبالغ النقدية: 3 منازل عشرية (فلس = 0.001 د.ك)
CENT = Decimal("0.001")
ZERO = Decimal("0.000")


def D(value, default=ZERO):
    """
    يحوّل أي قيمة (نص / عدد / None) إلى Decimal دون أخطاء التقريب.
    القيم غير القابلة للتحويل تعيد default (بنفس روح safe_float الحالية).
    """
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    try:
        text = str(value).strip().replace("٬", "").replace("،", "")
        if text == "":
            return Decimal(default)
        return Decimal(text)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def money(value):
    """Decimal مقدّر لأقرب 0.001 مع تقريب نصف-لأعلى (العادة المحاسبية)."""
    return D(value).quantize(CENT, rounding=ROUND_HALF_UP)


def to_float(value):
    """float جاهز للتخزين في Excel/SQLite بعد التقريب الصحيح."""
    return float(money(value))


def fmt(value, ndigits=3):
    """نص جاهز للعرض: 3 منازل دائماً، بلا أنماط علمية."""
    return ("%." + str(ndigits) + "f") % float(money(value))


def mul(a, b):
    """ضرب كمية × سعر مع التقريب الصحيح."""
    return money(D(a) * D(b))


def add(*values):
    """جمع مبالغ بدون انزياح الفاصلة العائمة."""
    total = ZERO
    for v in values:
        total += D(v)
    return total.quantize(CENT, rounding=ROUND_HALF_UP)


def sub(a, b):
    return money(D(a) - D(b))
