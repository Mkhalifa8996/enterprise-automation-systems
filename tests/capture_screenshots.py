# -*- coding: utf-8 -*-
"""يلتقط لقطات شاشة لكل شاشات التطبيق في مجلد screenshots/.

يُشغَّل مرة واحدة لتوليد الصور المستخدمة في README:
    python tests/capture_screenshots.py

يستخدم نافذة التطبيق الحقيقية على بيانات تجريبية، ويلتقط كل تبويب
ونافذة الفاتورة عبر أداة PrintWindow في ويندوز.
"""

import ctypes
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "screenshots")

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetProcessDPIAware()


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", ctypes.c_uint32 * 3)]


def window_rect(hwnd):
    """مستطيل النافذة على الشاشة."""
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def paint(hwnd, path):
    """يرسم محتوى النافذة مباشرة عبر PrintWindow (يلتقط التطبيق وحده).

    PrintWindow يرسم النافذة المطلوبة فقط دون受影响 بما خلفها، وهو آمن
    بخلاف التقاط الشاشة الذي قد يلتقط نوافذ شخصية.
    """
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    if width <= 0 or height <= 0:
        raise RuntimeError(f"invalid window size for {path}")

    hdc = user32.GetWindowDC(hwnd)
    mem_dc = gdi32.CreateCompatibleDC(hdc)
    bitmap = gdi32.CreateCompatibleBitmap(hdc, width, height)
    gdi32.SelectObject(mem_dc, bitmap)
    ok = user32.PrintWindow(hwnd, mem_dc, 2)   # PW_RENDERFULLCONTENT

    info = BITMAPINFO()
    info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    info.bmiHeader.biWidth = width
    info.bmiHeader.biHeight = -height
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = 0

    buf = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(info), 0)

    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hwnd, hdc)

    if not ok:
        raise RuntimeError(f"PrintWindow failed for {path}")

    from PIL import Image

    image = Image.frombuffer("RGBA", (width, height), buf, "raw", "BGRA", 0, 1)
    image.convert("RGB").save(path, "PNG")
    return path


def capture(widget, path):
    """يضمن ظهور النافذة فعلياً ثم يحفظ لقطة لها.

    بدون انتظار الرسم الفعلي (Expose) قد تبقى بعض العناصر مثل جداول
    Treeview بلا صفوف مرسومة في لقطة PrintWindow رغم وجود بياناتها.
    """
    widget.deiconify()
    widget.lift()
    for _ in range(5):
        widget.update_idletasks()
        widget.update()
    return paint(hwnd_of(widget), path)


def hwnd_of(widget):
    """معرّف النافذة الأصلي لعنصر Tk (أو إطاره إذا كان له إطار نظام)."""
    inner = int(widget.winfo_id())
    parent = user32.GetParent(inner)
    return parent or inner


def shot(widget, filename):
    """يحدّث العنصر ثم يحفظ لقطة له."""
    widget.update_idletasks()
    widget.update()
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    capture(widget, path)
    print("saved", filename)
    return path
def anonymise_path_labels(root):
    """يستبدل مسار التخزين الظاهر في الترويسة بنص محايد.

    التطبيق يعرض المسار الحقيقي لأنه معلومة مفيدة للمستخدم، لكن اللقطات
    المنشورة في README لا ينبغي أن تكشف مسار الجهاز أو اسم المجلد المحلي.
    """
    def walk(widget):
        try:
            if widget.winfo_class() in ("Label", "TLabel"):
                text = widget.cget("text")
                if isinstance(text, str) and "📁" in text:
                    widget.config(text="\U0001F4C1  data.xlsx  (قاعدة البيانات ونسخة إكسل)")
        except Exception:
            pass
        for child in widget.winfo_children():
            walk(child)

    walk(root)


