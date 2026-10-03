# -*- coding: utf-8 -*-
"""تعريف الأعمدة وقوائم الاختيار لكل جدول في قاعدة البيانات."""

from openpyxl.styles import Font
from openpyxl.styles import PatternFill

SHEETS = {
    "drivers": "السائقون",
    "vehicles": "السيارات",
    "maintenance": "صيانة السيارات",
    "customers": "العملاء والمخلصون",
    "companies": "الشركات",
    "places": "أماكن التحميل والتفريغ",
    "daily_expenses": "المصاريف اليومية",
    "trips": "الرحلات اليومية",
    "services": "الخدمات الإضافية",
    "invoices": "الفواتير",
    "payments": "دفعات العملاء",
    "salaries": "الرواتب",
    "vehicle_assignments": "تكليفات السيارات",
    "vehicle_partners": "شركاء السيارات",
    "partner_payments": "دفعات الشركاء",
    "driver_payments": "دفعات السائقين",
    "cash_ledger": "دفتر النقد والبنك",
    "fuel": "الديزل (سجل التزود)",
    "contracts": "العقود",
    "quotations": "عروض الأسعار",
    "maintenance_plans": "جدولة الصيانة",
    "parts": "قطع الغيار والإطارات",
    "vehicle_setup_expenses": "مصاريف تجهيز السيارات",
}

# ------------------------------------------------------------------
# تعريف الأعمدة لكل جدول: (المفتاح البرمجي, التسمية المعروضة بالعربي)
# ------------------------------------------------------------------
DRIVER_FIELDS = [
    ("name", "اسم السائق"),
    ("national_id", "الهوية"),
    ("license_no", "رقم رخصة القيادة"),
    ("phone", "الهاتف"),
    ("driver_type", "نوع السائق"),
    ("car_no", "رقم السيارة المخصصة"),
    ("base_salary", "الراتب الأساسي الشهري"),
    ("commission_per_trip", "عمولة كل رحلة"),
    ("notes", "ملاحظات"),
]

VEHICLE_WORK_TYPES = ["شحن داخلي (ميناء)", "شحن دولي (بري)", "داخلي ودولي معاً"]

VEHICLE_FIELDS = [
    ("car_no", "رقم السيارة / اللوحة"),
    ("model", "النوع / الموديل"),
    ("year", "سنة الصنع"),
    ("driver", "السائق المخصص"),
    ("work_type", "نوع العمل"),
    ("has_generator", "يحتوي على مولد؟"),
    ("is_flatbed", "ساطحة؟"),
    ("flatbed_type", "نوع الساطحة"),
    ("contents", "محتويات السيارة"),
    ("license_expiry", "تاريخ انتهاء الترخيص"),
    ("notes", "ملاحظات"),
]

VEHICLE_ASSIGNMENT_FIELDS = [
    ("id", "الرقم"),
    ("car_no", "رقم السيارة"),
    ("driver", "السائق"),
    ("start_date", "من تاريخ"),
    ("end_date", "إلى تاريخ"),
    ("notes", "ملاحظات"),
]

VEHICLE_PARTNER_FIELDS = [
    ("id", "الرقم"),
    ("car_no", "رقم السيارة"),
    ("partner", "اسم الشريك"),
    ("ownership_pct", "نسبة الشريك %"),
    ("start_date", "من تاريخ"),
    ("end_date", "إلى تاريخ"),
    ("locked", "النسبة مثبتة"),
    ("notes", "ملاحظات"),
]

PARTNER_SHARE_OPTIONS = ["ربع الإيراد (25%)", "ثلث الإيراد (33.333%)",
                         "نصف الإيراد (50%)", "كامل الإيراد (100%)"]

# أنواع الدفعات على حساب الشريك: «مدين» حركات تُحمَّل على حسابه (دفعة له)
# و«دائن» حركات تُقيَّد لصالح حسابه (نصيبه من الإيراد أو استرداد).
PAYMENT_TYPES = ["مدين", "دائن"]

PARTNER_PAYMENT_FIELDS = [
    ("id", "الرقم"),
    ("date", "التاريخ"),
    ("partner", "اسم الشريك"),
    ("car_no", "رقم السيارة"),
    ("payment_type", "نوع الدفعة"),
    ("amount", "المبلغ (د.ك)"),
    ("voided", "مشطوبة"),
    ("void_reason", "سبب الإشطب"),
    ("notes", "ملاحظات"),
]

