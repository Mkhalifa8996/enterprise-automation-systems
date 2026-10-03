# -*- coding: utf-8 -*-
"""دوال مساعدة عامة: تحويل الأرقام إلى كلمات، وتنسيق الفلس، وتحويل آمن للنصوص."""

# ------------------------------------------------------------------
# تحويل الأعداد إلى كلمات عربية (تُطبع على الفاتورة الورقية)
# ------------------------------------------------------------------
ARABIC_MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                 "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
ARABIC_WEEKDAYS = ["اثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة", "سبت", "أحد"]

ARABIC_UNITS = ["صفر", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة",
                "عشرة", "أحد عشر", "اثنا عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر", "ستة عشر", "سبعة عشر", "ثمانية عشر", "تسعة عشر"]
ARABIC_TENS = {
    20: "عشرون", 30: "ثلاثون", 40: "أربعون", 50: "خمسون", 60: "ستون",
    70: "سبعون", 80: "ثمانون", 90: "تسعون"
}
ARABIC_HUNDREDS = {
    100: "مائة", 200: "مائتان", 300: "ثلاثمائة", 400: "أربعمائة", 500: "خمسمائة",
    600: "ستمائة", 700: "سبعمائة", 800: "ثمانمائة", 900: "تسعمائة"
}


def arabic_int_to_words(n):
    if n < 0:
        return "سالب " + arabic_int_to_words(-n)
    if n < 20:
        return ARABIC_UNITS[n]
    if n < 100:
        if n in ARABIC_TENS:
            return ARABIC_TENS[n]
        unit = n % 10
        tens = n - unit
        return f"{ARABIC_UNITS[unit]} و {ARABIC_TENS[tens]}"
    if n < 1000:
        if n in ARABIC_HUNDREDS:
            return ARABIC_HUNDREDS[n]
        hundreds = n - (n % 100)
        remainder = n % 100
        return f"{ARABIC_HUNDREDS[hundreds]} و {arabic_int_to_words(remainder)}"
    if n < 1000000:
        thousands = n // 1000
        remainder = n % 1000
        if thousands == 1:
            prefix = "ألف"
        elif thousands == 2:
            prefix = "ألفان"
        elif 3 <= thousands <= 10:
            prefix = f"{arabic_int_to_words(thousands)} آلاف"
        else:
            prefix = f"{arabic_int_to_words(thousands)} ألف"
        return f"{prefix} و {arabic_int_to_words(remainder)}" if remainder else prefix
    if n < 1000000000:
        millions = n // 1000000
        remainder = n % 1000000
        if millions == 1:
            prefix = "مليون"
        elif millions == 2:
            prefix = "مليونان"
        elif 3 <= millions <= 10:
            prefix = f"{arabic_int_to_words(millions)} ملايين"
        else:
            prefix = f"{arabic_int_to_words(millions)} مليون"
        return f"{prefix} و {arabic_int_to_words(remainder)}" if remainder else prefix
    return str(n)


def arabic_currency_words(amount):
    try:
        total_fils = round(float(amount) * 1000)
    except (TypeError, ValueError):
        return ""
    dinars = total_fils // 1000
    fils = total_fils % 1000
    if dinars == 0 and fils == 0:
        return "صفر دينار كويتي فقط لا غير"
    parts = []
    if dinars:
        parts.append(f"{arabic_int_to_words(dinars)} دينار كويتي")
    if fils:
        parts.append(f"{arabic_int_to_words(fils)} فلساً")
    return " و ".join(parts) + " فقط لا غير"


# ------------------------------------------------------------------
# تحويل الأعداد إلى كلمات إنجليزية (تظهر في الترويسة الإنجليزية للفاتورة)
# ------------------------------------------------------------------
_EN_ONES = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
            'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
            'seventeen', 'eighteen', 'nineteen']
_EN_TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']


def english_int_to_words(n):
    """Convert integer n (0..999999999) to English words (simple)."""

    def _under_thousand(num):
        if num < 20:
            return _EN_ONES[num]
        if num < 100:
            t = num // 10
            r = num % 10
            return _EN_TENS[t] + ('' if r == 0 else ' ' + _EN_ONES[r])
        h = num // 100
        r = num % 100
        return _EN_ONES[h] + ' hundred' + ('' if r == 0 else ' ' + _under_thousand(r))

    if n < 0:
        return 'minus ' + english_int_to_words(-n)
    if n < 1000:
        return _under_thousand(n)
    if n < 1000000:
        thousands = n // 1000
        remainder = n % 1000
        prefix = _under_thousand(thousands) + ' thousand'
        return prefix + ('' if remainder == 0 else ' ' + _under_thousand(remainder))
    millions = n // 1000000
    remainder = n % 1000000
    prefix = _under_thousand(millions) + ' million'
    return prefix + ('' if remainder == 0 else ' ' + english_int_to_words(remainder))


def english_currency_words(amount):
    try:
        total_fils = round(float(amount) * 1000)
    except (TypeError, ValueError):
        return ""
    dinars = total_fils // 1000
    fils = total_fils % 1000
    if dinars == 0 and fils == 0:
        return 'zero Kuwaiti dinars only'
    parts = []
    if dinars:
        parts.append(f"{english_int_to_words(dinars)} Kuwaiti dinar{'s' if dinars != 1 else ''}")
    if fils:
        parts.append(f"{english_int_to_words(fils)} fils")
    return ' and '.join(parts) + ' only'


def fmt_fils3(v):
    """يعرض مبلغ الفلس بصيغة ثلاث خانات (مثل 050)."""
    if v in (None, ""):
        return ""
    try:
        return f"{int(v):03d}"
    except (TypeError, ValueError):
        return str(v)


# ------------------------------------------------------------------
# تحويلات آمنة للنصوص والأرقام
# ------------------------------------------------------------------
def safe_int(v):
    try:
        if v in (None, ""):
            return 0
        return int(round(float(v)))
    except (ValueError, TypeError):
        return 0


def safe_float(v):
    try:
        if v in (None, ""):
            return 0.0
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def safe_str(v):
    """يحوّل أي قيمة إلى نص نظيف بلا 'None' ولا مسافات زائدة."""
    if v is None:
        return ""
    return str(v).strip()


def normalize_company_code(v):
    """يحوّل رمز الشركة إلى رقمين (01-99) كنص، أو '' إن كان غير صالح/فارغ.

    دالة خالصة بلا حالة، فتصلح للاستخدام من أي طبقة دون استيراد دوري.
    """
    if v in (None, ""):
        return ""
    try:
        n = int(str(v).strip())
    except (ValueError, TypeError):
        return ""
    if n < 1 or n > 99:
        return ""
    return f"{n:02d}"