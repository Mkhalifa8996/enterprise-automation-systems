# -*- coding: utf-8 -*-
"""
شاشة الفواتير المجمّعة (تبويبات داخل شاشة واحدة):
  - إصدار الفواتير وسجلها وطباعتها
  - تسجيل دفعات العملاء (تحصيل جزئي/كامل) وتحديث حالة الفاتورة
  - كشف حساب عميل (فواتير مدين ودفعات دائن مع رصيد متحرك) وطباعته
"""

import os
import tempfile
import webbrowser
import tkinter as tk
from tkinter import ttk
from ui import dialogs as messagebox
from ui.rtl import add_rtl_tabs
import restaurant_data as rd
from ui.theme import (
    COLOR_BG,
    COLOR_CARD,
    COLOR_TEXT,
    COLOR_MUTED,
    F_LABEL,
    F_BODY,
    F_BOLD,
    safe_str,
    card_frame,
)
from ui.tabs import CrudTab
from ui.record_window import RecordPrintWindow
from ui.printing import generate_and_open_invoice_print


class InvoicesPages:
    # ---------------- بناء الصفحة المجمّعة ----------------
    def _build_invoices_page(self):
        frame = tk.Frame(self.pages_area, bg=COLOR_BG)
        nb = ttk.Notebook(frame)
        nb.pack(fill="both", expand=True)
        self.invoices_notebook = nb
        self.sub_notebooks["invoices"] = nb

        issue_tab = tk.Frame(nb, bg=COLOR_BG)
        payments_tab = tk.Frame(nb, bg=COLOR_BG)
        statement_tab = tk.Frame(nb, bg=COLOR_BG)
        add_rtl_tabs(nb, [
            (issue_tab, " 🧾 إصدار الفواتير والسجل "),
            (payments_tab, " 💵 تسجيل دفعة "),
            (statement_tab, " 📄 كشف حساب عميل "),
        ])

        self._build_issue_section(issue_tab)
        self._build_payments_section(payments_tab)
        self._build_statement_section(statement_tab)

        self.register_page("invoices", frame, refreshers=[
            self.refresh_customer_combo,
            self.refresh_unbilled_lists,
            self.refresh_invoice_history,
            self.refresh_payment_options,
            self.payments_tab.refresh,
            self.refresh_statement_options,
        ])

    # ---------------- تبويب إصدار الفواتير ----------------
    def _build_issue_section(self, parent):
        frame = tk.Frame(parent, bg=COLOR_BG)
        frame.pack(fill="both", expand=True)

        # ===== بطاقة إصدار الفاتورة — تخطيط نظيف =====
        top = card_frame(frame, "إصدار فاتورة جديدة لعميل")
        top.pack(fill="x", padx=16, pady=(16, 8))
        top_body = top.body
        row = tk.Frame(top_body, bg=COLOR_CARD)
        row.pack(fill="x", padx=14, pady=(0, 14))

        tk.Label(row, text="العميل:", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).grid(
            row=0, column=3, padx=6, pady=6, sticky="e")
        self.inv_customer_var = tk.StringVar()
        self.inv_customer_combo = ttk.Combobox(row, textvariable=self.inv_customer_var, font=F_BODY,
                                                justify="right", state="readonly", width=28)
        self.inv_customer_combo.grid(row=0, column=2, padx=6, pady=6, sticky="ew")
        self.inv_customer_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_unbilled_lists())
        ttk.Button(row, text="تحديث القائمة", style="TButton",
                   command=self.refresh_customer_combo).grid(row=0, column=1, padx=6, pady=6)
        ttk.Button(row, text="إصدار الفاتورة", style="Accent.TButton",
                   command=self.issue_invoice).grid(
            row=0, column=0, padx=6, pady=6)
        for i in range(4):
            row.grid_columnconfigure(i, weight=1)

        lists_frame = tk.Frame(frame, bg=COLOR_BG)
        lists_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # شريط الأدوات في الأسفل
        tools = tk.Frame(lists_frame, bg=COLOR_BG)
        tools.pack(side="bottom", fill="x", padx=0, pady=(8, 0))
        ttk.Button(tools, text="عرض سجل الفاتورة المحدد",
                   command=self.open_selected_invoice_record).pack(side="right", padx=4)

        orders_box = card_frame(lists_frame, "طلبات مؤسسات غير مفوترة لهذا العميل")
        orders_box.pack(side="right", fill="both", expand=True, padx=(8, 0))
        self.inv_orders_list = tk.Listbox(orders_box.body, selectmode="multiple", font=F_BODY,
                                           justify="right", height=10, relief="flat",
                                           highlightthickness=0, activestyle="none")
        self.inv_orders_list.pack(fill="both", expand=True, padx=10, pady=10)
        self.inv_orders_list.bind("<Double-1>", lambda e: self.issue_invoice())

        events_box = card_frame(lists_frame, "عزائم ومناسبات غير مفوترة لهذا العميل")
        events_box.pack(side="right", fill="both", expand=True, padx=(8, 0))
        self.inv_events_list = tk.Listbox(events_box.body, selectmode="multiple", font=F_BODY,
                                           justify="right", height=10, relief="flat",
                                           highlightthickness=0, activestyle="none")
        self.inv_events_list.pack(fill="both", expand=True, padx=10, pady=10)
        self.inv_events_list.bind("<Double-1>", lambda e: self.issue_invoice())

        hist_box = card_frame(frame, "سجل الفواتير الصادرة")
        hist_box.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        table_wrap = tk.Frame(hist_box.body, bg=COLOR_CARD)
        table_wrap.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        cols = [k for k, _ in rd.INVOICE_FIELDS if k != "items_json"]
        self.inv_tree = ttk.Treeview(table_wrap, columns=cols, show="headings", selectmode="browse")
        self.inv_tree.tag_configure("oddrow", background=COLOR_CARD)
        self.inv_tree.tag_configure("evenrow", background=COLOR_BG)
        for k, label in rd.INVOICE_FIELDS:
            if k == "items_json":
                continue
            self.inv_tree.heading(k, text=label)
            # عرض أعمدة مناسب للمحتوى
            if k in ("invoice_no", "date", "status"):
                self.inv_tree.column(k, width=100, anchor="center")
            elif k in ("total", "paid_amount", "remaining"):
                self.inv_tree.column(k, width=95, anchor="e")
            else:
                self.inv_tree.column(k, width=130, anchor="center")
        vs = ttk.Scrollbar(table_wrap, orient="vertical", command=self.inv_tree.yview)
        self.inv_tree.configure(yscrollcommand=vs.set)
        vs.pack(side="left", fill="y")
        self.inv_tree.pack(fill="both", expand=True)

        btns = tk.Frame(hist_box.body, bg=COLOR_CARD)
        btns.pack(fill="x", padx=14, pady=(0, 6), anchor="e")
        ttk.Button(btns, text="طباعة الفاتورة المحددة (HTML)", style="Accent.TButton",
                   command=self.print_selected_invoice).pack(side="right", padx=4)
        ttk.Button(btns, text="حفظ الفاتورة PDF",
                   command=self.save_selected_invoice_pdf).pack(side="right", padx=4)
        ttk.Button(btns, text="حذف الفاتورة المحددة", style="Danger.TButton",
                   command=self.delete_selected_invoice).pack(side="right", padx=4)

        search_row = tk.Frame(hist_box.body, bg=COLOR_CARD)
        search_row.pack(fill="x", padx=14, pady=(0, 14), anchor="e")
        tk.Label(search_row, text="بحث (عميل / رقم فاتورة):", font=F_LABEL,
                 bg=COLOR_CARD, fg=COLOR_TEXT).pack(side="right", padx=6)
        self.inv_search_var = tk.StringVar()
        ent = tk.Entry(search_row, textvariable=self.inv_search_var, font=F_BODY,
                       justify="right", width=26, relief="solid", bd=1)
        ent.pack(side="right", padx=6)
        ent.bind("<KeyRelease>", lambda e: self.refresh_invoice_history())
        tk.Label(search_row, text="الحالة:", font=F_LABEL,
                 bg=COLOR_CARD, fg=COLOR_TEXT).pack(side="right", padx=(14, 2))
        self.inv_status_var = tk.StringVar(value="الكل")
        status_combo = ttk.Combobox(search_row, textvariable=self.inv_status_var,
                                    values=["الكل", "غير مدفوعة", "جزئية", "مدفوعة"],
                                    state="readonly", width=12, justify="right")
        status_combo.pack(side="right", padx=6)
        status_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_invoice_history())

    # ---------------- تبويب تسجيل الدفعات ----------------
    def _build_payments_section(self, parent):
        self.payment_info_var = tk.StringVar(value="اختر فاتورة لعرض تفاصيلها والمتبقي عليها.")

        def wrapped_save(data, editing_key=None):
            rd.save_payment(data, editing_key)
            self.refresh_invoice_history()          # تحديث عمودي المدفوع والحالة مباشرة

        def wrapped_delete(row_id):
            rd.delete_payment(row_id)
            self.refresh_invoice_history()

        self.payments_tab = CrudTab(
            parent, rd.PAYMENT_FIELDS, rd.load_payments, wrapped_save, wrapped_delete,
            "id", "تسجيل دفعة من عميل على فاتورة",
            select_fields={"invoice_no": [], "method": rd.PAYMENT_METHODS},
            readonly_fields=["id", "customer"],
            extra_buttons=[
                {"label": "تعبئة المتبقي على الفاتورة", "style": "Accent.TButton",
                 "command": self.prefill_payment_balance},
            ])
        self.payments_tab.frame.pack(fill="both", expand=True)

        info = tk.Label(self.payments_tab.frame, textvariable=self.payment_info_var,
                        font=F_BOLD, bg=COLOR_CARD, fg=COLOR_MUTED, anchor="e")
        info.pack(fill="x", padx=30, pady=(0, 10))
        self.payments_tab.combos["invoice_no"].bind(
            "<<ComboboxSelected>>", lambda e: self.on_payment_invoice_selected())

    def refresh_payment_options(self):
        """تحديث قائمة الفواتير المتاحة للتحصيل في تبويب الدفعات."""
        self._payment_invoices = {str(inv.get("invoice_no", "")).strip(): inv
                                  for inv in rd.load_invoices()}
        self.payments_tab.refresh_combo("invoice_no", list(self._payment_invoices))

    def on_payment_invoice_selected(self):
        """عند اختيار فاتورة: تعبئة العميل والمتبقي وعرض ملخص الفاتورة."""
        invno = self.payments_tab.vars["invoice_no"].get().strip()
        inv = self._payment_invoices.get(invno)
        if not inv:
            return
        total = rd.safe_float(inv.get("total"))
        paid = rd.safe_float(inv.get("paid_amount"))
        balance = max(total - paid, 0.0)
        self.payments_tab.vars["customer"].set(safe_str(inv.get("customer")))
        if not self.payments_tab.vars["amount"].get().strip():
            self.payments_tab.vars["amount"].set("%.3f" % balance)
        self.payment_info_var.set(
            "فاتورة %s — العميل: %s — الإجمالي: %.3f — المدفوع: %.3f — المتبقي: %.3f د.ك"
            % (invno, inv.get("customer", ""), total, paid, balance))

    def prefill_payment_balance(self):
        """زر: تعبئة حقل المبلغ بالمتبقي على الفاتورة المحددة."""
        invno = self.payments_tab.vars["invoice_no"].get().strip()
        inv = getattr(self, "_payment_invoices", {}).get(invno)
        if not inv:
            messagebox.showwarning("تنبيه", "الرجاء اختيار رقم الفاتورة أولاً.")
            return
        total = rd.safe_float(inv.get("total"))
        paid = rd.safe_float(inv.get("paid_amount"))
        balance = max(total - paid, 0.0)
        if balance <= 0:
            messagebox.showinfo("تنبيه", "هذه الفاتورة محصّلة بالكامل.")
            return
        self.payments_tab.vars["amount"].set("%.3f" % balance)
        self.on_payment_invoice_selected()

    # ---------------- تبويب كشف حساب عميل ----------------
    def _build_statement_section(self, parent):
        frame = tk.Frame(parent, bg=COLOR_BG)
        frame.pack(fill="both", expand=True)

        top = card_frame(frame, "كشف حساب عميل (الفواتير مدين — الدفعات دائن)")
        top.pack(fill="x", padx=16, pady=(16, 8))
        row = tk.Frame(top.body, bg=COLOR_CARD)
        row.pack(fill="x", padx=14, pady=(0, 8))

        tk.Label(row, text="العميل:", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_TEXT).grid(
            row=0, column=3, padx=6, pady=6, sticky="e")
        self.stmt_customer_var = tk.StringVar()
        self.stmt_customer_combo = ttk.Combobox(row, textvariable=self.stmt_customer_var,
                                                font=F_BODY, justify="right",
                                                state="readonly", width=26)
        self.stmt_customer_combo.grid(row=0, column=2, padx=6, pady=6)
        tk.Label(row, text="من تاريخ:", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_TEXT).grid(
            row=0, column=1, padx=(20, 2), pady=6, sticky="e")
        self.stmt_from = tk.StringVar()
        tk.Entry(row, textvariable=self.stmt_from, font=F_BODY, justify="right", width=12,
                 relief="solid", bd=1).grid(row=0, column=1, padx=(70, 6), pady=6)
        tk.Label(row, text="إلى تاريخ:", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_TEXT).grid(
            row=0, column=0, padx=6, pady=6, sticky="e")
        self.stmt_to = tk.StringVar()
        tk.Entry(row, textvariable=self.stmt_to, font=F_BODY, justify="right", width=12,
                 relief="solid", bd=1).grid(row=1, column=0, padx=6, pady=6)
        btns = tk.Frame(top.body, bg=COLOR_CARD)
        btns.pack(fill="x", padx=14, pady=(0, 10), anchor="e")
        ttk.Button(btns, text="عرض الكشف", style="Accent.TButton",
                   command=self.show_statement).pack(side="right", padx=4)
        ttk.Button(btns, text="طباعة الكشف (HTML)",
                   command=self.print_statement).pack(side="right", padx=4)
        ttk.Button(btns, text="حفظ الكشف PDF",
                   command=self.save_statement_pdf).pack(side="right", padx=4)

        self.stmt_totals_var = tk.StringVar(value="اختر عميلاً ثم اضغط «عرض الكشف».")
        tk.Label(top.body, textvariable=self.stmt_totals_var, font=F_BOLD,
                 bg=COLOR_CARD, fg=COLOR_TEXT, anchor="e").pack(fill="x", padx=14, pady=(0, 12))

        table_card = card_frame(frame, "حركات الحساب")
        table_card.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        wrap = tk.Frame(table_card.body, bg=COLOR_CARD)
        wrap.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        cols = ("date", "doc", "description", "debit", "credit", "balance")
        heads = ("التاريخ", "المستند", "البيان", "مدين (عليه)", "دائن (له)", "الرصيد")
        self.stmt_tree = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="browse")
        for k, h in zip(cols, heads):
            self.stmt_tree.heading(k, text=h)
            self.stmt_tree.column(k, anchor="center", width=120)
        vs = ttk.Scrollbar(wrap, orient="vertical", command=self.stmt_tree.yview)
        self.stmt_tree.configure(yscrollcommand=vs.set)
        vs.pack(side="left", fill="y")
        self.stmt_tree.pack(fill="both", expand=True)
        self._statement = None

    def refresh_statement_options(self):
        self.stmt_customer_combo.config(values=[c["name"] for c in rd.load_customers()])

    def statement_period(self):
        """يقرأ فترة كشف الحساب ويتحقق من صيغتها، ويعيد (من, إلى) أو None."""
        d_from = self.stmt_from.get().strip()
        d_to = self.stmt_to.get().strip()
        for value, label in ((d_from, "حقل «من تاريخ»"), (d_to, "حقل «إلى تاريخ»")):
            if value and not rd.is_iso_date(value):
                messagebox.showwarning("تنبيه", f"{label} يجب أن يكون بصيغة YYYY-MM-DD.")
                return None
        if d_from and d_to and d_from > d_to:
            d_from, d_to = d_to, d_from
        return d_from or None, d_to or None

    def show_statement(self):
        customer = self.stmt_customer_var.get().strip()
        if not customer:
            messagebox.showwarning("تنبيه", "الرجاء اختيار العميل أولاً.")
            return
        period = self.statement_period()
        if period is None:
            return
        d_from, d_to = period
        try:
            s = rd.customer_statement(customer, d_from, d_to)
        except ValueError as e:
            messagebox.showwarning("تنبيه", str(e))
            return
        self._statement = s
        for r in self.stmt_tree.get_children():
            self.stmt_tree.delete(r)
        for idx, e in enumerate(s["rows"]):
            iid = "st%d" % idx
            self.stmt_tree.insert("", "end", iid=iid, values=tuple(
                safe_str(e.get(k, "")) for k in ("date", "doc", "description",
                                                 "debit", "credit", "balance")))
        self.stmt_totals_var.set(
            "إجمالي الفواتير: %.3f د.ك   |   إجمالي المدفوع: %.3f د.ك   |   الرصيد المستحق: %.3f د.ك"
            % (s["total_invoiced"], s["total_paid"], s["balance"]))

    def print_statement(self):
        if not self._statement:
            messagebox.showinfo("تنبيه", "اعرض الكشف أولاً قبل طباعته.")
            return
        s = self._statement
        d_from = self.stmt_from.get().strip() or "من البداية"
        d_to = self.stmt_to.get().strip() or "حتى اليوم"
        rows_html = "".join(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td class='c'>%.3f</td>"
            "<td class='c'>%.3f</td><td class='c'><b>%.3f</b></td></tr>"
            % (e.get("date", ""), e.get("doc", ""), e.get("description", ""),
               rd.safe_float(e.get("debit")), rd.safe_float(e.get("credit")),
               rd.safe_float(e.get("balance")))
            for e in s["rows"])
        if not rows_html:
            rows_html = ("<tr><td colspan='6' style='text-align:center;color:#777;'>"
                         "لا توجد حركات في الفترة</td></tr>")
        html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl"><head><meta charset="UTF-8">
