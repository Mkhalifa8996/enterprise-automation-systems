# -*- coding: utf-8 -*-
"""
نظام إدارة مطعم التموين والولائم - عمال وشيفات، معدات وسيارات توصيل،
مصاريف تأسيس، مصاريف شهرية ثابتة، مشتريات يومية (خضروات/لحوم/خبز/أرز
وبقوليات/غاز/زيوت)، عملاء (مؤسسات ومناسبات)، طلبات مؤسسات دائمة (شركات/
مستشفيات/مدارس)، عزائم ومناسبات (أفراح وعزائم بتاريخ محدد)، فواتير
العملاء، رواتب العمال، وتقارير مالية.

واجهة عصرية بتخطيط من اليمين لليسار: قائمة تنقّل جانبية على يمين الشاشة
ومحتوى كل شاشة يُعرض إلى يسارها.

طريقة التشغيل:
    pip install openpyxl
    python restaurant_desktop_app.py

التخزين: SQLite افتراضياً (restaurant.db بجوار البرنامج). عند أول إقلاع
ووجود ملف Excel القديم (restaurant_data.xlsx) تُستورد بياناته تلقائياً
مع نسخة احتياطية — لا حاجة لأي خطوة. وضع Excel القديم متاح فقط عبر
RESTAURANT_BACKEND=excel، والتصدير إلى Excel عبر زر في التقارير.

بنية الكود: الواجهة مقسومة في حزمة ui/ — المظهر في ui/theme، التنقل في ui/nav،
الشاشات العامة في ui/tabs، الطباعة في ui/printing، نافذة السجل في ui/record_window،
وصفحات التطبيق في ui/pages/. هذا الملف نقطة التشغيل وهيكل التطبيق الرئيسي فقط.

الاختبارات (تعمل على ملفات مؤقتة ولا تلمس بياناتك):
    python tests/test_data_layer.py        # طبقة البيانات والتقارير المالية
    python tests/test_smoke.py             # كل الشاشات + إصدار فاتورة فعلياً
    python tests/test_launch_real_data.py  # إقلاع حقيقي على ملف البيانات

خطة التطوير والمراحل القادمة موثّقة في EVOLUTION.md بجانب هذا الملف.
"""


import os
import sys
import traceback

import tkinter as tk
from tkinter import ttk

from ui import dialogs as messagebox

import restaurant_data as rd

# ---- بنية الكود: كل مكوّنات الواجهة تعيش في حزمة ui/ ----
from ui.theme import (
    FONT_NAME,
    COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_BG,
    COLOR_CARD, COLOR_MUTED, COLOR_BORDER,
    COLOR_ACCENT, COLOR_DANGER,
    F_TITLE, F_BODY, F_BOLD,
)
from ui.nav import Sidebar, NAV_ITEMS, PAGE_TITLES
from ui.pages.home import HomePages
from ui.pages.orders import OrdersPages
from ui.pages.expenses import ExpensesPages
from ui.pages.masterdata import MasterDataPages
from ui.pages.invoices import InvoicesPages
from ui.pages.salaries import SalariesPages
from ui.pages.reports import ReportsPages
from core.version import __version__


