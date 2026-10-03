# -*- coding: utf-8 -*-
"""طباعة كشوف الحساب وملخصات السجلات."""

import html, os, re, tempfile, webbrowser
from datetime import date
from . import data as td
from .print_letterhead import LETTERHEAD_PRINT_STYLE, _brand_ar, _brand_en, company_letterhead_html
from .print_theme import PRINT_FOOTER_HTML, PRINT_GOLD, PRINT_INK, PRINT_LINE, PRINT_MUTED, PRINT_NAVY, PRINT_ROW_ALT, apply_a4_print_layout, apply_print_footer
from .ui_helpers import safe_str


# ==================================================================
# طباعة ملخص السجلات — دالة عامة تستدعيها كل شاشات البرنامج
# ==================================================================
# كانت معرّفة كطريقة داخل «TransportApp» بينما تستدعيها الشاشات باسمها
# المجرّد، فكان زر الطباعة يفشل بـ NameError في كل شاشات البرنامج.
def generate_and_open_summary_print(title, fields, rows):
    """يفتح ملخصاً منسقاً للطباعة للسجلات المعروضة في أي شاشة."""
    headers_html = "".join(f"<th>{html.escape(label)}</th>" for _key, label in fields)
    rows_html = "".join(
    "<tr>" + "".join(
        f"<td>{html.escape(safe_str(row.get(key, '')))}</td>" for key, _label in fields
    ) + "</tr>"
    for row in rows
    ) or f"<tr><td colspan=\"{max(1, len(fields))}\">لا توجد سجلات للطباعة.</td></tr>"
    html_content = f"""<!doctype html>
    <html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>ملخص {html.escape(title)}</title>
    <style>
    body{{font-family:Tahoma,Arial,sans-serif;color:{PRINT_INK};padding:24px;}}
    h1{{color:{PRINT_NAVY};font-size:22px;margin:0 0 6px;}} .meta{{color:{PRINT_MUTED};margin-bottom:18px;}}
    table{{border-collapse:collapse;width:100%;font-size:11px;}} th{{background:{PRINT_NAVY};color:#fff;}}
    th,td{{border:1px solid {PRINT_LINE};padding:8px;text-align:right;vertical-align:top;}}
    tr:nth-child(even){{background:{PRINT_ROW_ALT};}} button{{padding:10px 24px;background:{PRINT_GOLD};border:0;cursor:pointer;font-weight:bold;}}
    @media print{{.noprint{{display:none;}} body{{padding:0;}}}}
    </style></head><body>
    <h1>ملخص سجل {html.escape(title)}</h1><div class="meta">عدد السجلات: {len(rows)} — تاريخ الطباعة: {date.today().isoformat()}</div>
    <table><thead><tr>{headers_html}</tr></thead><tbody>{rows_html}</tbody></table>
    <p class="noprint"><button onclick="window.print()">طباعة الملخص</button></p>
    </body></html>"""
    tmp_path = os.path.join(tempfile.gettempdir(), f"transport_summary_{date.today().isoformat()}.html")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(apply_a4_print_layout(html_content))
    webbrowser.open("file://" + tmp_path)

