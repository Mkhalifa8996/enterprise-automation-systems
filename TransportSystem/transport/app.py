# -*- coding: utf-8 -*-
"""صفقة TransportApp: تُركَّب من طبقات (mixins) حسب مجال كل منها.

كل طبقة ملف مستقل، فالتعديل في تقرير أو رواتب لا يمسّ ملف بقية الشاشة.
"""

import tkinter as tk

from .app_core import AppCoreMixin
from .app_entities import AppEntitiesMixin
from .app_salaries import AppSalariesMixin
from .app_partners import AppPartnersMixin
from .app_reports import AppReportsMixin


class TransportApp(
    AppCoreMixin,
    AppEntitiesMixin,
    AppSalariesMixin,
    AppPartnersMixin,
    AppReportsMixin,
    tk.Tk,
):
    """النافذة الرئيسية: تجمع كل التبويبات والشاشات في نافذة واحدة."""