def seed_demo_data():
    """يبني بيانات تجريبية تمثّل الاستخدام الحقيقي (بأسماء شركات عامة)."""
    import tempfile

    import customs_clearance_billing.config as config
    import customs_clearance_billing.data as data

    tmp = tempfile.mkdtemp(prefix="ccb_shots_")
    config.DB_FILE = os.path.join(tmp, "shots.db")
    config.DATA_FILE = os.path.join(tmp, "shots.xlsx")
    data._migration_done = False

    from customs_clearance_billing.data import save_customer, save_invoice, save_payment

    customers = [
        {"name": "Al Estidama Co.", "phone": "+965 6000 0000",
         "address": "Hawalli, Kuwait", "notes": "عميل دائم", "company_code": "01"},
        {"name": "Gulf Shipping", "phone": "+965 2222 1111",
         "address": "Shuwaikh, Kuwait", "notes": "", "company_code": "02"},
        {"name": "National Trade", "phone": "+965 3333 4444",
         "address": "Mangaf, Kuwait", "notes": "", "company_code": "03"},
    ]
    for c in customers:
        save_customer(c)

    def items(dinar, fils):
        return [{"label": "", "labelEn": "", "dinar": dinar if i == 0 else 0,
                 "fils": fils if i == 0 else 0} for i in range(24)]

    invoices = [
        ("010001", "2026-07-11", "Al Estidama Co.", "434343", "الشعب", "2", 182.0),
        ("010002", "2026-07-11", "Al Estidama Co.", "223232", "الشعب", "1", 696.066),
        ("020001", "2026-07-15", "Gulf Shipping", "34343", "الشويخ", "4", 435.0),
        ("010003", "2026-07-30", "Al Estidama Co.", "544", "الشعب", "3", 865.006),
        ("010004", "2026-07-30", "Al Estidama Co.", "3232", "الدعية", "2", 160.0),
        ("020002", "2026-08-02", "Gulf Shipping", "77120", "الشويخ", "5", 1240.5),
        ("030001", "2026-08-05", "National Trade", "90901", "المنقف", "1", 512.25),
        ("010005", "2026-08-09", "Al Estidama Co.", "61122", "الشعب", "2", 330.0),
    ]
    for invno, date, customer, declno, port, cnt, total in invoices:
        dinar = int(total)
        fils = int(round((total - dinar) * 1000))
        save_invoice({
            "invno": invno, "date": date, "customer": customer, "declno": declno,
            "decldate": date, "port": port, "containercount": cnt,
            "goodstype": "بضائع عامة", "origin": "الكويت", "notes": "",
            "items": items(dinar, fils),
        })

    payments = [
        ("010001", "Al Estidama Co.", "2026-07-30", 600.0, "دفعة نقدية", ["010001"]),
        ("010002", "Al Estidama Co.", "2026-07-31", 865.006, "", ["010003"]),
        ("010003", "Al Estidama Co.", "2026-08-01", 160.0, "شيك", ["010004"]),
        ("020001", "Gulf Shipping", "2026-08-03", 400.0, "", ["020001"]),
    ]
    for pid, customer, date, amount, notes, applied in payments:
        save_payment({"id": pid, "customer": customer, "date": date,
                      "amount": amount, "notes": notes,
                      "applied_invoices": applied})


def main():
    """يبني بيانات تجريبية ويلتقط كل الشاشات."""
    seed_demo_data()

    from customs_clearance_billing.ui.app import InvoiceApp
    from customs_clearance_billing.ui.invoice_form import InvoiceForm

    app = InvoiceApp()
    app.geometry("1280x760+40+40")
    app.update()
    anonymise_path_labels(app)

    app.refresh_dashboard()
    shot(app, "01-dashboard.png")

    app.notebook.select(app.tab_invoices)
    app.refresh_invoice_list()
    shot(app, "02-invoices.png")

    app.notebook.select(app.tab_customers)
    app.refresh_customer_list()
    shot(app, "03-customers.png")

    # شاشة الدفعات كثيفة، فنمنحها نافذة أطول قليلاً كي تظهر كل الجداول
    app.geometry("1360x900+40+40")
    app.notebook.select(app.tab_payments)
    app.refresh_payments_list()
    app.refresh_balances()
    app.p_customer.set("Al Estidama Co.")
    app._on_payment_customer_changed()
    app.update_idletasks()
    app.update()

    # جدول التخصيص قد لا يُرسم مع أول نداء رسم، فنترك Tk يستقرّ ثم نُعيد
    # ملء الجدول قبل الالتقاط مباشرة.
    app.p_customer.set("")
    app._on_payment_customer_changed()
    app.p_customer.set("Al Estidama Co.")
    app._on_payment_customer_changed()
    for _ in range(4):
        app.update_idletasks()
        app.update()
    shot(app, "04-payments.png")
    app.geometry("1280x760+40+40")
    app.update()

    form = InvoiceForm(app, invoice=None)
    form.geometry("980x760+120+80")
    form.vars["customer"].set("Al Estidama Co.")
    form._update_invno_for_customer()
    form.item_dinar_vars[0].set("250")
    form.item_fils_vars[0].set("750")
    form._update_total()
    form.update()
    shot(form, "05-invoice-form.png")

    form.destroy()
    app.destroy()
    print("\nAll screenshots saved to", OUT_DIR)


if __name__ == "__main__":
    main()
