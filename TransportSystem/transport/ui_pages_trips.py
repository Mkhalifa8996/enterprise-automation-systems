# -*- coding: utf-8 -*-
"""شاشة الرحلات اليومية ونافذة الإدخال الجماعي."""

import os, shutil, webbrowser
from datetime import date
from datetime import datetime
from tkinter import filedialog
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk
import urllib.parse
from . import data as td
from .app_config import COLOR_BG, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_CARD, COLOR_DANGER, COLOR_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_TEXT, FONT_NAME, F_BODY, F_BOLD, F_H2, F_LABEL
from .ui_crud_tab import CrudTab
from .ui_dialogs import DatePicker, date_input
from .print_letterhead import NO_CUSTOMER
from .driver_links import _BATCH_HEADER_COMBO_WIDTHS
from .ui_widgets import apply_table_style, card_frame, center_dialog, make_btn, tooltip
from .print_statement import generate_and_open_summary_print
from .ui_helpers import is_international_trip_category, log_exception, safe_str
from .ui_text_edit import refresh_related_screens


class BatchTripsDialog(tk.Toplevel):
    """
    نافذة منبثقة لإدخال عدة رحلات يومية دفعة واحدة.
    الحقول المشتركة (التاريخ، نوع الشحن، الاتجاه، الدولة) في الأعلى،
    وكل رحلة على هيئة صف مستقل يحتوي على: سيارة، سائق، حاوية، مبلغ، عمولة...
    """

    EXPENSE_FIELDS = ("car_expense_type", "car_expense_amount", "driver_expense")

    # الحقول الخاصة بكل رحلة (تختلف من رحلة لأخرى)
    PER_TRIP_FIELDS = [
        ("declaration_trip_no", "كود الرحلة", "entry"),
        ("declaration_no", "رقم البيان", "entry"),
        ("container_size", "حجم الحاوية", "combo"),
        ("driver", "السائق", "combo"),
        ("car_no", "رقم السيارة *", "combo"),
        ("customer", "العميل", "combo"),
        ("company", "الشركة", "combo"),
        ("fee", "المبلغ (د.ك)", "entry"),
        ("driver_commission", "العمولة (د.ك)", "entry"),
        ("notes", "ملاحظات", "entry"),
    ]

    def __init__(self, parent, app):
        self.app = app
        self.parent_page = parent
        self.PER_TRIP_FIELDS = [
            (key, "السعر (د.ك)" if key == "fee" else label, wtype)
            for key, label, wtype in self.PER_TRIP_FIELDS
        ]
        self.PER_TRIP_FIELDS = sorted(
            self.PER_TRIP_FIELDS,
            # In the RTL trip row, the first field is placed at the right.
            # Start with driver, followed immediately by the vehicle.
            key=lambda field: {"driver": 0, "car_no": 1,
                               "declaration_trip_no": 2, "declaration_no": 3,
                               "container_size": 4, "company": 5, "customer": 6,
                               "fee": 7, "driver_commission": 8, "driver_wage": 8,
                               "notes": 9}.get(field[0], 10),
        )
        tk.Toplevel.__init__(self, parent.frame)
        self.title("إدخال دفعي — رحلات يومية متعددة")
        self.geometry("1100x720")
        self.configure(bg=COLOR_BG)
        self.minsize(900, 560)
        self.transient(parent.frame)
        self.grab_set()
        center_dialog(self, parent.frame)

        self.common_vars = {}
        self.common_combos = {}
        self.trip_rows = []       # قائمة ببيانات كل صف [{vars, combos, frame}]
        self._editing_rows = []   # قائمة بالرحلات المحمّلة للتعديل

        self._build_common_fields()
        self._build_trips_area()
        self._build_bottom_buttons()

        # تهيئة القيم الافتراضية
        self.common_vars["date"].set(date.today().isoformat())
        self.common_vars["trip_category"].set(td.TRIP_CATEGORIES[0])
        self._on_common_category_change()
        self.add_trip_row()

    def _build_common_fields(self):
        """بطاقة الحقول المشتركة لكل الرحلات."""
        card = card_frame(self, "البيانات المشتركة (تنطبق على كل الرحلات)")
        card.pack(fill="x", padx=18, pady=(18, 8))
        box = card.body
        form = tk.Frame(box, bg=COLOR_CARD)
        form.pack(fill="x", padx=18, pady=(0, 8))

        common_defs = [
            ("date", "التاريخ *", None),
            ("trip_category", "نوع الشحن *", td.TRIP_CATEGORIES),
            ("direction", "مكان التحميل *", []),
            ("country", "مكان التنزيل", []),
        ]
        for idx, (key, label, values) in enumerate(common_defs):
            c = 4 - 1 - idx  # عكس الترتيب لليمين
            cell = tk.Frame(form, bg=COLOR_CARD)
            cell.grid(row=0, column=c, padx=8, pady=7, sticky="ew")
            tk.Label(cell, text=label, font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED,
                     anchor="e", justify="right").pack(fill="x", pady=(0, 3))
            var = tk.StringVar()
            if values is not None:
                w = ttk.Combobox(cell, textvariable=var, values=values, font=F_BOLD,
                                 justify="right", state="normal")
                self.common_combos[key] = w
            elif key == "date":
                date_input(cell, var)
                self.common_vars[key] = var
                continue
            else:
                w = tk.Entry(cell, textvariable=var, font=F_BODY, justify="right",
                             relief="flat", bd=0, highlightthickness=2,
                             highlightbackground=COLOR_BORDER,
                             highlightcolor=COLOR_PRIMARY_LIGHT)
            w.pack(fill="x", ipady=4)
            self.common_vars[key] = var
        for i in range(4):
            form.grid_columnconfigure(i, weight=1)

        self.common_combos["trip_category"].bind("<<ComboboxSelected>>", self._on_common_category_change)

        # تلميح المسار
        self.batch_hint = tk.Label(box, text="", font=(FONT_NAME, 9, "italic"),
                                   bg=COLOR_CARD, fg=COLOR_PRIMARY_LIGHT, anchor="e", justify="right")
        self.batch_hint.pack(fill="x", padx=18, pady=(0, 4))

    def _build_trips_area(self):
        """منطقة قابلة للتمرير تحتوي صفوف الرحلات الفردية."""
        card = card_frame(self, "رحلات اليوم (كل صف = رحلة واحدة)")
        card.pack(fill="both", expand=True, padx=18, pady=8)
        box = card.body

        # رأس الأعمدة
        header = tk.Frame(box, bg=COLOR_CARD)
        header.pack(fill="x", padx=18, pady=(8, 4))
        n = len(self.PER_TRIP_FIELDS)
        for idx, (key, label, _) in enumerate(self.PER_TRIP_FIELDS):
            c = n - 1 - idx
            tk.Label(header, text=label, font=(FONT_NAME, 8, "bold"),
                     bg=COLOR_CARD, fg=COLOR_MUTED, anchor="center").grid(
                row=0, column=c, padx=4, sticky="ew")
        for i in range(n):
            header.grid_columnconfigure(i, weight=1)
        tk.Label(header, text="حذف", font=(FONT_NAME, 8, "bold"),
                 bg=COLOR_CARD, fg=COLOR_DANGER, width=5).grid(row=0, column=n, padx=4)

        # منطقة قابلة للتمرير
        scroll_container = tk.Frame(box, bg=COLOR_CARD)
        scroll_container.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.canvas = tk.Canvas(scroll_container, bg=COLOR_CARD, highlightthickness=0)
        vs = ttk.Scrollbar(scroll_container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=COLOR_CARD)
        self.scroll_frame.bind("<Configure>",
                               lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig("all", width=e.width))
        self.canvas.configure(yscrollcommand=vs.set)
        # الشريط العمودي على اليمين كما في الواجهات العربية.
        vs.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # زر إضافة صف
        add_row_btn = tk.Frame(box, bg=COLOR_CARD)
        add_row_btn.pack(fill="x", padx=18, pady=(0, 10), anchor="e")
        make_btn(add_row_btn, "إضافة رحلة أخرى", self.add_trip_row, variant="accent").pack(side="right", padx=4)

    def _build_bottom_buttons(self):
        """أزرار الحفظ والإلغاء في الأسفل."""
        btns = tk.Frame(self, bg=COLOR_BG)
        btns.pack(fill="x", padx=18, pady=(0, 18), anchor="e")
        make_btn(btns, "حفظ الكل", self.save_all, variant="accent").pack(side="right", padx=4)
        make_btn(btns, "إلغاء", self.destroy, variant="secondary").pack(side="right", padx=4)

    # ---------------- منطق الصفوف ----------------
    def add_trip_row(self, data=None, trip_id=None):
        """إضافة صف رحلة جديد. إذا مرّرنا data تُعبأ الحقول منه. trip_id للتعديل."""
        row_idx = len(self.trip_rows)
        row_frame = tk.Frame(self.scroll_frame, bg=COLOR_CARD)
        row_frame.pack(fill="x", padx=4, pady=3)
        row_vars = {}
        row_combos = {}

        n = len(self.PER_TRIP_FIELDS)
        for idx, (key, label, wtype) in enumerate(self.PER_TRIP_FIELDS):
            c = n - 1 - idx
            cell = tk.Frame(row_frame, bg=COLOR_CARD)
            cell.grid(row=0, column=c, padx=4, sticky="ew")
            var = tk.StringVar()
            if wtype == "combo":
                if key == "car_no":
                    values = self._get_available_cars()
                elif key == "driver":
                    values = [d["name"] for d in td.load_drivers()]
                elif key == "customer":
                    values = [NO_CUSTOMER] + [c["name"] for c in td.load_customers()]
                elif key == "company":
                    values = [c["name"] for c in td.load_companies()]
                elif key == "container_size":
                    values = ["1× 20' DC", "2× 20' DC", "1× 40' HC", "1× 20' FR", "1× 40' FR"]
                elif key == "car_expense_type":
                    values = td.MAINTENANCE_TYPES
                else:
                    values = []
                w = ttk.Combobox(cell, textvariable=var, values=values, font=F_BODY,
                                 justify="right", width=12)
                row_combos[key] = w
            else:
                w = tk.Entry(cell, textvariable=var, font=F_BODY, justify="right",
                             relief="flat", bd=0, highlightthickness=2,
                             highlightbackground=COLOR_BORDER,
                             highlightcolor=COLOR_PRIMARY_LIGHT, width=12)
            w.pack(fill="x", ipady=3)
            row_vars[key] = var
        for i in range(n):
            row_frame.grid_columnconfigure(i, weight=1)

        # زر حذف الصف
        def remove_this():
            self._remove_row(row_idx)
        make_btn(row_frame, "حذف", remove_this, variant="danger", width=6).grid(row=0, column=n, padx=4)

        # تعبئة البيانات إن وُجدت
        if data:
            for k, v in data.items():
                if k in row_vars:
                    row_vars[k].set(safe_str(v))
        row_data = {"frame": row_frame, "vars": row_vars, "combos": row_combos,
                    "trip_id": trip_id}
        if "company" in row_combos:
            row_combos["company"].bind(
                "<<ComboboxSelected>>",
                lambda _event, r=row_data: self._on_batch_company_selected(r),
            )
        if "driver" in row_combos:
            row_combos["driver"].bind(
                "<<ComboboxSelected>>",
                lambda _event, r=row_data: self._on_batch_driver_selected(r),
            )
            # نتابع المتغير لا الفأرة فقط كي يعمل الحقل عند التحميل والكتابة.
            row_vars["driver"].trace_add(
                "write", lambda *_a, r=row_data: self._on_batch_driver_selected(r))
        self.trip_rows.append(row_data)

    def _on_batch_company_selected(self, row):
        company_name = row["vars"]["company"].get().strip()
        company = next((item for item in td.load_companies()
                        if str(item.get("name", "")).strip() == company_name), None)
        customer = safe_str(company.get("customs_broker")) if company else ""
        row["vars"]["customer"].set(customer or NO_CUSTOMER)

    def _on_batch_driver_selected(self, row):
        """تحديد السيارة المكلَّفة للسائق من جدول التكليفات أو سجل السيارات."""
        driver_name = row["vars"]["driver"].get().strip()
        car_no = td.car_for_driver(driver_name)
        if "car_no" not in row["combos"]:
            return
        if car_no:
            values = list(row["combos"]["car_no"].cget("values"))
            if car_no not in values:
                values.append(car_no)
                row["combos"]["car_no"].config(values=values)
        row["vars"]["car_no"].set(car_no)

    def _remove_row(self, idx):
        """حذف صف من القائمة."""
        if len(self.trip_rows) <= 1:
            messagebox.showinfo("تنبيه", "لا يمكن حذف كل الصفوف — يجب أن تبقى رحلة واحدة على الأقل.")
            return
        if idx < len(self.trip_rows):
            row = self.trip_rows.pop(idx)
            row["frame"].destroy()
            self._reindex_rows()

    def _reindex_rows(self):
        """إعادة ربط أزرار الحذف بعد حذف صف."""
        for i, row in enumerate(self.trip_rows):
            # إعادة ربط زر الحذف بالفهرس الجديد
            for child in row["frame"].winfo_children():
                if isinstance(child, tk.Button):
                    child.config(command=lambda i=i: self._remove_row(i))

    def _get_available_cars(self):
        """قائمة السيارات المتاحة حسب نوع الشحن المختار."""
        cat = self.common_vars["trip_category"].get() or td.TRIP_CATEGORIES[0]
        vehicles = td.load_vehicles()
        if is_international_trip_category(cat):
            allowed = {td.VEHICLE_WORK_TYPES[1], td.VEHICLE_WORK_TYPES[2]}
        else:
            allowed = {td.VEHICLE_WORK_TYPES[0], td.VEHICLE_WORK_TYPES[2]}
        cars = [v["car_no"] for v in vehicles if (not v.get("work_type")) or v.get("work_type") in allowed]
        if not cars:
            cars = [v["car_no"] for v in vehicles]
        return cars

    def _on_common_category_change(self, event=None):
        """تحديث خيارات مكان التحميل/التنزيل والسيارات عند تغيير نوع الشحن."""
        cat = self.common_vars["trip_category"].get() or td.TRIP_CATEGORIES[0]
        load_places = td.get_places_for_trip_category_and_usage(cat, "تحميل")
        unload_places = td.get_places_for_trip_category_and_usage(cat, "تفريغ")
        self.common_combos["direction"].config(values=load_places, state="normal")
        self.common_combos["country"].config(values=unload_places, state="normal")
        if not load_places:
            self.common_vars["direction"].set("")
        elif self.common_vars["direction"].get() not in load_places:
            self.common_vars["direction"].set(load_places[0])
        if not unload_places:
            self.common_vars["country"].set("")
        elif self.common_vars["country"].get() not in unload_places:
            self.common_vars["country"].set(unload_places[0])
        # تحديث قوائم السيارات في كل الصفوف
        cars = self._get_available_cars()
        for row in self.trip_rows:
            if "car_no" in row["combos"]:
                row["combos"]["car_no"].config(values=cars)
        is_intl = is_international_trip_category(cat)
        # تلميح
        if is_intl:
            hint = "شحن دولي بري — تأكد من تعبئة مكان التنزيل." 
        else:
            hint = "شحن داخلي/ضرب فله — اختر مكان التحميل والتنزيل من الأماكن المخزنة." 
        self.batch_hint.config(text=hint)

    # ---------------- الحفظ ----------------
    def save_all(self):
        """حفظ كل الرحلات دفعة واحدة."""
        # التحقق من الحقول المشتركة
        d_date = self.common_vars["date"].get().strip()
        d_cat = self.common_vars["trip_category"].get().strip()
        d_dir = self.common_vars["direction"].get().strip()
        if not d_date:
            messagebox.showwarning("تنبيه", "الرجاء إدخال التاريخ.", parent=self)
            return
        if not d_cat:
            messagebox.showwarning("تنبيه", "الرجاء اختيار نوع الشحن.", parent=self)
            return

        saved = 0
        errors = []
        for i, row in enumerate(self.trip_rows):
            car = row["vars"]["car_no"].get().strip()
            if not car:
                errors.append(f"صف {i+1}: رقم السيارة مطلوب.")
                continue
            data = {
                "date": d_date,
                "trip_category": d_cat,
                "direction": d_dir,
                "country": self.common_vars["country"].get().strip(),
                "driver": row["vars"]["driver"].get().strip(),
                "car_no": car,
                "customer": row["vars"]["customer"].get().strip(),
                "company": row["vars"].get("company", tk.StringVar()).get().strip() if row["vars"].get("company") is not None else "",
                "declaration_no": row["vars"].get("declaration_no", tk.StringVar()).get().strip() if row["vars"].get("declaration_no") is not None else "",
                "declaration_trip_no": row["vars"].get("declaration_trip_no", tk.StringVar()).get().strip() if row["vars"].get("declaration_trip_no") is not None else "",
                "container_size": row["vars"]["container_size"].get().strip(),
                "fee": row["vars"]["fee"].get().strip(),
                "driver_commission": row["vars"]["driver_commission"].get().strip(),
                "notes": row["vars"]["notes"].get().strip(),
            }
            try:
                td.save_trip(data, row.get("trip_id"))
                saved += 1
            except Exception as e:
                errors.append(f"صف {i+1}: {e}")

        if errors:
            messagebox.showwarning("تنبيه", f"تم حفظ {saved} رحلة.\nأخطاء:\n" + "\n".join(errors), parent=self)
        else:
            messagebox.showinfo("تم", f"تم حفظ {saved} رحلة بنجاح.", parent=self)

        if saved > 0:
            self.parent_page.refresh()
            refresh_related_screens(self.parent_page.frame)
            self.destroy()

    # ==================================================================
    # شاشة الرحلات اليومية - شحن داخلي (ميناء) وشحن دولي بري
    # ==================================================================
