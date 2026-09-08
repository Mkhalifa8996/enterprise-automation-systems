# -*- coding: utf-8 -*-
"""
نظام فواتير - شركة الاستدامة لتقديم الخدمات اللوجستية
برنامج سطح مكتب (Python + Tkinter) يقوم بتخزين جميع البيانات
مباشرة داخل ملف إكسل (data.xlsx) بجانب البرنامج.

طريقة التشغيل:
    1) تأكد من تثبيت بايثون 3.9 أو أحدث (على لينكس قد تحتاج أيضاً: sudo apt install python3-tk)
    2) ثبّت المكتبة المطلوبة مرة واحدة فقط:
           pip install openpyxl
       ولمظهر حديث أكثر (أزرار وألوان مسطّحة)، يمكن تثبيت مكتبة اختيارية إضافية:
           pip install ttkbootstrap
       (البرنامج يعمل بشكل كامل بدونها أيضاً، لكن بمظهر tkinter التقليدي المُحسَّن يدوياً.)
    3) شغّل البرنامج:
           python invoice_desktop_app.py

عند أول تشغيل سيتم إنشاء ملف data.xlsx تلقائياً في نفس المجلد بجانب
هذا الملف، وكل عملية إضافة/تعديل/حذف تُكتب مباشرة على القرص في هذا الملف.

يتطلب هذا الملف وجود invoice_data.py في نفس المجلد.
"""


import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv

from invoice_data import (
    DATA_FILE, ICON_FILE, LOGO_FILE, SERVICE_ITEMS, META_FIELDS, INVOICE_HEADERS, FONT_NAME, SaveError,
    get_tk_font,
    ensure_workbook, load_invoices, save_invoice, delete_invoice,
    invoice_dict_to_row,
    load_customers, save_customer, delete_customer, safe_int, safe_float,
    load_payments, save_payment, delete_payment, customer_balances,
    normalize_company_code, find_customer_by_company_code, next_invoice_number,
    next_available_company_code, next_receipt_number,
    invoice_payment_status, get_dashboard_stats,
)
from datetime import date, datetime
import calendar
import os
import sys
import webbrowser
import tempfile
import html as html_module
import base64

# ttkbootstrap يمنح واجهة مسطّحة وحديثة المظهر (أزرار وألوان وبطاقات أنعم)؛
# هذه المكتبة اختيارية بالكامل — إن لم تكن مثبتة أو كانت ضمن حزمة مُجمَّعة
# فينبغي استخدام واجهة tkinter الافتراضية للحفاظ على التشغيل في ملف
# تنفيذي مستقل.
try:
    import ttkbootstrap as tbs
    if getattr(sys, 'frozen', False):
        raise ImportError('Use Tkinter fallback in frozen executable')
    HAS_BOOTSTRAP = True
    _BaseWindow = tbs.Window
except Exception:
    HAS_BOOTSTRAP = False
    _BaseWindow = tk.Tk

# ------------------------------------------------------------------
# لوحة الألوان الحديثة (متوافقة مع هوية الشركة: كحلي داكن + ذهبي)
# ------------------------------------------------------------------
COL_BG = "#EEF2F7"          # خلفية عامة فاتحة وهادئة (رمادي مزرق ناعم)
COL_BG_ALT = "#E4EAF2"      # درجة أغمق قليلاً تُستخدم للأشرطة الجانبية والرؤوس
COL_CARD = "#FFFFFF"        # خلفية البطاقات
COL_CARD_SOFT = "#FAFBFD"   # خلفية بديلة ناعمة داخل البطاقات (رؤوس الجداول ونحوها)
COL_NAVY = "#0F2B46"        # اللون الأساسي (الهوية)
COL_NAVY_DARK = "#081726"
COL_NAVY_SOFT = "#E8EEF5"   # درجة فاتحة جداً من الكحلي (خلفيات تمييز ناعمة)
COL_GOLD = "#C99A3D"        # لون التمييز (الهوية)
COL_GOLD_DARK = "#A97D28"
COL_GOLD_SOFT = "#FBF3E1"
COL_TEXT = "#1A2331"
COL_SUBTEXT = "#67748A"
COL_MUTED = "#98A4B5"
COL_BORDER = "#E1E7EF"
COL_BORDER_SOFT = "#EDF1F6"
COL_DANGER = "#C0342A"
COL_DANGER_BG = "#FCEBEA"
COL_SUCCESS = "#1E8449"
COL_SUCCESS_BG = "#E9F7EF"
COL_WARN = "#B5750B"
COL_WARN_BG = "#FEF5E3"
COL_ROW_ALT = "#F5F8FC"     # لون تظليل الصفوف الزوجية في الجداول (زيبرا)
COL_SELECT = "#DCE9F8"      # لون تحديد الصف في الجداول

ARABIC_MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                 "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
ARABIC_WEEKDAYS = ["اثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة", "سبت", "أحد"]

ARABIC_UNITS = ["صفر", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة",
                "عشرة", "أحد عشر", "اثنا عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر", "ستة عشر", "سبعة عشر", "ثمانية عشر", "تسعة عشر"]
ARABIC_TENS = {
    20: "عشرون", 30: "ثلاثون", 40: "أربعون", 50: "خمسون", 60: "ستون",
    70: "سبعون", 80: "ثمانون", 90: "تسعون"
}
ARABIC_HUNDREDS = {
    100: "مائة", 200: "مائتان", 300: "ثلاثمائة", 400: "أربعمائة", 500: "خمسمائة",
    600: "ستمائة", 700: "سبعمائة", 800: "ثمانمائة", 900: "تسعمائة"
}


def arabic_int_to_words(n):
    if n < 0:
        return "سالب " + arabic_int_to_words(-n)
    if n < 20:
        return ARABIC_UNITS[n]
    if n < 100:
        if n in ARABIC_TENS:
            return ARABIC_TENS[n]
        unit = n % 10
        tens = n - unit
        return f"{ARABIC_UNITS[unit]} و {ARABIC_TENS[tens]}"
    if n < 1000:
        if n in ARABIC_HUNDREDS:
            return ARABIC_HUNDREDS[n]
        hundreds = n - (n % 100)
        remainder = n % 100
        return f"{ARABIC_HUNDREDS[hundreds]} و {arabic_int_to_words(remainder)}"
    if n < 1000000:
        thousands = n // 1000
        remainder = n % 1000
        if thousands == 1:
            prefix = "ألف"
        elif thousands == 2:
            prefix = "ألفان"
        elif 3 <= thousands <= 10:
            prefix = f"{arabic_int_to_words(thousands)} آلاف"
        else:
            prefix = f"{arabic_int_to_words(thousands)} ألف"
        return f"{prefix} و {arabic_int_to_words(remainder)}" if remainder else prefix
    if n < 1000000000:
        millions = n // 1000000
        remainder = n % 1000000
        if millions == 1:
            prefix = "مليون"
        elif millions == 2:
            prefix = "مليونان"
        elif 3 <= millions <= 10:
            prefix = f"{arabic_int_to_words(millions)} ملايين"
        else:
            prefix = f"{arabic_int_to_words(millions)} مليون"
        return f"{prefix} و {arabic_int_to_words(remainder)}" if remainder else prefix
    return str(n)


def arabic_currency_words(amount):
    try:
        total_fils = round(float(amount) * 1000)
    except (TypeError, ValueError):
        return ""
    dinars = total_fils // 1000
    fils = total_fils % 1000
    if dinars == 0 and fils == 0:
        return "صفر دينار كويتي فقط لا غير"
    parts = []
    if dinars:
        parts.append(f"{arabic_int_to_words(dinars)} دينار كويتي")
    if fils:
        parts.append(f"{arabic_int_to_words(fils)} فلساً")
    return " و ".join(parts) + " فقط لا غير"


def english_int_to_words(n):
    """Convert integer n (0..999999999) to English words (simple)."""
    to19 = ['zero','one','two','three','four','five','six','seven','eight','nine',
            'ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen',
            'seventeen','eighteen','nineteen']
    tens = ['','','twenty','thirty','forty','fifty','sixty','seventy','eighty','ninety']

    def _under_thousand(num):
        if num < 20:
            return to19[num]
        if num < 100:
            t = num // 10
            r = num % 10
            return tens[t] + ('' if r == 0 else ' ' + to19[r])
        h = num // 100
        r = num % 100
        return to19[h] + ' hundred' + ('' if r == 0 else ' ' + _under_thousand(r))

    if n < 0:
        return 'minus ' + english_int_to_words(-n)
    if n < 1000:
        return _under_thousand(n)
    if n < 1000000:
        k = n // 1000
        r = n % 1000
        return _under_thousand(k) + ' thousand' + ('' if r == 0 else ' ' + _under_thousand(r))
    if n < 1000000000:
        m = n // 1000000
        r = n % 1000000
        return _under_thousand(m) + ' million' + ('' if r == 0 else ' ' + english_int_to_words(r))
    return str(n)


def english_currency_words(amount):
    try:
        total_fils = round(float(amount) * 1000)
    except (TypeError, ValueError):
        return ""
    dinars = total_fils // 1000
    fils = total_fils % 1000
    if dinars == 0 and fils == 0:
        return 'zero Kuwaiti dinars only'
    parts = []
    if dinars:
        parts.append(f"{english_int_to_words(dinars)} Kuwaiti dinar{'s' if dinars != 1 else ''}")
    if fils:
        parts.append(f"{english_int_to_words(fils)} fils")
    return ' and '.join(parts) + ' only'


def fmt_fils3(v):
    if v in (None, ""):
        return ""
    try:
        return f"{int(v):03d}"
    except (TypeError, ValueError):
        return str(v)


def open_date_picker(parent, string_var):
    """يفتح نافذة تقويم صغيرة لاختيار تاريخ بدلاً من كتابته يدوياً،
    ويكتب النتيجة داخل string_var بصيغة YYYY-MM-DD."""
    try:
        cur = datetime.strptime((string_var.get() or "").strip(), "%Y-%m-%d")
    except (ValueError, TypeError):
        cur = datetime.today()

    BG = "#F7F9FC"
    win = tk.Toplevel(parent)
    win.title("اختر التاريخ")
    win.transient(parent)
    win.grab_set()
    win.resizable(False, False)
    win.configure(bg=BG, highlightthickness=1, highlightbackground="#D6DEE8")

    state = {"year": cur.year, "month": cur.month}

    top_bar = tk.Frame(win, bg="#0F2B46", height=6)
    top_bar.pack(fill="x")

    header = tk.Frame(win, bg=BG)
    header.pack(fill="x", padx=10, pady=(10, 6))
    tk.Button(header, text="◀", width=3, relief="flat", bg=BG, fg="#0F2B46",
              activebackground="#E8EEF5", cursor="hand2", command=lambda: change_month(1)).pack(side="right")
    tk.Button(header, text="▶", width=3, relief="flat", bg=BG, fg="#0F2B46",
              activebackground="#E8EEF5", cursor="hand2", command=lambda: change_month(-1)).pack(side="left")
    title_lbl = tk.Label(header, font=get_tk_font(11, "bold"), bg=BG, fg="#0F2B46")
    title_lbl.pack(side="left", expand=True, fill="x")

    grid = tk.Frame(win, bg=BG)
    grid.pack(padx=10, pady=(0, 6))

    def render():
        for w in grid.winfo_children():
            w.destroy()
        title_lbl.config(text=f"{ARABIC_MONTHS[state['month']-1]} {state['year']}")
        for i, wd in enumerate(ARABIC_WEEKDAYS):
            tk.Label(grid, text=wd, font=get_tk_font(8, "bold"), width=4, bg=BG, fg="#6B7A8D").grid(row=0, column=i, padx=1, pady=(0, 4))
        cal = calendar.Calendar(firstweekday=0)
        row = 1
        for week in cal.monthdayscalendar(state["year"], state["month"]):
            for col, day in enumerate(week):
                if day == 0:
                    tk.Label(grid, text="", width=4, bg=BG).grid(row=row, column=col)
                else:
                    is_today = (state["year"], state["month"], day) == (cur.year, cur.month, cur.day)
                    b = tk.Button(grid, text=str(day), width=4, relief="flat", cursor="hand2",
                                  font=get_tk_font(9, "bold" if is_today else "normal"),
                                  bg="#C99A3D" if is_today else BG, fg="white" if is_today else "#1C2530",
                                  activebackground="#E8EEF5",
                                  command=lambda d=day: select_day(d))
                    b.grid(row=row, column=col, padx=1, pady=1)
            row += 1

    def change_month(delta):
        m = state["month"] + delta
        y = state["year"]
        if m < 1:
            m, y = 12, y - 1
        elif m > 12:
            m, y = 1, y + 1
        state["month"], state["year"] = m, y
        render()

    def select_day(d):
        string_var.set(f"{state['year']:04d}-{state['month']:02d}-{d:02d}")
        win.destroy()

    def go_today():
        t = datetime.today()
        string_var.set(t.strftime("%Y-%m-%d"))
        win.destroy()

    render()
    tk.Button(win, text="📅 اليوم", relief="flat", bg="#0F2B46", fg="white", cursor="hand2",
              font=get_tk_font(9, "bold"), activebackground="#0B2036", activeforeground="white",
              padx=12, pady=5, command=go_today).pack(pady=(0, 10))


def build_date_field(parent, var):
    """يبني صفاً يحوي حقل إدخال تاريخ نصي بجانبه زر تقويم (📅) لفتح منتقي التاريخ."""
    row = tk.Frame(parent)
    tk.Button(row, text="📅", width=3, relief="flat", bg=COL_NAVY_SOFT, fg=COL_NAVY,
              activebackground=COL_NAVY, activeforeground="white", cursor="hand2",
              command=lambda: open_date_picker(row.winfo_toplevel(), var)).pack(side="right", padx=(0, 4), ipady=2)
    entry = tk.Entry(row, textvariable=var, font=get_tk_font(10), justify="right",
                      relief="solid", bd=1, highlightthickness=1, highlightbackground=COL_BORDER)
    entry.pack(side="right", fill="x", expand=True, ipady=3)
    return row, entry