DRIVER_PAYMENT_FIELDS = [
    ("id", "الرقم"),
    ("date", "التاريخ"),
    # الترتيب المطلوب: نوع السائق ← السائق ← السيارة.
    ("driver_type", "نوع السائق"),
    ("driver", "اسم السائق"),
    ("car_no", "رقم السيارة"),
    ("payment_type", "نوع الدفعة"),
    ("amount", "المبلغ (د.ك)"),
    ("voided", "مشطوبة"),
    ("void_reason", "سبب الإشطب"),
    ("notes", "ملاحظات"),
]

DRIVER_TYPES = ["داخلي", "خارجي"]

# حالات الإشطب: الدفعات المسجّلة لا تُحذف نهائياً حتى لا تختفي من كشوف
# مُسلَّمة سابقاً، بل تُعلَّم «مشطوبة» وتُستبعد من أرصدة الحسابات.
VOID_STATUSES = ["سليمة", "مشطوبة"]

def partner_share_percentage(value):
    """Convert the friendly partner share labels to their numeric percentage."""
    labels = {
        "ربع الإيراد (25%)": 25.0,
        "ثلث الإيراد (33.333%)": round(100.0 / 3.0, 3),
        "نصف الإيراد (50%)": 50.0,
        "كامل الإيراد (100%)": 100.0,
        "الربع": 25.0,
        "الثلث": round(100.0 / 3.0, 3),
        "النصف": 50.0,
        "الإيراد كامل": 100.0,
    }
    return labels.get(str(value or "").strip(), safe_float(value))

MAINTENANCE_TYPES = ["زيت", "بنزين / ديزل", "إطارات", "صيانة عامة", "أخرى"]

MAINTENANCE_FIELDS = [
    ("id", "الرقم"),
    ("date", "التاريخ"),
    ("car_no", "رقم السيارة"),
    ("type", "النوع"),
    ("cost", "التكلفة (د.ك)"),
    ("notes", "ملاحظات"),
]

CUSTOMER_FIELDS = [
    ("name", "الاسم"),
    ("phone", "الهاتف"),
    ("address", "العنوان"),
    ("notes", "ملاحظات"),
]

# ------------------------------------------------------------------
# الشركات (قائمة منفصلة لتسهيل إضافة شركات مستقلة عن العملاء)
# ------------------------------------------------------------------
COMPANY_FIELDS = [
    ("name", "اسم الشركة"),
    ("customs_broker", "المخلص الجمركي"),
    ("phone", "الهاتف"),
    ("address", "العنوان"),
    ("notes", "ملاحظات"),
]

# ------------------------------------------------------------------
# أماكن التحميل والتنزيل (محلي/دولي)
# ------------------------------------------------------------------
PLACES_FIELDS = [
    ("name", "الاسم"),
    ("type", "النوع (محلي/دولي)"),
    ("usage", "الاستخدام (تحميل/تفريغ/كلاهما)"),
]

PLACE_USAGES = ["تحميل", "تفريغ", "تحميل وتفريغ"]

TRANSACTION_TYPES = ["تحميل", "تنزيل"]

# سجل مستقل يسمح بتسجيل أكثر من مصروف لكل سيارة أو سائق في اليوم.
DAILY_EXPENSE_CATEGORIES = [
    "مخالفة سيارة", "مخالفة سائق", "زجاج أمامي", "إطارات السيارة",
    "صيانة كهرباء", "صيانة تكييف", "بطارية السيارة", "صيانة عامة",
    "بطارية المولد", "صيانة المولد", "ديزل السيارة", "ديزل المولد",
    "زيت السيارة", "زيت المولد", "لحام السيارة", "لحام المولد", "أخرى",
]

VEHICLE_EXPENSE_CATEGORIES = [c for c in DAILY_EXPENSE_CATEGORIES if c != "مخالفة سائق"]

DRIVER_EXPENSE_CATEGORIES = ["مخالفة سائق", "مصروف سائق", "خصم سائق", "أخرى"]

VEHICLE_EXPENSE_GROUPS = {
    "زيت وديزل": ["ديزل السيارة", "زيت السيارة", "ديزل المولد", "زيت المولد"],
    "صيانة سيارة": ["زجاج أمامي", "إطارات السيارة", "صيانة كهرباء", "صيانة تكييف",
                     "بطارية السيارة", "صيانة عامة", "لحام السيارة", "أخرى"],
    "صيانة مولد": ["بطارية المولد", "صيانة المولد", "لحام المولد", "أخرى"],
    "مخالفات سيارة": ["مخالفة سيارة"],
}

