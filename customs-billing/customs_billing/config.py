# -*- coding: utf-8 -*-
"""إعدادات التطبيق: الهوية، المسارات، ومعلومات الشركة.

يعمل هذا الملف في الحالتين: التشغيل العادي من الشيفرة المصدرية، والتشغيل
من ملف تنفيذي مبني بـ PyInstaller، فيحسب المسارات في كل حالة على حدة.

معلومات الشركة معرّفة هنا في مكان واحد، فتغييرها لا يتطلب تعديل أكثر من موضع
واحد (ترويسة النافذة، ترويسة الفاتورة المطبوعة، وكشوف الحساب).
"""

import os
import sys

# ------------------------------------------------------------------
# هوية التطبيق والشركة
# ------------------------------------------------------------------
APP_NAME = "Customs Billing"
APP_SLUG = "customs-billing"
APP_VERSION = "1.0.0"

COMPANY_NAME_AR = "فواتير جمركية"
COMPANY_NAME_EN = "Customs Billing"

# عنوان النافذة الرئيسي
WINDOW_TITLE_AR = COMPANY_NAME_AR


def _app_dir():
    """مجلد التطبيق الذي تُحفظ فيه قاعدة البيانات ونسخة إكسل.

    عند التشغيل من ملف exe نرجع إلى مجلد الملف التنفيذي نفسه (وليس المجلد
    المؤقت الذي يفكّ فيه PyInstaller الموارد)، حتى تبقى البيانات في مكان
    ثابت لا يُمسح عند إغلاق البرنامج.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    # هذا الملف داخل customs_billing/ ، فمجلد أبويه هو جذر المشروع.
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


APP_DIR = _app_dir()

# عند التجميد تكون الصور داخل المجلد المؤقت الذي يفكّه PyInstaller.
RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR) if getattr(sys, "frozen", False) else APP_DIR


def resource_path(name):
    """مسار ملف مورد (شعار أو أيقونة) بجانب البرنامج أو داخل الحزمة."""
    candidate = os.path.join(RESOURCE_DIR, name)
    if os.path.exists(candidate):
        return candidate
    return os.path.join(APP_DIR, name)


# قاعدة البيانات هي المصدر الأساسي لكل البيانات.
# يسمح بتجاوز مسارها عبر متغيّر البيئة CB_DB_PATH لأغراض الاختبار.
DB_FILE = os.environ.get("CB_DB_PATH") or os.path.join(APP_DIR, f"{APP_SLUG.replace('-', '_')}.db")

# نسخة إكسل المرآة: تُحدَّث تلقائياً بعد كل تعديل، وتبقى قابلة للفتح في إكسل.
# (CB_XLSX_PATH يُستخدم لعزل ملف الإكسل أثناء الاختبارات فقط.)
DATA_FILE = os.environ.get("CB_XLSX_PATH") or os.path.join(APP_DIR, "data.xlsx")

ICON_FILE = resource_path("icon.png")   # أيقونة التطبيق (شعار مبسط بدون نص)
LOGO_FILE = resource_path("logo.png")   # الشعار الكامل مع اسم الشركة

FONT_NAME = "Segoe UI"  # يدعم العربية بشكل جيد على ويندوز؛ Tk يستخدم بديلاً مناسباً تلقائياً على ماك/لينكس


def get_tk_font(size=10, weight="normal"):
    """يعيد صيغة خط متوافقة مع Tkinter على ويندوز/لينكس/ماك."""
    return (FONT_NAME, size, weight)