class InvoiceApp(_BaseWindow):
    def __init__(self):
        if HAS_BOOTSTRAP:
            super().__init__(themename="flatly")
        else:
            super().__init__()
        self.title("نظام فواتير  —  شركة الاستدامة لتقديم الخدمات اللوجستية")
        self.geometry("1280x760")
        self.configure(bg=COL_BG)
        # حد أدنى لحجم النافذة يكفي لعرض كل أزرار وحقول الشريط العلوي (خصوصاً صف
        # التصفية في تبويب الفواتير) دون أن يتم قصّها/إخفاؤها عند تصغير النافذة.
        self.minsize(1180, 680)

        self._style = ttk.Style(self)
        self._setup_style()

        self.configure(bg=COL_BG)
        self.option_add("*Font", get_tk_font(10))
        self.option_add("*Entry.Justify", "right")
        self.option_add("*TCombobox*Listbox.Font", get_tk_font(10))

        try:
            ensure_workbook()
        except SaveError as e:
            messagebox.showerror("خطأ في الحفظ", str(e))
            self.destroy()
            return

        # أيقونة نافذة التطبيق (تظهر في شريط العنوان وشريط المهام)
        if os.path.exists(ICON_FILE):
            try:
                self._icon_img = tk.PhotoImage(file=ICON_FILE)
                self.iconphoto(True, self._icon_img)
            except tk.TclError:
                pass  # صيغة الصورة غير مدعومة من Tk المثبت؛ يُتجاهل بأمان

        header = tk.Frame(self, bg=COL_NAVY, height=72)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        # شريط رفيع بلون الهوية الذهبي أسفل الرأس لإضافة لمسة تصميمية عصرية
        tk.Frame(self, bg=COL_GOLD, height=3).pack(fill="x", side="top")

        brand_frame = tk.Frame(header, bg=COL_NAVY)
        brand_frame.pack(side="right", padx=(4, 22), pady=10)
        brand_frame.grid_columnconfigure(0, weight=0)
        brand_frame.grid_columnconfigure(1, weight=0)
        brand_frame.grid_columnconfigure(2, weight=0)

        if os.path.exists(LOGO_FILE):
            try:
                logo_full = tk.PhotoImage(file=LOGO_FILE)
                factor = max(1, logo_full.width() // 52)
                self._header_logo_img = logo_full.subsample(factor, factor)
                tk.Label(brand_frame, image=self._header_logo_img, bg=COL_NAVY).grid(row=0, rowspan=2, column=2, padx=(14, 0))
            except tk.TclError:
                tk.Label(brand_frame, text="🚢 ✈️ 🚚", bg=COL_NAVY, fg=COL_GOLD,
                         font=get_tk_font(15)).grid(row=0, rowspan=2, column=2, padx=(14, 0))
        else:
            tk.Label(brand_frame, text="🚢 ✈️ 🚚", bg=COL_NAVY, fg=COL_GOLD,
                     font=get_tk_font(15)).grid(row=0, rowspan=2, column=2, padx=(14, 0))

        tk.Label(brand_frame, text="شركة الاستدامة لتقديم الخدمات اللوجستية",
                 bg=COL_NAVY, fg="white", font=get_tk_font(15, "bold"), justify="right").grid(row=0, column=0, columnspan=2, sticky="e")
        tk.Label(brand_frame, text="AL ESTIDAMA LOGISTICS SERVICES CO.",
                 bg=COL_NAVY, fg=COL_GOLD, font=get_tk_font(9), justify="right").grid(row=1, column=0, columnspan=2, sticky="e", pady=(2, 0))

        info_frame = tk.Frame(header, bg=COL_NAVY)
        info_frame.pack(side="right", padx=20)
        tk.Label(info_frame, text="نظام إدارة الفواتير", bg=COL_NAVY, fg="white",
                 font=get_tk_font(11, "bold")).pack(anchor="w")
        tk.Label(info_frame, text=f"📁 {DATA_FILE}",
                 bg=COL_NAVY, fg="#8FA3B8", font=get_tk_font(8)).pack(anchor="w", pady=(2, 0))

        content = tk.Frame(self, bg=COL_BG)
        content.pack(fill="both", expand=True, padx=16, pady=16)

        sidebar = tk.Frame(content, bg=COL_BG, width=220)
        sidebar.pack(side="right", fill="y", padx=(14, 0))
        sidebar.pack_propagate(False)

        self.notebook = ttk.Notebook(content)
        self.notebook.pack(side="left", fill="both", expand=True)

        self.tab_dashboard = ttk.Frame(self.notebook, style="TFrame")
        self.tab_invoices = ttk.Frame(self.notebook, style="TFrame")
        self.tab_customers = ttk.Frame(self.notebook, style="TFrame")
        self.tab_payments = ttk.Frame(self.notebook, style="TFrame")
        # نُبقي التبويبات الفعلية بلا رؤوس ظاهرة (نستخدم القائمة الجانبية للتنقل بدلاً منها)
        self.notebook.add(self.tab_dashboard, text="لوحة المعلومات")
        self.notebook.add(self.tab_invoices, text="سجل الفواتير")
        self.notebook.add(self.tab_customers, text="العملاء")
        self.notebook.add(self.tab_payments, text="الدفعات والأرصدة")

        tk.Label(sidebar, text="التنقّل", bg=COL_BG, fg=COL_MUTED,
                 font=get_tk_font(8, "bold")).pack(anchor="e", padx=6, pady=(0, 6))

        self.nav_buttons = []
        nav_items = [
            (self.tab_dashboard, "🏠", "لوحة المعلومات"),
            (self.tab_invoices, "🧾", "سجل الفواتير"),
            (self.tab_customers, "👥", "العملاء"),
            (self.tab_payments, "💳", "الدفعات والأرصدة"),
        ]
        for tab, icon, title in nav_items:
            container = ttk.Frame(sidebar, style="NavCard.TFrame")
            container.pack(fill="x", pady=6)
            label = tk.Label(container, text=f"{title}   {icon}", bg=COL_CARD, fg=COL_NAVY,
                            font=get_tk_font(10, "bold"), padx=14, pady=12, anchor="e",
                            cursor="hand2")
            label.pack(fill="both", expand=True)
            label.bind("<Button-1>", lambda e, t=tab: self.notebook.select(t))
            label.bind("<Enter>", lambda e, c=container: self._on_nav_hover(c, True))
            label.bind("<Leave>", lambda e, c=container: self._on_nav_hover(c, False))
            self.nav_buttons.append((container, label, tab))

        tk.Frame(sidebar, bg=COL_BG, height=20).pack()
        version_lbl = tk.Label(sidebar, text="Al Estidama © 2026", bg=COL_BG, fg=COL_MUTED, font=get_tk_font(7))
        version_lbl.pack(side="bottom", pady=6)

        self._refresh_nav_selection()

        self._build_dashboard_tab()
        self._build_invoices_tab()
        self._build_customers_tab()
        self._build_payments_tab()

        self.refresh_invoice_list()
        self.refresh_customer_list()
        self.refresh_payments_list()
        self.refresh_balances()
        self.refresh_dashboard()

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _refresh_nav_selection(self):
        active = self.notebook.select()
        for container, label, tab in self.nav_buttons:
            is_active = str(tab) == active
            container.configure(style="ActiveNavCard.TFrame" if is_active else "NavCard.TFrame")
            label.configure(bg=COL_NAVY if is_active else COL_CARD,
                            fg="white" if is_active else COL_NAVY)

    def _on_nav_hover(self, container, entering):
        active = self.notebook.select()
        for c, label, tab in self.nav_buttons:
            if c is container and str(tab) != active:
                c.configure(style="HoverNavCard.TFrame" if entering else "NavCard.TFrame")
                return

    def _on_tab_changed(self, event=None):
        self._refresh_nav_selection()
        # تحديث تلقائي عند فتح كل تبويب حتى تظهر أحدث البيانات المضافة في التبويبات الأخرى
        current = self.notebook.select()
        if current == str(self.tab_payments):
            self.refresh_payments_list()
            self.refresh_balances()
        elif current == str(self.tab_dashboard):
            self.refresh_dashboard()
        elif current == str(self.tab_invoices):
            self.refresh_invoice_list()

    def _setup_style(self):
        if not HAS_BOOTSTRAP:
            try:
                self._style.theme_use("clam")
            except tk.TclError:
                pass
        self._style.configure("TFrame", background=COL_BG)
        self._style.configure("TNotebook", background=COL_BG, borderwidth=0)
        # التنقل الفعلي أصبح عبر القائمة الجانبية، لذا نُخفي شريط تبويبات الـ Notebook
        # الافتراضي تماماً (بدون تغيير أي منطق آخر يعتمد عليه).
        try:
            self._style.layout("TNotebook.Tab", [])
        except tk.TclError:
            pass
        self._style.configure("TNotebook.Tab", font=get_tk_font(10, "bold"), padding=(0, 0))

        self._style.configure("Card.TFrame", background=COL_CARD, relief="solid", bordercolor=COL_BORDER_SOFT, borderwidth=1)
        self._style.configure("Card.TLabel", background=COL_CARD, foreground=COL_TEXT, font=get_tk_font(10))
        self._style.configure("CardHeader.TLabel", background=COL_CARD, foreground=COL_NAVY, font=get_tk_font(11, "bold"))
        self._style.configure("CardSubtext.TLabel", background=COL_CARD, foreground=COL_SUBTEXT, font=get_tk_font(9))
        self._style.configure("Card.Soft.TFrame", background=COL_CARD_SOFT, relief="solid", bordercolor=COL_BORDER_SOFT, borderwidth=1)
        self._style.configure("NavCard.TFrame", background=COL_CARD, relief="flat", bordercolor=COL_BORDER_SOFT, borderwidth=1)
        self._style.configure("HoverNavCard.TFrame", background=COL_NAVY_SOFT, relief="flat", bordercolor=COL_BORDER_SOFT, borderwidth=1)
        self._style.configure("ActiveNavCard.TFrame", background=COL_NAVY, relief="flat", bordercolor=COL_BORDER_SOFT, borderwidth=1)
        self._style.configure("NavCard.TLabel", background=COL_CARD, foreground=COL_NAVY, font=get_tk_font(10, "bold"))
        self._style.configure("ActiveNavCard.TLabel", background=COL_NAVY, foreground="white", font=get_tk_font(10, "bold"))

        # ---- أزرار ----
        self._style.configure("Accent.TButton", font=get_tk_font(10, "bold"), foreground="white", background=COL_NAVY,
                              borderwidth=0, focusthickness=0, padding=(18, 10))
        self._style.map("Accent.TButton", background=[("active", COL_NAVY_DARK), ("pressed", COL_NAVY_DARK)])
        self._style.configure("Gold.TButton", font=get_tk_font(10, "bold"), foreground="white", background=COL_GOLD,
                              borderwidth=0, padding=(18, 10))
        self._style.map("Gold.TButton", background=[("active", COL_GOLD_DARK), ("pressed", COL_GOLD_DARK)])
        self._style.configure("Danger.TButton", font=get_tk_font(10, "bold"), foreground="white", background=COL_DANGER,
                              borderwidth=0, padding=(16, 9))
        self._style.map("Danger.TButton", background=[("active", "#8F1D17"), ("pressed", "#8F1D17")])
        self._style.configure("Ghost.TButton", font=get_tk_font(10), foreground=COL_NAVY, background=COL_CARD,
                              borderwidth=1, padding=(16, 9))
        self._style.map("Ghost.TButton", background=[("active", COL_NAVY_SOFT)], relief=[("pressed", "sunken")])
        self._style.configure("TButton", font=get_tk_font(10), padding=(14, 9), relief="flat")

        self._style.configure("Flat.TEntry", padding=(10, 8), relief="flat",
                              fieldbackground=COL_CARD, background=COL_CARD, foreground=COL_TEXT)
        self._style.map("Flat.TEntry",
                        fieldbackground=[("active", "white"), ("!disabled", COL_CARD)])
        self._style.configure("TCombobox", padding=(10, 8), relief="flat", foreground=COL_TEXT)

        # ---- الجداول (Treeview) بمظهر أنعم وصف مرتفع قليلاً لسهولة القراءة ----
        self._style.configure("Treeview", font=get_tk_font(10), rowheight=30, background=COL_CARD,
                              fieldbackground=COL_CARD, borderwidth=0, relief="flat")
        self._style.configure("Treeview.Heading", font=get_tk_font(9, "bold"),
                              background=COL_NAVY, foreground="white", relief="flat", padding=(10, 10))
        self._style.map("Treeview.Heading", background=[("active", COL_NAVY_DARK)])
        self._style.map("Treeview", background=[("selected", COL_SELECT)], foreground=[("selected", COL_TEXT)])
        self._style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        # نمط مطبق على جدول تخصيص الدفعة للفواتير فقط (صفوف مضغوطة لتوفير
        # المساحة العمودية داخل شريط الدفع)؛ يرث باقي الإعدادات من "Treeview".
        self._style.configure("CompactTree.Treeview", rowheight=18)
        self._style.configure("CompactTree.Treeview.Heading", padding=(6, 3))

        self._style.configure("TLabelframe", background=COL_BG, borderwidth=1, relief="solid", bordercolor=COL_BORDER)
        self._style.configure("TLabelframe.Label", font=get_tk_font(10, "bold"), background=COL_BG, foreground=COL_NAVY)

        # ---- بطاقة KPI في لوحة المعلومات ----
        self._style.configure("Kpi.TFrame", background=COL_CARD, relief="solid", borderwidth=1, bordercolor=COL_BORDER)
        self._style.configure("KpiTitle.TLabel", background=COL_CARD, foreground=COL_SUBTEXT, font=get_tk_font(9, "bold"))
        self._style.configure("KpiValue.TLabel", background=COL_CARD, foreground=COL_NAVY, font=get_tk_font(22, "bold"))
        self._style.configure("KpiIcon.TLabel", background=COL_NAVY_SOFT, foreground=COL_NAVY, font=get_tk_font(15))

    # -------------------- تبويب لوحة المعلومات --------------------
    def _build_dashboard_tab(self):
        wrap = tk.Frame(self.tab_dashboard, bg=COL_BG)
        wrap.pack(fill="both", expand=True, padx=14, pady=14)

        top_row = tk.Frame(wrap, bg=COL_BG)
        top_row.pack(fill="x")
        title_box = tk.Frame(top_row, bg=COL_BG)
        title_box.pack(side="right")
        tk.Label(title_box, text="نظرة عامة", bg=COL_BG, fg=COL_NAVY,
                 font=get_tk_font(16, "bold")).pack(anchor="e")
        tk.Label(title_box, text="ملخص سريع لأداء الفواتير والتحصيلات", bg=COL_BG, fg=COL_SUBTEXT,
                 font=get_tk_font(9)).pack(anchor="e")
        ttk.Button(top_row, text="⟳ تحديث", style="Ghost.TButton",
                   command=self.refresh_dashboard).pack(side="right")

        # ---- الصف الأول من بطاقات المؤشرات ----
        self.kpi_vars = {}
        row1 = tk.Frame(wrap, bg=COL_BG)
        row1.pack(fill="x", pady=(14, 6))
        kpis_row1 = [
            ("invoice_count", "🧾  عدد الفواتير", ""),
            ("customer_count", "👥  عدد العملاء", ""),
            ("payment_count", "💳  عدد الدفعات", ""),
            ("avg_invoice", "📊  متوسط قيمة الفاتورة", " د.ك"),
        ]
        self._build_kpi_row(row1, kpis_row1)

        # ---- الصف الثاني: الأرقام المالية الأساسية ----
        row2 = tk.Frame(wrap, bg=COL_BG)
        row2.pack(fill="x", pady=6)
        kpis_row2 = [
            ("total_invoiced", "💰  إجمالي المستحق على العملاء", " د.ك"),
            ("total_paid", "✅  إجمالي المبالغ المحصّلة", " د.ك"),
            ("total_outstanding", "⏳  إجمالي الرصيد المتبقي", " د.ك"),
        ]
        self._build_kpi_row(row2, kpis_row2, big=True)

        # ---- الصف الثالث: حالة الفواتير ----
        row3 = tk.Frame(wrap, bg=COL_BG)
        row3.pack(fill="x", pady=6)
        kpis_row3 = [
            ("paid_count", "🟢  فواتير مسددة بالكامل", ""),
            ("partial_count", "🟡  فواتير مسددة جزئياً", ""),
            ("unpaid_count", "🔴  فواتير غير مسددة", ""),
        ]
        self._build_kpi_row(row3, kpis_row3)

        # ---- أكبر العملاء مديونية ----
        bottom = tk.Frame(wrap, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        bottom.pack(fill="both", expand=True, pady=(16, 0))
        tk.Label(bottom, text="⚠️  أكبر العملاء مديونية (الرصيد المستحق)", bg=COL_CARD, fg=COL_NAVY,
                 font=get_tk_font(11, "bold")).pack(anchor="e", padx=14, pady=(12, 4))
        cols_d = ("customer", "invoiced", "paid", "balance")
        self.debtors_tree = ttk.Treeview(bottom, columns=cols_d, show="headings", selectmode="browse", height=6)
        self.debtors_tree["displaycolumns"] = tuple(reversed(cols_d))
        headers_d = {"customer": "العميل", "invoiced": "إجمالي الفواتير", "paid": "إجمالي المدفوع", "balance": "الرصيد المستحق"}
        for c in cols_d:
            self.debtors_tree.heading(c, text=headers_d[c], anchor="e")
            self.debtors_tree.column(c, anchor="e", width=160)
        self.debtors_tree.tag_configure("owed", foreground=COL_DANGER, font=get_tk_font(10, "bold"))
        self.debtors_tree.tag_configure("rowodd", background=COL_CARD)
        self.debtors_tree.tag_configure("roweven", background=COL_ROW_ALT)
        self.debtors_tree.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_kpi_row(self, parent, kpis, big=False):
        for key, label, suffix in kpis:
            # نفصل الأيقونة (أول رمز) عن نص العنوان لعرضها داخل شارة دائرية أنيقة
            parts = label.split(None, 1)
            icon, title = (parts[0], parts[1]) if len(parts) == 2 else ("📌", label)

            outer = tk.Frame(parent, bg=COL_CARD, highlightthickness=1,
                              highlightbackground=COL_BORDER, highlightcolor=COL_BORDER)
            outer.pack(side="right", expand=True, fill="both", padx=6)
            # شريط تمييز رفيع أعلى البطاقة بلون الهوية
            tk.Frame(outer, bg=COL_GOLD if big else COL_NAVY, height=3).pack(fill="x", side="top")

            card = tk.Frame(outer, bg=COL_CARD, padx=16, pady=14)
            card.pack(fill="both", expand=True)

            top_row = tk.Frame(card, bg=COL_CARD)
            top_row.pack(fill="x", anchor="e")
            badge = tk.Label(top_row, text=icon, bg=COL_NAVY_SOFT, fg=COL_NAVY,
                              font=get_tk_font(13), width=3, height=1)
            badge.pack(side="right")
            tk.Label(top_row, text=title, bg=COL_CARD, fg=COL_SUBTEXT,
                     font=get_tk_font(9, "bold"), justify="right", wraplength=150).pack(side="right", padx=(0, 8), anchor="e")

            var = tk.StringVar(value="—")
            self.kpi_vars[key] = (var, suffix)
            tk.Label(card, textvariable=var, bg=COL_CARD, fg=COL_NAVY,
                     font=get_tk_font(20 if big else 18, "bold")).pack(anchor="e", pady=(10, 0))

    def refresh_dashboard(self):
        if not hasattr(self, "kpi_vars"):
            return
        invoices = load_invoices()
        payments = load_payments()
        customers = load_customers()
        stats = get_dashboard_stats(invoices, payments, customers)

        def fmt(key):
            val = stats.get(key, 0)
            if isinstance(val, float):
                return f"{val:,.3f}"
            return f"{val:,}"

        for key, (var, suffix) in self.kpi_vars.items():
            var.set(fmt(key) + suffix)

        for row in self.debtors_tree.get_children():
            self.debtors_tree.delete(row)
        for idx, b in enumerate(stats["top_debtors"]):
            stripe = "roweven" if idx % 2 else "rowodd"
            self.debtors_tree.insert("", "end", values=(b["customer"], f'{b["invoiced"]:.3f}',
                                                          f'{b["paid"]:.3f}', f'{b["balance"]:.3f}'),
                                      tags=(stripe, "owed"))
        if not stats["top_debtors"]:
            self.debtors_tree.insert("", "end", values=("لا يوجد عملاء عليهم رصيد مستحق حالياً", "", "", ""))

    # -------------------- تبويب الفواتير --------------------
    def _build_invoices_tab(self):
        wrap = tk.Frame(self.tab_invoices, bg=COL_BG)
        wrap.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(wrap, text="سجل الفواتير", bg=COL_BG, fg=COL_NAVY,
                 font=get_tk_font(15, "bold")).pack(anchor="e")

        top = tk.Frame(wrap, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        top.pack(fill="x", pady=(10, 12))
        top_pad = tk.Frame(top, bg=COL_CARD, padx=14, pady=12)
        top_pad.pack(fill="x")

        # ---- الصف الأول: أزرار الإجراءات + بحث برقم الفاتورة / اسم العميل ----
        row1 = tk.Frame(top_pad, bg=COL_CARD)
        row1.pack(fill="x")

        tk.Label(row1, text="🔍 بحث (رقم الفاتورة / اسم العميل / رقم البيان الجمركي):", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(6, 2))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh_invoice_list())
        search_entry = tk.Entry(row1, textvariable=self.search_var, font=get_tk_font(10), width=28, justify="right",
                     relief="solid", bd=1, highlightthickness=1, highlightbackground=COL_BORDER)
        search_entry.pack(side="right", padx=4, ipady=3)

        # (Declaration-number search merged into general search box)

        ttk.Button(row1, text="＋ فاتورة جديدة", style="Accent.TButton", command=self.open_new_invoice).pack(side="right", padx=3)
        ttk.Button(row1, text="✎ تعديل", style="Ghost.TButton", command=self.edit_selected_invoice).pack(side="right", padx=3)
        ttk.Button(row1, text="🗑 حذف", style="Danger.TButton", command=self.delete_selected_invoice).pack(side="right", padx=3)
        ttk.Button(row1, text="🖨 طباعة (فاتورة أو أكثر)", style="Ghost.TButton", command=self.print_selected_invoice).pack(side="right", padx=3)
        tk.Label(row1, text="💡 حدد عدة فواتير بالضغط مع Ctrl أو Shift لطباعتها دفعة واحدة",
                 bg=COL_CARD, fg=COL_MUTED, font=get_tk_font(8)).pack(side="right", padx=(10, 0))

        tk.Frame(top_pad, bg=COL_BORDER, height=1).pack(fill="x", pady=10)

        # ---- الصف الثاني: تصفية حسب العميل والفترة الزمنية + إجمالي النتائج ----
        row2 = tk.Frame(top_pad, bg=COL_CARD)
        row2.pack(fill="x")

        tk.Label(row2, text="العميل:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(6, 2))
        self.filter_customer_var = tk.StringVar(value="الكل")
        self.filter_customer_combo = ttk.Combobox(
            row2, textvariable=self.filter_customer_var, font=get_tk_font(10),
            justify="right", width=20, state="readonly"
        )
        self.filter_customer_combo.pack(side="right", padx=4)
        self.filter_customer_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_invoice_list())
        # postcommand يُستدعى دائماً من Tk نفسها قبل فتح القائمة المنسدلة (بالنقر أو
        # لوحة المفاتيح)، بعكس ربط <Button-1> اليدوي الذي قد لا يلتقط كل طرق الفتح
        # فتظهر القائمة فارغة أحياناً رغم وجود عملاء محفوظين فعلياً.
        self.filter_customer_combo.configure(postcommand=self._refresh_customer_filter_values)
        self._refresh_customer_filter_values()

        tk.Label(row2, text="من تاريخ:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(10, 2))
        self.filter_from_var = tk.StringVar()
        self.filter_from_var.trace_add("write", lambda *a: self.refresh_invoice_list())
        from_row, _ = build_date_field(row2, self.filter_from_var)
        from_row.pack(side="right", padx=4)

        tk.Label(row2, text="إلى تاريخ:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(10, 2))
        self.filter_to_var = tk.StringVar()
        self.filter_to_var.trace_add("write", lambda *a: self.refresh_invoice_list())
        to_row, _ = build_date_field(row2, self.filter_to_var)
        to_row.pack(side="right", padx=4)
        
        ttk.Button(row2, text="✕ مسح التصفية", style="Ghost.TButton", command=self.clear_invoice_filters).pack(side="right", padx=4)
        ttk.Button(row2, text="📄 كشف حساب العميل", style="Ghost.TButton", command=self.print_customer_statement).pack(side="right", padx=4)

        tk.Label(row2, text="(صيغة التاريخ: YYYY-MM-DD)", bg=COL_CARD, fg=COL_MUTED, font=get_tk_font(8)).pack(side="right", padx=(10, 0))
        self.summary_label = tk.Label(row2, text="", bg=COL_CARD, fg=COL_NAVY, font=get_tk_font(10, "bold"))
        self.summary_label.pack(side="right", padx=10)

        action_row = tk.Frame(top_pad, bg=COL_CARD)
        action_row.pack(fill="x", pady=(10, 0))
        ttk.Button(action_row, text="⟳ تحديث", style="Ghost.TButton", command=self.refresh_invoice_list).pack(side="right", padx=3)
        ttk.Button(action_row, text="⬇ تصدير CSV", style="Ghost.TButton", command=self.export_invoices_csv).pack(side="right", padx=3)
        ttk.Button(action_row, text="📄📄 كشف حساب لعدة عملاء", style="Ghost.TButton",
                   command=self.open_multi_customer_statement_dialog).pack(side="right", padx=3)

        table_card = tk.Frame(wrap, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        table_card.pack(fill="both", expand=True)



        cols = ("invno", "declno", "date", "customer", "port", "total", "paid", "balance", "status")
        headers = {"invno": "رقم الفاتورة", "declno": "رقم البيان الجمركي" , "date": "التاريخ", "customer": "السادة/العميل",
                   "port": "المنفذ", "total": "الإجمالي (د.ك)", "paid": "المدفوع (د.ك)",
                   "balance": "المتبقي (د.ك)", "status": "الحالة"}
        widths = {"invno": 100, "declno": 100, "date": 100, "customer": 200, "port": 110,
                  "total": 110, "paid": 110, "balance": 110, "status": 120}
        self.tree = ttk.Treeview(table_card, columns=cols, show="headings", selectmode="extended")
        self.tree["displaycolumns"] = tuple(reversed(cols))
        for c in cols:
            self.tree.heading(c, text=headers[c], anchor="e")
            self.tree.column(c, anchor="e", width=widths[c])
        self.tree.tag_configure("st_paid", foreground=COL_SUCCESS, font=get_tk_font(10, "bold"))
        self.tree.tag_configure("st_partial", foreground=COL_WARN, font=get_tk_font(10, "bold"))
        self.tree.tag_configure("st_unpaid", foreground=COL_DANGER, font=get_tk_font(10, "bold"))
        self.tree.tag_configure("rowodd", background=COL_CARD)
        self.tree.tag_configure("roweven", background=COL_ROW_ALT)
        self.tree.pack(fill="both", expand=True, padx=1, pady=1)
        self.tree.bind("<Double-1>", lambda e: self.edit_selected_invoice())

    def refresh_invoice_list(self):
        query = (self.search_var.get() or "").strip().lower()
        # merged declno searching into the main query; no separate decl_query
        customer_filter = self.filter_customer_var.get() if hasattr(self, "filter_customer_var") else "الكل"
        date_from = (self.filter_from_var.get() or "").strip() if hasattr(self, "filter_from_var") else ""
        date_to = (self.filter_to_var.get() or "").strip() if hasattr(self, "filter_to_var") else ""

        for row in self.tree.get_children():
            self.tree.delete(row)
        self._all_invoices = load_invoices()

        filtered = []
        for inv in self._all_invoices:
            # بحث حر برقم الفاتورة أو اسم العميل
            hay = f"{inv.get('invno','')} {inv.get('customer','')} {inv.get('declno','') }".lower()
            if query and query not in hay:
                continue
            # تصفية حسب عميل محدد
            if customer_filter and customer_filter != "الكل" and inv.get("customer", "") != customer_filter:
                continue
            # (declno is covered by the general hay string)
            # تصفية حسب الفترة الزمنية (يعتمد على أن التاريخ بصيغة YYYY-MM-DD قابلة للمقارنة نصياً)
            inv_date = str(inv.get("date", ""))
            if date_from and inv_date < date_from:
                continue
            if date_to and inv_date > date_to:
                continue
            filtered.append(inv)

        self._filtered_invoices = filtered
        status_map = invoice_payment_status(self._all_invoices, load_payments())
        status_labels = {"paid": "مسددة ✅", "partial": "جزئية ⏳", "unpaid": "غير مسددة ⛔"}
        status_tags = {"paid": "st_paid", "partial": "st_partial", "unpaid": "st_unpaid"}

        total_sum = 0.0
        for row_idx, inv in enumerate(filtered):
            no = str(inv.get("invno", ""))
            st = status_map.get(no, {"paid": 0.0, "balance": float(inv.get("total") or 0), "status": "unpaid"})
            stripe = "roweven" if row_idx % 2 else "rowodd"
            self.tree.insert("", "end", iid=no,
                              values=(inv.get("invno", ""), inv.get("declno", ""), inv.get("date", ""),
                                      inv.get("customer", ""), inv.get("port", ""),
                                      f'{float(inv.get("total") or 0):.3f}',
                                      f'{st["paid"]:.3f}', f'{st["balance"]:.3f}',
                                      status_labels[st["status"]]),
                              tags=(stripe, status_tags[st["status"]]))
            total_sum += float(inv.get("total") or 0)

        if hasattr(self, "summary_label"):
            self.summary_label.config(
                text=f"عدد الفواتير: {len(filtered)}    |    الإجمالي: {total_sum:.3f} د.ك"
            )

    def _refresh_customer_filter_values(self):
        current = self.filter_customer_var.get() if hasattr(self, "filter_customer_var") else "الكل"
        names = ["الكل"] + self.all_customer_names()
        self.filter_customer_combo.configure(values=names)
        if current not in names:
            self.filter_customer_var.set("الكل")

    def clear_invoice_filters(self):
        self.search_var.set("")
        self.filter_customer_var.set("الكل")
        self.filter_from_var.set("")
        self.filter_to_var.set("")
        self.refresh_invoice_list()

    def export_invoices_csv(self):
        invoices = getattr(self, "_filtered_invoices", load_invoices())
        if not invoices:
            messagebox.showinfo("تنبيه", "لا توجد فواتير لعمل تصدير CSV في الوقت الحالي.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="invoices_export.csv",
            filetypes=[("ملفات CSV", "*.csv"), ("الكل", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(INVOICE_HEADERS)
                for inv in invoices:
                    writer.writerow(invoice_dict_to_row(inv))
        except OSError as exc:
            messagebox.showerror("خطأ في التصدير", f"تعذر تصدير الملف:\n{exc}")
            return

        messagebox.showinfo("تم", f"تم تصدير {len(invoices)} فاتورة بنجاح إلى:\n{path}")

    def print_customer_statement(self):
        customer = self.filter_customer_var.get()
        if not customer or customer == "الكل":
            messagebox.showinfo("تنبيه", "الرجاء اختيار عميل محدد من قائمة \"العميل\" أعلاه لطباعة كشف حسابه")
            return
        # نجلب كل حركات هذا العميل (فواتير ودفعات) لحساب الرصيد الافتتاحي بشكل صحيح
        # قبل تصفية الفترة الزمنية المطلوبة في كشف الحساب
        all_invoices = [i for i in load_invoices() if i.get("customer") == customer]
        all_payments = [p for p in load_payments() if p.get("customer") == customer]
        if not all_invoices and not all_payments:
            messagebox.showinfo("تنبيه", "لا توجد أي فواتير أو دفعات لهذا العميل لعرضها في كشف الحساب")
            return
        generate_and_open_statement(
            customer=customer,
            date_from=(self.filter_from_var.get() or "").strip(),
            date_to=(self.filter_to_var.get() or "").strip(),
            invoices=all_invoices,
            payments=all_payments,
        )

    def open_multi_customer_statement_dialog(self):
        """يفتح نافذة صغيرة لاختيار عدة عملاء دفعة واحدة (Ctrl/Shift للتحديد
        المتعدد أو زر "تحديد الكل")، مع فترة زمنية مشتركة اختيارية، ثم يُنشئ
        مستنداً واحداً يجمع كشف حساب كل عميل في صفحة مستقلة قابلة للطباعة معاً."""
        names = self.all_customer_names()
        if not names:
            messagebox.showinfo("تنبيه", "لا يوجد عملاء محفوظون بعد. أضف عملاء أولاً من تبويب \"العملاء\"")
            return

        win = tk.Toplevel(self)
        win.title("كشف حساب لعدة عملاء")
        win.configure(bg=COL_BG)
        win.transient(self)
        win.grab_set()
        win.geometry("460x560")
        win.minsize(420, 480)

        tk.Label(win, text="📄📄 اختر العملاء المطلوب طباعة كشوف حسابهم", bg=COL_BG, fg=COL_NAVY,
                 font=get_tk_font(11, "bold")).pack(anchor="e", padx=14, pady=(14, 4))
        tk.Label(win, text="حدد عدة عملاء بالضغط مع Ctrl أو Shift، أو استخدم زر \"تحديد الكل\" أدناه",
                 bg=COL_BG, fg=COL_SUBTEXT, font=get_tk_font(9), justify="right").pack(anchor="e", padx=14)

        list_card = tk.Frame(win, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        list_card.pack(fill="both", expand=True, padx=14, pady=(10, 8))

        # حجز مساحة صف الأزرار السفلي أولاً (نفس مبدأ الإصلاح في تبويبي العملاء
        # والدفعات) حتى لا يختفي أي زر عند تصغير النافذة.
        list_btns = tk.Frame(list_card, bg=COL_CARD)
        list_btns.pack(side="bottom", fill="x", padx=8, pady=8)
        ttk.Button(list_btns, text="تحديد الكل", style="Ghost.TButton",
                   command=lambda: names_list.selection_set(0, "end")).pack(side="right", padx=2)
        ttk.Button(list_btns, text="إلغاء التحديد", style="Ghost.TButton",
                   command=lambda: names_list.selection_clear(0, "end")).pack(side="right", padx=2)

        list_row = tk.Frame(list_card, bg=COL_CARD)
        list_row.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        scroll = tk.Scrollbar(list_row, orient="vertical")
        names_list = tk.Listbox(list_row, selectmode=tk.EXTENDED, font=get_tk_font(10), justify="right",
                                 exportselection=False, yscrollcommand=scroll.set, activestyle="none",
                                 relief="solid", bd=1, selectbackground=COL_NAVY, selectforeground="white")
        scroll.config(command=names_list.yview)
        scroll.pack(side="left", fill="y")
        names_list.pack(side="left", fill="both", expand=True)
        for name in names:
            names_list.insert("end", name)

        period_card = tk.Frame(win, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        period_card.pack(fill="x", padx=14, pady=(0, 10))
        period_row = tk.Frame(period_card, bg=COL_CARD)
        period_row.pack(fill="x", padx=10, pady=10)

        tk.Label(period_row, text="من تاريخ:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(9)).pack(side="right", padx=(10, 2))
        dlg_from_var = tk.StringVar(value=(self.filter_from_var.get() or ""))
        dlg_from_row, _ = build_date_field(period_row, dlg_from_var)
        dlg_from_row.pack(side="right", padx=4)

        tk.Label(period_row, text="إلى تاريخ:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(9)).pack(side="right", padx=(6, 2))
        dlg_to_var = tk.StringVar(value=(self.filter_to_var.get() or ""))
        dlg_to_row, _ = build_date_field(period_row, dlg_to_var)
        dlg_to_row.pack(side="right", padx=4)

        bottom_btns = tk.Frame(win, bg=COL_BG)
        bottom_btns.pack(fill="x", padx=14, pady=(0, 14))

        def do_print():
            sel_indices = names_list.curselection()
            if not sel_indices:
                messagebox.showinfo("تنبيه", "الرجاء اختيار عميل واحد على الأقل من القائمة", parent=win)
                return
            selected_names = [names_list.get(i) for i in sel_indices]
            date_from = (dlg_from_var.get() or "").strip()
            date_to = (dlg_to_var.get() or "").strip()

            all_invoices = load_invoices()
            all_payments = load_payments()
            items = []
            skipped = []
            for customer in selected_names:
                cust_invoices = [i for i in all_invoices if i.get("customer") == customer]
                cust_payments = [p for p in all_payments if p.get("customer") == customer]
                if not cust_invoices and not cust_payments:
                    skipped.append(customer)
                    continue
                items.append({
                    "customer": customer, "date_from": date_from, "date_to": date_to,
                    "invoices": cust_invoices, "payments": cust_payments,
                })

            if not items:
                messagebox.showinfo("تنبيه", "لا توجد أي فواتير أو دفعات لأي من العملاء المحددين", parent=win)
                return

            if skipped:
                messagebox.showinfo(
                    "تنبيه",
                    "تم تجاوز العملاء التالية أسماؤهم لعدم وجود أي فواتير أو دفعات لهم:\n" + "، ".join(skipped),
                    parent=win,
                )
            win.destroy()
            generate_and_open_statements_print(items)

        ttk.Button(bottom_btns, text="🖨 طباعة كشوف العملاء المحددين", style="Accent.TButton", command=do_print).pack(side="right", padx=3)
        ttk.Button(bottom_btns, text="إلغاء", style="Ghost.TButton", command=win.destroy).pack(side="right", padx=3)

    def _get_selected_invoice(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار فاتورة من القائمة أولاً")
            return None
        if len(sel) > 1:
            messagebox.showinfo("تنبيه", "الرجاء اختيار فاتورة واحدة فقط لهذا الإجراء")
            return None
        invno = sel[0]
        for inv in self._all_invoices:
            if str(inv["invno"]) == str(invno):
                return inv
        return None

    def _get_selected_invoices(self):
        """يعيد كل الفواتير المحددة حالياً في الجدول (يدعم تحديد أكثر من فاتورة
        بالضغط مع Ctrl أو Shift، وهذا ما تعتمد عليه ميزة طباعة عدة فواتير دفعة واحدة)"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار فاتورة واحدة أو أكثر من القائمة أولاً\n(يمكن تحديد عدة فواتير بالضغط مع Ctrl أو Shift أثناء التحديد)")
            return []
        by_no = {str(inv["invno"]): inv for inv in self._all_invoices}
        result = [by_no[str(no)] for no in sel if str(no) in by_no]
        # نحافظ على ترتيب ظهورها في الجدول (وليس ترتيب الضغط العشوائي) لطباعة منطقية
        order = {str(inv["invno"]): i for i, inv in enumerate(self._all_invoices)}
        result.sort(key=lambda inv: order.get(str(inv["invno"]), 0))
        return result

    def open_new_invoice(self):
        InvoiceForm(self, invoice=None)

    def edit_selected_invoice(self):
        inv = self._get_selected_invoice()
        if inv:
            InvoiceForm(self, invoice=inv)

    def delete_selected_invoice(self):
        inv = self._get_selected_invoice()
        if not inv:
            return
        if messagebox.askyesno("تأكيد الحذف",
                                f"هل أنت متأكد من حذف الفاتورة رقم {inv['invno']}؟\nلا يمكن التراجع عن هذا الإجراء"):
            try:
                delete_invoice(inv["invno"])
            except SaveError as e:
                messagebox.showerror("خطأ في الحفظ", str(e))
                return
            self.refresh_invoice_list()
            if hasattr(self, "bal_tree"):
                self.refresh_balances()
            self.refresh_dashboard()

    def print_selected_invoice(self):
        invoices = self._get_selected_invoices()
        if not invoices:
            return
        if len(invoices) > 1:
            nums = "، ".join(str(i["invno"]) for i in invoices)
            if not messagebox.askyesno(
                "تأكيد الطباعة الجماعية",
                f"سيتم إنشاء مستند طباعة واحد يضم {len(invoices)} فاتورة "
                f"(كل فاتورة في صفحة مستقلة):\n{nums}\n\nهل تريد المتابعة؟"
            ):
                return
        generate_and_open_invoices_print(invoices)

    # -------------------- تبويب العملاء --------------------
    def _build_customers_tab(self):
        wrap = tk.Frame(self.tab_customers, bg=COL_BG)
        wrap.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(wrap, text="العملاء", bg=COL_BG, fg=COL_NAVY, font=get_tk_font(15, "bold")).pack(anchor="e")

        form_card = tk.Frame(wrap, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        form_card.pack(fill="x", pady=(10, 12))
        tk.Label(form_card, text="👤 إضافة / تعديل عميل", bg=COL_CARD, fg=COL_NAVY,
                 font=get_tk_font(10, "bold")).pack(anchor="e", padx=14, pady=(12, 4))

        form = tk.Frame(form_card, bg=COL_CARD)
        form.pack(fill="x", padx=12, pady=(0, 6))

        self.c_name = tk.StringVar()
        self.c_phone = tk.StringVar()
        self.c_address = tk.StringVar()
        self.c_notes = tk.StringVar()
        self._editing_customer = None
        self._editing_customer_company_code = ""  # يُحفظ داخلياً فقط، لا يظهر كحقل إدخال

        def field(parent, label, var, col, width=22):
            f = tk.Frame(parent, bg=COL_CARD)
            f.grid(row=0, column=col, padx=8, pady=6, sticky="ew")
            tk.Label(f, text=label, bg=COL_CARD, fg=COL_SUBTEXT, font=get_tk_font(9)).pack(anchor="e")
            tk.Entry(f, textvariable=var, font=get_tk_font(10), justify="right", width=width,
                     relief="solid", bd=1, highlightthickness=1, highlightbackground=COL_BORDER).pack(fill="x", ipady=3)
            return f

        field(form, "اسم العميل", self.c_name, 3)
        field(form, "الهاتف", self.c_phone, 2)
        field(form, "العنوان", self.c_address, 1)
        field(form, "ملاحظات", self.c_notes, 0)
        for i in range(4):
            form.grid_columnconfigure(i, weight=1)

        btns = tk.Frame(form_card, bg=COL_CARD)
        btns.pack(fill="x", padx=12, pady=(4, 14))
        self.btn_save_customer = ttk.Button(btns, text="💾 حفظ العميل", style="Accent.TButton", command=self.save_customer_form)
        self.btn_save_customer.pack(side="right", padx=3)
        ttk.Button(btns, text="مسح الحقول", style="Ghost.TButton", command=self.clear_customer_form).pack(side="right", padx=3)

        table_card = tk.Frame(wrap, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        table_card.pack(fill="both", expand=True)

        search_frame = tk.Frame(table_card, bg=COL_CARD)
        search_frame.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(search_frame, text="🔍 بحث:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(6, 2))
        self.cust_search_var = tk.StringVar()
        self.cust_search_var.trace_add("write", lambda *a: self.refresh_customer_list())
        tk.Entry(search_frame, textvariable=self.cust_search_var, font=get_tk_font(10),
                 justify="right", width=30, relief="solid", bd=1,
                 highlightthickness=1, highlightbackground=COL_BORDER).pack(side="right", ipady=3)

        # ملاحظة مهمة حول الترتيب: يجب حجز مساحة صف الأزرار (btns2) أولاً بربطه
        # بأسفل البطاقة (side="bottom") *قبل* إضافة الجدول الذي يتمدّد (expand=True).
        # فـ pack تُوزّع المساحة بالترتيب الذي تُستدعى به: لو تم تعبئة الجدول
        # المتمدّد أولاً فسيستهلك كل المساحة المتاحة عند تصغير النافذة، ولن يبقى
        # للأزرار مكان فتختفي تماماً. حجز مكان الأزرار أولاً يضمن ظهورها دائماً
        # مهما صغرت النافذة، ثم يأخذ الجدول ما تبقى من المساحة.
        btns2 = tk.Frame(table_card, bg=COL_CARD)
        btns2.pack(side="bottom", fill="x", padx=12, pady=10)
        ttk.Button(btns2, text="✎ تحميل للتعديل", style="Ghost.TButton", command=self.load_customer_into_form).pack(side="right", padx=3)
        ttk.Button(btns2, text="🗑 حذف العميل المحدد", style="Danger.TButton", command=self.delete_selected_customer).pack(side="right", padx=3)

        cols = ("name", "phone", "address", "notes", "company_code")
        self.cust_tree = ttk.Treeview(table_card, columns=cols, show="headings", selectmode="browse")
        self.cust_tree["displaycolumns"] = tuple(reversed(cols))
        headers = {"name": "اسم العميل", "phone": "الهاتف", "address": "العنوان",
                   "notes": "ملاحظات", "company_code": "رمز الشركة"}
        for c in cols:
            self.cust_tree.heading(c, text=headers[c], anchor="e")
            self.cust_tree.column(c, anchor="e", width=150 if c != "company_code" else 90)
        self.cust_tree.tag_configure("rowodd", background=COL_CARD)
        self.cust_tree.tag_configure("roweven", background=COL_ROW_ALT)
        self.cust_tree.pack(fill="both", expand=True, padx=1, pady=(4, 1))
        self.cust_tree.bind("<Double-1>", lambda e: self.load_customer_into_form())

    def refresh_customer_list(self):
        query = (self.cust_search_var.get() or "").strip().lower()
        for row in self.cust_tree.get_children():
            self.cust_tree.delete(row)
        self._all_customers = load_customers()
        row_idx = 0
        for c in self._all_customers:
            hay = f"{c['name']} {c['phone']}".lower()
            if query and query not in hay:
                continue
            stripe = "roweven" if row_idx % 2 else "rowodd"
            row_idx += 1
            self.cust_tree.insert("", "end", iid=c["name"], tags=(stripe,),
                                   values=(c["name"], c["phone"], c["address"], c["notes"], c.get("company_code", "")))

    def load_customer_into_form(self):
        sel = self.cust_tree.selection()
        if not sel:
            return
        name = sel[0]
        for c in self._all_customers:
            if c["name"] == name:
                self.c_name.set(c["name"])
                self.c_phone.set(c["phone"])
                self.c_address.set(c["address"])
                self.c_notes.set(c["notes"])
                self._editing_customer = name
                self._editing_customer_company_code = c.get("company_code", "")
                self.btn_save_customer.config(text="حفظ التعديلات")
                break

    def clear_customer_form(self):
        self.c_name.set(""); self.c_phone.set(""); self.c_address.set(""); self.c_notes.set("")
        self._editing_customer = None
        self._editing_customer_company_code = ""
        self.btn_save_customer.config(text="حفظ العميل")

    def save_customer_form(self):
        name = self.c_name.get().strip()
        if not name:
            messagebox.showwarning("تنبيه", "الرجاء إدخال اسم العميل.")
            return

        if self._editing_customer:
            # عميل موجود: نحافظ على رمز شركته الحالي كما هو (لا يُعاد توليده)
            company_code = self._editing_customer_company_code
        else:
            # عميل جديد: يُولَّد له رمز شركة تلقائياً (أصغر رمز متاح بين 01 و99)
            try:
                company_code = next_available_company_code()
            except ValueError as e:
                messagebox.showerror("تنبيه", str(e))
                return

        try:
            save_customer({"name": name, "phone": self.c_phone.get(), "address": self.c_address.get(),
                            "notes": self.c_notes.get(), "company_code": company_code},
                           editing_name=self._editing_customer)
        except SaveError as e:
            messagebox.showerror("خطأ في الحفظ", str(e))
            return
        self.clear_customer_form()
        self.refresh_customer_list()
        self.refresh_dashboard()

    def delete_selected_customer(self):
        sel = self.cust_tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار عميل من القائمة أولاً.")
            return
        name = sel[0]
        if messagebox.askyesno("تأكيد الحذف", f'هل أنت متأكد من حذف العميل "{name}"؟'):
            try:
                delete_customer(name)
            except SaveError as e:
                messagebox.showerror("خطأ في الحفظ", str(e))
                return
            self.refresh_customer_list()
            self.refresh_dashboard()

    def all_customer_names(self):
        return [c["name"] for c in load_customers()]

    # -------------------- تبويب الدفعات والأرصدة --------------------
    def _build_payments_tab(self):
        wrap = tk.Frame(self.tab_payments, bg=COL_BG)
        wrap.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(wrap, text="الدفعات والأرصدة", bg=COL_BG, fg=COL_NAVY, font=get_tk_font(15, "bold")).pack(anchor="e")

        # ---- نموذج إضافة دفعة ----
        form_card = tk.Frame(wrap, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        form_card.pack(fill="x", pady=(10, 12))
        tk.Label(form_card, text="💳 تسجيل دفعة جديدة", bg=COL_CARD, fg=COL_NAVY,
                 font=get_tk_font(10, "bold")).pack(anchor="e", padx=14, pady=(12, 4))

        form = tk.Frame(form_card, bg=COL_CARD)
        form.pack(fill="x", padx=12)

        self.p_customer = tk.StringVar()
        self.p_date = tk.StringVar(value=date.today().isoformat())
        self.p_amount = tk.StringVar()
        self.p_notes = tk.StringVar()
        self._editing_payment_id = None

        f1 = tk.Frame(form, bg=COL_CARD)
        f1.grid(row=0, column=3, padx=8, pady=6, sticky="ew")
        tk.Label(f1, text="اسم العميل", bg=COL_CARD, fg=COL_SUBTEXT, font=get_tk_font(9)).pack(anchor="e")
        self.p_customer_combo = ttk.Combobox(f1, textvariable=self.p_customer, font=get_tk_font(10), justify="right", width=22)
        self.p_customer_combo.pack(fill="x")
        self.p_customer_combo.configure(postcommand=lambda: self.p_customer_combo.configure(values=self.all_customer_names()))
        self.p_customer_combo.bind("<<ComboboxSelected>>", self._on_payment_customer_changed)
        self.p_customer_combo.bind("<FocusOut>", self._on_payment_customer_changed)
        self.p_receipt_preview_var = tk.StringVar(value="رقم السند: —")
        tk.Label(f1, textvariable=self.p_receipt_preview_var, bg=COL_CARD, font=get_tk_font(8, "bold"), fg=COL_GOLD_DARK).pack(anchor="e", pady=(3, 0))

        f2 = tk.Frame(form, bg=COL_CARD)
        f2.grid(row=0, column=2, padx=8, pady=6, sticky="ew")
        tk.Label(f2, text="التاريخ", bg=COL_CARD, fg=COL_SUBTEXT, font=get_tk_font(9)).pack(anchor="e")
        p_date_row, _ = build_date_field(f2, self.p_date)
        p_date_row.pack(fill="x")

        f3 = tk.Frame(form, bg=COL_CARD)
        f3.grid(row=0, column=1, padx=8, pady=6, sticky="ew")
        tk.Label(f3, text="المبلغ المدفوع (د.ك)", bg=COL_CARD, fg=COL_SUBTEXT, font=get_tk_font(9)).pack(anchor="e")
        tk.Entry(f3, textvariable=self.p_amount, font=get_tk_font(10), justify="right", width=16,
                 relief="solid", bd=1, highlightthickness=1, highlightbackground=COL_BORDER).pack(fill="x", ipady=3)

        f4 = tk.Frame(form, bg=COL_CARD)
        f4.grid(row=0, column=0, padx=8, pady=6, sticky="ew")
        tk.Label(f4, text="ملاحظات", bg=COL_CARD, fg=COL_SUBTEXT, font=get_tk_font(9)).pack(anchor="e")
        tk.Entry(f4, textvariable=self.p_notes, font=get_tk_font(10), justify="right", width=22,
                 relief="solid", bd=1, highlightthickness=1, highlightbackground=COL_BORDER).pack(fill="x", ipady=3)

        for i in range(4):
            form.grid_columnconfigure(i, weight=1)

        # ---- تخصيص الدفعة لفواتير محددة (اختياري) ----
        alloc_box = tk.Frame(form, bg=COL_CARD_SOFT, highlightthickness=1, highlightbackground=COL_BORDER_SOFT)
        alloc_box.grid(row=1, column=0, columnspan=4, padx=8, pady=(6, 10), sticky="ew")
        tk.Label(alloc_box, text="🧾 تخصيص الدفعة لفواتير محددة (اختياري)", bg=COL_CARD_SOFT, fg=COL_NAVY,
                 font=get_tk_font(9, "bold")).pack(anchor="e", padx=10, pady=(8, 2))

        # جدول الفواتير يُظهر كل بيانات كل فاتورة (رقم، تاريخ، بيان جمركي، منفذ،
        # نوع البضاعة، بلد المنشأ، الإجمالي، المدفوع، المتبقي، الحالة) بدلاً من
        # سطر نصي واحد، مما يتيح للمستخدم رؤية شاملة وتحديد الفواتير بسهولة.
        cols_pi = ("invno", "date", "declno", "port", "goodstype", "origin",
                   "total", "paid", "balance", "status")
        self.p_invoices_tree = ttk.Treeview(alloc_box, columns=cols_pi, show="headings",
                                            selectmode="extended", height=3,
                                            style="CompactTree.Treeview")
        self.p_invoices_tree["displaycolumns"] = tuple(reversed(cols_pi))
        headers_pi = {
            "invno": "رقم الفاتورة", "date": "التاريخ", "declno": "رقم البيان الجمركي",
            "port": "المنفذ", "goodstype": "نوع البضاعة", "origin": "بلد المنشأ",
            "total": "الإجمالي (د.ك)", "paid": "المدفوع (د.ك)", "balance": "المتبقي (د.ك)",
            "status": "الحالة",
        }
        widths_pi = {"invno": 95, "date": 95, "declno": 110, "port": 100,
                     "goodstype": 120, "origin": 115, "total": 100, "paid": 100,
                     "balance": 100, "status": 105}
        for c in cols_pi:
            self.p_invoices_tree.heading(c, text=headers_pi[c], anchor="e")
            self.p_invoices_tree.column(c, anchor="e", width=widths_pi[c])
        status_tag_map = {"paid": "st_paid", "partial": "st_partial", "unpaid": "st_unpaid"}
        status_label_map = {"paid": "مسددة ✅", "partial": "جزئية ⏳", "unpaid": "غير مسددة ⛔"}
        for tag in ("rowodd", "roweven"):
            tag_bg = COL_CARD_SOFT if tag == "rowodd" else COL_ROW_ALT
            self.p_invoices_tree.tag_configure(tag, background=tag_bg)
        for tag in status_tag_map.values():
            self.p_invoices_tree.tag_configure(tag, font=get_tk_font(10, "bold"))
        self.p_invoices_tree.tag_configure("st_paid", foreground=COL_SUCCESS)
        self.p_invoices_tree.tag_configure("st_partial", foreground=COL_WARN)
        self.p_invoices_tree.tag_configure("st_unpaid", foreground=COL_DANGER)
        self._p_invoice_choices = []  # قائمة موازية لعناصر الجدول: أرقام الفاتورات
        pi_scroll = ttk.Scrollbar(alloc_box, orient="vertical", command=self.p_invoices_tree.yview)
        self.p_invoices_tree.configure(yscrollcommand=pi_scroll.set)
        tree_wrap = tk.Frame(alloc_box, bg=COL_CARD_SOFT)
        tree_wrap.pack(fill="x", padx=10, pady=(6, 0))
        pi_scroll.pack(in_=tree_wrap, side="right", fill="y")
        self.p_invoices_tree.pack(in_=tree_wrap, side="right", fill="both", expand=True)

        alloc_btns = tk.Frame(alloc_box, bg=COL_CARD_SOFT)
        alloc_btns.pack(fill="x", padx=10, pady=(3, 6))
        ttk.Button(alloc_btns, text="⟳ تحديث قائمة الفاتورات", style="Ghost.TButton", command=self._update_payment_invoice_list).pack(side="right", padx=2)
        ttk.Button(alloc_btns, text="✕ إلغاء التحديد (دفعة عامة)", style="Ghost.TButton", command=lambda: self.p_invoices_tree.selection_remove(self.p_invoices_tree.get_children())).pack(side="right", padx=2)
        self.p_alloc_summary_var = tk.StringVar(value="")
        tk.Label(alloc_btns, textvariable=self.p_alloc_summary_var, bg=COL_CARD_SOFT, font=get_tk_font(8, "bold"), fg=COL_NAVY).pack(side="right", padx=6)
        self.p_invoices_tree.bind("<<TreeviewSelect>>", self._update_alloc_summary)

        btns = tk.Frame(form_card, bg=COL_CARD)
        btns.pack(fill="x", padx=12, pady=(0, 8))
        self.btn_save_payment = ttk.Button(btns, text="💾 حفظ الدفعة", style="Accent.TButton", command=self.save_payment_form)
        self.btn_save_payment.pack(side="right", padx=3)
        ttk.Button(btns, text="مسح الحقول", style="Ghost.TButton", command=self.clear_payment_form).pack(side="right", padx=3)

        # ---- تصفية سجل الدفعات ----
        filter_card = tk.Frame(wrap, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        filter_card.pack(fill="x", pady=(0, 12))
        pf = tk.Frame(filter_card, bg=COL_CARD)
        pf.pack(fill="x", padx=14, pady=10)
        tk.Label(pf, text="العميل:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(6, 2))
        self.p_filter_customer_var = tk.StringVar(value="الكل")
        self.p_filter_customer_combo = ttk.Combobox(pf, textvariable=self.p_filter_customer_var, font=get_tk_font(10),
                                                      justify="right", width=20, state="readonly")
        self.p_filter_customer_combo.pack(side="right", padx=4)
        self.p_filter_customer_combo.bind("<<ComboboxSelected>>", lambda e: (self.refresh_payments_list()))
        self.p_filter_customer_combo.configure(
            postcommand=lambda: self.p_filter_customer_combo.configure(values=["الكل"] + self.all_customer_names())
        )
        self.p_filter_customer_combo.configure(values=["الكل"] + self.all_customer_names())

        tk.Label(pf, text="من تاريخ:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(10, 2))
        self.p_filter_from_var = tk.StringVar()
        self.p_filter_from_var.trace_add("write", lambda *a: self.refresh_payments_list())
        p_from_row, _ = build_date_field(pf, self.p_filter_from_var)
        p_from_row.pack(side="right", padx=4)

        tk.Label(pf, text="إلى تاريخ:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(10, 2))
        self.p_filter_to_var = tk.StringVar()
        self.p_filter_to_var.trace_add("write", lambda *a: self.refresh_payments_list())
        p_to_row, _ = build_date_field(pf, self.p_filter_to_var)
        p_to_row.pack(side="right", padx=4)

        ttk.Button(pf, text="✕ مسح التصفية", style="Ghost.TButton", command=self.clear_payment_filters).pack(side="right", padx=4)
        self.payments_summary_label = tk.Label(pf, text="", bg=COL_CARD, fg=COL_NAVY, font=get_tk_font(10, "bold"))
        self.payments_summary_label.pack(side="left", padx=10)

        # ---- منطقة مقسّمة: سجل الدفعات (يمين) وجدول الأرصدة (يسار) ----
        split = tk.Frame(wrap, bg=COL_BG)
        split.pack(fill="both", expand=True)
        split.grid_columnconfigure(0, weight=3)
        split.grid_columnconfigure(1, weight=2)
        split.grid_rowconfigure(0, weight=1)

        pay_box = tk.Frame(split, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        pay_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)
        pay_box.grid_columnconfigure(0, weight=1)
        pay_box.grid_rowconfigure(2, weight=1)
        tk.Label(pay_box, text="📋 سجل الدفعات", bg=COL_CARD, fg=COL_NAVY, font=get_tk_font(10, "bold")).grid(row=0, column=0, sticky="e", padx=12, pady=(10, 4))
        # نحجز مساحة أزرار الدفعات ضمن شبكة مرنة لتفادي انهيار الحاوية عند العرض.
        pay_btns = tk.Frame(pay_box, bg=COL_CARD)
        pay_btns.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 10))
        pay_btns.grid_columnconfigure(0, weight=0)
        pay_btns.grid_columnconfigure(1, weight=0)
        ttk.Button(pay_btns, text="✎ تحميل للتعديل", style="Ghost.TButton", command=self.load_payment_into_form).grid(row=0, column=0, padx=4)
        ttk.Button(pay_btns, text="🗑 حذف الدفعة المحددة", style="Danger.TButton", command=self.delete_selected_payment).grid(row=0, column=1, padx=4)

        cols_p = ("id", "customer", "date", "amount", "applied", "notes")
        self.pay_tree = ttk.Treeview(pay_box, columns=cols_p, show="headings", selectmode="browse", height=8)
        self.pay_tree["displaycolumns"] = tuple(reversed(cols_p))
        pay_scroll = ttk.Scrollbar(pay_box, orient="vertical", command=self.pay_tree.yview)
        self.pay_tree.configure(yscrollcommand=pay_scroll.set)
        headers_p = {"id": "رقم السند", "customer": "العميل", "date": "التاريخ", "amount": "المبلغ (د.ك)",
                     "applied": "الفواتير المسددة", "notes": "ملاحظات"}
        for c in cols_p:
            self.pay_tree.heading(c, text=headers_p[c], anchor="e")
            self.pay_tree.column(c, anchor="e", width=90 if c == "id" else 120)
        self.pay_tree.tag_configure("rowodd", background=COL_CARD)
        self.pay_tree.tag_configure("roweven", background=COL_ROW_ALT)
        self.pay_tree.grid(row=2, column=0, sticky="nsew", padx=6, pady=6)
        pay_scroll.grid(row=2, column=1, sticky="ns", padx=(0, 4), pady=6)
        self.pay_tree.bind("<Double-1>", lambda e: self.load_payment_into_form())

        bal_box = tk.Frame(split, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        bal_box.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=0)
        tk.Label(bal_box, text="📊 أرصدة العملاء (الفواتير − المدفوع)", bg=COL_CARD, fg=COL_NAVY, font=get_tk_font(10, "bold")).pack(anchor="e", padx=12, pady=(10, 4))
        cols_b = ("customer", "invoiced", "paid", "balance")
        self.bal_tree = ttk.Treeview(bal_box, columns=cols_b, show="headings", selectmode="browse")
        self.bal_tree["displaycolumns"] = tuple(reversed(cols_b))
        headers_b = {"customer": "العميل", "invoiced": "إجمالي الفواتير", "paid": "إجمالي المدفوع", "balance": "الرصيد المستحق"}
        for c in cols_b:
            self.bal_tree.heading(c, text=headers_b[c], anchor="e")
            self.bal_tree.column(c, anchor="e", width=130)
        self.bal_tree.tag_configure("owed", foreground=COL_DANGER, font=get_tk_font(10, "bold"))
        self.bal_tree.tag_configure("settled", foreground=COL_SUCCESS, font=get_tk_font(10, "bold"))
        self.bal_tree.tag_configure("rowodd", background=COL_CARD)
        self.bal_tree.tag_configure("roweven", background=COL_ROW_ALT)
        bal_scroll = ttk.Scrollbar(bal_box, orient="vertical", command=self.bal_tree.yview)
        self.bal_tree.configure(yscrollcommand=bal_scroll.set)
        bal_scroll.pack(side="right", fill="y", padx=(0, 6), pady=6)
        self.bal_tree.pack(fill="both", expand=True, padx=(6, 0), pady=6)

    def refresh_payments_list(self):
        query_customer = self.p_filter_customer_var.get() if hasattr(self, "p_filter_customer_var") else "الكل"
        date_from = (self.p_filter_from_var.get() or "").strip() if hasattr(self, "p_filter_from_var") else ""
        date_to = (self.p_filter_to_var.get() or "").strip() if hasattr(self, "p_filter_to_var") else ""

        for row in self.pay_tree.get_children():
            self.pay_tree.delete(row)
        self._all_payments = load_payments()

        filtered = []
        for p in self._all_payments:
            if query_customer and query_customer != "الكل" and p.get("customer", "") != query_customer:
                continue
            p_date = str(p.get("date", ""))
            if date_from and p_date < date_from:
                continue
            if date_to and p_date > date_to:
                continue
            filtered.append(p)

        total_paid = 0.0
        for row_idx, p in enumerate(filtered):
            amount = float(p.get("amount") or 0)
            total_paid += amount
            applied = p.get("applied_invoices") or []
            applied_txt = " ، ".join(applied) if applied else "دفعة عامة"
            stripe = "roweven" if row_idx % 2 else "rowodd"
            self.pay_tree.insert("", "end", iid=str(p["id"]), tags=(stripe,),
                                  values=(p.get("id", ""), p.get("customer", ""), p.get("date", ""),
                                          f'{amount:.3f}', applied_txt, p.get("notes", "")))

        if hasattr(self, "payments_summary_label"):
            self.payments_summary_label.config(
                text=f"عدد الدفعات: {len(filtered)}    |    الإجمالي المدفوع: {total_paid:.3f} د.ك"
            )

    def refresh_balances(self):
        for row in self.bal_tree.get_children():
            self.bal_tree.delete(row)
        for idx, b in enumerate(customer_balances()):
            tag = "owed" if b["balance"] > 0.0005 else ("settled" if b["balance"] < -0.0005 else "")
            stripe = "roweven" if idx % 2 else "rowodd"
            self.bal_tree.insert("", "end", values=(b["customer"], f'{b["invoiced"]:.3f}',
                                                      f'{b["paid"]:.3f}', f'{b["balance"]:.3f}'),
                                  tags=(stripe, tag) if tag else (stripe,))

    def _get_selected_payment(self):
        sel = self.pay_tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار دفعة من القائمة أولاً")
            return None
        pid = sel[0]
        for p in getattr(self, "_all_payments", []):
            if str(p["id"]) == str(pid):
                return p
        return None

    def _on_payment_customer_changed(self, event=None):
        self._update_receipt_preview(event)
        self._update_payment_invoice_list()

    def _update_payment_invoice_list(self, preselect=None):
        """يملأ جدول الفواتير غير المسددة/الجزئية للعميل المحدد حالياً في نموذج الدفعة،
        ليختار المستخدم منه الفواتير التي يريد تخصيص الدفعة لها (إن وُجدت).
        يُظهر كل بيانات كل فاتورة في العمود المناسب لتسهيل المقارنة والاختيار."""
        # حفظ التحديد الحالي عند إعادة بناء الجدول (مثلاً عند فقدان التركيز
        # على الـ Combobox بعد اختيار فاتورة) لمنع فقدان اختيار المستخدم.
        preserve = None if preselect is not None else set(self._selected_payment_invoices())
        self.p_invoices_tree.delete(*self.p_invoices_tree.get_children())
        self._p_invoice_choices = []
        customer_name = self.p_customer.get().strip()
        if not customer_name:
            return
        all_invoices = load_invoices()
        status_map = invoice_payment_status(all_invoices, load_payments())
        invoices = [i for i in all_invoices if i.get("customer") == customer_name]
        invoices.sort(key=lambda i: str(i.get("date", "")))
        preselect = set(str(x) for x in (preselect or preserve or []))
        status_tag_map = {"paid": "st_paid", "partial": "st_partial", "unpaid": "st_unpaid"}
        status_label_map = {"paid": "مسددة ✅", "partial": "جزئية ⏳", "unpaid": "غير مسددة ⛔"}
        to_select = []
        for inv in invoices:
            no = str(inv.get("invno", ""))
            st = status_map.get(no, {"total": float(inv.get("total") or 0), "balance": float(inv.get("total") or 0), "status": "unpaid"})
            if st["status"] == "paid" and no not in preselect:
                continue  # لا داعي لعرض فواتير مسددة بالكامل ضمن خيارات التخصيص
            stripe = "roweven" if len(self._p_invoice_choices) % 2 else "rowodd"
            status_tag = status_tag_map.get(st["status"], "st_unpaid")
            self.p_invoices_tree.insert("", "end", iid=no, values=(
                inv.get("invno", ""),
                inv.get("date", ""),
                inv.get("declno", ""),
                inv.get("port", ""),
                inv.get("goodstype", ""),
                inv.get("origin", ""),
                f'{st["total"]:.3f}',
                f'{st["paid"]:.3f}',
                f'{st["balance"]:.3f}',
                status_label_map.get(st["status"], "غير مسددة ⛔"),
            ), tags=(stripe, status_tag))
            self._p_invoice_choices.append(no)
            if no in preselect:
                to_select.append(no)
        # Treeview.selection_set يحوّل selection set إلى "استبدال" وليس "إضافة"
        # في كل استدعاء، لذا يجب تحديد كل الفواتير المطلوب تمييزها مرة واحدة
        # (والترتيب يُحفظ حسب ترتيب الظهور = الأقدم أولاً = أولوية FIFO).
        if to_select:
            self.p_invoices_tree.selection_set(*to_select)
        self._update_alloc_summary()

    def _selected_payment_invoices(self):
        """يعيد أرقام الفواتير المحددة في الجدول بترتيب ظهورها (الأقدم أولاً)
        لضمان أولوية توزيع الدفعة على الفواتير المستحقة أقدماً."""
        sel = set(self.p_invoices_tree.selection())
        return [no for no in self._p_invoice_choices if no in sel]

    def _update_alloc_summary(self, event=None):
        chosen = self._selected_payment_invoices()
        if chosen:
            self.p_alloc_summary_var.set(f"سيتم تطبيق الدفعة على {len(chosen)} فاتورة محددة")
        else:
            self.p_alloc_summary_var.set("دفعة عامة — ستُطبَّق تلقائياً على أقدم الفواتير")

    def _update_receipt_preview(self, event=None):
        customer_name = self.p_customer.get().strip()
        if not customer_name:
            self.p_receipt_preview_var.set("رقم السند: —")
            return
        customers = {c["name"]: c for c in load_customers()}
        c = customers.get(customer_name)
        if not c or not c.get("company_code"):
            self.p_receipt_preview_var.set("رقم السند: (العميل بلا رمز شركة)")
            return
        try:
            preview = next_receipt_number(c["company_code"])
        except ValueError as e:
            self.p_receipt_preview_var.set("رقم السند: —")
            return
        self.p_receipt_preview_var.set(f"رقم السند القادم: {preview}")

    def load_payment_into_form(self):
        p = self._get_selected_payment()
        if not p:
            return
        self.p_customer.set(p.get("customer", ""))
        self.p_date.set(p.get("date", ""))
        self.p_amount.set(str(p.get("amount", "")))
        self.p_notes.set(p.get("notes", ""))
        self._editing_payment_id = p["id"]
        self.p_receipt_preview_var.set(f"رقم السند: {p['id']}")
        self.btn_save_payment.config(text="حفظ التعديلات")
        self._update_payment_invoice_list(preselect=p.get("applied_invoices"))

    def clear_payment_form(self):
        self.p_customer.set("")
        self.p_date.set(date.today().isoformat())
        self.p_amount.set("")
        self.p_notes.set("")
        self._editing_payment_id = None
        self.p_receipt_preview_var.set("رقم السند: —")
        self.btn_save_payment.config(text="حفظ الدفعة")
        self.p_invoices_tree.delete(*self.p_invoices_tree.get_children())
        self._p_invoice_choices = []
        self.p_alloc_summary_var.set("")

    def clear_payment_filters(self):
        self.p_filter_customer_var.set("الكل")
        self.p_filter_from_var.set("")
        self.p_filter_to_var.set("")
        self.refresh_payments_list()

    def save_payment_form(self):
        customer = self.p_customer.get().strip()
        if not customer:
            messagebox.showwarning("تنبيه", "الرجاء اختيار أو إدخال اسم العميل")
            return
        amount_val = safe_float(self.p_amount.get())
        if amount_val <= 0:
            messagebox.showwarning("تنبيه", "الرجاء إدخال مبلغ دفعة أكبر من صفر")
            return
        p = {
            "customer": customer,
            "date": self.p_date.get().strip(),
            "amount": amount_val,
            "notes": self.p_notes.get().strip(),
            "applied_invoices": self._selected_payment_invoices(),
        }
        try:
            save_payment(p, editing_id=self._editing_payment_id)
        except ValueError as e:
            messagebox.showwarning("تنبيه", str(e))
            return
        except SaveError as e:
            messagebox.showerror("خطأ في الحفظ", str(e))
            return
        self.clear_payment_form()
        self.refresh_payments_list()
        self.refresh_balances()
        self.refresh_invoice_list()
        self.refresh_dashboard()

    def delete_selected_payment(self):
        p = self._get_selected_payment()
        if not p:
            return
        if messagebox.askyesno("تأكيد الحذف", "هل أنت متأكد من حذف هذه الدفعة؟\nلا يمكن التراجع عن هذا الإجراء"):
            try:
                delete_payment(p["id"])
            except SaveError as e:
                messagebox.showerror("خطأ في الحفظ", str(e))
                return
            self.refresh_payments_list()
            self.refresh_balances()
            self.refresh_invoice_list()
            self.refresh_dashboard()


class InvoiceForm(tk.Toplevel):
    """نافذة إضافة / تعديل فاتورة."""

    def __init__(self, app: InvoiceApp, invoice=None):
        super().__init__(app)
        self.app = app
        self.editing_invno = invoice["invno"] if invoice else None
        self.title("تعديل فاتورة" if invoice else "فاتورة جديدة")
        self.geometry("980x760")
        self.minsize(760, 600)
        self.configure(bg=COL_BG)
        self.transient(app)
        self.grab_set()
        self.lift()
        self.focus_force()

        # ---- منطقة قابلة للتمرير ----
        container = tk.Frame(self, bg=COL_BG)
        container.pack(fill="both", expand=True)
        canvas = tk.Canvas(container, highlightthickness=0, bg=COL_BG)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=COL_BG)
        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._form_canvas = canvas
        self._form_scroll_frame = self.scroll_frame
        self._scroll_anim_id = None

        # ---- عجلة الفأرة: ربط متوافق مع Windows / macOS / Linux ----
        # نربطها على النافذة (self) لا على كامل التطبيق (bind_all)، لأن
        # وسم الربط "toplevel" هو أحد الوسوم الافتراضية لكل عنصر فرعي داخل
        # هذه النافذة تلقائياً، فتصل الأحداث من أي حقل بداخلها دون أن يؤثر
        # الربط على النوافذ الأخرى أو يسبب أخطاء بعد إغلاق هذه النافذة.
        try:
            windowing_system = self.tk.call("tk", "windowingsystem")
        except tk.TclError:
            windowing_system = "win32"

        def _on_mousewheel_windows(event):
            self._cancel_scroll_animation()
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_mac(event):
            self._cancel_scroll_animation()
            canvas.yview_scroll(int(-1 * event.delta), "units")

        def _on_mousewheel_linux(event):
            self._cancel_scroll_animation()
            canvas.yview_scroll(-1 if event.num == 4 else 1, "units")

        if windowing_system == "x11":
            # لينكس لا يرسل حدث <MouseWheel> بل أزراراً افتراضية 4/5
            self.bind("<Button-4>", _on_mousewheel_linux)
            self.bind("<Button-5>", _on_mousewheel_linux)
        elif windowing_system == "aqua":
            self.bind("<MouseWheel>", _on_mousewheel_mac)
        else:
            self.bind("<MouseWheel>", _on_mousewheel_windows)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.vars = {}
        self._build_meta_section(invoice)
        self._build_items_section(invoice)
        self._build_notes_and_actions(invoice)

    def _bind_widget_autoscroll(self, widget):
        widget.bind("<FocusIn>", self._on_widget_focus_in)

    def _on_widget_focus_in(self, event):
        widget = event.widget
        self.after_idle(lambda w=widget: self._ensure_widget_visible(w))

    def _ensure_widget_visible(self, widget):
        """يمرّر تلقائياً وبحركة سلسة حتى يظهر الحقل الذي حصل على التركيز
        كاملاً ضمن منطقة الرؤية، مع هامش مريح أعلى وأسفل"""
        if not widget or not widget.winfo_exists():
            return
        canvas = getattr(self, "_form_canvas", None)
        if canvas is None or not canvas.winfo_exists() or not canvas.winfo_ismapped():
            return
        try:
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if not bbox:
                return
            scroll_height = max(1, int(bbox[3] - bbox[1]))
            view_height = canvas.winfo_height()
            widget_top = widget.winfo_rooty() - canvas.winfo_rooty() + int(canvas.yview()[0] * scroll_height)
            widget_bottom = widget_top + max(widget.winfo_reqheight(), widget.winfo_height())
            view_top = canvas.yview()[0] * scroll_height
            view_bottom = view_top + view_height
            padding = 24

            target = None
            if widget_bottom > view_bottom - padding:
                target = (widget_bottom + padding - view_height) / scroll_height
            elif widget_top < view_top + padding:
                target = (widget_top - padding) / scroll_height

            if target is not None:
                self._animate_scroll_to(canvas, max(0.0, min(1.0, target)))
        except tk.TclError:
            return

    def _cancel_scroll_animation(self):
        anim_id = getattr(self, "_scroll_anim_id", None)
        if anim_id:
            try:
                self.after_cancel(anim_id)
            except tk.TclError:
                pass
            self._scroll_anim_id = None

    def _animate_scroll_to(self, canvas, target_fraction, duration_ms=180, steps=12):
        """تمرير سلس (ease-out) نحو target_fraction بدلاً من القفز المباشر،
        بحيث يشعر المستخدم بحركة طبيعية عند الانتقال بين الحقول بمفتاح Tab
        أو عند النقر على حقل خارج نطاق الرؤية الحالي"""
        self._cancel_scroll_animation()
        start_fraction = canvas.yview()[0]
        distance = target_fraction - start_fraction
        if abs(distance) < 0.0015:
            canvas.yview_moveto(target_fraction)
            return

        interval = max(8, duration_ms // steps)

        def ease_out_cubic(t):
            return 1 - (1 - t) ** 3

        def step(i=0):
            if not canvas.winfo_exists():
                self._scroll_anim_id = None
                return
            t = min(1.0, (i + 1) / steps)
            canvas.yview_moveto(start_fraction + distance * ease_out_cubic(t))
            if t < 1.0:
                self._scroll_anim_id = self.after(interval, lambda: step(i + 1))
            else:
                self._scroll_anim_id = None

        step()

    def _on_close(self):
        self._cancel_scroll_animation()
        self.destroy()

    def _build_meta_section(self, invoice):
        card = tk.Frame(self.scroll_frame, bg=COL_CARD, bd=1, relief="solid")
        card.pack(fill="x", padx=10, pady=(10, 8))

        header = tk.Frame(card, bg=COL_CARD)
        header.pack(fill="x", padx=14, pady=(12, 8))
        tk.Label(header, text="البيانات الأساسية وتفاصيل الشحنة",
                 bg=COL_CARD, fg=COL_NAVY, font=get_tk_font(10, "bold")).pack(side="right")
        tk.Label(header, text="أدخل البيانات الأساسية ثم عدّل بنود الخدمة والأرقام مباشرة قبل الحفظ",
                 bg=COL_CARD, fg=COL_SUBTEXT, font=get_tk_font(8)).pack(side="right", padx=(10, 0))

        fields = tk.Frame(card, bg=COL_CARD)
        fields.pack(fill="x", padx=12, pady=(0, 10))
        cols_per_row = 3
        field_labels = {key: label for key, label in META_FIELDS}
        field_rows = [
            ("invno", "date", "customer"),
            ("declno", "decldate", "port"),
            ("containercount", "goodstype", "origin"),
        ]

        for row_idx, row_keys in enumerate(field_rows):
            for col_idx, key in enumerate(row_keys):
                frame = tk.Frame(fields, bg=COL_CARD)
                frame.grid(row=row_idx, column=col_idx, padx=8, pady=6, sticky="ew")
                tk.Label(frame, text=field_labels[key], bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(9)).pack(anchor="e")
                var = tk.StringVar(value=(invoice.get(key, "") if invoice else self._default_for(key)))

                if key == "customer":
                    entry = ttk.Combobox(
                        frame,
                        textvariable=var,
                        values=self.app.all_customer_names(),
                        font=get_tk_font(10),
                        justify="right",
                        style="TCombobox"
                    )
                    entry.configure(postcommand=lambda cb=entry: cb.configure(values=self.app.all_customer_names()))
                    entry.bind("<<ComboboxSelected>>", self._update_invno_for_customer)
                    entry.bind("<FocusOut>", self._update_invno_for_customer)
                    var.trace_add("write", lambda *a: self._update_invno_for_customer())
                    entry.pack(fill="x")
                elif key in ("date", "decldate"):
                    date_row, entry = build_date_field(frame, var)
                    date_row.pack(fill="x")
                else:
                    entry = ttk.Entry(
                        frame,
                        textvariable=var,
                        font=get_tk_font(10),
                        justify="right",
                        style="Flat.TEntry"
                    )
                    entry.pack(fill="x")

                self._bind_widget_autoscroll(entry)
                self.vars[key] = var
        for c in range(cols_per_row):
            fields.grid_columnconfigure(c, weight=1)

        tk.Label(card, text="رقم الفاتورة يتولد تلقائياً (رمز الشركة + رقم تسلسلي) بعد اختيار العميل، ويمكن تعديله يدوياً عند الحاجة",
                 bg=COL_CARD, fg="#888", font=get_tk_font(8)).pack(anchor="e", padx=14, pady=(0, 12))

    def _update_invno_for_customer(self, event=None):
        # لا نغيّر رقم فاتورة موجودة مسبقاً عند التعديل
        if self.editing_invno is not None:
            return
        customer_name = self.vars["customer"].get().strip()
        if not customer_name:
            return
        customers = {c["name"]: c for c in load_customers()}
        c = customers.get(customer_name)
        if not c or not c.get("company_code"):
            return
        try:
            invno = next_invoice_number(c["company_code"])
        except ValueError as e:
            messagebox.showwarning("تنبيه", str(e))
            return
        self.vars["invno"].set(invno)

    def _default_for(self, key):
        if key == "date":
            return date.today().isoformat()
        # رقم الفاتورة سيُملأ تلقائياً بعد اختيار العميل (رمز الشركة + الرقم التسلسلي)
        return ""

    def _build_items_section(self, invoice):
        box = ttk.Frame(self.scroll_frame, style="Card.TFrame")
        box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        header = ttk.Frame(box, style="Card.TFrame")
        header.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(header, text="بنود الخدمة",
                 bg=COL_CARD, fg=COL_NAVY, font=get_tk_font(10, "bold")).pack(side="right")
        tk.Label(header, text="أدخل الأسماء ثم استخدم Tab بين دينار وفلس.",
                 bg=COL_CARD, fg=COL_SUBTEXT, font=get_tk_font(8)).pack(side="right", padx=(10, 0))

        grid_header = tk.Frame(box, bg=COL_CARD_SOFT)
        grid_header.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(grid_header, text="م", bg=COL_CARD_SOFT, width=4, font=get_tk_font(9, "bold")).grid(row=0, column=0, padx=4, pady=10)
        tk.Label(grid_header, text="الخدمة", bg=COL_CARD_SOFT, font=get_tk_font(9, "bold")).grid(row=0, column=1, padx=4, pady=10, sticky="e")
        tk.Label(grid_header, text="دينار", bg=COL_CARD_SOFT, width=10, font=get_tk_font(9, "bold")).grid(row=0, column=2, padx=4, pady=10)
        tk.Label(grid_header, text="فلس", bg=COL_CARD_SOFT, width=10, font=get_tk_font(9, "bold")).grid(row=0, column=3, padx=4, pady=10)
        grid_header.grid_columnconfigure(1, weight=1)

        self.item_dinar_vars = []
        self.item_fils_vars = []
        self.item_label_ar_vars = []
        self.item_label_en_vars = []
        self.item_numeric_entries = []
        existing_items = invoice.get("items") if invoice else None

        for idx, (ar, en) in enumerate(SERVICE_ITEMS):
            row = ttk.Frame(box, style="Card.TFrame")
            row.pack(fill="x", padx=8, pady=6)
            row.grid_columnconfigure(1, weight=1)

            tk.Label(row, text=str(idx + 1), width=4, font=get_tk_font(9), bg=COL_CARD).grid(row=0, column=0, padx=4, pady=2)

            existing_item = existing_items[idx] if existing_items and idx < len(existing_items) else {}
            ar_value = existing_item.get("label") if existing_item.get("label") not in (None, "") else ar
            en_value = existing_item.get("labelEn") if existing_item.get("labelEn") not in (None, "") else en

            edit_frame = ttk.Frame(row, style="Card.Soft.TFrame")
            edit_frame.grid(row=0, column=1, sticky="ew", padx=4, pady=2)
            ar_var = tk.StringVar(value=ar_value)
            en_var = tk.StringVar(value=en_value)
            self.item_label_ar_vars.append(ar_var)
            self.item_label_en_vars.append(en_var)

            ar_entry = ttk.Entry(edit_frame, textvariable=ar_var, font=get_tk_font(9), justify="right", style="Flat.TEntry")
            en_entry = ttk.Entry(edit_frame, textvariable=en_var, font=("Consolas", 8), justify="left", style="Flat.TEntry")
            ar_entry.pack(fill="x", pady=2, padx=4)
            en_entry.pack(fill="x", pady=2, padx=4)
            ar_entry.configure(takefocus=False)
            en_entry.configure(takefocus=False)
            self._bind_widget_autoscroll(ar_entry)
            self._bind_widget_autoscroll(en_entry)

            dv = tk.StringVar(value=str(existing_item.get("dinar", "")) if existing_item.get("dinar") not in ("", None) else "")
            fv = tk.StringVar(value=fmt_fils3(existing_item.get("fils", "")) if existing_item.get("fils") not in ("", None) else "")
            dv.trace_add("write", lambda *a: self._update_total())
            fv.trace_add("write", lambda *a: self._update_total())
            dinar_entry = ttk.Entry(row, textvariable=dv, width=10, font=("Consolas", 10), justify="center", style="Flat.TEntry")
            fils_entry = ttk.Entry(row, textvariable=fv, width=10, font=("Consolas", 10), justify="center", style="Flat.TEntry")
            dinar_entry.grid(row=0, column=2, padx=4, pady=2)
            fils_entry.grid(row=0, column=3, padx=4, pady=2)
            fils_entry.bind("<FocusOut>", lambda e, var=fv: var.set(fmt_fils3(var.get())))
            self._bind_widget_autoscroll(dinar_entry)
            self._bind_widget_autoscroll(fils_entry)
            self.item_dinar_vars.append(dv)
            self.item_fils_vars.append(fv)
            self.item_numeric_entries.extend([dinar_entry, fils_entry])

        total_frame = ttk.Frame(box, style="Card.Soft.TFrame")
        total_frame.pack(fill="x", padx=8, pady=(8, 10))
        label_wrapper = tk.Frame(total_frame, bg=COL_CARD_SOFT)
        label_wrapper.pack(fill="x", padx=10, pady=10)
        # Grid layout: [ English words (expands) ] [ Arabic — Total ] [ numeric total ]
        self.total_words_var_en = tk.StringVar(value='')
        # make column 0 expand and reserve extra minimum width to avoid wrapping
        label_wrapper.grid_columnconfigure(0, weight=1, minsize=420)
        label_wrapper.grid_columnconfigure(1, weight=0)
        label_wrapper.grid_columnconfigure(2, weight=0)
        self.total_words_label_en = tk.Label(label_wrapper, textvariable=self.total_words_var_en,
                             font=get_tk_font(9, "italic"), bg=COL_CARD_SOFT,
                             fg=COL_SUBTEXT, justify="left", anchor="w")
        self.total_words_label_en.grid(row=0, column=0, sticky="w", padx=(6, 10))
        tk.Label(label_wrapper, text="Total — المجموع", font=get_tk_font(11, "bold"), bg=COL_CARD_SOFT, fg=COL_NAVY).grid(row=0, column=1, sticky="e")
        self.total_label = tk.Label(label_wrapper, text="0.000 د.ك", font=("Consolas", 13, "bold"), bg=COL_CARD_SOFT, fg="#0F2B46")
        self.total_label.grid(row=0, column=2, sticky="e", padx=(10, 0))
        self._update_total()

    def _focus_next_input(self, event, target):
        if target is not None:
            target.focus_set()
            self.after_idle(lambda: self._ensure_widget_visible(target))
        return "break"

    def _bind_numeric_tab_order(self):
        if not getattr(self, "item_numeric_entries", None):
            return
        for idx, entry in enumerate(self.item_numeric_entries):
            next_entry = self.item_numeric_entries[idx + 1] if idx + 1 < len(self.item_numeric_entries) else getattr(self, "notes_text", None)
            prev_entry = self.item_numeric_entries[idx - 1] if idx > 0 else self.item_numeric_entries[-1]
            entry.bind("<Tab>", lambda e, target=next_entry: self._focus_next_input(e, target))
            entry.bind("<Shift-Tab>", lambda e, target=prev_entry: self._focus_next_input(e, target))

    def _update_total(self):
        total_fils = 0
        for dv, fv in zip(self.item_dinar_vars, self.item_fils_vars):
            total_fils += safe_int(dv.get()) * 1000 + safe_int(fv.get())
        total_amount = total_fils / 1000
        self.total_label.config(text=f"{total_amount:.3f} د.ك")
        # do not display Arabic words for the amount (user requested)
        if hasattr(self, "total_words_var_en"):
            self.total_words_var_en.set(english_currency_words(total_amount))

    def _build_notes_and_actions(self, invoice):
        box = ttk.Frame(self.scroll_frame, style="Card.TFrame")
        box.pack(fill="x", padx=10, pady=(0, 10))
        tk.Label(box, text="📝 ملاحظات", bg=COL_CARD, fg=COL_NAVY, font=get_tk_font(10, "bold")).pack(anchor="e", padx=12, pady=(10, 4))
        self.notes_text = tk.Text(box, height=4, font=get_tk_font(10), relief="flat", bd=0,
                                   highlightthickness=1, highlightbackground=COL_BORDER, background=COL_CARD_SOFT)
        self.notes_text.pack(fill="x", padx=12, pady=(0, 12))
        self._bind_widget_autoscroll(self.notes_text)
        if invoice:
            self.notes_text.insert("1.0", invoice.get("notes", ""))
        self._bind_numeric_tab_order()

        actions = tk.Frame(self.scroll_frame, bg=COL_BG)
        actions.pack(fill="x", padx=10, pady=(0, 16))
        ttk.Button(actions, text="💾 حفظ الفاتورة", style="Accent.TButton", command=self.save).pack(side="right", padx=4)
        ttk.Button(actions, text="إلغاء", style="Ghost.TButton", command=self._on_close).pack(side="right", padx=4)

    def save(self):
        customer = self.vars["customer"].get().strip()
        if not customer:
            messagebox.showwarning("تنبيه", "الرجاء إدخال اسم العميل.")
            return
        self._update_invno_for_customer()
        invno = self.vars["invno"].get().strip()
        if not invno:
            messagebox.showwarning(
                "تنبيه",
                "الرجاء اختيار عميل صالح له رمز شركة أو إدخال رقم الفاتورة يدويًا."
            )
            return
        # التحقق من عدم تكرار رقم الفاتورة عند الإضافة أو تغييره
        existing_numbers = [str(i["invno"]) for i in load_invoices()]
        if invno in existing_numbers and invno != str(self.editing_invno):
            messagebox.showwarning("تنبيه", "رقم الفاتورة مستخدم بالفعل، الرجاء اختيار رقم آخر.")
            return

        d = {key: var.get() for key, var in self.vars.items()}
        d["items"] = []
        for i, (ar, en) in enumerate(SERVICE_ITEMS):
            label_ar = self.item_label_ar_vars[i].get().strip() or ar
            label_en = self.item_label_en_vars[i].get().strip() or en
            d["items"].append({"label": label_ar, "labelEn": label_en,
                                "dinar": self.item_dinar_vars[i].get(),
                                "fils": self.item_fils_vars[i].get()})
        d["notes"] = self.notes_text.get("1.0", "end").strip()

        try:
            save_invoice(d, editing_invno=self.editing_invno)
        except SaveError as e:
            messagebox.showerror("خطأ في الحفظ", str(e))
            return
        messagebox.showinfo("تم", "تم حفظ الفاتورة بنجاح في ملف data.xlsx")
        self.app.refresh_invoice_list()
        if hasattr(self.app, "bal_tree"):
            self.app.refresh_balances()
        self.app.refresh_dashboard()
        self._on_close()


# ------------------------------------------------------------------
# الطباعة: إنشاء صفحة HTML مطابقة لشكل الفاتورة الورقية وفتحها للطباعة
# ------------------------------------------------------------------
_LOGO_IMG_HTML_CACHE = None


def _get_logo_img_html():
    """يقرأ شعار الشركة أو أيقونة التطبيق من القرص مرة واحدة فقط ويخزّنه مؤقتاً."""
    global _LOGO_IMG_HTML_CACHE
    if _LOGO_IMG_HTML_CACHE is None:
        image_path = None
        if os.path.exists(ICON_FILE):
            image_path = ICON_FILE
        elif os.path.exists(LOGO_FILE):
            image_path = LOGO_FILE

        if image_path is not None:
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("ascii")
            _LOGO_IMG_HTML_CACHE = (
                f'<img src="data:image/png;base64,{image_b64}" '
                f'alt="شعار الشركة" width="92" height="92">'
            )
        else:
            _LOGO_IMG_HTML_CACHE = ""
    return _LOGO_IMG_HTML_CACHE


def _safe_filename_part(v):
    s = "".join(c for c in str(v) if c.isalnum())
    return s or "x"


def _build_invoice_page_html(inv, logo_img_html):
    """يبني كتلة HTML لصفحة فاتورة واحدة فقط (بدون <html>/<head>/<body> وبدون زر
    الطباعة)، لتُستخدم سواء لطباعة فاتورة واحدة أو ضمن دفعة من عدة فواتير"""
    total = float(inv.get("total") or 0)
    total_d = int(total)
    total_f = round((total - total_d) * 1000)
    total_words = arabic_currency_words(total)
    total_words_en = english_currency_words(total)

    def esc(v):
        return html_module.escape(str(v)) if v not in (None, "") else "—"

    rows_html = ""
    for idx, it in enumerate(inv["items"]):
        row_bg = " style=\"background:#F7FAFD;\"" if idx % 2 else ""
        rows_html += f"""
        <tr{row_bg}>
          <td class="c">{idx+1}</td>
          <td><div class="svc-cell"><span class="svc-en">{esc(it['labelEn'])}</span><span class="svc-ar">{esc(it['label'])}</span></div></td>
          <td class="c">{it['dinar'] if it['dinar'] not in ('', None) else '—'}</td>
          <td class="c">{fmt_fils3(it['fils']) if it['fils'] not in ('', None) else '—'}</td>
        </tr>"""

    meta_html = ""
    meta_labels = {
        "declno": "رقم البيان الجمركي", "decldate": "تاريخ البيان الجمركي",
        "port": "المنفذ", "containercount": "عدد الحاويات", "goodstype": "نوع البضاعة",
        "origin": "بلد المنشأ",
    }
    for key, label in meta_labels.items():
        meta_html += f'<div><span class="k">{label}: </span><span class="v">{esc(inv.get(key))}</span></div>'

    return f"""  <div class="page">
  <div class="letterhead">
    <div class="header">
      <div class="brand-en">AL ESTIDAMA<br>LOGISTICS SERVICES</div>
      <div class="logo">
        {logo_img_html}
      </div>
      <div class="brand-ar">شركة الاستدامة<br>لتقديم الخدمات اللوجستية</div>
    </div>
    <div class="subheader">
      <div class="invno-box"><span class="k">رقم الفاتورة :</span> <span class="invno">{esc(inv['invno'])}</span></div>
      <div class="title">فاتورة نقداً / بالحساب<span class="title-en">CASH / CREDIT INVOICE</span></div>
      <div class="date-box"><span class="k">التاريخ :</span> <b>{esc(inv.get('date',''))}</b></div>
    </div>
  </div>
  <div class="rtl-block">
    <div>السادة: <b>{esc(inv.get('customer',''))}</b></div>

    <div class="grid">{meta_html}</div>
  </div>
  <table>
    <thead><tr>
      <th style="width:26px;">م</th>
      <th>نوع الخدمة<span class="th-en">Kind of Service</span></th>
      <th style="width:60px;">دينار</th>
      <th style="width:60px;">فلس</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
        <tfoot><tr class="total-row"><td>المجموع — Total</td><td class="eng">{html_module.escape(total_words_en)}</td><td class="c">{total_d}</td><td class="c">{total_f:03d}</td></tr></tfoot>
    </table>
  {'<div style="margin-top:10px;font-size:11px;"><b>ملاحظات:</b> ' + esc(inv.get('notes','')) + '</div>' if inv.get('notes') else ''}
  <div class="sign"><div>المحاسب</div><div>المستلم</div></div>
  <div class="footer">
    الكويت، حولي، شارع ابن خلدون، قطعة (2) مجمع محمود حمد الملا، الدور الثالث، مكتب رقم (11)<br>
    Kuwait, Hawally, Ibn Khaldoon St. Mahmoud Hamad Al Mulla Comp., 3rd Floor, Office No.: (11)<br>
    Tel.: +965 60039333 - +965 65550298 - +965 50508064 — E-mail: alestedama@gmail.com
  </div>
  </div>"""


_INVOICE_PRINT_STYLE = """
  body{font-family:'Tahoma','Arial',sans-serif;color:#1C2530;padding:5px 12px 5px 12px;margin:0px;background:#F3F6FA;}
  .page{max-width:900px;margin:10px auto;}
  .rtl-block{direction:rtl;}
  .letterhead{border:2px solid #0F2B46;border-radius:10px;padding:0px 8px;margin:0 px;background:#fff;}
  .header{display:flex;justify-content:space-between;align-items:center;gap:12px; margin-top:0px}
  .brand-en{flex:1 1 0;text-align:left;direction:ltr;font-weight:bold;color:#1C2530;font-size:15px;line-height:1.15;}
  .brand-ar{flex:1 1 0;text-align:right;direction:rtl;font-weight:bold;color:#1C2530;font-size:17px;line-height:1.15;}
  .logo{flex:0 0 auto;line-height:0;padding:0 8px;}
  .logo svg,.logo img{display:block;border-radius:8px;height:70px; width:auto; }
  .subheader{display:flex;justify-content:space-between;align-items:center;border-top:2px solid #0F2B46;margin-top:6px;padding-top:4px;font-size:10px;}
  .invno-box{direction:rtl;}
  .invno-box .k{color:#333;}
  .title{text-align:center;font-weight:bold;color:#0F2B46;font-size:10px;}
  .title .title-en{display:block;font-size:10px;font-weight:normal;color:#666;letter-spacing:1px;margin-top:2px;}
  .date-box{direction:rtl;}
  .meta{display:flex;justify-content:space-between;margin-bottom:10px;font-size:13px;}
  .invno{color:#93241F;font-weight:bold;font-size:15px;}
  .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px 18px;font-size:12px;margin-bottom:2px;padding:8px 10px;background:#F5F8FA;border-radius:8px;border:1px solid #E7EDF3;}
  .grid .k{color:#777;} .grid .v{font-weight:bold;}
  table{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px;border:1px solid #E7EDF3;border-radius:8px;overflow:hidden;}
  th{background:#0F2B46;color:#fff;padding:7px 8px;text-align:center;}
  th .th-en{display:block;font-weight:normal;font-size:9.5px;color:#C99A3D;margin-top:1px;}
  td{padding:6px 8px;border-bottom:1px solid #E7EDF3;}
  td.c{text-align:center;}
  .svc-cell{display:flex;justify-content:space-between;align-items:center;gap:10px;}
  .svc-en{direction:ltr;text-align:left;color:#333;font-size:11px;flex:1 1 0;}
  .svc-ar{direction:rtl;text-align:right;font-size:12.5px;flex:1 1 0;}
  .total-row td{font-weight:bold;background:#FBF6EA;border-top:2px solid #C99A3D;}
    td.eng{text-align:left;padding-left:10px;font-size:12px;color:#333;direction:ltr}
  .sign{display:flex;justify-content:space-between;margin-top:5px;font-size:13px;font-weight:bold;}
  .sign div{border-top:1px solid #999;padding-top:6px;width:150px;text-align:center;}
  .footer{margin-top:18px;text-align:center;font-size:10px;color:#777;border-top:1px solid #ddd;padding-top:4px;line-height:1.6;}
  .print-btn{background:#0F2B46;color:#fff;border:none;border-radius:8px;padding:11px 30px;font-size:14px;font-weight:bold;font-family:inherit;cursor:pointer;box-shadow:0 2px 6px rgba(15,43,70,.25);}
  .print-btn:hover{background:#081726;}
  .doc-wrap{page-break-after:always;}
  .doc-wrap:last-of-type{page-break-after:auto;}
  @media screen { .doc-wrap + .doc-wrap{margin-top:22px;border-top:3px dashed #C7D2DF;padding-top:22px;} }
  @media print { .noprint{display:none;} body{background:#fff;} }
"""


def generate_and_open_print(inv):
    """يطبع فاتورة واحدة (يستخدم دالة الدفعة أدناه بقائمة من عنصر واحد)"""
    generate_and_open_invoices_print([inv])


def generate_and_open_invoices_print(invoices):
    """يفتح فاتورة واحدة أو عدة فواتير مختارة دفعة واحدة في مستند HTML واحد قابل
    للطباعة، بحيث تكون كل فاتورة في صفحتها الخاصة (فاصل صفحة تلقائي بينها عند
    الطباعة الورقية) مع زر طباعة واحد يطبع الجميع دفعة واحدة"""
    if not invoices:
        return
    logo_img_html = _get_logo_img_html()
    pages_html = "\n".join(
        f'<div class="doc-wrap">{_build_invoice_page_html(inv, logo_img_html)}</div>'
        for inv in invoices
    )
    n = len(invoices)
    btn_text = "🖨 طباعة الفاتورة" if n == 1 else f"🖨 طباعة كل الفواتير ({n})"

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="ltr"><head><meta charset="UTF-8">
<style>{_INVOICE_PRINT_STYLE}</style></head>
<body>
{pages_html}
  <div class="noprint" style="text-align:center;margin-top:20px;">
    <button class="print-btn" onclick="window.print()">{btn_text}</button>
  </div>
</body></html>"""

    if n == 1:
        fname = f"invoice_{_safe_filename_part(invoices[0]['invno'])}.html"
    else:
        fname = f"invoices_batch_{_safe_filename_part(invoices[0]['invno'])}_{_safe_filename_part(invoices[-1]['invno'])}_{n}.html"
    tmp_path = os.path.join(tempfile.gettempdir(), fname)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file://{tmp_path}")


def _build_statement_page_html(customer, date_from, date_to, invoices, payments, logo_img_html):
    """يبني كتلة HTML لكشف حساب عميل واحد فقط (بدون <html>/<head>/<body> وبدون
    زر الطباعة)، لتُستخدم سواء لكشف عميل واحد أو ضمن دفعة من عدة عملاء"""

    def esc(v):
        return html_module.escape(str(v)) if v not in (None, "") else "—"

    STATUS_LABELS = {"paid": "مسددة", "partial": "جزئية", "unpaid": "غير مسددة"}
    STATUS_CLASS = {"paid": "st-paid", "partial": "st-partial", "unpaid": "st-unpaid"}

    # حالة سداد كل فاتورة (مسددة / جزئية / غير مسددة) تُحسب من فواتير ودفعات
    # هذا العميل نفسه، بنفس الطريقة المعتمدة في تبويب سجل الفواتير.
    status_map = invoice_payment_status(invoices, payments)

    # توحيد كل الحركات (فواتير = مدين، دفعات = دائن) في قائمة واحدة مرتبة زمنياً
    txns = []
    for inv in invoices:
        invno = str(inv.get("invno", ""))
        st = status_map.get(invno, {}).get("status", "unpaid")
        txns.append({
            "date": str(inv.get("date", "")),
            "desc": "فاتورة",
            "doc": invno,
            "declno": str(inv.get("declno", "") or ""),
            "debit": float(inv.get("total") or 0),
            "credit": 0.0,
            "status_label": STATUS_LABELS.get(st, ""),
            "status_class": STATUS_CLASS.get(st, ""),
            "sort_key": (str(inv.get("date", "")), 0, invno),
        })
    for p in payments:
        txns.append({
            "date": str(p.get("date", "")),
            "desc": "سند قبض",
            "doc": str(p.get("id", "")),
            "declno": "",
            "debit": 0.0,
            "credit": float(p.get("amount") or 0),
            "status_label": "",
            "status_class": "",
            "sort_key": (str(p.get("date", "")), 1, str(p.get("id", ""))),
        })
    txns.sort(key=lambda t: t["sort_key"])

    # الرصيد الافتتاحي = صافي كل الحركات قبل تاريخ "من" (إن وُجد)
    opening = 0.0
    period_txns = []
    for t in txns:
        if date_from and t["date"] < date_from:
            opening += t["debit"] - t["credit"]
            continue
        if date_to and t["date"] > date_to:
            continue
        period_txns.append(t)

    rows_html = ""
    running = opening
    if date_from:
        rows_html += f"""
        <tr class="opening-row">
          <td class="c">{esc(date_from)}</td>
          <td>رصيد افتتاحي (مرحّل من فترة سابقة)</td>
          <td class="c">—</td>
          <td class="c">—</td>
          <td class="c">—</td>
          <td class="c">—</td>
          <td class="c">{running:.3f}</td>
          <td class="c">—</td>
        </tr>"""

    total_debit = 0.0
    total_credit = 0.0
    for row_idx, t in enumerate(period_txns):
        running += t["debit"] - t["credit"]
        total_debit += t["debit"]
        total_credit += t["credit"]
        row_bg = " style=\"background:#F7FAFD;\"" if row_idx % 2 else ""
        status_html = f'<span class="{t["status_class"]}">{esc(t["status_label"])}</span>' if t["status_label"] else "—"
        rows_html += f"""
        <tr{row_bg}>
          <td class="c">{esc(t['date'])}</td>
          <td>{esc(t['desc'])}</td>
          <td class="c">{esc(t['doc'])}</td>
          <td class="c">{esc(t['declno'])}</td>
          <td class="c">{f"{t['debit']:.3f}" if t['debit'] else '—'}</td>
          <td class="c">{f"{t['credit']:.3f}" if t['credit'] else '—'}</td>
          <td class="c">{running:.3f}</td>
          <td class="c">{status_html}</td>
        </tr>"""

    final_balance = running
    final_balance_words_en = english_currency_words(abs(final_balance))

    if date_from or date_to:
        period_txt = f"من {esc(date_from) if date_from else '—'} إلى {esc(date_to) if date_to else '—'}"
    else:
        period_txt = "كل الفترات"

    balance_word = "مستحق على العميل" if final_balance > 0.0005 else ("رصيد لصالح العميل" if final_balance < -0.0005 else "مسدد بالكامل")

    opening_summary_row = ""
    if date_from:
        opening_summary_row = f'<div><span class="k">الرصيد الافتتاحي: </span><span class="v">{opening:.3f} د.ك</span></div>'

    return f"""  <div class="page">
  <div class="letterhead">
    <div class="header">
      <div class="brand-ar">شركة الاستدامة<br>لتقديم الخدمات اللوجستية</div>
      <div class="logo">{logo_img_html}</div>
      <div class="brand-en">Al Estidama for<br>Logistics Services Co.</div>

    </div>
    <div class="title">كشف حساب عميل — Customer Statement</div>
  </div>
  <div class="meta">
    <div><span class="k">العميل: </span><span class="v">{esc(customer)}</span></div>
    <div><span class="k">الفترة: </span><span class="v">{period_txt}</span></div>
    {opening_summary_row}
  </div>
  <table>
    <thead><tr>
      <th>التاريخ</th>
      <th>نوع البيان</th>
      <th>رقم المستند</th>
      <th>رقم البيان الجمركي</th>
      <th>مدين</th>
      <th>دائن</th>
      <th>الرصيد</th>
      <th>حالة السداد</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
  <div class="summary">
    <div><span>إجمالي الفواتير (مدين):</span><span>{total_debit:.3f} د.ك</span></div>
    <div><span>إجمالي المدفوعات (دائن):</span><span>{total_credit:.3f} د.ك</span></div>
    <div class="final"><span>الرصيد النهائي ({balance_word}):</span><span>{abs(final_balance):.3f} د.ك</span></div>
    <div class="final-words"><span>Amount in English:</span><span>{html_module.escape(final_balance_words_en)}</span></div>
  </div>
  <div class="footer">
    الكويت، حولي، شارع ابن خلدون، قطعة (2) مجمع محمود حمد الملا، الدور الثالث، مكتب رقم (11)<br>
    Kuwait, Hawally, Ibn Khaldoon St. Mahmoud Hamad Al Mulla Comp., 3rd Floor, Office No.: (11)<br>
    Tel.: +965 60039333 - +965 65550298 - +965 50508064 — E-mail: alestedama@gmail.com
  </div>
  </div>"""


_STATEMENT_PRINT_STYLE = """
  .st-paid{color:#1E8449;font-weight:bold;}
  .st-partial{color:#B5750B;font-weight:bold;}
  .st-unpaid{color:#C0342A;font-weight:bold;}
  body{font-family:'Tahoma','Arial',sans-serif;color:#1C2530;padding:5px 12px;margin:0px;background:#F3F6FA;}
  .page{max-width:900px;margin:10px auto;}
  .letterhead{border:2px solid #0F2B46;border-radius:10px;padding:0px 8px;background:#fff;}
  .header{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:0px}
  .brand-en{flex:1 1 0;text-align:left;direction:ltr;font-weight:bold;color:#1C2530;font-size:15px;line-height:1.15;}
  .brand-ar{flex:1 1 0;text-align:right;direction:rtl;font-weight:bold;color:#1C2530;font-size:17px;line-height:1.15;}
  .logo{flex:0 0 auto;line-height:0;}
  .logo img{display:block;border-radius:8px;height:70px;}
  .title{text-align:center;font-weight:bold;color:#0F2B46;font-size:16px;border-top:2px solid #0F2B46;margin-top:6px;padding-top:8px;}
  .meta{display:flex;flex-wrap:wrap;justify-content:space-between;gap:6px;margin:14px 0;font-size:13px;background:#F5F8FA;border:1px solid #E7EDF3;border-radius:8px;padding:10px;}
  .meta .k{color:#777;} .meta .v{font-weight:bold;}
  table{width:100%;border-collapse:collapse;font-size:11.5px;margin-top:10px;border:1px solid #E7EDF3;border-radius:8px;overflow:hidden;table-layout:fixed;}
  th{background:#0F2B46;color:#fff;padding:8px 4px;text-align:center;}
  td{padding:6px 4px;border-bottom:1px solid #E7EDF3;word-wrap:break-word;}
  td.c{text-align:center;}
  tr.opening-row td{background:#F5F8FA;font-style:italic;color:#555;}
  .total-row td{font-weight:bold;background:#FBF6EA;border-top:2px solid #C99A3D;font-size:14px;}
  .summary{margin-top:14px;font-size:13px;background:#F5F8FA;border:1px solid #E7EDF3;border-radius:8px;padding:10px 14px;display:inline-block;min-width:280px;float:left;}
  .summary div{display:flex;justify-content:space-between;padding:3px 0;}
  .summary .final{font-weight:bold;color:#0F2B46;border-top:1px solid #C99A3D;margin-top:4px;padding-top:6px;font-size:14px;}
  .summary-words{margin-top:8px;font-size:12px;color:#333;display:flex;justify-content:space-between;gap:10px;}
  .summary-words span{display:inline-block;}
  .footer{clear:both;margin-top:18px;text-align:center;font-size:10px;color:#777;border-top:1px solid #ddd;padding-top:4px;line-height:1.6;}
  .print-btn{background:#0F2B46;color:#fff;border:none;border-radius:8px;padding:11px 30px;font-size:14px;font-weight:bold;font-family:inherit;cursor:pointer;box-shadow:0 2px 6px rgba(15,43,70,.25);}
  .print-btn:hover{background:#081726;}
  .doc-wrap{page-break-after:always;}
  .doc-wrap:last-of-type{page-break-after:auto;}
  @media screen { .doc-wrap + .doc-wrap{margin-top:22px;border-top:3px dashed #C7D2DF;padding-top:22px;} }
  @media print { .noprint{display:none;} body{background:#fff;} }
"""


def generate_and_open_statement(customer, date_from, date_to, invoices, payments):
    """ينشئ كشف حساب لعميل واحد (يستخدم دالة الدفعة أدناه بقائمة من عنصر واحد)."""
    generate_and_open_statements_print([
        {"customer": customer, "date_from": date_from, "date_to": date_to,
         "invoices": invoices, "payments": payments}
    ])


def generate_and_open_statements_print(items):
    """يفتح كشف حساب عميل واحد أو عدة عملاء مختارين دفعة واحدة في مستند HTML
    واحد قابل للطباعة، بحيث يكون كل عميل في صفحته الخاصة (فاصل صفحة تلقائي
    بينها عند الطباعة الورقية) مع زر طباعة واحد يطبع كشوف الجميع دفعة واحدة"""
    if not items:
        return
    logo_img_html = _get_logo_img_html()
    pages_html = "\n".join(
        f'<div class="doc-wrap">'
        + _build_statement_page_html(
            it["customer"], it["date_from"], it["date_to"], it["invoices"], it["payments"], logo_img_html
        )
        + "</div>"
        for it in items
    )
    n = len(items)
    btn_text = "🖨 طباعة الكشف" if n == 1 else f"🖨 طباعة كشوف كل العملاء ({n})"

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl"><head><meta charset="UTF-8">
<style>{_STATEMENT_PRINT_STYLE}</style></head>
<body>
{pages_html}
  <div class="noprint" style="text-align:center;margin-top:20px;clear:both;">
    <button class="print-btn" onclick="window.print()">{btn_text}</button>
  </div>
</body></html>"""

    if n == 1:
        fname = f"statement_{_safe_filename_part(items[0]['customer'])}.html"
    else:
        fname = f"statements_batch_{n}_customers.html"
    tmp_path = os.path.join(tempfile.gettempdir(), fname)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file://{tmp_path}")


if __name__ == "__main__":
    app = InvoiceApp()
    app.mainloop()
