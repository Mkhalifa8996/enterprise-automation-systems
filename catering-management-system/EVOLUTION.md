# Evolution Plan — نظام إدارة مطعم التموين والولائم (Restaurant / Catering Manager)

Target app: `restaurant_desktop_app.py` (Tkinter UI) + `restaurant_data.py` (Excel data
layer) + `restaurant_data.xlsx` (the single source of truth).

---

## 1. Where the app stands after this repair pass

### 1.1 Blocking defects that were fixed (verified by tests)

| # | Defect | Impact before | Fix |
|---|--------|---------------|-----|
| 1 | 19 lines contained literal `\"` escape artefacts (e.g. `self.title(title or \"عرض السجل\")`) | **The file raised `SyntaxError` — the app could never start** | Escapes removed; the offending class rewritten cleanly |
| 2 | `class RecordPrintWindow` was spliced *inside* `RestaurantApp._build_invoices_tab()` | Every later method (`_build_invoices_tab`, `_build_salaries_tab`, `_build_reports_tab`, `issue_invoice`, `show_financial_summary` …) became a method of the wrong class → `AttributeError` on startup | Class extracted and appended at module level; `RestaurantApp` has its 32 methods back |
| 3 | Two listboxes in شاشة الفواتير were created but never `pack`ed, `events_box` was packed without ever being created, a `tools` bar was duplicated | The invoice screen could not show unbilled orders/events → "إصدار الفاتورة" always failed | Lists restored, creation/packing order fixed, duplicate toolbar row removed |
| 4 | `Treeview.insert(iid=key)` used the business key as the row id, while `save_customer`/`save_equipment` allowed duplicate names | Duplicate or blank names (common in hand-edited Excel files) → `TclError: Item already exists`, screen dies | Unique sequential iids + `iid → row` maps in all tables; name uniqueness enforced in the data layer (`ValueError` with an Arabic message) |
| 5 | `financial_summary()` never returned `daily_expenses_total`, yet the report printed it | A permanently `0.000` line in the report and in the printed HTML | Dead line removed (text + HTML); a real "نثريات يومية" table is proposed in phase 2 |
| 6 | Month filtering compared `"YYYY-MM" + "-01"` against the range start | A payroll/monthly expense for a month was **silently dropped** if the report range started after the 1st of that month | `month_bounds()` + period-overlap logic (`month_overlaps`) |
| 7 | `save_salary()` always inserted a new row | Saving a salary twice for the same staff/month double-counted payroll in reports | Upsert on (staff, month); existing `paid` flag preserved |
| 8 | No date/month format validation anywhere | Free text like `15/09/2026` broke sorting, filtering and month parsing silently | `is_iso_date()` / `is_month()` validation in the data layer + validated period fields in the reports screen |
| 9 | Search box called `refresh()` on every keystroke | Full `load_workbook()` + re-render on each keystroke (UI lag) | Rows cached; search only re-renders (`render_rows`) |
| 10 | `show_page()` wrapped refreshers in `except Exception: pass` | Real bugs were invisible | `traceback.print_exc()` |
| 11 | Dead no-op `apply_rtl_global_defaults()` with Korean/Chinese comments; unused `import json`; local re-imports of `tempfile`/`webbrowser` | Confusing, misleading code | Removed/cleaned |
| 12 | `create_invoice_for_customer` accepted empty selections; `generate_and_open_invoice_print` assumed well-formed JSON | Silent `0.000` invoices; crash on a corrupted cell | `ValueError` guard + `invoice_items()` safe parser used by both UI and printing |

### 1.2 Tests added (the safety net for everything that follows)

```
python tests/test_data_layer.py        # 20 checks: validation, totals, payroll upsert, invoicing, period maths
python tests/test_smoke.py             # GUI: all 12 screens, all refreshers, real invoice issue via the UI,
                                       #      record window, duplicate-name resilience, report validation
python tests/test_launch_real_data.py  # real launch on the user's xlsx; asserts the data file is not modified
```

