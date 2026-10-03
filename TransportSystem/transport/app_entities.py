# -*- coding: utf-8 -*-
"""تبويبات البيانات الأساسية والفواتير والمدفوعات."""

import html, json, os, re, tempfile, webbrowser
from datetime import date
from tkinter import filedialog
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk
from . import data as td
from .app_config import COLOR_BG, COLOR_BORDER, COLOR_CARD, COLOR_MUTED, COLOR_PRIMARY, FONT_NAME, F_BODY, F_BOLD, F_LABEL, F_SUBTITLE
from .ui_crud_tab import CrudTab
from .ui_pages_revenue import DailyCarsPage, VehicleRevenuePage
from .print_letterhead import INVOICE_FORM_ITEMS, LETTERHEAD_PRINT_STYLE, SERVICE_INVOICE_ITEMS, _contact_line, _deduplicate_invoice_items, _invoice_item_is_disabled, company_letterhead_html
from .ui_pages_trips import TripsPage
from .print_invoice import _REFERENCE_INVOICE_STYLE, _build_invoice_items_table, _build_reference_invoice_page, _invoice_container_count, generate_and_open_invoice_print
from .print_theme import apply_a4_print_layout, apply_print_footer
from .driver_links import apply_driver_car_to
from .ui_widgets import apply_table_style, card_frame, center_dialog, make_btn, scrollable_pane
from .ui_dialogs import date_input, open_attachment_manager_dialog
from .print_statement import generate_and_open_customer_statement
from .ui_helpers import log_exception, safe_str
from .ui_text_edit import refresh_related_screens

