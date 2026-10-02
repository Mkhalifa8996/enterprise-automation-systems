# -*- coding: utf-8 -*-
"""النوافذ المنبثقة المشتركة: التقويم وإدارة المرفقات."""

import calendar, os, shutil, webbrowser
from datetime import date
from tkinter import filedialog
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk
from . import data as td
from .app_config import COLOR_BG, COLOR_BORDER, COLOR_CARD, COLOR_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, F_BODY, F_BOLD, F_LABEL
from .ui_widgets import center_dialog, make_btn
from .ui_helpers import log_exception, safe_str


class DatePicker(tk.Toplevel):
    """تقويم بسيط يعيد التاريخ بصيغة YYYY-MM-DD إلى المتغير المُمرّر."""
    def __init__(self, parent, variable):
        super().__init__(parent)
        self.variable = variable
        try:
            selected = date.fromisoformat(variable.get())
        except (TypeError, ValueError):
            selected = date.today()
        self.year, self.month = selected.year, selected.month
        self.title("اختيار التاريخ")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.body = tk.Frame(self, padx=10, pady=10, bg=COLOR_CARD)
        self.body.pack()
        self._render()

    def _render(self):
        for child in self.body.winfo_children():
            child.destroy()
        nav = tk.Frame(self.body, bg=COLOR_CARD)
        nav.pack(fill="x", pady=(0, 6))
        make_btn(nav, "›", self._next, variant="secondary", width=3).pack(side="left")
        tk.Label(nav, text=f"{calendar.month_name[self.month]} {self.year}", font=F_BOLD,
                 bg=COLOR_CARD, fg=COLOR_PRIMARY).pack(side="left", expand=True)
        make_btn(nav, "‹", self._previous, variant="secondary", width=3).pack(side="right")
        grid = tk.Frame(self.body, bg=COLOR_CARD)
        grid.pack()
        for col, label in enumerate(["ح", "ن", "ث", "ر", "خ", "ج", "س"]):
            tk.Label(grid, text=label, font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED,
                     width=4).grid(row=0, column=col, pady=(0, 3))
        # calendar.monthcalendar يبدأ يوم الاثنين؛ نعيد الترتيب للعرض من الأحد.
        for row, week in enumerate(calendar.monthcalendar(self.year, self.month), start=1):
            for index, day_no in enumerate(week):
                if not day_no:
                    continue
                col = (index + 1) % 7
                make_btn(grid, str(day_no), lambda d=day_no: self._choose(d),
                         variant="secondary", width=3).grid(row=row, column=col, padx=1, pady=1)

    def _previous(self):
        self.month -= 1
        if self.month == 0:
            self.month, self.year = 12, self.year - 1
        self._render()

    def _next(self):
        self.month += 1
        if self.month == 13:
            self.month, self.year = 1, self.year + 1
        self._render()

    def _choose(self, day_no):
        self.variable.set(date(self.year, self.month, day_no).isoformat())
        self.destroy()

def date_input(parent, variable, shrink=False, ipady=4, width=None, **entry_options):
    """حقل تاريخ مع زر تقويم؛ يقبل الخيارات المعتادة لحقل الإدخال."""
    wrapper = tk.Frame(parent, bg=parent.cget("bg"))
    wrapper.pack(fill="x")
    options = {"font": F_BODY, "justify": "right", "relief": "flat", "bd": 0,
               "highlightthickness": 2, "highlightbackground": COLOR_BORDER,
               "highlightcolor": COLOR_PRIMARY_LIGHT}
    options.update(entry_options)
    pack_opts = {"side": "right", "ipady": ipady}
    if width is not None:
        options["width"] = width
    if not shrink:
        pack_opts.update({"fill": "x", "expand": True})
    tk.Entry(wrapper, textvariable=variable, **options).pack(**pack_opts)
    make_btn(wrapper, "📅", lambda: DatePicker(wrapper, variable), variant="secondary", width=2).pack(side="left", padx=(4, 0))
    return wrapper

