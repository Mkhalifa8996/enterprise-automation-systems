# -*- coding: utf-8 -*-
"""
core.data.config — ثوابت النظام ومخطط الجداول.

كل ما هو "بيانات وصفية" (أسماء الجداول، ترويسات الأعمدة، قوائم الاختيار) موجود
هنا ولا يتغيّر أثناء التشغيل، بخلاف core.data.runtime الذي يملك الحالة المتغيّرة.

قاعدة مهمة عند إضافة حقل جديد: أي حقل يُلحق دائماً في *نهاية* قائمة الحقول حتى
لا تنزاح مواضع الأعمدة في ملفات Excel القديمة.
"""

import os

from openpyxl.styles import Alignment, Font, PatternFill

# مجلد جذر المشروع (ثلاثة مستويات أعلى: core/data/config.py)
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BACKUP_DIR_NAME = "backups"           # مجلد النسخ الاحتياطية اليومية
AUDIT_DIR_NAME = "logs"               # مجلد سجل الحركات (إضافة/تعديل/حذف)
ATTACHMENTS_DIR_NAME = "attachments"  # مجلد ملفات المرفقات (فواتير، صور، ...)
MAX_BACKUPS = 30                      # عدد النسخ اليومية المحفوظة
AUDIT_HEADERS = ["الوقت", "الإجراء", "الجدول", "المفتاح", "التفاصيل"]

# اسم المطعم - عدّل هذا القسم بمعلومات مطعمك
COMPANY_NAME_AR = "مطعم الضيافة لتقديم الوجبات والولائم"
COMPANY_NAME_EN = "Al-Diyafa Catering Restaurant"
COMPANY_ADDRESS_AR = "الكويت"
COMPANY_ADDRESS_EN = "Kuwait"
COMPANY_PHONE = "+965 00000000"
COMPANY_EMAIL = "info@example.com"

FONT_NAME = "Segoe UI"

SHEETS = {
    "staff": "العمال والشيفات",
    "equipment": "المعدات وسيارات التوصيل",
    "setup_expenses": "مصاريف التأسيس",
    "monthly_expenses": "المصاريف الشهرية الثابتة",
    "purchases": "المشتريات اليومية",
    "customers": "العملاء",
    "institutional_orders": "طلبات المؤسسات الدائمة",
    "events": "العزائم والمناسبات",
    "invoices": "الفواتير",
    "salaries": "الرواتب",
    "products": "الأصناف والمنيو",
    "quotations": "عروض الأسعار",
    "payments": "مدفوعات العملاء",
    "petty_cash": "النثريات اليومية",
}
# ------------------------------------------------------------------
# تعريف الأعمدة لكل جدول: (المفتاح البرمجي, التسمية المعروضة بالعربي)
# ------------------------------------------------------------------
JOB_TITLES = ["شيف رئيسي", "طباخ مساعد", "عامل تحضير", "عامل توصيل", "عامل تقديم وضيافة", "إداري / محاسب", "أخرى"]
STAFF_FIELDS = [
    ("name", "اسم الموظف"),
    ("national_id", "الهوية"),
    ("job_title", "المسمى الوظيفي"),
    ("phone", "الهاتف"),
    ("base_salary", "الراتب الأساسي الشهري"),
    ("hire_date", "تاريخ التعيين"),
    ("notes", "ملاحظات"),
    ("attachment", "ملف مرفق (هوية/عقد...)"),
]

EQUIPMENT_CATEGORIES = ["معدات مطبخ", "سيارة توصيل", "أثاث وتجهيزات صالة", "أجهزة تبريد وتخزين", "أخرى"]
EQUIPMENT_FIELDS = [
    ("name", "اسم / وصف المعدة"),
    ("category", "التصنيف"),
    ("purchase_date", "تاريخ الشراء"),
    ("cost", "التكلفة (د.ك)"),
    ("notes", "ملاحظات"),
    ("attachment", "ملف مرفق (فاتورة شراء...)"),
]

SETUP_EXPENSE_TYPES = ["تراخيص وسجلات حكومية", "معدات مطبخ", "سيارات توصيل", "ديكور وتجهيز المكان", "تأمينات وايجار مقدم", "أخرى"]
SETUP_EXPENSE_FIELDS = [
    ("id", "الرقم"),
    ("date", "التاريخ"),
    ("type", "نوع المصروف"),
    ("description", "الوصف"),
    ("cost", "التكلفة (د.ك)"),
    ("notes", "ملاحظات"),
    ("attachment", "ملف مرفق (فاتورة...)"),
]

MONTHLY_EXPENSE_TYPES = ["إيجار المكان", "كهرباء وماء", "اتصالات وانترنت", "صيانة دورية", "تأمين", "أخرى"]
MONTHLY_EXPENSE_FIELDS = [
    ("id", "الرقم"),
    ("month", "الشهر (YYYY-MM)"),
    ("type", "نوع المصروف"),
    ("amount", "المبلغ (د.ك)"),
    ("notes", "ملاحظات"),
    ("attachment", "ملف مرفق (فاتورة...)"),
]

