# -*- coding: utf-8 -*-
"""سجلّ شاشات الإدخال لتحديثها جميعاً بعد أي تعديل."""

import tkinter as tk
from .ui_helpers import log_exception


# سجلّ عام لكل شاشات CrudTab المبنية، لتحديثها جميعاً فور أي تعديل في أي شاشة.
_ALL_CRUD_TABS = []

def refresh_all_registers():
    """يعيد بناء جداول كل شاشات الإدخال بعد أي حفظ أو حذف في أي مكان.

    كانت التحديثات محصورة في الشاشة المفتوحة، فيظهر تعديل السائق أو السيارة
    متأخراً على بقية التبويبات حتى لو كانت مفتوحة في نفس النافذة.
    """
    for tab in list(_ALL_CRUD_TABS):
        try:
            # CrudTab ليس عنصر widgets، فنفحص إطاره الحقيقي.
            if not tab.frame.winfo_exists():
                _ALL_CRUD_TABS.remove(tab)
                continue
            tab.refresh()
        except tk.TclError:
            if tab in _ALL_CRUD_TABS:
                _ALL_CRUD_TABS.remove(tab)
        except Exception as exc:
            log_exception("تحديث شاشة إدخال", exc)
