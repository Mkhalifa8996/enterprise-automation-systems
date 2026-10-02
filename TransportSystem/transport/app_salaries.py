# -*- coding: utf-8 -*-
"""تبويب الرواتب وحاسبة الراتب التفصيلية."""

import html, os, tempfile, traceback, webbrowser
from datetime import date
from tkinter import messagebox
from datetime import timedelta
import tkinter as tk
from tkinter import ttk
from . import data as td
from .app_config import COLOR_BG, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_CARD, COLOR_DANGER, COLOR_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_SUCCESS, COLOR_TEXT, F_BODY, F_BOLD, F_LABEL
from .print_theme import PRINT_GOLD, PRINT_INK, PRINT_LINE, PRINT_MUTED, PRINT_NAVY, PRINT_ROW_ALT, PRINT_TOTAL_BG, apply_a4_print_layout
from .ui_widgets import apply_table_style, card_frame, center_dialog, make_btn, modern_entry, scrollable_pane, tooltip
from .driver_links import bind_driver_type_cascade
from .ui_dialogs import date_input
from .print_statement import generate_and_open_summary_print
from .ui_helpers import get_trip_place_options, log_exception, safe_str
from .ui_text_edit import refresh_related_screens

class AppSalariesMixin:
    """تبويب الرواتب وحاسبة الراتب التفصيلية."""

    # ---------------- شاشة الرواتب ----------------
    def _build_salaries_tab(self):
        frame, content = scrollable_pane(self.pages_area)
        self.salary_editing_id = None
        self._salary_paid_value = "لا"
        self.salary_search_var = tk.StringVar()
        self.salary_driver_filter_var = tk.StringVar(value="الكل")
        self.salary_month_filter_var = tk.StringVar()
        # فترة افتراضية (الشهر الحالي) حتى تعمل الشاشة فور فتحها؛ فكانت
        # الحقول تبدأ فارغة فيتوقف الحساب early وتظهر كل القيم فارغة.
        self._salary_default_from = date.today().replace(day=1).isoformat()
        self._salary_default_to = date.today().isoformat()

        salaries_notebook = ttk.Notebook(content)
        salaries_notebook.pack(fill="both", expand=True, padx=12, pady=12)
        self._salaries_notebook = salaries_notebook
        calc_frame = tk.Frame(salaries_notebook, bg=COLOR_BG)
        history_frame = tk.Frame(salaries_notebook, bg=COLOR_BG)
        salaries_notebook.add(calc_frame, text="حساب راتب السائق")
        salaries_notebook.add(history_frame, text="سجل الرواتب")

        box = card_frame(calc_frame, "إعداد راتب شهري لسائق")
        box.pack(fill="x", padx=18, pady=(18, 8))
        form = tk.Frame(box.body, bg=COLOR_CARD)
        form.pack(fill="x", padx=18, pady=(0, 8))

        self.sal_vars = {}
        # حقل «العمولات» و«السلف» حُذفا من النموذج: العمولة تُحسب من سجل
        # السائق وعدد رحلاته، والسلفة مُدرجة أصلاً ضمن «مصاريف السائق» في لوحة
        # الحصر، فكانا يظهران مرتين ويُلخبط المستخدم أيّهما هو المحسوب. ولا
        # يعرضهما «سجل الرواتب» أيضاً حتى تتطابق الشاشتان.
        self.sal_vars["commission_total"] = tk.StringVar(value="0.000")
        self.sal_vars["advances"] = tk.StringVar(value="0.000")
        # ثلاثية السائق بترتيبها المطلوب: نوع السائق ← السائق ← السيارة، وكل
        # الحقول في صف واحد. العرض يأتي من حجم كل حقل نفسه (عدد المحارف)،
        # والوزن يساوي واحداً لكل عمود فتُوزَّع المساحة الفائضة بالتساوي.
        # كان الضبط بالبكسل الثابت يجعل الحقول الطويلة تتجاوز البطاقة، فيظهر
        # فراغ أمام أول حقل. الآن العرض من حجم الحقل نفسه والوزن متساوٍ.
        SALARY_FORM_ROW = [
            ("driver_type", "نوع السائق"),
            ("driver", "السائق"),
            ("car_no", "السيارة"),
            ("salary_type", "طريقة الحساب"),
            ("start_date", "من"),
            ("end_date", "إلى"),
            ("base_salary", "الراتب الأساسي"),
            # بدل «الخصومات»: يعرض المرحّل من الشهر السابق فقط للقراءة،
            # فالمحاسب يعرف هل عليه للسائق أو عليه السائق قبل الحفظ.
            ("carry_display", "مرحّل من الشهر الماضي"),
            ("settled_amount", "المسدّد"),
            ("notes", "ملاحظات"),
            ("holiday", None),
            ("clear", None),
        ]
        form_rows = [[field for field in SALARY_FORM_ROW]]
        form_fields = [field for field in SALARY_FORM_ROW if field[0]]
        self.salary_table_fields = [("id", "الرقم"), ("driver", "السائق"), ("car_no", "السيارة"), ("month", "الشهر"), ("salary_type", "طريقة الحساب"),
                                    ("base_salary", "الأساسي"), ("trip_revenue", "إيراد الرحلات"),
                                    ("holiday_revenue", "إيراد العطل"), ("driver_wages", "أجرة الرحلات"),
                                    ("car_expenses", "مصاريف السيارة"), ("driver_expenses", "مصاريف السائق"),
                                    ("carry_in", "مرحّل سابق"), ("net_salary", "الصافي"),
                                    ("balance_state", "الحالة"), ("paid", "مدفوع؟")]
        # العروض بالمحارف أصغر ما يمكن مع بقاء الأرقام والأسماء مقروءة.
        field_widths = {
            "driver": 11, "car_no": 8, "start_date": 10, "end_date": 10,
            "base_salary": 8, "salary_type": 12, "carry_display": 10, "notes": 9,
            "settled_amount": 8, "driver_type": 8,
        }
        # نحسب موضع كل خانة مرة واحدة ونستعمله في العرض والأوزان معاً، فلا
        # يتكرر حساب العمود في موضعين فيختلفان. الشبكة من اليسار لليمين،
        # فنبدأ العدّ من أقصى اليمين حتى يبقى ترتيب الحقول من اليمين لليسار.
        SALARY_FORM_COLUMNS = len(SALARY_FORM_ROW)
        layout = []
        for row_no, row_def in enumerate(form_rows):
            col = SALARY_FORM_COLUMNS
            for key, label in row_def:
                if not key:
                    continue
                col -= 1
                layout.append((row_no, col, key, label))
        # وزن لكل عمود بحسب عرضه المطلوب: يأخذ كل عمود حصّته من المساحة
        # الفائضة، فيمتلئ الصف حتى حافة البطاقة بلا فراغ على اليمين وبلا
        # تداخل بين الحقول، مع بقاء التاريخات أعرض من الأرقام.
        column_slack = {key: field_widths.get(key, 8) for key, _label in SALARY_FORM_ROW
                        if key in field_widths}
        for c in range(SALARY_FORM_COLUMNS):
            key = SALARY_FORM_ROW[SALARY_FORM_COLUMNS - 1 - c][0]
            form.grid_columnconfigure(c, weight=max(1, column_slack.get(key, 8)))
        self.sal_holiday_var = tk.BooleanVar(value=True)
        self.sal_holiday_var.trace_add("write", lambda *_: self._auto_calculate_salary())
        for row_no, col, key, label in layout:
            cell = tk.Frame(form, bg=COLOR_CARD)
            cell.grid(row=row_no, column=col, padx=2, pady=7, sticky="ew")
            if label:
                tk.Label(cell, text=label, font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED,
                         anchor="e").pack(fill="x", pady=(0, 3))
            var = tk.StringVar()
            if key == "driver_type":
                entry = ttk.Combobox(cell, textvariable=var, font=F_BODY, justify="right",
                                     state="readonly", width=field_widths["driver_type"])
                entry.config(values=[""] + list(td.DRIVER_TYPES))
                entry.pack(fill="x", ipady=4)
                self.sal_driver_type_combo = entry
                self.sal_vars["driver_type"] = var
            elif key == "driver":
                entry = ttk.Combobox(cell, textvariable=var, font=F_BODY, justify="right", state="normal", width=field_widths.get("driver", 10))
                entry.bind("<<ComboboxSelected>>", lambda e: self._on_driver_changed())
                entry.pack(fill="x", ipady=4)
                self.sal_driver_combo = entry
                self.sal_vars["driver"] = var
                # نتابع المتغير لا حدث القائمة فقط، فتواءم الفترة وتُحسب
                # القيم أيضاً عند كتابة اسم السائق يدوياً.
                var.trace_add("write", lambda *_: self._salary_driver_changed())
            elif key == "car_no":
                entry = ttk.Combobox(cell, textvariable=var, font=F_BODY, justify="right", state="normal", width=field_widths.get("car_no", 8))
                entry.config(values=[v["car_no"] for v in td.load_vehicles()])
                entry.bind("<<ComboboxSelected>>", lambda e: self._on_car_changed())
                entry.pack(fill="x", ipady=4)
                self.sal_car_combo = entry
                self.sal_vars["car_no"] = var
                var.trace_add("write", lambda *_: self._auto_calculate_salary())
            elif key == "salary_type":
                entry = ttk.Combobox(cell, textvariable=var, font=F_BODY, justify="right", state="normal", width=field_widths.get("salary_type", 18))
                # كل طرق الحساب المعتمدة، ومنها «إيراد السيارة» التي تُضبط تلقائياً
                # للسائقين العاملين بقاعدة revenue_share (كانت غائبة عن القائمة).
                entry.config(values=list(td.SALARY_METHOD_LABELS))
                entry.bind("<<ComboboxSelected>>", lambda e: self._auto_calculate_salary())
                entry.pack(fill="x", ipady=4)
                self.sal_salary_type_combo = entry
                self.sal_vars["salary_type"] = var
                var.trace_add("write", lambda *_: self._auto_calculate_salary())
            elif key in ("start_date", "end_date"):
                date_input(cell, var, shrink=True, width=field_widths.get(key, 8))
                self.sal_vars[key] = var
                var.trace_add("write", lambda *_: self._auto_fill_month())
                var.trace_add("write", lambda *_: self._auto_calculate_salary())
            elif key == "holiday":
                # النص مختصر عمداً: العنوان الطويل كان يفرض عرضاً أدنى كبيراً
                # على العمود فلا يتّسع الصف كاملاً في نافذة واحدة.
                tk.Checkbutton(cell, text="إضافة العطل", variable=self.sal_holiday_var,
                               bg=COLOR_CARD, font=F_LABEL, anchor="center").pack(
                    anchor="center", padx=1)
            elif key == "carry_display":
                # حقل للقراءة فقط: يعرض المرحّل من الشهر السابق مع اتجاهه
                # (متبقٍّ للسائق أو عليه السائق) ولا يقبل الكتابة.
                self.sal_vars["carry_display"] = var
                var.set("0.000")
                readout = tk.Entry(cell, textvariable=var, font=F_BODY, justify="right",
                                   relief="flat", bd=0, highlightthickness=2,
                                   highlightbackground=COLOR_BORDER,
                                   readonlybackground=COLOR_BORDER_LIGHT,
                                   foreground=COLOR_PRIMARY,
                                   width=field_widths.get("carry_display", 10))
                readout.configure(state="readonly")
                readout.pack(fill="x", ipady=4)
                tooltip(readout, "ما تبقى للسائق أو عليه من رواتب الشهور السابقة")
            elif key == "notes":
                entry = tk.Entry(cell, textvariable=var, font=F_BODY, justify="right",
                                 relief="flat", bd=0, highlightthickness=2,
                                 highlightbackground=COLOR_BORDER,
                                 highlightcolor=COLOR_PRIMARY_LIGHT,
                                 insertbackground=COLOR_TEXT, width=field_widths.get("notes", 16))
                entry.pack(fill="x", ipady=4)
                self.sal_vars["notes"] = var
                var.trace_add("write", lambda *_: self._auto_calculate_salary())
            elif key == "clear":
                make_btn(cell, "مسح الحقول", self.clear_salary_form, variant="secondary").pack(anchor="e", pady=4)
            else:
                width = field_widths.get(key)
                entry = tk.Entry(cell, textvariable=var, font=F_BODY, justify="right",
                                 relief="flat", bd=0, highlightthickness=2,
                                 highlightbackground=COLOR_BORDER,
                                 highlightcolor=COLOR_PRIMARY_LIGHT,
                                 insertbackground=COLOR_TEXT, width=width)
                entry.pack(fill="x", ipady=4)
                self.sal_vars[key] = var
                var.trace_add("write", lambda *_: self._auto_calculate_salary())
        self._salary_form = form
        # الربط المتسلسل: نوع السائق يصفّي قائمة السائقين، والسائق يصفّي
        # قائمة السيارات ويُظهر له سيارته فقط.
        bind_driver_type_cascade(
            {"driver_type": self.sal_vars["driver_type"],
             "driver": self.sal_vars["driver"],
             "car_no": self.sal_vars["car_no"]},
            {"driver": self.sal_driver_combo, "car_no": self.sal_car_combo},
            get_day=lambda: self.sal_vars["start_date"].get().strip())
        self.sal_vars["salary_type"].set("رحلة")
        # الحقول الرقمية تبدأ بصفر صريح بدل الفراغ، فيظهر الرقم دائماً ولا
        # يوهم المستخدم بأن الحقل معطّل أو أن الراتب غير محسوب.
        for _num_key in ("base_salary", "settled_amount"):
            if _num_key in self.sal_vars and not self.sal_vars[_num_key].get().strip():
                self.sal_vars[_num_key].set("0.000")

        # شرح طريقة الحساب: كان حقل «طريقة الحساب» بلا أي بيان يوضّح الكيفية،
        # فتعذّر معرفة مصدر الرقم. هذا السطر يظهر الوصف ويتبع تغيير الطريقة.
        method_hint = tk.Frame(box.body, bg=COLOR_CARD)
        method_hint.pack(fill="x", padx=18, pady=(0, 6), anchor="e")
        self.salary_method_hint = tk.Label(
        method_hint, text=td.salary_method_description("رحلة"),
        font=F_LABEL, bg=COLOR_CARD, fg=COLOR_PRIMARY, anchor="e",
        justify="right", wraplength=760)
        self.salary_method_hint.pack(side="right")
        self._refresh_salary_method_hint()
        # نضبط الفترة الافتراضية بعد إنشاء الحقول، فتُحسب القيم فور فتح
        # الشاشة بدل تركها فارغة حتى يختار المستخدم سائقاً من القائمة.
        self.sal_vars["start_date"].set(self._salary_default_from)
        self.sal_vars["end_date"].set(self._salary_default_to)

        self.salary_calc_container = tk.Frame(calc_frame, bg=COLOR_BG)
        self.salary_calc_container.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        list_box = card_frame(history_frame, "سجل الرواتب")
        list_box.pack(fill="both", expand=True, padx=18, pady=(8, 18))

        salary_filters = tk.Frame(list_box.body, bg=COLOR_CARD)
        salary_filters.pack(fill="x", padx=18, pady=(0, 10), anchor="e")
        tk.Label(salary_filters, text="بحث", font=F_LABEL, bg=COLOR_CARD,
         fg=COLOR_MUTED).pack(side="right", padx=(8, 3))
        tk.Entry(salary_filters, textvariable=self.salary_search_var, font=F_BODY,
         justify="right", width=12).pack(side="right", padx=3)
        tk.Label(salary_filters, text="السائق", font=F_LABEL, bg=COLOR_CARD,
         fg=COLOR_MUTED).pack(side="right", padx=(10, 3))
        self.salary_driver_filter_combo = ttk.Combobox(
        salary_filters, textvariable=self.salary_driver_filter_var, values=["الكل"],
        state="readonly", width=16, font=F_BODY, justify="right")
        self.salary_driver_filter_combo.pack(side="right", padx=3)
        tk.Label(salary_filters, text="الشهر", font=F_LABEL, bg=COLOR_CARD,
         fg=COLOR_MUTED).pack(side="right", padx=(10, 3))
        tk.Entry(salary_filters, textvariable=self.salary_month_filter_var, font=F_BODY,
         justify="right", width=10).pack(side="right", padx=3)
        make_btn(salary_filters, "مسح الفلاتر", self.clear_salary_filters,
         variant="secondary", padx=6, pady=4).pack(side="right", padx=4)
        self.salary_search_var.trace_add("write", lambda *_: self.refresh_salary_list())
        self.salary_month_filter_var.trace_add("write", lambda *_: self.refresh_salary_list())
        self.salary_driver_filter_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_salary_list())

        table_wrap = tk.Frame(list_box.body, bg=COLOR_CARD)
        table_wrap.pack(fill="both", expand=True, padx=18)
        # Keep the table aligned with the salary input form. Derived fields
        # (net salary/paid) are stored separately and are not input cells.
        # Treeview places its first column on the left; reverse the visual
        # order so the first logical field is on the right in Arabic.
        cols = tuple(key for key, _label in reversed(self.salary_table_fields))
        # تطابق أعمدة السجل حقول نموذج الإدخال: «السلف» و«العمولات» حُذفا
        # من الاثنين، فلا يبقى سبب لعرضهما في السجل وحده.
        headers = {"id": "الرقم", "driver": "السائق", "car_no": "رقم السيارة", "month": "الشهر", "salary_type": "طريقة الحساب",
           "base_salary": "الأساسي", "trip_revenue": "إيراد الرحلات",
           "holiday_revenue": "إيراد العطل", "driver_wages": "أجرة الرحلات",
           "car_expenses": "مصاريف السيارة", "driver_expenses": "مصاريف السائق",
           "carry_in": "مرحّل سابق", "net_salary": "الصافي",
           "balance_state": "حالة الرصيد", "paid": "مدفوع؟"}
        widths = {"id": 50, "driver": 120, "car_no": 90, "month": 90, "salary_type": 130,
          "base_salary": 90, "trip_revenue": 100, "holiday_revenue": 100,
          "driver_wages": 100, "car_expenses": 105, "driver_expenses": 105,
          "carry_in": 90, "net_salary": 90, "balance_state": 80, "paid": 80}
        anchors = {"id": "center", "driver": "e", "car_no": "e", "month": "center", "salary_type": "e",
           "base_salary": "e", "trip_revenue": "e", "holiday_revenue": "e",
           "driver_wages": "e", "car_expenses": "e", "driver_expenses": "e",
           "carry_in": "center", "net_salary": "e", "balance_state": "center", "paid": "center"}
        self.sal_tree = ttk.Treeview(table_wrap, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.sal_tree.heading(c, text=headers[c])
            self.sal_tree.column(c, anchor=anchors.get(c, "center"),
                                 width=widths.get(c, 95), stretch=True)
        self.sal_tree.pack(fill="both", expand=True, pady=4)
        apply_table_style(self.sal_tree)
        self.sal_tree.bind("<Double-1>", lambda e: self.load_salary_for_edit())
        self.sal_tree.bind("<<TreeviewSelect>>", lambda e: self._show_salary_detail())
        self.sal_tree.bind("<Configure>", lambda e: self._auto_size_tree(self.sal_tree, cols))

        # تفاصيل السجل المحدد: جدول بعمودين (البيان والقيمة) بدل نص واحد
        # طويل، فيقرأ كل بند في سطر مستقل ويسهل найجه.
        self.salary_detail_title = tk.StringVar(value="اختر سجل راتب لعرض التفاصيل")
        self.salary_detail_vars = {
            "driver": tk.StringVar(value="—"), "car_no": tk.StringVar(value="—"),
            "month": tk.StringVar(value="—"), "salary_type": tk.StringVar(value="—"),
            "base_salary": tk.StringVar(value="—"), "trip_revenue": tk.StringVar(value="—"),
            "holiday_revenue": tk.StringVar(value="—"), "driver_wages": tk.StringVar(value="—"),
            "car_expenses": tk.StringVar(value="—"), "driver_expenses": tk.StringVar(value="—"),
            "carry_in": tk.StringVar(value="—"), "net_salary": tk.StringVar(value="—"),
            "balance_state": tk.StringVar(value="—"), "paid": tk.StringVar(value="—"),
            "notes": tk.StringVar(value=""),
        }
        self.salary_detail_labels = {
            "driver": "السائق", "car_no": "السيارة", "month": "الشهر",
            "salary_type": "طريقة الحساب", "base_salary": "الراتب الأساسي",
            "trip_revenue": "إيراد الرحلات", "holiday_revenue": "إيراد العطل",
            "driver_wages": "أجرة الرحلات", "car_expenses": "مصاريف السيارة",
            "driver_expenses": "مصاريف السائق", "carry_in": "مرحّل من الشهر الماضي",
            "net_salary": "الصافي", "balance_state": "حالة الرصيد",
            "paid": "مدفوع؟", "notes": "ملاحظات",
        }
        detail_frame = tk.Frame(list_box.body, bg=COLOR_BG)
        detail_frame.pack(fill="x", padx=18, pady=(10, 4))
        detail_frame.grid_columnconfigure(0, weight=1, uniform="saldet")
        detail_frame.grid_columnconfigure(1, weight=1, uniform="saldet")
        detail_frame.grid_columnconfigure(2, weight=1, uniform="saldet")
        detail_frame.grid_columnconfigure(3, weight=1, uniform="saldet")
        tk.Label(detail_frame, textvariable=self.salary_detail_title, font=F_BOLD,
                 bg=COLOR_BG, fg=COLOR_PRIMARY, anchor="e").grid(
            row=0, column=0, columnspan=4, sticky="ew", pady=(0, 6))
        # كل حقل فيربع، عمودان لكل صف،فالبيان على اليمين وقيمته إلى يساره.
        self._salary_detail_cells = {}
        for index, key in enumerate(self.salary_detail_vars):
            row_no = index // 2 + 1
            pair = (index % 2) * 2
            cell = tk.Frame(detail_frame, bg=COLOR_BG)
            cell.grid(row=row_no, column=pair, columnspan=2, sticky="ew", pady=1)
            tk.Label(cell, text=self.salary_detail_labels[key], font=F_LABEL,
                     bg=COLOR_BG, fg=COLOR_MUTED, anchor="e").pack(side="right")
            value_label = tk.Label(cell, textvariable=self.salary_detail_vars[key],
                                   font=F_BOLD, bg=COLOR_BG, fg=COLOR_TEXT,
                                   anchor="e")
            value_label.pack(side="right", padx=(10, 6))
            self._salary_detail_cells[key] = value_label

        btns2 = tk.Frame(list_box.body, bg=COLOR_CARD)
        btns2.pack(fill="x", padx=18, pady=(8, 16), anchor="e")
        make_btn(btns2, "حساب رواتب جميع السائقين", self.recalculate_all_salaries,
         variant="accent").pack(side="right", padx=4)
        make_btn(btns2, "حذف السجل المحدد", self.delete_salary_row, variant="danger").pack(side="right", padx=4)
        make_btn(btns2, "تعديل المحدد", self.load_salary_for_edit, variant="secondary").pack(side="right", padx=4)
        make_btn(btns2, "تبديل حالة الدفع", self.toggle_salary_paid, variant="secondary").pack(side="right", padx=4)
        make_btn(btns2, "عرض تفاصيل الراتب", self.view_salary_details, variant="secondary").pack(side="right", padx=4)
        make_btn(btns2, "طباعة المحدد", self.print_selected_salary, variant="secondary").pack(side="right", padx=4)
        make_btn(btns2, "طباعة ملخص الرواتب", self.print_salaries_summary, variant="secondary").pack(side="right", padx=4)

        def refresh_salaries_page():
            self.refresh_salary_driver_combo()
            self.refresh_salary_list()
            # إذا تغيّرت بيانات مرتبطة أثناء وجود المستخدم في شاشة أخرى
            # نعيد بناء حصر الراتب المفتوح الآن.
            if getattr(self, "_salary_calc_dirty", False):
                self.refresh_salary_calculator()

        self.register_page("salaries", frame, refreshers=[refresh_salaries_page],
                           canvas=frame.canvas)

    def refresh_salary_driver_combo(self):
        self.sal_driver_combo.config(values=[d["name"] for d in td.load_drivers()])
        if hasattr(self, "sal_car_combo"):
            self.sal_car_combo.config(values=[v.get("car_no", "") for v in td.load_vehicles()])

    # ---------------- تحديث حصر الراتب عند تغيّر بيانات الشاشات الأخرى ----------------
    def mark_salary_calculator_dirty(self):
        """يُعلِم شاشة الرواتب بأن البيانات المرتبطة تغيّرت."""
        self._salary_calc_dirty = True
        if getattr(self, "current_page", "") == "salaries":
            self.refresh_salary_calculator()

    def refresh_salary_calculator(self):
        """إعادة بناء حصر الراتب المعروض حالياً إن كان صالحاً."""
        redraw = getattr(self, "_salary_calc_redraw", None)
        if not callable(redraw):
            self._salary_calc_dirty = False
            return
        tree = getattr(self, "_salary_trip_tree", None)
        try:
            if tree is None or not tree.winfo_exists():
                self._salary_calc_redraw = None
                self._salary_calc_dirty = False
                return
        except tk.TclError:
            self._salary_calc_redraw = None
            self._salary_calc_dirty = False
            return
        # لا نعيد الحساب إلا إذا كان النموذج ما زال يعرض نفس السائق والفترة،
        # حتى لا نستخدم بيانات سائق قديم بعد مسح الحقول أو تغييرها.
        driver = self.sal_vars["driver"].get().strip()
        start = self.sal_vars.get("start_date", tk.StringVar()).get().strip()
        end = self.sal_vars.get("end_date", tk.StringVar()).get().strip()
        context = getattr(self, "_salary_calc_context", {}) or {}
        if not driver or not start or not end or driver != context.get("driver"):
            self._salary_calc_dirty = False
            return
        self._salary_calc_dirty = False
        try:
            redraw()
        except tk.TclError:
            self._salary_calc_redraw = None

    # ---------------- تعديل الرحلات من داخل شاشة الرواتب ----------------
    def salary_edit_selected_trip(self, tree=None):
        """تعديل رحلة مختارة من جدول حصر الراتب مع تحديث سجل الرحلات."""
        tree = tree if tree is not None else getattr(self, "_salary_trip_tree", None)
        if tree is None:
            return
        try:
            if not tree.winfo_exists():
                return
        except tk.TclError:
            return
        selection = tree.selection()
        if not selection:
            messagebox.showinfo("تنبيه", "الرجاء اختيار رحلة من جدول الرحلات أولاً.")
            return
        tags = tree.item(selection[0], "tags")
        trip_id = safe_str(tags[0]).strip() if tags else ""
        trip = next((row for row in td.load_trips()
                     if safe_str(row.get("id", "")).strip() == trip_id), None)
        if not trip:
            messagebox.showwarning("تنبيه", "لم يتم العثور على هذه الرحلة في سجل الرحلات.")
            return
        self._open_salary_trip_editor(trip)

    def _open_salary_trip_editor(self, trip):
        """نافذة تعديل رحلة: تحفظ التغيير في سجل الرحلات وتحدّث الشاشات المرتبطة."""
        editable_fields = [
            ("fee", "السعر (د.ك)"),
            ("holiday_price", "سعر العطلة (د.ك)"),
            ("driver_wage", "أجرة السائق (د.ك)"),
            ("driver_commission", "عمولة السائق (د.ك)"),
            ("car_expense_amount", "مصاريف السيارة (د.ك)"),
            ("driver_expense", "مصاريف السائق (د.ك)"),
            ("date", "التاريخ"),
            ("driver", "السائق"),
            ("car_no", "رقم السيارة"),
            ("customer", "العميل"),
            ("company", "الشركة"),
            ("direction", "مكان التحميل"),
            ("country", "مكان التنزيل"),
            ("container_size", "حجم الحاوية"),
            ("declaration_no", "رقم البيان"),
            ("notes", "ملاحظات"),
        ]
        numeric_keys = {"fee", "holiday_price", "driver_wage", "driver_commission",
                        "car_expense_amount", "driver_expense"}
        labels = dict(editable_fields)
        category = safe_str(trip.get("trip_category", "")).strip()
        place_options = get_trip_place_options(category)
        combo_values = {
            "driver": [d.get("name", "") for d in td.load_drivers() if d.get("name", "")],
            "car_no": [v.get("car_no", "") for v in td.load_vehicles() if v.get("car_no", "")],
            "customer": [c.get("name", "") for c in td.load_customers() if c.get("name", "")],
            "company": [c.get("name", "") for c in td.load_companies() if c.get("name", "")],
            "direction": td.DIRECTIONS_BY_CATEGORY.get(category, td.INTERNAL_DIRECTIONS),
            "country": place_options,
        }

        dialog = tk.Toplevel(self)
        dialog.title(f"تعديل الرحلة رقم {safe_str(trip.get('id', ''))}")
        dialog.configure(bg=COLOR_BG)
        dialog.transient(self)
        dialog.grab_set()
        tk.Label(dialog, text="تعديل بيانات الرحلة — يُحدَّث سجل الرحلات وشاشة يومية السيارات تلقائياً.",
                 font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED, anchor="e").pack(fill="x", padx=18, pady=(14, 0))
        body = tk.Frame(dialog, bg=COLOR_BG)
        body.pack(fill="both", expand=True, padx=14, pady=(8, 4))
        edit_vars = {}
        columns = 2
        for index, (key, label) in enumerate(editable_fields):
            row_no, col = divmod(index, columns)
            cell = tk.Frame(body, bg=COLOR_BG)
            cell.grid(row=row_no, column=columns - 1 - col, padx=8, pady=6, sticky="ew")
            tk.Label(cell, text=label, font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED,
                     anchor="e").pack(fill="x", pady=(0, 3))
            var = tk.StringVar(value=safe_str(trip.get(key, "")))
            edit_vars[key] = var
            if key == "date":
                date_input(cell, var, width=14)
            elif key in combo_values:
                ttk.Combobox(cell, textvariable=var, values=combo_values[key], font=F_BODY,
                             justify="right", width=20).pack(fill="x", ipady=3)
            else:
                modern_entry(cell, var, width=20)
        for col in range(columns):
            body.grid_columnconfigure(col, weight=1)

    def save_changes():
            data = dict(trip)
            for key, var in edit_vars.items():
                value = var.get().strip()
                if key in numeric_keys:
                    if value:
                        try:
                            value = round(float(value.replace(",", "")), 3)
                        except ValueError:
                            messagebox.showwarning(
                                "تنبيه", f"القيمة في حقل «{labels[key]}» يجب أن تكون رقماً.",
                                parent=dialog)
                            return
                    else:
                        value = ""
                elif key == "date" and value:
                    try:
                        date.fromisoformat(value)
                    except ValueError:
                        messagebox.showwarning("تنبيه", "أدخل التاريخ بصيغة YYYY-MM-DD.", parent=dialog)
                        return
                data[key] = value
            try:
                td.save_trip(data, editing_id=trip.get("id"))
            except Exception as exc:  # أخطاء الحفظ تُعرض للمستخدم بدل إسقاط النافذة
                messagebox.showerror("خطأ", f"تعذّر حفظ الرحلة:\n{exc}", parent=dialog)
                return
            dialog.destroy()
            # التعديل يخصّ سجل الرحلات نفسه، لذلك تُحدَّث كل الشاشات المرتبطة.
            self.refresh_linked_data()
            messagebox.showinfo("تم", "تم تحديث الرحلة في سجل الرحلات.")

            buttons = tk.Frame(dialog, bg=COLOR_BG)
            buttons.pack(fill="x", padx=18, pady=(4, 14))
            make_btn(buttons, "حفظ التعديلات", save_changes, variant="accent").pack(side="right", padx=4)
            make_btn(buttons, "إلغاء", dialog.destroy, variant="secondary").pack(side="right", padx=4)

    # ---------------- تعديلات بنود المصروفات (محلية لشاشة الرواتب) ----------------
    def salary_expense_override(self, record):
        """يعيد صف المصروف بعد تطبيق التعديل المحلي الخاص بشاشة الرواتب."""
        overrides = getattr(self, "_salary_expense_overrides", {})
        override = overrides.get(safe_str(record.get("id", "")).strip())
        if not override:
            return record
        merged = dict(record)
        merged.update(override)
        merged["_salary_override"] = True
        return merged

    def set_salary_expense_override(self, record_id, values):
        record_id = safe_str(record_id).strip()
        if not record_id:
            return False
        if not hasattr(self, "_salary_expense_overrides"):
            self._salary_expense_overrides = {}
        self._salary_expense_overrides[record_id] = values
        return True

    def clear_salary_expense_override(self, record_id=None):
        overrides = getattr(self, "_salary_expense_overrides", {})
        if record_id is None:
            overrides.clear()
        else:
            overrides.pop(safe_str(record_id).strip(), None)

    def _auto_fill_month(self, *args):
        driver = self.sal_vars["driver"].get().strip()
        if not driver:
            return
        start = self.sal_vars.get("start_date", tk.StringVar()).get().strip()
        end = self.sal_vars.get("end_date", tk.StringVar()).get().strip()
        if start and end:
            return
        try:
            year = int(start[:4]) if len(start) >= 4 else date.today().year
            month = int(start[5:7]) if len(start) >= 7 else date.today().month
        except ValueError:
            year, month = date.today().year, date.today().month
        first = date(year, month, 1)
        if month == 12:
            last = date(year, 12, 31)
        else:
            last = date(year, month + 1, 1) - timedelta(days=1)
        self.sal_vars["start_date"].set(first.isoformat())
        self.sal_vars["end_date"].set(last.isoformat())

    def _salary_align_period(self, driver_name):
        """يوائم الفترة مع بيانات السائق: إن كانت الفترة الحالية بلا رحلات له
        ننقلها إلى آخر شهر مسجّل لديه، حتى لا تظهر الشاشة فارغة بلا سبب."""
        driver_name = str(driver_name or "").strip()
        start_date = self.sal_vars.get("start_date", tk.StringVar()).get().strip()
        end_date = self.sal_vars.get("end_date", tk.StringVar()).get().strip()
        if not start_date or not end_date:
            today = date.today()
            self.sal_vars["start_date"].set(today.replace(day=1).isoformat())
            self.sal_vars["end_date"].set(today.isoformat())
            start_date = self.sal_vars["start_date"].get().strip()
            end_date = self.sal_vars["end_date"].get().strip()
        if not driver_name:
            return
        driver_trips = [
            t for t in td.load_trips()
            if td._normalized_driver_name(t.get("driver")) == td._normalized_driver_name(driver_name)
        ]
        if not driver_trips or any(start_date <= str(t.get("date", "")) <= end_date
                                   for t in driver_trips):
            return
        months = [str(t.get("date", ""))[:7] for t in driver_trips if t.get("date")]
        try:
            latest_month = max(months)
            year, month_no = map(int, latest_month.split("-"))
            first = date(year, month_no, 1)
            last = date(year + (month_no == 12),
                        1 if month_no == 12 else month_no + 1, 1) - timedelta(days=1)
            self.sal_vars["start_date"].set(first.isoformat())
            self.sal_vars["end_date"].set(last.isoformat())
        except (ValueError, TypeError) as exc:
            log_exception("_salary_align_period", exc)

    def _salary_sync_car(self, driver_name):
        """يملأ حقل «السيارة» بسيارات السائق فقط (تكليفات السائقين أولاً).

        كان يقرأ حقل السائق من جدول السيارات وحده، فيفقد سيارة السائق المكلَّف
        بها من «تكليفات السائقين» ويُفرغ القائمة. صار يستعمل `cars_for_driver`
        نفسها التي تستخدمها بقية الشاشات، فتتطابق النتائج في كل مكان.
        """
        driver_name = str(driver_name or "").strip()
        combo = getattr(self, "sal_car_combo", None)
        if combo is None:
            return
        if not driver_name:
            # بلا سائق لا يعود سبب لتقييد السيارات، فتعود كل السيارات ظاهرة.
            try:
                combo.config(
                    values=[str(v.get("car_no", "")).strip()
                            for v in td.load_vehicles()
                            if str(v.get("car_no", "")).strip()])
            except tk.TclError as exc:
                log_exception("تحديث قائمة السيارات", exc)
            self.sal_vars["car_no"].set("")
            return
        driver_cars = td.cars_for_driver(
            driver_name, self.sal_vars.get("start_date", tk.StringVar()).get().strip())
        try:
            combo.config(values=driver_cars)
        except tk.TclError as exc:
            log_exception("تحديث قائمة السيارات", exc)
        current = self.sal_vars["car_no"].get().strip()
        if current and current in driver_cars:
            pass
        else:
            self.sal_vars["car_no"].set(
                td.car_for_driver(driver_name) or (driver_cars[0] if driver_cars else ""))

    def _salary_driver_changed(self):
        """يتبع تغيير اسم السائق (بالكتابة أو بالاختيار) فيواءم الفترة ويحسب."""
        driver_name = self.sal_vars["driver"].get().strip()
        self._salary_sync_car(driver_name)
        self._salary_align_period(driver_name)
        self._auto_calculate_salary()
        # نفتح لوحة الحاسبة أيضاً عند الكتابة، لا عند اختيار القائمة فقط،
        # وإلا بقيت المنطقة الكبيرة أسفل النموذج فارغة بلا سبب ظاهر.
        self._debounced_open_calculator()

    def _on_driver_changed(self):
        driver_name = self.sal_vars["driver"].get().strip()
        if not driver_name:
            self._salary_sync_car(driver_name)
            return
        # نفس دالة الربط التي يستعملها التتبع التلقائي، حتى لا تختلف قائمة
        # السيارات بين اختيار السائق من القائمة وكتابته يدوياً.
        self._salary_sync_car(driver_name)
        self._auto_fill_month()
        # Prefer the driver's latest recorded month when the default current
        # month has no data; this prevents an apparently empty calculator.
        self._salary_align_period(driver_name)
        month = self.sal_vars.get("start_date", tk.StringVar()).get().strip()[:7]
        if month:
            rule = td.revenue_salary_rule(driver_name)
            if rule:
                self.sal_vars["salary_type"].set(td.REVENUE_SALARY_TYPE)
                details = td.vehicle_revenue_salary_details(
                    driver_name, month, self.sal_vars.get("car_no", tk.StringVar()).get().strip())
                self.sal_vars["base_salary"].set(f"{details['base_salary']:.3f}")
                self._auto_calculate_salary()
                self.open_salary_calculator()
                return
        drivers = {d["name"]: d for d in td.load_drivers()}
        d = drivers.get(driver_name)
        if d:
            self.sal_vars["base_salary"].set(safe_str(d.get("base_salary", "")))
        self.sal_car_combo.update_idletasks()
        self._auto_calculate_salary()
        self.open_salary_calculator()

    def _on_car_changed(self):
        car_no = self.sal_vars["car_no"].get().strip()
        if not car_no:
            return
        vehicle = next((v for v in td.load_vehicles() if str(v.get("car_no", "")).strip() == car_no), None)
        if not vehicle:
            return
        vehicle_driver = str(vehicle.get("driver", "")).strip()
        current_driver = self.sal_vars["driver"].get().strip()
        if vehicle_driver and vehicle_driver != current_driver:
            self.sal_vars["driver"].set(vehicle_driver)
            self._on_driver_changed()
            return
        self._auto_fill_month()
        self._auto_calculate_salary()
        self._debounced_open_calculator()

    def _auto_calculate_salary(self):
        """تحديث خانات النموذج بنفس دالة الحساب المعتمدة في الحاسبة والحفظ."""
        driver_name = self.sal_vars["driver"].get().strip()
        start_date = self.sal_vars.get("start_date", tk.StringVar()).get().strip()
        end_date = self.sal_vars.get("end_date", tk.StringVar()).get().strip()
        month = start_date[:7] if start_date else ""
        # شرح طريقة الحساب يظهر دائماً حتى لا يختفي معنى الرقم المعروض.
        self._refresh_salary_method_hint()
        if not driver_name or not month:
            self._set_salary_carry_display(0.0)
            return
        car_no = self.sal_vars.get("car_no", tk.StringVar()).get().strip()
        method = self.sal_vars["salary_type"].get().strip() or "شهري"
        revenue = td.driver_salary_period_details(
            driver_name, start_date, end_date, car_no,
            exclude_salary_id=self.salary_editing_id)
        if method in td.SALARY_REVENUE_FRACTIONS:
            # صيغ إيراد السيارة تعتمد قاعدة «إيراد السيارة» الخاصة بكل سائق.
            details = td.vehicle_revenue_salary_details(driver_name, month, car_no)
            result = td.calculate_salary(
                method,
                base_salary=details["base_salary"],
                trip_revenue=details["vehicle_revenue"],
                holiday_revenue=details["holiday_revenue"],
                car_expenses=details["vehicle_expenses"],
                carry_balance=revenue["carry"]["balance"])
            self.sal_vars["base_salary"].set(f"{result['base']:.3f}")
        else:
            trips = revenue["trips"]
            base = revenue["base_salary"] if method != "رحلة" else 0.0
            result = td.calculate_salary(
                method, base_salary=base,
                trip_revenue=revenue["revenue"], holiday_revenue=revenue["holiday"],
                driver_wages=sum(td.safe_float(t.get("driver_wage")) for t in trips),
                driver_expenses=sum(revenue["driver_costs"].values()),
                carry_balance=revenue["carry"]["balance"])
            self.sal_vars["base_salary"].set(f"{result['base']:.3f}")
        # يعرض المرحّل من الشهر السابق: موجب متبقٍّ للسائق، وسالب عليه السائق.
        self._set_salary_carry_display(revenue["carry"]["balance"])
        self._salary_calculated_details = dict(result)
        self._debounced_redraw()

    def _set_salary_carry_display(self, amount):
        """يكتب المرحّل في حقل للعرض مع لفظ اتجاهه حتى لا يُقرأ رقماً بلا معنى."""
        var = self.sal_vars.get("carry_display")
        if var is None:
            return
        value = td.safe_float(amount)
        if value > 0:
            var.set(f"{value:.3f} (متبقٍّ للسائق)")
        elif value < 0:
            var.set(f"{abs(value):.3f} (على السائق)")
        else:
            var.set("0.000")

    def _refresh_salary_method_hint(self):
        """يعرض شرح طريقة الحساب المختارة أسفل حقل «طريقة الحساب»."""
        label = getattr(self, "salary_method_hint", None)
        if label is None:
            return
        try:
            method = self.sal_vars["salary_type"].get().strip()
            label.config(text=td.salary_method_description(method))
        except (tk.TclError, AttributeError) as exc:
            log_exception("عرض طريقة الحساب", exc)

    def _debounced_open_calculator(self):
        if getattr(self, "_salary_calc_rebuild_pending", None):
            self.after_cancel(self._salary_calc_rebuild_pending)
        self._salary_calc_rebuild_pending = self.after(150, self.open_salary_calculator)

    def _debounced_redraw(self):
        if getattr(self, "_salary_calc_redraw_pending", None):
            self.after_cancel(self._salary_calc_redraw_pending)
        self._salary_calc_redraw_pending = self.after(80, self._do_redraw)

    def _do_redraw(self):
        self._salary_calc_redraw_pending = None
        try:
            trip_tree = getattr(self, "_salary_trip_tree", None)
            if trip_tree is None or not trip_tree.winfo_exists():
                self._salary_calc_redraw = None
                return
        except (tk.TclError, AttributeError):
            self._salary_calc_redraw = None
            return
        if hasattr(self, "_salary_calc_redraw") and self._salary_calc_redraw:
            self._salary_calc_redraw()

    def open_salary_calculator(self):
        self._salary_calc_rebuild_pending = None
        self._salary_calc_redraw = None
        self._salary_calc_context = {}
        driver = self.sal_vars["driver"].get().strip()
        car_filter = self.sal_vars.get("car_no", tk.StringVar()).get().strip()
        start = self.sal_vars.get("start_date", tk.StringVar()).get().strip()
        end = self.sal_vars.get("end_date", tk.StringVar()).get().strip()
        if not driver or not start or not end:
            for widget in self.salary_calc_container.winfo_children():
                widget.destroy()
            empty_label = tk.Label(self.salary_calc_container,
                                   text="اختر السائق وأدخل الفترة من وإلى أولاً لعرض تفاصيل الراتب.",
                                   font=F_BODY, bg=COLOR_BG, fg=COLOR_MUTED)
            empty_label.pack(pady=20)
            return
        try:
            date.fromisoformat(start)
            date.fromisoformat(end)
        except ValueError:
            messagebox.showwarning("تنبيه", "أدخل تواريخ صحيحة بصيغة YYYY-MM-DD.")
            return
        if start > end:
            messagebox.showwarning("تنبيه", "تاريخ البداية يجب أن يكون قبل تاريخ النهاية.")
            return
        for widget in self.salary_calc_container.winfo_children():
            widget.destroy()

        scroll_container = tk.Frame(self.salary_calc_container, bg=COLOR_BG)
        scroll_container.pack(fill="both", expand=True)
        canvas = tk.Canvas(scroll_container, bg=COLOR_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=COLOR_BG)
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig("all", width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        content_padded = tk.Frame(content, bg=COLOR_BG)
        content_padded.pack(fill="both", expand=True, padx=16)
        trips_header = tk.Frame(content_padded, bg=COLOR_BG)
        trips_header.pack(fill="x", pady=(0, 4))
        tk.Label(trips_header,
                 text="رحلات الفترة (سجل الرحلات) — انقر مرتين على أي رحلة لتعديل السعر أو العطلة أو أجرة السائق.",
                 font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED, anchor="e").pack(side="right")
        make_btn(trips_header, "تعديل الرحلة المحددة",
                 lambda: self.salary_edit_selected_trip(trip_tree),
                 variant="secondary", padx=8, pady=3).pack(side="left")
        self._salary_trip_tree = trip_tree = ttk.Treeview(content_padded, columns=("driver_wage", "holiday", "fee", "country", "direction", "customer", "company", "declaration_no", "date", "container_size", "trip_no", "car_no"), show="headings", height=7)
        for key, label in {"driver_wage":"أجرة السائق", "holiday":"العطلة", "fee":"السعر", "country":"مكان التنزيل", "direction":"مكان التحميل", "customer":"العميل", "company":"الشركة", "declaration_no":"رقم البيان", "date":"التاريخ", "container_size":"حجم الحاوية", "trip_no":"رقم الضرب", "car_no":"رقم السيارة"}.items():
            trip_tree.heading(key, text=label); trip_tree.column(key, anchor="center", width=130)
        trip_tree.pack(fill="x", pady=(0, 8))
        apply_table_style(trip_tree)
        # تعديل الرحلة يُحدِّث سجل الرحلات الفعلي وبالتالي بقية الشاشات.
        trip_tree.bind("<Double-1>", lambda _e: self.salary_edit_selected_trip(trip_tree))
        choices = tk.Frame(content_padded, bg=COLOR_BG)
        choices.pack(fill="x")
        car_box = card_frame(choices, "اختر بنود مصاريف السيارة التي تخصم من الإيراد")
        car_box.pack(side="right", fill="both", expand=True, padx=(0, 6))
        driver_box = card_frame(choices, "اختر مصاريف السائق التي تخصم من الراتب")
        driver_box.pack(side="left", fill="both", expand=True, padx=(6, 0))
        car_vars, driver_vars = {}, {}
        car_detail_label = tk.StringVar(value="تفاصيل مصاريف السيارة")
        tk.Label(car_box.body, textvariable=car_detail_label, font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED, anchor="e").pack(fill="x", padx=14, pady=(2, 3))
        tk.Label(car_box.body, text="انقر مرتين على البند لتعديله داخل حصر الراتب فقط (لا يؤثر على شاشة يومية السيارات).",
                 font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED, anchor="e", wraplength=420,
                 justify="right").pack(fill="x", padx=14, pady=(0, 3))
        self._salary_car_detail_tree = car_detail_tree = ttk.Treeview(car_box.body, columns=("notes", "amount", "category", "car_no", "date"), show="headings", height=3)
        for key, label in {"notes":"ملاحظات", "amount":"التكلفة", "category":"البند", "car_no":"السيارة", "date":"التاريخ"}.items():
            car_detail_tree.heading(key, text=label); car_detail_tree.column(key, anchor="center", width=100)
        car_detail_tree.tag_configure("salary_override", foreground=COLOR_DANGER)
        car_detail_tree.pack(fill="x", padx=14, pady=(0, 4))
        apply_table_style(car_detail_tree)
        car_edit_row = tk.Frame(car_box.body, bg=COLOR_CARD)
        car_edit_row.pack(fill="x", padx=14, pady=(0, 6))
        make_btn(car_edit_row, "تعديل البند المحدد",
                 lambda: edit_expense_item(None, car_detail_tree, "car"),
                 variant="secondary", padx=8, pady=3).pack(side="right")
        car_total_var = tk.StringVar(value="الإجمالي: 0.000 د.ك")
        tk.Label(car_box.body, textvariable=car_total_var, font=F_LABEL, bg=COLOR_CARD, fg=COLOR_PRIMARY, anchor="e").pack(fill="x", padx=14, pady=(0, 8))

        driver_detail_label = tk.StringVar(value="تفاصيل مصاريف السائق والسلف")
        tk.Label(driver_box.body, textvariable=driver_detail_label, font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED, anchor="e").pack(fill="x", padx=14, pady=(2, 3))
        tk.Label(driver_box.body, text="انقر مرتين على البند لتعديله داخل حصر الراتب فقط (لا يؤثر على شاشة الرحلات اليومية).",
                 font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED, anchor="e", wraplength=420,
                 justify="right").pack(fill="x", padx=14, pady=(0, 3))
        self._salary_driver_detail_tree = driver_detail_tree = ttk.Treeview(driver_box.body, columns=("notes", "amount", "category", "car_no", "date"), show="headings", height=3)
        for key, label in {"notes":"ملاحظات", "amount":"التكلفة", "category":"البند", "car_no":"السيارة", "date":"التاريخ"}.items():
            driver_detail_tree.heading(key, text=label); driver_detail_tree.column(key, anchor="center", width=100)
        driver_detail_tree.tag_configure("salary_override", foreground=COLOR_DANGER)
        driver_detail_tree.pack(fill="x", padx=14, pady=(0, 4))
        apply_table_style(driver_detail_tree)
        driver_edit_row = tk.Frame(driver_box.body, bg=COLOR_CARD)
        driver_edit_row.pack(fill="x", padx=14, pady=(0, 6))
        make_btn(driver_edit_row, "تعديل البند المحدد",
                 lambda: edit_expense_item(None, driver_detail_tree, "driver"),
                 variant="secondary", padx=8, pady=3).pack(side="right")

        driver_total_var = tk.StringVar(value="الإجمالي: 0.000 د.ك")
        tk.Label(driver_box.body, textvariable=driver_total_var, font=F_LABEL, bg=COLOR_CARD, fg=COLOR_PRIMARY, anchor="e").pack(fill="x", padx=14, pady=(0, 8))

        car_filter_combo = ttk.Combobox(car_box.body, state="readonly", font=F_BODY, justify="right")
        car_filter_combo.pack(fill="x", padx=14, pady=(0, 8))
        car_filter_combo.bind("<<ComboboxSelected>>", lambda e: redraw())
        driver_filter_combo = ttk.Combobox(driver_box.body, state="readonly", font=F_BODY, justify="right")
        driver_filter_combo.pack(fill="x", padx=14, pady=(0, 8))
        driver_filter_combo.bind("<<ComboboxSelected>>", lambda e: redraw())

        car_btns = tk.Frame(car_box.body, bg=COLOR_CARD)
        car_btns.pack(fill="x", padx=14, pady=(0, 8))
        driver_btns = tk.Frame(driver_box.body, bg=COLOR_CARD)
        driver_btns.pack(fill="x", padx=14, pady=(0, 8))

        def edit_expense_item(event, tree, expense_type):
                """تعديل بند مصروف لحساب الراتب فقط — لا يُكتب في ملف البيانات."""
                sel = tree.selection()
                if not sel:
                    if event is None:  # الزر يوضّح سبب عدم التنفيذ، النقر المزدوج لا يحتاج ذلك
                        messagebox.showinfo("تنبيه", "الرجاء اختيار بند مصروف من الجدول أولاً.",
                                            parent=content_padded)
                    return
                item = sel[0]
                values = tree.item(item, "values")
                if not values:
                    return
                tags = tree.item(item, "tags")
                rec_id = safe_str(tags[0]).strip() if tags else ""
                old_notes, old_amount, old_cat, old_car, old_date = values
                if not rec_id:
                    messagebox.showinfo("تنبيه", "لا يمكن تعديل هذا البند لعدم وجود رقم مرجعي له.",
                                        parent=content_padded)
                    return

                dlg = tk.Toplevel(content_padded)
                dlg.title("تعديل بند مصروف داخل حصر الراتب")
                dlg.configure(bg=COLOR_BG)
                dlg.transient(content_padded)
                dlg.grab_set()
                tk.Label(dlg,
                         text=("التعديل هنا يُستخدم في حساب الراتب فقط ولا يغيّر سجلات شاشة "
                               "يومية السيارات أو شاشة الرحلات اليومية."),
                         font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED, anchor="e",
                         wraplength=360, justify="right").pack(fill="x", padx=16, pady=(12, 2))

                vars_edit = {
                    "notes": tk.StringVar(value=old_notes),
                    "amount": tk.StringVar(value=old_amount),
                    "category": tk.StringVar(value=old_cat),
                    "car_no": tk.StringVar(value=old_car),
                    "date": tk.StringVar(value=old_date),
                }
                categories = (td.VEHICLE_EXPENSE_CATEGORIES if expense_type == "car"
                              else td.DRIVER_EXPENSE_CATEGORIES)
                fields = [("ملاحظات", "notes"), ("التكلفة", "amount"), ("البند", "category"),
                          ("السيارة", "car_no"), ("التاريخ", "date")]
                for label, key in fields:
                    row = tk.Frame(dlg, bg=COLOR_BG)
                    row.pack(fill="x", padx=16, pady=6)
                    tk.Label(row, text=label, font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED,
                             anchor="e", width=10).pack(side="right", padx=4)
                    holder = tk.Frame(row, bg=COLOR_BG)
                    holder.pack(side="right", fill="x", expand=True)
                    if key == "category":
                        combo_values = sorted({old_cat, *categories} - {""})
                        ttk.Combobox(holder, textvariable=vars_edit[key], values=combo_values,
                                     font=F_BODY, justify="right").pack(fill="x", ipady=3)
                    elif key == "car_no":
                        cars = [v.get("car_no", "") for v in td.load_vehicles() if v.get("car_no", "")]
                        ttk.Combobox(holder, textvariable=vars_edit[key], values=cars,
                                     font=F_BODY, justify="right").pack(fill="x", ipady=3)
                    elif key == "date":
                        date_input(holder, vars_edit[key])
                    else:
                        modern_entry(holder, vars_edit[key], ipady=3)

                def save_edit():
                    amount_text = vars_edit["amount"].get().strip().replace(",", "")
                    try:
                        amount = round(float(amount_text or 0), 3)
                    except ValueError:
                        messagebox.showwarning("تنبيه", "أدخل تكلفة رقمية صحيحة.", parent=dlg)
                        return
                    new_date = vars_edit["date"].get().strip()
                    if new_date:
                        try:
                            date.fromisoformat(new_date)
                        except ValueError:
                            messagebox.showwarning("تنبيه", "أدخل التاريخ بصيغة YYYY-MM-DD.", parent=dlg)
                            return
                    notes = vars_edit["notes"].get().strip()
                    # التعديل يُخزَّن في الذاكرة فقط ويُطبَّق عند حساب الراتب.
                    self.set_salary_expense_override(rec_id, {
                        "amount": amount,
                        "category": vars_edit["category"].get().strip(),
                        "car_no": vars_edit["car_no"].get().strip(),
                        "date": new_date,
                        "description": notes,
                        "notes": notes,
                    })
                    dlg.destroy()
                    redraw()

                def restore_original():
                    self.clear_salary_expense_override(rec_id)
                    dlg.destroy()
                    redraw()

                btns = tk.Frame(dlg, bg=COLOR_BG)
                btns.pack(fill="x", padx=16, pady=10)
                # أزرار النافذة على اليمين كما في بقية النوافذ العربية.
                make_btn(btns, "حفظ داخل الحصر", save_edit, variant="accent").pack(side="right", padx=4)
                make_btn(btns, "استعادة القيمة الأصلية", restore_original, variant="secondary").pack(side="right", padx=4)
                make_btn(btns, "إلغاء", dlg.destroy, variant="secondary").pack(side="left", padx=4)

                car_detail_tree.bind("<Double-1>", lambda e: edit_expense_item(e, car_detail_tree, "car"))
                driver_detail_tree.bind("<Double-1>", lambda e: edit_expense_item(e, driver_detail_tree, "driver"))

        def load_actual_expenses():
            start_val = self.sal_vars.get("start_date", tk.StringVar()).get().strip()
            end_val = self.sal_vars.get("end_date", tk.StringVar()).get().strip()
            car = self.sal_vars.get("car_no", tk.StringVar()).get().strip()
            # نستبعد ما سبق احتسابه في راتب محفوظ لنفس السائق، ونستثني السجل
            # الجاري تعديله. بدون هذا كانت المصاريف القديمة تظل معروضة وتُحتسب.
            counted = td.counted_salary_periods(driver, self.salary_editing_id)

            def fresh(value):
                return not td._in_counted_period(value, counted)

            if car:
                allowed_cars = {car}
            else:
                # بلا سيارة محدّدة نقصر المصاريف على سيارات رحلات هذا السائق في
                # الفترة نفسها: كان الفلتر يقبل كل السيارات، فتُخصم مصاريف الشركة
                # كاملة من راتب سائق واحد ويظهر الرقم صفراً ربع أو ثلث الصافي.
                allowed_cars = {
                    str(item).strip()
                    for item in td.driver_salary_period_details(
                        driver, start_val, end_val, "",
                        exclude_salary_id=self.salary_editing_id)["cars"]
                    if str(item).strip()
                }
            car_expenses = []
            driver_expenses = []
            for row in td.load_daily_expenses():
                # تُطبَّق تعديلات شاشة الرواتب المحلية قبل التصفية والحساب.
                row = self.salary_expense_override(row)
                row_date = str(row.get("date", "")).strip()
                if start_val and row_date < start_val:
                    continue
                if end_val and row_date > end_val:
                    continue
                if not fresh(row_date):
                    continue
                row_car = str(row.get("car_no", "")).strip()
                row_driver = str(row.get("driver", "")).strip()
                owner = td.daily_expense_owner(row)
                if owner == "سيارة" and (not allowed_cars or row_car in allowed_cars):
                    car_expenses.append(row)
                elif owner == "سائق" and td._normalized_driver_name(row_driver) == td._normalized_driver_name(driver) and (not allowed_cars or row_car in allowed_cars):
                    driver_expenses.append(row)
                    advance = td.safe_float(row.get("driver_advance"))
                    if advance:
                        advance_row = dict(row)
                        advance_row["category"] = "سلفة للسائق"
                        advance_row["amount"] = advance
                        advance_row["description"] = "سلفة للسائق"
                        driver_expenses.append(advance_row)
            for row in td.load_trips():
                row_date = str(row.get("date", "")).strip()
                if start_val and row_date < start_val or end_val and row_date > end_val:
                    continue
                if not fresh(row_date):
                    continue
                row_car = str(row.get("car_no", "")).strip()
                if allowed_cars and row_car not in allowed_cars:
                    continue
                # مصاريف الرحلة تُحسب على سائق الرحلة نفسه: كان الفلتر بالسيارة
                # فقط فيضمّ ديزل رحلات سائق آخر على نفس السيارة، فينقص راتب هذا
                # السائق بمصاريف ليست له، ويختلف الرقم عن المعروض في النموذج.
                same_driver = td._normalized_driver_name(
                    row.get("driver")) == td._normalized_driver_name(driver)
                car_amount = td.safe_float(row.get("car_expense_amount"))
                if car_amount and same_driver:
                    car_expenses.append({
                        "id": f"trip-car-{row.get('id', '')}",
                        "date": row_date, "car_no": row_car,
                        "category": str(row.get("car_expense_type", "")).strip() or "مصاريف رحلة",
                        "amount": car_amount, "notes": row.get("notes", ""),
                        "description": "مصاريف مرتبطة بالرحلة",
                    })
                driver_amount = td.safe_float(row.get("driver_expense"))
                if driver_amount and same_driver:
                    driver_expenses.append({
                        "id": f"trip-driver-{row.get('id', '')}",
                        "date": row_date, "car_no": row_car,
                        "category": "مصروف سائق (رحلة)", "amount": driver_amount,
                        "notes": row.get("notes", ""),
                        "description": "مصروف مرتبط بالرحلة",
                    })
            for row in td.load_maintenance():
                row_date = str(row.get("date", "")).strip()
                row_car = str(row.get("car_no", "")).strip()
                if ((start_val and row_date < start_val) or
                        (end_val and row_date > end_val) or
                        not fresh(row_date) or
                        (allowed_cars and row_car not in allowed_cars)):
                    continue
                amount = td.safe_float(row.get("cost"))
                if amount:
                    car_expenses.append({
                        "id": f"maintenance-{row.get('id', '')}",
                        "date": row_date, "car_no": row_car,
                        "category": f"صيانة - {row.get('type', '') or 'أخرى'}",
                        "amount": amount, "notes": row.get("notes", ""),
                        "description": "سجل صيانة",
                    })
            return car_expenses, driver_expenses

        self._redrawing = False
        self._car_chk_states = {}
        self._drv_chk_states = {}

        def redraw():
            if self._redrawing:
                return
            try:
                trip_tree = self._salary_trip_tree
                car_detail_tree = self._salary_car_detail_tree
                driver_detail_tree = self._salary_driver_detail_tree
                if not all(widget and hasattr(widget, "winfo_exists") and widget.winfo_exists()
                           for widget in [trip_tree, car_detail_tree, driver_detail_tree]):
                    self._salary_calc_redraw = None
                    return
            except (tk.TclError, AttributeError):
                self._salary_calc_redraw = None
                return
            self._redrawing = True
            try:
                start_val = self.sal_vars.get("start_date", tk.StringVar()).get().strip()
                end_val = self.sal_vars.get("end_date", tk.StringVar()).get().strip()
                # تُقرأ السيارة من النموذج في كل إعادة رسم حتى يبقى الجدول
                # متوافقاً مع بنود المصروفات المعروضة.
                car_filter_value = self.sal_vars.get("car_no", tk.StringVar()).get().strip() or car_filter
                details = td.driver_salary_period_details(
                driver, start_val, end_val, car_filter_value,
                exclude_salary_id=self.salary_editing_id)
                for item in trip_tree.get_children(): trip_tree.delete(item)
                for idx, trip in enumerate(details["trips"]):
                    if car_filter_value and safe_str(trip.get("car_no")).strip() != car_filter_value:
                        continue
                    trip_tree.insert("", "end", values=(f"{td.safe_float(trip.get('driver_wage')):.3f}", f"{td.safe_float(trip.get('holiday_price')):.3f}", f"{td.safe_float(trip.get('fee')):.3f}", trip.get("country", ""), trip.get("direction", ""), trip.get("customer", ""), trip.get("company", ""), trip.get("declaration_no", ""), trip.get("date", ""), trip.get("container_size", ""), str(idx+1), safe_str(trip.get("car_no", ""))), tags=(str(trip.get("id", "")),))
                for cat, (var, _) in car_vars.items():
                    self._car_chk_states[cat] = var.get()
                for cat, (var, _) in driver_vars.items():
                    self._drv_chk_states[cat] = var.get()
                car_vars.clear(); driver_vars.clear()
                for widget in car_btns.winfo_children(): widget.destroy()
                for widget in driver_btns.winfo_children(): widget.destroy()
                car_expenses, driver_expenses = load_actual_expenses()
                car_costs = {}
                for rec in car_expenses:
                    cat = str(rec.get("category", "")).strip() or "أخرى"
                    car_costs[cat] = round(car_costs.get(cat, 0.0) + td.safe_float(rec.get("amount", 0)), 3)
                driver_costs = {}
                for rec in driver_expenses:
                    cat = str(rec.get("category", "")).strip() or "أخرى"
                    driver_costs[cat] = round(driver_costs.get(cat, 0.0) + td.safe_float(rec.get("amount", 0)), 3)
                car_options = ["الكل"] + sorted(car_costs.keys())
                driver_options = ["الكل"] + sorted(driver_costs.keys())
                # نحافظ على البند المختار في الفلتر بعد كل إعادة رسم.
                previous_car_filter = car_filter_combo.get().strip()
                previous_driver_filter = driver_filter_combo.get().strip()
                car_filter_combo["values"] = car_options
                car_filter_combo.set(previous_car_filter if previous_car_filter in car_options else "الكل")
                driver_filter_combo["values"] = driver_options
                driver_filter_combo.set(previous_driver_filter if previous_driver_filter in driver_options else "الكل")
                car_filter_val = car_filter_combo.get().strip()
                driver_filter_val = driver_filter_combo.get().strip()
                for item in car_detail_tree.get_children(): car_detail_tree.delete(item)
                for rec in car_expenses:
                    if car_filter_val != "الكل" and str(rec.get("category", "")).strip() != car_filter_val:
                        continue
                    rec_id = str(rec.get("id", ""))
                    row_tags = (rec_id, "salary_override") if rec.get("_salary_override") else (rec_id,)
                    car_detail_tree.insert("", "end", values=(rec.get("description", "") or rec.get("notes", ""), f"{td.safe_float(rec.get('amount', 0)):.3f}", rec.get("category", ""), rec.get("car_no", ""), rec.get("date", "")), tags=row_tags)
                for item in driver_detail_tree.get_children(): driver_detail_tree.delete(item)
                for rec in driver_expenses:
                    if driver_filter_val != "الكل" and str(rec.get("category", "")).strip() != driver_filter_val:
                        continue
                    rec_id = str(rec.get("id", ""))
                    row_tags = (rec_id, "salary_override") if rec.get("_salary_override") else (rec_id,)
                    driver_detail_tree.insert("", "end", values=(rec.get("description", "") or rec.get("notes", ""), f"{td.safe_float(rec.get('amount', 0)):.3f}", rec.get("category", ""), rec.get("car_no", ""), rec.get("date", "")), tags=row_tags)
                for category, amount in sorted(car_costs.items()):
                    var = tk.BooleanVar(value=self._car_chk_states.get(category, True)); car_vars[category] = (var, amount)
                    chk = tk.Checkbutton(car_btns, text=f"{category}: {amount:.3f}", variable=var, bg=COLOR_CARD, fg=COLOR_TEXT, activebackground=COLOR_CARD, selectcolor=COLOR_BG, anchor="e")
                    chk.pack(anchor="e", padx=14, pady=2)
                    var.trace_add("write", lambda *_: redraw())
                for category, amount in sorted(driver_costs.items()):
                    var = tk.BooleanVar(value=self._drv_chk_states.get(category, True)); driver_vars[category] = (var, amount)
                    chk = tk.Checkbutton(driver_btns, text=f"{category}: {amount:.3f}", variable=var, fg=COLOR_TEXT, bg=COLOR_CARD, activebackground=COLOR_CARD, selectcolor=COLOR_BG, anchor="e")
                    chk.pack(anchor="e", padx=14, pady=2)
                    var.trace_add("write", lambda *_: redraw())
                car_total_var.set(f"الإجمالي: {sum(amount for var, amount in car_vars.values() if var.get()):.3f} د.ك")
                driver_total_var.set(f"الإجمالي: {sum(amount for var, amount in driver_vars.values() if var.get()):.3f} د.ك")
                # نوضّح عدد البنود المعدّلة محلياً حتى لا تختلط بالبيانات الأصلية.
                car_override_count = sum(1 for rec in car_expenses if rec.get("_salary_override"))
                driver_override_count = sum(1 for rec in driver_expenses if rec.get("_salary_override"))
                car_detail_label.set("تفاصيل مصاريف السيارة"
                                     + (f"   |   بنود معدّلة داخل الحصر: {car_override_count}" if car_override_count else ""))
                driver_detail_label.set("تفاصيل مصاريف السائق والسلف"
                                        + (f"   |   بنود معدّلة داخل الحصر: {driver_override_count}" if driver_override_count else ""))
                calculate()
            except Exception as e:
                import traceback
                traceback.print_exc()
                messagebox.showerror("خطأ", f"حدث خطأ أثناء تحديث البيانات:\n{e}", parent=content_padded)
            finally:
                self._redrawing = False


        def salary_inputs(details):
            """مدخلات حساب الراتب الموحّدة للوحة العرض والتقرير والطباعة.

            كانت ثلاث شاشات تمرّر ثلاث مجموعات مدخلات مختلفة: النموذج والحفظ
            يستعملان إيراد سيارة الشهر، ولوحة الحصر تستعمل إيراد الفترة كاملاً.
            فيظهر رقمان مختلفان لنفس السائق. نجمعها هنا في مصدر واحد.
            """
            start_val = self.sal_vars.get("start_date", tk.StringVar()).get().strip()
            car_no_val = self.sal_vars.get("car_no", tk.StringVar()).get().strip()
            month_val = start_val[:7]
            method = self.sal_vars["salary_type"].get().strip()
            base_salary = details["base_salary"]
            rev_trips = details["revenue"]
            rev_holiday = details["holiday"] if self.sal_holiday_var.get() else 0.0
            if method in td.SALARY_REVENUE_FRACTIONS:
                # صيغ إيراد السيارة تعتمد إيراد سيارة السائق في الشهر، لا إيراد
                # الفترة، تماماً كما في النموذج والحفظ.
                vdetail = td.vehicle_revenue_salary_details(driver, month_val, car_no_val)
                base_salary = vdetail["base_salary"]
                rev_trips = vdetail["vehicle_revenue"]
                rev_holiday = vdetail["holiday_revenue"]
            return {
                "method": method, "month": month_val, "base_salary": base_salary,
                "trip_revenue": rev_trips, "holiday_revenue": rev_holiday,
                "car_expenses": sum(amount for var, amount in car_vars.values() if var.get()),
                "driver_expenses": sum(amount for var, amount in driver_vars.values() if var.get()),
                "driver_wages": sum(td.safe_float(t.get("driver_wage", 0))
                                     for t in details["trips"]),
            }

        # جدول ملخّص الراتب: كان نصاً طويلاً مفصولاً بعلامة «|» فتعذّر معرفة
        # أي رقم يخص أي بند. الجدول يعرض كل بند في سطر مستقل.
        SUMMARY_ROWS = [
            ("base", "الراتب الأساسي"),
            ("share", "حصة الإيراد / أجرة الرحلة"),
            ("wages", "إجمالي أجرة الرحلات"),
            ("holiday", "إيراد العطل"),
            ("car", "خصم بنود السيارة"),
            ("driver", "خصم بنود السائق"),
            ("carry", "رصيد مرحّل من الشهور السابقة"),
        ]
        summary_vars = {key: tk.StringVar(value="0.000") for key, _ in SUMMARY_ROWS}
        summary_vars["method"] = tk.StringVar(value="")
        summary_vars["note"] = tk.StringVar(value="")

        summary_card = tk.Frame(content_padded, bg=COLOR_CARD, relief="flat",
                                highlightbackground=COLOR_BORDER, highlightthickness=1)
        summary_card.pack(fill="x", pady=(0, 12))
        summary_grid = tk.Frame(summary_card, bg=COLOR_CARD)
        summary_grid.pack(fill="x", padx=14, pady=10)
        # العمود الأول (البيان) على اليمين، والثاني (القيمة) إلى يساره.
        summary_grid.grid_columnconfigure(0, weight=3, uniform="sum")
        summary_grid.grid_columnconfigure(1, weight=2, uniform="sum")
        tk.Label(summary_grid, text="البيان", font=F_BOLD, bg=COLOR_CARD,
                 fg=COLOR_PRIMARY, anchor="e").grid(row=0, column=0, sticky="ew", pady=(0, 4))
        tk.Label(summary_grid, text="القيمة (د.ك)", font=F_BOLD, bg=COLOR_CARD,
                 fg=COLOR_PRIMARY, anchor="e").grid(row=0, column=1, sticky="ew", pady=(0, 4))
        tk.Frame(summary_grid, bg=COLOR_BORDER, height=1).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        summary_carry_lbl = []
        for index, (key, label) in enumerate(SUMMARY_ROWS):
            row_no = index + 2
            tk.Label(summary_grid, text=label, font=F_BODY, bg=COLOR_CARD,
                     fg=COLOR_TEXT, anchor="e").grid(
                row=row_no, column=0, sticky="ew", pady=2)
            value_label = tk.Label(summary_grid, textvariable=summary_vars[key],
                                   font=F_BODY, bg=COLOR_CARD, fg=COLOR_TEXT,
                                   anchor="e")
            value_label.grid(row=row_no, column=1, sticky="ew", pady=2)
            if key == "carry":
                summary_carry_lbl.append(value_label)
        # سطر الصافي منفصل وبخط عريض حتى يبرز بين البنود.
        net_row = len(SUMMARY_ROWS) + 3
        tk.Frame(summary_grid, bg=COLOR_BORDER, height=1).grid(
            row=net_row - 1, column=0, columnspan=2, sticky="ew", pady=(6, 4))
        tk.Label(summary_grid, text="صافي الراتب", font=F_BOLD, bg=COLOR_CARD,
                 fg=COLOR_PRIMARY, anchor="e").grid(
            row=net_row, column=0, sticky="ew", pady=(2, 0))
        net_value_lbl = tk.Label(summary_grid, text="0.000  (متعادل)",
                                 font=F_BOLD, bg=COLOR_CARD, fg=COLOR_PRIMARY,
                                 anchor="e")
        net_value_lbl.grid(row=net_row, column=1, sticky="ew", pady=(2, 0))
        tk.Label(summary_grid, textvariable=summary_vars["method"], font=F_LABEL,
                 bg=COLOR_CARD, fg=COLOR_MUTED, anchor="e").grid(
            row=net_row + 1, column=0, columnspan=2, sticky="ew", pady=(2, 0))
        tk.Label(summary_grid, textvariable=summary_vars["note"], font=F_LABEL,
                 bg=COLOR_CARD, fg=COLOR_DANGER, anchor="e", justify="right").grid(
            row=net_row + 2, column=0, columnspan=2, sticky="ew", pady=(2, 0))

        def calculate(details=None):
                start_val = self.sal_vars.get("start_date", tk.StringVar()).get().strip()
                end_val = self.sal_vars.get("end_date", tk.StringVar()).get().strip()
                details = details or td.driver_salary_period_details(
                    driver, start_val, end_val, self.sal_vars.get("car_no", tk.StringVar()).get().strip())
                holiday_included = details["holiday"] if self.sal_holiday_var.get() else 0.0
                inputs = salary_inputs(details)
                method = inputs["method"]
                car_ded = inputs["car_expenses"]
                driver_ded = inputs["driver_expenses"]
                driver_wage_total = inputs["driver_wages"]
                base_salary = inputs["base_salary"]
                month_val = inputs["month"]
                # نسمّي الناتج calc لا result: فكانت التسمية result تحجب المتغيّر
                # النصّي result المرتبط بالمُلصق، فيسقط سطر «طريقة الحساب» بالكامل.
                calc = td.calculate_salary(
                    method, base_salary=base_salary,
                    trip_revenue=inputs["trip_revenue"], holiday_revenue=inputs["holiday_revenue"],
                    driver_wages=driver_wage_total, car_expenses=car_ded,
                    driver_expenses=driver_ded,
                    carry_balance=details.get("carry", {}).get("balance", 0.0))
                base, share, net = calc["base"], calc["share"], calc["net"]
                self._salary_calculated_details = dict(calc)
                # الرصيد يُقرأ بالحالة: موجب «دائن» أي مستحق له، وسالب «مدين»
                # أي عليه. الرقم وحده كان يُقرأ بلا معنى عند السالب.
                state = calc.get("state", td.salary_balance_state(net))
                summary_vars["base"].set(f"{base:.3f}")
                summary_vars["share"].set(f"{share:.3f}")
                summary_vars["holiday"].set(
                    f"{holiday_included:.3f} "
                    f"({'مضاف' if holiday_included else 'غير مضاف'})")
                summary_vars["wages"].set(f"{driver_wage_total:.3f}")
                summary_vars["car"].set(f"{car_ded:.3f}")
                summary_vars["driver"].set(f"{driver_ded:.3f}")
                carry = details.get("carry", {})
                carry_amount = td.safe_float(carry.get("balance"))
                summary_vars["carry"].set(
                    f"{carry_amount:.3f}"
                    + (f"  ({carry.get('state')})" if carry_amount else ""))
                carry_label = summary_carry_lbl[0] if summary_carry_lbl else None
                if carry_label is not None:
                    carry_label.config(
                        fg=COLOR_SUCCESS if carry_amount > 0 else
                        (COLOR_DANGER if carry_amount < 0 else COLOR_TEXT))
                summary_vars["method"].set(
                    f"طريقة الحساب: {method} — {td.salary_method_description(method)}")
                if details.get("duplicates"):
                    summary_vars["note"].set(
                        f"تنبيه: تم استبعاد {details['duplicates']} رحلة مكررة من الحساب.")
                else:
                    summary_vars["note"].set("")
                if state == "مدين":
                    net_value_lbl.config(
                        fg=COLOR_DANGER,
                        text=f"{net:.3f}  (مدين — عليه {abs(net):.3f})")
                elif state == "دائن":
                    net_value_lbl.config(
                        fg=COLOR_SUCCESS,
                        text=f"{net:.3f}  (دائن — مستحق له {net:.3f})")
                else:
                    net_value_lbl.config(fg=COLOR_PRIMARY, text="0.000  (متعادل)")

        def print_report():
            start_val = self.sal_vars.get("start_date", tk.StringVar()).get().strip()
            end_val = self.sal_vars.get("end_date", tk.StringVar()).get().strip()
            details = td.driver_salary_period_details(
                driver, start_val, end_val,
                self.sal_vars.get("car_no", tk.StringVar()).get().strip(),
                exclude_salary_id=self.salary_editing_id)
            car_ded = sum(amount for var, amount in car_vars.values() if var.get())
            driver_ded = sum(amount for var, amount in driver_vars.values() if var.get())
            holiday_included = details["holiday"] if self.sal_holiday_var.get() else 0.0
            # نفس مدخلات لوحة العرض تماماً، وإلا اختلف الرقم المطبوع عن المعروض.
            inputs = salary_inputs(details)
            month_val = inputs["month"]
            car_ded = inputs["car_expenses"]
            driver_ded = inputs["driver_expenses"]
            driver_wage_total = inputs["driver_wages"]
            base_salary = inputs["base_salary"]
            method = inputs["method"]
            calc = td.calculate_salary(
                method, base_salary=base_salary,
                trip_revenue=inputs["trip_revenue"], holiday_revenue=inputs["holiday_revenue"],
                driver_wages=driver_wage_total, car_expenses=car_ded,
                driver_expenses=driver_ded,
                carry_balance=details.get("carry", {}).get("balance", 0.0))
            base, share, net = calc["base"], calc["share"], calc["net"]
            holiday_state = "مُضاف" if self.sal_holiday_var.get() else "غير مُضاف"

            def trip_rows_html():
                out = ""
                for t in details["trips"]:
                    out += ("<tr><td>{car}</td><td>{dw}</td><td>{hp}</td><td>{fee}</td><td>{country}</td>"
                        "<td>{direction}</td><td>{customer}</td><td>{company}</td>"
                        "<td>{decl}</td><td>{date}</td><td>{size}</td><td>{tno}</td></tr>").format(
                    car=html.escape(safe_str(t.get('car_no'))),
                    dw=f"{td.safe_float(t.get('driver_wage')):.3f}",
                    hp=f"{td.safe_float(t.get('holiday_price')):.3f}",
                    fee=f"{td.safe_float(t.get('fee')):.3f}",
                    country=html.escape(safe_str(t.get('country'))),
                    direction=html.escape(safe_str(t.get('direction'))),
                    customer=html.escape(safe_str(t.get('customer'))),
                    company=html.escape(safe_str(t.get('company'))),
                    decl=html.escape(safe_str(t.get('declaration_no'))),
                    date=html.escape(safe_str(t.get('date'))),
                    size=html.escape(safe_str(t.get('container_size'))),
                    tno=html.escape(safe_str(t.get('trip_no'))))
                return out

            def expense_rows_html(vars_map):
                out = ""
                total = 0.0
                for cat, (var, amount) in vars_map.items():
                    if not var.get():
                        continue
                    out += (f"<tr><td>{html.escape(safe_str(cat))}</td>"
                            f"<td>{amount:.3f}</td></tr>")
                    total += amount
                out += (f"<tr class='total'><td>الإجمالي</td>"
                        f"<td>{total:.3f} د.ك</td></tr>")
                return out

            css = (
                f"body{{font-family:Tahoma,'Segoe UI',sans-serif;color:{PRINT_INK};padding:30px;}}"
                f".title{{text-align:center;color:{PRINT_NAVY};margin-bottom:4px;}}"
                f".subtitle{{text-align:center;color:{PRINT_MUTED};margin-top:0;font-size:13px;}}"
                ".section{margin-top:22px;}"
                f".section h2{{font-size:16px;color:{PRINT_NAVY};"
                f"border-bottom:2px solid {PRINT_GOLD};"
                "padding-bottom:6px;margin-bottom:10px;}"
                "table{width:100%;border-collapse:collapse;font-size:12px;}"
                f"th{{background:{PRINT_NAVY};color:#fff;padding:8px;text-align:right;}}"
                f"td{{border:1px solid {PRINT_LINE};padding:7px;text-align:right;}}"
                f"tr:nth-child(even) td{{background:{PRINT_ROW_ALT};}}"
                ".summary td{border:none;padding:5px 8px;}"
                f".summary .label{{color:{PRINT_MUTED};width:42%;}}"
                ".summary .value{font-weight:bold;}"
                f".total td{{font-weight:800;background:{PRINT_TOTAL_BG} !important;"
                f"color:{PRINT_NAVY};}}"
                f".net{{margin-top:18px;padding:12px 16px;background:{PRINT_NAVY};color:#fff;"
                "border-radius:8px;font-size:16px;text-align:center;}"
            )

            carry_balance = safe_float(details.get("carry", {}).get("balance", 0.0))
            if carry_balance > 0:
                carry_text = f"{carry_balance:.3f} د.ك (متبقٍّ للسائق من الشهور السابقة)"
            elif carry_balance < 0:
                carry_text = f"{abs(carry_balance):.3f} د.ك (على السائق من الشهور السابقة)"
            else:
                carry_text = "0.000 د.ك (لا يوجد رصيد سابق)"
            summary_pairs = [
                ("السائق", driver),
                ("طريقة الحساب", method),
                ("الراتب الأساسي", f"{base_salary:.3f} د.ك"),
                ("إجمالي أجرة الرحلات", f"{driver_wage_total:.3f} د.ك"),
                ("مرحّل من الشهر الماضي", carry_text),
                ("إيراد الرحلات", f"{details['revenue']:.3f} د.ك"),
                ("العطل", f"{details['holiday']:.3f} د.ك ({holiday_state})"),
                ("مصاريف السيارة المختارة", f"{car_ded:.3f} د.ك"),
                ("مصاريف السائق المختارة", f"{driver_ded:.3f} د.ك"),
                ("حصة الإيراد/الرحلة", f"{share:.3f} د.ك"),
            ]
            summary_html = "".join(
                f"<tr class='summary'><td class='label'>{html.escape(safe_str(k))}</td>"
                f"<td class='value'>{html.escape(safe_str(v))}</td></tr>"
                for k, v in summary_pairs)

            report = f"""<html dir='rtl'><meta charset='utf-8'><style>{css}</style>
        <h1 class='title'>تقرير حصر راتب السائق</h1>
        <p class='subtitle'>الفترة: {html.escape(start_val)} إلى {html.escape(end_val)}</p>
        <p class='subtitle'>السيارات: {html.escape('، '.join(safe_str(c) for c in details['cars']) or '—')}</p>
        <div class='section'>
        <table class='summary'>{summary_html}</table>
        </div>
        <div class='section'>
        <h2>الرحلات</h2>
        <table>
        <tr><th>رقم السيارة</th><th>أجرة السائق</th><th>العطلة</th><th>السعر</th><th>مكان التنزيل</th><th>مكان التحميل</th><th>العميل</th><th>الشركة</th><th>رقم البيان</th><th>التاريخ</th><th>حجم الحاوية</th><th>رقم الضرب</th></tr>
        {trip_rows_html()}
        </table>
        </div>
        <div class='section'>
        <h2>مصاريف السيارة (تُخصم من الإيراد)</h2>
        <table>
        <tr><th>البند</th><th>المبلغ (د.ك)</th></tr>
        {expense_rows_html(car_vars)}
        </table>
        </div>
        <div class='section'>
        <h2>مصاريف السائق (تُخصم من الراتب)</h2>
        <table>
        <tr><th>البند</th><th>المبلغ (د.ك)</th></tr>
        {expense_rows_html(driver_vars)}
        </table>
        </div>
        <div class='net'>صافي الراتب: {net:.3f} د.ك — {td.salary_balance_state(net)}</div>
        </html>"""
            path = os.path.join(tempfile.gettempdir(), "salary_calculation_report.html")
            with open(path, "w", encoding="utf-8") as file:
                file.write(apply_a4_print_layout(report))
            webbrowser.open("file:///" + path.replace("\\", "/"))


        start_val = self.sal_vars.get("start_date", tk.StringVar()).get().strip()
        end_val = self.sal_vars.get("end_date", tk.StringVar()).get().strip()

        btn_row = tk.Frame(content_padded, bg=COLOR_BG)
        btn_row.pack(fill="x", pady=(0, 8))
        make_btn(btn_row, "حفظ الراتب", self.save_salary, variant="accent").pack(side="right", padx=4)
        make_btn(btn_row, "تحديث الحصر", redraw, variant="accent").pack(side="right", padx=4)
        make_btn(btn_row, "طباعة التقرير", print_report, variant="secondary").pack(side="right", padx=4)
        make_btn(btn_row, "طباعة تفاصيل الرحلات", lambda: self._print_salary_section("trips", driver, start_val, end_val), variant="secondary").pack(side="right", padx=4)
        make_btn(btn_row, "طباعة مصاريف السائق", lambda: self._print_salary_section("driver_expenses", driver, start_val, end_val), variant="secondary").pack(side="right", padx=4)
        make_btn(btn_row, "طباعة مصاريف السيارة", lambda: self._print_salary_section("car_expenses", driver, start_val, end_val), variant="secondary").pack(side="right", padx=4)
        self._salary_calc_redraw = redraw
        # سياق الحصر الحالي: يمنع إعادة الحساب لسائق قديم بعد تغيير النموذج.
        self._salary_calc_context = {"driver": driver, "start": start, "end": end}
        self._salary_calc_dirty = False
        redraw()

    def save_salary(self):
        data = {k: v.get().strip() for k, v in self.sal_vars.items()}
        start_date = data.get("start_date", "").strip()
        end_date = data.get("end_date", "").strip()
        if not data.get("driver") or not start_date or not end_date:
            messagebox.showwarning("تنبيه", "الرجاء اختيار السائق وإدخال الفترة من وإلى.",
                                   parent=self)
            return
        if start_date:
            data["month"] = start_date[:7]
        # حفظ الفترة مع السجل: نستعملها لاحقاً لاستبعاد ما احتُسب هنا من
        # الرحلات والمصاريف، فلا يُحتسب مرتين في راتب جديد لنفس السائق.
        data["period_from"] = start_date
        data["period_to"] = end_date
        data["paid"] = self._salary_paid_value if self.salary_editing_id is not None else "لا"
        calculated = getattr(self, "_salary_calculated_details", None)
        if calculated and self._salary_calc_context.get("driver") == data["driver"]:
            data["_calculated_details"] = dict(calculated)
        try:
            td.save_salary(data, editing_id=self.salary_editing_id)
        except ValueError as exc:
            messagebox.showwarning("تنبيه", str(exc), parent=self)
            return
        messagebox.showinfo("تم", "تم حفظ الراتب بنجاح. لن تدخل نفس الرحلات "
                                   "والمصاريف في راتب آخر لنفس السائق في هذه الفترة.",
                            parent=self)
        self.clear_salary_form()
        self.refresh_salary_list()
        refresh_related_screens(self)

    def clear_salary_form(self):
        for var in self.sal_vars.values():
            var.set("")
        self.sal_vars["salary_type"].set("رحلة")
        self.salary_editing_id = None
        self._salary_paid_value = "لا"

    def recalculate_all_salaries(self):
        """إعادة حساب رواتب جميع السائقين للفترة المحددة.

        تحسب النتيجة أولاً بلا حفظ، فتعرضها في نافذة تأكيد تشرح العدد
        والإجمالي، فلا تُكتب في السجل إلا بموافقة المستخدم.
        """
        start_val = self.sal_vars.get("start_date", tk.StringVar()).get().strip()
        end_val = self.sal_vars.get("end_date", tk.StringVar()).get().strip()
        if not start_val or not end_val:
            messagebox.showwarning(
                "تنبيه", "أدخل تاريخي البداية والنهاية أولاً.", parent=self)
            return
        if start_val > end_val:
            messagebox.showwarning(
                "تنبيه", "تاريخ البداية يجب أن يسبق تاريخ النهاية.", parent=self)
            return
        every = ["طريقة كل سائق (المقترحة من سجله)"] + list(td.SALARY_METHOD_LABELS) + ["كل الطرق"]
        dialog = tk.Toplevel(self)
        dialog.title("إعادة حساب رواتب جميع السائقين")
        dialog.geometry("640x430")
        dialog.configure(bg=COLOR_BG)
        dialog.transient(self)
        center_dialog(dialog, self)
        body = tk.Frame(dialog, bg=COLOR_BG)
        body.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(body,
                 text=("تُحسب رواتب كل السائقين المسجّلين عن الفترة المختارة. "
                       "اختر «طريقة كل سائق» لحساب كل واحد بطريقته المعتادة، "
                       "أو اختر طريقة واحدة لتطبيقها على الجميع، أو «كل الطرق» "
                       "لتجربة جميع طرق الحساب على بيانات حقيقية."),
                 font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED, anchor="e",
                 justify="right", wraplength=600).pack(fill="x", pady=(0, 10))
        tk.Label(body, text="طريقة الحساب", font=F_LABEL, bg=COLOR_BG,
                 fg=COLOR_MUTED, anchor="e").pack(fill="x")
        method_var = tk.StringVar(value=every[0])
        ttk.Combobox(body, textvariable=method_var, values=every, state="readonly",
                     font=F_BODY, justify="right").pack(fill="x", ipady=4, pady=(0, 10))

        summary = tk.Label(body, text="", font=F_BOLD, bg=COLOR_BG, fg=COLOR_PRIMARY,
                           anchor="e", justify="right", wraplength=600)
        summary.pack(fill="x", pady=(0, 8))
        table_wrap = tk.Frame(body, bg=COLOR_BG)
        table_wrap.pack(fill="both", expand=True)
        tree = ttk.Treeview(table_wrap,
                            columns=("net", "share", "base", "type", "car_no", "driver"),
                            show="headings", selectmode="browse")
        for key, label, width in (
            ("net", "الصافي (د.ك)", 110), ("share", "الحصة (د.ك)", 100),
            ("base", "الأساسي", 90), ("type", "طريقة الحساب", 150),
            ("car_no", "السيارة", 90), ("driver", "السائق", 150),
        ):
            tree.heading(key, text=label)
            tree.column(key, anchor="e", width=width)
        tree.pack(fill="both", expand=True)
        apply_table_style(tree)
        state = {"rows": [], "errors": []}

    def run(save=False):
        choice = method_var.get().strip()
        wanted = "" if choice == every[0] else choice
        try:
            result = td.recalculate_all_driver_salaries(
                start_val, end_val, method=wanted, save=save)
        except Exception as exc:
            messagebox.showerror("إعادة الحساب", str(exc), parent=dialog)
            return
        state["rows"], state["errors"] = result["rows"], result["errors"]
        for item in tree.get_children():
            tree.delete(item)
        for row in state["rows"]:
            tree.insert("", "end", values=(
                f"{td.safe_float(row['net']):.3f}",
                f"{td.safe_float(row['share']):.3f}",
                f"{td.safe_float(row['base']):.3f}",
                safe_str(row["method"]), safe_str(row["car_no"]) or "—",
                safe_str(row["driver"])))
        summary.config(text=(
            f"السائقون: {result['drivers']} · سجلات الراتب: {result['records']} · "
            f"إجمالي الصافي: {result['total_net']:.3f} د.ك"
            + (f" · أخطاء: {len(state['errors'])}" if state["errors"] else "")))
        if save:
            self.refresh_salary_list()
            refresh_related_screens(self)
            messagebox.showinfo(
                "تم", f"تم حفظ {result['records']} سجل راتب.\n"
                      f"إجمالي الصافي: {result['total_net']:.3f} د.ك", parent=dialog)
            dialog.destroy()

        row = tk.Frame(body, bg=COLOR_BG)
        row.pack(fill="x", pady=(12, 0))
        make_btn(row, "احسب وعرض النتائج", lambda: run(False),
                 variant="secondary").pack(side="right", padx=4)
        make_btn(row, "احسب واحفظ الكل", lambda: run(True),
                 variant="accent").pack(side="right", padx=4)
        make_btn(row, "إغلاق", dialog.destroy, variant="secondary").pack(side="right", padx=4)
        run(False)

    def _print_salary_section(self, section, driver, start_val, end_val):
        import html, os, tempfile, webbrowser
        if section == "trips":
            tree = getattr(self, "_salary_trip_tree", None)
            if tree is None:
                return
            try:
                if not tree.winfo_exists():
                    return
            except tk.TclError:
                return
            headers = ["أجرة السائق", "العطلة", "السعر", "مكان التنزيل", "مكان التحميل", "العميل", "الشركة", "رقم البيان", "التاريخ", "حجم الحاوية", "رقم الضرب", "رقم السيارة"]
            rows = "".join("<tr>" + "".join(f"<td>{html.escape(safe_str(v))}</td>" for v in (tree.item(item, "values") or ())) + "</tr>" for item in tree.get_children())
            title = "تفاصيل الرحلات"
            table_title = "الرحلات"
        elif section == "car_expenses":
            tree = getattr(self, "_salary_car_detail_tree", None)
            if tree is None:
                return
            try:
                if not tree.winfo_exists():
                    return
            except tk.TclError:
                return
            headers = ["التاريخ", "السيارة", "البند", "التكلفة", "ملاحظات"]
            rows = ""
            for item in tree.get_children():
                vals = list(tree.item(item, "values") or ())
                while len(vals) < 5:
                    vals.append("")
                row_data = [vals[4], vals[3], vals[2], vals[1], vals[0]]
                rows += "<tr>" + "".join(f"<td>{html.escape(safe_str(v))}</td>" for v in row_data) + "</tr>"
            title = "تفاصيل مصاريف السيارة"
            table_title = "مصاريف السيارة"
        elif section == "driver_expenses":
            tree = getattr(self, "_salary_driver_detail_tree", None)
            if tree is None:
                return
            try:
                if not tree.winfo_exists():
                    return
            except tk.TclError:
                return
            headers = ["التاريخ", "السيارة", "البند", "التكلفة", "ملاحظات"]
            rows = ""
            for item in tree.get_children():
                vals = list(tree.item(item, "values") or ())
                while len(vals) < 5:
                    vals.append("")
                row_data = [vals[4], vals[3], vals[2], vals[1], vals[0]]
                rows += "<tr>" + "".join(f"<td>{html.escape(safe_str(v))}</td>" for v in row_data) + "</tr>"
            title = "تفاصيل مصاريف السائق"
            table_title = "مصاريف السائق"
        else:
            return
        headers_html = "".join(f"<th>{h}</th>" for h in headers)
        report = (f"<html dir='rtl'><meta charset='utf-8'><style>"
                 f"body{{font-family:Tahoma;padding:25px}}"
                 f"table{{width:100%;border-collapse:collapse}}"
                 f"td,th{{border:1px solid {PRINT_LINE};padding:7px;text-align:right}}"
                 f"th{{background:{PRINT_NAVY};color:white}}</style>"
                 f"<h1>{title}: {html.escape(safe_str(driver))}</h1>"
                 f"<p>الفترة: {safe_str(start_val)} إلى {safe_str(end_val)}</p>"
                 f"<h2>{table_title}</h2>"
                 f"<table><tr>{headers_html}</tr>{rows}</table></html>")
        path = os.path.join(tempfile.gettempdir(), f"salary_{section}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(apply_a4_print_layout(report))
        webbrowser.open("file:///" + path.replace("\\", "/"))

    def refresh_salary_list(self):
        for row in self.sal_tree.get_children():
            self.sal_tree.delete(row)
        self._salaries = td.load_salaries()
        # Upgrade only legacy rows. Re-saving every row here would discard the
        # exact period calculation captured by the salary calculator.
        for salary in self._salaries:
            if not any(safe_str(salary.get(key)).strip() for key in
                       ("trip_revenue", "holiday_revenue", "driver_wages", "car_expenses", "driver_expenses")):
                td.save_salary(dict(salary), editing_id=salary.get("id"))
        self._salaries = td.load_salaries()
        if hasattr(self, "salary_driver_filter_combo"):
            self.salary_driver_filter_combo.config(
                values=["الكل"] + [driver["name"] for driver in td.load_drivers()])
        query = self.salary_search_var.get().strip().lower()
        driver_filter = self.salary_driver_filter_var.get().strip()
        month_filter = self.salary_month_filter_var.get().strip().lower()
        for s in self._salaries:
            display_row = dict(s)
            if not safe_str(display_row.get("car_no")).strip():
                driver_name = safe_str(display_row.get("driver")).strip()
                assigned_car = next(
                    (safe_str(v.get("car_no")).strip() for v in td.load_vehicles()
                     if safe_str(v.get("car_no")).strip()
                     and td._normalized_driver_name(v.get("driver")) == td._normalized_driver_name(driver_name)),
                    "")
                display_row["car_no"] = assigned_car
            if ((driver_filter != "الكل" and safe_str(s.get("driver")).strip() != driver_filter)
                    or (month_filter and month_filter not in safe_str(s.get("month")).lower())
                    or (query and query not in " ".join(
                        safe_str(s.get(key, "")) for key, _label in self.salary_table_fields).lower())):
                continue
            self.sal_tree.insert(
                "", "end", iid=str(s["id"]),
                values=tuple(safe_str(display_row.get(k, "")) for k, _label in reversed(self.salary_table_fields)))

    def clear_salary_filters(self):
        self.salary_search_var.set("")
        self.salary_driver_filter_var.set("الكل")
        self.salary_month_filter_var.set("")
        self.refresh_salary_list()

    def _show_salary_detail(self):
        sel = self.sal_tree.selection()
        if not sel:
            self.salary_detail_title.set("اختر سجل راتب لعرض التفاصيل")
            return
        self._salaries = td.load_salaries()
        row = next((s for s in self._salaries if str(s["id"]) == sel[0]), None)
        if not row:
            self.salary_detail_title.set("اختر سجل راتب لعرض التفاصيل")
            return
        driver = safe_str(row.get("driver", ""))
        car = safe_str(row.get("car_no", ""))
        if not car:
            car = next(
                (safe_str(v.get("car_no")).strip() for v in td.load_vehicles()
                 if safe_str(v.get("car_no")).strip()
                 and td._normalized_driver_name(v.get("driver")) == td._normalized_driver_name(driver)),
                "")
        # جدول التفاصيل يعرض ما في السجل مباشرة بلا إعادة حساب، فيطابق ما
        # في الجدول أعلاه تماماً.
        for key, var in self.salary_detail_vars.items():
            var.set(safe_str(row.get(key, "")) or "—")
        net = td.safe_float(row.get("net_salary"))
        state = safe_str(row.get("balance_state", "")) or td.salary_balance_state(net)
        self.salary_detail_vars["balance_state"].set(state)
        self.salary_detail_title.set(
            f"تفاصيل سجل رقم {row.get('id', '')} — {driver}"
            f"{(' (' + car + ')') if car else ''}")
        net_label = self._salary_detail_cells.get("net_salary")
        if net_label is not None:
            net_label.config(
                fg=COLOR_DANGER if state == "مدين" else
                (COLOR_SUCCESS if state == "دائن" else COLOR_TEXT))
        state_label = self._salary_detail_cells.get("balance_state")
        if state_label is not None:
            state_label.config(
                fg=COLOR_DANGER if state == "مدين" else
                (COLOR_SUCCESS if state == "دائن" else COLOR_TEXT))

    def view_salary_details(self):
        sel = self.sal_tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار سجل راتب أولاً.")
            return
        row = next((s for s in self._salaries if str(s["id"]) == sel[0]), None)
        if not row:
            return
        self.show_page("salaries")
        if hasattr(self, "_salaries_notebook"):
            self._salaries_notebook.select(0)
        for key, var in self.sal_vars.items():
            var.set(safe_str(row.get(key, "")))
        saved_driver = safe_str(row.get("driver", "")).strip()
        if saved_driver:
            self.sal_vars["driver"].set(saved_driver)
            self._on_driver_changed()
        month = safe_str(row.get("month", "")).strip()
        if month and not self.sal_vars.get("start_date", tk.StringVar()).get().strip():
            try:
                year, month_no = map(int, month.split("-"))
                from datetime import date
                first = date(year, month_no, 1)
                if month_no == 12:
                    last = date(year, 12, 31)
                else:
                    last = date(year, month_no + 1, 1) - timedelta(days=1)
                self.sal_vars["start_date"].set(first.isoformat())
                self.sal_vars["end_date"].set(last.isoformat())
            except Exception as _log_exc: log_exception("view_salary_details", _log_exc)
        self.salary_editing_id = row["id"]
        self._salary_paid_value = safe_str(row.get("paid", "لا")) or "لا"
        if hasattr(self, "sal_car_combo"):
            saved_car = safe_str(row.get("car_no", "")).strip()
            if saved_car:
                values = list(self.sal_car_combo.cget("values"))
                if saved_car in values:
                    self.sal_vars["car_no"].set(saved_car)
                    self._on_car_changed()

    def toggle_salary_paid(self):
        sel = self.sal_tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار سجل راتب أولاً.")
            return
        row_id = sel[0]
        row = next((s for s in self._salaries if str(s["id"]) == row_id), None)
        if row:
            current = safe_str(row.get("paid", "لا")).strip()
            row["paid"] = "لا" if current == "نعم" else "نعم"
            td.save_salary(row, editing_id=row_id)
            self.refresh_salary_list()

    def load_salary_for_edit(self):
        sel = self.sal_tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار سجل راتب أولاً.",
                                parent=self)
            return
        row = next((s for s in self._salaries if str(s["id"]) == sel[0]), None)
        if not row:
            return
        # «السلف» و«العمولات» لم يعُدا حقولاً في النموذج، فنتجاهلهما عند
        # التحميل حتى لا نكتبهما في متغيرات محذوفة.
        for key, var in self.sal_vars.items():
            if key in ("commission_total", "advances"):
                continue
            var.set(safe_str(row.get(key, "")))
        self.salary_editing_id = row["id"]
        self._salary_paid_value = safe_str(row.get("paid", "لا")) or "لا"
        # الانتقال إلى تبويب «حساب راتب السائق»: بلا ذلك يبقى المستخدم في
        # السجل بعد التعديل فلا يرى ما كتبه، فيبدو أن الزر لم يفعل شيئاً.
        if getattr(self, "_salaries_notebook", None) is not None:
            self._salaries_notebook.select(0)
        self._salary_driver_changed()
        messagebox.showinfo("تعديل", "تم تحميل السجل في نموذج إعداد الراتب.",
                            parent=self)

    def print_salaries_summary(self):
        # نفس أعمدة جدول السجل، فتلتقي المطبوعة مع المعروض ولا تظهر
        # «السلف» أو «العمولات» بعد حذفهما من الشاشتين.
        fields = [field for field in self.salary_table_fields
                  if field[0] not in ("notes",)]
        generate_and_open_summary_print("الرواتب", fields, self._salaries)

    def print_selected_salary(self):
        sel = self.sal_tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار سجل راتب أولاً.")
            return
        row = next((s for s in self._salaries if str(s["id"]) == sel[0]), None)
        if row:
            fields = [(key, label) for key, label in td.SALARY_FIELDS]
            generate_and_open_summary_print("الراتب المحدد", fields, [row])

    def delete_salary_row(self):
        sel = self.sal_tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار سجل أولاً.")
            return
        if messagebox.askyesno("تأكيد الحذف", "هل تريد حذف سجل الراتب هذا؟"):
            td.delete_salary(sel[0])
            self.refresh_salary_list()
            refresh_related_screens(self)