DAILY_EXPENSE_FIELDS = [
    ("id", "الرقم"),
    ("date", "التاريخ"),
    # ثلاثية السائق بترتيبها: نوع السائق ← السائق ← السيارة.
    ("driver_type", "نوع السائق"),
    ("car_no", "رقم السيارة"),
    ("driver", "السائق"),
    ("category", "نوع المصروف"),
    ("amount", "المبلغ (د.ك)"),
    ("driver_advance", "سلفة للسائق (د.ك)"),
    ("expense_owner", "جهة المصروف"),
    ("description", "التفاصيل / السبب"),
]

# ------------------------------------------------------------------
# مصاريف تجهيز السيارة قبل بدء العمل الفعلي
# ------------------------------------------------------------------
# هذه المصاريف تُسجَّل مرة واحدة عند تجهيز السيارة (شراءها أو شراء ساطحتها
# أو مولدها) وصيانتها قبل أول رحلة، وتختلف عن «المصاريف اليومية» التي
# تتكرر مع كل يوم عمل بعد بدء التشغيل.
VEHICLE_SETUP_CATEGORIES = [
    "ثمن شراء السيارة",
    "ثمن شراء الساطحة",
    "ثمن شراء المولد",
    "صيانة المولد",
    "صيانة السيارة",
    "صيانة الساطحة",
    "أخرى",
]

# تصنيف كل بند إلى جهته: السيارة نفسها أو أحد تجهيزاتها.
VEHICLE_SETUP_TARGETS = {
    "ثمن شراء السيارة": "سيارة",
    "ثمن شراء الساطحة": "ساطحة",
    "ثمن شراء المولد": "مولد",
    "صيانة المولد": "مولد",
    "صيانة السيارة": "سيارة",
    "صيانة الساطحة": "ساطحة",
    "أخرى": "سيارة",
}

VEHICLE_SETUP_FIELDS = [
    ("id", "الرقم"),
    ("date", "التاريخ"),
    ("car_no", "رقم السيارة"),
    ("category", "بند التجهيز"),
    ("setup_target", "الجهة"),
    ("amount", "المبلغ (د.ك)"),
    ("description", "التفاصيل / السبب"),
]

# نوع الرحلة: شحن داخلي (بين الميناء ومكان العميل) أو شحن دولي بري (بين الكويت ودولة أخرى)
TRIP_CATEGORIES = ["شحن داخلي (ميناء)", "شحن دولي (بري)", "ضرب فله"]

# اتجاهات الشحن الداخلي: من/إلى الميناء
INTERNAL_DIRECTIONS = ["من الميناء إلى العميل", "من العميل إلى الميناء"]

# اتجاهات الشحن الدولي البري: من/إلى الكويت
INTERNATIONAL_DIRECTIONS = ["من الكويت إلى الخارج", "من الخارج إلى الكويت"]

DIRECTIONS_BY_CATEGORY = {
    TRIP_CATEGORIES[0]: INTERNAL_DIRECTIONS,
    TRIP_CATEGORIES[1]: INTERNATIONAL_DIRECTIONS,
    TRIP_CATEGORIES[2]: INTERNAL_DIRECTIONS,
}

TRIP_FIELDS = [
    ("id", "الرقم"),
    ("declaration_trip_no", "كود الرحلة"),
    ("date", "التاريخ"),
    ("trip_category", "نوع الشحن"),
    ("direction", "مكان التحميل"),
    # الترتيب المطلوب: نوع السائق ← السائق ← السيارة.
    ("driver_type", "نوع السائق"),
    ("driver", "السائق"),
    ("car_no", "رقم السيارة"),
    ("customer", "الشركة / العميل"),
    ("origin", "من (نقطة الانطلاق)"),
    ("destination", "إلى (الوجهة)"),
    ("country", "مكان التنزيل"),
    ("container_size", "حجم الحاوية"),
    ("declaration_no", "رقم البيان"),
    ("car_expense_type", "نوع مصاريف السيارة"),
    ("car_expense_amount", "مصاريف السيارة (د.ك)"),
    ("driver_expense", "مصاريف السائق (د.ك)"),
    ("transaction_type", "نوع المعاملة"),
    ("movement_name", "اسم الحركة"),
    ("hour", "الساعة"),
    ("agent_code", "الرمز / المندوب"),
    ("fee", "المبلغ المستحق على العميل (د.ك)"),
    ("holiday_price", "سعر العطلة (د.ك)"),
    ("driver_commission", "عمولة السائق (د.ك)"),
    ("driver_wage", "أجرة السائق (د.ك)"),
    ("invoiced", "مفوترة؟"),
    ("invoice_no", "رقم الفاتورة"),
    ("company", "الشركة"),
    ("notes", "ملاحظات"),
]

