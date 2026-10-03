# -*- coding: utf-8 -*-
"""شاشات إيراد السيارات ويومية السيارات."""

import html, os, tempfile, webbrowser
from datetime import date
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk
from . import data as td
from .app_config import COLOR_BG, COLOR_CARD, COLOR_DANGER, COLOR_MUTED, COLOR_PRIMARY, COLOR_SUCCESS, F_BODY, F_BOLD, F_LABEL
from .ui_pages_expenses import DailyExpenseTab
from .print_letterhead import LETTERHEAD_PRINT_STYLE
from .print_invoice import _REFERENCE_INVOICE_STYLE
from .print_theme import apply_a4_print_layout
from .ui_widgets import apply_table_style, card_frame, make_btn
from .ui_dialogs import date_input
from .ui_helpers import log_exception, safe_str


REVENUE_COLUMNS = [
    ("car_no", "رقم السيارة", 95),
    ("driver_type", "نوع السائق", 85),
    ("driver", "السائق", 120),
    ("trips_count", "الرحلات", 70),
    ("trip_revenue", "إيراد الرحلات", 110),
    ("holiday_revenue", "إيراد العطل", 100),
    ("income_total", "إجمالي الإيراد", 115),
    ("car_expenses", "مصاريف السيارة", 110),
    ("driver_wages", "راتب السائق", 100),
    ("operating_expenses", "إجمالي المصاريف", 115),
    ("net_revenue", "صافي الإيراد", 115),
    ("setup_total", "مصاريف التجهيز", 110),
    ("state", "الحالة", 80),
]

REVENUE_STATE_LABELS = {"دائن": "دائن", "مدين": "مدين", "متعادل": "متعادل"}

