# -*- coding: utf-8 -*-
"""
اختبار دخان (Smoke Test) للواجهة الرسومية بدون تشغيل الحلقة الرئيسية:
ينشئ بيانات تجريبية في ملف مؤقت، يفتح النافذة، يتنقل بين كل الشاشات،
يشغّل كل دوال التحديث، يصدر فاتورة فعلياً عبر الواجهة، يفتح نافذة سجل
الفاتورة، ويتحقق من مقاومة الجداول للأسماء المكررة في الملف.

طريقة التشغيل:
    python tests/test_smoke.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# اختبار الدخان يعمل على SQLite (الافتراضي الجديد) مع مسار قاعدة مؤقت.
SANDBOX = os.path.join(tempfile.gettempdir(), "restaurant_smoke_data")
os.makedirs(SANDBOX, exist_ok=True)
os.environ["RESTAURANT_BACKEND"] = "sqlite"
os.environ["RESTAURANT_DB_FILE"] = os.path.join(SANDBOX, "restaurant.db")
os.environ["RESTAURANT_DATA_FILE"] = os.path.join(SANDBOX, "restaurant_data.xlsx")

import restaurant_data as rd

if os.path.exists(os.environ["RESTAURANT_DB_FILE"]):
    os.remove(os.environ["RESTAURANT_DB_FILE"])

# ------------------------ بيانات تجريبية ------------------------
rd.save_customer({"name": "شركة الخليج", "type": "شركة", "phone": "222"})
rd.save_customer({"name": "عائلة الصباح", "type": "عميل مناسبة (فرح / عزيمة)"})
rd.save_staff({"name": "شيف سالم", "job_title": "شيف رئيسي", "base_salary": "400"})
rd.save_institutional_order({"date": rd.date.today().isoformat(), "customer": "شركة الخليج",
                             "meal_type": "غداء", "quantity": "60", "unit_price": "1.250",
                             "delivery_location": "المقر الرئيسي"})
rd.save_event({"event_date": rd.date.today().isoformat(), "customer": "عائلة الصباح",
               "event_type": "عزيمة عائلية", "guests_count": "80", "unit_price": "2.000",
               "deposit": "20"})

import restaurant_desktop_app as app


class FakeMessageBox:
    """بديل لصناديق الحوار حتى لا يتوقف الاختبار بانتظار المستخدم."""

    def __init__(self):
        self.calls = []

    def showinfo(self, title, message="", **kw):
        self.calls.append(("info", title, message))

    def showwarning(self, title, message="", **kw):
        self.calls.append(("warn", title, message))

    def showerror(self, title, message="", **kw):
        self.calls.append(("error", title, message))

    def askyesno(self, title, message="", **kw):
        self.calls.append(("ask", title, message))
        return True

    def last_warning(self):
        for kind, title, message in reversed(self.calls):
            if kind in ("warn", "error"):
                return message
        return ""


fake_mb = FakeMessageBox()
app.messagebox = fake_mb
import ui.dialogs
ui.dialogs.impl = fake_mb   # كل شاشات ui تمرّ عبر نقطة الحوار الوحيدة ui.dialogs

failures = []
checks_run = []


def check(label, fn=None):
    """ينفّذ خطوة اختبار ويسجّل النتيجة. يقبل check(label, fn) أو @check للمُزيّن."""
    if fn is None:
        fn = label
        label = getattr(fn, "__name__", "?")
    checks_run.append(label)
    try:
        result = fn()
        print("  [ OK ] %s" % label)
        return result
    except Exception as exc:                 # noqa: BLE001
        failures.append((label, exc))
        print("  [FAIL] %s -> %s: %s" % (label, type(exc).__name__, exc))
        return None


def assert_true(cond, label):
    assert cond, label


print("1) إنشاء الواجهة والتنقل بين كل الشاشات")
ui = app.RestaurantApp()
ui.update()
for key, _, label in app.NAV_ITEMS:
    check("show_page(%s) - %s" % (key, label), lambda k=key: ui.show_page(k))
ui.update()

print("2) تشغيل دوال التحديث في كل شاشة")
for key, refreshers in ui.page_refreshers.items():
    for fn in refreshers:
        check("refresher %s.%s" % (key, getattr(fn, "__name__", "?")), fn)

print("2.5) الشاشات المجمّعة: التبويبات الفرعية داخل كل شاشة")
@check
def _sub_notebooks_exist():
    for key in ("orders", "invoices", "expenses", "masterdata"):
        assert_true(key in ui.sub_notebooks and key in ui.pages,
                    "الشاشة المجمّعة %s مسجلة بتبويباتها" % key)
    assert_true(len(ui.orders_notebook.tabs()) == 4, "أربعة تبويبات في شاشة الطلبات")
    assert_true(len(ui.invoices_notebook.tabs()) == 3, "ثلاثة تبويبات في شاشة الفواتير")
    assert_true(len(ui.expenses_notebook.tabs()) == 4, "أربعة تبويبات في شاشة المصاريف")
    assert_true(len(ui.masterdata_notebook.tabs()) == 4, "أربعة تبويبات في البيانات الأساسية")


@check
def _switch_all_subtabs():
    for _key, nb in ui.sub_notebooks.items():
        for i in range(len(nb.tabs())):
            nb.select(i)
            ui.update()

print("3) شاشة الفواتير: تحميل القوائم ثم إصدار فاتورة فعلية")
ui.show_page("invoices")
ui.inv_customer_var.set("شركة الخليج")


@check
def _lists_loaded():
    ui.refresh_unbilled_lists()
    assert_true(ui.inv_orders_list.size() == 1, "طلب مؤسسة واحد غير مفوتر متوقع")
    assert_true(ui.inv_events_list.size() == 0, "لا مناسبات لهذا العميل")


@check
def _issue_without_selection():
    fake_mb.calls.clear()
    ui.issue_invoice()
    assert_true("اختيار" in fake_mb.last_warning(), "يجب تنبيه المستخدم لاختيار بنود")
    assert_true(len(rd.load_invoices()) == 0, "لا تُصدر فاتورة بلا بنود")


@check
def _issue_invoice_from_ui():
    ui.inv_orders_list.selection_set(0)
    ui.issue_invoice()
    invoices = rd.load_invoices()
    assert_true(len(invoices) == 1, "يجب إصدار فاتورة واحدة")
    assert_true(abs(rd.safe_float(invoices[0]["total"]) - 75.0) < 0.001,
                "إجمالي الفاتورة 60 × 1.250 = 75")
    assert_true(ui.inv_tree.get_children().__len__() == 1, "الفاتورة ظهرت في سجل الفواتير")
    assert_true(ui.inv_orders_list.size() == 0, "الطلب صار مفوتراً ولم يعد في القائمة")


print("3.5) الميزات الجديدة: عرض سعر، دفعات وكشف حساب، جدولة توصيل")
@check
def _quotation_flow():
    rd.save_quotation({"date": rd.date.today().isoformat(), "customer": "عائلة الصباح",
                       "event_type": "فرح / زفاف", "event_date": rd.date.today().isoformat(),
                       "guests_count": "100", "unit_price": "2.500"})
    q = rd.load_quotations()[-1]
    assert_true(abs(rd.safe_float(q["total"]) - 250.0) < 0.001, "إجمالي عرض السعر")
    assert_true(q["status"] == "معلق", "الحالة الافتراضية معلق")
    ev = rd.convert_quotation_to_event(q["id"])
    q2 = rd.load_quotations()[-1]
    assert_true(q2["status"] == "مقبول" and str(q2["converted_id"]) == str(ev["id"]),
                "تحويل العرض إلى مناسبة وربطهما")
    ui.quotations_tab.refresh()
    ui.events_tab.refresh()


@check
def _payments_and_statement():
    inv = rd.load_invoices()[0]          # فاتورة 75.0 صدرت في القسم السابق
    rd.save_payment({"date": rd.date.today().isoformat(), "invoice_no": inv["invoice_no"],
                     "amount": "50", "method": "كي نت"})
    inv2 = rd.load_invoices()[0]
    assert_true(abs(rd.safe_float(inv2["paid_amount"]) - 50.0) < 0.001,
                "المدفوع بعد الدفعة الجزئية")
    assert_true(inv2["status"] == "جزئية", "حالة الفاتورة بعد دفعة جزئية")
    stmt = rd.customer_statement("شركة الخليج")
    assert_true(abs(stmt["balance"] - 25.0) < 0.001, "رصيد كشف الحساب 25.000")
    ui.refresh_invoice_history()
    ui.refresh_payment_options()
    assert_true(ui.payments_tab.combos["invoice_no"].cget("values"),
                "قائمة الفواتير في تبويب الدفعات ممتلئة")


@check
def _deliveries_tab():
    ui.dlv_date_var.set(rd.date.today().isoformat())
    ui.refresh_deliveries()
    assert_true(len(ui.dlv_tree.get_children()) >= 1,
                "تسليمات اليوم ظهرت في تبويب جدولة التوصيل")
    rows = rd.deliveries_for_date(rd.date.today().isoformat())
    target = rows[0]
    rd.save_delivery_assignment(target["kind"], target["id"],
                                driver="سالم", vehicle="سيارة 1")
    ui.refresh_deliveries()
    assert_true(True, "إسناد التوصيل وتحديث الجدول دون أخطاء")


print("4) نافذة سجل الفاتورة")
@check
def _invoice_record_window():
    from ui.record_window import RecordPrintWindow
    ui.inv_tree.selection_set(ui.inv_tree.get_children()[0])
    win = RecordPrintWindow(ui, "سجل تجريبي", [("a", "حقل", "قيمة")],
                            printer_html_fn=lambda: None, bill_title="طباعة")
    win.update()
    win.destroy()


@check
def _selected_invoice_lookup():
    ui.inv_tree.selection_set(ui.inv_tree.get_children()[0])
    inv = ui.selected_invoice()
    assert_true(inv is not None and inv["invoice_no"] == rd.load_invoices()[0]["invoice_no"],
                "يجب إرجاع الفاتورة المحددة من الجدول")


print("5) مقاومة الجدول لأسماء مكررة/فارغة في الملف")
@check
def _duplicate_names_dont_crash():
    # على SQLite (الافتراضي) لا يمكن كتابة المفتاح الفارغ — نتحقق من عرض
    # المحتوى الحالي فقط؛ تغطية Excel القديم تبقى في test_launch_real_data.
    before = len(ui.customers_tab.tree.get_children())
    ui.customers_tab.refresh()
    assert_true(len(ui.customers_tab.tree.get_children()) == before,
                "يجب رسم كل العملاء دون سقوط الواجهة")


@check
def _duplicate_name_rejected_via_form():
    tab = ui.customers_tab
    tab.clear_form()
    tab.vars["name"].set("شركة الخليج")
    tab.vars["type"].set("شركة")
    fake_mb.calls.clear()
    tab.on_save()
    assert_true("موجود" in fake_mb.last_warning(), "يجب رفض الاسم المكرر من النموذج")


print("6) شاشة التقارير: التحقق من صحة الفترة والملخص")
ui.show_page("reports")


@check
def _summary_with_period():
    ui.rep_from.set("2026-01-01")
    ui.rep_to.set("2026-01-31")
    fake_mb.calls.clear()
    ui.show_financial_summary()
    text = ui.report_text.get("1.0", "end")
    assert_true("الفترة" in text and "الإيرادات" in text, "يجب عرض ملخص الفترة")
    assert_true("daily_expenses_total" not in text, "لا توجد مفاتيح برمجية في التقرير")


@check
def _summary_rejects_bad_date():
    ui.rep_from.set("01/01/2026")
    fake_mb.calls.clear()
    ui.show_financial_summary()
    assert_true("YYYY-MM-DD" in fake_mb.last_warning(), "يجب رفض صيغة التاريخ")
    ui.rep_from.set("")


print("7) إغلاق الواجهة")
check("إغلاق النافذة", ui.destroy)

print()
print("النتيجة: %d ناجح / %d فاشل من %d خطوة اختبار"
      % (len(checks_run) - len(failures), len(failures), len(checks_run)))
for label, exc in failures:
    print(" - %s -> %r" % (label, exc))
if failures:
    sys.exit(1)
print("كل اختبارات الدخان نجحت.")