class RestaurantApp(HomePages, OrdersPages, ExpensesPages, MasterDataPages,
                    InvoicesPages, SalariesPages, ReportsPages, tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"نظام إدارة مطعم التموين والولائم — v{__version__}")
        self.geometry("1340x780")
        self.configure(bg=COLOR_BG)
        self.minsize(1080, 660)

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.style.configure("Treeview", font=(FONT_NAME, 10), rowheight=27,
                              background=COLOR_CARD, fieldbackground=COLOR_CARD,
                              borderwidth=0)
        self.style.configure("Treeview.Heading", font=(FONT_NAME, 9, "bold"),
                              background=COLOR_PRIMARY, foreground="white", relief="flat")
        self.style.map("Treeview.Heading", background=[("active", COLOR_PRIMARY_LIGHT)])
        self.style.map("Treeview", background=[("selected", COLOR_PRIMARY_LIGHT)],
                        foreground=[("selected", "white")])
        self.style.configure("TButton", font=F_BODY, padding=6)
        self.style.configure("Accent.TButton", font=F_BOLD, padding=7,
                              background=COLOR_ACCENT, foreground=COLOR_PRIMARY)
        self.style.map("Accent.TButton", background=[("active", "#E5BC70")])
        self.style.configure("Danger.TButton", font=F_BODY, padding=6)
        self.style.map("Danger.TButton", foreground=[("!disabled", COLOR_DANGER)])
        self.style.configure("TCombobox", padding=4)
        self.style.configure("TCheckbutton", background=COLOR_CARD, font=F_BODY)

        # تجهيز ملف البيانات + نسخة احتياطية يومية تلقائية قبل أي تعديل
        self.last_backup = rd.startup_maintenance()

        # -------- تخطيط الشاشة الرئيسي: قائمة يمين + محتوى يسارها --------
        self.sidebar = Sidebar(self, NAV_ITEMS, self.show_page)
        self.sidebar.pack(side="right", fill="y")

        content = tk.Frame(self, bg=COLOR_BG)
        content.pack(side="right", fill="both", expand=True)

        topbar = tk.Frame(content, bg=COLOR_CARD, height=54)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        self.page_title_lbl = tk.Label(topbar, text="", font=F_TITLE, bg=COLOR_CARD,
                                        fg=COLOR_PRIMARY, anchor="e")
        self.page_title_lbl.pack(side="right", padx=22, pady=10)
        backup_txt = ("نسخة احتياطية اليوم: " + os.path.basename(self.last_backup)
                      if self.last_backup
                      else "النسخ الاحتياطية في مجلد: " + rd.BACKUP_DIR_NAME)
        tk.Label(topbar, text=f"ملف البيانات: {rd.DATA_FILE}   |   {backup_txt}",
                 bg=COLOR_CARD, fg=COLOR_MUTED, font=(FONT_NAME, 8)).pack(side="left", padx=20)
        tk.Frame(content, bg=COLOR_BORDER, height=1).pack(fill="x")

        self.pages_area = tk.Frame(content, bg=COLOR_BG)
        self.pages_area.pack(fill="both", expand=True)
        self.pages_area.grid_rowconfigure(0, weight=1)
        self.pages_area.grid_columnconfigure(0, weight=1)

        self.pages = {}
        self.page_refreshers = {}  # key -> list[callable] تُنفَّذ عند فتح الشاشة
        self.sub_notebooks = {}    # key -> ttk.Notebook للتبويبات الفرعية داخل الشاشات المجمّعة

        self._build_home_page()
        self._build_orders_page()
        self._build_invoices_page()
        self._build_expenses_page()
        self._build_masterdata_page()
        self._build_salaries_tab()
        self._build_reports_tab()

        self.show_page("home")

    # ---------------- التنقّل بين الشاشات ----------------
    def register_page(self, key, frame, refreshers=None):
        frame.grid(row=0, column=0, sticky="nsew")
        self.pages[key] = frame
        self.page_refreshers[key] = refreshers or []

    def show_page(self, key, sub_index=None):
        """
        فتح شاشة. sub_index: رقم التبويب الفرعي المطلوب تفعيله داخل الشاشات
        المجمّعة (مثل فتح شاشة الطلبات مباشرة على تبويب عروض الأسعار).
        """
        if key not in self.pages:
            return
        self.pages[key].tkraise()
        self.sidebar.set_active(key)
        self.page_title_lbl.config(text=PAGE_TITLES.get(key, ""))
        if sub_index is not None:
            notebook = self.sub_notebooks.get(key)
            if notebook is not None:
                try:
                    notebook.select(sub_index)
                except tk.TclError:
                    pass
        for fn in self.page_refreshers.get(key, []):
            try:
                fn()
            except Exception:
                traceback.print_exc()

    def on_close(self):
        """إغلاق البرنامج: تحرير قفل النسخة الواحدة ثم إغلاق النافذة."""
        rd.release_instance_lock()
        self.destroy()


def main(auto_close_ms=None):
    """
    نقطة تشغيل البرنامج:
      1) قفل النسخة الواحدة: منع فتح نسختين على نفس ملف البيانات (سبب رئيسي لفقدان البيانات).
      2) فتح الواجهة، وهي تجهّز ملف البيانات وتأخذ نسخة احتياطية يومية.
    auto_close_ms: تُستخدم في الاختبارات للإغلاق التلقائي بعد مدة.
    """
    if not rd.acquire_instance_lock():
        probe = tk.Tk()
        probe.withdraw()
        messagebox.showwarning(
            "تنبيه",
            "البرنامج مفتوح بالفعل في نافذة أخرى على نفس ملف البيانات:\n"
            f"{rd.DATA_FILE}\n\n"
            "أغلق النافذة الأخرى أولاً، لأن فتح نسختين معاً قد يؤدي إلى فقدان البيانات.")
        probe.destroy()
        return 1
    try:
        app = RestaurantApp()
        app.protocol("WM_DELETE_WINDOW", app.on_close)
        if auto_close_ms:
            app.after(auto_close_ms, app.on_close)
        app.mainloop()
    finally:
        rd.release_instance_lock()
    return 0


if __name__ == "__main__":
    sys.exit(main())
