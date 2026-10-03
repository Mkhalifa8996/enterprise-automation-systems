# -*- coding: utf-8 -*-
"""نقطة تشغيل نظام الفواتير.

الاستخدام:
    python main.py
أو بعد تثبيت الحزمة:
    python -m customs_billing
"""

import os
import sys

# جعل مجلد المشروع على مسار الاستيراد حتى تعمل الاستيرادات النسبية الداخلية.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from customs_billing import run_application
    return run_application()


if __name__ == "__main__":
    raise SystemExit(main())