# -*- coding: utf-8 -*-
"""نافذة عرض/طباعة أي سجل من أي جدول (مع دعم RTL ومرفق الفاتورة)."""

import os
import webbrowser
import tkinter as tk
from tkinter import ttk
from ui import dialogs as messagebox
from ui.theme import (
    COLOR_BG,
    COLOR_CARD,
    COLOR_TEXT,
    COLOR_MUTED,
    F_LABEL,
    F_BODY,
    safe_str,
    card_frame,
)


# ======================================================================
# نافذة عرض/طباعة أي سجل من أي جدول (مع دعم RTL ومرفق الفاتورة)
# ======================================================================
def open_path_with_default_app(path):
    """فتح ملف بالبرنامج الافتراضي للنظام دون إسقاط الواجهة عند الفشل."""
    try:
        if hasattr(os, "startfile"):
            os.startfile(path)
        else:
            webbrowser.open("file://" + str(path))
    except Exception as exc:
        messagebox.showwarning("تنبيه", "تعذّر فتح الملف:\n%s\n%s" % (path, exc))


class RecordPrintWindow(tk.Toplevel):
    """
    نافذة مستقلة تعرض بيانات سجل واحد:
      - العنوان، والحقول [(key,label,value)...] مصفوفة من اليمين لليسار.
      - مرفق الفاتورة إن كان مسارها موجوداً فعلاً على القرص.
      - زر طباعة يستدعي الدالة الممرَّرة في printer_html_fn.
    """

    def __init__(self, parent, title, fields, bill_image_path=None,
                 printer_html_fn=None, bill_title=None):
        super().__init__(parent)
        self.title(title or "عرض السجل")
        self.geometry("540x580")
        self.minsize(460, 380)
        self.configure(bg=COLOR_BG)

        frame = tk.Frame(self, bg=COLOR_BG)
        frame.pack(fill="both", expand=True, padx=18, pady=18)

        card = card_frame(frame, title or "تفاصيل السجل")
        card.pack(fill="both", expand=True)

        body = card.body
        # ===== الأزرار في الأعلى — تظهر دائماً حتى مع سجلات طويلة =====
        buttons = tk.Frame(body, bg=COLOR_CARD)
        buttons.pack(fill="x", padx=14, pady=(12, 4), anchor="e")
        if printer_html_fn:
            ttk.Button(buttons, text=bill_title or "طباعة", style="Accent.TButton",
                       command=printer_html_fn).pack(side="right", padx=6)
        ttk.Button(buttons, text="إغلاق", command=self.destroy).pack(side="right", padx=6)

        # صفوف الحقول داخل إطار فرعي بعد الأزرار
        rows = tk.Frame(body, bg=COLOR_CARD)
        rows.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        rows.grid_columnconfigure(0, weight=1)
        row_y = 0
        for _key, _label, value in fields:
            tk.Label(rows, text=_label, font=F_LABEL, bg=COLOR_CARD,
                     fg=COLOR_MUTED, anchor="e").grid(
                row=row_y, column=1, sticky="w", padx=(0, 8))
            tk.Label(rows, text=safe_str(value), font=F_BODY, bg=COLOR_CARD,
                     fg=COLOR_TEXT, justify="right", anchor="e", wraplength=360).grid(
                row=row_y, column=0, sticky="ew", padx=(8, 0))
            row_y += 1

        if bill_image_path and os.path.isfile(bill_image_path):
            img_frame = tk.Frame(rows, bg=COLOR_CARD)
            img_frame.grid(row=row_y, column=0, columnspan=2, sticky="ew", pady=(10, 0))
            tk.Label(img_frame, text="صورة الفاتورة المرفقة:", font=F_LABEL,
                     bg=COLOR_CARD, fg=COLOR_MUTED, anchor="e").pack(side="right")
            ttk.Button(img_frame, text="فتح صورة الفاتورة",
                       command=lambda p=bill_image_path: open_path_with_default_app(p)).pack(
                side="right", padx=(0, 10))
            row_y += 1

        self.transient(parent)
        self.grab_set()
