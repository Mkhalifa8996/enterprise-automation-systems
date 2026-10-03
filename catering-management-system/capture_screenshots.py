# -*- coding: utf-8 -*-
"""
capture_screenshots.py — يلتقط صورة لكل شاشة في screenshots/

يعمل على قاعدة بيانات مؤقتة ببيانات تجريبية، فلا يمس بيانات المستخدم الحقيقية.
بعد التشغيل تُحفظ الصور في screenshots/ مرقّمة بالترتيب نفسه لكل مشروع آخر.

    python capture_screenshots.py
"""
import ctypes
import os
import shutil
import sys
import tempfile
import time

# الواجهة وImageGrab يستخدمان مقاييس مختلفة على الشاشات ذات التكبير (DPI):
# نجعل العملية واعية بالتكبير قبل إنشاء أي نافذة، فتتطابق إحداثيات Tkinter
# مع بكسلات الصورة الملتقطة، وإلا خرجت القصّة ناقصة أو مموّهة.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)      # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

SANDBOX = os.path.join(tempfile.gettempdir(), "catering_screenshot_data")
SHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")

# المسارات تُضبط قبل الاستيراد: طبقة البيانات تقرأها مرة واحدة عند الإقلاع
shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(SANDBOX, exist_ok=True)
os.chdir(SANDBOX)          # يجعل المسار المعروض في شريط التطبيق قصيراً ونظيفاً
os.environ["RESTAURANT_BACKEND"] = "sqlite"
os.environ["RESTAURANT_DB_FILE"] = "showcase.db"
os.environ["RESTAURANT_DATA_FILE"] = "restaurant_data.xlsx"

import restaurant_data as rd          # noqa: E402
import restaurant_desktop_app as app  # noqa: E402

WIDTH, HEIGHT = 1600, 950

# (اسم ملف الصورة، مفتاح الشاشة، التبويب الفرعي)
SCREENS = [
    ("01-home.png", "home", None),
    ("02-orders.png", "orders", None),
    ("03-invoices.png", "invoices", None),
    ("04-expenses.png", "expenses", None),
    ("05-masterdata.png", "masterdata", None),
    ("06-salaries.png", "salaries", None),
    ("07-reports.png", "reports", None),
]


def _recent_months(count):
    """الشهور الأخيرة من الشهر الحالي إلى الجاري عدًً أشهرًًً."""
    today = rd.date.today()
    months = []
    year, month = today.year, today.month
    for _ in range(count):
        months.append("%04d-%02d" % (year, month))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    months.reverse()
    return months


# (نوع الوجبة, السعر, الكمية الشهرية) — أسعار الوجبات للمؤسسات
MONTHLY_MEALS = [("غداء", "2.750", 1400), ("عشاء", "3.250", 800),
                 ("فطار", "1.750", 1800)]

# (النوع, الصنف, الكمية, الوحدة, سعر الوحدة) — مشتريات شهرية تكفي عدد الوجبات
MONTHLY_PURCHASES = [("لحوم ودواجن", "دجاج طازج", "380", "كجم", "4.200"),
                     ("خضراوات وفواكه", "طامطم", "300", "كجم", "1.100"),
                     ("خبز ومخبزات", "عجين", "300", "كيس", "2.300"),
                     ("أرز وبقلويات", "أرز بسمتي", "200", "كيس", "5.400"),
                     ("ألبان وأجبان", "عرض", "150", "كيس", "2.800"),
                     ("غاز الطخخ", "أسطوانة غاز", "40", "أسطوانة", "25.000"),
                     ("زيوت وسمن", "زيت ذرة", "100", "كجم", "3.500"),
                     ("بهارات وتوابل", "خلط مطحون", "80", "كيس", "1.900"),
                     ("مواد تنظيف", "مصدف صحوني", "120", "كيس", "1.500")]

MONTHLY_FIXED = [("إيجار المكان", "1200.000"), ("كهرباء وماء", "380.500"),
                 ("اتصالات وانترنت", "95.000")]

# (الموظف, الراتب الأساسي)
MONTHLY_SALARIES = [("أحمد العنزي", "350.000"), ("سالم الرشيد", "280.000"),
                    ("مريم العبدالله", "190.000"), ("فهد المطيري", "210.000")]