All three pass on Python 3.13 + openpyxl 3.1.5.

> The smoke test immediately caught a `pack`/`grid` conflict in the rewritten record
> window — which is exactly why the tests exist.
---

## 2. Remaining structural risks (still true today)

1. **Excel is the only store, with no locking and no transactions.**
   Two instances of the app (or the app + an open Excel window) overwrite each other:
   `_save_row` does `load_workbook` → mutate → `wb.save` on every single operation.
   No audit trail, no undo, no automatic backup.
2. **`mark_*_invoiced` rewrites the whole workbook once per row.** Issuing an invoice
   for 10 orders performs ~10 full workbook rewrites.
3. **Money is `float` with `round(..., 3)`.** KWD has 3 decimals; repeated rounding in
   sums can drift. Use `Decimal` (or integer fils) for amounts.
4. **No receivables model.** Revenue is recognised the moment an invoice is issued;
   there is no partial payment, no paid/unpaid state on invoices, no aging report, and
   event deposits are netted off inside the invoice line *text* instead of being
   tracked as ledger entries.
5. **Invoice items live inside one cell as JSON** (`items_json`) → not queryable and not
   reportable, yet it is the only place the invoice breakdown exists.
6. **No cost side per meal.** Purchases are recorded as daily baskets; there is no
   recipe/BOM, no stock (مخزون), no cost-per-meal → food-cost % and gross margin per
   customer cannot be computed.
7. **No attachments.** `RecordPrintWindow` accepts `bill_image_path`, but no table has a
   column that can supply it — the feature is unreachable.
8. **Printing = temp HTML + default browser.** No PDF export, no embedded Arabic fonts,
   no ZATCA-style e-invoice fields (QR / tax number), no kitchen tickets; temp files are
   never cleaned up.
9. **Single-user desktop, no auth, no roles.** Deleting an invoice and editing a salary
   need the same (empty) privilege level.
10. **One 1,100-line module** mixes config, widgets and screen logic; no packaging
    (PyInstaller), no logging, and **no VCS**. This repair had to be done against
    `.orig.bak` copies — `git init` should be step 0 of any further work.
---

## 3. Proposed roadmap

### Phase 0 — Protect the data (days, highest value per hour)  ✅ **DONE**
- `git init` + first commit, and a documented backup routine (copy
  `restaurant_data.xlsx` to `backups/restaurant_data_YYYY-MM-DD.xlsx` on startup).
- **Atomic saves**: write to `*.tmp` then `os.replace()`, keeping the previous file as
  `restaurant_data.xlsx.bak.xlsx`, so a crash mid-save cannot destroy the workbook.
- **Single-instance guard** (lock file) so two app copies cannot write the
  same file.
- An **audit log** (`logs/audit_YYYY-MM.csv`: timestamp, action, sheet, key, details)
  written by the save/delete helpers — cheap insurance and the foundation for any
  later sync.
- Move the `.orig.bak` files into a `backups/` folder.

> **Status (2026-09):** all of the above is implemented in `restaurant_data.py`
> (`save_workbook`, `backup_data_file`, `startup_maintenance`,
> `acquire_instance_lock`/`release_instance_lock`, `log_action`) and wired into the
> app (`startup_maintenance()` + lock in `main`, `on_close` releases the lock).
> Tested by `tests/test_data_safety.py` (7 checks). `git init` done (first commit
> `bd53f5d`, live data/lock/backups/logs kept out of the repo) and the
> `*.orig.bak` repair copies were moved into `backups/`. **Phase 0 complete.**

### Phase 1 — Replace the storage, keep the UI  ✅ **Core DONE**
- Move to **SQLite** (`restaurant.db`) behind the *same* public API of
  `restaurant_data.py`, so `restaurant_desktop_app.py` keeps working while screens are
  migrated one at a time.