SERVICE_TYPES = ["عمال", "رافعة شوكية", "كرين", "كرين خرسانة", "غسيل حاوية", "أخرى"]

SERVICE_FIELDS = [
    ("declaration_no", "\u0631\u0642\u0645 \u0627\u0644\u0628\u064a\u0627\u0646"),
    ("declaration_trip_no", "\u0623\u0643\u0648\u0627\u062f \u0627\u0644\u0631\u062d\u0644\u0627\u062a"),
    ("id", "الرقم"),
    ("date", "التاريخ"),
    ("company", "الشركة"),
    ("customer", "الشركة / المخلص"),
    ("unit", "الوحدة"),
    ("service_type", "نوع الخدمة"),
    ("quantity", "الكمية / الساعات"),
    ("unit_price", "سعر الوحدة (د.ك)"),
    ("total", "الإجمالي (د.ك)"),
    ("invoiced", "مفوترة؟"),
    ("invoice_no", "رقم الفاتورة"),
    ("notes", "ملاحظات"),
    ("trip_ids", "الرحلات المرتبطة"),
    ("record_type", "نوع السجل"),
]

# يجب أن يبقى المعرّف أول عمود لأن عمليات التعديل والحذف تعتمد عليه.
_service_fields_by_key = {field[0]: field for field in SERVICE_FIELDS}

SERVICE_FIELDS = [_service_fields_by_key[key] for key in (
    "id", "date", "company", "customer", "declaration_no",
    "declaration_trip_no", "unit", "service_type", "quantity",
    "unit_price", "total", "invoiced", "invoice_no", "notes",
    "trip_ids", "record_type")]

INVOICE_FIELDS = [
    ("invoice_no", "رقم الفاتورة"),
    ("date", "التاريخ"),
    ("customer", "العميل"),
    ("paid", "حالة السداد"),
    ("awb_no", "رقم بوليصة الشحن"),
    ("container_count", "عدد الحاويات"),
    ("items_json", "بنود الفاتورة (JSON)"),
    ("total", "الإجمالي (د.ك)"),
    ("declaration_no", "رقم البيان الجمركي"),
    ("notes", "ملاحظات"),
]

# الدفعة حركة دائنة في حساب العميل/المخلص. يمكن ربطها بفاتورة عند الحاجة
# أو تركها كدفعة عامة على الحساب.
PAYMENT_FIELDS = [
    ("id", "الرقم"),
    ("date", "التاريخ"),
    ("customer", "العميل / المخلص"),
    ("amount", "المبلغ (د.ك)"),
    ("reference", "رقم السند / المرجع"),
    ("invoice_no", "البيان / الفاتورة المرتبطة (اختياري للدفعة العامة)"),
    ("notes", "ملاحظات"),
]

CASH_LEDGER_TYPES = ["قبض", "صرف"]

CASH_LEDGER_ACCOUNTS = ["نقدي", "بنك"]

CASH_LEDGER_FIELDS = [
    ("id", "الرقم"),
    ("date", "التاريخ"),
    ("transaction_type", "نوع الحركة"),
    ("account", "الحساب"),
    ("category", "البند"),
    ("party", "الطرف"),
    ("amount", "المبلغ (د.ك)"),
    ("reference", "المرجع"),
    ("notes", "ملاحظات"),
]

FUEL_FIELDS = [
    ("id", "الرقم"), ("date", "التاريخ"), ("car_no", "رقم السيارة"),
    ("driver", "السائق"), ("odometer", "عداد الكيلومترات"),
    ("liters", "اللترات"), ("price_per_liter", "سعر اللتر"),
    ("total", "الإجمالي"), ("station", "محطة الوقود"), ("notes", "ملاحظات"),
]