PURCHASE_TYPES = ["خضروات وفواكه", "لحوم ودواجن", "أسماك", "خبز ومخبوزات", "أرز وبقوليات", "ألبان وأجبان",
                  "غاز الطبخ", "زيوت وسمن", "بهارات وتوابل", "مواد تنظيف", "أخرى"]
PURCHASE_UNITS = ["كجم", "لتر", "قطعة", "كيس", "أسطوانة", "كرتون"]
PURCHASE_FIELDS = [
    ("id", "الرقم"),
    ("date", "التاريخ"),
    ("type", "نوع المشترى"),
    ("item", "اسم الصنف"),
    ("quantity", "الكمية"),
    ("unit", "الوحدة"),
    ("unit_cost", "سعر الوحدة (د.ك)"),
    ("total_cost", "الإجمالي (د.ك)"),
    ("supplier", "المورد"),
    ("notes", "ملاحظات"),
    ("attachment", "ملف مرفق (فاتورة شراء...)"),
]

CUSTOMER_TYPES = ["شركة", "مستشفى", "مدرسة", "عميل مناسبة (فرح / عزيمة)", "أخرى"]
CUSTOMER_FIELDS = [
    ("name", "الاسم"),
    ("type", "النوع"),
    ("phone", "الهاتف"),
    ("address", "العنوان"),
    ("contact_person", "الشخص المسؤول"),
    ("notes", "ملاحظات"),
]

MEAL_TYPES = ["إفطار", "غداء", "عشاء", "وجبات متعددة"]
ORDER_FREQUENCIES = ["يومي", "أسبوعي", "طلب لمرة واحدة"]
INSTITUTIONAL_ORDER_FIELDS = [
    ("id", "الرقم"),
    ("date", "تاريخ التسليم"),
    ("customer", "المؤسسة / العميل"),
    ("meal_type", "نوع الوجبة"),
    ("frequency", "التكرار"),
    ("quantity", "عدد الوجبات"),
    ("unit_price", "سعر الوجبة (د.ك)"),
    ("total", "الإجمالي (د.ك)"),
    ("delivery_location", "مكان التسليم"),
    ("delivery_time", "وقت التسليم"),
    ("invoiced", "مفوترة؟"),
    ("invoice_no", "رقم الفاتورة"),
    ("notes", "ملاحظات"),
    # حقول جدولة التوصيل — تُلحق آخر المخطط (انظر قاعدة الإلحق في أعلى الملف)
    ("driver", "السائق المُسند"),
    ("vehicle", "السيارة / المعدة"),
    ("delivered", "سُلّمت؟"),
]

EVENT_TYPES = ["فرح / زفاف", "عزيمة عائلية", "مناسبة رسمية / شركة", "تخرج", "عزاء", "أخرى"]
EVENT_FIELDS = [
    ("id", "الرقم"),
    ("event_date", "تاريخ المناسبة"),
    ("customer", "العميل"),
    ("event_type", "نوع المناسبة"),
    ("guests_count", "عدد الأشخاص"),
    ("menu_description", "وصف المنيو"),
    ("unit_price", "سعر الفرد (د.ك)"),
    ("total", "الإجمالي (د.ك)"),
    ("location", "مكان التنفيذ"),
    ("delivery_time", "وقت التسليم"),
    ("deposit", "العربون المستلم (د.ك)"),
    ("invoiced", "مفوترة؟"),
    ("invoice_no", "رقم الفاتورة"),
    ("notes", "ملاحظات"),
    # حقول جدولة التوصيل — تُلحق آخر المخطط (انظر قاعدة الإلحق في أعلى الملف)
    ("driver", "السائق المُسند"),
    ("vehicle", "السيارة / المعدة"),
    ("delivered", "سُلّمت؟"),
]

INVOICE_FIELDS = [
    ("invoice_no", "رقم الفاتورة"),
    ("date", "التاريخ"),
    ("customer", "العميل"),
    ("items_json", "بنود الفاتورة (JSON)"),
    ("total", "الإجمالي (د.ك)"),
    ("notes", "ملاحظات"),
    # أعمدة مرحلة التحصيل — تُلحق في نهاية المخطط حتى لا تنزاح أعمدة الملفات القديمة
    ("paid_amount", "المدفوع (د.ك)"),
    ("status", "حالة التحصيل"),
]

