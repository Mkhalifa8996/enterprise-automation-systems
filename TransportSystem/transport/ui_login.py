# -*- coding: utf-8 -*-
"""نافذة تسجيل الدخول للمشرف."""

from tkinter import messagebox
import tkinter as tk
from . import data as td
from .app_config import COLOR_CARD, COLOR_PRIMARY, F_BODY, F_H2, F_LABEL
from .ui_widgets import make_btn


class LoginDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("تسجيل الدخول")
        self.geometry("390x250")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.ok = False
        body = tk.Frame(self, bg=COLOR_CARD)
        body.pack(fill="both", expand=True, padx=24, pady=20)
        tk.Label(body, text="تسجيل الدخول إلى نظام النقل", font=F_H2,
                 bg=COLOR_CARD, fg=COLOR_PRIMARY).pack(pady=(0, 16))
        self.username = tk.StringVar(value="مدير النظام")
        self.password = tk.StringVar()
        for label, variable, show in (
            ("اسم المستخدم", self.username, ""),
            ("كلمة المرور", self.password, "*"),
        ):
            tk.Label(body, text=label, font=F_LABEL, bg=COLOR_CARD,
                     anchor="e").pack(fill="x")
            tk.Entry(body, textvariable=variable, show=show, justify="right",
                     font=F_BODY).pack(fill="x", pady=(2, 8), ipady=3)
        actions = tk.Frame(body, bg=COLOR_CARD)
        actions.pack(fill="x", pady=(4, 0))
        make_btn(actions, "دخول", self._submit, variant="accent").pack(side="right", padx=4)
        make_btn(actions, "إلغاء", self.destroy, variant="secondary").pack(side="right", padx=4)
        self.bind("<Return>", lambda _event: self._submit())

    def _submit(self):
        if td.authenticate_user(self.username.get(), self.password.get()):
            self.ok = True
            self.destroy()
        else:
            messagebox.showerror("تسجيل الدخول", "اسم المستخدم أو كلمة المرور غير صحيحة.",
                                 parent=self)
