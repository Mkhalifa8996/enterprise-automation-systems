# -*- coding: utf-8 -*-
"""تبويب سجل الفواتير: التصفية، والطباعة الفردية/الجماعية، وكشوف الحساب."""

import tkinter as tk
import csv
from tkinter import filedialog, messagebox, ttk

from ..config import get_tk_font
from ..constants import INVOICE_HEADERS
from ..data import (
    SaveError,
    delete_invoice,
    invoice_dict_to_row,
    invoice_payment_status,
    load_invoices,
    load_payments,
)
from .invoice_form import InvoiceForm
from .printing import (
    generate_and_open_invoices_print,
    generate_and_open_statement,
    generate_and_open_statements_print,
)
from .theme import (
    COL_BG,
    COL_BORDER,
    COL_CARD,
    COL_DANGER,
    COL_MUTED,
    COL_NAVY,
    COL_ROW_ALT,
    COL_SUBTEXT,
    COL_SUCCESS,
    COL_TEXT,
    COL_WARN,
)
from .widgets import build_date_field


class InvoicesMixin:
    """يبني تبويب «سجل الفواتير» ويدير إضافة/تعديل/حذف/طباعة الفواتير."""
    def _build_invoices_tab(self):
        wrap = tk.Frame(self.tab_invoices, bg=COL_BG)
        wrap.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(wrap, text="سجل الفواتير", bg=COL_BG, fg=COL_NAVY,
                 font=get_tk_font(15, "bold")).pack(anchor="e")

        top = tk.Frame(wrap, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        top.pack(fill="x", pady=(10, 12))
        top_pad = tk.Frame(top, bg=COL_CARD, padx=14, pady=12)
        top_pad.pack(fill="x")

        # ---- الصف الأول: أزرار الإجراءات + بحث برقم الفاتورة / اسم العميل ----
        row1 = tk.Frame(top_pad, bg=COL_CARD)
        row1.pack(fill="x")

        tk.Label(row1, text="🔍 بحث (رقم الفاتورة / اسم العميل / رقم البيان الجمركي):", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(6, 2))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh_invoice_list())
        search_entry = tk.Entry(row1, textvariable=self.search_var, font=get_tk_font(10), width=28, justify="right",
                     relief="solid", bd=1, highlightthickness=1, highlightbackground=COL_BORDER)
        search_entry.pack(side="right", padx=4, ipady=3)

        # (Declaration-number search merged into general search box)

        ttk.Button(row1, text="＋ فاتورة جديدة", style="Accent.TButton", command=self.open_new_invoice).pack(side="right", padx=3)
        ttk.Button(row1, text="✎ تعديل", style="Ghost.TButton", command=self.edit_selected_invoice).pack(side="right", padx=3)
        ttk.Button(row1, text="🗑 حذف", style="Danger.TButton", command=self.delete_selected_invoice).pack(side="right", padx=3)
        ttk.Button(row1, text="🖨 طباعة (فاتورة أو أكثر)", style="Ghost.TButton", command=self.print_selected_invoice).pack(side="right", padx=3)
        tk.Label(row1, text="💡 حدد عدة فواتير بالضغط مع Ctrl أو Shift لطباعتها دفعة واحدة",
                 bg=COL_CARD, fg=COL_MUTED, font=get_tk_font(8)).pack(side="right", padx=(10, 0))

        tk.Frame(top_pad, bg=COL_BORDER, height=1).pack(fill="x", pady=10)

        # ---- الصف الثاني: تصفية حسب العميل والفترة الزمنية + إجمالي النتائج ----
        row2 = tk.Frame(top_pad, bg=COL_CARD)
        row2.pack(fill="x")

        tk.Label(row2, text="العميل:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(6, 2))
        self.filter_customer_var = tk.StringVar(value="الكل")
        self.filter_customer_combo = ttk.Combobox(
            row2, textvariable=self.filter_customer_var, font=get_tk_font(10),
            justify="right", width=20, state="readonly"
        )
        self.filter_customer_combo.pack(side="right", padx=4)
        self.filter_customer_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_invoice_list())
        # postcommand يُستدعى دائماً من Tk نفسها قبل فتح القائمة المنسدلة (بالنقر أو
        # لوحة المفاتيح)، بعكس ربط <Button-1> اليدوي الذي قد لا يلتقط كل طرق الفتح
        # فتظهر القائمة فارغة أحياناً رغم وجود عملاء محفوظين فعلياً.
        self.filter_customer_combo.configure(postcommand=self._refresh_customer_filter_values)
        self._refresh_customer_filter_values()

        tk.Label(row2, text="من تاريخ:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(10, 2))
        self.filter_from_var = tk.StringVar()
        self.filter_from_var.trace_add("write", lambda *a: self.refresh_invoice_list())
        from_row, _ = build_date_field(row2, self.filter_from_var)
        from_row.pack(side="right", padx=4)

        tk.Label(row2, text="إلى تاريخ:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(10)).pack(side="right", padx=(10, 2))
        self.filter_to_var = tk.StringVar()
        self.filter_to_var.trace_add("write", lambda *a: self.refresh_invoice_list())
        to_row, _ = build_date_field(row2, self.filter_to_var)
        to_row.pack(side="right", padx=4)
        
        ttk.Button(row2, text="✕ مسح التصفية", style="Ghost.TButton", command=self.clear_invoice_filters).pack(side="right", padx=4)
        ttk.Button(row2, text="📄 كشف حساب العميل", style="Ghost.TButton", command=self.print_customer_statement).pack(side="right", padx=4)

        tk.Label(row2, text="(صيغة التاريخ: YYYY-MM-DD)", bg=COL_CARD, fg=COL_MUTED, font=get_tk_font(8)).pack(side="right", padx=(10, 0))
        self.summary_label = tk.Label(row2, text="", bg=COL_CARD, fg=COL_NAVY, font=get_tk_font(10, "bold"))
        self.summary_label.pack(side="right", padx=10)

        action_row = tk.Frame(top_pad, bg=COL_CARD)
        action_row.pack(fill="x", pady=(10, 0))
        ttk.Button(action_row, text="⟳ تحديث", style="Ghost.TButton", command=self.refresh_invoice_list).pack(side="right", padx=3)
        ttk.Button(action_row, text="⬇ تصدير CSV", style="Ghost.TButton", command=self.export_invoices_csv).pack(side="right", padx=3)
        ttk.Button(action_row, text="📄📄 كشف حساب لعدة عملاء", style="Ghost.TButton",
                   command=self.open_multi_customer_statement_dialog).pack(side="right", padx=3)

        table_card = tk.Frame(wrap, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        table_card.pack(fill="both", expand=True)



        cols = ("invno", "declno", "date", "customer", "port", "total", "paid", "balance", "status")
        headers = {"invno": "رقم الفاتورة", "declno": "رقم البيان الجمركي" , "date": "التاريخ", "customer": "السادة/العميل",
                   "port": "المنفذ", "total": "الإجمالي (د.ك)", "paid": "المدفوع (د.ك)",
                   "balance": "المتبقي (د.ك)", "status": "الحالة"}
        widths = {"invno": 100, "declno": 100, "date": 100, "customer": 200, "port": 110,
                  "total": 110, "paid": 110, "balance": 110, "status": 120}
        self.tree = ttk.Treeview(table_card, columns=cols, show="headings", selectmode="extended")
        self.tree["displaycolumns"] = tuple(reversed(cols))
        for c in cols:
            self.tree.heading(c, text=headers[c], anchor="e")
            self.tree.column(c, anchor="e", width=widths[c])
        self.tree.tag_configure("st_paid", foreground=COL_SUCCESS, font=get_tk_font(10, "bold"))
        self.tree.tag_configure("st_partial", foreground=COL_WARN, font=get_tk_font(10, "bold"))
        self.tree.tag_configure("st_unpaid", foreground=COL_DANGER, font=get_tk_font(10, "bold"))
        self.tree.tag_configure("rowodd", background=COL_CARD)
        self.tree.tag_configure("roweven", background=COL_ROW_ALT)
        self.tree.pack(fill="both", expand=True, padx=1, pady=1)
        self.tree.bind("<Double-1>", lambda e: self.edit_selected_invoice())

    def refresh_invoice_list(self):
        query = (self.search_var.get() or "").strip().lower()
        # merged declno searching into the main query; no separate decl_query
        customer_filter = self.filter_customer_var.get() if hasattr(self, "filter_customer_var") else "الكل"
        date_from = (self.filter_from_var.get() or "").strip() if hasattr(self, "filter_from_var") else ""
        date_to = (self.filter_to_var.get() or "").strip() if hasattr(self, "filter_to_var") else ""

        for row in self.tree.get_children():
            self.tree.delete(row)
        self._all_invoices = load_invoices()

        filtered = []
        for inv in self._all_invoices:
            # بحث حر برقم الفاتورة أو اسم العميل
            hay = f"{inv.get('invno','')} {inv.get('customer','')} {inv.get('declno','') }".lower()
            if query and query not in hay:
                continue
            # تصفية حسب عميل محدد
            if customer_filter and customer_filter != "الكل" and inv.get("customer", "") != customer_filter:
                continue
            # (declno is covered by the general hay string)
            # تصفية حسب الفترة الزمنية (يعتمد على أن التاريخ بصيغة YYYY-MM-DD قابلة للمقارنة نصياً)
            inv_date = str(inv.get("date", ""))
            if date_from and inv_date < date_from:
                continue
            if date_to and inv_date > date_to:
                continue
            filtered.append(inv)

        self._filtered_invoices = filtered
        status_map = invoice_payment_status(self._all_invoices, load_payments())
        status_labels = {"paid": "مسددة ✅", "partial": "جزئية ⏳", "unpaid": "غير مسددة ⛔"}
        status_tags = {"paid": "st_paid", "partial": "st_partial", "unpaid": "st_unpaid"}

        total_sum = 0.0
        for row_idx, inv in enumerate(filtered):
            no = str(inv.get("invno", ""))
            st = status_map.get(no, {"paid": 0.0, "balance": float(inv.get("total") or 0), "status": "unpaid"})
            stripe = "roweven" if row_idx % 2 else "rowodd"
            self.tree.insert("", "end", iid=no,
                              values=(inv.get("invno", ""), inv.get("declno", ""), inv.get("date", ""),
                                      inv.get("customer", ""), inv.get("port", ""),
                                      f'{float(inv.get("total") or 0):.3f}',
                                      f'{st["paid"]:.3f}', f'{st["balance"]:.3f}',
                                      status_labels[st["status"]]),
                              tags=(stripe, status_tags[st["status"]]))
            total_sum += float(inv.get("total") or 0)

        if hasattr(self, "summary_label"):
            self.summary_label.config(
                text=f"عدد الفواتير: {len(filtered)}    |    الإجمالي: {total_sum:.3f} د.ك"
            )

    def _refresh_customer_filter_values(self):
        current = self.filter_customer_var.get() if hasattr(self, "filter_customer_var") else "الكل"
        names = ["الكل"] + self.all_customer_names()
        self.filter_customer_combo.configure(values=names)
        if current not in names:
            self.filter_customer_var.set("الكل")

    def clear_invoice_filters(self):
        self.search_var.set("")
        self.filter_customer_var.set("الكل")
        self.filter_from_var.set("")
        self.filter_to_var.set("")
        self.refresh_invoice_list()

    def export_invoices_csv(self):
        invoices = getattr(self, "_filtered_invoices", load_invoices())
        if not invoices:
            messagebox.showinfo("تنبيه", "لا توجد فواتير لعمل تصدير CSV في الوقت الحالي.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="invoices_export.csv",
            filetypes=[("ملفات CSV", "*.csv"), ("الكل", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(INVOICE_HEADERS)
                for inv in invoices:
                    writer.writerow(invoice_dict_to_row(inv))
        except OSError as exc:
            messagebox.showerror("خطأ في التصدير", f"تعذر تصدير الملف:\n{exc}")
            return

        messagebox.showinfo("تم", f"تم تصدير {len(invoices)} فاتورة بنجاح إلى:\n{path}")

    def print_customer_statement(self):
        customer = self.filter_customer_var.get()
        if not customer or customer == "الكل":
            messagebox.showinfo("تنبيه", "الرجاء اختيار عميل محدد من قائمة \"العميل\" أعلاه لطباعة كشف حسابه")
            return
        # نجلب كل حركات هذا العميل (فواتير ودفعات) لحساب الرصيد الافتتاحي بشكل صحيح
        # قبل تصفية الفترة الزمنية المطلوبة في كشف الحساب
        all_invoices = [i for i in load_invoices() if i.get("customer") == customer]
        all_payments = [p for p in load_payments() if p.get("customer") == customer]
        if not all_invoices and not all_payments:
            messagebox.showinfo("تنبيه", "لا توجد أي فواتير أو دفعات لهذا العميل لعرضها في كشف الحساب")
            return
        generate_and_open_statement(
            customer=customer,
            date_from=(self.filter_from_var.get() or "").strip(),
            date_to=(self.filter_to_var.get() or "").strip(),
            invoices=all_invoices,
            payments=all_payments,
        )

    def open_multi_customer_statement_dialog(self):
        """يفتح نافذة صغيرة لاختيار عدة عملاء دفعة واحدة (Ctrl/Shift للتحديد
        المتعدد أو زر "تحديد الكل")، مع فترة زمنية مشتركة اختيارية، ثم يُنشئ
        مستنداً واحداً يجمع كشف حساب كل عميل في صفحة مستقلة قابلة للطباعة معاً."""
        names = self.all_customer_names()
        if not names:
            messagebox.showinfo("تنبيه", "لا يوجد عملاء محفوظون بعد. أضف عملاء أولاً من تبويب \"العملاء\"")
            return

        win = tk.Toplevel(self)
        win.title("كشف حساب لعدة عملاء")
        win.configure(bg=COL_BG)
        win.transient(self)
        win.grab_set()
        win.geometry("460x560")
        win.minsize(420, 480)

        tk.Label(win, text="📄📄 اختر العملاء المطلوب طباعة كشوف حسابهم", bg=COL_BG, fg=COL_NAVY,
                 font=get_tk_font(11, "bold")).pack(anchor="e", padx=14, pady=(14, 4))
        tk.Label(win, text="حدد عدة عملاء بالضغط مع Ctrl أو Shift، أو استخدم زر \"تحديد الكل\" أدناه",
                 bg=COL_BG, fg=COL_SUBTEXT, font=get_tk_font(9), justify="right").pack(anchor="e", padx=14)

        list_card = tk.Frame(win, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        list_card.pack(fill="both", expand=True, padx=14, pady=(10, 8))

        # حجز مساحة صف الأزرار السفلي أولاً (نفس مبدأ الإصلاح في تبويبي العملاء
        # والدفعات) حتى لا يختفي أي زر عند تصغير النافذة.
        list_btns = tk.Frame(list_card, bg=COL_CARD)
        list_btns.pack(side="bottom", fill="x", padx=8, pady=8)
        ttk.Button(list_btns, text="تحديد الكل", style="Ghost.TButton",
                   command=lambda: names_list.selection_set(0, "end")).pack(side="right", padx=2)
        ttk.Button(list_btns, text="إلغاء التحديد", style="Ghost.TButton",
                   command=lambda: names_list.selection_clear(0, "end")).pack(side="right", padx=2)

        list_row = tk.Frame(list_card, bg=COL_CARD)
        list_row.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        scroll = tk.Scrollbar(list_row, orient="vertical")
        names_list = tk.Listbox(list_row, selectmode=tk.EXTENDED, font=get_tk_font(10), justify="right",
                                 exportselection=False, yscrollcommand=scroll.set, activestyle="none",
                                 relief="solid", bd=1, selectbackground=COL_NAVY, selectforeground="white")
        scroll.config(command=names_list.yview)
        scroll.pack(side="left", fill="y")
        names_list.pack(side="left", fill="both", expand=True)
        for name in names:
            names_list.insert("end", name)

        period_card = tk.Frame(win, bg=COL_CARD, highlightthickness=1, highlightbackground=COL_BORDER)
        period_card.pack(fill="x", padx=14, pady=(0, 10))
        period_row = tk.Frame(period_card, bg=COL_CARD)
        period_row.pack(fill="x", padx=10, pady=10)

        tk.Label(period_row, text="من تاريخ:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(9)).pack(side="right", padx=(10, 2))
        dlg_from_var = tk.StringVar(value=(self.filter_from_var.get() or ""))
        dlg_from_row, _ = build_date_field(period_row, dlg_from_var)
        dlg_from_row.pack(side="right", padx=4)

        tk.Label(period_row, text="إلى تاريخ:", bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(9)).pack(side="right", padx=(6, 2))
        dlg_to_var = tk.StringVar(value=(self.filter_to_var.get() or ""))
        dlg_to_row, _ = build_date_field(period_row, dlg_to_var)
        dlg_to_row.pack(side="right", padx=4)

        bottom_btns = tk.Frame(win, bg=COL_BG)
        bottom_btns.pack(fill="x", padx=14, pady=(0, 14))

        def do_print():
            sel_indices = names_list.curselection()
            if not sel_indices:
                messagebox.showinfo("تنبيه", "الرجاء اختيار عميل واحد على الأقل من القائمة", parent=win)
                return
            selected_names = [names_list.get(i) for i in sel_indices]
            date_from = (dlg_from_var.get() or "").strip()
            date_to = (dlg_to_var.get() or "").strip()

            all_invoices = load_invoices()
            all_payments = load_payments()
            items = []
            skipped = []
            for customer in selected_names:
                cust_invoices = [i for i in all_invoices if i.get("customer") == customer]
                cust_payments = [p for p in all_payments if p.get("customer") == customer]
                if not cust_invoices and not cust_payments:
                    skipped.append(customer)
                    continue
                items.append({
                    "customer": customer, "date_from": date_from, "date_to": date_to,
                    "invoices": cust_invoices, "payments": cust_payments,
                })

            if not items:
                messagebox.showinfo("تنبيه", "لا توجد أي فواتير أو دفعات لأي من العملاء المحددين", parent=win)
                return

            if skipped:
                messagebox.showinfo(
                    "تنبيه",
                    "تم تجاوز العملاء التالية أسماؤهم لعدم وجود أي فواتير أو دفعات لهم:\n" + "، ".join(skipped),
                    parent=win,
                )
            win.destroy()
            generate_and_open_statements_print(items)

        ttk.Button(bottom_btns, text="🖨 طباعة كشوف العملاء المحددين", style="Accent.TButton", command=do_print).pack(side="right", padx=3)
        ttk.Button(bottom_btns, text="إلغاء", style="Ghost.TButton", command=win.destroy).pack(side="right", padx=3)

    def _get_selected_invoice(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار فاتورة من القائمة أولاً")
            return None
        if len(sel) > 1:
            messagebox.showinfo("تنبيه", "الرجاء اختيار فاتورة واحدة فقط لهذا الإجراء")
            return None
        invno = sel[0]
        for inv in self._all_invoices:
            if str(inv["invno"]) == str(invno):
                return inv
        return None

    def _get_selected_invoices(self):
        """يعيد كل الفواتير المحددة حالياً في الجدول (يدعم تحديد أكثر من فاتورة
        بالضغط مع Ctrl أو Shift، وهذا ما تعتمد عليه ميزة طباعة عدة فواتير دفعة واحدة)"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار فاتورة واحدة أو أكثر من القائمة أولاً\n(يمكن تحديد عدة فواتير بالضغط مع Ctrl أو Shift أثناء التحديد)")
            return []
        by_no = {str(inv["invno"]): inv for inv in self._all_invoices}
        result = [by_no[str(no)] for no in sel if str(no) in by_no]
        # نحافظ على ترتيب ظهورها في الجدول (وليس ترتيب الضغط العشوائي) لطباعة منطقية
        order = {str(inv["invno"]): i for i, inv in enumerate(self._all_invoices)}
        result.sort(key=lambda inv: order.get(str(inv["invno"]), 0))
        return result

    def open_new_invoice(self):
        InvoiceForm(self, invoice=None)

    def edit_selected_invoice(self):
        inv = self._get_selected_invoice()
        if inv:
            InvoiceForm(self, invoice=inv)

    def delete_selected_invoice(self):
        inv = self._get_selected_invoice()
        if not inv:
            return
        if messagebox.askyesno("تأكيد الحذف",
                                f"هل أنت متأكد من حذف الفاتورة رقم {inv['invno']}؟\nلا يمكن التراجع عن هذا الإجراء"):
            try:
                delete_invoice(inv["invno"])
            except SaveError as e:
                messagebox.showerror("خطأ في الحفظ", str(e))
                return
            self.refresh_invoice_list()
            if hasattr(self, "bal_tree"):
                self.refresh_balances()
            self.refresh_dashboard()

    def print_selected_invoice(self):
        invoices = self._get_selected_invoices()
        if not invoices:
            return
        if len(invoices) > 1:
            nums = "، ".join(str(i["invno"]) for i in invoices)
            if not messagebox.askyesno(
                "تأكيد الطباعة الجماعية",
                f"سيتم إنشاء مستند طباعة واحد يضم {len(invoices)} فاتورة "
                f"(كل فاتورة في صفحة مستقلة):\n{nums}\n\nهل تريد المتابعة؟"
            ):
                return
        generate_and_open_invoices_print(invoices)
