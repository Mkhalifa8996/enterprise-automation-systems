# -*- coding: utf-8 -*-
"""
اختبارات المرحلة الحديثة (الرسوم + PDF العربي): تعمل بـ pytest مباشرة.

    pytest tests/test_modern.py -v

تعمل على قاعدة بيانات مؤقتة تُملأ ببيانات نموذجية عند البدء، حتى تنجح على أي
جهاز جديد بدون الحاجة لملف بيانات حقيقي.
"""

import os
import shutil
import tempfile

import pytest

# يجب ضبط المسارات قبل استيراد restaurant_data لأنه يقرأها عند الإقلاع
SANDBOX = os.path.join(tempfile.gettempdir(), "restaurant_modern_tests")
shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(SANDBOX, exist_ok=True)
os.environ["RESTAURANT_BACKEND"] = "sqlite"
os.environ["RESTAURANT_DB_FILE"] = os.path.join(SANDBOX, "modern.db")
os.environ["RESTAURANT_DATA_FILE"] = os.path.join(SANDBOX, "unused.xlsx")

import restaurant_data as rd  # noqa: E402
from core.analytics import monthly_series, receivables_by_client, top_clients  # noqa: E402


def _seed():
    """بيانات نموذجية: عميل وطلب مناسبة وفاتورة، تكفي للرسوم وكشف الحساب و PDF."""
    rd.save_customer({"name": "شركة الاختبار", "type": "شركة", "phone": "1234"})
    rd.save_purchase({"date": rd.date.today().isoformat(), "type": "لحوم ودواجن",
                      "item": "دجاج", "quantity": "10", "unit": "كجم",
                      "unit_cost": "3.5"})
    rd.save_institutional_order({"date": rd.date.today().isoformat(),
                                 "customer": "شركة الاختبار", "meal_type": "غداء",
                                 "quantity": "25", "unit_price": "2.750"})
    order = rd.load_institutional_orders()[0]
    rd.create_invoice_for_customer("شركة الاختبار", [order["id"]], [])
    invoice = rd.load_invoices()[0]
    rd.save_payment({"date": rd.date.today().isoformat(),
                     "invoice_no": invoice["invoice_no"], "amount": "10.0"})


_seed()


def _pdf_deps():
    try:
        import reportlab  # noqa: F401
        import arabic_reshaper  # noqa: F401
        import bidi  # noqa: F401
        return True
    except ImportError:
        return False


needs_pdf = pytest.mark.skipif(not _pdf_deps(), reason="حزم PDF العربي غير مثبتة")


def test_analytics_monthly_series_shape():
    rows = monthly_series(6)
    assert len(rows) == 6
    for r in rows:
        for key in ("month", "revenue", "purchases", "salaries",
                    "fixed", "petty", "expenses", "profit"):
            assert key in r
        assert rd.is_month(r["month"])
        assert abs(r["profit"] - (r["revenue"] - r["expenses"])) < 0.002


def test_analytics_top_clients_sorted():
    top = top_clients(5)
    assert isinstance(top, list)
    vals = [v for _, v in top]
    assert vals == sorted(vals, reverse=True)


def test_analytics_receivables_non_negative():
    for _, rest in receivables_by_client():
        assert rest >= 0


def test_charts_draw_without_crash(tmp_path):
    plt = pytest.importorskip("matplotlib.pyplot")
    plt.switch_backend("Agg")
    from matplotlib.figure import Figure
    from ui.pages.charts import draw_charts

    fig = Figure(figsize=(8, 4.2), dpi=80)
    draw_charts(fig, months=3)
    out = tmp_path / "charts.png"
    fig.savefig(out)
    assert out.stat().st_size > 1000


def test_invoice_pdf_builds(tmp_path):
    pytest.importorskip("reportlab")
    from core.pdf_ar import invoice_pdf

    invs = rd.load_invoices()
    assert invs, "لا توجد فواتير في قاعدة البيانات للاختبار"
    inv = invs[0]
    items = [(it.get("desc", ""), it.get("amount", 0)) for it in rd.invoice_items(inv)]
    assert items
    out = str(tmp_path / "inv.pdf")
    invoice_pdf(inv, items, out)
    assert os.path.getsize(out) > 5000


def test_statement_pdf_builds(tmp_path):
    pytest.importorskip("reportlab")
    from core.pdf_ar import statement_pdf

    invs = rd.load_invoices()
    assert invs
    s = rd.customer_statement(invs[0]["customer"])
    out = str(tmp_path / "stmt.pdf")
    statement_pdf(s, None, None, out)
    assert os.path.getsize(out) > 5000


def test_summary_pdf_builds(tmp_path):
    pytest.importorskip("reportlab")
    from core.pdf_ar import summary_pdf

    out = str(tmp_path / "summary.pdf")
    summary_pdf(rd.financial_summary(), None, None, out)
    assert os.path.getsize(out) > 5000