# (العميل, نوع المناسبة, عدد الأشخاص, سعر الفرد) — مناسبة واحدة شهرياً
MONTHLY_EVENT = ("عميل مناسبة زفاف", "فرح / زفاف", 150, "6.500")


def seed():
    """بيانات تجريبية ممّثّ عدة أشهر: عملاء، عمال، معدات، مطاعبات،
    فواتير، مشتريات، مصاريف، رواتب، وأصناف — لتملأ التقارير، الرسوم،
    وشاش楥ات المحاريء بالشكل.
    """
    months = _recent_months(6)
    today = rd.date.today().isoformat()

    # ---------- البيانات الأساسية ----------
    customers = [
        ("شركة الخليج للخدمات", "شركة", "9655001",
         "حولي، شارع الاجتماعات", "أ. خالد العتبي"),
        ("مستشفى الشفاء", "مستشفى", "9655002", "السالمية", "د. هدى العنزي"),
        ("مدرسة الأفق الخاصة", "مدرسة", "9655003", "الجابرية", "أ. سالم"),
        ("شركة الأفاق للتموير", "شركة", "9655004", "قرطبة", "أ. محمد"),
        ("عميل مناسبة زفاف", "عميل مناسبة (فرح / عزيمة)", "9655005",
         "الصبية", "—"),
    ]
    for name, kind, phone, address, contact in customers:
        rd.save_customer({"name": name, "type": kind, "phone": phone,
                          "address": address, "contact_person": contact, "notes": ""})

    staff = [("أحمد العنزي", "شيف رئيسي"),
             ("سالم الرشيد", "طباخ مساعد"),
             ("مريم العبدالله", "عامل تحضير"),
             ("فهد المطيري", "عامل توصيل"),
             ("نورة السالم", "إداري / محاسب")]
    for name, title in staff:
        rd.save_staff({"name": name, "job_title": title, "phone": "9655100",
                       "base_salary": "350.000", "hire_date": "2025-03-01"})

    equipment = [("شاحنة توصيل 1", "سيارة توصيل", "120000.000"),
                 ("شاحنة توصيل 2", "سيارة توصيل", "95000.000"),
                 ("مجمدة كبيرة", "أجهزة تبريد وتخزين", "8000.000"),
                 ("فرن كهربائي", "معدات مطبخ", "6500.000")]
    for name, kind, cost in equipment:
        rd.save_equipment({"name": name, "category": kind,
                           "purchase_date": "2025-01-15", "cost": cost})

    products = [("منسف دجاج", "أطباق رئيسية", "3.100", "5.000"),
                ("كبسة لحم", "أطباق رئيسية", "3.800", "6.000"),
                ("مقبلات بقسماط", "مقبلات وسلات", "1.200", "2.500"),
                ("كنافة", "حلويات", "1.500", "2.750"),
                ("مشاء عربية", "مقبلات وسلات", "0.900", "1.800")]
    for name, cat, cost, sale in products:
        rd.save_product({"name": name, "category": cat, "unit": "حصة / فرد",
                         "cost": cost, "sale_price": sale})

    # ---------- مصاريف التأسيس (مرة واحدة) ----------
    rd.save_setup_expense({"date": "2025-01-20", "type": "معدات مطبخ",
                           "description": "تجهيز المطبخ الأساسي", "cost": "12000.000"})
    rd.save_setup_expense({"date": "2025-01-22", "type": "تراخيص وسائل وجاءة",
                           "description": "تأثيث التأصايح والمعاير", "cost": "8000.000"})

    # ---------- شهر تشغيل كامل لكل شهر من الأشهر الستة ----------
    for index, month in enumerate(months):
        scale = 1.0 + index * 0.06        # نمو تدريجي حتى تظهر اتجاهات في الرسوم
        # الشهر الجاري يؤخذ بتاريخ اليوم المحديث ولا تاريخُ مستقبلي
        stamp = today if index == len(months) - 1 else "%s-%02d" % (month, min(5 + index, 20))

        # مشتريات ومصاريف ثابتة
        for kind, item, qty, unit, cost in MONTHLY_PURCHASES:
            rd.save_purchase({"date": stamp, "type": kind, "item": item,
                              "quantity": str(int(float(qty) * scale)), "unit": unit,
                              "unit_cost": cost, "supplier": "مورد معتمد"})
        for kind, amount in MONTHLY_FIXED:
            rd.save_monthly_expense({"month": month, "type": kind, "amount": amount, "notes": ""})
        rd.save_petty_cash({"date": stamp, "type": "وقود وتوصيل",
                            "description": "وقود السائق", "amount": "45.000"})

        # رواتب
        for name, base in MONTHLY_SALARIES:
            rd.save_salary({"staff": name, "month": month, "base_salary": base,
                            "bonuses": "25.000", "advances": "0", "deductions": "0",
                            "paid": "نعم" if index < len(months) - 1 else "لا"})

        # طلبات مؤسسية ثم إصدار فاتورة لها
        order_ids = []
        for meal, price, qty in MONTHLY_MEALS:
            customer = customers[index % 3][0]
            rd.save_institutional_order({
                "date": stamp, "customer": customer, "meal_type": meal,
                "frequency": "يومي", "quantity": str(int(qty * scale)),
                "unit_price": price, "delivery_location": "مقر العميل",
                "delivery_time": "11:30", "notes": "تمة عن الخدمة"})
            order_ids.append(rd.load_institutional_orders()[-1])

        # مناسبة واحدة شهرياً تدخل في الفاتورة
        ev_customer, ev_type, guests, ev_price = MONTHLY_EVENT
        rd.save_event({"event_date": stamp, "customer": ev_customer,
                       "event_type": ev_type, "guests_count": str(int(guests * scale)),
                       "menu_description": "مقبلات + رئيسي + حلويات",
                       "unit_price": ev_price, "location": "قاعة الوصل",
                       "delivery_time": "18:00", "deposit": "500.000" if index % 2 == 0 else "0"})
        event = rd.load_events()[-1]

        invoice = rd.create_invoice_for_customer(
            customers[0][0], [o["id"] for o in order_ids], [event["id"]])
        # الفاتورة تُدون بتاريخ يوم إصدارها، فنعدها بتاريخ شهرها لتنوير الرسم بياني
        invoice["date"] = stamp
        rd.save_invoice(invoice, editing_invno=invoice["invoice_no"])
        if index == len(months) - 1:
            # الشهر الحالي: فاتورتان إضافيتان ودفعة جزئية لإظهار التحصيل
            rd.create_invoice_for_customer(customers[1][0], [order_ids[1]["id"]], [event["id"]])
            rd.create_invoice_for_customer(customers[2][0], [order_ids[2]["id"]], [])
            rd.save_payment({"date": today, "invoice_no": invoice["invoice_no"],
                             "customer": customers[0][0], "amount": "1500.000",
                             "method": "تحويل بنكي", "notes": "دفعة أولى"})

    # تثبيت الفواتور مرتبة بترتيب رقمها لأن تظهر الجدول الأخير في سجل الفواتور (التحديث يحذف الصف ويعيده)
    for inv in sorted(rd.load_invoices(), key=lambda r: str(r["invoice_no"])):
        rd.save_invoice(inv, editing_invno=inv["invoice_no"])

    # طلبات اليوم لكي تظهر عداد وجبه في شاشة الرئيسة
    for meal, price, qty in MONTHLY_MEALS:
        rd.save_institutional_order({
            "date": today, "customer": customers[3][0], "meal_type": meal,
            "frequency": "يومي", "quantity": str(qty),
            "unit_price": price, "delivery_location": "مقر العميل",
            "delivery_time": "11:30", "notes": "تمة عن المحفظة"})