CONTRACT_FIELDS = [
    ("id", "الرقم"), ("contract_no", "رقم العقد"), ("party", "الطرف"),
    ("contract_type", "نوع العقد"), ("start_date", "من تاريخ"),
    ("end_date", "إلى تاريخ"), ("value", "قيمة العقد"), ("status", "الحالة"),
    ("notes", "ملاحظات"),
]

QUOTATION_FIELDS = [
    ("id", "الرقم"), ("quotation_no", "رقم العرض"), ("date", "التاريخ"),
    ("customer", "الشركة / العميل"), ("description", "موضوع العرض"),
    ("amount", "القيمة التقديرية"), ("status", "الحالة"),
    ("invoice_no", "الفاتورة الناتجة"), ("notes", "ملاحظات"),
]

MAINTENANCE_PLAN_FIELDS = [
    ("id", "الرقم"), ("car_no", "رقم السيارة"), ("service_type", "نوع الصيانة"),
    ("due_date", "تاريخ الاستحقاق"), ("due_odometer", "العداد المستحق"),
    ("interval_km", "الفاصل بالكيلومتر"), ("status", "الحالة"), ("notes", "ملاحظات"),
]

PART_FIELDS = [
    ("id", "الرقم"), ("car_no", "رقم السيارة"), ("part_type", "النوع"),
    ("part_name", "اسم القطعة"), ("serial_no", "الرقم التسلسلي"),
    ("install_date", "تاريخ التركيب"), ("expiry_date", "تاريخ الاستبدال"),
    ("cost", "التكلفة"), ("notes", "ملاحظات"),
]

SALARY_TYPES = ["شهري", "رحلة", "إيراد السيارة"]

REVENUE_SALARY_TYPE = "إيراد السيارة"

# كل طرق الحساب المعروضة في شاشة الرواتب، بشرح مختصر يعرض للمستخدم.
# الترتيب: الأنواع الأساسية أولاً ثم صيغ 조합 بين الراتب وحصة الإيراد.
SALARY_METHODS = [
    ("شهري", "الراتب الأساسي الشهري بعد خصم مصاريف السائق والمرحّل"),
    ("رحلة", "أجرة السائق المدوّنة على كل رحلة"),
    (REVENUE_SALARY_TYPE, "نصيب السائق من إيراد السيارة بعد خصم المصاريف المتفق عليها"),
    ("الراتب الأساسي فقط", "الراتب الأساسي الشهري فقط بلا حصة"),
    ("ربع إيراد السيارة", "ربع صافي إيراد السيارة بعد خصم المصاريف"),
    ("ثلث إيراد السيارة", "ثلث صافي إيراد السيارة بعد خصم المصاريف"),
    ("نصف إيراد السيارة", "نصف صافي إيراد السيارة بعد خصم المصاريف"),
    ("راتب + ربع إيراد السيارة", "الراتب الأساسي + ربع صافي إيراد السيارة"),
    ("راتب + ثلث إيراد السيارة", "الراتب الأساسي + ثلث صافي إيراد السيارة"),
    ("راتب + نصف إيراد السيارة", "الراتب الأساسي + نصف صافي إيراد السيارة"),
    ("راتب + ايراد السيارة", "الراتب الأساسي + كامل صافي إيراد السيارة"),
]

SALARY_METHOD_LABELS = [name for name, _desc in SALARY_METHODS]

SALARY_METHOD_DESCRIPTIONS = dict(SALARY_METHODS)

# صيغ حصة الإيراد: المفتاح = طريقة الحساب، والقيمة = كسر الإيراد المستحق للسائق.
SALARY_REVENUE_FRACTIONS = {
    "ربع إيراد السيارة": 0.25,
    "ثلث إيراد السيارة": 0.333,
    "نصف إيراد السيارة": 0.5,
    "راتب + ربع إيراد السيارة": 0.25,
    "راتب + ثلث إيراد السيارة": 0.333,
    "راتب + نصف إيراد السيارة": 0.5,
    "راتب + ايراد السيارة": 1.0,
    REVENUE_SALARY_TYPE: 1.0,
}

# قواعد الرواتب المتفق عليها للسائقين العاملين بنظام إيراد السيارة.
FIXED_PLUS_REVENUE_DRIVERS = {"جمعة", "جمعه", "جمه", "محمدعبدالله", "محمدحسن"}

