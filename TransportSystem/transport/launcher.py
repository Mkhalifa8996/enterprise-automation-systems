# -*- coding: utf-8 -*-
"""تشغيل التطبيق مع منع فتح نسختين في نفس الوقت."""

import atexit

import tkinter as tk
from tkinter import messagebox

from . import single_instance
from .app import TransportApp
from .app_config import APP_LOCK_DIR


def start_application():
    """يشغّل البرنامج بعد التأكد من عدم وجود نسخة أخرى تعمل."""
    acquired, message = single_instance.acquire(APP_LOCK_DIR)
    if not acquired:
        try:
            tk.Tk().withdraw()
            messagebox.showwarning("البرنامج يعمل بالفعل", message)
        except Exception:
            print(message)
        return None
    # ضمان تحرير القفل حتى لو حدث انهيار غير متوقع.
    atexit.register(lambda: single_instance.release(APP_LOCK_DIR))
    return TransportApp()


def run_application():
    """نقطة التشغيل: تنشئ النافذة وتدخل في حلقة الأحداث."""
    app = start_application()
    if app is not None:
        app.mainloop()
    return app
