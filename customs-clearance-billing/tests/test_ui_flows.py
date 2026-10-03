# -*- coding: utf-8 -*-
"""اختبارات تشغيل الواجهة فعلياً: تحاكي ضغطات المستخدم على النماذج والأزرار.

تبني النافذة الحقيقية وتستدعي دوالها كما يفعل المستخدم (حفظ عميل، حفظ فاتورة
من النافذة، تسجيل دفعة وتخصيصها، طباعة، تصدير CSV، بحث وتصفية، حذف)، مع
استبدال نوافذ الرسائل بالإutral，让她 لا تتوقف بانتظار ضغطة المستخدم.
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


_APP = None  # نافذة واحدة لكل جلسة الاختبار: إنشاء جذور Tk متكررة يُفسد المفسّر


@pytest.fixture(scope="session")
def _session_app():
    """نافذة واحدة تُنشأ مرة واحدة، لأن Tk لا يتحمّل إتلاف جذر ثم إنشاؤه من جديد."""
    global _APP
    import customs_clearance_billing.config as config
    import customs_clearance_billing.data as data_pkg

    tmp = tempfile.mkdtemp(prefix="customs_clearance_billing_ui_")
    config.DB_FILE = os.path.join(tmp, "t.db")
    config.DATA_FILE = os.path.join(tmp, "t.xlsx")
    data_pkg._migration_done = False

    from customs_clearance_billing.ui.app import InvoiceApp

    _APP = InvoiceApp()
    yield _APP
    try:
        _APP.destroy()
    except Exception:
        pass


@pytest.fixture()
def ui(monkeypatch, _session_app):
    """نافذة التطبيق معزولة عن بيانات المستخدم في كل اختبار.

    تُحذف ملفات التخزين قبل كل اختبار فتبدأ كل حالة من قاعدة بيانات نظيفة،
    دون الحاجة لإعادة إنشاء نافذة Tk.
    """
    import tkinter.messagebox as mb

    import customs_clearance_billing.config as config
    import customs_clearance_billing.data as data_pkg

    for path in (config.DB_FILE, config.DATA_FILE,
                 config.DB_FILE + "-wal", config.DB_FILE + "-shm"):
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
    monkeypatch.setattr(data_pkg, "_migration_done", False, raising=False)

    # نلتقط الرسائل بدل عرضها على المستخدم
    calls = []

    def _record(kind):
        return lambda *a, **k: calls.append((kind, a))

    monkeypatch.setattr(mb, "showinfo", _record("info"))
    monkeypatch.setattr(mb, "showwarning", _record("warn"))
    monkeypatch.setattr(mb, "showerror", _record("error"))
    monkeypatch.setattr(mb, "askyesno", lambda *a, **k: True)
    monkeypatch.setattr(mb, "askokcancel", lambda *a, **k: True)

    _session_app.test_messages = calls
    _session_app.update_idletasks()
    yield _session_app
    try:
        _session_app.update_idletasks()
    except Exception:
        pass


def seed_invoice(invno="010001", customer="Ali", dinar=0, fils=0, filled=1, **over):
    """ينشئ عميلاً وفاتورة مباشرة عبر طبقة البيانات.

    `filled` يحدد عدد البنود التي تحمل قيمة (الباقي صفر)، تماماً كما يحدث
    عادةً في الاستخدام الحقيقي.
    """
    from customs_clearance_billing.data import save_customer, save_invoice

    save_customer({"name": "Ali", "company_code": "01"})
    save_customer({"name": "Sara", "company_code": "02"})
    items = [{"label": "", "labelEn": "", "dinar": dinar, "fils": fils}
             for _ in range(filled)]
    items += [{"label": "", "labelEn": "", "dinar": 0, "fils": 0}] * (24 - filled)
    inv = {
        "invno": invno, "date": "2026-01-01", "customer": customer,
        "declno": "", "decldate": "", "port": "", "containercount": "",
        "goodstype": "", "origin": "", "notes": "", "items": items,
    }
    inv.update(over)
    save_invoice(inv)
    return inv


# ------------------------------------------------------------------ العملاء
def test_ui_customer_form_saves(ui):
    from customs_clearance_billing.data import load_customers, next_available_company_code, save_customer

    code = next_available_company_code()
    assert code == "01"
    # النموذج يمنح رمز الشركة تلقائياً؛ نحاكي حفظ العميل عبر البيانات ثم التحديث
    save_customer({"name": "Ali", "phone": "900", "address": "KWT",
                   "notes": "VIP", "company_code": code})
    ui.refresh_customer_list()
    ui.update_idletasks()

    assert [c["name"] for c in load_customers()] == ["Ali"]
    assert load_customers()[0]["company_code"] == "01"
    assert len(ui.cust_tree.get_children()) == 1


def test_ui_customer_form_requires_name(ui):
    ui.c_name.set("")
    ui.save_customer_form()
    assert any(kind == "warn" for kind, _ in ui.test_messages)


# ------------------------------------------------------------------ الفواتير
def test_ui_invoice_form_saves(ui):
    from customs_clearance_billing.data import load_invoices, save_customer
    from customs_clearance_billing.ui.invoice_form import InvoiceForm

    save_customer({"name": "Ali", "company_code": "01"})
    ui.refresh_customer_list()

    form = InvoiceForm(ui, invoice=None)
    form.update_idletasks()

    # اختيار العميل يولّد رقم الفاتورة تلقائياً
    form.vars["customer"].set("Ali")
    form._update_invno_for_customer()
    assert form.vars["invno"].get() == "010001"

    form.item_dinar_vars[0].set("100")
    form.item_fils_vars[0].set("250")
    form.notes_text.insert("1.0", "ملاحظة اختبار")
    form._update_total()

    form.save()
    ui.update_idletasks()

    invoices = load_invoices()
    assert len(invoices) == 1
    assert invoices[0]["invno"] == "010001"
    assert invoices[0]["total"] == pytest.approx(100.25)
    assert invoices[0]["notes"] == "ملاحظة اختبار"
    assert len(invoices[0]["items"]) == 24
    assert invoices[0]["items"][0]["dinar"] == 100
    assert len(ui.tree.get_children()) == 1


def test_ui_invoice_form_requires_customer(ui):
    from customs_clearance_billing.ui.invoice_form import InvoiceForm

    form = InvoiceForm(ui, invoice=None)
    form.update_idletasks()
    form.vars["customer"].set("")
    form.save()
    ui.update_idletasks()
    assert any(kind == "warn" for kind, _ in ui.test_messages)


def test_ui_invoice_form_rejects_duplicate_number(ui):
    """رقم مكرر يجب أن يُرفض.

    نستخدم عميلاً بلا رمز شركة حتى لا يولّد النموذج رقماً تلقائياً، فيبقى
    الرقم المُدخَل يدوياً كما هو ويظهر تحذير التكرار.
    """
    from customs_clearance_billing.data import load_invoices, save_customer
    from customs_clearance_billing.ui.invoice_form import InvoiceForm

    seed_invoice("010001", "Ali", dinar=1)
    save_customer({"name": "NoCode", "company_code": ""})

    form = InvoiceForm(ui, invoice=None)
    form.update_idletasks()
    form.vars["customer"].set("NoCode")
    form.vars["invno"].set("010001")  # رقم مستخدم بالفعل
    form.save()
    ui.update_idletasks()

    assert any(kind == "warn" for kind, _ in ui.test_messages)
    assert len(load_invoices()) == 1


def test_ui_invoice_form_edits_existing(ui):
    from customs_clearance_billing.data import load_invoices
    from customs_clearance_billing.ui.invoice_form import InvoiceForm

    seed_invoice("010001", "Ali", dinar=10)
    ui.refresh_invoice_list()

    existing = load_invoices()[0]
    form = InvoiceForm(ui, invoice=existing)
    form.update_idletasks()
    assert form.editing_invno == "010001"

    form.item_dinar_vars[0].set("20")
    form.save()
    ui.update_idletasks()

    invoices = load_invoices()
    assert len(invoices) == 1
    assert invoices[0]["total"] == pytest.approx(20.0)
# ------------------------------------------------------------------ الدفعات
def test_ui_payment_saves_with_auto_receipt(ui):
    """تسجيل دفعة عبر النموذج يجب أن يولّد رقم السند تلقائياً."""
    from customs_clearance_billing.data import load_payments

    seed_invoice("010001", "Ali", dinar=100)
    ui.refresh_invoice_list()

    ui.p_customer.set("Ali")
    ui.p_date.set("2026-02-01")
    ui.p_amount.set("40")
    ui.p_notes.set("دفعة نقدية")
    ui._on_payment_customer_changed()
    ui.update_idletasks()

    # معاينة رقم السند القادم في النموذج
    assert "010001" in ui.p_receipt_preview_var.get()

    ui.save_payment_form()
    ui.update_idletasks()

    payments = load_payments()
    assert len(payments) == 1
    assert payments[0]["id"] == "010001"        # رقم السند تولّد تلقائياً
    assert payments[0]["amount"] == pytest.approx(40.0)
    assert payments[0]["customer"] == "Ali"
    assert payments[0]["notes"] == "دفعة نقدية"
    assert len(ui.pay_tree.get_children()) == 1
    assert len(ui.bal_tree.get_children()) == 1


def test_ui_payment_allocated_to_specific_invoice(ui):
    from customs_clearance_billing.data import invoice_payment_status, load_payments

    seed_invoice("010001", "Ali", dinar=100)
    seed_invoice("010002", "Ali", dinar=200)
    ui.refresh_invoice_list()

    ui.p_customer.set("Ali")
    ui.p_amount.set("50")
    ui._on_payment_customer_changed()
    ui.update_idletasks()

    # اختيار الفاتورة الأولى فقط للتخصيص
    ui.p_invoices_tree.selection_set("010001")
    ui._update_alloc_summary()
    assert ui._selected_payment_invoices() == ["010001"]
    ui.save_payment_form()
    ui.update_idletasks()

    payments = load_payments()
    assert payments[0]["applied_invoices"] == ["010001"]

    from customs_clearance_billing.data import load_invoices
    status = invoice_payment_status(load_invoices(), load_payments())
    assert status["010001"]["paid"] == pytest.approx(50.0)
    assert status["010002"]["paid"] == pytest.approx(0.0)


def test_ui_payment_requires_customer_and_amount(ui):
    from customs_clearance_billing.data import load_payments

    ui.p_customer.set("")
    ui.save_payment_form()
    ui.p_customer.set("Ali")
    ui.p_amount.set("0")
    ui.save_payment_form()
    ui.update_idletasks()
    assert load_payments() == []
    assert sum(1 for k, _ in ui.test_messages if k == "warn") >= 2


def test_ui_payment_edit_and_delete(ui):
    from customs_clearance_billing.data import load_payments

    seed_invoice("010001", "Ali", dinar=100)
    ui.refresh_invoice_list()

    ui.p_customer.set("Ali")
    ui.p_amount.set("10")
    ui._on_payment_customer_changed()
    ui.save_payment_form()
    ui.update_idletasks()
    assert load_payments()[0]["amount"] == pytest.approx(10.0)

    # تحميل الدفعة للتعديل ثم حذفها
    ui.pay_tree.selection_set("010001")
    ui.load_payment_into_form()
    ui.update_idletasks()
    ui.delete_selected_payment()
    ui.update_idletasks()
    assert load_payments() == []


# ------------------------------------------------------------------ البحث والتصفية
def test_ui_invoice_search_and_filters(ui):
    seed_invoice("010001", "Ali", dinar=1)
    seed_invoice("010002", "Sara", dinar=1)
    seed_invoice("020001", "Sara", dinar=1)
    ui.refresh_invoice_list()
    assert len(ui.tree.get_children()) == 3

    ui.search_var.set("Sara")
    ui.refresh_invoice_list()
    assert len(ui.tree.get_children()) == 2

    ui.search_var.set("")
    ui.filter_customer_var.set("Ali")
    ui.refresh_invoice_list()
    assert len(ui.tree.get_children()) == 1

    ui.clear_invoice_filters()
    ui.update_idletasks()
    assert len(ui.tree.get_children()) == 3


def test_ui_delete_invoice_flow(ui):
    from customs_clearance_billing.data import load_invoices

    seed_invoice("010001", "Ali", dinar=1)
    ui.refresh_invoice_list()
    assert len(ui.tree.get_children()) == 1

    ui.tree.selection_set("010001")
    ui.delete_selected_invoice()
    ui.update_idletasks()
    assert load_invoices() == []
    assert len(ui.tree.get_children()) == 0


# ------------------------------------------------------------------ الطباعة والتصدير
def _html_from_url(url):
    """يقرأ ملف HTML الذي كتبته دالة الطباعة من رابط file:// الذي فتحته."""
    path = url.split("file://", 1)[1].lstrip("/")
    return open(path, encoding="utf-8").read()


