# -*- coding: utf-8 -*-
"""
نقطة وحيدة لصناديق الحوار في كل الواجهة.

كل وحدات ui تستورد هذا الموديول باسم messagebox، ما يتيح:
  - استبدال صناديق الحوار ببدائل وهمية في الاختبارات (ui.dialogs.impl).
  - مستقبلاً: توحيد شكل الرسائل أو تسجيلها في سجل الحركات.
"""
import tkinter.messagebox as _tk_mb

impl = _tk_mb          # التنفيذ الحالي (تستبدله الاختبارات ببديل وهمي)


def showinfo(title, message="", **kw):
    return impl.showinfo(title, message, **kw)


def showwarning(title, message="", **kw):
    return impl.showwarning(title, message, **kw)


def showerror(title, message="", **kw):
    return impl.showerror(title, message, **kw)


def askyesno(title, message="", **kw):
    return impl.askyesno(title, message, **kw)
