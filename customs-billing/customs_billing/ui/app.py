# -*- coding: utf-8 -*-
"""النافذة الرئيسية: تخطيط الواجهة والتنقّل بين التبويبات.

`InvoiceApp` يجمع نافذة Tkinter مع أربع واجهات جزئية (mixins)، كل واحدة
مسؤولة عن تبويب واحد، فتبقى كل شاشة في ملفها الخاصinstead of ملف واحد ضخم.
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from ..config import (
    APP_NAME, APP_VERSION, COMPANY_NAME_AR, COMPANY_NAME_EN,
    ICON_FILE, LOGO_FILE, WINDOW_TITLE_AR, get_tk_font,
)
from ..data import SaveError, ensure_storage
from .tab_customers import CustomersMixin
from .tab_dashboard import DashboardMixin
from .tab_invoices import InvoicesMixin
from .tab_payments import PaymentsMixin
from .theme import (
    COL_BG, COL_BORDER, COL_BORDER_SOFT, COL_CARD, COL_CARD_SOFT, COL_DANGER,
    COL_GOLD, COL_GOLD_DARK, COL_MUTED, COL_NAVY, COL_NAVY_DARK, COL_NAVY_SOFT,
    COL_SELECT, COL_SUBTEXT, COL_TEXT,
)

# ttkbootstrap يمنح واجهة مسطّحة وحديثة المظهر (أزرار وألوان وبطاقات أنعم)؛
# هذه المكتبة اختيارية بالكامل — إن لم تكن مثبتة أو كانت ضمن حزمة مُجمَّعة
# فينبغي استخدام واجهة tkinter الافتراضية للحفاظ على التشغيل في ملف
# تنفيذي مستقل.
try:
    import ttkbootstrap as tbs
    if getattr(sys, "frozen", False):
        raise ImportError("Use Tkinter fallback in frozen executable")
    HAS_BOOTSTRAP = True
    _BaseWindow = tbs.Window
except Exception:
    HAS_BOOTSTRAP = False
    _BaseWindow = tk.Tk


class InvoiceApp(
    DashboardMixin,
    InvoicesMixin,
    CustomersMixin,
    PaymentsMixin,
    _BaseWindow,
):
    """نافذة البرنامج الرئيسية: تبويبات الفواتير والعملاء والدفعات."""

    def __init__(self):
        if HAS_BOOTSTRAP:
            super().__init__(themename="flatly")
        else:
            super().__init__()
        self.title(WINDOW_TITLE_AR)
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
            ensure_storage()
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

        # ==================== الشريط العلوي (App bar) ====================
        header = tk.Frame(self, bg=COL_NAVY, height=84)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        # خط تمييز ذهبي رفيع أسفل الشريط لإضفاء لمسة هوية عصرية
        tk.Frame(self, bg=COL_GOLD, height=3).pack(fill="x", side="top")
        self._build_app_bar(header)

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
        version_lbl = tk.Label(sidebar, text=f"{APP_NAME} v{APP_VERSION}", bg=COL_BG,
                           fg=COL_MUTED, font=get_tk_font(7))
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

    def _load_app_bar_logo(self):
        """يحضّر صورة الشعار بحجم مناسب لشريط العنوان، أو None إن لم تتوفّر."""
        for path in (LOGO_FILE, ICON_FILE):
            if os.path.exists(path):
                try:
                    full = tk.PhotoImage(file=path)
                except tk.TclError:
                    continue
                factor = max(1, round(full.width() / 52))
                return full.subsample(factor, factor)
        return None

    def _build_app_bar(self, header):
        """يبني الشريط العلوي: الشعار واسم الشركة يميناً، ووصف مختصر ورقم الإصدار يساراً."""
        # ---- الجهة اليمنى (RTL): الشعار ثم اسم الشركة بالعربية والإنجليزية ----
        brand = tk.Frame(header, bg=COL_NAVY)
        brand.pack(side="right", padx=(8, 24), pady=12)

        logo_img = self._load_app_bar_logo()
        if logo_img is not None:
            self._header_logo_img = logo_img
            # الشعار بخلفية بيضاء، فنضعه على بطاقة بيضاء صغيرة تبرز بوضوح فوق الشريط الكحلي
            tile = tk.Frame(brand, bg="white", highlightbackground=COL_GOLD,
                            highlightthickness=1, padx=6, pady=5)
            tile.pack(side="right", padx=(14, 0))
            tk.Label(tile, image=logo_img, bg="white", bd=0).pack()
        else:
            tk.Label(brand, text="🚢 ✈️ 🚚", bg=COL_NAVY, fg=COL_GOLD,
                     font=get_tk_font(15)).pack(side="right", padx=(14, 0))

        names = tk.Frame(brand, bg=COL_NAVY)
        names.pack(side="right")
        tk.Label(names, text=COMPANY_NAME_AR, bg=COL_NAVY, fg="white",
                 font=get_tk_font(16, "bold"), justify="right").pack(anchor="e")
        tk.Label(names, text=COMPANY_NAME_EN, bg=COL_NAVY, fg=COL_GOLD,
                 font=get_tk_font(9), justify="right").pack(anchor="e", pady=(3, 0))

        # ---- الجهة اليسرى: وصف مختصر ورقم الإصدار ----
        meta = tk.Frame(header, bg=COL_NAVY)
        meta.pack(side="left", padx=(24, 10))
        tk.Label(meta, text="نظام الفوترة والتحصيل الجمركي", bg=COL_NAVY,
                 fg="#9FB2C6", font=get_tk_font(9)).pack(anchor="w")
        tk.Label(meta, text=f"الإصدار {APP_VERSION}", bg=COL_NAVY, fg=COL_GOLD,
                 font=get_tk_font(8, "bold")).pack(anchor="w", pady=(4, 0))

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


def run():
    """يهيّئ التخزين ثم يفتح النافذة الرئيسية ويدير حلقة الأحداث."""
    try:
        ensure_storage()
    except SaveError as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("خطأ في قاعدة البيانات", str(exc))
        root.destroy()
        raise SystemExit(1)
    app = InvoiceApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