- Real schema with foreign keys: `customers`, `staff`, `orders`, `order_items`,
  `events`, `invoices`, `invoice_lines`, `purchases`, `products`, `expenses`,
  `salaries`, `payments`, `attachments`.
- Keep Excel as an **import/export** format only (`import_excel()` / `export_excel()`):
  removes the "whole-file rewrite per row" problem and enables transactions
  (`with conn:`).
- Split the module: `core/models.py`, `core/money.py` (Decimal), `core/repo_*.py`,
  `ui/pages/*.py`, `main.py`.
- Use `Decimal` for all amounts and add `tests/test_money.py`.

> **Status (2026-09):** ✅ **SQLite is now the DEFAULT backend** (cutover done):
> plain `python restaurant_desktop_app.py` runs on `restaurant.db`
> (path via `RESTAURANT_DB_FILE`). First launch with a legacy
> `restaurant_data.xlsx` beside it auto-imports its data (with a dated backup)
> exactly once — no manual step. Excel remains as export-only
> (`export_excel()` button in Reports) plus legacy mode via
> `RESTAURANT_BACKEND=excel`. Implemented:
> `restaurant_db.py` (schema per table, WAL, column auto-migration, per-table backups,
> `export_excel`/`import_excel`), dispatch in the 5 storage primitives of
> `restaurant_data.py`, `core/money.py` Decimal money now used in order/event/salary/
> invoice/summary calculations. The 1,233-line UI module is split: `ui/theme.py`,
> `ui/nav.py`, `ui/tabs.py`, `ui/printing.py`, `ui/record_window.py`,
> `ui/dialogs.py` (single messagebox seam for the whole UI), and one mixin per
> screen group in `ui/pages/`; `restaurant_desktop_app.py` is now the ~200-line
> shell (class composition + main). The cutover tool `migrate_to_sqlite.py`
> (backup → import → row-count verification → next-step instructions) was tested
> end-to-end on a fixture workbook: all 10 tables matched and the migrated DB was
> read back through the app's own API. Tested by `tests/test_money.py` (15) +
> `tests/test_sqlite_backend.py` (13, incl. Excel round-trip and UI launch on
> SQLite); all 95 checks across the six suites pass. Cutover completed in v2.2.0:
> default flipped to SQLite, one-time auto-import on first launch
> (tested in `test_sqlite_backend.py` §9.6: 15 checks), legacy suites pinned
> to Excel mode, smoke + launch suites run on SQLite (50 + content-stability
> checks), full `pytest` bridge green (6/6 in ~21s).
> Next: Phase 2 tables already live (`payments`, `products`, …).

### Phase 2 — Close the business gaps the owner actually feels
- **Receivables**: partial payments, `paid_amount`, invoice status, aging report,
  statement of account per customer (كشف حساب).
- **Credit notes / invoice cancellation** instead of deleting invoice rows.
- **Meal costing**: products + recipes (BOM) + stock movements → food cost and gross
  margin per order, per customer, per month.
- **Daily petty cash** (نثريات يومية) table, so the report line removed in this pass
  comes back with real data, plus cash-drawer reconciliation.
- **VAT/tax fields** (rate, tax number, tax-inclusive/exclusive amounts) and a yearly
  invoice series to satisfy local invoicing rules.
- **Attachments** column + a real file picker feeding `RecordPrintWindow`.

### Phase 3 — Reporting that decisions can be made from
- KPIs on الرئيسية: cost per meal, food-cost %, gross margin per customer, revenue per
  month, unpaid balance, meals delivered per day.
