# -*- coding: utf-8 -*-
"""الشاشات العامة القابلة لإعادة الاستخدام: CrudTab وDatedOrderTab (نموذج + جدول + بحث)."""

from datetime import date
import tkinter as tk
from tkinter import ttk
from ui import dialogs as messagebox
import restaurant_data as rd
from ui.theme import (
    COLOR_PRIMARY_LIGHT,
    COLOR_BG,
    COLOR_CARD,
    COLOR_TEXT,
    COLOR_MUTED,
    COLOR_BORDER,
    F_LABEL,
    F_BODY,
    safe_str,
    card_frame,
)


class CrudTab:
    """
    شاشة عامة لإدارة جدول بسيط: بطاقة إدخال أعلى الصفحة + جدول أسفل مع بحث.
    key_field: اسم الحقل الذي يُستخدم كمفتاح فريد (يُستخدم أيضاً كعمود بحث افتراضي).
    """

    def __init__(self, parent, fields, load_fn, save_fn, delete_fn, key_field,
                 title, select_fields=None, extra_buttons=None, readonly_fields=None):
        self.parent = parent
        self.fields = fields  # [(key,label), ...]
        self.load_fn = load_fn
        self.save_fn = save_fn
        self.delete_fn = delete_fn
        self.key_field = key_field
        self.title = title
        self.select_fields = select_fields or {}   # key -> list of options
        self.extra_buttons = extra_buttons or []   # أزرار إضافية بجانب أزرار السجل
        self.readonly_fields = readonly_fields or []
        self.editing_key = None
        self.vars = {}
        self.combos = {}
        self._rows = []        # آخر صفوف مقروءة من الملف (للتصفية والاختيار)
        self._iid_map = {}     # معرّف الصف داخل الجدول -> بيانات الصف

        self.frame = tk.Frame(parent, bg=COLOR_BG)
        self._build_form()
        self._build_table()
        self.refresh()

    def _build_form(self):
        card = card_frame(self.frame, f"إضافة / تعديل — {self.title}")
        card.pack(fill="x", padx=16, pady=(16, 8))
        box = card.body
        form = tk.Frame(box, bg=COLOR_CARD)
        form.pack(fill="x", padx=14, pady=(0, 6))

        cols_per_row = 4
        for idx, (key, label) in enumerate(self.fields):
            r, c = divmod(idx, cols_per_row)
            # عكس ترتيب الأعمدة لضمان تدفق الحقول من اليمين لليسار
            c = cols_per_row - 1 - c
            cell = tk.Frame(form, bg=COLOR_CARD)
            cell.grid(row=r, column=c, padx=6, pady=6, sticky="ew")
            tk.Label(cell, text=label, font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED,
                     anchor="e", justify="right").pack(fill="x")
            var = tk.StringVar()
            if key in self.select_fields:
                entry = ttk.Combobox(cell, textvariable=var, values=self.select_fields[key],
                                      font=F_BODY, justify="right", state="readonly")
                self.combos[key] = entry
            else:
                state = "readonly" if key in self.readonly_fields else "normal"
                entry = tk.Entry(cell, textvariable=var, font=F_BODY, justify="right",
                                  state=state, relief="solid", bd=1,
                                  highlightthickness=1, highlightbackground=COLOR_BORDER,
                                  highlightcolor=COLOR_PRIMARY_LIGHT)
            entry.pack(fill="x", ipady=3)
            self.vars[key] = var
        for c in range(cols_per_row):
            form.grid_columnconfigure(c, weight=1)

        btns = tk.Frame(box, bg=COLOR_CARD)
        btns.pack(fill="x", padx=14, pady=(4, 12), anchor="e")
        self.form_btns_frame = btns
        self.save_btn = ttk.Button(btns, text="حفظ", style="Accent.TButton", command=self.on_save)
        self.save_btn.pack(side="right", padx=4)
        ttk.Button(btns, text="مسح الحقول", command=self.clear_form).pack(side="right", padx=4)

    def _build_table(self):
        card = card_frame(self.frame, f"سجل {self.title}")
        card.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        box = card.body

        search_frame = tk.Frame(box, bg=COLOR_CARD)
        search_frame.pack(fill="x", padx=14, pady=(0, 8))
        tk.Label(search_frame, text="بحث:", font=F_BODY, bg=COLOR_CARD, fg=COLOR_TEXT).pack(side="right", padx=(6, 2))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.render_rows())
        tk.Entry(search_frame, textvariable=self.search_var, font=F_BODY,
                 justify="right", width=32, relief="solid", bd=1).pack(side="right", ipady=2)

        table_wrap = tk.Frame(box, bg=COLOR_CARD)
        table_wrap.pack(fill="both", expand=True, padx=14)
        cols = [k for k, _ in self.fields]
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings", selectmode="browse")
        for k, label in self.fields:
            self.tree.heading(k, text=label)
            self.tree.column(k, anchor="center", width=110)
        vs = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        vs.pack(side="left", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.load_selected_into_form())

        btns2 = tk.Frame(box, bg=COLOR_CARD)
        btns2.pack(fill="x", padx=14, pady=(8, 14), anchor="e")
        self.table_btns = btns2
        # أزرار إضافية خاصة بالشاشة (مثل: تحويل عرض سعر إلى مناسبة)
        for spec in self.extra_buttons:
            ttk.Button(btns2, text=spec.get("label", ""), command=spec.get("command"),
                       style=spec.get("style") or "TButton").pack(side="right", padx=4)
        ttk.Button(btns2, text="حذف المحدد", style="Danger.TButton", command=self.delete_selected).pack(side="right", padx=4)
        ttk.Button(btns2, text="تحميل للتعديل", command=self.load_selected_into_form).pack(side="right", padx=4)

    def refresh(self, reload=True):
        """
        إعادة تحميل الصفوف من الملف وإعادة رسم الجدول.
        البحث يعيد الرسم فقط (render_rows) بدون قراءة الملف من جديد.
        """
        if reload:
            self._rows = self.load_fn()
        self.render_rows()

    def refresh_combo(self, key, values):
        """تحديث خيارات قائمة منسدلة في النموذج (مثل قائمة العملاء بعد إضافة عميل)."""
        combo = self.combos.get(key)
        if combo is not None:
            combo.config(values=list(values))

    def render_rows(self):
        query = (self.search_var.get() or "").strip().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._iid_map = {}
        for idx, row in enumerate(self._rows):
            hay = " ".join(safe_str(row.get(k, "")) for k, _ in self.fields).lower()
            if query and query not in hay:
                continue
            # معرّف العمود الأول قد يتكرر (مثل تكرار اسم عميل في ملف قديم)،
            # لذلك نستخدم رقماً متسلسلاً كمفتاح للجدول ونربطه بالصف الأصلي.
            iid = "r%d" % idx
            self._iid_map[iid] = row
            values = [safe_str(row.get(k, "")) for k, _ in self.fields]
            self.tree.insert("", "end", iid=iid, values=values)

    def get_selected_row(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار عنصر من القائمة أولاً.")
            return None
        return self._iid_map.get(sel[0])

    def load_selected_into_form(self):
        row = self.get_selected_row()
        if not row:
            return
        for k, var in self.vars.items():
            var.set(safe_str(row.get(k, "")))
        self.editing_key = row.get(self.key_field, "")
        self.save_btn.config(text="حفظ التعديلات")

    def clear_form(self):
        for var in self.vars.values():
            var.set("")
        self.editing_key = None
        self.save_btn.config(text="حفظ")

    def on_save(self):
        data = {k: var.get().strip() for k, var in self.vars.items()}
        key_val = data.get(self.key_field, "")
        # حقل المفتاح إذا كان معرّفاً تلقائياً (للقراءة فقط) لا يُشترط أن يكون
        # ممتلئاً عند إضافة سجل جديد - سيُولَّد رقمه تلقائياً عند الحفظ.
        key_is_auto = self.key_field in self.readonly_fields
        if not key_val and not key_is_auto:
            label = dict(self.fields).get(self.key_field, self.key_field)
            messagebox.showwarning("تنبيه", f"الحقل «{label}» مطلوب.")
            return
        try:
            self.save_fn(data, self.editing_key)
        except ValueError as e:
            messagebox.showwarning("تنبيه", str(e))
            return
        self.clear_form()
        self.refresh()

    def delete_selected(self):
        row = self.get_selected_row()
        if not row:
            return
        if messagebox.askyesno("تأكيد الحذف", "هل أنت متأكد من الحذف؟ لا يمكن التراجع عن هذا الإجراء."):
            self.delete_fn(row.get(self.key_field, ""))
            self.refresh()


# ==================================================================
# شاشة مخصّصة عامة لسجل له تاريخ + كمية × سعر = إجمالي، مع زر "اليوم"
# تُستخدم لكل من طلبات المؤسسات والعزائم والمناسبات
# ==================================================================
class DatedOrderTab(CrudTab):
    """
    مثل CrudTab لكنها تضيف:
      - زر "تعبئة تاريخ اليوم" لحقل التاريخ.
      - تحديث قائمة العملاء تلقائياً من جدول العملاء.
      - عرض حقل الإجمالي كقراءة فقط (يُحسب تلقائياً في طبقة البيانات).
    """

    def __init__(self, parent, fields, load_fn, save_fn, delete_fn, key_field, title,
                 date_field, select_fields=None, readonly_fields=None, today_button=True):
        self.date_field = date_field
        self.today_button = today_button
        super().__init__(parent, fields, load_fn, save_fn, delete_fn, key_field, title,
                          select_fields=select_fields, readonly_fields=readonly_fields)
        if self.today_button and self.date_field in self.vars:
            self.vars[self.date_field].set(date.today().isoformat())

    def _build_form(self):
        super()._build_form()
        if self.today_button and self.date_field in self.vars:
            # نضيف زر تعبئة تاريخ اليوم أسفل النموذج مباشرة، قبل صف أزرار الحفظ
            quick = tk.Frame(self.form_btns_frame.master, bg=COLOR_CARD)
            quick.pack(fill="x", padx=14, pady=(0, 8), anchor="e", before=self.form_btns_frame)
            ttk.Button(quick, text="تعبئة تاريخ اليوم", command=self.set_today).pack(side="right", padx=4)

    def set_today(self):
        self.vars[self.date_field].set(date.today().isoformat())

    def set_today_if_empty(self):
        """
        تعبئة تاريخ اليوم عند فتح الشاشة إذا كان حقل التاريخ فارغاً
        (حتى لا يبقى التاريخ قديماً إذا تُرك البرنامج مفتوحاً ليلة كاملة).
        """
        if not self.vars[self.date_field].get().strip():
            self.set_today()

    def refresh_customer_options(self):
        if "customer" in self.combos:
            self.combos["customer"].config(values=[c["name"] for c in rd.load_customers()])
