# -*- coding: utf-8 -*-
"""اختبارات طبقة البيانات: قاعدة البيانات، الترحيل من إكسل، والحسابات.

تُشغَّل مع:  python -m pytest tests -q
كل اختبار يعمل على قاعدة بيانات مؤقتة معزولة (عبر CCB_DB_PATH)
حتى لا يلمس بيانات المستخدم الحقيقية.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def data(tmp_path, monkeypatch):
    """طبقة بيانات معزولة تماماً لكل اختبار.

    المسارات تُقرأ من `config` عند الاستدعاء، فنكفي توجيهها هنا.
    """
    import customs_clearance_billing.config as config
    import customs_clearance_billing.data as data_pkg

    monkeypatch.setattr(config, "DB_FILE", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "DATA_FILE", str(tmp_path / "data.xlsx"))
    monkeypatch.setattr(data_pkg, "_migration_done", False, raising=False)
    return data_pkg


def make_invoice(invno="010001", customer="Wazzan", **overrides):
    inv = {
        "invno": invno,
        "date": "2026-07-11",
        "customer": customer,
        "declno": "434343",
        "decldate": "2026-07-10",
        "port": "الشعب",
        "containercount": "2",
        "goodstype": "بضائع",
        "origin": "الكويت",
        "notes": "ملاحظة",
        "items": [],
    }
    inv.update(overrides)
    return inv


def make_items(dinar=0, fils=0, count=1):
    """يبني بنود فاتورة: البند الأول بقيمة، والباقي صفر."""
    items = []
    for i in range(24):
        items.append({
            "label": f"بند {i}", "labelEn": f"Item {i}",
            "dinar": dinar if i < count else 0,
            "fils": fils if i < count else 0,
        })
    return items


# ------------------------------------------------------------------ العملاء
def test_customers_crud(data):
    data.save_customer({"name": "Wazzan", "phone": "123", "address": "a", "notes": "n",
                        "company_code": "1"})
    assert [c["name"] for c in data.load_customers()] == ["Wazzan"]
    # company_code يُطبَّع إلى رقمين
    assert data.load_customers()[0]["company_code"] == "01"

    data.save_customer({"name": "Wazzan", "phone": "999", "company_code": "01"})
    updated = data.load_customers()[0]
    assert updated["phone"] == "999"
    assert len(data.load_customers()) == 1  # التحديث لا يُنشئ نسخة مكررة

    data.delete_customer("Wazzan")
    assert data.load_customers() == []


# ------------------------------------------------------------------ الفواتير
def test_invoice_total_computed_from_items(data):
    data.save_invoice(make_invoice(items=make_items(dinar=10, fils=250)))
    inv = data.load_invoices()[0]
    # 10 دينار + 250 فلس = 10.250
    assert inv["total"] == pytest.approx(10.25)
    assert len(inv["items"]) == 24


def test_invoice_upsert_and_rename(data):
    data.save_invoice(make_invoice("010001", items=make_items(dinar=5)))
    data.save_invoice(make_invoice("010001", items=make_items(dinar=7)))
    invs = data.load_invoices()
    assert len(invs) == 1 and invs[0]["total"] == pytest.approx(7.0)

    # تغيير رقم الفاتورة عند التعديل لا يترك نسخة قديمة
    data.save_invoice(make_invoice("010002", items=make_items(dinar=9)),
                      editing_invno="010001")
    invs = sorted(i["invno"] for i in data.load_invoices())
    assert invs == ["010002"]


def test_invoice_items_replaced_not_duplicated(data):
    data.save_invoice(make_invoice("010001", items=make_items(dinar=3, count=3)))
    data.save_invoice(make_invoice("010001", items=make_items(dinar=1, count=1)))
    inv = data.load_invoices()[0]
    assert len(inv["items"]) == 24
    assert sum(1 for it in inv["items"] if it["dinar"]) == 1


def test_delete_invoice_removes_items(data):
    data.save_invoice(make_invoice("010001", items=make_items(dinar=2)))
    data.delete_invoice("010001")
    assert data.load_invoices() == []
    conn = data.ensure_database()
    try:
        assert conn.execute("SELECT COUNT(*) FROM invoice_items").fetchone()[0] == 0
    finally:
        conn.close()


def test_save_invoice_requires_number(data):
    with pytest.raises(data.SaveError):
        data.save_invoice(make_invoice(invno=""))


# ------------------------------------------------------------------ الدفعات
def test_payment_crud_and_allocation_order(data):
    data.save_invoice(make_invoice("010001", items=make_items(dinar=100)))
    data.save_payment({"id": "010001", "customer": "Wazzan", "date": "2026-07-30",
                       "amount": 40.0, "notes": "", "applied_invoices": ["010001"]})
    p = data.load_payments()[0]
    assert p["amount"] == pytest.approx(40.0)
    assert p["applied_invoices"] == ["010001"]

    data.delete_payment("010001")
    assert data.load_payments() == []


def test_payment_update_clears_old_allocation(data):
    data.save_payment({"id": "010001", "customer": "A", "amount": 10,
                       "applied_invoices": ["010001", "010002"]})
    data.save_payment({"id": "010001", "customer": "A", "amount": 20,
                       "applied_invoices": []}, editing_id="010001")
    p = data.load_payments()[0]
    assert p["amount"] == pytest.approx(20.0)
    assert p["applied_invoices"] == []