# -*- coding: utf-8 -*-
"""نقطة تشغيل النظام: `python main.py` أو `python -m transport`."""

import os
import sys

# جعل مجلد الحزمة على مسار الاستيراد حتى تعمل الاستيرادات المطلقة الداخلية.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from transport import run_application
    return run_application()


if __name__ == "__main__":
    main()