<title>كشف حساب - {s['customer']}</title>
<style>
  body{{font-family:'Tahoma','Arial',sans-serif;color:#2A1E19;padding:24px;}}
  h1{{color:#6B2B1F;font-size:20px;margin:0 0 4px;}}
  table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:14px;}}
  th{{background:#6B2B1F;color:#fff;padding:8px;text-align:right;}}
  td{{padding:7px 8px;border-bottom:1px solid #ddd;}}
  td.c{{text-align:center;width:110px;}}
  .total-row td{{font-weight:bold;background:#FBF1DE;border-top:2px solid #D9A441;font-size:14px;}}
  .footer{{margin-top:30px;text-align:center;font-size:10px;color:#777;border-top:1px solid #ddd;padding-top:8px;}}
  @media print {{ .noprint{{display:none;}} }}
</style></head>
<body>
  <h1>كشف حساب عميل</h1>
  <div style="font-size:13px;">العميل: <b>{s['customer']}</b> — الفترة: {d_from} ← {d_to}</div>
  <table>
    <thead><tr><th>التاريخ</th><th>المستند</th><th>البيان</th>
    <th style="width:110px;">مدين (عليه)</th><th style="width:110px;">دائن (له)</th>
    <th style="width:110px;">الرصيد</th></tr></thead>
    <tbody>{rows_html}</tbody>
    <tfoot>
      <tr class="total-row"><td colspan="3">الإجماليات</td>
      <td class="c">{s['total_invoiced']:.3f}</td><td class="c">{s['total_paid']:.3f}</td>
      <td class="c">{s['balance']:.3f}</td></tr>
    </tfoot>
  </table>
  <div class="footer">{rd.COMPANY_NAME_AR} — {rd.COMPANY_ADDRESS_AR} — {rd.COMPANY_PHONE}</div>
  <div class="noprint" style="text-align:center;margin-top:20px;">
    <button onclick="window.print()" style="padding:10px 24px;font-size:14px;">طباعة الكشف</button>
  </div>
</body></html>"""
        safe_name = str(s["customer"]).replace(" ", "_")[:30] or "customer"
        path = os.path.join(tempfile.gettempdir(), "statement_%s.html" % safe_name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open("file://" + path)

    def save_statement_pdf(self):
        """يحفظ كشف الحساب المعروض كملف PDF عربي ويفتحه."""
        if not getattr(self, "_statement", None):
            messagebox.showinfo("تنبيه", "اعرض الكشف أولاً قبل حفظه.")
            return
        try:
            from core.pdf_ar import statement_pdf
        except ImportError:
            messagebox.showwarning("تنبيه", "توليد PDF غير متاح - ثبت حزم reportlab.")
            return
        s = self._statement
        d_from = self.stmt_from.get().strip() or None
        d_to = self.stmt_to.get().strip() or None
        safe_name = str(s["customer"]).replace(" ", "_")[:30] or "customer"
        path = os.path.join(tempfile.gettempdir(), "statement_%s.pdf" % safe_name)
        try:
            statement_pdf(s, d_from, d_to, path)
        except Exception as exc:
            messagebox.showerror("خطأ", "فشل توليد PDF: %s" % exc)
            return
        try:
            os.startfile(path)  # noqa: PGH003 - Windows فقط
        except Exception:
            webbrowser.open("file://%s" % path)

    # ---------------- عمليات إصدار الفواتير والسجل ----------------
    def refresh_customer_combo(self):
        self.inv_customer_combo.config(values=[c["name"] for c in rd.load_customers()])

    def refresh_unbilled_lists(self):
        """يعيد تعبئة قائمتي الطلبات والمناسبات غير المفوترة للعميل المحدد."""
        customer = self.inv_customer_var.get().strip()
        self._unbilled_orders = rd.unbilled_institutional_orders_for_customer(customer)
        self._unbilled_events = rd.unbilled_events_for_customer(customer)
        self.inv_orders_list.delete(0, "end")
        self.inv_events_list.delete(0, "end")
        for o in self._unbilled_orders:
            label = (f"#{o['id']} - {o.get('date','')} - {o.get('meal_type','')} - "
                     f"الكمية {o.get('quantity','')} - {rd.safe_float(o.get('total')):.3f} د.ك")
            self.inv_orders_list.insert("end", label)
        for e in self._unbilled_events:
            label = (f"#{e['id']} - {e.get('event_date','')} - {e.get('event_type','')} - "
                     f"الأشخاص {e.get('guests_count','')} - {rd.safe_float(e.get('total')):.3f} د.ك")
            self.inv_events_list.insert("end", label)

    def issue_invoice(self):
        customer = self.inv_customer_var.get().strip()
        if not customer:
            messagebox.showwarning("تنبيه", "الرجاء اختيار عميل أولاً.")
            return
        order_idx = self.inv_orders_list.curselection()
        event_idx = self.inv_events_list.curselection()
        if not order_idx and not event_idx:
            messagebox.showwarning("تنبيه", "الرجاء اختيار طلب مؤسسة واحد على الأقل أو مناسبة واحدة على الأقل.")
            return
        order_ids = [self._unbilled_orders[i]["id"] for i in order_idx]
        event_ids = [self._unbilled_events[i]["id"] for i in event_idx]
        try:
            inv = rd.create_invoice_for_customer(customer, order_ids, event_ids)
        except ValueError as e:
            messagebox.showwarning("تنبيه", str(e))
            return
        messagebox.showinfo("تم", f"تم إصدار الفاتورة رقم {inv['invoice_no']} بنجاح.")
        self.refresh_unbilled_lists()
        self.refresh_invoice_history()

    def refresh_invoice_history(self):
        qvar = getattr(self, "inv_search_var", None)
        q = qvar.get().strip() if qvar else ""
        svar = getattr(self, "inv_status_var", None)
        wanted = svar.get() if svar else "الكل"
        for row in self.inv_tree.get_children():
            self.inv_tree.delete(row)
        self._invoices = rd.load_invoices()
        self._inv_iid_map = {}
        cols = [k for k, _ in rd.INVOICE_FIELDS if k != "items_json"]
        for idx, inv in enumerate(self._invoices):
            if q:
                if q not in str(inv.get("customer", "")) and q not in str(inv.get("invoice_no", "")):
                    continue
            st = str(inv.get("status") or "")
            if wanted != "الكل" and st != wanted:
                if not (wanted == "غير مدفوعة" and not st and not rd.safe_float(inv.get("paid_amount"))):
                    continue
            iid = "inv%d" % idx      # مفتاح تسلسلي آمن حتى لو تكرر رقم فاتورة في الملف
            self._inv_iid_map[iid] = inv
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.inv_tree.insert("", "end", iid=iid,
                                 values=tuple(safe_str(inv.get(k, "")) for k in cols),
                                 tags=(tag,))

    def selected_invoice(self):
        """يعيد الفاتورة المحددة في جدول السجل، أو None مع رسالة تنبيه."""
        sel = self.inv_tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار فاتورة أولاً.")
            return None
        return getattr(self, "_inv_iid_map", {}).get(sel[0])

    def print_selected_invoice(self):
        inv = self.selected_invoice()
        if inv:
            generate_and_open_invoice_print(inv)

    def save_selected_invoice_pdf(self):
        """يحفظ الفاتورة المحددة كملف PDF عربي ويفتحه."""
        inv = self.selected_invoice()
        if not inv:
            return
        try:
            from core.pdf_ar import invoice_pdf
        except ImportError:
            messagebox.showwarning("تنبيه", "توليد PDF غير متاح - ثبت حزم reportlab.")
            return
        items = [(it.get("desc", ""), it.get("amount", 0)) for it in rd.invoice_items(inv)]
        path = os.path.join(tempfile.gettempdir(), "restaurant_invoice_%s.pdf" % inv.get("invoice_no", "x"))
        try:
            invoice_pdf(inv, items, path)
        except Exception as exc:
            messagebox.showerror("خطأ", "فشل توليد PDF: %s" % exc)
            return
        try:
            os.startfile(path)  # noqa: PGH003 - Windows فقط
        except Exception:
            webbrowser.open("file://%s" % path)

    def delete_selected_invoice(self):
        inv = self.selected_invoice()
        if not inv:
            return
        if messagebox.askyesno("تأكيد الحذف", "هل تريد حذف هذه الفاتورة؟ (لن يُلغى وسم البنود كمفوترة)"):
            rd.delete_invoice(inv.get("invoice_no"))
            self.refresh_invoice_history()
            self.refresh_payment_options()

    def open_selected_invoice_record(self):
        inv = self.selected_invoice()
        if inv:
            self.open_invoice_record_window(inv)

    def open_invoice_record_window(self, inv):
        """يعرض تفاصيل الفاتورة وبنودها في نافذة سجل مستقلة مع زر طباعة."""
        fields = [(k, label, inv.get(k, "")) for k, label in rd.INVOICE_FIELDS
                  if k != "items_json"]
        items = rd.invoice_items(inv)
        breakdown = "\n".join(
            "• %s — %.3f د.ك" % (it.get("desc", ""), rd.safe_float(it.get("amount")))
            for it in items)
        if breakdown:
            fields.append(("items", "بنود الفاتورة", breakdown))
        RecordPrintWindow(
            self, "سجل الفاتورة رقم %s" % inv.get("invoice_no", ""), fields,
            printer_html_fn=lambda: generate_and_open_invoice_print(inv),
            bill_title="طباعة هذه الفاتورة")
