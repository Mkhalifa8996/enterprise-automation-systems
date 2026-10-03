# -*- coding: utf-8 -*-
"""
شاشة البيانات الأساسية المجمّعة (تبويبات داخل شاشة واحدة):
  - العملاء (مؤسسات وعملاء مناسبات)
  - العمال والشيفات
  - المعدات وسيارات التوصيل
  - الأصناف والمنيو (كتالوج بتكلفة وسعر بيع)
"""

import restaurant_data as rd
from ui.tabs import CrudTab


class MasterDataPages:
    # ---------------- بناء صفحة البيانات الأساسية المجمّعة ----------------
    def _build_masterdata_page(self):
        from tkinter import ttk
        import tkinter as tk
        from ui.theme import COLOR_BG

        frame = tk.Frame(self.pages_area, bg=COLOR_BG)
        nb = ttk.Notebook(frame)
        nb.pack(fill="both", expand=True)
        self.masterdata_notebook = nb
        self.sub_notebooks["masterdata"] = nb

        customers_tab = tk.Frame(nb, bg=COLOR_BG)
        staff_tab = tk.Frame(nb, bg=COLOR_BG)
        equipment_tab = tk.Frame(nb, bg=COLOR_BG)
        products_tab = tk.Frame(nb, bg=COLOR_BG)
        nb.add(customers_tab, text=" 👥 العملاء ")
        nb.add(staff_tab, text=" 👨‍🍳 العمال والشيفات ")
        nb.add(equipment_tab, text=" 🧰 المعدات والسيارات ")
        nb.add(products_tab, text=" 🍽 الأصناف والمنيو ")

        self._build_customers_tab(customers_tab)
        self._build_staff_tab(staff_tab)
        self._build_equipment_tab(equipment_tab)
        self._build_products_tab(products_tab)

        self.register_page("masterdata", frame, refreshers=[
            self.customers_tab.refresh,
            self.staff_tab.refresh,
            self.equipment_tab.refresh,
            self.products_tab.refresh,
        ])

    # ---------------- تبويب العملاء ----------------
    def _build_customers_tab(self, parent):
        self.customers_tab = CrudTab(
            parent, rd.CUSTOMER_FIELDS, rd.load_customers, rd.save_customer,
            rd.delete_customer, "name", "العملاء",
            select_fields={"type": rd.CUSTOMER_TYPES})
        self.customers_tab.frame.pack(fill="both", expand=True)

    # ---------------- تبويب العمال والشيفات ----------------
    def _build_staff_tab(self, parent):
        self.staff_tab = CrudTab(
            parent, rd.STAFF_FIELDS, rd.load_staff, rd.save_staff,
            rd.delete_staff, "name", "العمال والشيفات",
            select_fields={"job_title": rd.JOB_TITLES})
        self.staff_tab.frame.pack(fill="both", expand=True)

    # ---------------- تبويب المعدات وسيارات التوصيل ----------------
    def _build_equipment_tab(self, parent):
        self.equipment_tab = CrudTab(
            parent, rd.EQUIPMENT_FIELDS, rd.load_equipment, rd.save_equipment,
            rd.delete_equipment, "name", "المعدات وسيارات التوصيل",
            select_fields={"category": rd.EQUIPMENT_CATEGORIES})
        self.equipment_tab.frame.pack(fill="both", expand=True)

    # ---------------- تبويب الأصناف والمنيو ----------------
    def _build_products_tab(self, parent):
        self.products_tab = CrudTab(
            parent, rd.PRODUCT_FIELDS, rd.load_products, rd.save_product,
            rd.delete_product, "name", "الأصناف والمنيو",
            select_fields={"category": rd.PRODUCT_CATEGORIES, "unit": rd.PRODUCT_UNITS})
        self.products_tab.frame.pack(fill="both", expand=True)