def test_ui_print_invoice_document(ui, monkeypatch):
    from customs_clearance_billing.data import load_invoices, save_invoice
    from customs_clearance_billing.ui import printing

    seed_invoice("010001", "Ali", dinar=12, fils=500,
                 declno="55", port="الشعب", notes="ملاحظة طباعة")
    inv = load_invoices()[0]
    inv["items"][0]["label"] = "بند مطبوع"
    inv["items"][0]["labelEn"] = "Printed item"
    save_invoice(inv)

    opened = {}
    monkeypatch.setattr(printing.webbrowser, "open",
                        lambda url: opened.setdefault("url", url))
    printing.generate_and_open_invoices_print(load_invoices())

    assert "url" in opened and opened["url"].startswith("file://")
    html = _html_from_url(opened["url"])
    assert "010001" in html        # رقم الفاتورة
    assert "Ali" in html           # اسم العميل
    assert "بند مطبوع" in html  # التسمية المخصّصة
    # المجموع يُطبع بالدينار والفلس في عمودين منفصلين (12 دينار / 500 فلس)
    assert "<td class=\"c\">12</td>" in html
    assert "<td class=\"c\">500</td>" in html
    # والمبلغ مكتوب بالكلمات (عربي وإنجليزي)
    assert "twelve" in html
    assert "دينار" in html