def find_scroll_frame(widget):
    """يبحث في شجرة الواجهة عن إطار التمرير المستخدم في شاشة التقارير."""
    from ui.theme import ScrollableFrame
    if isinstance(widget, ScrollableFrame):
        return widget
    for child in widget.winfo_children():
        found = find_scroll_frame(child)
        if found is not None:
            return found
    return None


def scroll_to(widget, fraction):
    """تمرير إطار قابل للتمرير إلنسبة من محتواه (0 = أعلى، 1 = أسفل)."""
    frame = find_scroll_frame(widget)
    if frame is not None:
        frame._canvas.yview_moveto(fraction)
        return True
    return False



def scroll_charts_to_top(window):
    """يمرّر حتى تعرض باطة الرسوم البيانية إلى أعلى مشاهدة العرض، لأن تظهر الصورة من اقطعها."""
    frame = find_scroll_frame(window)
    charts = getattr(window, "_charts_canvas", None)
    if frame is None or charts is None:
        return False
    canvas = frame._canvas
    # ثوحة matplotlib ليس عنصر تكنتر، فنأخذ وجه Tkinter المحفوظ بها
    charts_tk = charts.get_tk_widget() if hasattr(charts, "get_tk_widget") else charts
    bbox = canvas.bbox("all")
    view_h = canvas.winfo_height()
    total = bbox[3] if bbox else 0
    if total <= view_h:
        return False
    offset = charts_tk.winfo_rooty() - canvas.winfo_rooty()
    canvas.yview_moveto(min(max(offset / float(total - view_h), 0.0), 1.0))
    return True



