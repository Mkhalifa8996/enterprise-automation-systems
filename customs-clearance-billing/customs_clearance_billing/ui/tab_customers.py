# -*- coding: utf-8 -*-
"""تبويب العملاء: إضافة وتعديل العملاء ورموز الشركات."""

import tkinter as tk
from tkinter import messagebox, ttk

from ..config import get_tk_font
from ..data import (
    SaveError,
    delete_customer,
    load_customers,
    next_available_company_code,
    save_customer,
)
from .theme import (
    COL_BG,
    COL_BORDER,
    COL_CARD,
    COL_NAVY,
    COL_ROW_ALT,
    COL_SUBTEXT,
    COL_TEXT,
)


class CustomersMixin:
    """يبني تبويب «العملاء» ويدير سجلات العملاء."""
    def _build_customers_tab(self):
        wrap = tk.Frame(self.tab_customers, bg=COL_BG)
        wrap.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(wrap, text="العملاء", bg=COL_BG, fg=COL_NAVY, font=get_tk_font(15, "bold")).pack(anchor="e")

        form_card = tk.Frame(wrap, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        form_card.pack(fill="x", pady=(10, 12))
        tk.Label(form_card, text="👤 إضافة / تعديل عميل", bg=COL_CARD, fg=COL_NAVY,
                 font=get_tk_font(10, "bold")).pack(anchor="e", padx=14, pady=(12, 4))

        form = tk.Frame(form_card, bg=COL_CARD)
        form.pack(fill="x", padx=12, pady=(0, 6))

        self.c_name = tk.StringVar()
        self.c_phone = tk.StringVar()
        self.c_address = tk.StringVar()
        self.c_notes = tk.StringVar()
        self._editing_customer = None
        self._editing_customer_company_code = ""  # يُحفظ داخلياً فقط، لا يظهر كحقل إدخال

        def field(parent, label, var, col, width=22):
            f = tk.Frame(parent, bg=COL_CARD)
            f.grid(row=0, column=col, padx=8, pady=6, sticky="ew")
            tk.Label(f, text=label, bg=COL_CARD, fg=COL_SUBTEXT, font=get_tk_font(9)).pack(anchor="e")
            tk.Entry(f, textvariable=var, font=get_tk_font(10), justify="right", width=width,
                     relief="solid", bd=1, highlightthickness=1, highlightbackground=COL_BORDER).pack(fill="x", ipady=3)
            return f

        field(form, "اسم العميل", self.c_name, 3)
        field(form, "الهاتف", self.c_phone, 2)
        field(form, "العنوان", self.c_address, 1)
        field(form, "ملاحظات", self.c_notes, 0)
        for i in range(4):
            form.grid_columnconfigure(i, weight=1)

        btns = tk.Frame(form_card, bg=COL_CARD)
        btns.pack(fill="x", padx=12, pady=(4, 14))
        self.btn_save_customer = ttk.Button(btns, text="💾 حفظ العميل", style="Accent.TButton", command=self.save_customer_form)
        self.btn_save_customer.pack(side="right", padx=3)
        ttk.Button(btns, text="مسح الحقول", style="Ghost.TButton", command=self.clear_customer_form).pack(side="right", padx=3)

        table_card = tk.Frame(wrap, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        table_card.pack(fill="both", expand=True)

        search_frame = tk.Frame(table_card, bg=COL_CARD)
        search_frame.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(search_frame, text="🔍 بحث:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(6, 2))
        self.cust_search_var = tk.StringVar()
        self.cust_search_var.trace_add("write", lambda *a: self.refresh_customer_list())
        tk.Entry(search_frame, textvariable=self.cust_search_var, font=get_tk_font(10),
                 justify="right", width=30, relief="solid", bd=1,
                 highlightthickness=1, highlightbackground=COL_BORDER).pack(side="right", ipady=3)

        # ملاحظة مهمة حول الترتيب: يجب حجز مساحة صف الأزرار (btns2) أولاً بربطه
        # بأسفل البطاقة (side="bottom") *قبل* إضافة الجدول الذي يتمدّد (expand=True).
        # فـ pack تُوزّع المساحة بالترتيب الذي تُستدعى به: لو تم تعبئة الجدول
        # المتمدّد أولاً فسيستهلك كل المساحة المتاحة عند تصغير النافذة، ولن يبقى
        # للأزرار مكان فتختفي تماماً. حجز مكان الأزرار أولاً يضمن ظهورها دائماً
        # مهما صغرت النافذة، ثم يأخذ الجدول ما تبقى من المساحة.
        btns2 = tk.Frame(table_card, bg=COL_CARD)
        btns2.pack(side="bottom", fill="x", padx=12, pady=10)
        ttk.Button(btns2, text="✎ تحميل للتعديل", style="Ghost.TButton", command=self.load_customer_into_form).pack(side="right", padx=3)
        ttk.Button(btns2, text="🗑 حذف العميل المحدد", style="Danger.TButton", command=self.delete_selected_customer).pack(side="right", padx=3)

        cols = ("name", "phone", "address", "notes", "company_code")
        self.cust_tree = ttk.Treeview(table_card, columns=cols, show="headings", selectmode="browse")
        self.cust_tree["displaycolumns"] = tuple(reversed(cols))
        headers = {"name": "اسم العميل", "phone": "الهاتف", "address": "العنوان",
                   "notes": "ملاحظات", "company_code": "رمز الشركة"}
        for c in cols:
            self.cust_tree.heading(c, text=headers[c], anchor="e")
            self.cust_tree.column(c, anchor="e", width=150 if c != "company_code" else 90)
        self.cust_tree.tag_configure("rowodd", background=COL_CARD)
        self.cust_tree.tag_configure("roweven", background=COL_ROW_ALT)
        self.cust_tree.pack(fill="both", expand=True, padx=1, pady=(4, 1))
        self.cust_tree.bind("<Double-1>", lambda e: self.load_customer_into_form())

    def refresh_customer_list(self):
        query = (self.cust_search_var.get() or "").strip().lower()
        for row in self.cust_tree.get_children():
            self.cust_tree.delete(row)
        self._all_customers = load_customers()
        row_idx = 0
        for c in self._all_customers:
            hay = f"{c['name']} {c['phone']}".lower()
            if query and query not in hay:
                continue
            stripe = "roweven" if row_idx % 2 else "rowodd"
            row_idx += 1
            self.cust_tree.insert("", "end", iid=c["name"], tags=(stripe,),
                                   values=(c["name"], c["phone"], c["address"], c["notes"], c.get("company_code", "")))

    def load_customer_into_form(self):
        sel = self.cust_tree.selection()
        if not sel:
            return
        name = sel[0]
        for c in self._all_customers:
            if c["name"] == name:
                self.c_name.set(c["name"])
                self.c_phone.set(c["phone"])
                self.c_address.set(c["address"])
                self.c_notes.set(c["notes"])
                self._editing_customer = name
                self._editing_customer_company_code = c.get("company_code", "")
                self.btn_save_customer.config(text="حفظ التعديلات")
                break

    def clear_customer_form(self):
        self.c_name.set(""); self.c_phone.set(""); self.c_address.set(""); self.c_notes.set("")
        self._editing_customer = None
        self._editing_customer_company_code = ""
        self.btn_save_customer.config(text="حفظ العميل")

    def save_customer_form(self):
        name = self.c_name.get().strip()
        if not name:
            messagebox.showwarning("تنبيه", "الرجاء إدخال اسم العميل.")
            return

        if self._editing_customer:
            # عميل موجود: نحافظ على رمز شركته الحالي كما هو (لا يُعاد توليده)
            company_code = self._editing_customer_company_code
        else:
            # عميل جديد: يُولَّد له رمز شركة تلقائياً (أصغر رمز متاح بين 01 و99)
            try:
                company_code = next_available_company_code()
            except ValueError as e:
                messagebox.showerror("تنبيه", str(e))
                return

        try:
            save_customer({"name": name, "phone": self.c_phone.get(), "address": self.c_address.get(),
                            "notes": self.c_notes.get(), "company_code": company_code},
                           editing_name=self._editing_customer)
        except SaveError as e:
            messagebox.showerror("خطأ في الحفظ", str(e))
            return
        self.clear_customer_form()
        self.refresh_customer_list()
        self.refresh_dashboard()

    def delete_selected_customer(self):
        sel = self.cust_tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار عميل من القائمة أولاً.")
            return
        name = sel[0]
        if messagebox.askyesno("تأكيد الحذف", f'هل أنت متأكد من حذف العميل "{name}"؟'):
            try:
                delete_customer(name)
            except SaveError as e:
                messagebox.showerror("خطأ في الحفظ", str(e))
                return
            self.refresh_customer_list()
            self.refresh_dashboard()

    def all_customer_names(self):
        return [c["name"] for c in load_customers()]