- Interactive filters (customer, period, order type) and charts (`matplotlib`) inside
  the app; export to Excel/PDF.
  ✅ **تم في v2.3.0**: `core/analytics.py` (سلسلة آخر N شهراً للإيراد/المصروف/
  الربح + أعلى العملاء + المستحقات لكل عميل) تُغذي بطاقة رسوم بيانية مضمّنة في
  تبويب التقارير (`ui/pages/charts.py` — عمودي إيراد/مصروف/ربح شهري + أفقي أعلى
  5 عملاء، مع تجاهل آمن للتحذيرات)، وفلترة سجل الفواتير نصاً وبحالة التحصيل
  (بحث فوري + قائمة منسدلة) في شاشة الفواتير. التثبيت: `pip install -e .[charts]`.
- Monthly P&L and cash-flow statements built from the ledger rather than invoice totals.

### Phase 4 — Output quality
- A template layer (`templates/*.html` rendered with `string.Template`).
- ✅ **PDF invoices** (arabic-reshaper + python-bidi + reportlab) — **تم في v2.3.0**:
  `core/pdf_ar.py` يولّد فواتير وكشوف حساب وتقارير مالية PDF بخط Arial العربي
  (تحققنا من النص المستخرج)، وأزرار «حفظ PDF» في شاشتي الفواتير والتقارير،
  وطباعة HTML القديمة باقية كخيار. التثبيت: `pip install -e .[pdf]`.
- QR-coded e-invoice, kitchen order tickets (KOT), delivery notes.

### Phase 5 — Multi-user / connected operation (only after phases 1–2)
- **FastAPI + SQLite/PostgreSQL** exposing the same operations as JSON.
- The Tkinter app becomes a thin client (or is replaced by a browser UI) so office,
  kitchen and driver see the same data.
- Authentication + roles (manager / accountant / kitchen / viewer) with per-action audit.
- Optional offline-first mode for a kitchen tablet, syncing when back online.

### Phase 6 — Operate it like software
- Structured rotating logs (`logs/app.log`) and an in-app diagnostics screen.
- PyInstaller packaging (single `.exe`), version stamping, update notification.
- Scheduled backup + restore-from-backup command, `pytest` runner and CI
  (GitHub Actions) running the test scripts on every commit.

---

## 3.5 المنفَّذ: تجميع الشاشات + الميزات الجديدة (دفعة التحصيل والعروض والتوصيل)

تم تنفيذ هذه الدفعة بالكامل واختبارها (109 فحوصاً في ست مجموعات اختبار، كلها خضراء).

### شاشات مجمّعة (قائمة التنقل من 12 شاشة إلى 7، وكل شاشة فيها تبويبات فرعية)
| الشاشة | التبويبات الفرعية |
|---|---|
| 📦 الطلبات والمناسبات | طلبات المؤسسات، المناسبات والولائم، عروض الأسعار، جدولة التوصيل |
| 🧾 الفواتير وكشف الحساب | إصدار الفواتير والسجل، تسجيل دفعة، كشف حساب عميل |
| 🧮 المصاريف والمشتريات | المشتريات اليومية، مصاريف التأسيس، المصاريف الشهرية، النثريات اليومية |
| 🗂 البيانات الأساسية | العملاء، العمال والشيفات، المعدات والسيارات، الأصناف والمنيو |

`show_page(key, sub_index)` يسمح بفتح شاشة على تبويب فرعي محدد (تستخدمه اختصارات الرئيسية).
الملف المحذوف `ui/pages/simple.py` توزّع محتواه على `ui/pages/masterdata.py` و`ui/pages/expenses.py`.

### ميزات جديدة في طبقة البيانات (تعمل على محركي Excel وSQLite)
- **عروض الأسعار** (`quotations`): حفظ عرض بحالة (معلق/مقبول/مرفوض)، و
  `convert_quotation_to_event()` يحوّله لمناسبة فعلية ويمنع التحويل المزدوج.
- **المدفوعات الجزئية** (`payments`): دفعات على فاتورة، مع إعادة حساب تلقائية
  لعمودَي `paid_amount` و`status` (مدفوعة/جزئية/غير مدفوعة) في جدول الفواتير،
  وطرق دفع (نقداً/كي نت/تحويل/شيك). حذف دفعة يعيد الحساب.
