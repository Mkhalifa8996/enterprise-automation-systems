# -*- coding: utf-8 -*-
"""عناصر الواجهة القابلة لإعادة الاستخدام (بطاقات، حقول، أزرار)."""

import tkinter as tk
from tkinter import ttk
from .app_config import COLOR_ACCENT, COLOR_BG, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_CARD, COLOR_DANGER, COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_ROW_ALT, COLOR_SHADOW, COLOR_TEXT, FONT_NAME, F_BODY, F_BOLD, F_H2, PAD_BUTTON, PAD_BUTTON_V, PAD_CARD, PAD_INNER
from .ui_helpers import log_exception


class ToolTip:
    def __init__(self, widget, text=""):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self._id = None
        widget.bind("<Enter>", self._schedule_show, add="+")
        widget.bind("<Leave>", self._schedule_hide, add="+")
        widget.bind("<Motion>", self._on_motion, add="+")

    def _schedule_show(self, _event=None):
        self._cancel_hide()
        if self.tip_window or not self.text:
            return
        try:
            self._id = self.widget.after(600, self._show)
        except Exception as _log_exc: log_exception("_schedule_show", _log_exc)

    def _schedule_hide(self, _event=None):
        self._cancel_show()
        try:
            self._id = self.widget.after(150, self._hide)
        except Exception as _log_exc: log_exception("_schedule_hide", _log_exc)

    def _cancel_show(self):
        if self._id:
            try:
                self.widget.after_cancel(self._id)
            except Exception as _log_exc: log_exception("_cancel_show", _log_exc)
            self._id = None

    def _cancel_hide(self):
        if self._id:
            try:
                self.widget.after_cancel(self._id)
            except Exception as _log_exc: log_exception("_cancel_hide", _log_exc)
            self._id = None

    def _on_motion(self, event):
        if self.tip_window:
            try:
                self.tip_window.wm_geometry(f"+{event.x_root + 12}+{event.y_root + 12}")
            except Exception as _log_exc: log_exception("_on_motion", _log_exc)

    def _show(self):
        if self.tip_window:
            return
        try:
            x = self.widget.winfo_pointerx() + 12
            y = self.widget.winfo_pointery() + 12
            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            label = tk.Label(tw, text=self.text, justify="right", bg="#1A2B4A", fg="#fff",
                             font=(FONT_NAME, 9), relief="flat", bd=0, padx=8, pady=4)
            label.pack()
        except Exception as _log_exc: log_exception("_show", _log_exc)

    def _hide(self):
        if self._id:
            try:
                self.widget.after_cancel(self._id)
            except Exception as _log_exc: log_exception("_hide", _log_exc)
            self._id = None
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except Exception as _log_exc: log_exception("_hide", _log_exc)
            self.tip_window = None

    def update_text(self, text):
        self.text = text
        if self.tip_window:
            try:
                for child in self.tip_window.winfo_children():
                    child.destroy()
                tk.Label(self.tip_window, text=self.text, justify="right", bg="#1A2B4A", fg="#fff",
                         font=(FONT_NAME, 9), relief="flat", bd=0, padx=8, pady=4).pack()
            except Exception as _log_exc: log_exception("update_text", _log_exc)

def tooltip(widget, text=""):
    if not text:
        return
    ToolTip(widget, text)

def card_frame(parent, title=None, accent=True):
    """بطاقة بيضاء بظل خفيف وحواف عصرية تُستخدم كإطار موحّد لكل قسم."""
    outer = tk.Frame(parent, bg=COLOR_SHADOW)
    inner = tk.Frame(outer, bg=COLOR_CARD)
    inner.pack(fill="both", expand=True, padx=2, pady=2)
    if title:
        head = tk.Frame(inner, bg=COLOR_CARD)
        head.pack(fill="x", padx=PAD_CARD, pady=(14, 4))
        tk.Label(head, text=title, font=F_H2, bg=COLOR_CARD, fg=COLOR_PRIMARY,
                 anchor="e", justify="right").pack(fill="x")
        sep = tk.Frame(inner, bg=COLOR_ACCENT if accent else COLOR_BORDER, height=2)
        sep.pack(fill="x", padx=PAD_CARD, pady=(0, PAD_INNER))
    outer.body = inner
    return outer