class AppEntitiesMixin:
    """تبويبات البيانات الأساسية والفواتير والمدفوعات."""

    # ---------------- شاشة الرحلات اليومية ----------------
    def _build_trips_page(self):
        trips_frame, trips_content = scrollable_pane(self.pages_area)
        self.trips_tab = TripsPage(trips_content, on_add_service_invoice=self._open_service_invoice_editor_from_services)
        refreshers = [
            self.trips_tab.refresh_customers_drivers,
            self.trips_tab.refresh_car_options,
            self.trips_tab.refresh,
        ]
        if hasattr(self.trips_tab, "services_tab") and self.trips_tab.services_tab:
            refreshers.append(self.trips_tab.services_tab.refresh)
        self.trips_tab.frame.pack(fill="both", expand=True)
        self.register_page("trips", trips_frame, refreshers=refreshers,
                           canvas=trips_frame.canvas)

    def _build_revenue_tab(self):
        """شاشة إيراد السيارات: صافي إيراد كل سيارة بعد خصم مصاريفها وأجرة سائقها."""
        frame, content = scrollable_pane(self.pages_area)
        self.revenue_tab = VehicleRevenuePage(content)
        self.revenue_tab.frame.pack(fill="both", expand=True)
        self.register_page("revenue", frame, refreshers=[
            self.revenue_tab.refresh,
        ], canvas=frame.canvas)

    def print_vehicle_setup_expenses(self):
        """طباعة كشف مصاريف تجهيز السيارات: بالسيارة، وبالإجمالي العام."""
        rows = td.load_vehicle_setup_expenses()
        if not rows:
            messagebox.showinfo("تنبيه", "لا توجد مصاريف تجهيز مسجلة للطباعة.",
                                parent=self)
            return
        body = "".join(
            "<tr>"
            f"<td>{html.escape(safe_str(row.get('car_no')))}</td>"
            f"<td>{html.escape(safe_str(row.get('date')))}</td>"
            f"<td>{html.escape(safe_str(row.get('category')))}</td>"
            f"<td>{html.escape(safe_str(row.get('setup_target')))}</td>"
            f"<td>{td.safe_float(row.get('amount')):.3f}</td>"
            f"<td>{html.escape(safe_str(row.get('description')))}</td>"
            "</tr>" for row in rows)
        total = round(sum(td.safe_float(r.get("amount")) for r in rows), 3)
        total_row = (f"<tr class='total-row'><td colspan='4'>الإجمالي العام</td>"
                     f"<td>{total:.3f}</td><td></td></tr>")
        report = f"""<!doctype html><html lang='ar' dir='rtl'>
<head><meta charset='utf-8'>
<style>{_REFERENCE_INVOICE_STYLE}{LETTERHEAD_PRINT_STYLE}
.setup-table{{width:100%;border-collapse:collapse;font-size:11px}}
.setup-table th{{background:#0F2B46;color:#fff;padding:6px;text-align:center}}
.setup-table td{{border:1px solid #D8E0E9;padding:5px;text-align:center}}
.total-row td{{font-weight:800;background:#FBF6EA}}
</style></head><body>
<h2>كشف مصاريف تجهيز السيارات</h2>
<p>عدد البنود: {len(rows)} — الإجمالي: {total:.3f} د.ك</p>
<table class='setup-table'>
<tr><th>السيارة</th><th>التاريخ</th><th>البند</th><th>الجهة</th>
<th>المبلغ (د.ك)</th><th>التفاصيل</th></tr>
{body}{total_row}
</table>
</body></html>"""
        path = os.path.join(tempfile.gettempdir(), "vehicle_setup_report.html")
        with open(path, "w", encoding="utf-8") as file:
            file.write(apply_a4_print_layout(report))
        webbrowser.open("file:///" + path.replace("\\", "/"))

    def _sync_setup_target(self):
        """يواكب خانة «الجهة» مع بند التجهيز المختار، إلا إن غيّرها المستخدم."""
        tab = getattr(self, "vehicle_setup_tab", None)
        if tab is None or "setup_target" not in tab.vars:
            return
        category = tab.vars.get("category")
        if category is None:
            return
        target = td.VEHICLE_SETUP_TARGETS.get(category.get().strip())
        if target:
            tab.vars["setup_target"].set(target)

    def _build_daily_cars_tab(self):
        cars_frame, cars_content = scrollable_pane(self.pages_area)
        self.daily_cars_tab = DailyCarsPage(cars_content)
        self.daily_cars_tab.frame.pack(fill="both", expand=True)
        self.register_page("daily_cars", cars_frame, refreshers=[
            self.daily_cars_tab.refresh,
        ], canvas=cars_frame.canvas)

    # ---------------- شاشات CRUD البسيطة ----------------
    def _build_entities_tab(self):
        """إنشاء التابات وتجهيز استيراد مُسبق من الصورة إذا لزم الأمر."""

        """شاشة مجمّعة تحتوي تابات: السائقون، السيارات، العملاء، الشركات
        تُبقي نفس كائنات CrudTab (self.drivers_tab, self.vehicles_tab, self.customers_tab,
        self.companies_tab) لتوافق الاستخدام الحالي في بقية التطبيق.
        """
        frame, content = scrollable_pane(self.pages_area)

        nb = ttk.Notebook(content)
        nb.pack(fill="both", expand=True, padx=12, pady=12)
        # نحتفظ به للتنقل من شاشة الشركاء إلى تاب شركاء السيارات.
        self.entities_notebook = nb

        drivers_frame = tk.Frame(nb, bg=COLOR_BG)
        vehicles_frame = tk.Frame(nb, bg=COLOR_BG)
        customers_frame = tk.Frame(nb, bg=COLOR_BG)
        companies_frame = tk.Frame(nb, bg=COLOR_BG)
        assignments_frame = tk.Frame(nb, bg=COLOR_BG)
        partners_frame = tk.Frame(nb, bg=COLOR_BG)
        ledger_frame = tk.Frame(nb, bg=COLOR_BG)
        contracts_frame = tk.Frame(nb, bg=COLOR_BG)
        quotations_frame = tk.Frame(nb, bg=COLOR_BG)
        setup_frame = tk.Frame(nb, bg=COLOR_BG)

        nb.add(drivers_frame, text="السائقون")
        nb.add(vehicles_frame, text="السيارات")
        nb.add(customers_frame, text="العملاء")
        nb.add(companies_frame, text="الشركات")
        nb.add(assignments_frame, text="تكليفات السائقين")
        nb.add(partners_frame, text="شركاء السيارات")
        nb.add(setup_frame, text="تجهيز السيارات")
        nb.add(ledger_frame, text="النقد والبنك")
        nb.add(contracts_frame, text="العقود")
        nb.add(quotations_frame, text="عروض الأسعار")
        # نحتفظ بإطار التاب نفسه (لا بإطار CrudTab الداخلي) للتنقل إليه.
        self.entities_partners_frame = partners_frame
        # تاب لأماكن التحميل والتنزيل
        places_frame = tk.Frame(nb, bg=COLOR_BG)
        nb.add(places_frame, text="أماكن التحميل/التفريغ")

        # أنشئ CrudTab لكل تاب — parent هو إطار التاب الخاص به
        driver_fields = [field for field in td.DRIVER_FIELDS
                         if field[0] != "commission_per_trip"]
        self.drivers_tab = CrudTab(
            drivers_frame, driver_fields, td.load_drivers, td.save_driver,
            td.delete_driver, "name", "السائقون",
            # الاسم هنا هو السائق نفسه. «رقم السيارة المخصصة» يجب أن يكون قائمة
            # منسدلة حتى يختار المستخدم أي سيارة (بخلاف الاسم الحر).
            select_fields={"driver_type": [""] + list(td.DRIVER_TYPES),
                           "car_no": [v["car_no"] for v in td.load_vehicles()
                                      if v.get("car_no")]},
            attachment_fields=[
                ("civil_id", "البطاقة المدنية"),
                ("driving_license", "رخصة القيادة"),
                ("passport", "جواز السفر"),
                ("other_files", "ملفات أخرى"),
            ],
            show_edit_button=False, show_upload_button=False,
            multiselect=True, print_mode="combined", single_row=True,
            compact_filters=True)
        # الاسم هنا هو السائق نفسه، فنملأ «رقم السيارة المخصصة» بالسيارة المكلَّفة به.
        # نتتبّع «الاسم» لا «السيارة» كي يُملأ الحقل فور كتابة الاسم،
        # الخانة فقط إن كانت فارغة حتى لا نطمس سيارة محفوظة عند التعديل.
        def _fill_driver_car(*_args, tab=self.drivers_tab):
            if not tab.vars["car_no"].get().strip():
                apply_driver_car_to(tab.vars, tab.vars["name"].get().strip())
        self.drivers_tab.vars["name"].trace_add("write", _fill_driver_car)
        self.drivers_tab.frame.pack(fill="both", expand=True)

        vehicle_fields = [field for field in td.VEHICLE_FIELDS
                          if field[0] not in ("driver", "has_generator", "is_flatbed", "flatbed_type")]
        self.vehicles_tab = CrudTab(
            vehicles_frame, vehicle_fields, td.load_vehicles, td.save_vehicle,
            td.delete_vehicle, "car_no", "السيارات",
            select_fields={"work_type": td.VEHICLE_WORK_TYPES},
            multiselect_fields={"contents": ["ساطحة", "لوبد", "مولد", "مقطورة مبردة"]},
            attachment_fields=[
                ("vehicle_book", "دفتر السيارة"),
                ("vehicle_agency", "توكيل السيارة"),
                ("other_files", "ملفات أخرى"),
            ],
            show_edit_button=False, show_upload_button=False,
            multiselect=True, print_mode="combined", single_row=True,
            compact_filters=True)
        self.vehicles_tab.frame.pack(fill="both", expand=True)

        self.customers_tab = CrudTab(
            customers_frame, td.CUSTOMER_FIELDS, td.load_customers, td.save_customer,
            td.delete_customer, "name", "العملاء والمخلصون الجمركيون",
            attachment_fields=[
                ("civil_id", "البطاقة المدنية"),
                ("other_files", "ملفات أخرى"),
            ],
            show_edit_button=False, show_upload_button=False,
            multiselect=True, print_mode="combined", single_row=True,
            compact_filters=True)
        self.customers_tab.frame.pack(fill="both", expand=True)

        self.companies_tab = CrudTab(
            companies_frame, td.COMPANY_FIELDS, td.load_companies, td.save_company,
            td.delete_company, "name", "الشركات",
            select_fields={"customs_broker": []},
            attachment_fields=[
                ("company_papers", "أوراق الشركة"),
                ("other_papers", "أوراق أخرى"),
            ],
            show_edit_button=False, show_upload_button=False,
            multiselect=True, print_mode="combined", single_row=True,
            compact_filters=True)
        self.companies_tab.frame.pack(fill="both", expand=True)

        assignment_fields = [field for field in td.VEHICLE_ASSIGNMENT_FIELDS
                             if field[0] != "id"]
        self.vehicle_assignments_tab = CrudTab(
            assignments_frame, assignment_fields,
            td.load_vehicle_assignments, td.save_vehicle_assignment,
            td.delete_vehicle_assignment, "id", "تكليفات السائقين",
            select_fields={"car_no": [], "driver": []},
            attachment_fields=[("files", "ملفات")],
            readonly_fields=["id"],
            show_edit_button=False, show_upload_button=False,
            multiselect=True, print_mode="combined", single_row=True,
            compact_filters=True)
        self.vehicle_assignments_tab.frame.pack(fill="both", expand=True)

        partner_fields = [("partner", "اسم الشريك")] + [
            field for field in td.VEHICLE_PARTNER_FIELDS
            if field[0] not in ("id", "partner")
        ]
        self.vehicle_partners_tab = CrudTab(
            partners_frame, partner_fields,
            td.load_vehicle_partners, td.save_vehicle_partner,
            td.delete_vehicle_partner, "id", "شركاء السيارات",
            select_fields={"car_no": [], "ownership_pct": td.PARTNER_SHARE_OPTIONS,
                           "locked": ["نعم", "لا"]},
            attachment_fields=[
                ("civil_id", "البطاقة المدنية"),
                ("other_files", "ملفات أخرى"),
            ],
            readonly_fields=["id"],
            show_edit_button=False, show_upload_button=False,
            multiselect=True, print_mode="combined", single_row=True,
            compact_filters=True)
        self.vehicle_partners_tab.frame.pack(fill="both", expand=True)

        # مصاريف تجهيز السيارة قبل بدء العمل: شراء السيارة والساطحة والمولد
        # وصيانتها. تختلف عن المصاريف اليومية لأنها تُسجَّل مرة واحدة للتجهيز.
        setup_fields = [field for field in td.VEHICLE_SETUP_FIELDS
                        if field[0] != "id"]
        self.vehicle_setup_tab = CrudTab(
            setup_frame, setup_fields, td.load_vehicle_setup_expenses,
            td.save_vehicle_setup_expense, td.delete_vehicle_setup_expense,
            "id", "مصاريف تجهيز السيارات",
            select_fields={
                "car_no": [v["car_no"] for v in td.load_vehicles() if v.get("car_no")],
                "category": td.VEHICLE_SETUP_CATEGORIES,
                "setup_target": sorted(set(td.VEHICLE_SETUP_TARGETS.values())),
            },
            attachment_fields=[("files", "ملفات")],
            readonly_fields=["id"], date_fields=["date"],
            # زر التعديل ظاهر دائماً: تعديل بند تجهيز بعد تسجيله شيء شائع وطبيعي،
            # وإلا احتاج المستخدم حذف السجل وإعادة إدخاله من الصفر.
            show_edit_button=True, show_upload_button=False,
            multiselect=True, print_mode="combined", single_row=True,
            compact_filters=True,
            extra_buttons=[("🖨 طباعة تجهيز السيارات",
                             self.print_vehicle_setup_expenses, "secondary")])
        # الجهة تتبع البند تلقائياً ما لم يغيّرها المستخدم، فلا تتناقض البيانات.
        self.vehicle_setup_tab.vars["category"].trace_add(
            "write", lambda *_: self._sync_setup_target())
        self.vehicle_setup_tab.frame.pack(fill="both", expand=True)

        ledger_fields = [field for field in td.CASH_LEDGER_FIELDS
                         if field[0] != "id"]
        self.cash_ledger_tab = CrudTab(
            ledger_frame, ledger_fields, td.load_cash_ledger,
            td.save_cash_ledger, td.delete_cash_ledger, "id", "دفتر النقد والبنك",
            select_fields={
                "transaction_type": td.CASH_LEDGER_TYPES,
                "account": td.CASH_LEDGER_ACCOUNTS,
                "party": [],
            },
            attachment_fields=[
                ("civil_id", "البطاقة المدنية"),
                ("other_files", "ملفات أخرى"),
            ],
            readonly_fields=["id"],
            show_edit_button=False, show_upload_button=False,
            multiselect=True, print_mode="combined", single_row=True,
            compact_filters=True)
        self.cash_ledger_tab.frame.pack(fill="both", expand=True)

        contract_fields = [field for field in td.CONTRACT_FIELDS
                           if field[0] not in ("id", "contract_no")]
        self.contracts_tab = CrudTab(
            contracts_frame, contract_fields, td.load_contracts, td.save_contract,
            td.delete_contract, "id", "العقود",
            select_fields={"status": ["نشط", "منتهي", "معلق"]},
            attachment_fields=[
                ("civil_id", "البطاقة المدنية"),
                ("other_files", "ملفات أخرى"),
            ],
            readonly_fields=["id"],
            show_edit_button=False, show_upload_button=False,
            multiselect=True, print_mode="combined", single_row=True,
            compact_filters=True)
        self.contracts_tab.frame.pack(fill="both", expand=True)

        quotation_fields = [field for field in td.QUOTATION_FIELDS
                            if field[0] not in ("id", "quotation_no")]
        self.quotations_tab = CrudTab(
            quotations_frame, quotation_fields, td.load_quotations, td.save_quotation,
            td.delete_quotation, "id", "عروض الأسعار",
            select_fields={
                "status": ["مسودة", "تم الإرسال", "مقبول", "مرفوض", "ملغى"],
                "customer": [],
            },
            attachment_fields=[
                ("quotation", "إضافة عرض سعر"),
                ("other_files", "ملفات أخرى"),
            ],
            readonly_fields=["id"],
            attachment_entity_type="quotation",
            show_edit_button=False, show_upload_button=False,
            multiselect=True, print_mode="combined", single_row=True,
            compact_filters=True)
        self.quotations_tab.frame.pack(fill="both", expand=True)

        place_fields = td.PLACES_FIELDS
        self.places_tab = CrudTab(
            places_frame, place_fields, td.load_places, td.save_place,
            td.delete_place, "name", "أماكن التحميل/التفريغ",
            select_fields={"type": ["محلي", "دولي"], "usage": td.PLACE_USAGES},
            attachment_fields=[
                ("quotation", "إضافة عرض سعر"),
                ("other_files", "ملفات أخرى"),
            ],
            show_edit_button=False, show_upload_button=False,
            multiselect=True, print_mode="combined", single_row=True,
            compact_filters=True)
        self.places_tab.frame.pack(fill="both", expand=True)

        # Any change in a master screen immediately propagates to all linked
        # screens (vehicles, trips, expenses, services, invoices and salaries).
        for tab in (self.drivers_tab, self.vehicles_tab, self.customers_tab,
                    self.companies_tab, self.places_tab,
                    self.vehicle_assignments_tab, self.vehicle_partners_tab):
            tab.on_data_changed = self.refresh_linked_data

        # أزرار مساعدة لاستيراد الأماكن والسائقين من الصورة
        helper_row = tk.Frame(places_frame, bg=COLOR_BG)
        helper_row.pack(fill="x", padx=12, pady=(4, 6))
        make_btn(helper_row, "استيراد سائقين من الصورة", lambda: self._import_from_image("drivers"), variant="secondary").pack(side="right", padx=6)
        make_btn(helper_row, "استيراد أماكن من الصورة", lambda: self._import_from_image("places"), variant="secondary").pack(side="right", padx=6)

        # ريفريشر لتحديث قائمة السائقين في تبويب السيارات
        def refresh_vehicle_drivers():
            self.vehicles_tab.refresh()

        def refresh_vehicle_relations():
            cars = [v["car_no"] for v in td.load_vehicles() if v.get("car_no")]
            drivers = [d["name"] for d in td.load_drivers() if d.get("name")]
            self.vehicle_assignments_tab.combos["car_no"].config(values=cars)
            self.vehicle_assignments_tab.combos["driver"].config(values=drivers)
            self.vehicle_partners_tab.combos["car_no"].config(values=cars)
            self.vehicle_assignments_tab.refresh()
            self.vehicle_partners_tab.refresh()

        # ريفريشر لتحديث قائمة المخلصين الجمركيين (من العملاء بنوع "مخلص جمركي") في تبويب الشركات
        def refresh_company_brokers():
            try:
                # بعد إزالة حقل النوع من العملاء، يمكن اختيار أي عميل كمخلص
                # جمركي مرتبط بالشركة.
                brokers = [c["name"] for c in td.load_customers() if c.get("name")]
                self.companies_tab.combos["customs_broker"].config(values=brokers)
            except Exception as _log_exc: log_exception("refresh_company_brokers", _log_exc)
            self.companies_tab.refresh()

        # سجّل صفحة موحدة في نظام التنقّل
        self.register_page("entities", frame, refreshers=[
            self.drivers_tab.refresh,
            refresh_vehicle_drivers,
            refresh_vehicle_relations,
            self.customers_tab.refresh,
            refresh_company_brokers,
            self.places_tab.refresh,
        ], canvas=frame.canvas)

        # تابع استيراد النصوص من الصورة (يعرض مربع يسمح بلصق/تعديل النص ثم الحفظ)
        def _import_text_dialog(default_text, title, on_save_lines):
            dlg = tk.Toplevel(self)
            dlg.title(title)
            dlg.geometry("520x360")
            tk.Label(dlg, text="تحقق من النص ثم اضغط حفظ", bg=COLOR_BG).pack(anchor="e", padx=8, pady=(8,0))
            txt = tk.Text(dlg, wrap="word", font=F_BODY)
            txt.pack(fill="both", expand=True, padx=8, pady=8)
            txt.insert("1.0", default_text)
            def do_save():
                content = txt.get("1.0", "end").strip()
                lines = [l.strip() for l in content.replace(',', '\n').split('\n') if l.strip()]
                on_save_lines(lines)
                dlg.destroy()
            btns = tk.Frame(dlg, bg=COLOR_BG)
            btns.pack(fill="x", padx=8, pady=8)
            make_btn(btns, "حفظ", do_save, variant="accent").pack(side="right", padx=4)
            make_btn(btns, "إلغاء", dlg.destroy, variant="secondary").pack(side="right", padx=4)
            dlg.transient(self)
            dlg.grab_set()

        self._import_text_dialog = _import_text_dialog

        # دالة عامة لاستيراد من الصورة — تستخدم حقل النص الافتراضي المستخرج من الصورة
        def _import_from_image(kind):
            # اقتراح نص مُستخرج من الصورة (يمكنك تعديلها في مربع الحوار قبل الحفظ)
            if kind == "drivers":
                def on_save(names):
                    count = 0
                    for n in names:
                        try:
                            td.save_driver({"name": n})
                            count += 1
                        except Exception as _log_exc: log_exception("on_save", _log_exc)
                    messagebox.showinfo("تم", f"تم إضافة {count} سائقًا (أو تم تحديثهم إذا كانوا موجودين).")
                self._import_text_dialog(sample, "استيراد سائقين من الصورة", on_save)
            elif kind == "places":
                sample = "الدوحة\nصباح السالم\nالروضة\nميناء عبدالله\nالمسيلة\nالمنطقة الصناعية"
                def on_save(lines):
                    count = 0
                    for l in lines:
                        try:
                            td.save_place({"name": l, "type": "محلي"})
                            count += 1
                        except Exception as _log_exc: log_exception("on_save", _log_exc)
                    messagebox.showinfo("تم", f"تم إضافة {count} مكانًا محليًا.")
                self._import_text_dialog(sample, "استيراد أماكن من الصورة", on_save)

        self._import_from_image = _import_from_image

    # ---------------- شاشة الفواتير ----------------
    def _build_invoices_tab(self):
        frame, content = scrollable_pane(self.pages_area)

        # يحتفظ المتغير بدعم ملخص الحساب وكشف العميل، دون عرض أدوات إصدار فاتورة جديدة.
        self.inv_customer_var = tk.StringVar()
        notebook = ttk.Notebook(content)
        notebook.pack(fill="both", expand=True, padx=12, pady=8)
        payments_page = tk.Frame(notebook, bg=COLOR_BG)
        invoices_page = tk.Frame(notebook, bg=COLOR_BG)
        statement_page = tk.Frame(notebook, bg=COLOR_BG)
        notebook.add(invoices_page, text="الفواتير الصادرة")
        notebook.add(payments_page, text="دفعات العملاء")
        notebook.add(statement_page, text="كشف الحساب")

        payments_box = card_frame(payments_page, "دفعات العملاء والمخلصين")
        payments_box.pack(fill="x", expand=False, padx=18, pady=(8, 0))
        payment_actions = tk.Frame(payments_box.body, bg=COLOR_CARD)
        payment_actions.pack(fill="x", padx=18, pady=(0, 8))
        make_btn(payment_actions, "إضافة دفعة", self.add_payment, variant="accent", padx=4, pady=6).pack(side="right", padx=2)
        make_btn(payment_actions, "حذف الدفعة", self.delete_selected_payment, variant="danger", padx=4, pady=6).pack(side="right", padx=2)
        payment_table = tk.Frame(payments_box.body, bg=COLOR_CARD)
        payment_table.pack(fill="x", expand=False, padx=18, pady=(0, 12))
        # أدوات البحث والفلترة في نفس الصف، وتثبت كأول مجموعة من جهة اليمين.
        payment_filter = tk.Frame(payment_actions, bg=COLOR_CARD)
        payment_filter.pack(side="right", before=payment_actions.winfo_children()[0], padx=(0, 8))
        self.payment_search_var = tk.StringVar()
        self.payment_date_from_var = tk.StringVar()
        self.payment_date_to_var = tk.StringVar()
        self.payment_customer_filter_var = tk.StringVar(value="الكل")
        self.payment_scope_filter_var = tk.StringVar(value="كل الدفعات")
        tk.Label(payment_filter, text="بحث", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(8, 3))
        payment_search = tk.Entry(payment_filter, textvariable=self.payment_search_var, font=F_BODY, justify="right", width=12)
        payment_search.pack(side="right", padx=3)
        payment_search.bind("<KeyRelease>", lambda _e: self.refresh_payment_history())
        tk.Label(payment_filter, text="من", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(8, 2))
        payment_from = date_input(payment_filter, self.payment_date_from_var, width=10)
        payment_from.pack_forget()
        payment_from.pack(side="right", padx=2)
        payment_from.winfo_children()[0].bind("<KeyRelease>", lambda _e: self.refresh_payment_history())
        tk.Label(payment_filter, text="إلى", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(6, 2))
        payment_to = date_input(payment_filter, self.payment_date_to_var, width=10)
        payment_to.pack_forget()
        payment_to.pack(side="right", padx=2)
        payment_to.winfo_children()[0].bind("<KeyRelease>", lambda _e: self.refresh_payment_history())
        tk.Label(payment_filter, text="العميل", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        self.payment_customer_filter = ttk.Combobox(payment_filter, textvariable=self.payment_customer_filter_var,
                                                     font=F_BODY, justify="right", state="readonly", width=14)
        self.payment_customer_filter.pack(side="right", padx=3)
        self.payment_customer_filter.bind("<<ComboboxSelected>>", lambda _e: self.refresh_payment_history())
        tk.Label(payment_filter, text="النوع", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        self.payment_scope_filter = ttk.Combobox(payment_filter, textvariable=self.payment_scope_filter_var,
                                                  values=("كل الدفعات", "دفعات عامة", "دفعات مرتبطة ببيان"),
                                                  font=F_BODY, justify="right", state="readonly", width=18)
        self.payment_scope_filter.pack(side="right", padx=3)
        self.payment_scope_filter.bind("<<ComboboxSelected>>", lambda _e: self.refresh_payment_history())
        make_btn(payment_filter, "مسح الفلاتر", self.clear_payment_filters, variant="secondary", padx=4, pady=6).pack(side="right", padx=2)
        make_btn(payment_filter, "طباعة", self.print_filtered_payments, variant="secondary", padx=4, pady=6).pack(side="right", padx=2)
        payment_cols = ("invoice_no", "reference", "amount", "customer", "date", "id")
        self.payment_tree = ttk.Treeview(payment_table, columns=payment_cols, show="headings", selectmode="extended", height=5)
        payment_headers = {"id": "الرقم", "date": "التاريخ", "customer": "المخلص / العميل",
                           "amount": "الدفعة (د.ك)", "reference": "المرجع", "invoice_no": "البيان / الفاتورة المرتبطة"}
        for col in payment_cols:
            self.payment_tree.heading(col, text=payment_headers[col])
            self.payment_tree.column(col, anchor="center", width=125, stretch=True)
        self.payment_tree.pack(fill="x", expand=False)
        apply_table_style(self.payment_tree)
        self.payment_tree.bind("<Double-1>", lambda _e: self.edit_selected_payment())
        self.invoice_account_summary_var = tk.StringVar(value="إجمالي الفواتير: 0.000 د.ك  |  الدفعات: 0.000 د.ك  |  الرصيد: 0.000 د.ك")
        tk.Label(payments_box.body, textvariable=self.invoice_account_summary_var,
                 font=F_BOLD, bg=COLOR_CARD, fg=COLOR_PRIMARY,
                 anchor="e").pack(fill="x", padx=18, pady=(0, 10))

        statement_box = card_frame(statement_page, "كشف حساب العميل / المخلص")
        statement_box.pack(fill="x", padx=18, pady=18)
        statement_body = statement_box.body
        statement_form = tk.Frame(statement_body, bg=COLOR_CARD)
        statement_form.pack(fill="x", padx=18, pady=(0, 12))
        self.statement_customer_var = tk.StringVar(value="")
        tk.Label(statement_form, text="العميل / المخلص", font=F_LABEL,
                 bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=6)
        self.statement_customer_combo = ttk.Combobox(
            statement_form, textvariable=self.statement_customer_var,
            values=[c["name"] for c in td.load_customers()], font=F_BODY,
            justify="right", state="readonly", width=30)
        self.statement_customer_combo.pack(side="right", padx=6)
        self.statement_customer_combo.bind("<<ComboboxSelected>>",
                                           lambda _e: (self.refresh_statement_companies(),
                                                       self.refresh_statement_summary()))
        self.statement_date_from_var = tk.StringVar()
        self.statement_date_to_var = tk.StringVar()
        self.statement_company_var = tk.StringVar(value="الكل")
        tk.Label(statement_form, text="من", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        statement_from = date_input(statement_form, self.statement_date_from_var, width=10)
        statement_from.pack_forget(); statement_from.pack(side="right", padx=3)
        statement_from.winfo_children()[0].bind("<KeyRelease>", lambda _e: self.refresh_statement_summary())
        tk.Label(statement_form, text="إلى", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(8, 3))
        statement_to = date_input(statement_form, self.statement_date_to_var, width=10)
        statement_to.pack_forget(); statement_to.pack(side="right", padx=3)
        statement_to.winfo_children()[0].bind("<KeyRelease>", lambda _e: self.refresh_statement_summary())
        tk.Label(statement_form, text="الشركة", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        self.statement_company_combo = ttk.Combobox(statement_form, textvariable=self.statement_company_var,
                                                      font=F_BODY, justify="right", state="readonly", width=20)
        self.statement_company_combo.pack(side="right", padx=3)
        self.statement_company_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_statement_summary())
        make_btn(statement_form, "تحديث", self.refresh_statement_summary,
                 variant="secondary", padx=7, pady=3).pack(side="right", padx=4)
        make_btn(statement_form, "طباعة كشف الحساب", self.print_statement_tab,
                 variant="accent", padx=7, pady=3).pack(side="right", padx=4)
        self.statement_summary_var = tk.StringVar(
            value="اختر عميلًا لعرض إجمالي الفواتير والدفعات والرصيد المستحق.")
        tk.Label(statement_body, textvariable=self.statement_summary_var,
                 font=F_BOLD, bg=COLOR_CARD, fg=COLOR_PRIMARY,
                 anchor="e", justify="right").pack(fill="x", padx=18, pady=(0, 14))

        hist_box = card_frame(invoices_page, "سجل الفواتير الصادرة")
        hist_box.pack(fill="x", expand=False, padx=18, pady=(18, 8))
        invoice_actions = tk.Frame(hist_box.body, bg=COLOR_CARD)
        invoice_actions.pack(fill="x", padx=18, pady=(0, 10), anchor="e")
        make_btn(invoice_actions, "إضافة فاتورة", self.add_invoice_direct, variant="accent", padx=7, pady=3).pack(side="right", padx=3)
        make_btn(invoice_actions, "طباعة فواتير", self.print_selected_invoices, variant="accent", padx=7, pady=3).pack(side="right", padx=3)
        make_btn(invoice_actions, "حذف الفواتير", self.delete_selected_invoices, variant="danger", padx=7, pady=3).pack(side="right", padx=3)
        table_wrap = tk.Frame(hist_box.body, bg=COLOR_CARD)
        table_wrap.pack(fill="x", expand=False, padx=18)
        # أدوات البحث والفلترة في نفس شريط سجل الفواتير، جهة اليمين.
        invoice_filter = tk.Frame(invoice_actions, bg=COLOR_CARD)
        invoice_filter.pack(side="right", before=invoice_actions.winfo_children()[0], padx=(0, 8))
        self.invoice_search_var = tk.StringVar()
        self.invoice_date_from_var = tk.StringVar()
        self.invoice_date_to_var = tk.StringVar()
        self.invoice_customer_filter_var = tk.StringVar(value="الكل")
        tk.Label(invoice_filter, text="بحث", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(8, 3))
        invoice_search = tk.Entry(invoice_filter, textvariable=self.invoice_search_var, font=F_BODY, justify="right", width=12)
        invoice_search.pack(side="right", padx=3)
        invoice_search.bind("<KeyRelease>", lambda _e: self.refresh_invoice_history())
        tk.Label(invoice_filter, text="من", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(8, 2))
        invoice_from = date_input(invoice_filter, self.invoice_date_from_var, width=10)
        invoice_from.pack_forget()
        invoice_from.pack(side="right", padx=2)
        invoice_from.winfo_children()[0].bind("<KeyRelease>", lambda _e: self.refresh_invoice_history())
        tk.Label(invoice_filter, text="إلى", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(6, 2))
        invoice_to = date_input(invoice_filter, self.invoice_date_to_var, width=10)
        invoice_to.pack_forget()
        invoice_to.pack(side="right", padx=2)
        invoice_to.winfo_children()[0].bind("<KeyRelease>", lambda _e: self.refresh_invoice_history())
        tk.Label(invoice_filter, text="العميل", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="right", padx=(12, 3))
        self.invoice_customer_filter = ttk.Combobox(invoice_filter, textvariable=self.invoice_customer_filter_var,
                                                      font=F_BODY, justify="right", state="readonly", width=24)
        self.invoice_customer_filter.pack(side="right", padx=3)
        self.invoice_customer_filter.bind("<<ComboboxSelected>>", lambda _e: self.refresh_invoice_history())
        make_btn(invoice_filter, "مسح الفلاتر", self.clear_invoice_filters, variant="secondary", padx=7, pady=3).pack(side="right", padx=3)
        cols = ("paid", "total", "customer", "date", "invoice_no")
        self.inv_tree = ttk.Treeview(table_wrap, columns=cols, show="headings", selectmode="extended")
        headers = {"invoice_no": "رقم الفاتورة", "date": "التاريخ", "customer": "العميل",
                   "total": "الإجمالي (د.ك)", "paid": "حالة السداد"}
        for c in cols:
            self.inv_tree.heading(c, text=headers[c])
            self.inv_tree.column(c, anchor="center", width=140, stretch=True)
        self.inv_tree.pack(fill="x", expand=False, pady=4)
        apply_table_style(self.inv_tree)
        self.inv_tree.bind("<Configure>", lambda e: self._auto_size_tree(self.inv_tree, cols))
        self.inv_tree.bind("<Double-1>", lambda _e: self.edit_selected_invoice())

        btns = tk.Frame(hist_box.body, bg=COLOR_CARD)
        btns.pack(fill="x", padx=18, pady=(8, 16), anchor="e")
        make_btn(btns, "طباعة الفاتورة", self.print_selected_invoice, variant="accent").pack(side="right", padx=4)
        make_btn(btns, "طباعة كشف حساب العميل", self.print_customer_statement, variant="secondary").pack(side="right", padx=4)
        make_btn(btns, "تعديل بيانات الفاتورة", self.edit_selected_invoice, variant="secondary").pack(side="right", padx=4)

        self.register_page("invoices", frame, refreshers=[self.refresh_invoice_history,
                                                           self.refresh_payment_history,
                                                           self.refresh_statement_customers],
                           canvas=frame.canvas)

    def refresh_statement_customers(self):
        if not hasattr(self, "statement_customer_combo"):
            return
        names = sorted({safe_str(customer.get("name")).strip()
                        for customer in td.load_customers()
                        if safe_str(customer.get("name")).strip()})
        self.statement_customer_combo["values"] = names
        if self.statement_customer_var.get().strip() not in names:
            self.statement_customer_var.set("")
        self.refresh_statement_companies()
        self.refresh_statement_summary()

    def refresh_statement_companies(self):
        if not hasattr(self, "statement_company_combo"):
            return
        customer = self.statement_customer_var.get().strip()
        companies = {safe_str(company.get("name")).strip()
                     for company in td.load_companies()
                     if safe_str(company.get("name")).strip()
                     and (not customer or safe_str(company.get("customs_broker")).strip() == customer)}
        values = ["الكل"] + sorted(companies)
        self.statement_company_combo["values"] = values
        if self.statement_company_var.get() not in values:
            self.statement_company_var.set("الكل")

    def refresh_statement_summary(self):
        if not hasattr(self, "statement_summary_var"):
            return
        customer = self.statement_customer_var.get().strip()
        if not customer:
            self.statement_summary_var.set("اختر عميلًا لعرض إجمالي الفواتير والدفعات والرصيد المستحق.")
            return
        date_from = self.statement_date_from_var.get().strip()
        date_to = self.statement_date_to_var.get().strip()
        company = self.statement_company_var.get().strip()
        invoices, payments = self._statement_filtered_records(customer, date_from, date_to, company)
        invoice_total = sum(td.safe_float(invoice.get("total")) for invoice in invoices)
        payment_total = sum(td.safe_float(payment.get("amount")) for payment in payments)
        self.statement_summary_var.set(
            f"العميل: {customer}  |  عدد الفواتير: {len(invoices)}  |  "
            f"إجمالي الفواتير: {invoice_total:.3f} د.ك  |  "
            f"إجمالي الدفعات: {payment_total:.3f} د.ك  |  "
            f"الرصيد المستحق: {invoice_total - payment_total:.3f} د.ك"
        )

    def print_statement_tab(self):
        customer = self.statement_customer_var.get().strip()
        if not customer:
            messagebox.showinfo("تنبيه", "الرجاء اختيار العميل أولاً.")
            return
        date_from = self.statement_date_from_var.get().strip()
        date_to = self.statement_date_to_var.get().strip()
        company = self.statement_company_var.get().strip()
        invoices, payments = self._statement_filtered_records(customer, date_from, date_to, company)
        if not invoices and not payments:
            messagebox.showinfo("لا توجد بيانات", "لا توجد حركات مطابقة للفلاتر المحددة.")
            return
        generate_and_open_customer_statement(customer, invoices, payments=payments,
                                             date_from=date_from, date_to=date_to,
                                             company=company)

    def _statement_filtered_records(self, customer, date_from="", date_to="", company="الكل"):
        invoices = [invoice for invoice in td.load_invoices()
                    if safe_str(invoice.get("customer")).strip() == customer
                    and (not date_from or safe_str(invoice.get("date")) >= date_from)
                    and (not date_to or safe_str(invoice.get("date")) <= date_to)]
        if company and company != "الكل":
            invoice_numbers = {safe_str(trip.get("invoice_no")) for trip in td.load_trips()
                               if safe_str(trip.get("company")).strip() == company}
            invoices = [invoice for invoice in invoices
                        if safe_str(invoice.get("invoice_no")) in invoice_numbers]
        invoice_numbers = {safe_str(invoice.get("invoice_no")) for invoice in invoices}
        payments = [payment for payment in td.load_payments()
                    if safe_str(payment.get("customer")).strip() == customer
                    and (not date_from or safe_str(payment.get("date")) >= date_from)
                    and (not date_to or safe_str(payment.get("date")) <= date_to)
                    and (not company or company == "الكل" or safe_str(payment.get("invoice_no")) in invoice_numbers)]
        return invoices, payments

    def refresh_customer_combo(self):
        names = [c["name"] for c in td.load_customers()]
        if hasattr(self, "inv_customer_combo"):
            self.inv_customer_combo.config(values=names)
        self.refresh_unbilled_lists()
        self.refresh_invoice_account_summary()

    def refresh_unbilled_lists(self):
        if not hasattr(self, "inv_trips_list") or not hasattr(self, "inv_services_list"):
            self.refresh_invoice_account_summary()
            return
        self.inv_trips_list.delete(0, "end")
        self.inv_services_list.delete(0, "end")
        customer = self.inv_customer_var.get()
        self.refresh_invoice_account_summary()
        if not customer:
            return
        self._unbilled_trips = td.unbilled_trips_for_customer(customer)
        self._unbilled_services = td.unbilled_services_for_customer(customer)
        for t in self._unbilled_trips:
            route = f"{t.get('origin','')} ← {t.get('destination','')}".strip(" ←")
            self.inv_trips_list.insert(
                "end", f"#{t['id']} | {t.get('date','')} | {t.get('trip_category','')} | "
                       f"{route} | {t.get('fee','0')} د.ك")
        for s in self._unbilled_services:
            self.inv_services_list.insert(
                "end", f"#{s['id']} | {s.get('date','')} | {s.get('service_type','')} | "
                       f"الكمية {s.get('quantity','')} | {s.get('total','0')} د.ك")

    def issue_invoice(self):
        customer = self.inv_customer_var.get()
        if not customer:
            messagebox.showwarning("تنبيه", "الرجاء اختيار عميل أولاً.")
            return
        trip_idx = self.inv_trips_list.curselection()
        service_idx = self.inv_services_list.curselection()
        if not trip_idx and not service_idx:
            messagebox.showwarning("تنبيه", "الرجاء اختيار عنصر واحد على الأقل (رحلة أو خدمة) لإصدار الفاتورة.")
            return
        trip_ids = [self._unbilled_trips[i]["id"] for i in trip_idx]
        service_ids = [self._unbilled_services[i]["id"] for i in service_idx]
        items = td.build_invoice_items(trip_ids, service_ids)
        self._invoice_editor_dialog(customer=customer, trip_ids=trip_ids,
                                    service_ids=service_ids, items=items)

    def add_invoice_direct(self):
        """Open the same editor used for modifying an invoice."""
        self._invoice_editor_dialog()

    def add_invoice_from_screen(self):
        """Open a compact selector for creating an invoice from the invoices screen."""
        dlg = tk.Toplevel(self)
        dlg.title("إضافة فاتورة")
        dlg.geometry("760x470")
        dlg.configure(bg=COLOR_CARD)
        dlg.transient(self)
        dlg.grab_set()
        center_dialog(dlg, self)
        customer_var = tk.StringVar()
        tk.Label(dlg, text="العميل / المخلص", font=F_LABEL,
                 bg=COLOR_CARD, fg=COLOR_MUTED).pack(anchor="e", padx=18, pady=(16, 4))
        customer_combo = ttk.Combobox(
            dlg, textvariable=customer_var,
            values=[c["name"] for c in td.load_customers()],
            font=F_BODY, justify="right", state="readonly")
        customer_combo.pack(fill="x", padx=18, ipady=3)
        lists = tk.Frame(dlg, bg=COLOR_CARD)
        lists.pack(fill="both", expand=True, padx=18, pady=14)
        trips_list = tk.Listbox(lists, selectmode="extended", exportselection=False,
                                font=F_BODY, justify="right", height=12)
        services_list = tk.Listbox(lists, selectmode="extended", exportselection=False,
                                   font=F_BODY, justify="right", height=12)
        tk.Label(lists, text="الرحلات غير المفوترة", font=F_BOLD, bg=COLOR_CARD,
                 fg=COLOR_PRIMARY).pack(side="right", padx=8)
        trips_list.pack(side="right", fill="both", expand=True, padx=6)
        tk.Label(lists, text="الخدمات غير المفوترة", font=F_BOLD, bg=COLOR_CARD,
                 fg=COLOR_PRIMARY).pack(side="right", padx=8)
        services_list.pack(side="right", fill="both", expand=True, padx=6)
        records = {"trips": [], "services": []}

        def refresh_lists(_event=None):
            customer = customer_var.get().strip()
            records["trips"] = td.unbilled_trips_for_customer(customer) if customer else []
            records["services"] = td.unbilled_services_for_customer(customer) if customer else []
            trips_list.delete(0, "end")
            services_list.delete(0, "end")
            for row in records["trips"]:
                trips_list.insert("end", f"#{row.get('id')} | {row.get('date','')} | {row.get('declaration_no','')} | {row.get('fee','0')} د.ك")
            for row in records["services"]:
                services_list.insert("end", f"#{row.get('id')} | {row.get('date','')} | {row.get('service_type','')} | {row.get('total','0')} د.ك")

        customer_combo.bind("<<ComboboxSelected>>", refresh_lists)

        def continue_to_editor():
            if not customer_var.get().strip():
                messagebox.showwarning("تنبيه", "الرجاء اختيار العميل / المخلص.", parent=dlg)
                return
            trip_ids = [records["trips"][i].get("id") for i in trips_list.curselection()]
            service_ids = [records["services"][i].get("id") for i in services_list.curselection()]
            if not trip_ids and not service_ids:
                messagebox.showwarning("تنبيه", "الرجاء اختيار رحلة أو خدمة واحدة على الأقل.", parent=dlg)
                return
            items = td.build_invoice_items(trip_ids, service_ids)
            dlg.destroy()
            self._invoice_editor_dialog(customer=customer_var.get().strip(),
                                        trip_ids=trip_ids, service_ids=service_ids, items=items)

        actions = tk.Frame(dlg, bg=COLOR_CARD)
        actions.pack(fill="x", padx=18, pady=(0, 16))
        make_btn(actions, "متابعة", continue_to_editor, variant="accent").pack(side="right", padx=4)
        make_btn(actions, "إلغاء", dlg.destroy, variant="secondary").pack(side="right", padx=4)

    def refresh_invoice_history(self):
        if not hasattr(self, "inv_tree") or not self.inv_tree.winfo_exists():
            return
        for row in self.inv_tree.get_children():
            self.inv_tree.delete(row)
        self._invoices = td.load_invoices()
        search = safe_str(getattr(self, "invoice_search_var", tk.StringVar()).get()).strip().casefold()
        customer = safe_str(getattr(self, "invoice_customer_filter_var", tk.StringVar(value="الكل")).get()).strip()
        date_from = safe_str(getattr(self, "invoice_date_from_var", tk.StringVar()).get()).strip()
        date_to = safe_str(getattr(self, "invoice_date_to_var", tk.StringVar()).get()).strip()
        visible = [inv for inv in self._invoices
                   if (customer in ("", "الكل") or safe_str(inv.get("customer")).strip() == customer)
                   and (not date_from or safe_str(inv.get("date")) >= date_from)
                   and (not date_to or safe_str(inv.get("date")) <= date_to)
                   and (not search or search in " ".join(safe_str(inv.get(key)) for key in ("invoice_no", "date", "customer", "declaration_no")).casefold())]
        for inv in sorted(visible, key=lambda x: td.safe_int(x["invoice_no"]), reverse=True):
            self.inv_tree.insert("", "end", iid=str(inv["invoice_no"]),
                                  values=(safe_str(inv.get("paid")) or "لا", inv["total"],
                                          inv["customer"], inv["date"], inv["invoice_no"]))
        names = sorted({safe_str(inv.get("customer")).strip() for inv in self._invoices if safe_str(inv.get("customer")).strip()})
        if hasattr(self, "invoice_customer_filter"):
            self.invoice_customer_filter["values"] = ["الكل"] + names
        self.inv_tree.update_idletasks()

    def refresh_payment_history(self):
        if not hasattr(self, "payment_tree"):
            return
        for row in self.payment_tree.get_children():
            self.payment_tree.delete(row)
        self._payments = td.load_payments()
        search = safe_str(getattr(self, "payment_search_var", tk.StringVar()).get()).strip().casefold()
        customer = safe_str(getattr(self, "payment_customer_filter_var", tk.StringVar(value="الكل")).get()).strip()
        scope = safe_str(getattr(self, "payment_scope_filter_var", tk.StringVar(value="كل الدفعات")).get()).strip()
        date_from = safe_str(getattr(self, "payment_date_from_var", tk.StringVar()).get()).strip()
        date_to = safe_str(getattr(self, "payment_date_to_var", tk.StringVar()).get()).strip()
        visible = [payment for payment in self._payments
                   if (customer in ("", "الكل") or safe_str(payment.get("customer")).strip() == customer)
                   and (not date_from or safe_str(payment.get("date")) >= date_from)
                   and (not date_to or safe_str(payment.get("date")) <= date_to)
                   and (scope == "كل الدفعات"
                        or (scope == "دفعات عامة" and not safe_str(payment.get("invoice_no")).strip())
                        or (scope == "دفعات مرتبطة ببيان" and bool(safe_str(payment.get("invoice_no")).strip())))
                   and (not search or search in " ".join(safe_str(payment.get(key)) for key in ("id", "date", "customer", "amount", "reference", "invoice_no", "notes")).casefold())]
        for payment in sorted(visible, key=lambda row: (safe_str(row.get("date")), td.safe_int(row.get("id"))), reverse=True):
            self.payment_tree.insert("", "end", iid=str(payment["id"]), values=(
                payment.get("invoice_no", ""), payment.get("reference", ""),
                f"{td.safe_float(payment.get('amount')):.3f}", payment.get("customer", ""),
                payment.get("date", ""), payment.get("id", "")))
        names = sorted({safe_str(payment.get("customer")).strip() for payment in self._payments if safe_str(payment.get("customer")).strip()})
        if hasattr(self, "payment_customer_filter"):
            self.payment_customer_filter["values"] = ["الكل"] + names
        self.refresh_invoice_account_summary()

    def clear_payment_filters(self):
        self.payment_search_var.set("")
        self.payment_date_from_var.set("")
        self.payment_date_to_var.set("")
        self.payment_customer_filter_var.set("الكل")
        self.payment_scope_filter_var.set("كل الدفعات")
        self.refresh_payment_history()

    def clear_invoice_filters(self):
        self.invoice_search_var.set("")
        self.invoice_date_from_var.set("")
        self.invoice_date_to_var.set("")
        self.invoice_customer_filter_var.set("الكل")
        self.refresh_invoice_history()

    def _open_service_invoice_editor_from_services(self):
        if not hasattr(self, "trips_tab") or not self.trips_tab or not hasattr(self.trips_tab, "services_tab") or not self.trips_tab.services_tab:
            messagebox.showinfo("تنبيه", "يرجى الانتقال إلى شاشة الرحلات اليومية أولاً.")
            return
        selected = self.trips_tab.services_tab.tree.selection()
        service_ids = []
        for iid in selected:
            row = self.trips_tab.services_tab._tree_row_map.get(iid)
            if row:
                service_ids.append(str(row.get("id")))
        if not service_ids:
            messagebox.showinfo("تنبيه", "الرجاء اختيار خدمة واحدة على الأقل من سجل الخدمات الإضافية.")
            return
        customer = ""
        if service_ids:
            first_service = next((s for s in td.load_services() if str(s.get("id")) == service_ids[0]), None)
            if first_service:
                customer = safe_str(first_service.get("customer", "")).strip()
        self.show_page("invoices")
        self._invoice_editor_dialog(customer=customer, service_ids=service_ids, record_type="service")

    def print_filtered_payments(self):
        """يطبع الدفعات الظاهرة حاليًا بعد تطبيق البحث والفلاتر."""
        selected = list(self.payment_tree.get_children())
        if not selected:
            messagebox.showinfo("لا توجد بيانات", "لا توجد دفعات مطابقة للفلاتر الحالية.")
            return
        selected_ids = {str(row_id) for row_id in selected}
        payments = [payment for payment in self._payments
                    if str(payment.get("id")) in selected_ids]
        self._open_payments_print_report(payments)

    def _open_payments_print_report(self, payments):
        rows = "".join(
            f"<tr><td>{html.escape(safe_str(p.get('id')))}</td><td>{html.escape(safe_str(p.get('date')))}</td>"
            f"<td>{html.escape(safe_str(p.get('customer')))}</td><td>{td.safe_float(p.get('amount')):.3f}</td>"
            f"<td>{html.escape(safe_str(p.get('reference')))}</td><td>{html.escape(safe_str(p.get('invoice_no')) or 'دفعة عامة')}</td></tr>"
            for p in payments)
        total = sum(td.safe_float(p.get("amount")) for p in payments)
        header = company_letterhead_html("تقرير دفعات العملاء", document_date=date.today().isoformat())
        html_content = f"""<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'>
<style>{LETTERHEAD_PRINT_STYLE}body{{font-family:Tahoma,Arial,sans-serif;background:#F3F6FA;color:#1C2530;padding:8px}}.page{{max-width:900px;margin:auto;background:#fff;min-height:270mm;padding:10px}}table{{width:100%;border-collapse:collapse;font-size:12px;margin-top:10px}}th{{background:#0F2B46;color:#fff;padding:8px}}td{{padding:7px;border-bottom:1px solid #E7EDF3;text-align:center}}tr:nth-child(even){{background:#F7FAFC}}.summary{{margin-top:16px;font-weight:bold;text-align:left;color:#0F2B46}}.footer{{margin-top:28px;text-align:center;border-top:1px solid #ddd;padding-top:6px;color:#777;font-size:10px}}.noprint{{text-align:center;margin:18px}}button{{background:#0F2B46;color:#fff;border:0;border-radius:8px;padding:10px 28px}}@media print{{.noprint{{display:none}}}}</style></head><body><div class='page'>{header}
<table><thead><tr><th>الرقم</th><th>التاريخ</th><th>العميل</th><th>المبلغ (د.ك)</th><th>المرجع</th><th>البيان / الفاتورة</th></tr></thead><tbody>{rows}</tbody></table><div class='summary'>عدد الدفعات: {len(payments)} | الإجمالي: {total:.3f} د.ك</div><div class='footer'>{td.COMPANY_ADDRESS_AR}{td.COMPANY_ADDRESS_EN}{_contact_line()}</div></div><div class='noprint'><button onclick='window.print()'>طباعة</button></div></body></html>"""
        html_content = apply_print_footer(html_content)
        tmp_path = os.path.join(tempfile.gettempdir(), "transport_filtered_payments.html")
        with open(tmp_path, "w", encoding="utf-8") as report_file:
            report_file.write(apply_a4_print_layout(html_content))
        webbrowser.open(f"file://{tmp_path}")

    def open_transaction_report(self, kind):
        """فتح تقرير قابل للطباعة للفواتير أو الدفعات حسب العميل والفترة."""
        dlg = tk.Toplevel(self)
        dlg.title("طباعة الفواتير حسب المدة والعميل" if kind == "invoices" else "طباعة الدفعات حسب المدة والعميل")
        dlg.geometry("560x420")
        dlg.configure(bg=COLOR_CARD)
        dlg.transient(self)
        dlg.grab_set()
        center_dialog(dlg, self)

        customer_var = tk.StringVar(value="الكل")
        from_var = tk.StringVar()
        to_var = tk.StringVar()
        tk.Label(dlg, text="حدد معايير التقرير ثم اضغط طباعة.", font=F_SUBTITLE,
                 bg=COLOR_CARD, fg=COLOR_MUTED, anchor="e").pack(fill="x", padx=18, pady=(16, 8))

        form = tk.Frame(dlg, bg=COLOR_CARD)
        form.pack(fill="x", padx=18)
        tk.Label(form, text="العميل / المخلص", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(anchor="e", padx=6, pady=(7, 3))
        customer_combo = ttk.Combobox(form, textvariable=customer_var,
                                       values=["الكل"] + [c["name"] for c in td.load_customers()],
                                       font=F_BODY, justify="right", state="readonly", width=30)
        customer_combo.pack(fill="x", padx=6, pady=(0, 7))
        tk.Label(form, text="من تاريخ", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(anchor="e", padx=6, pady=(4, 3))
        date_input(form, from_var)
        tk.Label(form, text="إلى تاريخ", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(anchor="e", padx=6, pady=(8, 3))
        date_input(form, to_var)

        def print_report():
            date_from = from_var.get().strip()
            date_to = to_var.get().strip()
            if date_from and date_to and date_from > date_to:
                messagebox.showwarning("تنبيه", "تاريخ البداية يجب أن يسبق تاريخ النهاية.", parent=dlg)
                return
            customer = customer_var.get().strip()
            rows = td.load_invoices() if kind == "invoices" else td.load_payments()
            rows = [row for row in rows
                    if (not customer or customer == "الكل" or safe_str(row.get("customer")).strip() == customer)
                    and (not date_from or safe_str(row.get("date")) >= date_from)
                    and (not date_to or safe_str(row.get("date")) <= date_to)]
            rows.sort(key=lambda row: (safe_str(row.get("date")), td.safe_int(row.get("invoice_no" if kind == "invoices" else "id"))))
            if not rows:
                messagebox.showinfo("لا توجد بيانات", "لا توجد سجلات مطابقة للمعايير المحددة.", parent=dlg)
                return
            if kind == "invoices":
                headers = ("رقم الفاتورة", "التاريخ", "العميل", "رقم البيان", "الإجمالي (د.ك)")
                body = "".join(
                    f"<tr><td>{html.escape(safe_str(r.get('invoice_no')))}</td><td>{html.escape(safe_str(r.get('date')))}</td>"
                    f"<td>{html.escape(safe_str(r.get('customer')))}</td><td>{html.escape(safe_str(r.get('declaration_no')) or '—')}</td>"
                    f"<td>{td.safe_float(r.get('total')):.3f}</td></tr>" for r in rows)
                total = sum(td.safe_float(r.get("total")) for r in rows)
                summary = f"عدد الفواتير: {len(rows)} | الإجمالي: {total:.3f} د.ك"
                title = "تقرير الفواتير الصادرة"
            else:
                headers = ("الرقم", "التاريخ", "العميل", "المبلغ (د.ك)", "المرجع", "البيان / الفاتورة")
                body = "".join(
                    f"<tr><td>{html.escape(safe_str(r.get('id')))}</td><td>{html.escape(safe_str(r.get('date')))}</td>"
                    f"<td>{html.escape(safe_str(r.get('customer')))}</td><td>{td.safe_float(r.get('amount')):.3f}</td>"
                    f"<td>{html.escape(safe_str(r.get('reference')))}</td><td>{html.escape(safe_str(r.get('invoice_no')) or 'دفعة عامة')}</td></tr>" for r in rows)
                total = sum(td.safe_float(r.get("amount")) for r in rows)
                summary = f"عدد الدفعات: {len(rows)} | الإجمالي: {total:.3f} د.ك"
                title = "تقرير دفعات العملاء والمخلصين"
            header_html = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
            report_header = company_letterhead_html(title, document_date=date.today().isoformat())
            html_content = f"""<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'><title>{title}</title>
<style>{LETTERHEAD_PRINT_STYLE}@page{{size:A4;margin:12mm}}body{{font-family:Tahoma,Arial,sans-serif;color:#1C2530;margin:0;background:#F3F6FA}}.page{{max-width:900px;margin:10px auto;background:#fff;min-height:270mm;padding:10px}}h1{{text-align:center;color:#0F2B46;font-size:20px}}.meta{{background:#F5F8FA;border:1px solid #E7EDF3;border-radius:8px;padding:10px;margin:12px 0;text-align:center}}table{{width:100%;border-collapse:collapse;font-size:12px}}th{{background:#0F2B46;color:#fff;padding:8px}}td{{padding:7px;border-bottom:1px solid #E7EDF3;text-align:center}}tr:nth-child(even){{background:#F7FAFC}}.summary{{margin-top:16px;text-align:left;font-weight:bold;color:#0F2B46}}.footer{{margin-top:28px;text-align:center;border-top:1px solid #ddd;padding-top:6px;color:#777;font-size:10px}}.print{{text-align:center;margin:20px}}button{{background:#0F2B46;color:#fff;border:0;border-radius:7px;padding:10px 28px;font-size:14px}}@media print{{.print{{display:none}}}}</style></head>
<body><div class='page'>{report_header}<h1>{title}</h1><div class='meta'>العميل: {html.escape(customer if customer != 'الكل' else 'كل العملاء')} | الفترة: {html.escape(date_from or '—')} إلى {html.escape(date_to or '—')}</div>
<table><thead><tr>{header_html}</tr></thead><tbody>{body}</tbody></table><div class='summary'>{summary}</div><div class='footer'>{html.escape(td.COMPANY_ADDRESS_AR)} — {html.escape(td.COMPANY_ADDRESS_EN)}<br>Tel.: {html.escape(td.COMPANY_PHONE)} — E-mail: {html.escape(td.COMPANY_EMAIL)}</div></div><div class='print'><button onclick='window.print()'>طباعة التقرير</button></div></body></html>"""
            html_content = apply_print_footer(html_content)
            tmp_path = os.path.join(tempfile.gettempdir(), f"transport_{kind}_report.html")
            with open(tmp_path, "w", encoding="utf-8") as report_file:
                report_file.write(apply_a4_print_layout(html_content))
            webbrowser.open(f"file://{tmp_path}")
            dlg.destroy()

        actions = tk.Frame(dlg, bg=COLOR_CARD)
        actions.pack(fill="x", padx=18, pady=20)
        make_btn(actions, "طباعة التقرير", print_report, variant="accent").pack(side="right", padx=4)
        make_btn(actions, "إلغاء", dlg.destroy, variant="secondary").pack(side="right", padx=4)

    def refresh_invoice_account_summary(self):
        if not hasattr(self, "invoice_account_summary_var"):
            return
        customer = self.inv_customer_var.get().strip()
        invoices = [inv for inv in td.load_invoices()
                    if not customer or safe_str(inv.get("customer")).strip() == customer]
        payments = [payment for payment in td.load_payments()
                    if not customer or safe_str(payment.get("customer")).strip() == customer]
        invoice_total = sum(td.safe_float(inv.get("total")) for inv in invoices)
        payment_total = sum(td.safe_float(payment.get("amount")) for payment in payments)
        balance = invoice_total - payment_total
        self.invoice_account_summary_var.set(
            f"إجمالي الفواتير: {invoice_total:.3f} د.ك  |  "
            f"الدفعات: {payment_total:.3f} د.ك  |  "
            f"الرصيد المستحق: {balance:.3f} د.ك"
        )

    def _payment_dialog(self, payment=None):
        payment = payment or {}
        dlg = tk.Toplevel(self)
        dlg.title("تعديل دفعة" if payment else "إضافة دفعة من العميل / المخلص")
        dlg.geometry("620x720")
        dlg.minsize(560, 650)
        dlg.configure(bg=COLOR_CARD)
        dlg.transient(self)
        dlg.grab_set()
        center_dialog(dlg, self)
        tk.Label(dlg, text="يمكن تسجيل الدفعة على الحساب العام أو تخصيصها بفاتورة وبيان محدد.",
                 font=F_SUBTITLE, bg=COLOR_CARD, fg=COLOR_MUTED,
                 anchor="e", justify="right").pack(fill="x", padx=18, pady=(14, 2))
        vars_ = {
            "date": tk.StringVar(value=safe_str(payment.get("date")) or date.today().isoformat()),
            "customer": tk.StringVar(value=safe_str(payment.get("customer")) or self.inv_customer_var.get().strip()),
            "amount": tk.StringVar(value=safe_str(payment.get("amount"))),
            "reference": tk.StringVar(value=safe_str(payment.get("reference"))),
            "invoice_no": tk.StringVar(value=safe_str(payment.get("invoice_no"))),
            "notes": tk.StringVar(value=safe_str(payment.get("notes"))),
        }
        scope_var = tk.StringVar(value="بيان / فاتورة محددة" if vars_["invoice_no"].get().strip()
                                 else "دفعة عامة على الحساب")
        scope_values = ["دفعة عامة على الحساب", "بيان / فاتورة محددة"]
        invoice_list = None
        invoice_choices = []

        fields = [("date", "تاريخ الدفعة"), ("customer", "المخلص / العميل"), ("amount", "المبلغ (د.ك)"),
                  ("reference", "رقم السند / المرجع"), ("payment_scope", "تخصيص الدفعة"),
                  ("invoice_no", "الفواتير المرتبطة (يمكن اختيار أكثر من فاتورة)"), ("notes", "ملاحظات")]
        for key, label in fields:
            tk.Label(dlg, text=label, font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(anchor="e", padx=18, pady=(10, 3))
            if key == "customer":
                customer_combo = ttk.Combobox(dlg, textvariable=vars_[key], values=[c["name"] for c in td.load_customers()],
                                               font=F_BODY, justify="right", state="normal")
                customer_combo.pack(fill="x", padx=18, ipady=3)
            elif key == "date":
                date_input(dlg, vars_[key]).pack(fill="x", padx=18)
            elif key == "payment_scope":
                scope_combo = ttk.Combobox(dlg, textvariable=scope_var, values=scope_values,
                                           font=F_BODY, justify="right", state="readonly")
                scope_combo.pack(fill="x", padx=18, ipady=3)
            else:
                if key == "invoice_no":
                    invoice_list = tk.Listbox(
                        dlg, selectmode="extended", height=6, font=F_BODY,
                        justify="right", exportselection=False,
                        relief="flat", highlightthickness=1,
                        highlightbackground=COLOR_BORDER,
                    )
                    invoice_list.pack(fill="x", padx=18, pady=(0, 3))
                    tk.Label(
                        dlg, text="استخدم Ctrl لاختيار فواتير متفرقة أو Shift لاختيار مجموعة متتالية.",
                        font=(FONT_NAME, 8), bg=COLOR_CARD, fg=COLOR_MUTED,
                        anchor="e", justify="right",
                    ).pack(fill="x", padx=18)
                else:
                    tk.Entry(dlg, textvariable=vars_[key], font=F_BODY, justify="right").pack(fill="x", padx=18, ipady=3)

        def refresh_invoice_choices(*_):
            invoice_choices.clear()
            customer = vars_["customer"].get().strip()
            for inv in td.load_invoices():
                if safe_str(inv.get("customer")).strip() != customer:
                    continue
                number = safe_str(inv.get("invoice_no")).strip()
                declaration = safe_str(inv.get("declaration_no")).strip() or "بدون رقم بيان"
                invoice_choices.append((f"فاتورة {number} — بيان {declaration}", number))
            invoice_list.delete(0, "end")
            selected_numbers = {
                part.strip() for part in vars_["invoice_no"].get().split(",") if part.strip()
            }
            for index, (display, number) in enumerate(invoice_choices):
                invoice_list.insert("end", display)
                if number in selected_numbers:
                    invoice_list.selection_set(index)

        def update_scope_state(*_):
            specific = scope_var.get() == "بيان / فاتورة محددة"
            invoice_list.configure(state="normal" if specific else "disabled")
            if specific:
                refresh_invoice_choices()
            else:
                vars_["invoice_no"].set("")

        customer_combo.bind("<<ComboboxSelected>>", refresh_invoice_choices)
        scope_combo.bind("<<ComboboxSelected>>", update_scope_state)
        refresh_invoice_choices()
        update_scope_state()

        # ---------- مرفقات الدفعة (نفس تصميم شاشة السائقون) ----------
        import uuid as _uuid
        payment_key = safe_str(payment.get("id", "")).strip()
        temp_key = payment_key or f"temp_payment_{_uuid.uuid4().hex}"
        attachment_bar = tk.Frame(dlg, bg=COLOR_CARD)
        attachment_bar.pack(fill="x", padx=18, pady=(4, 0))
        category_frame = tk.Frame(attachment_bar, bg=COLOR_CARD)
        category_frame.pack(side="right")
        tk.Label(category_frame, text="ملفات الدفعة", font=(FONT_NAME, 8, "bold"),
                 bg=COLOR_CARD, fg=COLOR_PRIMARY, anchor="e").pack(anchor="e")
        controls = tk.Frame(category_frame, bg=COLOR_CARD)
        controls.pack(fill="x", anchor="e")
        payment_count_var = tk.StringVar(value="لا توجد ملفات")
        count_label = tk.Label(category_frame, textvariable=payment_count_var,
                               font=(FONT_NAME, 7), bg=COLOR_CARD, fg=COLOR_MUTED,
                               anchor="e")
        count_label.pack(anchor="e")

        def _refresh_payment_counts():
            record_key = safe_str(payment.get("id", "")).strip() or temp_key
            try:
                items = td.load_attachments("payments", str(record_key))
            except Exception:
                items = []
            payment_count_var.set(f"{len(items)} ملف" if items else "لا توجد ملفات")

        make_btn(controls, "إضافة ملفات",
                 lambda: attach_payment_files("ملفات الدفعة"),
                 variant="secondary", padx=5, pady=1).pack(side="right", padx=(0, 3))
        make_btn(controls, "عرض الملفات",
                 lambda: open_payment_manager("ملفات الدفعة"),
                 variant="secondary", padx=5, pady=1).pack(side="right", padx=(3, 0))
        _refresh_payment_counts()

        def attach_payment_files(category_label):
            record_key = safe_str(payment.get("id", "")).strip() or temp_key
            sources = filedialog.askopenfilenames(
                parent=dlg,
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
            for source in sources:
                try:
                    td.add_attachment("payments", record_key, source, notes=category_label)
                except (OSError, ValueError) as exc:
                    messagebox.showerror("المرفقات", str(exc), parent=dlg)
                    return
            messagebox.showinfo("المرفقات", "تمت إضافة الملفات بنجاح.", parent=dlg)
            _refresh_payment_counts()

        def open_payment_manager(category_label):
            record_key = str(safe_str(payment.get("id", "")).strip() or temp_key)
            open_attachment_manager_dialog(dlg, "payments", record_key, category_label,
                                           refresh_callback=_refresh_payment_counts)

        def save():
            if not vars_["customer"].get().strip() or td.safe_float(vars_["amount"].get()) <= 0:
                messagebox.showwarning("تنبيه", "الرجاء اختيار المخلص وإدخال مبلغ دفعة أكبر من صفر.", parent=dlg)
                return
            if scope_var.get() == "بيان / فاتورة محددة":
                selected_invoices = [
                    invoice_choices[index][1] for index in invoice_list.curselection()
                ]
                if not selected_invoices:
                    messagebox.showwarning("تنبيه", "الرجاء اختيار البيان أو الفاتورة المرتبطة بالدفعة.", parent=dlg)
                    return
                vars_["invoice_no"].set(", ".join(selected_invoices))
            else:
                vars_["invoice_no"].set("")
            payment_data = {key: var.get().strip() for key, var in vars_.items()}
            td.save_payment(payment_data, payment.get("id") or None)
            selected_invoice_numbers = {
                number.strip() for number in payment_data["invoice_no"].split(",") if number.strip()
            }
            if selected_invoice_numbers:
                td.mark_invoices_paid(selected_invoice_numbers)
            # نقل مرفقات الدفعة من المفتاح المؤقت إلى المفتاح النهائي
            try:
                saved = next(
                    (row for row in td.load_payments()
                     if str(row.get("customer", "")).strip() == payment_data["customer"]
                     and str(row.get("date", "")).strip() == payment_data["date"]
                     and td.safe_float(row.get("amount")) == td.safe_float(payment_data["amount"])),
                    None,
                )
                if saved is not None:
                    td.move_attachments("payments", temp_key, str(saved.get("id")))
            except Exception as _log_exc: log_exception("save", _log_exc)
            dlg.destroy()
            self.refresh_payment_history()
            refresh_related_screens(self)

        actions = tk.Frame(dlg, bg=COLOR_CARD)
        actions.pack(fill="x", padx=18, pady=18)
        make_btn(actions, "حفظ الدفعة", save, variant="accent").pack(side="right", padx=4)
        make_btn(actions, "إلغاء", dlg.destroy, variant="secondary").pack(side="right", padx=4)

    def add_payment(self):
        self._payment_dialog()

    def edit_selected_payment(self):
        selected = self.payment_tree.selection()
        if not selected:
            messagebox.showinfo("تنبيه", "الرجاء اختيار دفعة من القائمة أولاً.")
            return
        payment = next((p for p in getattr(self, "_payments", []) if str(p.get("id")) == selected[0]), None)
        if payment:
            self._payment_dialog(payment)

    def delete_selected_payment(self):
        selected = self.payment_tree.selection()
        if not selected:
            messagebox.showinfo("تنبيه", "الرجاء اختيار دفعة من القائمة أولاً.")
            return
        if messagebox.askyesno("تأكيد الحذف", "هل تريد حذف الدفعة المحددة؟"):
            td.delete_payment(selected[0])
            self.refresh_payment_history()
            refresh_related_screens(self)

    def print_selected_invoice(self):
        sel = self.inv_tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار فاتورة من القائمة أولاً.")
            return
        invno = sel[0]
        inv = next((i for i in self._invoices if str(i["invoice_no"]) == invno), None)
        if inv:
            generate_and_open_invoice_print(inv)

    def print_selected_invoices(self):
        """طباعة مجموعة من الفواتير المحددة، كل فاتورة في صفحة مستقلة."""
        selected = self.inv_tree.selection()
        if not selected:
            messagebox.showinfo("تنبيه", "الرجاء تحديد فاتورة واحدة أو أكثر للطباعة.")
            return
        selected_numbers = {str(number) for number in selected}
        invoices = [inv for inv in self._invoices
                    if str(inv.get("invoice_no")) in selected_numbers]
        invoices.sort(key=lambda inv: td.safe_int(inv.get("invoice_no")))
        pages = []
        for invoice in invoices:
            page = _build_reference_invoice_page(invoice)
            page = page.replace("</b></div><div><span class='k'>المنفذ:", "</span></div><div><span class='k'>المنفذ:")
            page = page.replace(
                "المنفذ:</span> <span class='v'>—</span>",
                f"رقم بوليصة الشحن:</span> <span class='v'>{html.escape(safe_str(invoice.get('awb_no')) or '—')}</span>",
            )
            container_count = _invoice_container_count(invoice)
            page = page.replace(
                "عدد الحاويات:</span> <span class='v'>—</span>",
                f"عدد الحاويات:</span> <span class='v'>{html.escape(str(container_count) if container_count else '—')}</span>",
            )
            page = re.sub(
                r"<table>.*?</table>",
                _build_invoice_items_table(invoice),
                page,
                count=1,
                flags=re.S,
            )
            page = re.sub(
                r"<div class='letterhead'>.*?</div><div class='rtl-block'>",
                company_letterhead_html(
                    "فاتورة نقداً / بالحساب", invoice.get("invoice_no"), invoice.get("date")
                ) + "<div class='rtl-block'>",
                page,
                count=1,
                flags=re.S,
            )
            pages.append(page)
        html_content = (
            "<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'>"
            "<title>طباعة الفواتير المحددة</title>"
            f"<style>{_REFERENCE_INVOICE_STYLE}{LETTERHEAD_PRINT_STYLE}"
            ".invoice-items{direction:ltr}.invoice-items th,.invoice-items td{text-align:center}.invoice-items .seq-col{width:54px}.invoice-items .money-col{width:62px}.invoice-items .item-en{direction:ltr;text-align:left;font-size:11px}.invoice-items .item-ar{direction:rtl;text-align:right;font-size:12.5px}.invoice-items .total-row td{font-weight:bold;background:#FBF6EA;border-top:2px solid #C99A3D}.invoice-items .total-row td:first-child{text-align:left;direction:ltr}.invoice-items .total-label{color:#0F2B46;margin-right:10px}.invoice-items .total-words{font-size:12px;color:#1C2530}"
            ".page{page-break-after:always}.page:last-of-type{page-break-after:auto}"
            ".noprint{text-align:center;margin:20px}.print-btn{background:#0F2B46;color:#fff;"
            "border:0;border-radius:8px;padding:11px 30px;font-size:14px;cursor:pointer}"
            "@media print{.noprint{display:none}}</style></head><body>"
            + "".join(pages)
            + "<div class='noprint'><button class='print-btn' onclick='window.print()'>طباعة الفواتير</button></div>"
            "</body></html>"
        )
        tmp_path = os.path.join(tempfile.gettempdir(), "transport_selected_invoices.html")
        with open(tmp_path, "w", encoding="utf-8") as report_file:
            report_file.write(apply_a4_print_layout(html_content))
        webbrowser.open(f"file://{tmp_path}")

    def print_customer_statement(self):
        customer = self.inv_customer_var.get().strip()
        if not customer:
            selected = self.inv_tree.selection()
            if selected:
                selected_inv = next((i for i in self._invoices if str(i.get("invoice_no")) == selected[0]), None)
                customer = safe_str(selected_inv.get("customer")) if selected_inv else ""
        if not customer:
            messagebox.showinfo("تنبيه", "الرجاء اختيار عميل أو فاتورة أولاً لطباعة كشف الحساب.")
            return
        invoices = [i for i in td.load_invoices() if safe_str(i.get("customer")) == customer]
        has_payments = any(safe_str(p.get("customer")) == customer for p in td.load_payments())
        if not invoices and not has_payments:
            messagebox.showinfo("تنبيه", "لا توجد حركات مسجلة لهذا العميل.")
            return
        generate_and_open_customer_statement(customer, invoices)

    def delete_selected_invoices(self):
        sel = self.inv_tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار فاتورة واحدة أو أكثر من القائمة أولاً.")
            return
        count = len(sel)
        if messagebox.askyesno(
                "تأكيد حذف الفواتير",
                f"سيتم حذف {count} فاتورة وإلغاء ربط الرحلات والخدمات المرتبطة بها. هل تريد المتابعة؟"):
            for invoice_no in sel:
                td.delete_invoice(invoice_no)
            self.refresh_invoice_history()
            self.refresh_unbilled_lists()
            refresh_related_screens(self)

    # توافق مع أي استدعاء قديم داخل الواجهة.
    def delete_selected_invoice(self):
        self.delete_selected_invoices()

    def edit_selected_invoice(self):
        sel = self.inv_tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار فاتورة من القائمة أولاً.")
            return
        inv = next((i for i in self._invoices if str(i["invoice_no"]) == sel[0]), None)
        if not inv:
            return
        self._invoice_editor_dialog(invoice=inv)

    def _invoice_editor_dialog(self, invoice=None, customer="", trip_ids=None,
                               service_ids=None, items=None, record_type="usage"):
        """نافذة إنشاء/تعديل الفاتورة وبنودها القابلة للتحرير."""
        trip_ids = trip_ids or []
        service_ids = service_ids or []
        if invoice:
            customer = safe_str(invoice.get("customer"))
            try:
                items = json.loads(invoice.get("items_json") or "[]")
            except (TypeError, ValueError, json.JSONDecodeError):
                items = []
        items = items or []
        items = _deduplicate_invoice_items(
            [item for item in items if not _invoice_item_is_disabled(item)])
        if invoice:
            linked_no = safe_str(invoice.get("invoice_no"))
            trip_ids = [t.get("id") for t in td.load_trips()
                        if safe_str(t.get("invoice_no")) == linked_no]
            service_ids = [s.get("id") for s in td.load_services()
                           if safe_str(s.get("invoice_no")) == linked_no]
        selected_trips = {str(t.get("id")): t for t in td.load_trips()}
        selected_services = {str(s.get("id")): s for s in td.load_services()}
        transport_total = sum(td.safe_float(selected_trips[str(tid)].get("fee"))
                              for tid in trip_ids if str(tid) in selected_trips)
        holiday_total = sum(td.safe_float(selected_trips[str(tid)].get("holiday_price"))
                            for tid in trip_ids if str(tid) in selected_trips)
        service_totals = {item: 0.0 for item in SERVICE_INVOICE_ITEMS.values()}
        for sid in service_ids:
            service = selected_services.get(str(sid))
            if not service:
                continue
            item = SERVICE_INVOICE_ITEMS.get(safe_str(service.get("service_type")).strip())
            if item:
                service_totals[item] += td.safe_float(service.get("total"))
        mapped_amounts = {
            "TRANSPORTATION CHARGES — أجور نقل": transport_total,
            "DELAYED TRUCK CHARGES — تأخير شاحنة": holiday_total,
            **service_totals,
        }
        if not invoice:
            items = [{"desc": description, "item_key": description.split(" — ", 1)[0],
                      "amount": round(mapped_amounts.get(description, 0), 3)}
                     for description in INVOICE_FORM_ITEMS]
            # احتفظ بأي خدمة إضافية ليست من نوع عمال كبند مستقل.
            for sid in service_ids:
                service = selected_services.get(str(sid))
                if service and safe_str(service.get("service_type")).strip() not in SERVICE_INVOICE_ITEMS:
                    items.append({
                        "desc": f"{safe_str(service.get('service_type'))} — {safe_str(service.get('date'))}",
                        "amount": round(td.safe_float(service.get("total")), 3),
                    })
        else:
            existing_descriptions = {safe_str(item.get("desc")).strip() for item in items}
            for description in INVOICE_FORM_ITEMS:
                item_key = description.split(" — ", 1)[0]
                matching = next((item for item in items
                                 if safe_str(item.get("item_key")) == item_key
                                 or safe_str(item.get("desc")).strip() == description), None)
                if matching is None:
                    items.append({"desc": description, "item_key": description.split(" — ", 1)[0],
                                  "amount": round(mapped_amounts.get(description, 0), 3)})
                # عند تعديل فاتورة، المبلغ المحفوظ هو القيمة المعتمدة حتى لو
                # تغيرت الرحلات المرتبطة أو تعذر العثور عليها في السجل.
                # تُستخدم mapped_amounts فقط لإضافة بند قياسي مفقود أعلاه.

        dlg = tk.Toplevel(self)
        dlg.title(f"تعديل الفاتورة رقم {invoice['invoice_no']}" if invoice else "إنشاء فاتورة جديدة")
        dlg.geometry("900x720")
        dlg.minsize(760, 600)
        dlg.resizable(True, True)
        dlg.configure(bg=COLOR_CARD)
        dlg.transient(self)
        dlg.grab_set()
        center_dialog(dlg, self)
        date_var = tk.StringVar(value=safe_str(invoice.get("date")) if invoice else date.today().isoformat())
        customer_var = tk.StringVar(value=customer)
        notes_var = tk.StringVar(value=safe_str(invoice.get("notes")) if invoice else "")
        awb_var = tk.StringVar(value=safe_str(invoice.get("awb_no")) if invoice else "")
        declaration_var = tk.StringVar(value=safe_str(invoice.get("declaration_no")) if invoice else "")
        container_var = tk.StringVar(value=safe_str(invoice.get("container_count")) if invoice else "")

        meta = tk.Frame(dlg, bg=COLOR_CARD)
        meta.pack(fill="x", padx=18, pady=(14, 4))
        tk.Label(meta, text="العميل / المخلص", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).grid(row=0, column=1, sticky="e", padx=6)
        ttk.Combobox(meta, textvariable=customer_var,
                     values=[c["name"] for c in td.load_customers()], font=F_BODY,
                     justify="right", state="normal", width=28).grid(row=0, column=0, sticky="ew", padx=6)
        tk.Label(meta, text="تاريخ الفاتورة", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).grid(row=0, column=3, sticky="e", padx=6)
        date_cell = tk.Frame(meta, bg=COLOR_CARD)
        date_cell.grid(row=0, column=2, sticky="ew", padx=6)
        date_input(date_cell, date_var)
        meta.grid_columnconfigure(0, weight=2)
        meta.grid_columnconfigure(2, weight=1)

        tk.Label(dlg, text="رقم بوليصة الشحن", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(anchor="e", padx=18, pady=(4, 3))
        tk.Entry(dlg, textvariable=awb_var, font=F_BODY, justify="right").pack(fill="x", padx=18, ipady=4)

        extra_meta = tk.Frame(dlg, bg=COLOR_CARD)
        extra_meta.pack(fill="x", padx=18, pady=(6, 0))
        tk.Label(extra_meta, text="رقم البيان", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(12, 4))
        tk.Entry(extra_meta, textvariable=declaration_var, font=F_BODY,
                 justify="right", width=24).pack(side="right", padx=4, ipady=3)
        tk.Label(extra_meta, text="عدد الحاويات", font=F_LABEL, bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(18, 4))
        tk.Entry(extra_meta, textvariable=container_var, font=F_BODY,
                 justify="right", width=10).pack(side="right", padx=4, ipady=3)

        tk.Label(dlg, text="بنود الفاتورة (يمكن تعديل الوصف والمبلغ أو إضافة وحذف بنود)",
                 font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(anchor="e", padx=18, pady=(10, 3))
        table = tk.Frame(dlg, bg=COLOR_CARD)
        table.pack(fill="both", expand=True, padx=18)
        tree = ttk.Treeview(table, columns=("description", "amount"), show="headings", selectmode="browse")
        tree.heading("description", text="وصف البند")
        tree.heading("amount", text="المبلغ (د.ك)")
        tree.column("description", anchor="e", stretch=True, width=520)
        tree.column("amount", anchor="center", width=130)
        tree.pack(fill="both", expand=True)
        apply_table_style(tree)
        scrollbar = ttk.Scrollbar(table, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)

        def start_inline_edit(event):
            row_id = tree.identify_row(event.y)
            column = tree.identify_column(event.x)
            if not row_id or column not in ("#1", "#2"):
                return
            idx = int(row_id)
            bbox = tree.bbox(row_id, column)
            if not bbox:
                return
            key = "desc" if column == "#1" else "amount"
            edit_var = tk.StringVar(value=safe_str(items[idx].get(key)))
            editor = tk.Entry(tree, textvariable=edit_var, font=F_BODY, justify="right")
            editor.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
            editor.focus_set()
            editor.select_range(0, "end")

            def commit(event=None):
                value = edit_var.get().strip()
                if key == "amount":
                    value = round(td.safe_float(value), 3)
                if key == "desc" and not value:
                    value = items[idx].get("desc", "")
                items[idx][key] = value
                editor.destroy()
                redraw()

            editor.bind("<Return>", commit)
            editor.bind("<FocusOut>", commit)
            editor.bind("<Escape>", lambda e: editor.destroy())

        tree.bind("<Double-1>", start_inline_edit)

        total_var = tk.StringVar()

        def redraw():
            tree.delete(*tree.get_children())
            for idx, item in enumerate(items):
                tree.insert("", "end", iid=str(idx), values=(safe_str(item.get("desc")), f"{td.safe_float(item.get('amount')):.3f}"))
            total_var.set(f"الإجمالي: {sum(td.safe_float(i.get('amount')) for i in items):.3f} د.ك")

        def edit_item():
            selected = tree.selection()
            if not selected:
                messagebox.showinfo("تنبيه", "الرجاء اختيار بند أولاً.", parent=dlg)
                return
            idx = int(selected[0])
            self._invoice_item_dialog(dlg, items[idx], redraw)

        def add_item():
            item = {"desc": "", "amount": 0}
            self._invoice_item_dialog(dlg, item, lambda: (items.append(item), redraw()))

        def remove_item():
            selected = tree.selection()
            if selected:
                items.pop(int(selected[0]))
                redraw()

        item_actions = tk.Frame(dlg, bg=COLOR_CARD)
        item_actions.pack(fill="x", padx=18, pady=8)
        make_btn(item_actions, "إضافة بند", add_item, variant="accent").pack(side="right", padx=4)
        make_btn(item_actions, "تعديل البند", edit_item, variant="secondary").pack(side="right", padx=4)
        make_btn(item_actions, "حذف البند", remove_item, variant="danger").pack(side="right", padx=4)
        tk.Label(item_actions, textvariable=total_var, font=F_BOLD, bg=COLOR_CARD, fg=COLOR_PRIMARY).pack(side="left", padx=8)
        redraw()

        tk.Label(dlg, text="ملاحظات", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(anchor="e", padx=18, pady=(4, 3))
        tk.Entry(dlg, textvariable=notes_var, font=F_BODY, justify="right").pack(fill="x", padx=18, ipady=4)

        def save_changes():
            if not customer_var.get().strip():
                messagebox.showwarning("تنبيه", "الرجاء إدخال العميل / المخلص.", parent=dlg)
                return
            if not items or any(not safe_str(i.get("desc")).strip() or td.safe_float(i.get("amount")) < 0 for i in items):
                messagebox.showwarning("تنبيه", "يجب إدخال بند واحد على الأقل مع وصف ومبلغ صحيح.", parent=dlg)
                return
            if invoice:
                updated, editing_no = invoice.copy(), invoice["invoice_no"]
            else:
                trips = {str(t["id"]): t for t in td.load_trips()}
                declaration_no = ", ".join(dict.fromkeys(
                    str(trips[str(tid)].get("declaration_no", "")).strip()
                    for tid in trip_ids if str(tid) in trips
                    and str(trips[str(tid)].get("declaration_no", "")).strip()
                ))
                updated, editing_no = {"invoice_no": td.next_invoice_no(customer_var.get().strip()),
                                       "declaration_no": declaration_no}, None
            declaration_value = declaration_var.get().strip()
            if not declaration_value and not invoice:
                declaration_value = updated.get("declaration_no", "")
            container_value = td.safe_int(container_var.get())
            updated.update({"date": date_var.get().strip(), "customer": customer_var.get().strip(),
                            "awb_no": awb_var.get().strip(),
                            "declaration_no": declaration_value,
                            "container_count": container_value if container_value else len({str(tid) for tid in trip_ids if str(tid).strip()}),
                            "items_json": json.dumps(items, ensure_ascii=False),
                            "total": round(sum(td.safe_float(i.get("amount")) for i in items), 3),
                            "notes": notes_var.get().strip(),
                            "record_type": record_type})
            td.save_invoice(updated, editing_invno=editing_no)
            if not invoice:
                for tid in trip_ids:
                    td.mark_trip_invoiced(tid, updated["invoice_no"])
                for sid in service_ids:
                    td.mark_service_invoiced(sid, updated["invoice_no"])
            dlg.destroy()
            self.refresh_unbilled_lists()
            if not invoice and hasattr(self, "show_page"):
                self.show_page("invoices")
            self.refresh_invoice_history()
            if hasattr(self, "after_idle"):
                self.after_idle(self.refresh_invoice_history)
            refresh_related_screens(self)
            messagebox.showinfo("تم", f"تم حفظ الفاتورة رقم {updated['invoice_no']} بإجمالي {updated['total']:.3f} د.ك")

        actions = tk.Frame(dlg, bg=COLOR_CARD)
        actions.pack(fill="x", padx=18, pady=14)
        make_btn(actions, "حفظ الفاتورة", save_changes, variant="accent").pack(side="right", padx=4)
        make_btn(actions, "إلغاء", dlg.destroy, variant="secondary").pack(side="right", padx=4)

    def _invoice_item_dialog(self, parent, item, on_saved):
        dlg = tk.Toplevel(parent)
        dlg.title("تعديل بند الفاتورة")
        dlg.configure(bg=COLOR_CARD)
        dlg.transient(parent)
        dlg.grab_set()
        center_dialog(dlg, parent)
        desc_var = tk.StringVar(value=safe_str(item.get("desc")))
        amount_var = tk.StringVar(value=safe_str(item.get("amount")))
        for var, label in ((desc_var, "وصف البند"), (amount_var, "المبلغ (د.ك)")):
            tk.Label(dlg, text=label, font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(anchor="e", padx=18, pady=(12, 3))
            tk.Entry(dlg, textvariable=var, font=F_BODY, justify="right", width=60).pack(fill="x", padx=18, ipady=4)
        def save_item():
            amount = td.safe_float(amount_var.get())
            if not desc_var.get().strip() or amount < 0:
                messagebox.showwarning("تنبيه", "أدخل وصفاً ومبلغاً صحيحاً.", parent=dlg)
                return
            item.update({"desc": desc_var.get().strip(), "amount": round(amount, 3)})
            dlg.destroy()
            on_saved()
        actions = tk.Frame(dlg, bg=COLOR_CARD)
        actions.pack(fill="x", padx=18, pady=16)
        make_btn(actions, "حفظ البند", save_item, variant="accent").pack(side="right", padx=4)
        make_btn(actions, "إلغاء", dlg.destroy, variant="secondary").pack(side="right", padx=4)