def test_ui_print_statement_document(ui, monkeypatch):
    from customs_clearance_billing.data import load_invoices, load_payments
    from customs_clearance_billing.ui import printing

    seed_invoice("010001", "Ali", dinar=100)
    opened = {}
    monkeypatch.setattr(printing.webbrowser, "open",
                        lambda url: opened.setdefault("url", url))
    printing.generate_and_open_statement("Ali", "", "", load_invoices(), load_payments())

    html = _html_from_url(opened["url"])
    assert "010001" in html
    assert "Ali" in html


def test_ui_export_invoices_csv(ui, monkeypatch, tmp_path):
    seed_invoice("010001", "Ali", dinar=5, declno="77")
    ui.refresh_invoice_list()

    target = tmp_path / "export.csv"
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename",
                        lambda *a, **k: str(target))
    ui.export_invoices_csv()
    ui.update_idletasks()

    assert target.exists()
    content = target.read_text(encoding="utf-8-sig")
    assert "010001" in content
    assert "Ali" in content


def test_ui_dashboard_reflects_data(ui):
    from customs_clearance_billing.data import get_dashboard_stats

    seed_invoice("010001", "Ali", dinar=100)
    ui.refresh_invoice_list()
    ui.refresh_dashboard()
    ui.update_idletasks()

    stats = get_dashboard_stats()
    assert stats["invoice_count"] == 1
    # بطاقة عدد الفواتير تعرض القيمة
    assert "1" in ui.kpi_vars["invoice_count"][0].get()