def generate_and_open_customer_statement(customer, invoices, payments=None, date_from="", date_to="", company=""):
    """يفتح كشف الحساب بالحركات المدينة (الفواتير) والدائنة (الدفعات)."""
    invoices = sorted(invoices, key=lambda row: (safe_str(row.get("date")), td.safe_int(row.get("invoice_no"))))
    if payments is None:
        payments = [p for p in td.load_payments() if safe_str(p.get("customer")) == customer]
        movements = []
        for inv in invoices:
            movements.append((safe_str(inv.get("date")), 0, td.safe_int(inv.get("invoice_no")), "invoice", inv))
        for payment in payments:
            movements.append((safe_str(payment.get("date")), 1, td.safe_int(payment.get("id")), "payment", payment))
        movements.sort(key=lambda row: (row[0], row[1], row[2]))
        balance = 0.0
        rows_html = []
        for _date, _kind_order, _number, kind, record in movements:
            if kind == "invoice":
                amount = td.safe_float(record.get("total"))
                balance += amount
                rows_html.append(
                    f"<tr><td class='c'>{html.escape(safe_str(record.get('date')))}</td>"
                    f"<td>{html.escape('فاتورة رقم ' + safe_str(record.get('invoice_no')))}</td>"
                    f"<td class='c'>{html.escape(safe_str(record.get('invoice_no')))}</td>"
                    f"<td class='c'>{html.escape(safe_str(record.get('declaration_no')) or '—')}</td>"
                    f"<td class='c'>{amount:.3f}</td><td class='c'>—</td><td class='c'>{balance:.3f}</td>"
                    f"<td class='c status-unpaid'>غير مسددة</td></tr>"
                )
            else:
                amount = td.safe_float(record.get("amount"))
                balance -= amount
                reference = safe_str(record.get("reference")) or safe_str(record.get("id"))
                payment_description = "دفعة واردة"
                if safe_str(record.get("invoice_no")).strip():
                    payment_description += " على فاتورة " + safe_str(record.get("invoice_no"))
                if safe_str(record.get("notes")):
                    payment_description += " - " + safe_str(record.get("notes"))
                rows_html.append(
                    f"<tr><td class='c'>{html.escape(safe_str(record.get('date')))}</td>"
                    f"<td>{html.escape(payment_description)}</td>"
                    f"<td class='c'>{html.escape(reference)}</td><td class='c'>—</td>"
                    f"<td class='c'>—</td><td class='c'>{amount:.3f}</td><td class='c'>{balance:.3f}</td>"
                    f"<td class='c' dir='rtl'>مسددة</td></tr>"
                )
        total = sum(td.safe_float(inv.get("total")) for inv in invoices)
    logo_svg = """<svg class="logo" viewBox="0 0 150 100"><path d="M8 70h134M28 64c20-8 42-7 62 1 18 7 31 5 48-2" fill="none" stroke="#1b314c" stroke-width="7"/><path d="M39 61 65 22l18 39M65 22v42M65 35l39-12-17 25 25 8" fill="none" stroke="#1b314c" stroke-width="5"/><path d="M28 72c27 16 65 16 96 0" fill="none" stroke="#1b314c" stroke-width="6"/></svg>"""
    html_content = f"""<!doctype html>
    <html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>كشف حساب {html.escape(customer)}</title>
    <style>
    @page{{size:A4;margin:10mm}}*{{box-sizing:border-box}}body{{font-family:Tahoma,Arial,sans-serif;color:#1c2530;margin:0;padding:12px;background:#f3f6fa}}.page{{max-width:900px;margin:auto;background:#fff;border:2px solid #0f2b46;border-radius:10px;padding:0 10px;min-height:270mm}}.header{{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #0f2b46;padding:8px 4px 6px}}.brand-en{{direction:ltr;text-align:left;font-size:16px;font-weight:bold;line-height:1.15}}.brand-ar{{text-align:right;font-size:17px;font-weight:bold;line-height:1.15}}.logo{{width:100px;height:62px}}.title{{text-align:center;color:#0f2b46;font-size:17px;font-weight:bold;padding:9px 0 5px;border-bottom:1px solid #dfe7ef}}.meta{{display:flex;justify-content:space-between;gap:10px;background:#f5f8fa;border:1px solid #e7edf3;border-radius:8px;padding:10px;margin:12px 0;font-size:13px}}.meta b{{color:#0f2b46}}table{{width:100%;border-collapse:collapse;font-size:12px;border:1px solid #e7edf3}}th{{background:#0f2b46;color:#fff;padding:8px;text-align:center}}td{{padding:7px;border-bottom:1px solid #e7edf3}}.c{{text-align:center}}tr:nth-child(even){{background:#f7fafd}}.summary{{margin-top:15px;margin-right:auto;width:310px;background:#f5f8fa;border:1px solid #e7edf3;border-radius:8px;padding:10px;font-size:13px}}.summary div{{display:flex;justify-content:space-between;padding:4px 0}}.summary .final{{font-weight:bold;color:#0f2b46;border-top:2px solid #c99a3d;margin-top:4px;padding-top:7px}}.footer{{margin-top:22px;padding-top:7px;border-top:1px solid #ddd;text-align:center;color:#777;font-size:10px;line-height:1.6}}.noprint{{text-align:center;margin:18px}}button{{background:#0f2b46;color:#fff;border:0;border-radius:8px;padding:10px 28px;font-weight:bold;cursor:pointer}}@media print{{.noprint{{display:none}}body{{background:#fff;padding:0}}.page{{border:0;min-height:0}}}}
    </style></head><body><div class="page"><div class="header"><div class="brand-en">{_brand_en()}</div>{logo_svg}<div class="brand-ar">{_brand_ar()}</div></div><div class="title">كشف حساب عميل — Customer Statement</div><div class="meta"><div><b>العميل:</b> {html.escape(customer)}</div><div><b>عدد الفواتير:</b> {len(invoices)}</div><div><b>عدد الدفعات:</b> {len(payments)}</div><div><b>التاريخ:</b> {date.today().isoformat()}</div></div><table><thead><tr><th>التاريخ</th><th>نوع البيان</th><th>رقم المستند</th><th>مدين</th><th>دائن</th><th>الرصيد</th></tr></thead><tbody>{''.join(rows_html)}</tbody></table><div class="summary"><div><span>إجمالي الفواتير:</span><span>{total:.3f} د.ك</span></div><div><span>إجمالي الدفعات:</span><span>{sum(td.safe_float(p.get('amount')) for p in payments):.3f} د.ك</span></div><div class="final"><span>الرصيد المستحق:</span><span>{balance:.3f} د.ك</span></div></div><div class="footer">{html.escape(td.COMPANY_ADDRESS_AR)} — {html.escape(td.COMPANY_ADDRESS_EN)}<br>Tel.: {html.escape(td.COMPANY_PHONE)} — E-mail: {html.escape(td.COMPANY_EMAIL)}</div></div><div class="noprint"><button onclick="window.print()">طباعة كشف الحساب</button></div></body></html>"""
    # تذييل ثابت لكشف حساب العميل، حتى يظهر مهما كانت بيانات الشركة القديمة.
    html_content = html_content.replace(
    '<div class="footer">' + html.escape(td.COMPANY_ADDRESS_AR) +
    ' — ' + html.escape(td.COMPANY_ADDRESS_EN) + '<br>Tel.: ' +
    html.escape(td.COMPANY_PHONE) + ' — E-mail: ' + html.escape(td.COMPANY_EMAIL) +
    '</div>',
    '<div class="footer">' + PRINT_FOOTER_HTML + '</div>',
    )
    html_content = apply_print_footer(html_content)
    html_content = html_content.replace("</style>", f"{LETTERHEAD_PRINT_STYLE}</style>", 1)
    filter_line = f"الفترة: {html.escape(date_from or '—')} إلى {html.escape(date_to or '—')}"
    if company and company != "الكل":
        filter_line += f" | الشركة: {html.escape(company)}"
    html_content = html_content.replace(
        '<div class="meta">',
        f'<div class="statement-filters">{filter_line}</div><div class="meta">',
        1,
    )
    shared_header = company_letterhead_html("كشف حساب عميل", document_date=date.today().isoformat())
    html_content = html_content.replace('<div class="page">', '<div class="page" style="border:0;min-height:0;padding:0;">', 1)
    html_content = re.sub(r"<div class=\"header\">.*?(?=<div class=\"title\">)", shared_header, html_content, count=1, flags=re.S)
    statement_header = "<thead><tr><th>التاريخ</th><th>البيان</th><th>رقم المستند</th><th>رقم البيان الجمركي</th><th>مدين</th><th>دائن</th><th>الرصيد</th><th>حالة السداد</th></tr></thead>"
    html_content = re.sub(r"<thead><tr>.*?</tr></thead>", statement_header, html_content, count=1, flags=re.S)
    tmp_path = os.path.join(tempfile.gettempdir(), f"transport_statement_{safe_str(customer).replace(' ', '_')}.html")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(apply_a4_print_layout(html_content))
    webbrowser.open(f"file://{tmp_path}")
