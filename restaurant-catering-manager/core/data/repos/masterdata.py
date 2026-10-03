# -*- coding: utf-8 -*-
"""
core.data.repos.masterdata — البيانات الأساسية: العمال، المعدات، العملاء، والأصناف.
"""

from core.data import storage


def _ensure_unique_name(sheet_key, data, editing_name, label):
    """
    منع وجود صفّين بنفس الاسم في الجداول التي يعتمد مفتاحها على الاسم
    (العملاء / المعدات / العمال / الأصناف)، لأن التكرار يكسر جدول الواجهة والبحث.
    """
    load_fn = {"equipment": load_equipment, "customers": load_customers,
               "staff": load_staff, "products": load_products}[sheet_key]
    name = str(data.get("name", "")).strip()
    if not name:
        raise ValueError("%s مطلوب." % label)
    data["name"] = name
    current = str(editing_name or "").strip()
    for row in load_fn():
        row_name = str(row.get("name", "")).strip()
        if row_name == name and row_name != current:
            raise ValueError("%s موجود بالفعل: %s" % (label, name))


# ------------------------------------------------------------------
# العمال والشيفات
# ------------------------------------------------------------------
def load_staff():
    return storage.load_rows("staff", "name")


def save_staff(data, editing_name=None):
    _ensure_unique_name("staff", data, editing_name, "اسم الموظف")
    storage.save_row_by_name("staff", data, editing_name)


def delete_staff(name):
    storage.delete_row("staff", "name", name)


# ------------------------------------------------------------------
# المعدات وسيارات التوصيل
# ------------------------------------------------------------------
def load_equipment():
    return storage.load_rows("equipment", "name")


def save_equipment(data, editing_name=None):
    _ensure_unique_name("equipment", data, editing_name, "اسم المعدة")
    storage.save_row_by_name("equipment", data, editing_name)


def delete_equipment(name):
    storage.delete_row("equipment", "name", name)


# ------------------------------------------------------------------
# العملاء (مؤسسات وعملاء مناسبات)
# ------------------------------------------------------------------
def load_customers():
    return storage.load_rows("customers", "name")


def save_customer(data, editing_name=None):
    _ensure_unique_name("customers", data, editing_name, "العميل")
    storage.save_row_by_name("customers", data, editing_name)


def delete_customer(name):
    storage.delete_row("customers", "name", name)


# ------------------------------------------------------------------
# الأصناف والمنيو
# ------------------------------------------------------------------
def load_products():
    return storage.load_rows("products", "name")


def save_product(data, editing_name=None):
    _ensure_unique_name("products", data, editing_name, "اسم الصنف")
    storage.save_row_by_name("products", data, editing_name)


def delete_product(name):
    storage.delete_row("products", "name", name)
