# -*- coding: utf-8 -*-
"""
core.pdf_ar — توليد ملفات PDF بالعربية (فواتير، كشوف حساب، تقارير مالية).

يستخدم reportlab مع arabic-reshaper وpython-bidi لعرض النص العربي متصلاً
وبالاتجاه الصحيح، وخط Arial من نظام ويندوز (يدعم العربية).
"""

import os

FONT_DIR = r"C:\Windows\Fonts"
FONT_REGULAR = os.path.join(FONT_DIR, "arial.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "arialbd.ttf")


def _ar(text):
    """يعيد النص العربي مشكّلاً ومعكوس الاتجاه لعرضه الصحيح في PDF."""
    import arabic_reshaper
    from bidi.algorithm import get_display

    s = "" if text is None else str(text)
    if not s:
        return s
    try:
        return get_display(arabic_reshaper.reshape(s))
    except Exception:
        return s


def _register_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for name, path in (("Arabic", FONT_REGULAR), ("Arabic-Bold", FONT_BOLD)):
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception:
                pass  # مسجل مسبقاً


def _base_styles():
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER

    _register_fonts()
    title = ParagraphStyle("title", fontName="Arabic-Bold", fontSize=16,
                           alignment=TA_CENTER, textColor="#6B2B1F", spaceAfter=6)
    head = ParagraphStyle("head", fontName="Arabic", fontSize=11,
                          alignment=TA_RIGHT, spaceAfter=4)
    cell = ParagraphStyle("cell", fontName="Arabic", fontSize=10, alignment=TA_RIGHT)
    cell_c = ParagraphStyle("cell_c", fontName="Arabic", fontSize=10, alignment=TA_CENTER)
    return title, head, cell, cell_c


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Arabic", 8)
    canvas.setFillColor("#777777")
    canvas.drawCentredString(297, 30, _ar("مطعم الضيافة لتقديم الوجبات والولائم — الكويت"))
    canvas.restoreState()


def _table_style():
    from reportlab.platypus import TableStyle
    from reportlab.lib import colors

    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6B2B1F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FBF1DE")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ])


def _build(filename, title_text, header_lines, table_data, col_widths=None):
    """يبني مستند PDF عام: عنوان + سطور رأس + جدول، ويعيده كمسار الملف."""
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
    from reportlab.lib.pagesizes import A4

    title, head, cell, cell_c = _base_styles()
    story = [Paragraph(_ar(title_text), title)]
    for line in header_lines:
        story.append(Paragraph(_ar(line), head))
    story.append(Spacer(1, 10))

    body = [[Paragraph(_ar(h), cell_c) for h in table_data[0]]]
    for row in table_data[1:]:
        cells = []
        for v in row:
            try:
                num = float(str(v).replace(",", ""))
                cells.append(Paragraph("%.3f" % num, cell_c))
            except (ValueError, TypeError):
                cells.append(Paragraph(_ar(v), cell))
        body.append(cells)
    tbl = Table(body, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(_table_style())
    story.append(tbl)

    doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=36, leftMargin=36,
                            topMargin=40, bottomMargin=50, title=title_text)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return filename


def invoice_pdf(inv, items, path):
    """فاتورة عميل: inv قاموس الفاتورة، items قائمة (البيان، المبلغ)."""
    rows = [["البيان", "المبلغ (د.ك)"]]
    total = 0.0
    for desc, amount in items:
        try:
            total += float(amount)
        except (ValueError, TypeError):
            pass
        rows.append([desc, amount])
    rows.append(["الإجمالي — Total", "%.3f" % total])
    try:
        paid = float(inv.get("paid_amount") or 0)
    except (ValueError, TypeError):
        paid = 0.0
    if paid > 0:
        rows.append(["المدفوع — Paid (%s)" % (inv.get("status") or ""), "%.3f" % paid])
        rows.append(["المتبقي — Balance Due", "%.3f" % max(total - paid, 0.0)])
    header = [
        "فاتورة رقم: %s" % inv.get("invoice_no", ""),
        "التاريخ: %s" % inv.get("date", ""),
        "العميل: %s" % inv.get("customer", ""),
    ]
    if inv.get("notes"):
        header.append("ملاحظات: %s" % inv.get("notes"))
    return _build(path, "فاتورة وجبات وضيافة", header, rows, col_widths=[380, 120])


def statement_pdf(statement, date_from, date_to, path):
    """كشف حساب عميل: statement هو ناتج customer_statement()."""
    rows = [["التاريخ", "المستند", "البيان", "مدين (عليه)", "دائن (له)", "الرصيد"]]
    for e in statement["rows"]:
        rows.append([e.get("date", ""), e.get("doc", ""), e.get("description", ""),
                     "%.3f" % float(e.get("debit") or 0),
                     "%.3f" % float(e.get("credit") or 0),
                     "%.3f" % float(e.get("balance") or 0)])
    rows.append(["", "", "الإجمالي",
                 "%.3f" % statement["total_invoiced"],
                 "%.3f" % statement["total_paid"],
                 "%.3f" % statement["balance"]])
    header = [
        "العميل: %s" % statement["customer"],
        "الفترة: %s ← %s" % (date_from or "من البداية", date_to or "حتى اليوم"),
    ]
    return _build(path, "كشف حساب عميل", header, rows,
                  col_widths=[70, 110, 130, 70, 70, 70])


def summary_pdf(summary, date_from, date_to, path):
    """التقرير المالي التشغيلي: summary هو ناتج financial_summary()."""
    s = summary
    rows = [
        ["البند", "المبلغ (د.ك)"],
        ["الإيرادات (الفواتير)", "%.3f" % s["revenue"]],
        ["مشتريات يومية", "%.3f" % s["purchases_cost"]],
        ["رواتب", "%.3f" % s["salaries_cost"]],
        ["مصاريف شهرية ثابتة", "%.3f" % s["monthly_expenses_cost"]],
        ["نثريات يومية", "%.3f" % s.get("petty_cash_cost", 0.0)],
        ["إجمالي المصروفات التشغيلية", "%.3f" % s["operating_expenses"]],
        ["صافي الربح التشغيلي", "%.3f" % s["operating_profit"]],
        ["مستحقات لم تُحصّل (تراكمي)", "%.3f" % s.get("receivables", 0.0)],
        ["مصاريف التأسيس التراكمية", "%.3f" % s["setup_expenses_total"]],
        ["صافي الربح بعد التأسيس", "%.3f" % s["net_profit_after_setup"]],
    ]
    header = ["الفترة: %s ← %s" % (date_from or "من البداية", date_to or "حتى اليوم")]
    return _build(path, "تقرير مالي تشغيلي", header, rows, col_widths=[330, 170])
