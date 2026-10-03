# -*- coding: utf-8 -*-
"""نظام إدارة شركة النقل — نقطة الدخول الموحّدة للتطبيق.

الحزمة تفصل بين: ثوابت الواجهة، والدوال المساعدة، وعناصر الواجهة، والطباعة،
وشاشات الإدخال، وطبقات التطبيق (mixins) — بدل صفحة واحدة ضخمة.
"""

from .app_config import APP_LOCK_DIR
from .app import TransportApp
from .launcher import run_application

__all__ = ["TransportApp", "run_application", "APP_LOCK_DIR"]
__version__ = "1.0.0"
