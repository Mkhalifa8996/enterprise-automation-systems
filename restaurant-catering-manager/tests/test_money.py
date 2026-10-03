# -*- coding: utf-8 -*-
"""
اختبارات دقة الحسابات النقدية (core.money) — أساس المرحلة 1.

    python tests/test_money.py
"""
import os
import sys
from decimal import Decimal

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from core.money import D, add, fmt, money, mul, sub, to_float, ZERO

passed, failed = [], []


def check(cond, label):
    if cond:
        passed.append(label)
        print("  [ OK ] %s" % label)
    else:
        failed.append(label)
        print("  [FAIL] %s" % label)


print("1) لماذا Decimal؟ (إثبات مشكلة float)")

# 0.1 + 0.2 في float ليس 0.3 بالضبط — لهذا وُجدت هذه الوحدة
check((0.1 + 0.2) != 0.3, "float(0.1+0.2) != 0.3 فعلًا (المشكلة المثبتة)")
check(to_float(add("0.1", "0.2")) == 0.3, "money(0.1)+money(0.2) == 0.300 بالضبط")

print("2) التحويل والتنسيق")

check(money("12.5") == Decimal("12.500"), "money من نص")
check(D(None) == ZERO and D("") == ZERO, "None/النص الفارغ => صفر")
check(D("أهلاً") == ZERO, "قيمة غير قابلة للتحويل => صفر (بدون انفجار)")
check(D("1٬000.5") == Decimal("1000.500"), "فاصل الآلاف العربي يُتجاهل")
check(fmt(3.5) == "3.500" and fmt(0) == "0.000", "fmt يعرض 3 منازل دائماً")

print("3) التقريب المحاسبي (نصف لأعلى) على 3 منازل")

check(money("2.6755") == Decimal("2.676"), "2.6755 => 2.676 (وليس تقريب float)")
check(money("-1.0005") == Decimal("-1.001"), "السالب يُقرَّب بعيداً عن الصفر")
check(money("1.0004") == Decimal("1.000"), "أقل من نصف فلس يُهمَل")

print("4) العمليات: ضرب وجمع وطرح")

check(to_float(mul("2.5", 3)) == 7.5, "mul(كمية × سعر) = 7.500")
check(to_float(mul("0.1", 3)) == 0.3, "mul(0.1 × 3) = 0.300 (float يفشل هنا)")
check(to_float(sub("10", "0.333")) == 9.667, "sub(10 - 0.333) = 9.667")
check(add() == ZERO, "add() بلا معاملات = صفر")
check(to_float(add(1.111, 2.222, 3.333)) == 6.666, "جمع ثلاث مبالغ بلا انزياح")

print()
print("النتيجة: %d ناجح / %d فاشل" % (len(passed), len(failed)))
if failed:
    print("اختبارات النقود فشلت.")
    sys.exit(1)
print("كل اختبارات النقود نجحت.")
