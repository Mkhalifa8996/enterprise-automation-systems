# -*- coding: utf-8 -*-
"""شريط التنقّل الجانبي."""

import tkinter as tk
from .app_config import COLOR_ACCENT, COLOR_NAV_ACTIVE, COLOR_NAV_HOVER, COLOR_PRIMARY, FONT_NAME, F_BRAND, F_BRAND_SUB, F_NAV


# ==================================================================
# شريط تنقّل جانبي (يمين الشاشة) لكل شاشات البرنامج
# ==================================================================
class Sidebar(tk.Frame):
    TRIGGER_WIDTH = 28
    EXPANDED_WIDTH = 230

    def __init__(self, parent, items, on_select):
        super().__init__(parent, bg=COLOR_PRIMARY, width=self.EXPANDED_WIDTH)
        self.pack_propagate(False)
        self.grid(row=0, column=1, sticky="ns")

        self.parent = parent
        self.on_select = on_select
        self.items = items
        self.buttons = {}
        self._active = None
        self.pinned = True
        self._after_id = None

        trigger_bg = COLOR_ACCENT
        self.trigger = tk.Frame(parent, bg=trigger_bg, width=self.TRIGGER_WIDTH, cursor="hand2")
        self.trigger.place(relx=1.0, x=-self.TRIGGER_WIDTH, y=0, anchor="ne", height=parent.winfo_height())
        self.trigger.lift()

        tk.Label(self.trigger, text="📂", font=(FONT_NAME, 14), bg=trigger_bg, fg="white").pack(side="top", pady=(18, 4))
        self.pin_indicator = tk.Label(self.trigger, text="📌", font=(FONT_NAME, 10), bg=trigger_bg, fg="white")
        self.pin_indicator.pack(side="bottom", pady=(0, 18))

        self.trigger.bind("<Enter>", self._on_trigger_enter)
        self.trigger.bind("<Leave>", self._on_trigger_leave)
        self.trigger.bind("<Button-1>", self._toggle_pin)
        self.bind("<Enter>", self._on_sidebar_enter)
        self.bind("<Leave>", self._on_sidebar_leave)

        brand = tk.Frame(self, bg=COLOR_PRIMARY)
        brand.pack(fill="x", pady=(24, 8))
        tk.Label(brand, text="🚚", font=(FONT_NAME, 28), bg=COLOR_PRIMARY, fg=COLOR_ACCENT).pack()
        tk.Label(brand, text="نظام إدارة النقل", font=F_BRAND,
                 bg=COLOR_PRIMARY, fg="white").pack(pady=(6, 0))
        tk.Label(brand, text="Transport & Logistics", font=F_BRAND_SUB,
                 bg=COLOR_PRIMARY, fg="#8FA3B8").pack()

        sep = tk.Frame(self, bg=COLOR_ACCENT, height=2)
        sep.pack(fill="x", padx=20, pady=14)

        nav_wrap = tk.Frame(self, bg=COLOR_PRIMARY)
        nav_wrap.pack(fill="both", expand=True)

        for key, icon, label in items:
            self._add_button(nav_wrap, key, icon, label)

        footer = tk.Frame(self, bg=COLOR_PRIMARY)
        footer.pack(fill="x", pady=(0, 16))
        tk.Label(footer, text="© 2026  —  إصدار 4.1", font=(FONT_NAME, 8),
                 bg=COLOR_PRIMARY, fg="#5A7088").pack()

        parent.bind("<Configure>", self._on_parent_resize, add="+")
        self._show_sidebar()

    def _add_button(self, parent, key, icon, label):
        btn = tk.Frame(parent, bg=COLOR_PRIMARY, cursor="hand2")
        btn.pack(fill="x", padx=8, pady=2)
        txt = tk.Label(btn, text=f"{label}   {icon}", font=F_NAV, bg=COLOR_PRIMARY,
                        fg="#C5D5E6", anchor="e", justify="right", padx=16, pady=11)
        txt.pack(fill="x")
        self.buttons[key] = (btn, txt)

        def enter(_e):
            if self._active != key:
                btn.config(bg=COLOR_NAV_HOVER)
                txt.config(bg=COLOR_NAV_HOVER)

        def leave(_e):
            if self._active != key:
                btn.config(bg=COLOR_PRIMARY)
                txt.config(bg=COLOR_PRIMARY)

        def click(_e):
            self.on_select(key)

        for w in (btn, txt):
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)
            w.bind("<Button-1>", click)

    def set_active(self, key):
        self._active = key
        for k, (btn, txt) in self.buttons.items():
            if k == key:
                btn.config(bg=COLOR_NAV_ACTIVE)
                txt.config(bg=COLOR_NAV_ACTIVE, fg="#FFFFFF",
                           font=(FONT_NAME, 10, "bold"))
            else:
                btn.config(bg=COLOR_PRIMARY)
                txt.config(bg=COLOR_PRIMARY, fg="#C5D5E6", font=F_NAV)

    def _on_parent_resize(self, _event=None):
        height = self.parent.winfo_height()
        if height > 1:
            self.config(height=height)
            self.trigger.config(height=height)

    def _on_trigger_enter(self, _event=None):
        if not self.pinned:
            self._show_sidebar()

    def _on_trigger_leave(self, _event=None):
        if not self.pinned:
            self._schedule_hide()

    def _on_sidebar_enter(self, _event=None):
        if not self.pinned:
            self._cancel_hide()

    def _on_sidebar_leave(self, _event=None):
        if not self.pinned:
            self._schedule_hide()

    def _schedule_hide(self):
        self._cancel_hide()
        self._after_id = self.after(400, self._hide_sidebar)

    def _cancel_hide(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _toggle_pin(self, _event=None):
        self.pinned = not self.pinned
        self.pin_indicator.config(text="📌" if self.pinned else "📍")
        if self.pinned:
            self._show_sidebar()
        else:
            self._hide_sidebar()

    def _show_sidebar(self):
        self._cancel_hide()
        self.config(width=self.EXPANDED_WIDTH)
        self.trigger.place_forget()

    def _hide_sidebar(self):
        self.config(width=0)
        self.trigger.place(relx=1.0, x=-self.TRIGGER_WIDTH, y=0, anchor="ne", height=self.parent.winfo_height())