class TripsPage(CrudTab):
    """
    شاشة مخصّصة للرحلات اليومية تفرّق بين:
      - شحن داخلي: بين الميناء ومكان العميل (تحميل من الميناء أو تسليم إليه) في الكويت.
      - شحن دولي بري: بين مكان العميل في الكويت ودولة أخرى (كالسعودية) والعكس.
    عند اختيار نوع الشحن تتحدث خيارات «الاتجاه» و«الدولة» وقائمة السيارات
    المتاحة تلقائياً بحسب نوع عمل كل سيارة.
    """

    EXPENSE_FIELDS = ("car_expense_type", "car_expense_amount", "driver_expense")

    def __init__(self, parent, on_add_service_invoice=None):
        self.today_var = tk.BooleanVar(value=False)
        self.on_add_service_invoice = on_add_service_invoice
        # Filters for the daily-trip register.
        self.trip_filter_field_var = tk.StringVar(value="الكل")
        self.trip_filter_value_var = tk.StringVar()
        self.batch_rows = []
        self.batch_groups = []
        self.active_batch_group = None
        self.services_tab = None

        outer = tk.Frame(parent, bg=COLOR_BG)
        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True)

        self._trips_frame = tk.Frame(notebook, bg=COLOR_BG)
        self._services_frame = tk.Frame(notebook, bg=COLOR_BG)
        notebook.add(self._trips_frame, text="الرحلات اليومية")
        notebook.add(self._services_frame, text="الخدمات الإضافية")

        services_container = tk.Frame(self._services_frame, bg=COLOR_BG)
        services_container.pack(fill="both", expand=True)

        trips_inner = tk.Frame(self._trips_frame, bg=COLOR_BG)
        trips_inner.pack(fill="both", expand=True)

        trip_fields = [f for f in td.TRIP_FIELDS if f[0] not in self.EXPENSE_FIELDS]
        super().__init__(
            trips_inner, trip_fields, td.load_trips, td.save_trip, td.delete_trip,
            "id", "الرحلات اليومية",
            select_fields={
                "trip_category": td.TRIP_CATEGORIES,
                "direction": td.INTERNAL_DIRECTIONS,
                # «مكان التنزيل» حقل حر بلا قائمة مقترحة: كانت الدول
                # مقترحة في الشيفرة فتظهر للمستخدم وكأنها بياناته.
                "country": [],
                "transaction_type": td.TRANSACTION_TYPES,
                "container_size": ["1× 20' DC", "2× 20' DC", "1× 40' HC", "1× 20' FR", "1× 40' FR"],
                "company": [],
                "driver": [], "car_no": [], "customer": [],
            },
            readonly_fields=["id", "invoiced", "invoice_no"],
            frame=trips_inner,
        )
        self.frame = outer
        self.vars["date"].set(date.today().isoformat())

        service_fields = [
            ("date", "التاريخ"),
            ("company", "الشركة"),
            ("customer", "العميل"),
            ("declaration_no", "رقم البيان"),
            ("declaration_trip_no", "أكواد الرحلات"),
            ("service_type", "نوع الخدمة"),
            ("unit", "الوحدة"),
            ("quantity", "الكمية"),
            ("unit_price", "سعر الوحدة (د.ك)"),
            ("total", "الإجمالي (د.ك)"),
            ("notes", "ملاحظات"),
        ]
        self.services_tab = CrudTab(
            services_container, service_fields, td.load_services, td.save_service,
            td.delete_service, "id", "الخدمات الإضافية",
            select_fields={
                "service_type": td.SERVICE_TYPES,
                "company": [c.get("name", "") for c in td.load_companies()],
                "customer": [NO_CUSTOMER] + [c.get("name", "") for c in td.load_customers()],
                "unit": ["ساعة", "يوم", "نقلة", "حاوية"],
            },
            readonly_fields=["id", "total"],
            cols_per_row=11,
            frame=services_container,
            show_edit_button=False,
            compact_filters=True,
            print_mode="dialog",
            single_row=True,
            show_upload_button=False,
            attachment_fields=[("files", "ملفات")],
            attachment_entity_type="services",
            narrow_fields=("date", "unit", "quantity", "unit_price", "declaration_no", "notes",
                           "company", "customer", "service_type", "total"),
            narrow_widths={"date": 8, "unit": 6, "quantity": 10, "unit_price": 12,
                           "declaration_no": 10, "notes": 12,
                           "company": 12, "customer": 12, "service_type": 12, "total": 10},
            default_values={"quantity": "1"},
            attachment_inline=True,
            attachment_inline_after="total",
        )
        self.services_tab.filter_rows = self._filter_services_rows
        if "service_type" in self.services_tab.vars:
            self.services_tab.vars["service_type"].set(td.SERVICE_TYPES[0])
        self.services_tab.tree.configure(selectmode="extended")
        self.services_tab.refresh()
        self._setup_service_total_autocalc()

        if hasattr(self.services_tab, "actions_frame") and self.on_add_service_invoice:
            make_btn(self.services_tab.actions_frame, "إضافة فاتورة", self.on_add_service_invoice, variant="accent", padx=7, pady=3).pack(side="right", padx=3)

        def add_new_service():
            self.services_tab.clear_form()
            if "date" in self.services_tab.vars:
                self.services_tab.vars["date"].set(date.today().isoformat())
            if "service_type" in self.services_tab.vars:
                self.services_tab.vars["service_type"].set(td.SERVICE_TYPES[0])
            if "unit" in self.services_tab.vars:
                self.services_tab.vars["unit"].set("ساعة")
            if "quantity" in self.services_tab.vars:
                self.services_tab.vars["quantity"].set("1")
            if "unit_price" in self.services_tab.vars:
                self.services_tab.vars["unit_price"].set("")
            if "total" in self.services_tab.vars:
                self.services_tab.vars["total"].set("0.000")
            self.services_tab.editing_key = None
            self.services_tab.save_btn.config(text="حفظ")
            try:
                first_entry = None
                for child in self.services_tab.frame.winfo_children():
                    card = child.winfo_children()[0] if child.winfo_children() else None
                    if card and hasattr(card, 'body'):
                        for widget in card.body.winfo_children():
                            if isinstance(widget, tk.Frame):
                                for sub in widget.winfo_children():
                                    if isinstance(sub, tk.Entry):
                                        first_entry = sub
                                        break
                            if first_entry:
                                break
                    if first_entry:
                        break
                if first_entry:
                    first_entry.focus_set()
            except Exception as _log_exc: log_exception("add_new_service", _log_exc)

        # زر الإضافة داخل نفس صف البحث/الفلاتر/الأزرار (على الشمال مع باقي الأزرار)
        if hasattr(self.services_tab, "actions_frame"):
            make_btn(self.services_tab.actions_frame, "خدمة جديدة", add_new_service,
                     variant="accent", padx=5, pady=3).pack(side="right", padx=3)

        if "company" in self.services_tab.combos:
            def _on_company_change(*_args):
                company_name = self.services_tab.vars["company"].get().strip()
                if not company_name:
                    return
                companies = td.load_companies()
                company = next((c for c in companies if c.get("name", "").strip() == company_name), None)
                if company:
                    customer = company.get("customs_broker", "").strip()
                    if customer and "customer" in self.services_tab.vars:
                        self.services_tab.vars["customer"].set(customer)
            self.services_tab.combos["company"].bind("<<ComboboxSelected>>", _on_company_change)

    def _current_services_context(self):
        date_value = ""
        declaration_value = ""
        trip_ids = []
        try:
            if self.active_batch_group:
                date_value = self.active_batch_group["date"].get().strip()
                declaration_value = self.active_batch_group["declaration_no"].get().strip()
            for row in getattr(self, "batch_rows", []):
                tid = row.get("trip_id")
                if tid:
                    trip_ids.append(str(tid))
        except Exception as _log_exc: log_exception("_current_services_context", _log_exc)
        return date_value, declaration_value, trip_ids

    def _filter_services_rows(self, rows):
        return rows

    def _setup_service_total_autocalc(self):
        tab = self.services_tab
        if not tab or not hasattr(tab, "vars"):
            return

        def _recalc(_event=None):
            qty = td.safe_float(tab.vars.get("quantity", tk.StringVar()).get())
            price = td.safe_float(tab.vars.get("unit_price", tk.StringVar()).get())
            total = round(qty * price, 3)
            if "total" in tab.vars:
                tab.vars["total"].set(f"{total:.3f}")

        qty_var = tab.vars.get("quantity")
        price_var = tab.vars.get("unit_price")
        if qty_var:
            qty_var.trace_add("write", _recalc)
        if price_var:
            price_var.trace_add("write", _recalc)
        _recalc()

    def _sync_services_tab(self, *_args):
        if hasattr(self, "services_tab") and self.services_tab:
            self.services_tab.refresh()

    def _build_form(self):
        # --- صف التاريخ (مختصر في صف واحد) ---
        date_row = tk.Frame(self.frame, bg=COLOR_BG)
        date_row.pack(fill="x", padx=18, pady=(10, 4))

        tk.Label(date_row, text="التاريخ *", font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED,
                 anchor="e", justify="right").pack(side="right", padx=(4, 8))
        date_var = tk.StringVar()
        self.vars["date"] = date_var
        date_control = tk.Frame(date_row, bg=COLOR_BG)
        date_control.pack(side="right", padx=(0, 4))
        tk.Entry(date_control, textvariable=date_var, font=F_BODY, justify="right",
                 relief="flat", bd=0, highlightthickness=2,
                 highlightbackground=COLOR_BORDER,
                 highlightcolor=COLOR_PRIMARY_LIGHT, width=18).pack(side="right", ipady=3)
        make_btn(date_control, "📅", lambda: DatePicker(date_control, date_var),
                 variant="secondary", width=2).pack(side="left", padx=(4, 0))
        make_btn(date_row, "تاريخ اليوم", self.set_today, variant="secondary").pack(side="right", padx=4)

        # --- بطاقة اليومية (إدخال دفعي للرحلات) ---
        batch_card = card_frame(self.frame, "اليومية")
        batch_card.pack(fill="both", expand=True, padx=18, pady=8)
        batch_box = batch_card.body
        date_row.pack_forget()

        # رقم البيان هو مفتاح تجميع الرحلات مع التاريخ. تبقى قيمة الرقم
        # محفوظة في كل رحلة حتى يمكن تعديل الرحلة منفردة دون تغيير بنية
        # البيانات القديمة.
        declaration_bar = tk.Frame(batch_box, bg=COLOR_CARD)
        declaration_bar.pack(fill="x", padx=18, pady=(8, 4))
        tk.Label(declaration_bar, text="بيان الرحلات الحالي", font=F_LABEL,
                 bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(0, 8))
        self.batch_declaration_var = tk.StringVar()
        tk.Entry(declaration_bar, textvariable=self.batch_declaration_var,
                 font=F_BODY, justify="right", relief="flat", bd=0,
                 highlightthickness=2, highlightbackground=COLOR_BORDER,
                 highlightcolor=COLOR_PRIMARY_LIGHT, width=10).pack(side="right", ipady=3)
        tk.Label(declaration_bar,
                 text="التاريخ + رقم البيان = مجموعة رحلات واحدة",
                 font=(FONT_NAME, 9), bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=12)
        make_btn(declaration_bar, "تطبيق الرقم على الصفوف", self._apply_batch_declaration,
                 variant="secondary").pack(side="left", padx=4)
        declaration_bar.pack_forget()

        # رأس الأعمدة
        batch_header = tk.Frame(batch_box, bg=COLOR_CARD)
        batch_header.pack(fill="x", padx=18, pady=(8, 4))
        # سيتم عرض عناوين الحقول داخل كل مجموعة بعد رأس البيان.
        batch_header.pack_forget()
        self._batch_fields = [
            ("declaration_trip_no", "كود الرحلة"),
            ("date", "التاريخ *"),
            ("declaration_no", "رقم البيان"),
            ("container_size", "حجم الحاوية"),
            ("trip_category", "نوع الشحن *"),
            ("direction", "مكان التحميل *"),
            ("country", "مكان التنزيل"),
            ("driver_type", "نوع السائق"),
            ("driver", "السائق"),
            ("car_no", "رقم السيارة *"),
            ("customer", "العميل"),
            ("company", "الشركة"),
            ("fee", "المبلغ (د.ك)"),
            ("holiday_price", "سعر العطلة (د.ك)"),
            ("driver_wage", "أجرة السائق (د.ك)"),
            ("notes", "ملاحظات"),
        ]
        # التاريخ ورقم البيان يظهران مرة واحدة في رأس كل مجموعة بيان.
        self._batch_fields = [f for f in self._batch_fields
                              if f[0] not in ("date", "declaration_no", "trip_category")]
        self._batch_fields.sort(
            # The rightmost fields in this RTL row are driver then vehicle.
            key=lambda field: {"driver_type": 0, "driver": 1, "car_no": 2,
                               "declaration_trip_no": 3, "container_size": 4,
                               "direction": 5, "country": 6, "company": 7,
                               "customer": 8, "fee": 9, "driver_wage": 10,
                               "holiday_price": 11, "notes": 12}.get(field[0], 13)
        )
        self._batch_fields = [
            (key, "السعر (د.ك)" if key == "fee" else ("عطلة" if key == "holiday_price" else label))
            for key, label in self._batch_fields
        ]
        n = len(self._batch_fields)
        header_width = max(10, max(len(label) for _key, label in self._batch_fields))
        for idx, (key, label) in enumerate(self._batch_fields):
            c = n - 1 - idx
            tk.Label(batch_header, text=label, font=(FONT_NAME, 8, "bold"),
                     bg=COLOR_CARD, fg=COLOR_MUTED, anchor="center",
                     width=header_width).grid(
                row=0, column=c, padx=4, sticky="ew")
        for i in range(n):
            # Keep every header column the same width as its input column.
            # Long Arabic headers otherwise widen only their own column.
            batch_header.grid_columnconfigure(i, weight=1, uniform="trip_batch")
        tk.Label(batch_header, text="حذف", font=(FONT_NAME, 8, "bold"),
                 bg=COLOR_CARD, fg=COLOR_DANGER, width=5).grid(row=0, column=n, padx=4)

        # منطقة قابلة للتمرير
        scroll_container = tk.Frame(batch_box, bg=COLOR_CARD)
        scroll_container.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.batch_canvas = tk.Canvas(scroll_container, bg=COLOR_CARD, highlightthickness=0)
        batch_vs = ttk.Scrollbar(scroll_container, orient="vertical", command=self.batch_canvas.yview)
        self.batch_scroll_frame = tk.Frame(self.batch_canvas, bg=COLOR_CARD)
        self.batch_scroll_frame.bind("<Configure>",
                               lambda e: self.batch_canvas.configure(scrollregion=self.batch_canvas.bbox("all")))
        self.batch_canvas.create_window((0, 0), window=self.batch_scroll_frame, anchor="nw")
        self.batch_canvas.bind("<Configure>",
                         lambda e: self.batch_canvas.itemconfig("all", width=e.width))
        self.batch_canvas.configure(yscrollcommand=batch_vs.set)
        # الشريط العمودي على اليمين كما في الواجهات العربية.
        batch_vs.pack(side="right", fill="y")
        self.batch_canvas.pack(side="left", fill="both", expand=True)

        # أزرار
        batch_btns = tk.Frame(batch_box, bg=COLOR_CARD)
        batch_btns.pack(fill="x", padx=18, pady=(0, 14), anchor="e")
        self.batch_btns = batch_btns
        make_btn(batch_btns, "رحلة لنفس البيان", self._add_same_declaration_row, variant="accent").pack(side="right", padx=4)
        make_btn(batch_btns, "رحلة لبيان آخر", self._add_new_declaration_row, variant="secondary").pack(side="right", padx=4)
        make_btn(batch_btns, "إضافة رحلة", self._add_batch_row, variant="accent").pack(side="right", padx=4)
        make_btn(batch_btns, "حفظ الكل", self._save_all_batch, variant="accent").pack(side="right", padx=4)
        make_btn(batch_btns, "تحميل رحلات اليوم", self._load_today_batch, variant="secondary").pack(side="right", padx=4)

        # إضافة صف فارغ افتراضي
        self._add_batch_row()

    # ---------------- منطق الإدخال الدفعي ----------------
    def _create_batch_group(self, data=None):
        """إنشاء رأس بيان مستقل يحتوي تاريخاً ورقم بيان ورحلاته."""
        data = data or {}
        frame = tk.Frame(self.batch_scroll_frame, bg=COLOR_BG, highlightthickness=1,
                         highlightbackground=COLOR_BORDER)
        frame.pack(fill="x", padx=4, pady=(8, 2))
        header = tk.Frame(frame, bg=COLOR_BG)
        header.pack(fill="x", padx=8, pady=6)
        tk.Label(header, text="بيان", font=F_LABEL, bg=COLOR_BG, fg=COLOR_PRIMARY,
                 anchor="e").pack(side="right", padx=6)

        # كل حقل يظهر اسمه فوق عنصر الإدخال وليس بجواره.
        def _batch_field_block(label_text):
            block = tk.Frame(header, bg=COLOR_BG)
            tk.Label(block, text=label_text, font=(FONT_NAME, 9), bg=COLOR_BG,
                     fg=COLOR_MUTED, anchor="e", justify="right").pack(fill="x", anchor="e")
            block.pack(side="right", padx=4)
            return block

        declaration_var = tk.StringVar(value=safe_str(data.get("declaration_no", "")))
        decl_block = _batch_field_block("رقم البيان")
        # عرض مضغوط لرقم البيان: الحقول لابد أن تتسع ليظهر زر «مسح الحقول»
        # في سطر واحد مع «الشركة» و«العميل» و«حذف البيان».
        tk.Entry(decl_block, textvariable=declaration_var, font=F_BODY, justify="right",
                 relief="flat", bd=0, highlightthickness=2,
                 highlightbackground=COLOR_BORDER, highlightcolor=COLOR_PRIMARY_LIGHT,
                 width=9).pack(fill="x", ipady=3)

        date_var = tk.StringVar(value=safe_str(data.get("date", "")))
        date_block = _batch_field_block("التاريخ")
        date_input(date_block, date_var, shrink=True, width=8)

        shared_vars = {
            "trip_category": tk.StringVar(value=safe_str(data.get("trip_category", td.TRIP_CATEGORIES[0]))),
            "company": tk.StringVar(value=safe_str(data.get("company", ""))),
            "customer": tk.StringVar(value=safe_str(data.get("customer", ""))),
        }
        # مفتاح ثابت للبيان (تاريخ + رقم) حتى تبقى الملفات والمواقع مرتبطة به
        # بعد الحفظ وإعادة الفتح. مؤقت فقط عند غياب التاريخ ورقم البيان معاً.
        group = {"frame": frame, "date": date_var, "declaration_no": declaration_var,
                 "rows": [], "shared": shared_vars, "combos": {},
                 "attachment_key": td.declaration_key(date_var.get(), declaration_var.get())
                 or f"temp_batch_{int(datetime.now().timestamp() * 1000)}"}
        for key, label, values in (
            ("trip_category", "نوع الشحن", td.TRIP_CATEGORIES),
            ("company", "الشركة", [c.get("name", "") for c in td.load_companies()]),
            ("customer", "العميل", [NO_CUSTOMER] + [c.get("name", "") for c in td.load_customers()]),
        ):
            combo_block = _batch_field_block(label)
            # حقول البيان الضيقة تُعرض بعرض أصغر ليبقى صف الرأس متساوياً.
            combo = ttk.Combobox(combo_block, textvariable=shared_vars[key], values=values,
                                 font=F_BODY, justify="right",
                                 width=_BATCH_HEADER_COMBO_WIDTHS.get(key, 14))
            combo.pack(fill="x", ipady=1)
            group["combos"][key] = combo
            if key == "trip_category":
                combo.bind("<<ComboboxSelected>>", lambda _e: self._on_group_category_change(group))
            elif key == "company":
                combo.bind("<<ComboboxSelected>>", lambda _e: self._on_group_company_change(group))
        columns = tk.Frame(frame, bg=COLOR_CARD)
        columns.pack(fill="x", padx=8, pady=(0, 2))
        n = len(self._batch_fields)
        header_width = max(10, max(len(label) for _key, label in self._batch_fields))
        for idx, (key, label) in enumerate(self._batch_fields):
            c = n - 1 - idx
            tk.Label(columns, text=label, font=(FONT_NAME, 8, "bold"),
                     bg=COLOR_CARD, fg=COLOR_MUTED, anchor="center",
                     width=header_width).grid(row=0, column=c, padx=4, sticky="ew")
        for i in range(n):
            columns.grid_columnconfigure(i, weight=1, uniform="trip_batch")
        tk.Label(columns, text="حذف", font=(FONT_NAME, 8, "bold"),
                 bg=COLOR_CARD, fg=COLOR_DANGER, width=6,
                 anchor="center", justify="center").grid(row=0, column=n, padx=4)
        # «مسح الحقول» يُحزَم أولاً على اليسار فيثبت إلى الحافة اليسرى فلا
        # يختفي عند ضيق الشاشة، ويليه «حذف البيان» ثم المواقع والملفات.
        make_btn(header, "مسح الحقول", lambda g=group: self._clear_batch_group(g),
                 variant="secondary", width=10).pack(side="left", padx=(2, 4))
        make_btn(header, "حذف البيان", lambda g=group: self._remove_batch_group(g),
                 variant="danger", width=8).pack(side="left", padx=4)
        loc_block = tk.Frame(header, bg=COLOR_BG)
        loc_block.pack(side="left", padx=5, pady=2)
        tk.Label(loc_block, text="موقع التنزيل", font=(FONT_NAME, 8, "bold"),
                 bg=COLOR_BG, fg=COLOR_PRIMARY, anchor="e").pack(anchor="e")
        loc_controls = tk.Frame(loc_block, bg=COLOR_BG)
        loc_controls.pack(fill="x", anchor="e")
        make_btn(loc_controls, "إضافة موقع", lambda g=group: self._quick_add_batch_location(g),
                 variant="secondary", padx=5, pady=1).pack(side="right", padx=(0, 3))
        make_btn(loc_controls, "عرض المواقع", lambda g=group: self._open_batch_locations(g),
                 variant="secondary", padx=5, pady=1).pack(side="right", padx=(3, 0))
        loc_lbl = tk.Label(loc_block, text="لا توجد مواقع", font=(FONT_NAME, 7),
                           bg=COLOR_BG, fg=COLOR_MUTED, anchor="e")
        loc_lbl.pack(anchor="e")
        attach_block = tk.Frame(header, bg=COLOR_BG)
        attach_block.pack(side="left", padx=5, pady=2)
        tk.Label(attach_block, text="ملفات البيان", font=(FONT_NAME, 8, "bold"),
                 bg=COLOR_BG, fg=COLOR_PRIMARY, anchor="e").pack(anchor="e")
        attach_controls = tk.Frame(attach_block, bg=COLOR_BG)
        attach_controls.pack(fill="x", anchor="e")
        make_btn(attach_controls, "إضافة ملفات", lambda g=group: self._add_batch_files(g),
                 variant="secondary", padx=5, pady=1).pack(side="right", padx=(0, 3))
        make_btn(attach_controls, "عرض الملفات", lambda g=group: self._open_batch_files(g),
                 variant="secondary", padx=5, pady=1).pack(side="right", padx=(3, 0))
        files_lbl = tk.Label(attach_block, text="لا توجد ملفات", font=(FONT_NAME, 7),
                             bg=COLOR_BG, fg=COLOR_MUTED, anchor="e")
        files_lbl.pack(anchor="e")
        group["files_label"] = files_lbl
        group["locations_label"] = loc_lbl
        self._refresh_batch_files_label(group)
        self._refresh_batch_locations_label(group)
        self.batch_groups.append(group)
        self.active_batch_group = group
        date_var.trace_add("write", lambda *_args: (self._refresh_group_selector(), self._sync_services_tab()))
        declaration_var.trace_add("write", lambda *_args: (self._refresh_group_selector(), self._sync_services_tab()))
        declaration_var.trace_add("write", lambda *_args, g=group: (self._refresh_group_trip_codes(g), self._sync_services_tab()))
        if not hasattr(self, "batch_group_selector"):
            old_buttons = self.batch_btns.winfo_children()
            for old_button in old_buttons[:2]:
                old_button.pack_forget()
            if len(old_buttons) > 2:
                old_buttons[2].configure(text="إضافة رحلة للبيان المحدد",
                                          command=self._add_selected_group_row, width=18)
            make_btn(self.batch_btns, "بيان جديد", self._start_new_group,
                     variant="secondary", width=12).pack(side="right", padx=4)
            make_btn(self.batch_btns, "مسح الحقول", self._clear_active_batch_group,
                     variant="secondary", width=12).pack(side="right", padx=4)
            tk.Label(self.batch_btns, text="اختيار البيان", font=F_LABEL,
                     bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=4)
            self.batch_group_selector_var = tk.StringVar()
            self.batch_group_selector = ttk.Combobox(
                self.batch_btns, textvariable=self.batch_group_selector_var,
                state="readonly", width=28, justify="right")
            self.batch_group_selector.pack(side="right", padx=4)
            self.batch_group_selector.bind("<<ComboboxSelected>>", self._select_batch_group)
        self._bind_group_clicks(frame, group)
        self._activate_batch_group(group)
        self._refresh_group_selector()
        return group

    def _bind_group_clicks(self, widget, group):
        widget.bind("<Button-1>", lambda _event, g=group: self._activate_batch_group(g), add="+")
        for child in widget.winfo_children():
            self._bind_group_clicks(child, group)

    def _activate_batch_group(self, group):
        if group not in self.batch_groups:
            return
        self.active_batch_group = group
        for item in self.batch_groups:
            item["frame"].configure(highlightbackground=COLOR_PRIMARY if item is group else COLOR_BORDER)
        self._refresh_group_selector()
        self._sync_services_tab()

    def _refresh_group_selector(self):
        if not hasattr(self, "batch_group_selector"):
            return
        values = []
        selected_index = 0
        for index, group in enumerate(self.batch_groups):
            label = f"بيان {index + 1} | {group['date'].get().strip()} | {group['declaration_no'].get().strip()}"
            values.append(label)
            if group is self.active_batch_group:
                selected_index = index
        self.batch_group_selector.configure(values=values)
        if values:
            self.batch_group_selector.current(selected_index)

    def _select_batch_group(self, _event=None):
        index = self.batch_group_selector.current()
        if 0 <= index < len(self.batch_groups):
            self._activate_batch_group(self.batch_groups[index])

    def _add_selected_group_row(self):
        if self.active_batch_group is None:
            self._start_new_group()
        else:
            self._add_batch_row(group=self.active_batch_group)

    def _start_new_group(self):
        group = self._create_batch_group({"date": "", "declaration_no": ""})
        self._add_batch_row(group=group)

    def _clear_active_batch_group(self):
        """مسح حقول البيان النشط لإعادة شاشة اليومية كما كانت (فارغة)."""
        group = getattr(self, "active_batch_group", None)
        if group is None:
            messagebox.showinfo("مسح الحقول", "لا يوجد بيان نشط لمسح حقوله.",
                                parent=self.frame)
            return
        self._clear_batch_group(group)

    # ---------- مرفقات البيان + مسح حقول البيان ----------
    def _batch_record_key(self, group):
        """مفتاح ثابت لربط ملفات ومواقع البيان: مشتق من التاريخ + رقم البيان.

        إن غيّر المستخدم التاريخ أو رقم البيان قبل الحفظ، تُرحَّل الملفات
        والمواقع المحفوظة سابقاً تلقائياً إلى المفتاح الجديد.
        """
        new_key = td.declaration_key(group["date"].get(), group["declaration_no"].get())
        old_key = safe_str(group.get("attachment_key", "")).strip()
        if not new_key:
            if old_key:
                return old_key
            new_key = f"temp_batch_{int(datetime.now().timestamp() * 1000)}"
            group["attachment_key"] = new_key
            return new_key
        if old_key and old_key != new_key:
            try:
                td.move_attachments("trips", old_key, new_key)
                td.move_locations(old_key, new_key)
            except Exception as _log_exc: log_exception("_batch_record_key", _log_exc)
        group["attachment_key"] = new_key
        return new_key

    def _refresh_batch_files_label(self, group):
        label = group.get("files_label")
        if label is None:
            return
        try:
            items = td.load_attachments("trips", self._batch_record_key(group))
        except Exception:
            items = []
        label.configure(text=f"{len(items)} ملف" if items else "لا توجد ملفات")

    def _refresh_batch_locations_label(self, group):
        label = group.get("locations_label")
        if label is None:
            return
        try:
            items = td.load_locations(self._batch_record_key(group))
        except Exception:
            items = []
        label.configure(text=f"{len(items)} موقع" if items else "لا توجد مواقع")

    def _build_location_editor(self, parent, record_key, existing=None, on_saved=None):
        """نافذة إضافة/تعديل موقع موحّدة (الاسم + الرابط + الملاحظات + لصق + حفظ).
        تُستخدم من زر «إضافة موقع» في رأس البيان ومن نافذة «عرض المواقع»."""
        editor = tk.Toplevel(parent)
        editor.title("تعديل الموقع" if existing else "اضافة موقع")
        editor.geometry("560x430")
        editor.configure(bg=COLOR_BG)
        try:
            editor.transient(parent)
            editor.grab_set()
        except Exception as _log_exc: log_exception("_build_location_editor", _log_exc)
        center_dialog(editor, parent)

        tk.Label(editor, text="اسم الموقع (اختياري)", font=F_LABEL,
                 bg=COLOR_BG, fg=COLOR_MUTED, anchor="e").pack(fill="x", padx=16, pady=(14, 2))
        name_var = tk.StringVar(value=safe_str(existing.get("name")) if existing else "")
        tk.Entry(editor, textvariable=name_var, font=F_BODY, justify="right").pack(
            fill="x", padx=16, ipady=4)

        tk.Label(editor, text="رابط Google Maps (يحفظ كما هو تماما)", font=F_LABEL,
                 bg=COLOR_BG, fg=COLOR_MUTED, anchor="e").pack(fill="x", padx=16, pady=(10, 2))
        url_text = tk.Text(editor, height=5, font=F_BODY, wrap="word")
        url_text.pack(fill="x", padx=16, ipady=4)
        url_text.focus_set()
        if existing:
            url_text.insert("1.0", safe_str(existing.get("google_maps_url")))

        def paste_into_url():
            try:
                value = editor.clipboard_get()
            except Exception:
                return
            if value:
                url_text.insert(tk.INSERT, value)
                url_text.see(tk.INSERT)
                url_text.focus_set()

        def _paste_ctrl_v(_event=None):
            paste_into_url()
            return "break"

        url_text.bind("<Control-v>", _paste_ctrl_v)
        url_text.bind("<Shift-Insert>", _paste_ctrl_v)
        url_menu = tk.Menu(url_text, tearoff=0)
        url_menu.add_command(label="لصق", command=paste_into_url)
        url_text.bind("<Button-3>", lambda e: url_menu.tk_popup(e.x_root, e.y_root))
        tk.Button(editor, text="لصق الرابط من الحافظة", command=paste_into_url,
                  font=F_BODY, relief="flat", bd=0, cursor="hand2",
                  bg=COLOR_BORDER_LIGHT, fg=COLOR_TEXT,
                  activebackground=COLOR_BORDER, activeforeground=COLOR_PRIMARY,
                  padx=6, pady=3).pack(anchor="w", padx=16, pady=(2, 0))

        tk.Label(editor, text="ملاحظات (اختيارية)", font=F_LABEL,
                 bg=COLOR_BG, fg=COLOR_MUTED, anchor="e").pack(fill="x", padx=16, pady=(10, 2))
        notes_var = tk.StringVar(value=safe_str(existing.get("notes")) if existing else "")
        tk.Entry(editor, textvariable=notes_var, font=F_BODY, justify="right").pack(
            fill="x", padx=16, ipady=4)

        def do_save():
            url = url_text.get("1.0", "end-1c")
            if not url.strip():
                messagebox.showwarning("تنبيه", "الصق رابط Google Maps اولا.", parent=editor)
                return
            try:
                td.save_location(name_var.get(), url, notes_var.get(), record_key,
                                 location_id=existing.get("id") if existing else None)
            except ValueError as exc:
                messagebox.showerror("حفظ الموقع", str(exc), parent=editor)
                return
            editor.destroy()
            if on_saved:
                on_saved()

        row = tk.Frame(editor, bg=COLOR_BG)
        row.pack(fill="x", padx=16, pady=14)
        make_btn(row, "حفظ", do_save, variant="accent").pack(side="right", padx=4)
        make_btn(row, "الغاء", editor.destroy, variant="secondary").pack(side="right", padx=4)
        return editor

    def _quick_add_batch_location(self, group):
        """إضافة موقع من رأس البيان — نفس نافذة شاشة «عرض المواقع» تماماً."""
        record_key = self._batch_record_key(group)

        def _after_save():
            self._refresh_batch_locations_label(group)
            messagebox.showinfo("موقع التنزيل", "تم حفظ الرابط الاصلي بالكامل.",
                                parent=self.frame)

        self._build_location_editor(self.frame, record_key, existing=None, on_saved=_after_save)

    def _add_batch_files(self, group):
        """إضافة عدة ملفات دفعة واحدة للبيان الحالي."""
        sources = filedialog.askopenfilenames(
            parent=self.frame,
            title="اضافة ملفات للبيان",
            filetypes=[
                ("المستندات والصور", (
                    "*.pdf", "*.doc", "*.docx", "*.xls", "*.xlsx",
                    "*.jpg", "*.jpeg", "*.png",
                )),
                ("كل الملفات", "*.*"),
            ],
        )
        if not sources:
            return
        record_key = self._batch_record_key(group)
        added = 0
        errors = []
        for source in sources:
            try:
                td.add_attachment("trips", record_key, source, notes="ملفات البيان")
                added += 1
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
        if errors:
            messagebox.showerror("اضافة الملفات",
                                 "تمت اضافة بعض الملفات او تعذر اضافتها:\n" + "\n".join(errors),
                                 parent=self.frame)
        else:
            messagebox.showinfo("المرفقات", f"تمت اضافة {added} ملف/ملفات.", parent=self.frame)
        self._refresh_batch_files_label(group)

    def _open_batch_locations(self, group):
        """مواقع التنزيل الخاصة بالبيان — حفظ رابط Google Maps الاصلي كنص فقط."""
        record_key = self._batch_record_key(group)
        dialog = tk.Toplevel(self.frame)
        title_no = safe_str(group["declaration_no"].get()).strip() or "بدون رقم"
        dialog.title(f"موقع التنزيل — {title_no}")
        dialog.geometry("900x480")
        dialog.configure(bg=COLOR_BG)
        dialog.transient(self.frame)
        dialog.grab_set()
        center_dialog(dialog, self.frame)
        tree = ttk.Treeview(
            dialog, columns=("notes", "url", "name", "at"), show="headings", selectmode="browse")
        for key, label, width in (
            ("notes", "ملاحظات", 170), ("url", "رابط Google Maps", 380),
            ("name", "الاسم", 150), ("at", "التاريخ", 140),
        ):
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor="e")
        tree.pack(fill="both", expand=True, padx=14, pady=14)
        # الضغط مرتين على الموقع يفتح الرابط مباشرة في المتصفح.
        tree.bind("<Double-1>", lambda _event: open_location())

        def reload_items():
            try:
                fresh = td.load_locations(record_key)
            except Exception:
                fresh = []
            for iid in tree.get_children():
                tree.delete(iid)
            for item in fresh:
                tree.insert("", "end", iid=str(item["id"]),
                            values=(item.get("notes", ""), item.get("google_maps_url", ""),
                                    item.get("name", ""), item.get("created_at", "")))
            self._refresh_batch_locations_label(group)
            return fresh

        items = reload_items()

        def selected_item():
            selection = tree.selection()
            if not selection:
                messagebox.showinfo("تنبيه", "اختر موقعا اولا.", parent=dialog)
                return None
            return next((item for item in items if str(item["id"]) == selection[0]), None)

        def location_editor(existing=None):
            def _after_save():
                fresh = reload_items()
                items.clear()
                items.extend(fresh)
            self._build_location_editor(dialog, record_key, existing=existing,
                                        on_saved=_after_save)

        def open_location():
            item = selected_item()
            if not item:
                return
            url = safe_str(item.get("google_maps_url"))
            if url.strip():
                webbrowser.open(url)

        def copy_location():
            item = selected_item()
            if not item:
                return
            dialog.clipboard_clear()
            dialog.clipboard_append(safe_str(item.get("google_maps_url")))
            messagebox.showinfo("نسخ", "تم نسخ الرابط الاصلي بالكامل.", parent=dialog)

        def share_whatsapp():
            item = selected_item()
            if not item:
                return
            url = safe_str(item.get("google_maps_url"))
            webbrowser.open("https://wa.me/?text=" + urllib.parse.quote(url, safe=""))

        def edit_location():
            item = selected_item()
            if not item:
                return
            location_editor(item)

        def delete_location():
            item = selected_item()
            if not item:
                return
            if not messagebox.askyesno("حذف الموقع", "حذف هذا الموقع نهائيا؟", parent=dialog):
                return
            td.delete_location(item["id"])
            fresh = reload_items()
            items.clear()
            items.extend(fresh)

        loc_buttons = tk.Frame(dialog, bg=COLOR_BG)
        loc_buttons.pack(fill="x", padx=14, pady=(0, 14))
        make_btn(loc_buttons, "اضافة موقع", lambda: location_editor(None),
                 variant="accent").pack(side="right", padx=4)
        make_btn(loc_buttons, "فتح", open_location, variant="secondary").pack(side="right", padx=4)
        make_btn(loc_buttons, "نسخ", copy_location, variant="secondary").pack(side="right", padx=4)
        make_btn(loc_buttons, "ارسال واتساب", share_whatsapp,
                 variant="secondary").pack(side="right", padx=4)
        make_btn(loc_buttons, "تعديل", edit_location, variant="secondary").pack(side="right", padx=4)
        make_btn(loc_buttons, "حذف", delete_location, variant="danger").pack(side="right", padx=4)
        make_btn(loc_buttons, "اغلاق", dialog.destroy, variant="secondary").pack(side="right", padx=4)

    def _open_batch_files(self, group):
        """عرض ملفات البيان — نفس نافذة شاشة السائقون (نوع المستند/الملف/أضافه/التاريخ)."""
        record_key = self._batch_record_key(group)
        category_label = "ملفات البيان"
        dialog = tk.Toplevel(self.frame)
        title_no = safe_str(group["declaration_no"].get()).strip() or "بدون رقم"
        dialog.title(f"ملفات — {title_no}")
        dialog.geometry("820x430")
        dialog.configure(bg=COLOR_BG)
        dialog.transient(self.frame)
        dialog.grab_set()
        center_dialog(dialog, self.frame)
        tree = ttk.Treeview(
            dialog, columns=("type", "name", "by", "at"), show="headings", selectmode="browse")
        for key, label, width in (
            ("type", "نوع المستند", 190), ("name", "الملف", 300),
            ("by", "أضافه", 120), ("at", "التاريخ", 150),
        ):
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor="e")
        tree.bind("<Double-1>", lambda _event: open_file())
        tree.pack(fill="both", expand=True, padx=14, pady=14)

        def reload_items():
            fresh = td.load_attachments("trips", str(record_key))
            for iid in tree.get_children():
                tree.delete(iid)
            for item in fresh:
                tree.insert("", "end", iid=str(item["id"]),
                            values=(item["notes"], item["file_name"],
                                    item["created_by"], item["created_at"]))
            self._refresh_batch_files_label(group)
            return fresh

        items = reload_items()

        def selected_item():
            selection = tree.selection()
            if not selection:
                messagebox.showinfo("تنبيه", "اختر ملفا اولا.", parent=dialog)
                return None
            return next((item for item in items if str(item["id"]) == selection[0]), None)

        def open_file():
            item = selected_item()
            if not item:
                return
            if not os.path.isfile(item["path"]):
                messagebox.showerror("فتح الملف", "الملف غير موجود.", parent=dialog)
                return
            try:
                os.startfile(item["path"])
            except OSError as exc:
                messagebox.showerror("فتح الملف", str(exc), parent=dialog)

        def download_file():
            item = selected_item()
            if not item:
                return
            if not os.path.isfile(item["path"]):
                messagebox.showerror("تنزيل الملف", "الملف غير موجود.", parent=dialog)
                return
            target = filedialog.asksaveasfilename(
                parent=dialog, title="تنزيل نسخة من الملف",
                initialfile=item["file_name"])
            if not target:
                return
            try:
                shutil.copy2(item["path"], target)
            except OSError as exc:
                messagebox.showerror("تنزيل الملف", str(exc), parent=dialog)
                return
            messagebox.showinfo("المرفقات", "تم تنزيل نسخة الملف.", parent=dialog)

        def replace_file():
            item = selected_item()
            if not item:
                return
            source = filedialog.askopenfilename(
                parent=dialog, title="اختيار الملف البديل",
                filetypes=[("كل الملفات", "*.*")])
            if not source:
                return
            try:
                replacement = td.add_attachment(
                    "trips", record_key, source,
                    notes=safe_str(item.get("notes")).strip() or category_label)
                td.delete_attachment(item["id"])
                messagebox.showinfo("المرفقات",
                                    f"تم الاستبدال بـ {replacement['file_name']}.", parent=dialog)
                new_items = reload_items()
                items.clear()
                items.extend(new_items)
            except (OSError, ValueError) as exc:
                messagebox.showerror("استبدال الملف", str(exc), parent=dialog)

        def delete_file():
            item = selected_item()
            if not item:
                return
            if not messagebox.askyesno("حذف الملف", "حذف هذا الملف نهائيا؟", parent=dialog):
                return
            try:
                td.delete_attachment(item["id"])
                messagebox.showinfo("المرفقات", "تم حذف الملف.", parent=dialog)
                new_items = reload_items()
                items.clear()
                items.extend(new_items)
            except (OSError, ValueError) as exc:
                messagebox.showerror("حذف الملف", str(exc), parent=dialog)

        buttons = tk.Frame(dialog, bg=COLOR_BG)
        buttons.pack(fill="x", padx=14, pady=(0, 14))
        make_btn(buttons, "تنزيل نسخة", download_file, variant="accent").pack(side="right", padx=4)
        make_btn(buttons, "استبدال", replace_file, variant="secondary").pack(side="right", padx=4)
        make_btn(buttons, "حذف", delete_file, variant="danger").pack(side="right", padx=4)
        make_btn(buttons, "فتح", open_file, variant="secondary").pack(side="right", padx=4)
        make_btn(buttons, "اغلاق", dialog.destroy, variant="secondary").pack(side="right", padx=4)

    def _clear_batch_group(self, group):
        """تفريغ حقول البيان بدون حذف الصفوف."""
        if not messagebox.askyesno("مسح الحقول",
                                    "سيتم تفريغ جميع حقول هذا البيان. المتابعة؟",
                                    parent=self.frame):
            return
        for key, var in group["shared"].items():
            try:
                var.set(td.TRIP_CATEGORIES[0] if key == "trip_category" else "")
            except Exception as _log_exc: log_exception("_clear_batch_group", _log_exc)
        for key in ("date", "declaration_no"):
            try:
                group[key].set("")
            except Exception as _log_exc: log_exception("_clear_batch_group", _log_exc)
        for row in group["rows"]:
            for key, var in row["vars"].items():
                if key in ("trip_category", "company", "customer"):
                    continue
                try:
                    var.set("")
                except Exception as _log_exc: log_exception("_clear_batch_group", _log_exc)
            row["hidden_values"].clear()
            row["trip_id"] = None
        self._refresh_group_trip_codes(group)
        self._refresh_group_selector()
        self._sync_services_tab()
        self._refresh_batch_files_label(group)

    def _remove_batch_group(self, group):
        """حذف بيان كامل وجميع الرحلات التابعة له من الإدخال الحالي."""
        declaration = group["declaration_no"].get().strip() or "بدون رقم"
        if not messagebox.askyesno(
                "تأكيد حذف البيان",
                f"سيتم حذف البيان ({declaration}) وجميع رحلاته من شاشة الإدخال. هل تريد المتابعة؟"):
            return
        for row in group["rows"]:
            trip_id = row.get("trip_id")
            if trip_id not in (None, ""):
                td.delete_trip(trip_id)
        self.batch_rows = [row for row in self.batch_rows if row.get("group") is not group]
        if group in self.batch_groups:
            self.batch_groups.remove(group)
        group["frame"].destroy()
        if self.active_batch_group is group:
            self.active_batch_group = self.batch_groups[-1] if self.batch_groups else None
        self._refresh_group_selector()
        self._sync_services_tab()
        if not self.batch_groups:
            self._add_batch_row()
        if any(row.get("trip_id") not in (None, "") for row in group.get("rows", [])):
            refresh_related_screens(self.frame)

    def _on_group_company_change(self, group):
        company_name = group["shared"]["company"].get().strip()
        company = next((c for c in td.load_companies() if safe_str(c.get("name")) == company_name), None)
        group["shared"]["customer"].set(safe_str(company.get("customs_broker")) if company else NO_CUSTOMER)

    def _on_group_category_change(self, group):
        for row in group["rows"]:
            self._on_row_category_change(row)

    def _add_batch_row(self, data=None, trip_id=None, group=None):
        """إضافة صف رحلة جديد للإدخال الدفعي."""
        data = data or {}
        group = group or self.active_batch_group
        if group is None:
            group = self._create_batch_group({"date": self.vars["date"].get().strip() or date.today().isoformat()})
        self.active_batch_group = group
        row_frame = tk.Frame(group["frame"], bg=COLOR_CARD)
        row_frame.pack(fill="x", padx=4, pady=3)
        row_vars = {}
        row_combos = {}

        n = len(self._batch_fields)
        for idx, (key, label) in enumerate(self._batch_fields):
            c = n - 1 - idx
            cell = tk.Frame(row_frame, bg=COLOR_CARD)
            cell.grid(row=0, column=c, padx=4, sticky="ew")
            # Shared fields must use the group's variables from the start.
            # Creating a temporary variable and replacing row_vars later
            # leaves the visible Combobox bound to the wrong variable, which
            # prevents the loading/unloading lists from updating correctly on
            # newly added rows.
            var = group["shared"][key] if key in ("trip_category", "company", "customer") else tk.StringVar()
            if key == "date":
                date_input(cell, var).pack(fill="x")
                row_vars[key] = var
                continue
            if key == "declaration_trip_no":
                ttk.Entry(cell, textvariable=var, state="readonly", justify="right",
                          width=14).pack(fill="x", ipady=3)
                row_vars[key] = var
                continue
            if key in ("trip_category", "direction", "country", "driver_type", "driver", "car_no", "customer", "company", "container_size", "car_expense_type"):
                if key == "trip_category":
                    values = td.TRIP_CATEGORIES
                elif key == "direction":
                    values = []
                elif key == "country":
                    values = []
                elif key == "driver_type":
                    values = ["داخلي", "خارجي"]
                elif key == "car_no":
                    values = self._get_batch_cars()
                elif key == "driver":
                    values = [d["name"] for d in td.load_drivers()]
                elif key == "customer":
                    values = [NO_CUSTOMER] + [c["name"] for c in td.load_customers()]
                elif key == "company":
                    values = [c["name"] for c in td.load_companies()]
                elif key == "container_size":
                    values = ["1× 20' DC", "2× 20' DC", "1× 40' HC", "1× 20' FR", "1× 40' FR"]
                elif key == "car_expense_type":
                    values = td.MAINTENANCE_TYPES
                else:
                    values = []
                w = ttk.Combobox(cell, textvariable=var, values=values, font=F_BODY,
                                 justify="right", width=14)
                row_combos[key] = w
            else:
                w = tk.Entry(cell, textvariable=var, font=F_BODY, justify="right",
                             relief="flat", bd=0, highlightthickness=2,
                             highlightbackground=COLOR_BORDER,
                             highlightcolor=COLOR_PRIMARY_LIGHT, width=14)
            w.pack(fill="x", ipady=3)
            row_vars[key] = var
            for key, default in (
                ("container_size", "1× 40' HC"),
                ("direction", "ميناء الشويخ"),
                ("country", "ميناء الشويخ"),
            ):
                if key in row_vars and not row_vars[key].get().strip():
                    row_vars[key].set(default)
            for i in range(n):
                row_frame.grid_columnconfigure(i, weight=1, uniform="trip_batch")
            # Shared values are displayed in the group header but are also needed
            # by the row-level save and option-refresh logic.
            for key in ("trip_category", "company", "customer"):
                row_vars[key] = group["shared"][key]

            # زر حذف الصف
            row_idx = len(self.batch_rows)
            def remove_this():
                self._remove_batch_row(row_idx)
            make_btn(row_frame, "حذف", remove_this, variant="danger", width=6).grid(row=0, column=n, padx=4)

            # تعبئة البيانات إن وُجدت
            if data:
                for k, v in data.items():
                    if k in row_vars:
                        row_vars[k].set(safe_str(v))
            row_data = {"frame": row_frame, "vars": row_vars, "combos": row_combos,
                         "trip_id": trip_id, "hidden_values": {}, "group": group}

            if "company" in row_combos:
                row_combos["company"].bind(
                    "<<ComboboxSelected>>",
                    lambda _event, r=row_data: self._on_company_selected(r),
                )
            if "driver" in row_combos:
                row_combos["driver"].bind(
                    "<<ComboboxSelected>>",
                    lambda _event, r=row_data: self._on_driver_selected(r),
                )
            if "driver_type" in row_combos:
                row_combos["driver_type"].bind(
                    "<<ComboboxSelected>>",
                    lambda _event, r=row_data: self._on_driver_type_selected(r),
                )

            # نفس الربط يتابع تغيير قيمة المتغير لا الفأرة فقط، فيعمل السلسلة
            # أيضاً عند الكتابة أو اللصق أو التحميل التلقائي للصفوف.
            if "driver_type" in row_vars and "driver" in row_vars:
                def _on_type_var(*_args, r=row_data):
                    if r.get("link_busy"):
                        return
                    r["link_busy"] = True
                    try:
                        self._on_driver_type_selected(r)
                    finally:
                        r["link_busy"] = False
                row_vars["driver_type"].trace_add("write", _on_type_var)
            if "driver" in row_vars:
                def _on_driver_var(*_args, r=row_data):
                    if r.get("link_busy"):
                        return
                    r["link_busy"] = True
                    try:
                        self._on_driver_selected(r)
                    finally:
                        r["link_busy"] = False
                row_vars["driver"].trace_add("write", _on_driver_var)

            # الصفوف المحمّلة من قاعدة البيانات لا تمرّ بأحداث الفأرة، فتُطبَّق
            # التصفية مرة واحدة هنا حتى تظهر قائمتها مفلترة حسب نوع السائق.
            if row_vars.get("driver_type") is not None and row_combos.get("driver") is not None:
                row_data["link_busy"] = True
                try:
                    self._on_driver_type_selected(row_data)
                finally:
                    row_data["link_busy"] = False

            # احتفظ بالقيم المخفية لمصروفات السيارة إذا كانت موجودة
            if data:
                for key in self.EXPENSE_FIELDS:
                    if key in data:
                        row_data["hidden_values"][key] = safe_str(data[key])
 
            # ربط تغيير نوع الشحن بتحديث الاتجاه والدولة والسيارات لكل صف
            if "trip_category" in row_combos:
                row_combos["trip_category"].bind("<<ComboboxSelected>>",
                    lambda e, r=row_data: self._on_row_category_change(r))
            # The trip category normally lives in the declaration header (it is
            # intentionally omitted from the row fields), so this must run even
            # when the row has no trip_category Combobox of its own.
            self._on_row_category_change(row_data)
 
            self.batch_rows.append(row_data)
            group["rows"].append(row_data)
            self._refresh_group_trip_codes(group)

    @staticmethod
    def _trip_code_sequence(value):
        """Extract the numeric trip suffix from a code such as 123-2."""
        text = safe_str(value).strip()
        suffix = text.rsplit("-", 1)[-1] if "-" in text else ""
        try:
            number = int(suffix)
            return number if number > 0 else None
        except (TypeError, ValueError):
            return None

    def _refresh_group_trip_codes(self, group):
        """Create stable codes; existing suffixes are never renumbered."""
        declaration = group["declaration_no"].get().strip()
        used = set()
        next_number = 1
        if not declaration:
            for row in group["rows"]:
                if "declaration_trip_no" in row["vars"]:
                    row["vars"]["declaration_trip_no"].set("")
            return

        for row in group["rows"]:
            if "declaration_trip_no" not in row["vars"]:
                continue
            current = row["vars"]["declaration_trip_no"].get().strip()
            number = self._trip_code_sequence(current)
            if number is None or number in used:
                while next_number in used:
                    next_number += 1
                number = next_number
            used.add(number)
            next_number = max(next_number, number + 1)
            row["vars"]["declaration_trip_no"].set(f"{declaration}-{number}")

    def _apply_batch_declaration(self):
        """تطبيق رقم البيان الحالي على كل الصفوف الظاهرة."""
        declaration = self.batch_declaration_var.get().strip()
        for row in self.batch_rows:
            if "declaration_no" in row["vars"]:
                row["vars"]["declaration_no"].set(declaration)

    def _add_same_declaration_row(self):
        self._add_batch_row()

    def _add_new_declaration_row(self):
        """بدء مجموعة بيان جديدة في نفس التاريخ."""
        self.active_batch_group = self._create_batch_group({"date": "", "declaration_no": ""})
        self._add_batch_row(group=self.active_batch_group)

    def _on_company_selected(self, row):
        company_name = row["vars"]["company"].get().strip()
        company = next((item for item in td.load_companies()
                    if str(item.get("name", "")).strip() == company_name), None)
        customer = safe_str(company.get("customs_broker")) if company else ""
        row["vars"]["customer"].set(customer or NO_CUSTOMER)

    def _on_driver_selected(self, row):
        """تحديد السيارة المكلَّفة للسائق من جدول تكليفات السائقين عند اختياره."""
        driver_name = row["vars"]["driver"].get().strip()
        # جدول تكليفات السائقين هو الشاشة التي تربط كل سائق بسيارة، فيُعتمد عليه هنا.
        day = row["vars"]["date"].get().strip() if "date" in row["vars"] else ""
        car_no = td.car_for_driver(driver_name, day)
        if "car_no" in row["combos"]:
            if car_no:
                values = list(row["combos"]["car_no"].cget("values"))
                if car_no not in values:
                    values.append(car_no)
                    row["combos"]["car_no"].config(values=values)
            row["vars"]["car_no"].set(car_no)

    def _on_driver_type_selected(self, row):
        """تصفية قائمة السائقين حسب النوع المختار؛ والسيارة تُحدَّد عند اختيار السائق."""
        driver_type = row["vars"]["driver_type"].get().strip()
        names = td.driver_names_by_type(driver_type)
        if "driver" in row["combos"]:
            row["combos"]["driver"].config(values=names)
        # نُبقي السائق إن كان ضمن القائمة الجديدة، وإلا نفرّغه حتى لا يبقى
        # اسم سائق داخلي في صف نوعه خارجي.
        current = row["vars"]["driver"].get().strip()
        if not (current and current in names):
            row["vars"]["driver"].set("")
        if "car_no" in row["combos"]:
            cars = self._get_batch_cars(row["vars"]["trip_category"].get()
                                        or td.TRIP_CATEGORIES[0])
            row["combos"]["car_no"].config(values=cars)

    def _remove_batch_row(self, idx):
        """حذف صف من الإدخال الدفعي."""
        if len(self.batch_rows) <= 1:
            messagebox.showinfo("تنبيه", "لا يمكن حذف كل الصفوف — يجب أن تبقى رحلة واحدة على الأقل.")
            return
        if idx < len(self.batch_rows):
            row = self.batch_rows.pop(idx)
            group = row.get("group")
            if group and row in group.get("rows", []):
                group["rows"].remove(row)
            row["frame"].destroy()
            self._reindex_batch_rows()

    def _reindex_batch_rows(self):
        """إعادة ربط أزرار الحذف بعد حذف صف."""
        for i, row in enumerate(self.batch_rows):
            for child in row["frame"].winfo_children():
                if isinstance(child, tk.Button):
                    child.config(command=lambda i=i: self._remove_batch_row(i))

    def _get_batch_cars(self, cat=None):
        """قائمة السيارات المتاحة حسب نوع الشحن المختار."""
        if cat is None:
            cat = td.TRIP_CATEGORIES[0]
        vehicles = td.load_vehicles()
        if is_international_trip_category(cat):
            allowed = {td.VEHICLE_WORK_TYPES[1], td.VEHICLE_WORK_TYPES[2]}
        else:
            allowed = {td.VEHICLE_WORK_TYPES[0], td.VEHICLE_WORK_TYPES[2]}
        cars = [v["car_no"] for v in vehicles if (not v.get("work_type")) or v.get("work_type") in allowed]
        if not cars:
            cars = [v["car_no"] for v in vehicles]
        return cars

    def _on_row_category_change(self, row, event=None):
        """تحديث خيارات مكان التحميل/التنزيل والسيارات عند تغيير نوع الشحن في صف معين.

        «مكان التحميل» و«مكان التنزيل» يعيشان في رأس البيان لا في الصف، فنتعامل
        مع غيابهما من الصف دون خطأ.
        """
        cat = row["vars"]["trip_category"].get() or td.TRIP_CATEGORIES[0]
        load_places = td.get_places_for_trip_category_and_usage(cat, "تحميل")
        unload_places = td.get_places_for_trip_category_and_usage(cat, "تفريغ")
        if "direction" in row["combos"]:
            row["combos"]["direction"].config(values=load_places, state="normal")
        if "direction" in row["vars"] and row["vars"]["direction"].get() not in load_places:
            row["vars"]["direction"].set(load_places[0] if load_places else "")
        if "country" in row["combos"]:
            row["combos"]["country"].config(values=unload_places, state="normal")
        if "country" in row["vars"] and row["vars"]["country"].get() not in unload_places:
            row["vars"]["country"].set(unload_places[0] if unload_places else "")
        self._refresh_row_cars(row)

    def _refresh_row_cars(self, row):
        """تحديث قائمة السيارات لصف معين حسب نوع الشحن، مع إبقاء سيارة السائق."""
        cat = row["vars"]["trip_category"].get() or td.TRIP_CATEGORIES[0]
        cars = self._get_batch_cars(cat)
        if "car_no" in row["combos"]:
            combo = row["combos"]["car_no"]
            current = row["vars"]["car_no"].get().strip()
            # نحتفظ دائماً بسيارة السائق المختار حتى لو كانت خارج نوع الشحن،
            # ونترك للمستخدم حرية تغييرها من القائمة.
            if current and current not in cars:
                cars = [current] + cars
            combo.config(values=cars)

    def _save_all_batch(self):
        """حفظ كل رحلات الإدخال الدفعي."""
        d_date = ""
        if not self.batch_rows:
            messagebox.showwarning("تنبيه", "الرجاء إدخال التاريخ.")
            return

        for group in self.batch_groups:
            self._refresh_group_trip_codes(group)

        saved = 0
        errors = []
        saved_ids = []
        for i, row in enumerate(self.batch_rows):
            group = row["group"]
            d_date = group["date"].get().strip()
            if not d_date:
                errors.append(f"صف {i+1}: التاريخ مطلوب.")
                continue
            car = row["vars"]["car_no"].get().strip()
            if not car:
                errors.append(f"صف {i+1}: رقم السيارة مطلوب.")
                continue
            data = {
                "date": d_date,
                "trip_category": row["vars"]["trip_category"].get().strip(),
                "direction": row["vars"]["direction"].get().strip(),
                "country": row["vars"]["country"].get().strip(),
                "driver_type": row["vars"]["driver_type"].get().strip(),
                "driver": row["vars"]["driver"].get().strip(),
                "car_no": car,
                "customer": row["vars"]["customer"].get().strip(),
                "company": row["vars"].get("company", tk.StringVar()).get().strip() if row["vars"].get("company") is not None else "",
                "declaration_no": group["declaration_no"].get().strip(),
                "declaration_trip_no": row["vars"]["declaration_trip_no"].get().strip(),
                "container_size": row["vars"]["container_size"].get().strip(),
                "car_expense_type": row.get("hidden_values", {}).get("car_expense_type", ""),
                "car_expense_amount": row.get("hidden_values", {}).get("car_expense_amount", ""),
                "driver_expense": row.get("hidden_values", {}).get("driver_expense", ""),
                "fee": row["vars"]["fee"].get().strip(),
                "holiday_price": row["vars"]["holiday_price"].get().strip(),
                "driver_wage": row["vars"]["driver_wage"].get().strip(),
                "notes": row["vars"]["notes"].get().strip(),
            }
            try:
                td.save_trip(data, row.get("trip_id"))
                saved += 1
                saved_ids.append(safe_str(data.get("id", "")).strip())
            except Exception as e:
                errors.append(f"صف {i+1}: {e}")

        if saved > 0:
            # مزامنة مفتاح ملفات/مواقع كل بيان مع التاريخ ورقم البيان النهائيين
            # حتى لا تُفقد الملفات أو المواقع إن غيّر المستخدم التاريخ/الرقم
            # بعد آخر مرة فتح فيها ملفات البيان أو مواقعه.
            for group in self.batch_groups:
                try:
                    self._batch_record_key(group)
                except Exception as _log_exc: log_exception("_save_all_batch", _log_exc)
        if saved > 0 and getattr(self, "_temp_attachment_key", None) and saved_ids:
            temp_key = self._temp_attachment_key
            last_id = saved_ids[-1]
            try:
                td.move_attachments(self.attachment_entity_type, temp_key, last_id)
            except Exception as exc:
                messagebox.showwarning("المرفقات",
                    f"تم حفظ البيانات لكن فشل ربط بعض المرفقات بالرحلة:\n{exc}", parent=self.frame)
            self._temp_attachment_key = None

        if errors:
            messagebox.showwarning("تنبيه", f"تم حفظ {saved} رحلة.\nأخطاء:\n" + "\n".join(errors))
        else:
            messagebox.showinfo("تم", f"تم حفظ {saved} رحلة بنجاح.")

        if saved > 0 and not errors:
            self._auto_invoice_saved_declarations()
            self.refresh()
            refresh_related_screens(self.frame)
            for group in self.batch_groups:
                group["frame"].destroy()
            self.batch_groups.clear()
            self.batch_rows.clear()
            self.active_batch_group = None
            self._add_batch_row()
            self._sync_services_tab()

    def _auto_invoice_saved_declarations(self):
        """Create one invoice automatically for each newly saved declaration."""
        all_trips = td.load_trips()
        invoice_numbers = []
        errors = []
        declarations = {(safe_str(group["date"].get()).strip(),
                     safe_str(group["declaration_no"].get()).strip())
                    for group in self.batch_groups}
        for group_date, group_declaration in declarations:
            rows = [trip for trip in all_trips
                    if safe_str(trip.get("date")).strip() == group_date
                    and safe_str(trip.get("declaration_no")).strip() == group_declaration]
            unbilled = [trip for trip in rows if safe_str(trip.get("invoiced")) != "نعم"]
            if not unbilled:
                continue
            try:
                invoice = td.create_invoice_for_declaration([trip.get("id") for trip in unbilled])
                invoice_numbers.append(str(invoice["invoice_no"]))
            except Exception as exc:
                errors.append(f"{group_declaration or 'بدون رقم بيان'}: {exc}")
        if invoice_numbers:
            messagebox.showinfo("تم", "تم إنشاء الفواتير تلقائيًا: " + ", ".join(invoice_numbers))
        if errors:
            messagebox.showwarning(
                "لم تُنشأ بعض الفواتير",
                "تم حفظ الرحلات، لكن راجع بيانات العميل قبل إصدار الفاتورة:\n" + "\n".join(errors),
            )

    def _load_today_batch(self):
        """تحميل رحلات اليوم الحالية للتعديل."""
        today_iso = date.today().isoformat()
        today_trips = td.trips_for_date(today_iso)
        if not today_trips:
            messagebox.showinfo("تنبيه", "لا توجد رحلات مسجّلة لهذا اليوم بعد.")
            return
        self.vars["date"].set(safe_str(today_trips[0].get("date", "")))
        self.batch_declaration_var.set(safe_str(today_trips[0].get("declaration_no", "")))
        for group in self.batch_groups:
            group["frame"].destroy()
        self.batch_groups.clear()
        self.active_batch_group = None
        self.batch_rows.clear()
        groups = {}
        for t in today_trips:
            group_key = (safe_str(t.get("date", "")), safe_str(t.get("declaration_no", "")))
            group = groups.get(group_key)
            if group is None:
                group = self._create_batch_group({"date": group_key[0], "declaration_no": group_key[1],
                                              "trip_category": t.get("trip_category", ""),
                                              "company": t.get("company", ""), "customer": t.get("customer", "")})
            groups[group_key] = group
        self._add_batch_row({
            "date": t.get("date", ""),
            "trip_category": t.get("trip_category", ""),
            "direction": t.get("direction", ""),
            "country": t.get("country", ""),
            "driver_type": t.get("driver_type", ""),
            "driver": t.get("driver", ""),
            "car_no": t.get("car_no", ""),
            "customer": t.get("customer", ""),
            "company": t.get("company", "") if t.get("company") is not None else "",
            "declaration_no": t.get("declaration_no", ""),
            "declaration_trip_no": t.get("declaration_trip_no", ""),
            "container_size": t.get("container_size", ""),
            "car_expense_type": t.get("car_expense_type", ""),
            "car_expense_amount": t.get("car_expense_amount", ""),
            "driver_expense": t.get("driver_expense", ""),
            "fee": t.get("fee", ""),
            "holiday_price": t.get("holiday_price", ""),
            "notes": t.get("notes", ""),
        }, trip_id=t.get("id", ""), group=group)

    def _build_table(self):
        # Display exactly the fields used by the daily-entry form. The record
        # id remains the Treeview item id and does not need its own cell.
        self.fields = [("date", "التاريخ")] + list(self._batch_fields)
        card = card_frame(self.frame, "سجل الرحلات اليومية")
        card.pack(fill="both", expand=True, padx=18, pady=(8, 18))
        box = card.body

        toolbar = tk.Frame(box, bg=COLOR_CARD)
        toolbar.pack(fill="x", padx=12, pady=(0, 8))
        # --- كل أدوات البحث/الفلترة والأزرار في صف واحد ---
        # البحث + الفلاتر على اليمين (تتمدد لتملأ المساحة)
        tools = tk.Frame(toolbar, bg=COLOR_CARD)
        tools.pack(side="right", fill="x", expand=True)
        tk.Label(tools, text="بحث", font=F_BODY, bg=COLOR_CARD, fg=COLOR_MUTED).pack(
            side="right", padx=(2, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        search_entry = tk.Entry(tools, textvariable=self.search_var, font=F_BODY,
                 justify="right", relief="flat", bd=0,
                 highlightthickness=2, highlightbackground=COLOR_BORDER,
                 highlightcolor=COLOR_PRIMARY_LIGHT, width=10)
        search_entry.pack(side="right", ipady=4)
        tooltip(search_entry, "بحث في جميع حقول السجل")
        ttk.Checkbutton(tools, text="رحلات اليوم فقط", variable=self.today_var,
                         command=self.refresh).pack(side="right", padx=8)

        # الفلاتر في نفس الصف مباشرة بعد البحث
        self._trip_filter_labels = {label: key for key, label in self.fields}
        filter_values = ["الكل"] + list(self._trip_filter_labels)
        tk.Label(tools, text="فلترة حسب", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(6, 2))
        field_combo = ttk.Combobox(tools, textvariable=self.trip_filter_field_var,
                                   values=filter_values, state="readonly", width=8,
                                   font=F_BODY, justify="right")
        field_combo.pack(side="right", padx=1)
        field_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        tooltip(field_combo, "اختر الحقل الذي تريد الفلترة بواسطته")
        tk.Label(tools, text="القيمة", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(6, 2))
        value_entry = tk.Entry(tools, textvariable=self.trip_filter_value_var,
                               font=F_BODY, justify="right", width=10)
        value_entry.pack(side="right", padx=1)
        self.trip_filter_value_var.trace_add("write", lambda *_: self.refresh())
        tooltip(value_entry, "أدخل قيمة الفلترة المطلوبة")
        make_btn(tools, "مسح الفلاتر", self._clear_register_filters,
                 variant="secondary", width=10).pack(side="right", padx=(4, 1))

        # أزرار الإجراءات في نفس الصف (على الشمال)
        actions = tk.Frame(toolbar, bg=COLOR_CARD)
        actions.pack(side="left")
        btn2 = make_btn(actions, "إنشاء فاتورة للبيان", self.create_invoice_for_selected_declaration,
                 variant="accent")
        btn2.pack(side="right", padx=2)
        tooltip(btn2, "إنشاء فاتورة للبيان المحدد")
        btn3 = make_btn(actions, "طباعة", self.open_print_dialog,
                 variant="secondary")
        btn3.pack(side="right", padx=2)
        tooltip(btn3, "فتح نافذة الطباعة")
        btn4 = make_btn(actions, "حذف المحدد", self.delete_selected, variant="danger")
        btn4.pack(side="right", padx=2)
        tooltip(btn4, "حذف الرحلات المحددة")

        table_wrap = tk.Frame(box, bg=COLOR_CARD)
        table_wrap.pack(fill="both", expand=True, padx=18)
        cols = [k for k, _ in reversed(self.fields)]
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings", selectmode="extended")
        for k, label in reversed(self.fields):
            self.tree.heading(k, text=label)
            width = 130 if k in ("trip_category", "direction", "origin", "destination", "customer", "company") else 95
            self.tree.column(k, anchor="center", width=width, minwidth=80, stretch=True)
        apply_table_style(self.tree)
        vs = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        hs = ttk.Scrollbar(table_wrap, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        # الشريط العمودي على اليمين كما في الواجهات العربية.
        vs.pack(side="right", fill="y")
        hs.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.load_selected_into_form())
        self.tree.bind("<Configure>", lambda e: self._auto_size_columns())

        # ---------------- منطق الديناميكية الخاص بشاشة الرحلات ----------------
    def _selected_trip_rows(self):
        selected_ids = {str(item_id) for item_id in self.tree.selection()}
        row_map = getattr(self, "_tree_row_map", {})
        rows = [row_map[item_id] for item_id in self.tree.selection()
                if item_id in row_map]
        if not rows:
            selected_record_ids = {str(row_map[item].get(self.key_field, "")) for item in self.tree.selection() if item in row_map}
            rows = [row for row in self._rows
                    if str(row.get(self.key_field, "")) in selected_record_ids]
        if not rows:
            messagebox.showwarning("تنبيه", "الرجاء تحديد رحلة واحدة على الأقل.")
            return rows

    def print_selected_summary(self):
        """Print every selected daily-trip row, not only the first one."""
        rows = self._selected_trip_rows()
        if rows:
            generate_and_open_summary_print(
                f"{self.title} — السجلات المحددة", self.fields, rows)

    def open_print_dialog(self):
        dialog = tk.Toplevel(self.frame)
        dialog.title("طباعة الرحلات")
        dialog.configure(bg=COLOR_BG)
        dialog.transient(self.frame)
        dialog.grab_set()
        center_dialog(dialog, self.frame)

        mode_var = tk.StringVar(value="selected")
        tk.Radiobutton(dialog, text="طباعة المحدد", variable=mode_var, value="selected",
                    bg=COLOR_BG, font=F_BODY).pack(anchor="e", padx=18, pady=(12, 4))
        tk.Radiobutton(dialog, text="طباعة السجل المفلتر", variable=mode_var, value="filtered",
                    bg=COLOR_BG, font=F_BODY).pack(anchor="e", padx=18, pady=4)

        date_box = tk.Frame(dialog, bg=COLOR_BG)
        date_box.pack(fill="x", padx=18, pady=8)
        date_from_var = tk.StringVar()
        date_to_var = tk.StringVar()
        tk.Label(date_box, text="من", font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED).pack(side="right", padx=(10, 3))
        date_input(date_box, date_from_var, width=12).pack(side="right", padx=3)
        tk.Label(date_box, text="إلى", font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED).pack(side="right", padx=(10, 3))
        date_input(date_box, date_to_var, width=12).pack(side="right", padx=3)

        def do_print():
            mode = mode_var.get()
            date_from = date_from_var.get().strip()
            date_to = date_to_var.get().strip()
            rows = []
            if mode == "selected":
                rows = self._selected_trip_rows()
            else:
                for iid in self.tree.get_children():
                    row = self._tree_row_map.get(iid)
                    if row is None:
                        continue
                    row_date = safe_str(row.get("date", ""))
                    if date_from and row_date < date_from:
                        continue
                    if date_to and row_date > date_to:
                        continue
                    rows.append(row)
        if not rows:
            messagebox.showwarning("تنبيه", "لا توجد رحلات للطباعة.", parent=dialog)
            return
        generate_and_open_summary_print(
            f"{self.title} — طباعة", self.fields, rows)
        dialog.destroy()

        btns = tk.Frame(dialog, bg=COLOR_BG)
        btns.pack(fill="x", padx=18, pady=(0, 14), anchor="e")
        make_btn(btns, "طباعة", do_print, variant="accent").pack(side="right", padx=4)
        make_btn(btns, "إلغاء", dialog.destroy, variant="secondary").pack(side="right", padx=4)

    def select_declaration_rows(self):
        """Select all visible trips belonging to the selected trip's declaration."""
        rows = self._selected_trip_rows()
        if not rows:
            return
        selected = rows[0]
        declaration = safe_str(selected.get("declaration_no", "")).strip()
        day = safe_str(selected.get("date", ""))
        matching = [row for row in self._rows
                    if safe_str(row.get("date", "")) == day
                    and safe_str(row.get("declaration_no", "")).strip() == declaration]
        row_map = getattr(self, "_tree_row_map", {})
        visible_item_ids = set(self.tree.get_children())
        visible_record_ids = {str(row_map[item_id].get(self.key_field, "")) for item_id in visible_item_ids if item_id in row_map}
        ids = [str(row.get(self.key_field, "")) for row in matching
               if str(row.get(self.key_field, "")) in visible_record_ids]
        self.tree.selection_set(ids)

    def create_invoice_for_selected_declaration(self):
        """Issue an invoice from the complete declaration of the selected trip."""
        rows = self._selected_trip_rows()
        if not rows:
            return
        first = rows[0]
        declaration = safe_str(first.get("declaration_no", "")).strip()
        day = safe_str(first.get("date", ""))
        if not declaration:
            messagebox.showwarning("تنبيه", "لا يمكن إنشاء فاتورة قبل إدخال رقم البيان.")
            return
        declaration_rows = [row for row in td.load_trips()
                            if safe_str(row.get("date", "")) == day
                            and safe_str(row.get("declaration_no", "")).strip() == declaration]
        if not declaration_rows:
            return
        customer = safe_str(declaration_rows[0].get("customer", "")).strip()
        existing_numbers = {safe_str(row.get("invoice_no")).strip()
                            for row in declaration_rows
                            if safe_str(row.get("invoice_no")).strip()}
        if existing_numbers:
            invoice_no = next(iter(existing_numbers))
            invoice = next((item for item in td.load_invoices()
                            if safe_str(item.get("invoice_no")) == invoice_no), None)
            app = self.frame.winfo_toplevel()
            if invoice and hasattr(app, "_invoice_editor_dialog"):
                app._invoice_editor_dialog(invoice=invoice)
                self.refresh()
                return
        if not customer:
            messagebox.showwarning("تنبيه", "الرجاء تحديد العميل / المخلص للبيان أولاً.")
            return
        if not messagebox.askyesno(
            "إنشاء فاتورة",
            f"سيتم إنشاء فاتورة للمخلص: {customer}\nرقم البيان: {declaration}\n"
            f"وتشمل {len(declaration_rows)} رحلة والخدمات الإضافية المرتبطة به."):
            return
        try:
            context = td.invoice_context_for_declaration([row.get("id") for row in declaration_rows])
        except ValueError as exc:
            messagebox.showwarning("تنبيه", str(exc))
            return
        app = self.frame.winfo_toplevel()
        if hasattr(app, "_invoice_editor_dialog"):
            items = td.build_invoice_items(context["trip_ids"], context["service_ids"])
            app._invoice_editor_dialog(customer=customer,
                                       trip_ids=context["trip_ids"],
                                       service_ids=context["service_ids"],
                                       items=items)
        self.refresh()

    def assign_service_to_selected(self):
        trips = self._selected_trip_rows()
        if not trips:
            return

        dialog = tk.Toplevel(self.frame)
        dialog.title("إضافة خدمة إضافية للرحلات المحددة")
        dialog.geometry("760x440")
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(bg=COLOR_BG)
        tk.Label(dialog, text=f"إضافة خدمة إلى {len(trips)} رحلة محددة",
                     font=F_H2, bg=COLOR_BG, fg=COLOR_PRIMARY).pack(fill="x", padx=18, pady=(16, 8))
        tk.Label(dialog, text="أدخل بيانات الخدمة كما في شاشة الخدمات الإضافية، ثم اضغط حفظ وإضافة.",
                 font=F_BODY, bg=COLOR_BG, fg=COLOR_MUTED).pack(fill="x", padx=18, pady=(0, 8))

        form = tk.Frame(dialog, bg=COLOR_CARD)
        form.pack(fill="both", expand=True, padx=18, pady=8)
        first_trip = trips[0]
        values = {
            "company": safe_str(first_trip.get("company", "")),
            "customer": safe_str(first_trip.get("customer", "")),
            "declaration_no": ", ".join(dict.fromkeys(
                safe_str(trip.get("declaration_no", "")).strip()
                for trip in trips
                if safe_str(trip.get("declaration_no", "")).strip()
            )),
            "declaration_trip_no": ", ".join(
                safe_str(trip.get("declaration_trip_no", "")).strip()
                for trip in trips
                if safe_str(trip.get("declaration_trip_no", "")).strip()
            ),
            "service_type": td.SERVICE_TYPES[0],
            "unit": "ساعة",
            "quantity": "1",
            "unit_price": "",
            "total": "0.000",
            "notes": "",
        }
        vars_ = {key: tk.StringVar(value=value) for key, value in values.items()}
        fields = [
            ("declaration_no", "\u0631\u0642\u0645 \u0627\u0644\u0628\u064a\u0627\u0646"),
            ("customer", "\u0627\u0644\u0645\u062e\u0644\u0635"),
            ("company", "\u0627\u0644\u0634\u0631\u0643\u0629"),
            ("declaration_trip_no", "\u0623\u0643\u0648\u0627\u062f \u0627\u0644\u0631\u062d\u0644\u0627\u062a"),
            ("unit", "\u0627\u0644\u0648\u062d\u062f\u0629"),
            ("service_type", "\u0646\u0648\u0639 \u0627\u0644\u062e\u062f\u0645\u0629"),
            ("quantity", "الكمية"),
            ("unit_price", "سعر الوحدة (د.ك)"),
            ("total", "إجمالي السعر (د.ك)"),
            ("customer", "الشركة / المخلص"),
            ("notes", "ملاحظات"),
        ]
        # ترتيب RTL النهائي: المخلص ثم رقم البيان، وإجمالي السعر ثم الملاحظات.
        fields = [
            ("declaration_no", "\u0631\u0642\u0645 \u0627\u0644\u0628\u064a\u0627\u0646"),
            ("customer", "\u0627\u0644\u0645\u062e\u0644\u0635"),
            ("company", "\u0627\u0644\u0634\u0631\u0643\u0629"),
            ("unit", "\u0627\u0644\u0648\u062d\u062f\u0629"),
            ("service_type", "\u0646\u0648\u0639 \u0627\u0644\u062e\u062f\u0645\u0629"),
            ("declaration_trip_no", "\u0623\u0643\u0648\u0627\u062f \u0627\u0644\u0631\u062d\u0644\u0627\u062a"),
            ("total", "\u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u0633\u0639\u0631"),
            ("unit_price", "\u0633\u0639\u0631 \u0627\u0644\u0648\u062d\u062f\u0629"),
            ("quantity", "\u0627\u0644\u0643\u0645\u064a\u0629"),
            ("notes", "\u0645\u0644\u0627\u062d\u0638\u0627\u062a"),
        ]
        for index, (key, label) in enumerate(fields):
                row = index // 3
                col = index % 3
                if key == "notes":
                    col = 2
                cell = tk.Frame(form, bg=COLOR_CARD)
                cell.grid(row=row, column=col, padx=10, pady=9, sticky="ew")
                tk.Label(cell, text=label, font=F_LABEL, bg=COLOR_CARD,
                         fg=COLOR_MUTED, anchor="e").pack(fill="x")
                if key == "service_type":
                    control = ttk.Combobox(cell, textvariable=vars_[key],
                                           values=td.SERVICE_TYPES, state="normal",
                                           font=F_BODY, justify="right")
                    control.pack(fill="x", ipady=3)
                elif key in ("declaration_no", "company", "customer", "declaration_trip_no"):
                    tk.Entry(cell, textvariable=vars_[key], state="readonly", font=F_BODY,
                             justify="right", relief="flat", bd=0,
                             readonlybackground=COLOR_BORDER_LIGHT).pack(fill="x", ipady=4)
                elif key == "unit":
                    control = ttk.Combobox(cell, textvariable=vars_[key],
                                           values=("ساعة", "يوم", "نقلة", "حاوية"), state="normal",
                                           font=F_BODY, justify="right")
                    control.pack(fill="x", ipady=3)
                elif key == "total":
                    tk.Entry(cell, textvariable=vars_[key], state="readonly", font=F_BODY,
                             justify="right", relief="flat", bd=0,
                             readonlybackground=COLOR_BORDER_LIGHT).pack(fill="x", ipady=4)
                else:
                    tk.Entry(cell, textvariable=vars_[key], font=F_BODY,
                             justify="right", relief="flat", bd=0,
                             highlightthickness=2, highlightbackground=COLOR_BORDER,
                             highlightcolor=COLOR_PRIMARY_LIGHT).pack(fill="x", ipady=4)
                for column in range(3):
                    form.grid_columnconfigure(column, weight=1)

                def update_total(*_args):
                    total = td.safe_float(vars_["quantity"].get()) * td.safe_float(vars_["unit_price"].get())
                    vars_["total"].set(f"{total:.3f}")

                vars_["quantity"].trace_add("write", update_total)
                vars_["unit_price"].trace_add("write", update_total)
                update_total()

                def apply():
                    if not vars_["service_type"].get().strip():
                        messagebox.showwarning("تنبيه", "نوع الخدمة مطلوب.", parent=dialog)
                        return
                    try:
                        service = {
                            "date": safe_str(first_trip.get("date", "")),
                            "company": vars_["company"].get().strip(),
                            "customer": vars_["customer"].get().strip(),
                            "declaration_no": vars_["declaration_no"].get().strip(),
                            "declaration_trip_no": vars_["declaration_trip_no"].get().strip(),
                            "service_type": vars_["service_type"].get().strip(),
                            "unit": vars_["unit"].get().strip(),
                            "quantity": vars_["quantity"].get().strip(),
                            "unit_price": vars_["unit_price"].get().strip(),
                            "notes": vars_["notes"].get().strip(),
                        }
                        td.save_service(service)
                        td.assign_service_to_trips(service.get("id"),
                                                   [trip.get("id") for trip in trips])
                        updated_invoice = td.update_invoice_for_service(service.get("id"))
                        app = self.frame.winfo_toplevel()
                        if updated_invoice and hasattr(app, "refresh_invoice_history"):
                            app.refresh_invoice_history()
                    except Exception as exc:
                        messagebox.showerror("خطأ", str(exc), parent=dialog)
                        return
                    dialog.destroy()
                    messagebox.showinfo("تم", f"تم حفظ الخدمة وإضافتها إلى {len(trips)} رحلة.")
                    refresh_related_screens(self.frame)

                buttons = tk.Frame(dialog, bg=COLOR_BG)
                buttons.pack(fill="x", padx=18, pady=(4, 16))
                make_btn(buttons, "حفظ وإضافة", apply, variant="accent").pack(side="right", padx=4)
                make_btn(buttons, "إلغاء", dialog.destroy, variant="secondary").pack(side="right", padx=4)

    def set_today(self):
        self.vars["date"].set(date.today().isoformat())

    def refresh_car_options(self):
        for row in self.batch_rows:
            self._refresh_row_cars(row)

    def refresh_customers_drivers(self):
        drivers = [d["name"] for d in td.load_drivers()]
        internal_drivers = [d["name"] for d in td.load_drivers() if d.get("driver_type", "") == "داخلي"]
        external_drivers = [d["name"] for d in td.load_drivers() if d.get("driver_type", "") == "خارجي"]
        customers = [NO_CUSTOMER] + [c["name"] for c in td.load_customers()]
        companies = [c["name"] for c in td.load_companies()]
        for row in self.batch_rows:
            if "driver" in row["combos"]:
                driver_type = row["vars"]["driver_type"].get().strip()
                if driver_type == "داخلي":
                    row["combos"]["driver"].config(values=internal_drivers)
                elif driver_type == "خارجي":
                    row["combos"]["driver"].config(values=external_drivers)
                else:
                    row["combos"]["driver"].config(values=drivers)
            if "driver_type" in row["combos"]:
                row["combos"]["driver_type"].config(values=["داخلي", "خارجي"])
            if "customer" in row["combos"]:
                row["combos"]["customer"].config(values=customers)
            if "company" in row["combos"]:
                row["combos"]["company"].config(values=companies)
        # قوائم رأس كل بيان (الشركة/العميل) تبقى محدّثة أيضاً.
        for group in self.batch_groups:
            group_combos = group.get("combos", {})
            if "company" in group_combos:
                group_combos["company"].config(values=companies)
            if "customer" in group_combos:
                group_combos["customer"].config(values=customers)

    def refresh_place_options(self):
        for row in self.batch_rows:
            self._on_row_category_change(row)

    def load_selected_into_form(self, row=None):
        if row is None:
            row = self.get_selected_row()
            if not row:
                return
        self.vars["date"].set(safe_str(row.get("date", "")))
        declaration = safe_str(row.get("declaration_no", "")).strip()
        self.batch_declaration_var.set(declaration)
        # اختيار أي رحلة من بيان يحمّل كامل المجموعة (التاريخ + رقم البيان).
        # السجلات القديمة التي لا تحتوي رقم بيان تبقى قابلة للتعديل منفردة.
        selected_rows = [r for r in self._rows
                         if safe_str(r.get("date", "")) == safe_str(row.get("date", ""))
                         and safe_str(r.get("declaration_no", "")).strip() == declaration]
        if declaration and selected_rows:
            for group in self.batch_groups:
                group["frame"].destroy()
            self.batch_groups.clear()
            self.active_batch_group = self._create_batch_group({"date": row.get("date", ""), "declaration_no": declaration})
            for key in ("trip_category", "company", "customer"):
                self.active_batch_group["shared"][key].set(safe_str(row.get(key, "")))
            self.batch_rows.clear()
            for selected in selected_rows:
                data = {key: selected.get(key, "") for key, _label in self._batch_fields}
                for key in self.EXPENSE_FIELDS:
                    data[key] = selected.get(key, "")
                self._add_batch_row(data, trip_id=selected.get("id", ""), group=self.active_batch_group)
            return
        for group in self.batch_groups:
            group["frame"].destroy()
        self.batch_groups.clear()
        self.active_batch_group = self._create_batch_group({"date": row.get("date", ""), "declaration_no": declaration})
        for key in ("trip_category", "company", "customer"):
            self.active_batch_group["shared"][key].set(safe_str(row.get(key, "")))
        self.batch_rows.clear()
        self._add_batch_row({
            "trip_category": row.get("trip_category", ""),
            "direction": row.get("direction", ""),
            "country": row.get("country", ""),
            "driver_type": row.get("driver_type", ""),
            "driver": row.get("driver", ""),
            "car_no": row.get("car_no", ""),
            "customer": row.get("customer", ""),
            "company": row.get("company", "") if row.get("company") is not None else "",
            "declaration_no": row.get("declaration_no", ""),
            "declaration_trip_no": row.get("declaration_trip_no", ""),
            "container_size": row.get("container_size", ""),
            "car_expense_type": row.get("car_expense_type", ""),
            "car_expense_amount": row.get("car_expense_amount", ""),
            "driver_expense": row.get("driver_expense", ""),
            "fee": row.get("fee", ""),
            "holiday_price": row.get("holiday_price", ""),
            "driver_wage": row.get("driver_wage", ""),
                "notes": row.get("notes", ""),
            }, trip_id=row.get("id", ""), group=self.active_batch_group)
 

    def clear_trip_filters(self):
        self.trip_filter_field_var.set("الكل")
        self.trip_filter_value_var.set("")
        self.refresh()

    def _clear_register_filters(self):
        """مسح البحث والفلترة في سجل الرحلات وإعادة عرض كل الصفوف."""
        try:
            self.search_var.set("")
        except Exception as _log_exc: log_exception("_clear_register_filters", _log_exc)
        try:
            self.today_var.set(False)
        except Exception as _log_exc: log_exception("_clear_register_filters", _log_exc)
        self.clear_trip_filters()

    def refresh(self):
        query = (self.search_var.get() or "").strip().lower()
        only_today = self.today_var.get()
        today_iso = date.today().isoformat()
        filter_field = self.trip_filter_field_var.get().strip()
        filter_value = self.trip_filter_value_var.get().strip().lower()
        filter_key = getattr(self, "_trip_filter_labels", {}).get(filter_field, "")
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._rows = self.load_fn()
        self._tree_row_map = {}
        used_iids = set()
        for idx, row in enumerate(self._rows):
            if only_today and str(row.get("date", "")) != today_iso:
                continue
            if filter_key and filter_value and filter_value not in safe_str(row.get(filter_key, "")).lower():
                continue
            hay = " ".join(safe_str(row.get(k, "")) for k, _ in self.fields).lower()
            if query and query not in hay:
                continue
            key_val = row.get(self.key_field, "")
            values = [safe_str(row.get(k, "")) for k, _ in reversed(self.fields)]
            tag = "odd" if idx % 2 else ""
            base_iid = str(key_val).strip() or "row"
            iid = base_iid
            suffix = 2
            while iid in used_iids:
                iid = f"{base_iid}_{suffix}"
                suffix += 1
            used_iids.add(iid)
            self._tree_row_map[iid] = row
            self.tree.insert("", "end", iid=iid, values=values, tags=(tag,) if tag else ())