class VehicleRevenuePage:
    """شاشة واحدة تجمع ملخص الإيراد والمصاريف لكل سيارة مع تفاصيلها الكاملة.

    كانت الشاشتان منفصلتين («إيراد السيارات» و«ملخص الإيراد والمصاريف») وكلتاهما
    تعرض الأرقام نفسها، فتكرر الحساب على المستخدم. صارت شاشة واحدة تعرض لكل
    سيارة، داخلية كانت أو خارجية:

    - الجدول العلوي: إيراد الرحلات والعطل، مصاريف السيارة، راتب السائق، الصافي
      (= الإيراد − مصاريف السيارة − راتب السائق) وحالة الرصيد.
    - التبويبات السفلية: تفاصيل الرحلات، ومصاريف السيارة، ومصاريف السائق والسلف،
      ومصاريف التجهيز — كلها للسيارة المختارة.
    - زرا طباعة: كشف كامل لكل السيارات، وكشف للسيارة المختارة وحدها.
    """

    DETAIL_TABS = [
        ("trips", "الرحلات",
         ("date", "reference", "customer", "revenue", "holiday", "total"),
         {"date": "التاريخ", "reference": "كود الرحلة", "customer": "العميل",
          "revenue": "السعر", "holiday": "العطلة", "total": "الإجمالي"}),
        ("car", "مصاريف السيارة", ("date", "category", "source", "amount"),
         {"date": "التاريخ", "category": "البند", "source": "المصدر", "amount": "المبلغ"}),
        ("driver", "مصاريف السائق والسلف", ("date", "category", "source", "amount"),
         {"date": "التاريخ", "category": "البند", "source": "المصدر", "amount": "المبلغ"}),
        ("setup", "مصاريف التجهيز", ("date", "category", "amount"),
         {"date": "التاريخ", "category": "البند", "amount": "المبلغ"}),
    ]

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=COLOR_BG)
        self.rows = []
        self.selected = None
        self._build_filters(parent)
        self._build_tables(parent)

    def _build_filters(self, parent):
        filter_card = card_frame(self.frame, "فترة احتساب الإيراد")
        filter_card.pack(fill="x", padx=18, pady=(18, 8))
        filters = tk.Frame(filter_card.body, bg=COLOR_CARD)
        filters.pack(fill="x", padx=18, pady=(0, 14))
        self.date_from = tk.StringVar(value=date.today().replace(day=1).isoformat())
        self.date_to = tk.StringVar(value=date.today().isoformat())
        tk.Label(filters, text="من", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(8, 3))
        date_input(filters, self.date_from, width=10).pack(side="right", padx=3)
        tk.Label(filters, text="إلى", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(8, 3))
        date_input(filters, self.date_to, width=10).pack(side="right", padx=3)
        tk.Label(filters, text="السيارة", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(14, 3))
        self.car_filter = tk.StringVar(value="الكل")
        self.car_combo = ttk.Combobox(filters, textvariable=self.car_filter,
                                      state="readonly", width=15, font=F_BODY,
                                      justify="right")
        self.car_combo.pack(side="right", padx=3)
        self.car_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        tk.Label(filters, text="نوع السائق", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(14, 3))
        self.type_filter = tk.StringVar(value="الكل")
        self.type_combo = ttk.Combobox(
            filters, textvariable=self.type_filter, state="readonly", width=11,
            font=F_BODY, justify="right", values=["الكل"] + list(td.DRIVER_TYPES))
        self.type_combo.pack(side="right", padx=3)
        self.type_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        make_btn(filters, "تحديث", self.refresh, variant="accent",
                 padx=9, pady=4).pack(side="right", padx=(14, 3))
        make_btn(filters, "🖨 طباعة الكشف الكامل", self.print_full_report,
                 variant="secondary", padx=9, pady=4).pack(side="right", padx=3)
        make_btn(filters, "🖨 طباعة السيارة المختارة", self.print_selected_car,
                 variant="secondary", padx=9, pady=4).pack(side="right", padx=3)
        self.totals_var = tk.StringVar(value="")
        tk.Label(filter_card.body, textvariable=self.totals_var, font=F_BOLD,
                 bg=COLOR_CARD, fg=COLOR_PRIMARY, anchor="e",
                 justify="right").pack(fill="x", padx=18, pady=(0, 14))

    def _build_tables(self, parent):
        table_card = card_frame(self.frame, "صافي إيراد كل سيارة")
        table_card.pack(fill="both", expand=True, padx=18, pady=8)
        # جداول Tk ترسم أول عمود على اليسار، فنمرّر الحقول معكوسة كما تفعل
        # بقية شاشات البرنامج، فيظهر عمود «رقم السيارة» في أقصى اليمين.
        self.columns = list(REVENUE_COLUMNS)
        columns = tuple(key for key, _l, _w in reversed(self.columns))
        self.tree = ttk.Treeview(table_card.body, columns=columns,
                                 show="headings", selectmode="browse")
        for key, label, width in self.columns:
            self.tree.heading(key, text=label)
            self.tree.column(key, anchor="center", width=width, stretch=True)
        self.tree.pack(fill="both", expand=True, padx=18, pady=14)
        apply_table_style(self.tree)
        self.tree.tag_configure("credit", foreground=COLOR_SUCCESS)
        self.tree.tag_configure("debit", foreground=COLOR_DANGER)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        detail_card = card_frame(self.frame, "تفاصيل السيارة المختارة")
        detail_card.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.detail_title = tk.StringVar(
            value="اختر سيارة من الجدول لعرض تفاصيلها.")
        tk.Label(detail_card.body, textvariable=self.detail_title, font=F_BOLD,
                 bg=COLOR_CARD, fg=COLOR_PRIMARY, anchor="e").pack(
            fill="x", padx=18, pady=(8, 4))
        book = ttk.Notebook(detail_card.body)
        book.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.detail_trees = {}
        for key, title, columns, headers in self.DETAIL_TABS:
            page = tk.Frame(book, bg=COLOR_CARD)
            book.add(page, text=title)
            # نفس قاعدة الجدول الرئيسي: الأعمدة معكوسة لتُقرأ من اليمين.
            tree = ttk.Treeview(page, columns=tuple(reversed(columns)),
                               show="headings", height=8)
            for column in columns:
                tree.heading(column, text=headers[column])
                tree.column(column, anchor="e" if column in ("category", "customer")
                            else "center", width=130, stretch=True)
            tree.pack(fill="both", expand=True, padx=8, pady=8)
            apply_table_style(tree)
            self.detail_trees[key] = (tree, columns)

    def _state_of(self, net):
        return td.salary_balance_state(net)

    def refresh(self):
        cars = ["الكل"] + sorted({str(v.get("car_no", "")).strip()
                                  for v in td.load_vehicles() if v.get("car_no")})
        self.car_combo.config(values=cars)
        if self.car_filter.get().strip() not in cars:
            self.car_filter.set("الكل")
        wanted_car = self.car_filter.get().strip()
        wanted_type = self.type_filter.get().strip()
        try:
            # المصدر الموحّد: يجمع ملخص الإيراد والمصاريف وتفاصيلهما معاً في
            # مرور واحد على الجداول، فلا تُحسب الأرقام مرتين ولا تختلف.
            self.rows = td.vehicle_financial_details(
                self.date_from.get().strip() or None,
                self.date_to.get().strip() or None,
                "" if wanted_car == "الكل" else wanted_car,
                "" if wanted_type == "الكل" else wanted_type)
        except Exception as exc:
            log_exception("حساب إيراد السيارات", exc)
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        for index, row in enumerate(self.rows):
            state = self._state_of(row["net_revenue"])
            record = {
                "car_no": row["car_no"],
                "driver_type": row.get("driver_type") or "—",
                "driver": row.get("driver") or "—",
                "trips_count": row["trips_count"],
                "trip_revenue": f"{row['revenue']:.3f}",
                "holiday_revenue": f"{row['holiday']:.3f}",
                "income_total": f"{row['income_total']:.3f}",
                "car_expenses": f"{row['car_expenses']:.3f}",
                "driver_wages": f"{row['driver_wages']:.3f}",
                "operating_expenses": f"{row['operating_expenses']:.3f}",
                "net_revenue": f"{row['net_revenue']:.3f}",
                "setup_total": f"{row['setup_total']:.3f}",
                "state": REVENUE_STATE_LABELS.get(state, state),
            }
            # القيم بنفس ترتيب الأعمدة المعكوس، وإلا قُرئ كل صف مقلوباً.
            self.tree.insert(
                "", "end", iid=row["car_no"] or f"row{index}",
                values=tuple(record[key]
                             for key, _l, _w in reversed(self.columns)),
                tags=("credit",) if state == "دائن" else
                     (("debit",) if state == "مدين" else ()))
        self.totals_var.set(self._totals_text())
        if self.selected and self.tree.exists(self.selected):
            self._show_detail(self.selected)
        else:
            self._clear_details()

    def _totals_text(self):
        def total(key):
            return round(sum(r.get(key, 0) for r in self.rows), 3)
        net = total("net_revenue")
        parts = [
            f"عدد السيارات: {len(self.rows)}",
            f"الرحلات: {total('trips_count')}",
            f"إيراد الرحلات: {total('revenue'):.3f} د.ك",
            f"إيراد العطل: {total('holiday'):.3f} د.ك",
            f"إجمالي الإيراد: {total('income_total'):.3f} د.ك",
            f"مصاريف السيارات: {total('car_expenses'):.3f} د.ك",
            f"أجرة السائقين: {total('driver_wages'):.3f} د.ك",
            f"إجمالي المصاريف: {total('operating_expenses'):.3f} د.ك",
            f"صافي الإيراد: {net:.3f} د.ك ({self._state_of(net)})",
            f"مصاريف التجهيز: {total('setup_total'):.3f} د.ك",
        ]
        dups = sum(r.get("duplicates", 0) for r in self.rows)
        if dups:
            parts.append(f"رحلات مكررة مستبعدة: {dups}")
        return "    |    ".join(parts)

    def _clear_details(self):
        for tree, _cols in self.detail_trees.values():
            for item in tree.get_children():
                tree.delete(item)

    def _fill_detail(self, key, records):
        tree, columns = self.detail_trees[key]
        for item in tree.get_children():
            tree.delete(item)
        for record in records:
            values = []
            for column in reversed(columns):
                if column == "amount":
                    values.append(f"{td.safe_float(record.get(column, 0)):.3f}")
                else:
                    values.append(safe_str(record.get(column, "")) or "—")
            tree.insert("", "end", values=tuple(values))

    def _on_select(self, _event=None):
        selection = self.tree.selection()
        if selection:
            self._show_detail(selection[0])

    def _show_detail(self, car_no):
        row = next((r for r in self.rows if r["car_no"] == car_no), None)
        if row is None:
            return
        self.selected = car_no
        self._fill_detail("trips", row.get("revenue_records", []))
        self._fill_detail("car", row.get("car_expense_records", []))
        self._fill_detail("driver", row.get("driver_expense_records", []))
        self._fill_detail("setup", [
            {"date": "", "category": cat, "amount": amount}
            for cat, amount in row.get("setup_items", {}).items()])
        self.detail_title.set(
            f"سيارة {row['car_no']} — {row.get('driver') or 'بلا سائق'}"
            f" ({row.get('driver_type') or 'غير محدد'})"
            f"    |    الرحلات: {row['trips_count']}"
            f"    |    الإيراد: {row['income_total']:.3f}"
            f"    |    المصاريف: {row['operating_expenses']:.3f}"
            f"    |    الصافي: {row['net_revenue']:.3f}"
            f" ({self._state_of(row['net_revenue'])})")
    # ---------------- الطباعة ----------------
    def _report_html(self, rows, title, subtitle):
        """يبني كشفاً واحداً بالجدول الكامل وتفاصيل كل سيارة."""
        head = ("<tr><th>السيارة</th><th>نوع السائق</th><th>السائق</th>"
                "<th>الرحلات</th><th>إيراد الرحلات</th><th>إيراد العطل</th>"
                "<th>إجمالي الإيراد</th><th>مصاريف السيارة</th><th>راتب السائق</th>"
                "<th>إجمالي المصاريف</th><th>صافي الإيراد</th>"
                "<th>مصاريف التجهيز</th><th>الحالة</th></tr>")
        body = "".join(
            "<tr>"
            f"<td>{html.escape(safe_str(r['car_no']))}</td>"
            f"<td>{html.escape(safe_str(r.get('driver_type')) or '—')}</td>"
            f"<td>{html.escape(safe_str(r.get('driver')) or '—')}</td>"
            f"<td>{r['trips_count']}</td>"
            f"<td>{r['revenue']:.3f}</td><td>{r['holiday']:.3f}</td>"
            f"<td>{r['income_total']:.3f}</td>"
            f"<td>{r['car_expenses']:.3f}</td><td>{r['driver_wages']:.3f}</td>"
            f"<td>{r['operating_expenses']:.3f}</td>"
            f"<td>{r['net_revenue']:.3f}</td>"
            f"<td>{r['setup_total']:.3f}</td>"
            f"<td>{self._state_of(r['net_revenue'])}</td></tr>" for r in rows)
        net = round(sum(r["net_revenue"] for r in rows), 3)
        total_row = (
            "<tr class='total-row'>"
            f"<td colspan='3'>الإجمالي ({len(rows)} سيارة)</td>"
            f"<td>{sum(r['trips_count'] for r in rows)}</td>"
            f"<td>{round(sum(r['revenue'] for r in rows), 3):.3f}</td>"
            f"<td>{round(sum(r['holiday'] for r in rows), 3):.3f}</td>"
            f"<td>{round(sum(r['income_total'] for r in rows), 3):.3f}</td>"
            f"<td>{round(sum(r['car_expenses'] for r in rows), 3):.3f}</td>"
            f"<td>{round(sum(r['driver_wages'] for r in rows), 3):.3f}</td>"
            f"<td>{round(sum(r['operating_expenses'] for r in rows), 3):.3f}</td>"
            f"<td>{net:.3f}</td>"
            f"<td>{round(sum(r['setup_total'] for r in rows), 3):.3f}</td>"
            f"<td>{self._state_of(net)}</td></tr>")
        return f"""<!doctype html><html lang='ar' dir='rtl'>
<head><meta charset='utf-8'>
<style>{_REFERENCE_INVOICE_STYLE}{LETTERHEAD_PRINT_STYLE}
.rev{{width:100%;border-collapse:collapse;font-size:10.5px}}
.rev th{{background:#0F2B46;color:#fff;padding:6px;text-align:center}}
.rev td{{border:1px solid #D8E0E9;padding:5px;text-align:center}}
.total-row td{{font-weight:800;background:#FBF6EA}}
.wage-row td{{background:#F2F6FA;font-style:italic}}
h3{{margin-top:20px;font-size:14px;color:#0F2B46}}
</style></head><body>
<h2>{html.escape(title)}</h2>
<p>{html.escape(subtitle)}</p>
<p>الصافي = (إيراد الرحلات + إيراد العطل) − (مصاريف السيارة + راتب السائق)</p>
<table class='rev'>{head}{body}{total_row}</table>
{self._details_section_html(rows)}
</body></html>"""

    def _expense_records_html(self, records, title, empty_text, wages=0.0):
        """جدول مصاريف لجهة واحدة (سيارة أو سائق) مع إجماليه.

        كان الكشف يدمج مصاريف السيارة بمصاريف السائق في جدول واحد، فتفقد
        المصاريف جهتها ويُخطئ القارئ في معرفة أيّهما مخصوم. و«مصاريف السائق»
        تُعرض معها «أجرة السائق من الرحلات» لأنها هي ما يُخصم فعلياً في حساب
        الصافي، بينما بنود المصاريف اليومية 추가ٌ عليها ولا تدخل الصافي.
        """
        total = round(wages + sum(td.safe_float(e.get("amount")) for e in records), 3)
        head = ("<tr><th>التاريخ</th><th>البند</th><th>المصدر</th>"
                "<th>المبلغ</th></tr>")
        body = ""
        if wages:
            body += ("<tr class='wage-row'><td>—</td>"
                     "<td>أجرة السائق</td><td>أجور الرحلات</td>"
                     f"<td>{wages:.3f}</td></tr>")
        body += "".join(
            f"<tr><td>{html.escape(safe_str(e.get('date')))}</td>"
            f"<td>{html.escape(safe_str(e.get('category')))}</td>"
            f"<td>{html.escape(safe_str(e.get('source')))}</td>"
            f"<td>{td.safe_float(e.get('amount')):.3f}</td></tr>"
            for e in records)
        if not body:
            body = f"<tr><td colspan='4'>{html.escape(empty_text)}</td></tr>"
        return (f"<table class='rev'><tr><th colspan='4'>{html.escape(title)}</th></tr>"
                f"{head}{body}"
                f"<tr class='total-row'><td colspan='3'>إجمالي {html.escape(title)}</td>"
                f"<td>{total:.3f}</td></tr></table>")

    def _details_section_html(self, rows):
        """قسم تفاصيل كل سيارة: الرحلات ومصاريف السيارة ومصاريف السائق والتجهيز."""
        blocks = []
        for row in rows:
            trips = "".join(
                f"<tr><td>{html.escape(safe_str(t.get('date')))}</td>"
                f"<td>{html.escape(safe_str(t.get('reference')))}</td>"
                f"<td>{html.escape(safe_str(t.get('customer')))}</td>"
                f"<td>{td.safe_float(t.get('revenue')):.3f}</td>"
                f"<td>{td.safe_float(t.get('holiday')):.3f}</td>"
                f"<td>{td.safe_float(t.get('total')):.3f}</td></tr>"
                for t in row.get("revenue_records", []))
            car_records = row.get("car_expense_records", [])
            driver_records = row.get("driver_expense_records", [])
            wages = td.safe_float(row.get("driver_wages"))
            extra_total = round(sum(td.safe_float(e.get("amount"))
                                    for e in driver_records), 3)
            car_total = round(sum(td.safe_float(e.get("amount")) for e in car_records), 3)
            driver_total = round(wages + extra_total, 3)
            setup = "".join(
                f"<tr><td>{html.escape(safe_str(cat))}</td>"
                f"<td>{amount:.3f}</td></tr>"
                for cat, amount in row.get("setup_items", {}).items())
            blocks.append(
                f"<h3>سيارة {html.escape(safe_str(row['car_no']))} — "
                f"{html.escape(safe_str(row.get('driver')) or 'بلا سائق')}"
                f" ({html.escape(safe_str(row.get('driver_type')) or 'غير محدد')})</h3>"
                f"<p>الرحلات: {row['trips_count']} | الإيراد: "
                f"{row['income_total']:.3f} | المصاريف: "
                f"{row['operating_expenses']:.3f} | الصافي: "
                f"{row['net_revenue']:.3f} ({self._state_of(row['net_revenue'])})</p>"
                f"<p>مصاريف السيارة: {car_total:.3f} | مصاريف السائق: "
                f"{driver_total:.3f} (أجرة {wages:.3f} + بنود "
                f"{extra_total:.3f})</p>"
                "<table class='rev'><tr><th colspan='6'>الرحلات</th></tr>"
                "<tr><th>التاريخ</th><th>كود الرحلة</th><th>العميل</th>"
                "<th>السعر</th><th>العطلة</th><th>الإجمالي</th></tr>"
                f"{trips or '<tr><td colspan=6>لا رحلات</td></tr>'}</table>"
                f"{self._expense_records_html(car_records, 'مصاريف السيارة', 'لا مصاريف سيارة')}"
                f"{self._expense_records_html(driver_records, 'مصاريف السائق', 'لا مصاريف سائق', wages)}"
                "<table class='rev'><tr><th colspan='2'>مصاريف التجهيز</th></tr>"
                "<tr><th>البند</th><th>المبلغ</th></tr>"
                f"{setup or '<tr><td colspan=2>لا تجهيز</td></tr>'}</table>")
        return "".join(blocks)

    def _open_report(self, rows, title, subtitle, filename):
        if not rows:
            messagebox.showinfo("تنبيه", "لا توجد بيانات للطباعة.", parent=self.frame)
            return
        path = os.path.join(tempfile.gettempdir(), filename)
        with open(path, "w", encoding="utf-8") as file:
            file.write(apply_a4_print_layout(
                self._report_html(rows, title, subtitle)))
        webbrowser.open("file:///" + path.replace("\\", "/"))

    def _period_text(self):
        return (f"الفترة: {self.date_from.get().strip() or 'البداية'} "
                f"إلى {self.date_to.get().strip() or 'اليوم'}")

    def print_full_report(self):
        scope = "جميع السيارات"
        if self.car_filter.get().strip() not in ("", "الكل"):
            scope = f"سيارة {self.car_filter.get().strip()}"
        if self.type_filter.get().strip() not in ("", "الكل"):
            scope += f" — سائق {self.type_filter.get().strip()}"
        self._open_report(self.rows, "كشف إيراد ومصاريف السيارات",
                          f"{self._period_text()} — {scope}",
                          "vehicle_revenue_report.html")

    def print_selected_car(self):
        car = self.selected or (self.tree.selection() or [None])[0]
        row = next((r for r in self.rows if r["car_no"] == car), None)
        if row is None:
            messagebox.showinfo("تنبيه", "اختر سيارة من الجدول أولاً.",
                                parent=self.frame)
            return
        self._open_report([row], f"كشف سيارة {row['car_no']}",
                          self._period_text(),
                          f"vehicle_{row['car_no']}_report.html")

