# -*- coding: utf-8 -*-
"""عناصر واجهة مشتركة: منتقي التاريخ وحقل إدخال التاريخ."""

import calendar
import tkinter as tk
from datetime import datetime

from ..config import get_tk_font
from ..utils import ARABIC_MONTHS, ARABIC_WEEKDAYS
from .theme import COL_BORDER, COL_NAVY, COL_NAVY_SOFT


def open_date_picker(parent, string_var):
    """يفتح نافذة تقويم صغيرة لاختيار تاريخ بدلاً من كتابته يدوياً،
    ويكتب النتيجة داخل string_var بصيغة YYYY-MM-DD."""
    try:
        cur = datetime.strptime((string_var.get() or "").strip(), "%Y-%m-%d")
    except (ValueError, TypeError):
        cur = datetime.today()

    BG = "#F7F9FC"
    win = tk.Toplevel(parent)
    win.title("اختر التاريخ")
    win.transient(parent)
    win.grab_set()
    win.resizable(False, False)
    win.configure(bg=BG, highlightthickness=1, highlightbackground="#D6DEE8")

    state = {"year": cur.year, "month": cur.month}

    top_bar = tk.Frame(win, bg="#0F2B46", height=6)
    top_bar.pack(fill="x")

    header = tk.Frame(win, bg=BG)
    header.pack(fill="x", padx=10, pady=(10, 6))
    tk.Button(header, text="◀", width=3, relief="flat", bg=BG, fg="#0F2B46",
              activebackground="#E8EEF5", cursor="hand2", command=lambda: change_month(1)).pack(side="right")
    tk.Button(header, text="▶", width=3, relief="flat", bg=BG, fg="#0F2B46",
              activebackground="#E8EEF5", cursor="hand2", command=lambda: change_month(-1)).pack(side="left")
    title_lbl = tk.Label(header, font=get_tk_font(11, "bold"), bg=BG, fg="#0F2B46")
    title_lbl.pack(side="left", expand=True, fill="x")

    grid = tk.Frame(win, bg=BG)
    grid.pack(padx=10, pady=(0, 6))

    def render():
        for w in grid.winfo_children():
            w.destroy()
        title_lbl.config(text=f"{ARABIC_MONTHS[state['month']-1]} {state['year']}")
        for i, wd in enumerate(ARABIC_WEEKDAYS):
            tk.Label(grid, text=wd, font=get_tk_font(8, "bold"), width=4, bg=BG, fg="#6B7A8D").grid(row=0, column=i, padx=1, pady=(0, 4))
        cal = calendar.Calendar(firstweekday=0)
        row = 1
        for week in cal.monthdayscalendar(state["year"], state["month"]):
            for col, day in enumerate(week):
                if day == 0:
                    tk.Label(grid, text="", width=4, bg=BG).grid(row=row, column=col)
                else:
                    is_today = (state["year"], state["month"], day) == (cur.year, cur.month, cur.day)
                    b = tk.Button(grid, text=str(day), width=4, relief="flat", cursor="hand2",
                                  font=get_tk_font(9, "bold" if is_today else "normal"),
                                  bg="#C99A3D" if is_today else BG, fg="white" if is_today else "#1C2530",
                                  activebackground="#E8EEF5",
                                  command=lambda d=day: select_day(d))
                    b.grid(row=row, column=col, padx=1, pady=1)
            row += 1

    def change_month(delta):
        m = state["month"] + delta
        y = state["year"]
        if m < 1:
            m, y = 12, y - 1
        elif m > 12:
            m, y = 1, y + 1
        state["month"], state["year"] = m, y
        render()

    def select_day(d):
        string_var.set(f"{state['year']:04d}-{state['month']:02d}-{d:02d}")
        win.destroy()

    def go_today():
        t = datetime.today()
        string_var.set(t.strftime("%Y-%m-%d"))
        win.destroy()

    render()
    tk.Button(win, text="📅 اليوم", relief="flat", bg="#0F2B46", fg="white", cursor="hand2",
              font=get_tk_font(9, "bold"), activebackground="#0B2036", activeforeground="white",
              padx=12, pady=5, command=go_today).pack(pady=(0, 10))


def build_date_field(parent, var):
    """يبني صفاً يحوي حقل إدخال تاريخ نصي بجانبه زر تقويم (📅) لفتح منتقي التاريخ."""
    row = tk.Frame(parent)
    tk.Button(row, text="📅", width=3, relief="flat", bg=COL_NAVY_SOFT, fg=COL_NAVY,
              activebackground=COL_NAVY, activeforeground="white", cursor="hand2",
              command=lambda: open_date_picker(row.winfo_toplevel(), var)).pack(side="right", padx=(0, 4), ipady=2)
    entry = tk.Entry(row, textvariable=var, font=get_tk_font(10), justify="right",
                      relief="solid", bd=1, highlightthickness=1, highlightbackground=COL_BORDER)
    entry.pack(side="right", fill="x", expand=True, ipady=3)
    return row, entry
