# -*- coding: utf-8 -*-
"""تبويب الرسوم البيانية في التقارير: يعمل مع matplotlib إن توفرت،
وإلا يعرض رسالة ودية بدل كسر الشاشة (التثبيت: pip install matplotlib)."""

import tkinter as tk
from ui.theme import COLOR_CARD, COLOR_TEXT, F_BODY, F_BOLD, card_frame


def _mpl_available():
    try:
        import matplotlib  # noqa: F401
        return True
    except ImportError:
        return False


def build_charts_card(parent_frame, refresh_callback):
    """يبني بطاقة الرسوم البيانية ويربط زر التحديث بـ refresh_callback."""
    box = card_frame(parent_frame, "الرسوم البيانية (تحتاج matplotlib)")
    box.pack(fill="both", expand=True, padx=16, pady=(8, 8))
    body = box.body
    if not _mpl_available():
        tk.Label(body, text="الرسوم البيانية غير متاحة — ثبّت الحزمة بالأمر:\n"
                            "pip install matplotlib ثم أعد تشغيل البرنامج.",
                 font=F_BODY, bg=COLOR_CARD, fg=COLOR_TEXT,
                 justify="right").pack(padx=14, pady=14)
        return None, None
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure

    fig = Figure(figsize=(8, 4.2), dpi=100)
    fig.patch.set_facecolor("white")
    canvas = FigureCanvasTkAgg(fig, master=body)
    canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(4, 6))
    bar = tk.Frame(body, bg=COLOR_CARD)
    bar.pack(fill="x", padx=14, pady=(0, 10))
    tk.Button(bar, text="تحديث الرسوم", font=F_BOLD, command=refresh_callback,
              bg="#6B2B1F", fg="white", relief="flat",
              padx=14, pady=4).pack(side="right")
    return fig, canvas


def draw_charts(fig, months=6):
    """يرسم: (1) إيراد/مصروف/ربح شهري (2) أعلى 5 عملاء. يعمل فوق analytics."""
    from core.analytics import monthly_series, top_clients

    fig.clear()
    rows = monthly_series(months)
    labels = [r["month"][2:] for r in rows]
    rev = [r["revenue"] for r in rows]
    exp = [r["expenses"] for r in rows]
    prof = [r["profit"] for r in rows]

    ax1 = fig.add_subplot(1, 2, 1)
    x = range(len(labels))
    w = 0.26
    ax1.bar([i - w for i in x], rev, width=w, label="Revenue", color="#2E7D42")
    ax1.bar(x, exp, width=w, label="Expenses", color="#9C2B20")
    ax1.bar([i + w for i in x], prof, width=w, label="Profit", color="#D9A441")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels, rotation=45, fontsize=8)
    ax1.set_title("Monthly revenue vs expenses", fontsize=10)
    ax1.legend(fontsize=8)
    ax1.grid(axis="y", alpha=0.3)

    ax2 = fig.add_subplot(1, 2, 2)
    top = top_clients(5)
    if top:
        names = [n for n, _ in top][::-1]
        vals = [v for _, v in top][::-1]
        ax2.barh(names, vals, color="#6B2B1F")
        ax2.set_title("Top clients", fontsize=10)
        ax2.tick_params(labelsize=8)
    else:
        ax2.text(0.5, 0.5, "No invoices yet", ha="center", va="center")
        ax2.set_title("Top clients", fontsize=10)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            fig.tight_layout()
        except Exception:
            pass