class DailyCarsPage:
    """شاشة تضم تبويبي مصاريف السيارات ومصاريف السائقين والسلف."""

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=COLOR_BG)
        notebook = ttk.Notebook(self.frame)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)
        vehicle_frame = tk.Frame(notebook, bg=COLOR_BG)
        driver_frame = tk.Frame(notebook, bg=COLOR_BG)
        notebook.add(vehicle_frame, text="مصاريف السيارات")
        notebook.add(driver_frame, text="مصاريف السائقين والسلف")
        # «نوع السائق» أُضيف لكلا التبويبين: كانا يحويان «السائق» و«السيارة»
        # فقط، فلا كانت هناك قائمة تصفّي السائقين بالنوع ولا تظهر سيارات السائق.
        vehicle_fields = [
            ("id", "الرقم"), ("date", "التاريخ"),
            ("driver_type", "نوع السائق"), ("car_no", "رقم السيارة"),
            ("driver", "السائق"), ("category", "نوع مصروف السيارة"),
            ("amount", "المبلغ (د.ك)"), ("description", "التفاصيل / السبب"),
        ]
        driver_fields = [
            ("id", "الرقم"), ("date", "التاريخ"),
            ("driver_type", "نوع السائق"),
            ("car_no", "رقم السيارة"),
            ("driver", "السائق"),
            ("category", "نوع مصروف السائق"), ("amount", "مبلغ المصروف (د.ك)"),
            ("description", "التفاصيل / السبب"),
        ]
        self.vehicle_tab = DailyExpenseTab(vehicle_frame, "سيارة", "مصاريف السيارات",
                                            vehicle_fields, td.VEHICLE_EXPENSE_CATEGORIES,
                                            td.VEHICLE_EXPENSE_GROUPS,
                                            show_edit_button=False,
                                            show_upload_button=False,
                                            print_mode="combined",
                                            multiselect=True,
                                            single_row_form=True)
        self.driver_tab = DailyExpenseTab(driver_frame, "سائق", "مصاريف السائقين والسلف",
                                           driver_fields, td.DRIVER_EXPENSE_CATEGORIES,
                                           actions_on_own_row=True)
        self.vehicle_tab.frame.pack(fill="both", expand=True)
        self.driver_tab.frame.pack(fill="both", expand=True)
        # زر طباعة الكشف المقسّم: يطبع الجهتين في ورقة واحدة مقسومتين.
        for tab in (self.vehicle_tab, self.driver_tab):
            make_btn(tab.actions_frame, "🖨 طباعة كشف مصاريف مقسّم",
                     tab.print_expenses_split, variant="accent",
                     padx=4, pady=2).pack(side="right", padx=2)

    def print_expenses_report(self):
        """طباعة الكشف المقسّم — متاحة من أي تبويب بلا ازدواج."""
        self.vehicle_tab.print_expenses_split()

    def refresh(self):
        self.vehicle_tab.refresh()
        self.driver_tab.refresh()
