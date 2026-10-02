# -*- coding: utf-8 -*-
"""إطار CRUD عام: نموذج إدخال + جدول + بحث + مرفقات."""

import os, shutil
from datetime import date
from datetime import datetime
from tkinter import filedialog
from tkinter import messagebox
from tkinter import simpledialog
import tkinter as tk
from tkinter import ttk
from . import data as td
from .app_config import COLOR_BG, COLOR_BORDER, COLOR_CARD, COLOR_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_TEXT, FONT_NAME, F_BODY, F_LABEL
from .app_registry import _ALL_CRUD_TABS
from .ui_helpers import _join_multiselect, _split_multiselect, log_exception, safe_str
from .ui_widgets import apply_table_style, card_frame, center_dialog, make_btn, tooltip
from .driver_links import bind_driver_type_cascade, driver_link_keys_in, ensure_driver_link_fields
from .ui_dialogs import date_input
from .print_statement import generate_and_open_summary_print
from .ui_text_edit import refresh_related_screens


# ==================================================================
# إطار عام قابل لإعادة الاستخدام: نموذج إدخال + جدول + بحث + أزرار
# ==================================================================
class CrudTab:
    """
    شاشة عامة لإدارة جدول بسيط: بطاقة إدخال أعلى الصفحة + جدول أسفل مع بحث.
    key_field: اسم الحقل الذي يُستخدم كمفتاح فريد (يُستخدم أيضاً كعمود بحث افتراضي).
    """

    def __init__(self, parent, fields, load_fn, save_fn, delete_fn, key_field,
                 title, select_fields=None, extra_buttons=None, readonly_fields=None,
                 multiselect_fields=None, cols_per_row=4, frame=None, filter_fn=None,
                 show_edit_button=True, compact_filters=False, print_mode="default",
                 attachment_entity_type=None, attachment_fields=None,
                 show_upload_button=True, multiselect=False, single_row=False,
                 date_fields=None, narrow_fields=None, default_values=None,
                 attachment_inline=False, attachment_inline_after="total",
                 narrow_widths=None, hide_fields=None, stretch_fields=False,
                 actions_on_own_row=False):
        self.parent = parent
        # واجهة CRUD تستخدم المفتاح والتسمية فقط حتى لو احتوى التعريف
        # على بيانات وصفية إضافية في إصدار سابق.
        self.fields = ensure_driver_link_fields(
            [(field[0], field[1]) for field in fields])
        self.load_fn = load_fn
        self.save_fn = save_fn
        self.delete_fn = delete_fn
        self.key_field = key_field
        self.title = title
        self.select_fields = select_fields or {}   # key -> list of options
        self.multiselect_fields = multiselect_fields or {}  # key -> list of options
        # أي شاشة تحوي الثلاثية (نوع السائق/السائق/السيارة) تُعامَل كسلسلة مترابطة:
        # قوائمها تصبح Combobox تلقائياً، وتُفعَّل التصفية بتغيير نوع السائق.
        self.driver_link = driver_link_keys_in(self.fields)
        if self.driver_link:
            self.select_fields.setdefault("driver_type", [""] + list(td.DRIVER_TYPES))
            self.select_fields.setdefault("driver", td.driver_names_by_type())
            self.select_fields.setdefault("car_no", [v["car_no"] for v in td.load_vehicles()])

        self.readonly_fields = readonly_fields or []
        self.cols_per_row = cols_per_row
        self.editing_key = None
        self.vars = {}
        self.entries = {}
        self.combos = {}
        self.multiselect_vars = {}
        self.attachment_controls = {}
        self.on_data_changed = None
        self.filter_fn = filter_fn
        self.filter_rows = None
        self.extra_buttons = list(extra_buttons or ())
        self.show_edit_button = show_edit_button
        self.compact_filters = compact_filters
        self.print_mode = print_mode
        self.attachment_entity_type = attachment_entity_type or title
        self.attachment_fields = attachment_fields or []
        self.show_upload_button = show_upload_button
        self.multiselect = multiselect
        self.single_row = single_row
        # أزرار الجدول في صف مستقل أسفل شريط البحث بدل مزاحمته له. استُخدم في
        # السجلات كثيرة الأزرار كسجل مصاريف السائقين، فكان الصف يتزاحم.
        self.actions_on_own_row = actions_on_own_row
        self.date_fields = set(date_fields or ("date", "license_expiry", "start_date", "end_date"))
        self.narrow_fields = set(narrow_fields or ())
        self.default_values = dict(default_values or {})
        self.narrow_widths = dict(narrow_widths or {})
        self.hide_fields = set(hide_fields or ())
        # عند التفعيل: خلايا النموذج تتمدد لتغطي كامل عرض الشاشة
        # (توزيع متساوٍ بدل العرض الثابت الضيق).
        self.stretch_fields = stretch_fields
        self.attachment_inline = attachment_inline
        self.attachment_inline_after = attachment_inline_after
        self.attachment_counts = {}
        self._temp_attachment_key = None
        # Universal register filters.  They are deliberately data-driven so
        # every CRUD register receives filters for its own columns.
        self.register_date_from_var = tk.StringVar()
        self.register_date_to_var = tk.StringVar()
        self.register_filter_field_var = tk.StringVar(value="الكل")
        self.register_filter_value_var = tk.StringVar()

        self.frame = frame or tk.Frame(parent, bg=COLOR_BG)
        _ALL_CRUD_TABS.append(self)
        self._build_form()
        # الربط المتسلسل: نوع السائق يصفّي السائقين، والسائق يحدّد السيارة.
        if self.driver_link:
            try:
                bind_driver_type_cascade(
                    self.vars, self.combos,
                    get_day=lambda: self.vars.get("date", tk.StringVar()).get().strip())
            except Exception as _log_exc:
                log_exception("ربط حقول السائق", _log_exc)

        self._build_table()
        # إذا كانت هناك علاقة منطقية بين حقل الساطحة ونوعها، اربط تمكين/تعطيل combobox الخاص بنوع الساطحة
        try:
            if "is_flatbed" in self.vars and "flatbed_type" in self.combos:
                def _on_flatbed_change(*_a):
                    val = self.vars["is_flatbed"].get()
                    state = "normal" if val == "نعم" else "disabled"
                    try:
                        self.combos["flatbed_type"].config(state=state)
                    except Exception as _log_exc: log_exception("_on_flatbed_change", _log_exc)
                # تتبع التغيير
                self.vars["is_flatbed"].trace_add("write", _on_flatbed_change)
                _on_flatbed_change()
        except Exception as _log_exc: log_exception("__init__", _log_exc)

        self.refresh()

    def _build_form(self):
        card = card_frame(self.frame, f"إضافة / تعديل — {self.title}")
        card.pack(fill="x", padx=18, pady=(18, 8))
        box = card.body
        form = tk.Frame(box, bg=COLOR_CARD)
        form.pack(fill="x", padx=18, pady=(0, 8))

        form_fields = [(key, label) for key, label in self.fields
                       if key not in self.hide_fields]
        cols_per_row = len(form_fields) if self.single_row else self.cols_per_row
        compact = cols_per_row == len(form_fields)
        cell_padx = 4 if compact else 8
        cell_pady = 4 if compact else 7
        label_font = (FONT_NAME, 8) if compact else F_LABEL
        entry_ipady = 2 if compact else 4
        # عند دمج المرفقات داخل صف الإدخال نضيف خلية إضافية لزر الملفات
        # بعد حقل معين (الإجمالي افتراضياً) ليظهر بين الإجمالي وملاحظات.
        inline_keys = [key for key, _label in form_fields]
        extra_cells = 1 if (self.attachment_inline and self.attachment_fields) else 0
        total_cells = len(form_fields) + extra_cells
        if self.single_row:
            cols_per_row = total_cells
        for idx, (key, label) in enumerate(form_fields):
            visual_idx = idx
            if extra_cells:
                try:
                    after_pos = inline_keys.index(self.attachment_inline_after)
                except ValueError:
                    after_pos = total_cells - 2
                if idx > after_pos:
                    visual_idx = idx + 1
            r, c = divmod(visual_idx, cols_per_row)
            # عكس ترتيب الأعمدة لضمان تدفق الحقول من اليمين لليسار
            c = cols_per_row - 1 - c
            cell = tk.Frame(form, bg=COLOR_CARD)
            cell.grid(row=r, column=c, padx=cell_padx, pady=cell_pady, sticky="ew")
            tk.Label(cell, text=label, font=label_font, bg=COLOR_CARD, fg=COLOR_MUTED,
                     anchor="e", justify="right").pack(fill="x", pady=(0, 3))
            var = tk.StringVar()
            if key in self.multiselect_fields:
                option_vars = {}

                def sync_options(*_args, field_key=key, value_var=var, variables=option_vars):
                    selected = set(_split_multiselect(value_var.get()))
                    for option, option_var in variables.items():
                        option_var.set(option in selected)

                def save_options(field_key=key, value_var=var, variables=option_vars):
                    value_var.set(_join_multiselect(option for option, option_var in variables.items() if option_var.get()))

                options_frame = tk.Frame(cell, bg=COLOR_CARD)
                options_frame.pack(fill="x")
                for option in self.multiselect_fields[key]:
                    option_var = tk.BooleanVar()
                    option_vars[option] = option_var
                    tk.Checkbutton(options_frame, text=option, variable=option_var, command=save_options,
                                   font=F_LABEL, bg=COLOR_CARD, anchor="e").pack(side="right", padx=3)
                var.trace_add("write", sync_options)
                self.multiselect_vars[key] = option_vars
            elif key in self.select_fields:
                vals = self.select_fields[key]
                # إذا كان الحقل منطقي (نعم/لا) نعرض Checkbutton بدلاً من Combobox
                if isinstance(vals, list) and vals == ["نعم", "لا"]:
                    cb = tk.Checkbutton(cell, variable=var, onvalue="نعم", offvalue="لا",
                                        bg=COLOR_CARD, anchor="e")
                    cb.pack(fill="x", ipady=entry_ipady - 2)
                    var.set("لا")
                else:
                    if self.stretch_fields or key not in self.narrow_fields:
                        entry = ttk.Combobox(cell, textvariable=var, values=vals,
                                              font=F_BODY, justify="right", state="normal",
                                              height=8)
                        entry.pack(fill="x", ipady=entry_ipady)
                    else:
                        entry = ttk.Combobox(cell, textvariable=var, values=vals,
                                              font=F_BODY, justify="right", state="normal",
                                              height=8,
                                              width=self.narrow_widths.get(key, 8))
                        entry.pack(anchor="e", ipady=entry_ipady)
                    tooltip(entry, label)
                    self.combos[key] = entry
                    entry.bind("<<ComboboxSelected>>", lambda _event: refresh_related_screens(self.frame), add="+")
                    entry.bind("<FocusOut>", lambda _event: refresh_related_screens(self.frame), add="+")
            elif key in self.date_fields:
                if self.stretch_fields:
                    date_frame = date_input(cell, var, ipady=entry_ipady)
                else:
                    narrow_w = self.narrow_widths.get(key, 10)
                    date_frame = date_input(cell, var, ipady=entry_ipady,
                                            **({"shrink": True, "width": narrow_w} if key in self.narrow_fields else {}))
                if key != "end_date" and not var.get().strip():
                    var.set(date.today().isoformat())
            else:
                state = "readonly" if key in self.readonly_fields else "normal"
                entry = tk.Entry(cell, textvariable=var, font=F_BODY, justify="right",
                                  state=state, relief="flat", bd=0,
                                  highlightthickness=2,
                                  highlightbackground=COLOR_BORDER,
                                  highlightcolor=COLOR_PRIMARY_LIGHT,
                                  insertbackground=COLOR_TEXT)
                if key in self.narrow_fields and not self.stretch_fields:
                    entry.configure(width=self.narrow_widths.get(key, 8))
                    entry.pack(anchor="e", ipady=entry_ipady)
                else:
                    entry.pack(fill="x", ipady=entry_ipady)
                tooltip(entry, label)
                self.entries[key] = entry
            self.vars[key] = var
        for c in range(cols_per_row):
            form.grid_columnconfigure(c, weight=1)

        # خلية زر الملفات داخل نفس صف الإدخال (بين الإجمالي وملاحظات)
        if extra_cells:
            try:
                after_pos = inline_keys.index(self.attachment_inline_after)
            except ValueError:
                after_pos = total_cells - 2
            r, c = divmod(after_pos + 1, cols_per_row)
            c = cols_per_row - 1 - c
            attach_cell = tk.Frame(form, bg=COLOR_CARD)
            attach_cell.grid(row=r, column=c, padx=cell_padx, pady=cell_pady, sticky="ew")
            tk.Label(attach_cell, text="ملفات", font=label_font, bg=COLOR_CARD,
                     fg=COLOR_MUTED, anchor="e", justify="right").pack(fill="x", pady=(0, 3))
            attach_controls = tk.Frame(attach_cell, bg=COLOR_CARD)
            attach_controls.pack(fill="x", anchor="e")
            category_key, category_label = self.attachment_fields[0]
            make_btn(attach_controls, "إضافة ملفات",
                     lambda event_category=category_key: self.attach_files(event_category),
                     variant="secondary", padx=5, pady=1).pack(side="right", padx=(0, 3))
            make_btn(attach_controls, "عرض",
                     lambda event_category=category_key: self.open_attachment_manager(event_category),
                     variant="secondary", padx=5, pady=1).pack(side="right", padx=(3, 0))
            inline_count_var = tk.StringVar(value="لا توجد ملفات")
            tk.Label(attach_cell, textvariable=inline_count_var, font=(FONT_NAME, 7),
                     bg=COLOR_CARD, fg=COLOR_MUTED, anchor="e").pack(anchor="e")
            # ربط العدّاد الداخلي بعدّاد الشريط السفلي (إن وجد) عبر نفس المتغير
            self.attachment_counts[category_key] = inline_count_var

        if self.attachment_fields and not self.attachment_inline:
            attachment_bar = tk.Frame(box, bg=COLOR_CARD)
            attachment_bar.pack(fill="x", padx=18, pady=(0, 6))
            for category_key, category_label in self.attachment_fields:
                category_frame = tk.Frame(attachment_bar, bg=COLOR_CARD)
                category_frame.pack(side="right", padx=5, pady=2)
                tk.Label(category_frame, text=category_label, font=(FONT_NAME, 8, "bold"),
                         bg=COLOR_CARD, fg=COLOR_PRIMARY, anchor="e").pack(anchor="e")
                controls = tk.Frame(category_frame, bg=COLOR_CARD)
                controls.pack(fill="x", anchor="e")
                add_btn = make_btn(controls, "إضافة ملفات", lambda event_category=category_key: self.attach_files(event_category),
                                   variant="secondary", padx=5, pady=1)
                add_btn.pack(side="right", padx=(0, 3))
                manage_btn = make_btn(controls, "عرض الملفات", lambda event_category=category_key: self.open_attachment_manager(event_category),
                                      variant="secondary", padx=5, pady=1)
                manage_btn.pack(side="right", padx=(3, 0))
                count_var = tk.StringVar(value="لا توجد ملفات")
                count_label = tk.Label(category_frame, textvariable=count_var, font=(FONT_NAME, 7),
                                       bg=COLOR_CARD, fg=COLOR_MUTED, anchor="e")
                count_label.pack(anchor="e")
                self.attachment_counts[category_key] = count_var
                self.attachment_controls[category_key] = (add_btn, manage_btn, count_label)
            self._attachment_message_var = tk.StringVar()
            message_label = tk.Label(attachment_bar, textvariable=self._attachment_message_var,
                                     font=(FONT_NAME, 8), bg=COLOR_CARD, fg=COLOR_MUTED, anchor="e")
            message_label.pack(side="left", padx=8)

        btns = tk.Frame(box, bg=COLOR_CARD)
        btns.pack(fill="x", padx=18, pady=(4, 14), anchor="e")
        self.save_btn = make_btn(btns, "حفظ", self.on_save, variant="accent")
        self.save_btn.pack(side="right", padx=4)
        tooltip(self.save_btn, "حفظ البيانات")
        self.clear_btn = make_btn(btns, "مسح الحقول", self.clear_form, variant="secondary")
        self.clear_btn.pack(side="right", padx=4)
        tooltip(self.clear_btn, "مسح جميع الحقول")

    def refresh_driver_options(self):
        """تحديث قوائم السائق/السيارة مع الحفاظ على القيم المختارة.

        تُستدعى بعد أي تغيير في سجل السائقين أو السيارات حتى لا تبقى قوائم
        الاختيار في الشاشات الأخرى تحمل أسماء أو سيارات لم تعد موجودة.
        """
        if not getattr(self, "driver_link", ()):
            return
        try:
            names = td.driver_names_by_type()
            cars = [v["car_no"] for v in td.load_vehicles() if v.get("car_no")]
            self.select_fields["driver"] = names
            self.select_fields["car_no"] = cars
            driver_combo = self.combos.get("driver")
            if driver_combo is not None:
                driver_combo.config(values=names)
            car_combo = self.combos.get("car_no")
            if car_combo is not None:
                car_combo.config(values=cars)
            # إعادة تطبيق التصفية إن كان النوع محدداً، فتبقى القائمة متسقة معه.
            type_var = self.vars.get("driver_type")
            if type_var is not None and type_var.get().strip():
                allowed = td.driver_names_by_type(type_var.get().strip())
                if driver_combo is not None:
                    driver_combo.config(values=allowed)
                current = self.vars["driver"].get().strip()
                if not (current and current in allowed):
                    self.vars["driver"].set("")
        except Exception as exc:
            log_exception("تحديث خيارات السائق", exc)

    def _build_table(self):
        card = card_frame(self.frame, f"سجل {self.title}")
        card.pack(fill="both", expand=True, padx=18, pady=(8, 18))
        box = card.body

        # شريط البحث/الفلاتر/الأزرار — صف واحد مضغوط في وضع single_row
        search_frame = tk.Frame(box, bg=COLOR_CARD)
        search_frame.pack(fill="x", padx=8, pady=(0, 6))
        tk.Label(search_frame, text="بحث", font=F_BODY, bg=COLOR_CARD, fg=COLOR_MUTED).pack(
            side="right", padx=(2, 3) if self.single_row else (4, 8))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=F_BODY,
                 justify="right", relief="flat", bd=0,
                 highlightthickness=2, highlightbackground=COLOR_BORDER,
                 highlightcolor=COLOR_PRIMARY_LIGHT, width=8 if self.single_row else 14)
        search_entry.pack(side="right", ipady=3 if self.single_row else 4)

        extra_filters = getattr(self, "_build_extra_filters", None)
        if callable(extra_filters):
            extra_filters(search_frame)
        else:
            self._build_register_filters(search_frame)

        # كل الأزرار وحقول الإدخال في صف واحد: البحث والفلاتر على اليمين
        # والأزرار على الشمال داخل نفس شريط البحث. أما السجلات التي تكثر
        # أزرارها فتطلب صفاً مستقلاً لها فتبقى مقروءة.
        separate_actions = self.single_row and self.actions_on_own_row
        if not self.single_row or separate_actions:
            actions_parent = tk.Frame(box, bg=COLOR_CARD)
            actions_parent.pack(fill="x", padx=18, pady=(0, 8), anchor="e")
        else:
            actions_parent = search_frame
        actions = tk.Frame(actions_parent, bg=COLOR_CARD)
        if not self.single_row or separate_actions:
            actions.pack(side="right", padx=(8, 0))
        else:
            actions.pack(side="left")
        self.actions_frame = actions
        # أزرار إضافية تمرّرها الشاشة (نص، دالة، نمط) وتظهر مع بقية أزرار الجدول.
        for label, command, variant in (self.extra_buttons or ()):
            make_btn(actions, label, command, variant=variant or "secondary",
                     padx=4, pady=2).pack(side="right", padx=2)
        if self.show_edit_button:
            make_btn(actions, "تعديل المحدد", self.load_selected_into_form, variant="secondary",
                     padx=4, pady=2).pack(side="right", padx=2)
        if "end_date" in {key for key, _label in self.fields}:
            make_btn(actions, "إنهاء اليوم", self.end_selected_relation, variant="secondary",
                     padx=4, pady=2).pack(side="right", padx=2)
        make_btn(actions, "الملفات", self.open_attachments, variant="secondary",
                 padx=4, pady=2).pack(side="right", padx=2)
        if self.show_upload_button:
            make_btn(actions, "رفع ملف", self.attach_selected_file, variant="accent",
                     padx=4, pady=2).pack(side="right", padx=2)
        make_btn(actions, "حذف المحدد", self.delete_selected, variant="danger",
                 padx=4, pady=2).pack(side="right", padx=2)
        if self.print_mode == "dialog":
            make_btn(actions, "طباعة", self.open_print_dialog, variant="secondary",
                     padx=4, pady=2).pack(side="right", padx=2)
        elif self.print_mode == "combined":
            make_btn(actions, "طباعة", self.print_selected_or_filtered, variant="secondary",
                     padx=4, pady=2).pack(side="right", padx=2)
        else:
            make_btn(actions, "طباعة", self.print_selected_or_filtered, variant="secondary",
                     padx=4, pady=2).pack(side="right", padx=2)

        table_wrap = tk.Frame(box, bg=COLOR_CARD)
        table_wrap.pack(fill="both", expand=True, padx=18)
        cols = [k for k, _ in reversed(self.fields)]
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings",
                                 selectmode="extended" if self.multiselect else "browse")
        for k, label in reversed(self.fields):
            self.tree.heading(k, text=label)
            width = 110 if k in ("trip_category", "direction", "origin", "destination", "customer") else 95
            self.tree.column(k, anchor="center", width=width, stretch=True)
        vs = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        hs = ttk.Scrollbar(table_wrap, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        # الشريط العمودي على اليمين كما في الواجهات العربية.
        vs.pack(side="right", fill="y")
        hs.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        apply_table_style(self.tree)
        self.tree.bind("<Double-1>", lambda e: self.load_selected_into_form())
        self.tree.bind("<Configure>", lambda e: self._auto_size_columns())

    def _selected_attachment_key(self, show_warning=True):
        if getattr(self, "editing_key", None):
            return str(self.editing_key)
        selection = self.tree.selection()
        if not selection:
            return None
        row = self._tree_row_map.get(selection[0])
        if row is None:
            return None
        key = safe_str(row.get(self.key_field)).strip()
        return key or None

    def _attachment_category_label(self, category_key):
        return dict(self.attachment_fields).get(category_key, category_key)

    def _refresh_attachment_counts(self, record_key=None):
        if not self.attachment_fields:
            return
        if record_key is None:
            record_key = self.editing_key
        if not record_key:
            for category_key, count_var in self.attachment_counts.items():
                count_var.set("لا توجد ملفات")
            return
        try:
            items = td.load_attachments(self.attachment_entity_type, str(record_key))
        except Exception:
            items = []
        for category_key, count_var in self.attachment_counts.items():
            label = self._attachment_category_label(category_key)
            count = sum(1 for item in items if safe_str(item.get("notes")).strip() == label)
            count_var.set(f"{count} ملف" if count else "لا توجد ملفات")

    def attach_files(self, category_key):
        category_label = self._attachment_category_label(category_key)
        sources = filedialog.askopenfilenames(
            parent=self.frame,
            title=f"إضافة ملفات — {category_label}",
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
        record_key = self._selected_attachment_key(show_warning=False)
        if not record_key:
            record_key = safe_str(getattr(self, "editing_key", "") or "").strip()
            if not record_key:
                if getattr(self, "_temp_attachment_key", None):
                    record_key = self._temp_attachment_key
                else:
                    manual_key = ""
                    for field_key, _ in self.fields:
                        if field_key == self.key_field:
                            continue
                        value = safe_str(self.vars.get(field_key, tk.StringVar()).get()).strip()
                        if value:
                            manual_key = value
                            break
                    record_key = manual_key or f"temp_{int(datetime.now().timestamp())}"
                    self._temp_attachment_key = record_key
        added = 0
        errors = []
        for source in sources:
            try:
                td.add_attachment(self.attachment_entity_type, record_key, source, notes=category_label)
                added += 1
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
        if errors:
            messagebox.showerror("إضافة الملفات", "تمت إضافة بعض الملفات أو تعذر إضافتها:\n" + "\n".join(errors), parent=self.frame)
        else:
            messagebox.showinfo("المرفقات", f"تمت إضافة {added} ملف/ملفات.", parent=self.frame)
        self._refresh_attachment_counts(record_key)

    def attach_selected_file(self):
        category_label = self.title
        source = filedialog.askopenfilename(
            parent=self.frame,
            title=f"رفع ملف — {self.title}",
            filetypes=[
                ("المستندات والصور", (
                    "*.pdf", "*.doc", "*.docx", "*.xls", "*.xlsx",
                    "*.jpg", "*.jpeg", "*.png",
                )),
                ("كل الملفات", "*.*"),
            ],
        )
        if not source:
            return
        record_key = self._selected_attachment_key(show_warning=False)
        if not record_key:
            record_key = safe_str(getattr(self, "editing_key", "") or "").strip()
            if not record_key:
                if getattr(self, "_temp_attachment_key", None):
                    record_key = self._temp_attachment_key
                else:
                    manual_key = ""
                    for field_key, _ in self.fields:
                        if field_key == self.key_field:
                            continue
                        value = safe_str(self.vars.get(field_key, tk.StringVar()).get()).strip()
                        if value:
                            manual_key = value
                            break
                    record_key = manual_key or f"temp_{int(datetime.now().timestamp())}"
                    self._temp_attachment_key = record_key
        notes = simpledialog.askstring(
            "نوع المستند",
            "اكتب نوع المستند (مثال: رخصة القيادة، البطاقة المدنية، جواز السفر):",
            parent=self.frame,
        )
        if notes is None:
            return
        try:
            item = td.add_attachment(
                self.attachment_entity_type, record_key, source, notes=notes.strip())
        except (OSError, ValueError) as exc:
            messagebox.showerror("رفع الملف", str(exc), parent=self.frame)
            return
        messagebox.showinfo("المرفقات", f"تم رفع الملف: {item['file_name']}", parent=self.frame)
        self._refresh_attachment_counts(record_key)

    def open_attachments(self):
        self.open_attachment_manager(None)

    def open_attachment_manager(self, category_key=None):
        category_label = None if category_key is None else self._attachment_category_label(category_key)
        dialog = tk.Toplevel(self.frame)
        dialog.title(f"ملفات — {self.title}")
        dialog.geometry("820x430")
        dialog.configure(bg=COLOR_BG)
        dialog.transient(self.frame)
        dialog.grab_set()
        center_dialog(dialog, self.frame)
        record_key = self._selected_attachment_key(show_warning=False)
        if not record_key:
            record_key = safe_str(getattr(self, "editing_key", "") or "").strip()
            if not record_key:
                if getattr(self, "_temp_attachment_key", None):
                    record_key = self._temp_attachment_key
                else:
                    manual_key = ""
                    for field_key, _ in self.fields:
                        if field_key == self.key_field:
                            continue
                        value = safe_str(self.vars.get(field_key, tk.StringVar()).get()).strip()
                        if value:
                            manual_key = value
                            break
                    record_key = manual_key or f"temp_{int(datetime.now().timestamp())}"
                    self._temp_attachment_key = record_key
        tree = ttk.Treeview(
            dialog, columns=("type", "name", "by", "at"), show="headings", selectmode="browse")
        for key, label, width in (
            ("type", "نوع المستند", 190), ("name", "الملف", 300),
            ("by", "أضافه", 120), ("at", "التاريخ", 150)
        ):
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor="e")
        tree.bind("<Double-1>", lambda _event: open_file())
        tree.pack(fill="both", expand=True, padx=14, pady=14)

        def reload_items():
            for item_id in tree.get_children():
                tree.delete(item_id)
            all_items = td.load_attachments(self.attachment_entity_type, str(record_key))
            items = [item for item in all_items if category_label is None or safe_str(item.get("notes")).strip() == category_label]
            for item in items:
                tree.insert("", "end", iid=str(item["id"]),
                            values=(item["notes"], item["file_name"],
                                    item["created_by"], item["created_at"]))
            return items

        items = reload_items()

        def selected_item():
            selection = tree.selection()
            if not selection:
                messagebox.showinfo("المرفقات", "اختر ملفاً أولاً.", parent=dialog)
                return None
            return next((item for item in items if str(item["id"]) == selection[0]), None)

        def open_file():
            item = selected_item()
            if not item:
                return
            if not os.path.isfile(item["path"]):
                messagebox.showerror("فتح الملف", "الملف غير موجود في مجلد المرفقات.", parent=dialog)
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
                messagebox.showerror("تنزيل الملف", "الملف غير موجود في مجلد المرفقات.", parent=dialog)
                return
            target = filedialog.asksaveasfilename(
                parent=dialog, title="تنزيل نسخة من الملف",
                initialfile=item["file_name"],
            )
            if not target:
                return
            try:
                shutil.copy2(item["path"], target)
            except OSError as exc:
                messagebox.showerror("تنزيل الملف", str(exc), parent=dialog)
                return
            messagebox.showinfo("المرفقات", "تم تنزيل نسخة الملف بنجاح.", parent=dialog)

        def replace_file():
            item = selected_item()
            if not item:
                return
            source = filedialog.askopenfilename(
                parent=dialog, title="اختيار الملف البديل",
                filetypes=[("كل الملفات", "*.*")],
            )
            if not source:
                return
            try:
                replacement = td.add_attachment(
                    self.attachment_entity_type, record_key, source,
                    notes=safe_str(item.get("notes")).strip() or category_label or "")
                td.delete_attachment(item["id"])
                messagebox.showinfo("المرفقات", f"تم استبدال الملف بـ {replacement['file_name']}.", parent=dialog)
                items = reload_items()
                self._refresh_attachment_counts(record_key)
            except (OSError, ValueError) as exc:
                messagebox.showerror("استبدال الملف", str(exc), parent=dialog)

        def delete_file():
            item = selected_item()
            if not item:
                return
            if not messagebox.askyesno("حذف الملف", "حذف هذا الملف نهائياً؟", parent=dialog):
                return
            try:
                td.delete_attachment(item["id"])
                messagebox.showinfo("المرفقات", "تم حذف الملف.", parent=dialog)
                items = reload_items()
                self._refresh_attachment_counts(record_key)
            except (OSError, ValueError) as exc:
                messagebox.showerror("حذف الملف", str(exc), parent=dialog)

        buttons = tk.Frame(dialog, bg=COLOR_BG)
        buttons.pack(fill="x", padx=14, pady=(0, 14))
        make_btn(buttons, "تنزيل نسخة", download_file, variant="accent").pack(side="right", padx=4)
        make_btn(buttons, "استبدال", replace_file, variant="secondary").pack(side="right", padx=4)
        make_btn(buttons, "حذف", delete_file, variant="danger").pack(side="right", padx=4)
        make_btn(buttons, "فتح", open_file, variant="secondary").pack(side="right", padx=4)
        make_btn(buttons, "إغلاق", dialog.destroy, variant="secondary").pack(side="right", padx=4)

    def _build_register_filters(self, parent):
        """Add the appropriate filters to every standard program register."""
        filter_box = tk.Frame(parent, bg=COLOR_CARD)
        filter_box.pack(side="right", padx=(8, 0))
        field_keys = {key for key, _label in self.fields}
        date_width = 8 if self.compact_filters else 10
        combo_width = 8 if self.compact_filters else 16
        value_width = 8 if self.compact_filters else 18

        if "date" in field_keys:
            tk.Label(filter_box, text="من", font=F_LABEL, bg=COLOR_CARD,
                     fg=COLOR_MUTED).pack(side="right", padx=(6, 2))
            date_input(filter_box, self.register_date_from_var, width=date_width).pack(side="right", padx=2)
            tk.Label(filter_box, text="إلى", font=F_LABEL, bg=COLOR_CARD,
                     fg=COLOR_MUTED).pack(side="right", padx=(6, 2))
            date_input(filter_box, self.register_date_to_var, width=date_width).pack(side="right", padx=2)
            self.register_date_from_var.trace_add("write", lambda *_: self.refresh())
            self.register_date_to_var.trace_add("write", lambda *_: self.refresh())

        self._register_filter_labels = {label: key for key, label in self.fields}
        filter_values = ["الكل"] + list(self._register_filter_labels)
        tk.Label(filter_box, text="فلترة حسب", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(6, 2))
        field_combo = ttk.Combobox(filter_box, textvariable=self.register_filter_field_var,
                                   values=filter_values, state="readonly", width=combo_width,
                                   font=F_BODY, justify="right")
        field_combo.pack(side="right", padx=2)
        field_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        tk.Label(filter_box, text="القيمة", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(6, 2))
        value_entry = tk.Entry(filter_box, textvariable=self.register_filter_value_var,
                               font=F_BODY, justify="right", width=value_width)
        value_entry.pack(side="right", padx=2)
        self.register_filter_value_var.trace_add("write", lambda *_: self.refresh())
        make_btn(filter_box, "مسح الفلاتر", self.clear_register_filters,
                 variant="secondary", padx=4, pady=3).pack(side="right", padx=2)

    def clear_register_filters(self):
        self.register_date_from_var.set("")
        self.register_date_to_var.set("")
        self.register_filter_field_var.set("الكل")
        self.register_filter_value_var.set("")
        self.refresh()

    def end_selected_relation(self):
        """Close a driver assignment or partnership without deleting its history."""
        row = self.get_selected_row()
        if not row:
            return
        if safe_str(row.get("end_date")).strip():
            messagebox.showinfo("تنبيه", "هذا السجل منتهٍ بالفعل.")
            return
        if not messagebox.askyesno("تأكيد الإنهاء", "سيتم إنهاء العلاقة بتاريخ اليوم مع الاحتفاظ بالسجل. متابعة؟"):
            return
        row["end_date"] = date.today().isoformat()
        self.save_fn(row, row.get(self.key_field))
        self.refresh()
        if self.on_data_changed:
            self.on_data_changed()


    def _auto_size_columns(self):
        """توزيع عرض الأعمدة تلقائياً حسب عرض الجدول المتاح (استجابة لتغيير حجم النافذة)."""
        try:
            tree_width = self.tree.winfo_width()
            if tree_width <= 1:
                return
            n = len(self.fields)
            if n == 0:
                return
            avg = max(80, tree_width // n)
            for k, _ in self.fields:
                self.tree.column(k, width=avg, stretch=True)
        except Exception as _log_exc: log_exception("_auto_size_columns", _log_exc)

    def refresh(self):
        query = (getattr(self, "search_var", tk.StringVar()).get() or "").strip().lower()
        date_from = self.register_date_from_var.get().strip()
        date_to = self.register_date_to_var.get().strip()
        filter_key = getattr(self, "_register_filter_labels", {}).get(
            self.register_filter_field_var.get().strip(), "")
        filter_value = self.register_filter_value_var.get().strip().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._tree_row_map = {}
        used_iids = set()
        self._rows = self.load_fn()
        if getattr(self, "filter_rows", None):
            self._rows = self.filter_rows(self._rows)
        if self.filter_fn:
            self._rows = [r for r in self._rows if self.filter_fn(r)]
        self._sort_rows_by_date()
        for row in self._rows:
            row_date = safe_str(row.get("date", ""))
            if ((date_from and row_date < date_from)
                    or (date_to and row_date > date_to)
                    or (filter_key and filter_value
                        and filter_value not in safe_str(row.get(filter_key, "")).lower())):
                continue
            hay = " ".join(safe_str(row.get(k, "")) for k, _ in self.fields).lower()
            if query and query not in hay:
                continue
            key_val = row.get(self.key_field, "")
            # القيم تعرض بالترتيب المعاكس حتى تطابق رؤوس الأعمدة RTL
            values = [safe_str(row.get(k, "")) for k, _ in reversed(self.fields)]
            base_iid = str(key_val).strip() or "row"
            iid = base_iid
            suffix = 2
            while iid in used_iids:
                iid = f"{base_iid}_{suffix}"
                suffix += 1
            used_iids.add(iid)
            self._tree_row_map[iid] = row
            self.tree.insert("", "end", iid=iid, values=values)

    def _sort_rows_by_date(self):
        field_keys = {key for key, _ in self.fields}
        sort_key = "date" if "date" in field_keys else ("month" if "month" in field_keys else None)
        if not sort_key:
            return

        def _date_value(row):
            raw = safe_str(row.get(sort_key, "")).strip()
            if not raw:
                return ""
            return raw

        self._rows.sort(key=_date_value, reverse=True)

    def get_selected_row(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار عنصر من القائمة أولاً.")
            return None
        key_val = sel[0]
        mapped_row = getattr(self, "_tree_row_map", {}).get(key_val)
        if mapped_row is not None:
            return mapped_row
        for row in self._rows:
            if str(row.get(self.key_field, "")) == key_val:
                return row
        return None

    def load_selected_into_form(self, row=None):
        if row is None:
            row = self.get_selected_row()
            if not row:
                return
        for k, var in self.vars.items():
            value = safe_str(row.get(k, ""))
            # توافق السجلات القديمة للسيارات قبل إضافة حقل «محتويات السيارة».
            if k == "contents" and not value:
                old_contents = []
                if row.get("is_flatbed") == "نعم":
                    old_contents.append("ساطحة")
                if row.get("flatbed_type"):
                    old_contents.append(safe_str(row.get("flatbed_type")))
                if row.get("has_generator") == "نعم":
                    old_contents.append("مولد")
                value = "، ".join(old_contents)
            var.set(value)
        self.editing_key = row.get(self.key_field, "")
        self._temp_attachment_key = None
        self.save_btn.config(text="حفظ التعديلات")
        self._refresh_attachment_counts(self.editing_key)

    def clear_form(self):
        for key, var in self.vars.items():
            if key in self.default_values:
                var.set(self.default_values[key])
            else:
                var.set("")
        if "service_type" in self.vars and "service_type" not in self.default_values:
            self.vars["service_type"].set(td.SERVICE_TYPES[0])
        self.editing_key = None
        self._temp_attachment_key = None
        self.save_btn.config(text="حفظ")

    def on_save(self):
        data = {k: var.get().strip() for k, var in self.vars.items()}
        key_val = data.get(self.key_field, "")
        old_key = self.editing_key
        # هل هذا الحفظ تعديل لسجل قائم أم إضافة جديدة؟ كان الاسم `was_editing`
        # مستعملاً أدناه دون تعريفه، فيفشل الحفظ بـ NameError عند كل تعديل.
        was_editing = old_key is not None
        key_is_auto = self.key_field in self.readonly_fields
        if not key_val and not key_is_auto:
            label = dict(self.fields).get(self.key_field, self.key_field)
            messagebox.showwarning("تنبيه", f"الحقل «{label}» مطلوب.")
            return
        before_keys = {str(row.get(self.key_field, "")).strip() for row in self.load_fn()}
        try:
            result = self.save_fn(data, self.editing_key)
        except Exception as exc:
            messagebox.showerror("حفظ", str(exc), parent=self.frame)
            return
        saved_key = result if isinstance(result, str) and result.strip() else data.get(self.key_field, "").strip()
        if not saved_key and old_key:
            saved_key = str(old_key).strip()
        if not saved_key:
            try:
                after_rows = self.load_fn()
                candidates = [row for row in after_rows if str(row.get(self.key_field, "")).strip() not in before_keys]
                if candidates:
                    saved_key = str(candidates[-1].get(self.key_field, "")).strip()
            except Exception as _log_exc: log_exception("on_save", _log_exc)
        new_key = saved_key
        if old_key is not None and new_key and str(old_key) != new_key:
            try:
                td.move_attachments(self.attachment_entity_type, old_key, new_key)
            except Exception as exc:
                messagebox.showwarning("المرفقات", f"تم حفظ البيانات لكن فشل نقل المرفقات:\n{exc}", parent=self.frame)
        elif old_key is None and new_key and getattr(self, "_temp_attachment_key", None):
            try:
                td.move_attachments(self.attachment_entity_type, self._temp_attachment_key, new_key)
            except Exception as exc:
                messagebox.showwarning("المرفقات", f"تم حفظ البيانات لكن فشل نقل المرفقات:\n{exc}", parent=self.frame)
        self._temp_attachment_key = None
        self.clear_form()
        self.refresh()
        # إذا كانت إضافة جديدة (وليس تعديل)، لا تقم بتحميل العنصر المحفوظ
        # بل اترك النموذج فارغًا وجاهزًا لإدخال عنصر جديد
        if new_key and not was_editing:
            # إعداد تاريخ اليوم كافتراض للحقول التي تتطلب تاريخ
            if "date" in self.vars:
                self.vars["date"].set(date.today().isoformat())
        else:
            # إذا كان تعديلًا، قم بتحميل العنصر المعدل ليظهر القيم الحالية
            if new_key:
                for row in reversed(self._rows):
                    if str(row.get(self.key_field, "")) == new_key:
                        self.load_selected_into_form(row)
                        break
        if callable(getattr(self, "on_data_changed", None)):
            self.on_data_changed()
        else:
            refresh_related_screens(self.frame)

    def delete_selected(self):
        selected_ids = list(self.tree.selection())
        if not selected_ids:
            messagebox.showinfo("تنبيه", "الرجاء اختيار عنصر من القائمة أولاً.")
            return
        row_map = getattr(self, "_tree_row_map", {})
        rows = [row_map[iid] for iid in selected_ids if iid in row_map]
        if not rows:
            return
        count = len(rows)
        if messagebox.askyesno("تأكيد الحذف", f"هل أنت متأكد من حذف {count} سجل/سجلات؟ لا يمكن التراجع عن هذا الإجراء."):
            errors = []
            for row in rows:
                record_key = row.get(self.key_field, "")
                try:
                    self.delete_fn(record_key)
                except Exception as exc:
                    errors.append(str(exc))
                    continue
                try:
                    td.delete_attachments_for_record(self.attachment_entity_type, record_key)
                except Exception as exc:
                    errors.append(f"حذف المرفقات: {exc}")
            self.refresh()
            if errors:
                messagebox.showwarning("تنبيه", "تم الحذف مع ملاحظات:\n" + "\n".join(errors), parent=self.frame)
            else:
                messagebox.showinfo("تم", f"تم حذف {count} سجل/سجلات.", parent=self.frame)
            self.refresh()
            if callable(self.on_data_changed):
                self.on_data_changed()
            else:
                refresh_related_screens(self.frame)

    def print_summary(self):
        """يطبع السجلات الظاهرة حالياً، بما فيها نتيجة البحث الحالية."""
        rows = [self._tree_row_map[item_id] for item_id in self.tree.get_children()
                if item_id in self._tree_row_map]
        if not rows:
            messagebox.showinfo("طباعة", "لا توجد سجلات مطابقة للطباعة.", parent=self.frame)
            return
        generate_and_open_summary_print(self.title, self.fields, rows)

    def print_selected_summary(self):
        selected_ids = self.tree.selection()
        row_map = getattr(self, "_tree_row_map", {})
        rows = [row_map[item_id] for item_id in selected_ids if item_id in row_map]
        if not rows:
            messagebox.showinfo("طباعة", "الرجاء اختيار سجل أولاً.", parent=self.frame)
            return
        generate_and_open_summary_print(
            f"{self.title} — السجلات المحددة", self.fields, rows)

    def print_selected_or_filtered(self):
        selected_ids = self.tree.selection()
        row_map = getattr(self, "_tree_row_map", {})
        rows = [row_map[item_id] for item_id in selected_ids if item_id in row_map]
        if not rows:
            rows = [row_map[item_id] for item_id in self.tree.get_children()
                    if item_id in row_map]
        if not rows:
            messagebox.showinfo("طباعة", "لا توجد سجلات مطابقة للطباعة.", parent=self.frame)
            return
        title = f"{self.title} — السجلات المحددة" if selected_ids else f"{self.title} — السجل المفلتر"
        generate_and_open_summary_print(title, self.fields, rows)

    def open_print_dialog(self):
        dialog = tk.Toplevel(self.frame)
        dialog.title(f"طباعة {self.title}")
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
                selected_ids = self.tree.selection()
                row_map = getattr(self, "_tree_row_map", {})
                rows = [row_map[iid] for iid in selected_ids if iid in row_map]
                if not rows:
                    row = self.get_selected_row()
                    if row:
                        rows = [row]
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
                messagebox.showwarning("تنبيه", "لا توجد سجلات للطباعة.", parent=dialog)
                return
            generate_and_open_summary_print(
                f"{self.title} — طباعة", self.fields, rows)
            dialog.destroy()

        btns = tk.Frame(dialog, bg=COLOR_BG)
        btns.pack(fill="x", padx=18, pady=(0, 14), anchor="e")
        make_btn(btns, "طباعة", do_print, variant="accent").pack(side="right", padx=4)
        make_btn(btns, "إلغاء", dialog.destroy, variant="secondary").pack(side="right", padx=4)
