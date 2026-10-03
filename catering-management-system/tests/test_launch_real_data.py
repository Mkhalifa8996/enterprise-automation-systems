# -*- coding: utf-8 -*-
"""
تشغيل حقيقي سريع: يفتح البرنامج على قاعدة SQLite مؤقتة ثم يغلق نفسه تلقائياً.
يُستخدم للتأكد من أن التطبيق يقلع فعلاً على بيانات المستخدم دون تعديلها.
    python tests/test_launch_real_data.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

# اختبار الإقلاع الحقيقي يعمل على SQLite الآن: يجهّز قاعدة مؤقتة من بيانات
# حقيقية (استيراد من ملف Excel الأصلي إن وُجد، وإلا بيانات تجريبية)، ثم يتحقق
# أن الإقلاع نفسه مع التنقل بين الشاشات لا يعدّل محتوى القاعدة.
SANDBOX = os.path.join(BASE, "tests", "_launch_probe")
os.makedirs(SANDBOX, exist_ok=True)
os.environ["RESTAURANT_BACKEND"] = "sqlite"
os.environ["RESTAURANT_DB_FILE"] = os.path.join(SANDBOX, "probe.db")
os.environ["RESTAURANT_DATA_FILE"] = os.path.join(SANDBOX, "probe.xlsx")

import restaurant_data as rd
import restaurant_desktop_app as app

import sqlite3

if os.path.exists(os.environ["RESTAURANT_DB_FILE"]):
    os.remove(os.environ["RESTAURANT_DB_FILE"])
rd.ensure_workbook()
if not rd.load_customers():
    # قاعدة فارغة تماماً: نزرع صفاً تجريبياً حتى يكون للإقلاع محتوى
    rd.save_customer({"name": "عميل الإقلاع", "type": "شركة"})


def _db_dump():
    conn = sqlite3.connect(os.environ["RESTAURANT_DB_FILE"])
    try:
        out = []
        for (name,) in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            rows = conn.execute('SELECT * FROM "%s" ORDER BY rowid' % name).fetchall()
            out.append((name, [tuple(r) for r in rows]))
        return out
    finally:
        conn.close()


before = _db_dump()
print("القاعدة:", os.environ["RESTAURANT_DB_FILE"])
print("عدد العملاء:", len(rd.load_customers()), "| عدد الفواتير:", len(rd.load_invoices()))

ui = app.RestaurantApp()
ui.after(2500, ui.destroy)      # إغلاق تلقائي بعد 2.5 ثانية
ui.update()                     # رسم الشاشة الأولى
ui.after(100, lambda: ui.show_page("invoices"))
ui.after(200, lambda: ui.show_page("reports"))
ui.update()
ui.mainloop()

after = _db_dump()
print("المحتوى بعد التشغيل:", "لم يتغير" if before == after else "تغيّر!")
print("تم الإقلاع والإغلاق بنجاح.")
sys.exit(0 if before == after else 1)