def grab_window(hwnd, path):
    """
    يلتقط محتوى النافذة مباشرة عبر PrintWindow بدل تصوير الشاشة.

    تصوير الشاشة لا يصلح هنا: لو كانت هناك نافذة أخرى فوق التطبيق (متصفح مثلاً)
    لتقطها الصورة كلها. هذه الطريقة ترسم نافذة التطبيق نفسها فقط، فيكون
    الناتج نظيفاً مهما كان ما يحدث على الشاشة.
    """
    import ctypes
    import ctypes.wintypes as wintypes
    from PIL import Image

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    if width <= 0 or height <= 0:
        raise RuntimeError("حجم النافذة غير صالح")

    hwnd_dc = user32.GetWindowDC(hwnd)
    mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
    gdi32.SelectObject(mem_dc, bitmap)
    user32.PrintWindow(hwnd, mem_dc, 2)          # PW_RENDERFULLCONTENT

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG),
                    ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]

    header = BITMAPINFOHEADER()
    header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    header.biWidth = width
    header.biHeight = -height                    # من الأعلى للأسفل
    header.biPlanes = 1
    header.biBitCount = 32
    header.biCompression = 0                     # BI_RGB

    buffer = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(mem_dc, bitmap, 0, height, buffer, ctypes.byref(header), 0)

    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hwnd, hwnd_dc)

    Image.frombuffer("RGB", (width, height), buffer, "raw", "BGRX", 0, 1).save(path)
    return width, height


def capture():
    """يعرض كل شاشة على حدة ويلتقط صورة لها."""
    if not os.path.isdir(SHOTS_DIR):
        os.makedirs(SHOTS_DIR, exist_ok=True)

    window = app.RestaurantApp()
    window.geometry("%dx%d+0+0" % (WIDTH, HEIGHT))
    window.update_idletasks()
    window.update()

    for filename, key, sub_index in SCREENS:
        window.show_page(key, sub_index)
        window.update_idletasks()
        window.update()

        if key == "reports":
            window.show_financial_summary()   # نملأ الملخص قبل الالتقاط
            window.update_idletasks()
            window.update()

        if key == "invoices":
            # القوائم الفرعية تُملأ حسب العميل المختار، فنختار عميلاً
            # لديه طلبات غير مفوترة حتى لا تظهر الشاشة فارغة في الصورة
            pending = [c["name"] for c in rd.load_customers()
                       if rd.unbilled_institutional_orders_for_customer(c["name"])]
            if pending:
                window.refresh_customer_combo()
                window.inv_customer_var.set(pending[0])
                window.refresh_unbilled_lists()
                window.update_idletasks()
                window.update()

        time.sleep(0.7)                      # نمهل Tkinter قبل الالتقاط

        if key == "reports":
            # نمرّر بعد استقرار الرسم (الرسوم البيانية تُعاد بناؤها بتأخير
            # وتُعيد التمرير إلى الأعلى إن حرّكناه قبل ذلك)
            scroll_charts_to_top(window)
            window.update_idletasks()
            window.update()
            time.sleep(0.4)

        # نثبّت المقاس قبل كل لقطة: بعض الشاشات قد تطلب اتساعاً أكبر
        # فيكبر النافذة، ونريد صوراً كلها بمقاس واحد
        window.geometry("%dx%d+0+0" % (WIDTH, HEIGHT))
        window.update_idletasks()
        window.update()

        path = os.path.join(SHOTS_DIR, filename)
        w, h = grab_window(window.winfo_id(), path)
        print("saved %s (%dx%d)" % (path, w, h))

    window.destroy()


def main():
    seed()
    capture()
    print("تم حفظ %d صورة في %s" % (len(SCREENS), SHOTS_DIR))
    return 0


if __name__ == "__main__":
    sys.exit(main())
