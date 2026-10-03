# -*- coding: utf-8 -*-
"""اختبار دخان: تشغيل الواجهة فعلياً في وضع لا رئيسي والتحقق من بناء التبويبات."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    import customs_clearance_billing.data as data

    data.ensure_storage()
    print("storage ready")

    from customs_clearance_billing.ui.app import InvoiceApp

    app = InvoiceApp()
    app.update_idletasks()
    app.update()

    # التحقق من بناء كل التبويبات وربطها بالواجهة
    checks = {
        "dashboard": app.debtors_tree,
        "invoices": app.tree,
        "customers": getattr(app, "cust_tree", None),
        "payments": app.pay_tree,
        "balances": app.bal_tree,
    }
    for name, widget in checks.items():
        assert widget is not None, f"tab {name} not built"
        print(f"  {name}: rows={len(widget.get_children())}")

    app.open_new_invoice()
    app.update()
    print("invoice form opened ok")
    app.destroy()
    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    main()