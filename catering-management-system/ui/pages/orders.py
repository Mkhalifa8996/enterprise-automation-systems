# -*- coding: utf-8 -*-
"""
شاشة الطلبات والمناسبات المجمّعة (تبويبات داخل شاشة واحدة):
  - طلبات المؤسسات الدائمة
  - العزائم والمناسبات
  - عروض الأسعار (+ تحويل العرض المقبول إلى مناسبة)
  - جدولة التوصيل (إسناد السائق والسيارة ووسم التسليم)
"""

from datetime import date
import tkinter as tk
from tkinter import ttk
from ui import dialogs as messagebox
from ui.rtl import add_rtl_tabs
import restaurant_data as rd
from ui.theme import (
    COLOR_BG,
    COLOR_CARD,
    COLOR_MUTED,
    F_LABEL,
    F_BODY,
    safe_str,
    card_frame,
)
from ui.tabs import CrudTab, DatedOrderTab


class OrdersPages:
    # ---------------- بناء صفحة الطلبات المجمّعة ----------------
    def _build_orders_page(self):
        frame = tk.Frame(self.pages_area, bg=COLOR_BG)
        nb = ttk.Notebook(frame)
        nb.pack(fill="both", expand=True)
        self.orders_notebook = nb
        self.sub_notebooks["orders"] = nb

        inst_tab = tk.Frame(nb, bg=COLOR_BG)
        events_tab = tk.Frame(nb, bg=COLOR_BG)
        quotes_tab = tk.Frame(nb, bg=COLOR_BG)
        dlv_tab = tk.Frame(nb, bg=COLOR_BG)
        add_rtl_tabs(nb, [
            (inst_tab, " 🏢 طلبات المؤسسات "),
            (events_tab, " 🎉 المناسبات والولائم "),
            (quotes_tab, " 📝 عروض الأسعار "),
            (dlv_tab, " 🚚 جدولة التوصيل "),
        ])

        self._build_institutional_tab(inst_tab)
        self._build_events_tab(events_tab)
        self._build_quotations_tab(quotes_tab)
        self._build_deliveries_tab(dlv_tab)

        self.register_page("orders", frame, refreshers=[
            self.inst_tab.refresh_customer_options,
            self.inst_tab.set_today_if_empty,
            self.inst_tab.refresh,
            self.events_tab.refresh_customer_options,
            self.events_tab.set_today_if_empty,
            self.events_tab.refresh,
            self._refresh_quotation_customers,
            self.quotations_tab.refresh,
            self.refresh_deliveries,
        ])

    def _refresh_quotation_customers(self):
        """تحديث قائمة العملاء في تبويب عروض الأسعار (CrudTab عام لا يملك الدالة الجاهزة)."""
        self.quotations_tab.refresh_combo("customer", [c["name"] for c in rd.load_customers()])

    # ---------------- تبويب طلبات المؤسسات الدائمة ----------------
    def _build_institutional_tab(self, parent):
        self.inst_tab = DatedOrderTab(
            parent, rd.INSTITUTIONAL_ORDER_FIELDS,
            rd.load_institutional_orders, rd.save_institutional_order, rd.delete_institutional_order,
            "id", "طلبات المؤسسات الدائمة", date_field="date",
            select_fields={
                "meal_type": rd.MEAL_TYPES,
                "frequency": rd.ORDER_FREQUENCIES,
                "customer": [],
            },
            readonly_fields=["id", "total", "invoiced", "invoice_no"],
        )
        self.inst_tab.frame.pack(fill="both", expand=True)

    # ---------------- تبويب العزائم والمناسبات ----------------
    def _build_events_tab(self, parent):
        self.events_tab = DatedOrderTab(
            parent, rd.EVENT_FIELDS,
            rd.load_events, rd.save_event, rd.delete_event,
            "id", "العزائم والمناسبات", date_field="event_date",
            select_fields={
                "event_type": rd.EVENT_TYPES,
                "customer": [],
            },
            readonly_fields=["id", "total", "invoiced", "invoice_no"],
        )
        self.events_tab.frame.pack(fill="both", expand=True)

    # ---------------- تبويب عروض الأسعار ----------------
    def _build_quotations_tab(self, parent):
        self.quotations_tab = CrudTab(
            parent, rd.QUOTATION_FIELDS,
            rd.load_quotations, rd.save_quotation, rd.delete_quotation,
            "id", "عروض الأسعار",
            select_fields={
                "event_type": rd.EVENT_TYPES,
                "customer": [],
                "status": rd.QUOTATION_STATUSES,
            },
            readonly_fields=["id", "total", "converted_id"],
            extra_buttons=[
                {"label": "تحويل العرض المحدد إلى مناسبة", "style": "Accent.TButton",
                 "command": self.convert_selected_quotation},
            ],
        )
        self.quotations_tab.frame.pack(fill="both", expand=True)

    def convert_selected_quotation(self):
        row = self.quotations_tab.get_selected_row()
        if not row:
            return
        try:
            event = rd.convert_quotation_to_event(row.get("id"))
        except ValueError as e:
            messagebox.showwarning("تنبيه", str(e))
            return
        self.quotations_tab.refresh()
        messagebox.showinfo("تم", "تم إنشاء المناسبة رقم %s بتاريخ %s بنجاح."
                            % (event["id"], event["event_date"]))

    # ---------------- تبويب جدولة التوصيل ----------------
    def _build_deliveries_tab(self, parent):
        frame = tk.Frame(parent, bg=COLOR_BG)
        frame.pack(fill="both", expand=True)

        top = card_frame(frame, "إسناد السائق والسيارة لتسليمات يوم محدد")
        top.pack(fill="x", padx=16, pady=(16, 8))
        row = tk.Frame(top.body, bg=COLOR_CARD)
        row.pack(fill="x", padx=14, pady=(0, 10))

        tk.Label(row, text="التاريخ (YYYY-MM-DD):", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).grid(row=0, column=3, padx=6, pady=6, sticky="e")
        self.dlv_date_var = tk.StringVar(value=date.today().isoformat())
        tk.Entry(row, textvariable=self.dlv_date_var, font=F_BODY, justify="right",
                 width=13, relief="solid", bd=1).grid(row=0, column=2, padx=6, pady=6)
        ttk.Button(row, text="تعبئة تاريخ اليوم",
                   command=lambda: self.dlv_date_var.set(date.today().isoformat())).grid(
            row=0, column=1, padx=6, pady=6)
        ttk.Button(row, text="عرض التسليمات", style="Accent.TButton",
                   command=self.refresh_deliveries).grid(row=0, column=0, padx=6, pady=6)

        tk.Label(row, text="السائق:", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).grid(row=1, column=3, padx=6, pady=6, sticky="e")
        self.dlv_driver_var = tk.StringVar()
        self.dlv_driver_combo = ttk.Combobox(row, textvariable=self.dlv_driver_var,
                                             font=F_BODY, justify="right",
                                             state="readonly", width=22)
        self.dlv_driver_combo.grid(row=1, column=2, padx=6, pady=6)
        tk.Label(row, text="السيارة / المعدة:", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).grid(row=1, column=1, padx=6, pady=6, sticky="e")
        self.dlv_vehicle_var = tk.StringVar()
        self.dlv_vehicle_combo = ttk.Combobox(row, textvariable=self.dlv_vehicle_var,
                                              font=F_BODY, justify="right",
                                              state="readonly", width=22)
        self.dlv_vehicle_combo.grid(row=2, column=2, padx=6, pady=6)
        ttk.Button(row, text="حفظ الإسناد", style="Accent.TButton",
                   command=self.save_assignment).grid(row=2, column=1, padx=6, pady=6)
        ttk.Button(row, text="وسم كسُلّمت",
                   command=self.mark_delivery_done).grid(row=2, column=0, padx=6, pady=6)

        table_card = card_frame(frame, "تسليمات اليوم (طلبات المؤسسات + المناسبات)")
        table_card.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        wrap = tk.Frame(table_card.body, bg=COLOR_CARD)
        wrap.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        self._dlv_cols = ("kind_label", "id", "customer", "details", "qty",
                          "time", "location", "driver", "vehicle", "delivered")
        heads = ("النوع", "الرقم", "العميل", "التفاصيل", "الكمية",
                 "وقت التسليم", "المكان", "السائق", "السيارة", "سُلّمت؟")
        self.dlv_tree = ttk.Treeview(wrap, columns=self._dlv_cols, show="headings",
                                     selectmode="browse")
        for k, h in zip(self._dlv_cols, heads):
            self.dlv_tree.heading(k, text=h)
            self.dlv_tree.column(k, anchor="center", width=100)
        vs = ttk.Scrollbar(wrap, orient="vertical", command=self.dlv_tree.yview)
        self.dlv_tree.configure(yscrollcommand=vs.set)
        vs.pack(side="left", fill="y")
        self.dlv_tree.pack(fill="both", expand=True)
        self.dlv_tree.bind("<<TreeviewSelect>>", self._on_delivery_select)

        self._dlv_rows = []
        self._dlv_iid_map = {}

    def refresh_deliveries(self):
        """إعادة قراءة تسليمات اليوم المحدد وتحديث قوائم السائقين والسيارات."""
        day = self.dlv_date_var.get().strip()
        if day and not rd.is_iso_date(day):
            messagebox.showwarning("تنبيه", "التاريخ يجب أن يكون بصيغة YYYY-MM-DD.")
            return
        self.dlv_driver_combo.config(values=[s["name"] for s in rd.load_staff()])
        equipment = rd.load_equipment()
        cars = [e["name"] for e in equipment if e.get("category") == "سيارة توصيل"]
        self.dlv_vehicle_combo.config(values=cars or [e["name"] for e in equipment])
        for row in self.dlv_tree.get_children():
            self.dlv_tree.delete(row)
        self._dlv_rows = rd.deliveries_for_date(day)
        self._dlv_iid_map = {}
        for idx, d in enumerate(self._dlv_rows):
            iid = "d%d" % idx
            self._dlv_iid_map[iid] = d
            self.dlv_tree.insert("", "end", iid=iid,
                                 values=tuple(safe_str(d.get(k, "")) for k in self._dlv_cols))

    def selected_delivery(self):
        sel = self.dlv_tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار تسليم من الجدول أولاً.")
            return None
        return self._dlv_iid_map.get(sel[0])

    def _on_delivery_select(self, _event=None):
        sel = self.dlv_tree.selection()
        if not sel:
            return
        d = self._dlv_iid_map.get(sel[0])
        if d:
            self.dlv_driver_var.set(safe_str(d.get("driver", "")))
            self.dlv_vehicle_var.set(safe_str(d.get("vehicle", "")))

    def save_assignment(self):
        d = self.selected_delivery()
        if not d:
            return
        try:
            rd.save_delivery_assignment(d["kind"], d["id"],
                                        driver=self.dlv_driver_var.get(),
                                        vehicle=self.dlv_vehicle_var.get())
        except ValueError as e:
            messagebox.showwarning("تنبيه", str(e))
            return
        self.refresh_deliveries()
        messagebox.showinfo("تم", "تم حفظ إسناد التسليم.")

    def mark_delivery_done(self):
        d = self.selected_delivery()
        if not d:
            return
        try:
            rd.save_delivery_assignment(d["kind"], d["id"],
                                        driver=self.dlv_driver_var.get(),
                                        vehicle=self.dlv_vehicle_var.get(),
                                        delivered=True)
        except ValueError as e:
            messagebox.showwarning("تنبيه", str(e))
            return
        self.refresh_deliveries()
        messagebox.showinfo("تم", "تم وسم التسليم بأنه سُلّم.")
