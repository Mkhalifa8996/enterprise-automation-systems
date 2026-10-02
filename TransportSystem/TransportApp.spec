# -*- mode: python ; coding: utf-8 -*-
# ملف بناء البرنامج كملف تنفيذي واحد (PyInstaller).
#
# بعد تقسيم المشروع إلى حزمة `transport/` صارت نقطة الدخول `main.py`، ويجب
# إخبار PyInstaller بجمع وحدات الحزمة الفرعية كلّها — وإلا حزم الملف التنفيذي
# لن يجد `transport.app_reports` وأمثاله عند التشغيل.
#
# ونضمّن معه:
#  - transport_data.db: تُنسخ مرة واحدة بجانب الملف التنفيذي عند أول تشغيل،
#    فيبدأ البرنامج بقاعدة سليمة بلا أي بيانات. إن لم تكن موجودة في المجلد
#    تُبنى قاعدة فارغة مؤقتة وتُضمّن (المشروع لا يرفع بيانات الشركة).
#  - icon.png: تُقرأ من مجلد الحزم المؤقت (‎__file__‎ داخل الـexe)، فلولا
#    ضمّنها لاختفت أيقونة الشركة من الفواتير والكشوف المطبوعة.
import os
import sqlite3
import tempfile

from PyInstaller.utils.hooks import collect_submodules

HERE = os.path.abspath(SPECPATH)
DB_FILE = os.path.join(HERE, "transport_data.db")
_seeded_db = DB_FILE

if not os.path.isfile(_seeded_db):
    # No local database (fresh clone): build an empty schema-only copy so the
    # executable still ships a working first-run experience.
    _tmp = tempfile.mkdtemp()
    _seeded_db = os.path.join(_tmp, "transport_data.db")
    _con = sqlite3.connect(_seeded_db)
    try:
        _con.execute("CREATE TABLE records ("
                     "sheet_key TEXT NOT NULL, record_key TEXT NOT NULL, "
                     "data_json TEXT NOT NULL, updated_at TEXT NOT NULL, "
                     "PRIMARY KEY (sheet_key, record_key))")
        _con.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)")
        _con.commit()
    finally:
        _con.close()

hiddenimports = (
    ['tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog',
     'tkinter.simpledialog', 'openpyxl', 'dotenv', 'PIL']
    + collect_submodules('transport')
)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.png', '.'),
        (_seeded_db, '.'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TransportApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.png'],
)
