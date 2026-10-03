# -*- coding: utf-8 -*-
"""
ui.rtl — توحيد اتجاه الواجهة من اليمين إلى اليسار (RTL).

Tkinter لا يدعم RTL أصلياً، فالعربية تُبنى فيه يدوياً: نحدد محاذاة الحقول،
ونعكس ترتيب أعمدة الجداول، ونضع شريط التمرير في اليسار. كل ذلك مركزي هنا
حتى لا تتكرر القواعد في كل شاشة.

دوال هذه الوحدة لا تغيّر سلوك التطبيق على البيانات إطلاقاً — ترتيب الأعمدة
المعروض فقط هو ما ينعكس، أما ربط القيم فيبقى كما هو.
"""
import tkinter as tk
from tkinter import ttk

RIGHT = "e"           # محور "شرق" في Tk = اليمين
JUSTIFY = "right"     # ضبط نص الحقول إلى اليمين
TEXT_TAG = "rtl"      # وسم يُستخدم لمحاذاة محتوى widgets النصية


def rtl_tree(tree, anchor=RIGHT):
    """
    يحوّل جدول ttk.Treeview إلى عرض من اليمين إلى اليسار.

    يُعكس ترتيب الأعمدة المعروض (displaycolumns) فيظهر العمود الأول على اليمين،
    بينما تبقى قيمة كل عمود مرتبطة بعموده الأصلي كما هي.
    """
    cols = [c for c in (tree.cget("columns") or ()) if c != "#0"]
    if not cols:
        return tree
    tree.configure(displaycolumns=list(reversed(cols)))
    for col in cols:
        tree.heading(col, anchor=RIGHT)
        try:
            tree.column(col, anchor=anchor)
        except tk.TclError:          # بعض الأنواع لا تقبل المحاذاة المخصصة
            pass
    return tree


def rtl_text(widget):
    """محاذاة محتوى widget نصي إلى اليمين عبر وسم يُطبَّق على كل ما يُكتب فيه."""
    try:
        widget.tag_configure(TEXT_TAG, justify=JUSTIFY)
        widget.tag_add(TEXT_TAG, "1.0", "end")
    except tk.TclError:
        pass
    return widget


def rtl_entry(widget):
    """محاذاة حقل إدخال (Entry/Combobox/Spinbox) إلى اليمين."""
    try:
        widget.configure(justify=JUSTIFY)
    except tk.TclError:
        pass
    return widget


def add_rtl_tabs(notebook, tabs):
    """
    يضيف تبويبات notebook بحيث تظهر أول تبويبة على اليمين.

    tabs: قائمة [(frame, text), ...] بالترتيب المنطقي (الأول = الافتراضي).
    تُضاف فعلياً بترتيب معكوس لأن Tk يرسم التبويبات من اليسار إلى اليمين،
    ثم نُفعّل التبويبة المنطقية الأولى (وهي آخر تبويب مضاف).
    """
    for frame, text in reversed(tabs):
        notebook.add(frame, text=text)
    if tabs:
        notebook.select(len(tabs) - 1)     # التبويب الأول منطقياً = آخر موضع
    return len(tabs)


def tab_index(notebook, logical_index):
    """يترجم رقم التبويب المنطقي إلى موضعه الفعلي بعد عكس الترتيب."""
    count = len(notebook.tabs())
    if count == 0:
        return None
    if logical_index is None:
        return None
    if 0 <= logical_index < count:
        return count - 1 - logical_index
    return None


def _apply_one(widget):
    """يطبّق قواعد RTL على عنصر واحد حسب نوعه."""
    if isinstance(widget, (ttk.Treeview,)):
        rtl_tree(widget)
    elif isinstance(widget, tk.Text):
        rtl_text(widget)
    elif isinstance(widget, (tk.Entry, ttk.Entry, ttk.Combobox, ttk.Spinbox)):
        rtl_entry(widget)


def apply_rtl(widget):
    """
    يمر على شجرة الواجهة كاملة ويطبّق قواعد RTL على كل عنصر قابل للضبط.

    يُستدعى مرة واحدة بعد بناء كل الشاشات، فيلتقط الحقول والجداول
    بأكملها دفعة واحدة دون تكرار في كل ملف شاشة.
    """
    for child in widget.winfo_children():
        _apply_one(child)
        apply_rtl(child)
