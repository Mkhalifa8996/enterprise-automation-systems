# -*- coding: utf-8 -*-
"""تبويب لوحة المعلومات: مؤشرات الأداء وأكبر العملاء مديونية."""

import tkinter as tk
from tkinter import ttk

from ..config import get_tk_font
from ..data import get_dashboard_stats, load_customers, load_invoices, load_payments
from .theme import (
    COL_BG,
    COL_BORDER,
    COL_CARD,
    COL_DANGER,
    COL_GOLD,
    COL_NAVY,
    COL_NAVY_SOFT,
    COL_ROW_ALT,
    COL_SUBTEXT,
)


class DashboardMixin:
    """يبني تبويب «نظرة عامة» ويحدّث بطاقات المؤشرات."""
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
