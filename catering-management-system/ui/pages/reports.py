# -*- coding: utf-8 -*-
"""شاشة التقارير المالية: الملخص المالي لفترة وطباعته."""

import os
import tempfile
import webbrowser
import tkinter as tk
from tkinter import ttk
from ui import dialogs as messagebox
import restaurant_data as rd
from ui.pages.charts import build_charts_card, draw_charts
from ui.theme import (
    COLOR_BG,
    COLOR_CARD,
    COLOR_TEXT,
    F_LABEL,
    F_BODY,
    card_frame,
    ScrollableFrame,
)


class ReportsPages:
    # ---------------- شاشة التقارير المالية ----------------
    def _build_reports_tab(self):
        frame = tk.Frame(self.pages_area, bg=COLOR_BG)
        scroll = ScrollableFrame(frame)
        scroll.pack(fill="both", expand=True)

        box = card_frame(scroll.inner, "ملخص مالي تشغيلي عن فترة محددة")
        box.pack(fill="x", padx=16, pady=(16, 8))
        row = tk.Frame(box.body, bg=COLOR_CARD)
        row.pack(fill="x", padx=14, pady=(0, 10))

        tk.Label(row, text="من تاريخ (YYYY-MM-DD):", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_TEXT).grid(
            row=0, column=3, padx=6, pady=6)
        self.rep_from = tk.StringVar()
        tk.Entry(row, textvariable=self.rep_from, font=F_BODY, justify="right", width=14,
                 relief="solid", bd=1).grid(row=0, column=2, padx=6)
        tk.Label(row, text="إلى تاريخ (YYYY-MM-DD):", font=F_LABEL, bg=COLOR_CARD, fg=COLOR_TEXT).grid(
            row=0, column=1, padx=6, pady=6)
        self.rep_to = tk.StringVar()
        tk.Entry(row, textvariable=self.rep_to, font=F_BODY, justify="right", width=14,
                 relief="solid", bd=1).grid(row=0, column=0, padx=6)
        ttk.Button(row, text="عرض الملخص", style="Accent.TButton", command=self.show_financial_summary).grid(
            row=1, column=0, columnspan=4, pady=8)

        report_card = card_frame(scroll.inner, "النتائج")
        report_card.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        self.report_text = tk.Text(report_card.body, font=("Consolas", 12), height=16, state="disabled",
                                    relief="flat", bg=COLOR_CARD, highlightthickness=0)
        self.report_text.pack(fill="both", expand=True, padx=14, pady=14)

        buttons = tk.Frame(report_card.body, bg=COLOR_CARD)
        buttons.pack(fill="x", padx=14, pady=(0, 10), anchor="e")
        ttk.Button(buttons, text="طباعة هذا التقرير", style="Accent.TButton", command=self.print_financial_summary).pack(side="right", padx=4)
        ttk.Button(buttons, text="حفظ PDF", command=self.save_summary_pdf).pack(side="right", padx=4)
        ttk.Button(buttons, text="تصدير نسخة Excel", command=self.export_excel_copy).pack(side="right", padx=4)

        self._charts_fig, self._charts_canvas = build_charts_card(
            scroll.inner, self.refresh_charts)

        self.register_page("reports", frame, refreshers=[self.refresh_charts])

    def refresh_charts(self):
        """يرسم الرسوم البيانية للفترة الظاهرة (أو آخر 6 أشهر افتراضياً)."""
        if not getattr(self, "_charts_fig", None):
            return
        try:
            draw_charts(self._charts_fig)
            self._charts_canvas.draw()
        except Exception:
            pass  # لا نكسر شاشة التقارير بسبب الرسم

    def save_summary_pdf(self):
        """يحفظ الملخص المالي الحالي كملف PDF عربي ويفتحه."""
        period = self.report_period()
        if period is None:
            return
        d_from, d_to = period
        try:
            from core.pdf_ar import summary_pdf
        except ImportError:
            messagebox.showwarning(
                "تنبيه",
                "توليد PDF غير متاح — ثبّت الحزم:\n"
                "pip install reportlab arabic-reshaper python-bidi")
            return
        s = rd.financial_summary(d_from, d_to)
        path = os.path.join(tempfile.gettempdir(), "restaurant_report.pdf")
        try:
            summary_pdf(s, d_from, d_to, path)
        except Exception as exc:
            messagebox.showerror("خطأ", "فشل توليد PDF: %s" % exc)
            return
        try:
            os.startfile(path)  # noqa: PGH003 - Windows فقط
        except Exception:
            webbrowser.open("file://%s" % path)

    def report_period(self):
        """
        يقرأ فترة التقرير من الحقول ويتحقق من صيغتها (YYYY-MM-DD).
        يعيد (من, إلى) أو None إذا كانت هناك قيمة غير صالحة.
        """
        d_from = self.rep_from.get().strip()
        d_to = self.rep_to.get().strip()
        for value, label in ((d_from, "حقل «من تاريخ»"), (d_to, "حقل «إلى تاريخ»")):
            if value and not rd.is_iso_date(value):
                messagebox.showwarning("تنبيه", f"{label} يجب أن يكون بصيغة YYYY-MM-DD.")
                return None
        if d_from and d_to and d_from > d_to:
            d_from, d_to = d_to, d_from      # تبديل تلقائي بدل إظهار تقرير فارغ
        return d_from or None, d_to or None

    def show_financial_summary(self):
        period = self.report_period()
        if period is None:
            return
        d_from, d_to = period
        s = rd.financial_summary(d_from, d_to)
        text = (
            f"الفترة: {d_from or 'من البداية'} ← {d_to or 'حتى اليوم'}\n"
            f"{'='*60}\n"
            f"الإيرادات (من الفواتير الصادرة خلال الفترة):        {s['revenue']:.3f} د.ك\n"
            f"مصاريف المشتريات اليومية:                           {s['purchases_cost']:.3f} د.ك\n"
            f"مصاريف الرواتب (خلال الفترة):                       {s['salaries_cost']:.3f} د.ك\n"
            f"المصاريف الشهرية الثابتة (إيجار وغيره):              {s['monthly_expenses_cost']:.3f} د.ك\n"
            f"نثريات يومية (وقود ومستلزمات وغيرها):                {s.get('petty_cash_cost', 0.0):.3f} د.ك\n"
            f"{'-'*60}\n"
            f"إجمالي المصروفات التشغيلية:                          {s['operating_expenses']:.3f} د.ك\n"
            f"صافي الربح التشغيلي للفترة:                          {s['operating_profit']:.3f} د.ك\n"
            f"{'='*60}\n"
            f"مستحقات لم تُحصّل من العملاء (تراكمي):                {s.get('receivables', 0.0):.3f} د.ك\n"
            f"إجمالي مصاريف التأسيس (تراكمي منذ بداية المشروع):    {s['setup_expenses_total']:.3f} د.ك\n"
            f"صافي الربح بعد خصم مصاريف التأسيس (تراكمي):          {s['net_profit_after_setup']:.3f} د.ك\n"
        )
        self.report_text.config(state="normal")
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", text)
        self.report_text.config(state="disabled")

    def export_excel_copy(self):
        """تصدير نسخة Excel من البيانات الحالية للدراسة أو التبادل."""
        try:
            path = rd.export_excel()
        except Exception as exc:
            messagebox.showerror("خطأ", "فشل التصدير: %s" % exc)
            return
        messagebox.showinfo("تم", "حُفظت نسخة Excel في:\n%s" % path)

    def print_financial_summary(self):
        period = self.report_period()
        if period is None:
            return
        d_from, d_to = period
        s = rd.financial_summary(d_from, d_to)
        html = (
            "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'>"
            "<title>تقرير مالي للمطعم</title>"
            "<style>"
            "body{font-family:'Tahoma',sans-serif;color:#2A1E19;padding:28px;}"
            "table{width:100%;border-collapse:collapse;margin-top:14px;font-size:14px;}"
            "td{padding:9px 8px;border-bottom:1px solid #ccc;}"
            "td.amt{text-align:right;font-weight:bold;width:180px;}"
            ".total td{background:#FBF1DE;font-size:15px;border-top:2px solid #D9A441;}"
            ".signrow{display:flex;justify-content:space-between;margin-top:60px;}"
            ".signrow div{border-top:1px solid #999;padding-top:6px;width:200px;text-align:center;font-weight:bold;}"
            ".footer{margin-top:30px;text-align:center;font-size:11px;color:#666;border-top:1px solid #ddd;padding-top:8px;}"
            "@media print{{ button.noprint{{display:none;}} }}"
            "</style></head><body>"
            f"<h1>تقرير مالي تشغيلي</h1>"
            f"<div style='font-size:13px;color:#666;'>الفترة: {d_from or 'من البداية'} ← {d_to or 'حتى اليوم'}</div>"
            f"<table>"
            f"<tr><td style='text-align:right;'>الإيرادات (الفواتير):</td><td class='amt'>{s['revenue']:.3f} د.ك</td></tr>"
            f"<tr><td style='text-align:right;'>مشتريات يومية:</td><td class='amt'>{s['purchases_cost']:.3f} د.ك</td></tr>"
            f"<tr><td style='text-align:right;'>رواتب:</td><td class='amt'>{s['salaries_cost']:.3f} د.ك</td></tr>"
            f"<tr><td style='text-align:right;'>مصاريف شهرية ثابتة:</td><td class='amt'>{s['monthly_expenses_cost']:.3f} د.ك</td></tr>"
            f"<tr><td style='text-align:right;'>نثريات يومية:</td><td class='amt'>{s.get('petty_cash_cost', 0.0):.3f} د.ك</td></tr>"
            f"<tr class='total'><td>إجمالي المصروفات التشغيلية:</td><td class='amt'>{s['operating_expenses']:.3f} د.ك</td></tr>"
            f"<tr class='total'><td>صافي الربح التشغيلي:</td><td class='amt' style='color:#2E7D42;'>{s['operating_profit']:.3f} د.ك</td></tr>"
            f"<tr><td colspan='2' style='height:12px;'></td></tr>"
            f"<tr><td style='text-align:right;'>مستحقات لم تُحصّل من العملاء (تراكمي):</td><td class='amt'>{s.get('receivables', 0.0):.3f} د.ك</td></tr>"
            f"<tr><td style='text-align:right;'>مصاريف التأسيس التراكمية:</td><td class='amt'>{s['setup_expenses_total']:.3f} د.ك</td></tr>"
            f"<tr class='total'><td>صافي الربح بعد التأسيس:</td><td class='amt' style='color:#9C2B20;'>{s['net_profit_after_setup']:.3f} د.ك</td></tr>"
            f"</table>"
            "<div class='signrow'><div>المحاسب</div><div>مدير المطعم</div></div>"
            f"<div class='footer'>{rd.COMPANY_ADDRESS_AR} — {rd.COMPANY_PHONE}<br>{rd.COMPANY_EMAIL}</div>"
            "<button class='noprint' onclick='window.print()' style='margin-top:24px;padding:10px 24px;font-size:14px;'>طباعة التقرير</button>"
            "</body></html>"
        )
        path = os.path.join(tempfile.gettempdir(), "restaurant_report.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open(f"file://{path}")