def modern_entry(parent, var, font=F_BODY, justify="right", state="normal",
                 width=None, ipady=4):
    """حقل إدخال عصري بحدود ناعمة وحالة تركيز مميّزة."""
    entry = tk.Entry(parent, textvariable=var, font=font, justify=justify,
                     state=state, relief="flat", bd=0,
                     highlightthickness=2, highlightbackground=COLOR_BORDER,
                     highlightcolor=COLOR_PRIMARY_LIGHT,
                     insertbackground=COLOR_TEXT)
    if width:
        entry.config(width=width)
    entry.pack(fill="x", ipady=ipady)
    return entry

def make_btn(parent, text, command, variant="secondary", **kw):
    """زر عصري موحّد — يستخدم tk.Button لضمان ظهور النص على كل الأنظمة."""
    cfg = {
        "accent": dict(bg=COLOR_ACCENT, fg=COLOR_PRIMARY,
                       activebackground="#D49B30", activeforeground=COLOR_PRIMARY,
                       font=F_BOLD),
        "secondary": dict(bg=COLOR_BORDER_LIGHT, fg=COLOR_TEXT,
                          activebackground=COLOR_BORDER, activeforeground=COLOR_PRIMARY,
                          font=F_BODY),
        "danger": dict(bg="#FED7D7", fg=COLOR_DANGER,
                       activebackground="#FEB2B2", activeforeground=COLOR_DANGER,
                       font=F_BODY),
    }.get(variant, dict(bg=COLOR_BORDER_LIGHT, fg=COLOR_TEXT,
                         activebackground=COLOR_BORDER, activeforeground=COLOR_PRIMARY,
                         font=F_BODY))
    cfg.update(kw)
    cfg.setdefault("padx", PAD_BUTTON)
    cfg.setdefault("pady", PAD_BUTTON_V)
    return tk.Button(parent, text=text, command=command, relief="flat", bd=0,
                     anchor="center", justify="center",
                     cursor="hand2", **cfg)

def scrollable_pane(parent, bg=COLOR_BG):
    """حاوية تمرير رأسية موحّدة تلتفّ محتوى أي شاشة.

    تعيد (الإطار الخارجي، إطار المحتوى). يُسجَّل الإطار الخارجي في نظام
    التنقّل، بينما يُبنى المحتوى داخل إطار المحتوى المرتبط باللوحة.
    """
    outer = tk.Frame(parent, bg=bg)
    canvas = tk.Canvas(outer, bg=bg, highlightthickness=0, bd=0)
    scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    # الشريط العمودي على اليمين كما في الواجهات العربية، والمحتوى يساره.
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    content = tk.Frame(canvas, bg=bg)
    window = canvas.create_window((0, 0), window=content, anchor="nw")
    content.bind("<Configure>",
                 lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
    outer.canvas = canvas
    outer.content = content
    return outer, content

def _nearest_canvas(widget):
    """أقرب لوحة رسم تحوي عنصراً (الأعمق أولاً)، أو None إن لم توجد."""
    current = widget
    while current is not None:
        parent = getattr(current, "master", None)
        if isinstance(parent, tk.Canvas):
            return parent
        current = parent
    return None

def _is_descendant_of(widget, ancestor):
    """هل يندرج العنصر ضمن شجرة العنصر المحدد؟"""
    current = getattr(widget, "master", None)
    while current is not None:
        if current is ancestor:
            return True
        current = getattr(current, "master", None)
    return False

def apply_table_style(tree):
    tree.tag_configure("odd", background=COLOR_ROW_ALT)
    tree.tag_configure("selected", foreground="white")
    tree.tag_configure("hover", background="#EDF2F7")

    def _on_hover(event):
        item = tree.identify_row(event.y)
        if item and tree.item(item, "tags"):
            tree.tk.call(tree, "tag", "remove", "hover", tree.get_children())
            tree.tk.call(tree, "tag", "add", "hover", item)

    def _on_leave(event):
        tree.tk.call(tree, "tag", "remove", "hover", tree.get_children())

    tree.bind("<Motion>", _on_hover, add="+")
    tree.bind("<Leave>", _on_leave, add="+")

def center_dialog(dialog, parent=None):
    dialog.update_idletasks()
    if parent is None:
        parent = dialog.master
    try:
        px = parent.winfo_x()
        py = parent.winfo_y()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        dw = dialog.winfo_width()
        dh = dialog.winfo_height()
        x = px + (pw - dw) // 2
        y = py + (ph - dh) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    except Exception as _log_exc: log_exception("center_dialog", _log_exc)