REVENUE_AFTER_DIESEL_DRIVERS = {"صابر", "ناصر", "وليد"}

SALARY_FIELDS = [
    ("id", "الرقم"),
    ("driver", "السائق"),
    ("car_no", "رقم السيارة"),
    ("month", "الشهر (YYYY-MM)"),
    ("salary_type", "طريقة الحساب"),
    ("base_salary", "الراتب الأساسي"),
    ("trip_revenue", "إيراد الرحلات"),
    ("holiday_revenue", "إيراد العطل"),
    ("driver_wages", "أجرة الرحلات"),
    ("car_expenses", "مصاريف السيارة"),
    ("driver_expenses", "مصاريف السائق"),
    # الرصيد الذي جاء مع الراتب من رواتب سابقة: موجب له وسالب عليه.
    ("carry_in", "مرحّل من الشهر السابق (د.ك)"),
    ("net_salary", "الصافي (د.ك)"),
    ("balance_state", "حالة الرصيد"),
    # فترة الراتب المحسوب: نحفظها لنعرف أي الرحلات والمصاريف استُعملت
    # سابقاً، فلا تدخل في راتب جديد لنفس السائق في الفترة نفسها.
    ("period_from", "من تاريخ الفترة"),
    ("period_to", "إلى تاريخ الفترة"),
    # ما سُدّد فعلياً من هذا الراتب، والفرق بينه والصافي يُرحَّل للشهر التالي.
    ("settled_amount", "المسدّد (د.ك)"),
    ("carry_forward", "المرحّل للشهر التالي"),
    ("paid", "مدفوع؟"),
    ("notes", "ملاحظات"),
]

HEADER_FILL = PatternFill(start_color="0F2B46", end_color="0F2B46", fill_type="solid")

HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF")

# ------------------------------------------------------------------
# أدوات مساعدة عامة
# ------------------------------------------------------------------
def safe_float(v):
    try:
        if v in (None, ""):
            return 0.0
        return round(float(v), 3)
    except (ValueError, TypeError):
        return 0.0

def safe_int(v):
    try:
        if v in (None, ""):
            return 0
        return int(float(v))
    except (ValueError, TypeError):
        return 0

INVOICE_STANDARD_ITEMS = [
    "CUSTOMS CHARGES — رسوم جمارك",
    "MUNICIPAL CLEARANCE CHARGES — أجور تخليص بلدية", "INSPECTION CHARGES — أجور كشف",
    "LEGALIZATION DUTIES & CHARGES — أجور ورسوم تصديق", "AGENT CHARGES — أجور أرضيات وكيل",
    "HARBOR FLOORING CHARGES — أجور أرضيات ميناء", "RELEASE CHARGES — أجور إفراجات",
    "ENVIRONMENTAL RELEASE CHARGES — أجور إفراج بيئة", "AGRICULTURAL RELEASE CHARGES — أجور إفراج زراعة",
    "CLEARANCE CHARGES — أجور تخليص", "TRANSPORTATION CHARGES — أجور نقل",
    "FORKLIFT CHARGES — رافعة شوكية", "CRANE CHARGES — كرين",
    "CONCRETE CRANE CHARGES — كرين خرسانة", "CONTAINER WASHING CHARGES — غسيل حاوية",
    "LABOUR CHARGES — أجور عمال",
    "DELAYED TRUCK CHARGES — تأخير شاحنة", "OTHER CHARGES — مصاريف أخرى",
]

DISABLED_INVOICE_ITEM_KEYS = {
    "DELIVERY ORDER", "RECEIPT CHARGES", "BANK COMMISSION", "INSPECTION CHARGES",
    "إذن تسليم", "أجور استلام", "عمولة بنك", "أجور كشف",
}

SERVICE_INVOICE_ITEMS = {
    "رافعة شوكية": "FORKLIFT CHARGES — رافعة شوكية",
    "كرين": "CRANE CHARGES — كرين",
    "كرين خرسانة": "CONCRETE CRANE CHARGES — كرين خرسانة",
    "غسيل حاوية": "CONTAINER WASHING CHARGES — غسيل حاوية",
    "عمال": "LABOUR CHARGES — أجور عمال",
}

def _normalized_driver_name(name):
    """Match salary rules even when the name contains spaces or tashkeel."""
    return "".join(char for char in str(name or "").strip()
                   if not char.isspace() and char not in "ـًٌٍَُِّْ")