SALARY_FIELDS = [
    ("id", "الرقم"),
    ("staff", "الموظف"),
    ("month", "الشهر (YYYY-MM)"),
    ("base_salary", "الراتب الأساسي"),
    ("bonuses", "المكافآت"),
    ("advances", "السلف"),
    ("deductions", "الخصومات"),
    ("net_salary", "الصافي (د.ك)"),
    ("paid", "مدفوع؟"),
    ("notes", "ملاحظات"),
]
# ------------------------------------------------------------------
# جداول الميزات الجديدة: المنيو، عروض الأسعار، مدفوعات العملاء، النثريات
# ------------------------------------------------------------------
PRODUCT_CATEGORIES = ["أطباق رئيسية", "مقبلات وسلطات", "حلويات", "مشروبات", "خبز ومخبوزات", "بوفيه مفتوح", "أخرى"]
PRODUCT_UNITS = ["حصة / فرد", "صينية", "كجم", "لتر", "قطعة", "كرتون"]
PRODUCT_FIELDS = [
    ("name", "اسم الصنف"),
    ("category", "التصنيف"),
    ("unit", "الوحدة"),
    ("cost", "تكلفة التجهيز (د.ك)"),
    ("sale_price", "سعر البيع (د.ك)"),
    ("notes", "ملاحظات"),
]

QUOTATION_STATUSES = ["معلق", "مقبول", "مرفوض"]
QUOTATION_FIELDS = [
    ("id", "الرقم"),
    ("date", "تاريخ العرض"),
    ("customer", "العميل"),
    ("event_type", "نوع المناسبة"),
    ("event_date", "تاريخ المناسبة المقترح"),
    ("guests_count", "عدد الأشخاص"),
    ("menu_description", "وصف المنيو"),
    ("unit_price", "سعر الفرد (د.ك)"),
    ("total", "الإجمالي (د.ك)"),
    ("status", "الحالة"),
    ("converted_id", "رقم المناسبة بعد التحويل"),
    ("notes", "ملاحظات"),
    ("attachment", "ملف مرفق (قائمة طعام...)"),
]

PAYMENT_METHODS = ["نقداً", "كي نت", "تحويل بنكي", "شيك", "أخرى"]
PAYMENT_FIELDS = [
    ("id", "الرقم"),
    ("date", "التاريخ"),
    ("invoice_no", "رقم الفاتورة"),
    ("customer", "العميل"),
    ("amount", "المبلغ (د.ك)"),
    ("method", "طريقة الدفع"),
    ("notes", "ملاحظات"),
    ("attachment", "ملف مرفق (إيصال...)"),
]

PETTY_CASH_TYPES = ["وقود وتوصيل", "أدوات ومستلزمات", "صيانة طارئة", "قرطاسية", "ضيافة وضيوف", "أخرى"]
PETTY_CASH_FIELDS = [
    ("id", "الرقم"),
    ("date", "التاريخ"),
    ("type", "نوع النثريات"),
    ("description", "الوصف"),
    ("amount", "المبلغ (د.ك)"),
    ("notes", "ملاحظات"),
    ("attachment", "ملف مرفق (إيصال...)"),
]

_FIELDS_BY_SHEET = {
    "staff": STAFF_FIELDS,
    "equipment": EQUIPMENT_FIELDS,
    "setup_expenses": SETUP_EXPENSE_FIELDS,
    "monthly_expenses": MONTHLY_EXPENSE_FIELDS,
    "purchases": PURCHASE_FIELDS,
    "customers": CUSTOMER_FIELDS,
    "institutional_orders": INSTITUTIONAL_ORDER_FIELDS,
    "events": EVENT_FIELDS,
    "invoices": INVOICE_FIELDS,
    "salaries": SALARY_FIELDS,
    "products": PRODUCT_FIELDS,
    "quotations": QUOTATION_FIELDS,
    "payments": PAYMENT_FIELDS,
    "petty_cash": PETTY_CASH_FIELDS,
}


def headers_for(sheet_key):
    """قائمة أعمدة الجدول: [(المفتاح, التسمية), ...] — المصدر الوحيد للحقيقة."""
    return _FIELDS_BY_SHEET[sheet_key]


# تنسيق صف العناوين في Excel
HEADER_FILL = PatternFill(start_color="6B2B1F", end_color="6B2B1F", fill_type="solid")
HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF")
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center")

# الامتدادات القابلة للعرض مباشرة في المتصفح/العارض الافتراضي
ATTACHMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp",
                         ".doc", ".docx", ".xls", ".xlsx", ".txt", ".csv"}


def attachments_dir():
    """المسار الكامل لمجلد المرفقات (يدخل فيه الملفات ويقرأ منه)."""
    return os.path.join(APP_DIR, ATTACHMENTS_DIR_NAME)


def attachment_path(filename):
    """يحوّل اسم الملف المخزّن في الجدول إلى مسار كامل داخل مجلد المرفقات."""
    if not filename:
        return None
    # للأمان: لا نسمح بمسارات ../ أو مسارات مطلقة
    filename = os.path.basename(filename)
    return os.path.join(attachments_dir(), filename)