def open_attachment_manager_dialog(parent, entity_type, record_key, category_label, refresh_callback=None):
    """نافذة إدارة المرفقات الموحدة — نفس تصميم شاشة السائقون."""
    dialog = tk.Toplevel(parent)
    dialog.title(f"ملفات — {category_label}")
    dialog.geometry("820x430")
    dialog.configure(bg=COLOR_BG)
    try:
        dialog.transient(parent)
    except Exception as _log_exc: log_exception("open_attachment_manager_dialog", _log_exc)
    try:
        dialog.grab_set()
    except Exception as _log_exc: log_exception("open_attachment_manager_dialog", _log_exc)
    center_dialog(dialog, parent)
    tree = ttk.Treeview(
        dialog, columns=("type", "name", "by", "at"), show="headings", selectmode="browse")
    for key, label, width in (
        ("type", "نوع المستند", 190), ("name", "الملف", 300),
        ("by", "أضافه", 120), ("at", "التاريخ", 150),
    ):
        tree.heading(key, text=label)
        tree.column(key, width=width, anchor="e")
    tree.bind("<Double-1>", lambda _event: open_file())
    tree.pack(fill="both", expand=True, padx=14, pady=14)
    try:
        items = td.load_attachments(entity_type, str(record_key))
    except Exception as exc:
        messagebox.showerror("المرفقات", str(exc), parent=dialog)
        dialog.destroy()
        return

    def reload_items():
        fresh = td.load_attachments(entity_type, str(record_key))
        for iid in tree.get_children():
            tree.delete(iid)
        for item in fresh:
            tree.insert("", "end", iid=str(item["id"]),
                        values=(item["notes"], item["file_name"],
                                item["created_by"], item["created_at"]))
        if callable(refresh_callback):
            try:
                refresh_callback()
            except Exception as _log_exc: log_exception("reload_items", _log_exc)
        return fresh

    items = reload_items()

    def selected_item():
        selection = tree.selection()
        if not selection:
            messagebox.showinfo("تنبيه", "اختر ملفا أولا.", parent=dialog)
            return None
        return next((item for item in items if str(item["id"]) == selection[0]), None)

    def open_file():
        item = selected_item()
        if not item:
            return
        if not os.path.isfile(item["path"]):
            messagebox.showerror("فتح الملف", "الملف غير موجود.", parent=dialog)
            return
        try:
            if hasattr(os, "startfile"):
                os.startfile(item["path"])
            else:
                webbrowser.open(f"file://{item['path']}")
        except OSError as exc:
            messagebox.showerror("فتح الملف", str(exc), parent=dialog)

    def download_file():
        item = selected_item()
        if not item:
            return
        if not os.path.isfile(item["path"]):
            messagebox.showerror("تنزيل الملف", "الملف غير موجود.", parent=dialog)
            return
        target = filedialog.asksaveasfilename(
            parent=dialog, title="تنزيل نسخة من الملف",
            initialfile=item["file_name"])
        if not target:
            return
        try:
            shutil.copy2(item["path"], target)
        except OSError as exc:
            messagebox.showerror("تنزيل الملف", str(exc), parent=dialog)
            return
        messagebox.showinfo("المرفقات", "تم تنزيل نسخة الملف.", parent=dialog)

    def replace_file():
        item = selected_item()
        if not item:
            return
        source = filedialog.askopenfilename(
            parent=dialog, title="اختيار الملف البديل",
            filetypes=[("كل الملفات", "*.*")])
        if not source:
            return
        try:
            replacement = td.add_attachment(
                entity_type, record_key, source,
                notes=safe_str(item.get("notes")).strip() or category_label or "")
            td.delete_attachment(item["id"])
            messagebox.showinfo("المرفقات",
                                f"تم الاستبدال بـ {replacement['file_name']}.", parent=dialog)
            new_items = reload_items()
            items.clear()
            items.extend(new_items)
        except (OSError, ValueError) as exc:
            messagebox.showerror("استبدال الملف", str(exc), parent=dialog)

    def delete_file():
        item = selected_item()
        if not item:
            return
        if not messagebox.askyesno("حذف الملف", "حذف هذا الملف نهائيا؟", parent=dialog):
            return
        try:
            td.delete_attachment(item["id"])
            messagebox.showinfo("المرفقات", "تم حذف الملف.", parent=dialog)
            new_items = reload_items()
            items.clear()
            items.extend(new_items)
        except (OSError, ValueError) as exc:
            messagebox.showerror("حذف الملف", str(exc), parent=dialog)

    buttons = tk.Frame(dialog, bg=COLOR_BG)
    buttons.pack(fill="x", padx=14, pady=(0, 14))
    make_btn(buttons, "تنزيل نسخة", download_file, variant="accent").pack(side="right", padx=4)
    make_btn(buttons, "استبدال", replace_file, variant="secondary").pack(side="right", padx=4)
    make_btn(buttons, "حذف", delete_file, variant="danger").pack(side="right", padx=4)
    make_btn(buttons, "فتح", open_file, variant="secondary").pack(side="right", padx=4)
    make_btn(buttons, "اغلاق", dialog.destroy, variant="secondary").pack(side="right", padx=4)
