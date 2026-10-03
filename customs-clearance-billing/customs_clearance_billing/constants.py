# -*- coding: utf-8 -*-
"""تعريف بنية البيانات المشتركة: أسماء الأوراق، بنود الخدمة، وحقول الفاتورة.

تعيش هذه الثوابت في مكان واحد حتى تتفق قاعدة البيانات ونسخة إكسل
والواجهة على نفس ترتيب الأعمدة ونفس التسميات.
"""

# ------------------------------------------------------------------
# الإعدادات العامة
# ------------------------------------------------------------------
SHEET_INVOICES = "الفواتير"
SHEET_CUSTOMERS = "العملاء"
SHEET_PAYMENTS = "الدفعات"

# 24 بند خدمة كما في الفاتورة الورقية الأصلية (عربي، إنجليزي)
SERVICE_ITEMS = [
    ("إذن تسليم بوليصة الشحن", "DELIVERY ORDER SHIPPING"),
    ("أجور استلام إذن التسليم", "REVIEWING CHARGE - DELIVERY ORDER"),
    ("أجور الشحن والخدمات اللوجستية", "FREIGHT CHARGE SHIPPING LOGISTIC"),
    ("أرضيات الوكيل او محطة الحاويات", "FREIGHT FORWARDWE FLOORING - FEES"),
    ("رسوم تصديقات الفاتورة والمنشأ", "LEGALIZATION FEES INVOICE"),
    ("أجور تصديقات الفواتير", "LEGALIZAION CHARGES"),
    ("رسوم جلوبال", "GLOBAL FEES"),
    ("الرسوم الجمركية (الجمارك)", "CUSTOMS DUTY"),
    ("عمولة البنك للرسوم الجمركية", "BANK COMMISSION"),
    ("خدمة الإعفاء الجمركي", "EXEMPTION FROM LNDUSTRAY"),
    ("رسوم أفراج الصناعة أو البيئة", "APPROVAL OF LNDUSTRAY"),
    ("رسوم خدمات الأفراج", "APPROVAL OF LNDUSTRIAL - FEES"),
    ("رسوم خدمات الميناء", "PORT SERVICE - FEES"),
    ("أجور كشف جمركي", "CUSTOMS CHARGE"),
    ("أجور خدمات النقل", "TRANSPORTATION CHARGE"),
    ("أجور خدمات العمال", "SERVICE - FEES"),
    ("أجور الكرين أو الرافعة", "FORKLIFT AND CRANE - FEES"),
    ("غرامة طبالي", "FINE FOR DRUMS"),
    ("أجور البيان الجمركي", "CUSTOMS - FEES"),
    ("رسوم خدمات جمركية سحب إسكان", "CUSTOMS SERVICE - FEES"),
    ("أجور التخليص والأتعاب", "CLEARANCE FEES CHARGE"),
    ("طباعة وتصوير المستندات", "PRINTING AND COPYING - FEES"),
    ("أجور الاستلام والمتابعة", "RECEIVING & FOLLOW UP SERVICE"),
    ("أجور خدمات أخرى", "OTHER SERVICE CHARGES"),
]

# الحقول الأساسية + تفاصيل الشحنة (المفتاح، التسمية المعروضة)
META_FIELDS = [
    ("invno", "رقم الفاتورة"),
    ("date", "التاريخ"),
    ("customer", "السادة / اسم العميل"),
    ("declno", "رقم البيان الجمركي"),
    ("decldate", "تاريخ البيان الجمركي"),
    ("port", "المنفذ"),
    ("containercount", "عدد الحاويات"),
    ("goodstype", "نوع البضاعة"),
    ("origin", "بلد المنشأ"),
]

META_KEYS = [key for key, _ in META_FIELDS]

INVOICE_HEADERS = [lbl for _, lbl in META_FIELDS]
for _ar, _en in SERVICE_ITEMS:
    INVOICE_HEADERS.append(_ar + " - دينار")
    INVOICE_HEADERS.append(_ar + " - فلس")
INVOICE_HEADERS += ["ملاحظات", "الإجمالي"]
del _ar, _en

CUSTOMER_HEADERS = ["اسم العميل", "الهاتف", "العنوان", "ملاحظات", "رمز الشركة"]

PAYMENT_HEADERS = ["رقم السند", "اسم العميل", "التاريخ", "المبلغ (د.ك)", "ملاحظات", "الفواتير المسددة"]