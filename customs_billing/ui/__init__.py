# -*- coding: utf-8 -*-
"""واجهة المستخدم (Tkinter)، مقسّمة إلى وحدة لكل شاشة.

    app             النافذة الرئيسية والتنقّل بين التبويبات.
    tab_dashboard   لوحة المعلومات.
    tab_invoices    سجل الفواتير.
    tab_customers   العملاء.
    tab_payments    الدفعات والأرصدة.
    invoice_form    نافذة إضافة/تعديل فاتورة.
    printing        توليد صفحات HTML للطباعة.
    theme           لوحة الألوان.
    widgets         عناصر مشتركة (منتقي التاريخ).
"""

__all__ = ["run", "InvoiceApp"]


def __getattr__(name):
    """يستورد `run` و `InvoiceApp` عند الطلب لتفادي الاستيراد الدائري."""
    if name in __all__:
        from . import app
        return getattr(app, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")