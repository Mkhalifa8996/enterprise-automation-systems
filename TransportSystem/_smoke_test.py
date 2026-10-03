"""Runtime smoke test: actually build the real window and walk every tab.

This is the test that matters - it proves the split did not just compile,
it proves the application still constructs and every screen still builds.
"""
import os
import sys
import traceback

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

import tkinter as tk  # noqa: E402

from transport import TransportApp  # noqa: E402
from transport.app_config import NAV_ITEMS  # noqa: E402
from transport import data as td  # noqa: E402  (data layer now lives in the package)

failures = []


def check(label, fn):
    try:
        fn()
        print(f"  [OK]   {label}")
        return True
    except Exception as exc:
        print(f"  [FAIL] {label}: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        failures.append(label)
        return False


print("### data layer")
print(f"   exported names in transport.data: {len(td.__all__)}")

# مقارنة بملف البيانات الأصلي للتحقق من عدم فقدان أي اسم (إن كان نسخة
# الإحالة الأصلية ما زالت موجودة؛ اختفت بعد تنظيف الملفات الخاصة).
import ast as _ast  # noqa: E402

_orig_path = os.path.join("_refactor_backup", "transport_data.py")
if os.path.isfile(_orig_path):
    _orig = _ast.parse(open(_orig_path, encoding="utf-8-sig").read())
    _orig_names = set()
    for _n in _orig.body:
        if isinstance(_n, (_ast.FunctionDef, _ast.ClassDef)):
            _orig_names.add(_n.name)
        elif isinstance(_n, _ast.AnnAssign) and isinstance(_n.target, _ast.Name):
            _orig_names.add(_n.target.id)
        elif isinstance(_n, _ast.Assign):
            _orig_names.update(t.id for t in _n.targets if isinstance(t, _ast.Name))
    _lost = sorted(_orig_names - set(td.__all__))
    print(f"   names in original transport_data.py: {len(_orig_names)}")
    print(f"   missing from package: {_lost or '(none)'}")
    if _lost:
        failures.append(f"data layer lost {len(_lost)} names: {_lost[:5]}")
else:
    print("   (original transport_data.py reference removed - skipping comparison)")

check("load trips", lambda: td.load_trips())
check("load drivers", lambda: td.load_drivers())
check("load vehicles", lambda: td.load_vehicles())
check("load customers", lambda: td.load_customers())
check("load companies", lambda: td.load_companies())
check("load invoices", lambda: td.load_invoices())
check("load payments", lambda: td.load_payments())
check("load services", lambda: td.load_services())
check("load_salaries", lambda: td.load_salaries())
check("load_daily_expenses", lambda: td.load_daily_expenses())
check("load_attachments", lambda: td.load_attachments())
check("load_locations", lambda: td.load_locations())
check("financial_summary", lambda: td.financial_summary("2026-09"))
check("driver_names_by_type", lambda: td.driver_names_by_type())
check("current_user", lambda: td.current_user())
check("schemas present", lambda: (td.DRIVER_FIELDS, td.TRIP_FIELDS, td.SHEETS))
check("safe_float / safe_int", lambda: (td.safe_float("1.5"), td.safe_int("3")))
check("demo_counts", lambda: __import__("transport.data.demo_data",
                                       fromlist=["demo_counts"]).demo_counts())

print("\n### print/document builders (pure string work, no GUI)")
from transport import print_invoice, print_letterhead, print_theme, print_statement  # noqa: E402

check("company_letterhead_html", lambda: print_letterhead.company_letterhead_html("فاتورة", "1", "2026-09-30"))
check("apply_print_footer", lambda: print_theme.apply_print_footer("<html>x</html>"))
check("statement_footer_html", lambda: print_theme.statement_footer_html())
check("_english_number_words", lambda: print_invoice._english_number_words(1234))
check("_invoice_money_parts", lambda: print_invoice._invoice_money_parts(1234.5))

print("\n### application window")
app = None
try:
    app = TransportApp()
    print("  [OK]   TransportApp() constructed")
except Exception as exc:
    print(f"  [FAIL] TransportApp(): {type(exc).__name__}: {exc}")
    traceback.print_exc()
    failures.append("TransportApp()")
    sys.exit(1)

try:
    app.update_idletasks()
    check("sidebar rendered", lambda: app.sidebar)
    for key, _icon, label in NAV_ITEMS:
        def visit(k=key, lbl=label):
            app.show_page(k)
            app.update_idletasks()
        check(f"page: {label}", visit)
    check("refresh_home_stats", lambda: (app.refresh_home_stats(), app.update_idletasks()))
    from transport.app_registry import refresh_all_registers
    check("refresh_all_registers", lambda: refresh_all_registers())
except Exception as exc:
    print(f"  [FAIL] during tab walk: {type(exc).__name__}: {exc}")
    traceback.print_exc()
    failures.append("tab walk")
finally:
    try:
        app.destroy()
    except Exception:
        pass

# ---- letterhead must render from configuration, not hardcoded text
print("\n### letterhead built from configuration (no private data hardcoded)")


def letterhead_from_env():
    """Re-import the config with company values set, then render."""
    import importlib
    os.environ["TRANSPORT_COMPANY_NAME_EN"] = "SAMPLE LOGISTICS CO"
    os.environ["TRANSPORT_COMPANY_NAME_AR"] = "شركة تجريبية"
    os.environ["TRANSPORT_COMPANY_ADDRESS_AR"] = "عنوان تجريبي"
    os.environ["TRANSPORT_COMPANY_PHONE"] = "+965 00000000"
    os.environ["TRANSPORT_COMPANY_EMAIL"] = "demo@example.com"
    from transport import data, print_letterhead, print_theme
    # paths.py reads the environment at import time, so the whole config chain
    # has to be reloaded, not just the print helpers.
    for mod in (data.paths, data, print_theme, print_letterhead):
        importlib.reload(mod)
    html_out = print_letterhead.company_letterhead_html("Test", "1", "2026-01-01")
    assert "SAMPLE LOGISTICS CO" in html_out, "company name missing from letterhead"
    assert "شركة تجريبية" in html_out, "arabic name missing from letterhead"
    assert "+965 00000000" in print_theme.PRINT_FOOTER_HTML, "phone missing from footer"
    # clean up so later runs are unaffected
    for k in ("TRANSPORT_COMPANY_NAME_EN", "TRANSPORT_COMPANY_NAME_AR",
              "TRANSPORT_COMPANY_ADDRESS_AR", "TRANSPORT_COMPANY_PHONE",
              "TRANSPORT_COMPANY_EMAIL"):
        os.environ.pop(k, None)
    for mod in (data.paths, data, print_theme, print_letterhead):
        importlib.reload(mod)


check("letterhead renders from env config", letterhead_from_env)

# ---- Firebase: the user must be able to supply their OWN credentials.
# This is the feature that keeps sync working after my project credentials
# were removed, so it is worth proving rather than assuming.
print("\n### Firebase setup accepts user-supplied credentials (no stored creds)")


def firebase_setup_roundtrip():
    cfg_path = os.path.join(td.APP_DIR, "firebase_sync_config.json")

    # 1. nothing stored -> not configured, and no project id baked in
    if os.path.isfile(cfg_path):
        os.remove(cfg_path)
    assert not td.is_firebase_sync_configured(), "should not be configured yet"
    assert td.FIREBASE_DATABASE_URL == "", "a project URL is still hardcoded!"

    # 2. the user saves their own credentials through the normal API
    td.configure_firebase_sync(
        "https://my-own-project-default-rtdb.europe-west1.firebasedatabase.app",
        "AIzaSyMY_OWN_KEY_0000000000",
        "me@example.com",
        "my-own-password",
    )
    cfg = td.get_firebase_sync_config()
    assert cfg["database_url"].startswith("https://my-own-project"), cfg
    assert cfg["api_key"] == "AIzaSyMY_OWN_KEY_0000000000", cfg
    assert cfg["email"] == "me@example.com", cfg
    assert td.is_firebase_sync_configured(cfg), "user credentials not accepted"

    # 3. it must be written next to the app, never inside the package
    assert os.path.dirname(cfg_path) == td.APP_DIR, cfg_path

    # 4. bad input is rejected with a clear message (not silently accepted)
    for bad in ("", "not-a-url", "https://example.com/not-firebase-db"):
        try:
            td.configure_firebase_sync(bad, "key", "a@b.com", "pw")
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted an invalid database url: {bad!r}")

    os.remove(cfg_path)


check("user can configure Firebase with own credentials", firebase_setup_roundtrip)

print("\n" + "=" * 60)
if failures:
    print(f"FAILURES ({len(failures)}): {failures}")
    sys.exit(1)
print("ALL CHECKS PASSED")