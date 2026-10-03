# -*- coding: utf-8 -*-
"""
core.data.runtime — الحالة المتغيّرة الوحيدة لمخزن البيانات.

يشمل: محرك التخزين المختار، ومسارات الملفات، وقفل النسخة الواحدة. أي وحدة
أخرى تحتاج هذه القيم تستورد منها ولا تملك نسخة خاصة بها.

المسارات تُقرأ من متغيرات البيئة مرة واحدة عند الإقلاع (وهي الطريقة التي
تستخدمها كل الاختبارات لتوجيه البرنامج إلى مجلد مؤقت).
"""

import os

from core.data.config import APP_DIR

# مسار ملف Excel: يمكن تغييره من متغير البيئة (يفيد لوضع الملف على قرص مشترك
# أو لاختبارات القفل بين عمليتين)، وإلا فهو مجاور للبرنامج.
DATA_FILE = (os.environ.get("RESTAURANT_DATA_FILE")
             or os.path.join(APP_DIR, "restaurant_data.xlsx"))

# نسخة الطوارئ من الإصدار السابق قبل كل حفظ. نحافظ على الامتداد .xlsx لأن
# openpyxl (وExcel) لا يفتحان ملفات بامتداد آخر.
BAK_FILE = DATA_FILE + ".bak.xlsx"

# محرك التخزين: "sqlite" (الافتراضي) أو "excel" (وضع التوافق القديم فقط).
# التبديل عبر متغير البيئة RESTAURANT_BACKEND — كل دوال الواجهة تعمل على
# المحركين دون تغيير. عند أول إقلاع على SQLite وكان ملف Excel موجوداً والقاعدة
# فارغة، يُستورد تلقائياً (مع نسخة احتياطية) — لا حاجة لأي خطوة.
BACKEND = (os.environ.get("RESTAURANT_BACKEND") or "sqlite").strip().lower()
if BACKEND not in ("excel", "sqlite"):
    BACKEND = "sqlite"

# هل تم التحقق من جداول ملف Excel في هذه الجلسة؟ (يُستعمل في وضع Excel فقط)
_schema_checked = False
_lock_handle = None            # مقبض ملف قفل النسخة الواحدة


def is_sqlite():
    """هل يعمل البرنامج على محرك SQLite؟"""
    return BACKEND == "sqlite"


def app_data_dir():
    """المجلد الذي تُحفظ فيه البيانات (نسخ احتياطية، سجل، مرفقات)."""
    return os.path.dirname(os.path.abspath(DATA_FILE))


def sub_dir(name, create=True):
    """مجلد فرعي داخل مجلد البيانات، يُنشأ تلقائياً افتراضياً."""
    path = os.path.join(app_data_dir(), name)
    if create:
        os.makedirs(path, exist_ok=True)
    return path


def reset_schema_check():
    """إعادة فحص مخطط ملف Excel (تُستخدم في الاختبارات بعد تعديل الملف يدوياً)."""
    global _schema_checked
    _schema_checked = False
