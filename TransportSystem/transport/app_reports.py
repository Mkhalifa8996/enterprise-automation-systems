# -*- coding: utf-8 -*-
"""تبويب التقارير وكل تقاريره."""

import csv, json, os, re, tempfile
from datetime import date
from datetime import datetime
from tkinter import filedialog
from tkinter import messagebox
from datetime import timedelta
import tkinter as tk
from tkinter import ttk
try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False
from . import data as td
from .app_config import CHART_PALETTE, COLOR_ACCENT, COLOR_ACCENT_LIGHT, COLOR_BG, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_CARD, COLOR_DANGER, COLOR_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_SHADOW, COLOR_SUCCESS, COLOR_TEXT, FONT_NAME, F_BODY, F_H2, F_LABEL, REPORT_CATEGORIES, REPORT_SCREENSHOT_DIR
from .ui_widgets import apply_table_style, card_frame, make_btn, scrollable_pane
from .ui_dialogs import date_input
from .print_statement import generate_and_open_summary_print
from .ui_helpers import log_exception, safe_str

class AppReportsMixin:
    """تبويب التقارير وكل تقاريره."""

        # ---------------- شاشة التقارير ----------------
    def _build_reports_tab(self):
        frame, report_content = scrollable_pane(self.pages_area)
        report_canvas = frame.canvas

        hero = tk.Frame(report_content, bg=COLOR_PRIMARY, height=68)
        hero.pack(fill="x", padx=18, pady=(12, 8))
        hero.pack_propagate(False)
        hero_text = tk.Frame(hero, bg=COLOR_PRIMARY)
        hero_text.pack(side="right", fill="both", expand=True, padx=18, pady=8)
        tk.Label(hero_text, text="📊 مركز التقارير والتحليلات", font=(FONT_NAME, 13, "bold"),
                 bg=COLOR_PRIMARY, fg="white", anchor="e").pack(side="right")
        # سطر حي يعرض التقرير المختار والفترة وعدد السجلات
        self.report_meta_label = tk.Label(
            hero_text, text="اختر نوع التقرير من القائمة ثم حدد الفترة الزمنية",
            font=F_LABEL, bg=COLOR_PRIMARY, fg="#D8E2F0", anchor="e")
        self.report_meta_label.pack(side="right", fill="x")
        self.report_meta_var = tk.StringVar(value="اختر نوع التقرير من القائمة ثم حدد الفترة الزمنية")
        self.rep_type_var = tk.StringVar(value="")
        self.rep_entity_var = tk.StringVar(value="")
        self.rep_status_var = tk.StringVar(value="")
        self.rep_from = tk.StringVar(value="")
        self.rep_to = tk.StringVar(value="")

        # شريط فئات التقارير: أسماء مختصرة حتى لا تُقتطع، والتصنيف الكامل يظهر في الرأس
        self.rep_category_var = tk.StringVar(value="")
        chips_row = tk.Frame(report_content, bg=COLOR_CARD)
        chips_row.pack(fill="x", padx=18, pady=(0, 6))
        self._report_chips = {}

        def _add_chip(key, label):
            btn = tk.Label(chips_row, text=label, font=F_LABEL, bg=COLOR_CARD,
                           fg=COLOR_MUTED, cursor="hand2", padx=10, pady=5)
            btn.pack(side="right", padx=3)
            btn.bind("<Button-1>", lambda _e, c=key: self._select_report_category(c))
            self._report_chips[key] = btn

        for _cat, _items in REPORT_CATEGORIES:
            _icon = _cat.split()[0]
            _words = [w for w in _cat.split()[1:] if w]
            _short = _words[-1] if _words else _cat
            _add_chip(_cat, f"{_icon}  {_short}")
        _add_chip("", "🗂  الكل")

        # نوع التقرير (في صف مستقل ليأخذ العرض الكامل)
        row = tk.Frame(report_content, bg=COLOR_CARD)
        row.pack(fill="x", padx=18, pady=(8, 4))
        tk.Label(row, text="نوع التقرير", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(0, 4))
        self.rep_type_combo = ttk.Combobox(
            row, textvariable=self.rep_type_var, state="readonly",
            width=32, font=F_BODY,
            values=[name for _cat, items in REPORT_CATEGORIES for name, _icon in items]
        )
        self.rep_type_combo.pack(side="right", padx=(0, 10), fill="x", expand=True)
        make_btn(row, "🔄 تشغيل", self._run_current_report, variant="accent", padx=8, pady=2).pack(side="right", padx=2)

        # صف الفلاتر
        row = tk.Frame(report_content, bg=COLOR_CARD)
        row.pack(fill="x", padx=18, pady=(4, 4))

        # الكيان
        tk.Label(row, text="الكيان", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(0, 4))
        self.rep_entity_combo = ttk.Combobox(row, textvariable=self.rep_entity_var, state="readonly", width=8, font=F_BODY)
        self.rep_entity_combo.pack(side="right", padx=(0, 10))

        # الحالة
        tk.Label(row, text="الحالة", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(0, 4))
        self.rep_status_combo = ttk.Combobox(row, textvariable=self.rep_status_var, state="readonly", width=10, font=F_BODY)
        self.rep_status_combo.pack(side="right", padx=(0, 10))

        # الفترة
        tk.Label(row, text="الفترة", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(0, 4))
        period_labels = {"all": "الكل", "today": "اليوم", "week": "آخر 7 أيام", "month": "هذا الشهر",
                         "last_month": "الشهر الماضي", "year": "هذا العام"}
        self._report_period_labels = period_labels
        self.rep_period_var = tk.StringVar(value="all")
        self.rep_period_combo = ttk.Combobox(
            row, textvariable=self.rep_period_var, state="readonly",
            width=12, font=F_BODY,
            values=list(period_labels.values())
        )
        self.rep_period_combo.pack(side="right", padx=(0, 10))
        def _on_period_selected(*args):
            display = self.rep_period_var.get()
            for key, label in period_labels.items():
                if label == display:
                    self._report_quick_period(key)
                    self._run_current_report()
                    return
        self.rep_period_combo.bind("<<ComboboxSelected>>", _on_period_selected)

        # من - إلى
        tk.Label(row, text="من", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(0, 4))
        date_input(row, self.rep_from, width=9).pack(side="right", padx=(0, 4))
        tk.Label(row, text="إلى", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(0, 4))
        date_input(row, self.rep_to, width=9).pack(side="right", padx=(0, 10))

        # أزرار التصدير في صف مستقل حتى لا تُقتطع
        action_row = tk.Frame(report_content, bg=COLOR_CARD)
        action_row.pack(fill="x", padx=18, pady=(0, 8))
        tk.Label(action_row, text="الإجراءات", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(0, 6))
        make_btn(action_row, "🖨 طباعة", self._print_current_report, variant="secondary", padx=8, pady=2).pack(side="right", padx=2)
        make_btn(action_row, "📤 CSV", self._export_current_report_csv, variant="secondary", padx=8, pady=2).pack(side="right", padx=2)
        make_btn(action_row, "📸 تصوير", self._save_current_report_as_screenshot, variant="secondary", padx=8, pady=2).pack(side="right", padx=2)
        make_btn(action_row, "📂 الحافظة", self._open_screenshot_gallery, variant="secondary", padx=8, pady=2).pack(side="right", padx=2)

        self.rep_type_var.trace_add("write", lambda *a: self._on_report_type_changed())
        self.rep_entity_combo.bind("<<ComboboxSelected>>", lambda *a: self._run_current_report())
        self.rep_status_combo.bind("<<ComboboxSelected>>", lambda *a: self._run_current_report())

        self._report_fields_cache = []
        self._report_rows_cache = []
        self._chart_series_cache = []
        self._donut_cache = []
        self._chart_kind = "bar"

        summary_card = card_frame(report_content, "مؤشرات التقرير")
        summary_card.pack(fill="x", padx=18, pady=(0, 10))
        self.report_kpi_wrap = tk.Frame(summary_card.body, bg=COLOR_CARD)
        self.report_kpi_wrap.pack(fill="x", padx=10, pady=10)
        self._kpi_cards = []

        charts_card = card_frame(report_content, "الرسوم التحليلية للتقرير")
        charts_card.pack(fill="x", padx=18, pady=(0, 10))
        charts_row = tk.Frame(charts_card.body, bg=COLOR_CARD)
        charts_row.pack(fill="x", padx=14, pady=(0, 14))

        main_chart_frame = tk.Frame(charts_row, bg=COLOR_CARD)
        main_chart_frame.pack(side="right", fill="both", expand=True, padx=(0, 8))
        tk.Label(main_chart_frame, text="📈 قيم التقرير", font=F_H2,
                 bg=COLOR_CARD, fg=COLOR_TEXT, anchor="e").pack(fill="x", pady=(0, 6))
        self.report_chart = tk.Canvas(main_chart_frame, height=220, bg=COLOR_CARD,
                                      highlightthickness=1, highlightbackground=COLOR_BORDER)
        self.report_chart.pack(fill="both", expand=True)

        donut_frame = tk.Frame(charts_row, bg=COLOR_CARD)
        donut_frame.pack(side="left", fill="both", padx=(8, 0))
        tk.Label(donut_frame, text="🍩 التوزيع النسبي", font=F_H2,
                 bg=COLOR_CARD, fg=COLOR_TEXT, anchor="e").pack(fill="x", pady=(0, 6))
        self.report_donut = tk.Canvas(donut_frame, width=330, height=220, bg=COLOR_CARD,
                                      highlightthickness=1, highlightbackground=COLOR_BORDER)
        self.report_donut.pack(fill="both", expand=True)

        result_card = card_frame(report_content, "نتيجة التقرير")
        result_card.pack(fill="x", padx=18, pady=(0, 18))
        report_table_wrap = tk.Frame(result_card.body, bg=COLOR_CARD)
        report_table_wrap.pack(fill="both", expand=True, padx=18, pady=18)
        columns = ("col1", "col2", "col3", "col4")
        self.report_tree = ttk.Treeview(report_table_wrap, columns=columns, show="headings", height=16)
        self.report_tree.heading("col1", text="البيان")
        self.report_tree.heading("col2", text="التفاصيل")
        self.report_tree.heading("col3", text="معلومات إضافية")
        self.report_tree.heading("col4", text="المبلغ / القيمة")
        self.report_tree.column("col1", anchor="e", width=180)
        self.report_tree.column("col2", anchor="e", width=260)
        self.report_tree.column("col3", anchor="e", width=220)
        self.report_tree.column("col4", anchor="e", width=120)
        report_tree_scrollbar = ttk.Scrollbar(report_table_wrap, orient="vertical", command=self.report_tree.yview)
        report_tree_hscrollbar = ttk.Scrollbar(report_table_wrap, orient="horizontal", command=self.report_tree.xview)
        self.report_tree.configure(
            yscrollcommand=report_tree_scrollbar.set,
            xscrollcommand=report_tree_hscrollbar.set,
        )
        # الشريط العمودي على اليمين كما في الواجهات العربية.
        report_tree_scrollbar.pack(side="right", fill="y")
        report_tree_hscrollbar.pack(side="bottom", fill="x")
        self.report_tree.pack(fill="both", expand=True)
        apply_table_style(self.report_tree)
        self.report_tree.tag_configure("positive", foreground=COLOR_SUCCESS)
        self.report_tree.tag_configure("negative", foreground=COLOR_DANGER)
        self.report_chart.bind("<Configure>", lambda _event: self._render_report_charts(), add="+")
        self.report_donut.bind("<Configure>", lambda _event: self._render_report_charts(), add="+")

        self.report_text = tk.Text(result_card.body, state="disabled", height=1, width=1)

        self._refresh_report_options()
        self._highlight_report_tiles()
        self.register_page("reports", frame, refreshers=[
            self._refresh_report_options,
            self._run_current_report,
        ], canvas=frame.canvas)

    def _select_report_type(self, name):
        """اختيار تقرير من بطاقات الفئات (يشغّل التحديث تلقائياً عبر التتبع)."""
        self.rep_type_var.set(name)

    def _select_report_category(self, category):
        """تصفية قائمة التقارير حسب الفئة المختارة."""
        self.rep_category_var.set(category)
        self._refresh_report_options()
        self._highlight_report_tiles()
        self._run_current_report()

    def _highlight_report_tiles(self):
        """تمييز الفئة المختارة في شريط الفئات."""
        current = getattr(self, "rep_category_var", tk.StringVar()).get()
        for name, chip in getattr(self, "_report_chips", {}).items():
            active = name == current
            chip.configure(bg=COLOR_PRIMARY if active else COLOR_CARD,
                           fg="white" if active else COLOR_MUTED)

    def _on_report_type_changed(self):
        self._refresh_report_options()
        self._highlight_report_tiles()
        self._run_current_report()

    def _clear_report_filters(self):
        self.rep_entity_var.set("")
        self.rep_status_var.set("")
        self.rep_from.set("")
        self.rep_to.set("")
        self._run_current_report()

    def _report_quick_period(self, choice):
        """ضبط الفترة الزمنية السريعة ثم تشغيل التقرير مباشرة."""
        today = date.today()
        if choice == "today":
            self.rep_from.set(today.isoformat())
            self.rep_to.set(today.isoformat())
        elif choice == "week":
            self.rep_from.set((today - timedelta(days=6)).isoformat())
            self.rep_to.set(today.isoformat())
        elif choice == "month":
            self.rep_from.set(today.replace(day=1).isoformat())
            self.rep_to.set(today.isoformat())
        elif choice == "last_month":
            previous_end = today.replace(day=1) - timedelta(days=1)
            self.rep_from.set(previous_end.replace(day=1).isoformat())
            self.rep_to.set(previous_end.isoformat())
        elif choice == "year":
            self.rep_from.set(today.replace(month=1, day=1).isoformat())
            self.rep_to.set(today.isoformat())
        elif choice == "all":
            self.rep_from.set("")
            self.rep_to.set("")
        self._run_current_report()

    def _refresh_report_options(self):
        report_type = self.rep_type_var.get()
        entity_values = []
        status_values = [""]

        if report_type == "تقرير السائقين":
            entity_values = [""] + sorted({d.get("name", "") for d in td.load_drivers() if d.get("name", "")})
        elif report_type == "تقرير السيارات":
            entity_values = [""] + sorted({v.get("car_no", "") for v in td.load_vehicles() if v.get("car_no", "")})
        elif report_type == "تقرير الرحلات":
            drivers = sorted({t.get("driver", "") for t in td.load_trips() if t.get("driver", "")})
            cars = sorted({v.get("car_no", "") for v in td.load_vehicles() if v.get("car_no", "")})
            customers = sorted({c.get("name", "") for c in td.load_customers() if c.get("name", "")})
            companies = sorted({c.get("name", "") for c in td.load_companies() if c.get("name", "")})
            entity_values = [""] + drivers + cars + customers + companies
            status_values = [""] + sorted({t.get("trip_category", "") for t in td.load_trips() if t.get("trip_category", "")})
        elif report_type == "تقرير المصاريف":
            entity_values = [""] + sorted({v.get("car_no", "") for v in td.load_vehicles() if v.get("car_no", "")})
            entity_values += [d.get("name", "") for d in td.load_drivers() if d.get("name", "") and d.get("name", "") not in entity_values]
            status_values = [""] + sorted({e.get("category", "") for e in td.load_daily_expenses() if e.get("category", "")})
        elif report_type == "تقرير الفواتير":
            entity_values = [""] + sorted({i.get("customer", "") for i in td.load_invoices() if i.get("customer", "")})
            status_values = ["", "نعم", "لا"]
        elif report_type == "تقرير الدفعات":
            entity_values = [""] + sorted({p.get("customer", "") for p in td.load_payments() if p.get("customer", "")})
        elif report_type == "تقرير الخدمات":
            entity_values = [""] + sorted({s.get("customer", "") for s in td.load_services() if s.get("customer", "")})
            status_values = [""] + sorted({s.get("service_type", "") for s in td.load_services() if s.get("service_type", "")})
        elif report_type == "تقرير الصيانة":
            entity_values = [""] + sorted({m.get("car_no", "") for m in td.load_maintenance() if m.get("car_no", "")})
            status_values = [""] + sorted({m.get("type", "") for m in td.load_maintenance() if m.get("type", "")})
        elif report_type == "تقرير الرواتب":
            entity_values = [""] + sorted({s.get("driver", "") for s in td.load_salaries() if s.get("driver", "")})
            status_values = [""] + sorted({s.get("paid", "") for s in td.load_salaries() if s.get("paid", "")})
        elif report_type == "تقرير العملاء":
            entity_values = [""] + sorted({c.get("name", "") for c in td.load_customers() if c.get("name", "")})
        elif report_type == "تقرير الشركات":
            entity_values = [""] + sorted({c.get("name", "") for c in td.load_companies() if c.get("name", "")})
        elif report_type == "تقرير إيراد العطل":
            entity_values = [""] + sorted({t.get("driver", "") for t in td.load_trips() if t.get("driver", "")})
            status_values = [""] + sorted({t.get("car_no", "") for t in td.load_trips() if t.get("car_no", "")})
        elif report_type == "تحليل أداء السائقين":
            entity_values = [""] + sorted({t.get("driver", "") for t in td.load_trips() if t.get("driver", "")})
        elif report_type == "توزيع أرباح الشركاء":
            entity_values = [""] + sorted({v.get("car_no", "") for v in td.load_vehicles() if v.get("car_no", "")})
        elif report_type == "أرباح الشركاء":
            entity_values = [""] + td.partner_names()
            entity_values += [car for car in sorted({v.get("car_no", "")
                                                     for v in td.load_vehicles() if v.get("car_no", "")})
                              if car not in entity_values]
        elif report_type == "دفعات الشركاء":
            entity_values = [""] + td.partner_names()
            status_values = [""] + [t for t in td.PAYMENT_TYPES]
        elif report_type == "دفعات السائقين":
            entity_values = [""] + sorted({d.get("name", "") for d in td.load_drivers()
                                           if d.get("name", "")})
            status_values = [""] + td.PAYMENT_TYPES
        elif report_type == "مصفوفة نسب الشركاء":
            entity_values = [""] + sorted({str(p.get("car_no", "")).strip()
                                           for p in td.load_vehicle_partners()
                                           if str(p.get("car_no", "")).strip()})
        elif report_type == "تقرير النقد والبنك":
            entity_values = [""] + td.CASH_LEDGER_ACCOUNTS
            status_values = [""] + td.CASH_LEDGER_TYPES
        elif report_type == "تقرير الوقود":
            entity_values = [""] + sorted({f.get("car_no", "") for f in td.load_fuel() if f.get("car_no", "")})
            entity_values += sorted({str(f.get("driver", "")).strip() for f in td.load_fuel()
                                     if str(f.get("driver", "")).strip() and str(f.get("driver", "")).strip() not in entity_values})
            status_values = [""] + sorted({f.get("station", "") for f in td.load_fuel() if f.get("station", "")})
        elif report_type == "تقرير العقود":
            entity_values = [""] + sorted({c.get("party", "") for c in td.load_contracts() if c.get("party", "")})
            status_values = ["", "نشط", "منتهي", "معلق"]
        elif report_type == "تقرير عروض الأسعار":
            entity_values = [""] + sorted({q.get("customer", "") for q in td.load_quotations() if q.get("customer", "")})
            status_values = [""] + sorted({q.get("status", "") for q in td.load_quotations() if q.get("status", "")})
        elif report_type == "تقرير قطع الغيار":
            entity_values = [""] + sorted({p.get("car_no", "") for p in td.load_parts() if p.get("car_no", "")})
            status_values = [""] + sorted({p.get("part_type", "") for p in td.load_parts() if p.get("part_type", "")})
        elif report_type == "تقرير خطط الصيانة":
            entity_values = [""] + sorted({p.get("car_no", "") for p in td.load_maintenance_plans() if p.get("car_no", "")})
            status_values = [""] + sorted({p.get("status", "") for p in td.load_maintenance_plans() if p.get("status", "")})
        elif report_type == "أرصدة العملاء":
            entity_values = [""] + sorted({c.get("name", "") for c in td.load_customers() if c.get("name", "")})
            status_values = ["", "مستحق", "مسدد"]
        elif report_type == "أعمار الذمم":
            entity_values = [""] + sorted({c.get("name", "") for c in td.load_customers() if c.get("name", "")})
        elif report_type == "كفاءة السيارات":
            entity_values = [""] + sorted({v.get("car_no", "") for v in td.load_vehicles() if v.get("car_no", "")})
        elif report_type == "سجل العمليات":
            audit_rows = td.load_audit_logs(limit=500)
            entity_values = [""] + sorted({str(log.get("sheet_key", "")).strip() for log in audit_rows
                                           if str(log.get("sheet_key", "")).strip()})
            status_values = [""] + sorted({str(log.get("action", "")).strip() for log in audit_rows
                                           if str(log.get("action", "")).strip()})
        # التقرير المالي / المقارنة المالية / الأرباح الشهرية / التقرير الشامل: بدون كيانات

        # تصفية قائمة أنواع التقارير حسب الفئة المختارة في شريط الفئات
        category = getattr(self, "rep_category_var", None)
        category = category.get() if category is not None else ""
        all_names = [name for _cat, items in REPORT_CATEGORIES for name, _icon in items]
        if category:
            type_values = [name for cat, items in REPORT_CATEGORIES
                           if cat == category for name, _icon in items]
        else:
            type_values = list(all_names)
        current_type = self.rep_type_var.get().strip()
        if current_type and current_type in type_values:
            self.rep_type_var.set(current_type)
        else:
            self.rep_type_var.set(type_values[0] if type_values else "")
        self.rep_type_combo.config(values=type_values)

        self.rep_entity_combo.config(values=entity_values)
        self.rep_status_combo.config(values=status_values)
        current_entity = self.rep_entity_var.get().strip()
        self.rep_entity_var.set(current_entity if current_entity in entity_values else (entity_values[0] if entity_values else ""))
        current_status = self.rep_status_var.get().strip()
        self.rep_status_var.set(current_status if current_status in status_values else (status_values[0] if status_values else ""))

    def _parse_report_period(self):
        d_from = self.rep_from.get().strip() or None
        d_to = self.rep_to.get().strip() or None
        for value, label in ((d_from, "من"), (d_to, "إلى")):
            if value:
                try:
                    date.fromisoformat(value)
                except ValueError:
                    messagebox.showwarning("تنبيه", f"أدخل تاريخ «{label}» بصيغة YYYY-MM-DD.")
                    return None, None
        if d_from and d_to and d_from > d_to:
            messagebox.showwarning("تنبيه", "تاريخ البداية يجب أن يسبق تاريخ النهاية.")
            return None, None
        return d_from, d_to

    def _update_summary(self, count=0, total=0.0, avg=0.0, kpis=None):
        """تحديث بطاقات المؤشرات (KPI) وشريط المعلومات أعلى الشاشة."""
        if kpis is None:
            kpis = [
                ("عدد السجلات", str(count), COLOR_PRIMARY_LIGHT),
                ("الإجمالي", f"{total:,.3f} د.ك" if total else "0 د.ك", COLOR_ACCENT),
                ("المتوسط", f"{avg:,.3f} د.ك" if avg else "0 د.ك", COLOR_PRIMARY),
            ]
        self._set_report_kpis(kpis)
        report_type = self.rep_type_var.get().strip()
        entity = self.rep_entity_var.get().strip()
        start = self.rep_from.get().strip()
        end = self.rep_to.get().strip()
        period = f"{start or 'البداية'} إلى {end or 'اليوم'}"
        self.report_meta_var.set(
            f"{report_type}{f' — {entity}' if entity else ''} | الفترة: {period} | {count} سجل"
        )
        # عرض السطر الحي في رأس صفحة التقارير
        meta_label = getattr(self, "report_meta_label", None)
        if meta_label is not None:
            meta_label.configure(text=self.report_meta_var.get())

    def _set_report_kpis(self, kpis):
        """إعادة رسم بطاقات المؤشرات حسب نتائج التقرير الحالي (حتى 6 بطاقات)."""
        wrap = getattr(self, "report_kpi_wrap", None)
        if wrap is None:
            return
        for card in getattr(self, "_kpi_cards", []):
            card.destroy()
        self._kpi_cards = []
        self._kpi_cache = list(kpis or [])  # حفظ للتصوير
        for label, value, color in (kpis or [])[:6]:
            card = self._kpi_card(wrap, label, value, color)
            card.pack(side="right", fill="both", expand=True, padx=4, pady=2)
            self._kpi_cards.append(card)

    def _kpi_card(self, parent, label, value, color):
        """بطاقة مؤشر صغيرة: شريط ملون + اسم المؤشر + القيمة."""
        outer = tk.Frame(parent, bg=COLOR_SHADOW)
        inner = tk.Frame(outer, bg=COLOR_CARD)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Frame(inner, bg=color, height=3).pack(fill="x")
        tk.Label(inner, text=label, font=(FONT_NAME, 8), bg=COLOR_CARD, fg=COLOR_MUTED,
                 anchor="e").pack(fill="x", padx=10, pady=(7, 0))
        tk.Label(inner, text=value, font=(FONT_NAME, 14, "bold"), bg=COLOR_CARD, fg=color,
                 anchor="e").pack(fill="x", padx=10, pady=(1, 8))
        return outer

    def _run_current_report(self):
        report_type = self.rep_type_var.get()
        entity = self.rep_entity_var.get().strip()
        status = self.rep_status_var.get().strip()
        d_from, d_to = self._parse_report_period()
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        self._report_fields_cache = []
        self._report_rows_cache = []
        self._chart_series_cache = []
        self._donut_cache = []
        self._chart_kind = "bar"

        report_map = {
            "تقرير مالي": self._report_financial,
            "تقرير السائقين": self._report_drivers,
            "تقرير السيارات": self._report_vehicles,
            "تقرير الرحلات": self._report_trips,
            "تقرير المصاريف": self._report_expenses,
            "تقرير الفواتير": self._report_invoices,
            "تقرير الدفعات": self._report_payments,
            "تقرير الخدمات": self._report_services,
            "تقرير الصيانة": self._report_maintenance,
            "تقرير الرواتب": self._report_salaries,
            "تقرير العملاء": self._report_customers,
            "تقرير الشركات": self._report_companies,
            "تقرير إيراد العطل": self._report_holidays,
            "تحليل أداء السائقين": self._report_driver_performance,
            "تقرير شامل": self._report_all,
            "توزيع أرباح الشركاء": self._report_partner_distribution,
            "تقرير النقد والبنك": self._report_cash_ledger,
            "مقارنة مالية": self._report_financial_comparison,
            "تقرير الوقود": self._report_fuel,
            "تقرير العقود": self._report_contracts,
            "تقرير عروض الأسعار": self._report_quotations,
            "تقرير قطع الغيار": self._report_parts,
            "تقرير خطط الصيانة": self._report_maintenance_plans,
            "أرصدة العملاء": self._report_customer_balances,
            "أعمار الذمم": self._report_receivables_aging,
            "الأرباح الشهرية": self._report_monthly_profit,
            "كفاءة السيارات": self._report_vehicle_utilization,
            "أرباح الشركاء": self._report_partner_profit,
            "دفعات الشركاء": self._report_partner_payments,
            "دفعات السائقين": self._report_driver_payments,
            "مصفوفة نسب الشركاء": self._report_partner_matrix,
            "سجل العمليات": self._report_audit_log,
        }
        handler = report_map.get(report_type)
        if handler:
            handler(entity, d_from, d_to, status)
        self._render_report_charts()

    def _report_cash_ledger(self, account, d_from, d_to, transaction_type=""):
        fields = {"date": "التاريخ", "transaction_type": "الحركة",
                  "account": "الحساب", "category": "البند",
                  "party": "الطرف", "amount": "المبلغ (د.ك)"}
        rows = []
        for entry in td.load_cash_ledger():
            value = str(entry.get("date", "")).strip()
            if d_from and value < d_from or d_to and value > d_to:
                continue
            if account and entry.get("account") != account:
                continue
            if transaction_type and entry.get("transaction_type") != transaction_type:
                continue
            row = {key: entry.get(key, "") for key in fields}
            signed = td.safe_float(entry.get("amount"))
            if entry.get("transaction_type") == "صرف":
                signed = -signed
            row["amount"] = f"{signed:.3f}"
            rows.append(row)
        self._set_report_columns(fields, {"date": 110, "transaction_type": 100,
                                          "account": 100, "category": 150,
                                          "party": 150, "amount": 130})
        self._report_fields_cache = list(fields.items())
        self._report_rows_cache = rows
        self._insert_report_rows(rows, list(fields))
        amounts = [td.safe_float(row["amount"]) for row in rows]
        self._update_summary(len(rows), sum(amounts), sum(amounts) / len(amounts) if amounts else 0)
        # رسم بياني: مجاميع الحسابات
        account_totals = {}
        for row in rows:
            acct = str(row.get("account", "")).strip() or "غير محدد"
            account_totals[acct] = account_totals.get(acct, 0.0) + td.safe_float(row.get("amount", 0))
        self._chart_series_cache = sorted(account_totals.items(), key=lambda kv: -abs(kv[1]))[:8]
        self._chart_kind = "bar"
        self._donut_cache = [("مدين", sum(v for v in account_totals.values() if v > 0)),
                              ("دائن", abs(sum(v for v in account_totals.values() if v < 0)))]

    def _report_financial_comparison(self, _entity, d_from, d_to, _status=""):
        if not d_from or not d_to:
            self._report_financial("", d_from, d_to)
            return
        try:
            start = date.fromisoformat(d_from)
            end = date.fromisoformat(d_to)
        except ValueError:
            return
        span = (end - start).days + 1
        previous_end = start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=span - 1)
        current = td.financial_summary(d_from, d_to)
        previous = td.financial_summary(previous_start.isoformat(), previous_end.isoformat())
        rows = []
        for key, label in (("revenue", "الإيرادات"), ("expenses", "المصروفات"),
                           ("net_profit", "صافي الربح")):
            old, new = previous[key], current[key]
            change = new - old
            rows.append({"item": label, "current": f"{new:.3f}",
                         "previous": f"{old:.3f}", "change": f"{change:+.3f}"})
        fields = {"item": "البيان", "current": "الفترة الحالية",
                  "previous": "الفترة السابقة", "change": "التغير"}
        self._set_report_columns(fields, {"item": 180, "current": 140,
                                          "previous": 140, "change": 140})
        self._report_fields_cache = list(fields.items())
        self._report_rows_cache = rows
        self._insert_report_rows(rows, list(fields))
        self._update_summary(len(rows), current["net_profit"], current["net_profit"] / len(rows))
        # رسم بياني: مقارنة الفترة الحالية مع السابقة
        self._chart_series_cache = [
            ("إيرادات حالية", current["revenue"]), ("إيرادات سابقة", previous["revenue"]),
            ("مصاريف حالية", current["expenses"]), ("مصاريف سابقة", previous["expenses"]),
            ("ربح حالي", current["net_profit"]), ("ربح سابق", previous["net_profit"]),
        ]
        self._chart_kind = "bar"
        self._donut_cache = [("إيرادات", current["revenue"]), ("مصاريف", current["expenses"]),
                              ("صافي ربح", max(current["net_profit"], 0))]

    def _approve_financial_report(self):
        d_from, d_to = self._parse_report_period()
        if not d_from or not d_to:
            messagebox.showwarning("الاعتماد", "حدد بداية ونهاية الفترة أولاً.", parent=self)
            return
        if self.rep_type_var.get() not in ("تقرير مالي", "مقارنة مالية"):
            messagebox.showwarning("الاعتماد", "الاعتماد متاح للتقارير المالية فقط.", parent=self)
            return
        if not messagebox.askyesno("تأكيد الاعتماد",
                                   "سيتم حفظ نتيجة الفترة كنسخة معتمدة. متابعة؟",
                                   parent=self):
            return
        summary = td.financial_summary(d_from, d_to)
        try:
            td.approve_financial_period(f"{d_from}:{d_to}", summary)
        except (ValueError, PermissionError) as exc:
            messagebox.showerror("الاعتماد", str(exc), parent=self)
            return
        messagebox.showinfo("تم", "تم اعتماد التقرير المالي وحفظ نتيجته.", parent=self)

    def _current_report_display_name(self):
        return self.rep_type_var.get().strip() or "تقرير"

    def _save_report_screenshot(self, filename=None):
        """حفظ التقرير الحالي كصورة PNG."""
        if not _HAS_PIL:
            messagebox.showwarning("التصوير", "مكتبة Pillow غير متوفرة. قم بتثبيت pillow لاستخدام هذه الميزة.", parent=self)
            return None
        report_name = self._current_report_display_name()
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = re.sub(r"[^\w\s-]", "", report_name).strip() or "تقرير"
            filename = f"{safe_name[:30]}_{timestamp}.png"
        dest_dir = REPORT_SCREENSHOT_DIR
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except OSError:
            dest_dir = tempfile.gettempdir()
            try:
                os.makedirs(dest_dir, exist_ok=True)
            except OSError as _log_exc: log_exception("_save_report_screenshot", _log_exc)
        dest_path = os.path.join(dest_dir, filename)
        if not dest_path.lower().endswith(".png"):
            dest_path += ".png"
        try:
            img = self._compose_report_snapshot(report_name)
            if img:
                img.save(dest_path, "PNG", optimize=True)
            else:
                raise RuntimeError("compose returned None")
        except Exception as exc:
            messagebox.showerror("التصوير", f"تعذر حفظ لقطة التقرير:\n{exc}", parent=self)
            return None
        try:
            file_size = os.path.getsize(dest_path)
        except OSError:
            file_size = 0
        messagebox.showinfo("تم الحفظ", f"تم حفظ لقطة التقرير:\nالتقرير: {report_name}\nالملف: {os.path.basename(dest_path)}\nالحجم: {file_size / 1024:.1f} كيلوبايت\nالمجلد: {dest_dir}", parent=self)
        return dest_path

    def _compose_report_snapshot(self, report_name=None):
        """إنشاء لقطة موحدة للتقرير كصورة تتضمن العنوان + الجدول + الرسوم."""
        if not _HAS_PIL:
            return None
        report_name = report_name or self._current_report_display_name()
        base_w = max(self.report_tree.winfo_width(), 640)
        base_h = max(self.report_chart.winfo_height() + self.report_donut.winfo_height() + 120, 420)
        img = Image.new("RGB", (base_w, base_h), "#FFFFFF")
        draw = ImageDraw.Draw(img)
        try:
            title_font = ImageFont.truetype(FONT_NAME, 16)
            label_font = ImageFont.truetype(FONT_NAME, 11)
            small_font = ImageFont.truetype(FONT_NAME, 9)
        except (IOError, OSError):
            title_font = label_font = small_font = ImageFont.load_default()
        draw.rectangle([(0, 0), (base_w, 36)], fill="#1A2B4A")
        draw.text((12, 8), f"📊 {report_name}", font=title_font, fill="#FFFFFF")
        y = 40
        rows = getattr(self, "_report_rows_cache", [])
        fields = getattr(self, "_report_fields_cache", [])
        if rows and fields:
            col_count = len(fields)
            col_width = max(base_w // col_count, 110)
            header_h = 22
            row_h = 20
            draw.rectangle([(0, y), (base_w, y + header_h)], fill="#1A2B4A")
            x = 0
            for key, label in fields:
                draw.text((x + 6, y + 4), label, font=label_font, fill="#FFFFFF")
                x += col_width
            y += header_h
            for i, row in enumerate(rows):
                if i % 2 == 0:
                    draw.rectangle([(0, y), (base_w, y + row_h)], fill="#F7FAFC")
                x = 0
                for key, _label in fields:
                    val = safe_str(row.get(key, ""))
                    text_color = "#2D3748"
                    if key == "amount":
                        try:
                            v = float(val)
                            if v < 0:
                                text_color = "#C53030"
                            elif v > 0:
                                text_color = "#2F855A"
                        except (ValueError, TypeError) as _log_exc: log_exception("_compose_report_snapshot", _log_exc)
                    draw.text((x + 6, y + 3), val, font=small_font, fill=text_color)
                    x += col_width
                y += row_h
                if y > base_h - 120:
                    break
        kpis = getattr(self, "_kpi_cache", None)
        if kpis:
            for label, value, _color in kpis:
                draw.text((12, y + 18), f"{label}: {value}", font=label_font, fill="#1A2B4A")
                y += 18
        series = getattr(self, "_chart_series_cache", []) or []
        if series:
            bar_x = 12
            bar_area_w = max(base_w - 24, 300)
            bar_area_h = 110
            draw.rectangle([(0, y), (base_w, y + bar_area_h)], fill="#F5F7FA")
            values = [abs(td.safe_float(v)) for _, v in series[:8]]
            max_v = max(values) if values else 1.0
            if max_v == 0:
                max_v = 1.0
            bar_w = max(20, (bar_area_w - 20) // min(len(series), 8))
            bar_gap = 6
            color_idx = 0
            for label, value in series[:8]:
                v = td.safe_float(value)
                bh = max(4, int((abs(v) / max_v) * (bar_area_h - 20)))
                color = CHART_PALETTE[color_idx % len(CHART_PALETTE)]
                draw.rectangle([(bar_x, y + bar_area_h - 16 - bh), (bar_x + bar_w - bar_gap, y + bar_area_h - 16)], fill=color)
                draw.text((bar_x, y + bar_area_h - 14), label[:14], font=small_font, fill="#2D3748")
                bar_x += bar_w
                color_idx += 1
        draw.text((base_w - 12, base_h - 14), f"تم التصوير {datetime.now().strftime('%Y-%m-%d %H:%M')} — {report_name}", font=small_font, fill="#718096", anchor="ra")
        return img

    def _open_screenshot_gallery(self):
        """عرض حافظة تصوير التقارير."""
        if not _HAS_PIL:
            messagebox.showwarning("حافظة التصوير", "مكتبة Pillow غير متوفرة. قم بتثبيت pillow لعرض الحافظة.", parent=self)
            return

        gallery = tk.Toplevel(self)
        gallery.title("📸 حافظة تصوير التقارير")
        gallery.geometry("950x620")
        gallery.minsize(700, 480)
        gallery.configure(bg=COLOR_BG)
        gallery.transient(self)
        gallery.grab_set()

        top_bar = tk.Frame(gallery, bg=COLOR_PRIMARY, height=46)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)
        tk.Label(top_bar, text="📸 حافظة تصوير التقارير — لقطات محفوظة للتقارير والرسوم البيانية",
                 font=(FONT_NAME, 12, "bold"), bg=COLOR_PRIMARY, fg="white").pack(side="right", padx=18, pady=10)
        tk.Button(top_bar, text="🔄 تحديث", font=(FONT_NAME, 9), bg=COLOR_PRIMARY_LIGHT, fg="white",
                  activebackground=COLOR_ACCENT, activeforeground=COLOR_PRIMARY, relief="flat", bd=0,
                  cursor="hand2", command=rebuild).pack(side="right", padx=10, pady=10)

        filter_row = tk.Frame(gallery, bg=COLOR_BG)
        filter_row.pack(fill="x", padx=18, pady=(10, 6))
        tk.Label(filter_row, text="تصفية:", font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED).pack(side="right")
        gallery_filter_var = tk.StringVar()
        gallery_filter_cb = ttk.Combobox(filter_row, textvariable=gallery_filter_var, state="readonly",
                                          width=22, font=F_BODY)
        gallery_filter_cb.pack(side="right", padx=(4, 8))
        tk.Button(filter_row, text="🎯 الكل", font=F_LABEL, bg=COLOR_BORDER_LIGHT, fg=COLOR_TEXT,
                  relief="flat", bd=0, cursor="hand2",
                  command=lambda: (gallery_filter_var.set(""), rebuild())).pack(side="right", padx=4)
        gallery_filter_cb.bind("<<ComboboxSelected>>", lambda *a: rebuild())


        gallery_body = tk.Frame(gallery, bg=COLOR_BG)
        gallery_body.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        scroll = ttk.Scrollbar(gallery_body, orient="vertical")
        scroll.pack(side="right", fill="y")
        inner_canvas = tk.Canvas(gallery_body, bg=COLOR_BG, highlightthickness=0, yscrollcommand=scroll.set)
        inner_canvas.pack(side="left", fill="both", expand=True)
        scroll.config(command=inner_canvas.yview)
        inner_frame = tk.Frame(inner_canvas, bg=COLOR_BG)
        inner_canvas.create_window((0, 0), window=inner_frame, anchor="nw")
        inner_frame.bind("<Configure>", lambda e: inner_canvas.configure(scrollregion=inner_canvas.bbox("all")))
        inner_canvas.bind("<Configure>", lambda e: inner_canvas.itemconfig(inner_canvas.find_all()[0], width=e.width) if inner_canvas.find_all() else None)

        gallery_items = []

        def load_files():
            gallery_items.clear()
            try:
                for entry in os.scandir(REPORT_SCREENSHOT_DIR):
                    if entry.is_file and entry.name.lower().endswith(".png"):
                        gallery_items.append(entry.path)
            except OSError as _log_exc: log_exception("load_files", _log_exc)
            gallery_items.sort(reverse=True)

        def get_report_names_from_files():
            names = set()
            for fp in gallery_items:
                stem = os.path.splitext(os.path.basename(fp))[0]
                parts = stem.rsplit("_", 1)
                if len(parts) == 2 and len(parts[1]) >= 12:
                    names.add(parts[0].strip() or "تقرير")
                else:
                    names.add(stem.strip() or "تقرير")
            return sorted(names)

        def view_preview(path):
            preview = tk.Toplevel(gallery)
            preview.title(f"👁 عرض لقطة — {os.path.basename(path)}")
            preview.geometry("780x560")
            preview.configure(bg=COLOR_BG)
            preview.transient(gallery)
            preview.grab_set()
            top_b = tk.Frame(preview, bg=COLOR_PRIMARY, height=40)
            top_b.pack(fill="x")
            top_b.pack_propagate(False)
            tk.Label(top_b, text=f"👁 عرض لقطة — {os.path.basename(path)}", font=(FONT_NAME, 11, "bold"),
                     bg=COLOR_PRIMARY, fg="white").pack(side="left", padx=14, pady=8)
            tk.Button(top_b, text="إغلاق", font=F_LABEL, bg=COLOR_PRIMARY_LIGHT, fg="white",
                      relief="flat", bd=0, cursor="hand2", command=preview.destroy).pack(side="right", padx=10)
            try:
                img = Image.open(path).convert("RGB")
                img.thumbnail((740, 470), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                lbl = tk.Label(preview, image=photo, bg=COLOR_CARD, bd=0)
                lbl.img_ref = photo
                lbl.pack(fill="both", expand=True, padx=14, pady=10)
            except (OSError, IOError):
                tk.Label(preview, text="⚠ تعذرت قراءة الملف.", font=F_BODY, bg=COLOR_CARD, fg=COLOR_DANGER).pack(expand=True)
            preview.protocol("WM_DELETE_WINDOW", preview.destroy)

        def delete_one(path, name):
            if not messagebox.askyesno("حذف اللقطة", f"حذف لقطة:\n{name}\nلا يمكن التراجع. متابعة؟", parent=self):
                return
            try:
                os.remove(path)
                messagebox.showinfo("تم", f"تم الحذف:\n{name}", parent=self)
                rebuild()
            except OSError as exc:
                messagebox.showerror("خطأ", f"تعذر الحذف:\n{exc}", parent=self)

        def rebuild():
            load_files()
            gallery_filter_cb.config(values=get_report_names_from_files())
            fv = gallery_filter_var.get().strip()
            for child in list(inner_frame.winfo_children()):
                child.destroy()
            if not gallery_items:
                tk.Label(inner_frame, text="📸 لا توجد لقطات محفوظة بعد.\nشغّل تقريراً ثم اضغط على زر الحافظة لحفظ لقطة.",
                         font=F_BODY, bg=COLOR_CARD, fg=COLOR_MUTED, justify="center").pack(expand=True, padx=30, pady=30)
            else:
                filtered = []
                for fp in gallery_items:
                    stem = os.path.splitext(os.path.basename(fp))[0]
                    parts = stem.rsplit("_", 1)
                    rn = parts[0].strip() if len(parts) == 2 and len(parts[1]) >= 12 else stem.strip()
                    if not fv or rn == fv or fv in rn:
                        filtered.append(fp)
                for col in range(3):
                    inner_frame.grid_columnconfigure(col, weight=1)
                for idx, fp in enumerate(filtered):
                    card = tk.Frame(inner_frame, bg=COLOR_CARD, relief="flat", bd=0)
                    card.grid(row=idx // 3, column=idx % 3, padx=6, pady=6, sticky="nsew")
                    card.grid_rowconfigure(0, weight=1)
                    card.grid_columnconfigure(0, weight=1)
                    try:
                        thumb = Image.open(fp).convert("RGB")
                        thumb.thumbnail((210, 180), Image.LANCZOS)
                        thumb_img = ImageTk.PhotoImage(thumb)
                        lbl = tk.Label(card, image=thumb_img, bg=COLOR_CARD, bd=0)
                        lbl.image_ref = thumb_img
                        lbl.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4, 2))
                    except (OSError, IOError):
                        tk.Label(card, text="📸", font=(FONT_NAME, 48), bg=COLOR_CARD, fg=COLOR_MUTED).grid(row=0, column=0)
                    base = os.path.basename(fp)
                    stem = os.path.splitext(base)[0]
                    parts = stem.rsplit("_", 1)
                    date_str = ""
                    short_name = stem
                    if len(parts) == 2 and len(parts[1]) >= 12 and parts[1][4] == "_":
                        date_str = f"{parts[1][:4]}-{parts[1][4:6]}-{parts[1][6:8]} {parts[1][9:11]}:{parts[1][11:13]}"
                        short_name = parts[0]
                    report_name = short_name.strip() or "تقرير"
                    info = tk.Frame(card, bg=COLOR_CARD)
                    info.grid(row=1, column=0, sticky="ew", padx=4, pady=(2, 4))
                    tk.Label(info, text=report_name[:32] or "تقرير", font=(FONT_NAME, 9, "bold"),
                             bg=COLOR_CARD, fg=COLOR_TEXT, justify="right", wraplength=200).pack(fill="x")
                    if date_str:
                        tk.Label(info, text=f"🕐 {date_str}", font=(FONT_NAME, 8), bg=COLOR_CARD, fg=COLOR_MUTED).pack(fill="x")
                    tk.Label(info, text=f"📄 {base}", font=(FONT_NAME, 7), bg=COLOR_CARD, fg=COLOR_MUTED).pack(fill="x")
                    btn_frame = tk.Frame(card, bg=COLOR_CARD)
                    btn_frame.grid(row=2, column=0, sticky="ew", padx=4, pady=(0, 4))
                    tk.Button(btn_frame, text="👁 عرض", font=(FONT_NAME, 8), bg=COLOR_ACCENT_LIGHT,
                              fg=COLOR_PRIMARY, activebackground=COLOR_ACCENT, activeforeground=COLOR_PRIMARY,
                              relief="raised", bd=1, cursor="hand2", command=lambda p=fp: view_preview(p)).pack(side="left", fill="x", expand=True, padx=(0, 2))
                    tk.Button(btn_frame, text="🗑 حذف", font=(FONT_NAME, 8), bg=COLOR_BORDER_LIGHT,
                              fg=COLOR_DANGER, activebackground=COLOR_DANGER, activeforeground="white",
                              relief="raised", bd=1, cursor="hand2",
                              command=lambda p=fp, n=base: delete_one(p, n)).pack(side="left", fill="x", expand=True, padx=(2, 0))

        rebuild()

        bottom_bar = tk.Frame(gallery, bg=COLOR_BG)
        bottom_bar.pack(fill="x", padx=18, pady=(0, 10))
        tk.Button(bottom_bar, text="📂 فتح مجلد التصوير", font=F_LABEL, bg=COLOR_BORDER_LIGHT,
                  fg=COLOR_TEXT, relief="flat", bd=0, cursor="hand2",
                  command=lambda: os.startfile(REPORT_SCREENSHOT_DIR) if os.path.isdir(REPORT_SCREENSHOT_DIR) else None).pack(side="right")
        gallery.protocol("WM_DELETE_WINDOW", gallery.destroy)
        gallery.focus_set()

        # ---------------- محرك الرسوم البيانية للتقارير ----------------
    def _render_report_charts(self):
        """يرسم المخطط الرئيسي (أعمدة/خط) والمخطط الدائري وفق بيانات التقرير الحالي."""
        canvas = getattr(self, "report_chart", None)
        donut = getattr(self, "report_donut", None)
        if canvas is None:
            return
        series = getattr(self, "_chart_series_cache", []) or []
        if not series:
            series = self._derive_chart_series()
        kind = getattr(self, "_chart_kind", "bar")
        self._draw_series_chart(canvas, series, kind)
        if donut is not None:
            slices = getattr(self, "_donut_cache", []) or []
            if not slices:
                slices = series
            self._draw_donut_chart(donut, slices)

    def _derive_chart_series(self):
        """اشتقاق تلقائي لسلسلة الرسم من صفوف التقرير بتجميع القيم حسب العمود المناسب."""
        rows = getattr(self, "_report_rows_cache", [])
        if not rows:
            return []
        first = rows[0]
        for key in ("label", "type", "item", "car", "partner", "month", "customer", "category"):
            if key in first:
                totals = {}
                order = []
                for row in rows:
                    label = safe_str(row.get(key, "")).strip() or "غير محدد"
                    if label not in totals:
                        order.append(label)
                    totals[label] = totals.get(label, 0.0) + td.safe_float(row.get("amount", 0))
                series = [(label[:16], totals[label]) for label in order if totals[label]]
                series.sort(key=lambda item: -item[1])
                return series[:12]
        return []

    def _draw_series_chart(self, canvas, series, kind="bar"):
        """رسم سلسلة القيم: أعمدة رأسية (مع دعم القيم السالبة) أو خط بياني."""
        canvas.delete("all")
        width = max(canvas.winfo_width(), 420)
        height = max(canvas.winfo_height(), 200)
        data = [(safe_str(label).strip()[:16] or "غير محدد", td.safe_float(value))
                for label, value in (series or [])]
        values = [value for _label, value in data]
        if not data or not any(values):
            canvas.create_text(width / 2, height / 2, text="لا توجد قيم كافية لعرض الرسم البياني",
                               fill=COLOR_MUTED, font=F_LABEL)
            return
        pad_top, pad_bottom, pad_left, pad_right = 26, 34, 52, 14
        plot_w = width - pad_left - pad_right
        plot_h = height - pad_top - pad_bottom
        v_max = max(values + [0.0])
        v_min = min(values + [0.0])
        span = (v_max - v_min) or 1.0

        def y_for(value):
            return pad_top + plot_h * (1.0 - (value - v_min) / span)

        for i in range(5):
            grid_value = v_min + span * i / 4.0
            y = pad_top + plot_h * i / 4.0
            canvas.create_line(pad_left, y, width - pad_right, y, fill=COLOR_BORDER)
            canvas.create_text(pad_left - 6, y, text=f"{grid_value:,.1f}", anchor="e",
                               font=(FONT_NAME, 7), fill=COLOR_MUTED)
        zero_y = y_for(0.0)
        canvas.create_line(pad_left, zero_y, width - pad_right, zero_y,
                           fill=COLOR_MUTED, dash=(4, 3))
        n = len(data)
        if kind == "line" or n > 12:
            points = []
            for index, (_label, value) in enumerate(data):
                x = pad_left + (plot_w * index / (n - 1) if n > 1 else plot_w / 2)
                points.extend([x, y_for(value)])
            canvas.create_line(*points, fill=COLOR_PRIMARY_LIGHT, width=2, smooth=True)
            for index, (label, value) in enumerate(data):
                x = pad_left + (plot_w * index / (n - 1) if n > 1 else plot_w / 2)
                y = y_for(value)
                color = COLOR_SUCCESS if value >= 0 else COLOR_DANGER
                canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline="")
                canvas.create_text(x, y - 10 if value >= 0 else y + 10,
                                   text=f"{value:,.1f}", font=(FONT_NAME, 7), fill=COLOR_TEXT)
                canvas.create_text(x, height - pad_bottom + 12, text=label[:10],
                                   font=(FONT_NAME, 7), fill=COLOR_MUTED)
        else:
            slot = plot_w / n
            bar_w = max(14, min(46, slot * 0.62))
            for index, (label, value) in enumerate(data):
                center = pad_left + slot * (index + 0.5)
                y = y_for(value)
                color = COLOR_SUCCESS if value >= 0 else COLOR_DANGER
                canvas.create_rectangle(center - bar_w / 2, min(y, zero_y),
                                        center + bar_w / 2, max(y, zero_y),
                                        fill=color, outline="")
                canvas.create_text(center, y - 9 if value >= 0 else y + 9,
                                   text=f"{value:,.1f}", font=(FONT_NAME, 7), fill=COLOR_TEXT)
                canvas.create_text(center, height - pad_bottom + 12, text=label,
                                   font=(FONT_NAME, 7), fill=COLOR_MUTED)

    def _draw_donut_chart(self, canvas, slices):
        """رسم مخطط دائري مجوّف (Donut) مع مفتاح تفسيري بالنِسب."""
        canvas.delete("all")
        width = max(canvas.winfo_width(), 300)
        height = max(canvas.winfo_height(), 200)
        data = []
        for label, value in (slices or []):
            value = abs(td.safe_float(value))
            label = safe_str(label).strip()[:20] or "غير محدد"
            if value > 0:
                data.append((label, value))
        data.sort(key=lambda item: -item[1])
        if len(data) > 6:
            rest = sum(value for _label, value in data[5:])
            data = data[:5] + [("أخرى", rest)]
        if not data:
            canvas.create_text(width / 2, height / 2, text="لا توجد بيانات للتوزيع",
                               fill=COLOR_MUTED, font=F_LABEL)
            return
        total = sum(value for _label, value in data)
        radius = max(44, min(70, (height - 44) / 2))
        cx = width - radius - 36
        cy = height / 2
        start = 90.0
        for index, (_label, value) in enumerate(data):
            extent = (value / total) * 360.0
            color = CHART_PALETTE[index % len(CHART_PALETTE)]
            canvas.create_arc(cx - radius, cy - radius, cx + radius, cy + radius,
                              start=start, extent=extent, fill=color,
                              outline=COLOR_CARD, width=2, style="pieslice")
            start += extent
        hole = radius * 0.60
        canvas.create_oval(cx - hole, cy - hole, cx + hole, cy + hole,
                           fill=COLOR_CARD, outline=COLOR_BORDER)
        canvas.create_text(cx, cy - 10, text="الإجمالي", font=(FONT_NAME, 7), fill=COLOR_MUTED)
        canvas.create_text(cx, cy + 6, text=f"{total:,.0f}",
                           font=(FONT_NAME, 11, "bold"), fill=COLOR_TEXT)
        legend_x = 12
        row_h = max(20, min(30, int((height - 20) / max(1, len(data)))))
        y = 14
        for index, (label, value) in enumerate(data):
            pct = (value / total) * 100.0
            color = CHART_PALETTE[index % len(CHART_PALETTE)]
            canvas.create_rectangle(legend_x, y, legend_x + 13, y + 13, fill=color, outline="")
            canvas.create_text(legend_x + 21, y + 6, anchor="w",
                               text=f"{label}: {value:,.1f} ({pct:.0f}%)",
                               font=(FONT_NAME, 8), fill=COLOR_TEXT)
            y += row_h

    def _set_report_columns(self, columns, widths=None):
        self._report_fields_cache = [(key, label) for key, label in columns.items()]
        visual_columns = list(reversed(list(columns.items())))
        self.report_tree.config(columns=[key for key, _label in visual_columns])
        for key, label in visual_columns:
            self.report_tree.heading(key, text=label)
            width = widths.get(key, 160) if widths else 160
            anchor = "e" if key == "amount" else "e"
            self.report_tree.column(key, anchor=anchor, width=width)

    def _insert_report_rows(self, rows, key_order):
        for index, row in enumerate(rows):
            values = tuple(safe_str(row.get(k, "")) for k in reversed(key_order))
            amount = td.safe_float(row.get("amount", 0))
            if amount < 0:
                tag = ("negative",)
            elif index % 2:
                tag = ("odd",)
            else:
                tag = ()
            self.report_tree.insert("", "end", values=values, tags=tag)

    def _report_financial(self, entity, d_from, d_to, status=""):
        s = td.financial_summary(d_from, d_to)
        self._set_report_columns({"item": "البيان", "amount": "المبلغ (د.ك)"}, {"item": 280, "amount": 160})
        rows = [
            {"item": "الإيرادات من الفواتير الصادرة", "amount": f"{s['revenue']:.3f}"},
            {"item": "مصاريف صيانة السيارات", "amount": f"{s['maintenance_cost']:.3f}"},
            {"item": "المصاريف اليومية للسيارات", "amount": f"{s['daily_expenses_cost']:.3f}"},
            {"item": "السلف اليومية للسائقين", "amount": f"{s['advances_cost']:.3f}"},
            {"item": "مصاريف الرواتب", "amount": f"{s['salaries_cost']:.3f}"},
            {"item": "إجمالي المصروفات", "amount": f"{s['expenses']:.3f}"},
            {"item": "صافي الربح / الخسارة", "amount": f"{s['net_profit']:.3f}"},
        ]
        margin = (s["net_profit"] / s["revenue"] * 100.0) if s["revenue"] else 0.0
        self._chart_series_cache = [
            ("الإيرادات", s["revenue"]), ("الصيانة", s["maintenance_cost"]),
            ("مصاريف يومية", s["daily_expenses_cost"]), ("السلف", s["advances_cost"]),
            ("الرواتب", s["salaries_cost"]), ("صافي الربح", s["net_profit"]),
        ]
        self._chart_kind = "bar"
        self._donut_cache = [
            ("الصيانة", s["maintenance_cost"]), ("مصاريف يومية", s["daily_expenses_cost"]),
            ("السلف", s["advances_cost"]), ("الرواتب", s["salaries_cost"]),
        ]
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["item", "amount"])
        self._update_summary(
            count=len(rows), total=s["net_profit"],
            avg=s["net_profit"] / len(rows) if rows else 0,
            kpis=[
                ("الإيرادات", f"{s['revenue']:,.3f} د.ك", COLOR_SUCCESS),
                ("المصروفات", f"{s['expenses']:,.3f} د.ك", COLOR_DANGER),
                ("صافي الربح", f"{s['net_profit']:,.3f} د.ك",
                 COLOR_SUCCESS if s["net_profit"] >= 0 else COLOR_DANGER),
                ("هامش الربح", f"{margin:.1f}%", COLOR_ACCENT),
            ],
        )

    def _report_drivers(self, driver, d_from, d_to, status=""):
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "amount": "المبلغ (د.ك)"}, {"label": 140, "detail": 320, "amount": 140})
        self._report_fields_cache = [("label", "البيان"), ("detail", "التفاصيل"), ("amount", "المبلغ (د.ك)")]
        drivers = [d for d in td.load_drivers() if not driver or str(d.get("name", "")) == driver]
        if not drivers:
            return
        rows = []
        totals = []
        for driver_row in drivers:
            target = driver_row.get("name", "")
            details = td.driver_salary_period_details(target, d_from, d_to)
            start_index = len(rows)
            rows.append({"label": "السائق", "detail": target, "amount": ""})
            rows.append({"label": "الراتب الأساسي", "detail": f"{details['base_salary']:.3f} د.ك", "amount": f"{details['base_salary']:.3f}"})
            for record in details.get("car_expense_records", []):
                rows.append({"label": "مصروف سيارة", "detail": f"{record['date']} - {record['category']}", "amount": f"{record['amount']:.3f}"})
            for record in details.get("driver_expense_records", []):
                rows.append({"label": "مصروف سائق", "detail": f"{record['date']} - {record['category']}", "amount": f"{record['amount']:.3f}"})
            rows.append({"label": "إجمالي الرحلات", "detail": f"{len(details.get('trips', []))} رحلة", "amount": f"{details.get('revenue', 0):.3f}"})
            car_total = sum(td.safe_float(rows[i].get('amount', 0)) for i in range(start_index, len(rows)) if rows[i].get('label') == 'مصروف سيارة')
            driver_total = sum(td.safe_float(rows[i].get('amount', 0)) for i in range(start_index, len(rows)) if rows[i].get('label') == 'مصروف سائق')
            rows.append({"label": "إجمالي مصاريف السيارة", "detail": "", "amount": f"{car_total:.3f}"})
            rows.append({"label": "إجمالي مصاريف السائق", "detail": "", "amount": f"{driver_total:.3f}"})
            totals.append(car_total + driver_total)
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "amount"])
        self._update_summary(count=len(drivers), total=sum(totals), avg=sum(totals) / len(totals) if totals else 0)
        # رسم بياني: إجمالي مصاريف كل سائق
        driver_names = [str(d.get("name", "")).strip() or f"سائق {i+1}" for i, d in enumerate(drivers)]
        self._chart_series_cache = list(zip(driver_names[:10], totals[:10]))
        self._chart_kind = "bar"
        self._donut_cache = [("مصاريف السيارات", sum(car_total for car_total in totals if car_total > 0)),
                              ("عدد السائقين", float(len(drivers)))]

    def _report_vehicles(self, car_no, d_from, d_to, status=""):
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "amount": "المبلغ (د.ك)"}, {"label": 140, "detail": 320, "amount": 140})
        self._report_fields_cache = [("label", "البيان"), ("detail", "التفاصيل"), ("amount", "المبلغ (د.ك)")]
        rows = []
        totals = []
        for record in td.vehicle_financial_details(d_from, d_to, car_no):
            rows.append({"label": "السيارة", "detail": record.get("car_no", ""), "amount": ""})
            rows.append({"label": "السائق", "detail": record.get("driver", ""), "amount": ""})
            rows.append({"label": "الإيرادات", "detail": "رسوم الرحلات", "amount": f"{record.get('revenue', 0):.3f}"})
            rows.append({"label": "إيراد العطل", "detail": "", "amount": f"{record.get('holiday', 0):.3f}"})
            for item in record.get("car_expense_records", []):
                rows.append({"label": "مصروف سيارة", "detail": f"{item['date']} - {item['category']} ({item['source']})", "amount": f"{item['amount']:.3f}"})
            for item in record.get("driver_expense_records", []):
                rows.append({"label": "مصروف سائق", "detail": f"{item['date']} - {item['category']} ({item['source']})", "amount": f"{item['amount']:.3f}"})
            rows.append({"label": "إجمالي مصاريف السيارة", "detail": "", "amount": f"{record.get('car_expenses', 0):.3f}"})
            rows.append({"label": "إجمالي مصاريف السائق", "detail": "", "amount": f"{record.get('driver_expenses', 0):.3f}"})
            rows.append({"label": "صافي السيارة", "detail": "", "amount": f"{record.get('net_vehicle', 0):.3f}"})
            totals.append(record.get('net_vehicle', 0))
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "amount"])
        self._update_summary(count=len(totals), total=sum(totals), avg=sum(totals) / len(totals) if totals else 0)
        # رسم بياني: صافي ربح كل سيارة
        car_labels = []
        car_values = []
        for record in td.vehicle_financial_details(None, None, None):
            car_labels.append(str(record.get("car_no", "")).strip() or "—")
            car_values.append(record.get("net_vehicle", 0))
        self._chart_series_cache = list(zip(car_labels[:10], car_values[:10]))
        self._chart_kind = "bar"
        self._donut_cache = [("إجمالي صافي الربح", sum(v for v in car_values if v > 0)),
                              ("عدد السيارات", float(len(car_values)))]

    def _report_trips(self, entity, d_from, d_to, status=""):
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "amount": "المبلغ (د.ك)"}, {"label": 140, "detail": 320, "amount": 140})
        self._report_fields_cache = [("label", "البيان"), ("detail", "التفاصيل"), ("amount", "المبلغ (د.ك)")]
        rows = []
        totals = []
        month_totals = {}
        category_totals = {}
        for trip in td.load_trips():
            trip_date = str(trip.get("date", ""))
            if d_from and trip_date < d_from:
                continue
            if d_to and trip_date > d_to:
                continue
            category = str(trip.get("trip_category", "")).strip()
            if status and category != status:
                continue
            if entity and not any(
                str(trip.get(f, "")) == entity
                for f in ("driver", "car_no", "customer", "company")
            ):
                continue
            fee = td.safe_float(trip.get("fee"))
            rows.append({
                "label": "رحلة",
                "detail": f"{trip_date} - {category} - {trip.get('direction', '')}",
                "amount": f"{fee:.3f}"
            })
            totals.append(fee)
            month_key = trip_date[:7]
            if month_key:
                month_totals[month_key] = month_totals.get(month_key, 0.0) + fee
            if category:
                category_totals[category] = category_totals.get(category, 0.0) + fee
        self._chart_series_cache = [(key, month_totals[key]) for key in sorted(month_totals)[-12:]]
        self._chart_kind = "bar"
        self._donut_cache = list(category_totals.items())
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "amount"])
        self._update_summary(
            count=len(rows), total=sum(totals),
            avg=sum(totals) / len(totals) if totals else 0,
            kpis=[
                ("عدد الرحلات", str(len(rows)), COLOR_PRIMARY_LIGHT),
                ("قيمة الرحلات", f"{sum(totals):,.3f} د.ك", COLOR_ACCENT),
                ("متوسط الرحلة", f"{sum(totals) / len(totals):,.3f} د.ك" if totals else "0 د.ك", COLOR_PRIMARY),
            ],
        )
        # رسم إضافي: متوسط الإيراد الشهري
        if month_totals:
            display_months = sorted(month_totals)[-6:]
            self._chart_series_cache = [(k, month_totals[k]) for k in display_months]
            self._donut_cache = [(k, month_totals[k]) for k in display_months]

    def _report_expenses(self, owner, d_from, d_to, status=""):
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "amount": "المبلغ (د.ك)"}, {"label": 140, "detail": 320, "amount": 140})
        self._report_fields_cache = [("label", "البيان"), ("detail", "التفاصيل"), ("amount", "المبلغ (د.ك)")]
        rows = []
        totals = []
        category_totals = {}
        owner_totals = {}
        for expense in td.load_daily_expenses():
            if d_from and str(expense.get("date", "")) < d_from:
                continue
            if d_to and str(expense.get("date", "")) > d_to:
                continue
            if status and str(expense.get("category", "")) != status:
                continue
            expense_owner = td.daily_expense_owner(expense)
            if owner and expense_owner != owner and str(expense.get("car_no", "")) != owner and str(expense.get("driver", "")) != owner:
                continue
            amount = td.safe_float(expense.get("amount"))
            rows.append({
                "label": expense_owner,
                "detail": f"{expense.get('date', '')} - {expense.get('category', '')} - {expense.get('car_no', '')} / {expense.get('driver', '')}",
                "amount": f"{amount:.3f}"
            })
            totals.append(amount)
            category = str(expense.get("category", "")).strip() or "غير محدد"
            category_totals[category] = category_totals.get(category, 0.0) + amount
            owner_key = str(expense.get("car_no", "")).strip() or expense_owner or "غير محدد"
            owner_totals[owner_key] = owner_totals.get(owner_key, 0.0) + amount
        self._chart_series_cache = sorted(category_totals.items(), key=lambda kv: -kv[1])[:12]
        self._chart_kind = "bar"
        self._donut_cache = sorted(owner_totals.items(), key=lambda kv: -kv[1])[:6]
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "amount"])
        self._update_summary(
            count=len(rows), total=sum(totals),
            avg=sum(totals) / len(totals) if totals else 0,
            kpis=[
                ("عدد المصاريف", str(len(rows)), COLOR_PRIMARY_LIGHT),
                ("إجمالي المصاريف", f"{sum(totals):,.3f} د.ك", COLOR_DANGER),
                ("متوسط المصروف", f"{sum(totals) / len(totals):,.3f} د.ك" if totals else "0 د.ك", COLOR_PRIMARY),
                ("أعلى بند", f"{max(category_totals.items(), key=lambda kv: kv[1])[0]}" if category_totals else "—", COLOR_ACCENT),
            ],
        )

    def _report_invoices(self, customer, d_from, d_to, status=""):
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "extra": "معلومات إضافية", "amount": "المبلغ (د.ك)"}, {"label": 140, "detail": 260, "extra": 200, "amount": 120})
        self._report_fields_cache = [("label", "البيان"), ("detail", "التفاصيل"), ("extra", "معلومات إضافية"), ("amount", "المبلغ (د.ك)")]
        rows = []
        totals = []
        month_totals = {}
        paid_totals = {"مدفوعة": 0.0, "غير مدفوعة": 0.0}
        for inv in td.load_invoices():
            if d_from and str(inv.get("date", "")) < d_from:
                continue
            if d_to and str(inv.get("date", "")) > d_to:
                continue
            if customer and str(inv.get("customer", "")) != customer:
                continue
            paid_state = (safe_str(inv.get("paid")).strip() or "لا")
            if status and paid_state != status:
                continue
            total = td.safe_float(inv.get("total"))
            rows.append({
                "label": "فاتورة",
                "detail": f"{inv.get('date', '')} - {inv.get('customer', '')}",
                "extra": f"رقم: {inv.get('invoice_no', '')} | بيان: {inv.get('declaration_no', '')}",
                "amount": f"{total:.3f}"
            })
            totals.append(total)
            month_key = str(inv.get("date", ""))[:7]
            if month_key:
                month_totals[month_key] = month_totals.get(month_key, 0.0) + total
            paid_totals["مدفوعة" if paid_state == "نعم" else "غير مدفوعة"] += total
        self._chart_series_cache = [(key, month_totals[key]) for key in sorted(month_totals)[-12:]]
        self._chart_kind = "bar"
        self._donut_cache = list(paid_totals.items())
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(
            count=len(rows), total=sum(totals),
            avg=sum(totals) / len(totals) if totals else 0,
            kpis=[
                ("عدد الفواتير", str(len(rows)), COLOR_PRIMARY_LIGHT),
                ("إجمالي الفواتير", f"{sum(totals):,.3f} د.ك", COLOR_ACCENT),
                ("المحصّل (مدفوع)", f"{paid_totals['مدفوعة']:,.3f} د.ك", COLOR_SUCCESS),
                ("المتبقي (غير مدفوع)", f"{paid_totals['غير مدفوعة']:,.3f} د.ك", COLOR_DANGER),
            ],
        )

    def _report_payments(self, customer, d_from, d_to, status=""):
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "extra": "معلومات إضافية", "amount": "المبلغ (د.ك)"}, {"label": 140, "detail": 260, "extra": 200, "amount": 120})
        self._report_fields_cache = [("label", "البيان"), ("detail", "التفاصيل"), ("extra", "معلومات إضافية"), ("amount", "المبلغ (د.ك)")]
        rows = []
        totals = []
        for payment in td.load_payments():
            if d_from and str(payment.get("date", "")) < d_from:
                continue
            if d_to and str(payment.get("date", "")) > d_to:
                continue
            if customer and str(payment.get("customer", "")) != customer:
                continue
            amount = td.safe_float(payment.get("amount"))
            rows.append({
                "label": "دفعة",
                "detail": f"{payment.get('date', '')} - {payment.get('customer', '')}",
                "extra": f"مرجع: {payment.get('reference', '')} | بيان: {payment.get('invoice_no', '')}",
                "amount": f"{amount:.3f}"
            })
            totals.append(amount)
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(count=len(rows), total=sum(totals), avg=sum(totals) / len(totals) if totals else 0)
        # رسم دفعات حسب المرجع
        ref_totals = {}
        for r in rows:
            extra = r.get("extra", "")
            m = re.search(r"مرجع[:\s]+([^|]+)", extra)
            if m:
                ref = m.group(1).strip()[:16]
                ref_totals[ref] = ref_totals.get(ref, 0.0) + td.safe_float(r.get("amount", 0))
        if ref_totals:
            self._chart_series_cache = sorted(ref_totals.items(), key=lambda kv: -kv[1])[:8]
            self._chart_kind = "bar"
        self._donut_cache = list(ref_totals.items())[:6]

    def _report_services(self, customer, d_from, d_to, status=""):
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "extra": "معلومات إضافية", "amount": "المبلغ (د.ك)"}, {"label": 140, "detail": 260, "extra": 200, "amount": 120})
        self._report_fields_cache = [("label", "البيان"), ("detail", "التفاصيل"), ("extra", "معلومات إضافية"), ("amount", "المبلغ (د.ك)")]
        rows = []
        totals = []
        for service in td.load_services():
            if d_from and str(service.get("date", "")) < d_from:
                continue
            if d_to and str(service.get("date", "")) > d_to:
                continue
            if customer and str(service.get("customer", "")) != customer:
                continue
            if status and str(service.get("service_type", "")) != status:
                continue
            total = td.safe_float(service.get("total"))
            rows.append({
                "label": service.get("service_type", ""),
                "detail": f"{service.get('date', '')} - {service.get('customer', '')}",
                "extra": f"كمية: {service.get('quantity', '')} | سعر: {service.get('unit_price', '')}",
                "amount": f"{total:.3f}"
            })
            totals.append(total)
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(count=len(rows), total=sum(totals), avg=sum(totals) / len(totals) if totals else 0)
        # رسم الخدمات حسب النوع
        type_totals = {}
        for r in rows:
            label = r.get("label", "").strip()[:16]
            if label:
                type_totals[label] = type_totals.get(label, 0.0) + td.safe_float(r.get("amount", 0))
        if type_totals:
            self._chart_series_cache = sorted(type_totals.items(), key=lambda kv: -kv[1])[:8]
            self._chart_kind = "bar"
        self._donut_cache = list(type_totals.items())[:6]

    def _report_maintenance(self, car_no, d_from, d_to, status=""):
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "extra": "معلومات إضافية", "amount": "المبلغ (د.ك)"}, {"label": 140, "detail": 260, "extra": 200, "amount": 120})
        self._report_fields_cache = [("label", "البيان"), ("detail", "التفاصيل"), ("extra", "معلومات إضافية"), ("amount", "المبلغ (د.ك)")]
        rows = []
        totals = []
        for m in td.load_maintenance():
            if d_from and str(m.get("date", "")) < d_from:
                continue
            if d_to and str(m.get("date", "")) > d_to:
                continue
            if car_no and str(m.get("car_no", "")) != car_no:
                continue
            if status and str(m.get("type", "")) != status:
                continue
            cost = td.safe_float(m.get("cost"))
            rows.append({
                "label": "صيانة",
                "detail": f"{m.get('date', '')} - {m.get('car_no', '')}",
                "extra": f"نوع: {m.get('type', '')} | ملاحظات: {m.get('notes', '')}",
                "amount": f"{cost:.3f}"
            })
            totals.append(cost)
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(count=len(rows), total=sum(totals), avg=sum(totals) / len(totals) if totals else 0)
        # رسم الصيانة حسب النوع
        type_totals = {}
        for r in rows:
            extra = r.get("extra", "")
            m = re.search(r"نوع[:\s]+([^|]+)", extra)
            if m:
                t = m.group(1).strip()[:16]
                type_totals[t] = type_totals.get(t, 0.0) + td.safe_float(r.get("amount", 0))
        if type_totals:
            self._chart_series_cache = sorted(type_totals.items(), key=lambda kv: -kv[1])[:8]
            self._chart_kind = "bar"
        self._donut_cache = list(type_totals.items())[:6]

    def _report_salaries(self, driver, d_from, d_to, status=""):
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "extra": "معلومات إضافية", "amount": "المبلغ (د.ك)"}, {"label": 140, "detail": 260, "extra": 200, "amount": 120})
        self._report_fields_cache = [("label", "البيان"), ("detail", "التفاصيل"), ("extra", "معلومات إضافية"), ("amount", "المبلغ (د.ك)")]
        rows = []
        totals = []
        for s in td.load_salaries():
            salary_month = str(s.get("month", "")).strip()
            if d_from and salary_month < d_from[:7]:
                continue
            if d_to and salary_month > d_to[:7]:
                continue
            if driver and str(s.get("driver", "")) != driver:
                continue
            if status and str(s.get("paid", "")) != status:
                continue
            net = td.safe_float(s.get("net_salary"))
            rows.append({
                "label": "راتب",
                "detail": f"{s.get('driver', '')} - {s.get('month', '')}",
                "extra": (
                    f"نوع: {s.get('salary_type', '')} | مدفوع: {s.get('paid', '')}"
                    f" | رحلات: {td.safe_float(s.get('trip_revenue')):.3f}"
                    f" | عطل: {td.safe_float(s.get('holiday_revenue')):.3f}"
                    f" | أساسي: {td.safe_float(s.get('base_salary')):.3f}"
                ),
                "amount": f"{net:.3f}"
            })
            totals.append(net)
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(count=len(rows), total=sum(totals), avg=sum(totals) / len(totals) if totals else 0)
        # رسم رواتب حسب السائق
        driver_totals = {}
        for r in rows:
            detail = r.get("detail", "").strip()[:16]
            if detail:
                driver_totals[detail] = driver_totals.get(detail, 0.0) + td.safe_float(r.get("amount", 0))
        if driver_totals:
            self._chart_series_cache = sorted(driver_totals.items(), key=lambda kv: -kv[1])[:10]
            self._chart_kind = "bar"
        self._donut_cache = [("إجمالي الرواتب", sum(totals))] if totals else [("إجمالي الرواتب", 0)]

    def _report_customers(self, customer, d_from, d_to, status=""):
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "extra": "معلومات إضافية", "amount": "المبلغ (د.ك)"}, {"label": 140, "detail": 260, "extra": 200, "amount": 120})
        self._report_fields_cache = [("label", "البيان"), ("detail", "التفاصيل"), ("extra", "معلومات إضافية"), ("amount", "المبلغ (د.ك)")]
        rows = []
        for c in td.load_customers():
            if customer and str(c.get("name", "")) != customer:
                continue
            name = c.get("name", "")
            phone = c.get("phone", "")
            address = c.get("address", "")
            rows.append({
                "label": "عميل",
                "detail": name,
                "extra": f"هاتف: {phone} | عنوان: {address}",
                "amount": ""
            })
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(count=len(rows))
        # رسم: تمثيل بسيط (العملاء كأعمدة)
        self._chart_series_cache = [(r["detail"], 1.0) for r in rows[:12]]
        self._chart_kind = "bar"
        self._donut_cache = [("عدد العملاء", float(len(rows)))] if rows else [("عدد العملاء", 0)]

    def _report_companies(self, company, d_from, d_to, status=""):
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "extra": "معلومات إضافية", "amount": "المبلغ (د.ك)"}, {"label": 140, "detail": 260, "extra": 200, "amount": 120})
        self._report_fields_cache = [("label", "البيان"), ("detail", "التفاصيل"), ("extra", "معلومات إضافية"), ("amount", "المبلغ (د.ك)")]
        rows = []
        for c in td.load_companies():
            if company and str(c.get("name", "")) != company:
                continue
            name = c.get("name", "")
            broker = c.get("customs_broker", "")
            phone = c.get("phone", "")
            rows.append({
                "label": "شركة",
                "detail": name,
                "extra": f"مخلص: {broker} | هاتف: {phone}",
                "amount": ""
            })
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(count=len(rows))
        # رسم بسيط لعدد الشركات
        self._chart_series_cache = [(str(i+1), td.safe_float(r.get("amount", 0)) if r.get("amount","")!="" else 1.0) for i, r in enumerate(rows[:10])]
        self._chart_kind = "bar"
        high_val = max([td.safe_float(r.get("amount", 0)) if r.get("amount","")!="" else 1.0 for r in rows], default=1.0)
        if high_val == 0:
            high_val = 1.0
        self._chart_series_cache = [(str(i+1), high_val) for i in range(min(len(rows), 10))]
        self._donut_cache = [("عدد الشركات", float(len(rows)))]

    def _report_holidays(self, driver, d_from, d_to, car_no=""):
        self._set_report_columns(
            {"label": "البيان", "detail": "التفاصيل", "extra": "التاريخ / السيارة", "amount": "إيراد العطلة (د.ك)"},
            {"label": 140, "detail": 280, "extra": 220, "amount": 150})
        rows, totals = [], []
        for trip in td.load_trips():
            trip_date = str(trip.get("date", ""))
            holiday = td.safe_float(trip.get("holiday_price"))
            if not holiday or (d_from and trip_date < d_from) or (d_to and trip_date > d_to):
                continue
            if driver and str(trip.get("driver", "")) != driver:
                continue
            if car_no and str(trip.get("car_no", "")) != car_no:
                continue
            rows.append({
                "label": "عطلة",
                "detail": f"{trip.get('driver', '')} | {trip.get('customer', '')}",
                "extra": f"{trip_date} | سيارة {trip.get('car_no', '')}",
                "amount": f"{holiday:.3f}",
            })
            totals.append(holiday)
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(len(rows), sum(totals), sum(totals) / len(totals) if totals else 0)
        # رسم دوري إيراد العطل حسب النوع
        category_totals = {}
        for trip in td.load_trips():
            holiday = td.safe_float(trip.get("holiday_price"))
            if not holiday:
                continue
            trip_date = str(trip.get("date", ""))
            if d_from and trip_date < d_from:
                continue
            if d_to and trip_date > d_to:
                continue
            cat = str(trip.get("trip_category", "")).strip() or "عطلة عامة"
            category_totals[cat] = category_totals.get(cat, 0.0) + holiday
        if category_totals:
            self._chart_series_cache = sorted(category_totals.items(), key=lambda kv: -kv[1])[:8]
            self._chart_kind = "bar"
        self._donut_cache = list(category_totals.items())[:6]
        if not category_totals:
            self._donut_cache = [("إجمالي إيراد العطل", float(sum(totals)))]

    def _report_driver_performance(self, driver, d_from, d_to, status=""):
        self._set_report_columns(
            {"label": "السائق", "detail": "عدد الرحلات", "extra": "إيراد الرحلات + العطل", "amount": "أجرة السائق (د.ك)"},
            {"label": 160, "detail": 140, "extra": 220, "amount": 160})
        grouped = {}
        for trip in td.load_trips():
            trip_date = str(trip.get("date", ""))
            name = str(trip.get("driver", "")).strip()
            if not name or (driver and name != driver) or (d_from and trip_date < d_from) or (d_to and trip_date > d_to):
                continue
            item = grouped.setdefault(name, {"count": 0, "revenue": 0.0, "wages": 0.0})
            item["count"] += 1
            item["revenue"] += td.safe_float(trip.get("fee")) + td.safe_float(trip.get("holiday_price"))
            item["wages"] += td.safe_float(trip.get("driver_wage"))
        rows = [{
            "label": name,
            "detail": f"{item['count']} رحلة",
            "extra": f"{item['revenue']:.3f} د.ك",
            "amount": f"{item['wages']:.3f}",
        } for name, item in sorted(grouped.items())]
        totals = [td.safe_float(row["amount"]) for row in rows]
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(len(rows), sum(totals), sum(totals) / len(totals) if totals else 0)
        self._chart_series_cache = [(r["label"], td.safe_float(r["amount"])) for r in rows[:10]]
        self._chart_kind = "bar"
        self._donut_cache = [(r["label"], td.safe_float(r["amount"])) for r in rows[:6]]

    def _report_all(self, entity, d_from, d_to, status=""):
        """Unified operational report covering every dated record type."""
        fields = {"type": "السجل", "date": "التاريخ", "detail": "التفاصيل", "amount": "المبلغ (د.ك)"}
        rows = []

        def add(kind, record, detail, amount=0.0):
            record_date = str(record.get("date") or record.get("month") or "")
            if d_from and record_date < d_from:
                return
            if d_to and record_date > d_to:
                return
            text = " ".join(str(value or "") for value in record.values())
            if entity and entity not in text:
                return
            rows.append({"type": kind, "date": record_date, "detail": detail,
                         "amount": f"{td.safe_float(amount):.3f}"})

        for row in td.load_trips():
            add("رحلة", row, f"{row.get('driver', '')} | {row.get('car_no', '')} | {row.get('customer', '')}",
                td.safe_float(row.get("fee")) + td.safe_float(row.get("holiday_price")))
        for row in td.load_daily_expenses():
            add("مصروف", row, f"{row.get('category', '')} | {row.get('car_no', '')} | {row.get('driver', '')}",
                row.get("amount"))
        for row in td.load_maintenance():
            add("صيانة", row, f"{row.get('car_no', '')} | {row.get('type', '')}", row.get("cost"))
        for row in td.load_invoices():
            add("فاتورة", row, f"{row.get('invoice_no', '')} | {row.get('customer', '')}", row.get("total"))
        for row in td.load_payments():
            add("دفعة", row, f"{row.get('customer', '')} | {row.get('reference', '')}", row.get("amount"))
        for row in td.load_services():
            add("خدمة", row, f"{row.get('service_type', '')} | {row.get('customer', '')}", row.get("total"))
        for row in td.load_salaries():
            add("راتب", row, f"{row.get('driver', '')} | {row.get('salary_type', '')}", row.get("net_salary"))

        rows.sort(key=lambda row: (row["date"], row["type"]))
        self._set_report_columns(fields, {"type": 100, "date": 110, "detail": 360, "amount": 140})
        self._report_fields_cache = list(fields.items())
        self._report_rows_cache = rows
        self._insert_report_rows(rows, list(fields))
        amounts = [td.safe_float(row["amount"]) for row in rows]
        self._update_summary(count=len(rows), total=sum(amounts), avg=sum(amounts) / len(amounts) if amounts else 0)
        # رسم عام للتقارير الشاملة: توزيع حسب نوع السجل
        type_totals = {}
        for row in rows:
            t = str(row.get("type", "")).strip() or "سجل"
            type_totals[t] = type_totals.get(t, 0.0) + td.safe_float(row.get("amount", 0))
        if type_totals:
            self._chart_series_cache = sorted(type_totals.items(), key=lambda kv: -kv[1])[:8]
            self._chart_kind = "bar"
        self._donut_cache = list(type_totals.items())[:6]

    def _report_actions(self, entity, d_from, d_to, status=""):
        """سجل العمليات: يعرض ما جرى في النظام مع تجميعه حسب نوع الإجراء."""
        self._set_report_columns(
            {"label": "الإجراء", "detail": "المستخدم", "extra": "التاريخ",
             "amount": "التفاصيل"},
            {"label": 160, "detail": 140, "extra": 140, "amount": 300})
        rows, action_totals = [], {}
        try:
            logs = td.load_audit_logs() if hasattr(td, "load_audit_logs") else []
        except Exception as exc:
            log_exception("سجل العمليات", exc)
            logs = []
        for log in logs:
            log_date = str(log.get("created_at", "") or log.get("date", ""))
            if d_from and log_date < d_from:
                continue
            if d_to and log_date > d_to:
                continue
            action = str(log.get("action", "") or "إجراء")
            text = " ".join(str(value or "") for value in log.values())
            if entity and entity not in text:
                continue
            rows.append({"label": action,
                         "detail": str(log.get("user", "") or log.get("username", "") or "—"),
                         "extra": log_date,
                         "amount": str(log.get("details", "") or log.get("notes", ""))})
            action_totals[action] = action_totals.get(action, 0.0) + 1.0
        rows.sort(key=lambda row: (row["extra"], row["label"]))
        self._chart_series_cache = sorted(action_totals.items(), key=lambda kv: -kv[1])[:8]
        self._chart_kind = "bar"
        self._donut_cache = list(action_totals.items())[:6]
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(len(rows), len(rows), 1.0)

    def _report_partner_distribution(self, car_no, d_from, d_to, status=""):
        """Show net vehicle profit after driver salary and partner allocations."""
        self._set_report_columns(
            {"car": "السيارة", "partner": "الشريك", "pct": "النسبة %",
             "detail": "الإيراد - المصاريف - راتب السائق", "amount": "النصيب (د.ك)"},
            {"car": 110, "partner": 170, "pct": 90, "detail": 280, "amount": 130})
        vehicles = [v.get("car_no", "") for v in td.load_vehicles() if v.get("car_no")]
        if car_no:
            vehicles = [car_no]
        rows, totals = [], []
        for car in vehicles:
            salary_total = sum(
                td.safe_float(salary.get("net_salary"))
                for salary in td.load_salaries()
                if str(salary.get("car_no", "")).strip() == str(car).strip()
                and (not d_from or str(salary.get("month", "")) >= d_from[:7])
                and (not d_to or str(salary.get("month", "")) <= d_to[:7])
            )
            result = td.vehicle_profit_distribution(car, d_from, d_to, salary_total)
            detail = (
                f"{result['revenue']:.3f} - {result['vehicle_expenses']:.3f}"
                f" - {result['driver_salary']:.3f} = {result['distributable']:.3f}"
            )
            allocated_pct = 0.0
            for partner in result["partners"]:
                amount = partner["amount"]
                allocated_pct += partner["ownership_pct"]
                rows.append({
                    "car": car, "partner": partner["partner"],
                    "pct": f"{partner['ownership_pct']:.3f}",
                    "detail": detail, "amount": f"{amount:.3f}",
                })
                totals.append(amount)
            remaining_pct = round(100.0 - allocated_pct, 3)
            if remaining_pct > 0 and result["distributable"]:
                rows.append({
                    "car": car, "partner": "المتبقي غير موزع / المالك",
                    "pct": f"{remaining_pct:.3f}",
                    "detail": detail,
                    "amount": f"{result['distributable'] * remaining_pct / 100.0:.3f}",
                })
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["car", "partner", "pct", "detail", "amount"])
        self._update_summary(len(rows), sum(totals), sum(totals) / len(totals) if totals else 0)
        self._chart_series_cache = [(r["partner"], td.safe_float(r["amount"])) for r in rows[:10]]
        self._chart_kind = "bar"
        self._donut_cache = [(r["partner"], td.safe_float(r["amount"])) for r in rows[:6]]

    def _report_fuel(self, car_no, d_from, d_to, status=""):
        """تقرير استهلاك الوقود حسب السيارة والفترة."""
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "amount": "المبلغ (د.ك)"},
                               {"label": 140, "detail": 320, "amount": 140})
        rows, totals = [], []
        fuel_total = {}
        for exp in td.load_daily_expenses():
            cat = str(exp.get("category", "")).strip()
            if "وقود" not in cat and "بنزين" not in cat and "fuel" not in cat.lower():
                continue
            d = str(exp.get("date", ""))
            if d_from and d < d_from:
                continue
            if d_to and d > d_to:
                continue
            car = str(exp.get("car_no", "")).strip()
            if car_no and car != car_no:
                continue
            amount = td.safe_float(exp.get("amount"))
            rows.append({"label": "وقود", "detail": f"{d} - {car} - {cat}", "amount": f"{amount:.3f}"})
            totals.append(amount)
            fuel_total[car] = fuel_total.get(car, 0.0) + amount
        self._chart_series_cache = sorted(fuel_total.items(), key=lambda kv: -kv[1])[:10]
        self._chart_kind = "bar"
        self._donut_cache = list(fuel_total.items())[:6]
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "amount"])
        self._update_summary(len(rows), sum(totals), sum(totals) / len(totals) if totals else 0)

    def _report_contracts(self, entity, d_from, d_to, status=""):
        """تقرير العقود المسجلة."""
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "extra": "معلومات إضافية", "amount": "المبلغ (د.ك)"},
                               {"label": 140, "detail": 260, "extra": 200, "amount": 120})
        rows = []
        totals = []
        for inv in td.load_invoices():
            if str(inv.get("contract_no", "")).strip():
                d = str(inv.get("date", ""))
                if d_from and d < d_from:
                    continue
                if d_to and d > d_to:
                    continue
                total = td.safe_float(inv.get("total"))
                rows.append({"label": "عقد", "detail": f"{inv.get('customer', '')}", "extra": f"رقم: {inv.get('contract_no', '')} | فاتورة: {inv.get('invoice_no', '')}", "amount": f"{total:.3f}"})
                totals.append(total)
        for c in td.load_customers():
            contract = str(c.get("contract_no", "")).strip()
            if contract and (not entity or str(c.get("name", "")) == entity):
                rows.append({"label": "عقد عميل", "detail": c.get("name", ""), "extra": f"رقم العقد: {contract}", "amount": ""})
        for c in td.load_companies():
            contract = str(c.get("contract_no", "")).strip()
            if contract and (not entity or str(c.get("name", "")) == entity):
                rows.append({"label": "عقد شركة", "detail": c.get("name", ""), "extra": f"رقم العقد: {contract}", "amount": ""})
        self._chart_series_cache = [(str(i+1), td.safe_float(r.get("amount", 0))) for i, r in enumerate(rows[:10])]
        self._chart_kind = "bar"
        self._donut_cache = [("عقود الفواتير", float(len([r for r in rows if r["label"] == "عقد"])))]
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(len(rows), sum(totals), sum(totals) / len(totals) if totals else 0)

    def _report_quotations(self, entity, d_from, d_to, status=""):
        """تقرير عروض الأسعار المسجلة."""
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "extra": "معلومات إضافية", "amount": "المبلغ (د.ك)"},
                               {"label": 140, "detail": 260, "extra": 200, "amount": 120})
        rows = []
        totals = []
        status_totals = {}
        for q in td.load_quotations():
            d = str(q.get("date", ""))
            if d_from and d < d_from:
                continue
            if d_to and d > d_to:
                continue
            if entity and str(q.get("customer", "")) != entity:
                continue
            total = td.safe_float(q.get("total"))
            q_status = str(q.get("status", "")).strip() or "معلق"
            if status and q_status != status:
                continue
            rows.append({"label": "عرض سعر", "detail": f"{q.get('customer', '')}", "extra": f"رقم: {q.get('quotation_no', '')} | الحالة: {q_status}", "amount": f"{total:.3f}"})
            totals.append(total)
            status_totals[q_status] = status_totals.get(q_status, 0.0) + total
        self._chart_series_cache = sorted(status_totals.items(), key=lambda kv: -kv[1])[:8]
        self._chart_kind = "bar"
        self._donut_cache = list(status_totals.items())[:6]
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(len(rows), sum(totals), sum(totals) / len(totals) if totals else 0)

    def _report_parts(self, car_no, d_from, d_to, status=""):
        """تقرير قطع الغيار المشتراة أو المثبتة."""
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "extra": "معلومات إضافية", "amount": "المبلغ (د.ك)"},
                               {"label": 140, "detail": 260, "extra": 200, "amount": 120})
        rows = []
        totals = []
        car_totals = {}
        for p in td.load_parts():
            d = str(p.get("date", ""))
            if d_from and d < d_from:
                continue
            if d_to and d > d_to:
                continue
            if car_no and str(p.get("car_no", "")) != car_no:
                continue
            cost = td.safe_float(p.get("cost"))
            rows.append({"label": "قطعة غيار", "detail": f"{p.get('part_name', '')}", "extra": f"سيارة: {p.get('car_no', '')} | مورد: {p.get('supplier', '')}", "amount": f"{cost:.3f}"})
            totals.append(cost)
            car = str(p.get("car_no", "")).strip() or "غير محدد"
            car_totals[car] = car_totals.get(car, 0.0) + cost
        self._chart_series_cache = sorted(car_totals.items(), key=lambda kv: -kv[1])[:8]
        self._chart_kind = "bar"
        self._donut_cache = list(car_totals.items())[:6]
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(len(rows), sum(totals), sum(totals) / len(totals) if totals else 0)

    def _report_maintenance_plans(self, car_no, d_from, d_to, status=""):
        """تقرير خطط الصيانة الوقائية والتنفيذ."""
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "extra": "معلومات إضافية", "amount": "المبلغ (د.ك)"},
                               {"label": 140, "detail": 260, "extra": 200, "amount": 120})
        rows = []
        totals = []
        type_totals = {}
        for p in td.load_maintenance_plans():
            if car_no and str(p.get("car_no", "")) != car_no:
                continue
            cost = td.safe_float(p.get("estimated_cost"))
            p_status = str(p.get("status", "")).strip() or "مجدول"
            if status and p_status != status:
                continue
            rows.append({"label": "خطة صيانة", "detail": f"{p.get('car_no', '')} - {p.get('task', '')}", "extra": f"التاريخ: {p.get('scheduled_date', '')} | الحالة: {p_status}", "amount": f"{cost:.3f}"})
            totals.append(cost)
            type_totals[p_status] = type_totals.get(p_status, 0.0) + cost
        self._chart_series_cache = sorted(type_totals.items(), key=lambda kv: -kv[1])[:8]
        self._chart_kind = "bar"
        self._donut_cache = list(type_totals.items())[:6]
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(len(rows), sum(totals), sum(totals) / len(totals) if totals else 0)

    def _report_customer_balances(self, entity, d_from, d_to, status=""):
        """أرصدة العملاء: إجمالي الفواتير - المدفوعات."""
        self._set_report_columns({"label": "العميل", "detail": "إجمالي الفواتير", "extra": "المدفوعات", "amount": "الرصيد المستحق (د.ك)"},
                               {"label": 180, "detail": 140, "extra": 140, "amount": 160})
        rows = []
        totals = []
        for customer in td.load_customers():
            name = customer.get("name", "").strip()
            if not name:
                continue
            if entity and name != entity:
                continue
            cust_invoices = td.safe_float(customer.get("total_invoices", 0))
            cust_payments = td.safe_float(customer.get("total_payments", 0))
            balance = cust_invoices - cust_payments
            rows.append({"label": name, "detail": f"{cust_invoices:.3f}", "extra": f"{cust_payments:.3f}", "amount": f"{balance:.3f}"})
            totals.append(balance)
        self._chart_series_cache = sorted([(r["label"][:16], td.safe_float(r["amount"])) for r in rows if abs(td.safe_float(r["amount"])) > 0], key=lambda kv: -abs(kv[1]))[:10]
        self._chart_kind = "bar"
        self._donut_cache = [("مستحق", sum(max(t, 0) for t in totals)), ("دائن", sum(abs(min(t, 0)) for t in totals))]
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(len(rows), sum(totals), sum(totals) / len(totals) if totals else 0)

    def _report_receivables_aging(self, entity, d_from, d_to, status=""):
        """أعمار الذمم: تصنيف أرصدة العملاء حسب تاريخ آخر فاتورة."""
        self._set_report_columns({"label": "العميل", "detail": "الرصيد", "extra": "آخر فاتورة", "amount": "التصنيف"},
                               {"label": 200, "detail": 140, "extra": 180, "amount": 140})
        rows = []
        today = date.today()
        aging_buckets = {"خلال 30 يوم": 0.0, "31-60 يوم": 0.0, "61-90 يوم": 0.0, "أكثر من 90": 0.0}
        for customer in td.load_customers():
            name = customer.get("name", "").strip()
            if not name:
                continue
            if entity and name != entity:
                continue
            cust_invoices = td.safe_float(customer.get("total_invoices", 0))
            cust_payments = td.safe_float(customer.get("total_payments", 0))
            balance = cust_invoices - cust_payments
            if balance <= 0:
                continue
            last_invoice_date = str(customer.get("last_invoice_date", "")).strip()
            try:
                days = (today - date.fromisoformat(last_invoice_date)).days if last_invoice_date else 999
            except ValueError:
                days = 999
            if days <= 30:
                bucket = "خلال 30 يوم"
            elif days <= 60:
                bucket = "31-60 يوم"
            elif days <= 90:
                bucket = "61-90 يوم"
            else:
                bucket = "أكثر من 90"
            aging_buckets[bucket] = aging_buckets.get(bucket, 0.0) + balance
            rows.append({"label": name, "detail": f"{balance:.3f}", "extra": last_invoice_date or "—", "amount": bucket})
        self._chart_series_cache = [(k, v) for k, v in aging_buckets.items() if v > 0]
        self._chart_kind = "bar"
        self._donut_cache = [(k, v) for k, v in aging_buckets.items() if v > 0]
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(len(rows), sum(aging_buckets.values()), sum(aging_buckets.values()) / len(rows) if rows else 0)

    def _report_spare_parts(self, entity, d_from, d_to, status=""):
        """تقرير قطع الغيار: حركة صيانة وقطع غير مستخدمة."""
        self._set_report_columns({"label": "البيان", "detail": "التفاصيل", "extra": "المصدر / التاريخ", "amount": "التكلفة (د.ك)"},
                                 {"label": 140, "detail": 260, "extra": 200, "amount": 120})
        rows = []
        totals = []
        part_totals = {}
        for m in td.load_maintenance():
            mdate = str(m.get("date", ""))
            if d_from and mdate < d_from: continue
            if d_to and mdate > d_to: continue
            parts = m.get("parts", "")
            if isinstance(parts, str):
                try: parts = json.loads(parts)
                except (json.JSONDecodeError, TypeError): parts = []
            if not isinstance(parts, list):
                parts = [parts]
            for part in parts:
                if isinstance(part, dict):
                    pname = str(part.get("name", "")).strip()
                    pquantity = td.safe_float(part.get("quantity"))
                    pprice = td.safe_float(part.get("price"))
                else:
                    pname = str(part).strip()
                    pquantity = 1.0
                    pprice = 0.0
                if not pname:
                    continue
                if status and status not in pname:
                    continue
                cost = pquantity * pprice
                rows.append({"label": "قطعة غيار", "detail": pname, "extra": f"{mdate} - سيارة {m.get('car_no', '')}", "amount": f"{cost:.3f}"})
                totals.append(cost)
                part_totals[pname[:24]] = part_totals.get(pname[:24], 0.0) + cost
        self._chart_series_cache = sorted(part_totals.items(), key=lambda kv: -kv[1])[:8]
        self._chart_kind = "bar"
        self._donut_cache = sorted(part_totals.items(), key=lambda kv: -kv[1])[:6]
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(count=len(rows), total=sum(totals), avg=sum(totals) / len(totals) if totals else 0,
                             kpis=[("قطع مستخدمة", str(len(totals)), COLOR_PRIMARY_LIGHT), ("إجمالي التكاليف", f"{sum(totals):,.3f} د.ك", COLOR_DANGER)])

    def _report_price_quotes(self, entity, d_from, d_to, status=""):
        """تقرير عروض الأسعار: قوائم الأسعار المسجلة."""
        self._set_report_columns({"label": "البيان", "detail": "العنوان / البنود", "extra": "العميل/التاريخ", "amount": "القيمة (د.ك)"},
                                 {"label": 140, "detail": 280, "extra": 180, "amount": 100})
        rows = []
        totals = []
        month_totals = {}
        for pq in td.load_quotations():
            pq_date = str(pq.get("date", ""))[:10]
            month_key = pq_date[:7]
            cust = str(pq.get("customer", "")).strip()
            if entity and entity != cust:
                continue
            total = td.safe_float(pq.get("amount"))
            quot_no = str(pq.get("quotation_no", "")).strip() or str(pq.get("id", ""))
            rows.append({"label": "عرض سعر", "detail": f"{quot_no} - {str(pq.get('description', ''))[:35]}", "extra": f"{pq_date} | {cust}", "amount": f"{total:.3f}"})
            totals.append(total)
            if month_key:
                month_totals[month_key] = month_totals.get(month_key, 0.0) + total
        self._chart_series_cache = [(k, month_totals[k]) for k in sorted(month_totals)[-12:]]
        self._chart_kind = "bar"
        self._donut_cache = [("مجموع عروض الأسعار", sum(totals))]
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(count=len(rows), total=sum(totals), avg=sum(totals) / len(totals) if totals else 0,
                             kpis=[("عدد العروض", str(len(rows)), COLOR_PRIMARY_LIGHT), ("إجمالي القيمة", f"{sum(totals):,.3f} د.ك", COLOR_ACCENT)])

    def _report_monthly_profit(self, entity, d_from, d_to, status=""):
        """الأرباح الشهرية: ملخص الربح لكل شهر في الفترة المحددة."""
        self._set_report_columns({"label": "الشهر", "detail": "الإيرادات", "extra": "المصروفات", "amount": "صافي الربح (د.ك)"},
                               {"label": 140, "detail": 140, "extra": 140, "amount": 160})
        rows = []
        totals = []
        all_months = set()
        for inv in td.load_invoices():
            m = str(inv.get("date", ""))[:7]
            if m:
                all_months.add(m)
        for exp in td.load_maintenance():
            m = str(exp.get("date", ""))[:7]
            if m:
                all_months.add(m)
        for salary in td.load_salaries():
            m = str(salary.get("month", "")).strip() or str(salary.get("date", ""))[:7]
            if m:
                all_months.add(m)
        for month in sorted(all_months):
            if d_from and month < d_from[:7]:
                continue
            if d_to and month > d_to[:7]:
                continue
            rev = 0.0
            for inv in td.load_invoices():
                if str(inv.get("date", ""))[:7] == month:
                    rev += td.safe_float(inv.get("total"))
            exp = 0.0
            for m in td.load_maintenance():
                if str(m.get("date", ""))[:7] == month:
                    exp += td.safe_float(m.get("cost"))
            for s in td.load_salaries():
                sm = str(s.get("month", "")).strip() or str(s.get("date", ""))[:7]
                if sm == month:
                    exp += td.safe_float(s.get("net_salary"))
            net = rev - exp
            rows.append({"label": month, "detail": f"{rev:.3f}", "extra": f"{exp:.3f}", "amount": f"{net:.3f}"})
            totals.append(net)
        self._chart_series_cache = [(r["label"], td.safe_float(r["amount"])) for r in rows[:12]]
        self._chart_kind = "line" if len(rows) > 6 else "bar"
        self._donut_cache = [("إجمالي الأرباح", sum(max(t, 0) for t in totals)), ("إجمالي الخسائر", abs(sum(min(t, 0) for t in totals)))]
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(len(rows), sum(totals), sum(totals) / len(totals) if totals else 0)

    def _report_vehicle_utilization(self, car_no, d_from, d_to, status=""):
        """كفاءة السيارات: عدد الرحلات والإيرادات والمصاريف لكل سيارة."""
        self._set_report_columns(
            {"label": "السيارة", "detail": "عدد الرحلات", "extra": "المصاريف", "amount": "الإيرادات (د.ك)"},
            {"label": 160, "detail": 120, "extra": 160, "amount": 160})
        rows = []
        totals = []
        car_trips = {}
        for trip in td.load_trips():
            trip_date = str(trip.get("date", ""))
            car = str(trip.get("car_no", "")).strip()
            if not car or (d_from and trip_date < d_from) or (d_to and trip_date > d_to):
                continue
            if car_no and car != car_no:
                continue
            if car not in car_trips:
                car_trips[car] = {"count": 0, "revenue": 0.0}
            car_trips[car]["count"] += 1
            car_trips[car]["revenue"] += td.safe_float(trip.get("fee")) + td.safe_float(trip.get("holiday_price"))
        car_expenses = {}
        for exp in td.load_daily_expenses():
            exp_date = str(exp.get("date", ""))
            car = str(exp.get("car_no", "")).strip()
            if not car or (d_from and exp_date < d_from) or (d_to and exp_date > d_to):
                continue
            if car_no and car != car_no:
                continue
            car_expenses[car] = car_expenses.get(car, 0.0) + td.safe_float(exp.get("amount"))
        for m in td.load_maintenance():
            m_date = str(m.get("date", ""))
            car = str(m.get("car_no", "")).strip()
            if not car or (d_from and m_date < d_from) or (d_to and m_date > d_to):
                continue
            if car_no and car != car_no:
                continue
            car_expenses[car] = car_expenses.get(car, 0.0) + td.safe_float(m.get("cost"))
        for car in sorted(car_trips):
            data = car_trips[car]
            exp = car_expenses.get(car, 0.0)
            rows.append({"label": car, "detail": f"{data['count']} رحلة",
                          "extra": f"{exp:,.3f} د.ك", "amount": f"{data['revenue']:,.3f}"})
            totals.append(data["revenue"])
        self._chart_series_cache = [(r["label"], td.safe_float(r["amount"])) for r in rows[:10]]
        self._chart_kind = "bar"
        self._donut_cache = sorted(car_expenses.items(), key=lambda kv: -kv[1])[:6]
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        self._update_summary(len(rows), sum(totals), sum(totals) / len(totals) if totals else 0)

    def _report_partner_profit(self, entity, d_from, d_to, status=""):
        """أرباح الشركاء: نصيب كل شريك من صافي إيراد كل سيارة."""
        result = td.partner_profit_report(d_from, d_to)
        self._set_report_columns(
            {"amount": "النصيب (د.ك)", "distributable": "صافي قابل للتوزيع",
             "driver_salary": "راتب السائق", "vehicle_expenses": "مصاريف السيارة",
             "revenue": "إجمالي الإيراد", "pct": "النسبة %",
             "car": "السيارة", "partner": "الشريك"},
            {"amount": 130, "distributable": 140, "driver_salary": 120,
             "vehicle_expenses": 120, "revenue": 130, "pct": 90, "car": 110, "partner": 150})
        rows = []
        for item in result["rows"]:
            if entity and entity not in (item["partner"], item["car_no"]):
                continue
            rows.append({
                "partner": item["partner"], "car": item["car_no"],
                "pct": f"{item['ownership_pct']:.3f}",
                "revenue": f"{item['revenue']:.3f}",
                "vehicle_expenses": f"{item['vehicle_expenses']:.3f}",
                "driver_salary": f"{item['driver_salary']:.3f}",
                "distributable": f"{item['distributable']:.3f}",
                "amount": f"{item['amount']:.3f}"})
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["partner", "car", "pct", "revenue", "vehicle_expenses",
                                        "driver_salary", "distributable", "amount"])
        self._chart_series_cache = [(item["partner"], item["amount"])
                                    for item in result["by_partner"][:8]]
        self._chart_kind = "bar"
        self._donut_cache = self._chart_series_cache[:6]
        self._update_summary(len(rows), result["total"],
                             result["total"] / len(result["by_partner"]) if result["by_partner"] else 0)

    def _report_partner_payments(self, entity, d_from, d_to, status=""):
        """دفعات الشركاء مع تمييز المشطوبة."""
        result = td.partner_payments_report(d_from, d_to)
        self._set_report_columns(
            {"amount": "المبلغ (د.ك)", "state": "الحالة", "car": "السيارة",
             "kind": "النوع", "partner": "الشريك", "label": "التاريخ", "notes": "ملاحظات"},
            {"amount": 120, "state": 90, "car": 110, "kind": 90, "partner": 150,
             "label": 120, "notes": 200})
        rows = []
        for item in result["rows"]:
            partner = safe_str(item.get("partner"))
            if entity and entity != partner:
                continue
            if status and safe_str(item.get("payment_type")) != status:
                continue
            rows.append({
                "label": safe_str(item.get("date")), "partner": partner,
                "car": safe_str(item.get("car_no")) or "—",
                "kind": safe_str(item.get("payment_type")),
                "amount": f"{td.safe_float(item.get('amount')):.3f}",
                "state": "مشطوبة" if td.is_voided(item) else "سليمة",
                "notes": safe_str(item.get("void_reason")) or safe_str(item.get("notes"))})
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "partner", "car", "kind", "amount", "state", "notes"])
        self._chart_series_cache = [(item["partner"], item["total"])
                                    for item in result["by_partner"][:8]]
        self._chart_kind = "bar"
        self._donut_cache = self._chart_series_cache[:6]
        self._update_summary(len(rows), result["total"],
                             result["total"] / len(rows) if rows else 0)

    def _report_driver_payments(self, entity, d_from, d_to, status=""):
        """دفعات السائقين مع تمييز المشطوبة."""
        result = td.driver_payments_report(d_from, d_to)
        self._set_report_columns(
            {"amount": "المبلغ (د.ك)", "state": "الحالة", "kind": "النوع",
             "driver_type": "نوع السائق", "car": "السيارة",
             "driver": "السائق", "label": "التاريخ"},
            {"amount": 120, "state": 90, "kind": 90, "driver_type": 110,
             "car": 110, "driver": 150, "label": 120})
        rows = []
        for item in result["rows"]:
            driver = safe_str(item.get("driver"))
            if entity and entity != driver:
                continue
            if status and safe_str(item.get("payment_type")) != status:
                continue
            rows.append({
                "label": safe_str(item.get("date")), "driver": driver,
                "driver_type": safe_str(item.get("driver_type")) or "—",
                "car": safe_str(item.get("car_no")) or "—",
                "kind": safe_str(item.get("payment_type")),
                "amount": f"{td.safe_float(item.get('amount')):.3f}",
                "state": "مشطوبة" if td.is_voided(item) else "سليمة"})
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "driver", "driver_type", "car", "kind",
                                        "amount", "state"])
        self._chart_series_cache = [(item["driver"], item["total"])
                                    for item in result["by_driver"][:8]]
        self._chart_kind = "bar"
        self._donut_cache = self._chart_series_cache[:6]
        self._update_summary(len(rows), result["total"],
                             result["total"] / len(rows) if rows else 0)

    def _report_partner_matrix(self, entity, d_from, d_to, status=""):
        """مصفوفة نسب الشركاء وحالة اكتمال توزيع كل سيارة."""
        matrix = td.partner_share_matrix(entity)
        self._set_report_columns(
            {"status": "حالة التوزيع", "total": "مجموع السيارة %", "locked": "مثبّتة",
             "end": "إلى تاريخ", "start": "من تاريخ", "pct": "النسبة %",
             "partner": "الشريك", "car": "السيارة"},
            {"status": 150, "total": 130, "locked": 80, "end": 110, "start": 110,
             "pct": 90, "partner": 160, "car": 110})
        rows = []
        for group in matrix:
            for share in group["partners"]:
                rows.append({
                    "car": group["car_no"], "partner": share["partner"],
                    "pct": f"{share['ownership_pct']:.3f}",
                    "locked": "نعم" if share["locked"] else "لا",
                    "start": share["start_date"], "end": share["end_date"] or "مفتوحة",
                    "total": f"{group['total_pct']:.3f}",
                    "status": "مكتمل 100%" if group["complete"]
                    else f"ناقص ({100 - group['total_pct']:.3f}%)"})
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["car", "partner", "pct", "locked", "start",
                                        "end", "total", "status"])
        self._chart_series_cache = [(group["car_no"], group["total_pct"])
                                    for group in matrix][:8]
        self._chart_kind = "bar"
        incomplete = sum(1 for group in matrix if not group["complete"])
        self._update_summary(len(rows), sum(g["total_pct"] for g in matrix),
                             100.0 - (incomplete * 100.0 / len(matrix)) if matrix else 0)

    def _report_audit_log(self, entity, d_from, d_to, status=""):
        """سجل العمليات: عرض جميع العمليات المسجلة في النظام."""
        self._set_report_columns(
            {"label": "التاريخ", "detail": "المستخدم", "extra": "الإجراء", "amount": "التفاصيل"},
            {"label": 140, "detail": 140, "extra": 160, "amount": 280})
        rows = []
        totals = []
        try:
            if hasattr(td, "load_audit_logs"):
                logs = td.load_audit_logs()
            else:
                logs = []
            for log in logs:
                log_date = str(log.get("created_at", "") or log.get("date", ""))
                if d_from and log_date < d_from:
                    continue
                if d_to and log_date > d_to:
                    continue
                user = safe_str(log.get("user", "") or log.get("username", ""))
                action = safe_str(log.get("action", "") or log.get("operation", ""))
                detail = safe_str(log.get("detail", "") or log.get("description", ""))
                amount_val = safe_str(log.get("amount", ""))
                if entity:
                    combined = f"{user} {action} {detail} {amount_val}"
                    if entity not in combined:
                        continue
                rows.append({"label": log_date[:19], "detail": user, "extra": action, "amount": detail or amount_val})
        except Exception:
            rows.append({"label": "—", "detail": "", "extra": "غير متاح", "amount": "سجل العمليات غير مفعل"})
        self._report_rows_cache = rows
        self._insert_report_rows(rows, ["label", "detail", "extra", "amount"])
        action_counts = {}
        for row in rows:
            action = row.get("extra", "")
            if action:
                action_counts[action] = action_counts.get(action, 0) + 1
        self._update_summary(len(rows), 0, 0)
        self._chart_series_cache = sorted(action_counts.items(), key=lambda kv: -kv[1])[:8]
        self._chart_kind = "bar"
        self._donut_cache = list(action_counts.items())[:6]

    def _save_profit_snapshot(self):
        month = (self.rep_from.get().strip() or date.today().isoformat())[:7]
        start = f"{month}-01"
        end = self.rep_to.get().strip() or date.today().isoformat()
        vehicles = [v.get("car_no", "") for v in td.load_vehicles() if v.get("car_no")]
        if self.rep_entity_var.get().strip():
            vehicles = [self.rep_entity_var.get().strip()]
        distributions = []
        for car in vehicles:
            salary_total = sum(
                td.safe_float(salary.get("net_salary"))
                for salary in td.load_salaries()
                if str(salary.get("car_no", "")).strip() == str(car).strip()
                and start[:7] <= str(salary.get("month", ""))[:7] <= end[:7]
            )
            result = td.vehicle_profit_distribution(car, start, end, salary_total)
            result["car_no"] = car
            result["snapshot_month"] = month
            distributions.append(result)
        try:
            td.save_profit_snapshots(month, distributions)
        except Exception as exc:
            messagebox.showerror("اللقطة الشهرية", str(exc), parent=self)
            return
        messagebox.showinfo("تم", f"تم حفظ لقطة توزيع الأرباح لشهر {month}.", parent=self)

    def _save_current_report_as_screenshot(self):
        return self._save_report_screenshot()

    def _print_current_report(self):
        title = f"تقرير {self.rep_type_var.get()}"
        if self.rep_entity_var.get().strip():
            title += f" - {self.rep_entity_var.get().strip()}"
        if self.rep_status_var.get().strip():
            title += f" ({self.rep_status_var.get().strip()})"
        generate_and_open_summary_print(title, self._report_fields_cache, self._report_rows_cache)

    def _export_current_report_csv(self):
        """Export the currently filtered report using UTF-8 with an Excel BOM."""
        if not self._report_fields_cache:
            messagebox.showinfo("التقارير", "شغّل التقرير أولاً قبل التصدير.", parent=self)
            return
        default_name = f"تقرير_{self.rep_type_var.get()}_{date.today().isoformat()}.csv"
        path = filedialog.asksaveasfilename(
            parent=self,
            title="حفظ التقرير",
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSV UTF-8", "*.csv"), ("كل الملفات", "*.*")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8-sig", newline="") as output:
            writer = csv.writer(output)
            writer.writerow([label for _key, label in self._report_fields_cache])
            writer.writerows(
                [safe_str(row.get(key, "")) for key, _label in self._report_fields_cache]
                for row in self._report_rows_cache
            )
        messagebox.showinfo("تم التصدير", f"تم حفظ التقرير في:\n{path}", parent=self)

    def _report_current_month(self):
        today = date.today()
        self.rep_from.set(today.replace(day=1).isoformat())
        self.rep_to.set(today.isoformat())
        self._run_current_report()

    def _report_all_dates(self):
        self.rep_from.set("")
        self.rep_to.set("")
        self._run_current_report()

    def show_financial_summary(self):
        d_from, d_to = self._parse_report_period()
        if d_from is None and d_to is None:
            return
        self.rep_type_var.set("تقرير مالي")
        self._run_current_report()

    def print_financial_summary(self):
        self._print_current_report()