- **كشف حساب عميل** `customer_statement()`: الفواتير مدين والدفعات دائن مع رصيد
  متحرك، مع فترة اختيارية وطباعة HTML. والعربون غير مدرج كسطر لأنه مطروح من الفاتورة.
- **جدولة التوصيل**: أعمدة `driver/vehicle/delivered` على الطلبات والمناسبات،
  `deliveries_for_date()` تجمع تسليمات يوم من المصدرين، وشاشة إسناد ووسم تسليم.
- **الأصناف والمنيو** (`products`): كتالوج بتكلفة وسعر بيع (أساس حساب الهامش لاحقاً).
- **النثريات اليومية** (`petty_cash`): تدخل في `financial_summary` ضمن المصروفات
  التشغيلية، ومستحقات العملاء غير المحصلة تعود في مفتاح `receivables`.
- طباعة الفاتورة تعرض سطرَي المدفوع/المتبقي عند وجود دفعات.

### تحسينات واجهة المستخدم — دفعة UX (تم التنفيذ)
- **أزرار إغلاق/طباعة في الأعلى**: في `RecordPrintWindow` تُعرض الأزرار دائماً في الأعلي،
  حتى مع السجلات الطويلة التي تطيل الصفحة لأسفل.
- **شاشات قابلة للتمرير**: `ui/theme.py` أضاف `ScrollableFrame` (Canvas+Scrollbar مع
  دعم تمرير بالماوس)؛ شاشة **التقارير** الآن تحتوي كل محتواها داخلها لتظهر كاملة
  حتى على شاشات صغيرة.
- **تخطيط حديث لشاشة الفواتير**: بطاقة إصدار الفاتورة بتنسيق نظيف (تسمية بخط مائل،
  أزرار بتنسيق TButton/Accent.TButton)، وجدول سجل الفواتير بأسطر متباينة الألوان
  (striping) وأعمدة بعرض مناسب للمحتوى (توزيع، مبالغ محاذاة إلى اليمين، باقي مركّزة).

### ترقية مخطط ملفات قديمة (آلية دائمة)
`_add_missing_columns()` يكتب ترويسات الأعمدة الجديدة في نهاية كل ورقة قديمة
دون تحريك الأعمدة القائمة — القاعدة: **أي حقل جديد يُلحق آخر قائمة الحقول**.
محرك SQLite يفعل المثل عبر `_migrate_columns` الموجود مسبقاً.

## 4. Anti-goals / cautions
- Do **not** start with the web/multi-user work: Money-as-float, JSON items and the
  missing receivables model must be fixed first, otherwise the problems multiply.
- Do not "big-bang" rewrite the UI: migrate screen by screen behind the existing
  `restaurant_data.py` API, keeping `tests/test_smoke.py` green at every step.
- Keep the Arabic RTL UX and the warm كستنائي/ذهبي identity — they work and match what
  the client asked for.

---

## 5. How to run today
```
pip install -r requirements.txt
python restaurant_desktop_app.py        # تشغيل البرنامج
python -m pytest                        # كل مجموعات الاختبار معاً
python tests/test_data_layer.py         # اختبارات طبقة البيانات
python tests/test_smoke.py              # اختبار واجهة شامل
python tests/test_launch_real_data.py   # إقلاع حقيقي على ملف البيانات
python migrate_to_sqlite.py             # ترحيل Excel ← SQLite (عند الحاجة)
```

النسخ الأصلية القديمة محفوظة للمقارنة في مجلد `backups/` (خارج المستودع):
`restaurant_desktop_app.py.orig.bak`, `restaurant_data.py.orig.bak`,
`restaurant_data.xlsx.orig.bak`. كما هو موضح في `README.md`،
`restaurant_data.py` صار واجهة تصدير فقط، والمنطق كله في حزمة `core/data`
مقسّمة إلى وحدات حسب المسؤولية.