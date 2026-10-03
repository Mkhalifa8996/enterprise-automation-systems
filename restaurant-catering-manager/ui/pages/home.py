# -*- coding: utf-8 -*-
"""الصفحة الرئيسية: بطاقات إحصائية وأزرار سريعة ونسخة احتياطية فورية."""

from datetime import date
import tkinter as tk
from tkinter import ttk
from ui import dialogs as messagebox
import restaurant_data as rd
from ui.theme import (
    FONT_NAME,
    COLOR_PRIMARY,
    COLOR_PRIMARY_LIGHT,
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_CARD,
    COLOR_MUTED,
    COLOR_SUCCESS,
    COLOR_DANGER,
    F_SUBTITLE,
    F_BODY,
    card_frame,
)


class HomePages:
    # ---------------- الشاشة الرئيسية (لوحة سريعة) ----------------
    def _build_home_page(self):
        frame = tk.Frame(self.pages_area, bg=COLOR_BG)
        self.home_frame = frame

        welcome = tk.Frame(frame, bg=COLOR_BG)
        welcome.pack(fill="x", padx=20, pady=(20, 8))
        tk.Label(welcome, text=f"مرحباً بك في {rd.COMPANY_NAME_AR}", font=(FONT_NAME, 14, "bold"),
                 bg=COLOR_BG, fg=COLOR_PRIMARY, anchor="e").pack(fill="x")
        tk.Label(welcome, text="نظرة سريعة على نشاط المطعم اليوم.", font=F_SUBTITLE,
                 bg=COLOR_BG, fg=COLOR_MUTED, anchor="e").pack(fill="x")

        self.stats_wrap = tk.Frame(frame, bg=COLOR_BG)
        self.stats_wrap.pack(fill="x", padx=20, pady=10)

        self.register_page("home", frame, refreshers=[self.refresh_home_stats])

    def _stat_card(self, parent, title, value, color):
        card = card_frame(parent)
        body = card.body
        tk.Label(body, text=title, font=F_BODY, bg=COLOR_CARD, fg=COLOR_MUTED, anchor="e").pack(
            fill="x", padx=16, pady=(16, 2))
        tk.Label(body, text=value, font=(FONT_NAME, 20, "bold"), bg=COLOR_CARD, fg=color,
                 anchor="e").pack(fill="x", padx=16, pady=(0, 16))
        return card

    def refresh_home_stats(self):
        for w in self.stats_wrap.winfo_children():
            w.destroy()
        today_iso = date.today().isoformat()
        orders_today = rd.institutional_orders_for_date(today_iso)
        upcoming = rd.upcoming_events(today_iso)
        summary = rd.financial_summary()

        cards = [
            ("وجبات مؤسسات اليوم", str(len(orders_today)), COLOR_PRIMARY),
            ("مناسبات قادمة", str(len(upcoming)), COLOR_PRIMARY_LIGHT),
            ("عدد العملاء", str(len(rd.load_customers())), COLOR_ACCENT),
            ("عدد الموظفين", str(len(rd.load_staff())), COLOR_PRIMARY),
            ("صافي الربح التشغيلي", f"{summary['operating_profit']:.3f} د.ك", COLOR_SUCCESS),
            ("مستحقات لم تُحصّل", f"{summary.get('receivables', 0.0):.3f} د.ك", COLOR_DANGER),
        ]
        for i, (title, value, color) in enumerate(cards):
            c = self._stat_card(self.stats_wrap, title, value, color)
            c.grid(row=0, column=len(cards) - 1 - i, padx=8, sticky="ew")
        for i in range(len(cards)):
            self.stats_wrap.grid_columnconfigure(i, weight=1)

        shortcuts = card_frame(self.home_frame, "اختصارات سريعة")
        for old in getattr(self, "_home_shortcuts", []):
            old.destroy()
        shortcuts.pack(fill="x", padx=20, pady=10)
        self._home_shortcuts = [shortcuts]
        row = tk.Frame(shortcuts.body, bg=COLOR_CARD)
        row.pack(fill="x", padx=14, pady=14, anchor="e")
        ttk.Button(row, text="+ إضافة طلب مؤسسة", style="Accent.TButton",
                   command=lambda: self.show_page("orders", 0)).pack(side="right", padx=4)
        ttk.Button(row, text="+ إضافة مناسبة", style="Accent.TButton",
                   command=lambda: self.show_page("orders", 1)).pack(side="right", padx=4)
        ttk.Button(row, text="+ عرض سعر", style="Accent.TButton",
                   command=lambda: self.show_page("orders", 2)).pack(side="right", padx=4)
        ttk.Button(row, text="عرض الفواتير", command=lambda: self.show_page("invoices", 0)).pack(side="right", padx=4)
        ttk.Button(row, text="كشف حساب عميل", command=lambda: self.show_page("invoices", 2)).pack(side="right", padx=4)
        ttk.Button(row, text="التقارير المالية", command=lambda: self.show_page("reports")).pack(side="right", padx=4)
        ttk.Button(row, text="نسخة احتياطية الآن", command=self.backup_now).pack(side="right", padx=4)

    def backup_now(self):
        """زر يدوي لأخذ نسخة احتياطية فورية من ملف البيانات."""
        try:
            path = rd.backup_data_file(force=True)
        except OSError as e:
            messagebox.showwarning("تنبيه", f"تعذّر أخذ النسخة الاحتياطية:\n{e}")
            return
        self.last_backup = path
        messagebox.showinfo("تم", f"تم أخذ نسخة احتياطية:\n{path}")
