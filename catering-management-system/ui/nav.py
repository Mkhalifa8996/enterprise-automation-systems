# -*- coding: utf-8 -*-
"""الشريط الجانبي للتنقّل وعناصر القائمة NAV_ITEMS."""

import tkinter as tk
from ui.theme import (
    FONT_NAME,
    COLOR_PRIMARY,
    COLOR_ACCENT,
    COLOR_NAV_HOVER,
    COLOR_NAV_ACTIVE,
    F_NAV,
)


# ==================================================================
# الشريط الجانبي للتنقّل
# ==================================================================
class Sidebar(tk.Frame):
    def __init__(self, parent, items, on_select):
        super().__init__(parent, bg=COLOR_PRIMARY, width=230)
        self.pack_propagate(False)
        self.on_select = on_select
        self.buttons = {}
        self._active = None      # عنصر القائمة النشط حالياً

        brand = tk.Frame(self, bg=COLOR_PRIMARY)
        brand.pack(fill="x", pady=(24, 10))
        tk.Label(brand, text="🍽", font=(FONT_NAME, 26), bg=COLOR_PRIMARY, fg=COLOR_ACCENT).pack()
        tk.Label(brand, text="نظام إدارة الضيافة", font=(FONT_NAME, 13, "bold"),
                 bg=COLOR_PRIMARY, fg="white").pack(pady=(4, 0))
        tk.Label(brand, text="Catering Management System", font=(FONT_NAME, 8),
                 bg=COLOR_PRIMARY, fg="#E4C9A8").pack()

        sep = tk.Frame(self, bg=COLOR_ACCENT, height=2)
        sep.pack(fill="x", padx=18, pady=14)

        nav_wrap = tk.Frame(self, bg=COLOR_PRIMARY)
        nav_wrap.pack(fill="both", expand=True)

        for key, icon, label in items:
            self._add_button(nav_wrap, key, icon, label)

    def _add_button(self, parent, key, icon, label):
        btn = tk.Frame(parent, bg=COLOR_PRIMARY, cursor="hand2")
        btn.pack(fill="x", padx=10, pady=2)
        txt = tk.Label(btn, text=f"{label}   {icon}", font=F_NAV, bg=COLOR_PRIMARY,
                        fg="#F1E1CC", anchor="e", justify="right", padx=14, pady=10)
        txt.pack(fill="x")
        self.buttons[key] = (btn, txt)

        def enter(_e):
            if self._active != key:
                btn.config(bg=COLOR_NAV_HOVER)
                txt.config(bg=COLOR_NAV_HOVER)

        def leave(_e):
            if self._active != key:
                btn.config(bg=COLOR_PRIMARY)
                txt.config(bg=COLOR_PRIMARY)

        def click(_e):
            self.on_select(key)

        for w in (btn, txt):
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)
            w.bind("<Button-1>", click)

    def set_active(self, key):
        self._active = key
        for k, (btn, txt) in self.buttons.items():
            bg = COLOR_NAV_ACTIVE if k == key else COLOR_PRIMARY
            fg = COLOR_PRIMARY if k == key else "#F1E1CC"
            btn.config(bg=bg)
            txt.config(bg=bg, fg=fg, font=(FONT_NAME, 11, "bold") if k == key else F_NAV)


# ==================================================================
# التطبيق الرئيسي
# ==================================================================
NAV_ITEMS = [
    ("home", "🏠", "الرئيسية"),
    ("orders", "📦", "الطلبات"),
    ("invoices", "🧾", "الفواتير"),
    ("expenses", "🧮", "المشتريات"),
    ("masterdata", "🗂", "البيانات الأساسية"),
    ("salaries", "💰", "الرواتب"),
    ("reports", "📊", "التقارير المالية"),
]

PAGE_TITLES = dict((k, label) for k, _, label in NAV_ITEMS)
