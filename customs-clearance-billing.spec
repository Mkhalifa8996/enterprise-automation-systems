# -*- mode: python ; coding: utf-8 -*-
"""ملف PyInstaller لبناء ملف تنفيذي مستقل.

البناء من داخل مجلد المشروع:
    python -m PyInstaller customs-clearance-billing.spec

تُبنى المسارات نسبياً حتى يعمل البناء من أي مسار على أي جهاز.
"""

import os

from PyInstaller.utils.hooks import collect_data_files

PROJECT_DIR = os.path.abspath(os.getcwd())

# ملفات ttkbootstrap (السمات)، وهي اختيارية لكن نضمن تضمينها إن كانت مثبتة.
ttkbootstrap_datas = collect_data_files("ttkbootstrap")

# موارد الصورة (شعار التطبيق). تُضمَّن فقط إن وُجدت.
image_datas = [
    (name, ".")
    for name in ("icon.png", "logo.png")
    if os.path.exists(os.path.join(PROJECT_DIR, name))
]

a = Analysis(
    [os.path.join(PROJECT_DIR, "main.py")],
    pathex=[PROJECT_DIR],
    binaries=[],
    datas=ttkbootstrap_datas + image_datas,
    hiddenimports=[],
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
    name="customs-clearance-billing",
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
)