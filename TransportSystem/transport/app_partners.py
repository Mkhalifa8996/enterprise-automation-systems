# -*- coding: utf-8 -*-
"""تبويبات الشركاء وحسابات السائقين."""

import html
from datetime import date
from tkinter import messagebox
from tkinter import simpledialog
import tkinter as tk
from tkinter import ttk
from . import data as td
from .app_config import COLOR_BG, COLOR_CARD, COLOR_MUTED, COLOR_PRIMARY, FONT_NAME, F_BODY, F_H2, F_LABEL
from .print_theme import _open_print_report
from .ui_widgets import apply_table_style, card_frame, center_dialog, make_btn, scrollable_pane
from .driver_links import bind_driver_type_cascade
from .ui_dialogs import date_input
from .ui_helpers import log_exception, safe_str
from .ui_text_edit import refresh_related_screens, set_combo_values

class AppPartnersMixin:
    """تبويبات الشركاء وحسابات السائقين."""

        # ---------------- شاشة الشركاء ----------------
    def _build_partner_vehicle_details_tab(self, parent):
        """تاب يعرض تفاصيل كل سيارة شريك على حدة مع سجل رحلاتها وإمكانية الطباعة."""
        filter_card = card_frame(parent, "اختر الشريك والفترة لعرض تفاصيل سياراته")
        filter_card.pack(fill="x", padx=18, pady=(18, 8))
        filters = tk.Frame(filter_card.body, bg=COLOR_CARD)
        filters.pack(fill="x", padx=18, pady=(0, 14))

        self.partner_details_partner_var = tk.StringVar(value="الكل")
        self.partner_details_from_var = tk.StringVar(value=date.today().replace(day=1).isoformat())
        self.partner_details_to_var = tk.StringVar(value=date.today().isoformat())

        tk.Label(filters, text="من", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(8, 3))
        date_input(filters, self.partner_details_from_var, width=10).pack(side="right", padx=3)
        tk.Label(filters, text="إلى", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(8, 3))
        date_input(filters, self.partner_details_to_var, width=10).pack(side="right", padx=3)
        tk.Label(filters, text="الشريك", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(14, 3))
        self.partner_details_combo = ttk.Combobox(
            filters, textvariable=self.partner_details_partner_var, state="readonly",
            width=20, font=F_BODY, justify="right")
        self.partner_details_combo.pack(side="right", padx=3)
        self.partner_details_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_partner_vehicle_details())
        make_btn(filters, "تحديث", self.refresh_partner_vehicle_details, variant="accent").pack(side="right", padx=4)
        make_btn(filters, "طباعة تفاصيل السيارات", self.print_partner_vehicle_details,
                 variant="secondary").pack(side="right", padx=4)

        summary_card = card_frame(parent, "ملخص إيراد ومصاريف ونصيب كل سيارة")
        summary_card.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        # الترتيب المنطقي: الشريك أولاً، فيظهر على يمين الجدول كبقية الشاشات.
        summary_columns = ("partner", "car_no", "pct", "driver", "revenue", "holiday",
                           "income_total", "car_expenses", "driver_expenses",
                           "net_distributable", "share_amount")
        summary_headers = {
            "partner": "الشريك", "car_no": "السيارة", "pct": "النسبة %",
            "driver": "السائق", "revenue": "إيراد الرحلات", "holiday": "العطل",
            "income_total": "إجمالي الإيراد", "car_expenses": "مصاريف السيارة",
            "driver_expenses": "مصاريف السائق", "net_distributable": "صافي قابل للتوزيع",
            "share_amount": "نصيب الشريك"}
        holder = tk.Frame(summary_card.body, bg=COLOR_CARD)
        holder.pack(fill="both", expand=True, padx=18, pady=14)
        self.partner_details_tree = self._make_partner_tree(holder, summary_columns,
                                                             summary_headers)
        self.partner_details_tree.config(height=7, selectmode="browse")
        for column in summary_columns:
            self.partner_details_tree.column(column, width=110)
        self.partner_details_tree.bind("<<TreeviewSelect>>", self._show_partner_vehicle_breakdown)
        self.partner_details_tree.bind("<Double-1>", lambda _e: self.open_partner_vehicle_window())

        details_card = card_frame(parent, "تفاصيل الحركة للسيارة المختارة")
        details_card.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        details_notebook = ttk.Notebook(details_card.body)
        details_notebook.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        trips_page = tk.Frame(details_notebook, bg=COLOR_CARD)
        revenue_page = tk.Frame(details_notebook, bg=COLOR_CARD)
        car_page = tk.Frame(details_notebook, bg=COLOR_CARD)
        driver_page = tk.Frame(details_notebook, bg=COLOR_CARD)
        details_notebook.add(trips_page, text="سجل رحلات السيارة")
        details_notebook.add(revenue_page, text="إيراد الرحلات والعطل")
        details_notebook.add(car_page, text="حركات مصاريف السيارة")
        details_notebook.add(driver_page, text="حركات مصاريف السائق")
        self.partner_trips_tree = self._make_partner_tree(
            trips_page, ("date", "reference", "customer", "total"),
            {"date": "التاريخ", "reference": "كود الرحلة", "customer": "العميل", "total": "الإجمالي (د.ك)"})
        self.partner_revenue_tree = self._make_partner_tree(
            revenue_page, ("date", "reference", "customer", "revenue", "holiday", "total"),
            {"date": "التاريخ", "reference": "كود الرحلة", "customer": "العميل",
             "revenue": "السعر", "holiday": "العطلة", "total": "الإجمالي"})
        expense_headers = {"date": "التاريخ", "category": "البند", "source": "المصدر", "amount": "المبلغ"}
        self.partner_car_expense_tree = self._make_partner_tree(
            car_page, ("date", "category", "source", "amount"), expense_headers)
        self.partner_driver_expense_tree = self._make_partner_tree(
            driver_page, ("date", "category", "source", "amount"), expense_headers)

    @staticmethod
    def _make_partner_tree(parent, columns, headers):
        """جدول شاشات الشركاء: أول حقل منطقي يظهر على اليمين مثل بقية الشاشات.

        نمرّر الأعمدة معكوسة إلى Treeview، ونحفظ الترتيب المنطقي على الجدول
        ليملؤه _fill_partner_tree بنفس الترتيب دون اختلاق.
        """
        logical = tuple(columns)
        visual = list(reversed(logical))
        tree = ttk.Treeview(parent, columns=visual, show="headings", height=8)
        for column in visual:
            tree.heading(column, text=headers[column])
            tree.column(column, anchor="center", width=140, stretch=True)
        tree.pack(fill="both", expand=True, padx=12, pady=12)
        apply_table_style(tree)
        tree.logical_columns = logical
        return tree

    @staticmethod
    def _fill_partner_tree(tree, records, columns=None, iid_key=None):
        """يملأ الجدول بالقيم بنفس ترتيب رؤوسه تماماً (بلا انزياح).

        القيم تُبنى بترتيب الأعمدة المرئي (المعكوس) حتى يقع كل حقل تحت
        عنوانه، ويبقى أول حقل منطقي على يمين الجدول كما في بقية الشاشات.
        """
        logical = tuple(getattr(tree, "logical_columns", None) or columns or tree["columns"])
        visual = tuple(reversed(logical))
        for row in tree.get_children():
            tree.delete(row)
        # كل الأعمدة المالية تُعرض بمنازل ثلاث ثابتة مهما كان مصدرها.
        numeric = ("revenue", "holiday", "total", "amount", "debit", "credit",
                   "balance", "pct", "total_pct", "income_total", "car_expenses",
                   "driver_expenses", "net_distributable", "share_amount",
                   "distributable", "vehicle_expenses", "driver_salary")
        for record in records:
            values = []
            for column in visual:
                value = record.get(column, "")
                if column == "voided":
                    # عمود الحالة يعرض المشطوبة بوضوح في الجداول.
                    value = "مشطوبة" if td.is_voided(record) else "سليمة"
                values.append(f"{td.safe_float(value):.3f}" if column in numeric
                              else safe_str(value))
            # معرّف الصف اختياري؛ نحتاجه للتحديد بعد إعادة الملء.
            iid = str(record.get(iid_key, "")) if iid_key else ""
            if iid and tree.exists(iid):
                iid = ""
            tree.insert("", "end", iid=iid or None, values=values)

    def _partner_vehicle_rows(self):
        """يبني صفوف الملخص من جدول الشراكات + الملخص المالي لكل سيارة."""
        period_from = self.partner_details_from_var.get().strip()
        period_to = self.partner_details_to_var.get().strip()
        selected = self.partner_details_partner_var.get().strip()
        rows = []
        for share in td.load_vehicle_partners():
            partner = str(share.get("partner", "")).strip()
            if selected and selected != "الكل" and partner != selected:
                continue
            car_no = str(share.get("car_no", "")).strip()
            if not td._periods_overlap(period_from, period_to,
                                        share.get("start_date"), share.get("end_date")):
                continue
            details = next(iter(td.vehicle_financial_details(period_from, period_to, car_no)), {})
            percentage = td.partner_share_percentage(share.get("ownership_pct"))
            distributable = (td.safe_float(details.get("income_total"))
                             - td.safe_float(details.get("car_expenses"))
                             - td.driver_salary_for_car_period(car_no, period_from, period_to))
            rows.append({
                "iid": f"{partner}::{car_no}",
                "partner": partner, "car_no": car_no, "pct": f"{percentage:.3f}",
                "driver": safe_str(details.get("driver")),
                "revenue": td.safe_float(details.get("revenue")),
                "holiday": td.safe_float(details.get("holiday")),
                "income_total": td.safe_float(details.get("income_total")),
                "car_expenses": td.safe_float(details.get("car_expenses")),
                "driver_expenses": td.safe_float(details.get("driver_expenses")),
                "net_distributable": round(max(0.0, distributable), 3),
                "share_amount": round(max(0.0, distributable) * percentage / 100.0, 3),
                "details": details,
            })
        return rows

    def refresh_partner_vehicle_details(self):
        if not hasattr(self, "partner_details_tree"):
            return
        names = ["الكل"] + td.partner_names()
        set_combo_values(self.partner_details_combo, names)
        if self.partner_details_partner_var.get().strip() not in names:
            self.partner_details_partner_var.set("الكل")
        self._partner_vehicle_rows_cache = rows = self._partner_vehicle_rows()
        # نملأ بنفس ترتيب رؤوس الجدول تماماً حتى لا تنزاح القيم تحت عناوينها.
        self._fill_partner_tree(self.partner_details_tree, rows, iid_key="iid")

    def _selected_partner_vehicle(self, quiet=False):
        selected = self.partner_details_tree.selection()
        if not selected:
            if not quiet:
                messagebox.showinfo("تنبيه", "الرجاء اختيار سيارة من جدول الملخص أولاً.",
                                    parent=self.partners_notebook)
            return None
        return next((row for row in getattr(self, "_partner_vehicle_rows_cache", [])
                     if f"{row['partner']}::{row['car_no']}" == selected[0]), None)

    def _partner_car_trip_rows(self, row):
        period_from = self.partner_details_from_var.get().strip()
        period_to = self.partner_details_to_var.get().strip()
        return [{"date": t.get("date"), "reference": t.get("declaration_trip_no"),
                 "customer": t.get("customer"),
                 "total": td.safe_float(t.get("fee")) + td.safe_float(t.get("holiday_price"))}
                for t in td.load_trips()
                if str(t.get("car_no", "")).strip() == row["car_no"]
                and period_from <= str(t.get("date", "")) <= period_to]

    def _show_partner_vehicle_breakdown(self, _event=None):
        row = self._selected_partner_vehicle(quiet=True)
        if not row:
            return
        details = row["details"]
        self._fill_partner_tree(self.partner_trips_tree, self._partner_car_trip_rows(row),
                                ("date", "reference", "customer", "total"))
        self._fill_partner_tree(self.partner_revenue_tree, details.get("revenue_records", []),
                                ("date", "reference", "customer", "revenue", "holiday", "total"))
        self._fill_partner_tree(self.partner_car_expense_tree, details.get("car_expense_records", []),
                                ("date", "category", "source", "amount"))
        self._fill_partner_tree(self.partner_driver_expense_tree, details.get("driver_expense_records", []),
                                ("date", "category", "source", "amount"))

    def open_partner_vehicle_window(self):
        """نافذة مستقلة تعرض تفاصيل سيارة شريك كاملة مع سجل رحلاتها."""
        row = self._selected_partner_vehicle()
        if not row:
            return
        period_from = self.partner_details_from_var.get().strip()
        period_to = self.partner_details_to_var.get().strip()
        dialog = tk.Toplevel(self)
        dialog.title(f"تفاصيل سيارة الشريك — {row['car_no']}")
        dialog.geometry("1080x640")
        dialog.minsize(820, 500)
        dialog.transient(self)
        dialog.configure(bg=COLOR_BG)
        tk.Label(dialog, text=(f"الشريك: {row['partner']}    |    السيارة: {row['car_no']}    |    "
                               f"النسبة: {row['pct']}%    |    السائق: {row['driver'] or 'غير محدد'}\n"
                               f"الفترة: {period_from or 'البداية'} — {period_to or 'اليوم'}    |    "
                               f"نصيب الشريك: {td.safe_float(row['share_amount']):.3f} د.ك"),
                 font=F_H2, bg=COLOR_BG, fg=COLOR_PRIMARY, anchor="e",
                 justify="right").pack(fill="x", padx=18, pady=(16, 8))
        details = row["details"]
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        pages = (
            ("سجل الرحلات", ("date", "reference", "customer", "total"),
             {"date": "التاريخ", "reference": "كود الرحلة", "customer": "العميل", "total": "الإجمالي (د.ك)"},
             self._partner_car_trip_rows(row)),
            ("إيراد الرحلات والعطل", ("date", "reference", "customer", "revenue", "holiday", "total"),
             {"date": "التاريخ", "reference": "كود الرحلة", "customer": "العميل",
              "revenue": "السعر", "holiday": "العطلة", "total": "الإجمالي"},
             details.get("revenue_records", [])),
            ("مصاريف السيارة", ("date", "category", "source", "amount"),
             {"date": "التاريخ", "category": "البند", "source": "المصدر", "amount": "المبلغ"},
             details.get("car_expense_records", [])),
            ("مصاريف السائق", ("date", "category", "source", "amount"),
             {"date": "التاريخ", "category": "البند", "source": "المصدر", "amount": "المبلغ"},
             details.get("driver_expense_records", [])),
        )
        for label, columns, headers, records in pages:
            page = tk.Frame(notebook, bg=COLOR_CARD)
            notebook.add(page, text=label)
            self._fill_partner_tree(self._make_partner_tree(page, columns, headers), records, columns)
        make_btn(dialog, "طباعة تفاصيل سيارة الشريك", self.print_partner_vehicle_details,
                 variant="accent").pack(pady=(0, 16))
        center_dialog(dialog, self)

    def print_partner_vehicle_details(self):
        """طباعة تقرير كامل عن كل سيارة مسجلة للشركاء في الفترة المحددة."""
        rows = getattr(self, "_partner_vehicle_rows_cache", None)
        if rows is None:
            rows = self._partner_vehicle_rows()
        if not rows:
            messagebox.showinfo("لا توجد بيانات", "لا توجد سيارات شركاء في الفترة المحددة.",
                                parent=self.partners_notebook)
            return
        period_from = self.partner_details_from_var.get().strip()
        period_to = self.partner_details_to_var.get().strip()
        columns = ("partner", "car_no", "pct", "driver", "revenue", "holiday", "income_total",
                   "car_expenses", "driver_expenses", "net_distributable", "share_amount")
        headers = ("الشريك", "السيارة", "النسبة %", "السائق", "إيراد الرحلات", "العطل",
                   "إجمالي الإيراد", "مصاريف السيارة", "مصاريف السائق", "صافي قابل للتوزيع",
                   "نصيب الشريك")
        body = "".join(
            "<tr>" + "".join(
                f"<td class='c'>{html.escape(f'{td.safe_float(row[c]):.3f}' if c in columns[4:] else safe_str(row[c]))}</td>"
                for c in columns) + "</tr>"
            for row in rows)
        trips_sections = ""
        for row in rows:
            trips = self._partner_car_trip_rows(row)
            if not trips:
                continue
            trip_rows = "".join(
                "<tr>"
                f"<td class='c'>{html.escape(safe_str(trip.get('date')))}</td>"
                f"<td class='c'>{html.escape(safe_str(trip.get('reference')))}</td>"
                f"<td>{html.escape(safe_str(trip.get('customer')))}</td>"
                f"<td class='c'>{td.safe_float(trip.get('total')):.3f}</td>"
                "</tr>" for trip in trips)
            trips_sections += (
                f"<h2>سجل رحلات السيارة {html.escape(row['car_no'])} — {html.escape(row['partner'])}</h2>"
                "<table><thead><tr><th>التاريخ</th><th>كود الرحلة</th><th>العميل</th>"
                f"<th>الإجمالي (د.ك)</th></tr></thead><tbody>{trip_rows}</tbody></table>")
        _open_print_report(
            "تفاصيل سيارات الشركاء",
            f"الفترة: {period_from or 'البداية'} — {period_to or 'اليوم'} — عدد السيارات: {len(rows)}",
            f"<h2>ملخص كل سيارة</h2><table><thead><tr>"
            + "".join(f"<th>{html.escape(item)}</th>" for item in headers)
            + f"</tr></thead><tbody>{body}</tbody></table>{trips_sections}",
            f"partner_vehicles_{date.today().isoformat()}.html")

    def _build_partner_payments_tab(self, parent):
        """تبويب دفعات الشركاء: تسجيل دفعة (مدين/دائن) وطباعة كشف الحساب."""
        form_card = card_frame(parent, "إضافة / تعديل دفعة على حساب الشريك")
        form_card.pack(fill="x", padx=18, pady=(18, 8))
        form = tk.Frame(form_card.body, bg=COLOR_CARD)
        form.pack(fill="x", padx=18, pady=(0, 14))

        self.partner_pay_date_var = tk.StringVar(value=date.today().isoformat())
        self.partner_pay_partner_var = tk.StringVar()
        self.partner_pay_type_var = tk.StringVar(value=td.PAYMENT_TYPES[0])
        self.partner_pay_amount_var = tk.StringVar()
        self.partner_pay_notes_var = tk.StringVar()
        self.partner_pay_editing_id = None

        tk.Label(form, text="التاريخ", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(8, 3))
        date_input(form, self.partner_pay_date_var, width=12).pack(side="right", padx=3)
        tk.Label(form, text="اسم الشريك", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        self.partner_pay_partner_combo = ttk.Combobox(
            form, textvariable=self.partner_pay_partner_var, state="normal",
            width=20, font=F_BODY, justify="right")
        self.partner_pay_partner_combo.pack(side="right", padx=3)
        self.partner_pay_partner_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_partner_payment_cars())
        tk.Label(form, text="نوع الدفعة", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        self.partner_pay_type_combo = ttk.Combobox(
            form, textvariable=self.partner_pay_type_var, state="readonly",
            values=td.PAYMENT_TYPES, width=10, font=F_BODY, justify="right")
        self.partner_pay_type_combo.pack(side="right", padx=3)
        tk.Label(form, text="رقم السيارة", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        self.partner_pay_car_combo = ttk.Combobox(
            form, state="readonly", width=14, font=F_BODY, justify="right")
        self.partner_pay_car_combo.pack(side="right", padx=3)
        tk.Label(form, text="المبلغ", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        tk.Entry(form, textvariable=self.partner_pay_amount_var, font=F_BODY,
                 justify="right", width=12).pack(side="right", padx=3)
        tk.Label(form, text="ملاحظات", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        tk.Entry(form, textvariable=self.partner_pay_notes_var, font=F_BODY, justify="right").pack(
            side="right", padx=3, fill="x", expand=True)

        actions = tk.Frame(form_card.body, bg=COLOR_CARD)
        actions.pack(fill="x", padx=18, pady=(0, 12))
        make_btn(actions, "حفظ الدفعة", self.save_partner_payment, variant="accent").pack(side="right", padx=4)
        make_btn(actions, "تعديل", self.edit_partner_payment, variant="secondary").pack(side="right", padx=4)
        make_btn(actions, "إشطب", self.void_partner_payment, variant="danger").pack(side="right", padx=4)
        make_btn(actions, "إعادة الإشطب", self.restore_partner_payment, variant="secondary").pack(side="right", padx=4)
        make_btn(actions, "حذف نهائي", self.delete_partner_payment, variant="danger").pack(side="right", padx=4)
        make_btn(actions, "مسح النموذج", self.clear_partner_payment_form, variant="secondary").pack(side="right", padx=4)

        statement_card = card_frame(parent, "طباعة كشف حساب الشريك خلال فترة محددة")
        statement_card.pack(fill="x", padx=18, pady=(0, 8))
        statement_row = tk.Frame(statement_card.body, bg=COLOR_CARD)
        statement_row.pack(fill="x", padx=18, pady=(0, 12))
        self.partner_stmt_from_var = tk.StringVar(value=date.today().replace(day=1).isoformat())
        self.partner_stmt_to_var = tk.StringVar(value=date.today().isoformat())
        tk.Label(statement_row, text="إلى", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(8, 3))
        date_input(statement_row, self.partner_stmt_to_var, width=11).pack(side="right", padx=3)
        tk.Label(statement_row, text="من", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(8, 3))
        date_input(statement_row, self.partner_stmt_from_var, width=11).pack(side="right", padx=3)
        tk.Label(statement_row, text="الشريك", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(14, 3))
        self.partner_stmt_combo = ttk.Combobox(
            statement_row, state="readonly", width=20, font=F_BODY, justify="right")
        self.partner_stmt_combo.pack(side="right", padx=3)
        make_btn(statement_row, "طباعة كشف الحساب", self.print_partner_statement,
                 variant="accent").pack(side="right", padx=6)

        table_card = card_frame(parent, "سجل دفعات الشركاء")
        table_card.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.partner_pay_tree = self._make_partner_tree(
            table_card.body,
            ("id", "date", "partner", "car_no", "payment_type", "amount", "voided", "notes"),
            {"id": "الرقم", "date": "التاريخ", "partner": "اسم الشريك", "car_no": "رقم السيارة",
             "payment_type": "نوع الدفعة", "amount": "المبلغ (د.ك)", "voided": "الحالة",
             "notes": "ملاحظات"})
        self.partner_pay_tree.bind("<Double-1>", lambda _e: self.edit_partner_payment())

    def _partner_cars_for(self, partner):
        return sorted({str(row.get("car_no", "")).strip() for row in td.load_vehicle_partners()
                       if str(row.get("partner", "")).strip() == partner
                       and str(row.get("car_no", "")).strip()})

    def refresh_partner_payment_cars(self):
        cars = ["(دفعة عامة)"] + self._partner_cars_for(self.partner_pay_partner_var.get().strip())
        current = safe_str(self.partner_pay_car_combo.get()).strip()
        set_combo_values(self.partner_pay_car_combo, cars)
        if not current:
            self.partner_pay_car_combo.set(cars[0])

    def clear_partner_payment_form(self):
        self.partner_pay_date_var.set(date.today().isoformat())
        self.partner_pay_partner_var.set("")
        self.partner_pay_type_var.set(td.PAYMENT_TYPES[0])
        self.partner_pay_amount_var.set("")
        self.partner_pay_notes_var.set("")
        self.partner_pay_editing_id = None
        set_combo_values(self.partner_pay_car_combo, ["(دفعة عامة)"])
        self.partner_pay_car_combo.set("(دفعة عامة)")

    def save_partner_payment(self):
        car_no = safe_str(self.partner_pay_car_combo.get()).strip()
        data = {
            "id": self.partner_pay_editing_id or "",
            "date": self.partner_pay_date_var.get().strip(),
            "partner": self.partner_pay_partner_var.get().strip(),
            "car_no": "" if car_no == "(دفعة عامة)" else car_no,
            "payment_type": self.partner_pay_type_var.get().strip(),
            "amount": self.partner_pay_amount_var.get().strip(),
            "notes": self.partner_pay_notes_var.get().strip(),
        }
        try:
            td.save_partner_payment(data, self.partner_pay_editing_id)
        except Exception as exc:
            messagebox.showerror("حفظ الدفعة", str(exc), parent=self.partners_notebook)
            return
        self.clear_partner_payment_form()
        self.refresh_partner_payments()
        refresh_related_screens(self)

    def _selected_partner_payment(self):
        selected = self.partner_pay_tree.selection()
        if not selected:
            messagebox.showinfo("تنبيه", "الرجاء اختيار دفعة من السجل أولاً.",
                                parent=self.partners_notebook)
            return None
        return next((row for row in td.load_partner_payments()
                     if str(row.get("id")) == selected[0]), None)

    def edit_partner_payment(self):
        row = self._selected_partner_payment()
        if not row:
            return
        self.partner_pay_editing_id = str(row.get("id"))
        self.partner_pay_date_var.set(safe_str(row.get("date")))
        self.partner_pay_partner_var.set(safe_str(row.get("partner")))
        self.partner_pay_type_var.set(safe_str(row.get("payment_type")))
        self.partner_pay_amount_var.set(safe_str(row.get("amount")))
        self.partner_pay_notes_var.set(safe_str(row.get("notes")))
        self.refresh_partner_payment_cars()
        self.partner_pay_car_combo.set(safe_str(row.get("car_no")).strip() or "(دفعة عامة)")

    def delete_partner_payment(self):
        row = self._selected_partner_payment()
        if not row:
            return
        if not messagebox.askyesno(
                "تأكيد الحذف",
                "الحذف نهائي ويزيل الدفعة من كل الكشوف.\n"
                "يُفضَّل استخدام «إشطب» للاحتفاظ بسجل الكشوف السابقة.\n\nهل تريد الحذف النهائي؟"):
            return
        td.delete_partner_payment(row.get("id"))
        self.clear_partner_payment_form()
        self.refresh_partner_payments()
        refresh_related_screens(self)

    def void_partner_payment(self):
        """يشطب الدفعة مع سبب، فتظل ظاهرة في كشف الفترة التي صدرت فيه."""
        row = self._selected_partner_payment()
        if not row:
            return
        if td.is_voided(row):
            messagebox.showinfo("تنبيه", "الدفعة مشطوبة بالفعل.", parent=self.partners_notebook)
            return
        reason = simpledialog.askstring(
            "إشطب الدفعة", "سبب الإشطب (مطلوب):", parent=self.partners_notebook)
        if not str(reason or "").strip():
            return
        try:
            td.void_partner_payment(row.get("id"), reason)
        except Exception as exc:
            messagebox.showerror("إشطب الدفعة", str(exc), parent=self.partners_notebook)
            return
        self.refresh_partner_payments()
        refresh_related_screens(self)

    def restore_partner_payment(self):
        row = self._selected_partner_payment()
        if not row:
            return
        if not td.is_voided(row):
            messagebox.showinfo("تنبيه", "الدفعة سليمة بالفعل.", parent=self.partners_notebook)
            return
        try:
            td.restore_partner_payment(row.get("id"))
        except Exception as exc:
            messagebox.showerror("إعادة الإشطب", str(exc), parent=self.partners_notebook)
            return
        self.refresh_partner_payments()
        refresh_related_screens(self)

    def refresh_partner_payments(self):
        if not hasattr(self, "partner_pay_tree"):
            return
        names = td.partner_names()
        set_combo_values(self.partner_pay_partner_combo, names)
        set_combo_values(self.partner_stmt_combo, names)
        if not safe_str(self.partner_stmt_combo.get()).strip() and names:
            self.partner_stmt_combo.set(names[0])
        self.refresh_partner_payment_cars()
        self._fill_partner_tree(self.partner_pay_tree, td.load_partner_payments(),
                                self.partner_pay_tree["columns"])

    def print_partner_statement(self):
        """كشف حساب الشريك: الدفعات مدينة/دائنة + نصيبه كدفعة مستحقة."""
        partner = safe_str(self.partner_stmt_combo.get()).strip()
        if not partner:
            messagebox.showinfo("تنبيه", "الرجاء اختيار الشريك أولاً.", parent=self.partners_notebook)
            return
        date_from = self.partner_stmt_from_var.get().strip()
        date_to = self.partner_stmt_to_var.get().strip()
        if date_from and date_to and date_from > date_to:
            messagebox.showwarning("تنبيه", "تاريخ البداية يجب أن يسبق تاريخ النهاية.",
                                   parent=self.partners_notebook)
            return
        statement = td.partner_statement(partner, date_from, date_to)
        doc_no = td.next_statement_number("PS")
        movement_rows = "".join(
            f"<tr class='{'voided' if item['voided'] else ''}'>"
            f"<td class='c'>{html.escape(item['date'])}</td>"
            f"<td>{html.escape(item['label'])}</td>"
            f"<td class='c'>{html.escape(item['car_no'] or '—')}</td>"
            f"<td class='c'>{item['debit']:.3f}</td>"
            f"<td class='c'>{item['credit']:.3f}</td>"
            f"<td class='c'>{item['balance']:.3f}</td>"
            f"<td>{html.escape(item['notes'])}</td>"
            "</tr>" for item in statement["movements"])
        share_rows = "".join(
            "<tr>"
            f"<td class='c'>{html.escape(share['car_no'])}</td>"
            f"<td class='c'>{share['ownership_pct']:.3f}</td>"
            f"<td class='c'>{share['revenue']:.3f}</td>"
            f"<td class='c'>{share['vehicle_expenses']:.3f}</td>"
            f"<td class='c'>{share['driver_salary']:.3f}</td>"
            f"<td class='c'>{share['distributable']:.3f}</td>"
            f"<td class='c'>{share['amount']:.3f}</td>"
            "</tr>" for share in statement["shares"])
        share_section = ""
        if statement["shares"]:
            share_section = (
                "<h2>تفصيل نصيب الشريك من صافي إيراد السيارات</h2><table><thead><tr>"
                "<th>السيارة</th><th>النسبة %</th><th>إجمالي الإيراد</th><th>مصاريف السيارة</th>"
                "<th>راتب السائق</th><th>صافي قابل للتوزيع</th><th>النصيب</th></tr></thead>"
                f"<tbody>{share_rows}</tbody><tfoot><tr><td colspan='6'>إجمالي النصيب</td>"
                f"<td class='c'>{statement['total_share']:.3f}</td></tr></tfoot></table>")
        body = (
            "<h2>حركات الحساب</h2><table><thead><tr><th>التاريخ</th><th>البيان</th><th>السيارة</th>"
            "<th>مدين</th><th>دائن</th><th>الرصيد</th><th>ملاحظات</th></tr></thead><tbody>"
            f"{movement_rows}</tbody><tfoot><tr><td colspan='3'>الرصيد النهائي</td>"
            f"<td colspan='4' class='c'>{statement['balance']:.3f}</td></tr></tfoot></table>"
            f"{share_section}")
        _open_print_report(
            f"كشف حساب الشريك — {partner}",
            f"الفترة: {date_from or 'البداية'} — {date_to or 'اليوم'} — تاريخ الطباعة: {date.today().isoformat()}",
            body, f"partner_statement_{date.today().isoformat()}.html", doc_no=doc_no)

    def _build_driver_accounts_tab(self, parent):
        """كشوف حسابات السائقين الداخليين والخارجيين مع دفعاتهم وتفاصيل رحلاتهم."""
        filter_card = card_frame(parent, "اختر السائق ونوعه والفترة لعرض كشف حسابه")
        filter_card.pack(fill="x", padx=18, pady=(18, 8))
        filters = tk.Frame(filter_card.body, bg=COLOR_CARD)
        filters.pack(fill="x", padx=18, pady=(0, 14))

        self.driver_acc_driver_var = tk.StringVar()
        self.driver_acc_type_var = tk.StringVar(value="الكل")
        self.driver_acc_from_var = tk.StringVar(value=date.today().replace(day=1).isoformat())
        self.driver_acc_to_var = tk.StringVar(value=date.today().isoformat())

        tk.Label(filters, text="من", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(8, 3))
        date_input(filters, self.driver_acc_from_var, width=11).pack(side="right", padx=3)
        tk.Label(filters, text="إلى", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(8, 3))
        date_input(filters, self.driver_acc_to_var, width=11).pack(side="right", padx=3)
        tk.Label(filters, text="نوع السائق", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(14, 3))
        self.driver_acc_type_combo = ttk.Combobox(
            filters, textvariable=self.driver_acc_type_var, state="readonly",
            values=["الكل"] + td.DRIVER_TYPES, width=10, font=F_BODY, justify="right")
        self.driver_acc_type_combo.pack(side="right", padx=3)
        self.driver_acc_type_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_driver_accounts())
        tk.Label(filters, text="السائق", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(14, 3))
        self.driver_acc_combo = ttk.Combobox(
            filters, textvariable=self.driver_acc_driver_var, state="readonly",
            width=22, font=F_BODY, justify="right")
        self.driver_acc_combo.pack(side="right", padx=3)
        self.driver_acc_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_driver_accounts())
        make_btn(filters, "تحديث", self.refresh_driver_accounts, variant="accent").pack(side="right", padx=4)
        make_btn(filters, "طباعة كشوف الخارجيين", self.print_external_drivers_statements,
                 variant="secondary").pack(side="right", padx=4)
        make_btn(filters, "طباعة كشف الحساب", self.print_driver_statement,
                 variant="secondary").pack(side="right", padx=4)
        make_btn(filters, "طباعة تفاصيل الرحلات", self.print_driver_trips,
                 variant="secondary").pack(side="right", padx=4)

        pay_card = card_frame(parent, "إضافة / تعديل دفعة على حساب السائق")
        pay_card.pack(fill="x", padx=18, pady=(0, 8))
        pay_row = tk.Frame(pay_card.body, bg=COLOR_CARD)
        pay_row.pack(fill="x", padx=18, pady=(0, 12))
        self.driver_pay_date_var = tk.StringVar(value=date.today().isoformat())
        self.driver_pay_type_var = tk.StringVar(value=td.PAYMENT_TYPES[0])
        self.driver_pay_amount_var = tk.StringVar()
        self.driver_pay_notes_var = tk.StringVar()
        self.driver_pay_editing_id = None
        # ثلاثية السائق: نوع السائق ← السائق ← السيارة (متسلسلة كما في بقية الشاشات)
        self.driver_pay_kind_var = tk.StringVar()
        self.driver_pay_driver_var = tk.StringVar()
        self.driver_pay_car_var = tk.StringVar()

        tk.Label(pay_row, text="التاريخ", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(8, 3))
        date_input(pay_row, self.driver_pay_date_var, width=11).pack(side="right", padx=3)
        # 1) نوع السائق أولاً: يحدّد من هم السائقون المسموح اختيارهم في الحقل التالي.
        tk.Label(pay_row, text="نوع السائق", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        self.driver_pay_kind_combo = ttk.Combobox(
            pay_row, textvariable=self.driver_pay_kind_var, state="readonly",
            values=[""] + td.DRIVER_TYPES, width=10, font=F_BODY, justify="right")
        self.driver_pay_kind_combo.pack(side="right", padx=3)
        # 2) السائق: تظهر أسماؤه حسب النوع المختار.
        tk.Label(pay_row, text="السائق", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        self.driver_pay_driver_combo = ttk.Combobox(
            pay_row, textvariable=self.driver_pay_driver_var, state="normal",
            values=td.driver_names_by_type(), width=20, font=F_BODY, justify="right")
        self.driver_pay_driver_combo.pack(side="right", padx=3)
        # 3) السيارة: تُحدَّد تلقائياً بمجرد اختيار السائق.
        tk.Label(pay_row, text="السيارة", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        self.driver_pay_car_combo = ttk.Combobox(
            pay_row, textvariable=self.driver_pay_car_var, state="normal",
            values=[v["car_no"] for v in td.load_vehicles() if v.get("car_no")],
            width=14, font=F_BODY, justify="right")
        self.driver_pay_car_combo.pack(side="right", padx=3)
        bind_driver_type_cascade(
            {"driver_type": self.driver_pay_kind_var,
             "driver": self.driver_pay_driver_var,
             "car_no": self.driver_pay_car_var},
            {"driver": self.driver_pay_driver_combo, "car_no": self.driver_pay_car_combo},
            get_day=lambda: self.driver_pay_date_var.get().strip())
        self.driver_pay_driver_combo.bind("<<ComboboxSelected>>", lambda _e: self._sync_driver_pay_type())
        tk.Label(pay_row, text="نوع الدفعة", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        self.driver_pay_type_combo = ttk.Combobox(
            pay_row, textvariable=self.driver_pay_type_var, state="readonly",
            values=td.PAYMENT_TYPES, width=10, font=F_BODY, justify="right")
        self.driver_pay_type_combo.pack(side="right", padx=3)
        tk.Label(pay_row, text="المبلغ", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        tk.Entry(pay_row, textvariable=self.driver_pay_amount_var, font=F_BODY,
                 justify="right", width=12).pack(side="right", padx=3)
        tk.Label(pay_row, text="ملاحظات", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        tk.Entry(pay_row, textvariable=self.driver_pay_notes_var, font=F_BODY, justify="right").pack(
            side="right", padx=3, fill="x", expand=True)
        pay_actions = tk.Frame(pay_card.body, bg=COLOR_CARD)
        pay_actions.pack(fill="x", padx=18, pady=(0, 12))
        make_btn(pay_actions, "حفظ الدفعة", self.save_driver_payment, variant="accent").pack(side="right", padx=4)
        make_btn(pay_actions, "تعديل", self.edit_driver_payment, variant="secondary").pack(side="right", padx=4)
        make_btn(pay_actions, "إشطب", self.void_driver_payment, variant="danger").pack(side="right", padx=4)
        make_btn(pay_actions, "إعادة الإشطب", self.restore_driver_payment, variant="secondary").pack(side="right", padx=4)
        make_btn(pay_actions, "حذف نهائي", self.delete_driver_payment, variant="danger").pack(side="right", padx=4)
        make_btn(pay_actions, "مسح النموذج", self.clear_driver_payment_form, variant="secondary").pack(side="right", padx=4)

        body_card = card_frame(parent, "كشف الحساب وسجل رحلات السائق")
        body_card.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        body_notebook = ttk.Notebook(body_card.body)
        body_notebook.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        statement_page = tk.Frame(body_notebook, bg=COLOR_CARD)
        trips_page = tk.Frame(body_notebook, bg=COLOR_CARD)
        payments_page = tk.Frame(body_notebook, bg=COLOR_CARD)
        body_notebook.add(statement_page, text="حركات الحساب")
        body_notebook.add(trips_page, text="كافة تفاصيل الرحلات")
        body_notebook.add(payments_page, text="دفعات السائق")
        self.driver_stmt_tree = self._make_partner_tree(
            statement_page, ("date", "label", "car_no", "debit", "credit", "balance", "notes"),
            {"date": "التاريخ", "label": "البيان", "car_no": "السيارة", "debit": "مدين",
             "credit": "دائن", "balance": "الرصيد", "notes": "ملاحظات"})
        self.driver_trips_tree = self._make_partner_tree(
            trips_page, ("date", "code", "car_no", "customer", "driver_type", "revenue", "holiday", "total"),
            {"date": "التاريخ", "code": "كود الرحلة", "car_no": "السيارة", "customer": "العميل",
             "driver_type": "نوع السائق", "revenue": "السعر", "holiday": "العطلة", "total": "الإجمالي"})
        self.driver_pay_tree = self._make_partner_tree(
            payments_page,
            ("id", "date", "driver", "driver_type", "car_no", "payment_type", "amount", "voided", "notes"),
            {"id": "الرقم", "date": "التاريخ", "driver": "السائق", "driver_type": "نوع السائق",
             "car_no": "السيارة", "payment_type": "نوع الدفعة", "amount": "المبلغ (د.ك)",
             "voided": "الحالة", "notes": "ملاحظات"})
        self.driver_pay_tree.bind("<Double-1>", lambda _e: self.edit_driver_payment())
        self._driver_accounts_parent = parent

    def _driver_options(self, driver_type):
        return [str(row.get("name", "")).strip() for row in td.load_drivers()
                if str(row.get("name", "")).strip()
                and (not driver_type or driver_type == "الكل"
                     or str(row.get("driver_type", "")).strip() == driver_type)]

    def _sync_driver_pay_type(self):
        """يوافق نوع السائق مع سجل السائق المختار (يفضّل ما يختاره المستخدم)."""
        chosen = self.driver_pay_kind_var.get().strip()
        actual = td.driver_type_of(self.driver_pay_driver_var.get().strip())
        if chosen and actual and chosen != actual:
            return
        self.driver_pay_kind_var.set(actual)

    def clear_driver_payment_form(self):
        self.driver_pay_date_var.set(date.today().isoformat())
        self.driver_pay_type_var.set(td.PAYMENT_TYPES[0])
        self.driver_pay_amount_var.set("")
        self.driver_pay_notes_var.set("")
        self.driver_pay_editing_id = None
        # نمسح السائق أولاً ثم النوع حتى لا تملأ السلسلة السيارة من سائق جديد.
        self.driver_pay_driver_var.set("")
        self.driver_pay_kind_var.set("")
        self.driver_pay_car_var.set("")

    def save_driver_payment(self):
        data = {
            "id": self.driver_pay_editing_id or "",
            "date": self.driver_pay_date_var.get().strip(),
            "driver": self.driver_pay_driver_var.get().strip(),
            "driver_type": self.driver_pay_kind_var.get().strip(),
            "car_no": self.driver_pay_car_var.get().strip(),
            "payment_type": self.driver_pay_type_var.get().strip(),
            "amount": self.driver_pay_amount_var.get().strip(),
            "notes": self.driver_pay_notes_var.get().strip(),
        }
        try:
            td.save_driver_payment(data, self.driver_pay_editing_id)
        except Exception as exc:
            messagebox.showerror("حفظ الدفعة", str(exc),
                                 parent=getattr(self, "partners_notebook", self))
            return
        self.clear_driver_payment_form()
        self.refresh_driver_accounts()
        refresh_related_screens(self)

    def _selected_driver_payment(self):
        selected = self.driver_pay_tree.selection()
        if not selected:
            messagebox.showinfo("تنبيه", "الرجاء اختيار دفعة من السجل أولاً.",
                                parent=self.partners_notebook)
            return None
        return next((row for row in td.load_driver_payments()
                     if str(row.get("id")) == selected[0]), None)

    def edit_driver_payment(self):
        row = self._selected_driver_payment()
        if not row:
            return
        self.driver_pay_editing_id = str(row.get("id"))
        self.driver_pay_date_var.set(safe_str(row.get("date")))
        # نضبط النوع قبل السائق حتى تظهر القائمة مفلترة، ثم نستعيد ما حُفظ.
        self.driver_pay_kind_var.set(safe_str(row.get("driver_type")).strip())
        self.driver_pay_driver_var.set(safe_str(row.get("driver")))
        self._sync_driver_pay_type()
        self.driver_pay_car_var.set(safe_str(row.get("car_no")).strip())
        self.driver_pay_type_var.set(safe_str(row.get("payment_type")))
        self.driver_pay_amount_var.set(safe_str(row.get("amount")))
        self.driver_pay_notes_var.set(safe_str(row.get("notes")))

    def delete_driver_payment(self):
        row = self._selected_driver_payment()
        if not row:
            return
        if not messagebox.askyesno(
                "تأكيد الحذف",
                "الحذف نهائي ويزيل الدفعة من كل الكشوف.\n"
                "يُفضَّل استخدام «إشطب» للاحتفاظ بسجل الكشوف السابقة.\n\nهل تريد الحذف النهائي؟"):
            return
        td.delete_driver_payment(row.get("id"))
        self.clear_driver_payment_form()
        self.refresh_driver_accounts()
        refresh_related_screens(self)

    def void_driver_payment(self):
        row = self._selected_driver_payment()
        if not row:
            return
        if td.is_voided(row):
            messagebox.showinfo("تنبيه", "الدفعة مشطوبة بالفعل.", parent=self.partners_notebook)
            return
        reason = simpledialog.askstring(
            "إشطب الدفعة", "سبب الإشطب (مطلوب):", parent=self.partners_notebook)
        if not str(reason or "").strip():
            return
        try:
            td.void_driver_payment(row.get("id"), reason)
        except Exception as exc:
            messagebox.showerror("إشطب الدفعة", str(exc), parent=self.partners_notebook)
            return
        self.refresh_driver_accounts()
        refresh_related_screens(self)

    def restore_driver_payment(self):
        row = self._selected_driver_payment()
        if not row:
            return
        if not td.is_voided(row):
            messagebox.showinfo("تنبيه", "الدفعة سليمة بالفعل.", parent=self.partners_notebook)
            return
        try:
            td.restore_driver_payment(row.get("id"))
        except Exception as exc:
            messagebox.showerror("إعادة الإشطب", str(exc), parent=self.partners_notebook)
            return
        self.refresh_driver_accounts()
        refresh_related_screens(self)

    def _current_driver_statement(self):
        driver = self.driver_acc_driver_var.get().strip()
        return td.driver_statement(driver, self.driver_acc_from_var.get().strip(),
                                   self.driver_acc_to_var.get().strip())

    def refresh_driver_accounts(self):
        if not hasattr(self, "driver_stmt_tree"):
            return
        driver_type = self.driver_acc_type_var.get().strip()
        names = self._driver_options(driver_type)
        current = self.driver_acc_driver_var.get().strip()
        set_combo_values(self.driver_acc_combo, names)
        # لوحة الدفعة تتبع نفس التصفية، وتُحدَّث قائمة سيارتها فوراً.
        set_combo_values(self.driver_pay_driver_combo, td.driver_names_by_type(""))
        if getattr(self, "driver_pay_car_combo", None) is not None:
            set_combo_values(self.driver_pay_car_combo,
                             [v["car_no"] for v in td.load_vehicles() if v.get("car_no")])
        if current not in names:
            self.driver_acc_driver_var.set(names[0] if names else "")
        driver = self.driver_acc_driver_var.get().strip()
        if not driver:
            for tree in (self.driver_stmt_tree, self.driver_trips_tree, self.driver_pay_tree):
                for row in tree.get_children():
                    tree.delete(row)
            return
        statement = self._current_driver_statement()
        self._driver_statement_cache = statement
        self._fill_partner_tree(self.driver_stmt_tree, statement["movements"],
                                ("date", "label", "car_no", "debit", "credit", "balance", "notes"))
        trip_rows = [{"date": t.get("date"), "code": t.get("declaration_trip_no"),
                      "car_no": t.get("car_no"), "customer": t.get("customer"),
                      "driver_type": statement["driver_type"],
                      "revenue": td.safe_float(t.get("fee")),
                      "holiday": td.safe_float(t.get("holiday_price")),
                      "total": td.safe_float(t.get("fee")) + td.safe_float(t.get("holiday_price"))}
                     for t in statement["trips"]]
        self._fill_partner_tree(self.driver_trips_tree, trip_rows,
                                ("date", "code", "car_no", "customer", "driver_type",
                                 "revenue", "holiday", "total"))
        self._fill_partner_tree(
            self.driver_pay_tree,
            [row for row in td.load_driver_payments()
             if str(row.get("driver", "")).strip() == driver],
            self.driver_pay_tree["columns"])

    def print_external_drivers_statements(self):
        """طباعة كشف حساب + رحلات كل السائقين الخارجيين في ملف واحد.

        السائقون الخارجيون يُستعاقَلون من جهات خارجية لتوصيل رحلات متفرقة، فالمطلوب
        تقرير واحد يبيّن لكل سائق: كم رحلة أوصل، ما قيمتها، وما حركات حسابه
        ورصيده. كان متاحاً كشف سائق واحد فقط فكان العمل يتكرر يدوياً.
        """
        date_from = self.driver_acc_from_var.get().strip()
        date_to = self.driver_acc_to_var.get().strip()
        drivers = [row.get("name", "").strip() for row in td.load_drivers()
                   if str(row.get("driver_type", "")).strip() == "خارجي"
                   and str(row.get("name", "")).strip()]
        drivers.sort()
        if not drivers:
            messagebox.showinfo(
                "لا يوجد سائقون خارجيون",
                "لا يوجد سائقون مسجّلون بنوع «خارجي» لطباعة كشوفهم.",
                parent=self.partners_notebook)
            return

        summary_rows, sections, active, total_trips = [], [], 0, 0
        for name in drivers:
            statement = td.driver_statement(name, date_from, date_to, "خارجي")
            trips = statement["trips"]
            trip_total = sum(td.safe_float(t.get("fee")) + td.safe_float(t.get("holiday_price"))
                             for t in trips)
            trip_wages = sum(td.safe_float(t.get("driver_wage")) for t in trips)
            paid = sum(td.safe_float(m["debit"]) for m in statement["movements"]
                       if m["kind"] == "payment" and not m.get("voided"))
            total_trips += len(trips)
            if trips or statement["movements"]:
                active += 1
            summary_rows.append(
                "<tr>"
                f"<td>{html.escape(name)}</td>"
                f"<td class='c'>{len(trips)}</td>"
                f"<td class='c'>{trip_total:.3f}</td>"
                f"<td class='c'>{trip_wages:.3f}</td>"
                f"<td class='c'>{paid:.3f}</td>"
                f"<td class='c'>{statement['balance']:.3f}</td>"
                "</tr>")
            if trips or statement["movements"]:
                sections.append(self._external_driver_section(name, statement, trips,
                                                              trip_total))
        if not sections:
            messagebox.showinfo(
                "لا توجد حركات",
                "لا توجد رحلات أو حركات مسجلة للسائقين الخارجيين في الفترة المحددة.",
                parent=self.partners_notebook)
            return
        summary = (
            "<h2>ملخّص السائقين الخارجيين</h2><table><thead><tr><th>السائق</th>"
            "<th>عدد الرحلات</th><th>إجمالي الرحلات (د.ك)</th><th>أجرة السائق (د.ك)</th>"
            "<th>المدفوع (د.ك)</th><th>الرصيد (د.ك)</th></tr></thead><tbody>"
            + "".join(summary_rows) + "</tbody></table>")
        body = (f"<p class='intro'>عدد السائقين الخارجيين: {len(drivers)} · "
                f"لهم حركات في الفترة: {active} · إجمالي الرحلات: {total_trips}</p>"
                + summary + "".join(sections))
        _open_print_report(
            "كشوف حساب السائقين الخارجيين",
            f"الفترة: {date_from or 'البداية'} — {date_to or 'اليوم'} — "
            f"تاريخ الطباعة: {date.today().isoformat()}",
            body, f"external_drivers_statements_{date.today().isoformat()}.html",
            footer=True)

    def _external_driver_section(self, name, statement, trips, trip_total):
        """قسم HTML لسائق خارجي واحد: الرحلات التي أوصلها + حركات حسابه."""
        trip_rows = "".join(
            "<tr>"
            f"<td class='c'>{html.escape(safe_str(t.get('date')))}</td>"
            f"<td class='c'>{html.escape(safe_str(t.get('declaration_trip_no')))}</td>"
            f"<td class='c'>{html.escape(safe_str(t.get('car_no')) or '—')}</td>"
            f"<td>{html.escape(safe_str(t.get('customer')))}</td>"
            f"<td>{html.escape(safe_str(t.get('company')))}</td>"
            f"<td class='c'>{td.safe_float(t.get('fee')):.3f}</td>"
            f"<td class='c'>{td.safe_float(t.get('holiday_price')):.3f}</td>"
            f"<td class='c'>{td.safe_float(t.get('driver_wage')):.3f}</td>"
            "</tr>" for t in trips)
        trips_table = (
            "<table><thead><tr><th>التاريخ</th><th>كود الرحلة</th><th>السيارة</th>"
            "<th>العميل</th><th>الشركة</th><th>السعر</th><th>العطلة</th>"
            f"<th>أجرة السائق</th></tr></thead><tbody>{trip_rows}</tbody><tfoot>"
            f"<tr><td colspan='5'>إجمالي رحلات ({len(trips)})</td>"
            f"<td colspan='3' class='c'>{trip_total:.3f}</td></tr></tfoot></table>"
            if trips else
            "<p class='intro'>لا توجد رحلات مسجّلة لهذا السائق في الفترة المحددة.</p>")
        movement_rows = "".join(
            "<tr>"
            f"<td class='c'>{html.escape(item['date'])}</td>"
            f"<td>{html.escape(item['label'])}</td>"
            f"<td class='c'>{html.escape(item['car_no'] or '—')}</td>"
            f"<td class='c'>{item['debit']:.3f}</td>"
            f"<td class='c'>{item['credit']:.3f}</td>"
            f"<td class='c'>{item['balance']:.3f}</td>"
            f"<td>{html.escape(item['notes'])}</td>"
            "</tr>" for item in statement["movements"])
        account_table = (
            "<h3>حركات الحساب</h3><table><thead><tr><th>التاريخ</th><th>البيان</th>"
            "<th>السيارة</th><th>مدين</th><th>دائن</th><th>الرصيد</th>"
            f"<th>ملاحظات</th></tr></thead><tbody>{movement_rows}</tbody><tfoot>"
            f"<tr><td colspan='3'>الرصيد لصالح السائق</td>"
            f"<td colspan='4' class='c'>{statement['balance']:.3f}</td>"
            "</tr></tfoot></table>" if statement["movements"] else
            "<p class='intro'>لا توجد حركات على الحساب في الفترة المحددة.</p>")
        return (f"<h2 class='driver'>{html.escape(name)}"
                f"<span class='badge'>{len(trips)} رحلة · "
                f"رصيد {statement['balance']:.3f} د.ك</span></h2>"
                "<h3>الرحلات التي أوصلها</h3>" + trips_table + account_table)

    def print_driver_statement(self):
        """طباعة كشف حساب السائق مع حركاته عن الفترة المحددة."""
        driver = self.driver_acc_driver_var.get().strip()
        if not driver:
            messagebox.showinfo("تنبيه", "الرجاء اختيار السائق أولاً.", parent=self.partners_notebook)
            return
        statement = getattr(self, "_driver_statement_cache", None) or self._current_driver_statement()
        date_from = self.driver_acc_from_var.get().strip()
        date_to = self.driver_acc_to_var.get().strip()
        rows = "".join(
            "<tr>"
            f"<td class='c'>{html.escape(item['date'])}</td>"
            f"<td>{html.escape(item['label'])}</td>"
            f"<td class='c'>{html.escape(item['car_no'] or '—')}</td>"
            f"<td class='c'>{item['debit']:.3f}</td>"
            f"<td class='c'>{item['credit']:.3f}</td>"
            f"<td class='c'>{item['balance']:.3f}</td>"
            f"<td>{html.escape(item['notes'])}</td>"
            "</tr>" for item in statement["movements"])
        body = ("<h2>حركات الحساب</h2><table><thead><tr><th>التاريخ</th><th>البيان</th><th>السيارة</th>"
                "<th>مدين</th><th>دائن</th><th>الرصيد</th><th>ملاحظات</th></tr></thead><tbody>"
                f"{rows}</tbody><tfoot><tr><td colspan='3'>الرصيد لصالح السائق</td>"
                f"<td colspan='4' class='c'>{statement['balance']:.3f}</td></tr></tfoot></table>")
        _open_print_report(
            f"كشف حساب السائق — {driver}",
            f"نوع السائق: {statement['driver_type'] or 'غير محدد'} — "
            f"الفترة: {date_from or 'البداية'} — {date_to or 'اليوم'} — "
            f"تاريخ الطباعة: {date.today().isoformat()}",
            body, f"driver_statement_{date.today().isoformat()}.html")

    def print_driver_trips(self):
        """طباعة كافة تفاصيل رحلات السائق (مفيد للسائقين الخارجيين)."""
        driver = self.driver_acc_driver_var.get().strip()
        if not driver:
            messagebox.showinfo("تنبيه", "الرجاء اختيار السائق أولاً.", parent=self.partners_notebook)
            return
        statement = self._current_driver_statement()
        if not statement["trips"]:
            messagebox.showinfo("لا توجد بيانات", "لا توجد رحلات مسجلة لهذا السائق في الفترة المحددة.",
                                parent=self.partners_notebook)
            return
        rows = "".join(
            "<tr>"
            f"<td class='c'>{html.escape(safe_str(trip.get('date')))}</td>"
            f"<td class='c'>{html.escape(safe_str(trip.get('declaration_trip_no')))}</td>"
            f"<td class='c'>{html.escape(safe_str(trip.get('car_no')))}</td>"
            f"<td>{html.escape(safe_str(trip.get('customer')))}</td>"
            f"<td class='c'>{html.escape(statement['driver_type'])}</td>"
            f"<td class='c'>{td.safe_float(trip.get('fee')):.3f}</td>"
            f"<td class='c'>{td.safe_float(trip.get('holiday_price')):.3f}</td>"
            f"<td class='c'>{td.safe_float(trip.get('fee')) + td.safe_float(trip.get('holiday_price')):.3f}</td>"
            "</tr>" for trip in statement["trips"])
        total = sum(td.safe_float(t.get("fee")) + td.safe_float(t.get("holiday_price"))
                    for t in statement["trips"])
        body = ("<h2>كافة تفاصيل الرحلات</h2><table><thead><tr><th>التاريخ</th><th>كود الرحلة</th>"
                "<th>السيارة</th><th>العميل</th><th>نوع السائق</th><th>السعر</th><th>العطلة</th>"
                f"<th>الإجمالي</th></tr></thead><tbody>{rows}</tbody>"
                f"<tfoot><tr><td colspan='7'>إجمالي الرحلات ({len(statement['trips'])})</td>"
                f"<td class='c'>{total:.3f}</td></tr></tfoot></table>")
        _open_print_report(
            f"تفاصيل رحلات السائق — {driver}",
            f"نوع السائق: {statement['driver_type'] or 'غير محدد'} — "
            f"الفترة: {statement['date_from'] or 'البداية'} — {statement['date_to'] or 'اليوم'}",
            body, f"driver_trips_{date.today().isoformat()}.html",
            doc_no=td.next_statement_number("DT"))

    def _build_partner_share_matrix_tab(self, parent):
        """تاب مصفوفة النسب: يعرض توزيع ملكية كل سيارة وحالة اكتماله وتثبيته."""
        hint_card = card_frame(parent, "مصفوفة نسب الشركاء لكل سيارة")
        hint_card.pack(fill="x", padx=18, pady=(18, 8))
        hint_row = tk.Frame(hint_card.body, bg=COLOR_CARD)
        hint_row.pack(fill="x", padx=18, pady=(0, 12))
        self.partner_matrix_car_var = tk.StringVar(value="الكل")
        tk.Label(hint_row, text="السيارة", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        self.partner_matrix_car_combo = ttk.Combobox(
            hint_row, textvariable=self.partner_matrix_car_var, state="readonly",
            width=16, font=F_BODY, justify="right")
        self.partner_matrix_car_combo.pack(side="right", padx=3)
        self.partner_matrix_car_combo.bind("<<ComboboxSelected>>",
                                           lambda _e: self.refresh_partner_share_matrix())
        make_btn(hint_row, "تحديث", self.refresh_partner_share_matrix, variant="accent").pack(side="right", padx=4)
        make_btn(hint_row, "تثبيت النسبة المحددة", self.lock_selected_partner_share,
                 variant="secondary").pack(side="right", padx=4)
        make_btn(hint_row, "إلغاء التثبيت", self.unlock_selected_partner_share,
                 variant="secondary").pack(side="right", padx=4)
        make_btn(hint_row, "طباعة المصفوفة", self.print_partner_share_matrix,
                 variant="accent").pack(side="right", padx=4)
        tk.Label(hint_row,
                 text="التثبيت يمنع تعديل النسبة بعد اعتماد كشوف حساب الشريك، ويمكن إلغاؤه متى شئت.",
                 font=(FONT_NAME, 8), bg=COLOR_CARD, fg=COLOR_MUTED,
                 anchor="e").pack(side="right", padx=8)

        table_card = card_frame(parent, "توزيع النسب")
        table_card.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.partner_matrix_tree = self._make_partner_tree(
            table_card.body,
            ("car_no", "partner", "pct", "locked", "start_date", "end_date",
             "total_pct", "status"),
            {"car_no": "السيارة", "partner": "الشريك", "pct": "النسبة %", "locked": "مثبّتة",
             "start_date": "من تاريخ", "end_date": "إلى تاريخ", "total_pct": "مجموع السيارة %",
             "status": "حالة التوزيع"})
        self.partner_matrix_tree.bind("<Double-1>", lambda _e: self._open_partner_share_from_matrix())
        self.partner_matrix_summary_var = tk.StringVar(value="")
        tk.Label(table_card.body, textvariable=self.partner_matrix_summary_var,
                 font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED,
                 anchor="e").pack(fill="x", padx=18, pady=(0, 14))

    def _selected_partner_share(self):
        selected = self.partner_matrix_tree.selection()
        if not selected:
            messagebox.showinfo("تنبيه", "الرجاء اختيار صف من المصفوفة أولاً.",
                                parent=self.partners_notebook)
            return None
        return next((row for row in getattr(self, "_partner_matrix_cache", [])
                     if row.get("iid") == selected[0]), None)

    def _open_partner_share_from_matrix(self):
        """ينقل المستخدم إلى سجل الشراكة نفسه في شاشة البيانات الأساسية."""
        row = self._selected_partner_share()
        if not row:
            return
        self.show_page("entities")
        notebook = getattr(self, "entities_notebook", None)
        tab_frame = getattr(self, "entities_partners_frame", None)
        if notebook is not None and tab_frame is not None:
            try:
                notebook.select(tab_frame)
            except tk.TclError as _log_exc: log_exception("_open_partner_share_from_matrix", _log_exc)
        self.vehicle_partners_tab.load_selected_into_form(row.get("raw", {}))

    def lock_selected_partner_share(self):
        row = self._selected_partner_share()
        if not row:
            return
        try:
            td.set_partner_share_lock(row["id"], True)
        except Exception as exc:
            messagebox.showerror("تثبيت النسبة", str(exc), parent=self.partners_notebook)
            return
        self.refresh_partner_share_matrix()
        refresh_related_screens(self)

    def unlock_selected_partner_share(self):
        row = self._selected_partner_share()
        if not row:
            return
        try:
            td.set_partner_share_lock(row["id"], False)
        except Exception as exc:
            messagebox.showerror("إلغاء التثبيت", str(exc), parent=self.partners_notebook)
            return
        self.refresh_partner_share_matrix()
        refresh_related_screens(self)

    def refresh_partner_share_matrix(self):
        if not hasattr(self, "partner_matrix_tree"):
            return
        # نحتفظ بالصف المحدد حتى يستطيع المستخدم التثبيت ثم الإلغاء بالتتابع.
        previous = (self.partner_matrix_tree.selection() or [None])[0]
        cars = ["الكل"] + sorted({str(row.get("car_no", "")).strip()
                                  for row in td.load_vehicle_partners()
                                  if str(row.get("car_no", "")).strip()})
        set_combo_values(self.partner_matrix_car_combo, cars)
        if self.partner_matrix_car_var.get().strip() not in cars:
            self.partner_matrix_car_var.set("الكل")
        target = self.partner_matrix_car_var.get().strip()
        matrix = td.partner_share_matrix("" if target == "الكل" else target)
        raw_by_id = {str(row.get("id")): row for row in td.load_vehicle_partners()}
        for item in self.partner_matrix_tree.get_children():
            self.partner_matrix_tree.delete(item)
        flat = []
        for group in matrix:
            for share in group["partners"]:
                flat.append({
                    "iid": f"{group['car_no']}::{share['id']}",
                    "id": share["id"],
                    "car_no": group["car_no"],
                    "partner": share["partner"],
                    "pct": f"{share['ownership_pct']:.3f}",
                    "locked": "نعم" if share["locked"] else "لا",
                    "start_date": share["start_date"],
                    "end_date": share["end_date"] or "مفتوحة",
                    "total_pct": f"{group['total_pct']:.3f}",
                    # نقص التوزيع يعني أن الشراكة لا تغطي كامل السيارة.
                    "status": "مكتمل 100%" if group["complete"]
                    else f"ناقص ({100 - group['total_pct']:.3f}%)",
                    "raw": raw_by_id.get(share["id"], {}),
                })
        self._partner_matrix_cache = flat
        # نملأ بنفس ترتيب رؤوس الجدول تماماً حتى لا تنزاح القيم.
        self._fill_partner_tree(self.partner_matrix_tree, flat, iid_key="iid")
        if previous and self.partner_matrix_tree.exists(previous):
            self.partner_matrix_tree.selection_set(previous)
        incomplete = sum(1 for group in matrix if not group["complete"])
        self.partner_matrix_summary_var.set(
            f"عدد السيارات: {len(matrix)} | شراكات: {len(flat)} | توزيع ناقص: {incomplete}")

    def print_partner_share_matrix(self):
        rows = getattr(self, "_partner_matrix_cache", [])
        if not rows:
            messagebox.showinfo("لا توجد بيانات", "لا توجد نسب شركاء مسجلة.",
                                parent=self.partners_notebook)
            return
        body = ("<h2>مصفوفة نسب الشركاء</h2><table><thead><tr><th>السيارة</th><th>الشريك</th>"
                "<th>النسبة %</th><th>مثبّتة</th><th>من تاريخ</th><th>إلى تاريخ</th>"
                "<th>مجموع السيارة %</th><th>الحالة</th></tr></thead><tbody>"
                + "".join(
                    "<tr>"
                    f"<td class='c'>{html.escape(row['car_no'])}</td>"
                    f"<td>{html.escape(row['partner'])}</td>"
                    f"<td class='c'>{html.escape(row['pct'])}</td>"
                    f"<td class='c'>{html.escape(row['locked'])}</td>"
                    f"<td class='c'>{html.escape(row['start_date'])}</td>"
                    f"<td class='c'>{html.escape(row['end_date'])}</td>"
                    f"<td class='c'>{html.escape(row['total_pct'])}</td>"
                    f"<td class='c'>{html.escape(row['status'])}</td>"
                    "</tr>" for row in rows)
                + "</tbody></table>")
        _open_print_report("مصفوفة نسب الشركاء",
                           f"تاريخ الطباعة: {date.today().isoformat()}",
                           body, f"partner_matrix_{date.today().isoformat()}.html",
                           doc_no=td.next_statement_number("PM"))

    def _build_partners_tab(self):
        """شاشة الشركاء: تفاصيل سيارات الشركاء + دفعاتهم + كشوف حسابات السائقين."""
        frame, content = scrollable_pane(self.pages_area)
        self.partners_notebook = ttk.Notebook(content)
        self.partners_notebook.pack(fill="both", expand=True, padx=12, pady=12)

        # تاب 1: تفاصيل سيارات الشركاء
        vehicle_details_frame = tk.Frame(self.partners_notebook, bg=COLOR_BG)
        self.partners_notebook.add(vehicle_details_frame, text="تفاصيل السيارات")
        self._build_partner_vehicle_details_tab(vehicle_details_frame)

        # تاب 2: دفعات الشركاء
        payments_frame = tk.Frame(self.partners_notebook, bg=COLOR_BG)
        self.partners_notebook.add(payments_frame, text="دفعات الشركاء")
        self._build_partner_payments_tab(payments_frame)

        # تاب 3: كشوف حسابات السائقين (داخلي وخارجي)
        driver_frame = tk.Frame(self.partners_notebook, bg=COLOR_BG)
        self.partners_notebook.add(driver_frame, text="كشوف حسابات السائقين")
        self._build_driver_accounts_tab(driver_frame)

        # تاب 4: مصفوفة نسب الشركاء وتثبيتها
        matrix_frame = tk.Frame(self.partners_notebook, bg=COLOR_BG)
        self.partners_notebook.add(matrix_frame, text="مصفوفة نسب الشركاء")
        self._build_partner_share_matrix_tab(matrix_frame)

        self.register_page("partners", frame, refreshers=[
            self.refresh_partner_vehicle_details,
            self.refresh_partner_payments,
            self.refresh_driver_accounts,
            self.refresh_partner_share_matrix,
        ], canvas=frame.canvas)
