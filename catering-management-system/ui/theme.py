# -*- coding: utf-8 -*-
"""الهوية البصرية: الألوان والخطوط والثوابت، وعناصر مشتركة (بطاقة، تحويل نص آمن)."""

import tkinter as tk
from tkinter import ttk
import restaurant_data as rd


FONT_NAME = rd.FONT_NAME

# ======================================================================
# لوحة الألوان والخطوط - هوية بصرية دافئة تناسب مطعماً (كستنائي وذهبي)
# ======================================================================
COLOR_PRIMARY = "#6B2B1F"      # كستنائي/بني محمر أساسي (الهوية/الشريط الجانبي)
COLOR_PRIMARY_LIGHT = "#8C4632"
COLOR_ACCENT = "#D9A441"       # ذهبي دافئ للتمييز
COLOR_BG = "#F7F1EA"           # خلفية عامة فاتحة دافئة
COLOR_CARD = "#FFFFFF"         # خلفية البطاقات
COLOR_TEXT = "#2A1E19"
COLOR_MUTED = "#8A7468"
COLOR_BORDER = "#E7DACB"
COLOR_SUCCESS = "#2E7D42"
COLOR_DANGER = "#9C2B20"
COLOR_NAV_HOVER = "#823B29"
COLOR_NAV_ACTIVE = "#D9A441"

F_TITLE = (FONT_NAME, 15, "bold")
F_SUBTITLE = (FONT_NAME, 10)
F_LABEL = (FONT_NAME, 9)
F_BODY = (FONT_NAME, 10)

F_BOLD = (FONT_NAME, 10, "bold")
F_NAV = (FONT_NAME, 11)
F_H2 = (FONT_NAME, 12, "bold")


def safe_str(v):
    return "" if v is None else str(v)


def card_frame(parent, title=None):
    """بطاقة بيضاء بحوامل بسيطة تُستخدم كإطار موحّد لكل قسم في الشاشات."""
    outer = tk.Frame(parent, bg=COLOR_BORDER)
    inner = tk.Frame(outer, bg=COLOR_CARD)
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    if title:
        head = tk.Frame(inner, bg=COLOR_CARD)
        head.pack(fill="x", padx=14, pady=(12, 4))
        tk.Label(head, text=title, font=F_H2, bg=COLOR_CARD, fg=COLOR_PRIMARY,
                 anchor="e", justify="right").pack(fill="x")
        sep = tk.Frame(inner, bg=COLOR_ACCENT, height=2)
        sep.pack(fill="x", padx=14, pady=(0, 8))
    outer.body = inner
    return outer


# =====================================================================
# إطار قابل للتمرير — يلف محتوى طويل بعدوي سكروول عمودي
# =====================================================================
class ScrollableFrame(tk.Frame):
    """
    إطار يحتوي على Canvas + Scrollbar لعرض محتوى طويل.
    يُستَخدم داخل الشاشات التي تتجاوز ارتفاع النافذة (مثل التقارير).
    الواجهة inner تُضاف إليها العناصر عبر .inner.
    """
    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self._canvas = tk.Canvas(self, bg=COLOR_BG, highlightthickness=0)
        self._vsb = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vsb.set)
        self._vsb.pack(side="left", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self._canvas, bg=COLOR_BG)
        self._window = self._canvas.create_window(
            (0, 0), window=self.inner, anchor="nw", width=0)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # تمرير بالماوس — يعمل داخل الإطار ويتوقف عند الخروج
        self.inner.bind("<Enter>", self._on_enter)
        self.inner.bind("<Leave>", self._on_leave)

    def _on_inner_configure(self, _e):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        w = self._canvas.winfo_width()
        if w > 0:
            self._canvas.itemconfig(self._window, width=w)

    def _on_canvas_configure(self, e):
        self._canvas.itemconfig(self._window, width=e.width)

    def _on_enter(self, _e=None):
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_leave(self, _e=None):
        self._canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, e):
        if e.delta:
            delta = int(-e.delta / 120)
        else:  # Linux
            delta = -1 if e.num == 5 else 1
        self._canvas.yview_scroll(delta, "unit")
