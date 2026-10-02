# Enterprise Automation Systems

A repository containing two independent projects:

| Folder | Project | Description |
|---|---|---|
| [`TransportSystem/`](TransportSystem/) | Transport Management System | Desktop app for trips, drivers, invoices, salaries and financial reports |
| [`AlEstidamaInvoices/`](AlEstidamaInvoices/) | Invoice System | Standalone invoice app backed by an Excel workbook |

Each project is fully self-contained: it has its own entry point, requirements
and documentation.

---

## Transport Management System

```bash
cd TransportSystem
pip install -r requirements.txt
python main.py
```

Full documentation: [`TransportSystem/README.md`](TransportSystem/README.md).

The project is organised as a `transport/` package rather than one large file:

- `transport/app_*.py` — application layers (screen mixins)
- `transport/ui_*.py` — shared widgets and data-entry screens
- `transport/print_*.py` — printing, invoices and letterhead
- `transport/data/*.py` — database layer

### Screens

| Home | Daily trips |
|---|---|
| ![Home](TransportSystem/docs/screenshots/home.png) | ![Trips](TransportSystem/docs/screenshots/trips.png) |

| Reports | Invoices |
|---|---|
| ![Reports](TransportSystem/docs/screenshots/reports.png) | ![Invoices](TransportSystem/docs/screenshots/invoices.png) |

All nine screens are in [`TransportSystem/README.md`](TransportSystem/README.md#screenshots).

**The source contains no private data.** Every user supplies their own company
details and Firebase project. See [FIREBASE_SETUP.md](TransportSystem/FIREBASE_SETUP.md).

To build a standalone executable, run `TransportSystem\build_exe.bat`, which
produces `TransportApp.exe`.

---

## Invoice System

```bash
cd AlEstidamaInvoices
python invoice_desktop_app.py
```

---

## Notes

- [.gitignore](.gitignore) excludes databases, Excel exports, attachments and
  any file holding business data or secrets.
- [.gitattributes](.gitattributes) normalises line endings across platforms.