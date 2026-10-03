# -*- coding: utf-8 -*-
"""
شاشة المشتريات المجمّعة (تبويبات داخل شاشة واحدة):
  - المشتريات اليومية
  - مصاريف التأسيس
  - المصاريف الشهرية الثابتة
  - النثريات اليومية (مصروفات نقدية صغيرة من الصندوق)
"""

import restaurant_data as rd
from ui.tabs import CrudTab, DatedOrderTab
from ui.rtl import add_rtl_tabs


class ExpensesPages:
    # ---------------- بناء صفحة المصاريف المجمّعة ----------------
    def _build_expenses_page(self):
        from tkinter import ttk
        import tkinter as tk
        from ui.theme import COLOR_BG

        frame = tk.Frame(self.pages_area, bg=COLOR_BG)
        nb = ttk.Notebook(frame)
        nb.pack(fill="both", expand=True)
        self.expenses_notebook = nb
        self.sub_notebooks["expenses"] = nb

        purchases_tab = tk.Frame(nb, bg=COLOR_BG)
        setup_tab = tk.Frame(nb, bg=COLOR_BG)
        monthly_tab = tk.Frame(nb, bg=COLOR_BG)
        petty_tab = tk.Frame(nb, bg=COLOR_BG)
        add_rtl_tabs(nb, [
            (purchases_tab, " 🛒 المشتريات اليومية "),
            (setup_tab, " 🏗 مصاريف التأسيس "),
            (monthly_tab, " 📅 المصاريف الشهرية "),
            (petty_tab, " 💸 النثريات اليومية "),
        ])

        self._build_purchases_tab(purchases_tab)
        self._build_setup_expenses_tab(setup_tab)
        self._build_monthly_expenses_tab(monthly_tab)
        self._build_petty_cash_tab(petty_tab)

        self.register_page("expenses", frame, refreshers=[
            self.purchases_tab.set_today_if_empty,
            self.purchases_tab.refresh,
            self.setup_tab.refresh,
            self.monthly_tab.refresh,
            self.petty_tab.set_today_if_empty,
            self.petty_tab.refresh,
        ])

    # ---------------- تبويب المشتريات اليومية ----------------
    def _build_purchases_tab(self, parent):
        self.purchases_tab = DatedOrderTab(
            parent, rd.PURCHASE_FIELDS, rd.load_purchases, rd.save_purchase,
            rd.delete_purchase, "id", "المشتريات اليومية", date_field="date",
            select_fields={"type": rd.PURCHASE_TYPES, "unit": rd.PURCHASE_UNITS},
            readonly_fields=["id", "total_cost"])
        self.purchases_tab.frame.pack(fill="both", expand=True)

    # ---------------- تبويب مصاريف التأسيس ----------------
    def _build_setup_expenses_tab(self, parent):
        self.setup_tab = CrudTab(
            parent, rd.SETUP_EXPENSE_FIELDS, rd.load_setup_expenses, rd.save_setup_expense,
            rd.delete_setup_expense, "id", "مصاريف التأسيس",
            select_fields={"type": rd.SETUP_EXPENSE_TYPES},
            readonly_fields=["id"])
        self.setup_tab.frame.pack(fill="both", expand=True)

    # ---------------- تبويب المصاريف الشهرية الثابتة ----------------
    def _build_monthly_expenses_tab(self, parent):
        self.monthly_tab = CrudTab(
            parent, rd.MONTHLY_EXPENSE_FIELDS, rd.load_monthly_expenses, rd.save_monthly_expense,
            rd.delete_monthly_expense, "id", "المصاريف الشهرية الثابتة",
            select_fields={"type": rd.MONTHLY_EXPENSE_TYPES},
            readonly_fields=["id"])
        self.monthly_tab.frame.pack(fill="both", expand=True)

    # ---------------- تبويب النثريات اليومية ----------------
    def _build_petty_cash_tab(self, parent):
        self.petty_tab = DatedOrderTab(
            parent, rd.PETTY_CASH_FIELDS, rd.load_petty_cash, rd.save_petty_cash,
            rd.delete_petty_cash, "id", "النثريات اليومية", date_field="date",
            select_fields={"type": rd.PETTY_CASH_TYPES},
            readonly_fields=["id"])
        self.petty_tab.frame.pack(fill="both", expand=True)
