# -*- coding: utf-8 -*-
"""
جسر pytest فوق مجموعات الاختبارات الست الحالية (سكربتات تنفيذية مكتوبة
بأسلوبها الخاص وكل واحدة تُغلق برمز خروج). يشغّلها هنا كعمليات فرعية حتى
تعمل `pytest` من الجذر مباشرة، وتفشل المجموعة إذا فشل أي فحص داخلها.

ملاحظة: مجموعات الواجهة (test_smoke / test_launch_real_data) تُستبعد تلقائياً
إذا لم يوجد عرض رسومي (مثل مستودع CI على لينكس) — وهذا ما يفعله فحص DISPLAY
أدناه، وعلى ويندوز تعمل دائماً.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent

ALL_SUITES = [
    "test_data_layer.py",
    "test_money.py",
    "test_data_safety.py",
    "test_sqlite_backend.py",
    "test_smoke.py",
    "test_launch_real_data.py",
]

GUI_SUITES = {"test_smoke.py", "test_launch_real_data.py"}


def _gui_available() -> bool:
    if os.name == "nt":
        return True
    return bool(os.environ.get("DISPLAY"))


def _active_suites():
    suites = []
    for suite in ALL_SUITES:
        if suite in GUI_SUITES and not _gui_available():
            continue
        suites.append(suite)
    return suites


@pytest.mark.parametrize("suite", _active_suites())
def test_suite(suite):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    result = subprocess.run(
        [sys.executable, str(BASE / "tests" / suite)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(BASE), env=env, timeout=300,
    )
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    assert result.returncode == 0, "فشلت مجموعة %s\n%s" % (suite, output[-3000:])
