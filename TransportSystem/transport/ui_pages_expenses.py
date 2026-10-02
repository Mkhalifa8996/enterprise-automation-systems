# -*- coding: utf-8 -*-
"""شاشة المصروفات اليومية."""

import html, os, tempfile, webbrowser
from datetime import date
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk
from . import data as td
from .app_config import COLOR_BG, COLOR_CARD, COLOR_MUTED, F_BODY, F_LABEL
from .ui_crud_tab import CrudTab
from .print_letterhead import LETTERHEAD_PRINT_STYLE
from .print_invoice import _REFERENCE_INVOICE_STYLE
from .print_theme import apply_a4_print_layout
from .ui_dialogs import date_input
from .ui_widgets import make_btn
from .ui_text_edit import refresh_related_screens
from .ui_helpers import safe_str


class DailyExpenseTab(CrudTab):
    """تبويب مصروفات مخصص لجهة واحدة: سيارة أو سائق."""

    def __init__(self, parent, owner, title, fields, categories, category_groups=None,
                 show_edit_button=True, show_upload_button=True, print_mode="default",
                 multiselect=False, single_row_form=True, actions_on_own_row=False):
        self.owner = owner
        self.categories = categories
        self.date_from_var = tk.StringVar()
        self.date_to_var = tk.StringVar()
        self.driver_filter_var = tk.StringVar(value="الكل")
        self.car_filter_var = tk.StringVar(value="الكل")
        self.type_filter_var = tk.StringVar(value="الكل")
        super().__init__(parent, fields, self._load_owned_rows, td.save_daily_expense,
                         td.delete_daily_expense, "id", title,
                         select_fields={"driver_type": [""] + list(td.DRIVER_TYPES),
                                        "driver": td.driver_names_by_type(),
                                        "car_no": [v["car_no"] for v in td.load_vehicles()
                                                   if v.get("car_no")],
                                        "category": categories},
                         readonly_fields=["id"],
                         attachment_fields=[("files", "ملفات")],
                         attachment_entity_type="daily_expenses",
                         show_edit_button=show_edit_button,
                         show_upload_button=show_upload_button,
                         print_mode=print_mode,
                         multiselect=multiselect,
                         single_row=single_row_form,
                         hide_fields=["id"],
                         narrow_fields=(),
                         narrow_widths={},
                         attachment_inline=True,
                         attachment_inline_after="description",
                         stretch_fields=True,
                         actions_on_own_row=actions_on_own_row)
        self.vars["date"].set(date.today().isoformat())
        if category_groups:
            self._add_category_group_buttons(category_groups)

    def _build_extra_filters(self, parent):
        """Build date/driver/vehicle filters for the daily-expense register."""
        # كل الفلاتر في نفس صف البحث/الأزرار — مضغوطة لتناسب صفاً واحداً.
        tk.Label(parent, text="من", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(4, 2))
        date_input(parent, self.date_from_var, width=8, shrink=True, ipady=3).pack(side="right", padx=1)
        tk.Label(parent, text="إلى", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(4, 2))
        date_input(parent, self.date_to_var, width=8, shrink=True, ipady=3).pack(side="right", padx=1)

        tk.Label(parent, text="نوع السائق", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(4, 2))
        type_combo = ttk.Combobox(parent, textvariable=self.type_filter_var,
                                  values=["الكل"] + list(td.DRIVER_TYPES),
                                  state="readonly", width=7,
                                  font=F_BODY, justify="right")
        type_combo.pack(side="right", padx=1)
        type_combo.bind("<<ComboboxSelected>>", self._on_filter_type_selected)
        self.type_filter_combo = type_combo

        tk.Label(parent, text="السائق", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(4, 2))
        driver_combo = ttk.Combobox(parent, textvariable=self.driver_filter_var,
                                    values=["الكل"] + td.driver_names_by_type(),
                                    state="readonly", width=8,
                                    font=F_BODY, justify="right")
        driver_combo.pack(side="right", padx=1)
        driver_combo.bind("<<ComboboxSelected>>", self._on_filter_driver_selected)

        tk.Label(parent, text="السيارة", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(4, 2))
        car_combo = ttk.Combobox(parent, textvariable=self.car_filter_var,
                                 values=["الكل"] + [v["car_no"] for v in td.load_vehicles()
                                                   if v.get("car_no")],
                                 state="readonly", width=8,
                                 font=F_BODY, justify="right")
        car_combo.pack(side="right", padx=1)
        car_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        self.driver_filter_combo = driver_combo
        self.car_filter_combo = car_combo

        make_btn(parent, "مسح الفلاتر", self.clear_filters, variant="secondary", padx=4, pady=2).pack(
            side="right", padx=1)

        self.date_from_var.trace_add("write", lambda *_: self.refresh())
        self.date_to_var.trace_add("write", lambda *_: self.refresh())

    def clear_filters(self):
        self.date_from_var.set("")
        self.date_to_var.set("")
        self.type_filter_var.set("الكل")
        self.driver_filter_var.set("الكل")
        self.car_filter_var.set("الكل")
        self.refresh()

    def _on_filter_type_selected(self, _event=None):
        """يصفّي قائمة السائقين بالنوع، ثم يقيّد السيارات بسيارة السائق."""
        kind = self.type_filter_var.get().strip()
        names = td.driver_names_by_type("" if kind == "الكل" else kind)
        current = self.driver_filter_var.get().strip()
        self.driver_filter_combo.config(values=["الكل"] + names)
        if current == "الكل" or current in names:
            self.driver_filter_var.set(current)
        else:
            self.driver_filter_var.set("الكل")
        self._on_filter_driver_selected()

    def _on_filter_driver_selected(self, _event=None):
        """Use the selected driver's vehicle as a convenient default filter."""
        driver = self.driver_filter_var.get().strip()
        if driver == "الكل":
            self.car_filter_combo.config(
                values=["الكل"] + [v["car_no"] for v in td.load_vehicles()
                                   if v.get("car_no")])
            self.car_filter_var.set("الكل")
        else:
            # السيارات المقصورة على السائق المختار: كانت تقبل كل السيارات
            # فتُعرض مصاريف سيارة أخرى ضمن مصاريفه.
            cars = td.cars_for_driver(driver)
            self.car_filter_combo.config(values=["الكل"] + cars)
            if cars:
                self.car_filter_var.set(cars[0])
            else:
                self.car_filter_var.set("الكل")
        self.refresh()

    def _on_link_selection(self, _event=None):
        """Suggest the master record's linked counterpart while allowing edits."""
        if self.owner == "سيارة":
            car_no = self.vars.get("car_no", tk.StringVar()).get().strip()
            vehicle = next((v for v in td.load_vehicles()
                            if safe_str(v.get("car_no")).strip() == car_no), None)
            if vehicle and "driver" in self.vars:
                self.vars["driver"].set(safe_str(vehicle.get("driver", "")))
        else:
            driver = self.vars.get("driver", tk.StringVar()).get().strip()
            driver_row = next((d for d in td.load_drivers()
                               if safe_str(d.get("name")).strip() == driver), None)
            if driver_row and "car_no" in self.vars:
                self.vars["car_no"].set(safe_str(driver_row.get("car_no", "")))

    def _add_category_group_buttons(self, category_groups):
        bar = tk.Frame(self.frame, bg=COLOR_BG)
        children = self.frame.winfo_children()
        bar.pack(fill="x", padx=18, pady=(14, 0), before=children[0] if children else None)
        tk.Label(bar, text="تصنيف سريع للمصروف", font=F_LABEL, bg=COLOR_BG,
                 fg=COLOR_MUTED).pack(side="right", padx=(0, 8))
        for group_name, options in category_groups.items():
            make_btn(bar, group_name,
                     lambda values=options: self._select_category_group(values),
                     variant="secondary").pack(side="right", padx=3)

    def _select_category_group(self, options):
        combo = self.combos.get("category")
        if combo:
            combo.config(values=options)
        self.vars["category"].set(options[0] if options else "")

    def _load_owned_rows(self):
        rows = [row for row in td.load_daily_expenses() if td.daily_expense_owner(row) == self.owner]
        start = self.date_from_var.get().strip()
        end = self.date_to_var.get().strip()
        driver = self.driver_filter_var.get().strip()
        car_no = self.car_filter_var.get().strip()
        kind = self.type_filter_var.get().strip()
        if driver == "الكل":
            driver = ""
        if car_no == "الكل":
            car_no = ""
        if kind == "الكل":
            kind = ""
        return [row for row in rows
                if (not start or safe_str(row.get("date")) >= start)
                and (not end or safe_str(row.get("date")) <= end)
                and (not kind or td.daily_expense_driver_type(row) == kind)
                and (not driver or safe_str(row.get("driver")).strip() == driver)
                and (not car_no or safe_str(row.get("car_no")).strip() == car_no)]

    # ---------------- الطباعة ----------------
    def _filtered_daily_expenses(self):
        """كل المصاريف اليومية المطابقة للفلاتر، مقسومة بين السيارة والسائق.

        كان الطباعة من أي تبويب تعرض جهة واحدة فقط، فيضطر المستخدم لطباعة
        كشفين ومزجهما. هنا نطبع كشفاً واحداً مقسماً إلى قسمين.
        """
        start = self.date_from_var.get().strip()
        end = self.date_to_var.get().strip()
        driver = self.driver_filter_var.get().strip()
        car_no = self.car_filter_var.get().strip()
        kind = self.type_filter_var.get().strip()
        if driver == "الكل":
            driver = ""
        if car_no == "الكل":
            car_no = ""
        if kind == "الكل":
            kind = ""
        car_rows, driver_rows = [], []
        query = safe_str(getattr(self, "search_var", tk.StringVar()).get()).strip().lower()
        for row in td.load_daily_expenses():
            day = safe_str(row.get("date"))
            if start and day < start:
                continue
            if end and day > end:
                continue
            if query and query not in " ".join(
                    safe_str(row.get(k)) for k in
                    ("date", "car_no", "driver", "category", "description")).lower():
                continue
            if car_no and safe_str(row.get("car_no")).strip() != car_no:
                continue
            row_driver = safe_str(row.get("driver")).strip()
            if driver and row_driver != driver:
                continue
            if kind and td.daily_expense_driver_type(row) != kind:
                continue
            if not car_no and driver:
                # بلا تحديد سيارة، نقصر على سيارات السائق المختار.
                if safe_str(row.get("car_no")).strip() not in td.cars_for_driver(driver):
                    continue
            owner = td.daily_expense_owner(row)
            (car_rows if owner == "سيارة" else driver_rows).append(row)
        car_rows.sort(key=lambda r: (safe_str(r.get("date")), safe_str(r.get("car_no"))))
        driver_rows.sort(key=lambda r: (safe_str(r.get("date")), safe_str(r.get("driver"))))
        return car_rows, driver_rows

    @staticmethod
    def _expense_table_html(rows, columns, headers, empty_text):
        if not rows:
            return f"<p class='empty'>{html.escape(empty_text)}</p>"
        head = "".join(f"<th>{html.escape(headers.get(c, c))}</th>" for c in columns)
        body = "".join(
            "<tr>" + "".join(
                f"<td>{html.escape(safe_str(row.get(c, '')) or '—')}</td>"
                for c in columns) + "</tr>" for row in rows)
        total = round(sum(td.safe_float(r.get("amount")) for r in rows), 3)
        return (f"<table class='exp'><tr>{head}</tr>{body}"
                f"<tr class='total-row'><td colspan='{len(columns) - 1}'>"
                f"إجمالي {html.escape(empty_text)}</td>"
                f"<td>{total:.3f}</td></tr></table>")

    def print_expenses_split(self):
        """يطبع كشفاً واحداً للمصاريف مقسوماً: مصاريف السيارة ثم مصاريف السائق."""
        car_rows, driver_rows = self._filtered_daily_expenses()
        if not car_rows and not driver_rows:
            messagebox.showinfo("طباعة", "لا توجد مصاريف مطابقة للطباعة.",
                                parent=self.frame)
            return
        columns = ["date", "car_no", "driver", "category", "amount", "description"]
        car_headers = {"date": "التاريخ", "car_no": "السيارة", "driver": "السائق",
                       "category": "نوع المصروف", "amount": "المبلغ",
                       "description": "التفاصيل"}
        car_total = round(sum(td.safe_float(r.get("amount")) for r in car_rows), 3)
        driver_total = round(sum(td.safe_float(r.get("amount")) for r in driver_rows), 3)
        advance_total = round(
            sum(td.safe_float(r.get("driver_advance")) for r in driver_rows), 3)
        period = (f"الفترة: {self.date_from_var.get().strip() or 'البداية'} "
                  f"إلى {self.date_to_var.get().strip() or 'اليوم'}")
        report = f"""<!doctype html><html lang='ar' dir='rtl'>
<head><meta charset='utf-8'>
<style>{_REFERENCE_INVOICE_STYLE}{LETTERHEAD_PRINT_STYLE}
.exp{{width:100%;border-collapse:collapse;font-size:11px}}
.exp th{{background:#0F2B46;color:#fff;padding:6px;text-align:center}}
.exp td{{border:1px solid #D8E0E9;padding:5px;text-align:center}}
.total-row td{{font-weight:800;background:#FBF6EA}}
h3{{margin-top:22px;font-size:15px;color:#0F2B46}}
.empty{{color:#718096;font-size:12px}}
</style></head><body>
<h2>كشف المصاريف اليومية</h2>
<p>{html.escape(period)}</p>
<p>إجمالي مصاريف السيارات: {car_total:.3f} د.ك | إجمالي مصاريف السائقين: {driver_total:.3f} د.ك
 | السلف: {advance_total:.3f} د.ك</p>
<h3>أولاً: مصاريف السيارات ({len(car_rows)} بند)</h3>
{self._expense_table_html(car_rows, columns, car_headers, "مصاريف السيارات")}
<h3>ثانياً: مصاريف السائقين والسلف ({len(driver_rows)} بند)</h3>
{self._expense_table_html(driver_rows, columns, car_headers, "مصاريف السائقين")}
</body></html>"""
        path = os.path.join(tempfile.gettempdir(), "daily_expenses_split.html")
        with open(path, "w", encoding="utf-8") as file:
            file.write(apply_a4_print_layout(report))
        webbrowser.open("file:///" + path.replace("\\", "/"))

    def refresh(self):
        if hasattr(self, "combos"):
            # التحديث يعيد ملء القوائم بالكل، فيبطل التصفية بالنوع إن حدث بعد
            # اختيار المستخدم. لذلك نعيد تطبيق الفلاتر المختارة كما هي.
            kind = self.type_filter_var.get().strip()
            driver = self.driver_filter_var.get().strip()
            car_no = self.car_filter_var.get().strip()
            all_cars = [v.get("car_no", "") for v in td.load_vehicles()
                        if v.get("car_no")]
            all_drivers = [d.get("name", "") for d in td.load_drivers()
                           if d.get("name")]
            if "car_no" in self.combos:
                # حقول الإدخال تحترم السلسلة نفسها: نوع السائق يصفّي السائقين،
                # والسائق يصفّي السيارات. كان التحديث يعيدها للجميع فيبطل الربط.
                # نقرأ نوع النموذج في متغيّر منفصل: كان يُكتب فوق kind (نوع
                # الفلتر) فيعود فلتر النوع إلى «الكل» عند كل تحديث.
                type_var = self.vars.get("driver_type")
                form_kind = type_var.get().strip() if type_var is not None else ""
                names = td.driver_names_by_type("" if not form_kind else form_kind)
                self.combos["driver"].config(values=names)
                cur_driver = self.vars.get("driver")
                cur_name = cur_driver.get().strip() if cur_driver is not None else ""
                cars = all_cars if not cur_name else td.cars_for_driver(cur_name)
                self.combos["car_no"].config(values=cars)
            if "driver" in self.combos and "driver_type" not in self.vars:
                self.combos["driver"].config(values=all_drivers)
            if hasattr(self, "driver_filter_combo"):
                # قوائم الفلترة: تحترم النوع والسائق المختارين.
                names = td.driver_names_by_type("" if kind == "الكل" else kind)
                self.driver_filter_combo.config(values=["الكل"] + names)
                if driver not in (["الكل"] + names):
                    self.driver_filter_var.set("الكل")
                cars = all_cars if self.driver_filter_var.get().strip() in ("", "الكل") \
                    else td.cars_for_driver(self.driver_filter_var.get().strip())
                self.car_filter_combo.config(values=["الكل"] + cars)
                if car_no not in (["الكل"] + cars):
                    self.car_filter_var.set(cars[0] if cars else "الكل")
            if "car_no" in self.combos:
                self.combos["car_no"].bind("<<ComboboxSelected>>", self._on_link_selection)
            if "driver" in self.combos:
                self.combos["driver"].bind("<<ComboboxSelected>>", self._on_link_selection)
        super().refresh()

    def on_save(self):
        data = {key: "" for key, _label in td.DAILY_EXPENSE_FIELDS}
        data.update({key: var.get().strip() for key, var in self.vars.items()})
        data["expense_owner"] = self.owner
        try:
            td.save_daily_expense(data, self.editing_key)
        except ValueError as exc:
            messagebox.showwarning("تنبيه", str(exc), parent=self.frame)
            return
        self.clear_form()
        self.vars["date"].set(date.today().isoformat())
        self.refresh()
        if callable(self.on_data_changed):
            self.on_data_changed()
        else:
            refresh_related_screens(self.frame)
