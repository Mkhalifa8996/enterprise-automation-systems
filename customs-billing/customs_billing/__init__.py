# -*- coding: utf-8 -*-
"""فواتير جمركية — Customs Billing.

حزمة مقسّمة إلى طبقات:
    config / constants / utils   إعدادات وثوابت ودوال مساعدة.
    data                        قاعدة البيانات ونسخة إكسل المرآة والحسابات.
    ui                          واجهة Tkinter بتبويبات.

الاستيراد كسول (lazy) لواجهة المستخدم: استيراد `customs_billing.data`
لا يسحب Tkinter معه، فالتعامل مع طبقة البيانات (في الاختبارات أو السكربتات
أو على خادم بلا شاشة) يبقى ممكناً وخفيفاً. الوصول إلى `InvoiceApp` أو `run`
يحمّل `ui.app` عند أول طلب فقط.
"""

from .config import APP_NAME, APP_SLUG, APP_VERSION as __version__

__all__ = ["APP_NAME", "APP_SLUG", "InvoiceApp", "run", "run_application", "__version__"]


def __getattr__(name):
    """يحمّل واجهة المستخدم عند الطلب فقط (تفادياً للاستيراد الدائري)."""
    if name in ("InvoiceApp", "run"):
        from .ui import app
        return getattr(app, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def run_application():
    """نقطة تشغيل واجهة المستخدم (تُستخدم من `main.py`)."""
    from .ui.app import run
    return run()