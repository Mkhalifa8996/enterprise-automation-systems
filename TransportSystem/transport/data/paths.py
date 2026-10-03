# -*- coding: utf-8 -*-
"""مسارات التطبيق ومعلومات الشركة وشعار الخط."""

import os
import sys


def _get_app_dir():
    """مسار مجلد التطبيق: يعمل مع PyInstaller ومع التشغيل العادي.

    بعد تقسيم المشروع إلى حزمة صار هذا الملف داخل `transport/data/`، فلو
    أخذنا مجلده مباشرة لوقعت قاعدة البيانات والمرفقات داخل الشيفرة نفسها.
    نرجع مستويين للأعلى حتى يقود ذلك إلى جذر المشروع دائماً.
    """
    if getattr(sys, 'frozen', False):
        # التشغيل من ملف exe مترجم بـ PyInstaller
        return os.path.dirname(sys.executable)
    # التشغيل العادي من الكود المصدري: مجلد الحزمة (transport/data)
    return os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))


APP_DIR = _get_app_dir()

def _get_resource_path(relative_path):
    """الحصول على مسار المورد المضمّن في ملف exe المترجم بـ PyInstaller."""
    try:
        base_path = getattr(sys, "frozen", False) and sys._MEIPASS \
            or _get_app_dir()
        if os.path.isfile(os.path.join(base_path, relative_path)):
            return os.path.join(base_path, relative_path)
    except Exception:
        pass
    return os.path.join(_get_app_dir(), relative_path)

def _configured_database_path():
    """مسار قاعدة البيانات: يسمح بعزل الاختبارات عبر TRANSPORT_DB_PATH."""
    override = os.environ.get("TRANSPORT_DB_PATH", "").strip()
    return override or os.path.join(APP_DIR, "transport_data.db")

DATA_FILE = os.path.join(APP_DIR, "transport_data.xlsx")

BACKUP_FILE = os.path.join(APP_DIR, "transport_data_backup.xlsx")

DB_FILE = _configured_database_path()

BACKUP_DIR = os.path.join(APP_DIR, "backups")

SYNC_CONFIG_FILE = os.path.join(APP_DIR, "google_sync_config.json")

FIREBASE_CONFIG_FILE = os.path.join(APP_DIR, "firebase_sync_config.json")

# رابط قاعدة Firebase: يُقرأ من ملف الإعداد `firebase_sync_config.json` أو من
# متغيّر البيئة FIREBASE_DATABASE_URL. لا تُثبَّت هنا قيمة المشروع، فذلك يربط
# الشيفرة بمشروع بعينه ويكشف معرّفه.
FIREBASE_DATABASE_URL = os.environ.get("FIREBASE_DATABASE_URL", "").strip()

# معلومات الشركة المستخدمة في ترويسة الفواتير والكشوف المطبوعة.
# تُقرأ من متغيّرات البيئة لتبقى الشيفرة خالية من بيانات خاصة، وتُملأ محلياً
# من ملف الإعداد أو البيئة عند التشغيل:
#   TRANSPORT_COMPANY_NAME_AR / _EN, _ADDRESS_AR / _EN, _PHONE, _EMAIL
COMPANY_NAME_AR = os.environ.get("TRANSPORT_COMPANY_NAME_AR", "").strip()

COMPANY_NAME_EN = os.environ.get("TRANSPORT_COMPANY_NAME_EN", "").strip()

COMPANY_ADDRESS_AR = os.environ.get("TRANSPORT_COMPANY_ADDRESS_AR", "").strip()

COMPANY_ADDRESS_EN = os.environ.get("TRANSPORT_COMPANY_ADDRESS_EN", "").strip()

COMPANY_PHONE = os.environ.get("TRANSPORT_COMPANY_PHONE", "").strip()

COMPANY_EMAIL = os.environ.get("TRANSPORT_COMPANY_EMAIL", "").strip()

FONT_NAME = "Segoe UI"
