# -*- coding: utf-8 -*-
"""تبويب الدفعات والأرصدة: تسجيل السندات وتخصيصها على الفواتير."""

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from ..config import get_tk_font
from ..data import (
    SaveError,
    customer_balances,
    delete_payment,
    invoice_payment_status,
    load_customers,
    load_invoices,
    load_payments,
    next_receipt_number,
    save_payment,
)
from ..utils import safe_float
from .theme import (
    COL_BG,
    COL_BORDER,
    COL_BORDER_SOFT,
    COL_CARD,
    COL_CARD_SOFT,
    COL_DANGER,
    COL_GOLD_DARK,
    COL_NAVY,
    COL_ROW_ALT,
    COL_SUBTEXT,
    COL_SUCCESS,
    COL_TEXT,
    COL_WARN,
)
from .widgets import build_date_field


class PaymentsMixin:
    """يبني تبويب «الدفعات والأرصدة» ويدير السندات وأرصدة العملاء."""
    def _build_payments_tab(self):
        wrap = tk.Frame(self.tab_payments, bg=COL_BG)
        wrap.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(wrap, text="الدفعات والأرصدة", bg=COL_BG, fg=COL_NAVY, font=get_tk_font(15, "bold")).pack(anchor="e")

        # ---- نموذج إضافة دفعة ----
        form_card = tk.Frame(wrap, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        form_card.pack(fill="x", pady=(10, 12))
        tk.Label(form_card, text="💳 تسجيل دفعة جديدة", bg=COL_CARD, fg=COL_NAVY,
                 font=get_tk_font(10, "bold")).pack(anchor="e", padx=14, pady=(12, 4))

        form = tk.Frame(form_card, bg=COL_CARD)
        form.pack(fill="x", padx=12)

        self.p_customer = tk.StringVar()
        self.p_date = tk.StringVar(value=date.today().isoformat())
        self.p_amount = tk.StringVar()
        self.p_notes = tk.StringVar()
        self._editing_payment_id = None

        f1 = tk.Frame(form, bg=COL_CARD)
        f1.grid(row=0, column=3, padx=8, pady=6, sticky="ew")
        tk.Label(f1, text="اسم العميل", bg=COL_CARD, fg=COL_SUBTEXT, font=get_tk_font(9)).pack(anchor="e")
        self.p_customer_combo = ttk.Combobox(f1, textvariable=self.p_customer, font=get_tk_font(10), justify="right", width=22)
        self.p_customer_combo.pack(fill="x")
        self.p_customer_combo.configure(postcommand=lambda: self.p_customer_combo.configure(values=self.all_customer_names()))
        self.p_customer_combo.bind("<<ComboboxSelected>>", self._on_payment_customer_changed)
        self.p_customer_combo.bind("<FocusOut>", self._on_payment_customer_changed)
        self.p_receipt_preview_var = tk.StringVar(value="رقم السند: —")
        tk.Label(f1, textvariable=self.p_receipt_preview_var, bg=COL_CARD, font=get_tk_font(8, "bold"), fg=COL_GOLD_DARK).pack(anchor="e", pady=(3, 0))

        f2 = tk.Frame(form, bg=COL_CARD)
        f2.grid(row=0, column=2, padx=8, pady=6, sticky="ew")
        tk.Label(f2, text="التاريخ", bg=COL_CARD, fg=COL_SUBTEXT, font=get_tk_font(9)).pack(anchor="e")
        p_date_row, _ = build_date_field(f2, self.p_date)
        p_date_row.pack(fill="x")

        f3 = tk.Frame(form, bg=COL_CARD)
        f3.grid(row=0, column=1, padx=8, pady=6, sticky="ew")
        tk.Label(f3, text="المبلغ المدفوع (د.ك)", bg=COL_CARD, fg=COL_SUBTEXT, font=get_tk_font(9)).pack(anchor="e")
        tk.Entry(f3, textvariable=self.p_amount, font=get_tk_font(10), justify="right", width=16,
                 relief="solid", bd=1, highlightthickness=1, highlightbackground=COL_BORDER).pack(fill="x", ipady=3)

        f4 = tk.Frame(form, bg=COL_CARD)
        f4.grid(row=0, column=0, padx=8, pady=6, sticky="ew")
        tk.Label(f4, text="ملاحظات", bg=COL_CARD, fg=COL_SUBTEXT, font=get_tk_font(9)).pack(anchor="e")
        tk.Entry(f4, textvariable=self.p_notes, font=get_tk_font(10), justify="right", width=22,
                 relief="solid", bd=1, highlightthickness=1, highlightbackground=COL_BORDER).pack(fill="x", ipady=3)

        for i in range(4):
            form.grid_columnconfigure(i, weight=1)

        # ---- تخصيص الدفعة لفواتير محددة (اختياري) ----
        alloc_box = tk.Frame(form, bg=COL_CARD_SOFT, highlightthickness=1, highlightbackground=COL_BORDER_SOFT)
        alloc_box.grid(row=1, column=0, columnspan=4, padx=8, pady=(6, 10), sticky="ew")
        tk.Label(alloc_box, text="🧾 تخصيص الدفعة لفواتير محددة (اختياري)", bg=COL_CARD_SOFT, fg=COL_NAVY,
                 font=get_tk_font(9, "bold")).pack(anchor="e", padx=10, pady=(8, 2))

        # جدول الفواتير يُظهر كل بيانات كل فاتورة (رقم، تاريخ، بيان جمركي، منفذ،
        # نوع البضاعة، بلد المنشأ، الإجمالي، المدفوع، المتبقي، الحالة) بدلاً من
        # سطر نصي واحد، مما يتيح للمستخدم رؤية شاملة وتحديد الفواتير بسهولة.
        cols_pi = ("invno", "date", "declno", "port", "goodstype", "origin",
                   "total", "paid", "balance", "status")
        self.p_invoices_tree = ttk.Treeview(alloc_box, columns=cols_pi, show="headings",
                                            selectmode="extended", height=3,
                                            style="CompactTree.Treeview")
        self.p_invoices_tree["displaycolumns"] = tuple(reversed(cols_pi))
        headers_pi = {
            "invno": "رقم الفاتورة", "date": "التاريخ", "declno": "رقم البيان الجمركي",
            "port": "المنفذ", "goodstype": "نوع البضاعة", "origin": "بلد المنشأ",
            "total": "الإجمالي (د.ك)", "paid": "المدفوع (د.ك)", "balance": "المتبقي (د.ك)",
            "status": "الحالة",
        }
        widths_pi = {"invno": 95, "date": 95, "declno": 110, "port": 100,
                     "goodstype": 120, "origin": 115, "total": 100, "paid": 100,
                     "balance": 100, "status": 105}
        for c in cols_pi:
            self.p_invoices_tree.heading(c, text=headers_pi[c], anchor="e")
            self.p_invoices_tree.column(c, anchor="e", width=widths_pi[c])
        status_tag_map = {"paid": "st_paid", "partial": "st_partial", "unpaid": "st_unpaid"}
        status_label_map = {"paid": "مسددة ✅", "partial": "جزئية ⏳", "unpaid": "غير مسددة ⛔"}
        for tag in ("rowodd", "roweven"):
            tag_bg = COL_CARD_SOFT if tag == "rowodd" else COL_ROW_ALT
            self.p_invoices_tree.tag_configure(tag, background=tag_bg)
        for tag in status_tag_map.values():
            self.p_invoices_tree.tag_configure(tag, font=get_tk_font(10, "bold"))
        self.p_invoices_tree.tag_configure("st_paid", foreground=COL_SUCCESS)
        self.p_invoices_tree.tag_configure("st_partial", foreground=COL_WARN)
        self.p_invoices_tree.tag_configure("st_unpaid", foreground=COL_DANGER)
        self._p_invoice_choices = []  # قائمة موازية لعناصر الجدول: أرقام الفاتورات
        pi_scroll = ttk.Scrollbar(alloc_box, orient="vertical", command=self.p_invoices_tree.yview)
        self.p_invoices_tree.configure(yscrollcommand=pi_scroll.set)
        tree_wrap = tk.Frame(alloc_box, bg=COL_CARD_SOFT)
        tree_wrap.pack(fill="x", padx=10, pady=(6, 0))
        pi_scroll.pack(in_=tree_wrap, side="right", fill="y")
        self.p_invoices_tree.pack(in_=tree_wrap, side="right", fill="both", expand=True)

        alloc_btns = tk.Frame(alloc_box, bg=COL_CARD_SOFT)
        alloc_btns.pack(fill="x", padx=10, pady=(3, 6))
        ttk.Button(alloc_btns, text="⟳ تحديث قائمة الفاتورات", style="Ghost.TButton", command=self._update_payment_invoice_list).pack(side="right", padx=2)
        ttk.Button(alloc_btns, text="✕ إلغاء التحديد (دفعة عامة)", style="Ghost.TButton", command=lambda: self.p_invoices_tree.selection_remove(self.p_invoices_tree.get_children())).pack(side="right", padx=2)
        self.p_alloc_summary_var = tk.StringVar(value="")
        tk.Label(alloc_btns, textvariable=self.p_alloc_summary_var, bg=COL_CARD_SOFT, font=get_tk_font(8, "bold"), fg=COL_NAVY).pack(side="right", padx=6)
        self.p_invoices_tree.bind("<<TreeviewSelect>>", self._update_alloc_summary)

        btns = tk.Frame(form_card, bg=COL_CARD)
        btns.pack(fill="x", padx=12, pady=(0, 8))
        self.btn_save_payment = ttk.Button(btns, text="💾 حفظ الدفعة", style="Accent.TButton", command=self.save_payment_form)
        self.btn_save_payment.pack(side="right", padx=3)
        ttk.Button(btns, text="مسح الحقول", style="Ghost.TButton", command=self.clear_payment_form).pack(side="right", padx=3)

        # ---- تصفية سجل الدفعات ----
        filter_card = tk.Frame(wrap, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        filter_card.pack(fill="x", pady=(0, 12))
        pf = tk.Frame(filter_card, bg=COL_CARD)
        pf.pack(fill="x", padx=14, pady=10)
        tk.Label(pf, text="العميل:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(6, 2))
        self.p_filter_customer_var = tk.StringVar(value="الكل")
        self.p_filter_customer_combo = ttk.Combobox(pf, textvariable=self.p_filter_customer_var, font=get_tk_font(10),
                                                      justify="right", width=20, state="readonly")
        self.p_filter_customer_combo.pack(side="right", padx=4)
        self.p_filter_customer_combo.bind("<<ComboboxSelected>>", lambda e: (self.refresh_payments_list()))
        self.p_filter_customer_combo.configure(
            postcommand=lambda: self.p_filter_customer_combo.configure(values=["الكل"] + self.all_customer_names())
        )
        self.p_filter_customer_combo.configure(values=["الكل"] + self.all_customer_names())

        tk.Label(pf, text="من تاريخ:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(10, 2))
        self.p_filter_from_var = tk.StringVar()
        self.p_filter_from_var.trace_add("write", lambda *a: self.refresh_payments_list())
        p_from_row, _ = build_date_field(pf, self.p_filter_from_var)
        p_from_row.pack(side="right", padx=4)

        tk.Label(pf, text="إلى تاريخ:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(10, 2))
        self.p_filter_to_var = tk.StringVar()
        self.p_filter_to_var.trace_add("write", lambda *a: self.refresh_payments_list())
        p_to_row, _ = build_date_field(pf, self.p_filter_to_var)
        p_to_row.pack(side="right", padx=4)

        ttk.Button(pf, text="✕ مسح التصفية", style="Ghost.TButton", command=self.clear_payment_filters).pack(side="right", padx=4)
        self.payments_summary_label = tk.Label(pf, text="", bg=COL_CARD, fg=COL_NAVY, font=get_tk_font(10, "bold"))
        self.payments_summary_label.pack(side="left", padx=10)

        # ---- منطقة مقسّمة: سجل الدفعات (يمين) وجدول الأرصدة (يسار) ----
        split = tk.Frame(wrap, bg=COL_BG)
        split.pack(fill="both", expand=True)
        split.grid_columnconfigure(0, weight=3)
        split.grid_columnconfigure(1, weight=2)
        split.grid_rowconfigure(0, weight=1)

        pay_box = tk.Frame(split, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        pay_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)
        pay_box.grid_columnconfigure(0, weight=1)
        pay_box.grid_rowconfigure(2, weight=1)
        tk.Label(pay_box, text="📋 سجل الدفعات", bg=COL_CARD, fg=COL_NAVY, font=get_tk_font(10, "bold")).grid(row=0, column=0, sticky="e", padx=12, pady=(10, 4))
        # نحجز مساحة أزرار الدفعات ضمن شبكة مرنة لتفادي انهيار الحاوية عند العرض.
        pay_btns = tk.Frame(pay_box, bg=COL_CARD)
        pay_btns.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 10))
        pay_btns.grid_columnconfigure(0, weight=0)
        pay_btns.grid_columnconfigure(1, weight=0)
        ttk.Button(pay_btns, text="✎ تحميل للتعديل", style="Ghost.TButton", command=self.load_payment_into_form).grid(row=0, column=0, padx=4)
        ttk.Button(pay_btns, text="🗑 حذف الدفعة المحددة", style="Danger.TButton", command=self.delete_selected_payment).grid(row=0, column=1, padx=4)

        cols_p = ("id", "customer", "date", "amount", "applied", "notes")
        self.pay_tree = ttk.Treeview(pay_box, columns=cols_p, show="headings", selectmode="browse", height=8)
        self.pay_tree["displaycolumns"] = tuple(reversed(cols_p))
        pay_scroll = ttk.Scrollbar(pay_box, orient="vertical", command=self.pay_tree.yview)
        self.pay_tree.configure(yscrollcommand=pay_scroll.set)
        headers_p = {"id": "رقم السند", "customer": "العميل", "date": "التاريخ", "amount": "المبلغ (د.ك)",
                     "applied": "الفواتير المسددة", "notes": "ملاحظات"}
        for c in cols_p:
            self.pay_tree.heading(c, text=headers_p[c], anchor="e")
            self.pay_tree.column(c, anchor="e", width=90 if c == "id" else 120)
        self.pay_tree.tag_configure("rowodd", background=COL_CARD)
        self.pay_tree.tag_configure("roweven", background=COL_ROW_ALT)
        self.pay_tree.grid(row=2, column=0, sticky="nsew", padx=6, pady=6)
        pay_scroll.grid(row=2, column=1, sticky="ns", padx=(0, 4), pady=6)
        self.pay_tree.bind("<Double-1>", lambda e: self.load_payment_into_form())

        bal_box = tk.Frame(split, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        bal_box.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=0)
        tk.Label(bal_box, text="📊 أرصدة العملاء (الفواتير − المدفوع)", bg=COL_CARD, fg=COL_NAVY, font=get_tk_font(10, "bold")).pack(anchor="e", padx=12, pady=(10, 4))
        cols_b = ("customer", "invoiced", "paid", "balance")
        self.bal_tree = ttk.Treeview(bal_box, columns=cols_b, show="headings", selectmode="browse")
        self.bal_tree["displaycolumns"] = tuple(reversed(cols_b))
        headers_b = {"customer": "العميل", "invoiced": "إجمالي الفواتير", "paid": "إجمالي المدفوع", "balance": "الرصيد المستحق"}
        for c in cols_b:
            self.bal_tree.heading(c, text=headers_b[c], anchor="e")
            self.bal_tree.column(c, anchor="e", width=130)
        self.bal_tree.tag_configure("owed", foreground=COL_DANGER, font=get_tk_font(10, "bold"))
        self.bal_tree.tag_configure("settled", foreground=COL_SUCCESS, font=get_tk_font(10, "bold"))
        self.bal_tree.tag_configure("rowodd", background=COL_CARD)
        self.bal_tree.tag_configure("roweven", background=COL_ROW_ALT)
        bal_scroll = ttk.Scrollbar(bal_box, orient="vertical", command=self.bal_tree.yview)
        self.bal_tree.configure(yscrollcommand=bal_scroll.set)
        bal_scroll.pack(side="right", fill="y", padx=(0, 6), pady=6)
        self.bal_tree.pack(fill="both", expand=True, padx=(6, 0), pady=6)

    def refresh_payments_list(self):
        query_customer = self.p_filter_customer_var.get() if hasattr(self, "p_filter_customer_var") else "الكل"
        date_from = (self.p_filter_from_var.get() or "").strip() if hasattr(self, "p_filter_from_var") else ""
        date_to = (self.p_filter_to_var.get() or "").strip() if hasattr(self, "p_filter_to_var") else ""

        for row in self.pay_tree.get_children():
            self.pay_tree.delete(row)
        self._all_payments = load_payments()

        filtered = []
        for p in self._all_payments:
            if query_customer and query_customer != "الكل" and p.get("customer", "") != query_customer:
                continue
            p_date = str(p.get("date", ""))
            if date_from and p_date < date_from:
                continue
            if date_to and p_date > date_to:
                continue
            filtered.append(p)

        total_paid = 0.0
        for row_idx, p in enumerate(filtered):
            amount = float(p.get("amount") or 0)
            total_paid += amount
            applied = p.get("applied_invoices") or []
            applied_txt = " ، ".join(applied) if applied else "دفعة عامة"
            stripe = "roweven" if row_idx % 2 else "rowodd"
            self.pay_tree.insert("", "end", iid=str(p["id"]), tags=(stripe,),
                                  values=(p.get("id", ""), p.get("customer", ""), p.get("date", ""),
                                          f'{amount:.3f}', applied_txt, p.get("notes", "")))

        if hasattr(self, "payments_summary_label"):
            self.payments_summary_label.config(
                text=f"عدد الدفعات: {len(filtered)}    |    الإجمالي المدفوع: {total_paid:.3f} د.ك"
            )

    def refresh_balances(self):
        for row in self.bal_tree.get_children():
            self.bal_tree.delete(row)
        for idx, b in enumerate(customer_balances()):
            tag = "owed" if b["balance"] > 0.0005 else ("settled" if b["balance"] < -0.0005 else "")
            stripe = "roweven" if idx % 2 else "rowodd"
            self.bal_tree.insert("", "end", values=(b["customer"], f'{b["invoiced"]:.3f}',
                                                      f'{b["paid"]:.3f}', f'{b["balance"]:.3f}'),
                                  tags=(stripe, tag) if tag else (stripe,))

    def _get_selected_payment(self):
        sel = self.pay_tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار دفعة من القائمة أولاً")
            return None
        pid = sel[0]
        for p in getattr(self, "_all_payments", []):
            if str(p["id"]) == str(pid):
                return p
        return None

    def _on_payment_customer_changed(self, event=None):
        self._update_receipt_preview(event)
        self._update_payment_invoice_list()

    def _update_payment_invoice_list(self, preselect=None):
        """يملأ جدول الفواتير غير المسددة/الجزئية للعميل المحدد حالياً في نموذج الدفعة،
        ليختار المستخدم منه الفواتير التي يريد تخصيص الدفعة لها (إن وُجدت).
        يُظهر كل بيانات كل فاتورة في العمود المناسب لتسهيل المقارنة والاختيار."""
        # حفظ التحديد الحالي عند إعادة بناء الجدول (مثلاً عند فقدان التركيز
        # على الـ Combobox بعد اختيار فاتورة) لمنع فقدان اختيار المستخدم.
        preserve = None if preselect is not None else set(self._selected_payment_invoices())
        self.p_invoices_tree.delete(*self.p_invoices_tree.get_children())
        self._p_invoice_choices = []
        customer_name = self.p_customer.get().strip()
        if not customer_name:
            return
        all_invoices = load_invoices()
        status_map = invoice_payment_status(all_invoices, load_payments())
        invoices = [i for i in all_invoices if i.get("customer") == customer_name]
        invoices.sort(key=lambda i: str(i.get("date", "")))
        preselect = set(str(x) for x in (preselect or preserve or []))
        status_tag_map = {"paid": "st_paid", "partial": "st_partial", "unpaid": "st_unpaid"}
        status_label_map = {"paid": "مسددة ✅", "partial": "جزئية ⏳", "unpaid": "غير مسددة ⛔"}
        to_select = []
        for inv in invoices:
            no = str(inv.get("invno", ""))
            st = status_map.get(no, {"total": float(inv.get("total") or 0), "balance": float(inv.get("total") or 0), "status": "unpaid"})
            if st["status"] == "paid" and no not in preselect:
                continue  # لا داعي لعرض فواتير مسددة بالكامل ضمن خيارات التخصيص
            stripe = "roweven" if len(self._p_invoice_choices) % 2 else "rowodd"
            status_tag = status_tag_map.get(st["status"], "st_unpaid")
            self.p_invoices_tree.insert("", "end", iid=no, values=(
                inv.get("invno", ""),
                inv.get("date", ""),
                inv.get("declno", ""),
                inv.get("port", ""),
                inv.get("goodstype", ""),
                inv.get("origin", ""),
                f'{st["total"]:.3f}',
                f'{st["paid"]:.3f}',
                f'{st["balance"]:.3f}',
                status_label_map.get(st["status"], "غير مسددة ⛔"),
            ), tags=(stripe, status_tag))
            self._p_invoice_choices.append(no)
            if no in preselect:
                to_select.append(no)
        # Treeview.selection_set يحوّل selection set إلى "استبدال" وليس "إضافة"
        # في كل استدعاء، لذا يجب تحديد كل الفواتير المطلوب تمييزها مرة واحدة
        # (والترتيب يُحفظ حسب ترتيب الظهور = الأقدم أولاً = أولوية FIFO).
        if to_select:
            self.p_invoices_tree.selection_set(*to_select)
        self._update_alloc_summary()

    def _selected_payment_invoices(self):
        """يعيد أرقام الفواتير المحددة في الجدول بترتيب ظهورها (الأقدم أولاً)
        لضمان أولوية توزيع الدفعة على الفواتير المستحقة أقدماً."""
        sel = set(self.p_invoices_tree.selection())
        return [no for no in self._p_invoice_choices if no in sel]

    def _update_alloc_summary(self, event=None):
        chosen = self._selected_payment_invoices()
        if chosen:
            self.p_alloc_summary_var.set(f"سيتم تطبيق الدفعة على {len(chosen)} فاتورة محددة")
        else:
            self.p_alloc_summary_var.set("دفعة عامة — ستُطبَّق تلقائياً على أقدم الفواتير")

    def _update_receipt_preview(self, event=None):
        customer_name = self.p_customer.get().strip()
        if not customer_name:
            self.p_receipt_preview_var.set("رقم السند: —")
            return
        customers = {c["name"]: c for c in load_customers()}
        c = customers.get(customer_name)
        if not c or not c.get("company_code"):
            self.p_receipt_preview_var.set("رقم السند: (العميل بلا رمز شركة)")
            return
        try:
            preview = next_receipt_number(c["company_code"])
        except ValueError as e:
            self.p_receipt_preview_var.set("رقم السند: —")
            return
        self.p_receipt_preview_var.set(f"رقم السند القادم: {preview}")

    def load_payment_into_form(self):
        p = self._get_selected_payment()
        if not p:
            return
        self.p_customer.set(p.get("customer", ""))
        self.p_date.set(p.get("date", ""))
        self.p_amount.set(str(p.get("amount", "")))
        self.p_notes.set(p.get("notes", ""))
        self._editing_payment_id = p["id"]
        self.p_receipt_preview_var.set(f"رقم السند: {p['id']}")
        self.btn_save_payment.config(text="حفظ التعديلات")
        self._update_payment_invoice_list(preselect=p.get("applied_invoices"))

    def clear_payment_form(self):
        self.p_customer.set("")
        self.p_date.set(date.today().isoformat())
        self.p_amount.set("")
        self.p_notes.set("")
        self._editing_payment_id = None
        self.p_receipt_preview_var.set("رقم السند: —")
        self.btn_save_payment.config(text="حفظ الدفعة")
        self.p_invoices_tree.delete(*self.p_invoices_tree.get_children())
        self._p_invoice_choices = []
        self.p_alloc_summary_var.set("")

    def clear_payment_filters(self):
        self.p_filter_customer_var.set("الكل")
        self.p_filter_from_var.set("")
        self.p_filter_to_var.set("")
        self.refresh_payments_list()

    def save_payment_form(self):
        customer = self.p_customer.get().strip()
        if not customer:
            messagebox.showwarning("تنبيه", "الرجاء اختيار أو إدخال اسم العميل")
            return
        amount_val = safe_float(self.p_amount.get())
        if amount_val <= 0:
            messagebox.showwarning("تنبيه", "الرجاء إدخال مبلغ دفعة أكبر من صفر")
            return
        p = {
            "customer": customer,
            "date": self.p_date.get().strip(),
            "amount": amount_val,
            "notes": self.p_notes.get().strip(),
            "applied_invoices": self._selected_payment_invoices(),
        }
        try:
            save_payment(p, editing_id=self._editing_payment_id)
        except ValueError as e:
            messagebox.showwarning("تنبيه", str(e))
            return
        except SaveError as e:
            messagebox.showerror("خطأ في الحفظ", str(e))
            return
        self.clear_payment_form()
        self.refresh_payments_list()
        self.refresh_balances()
        self.refresh_invoice_list()
        self.refresh_dashboard()

    def delete_selected_payment(self):
        p = self._get_selected_payment()
        if not p:
            return
        if messagebox.askyesno("تأكيد الحذف", "هل أنت متأكد من حذف هذه الدفعة؟\nلا يمكن التراجع عن هذا الإجراء"):
            try:
                delete_payment(p["id"])
            except SaveError as e:
                messagebox.showerror("خطأ في الحفظ", str(e))
                return
            self.refresh_payments_list()
            self.refresh_balances()
            self.refresh_invoice_list()
            self.refresh_dashboard()
