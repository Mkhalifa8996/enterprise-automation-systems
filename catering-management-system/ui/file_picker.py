# -*- coding: utf-8 -*-
"""أدوات اختيار وعرض ملفات المرفقات: زر اختيار ملف + زر عرض مرفق."""

import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog
from ui import dialogs as messagebox
import restaurant_data as rd
from ui.theme import COLOR_CARD, F_BODY


def pick_attachment(parent, on_selected):
    """
    يفتح نافذة اختيار ملف ويُرسل المسار المختار (أو None) إلى on_selected.
    يُنسخ الملف إلى مجلد attachments/ ويُرسل اسمه فقط لحفظه في الجدول.
    """
    filetypes = [
        ("ملفات دعم", "*.pdf;*.jpg;*.jpeg;*.png;*.gif;*.bmp;*.doc;*.docx;*.xls;*.xlsx;*.txt;*.csv"),
        ("كل الملفات", "*.*"),
    ]
    path = filedialog.askopenfilename(
        parent=parent,
        title="اختر ملفاً للمرفق",
        filetypes=filetypes,
    )
    if not path:
        return
    try:
        os.makedirs(rd.attachments_dir(), exist_ok=True)
        target = os.path.join(rd.attachments_dir(), os.path.basename(path))
        # إذا كان الملف موجوداً بنفس الاسم، نضيف رقماً
        if os.path.exists(target):
            base, ext = os.path.splitext(target)
            i = 1
            while os.path.exists(f"{base}_{i}{ext}"):
                i += 1
            target = f"{base}_{i}{ext}"
        shutil.copy2(path, target)
        on_selected(os.path.basename(target))
    except OSError as e:
        messagebox.showwarning("تنبيه", f"تعذر نسخ الملف:\n{e}")


def view_attachment(parent, filename):
    """يفتح المرفق المحفوظ في برنامجه الافتراضي."""
    full_path = rd.attachment_path(filename)
    if not full_path or not os.path.isfile(full_path):
        messagebox.showwarning("تنبيه", "لم يتم العثور على الملف.")
        return
    try:
        if hasattr(os, "startfile"):
            os.startfile(full_path)  # noqa: PGH003 - Windows فقط
        else:
            import webbrowser
            webbrowser.open("file://" + full_path)
    except Exception as e:
        messagebox.showwarning("تنبيه", f"تعذر فتح الملف:\n{e}")


class AttachmentPicker(ttk.Frame):
    """
    حقل اختيار ملف مرفق — بديل للـ Entry عندما يكون الحقل هو 'attachment'.
    يعرض:
      - مربع نص للقراءة فقط يوضح اسم الملف المختار.
      - زر "+ إضافة ملف" لاختيار مرفق جديد.
      - زر "عرض" لفتح المرفق في برنامجه الافتراضي (يظهر عندما يكون هناك ملف).
    """

    def __init__(self, parent, var, **kw):
        super().__init__(parent, **kw)
        self.var = var
        self.parent = parent

        inner = tk.Frame(self, bg=COLOR_CARD)
        inner.pack(fill="x", side="right")

        self.entry = ttk.Entry(inner, textvariable=var, font=F_BODY,
                               justify="right", state="readonly", width=22,
                               relief="solid", bd=1)
        self.entry.pack(side="right", padx=(8, 0), ipady=3)

        self.view_btn = ttk.Button(inner, text="عرض", width=8,
                                   command=self._view)
        self.view_btn.pack(side="right", padx=2)

        self.add_btn = ttk.Button(inner, text="+ مرفق", width=10,
                                  command=self._pick)
        self.add_btn.pack(side="right", padx=2)

        # أظهر زر العرض فقط عند وجود ملف
        self._update_view_btn()
        self.var.trace_add("write", lambda *a: self._update_view_btn())

    def _update_view_btn(self):
        has_file = bool(self.var.get().strip())
        self.view_btn.config(state=("normal" if has_file else "disabled"))

    def _pick(self):
        pick_attachment(self.parent, self._on_picked)

    def _on_picked(self, basename):
        self.var.set(basename)

    def _view(self):
        view_attachment(self.parent, self.var.get().strip())
