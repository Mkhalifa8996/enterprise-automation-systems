# -*- coding: utf-8 -*-
"""الطباعة: إنشاء صفحات HTML مطابقة لشكل الفاتورة الورقية وفتحها للطباعة.

يُبنى مستند HTML ثم يُفتح في المتصفح الافتراضي ليتملك المستخدم أمر الطباعة
(يمكنه الحفظ كـ PDF من نافذة الطباعة). تُجمَّع عدة فواتير أو عدة كشوف في
مستند واحد، كل واحد في صفحته مع فاصل صفحات تلقائي.
"""

import base64
import html as html_module
import os
import tempfile
import webbrowser

from ..config import COMPANY_NAME_AR, COMPANY_NAME_EN, ICON_FILE, LOGO_FILE
from ..data import invoice_payment_status
from ..utils import arabic_currency_words, english_currency_words, fmt_fils3


_LOGO_IMG_HTML_CACHE = None


def _get_logo_img_html():
    """يقرأ شعار الشركة أو أيقونة التطبيق من القرص مرة واحدة فقط ويخزّنه مؤقتاً."""
    global _LOGO_IMG_HTML_CACHE
    if _LOGO_IMG_HTML_CACHE is None:
        image_path = None
        if os.path.exists(ICON_FILE):
            image_path = ICON_FILE
        elif os.path.exists(LOGO_FILE):
            image_path = LOGO_FILE

        if image_path is not None:
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("ascii")
            _LOGO_IMG_HTML_CACHE = (
                f'<img src="data:image/png;base64,{image_b64}" '
                f'alt="شعار الشركة" width="92" height="92">'
            )
        else:
            _LOGO_IMG_HTML_CACHE = ""
    return _LOGO_IMG_HTML_CACHE


def _safe_filename_part(v):
    s = "".join(c for c in str(v) if c.isalnum())
    return s or "x"


def _build_invoice_page_html(inv, logo_img_html):
    """يبني كتلة HTML لصفحة فاتورة واحدة فقط (بدون <html>/<head>/<body> وبدون زر
    الطباعة)، لتُستخدم سواء لطباعة فاتورة واحدة أو ضمن دفعة من عدة فواتير"""
    total = float(inv.get("total") or 0)
    total_d = int(total)
    total_f = round((total - total_d) * 1000)
    total_words = arabic_currency_words(total)
    total_words_en = english_currency_words(total)

    # ترويسة الشركة (معرّفة في config كقيمة واحدة قابلة للتغيير)
    company_ar = html_module.escape(COMPANY_NAME_AR)
    company_en = html_module.escape(COMPANY_NAME_EN)

    def esc(v):
        return html_module.escape(str(v)) if v not in (None, "") else "—"

    rows_html = ""
    for idx, it in enumerate(inv["items"]):
        row_bg = " style=\"background:#F7FAFD;\"" if idx % 2 else ""
        rows_html += f"""
        <tr{row_bg}>
          <td class="c">{idx+1}</td>
          <td><div class="svc-cell"><span class="svc-en">{esc(it['labelEn'])}</span><span class="svc-ar">{esc(it['label'])}</span></div></td>
          <td class="c">{it['dinar'] if it['dinar'] not in ('', None) else '—'}</td>
          <td class="c">{fmt_fils3(it['fils']) if it['fils'] not in ('', None) else '—'}</td>
        </tr>"""

    meta_html = ""
    meta_labels = {
        "declno": "رقم البيان الجمركي", "decldate": "تاريخ البيان الجمركي",
        "port": "المنفذ", "containercount": "عدد الحاويات", "goodstype": "نوع البضاعة",
        "origin": "بلد المنشأ",
    }
    for key, label in meta_labels.items():
        meta_html += f'<div><span class="k">{label}: </span><span class="v">{esc(inv.get(key))}</span></div>'

    return f"""  <div class="page">
  <div class="letterhead">
    <div class="header">
      <div class="brand-en">{company_en}</div>
      <div class="logo">
        {logo_img_html}
      </div>
      <div class="brand-ar">{company_ar}</div>
    </div>
    <div class="subheader">
      <div class="invno-box"><span class="k">رقم الفاتورة :</span> <span class="invno">{esc(inv['invno'])}</span></div>
      <div class="title">فاتورة نقداً / بالحساب<span class="title-en">CASH / CREDIT INVOICE</span></div>
      <div class="date-box"><span class="k">التاريخ :</span> <b>{esc(inv.get('date',''))}</b></div>
    </div>
  </div>
  <div class="rtl-block">
    <div>السادة: <b>{esc(inv.get('customer',''))}</b></div>

    <div class="grid">{meta_html}</div>
  </div>
  <table>
    <thead><tr>
      <th style="width:26px;">م</th>
      <th>نوع الخدمة<span class="th-en">Kind of Service</span></th>
      <th style="width:60px;">دينار</th>
      <th style="width:60px;">فلس</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
        <tfoot><tr class="total-row"><td>المجموع — Total</td><td class="eng">{html_module.escape(total_words_en)}</td><td class="c">{total_d}</td><td class="c">{total_f:03d}</td></tr></tfoot>
    </table>
  {'<div style="margin-top:10px;font-size:11px;"><b>ملاحظات:</b> ' + esc(inv.get('notes','')) + '</div>' if inv.get('notes') else ''}
  <div class="sign"><div>المحاسب</div><div>المستلم</div></div>
  <div class="footer">
    الكويت، حولي، شارع ابن خلدون، قطعة (2) مجمع محمود حمد الملا، الدور الثالث، مكتب رقم (11)<br>
    Kuwait, Hawally, Ibn Khaldoon St. Mahmoud Hamad Al Mulla Comp., 3rd Floor, Office No.: (11)<br>
    Tel.: +965 60039333 - +965 65550298 - +965 50508064 — E-mail: alestedama@gmail.com
  </div>
  </div>"""


_INVOICE_PRINT_STYLE = """
  body{font-family:'Tahoma','Arial',sans-serif;color:#1C2530;padding:5px 12px 5px 12px;margin:0px;background:#F3F6FA;}
  .page{max-width:900px;margin:10px auto;}
  .rtl-block{direction:rtl;}
  .letterhead{border:2px solid #0F2B46;border-radius:10px;padding:0px 8px;margin:0 px;background:#fff;}
  .header{display:flex;justify-content:space-between;align-items:center;gap:12px; margin-top:0px}
  .brand-en{flex:1 1 0;text-align:left;direction:ltr;font-weight:bold;color:#1C2530;font-size:15px;line-height:1.15;}
  .brand-ar{flex:1 1 0;text-align:right;direction:rtl;font-weight:bold;color:#1C2530;font-size:17px;line-height:1.15;}
  .logo{flex:0 0 auto;line-height:0;padding:0 8px;}
  .logo svg,.logo img{display:block;border-radius:8px;height:70px; width:auto; }
  .subheader{display:flex;justify-content:space-between;align-items:center;border-top:2px solid #0F2B46;margin-top:6px;padding-top:4px;font-size:10px;}
  .invno-box{direction:rtl;}
  .invno-box .k{color:#333;}
  .title{text-align:center;font-weight:bold;color:#0F2B46;font-size:10px;}
  .title .title-en{display:block;font-size:10px;font-weight:normal;color:#666;letter-spacing:1px;margin-top:2px;}
  .date-box{direction:rtl;}
  .meta{display:flex;justify-content:space-between;margin-bottom:10px;font-size:13px;}
  .invno{color:#93241F;font-weight:bold;font-size:15px;}
  .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px 18px;font-size:12px;margin-bottom:2px;padding:8px 10px;background:#F5F8FA;border-radius:8px;border:1px solid #E7EDF3;}
  .grid .k{color:#777;} .grid .v{font-weight:bold;}
  table{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px;border:1px solid #E7EDF3;border-radius:8px;overflow:hidden;}
  th{background:#0F2B46;color:#fff;padding:7px 8px;text-align:center;}
  th .th-en{display:block;font-weight:normal;font-size:9.5px;color:#C99A3D;margin-top:1px;}
  td{padding:6px 8px;border-bottom:1px solid #E7EDF3;}
  td.c{text-align:center;}
  .svc-cell{display:flex;justify-content:space-between;align-items:center;gap:10px;}
  .svc-en{direction:ltr;text-align:left;color:#333;font-size:11px;flex:1 1 0;}
  .svc-ar{direction:rtl;text-align:right;font-size:12.5px;flex:1 1 0;}
  .total-row td{font-weight:bold;background:#FBF6EA;border-top:2px solid #C99A3D;}
    td.eng{text-align:left;padding-left:10px;font-size:12px;color:#333;direction:ltr}
  .sign{display:flex;justify-content:space-between;margin-top:5px;font-size:13px;font-weight:bold;}
  .sign div{border-top:1px solid #999;padding-top:6px;width:150px;text-align:center;}
  .footer{margin-top:18px;text-align:center;font-size:10px;color:#777;border-top:1px solid #ddd;padding-top:4px;line-height:1.6;}
  .print-btn{background:#0F2B46;color:#fff;border:none;border-radius:8px;padding:11px 30px;font-size:14px;font-weight:bold;font-family:inherit;cursor:pointer;box-shadow:0 2px 6px rgba(15,43,70,.25);}
  .print-btn:hover{background:#081726;}
  .doc-wrap{page-break-after:always;}
  .doc-wrap:last-of-type{page-break-after:auto;}
  @media screen { .doc-wrap + .doc-wrap{margin-top:22px;border-top:3px dashed #C7D2DF;padding-top:22px;} }
  @media print { .noprint{display:none;} body{background:#fff;} }
"""


def generate_and_open_print(inv):
    """يطبع فاتورة واحدة (يستخدم دالة الدفعة أدناه بقائمة من عنصر واحد)"""
    generate_and_open_invoices_print([inv])


def generate_and_open_invoices_print(invoices):
    """يفتح فاتورة واحدة أو عدة فواتير مختارة دفعة واحدة في مستند HTML واحد قابل
    للطباعة، بحيث تكون كل فاتورة في صفحتها الخاصة (فاصل صفحة تلقائي بينها عند
    الطباعة الورقية) مع زر طباعة واحد يطبع الجميع دفعة واحدة"""
    if not invoices:
        return
    logo_img_html = _get_logo_img_html()
    pages_html = "\n".join(
        f'<div class="doc-wrap">{_build_invoice_page_html(inv, logo_img_html)}</div>'
        for inv in invoices
    )
    n = len(invoices)
    btn_text = "🖨 طباعة الفاتورة" if n == 1 else f"🖨 طباعة كل الفواتير ({n})"

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="ltr"><head><meta charset="UTF-8">
<style>{_INVOICE_PRINT_STYLE}</style></head>
<body>
{pages_html}
  <div class="noprint" style="text-align:center;margin-top:20px;">
    <button class="print-btn" onclick="window.print()">{btn_text}</button>
  </div>
</body></html>"""

    if n == 1:
        fname = f"invoice_{_safe_filename_part(invoices[0]['invno'])}.html"
    else:
        fname = f"invoices_batch_{_safe_filename_part(invoices[0]['invno'])}_{_safe_filename_part(invoices[-1]['invno'])}_{n}.html"
    tmp_path = os.path.join(tempfile.gettempdir(), fname)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file://{tmp_path}")


def _build_statement_page_html(customer, date_from, date_to, invoices, payments, logo_img_html):
    """يبني كتلة HTML لكشف حساب عميل واحد فقط (بدون <html>/<head>/<body> وبدون
    زر الطباعة)، لتُستخدم سواء لكشف عميل واحد أو ضمن دفعة من عدة عملاء"""

    def esc(v):
        return html_module.escape(str(v)) if v not in (None, "") else "—"

    STATUS_LABELS = {"paid": "مسددة", "partial": "جزئية", "unpaid": "غير مسددة"}
    STATUS_CLASS = {"paid": "st-paid", "partial": "st-partial", "unpaid": "st-unpaid"}

    # حالة سداد كل فاتورة (مسددة / جزئية / غير مسددة) تُحسب من فواتير ودفعات
    # هذا العميل نفسه، بنفس الطريقة المعتمدة في تبويب سجل الفواتير.
    status_map = invoice_payment_status(invoices, payments)

    # توحيد كل الحركات (فواتير = مدين، دفعات = دائن) في قائمة واحدة مرتبة زمنياً
    txns = []
    for inv in invoices:
        invno = str(inv.get("invno", ""))
        st = status_map.get(invno, {}).get("status", "unpaid")
        txns.append({
            "date": str(inv.get("date", "")),
            "desc": "فاتورة",
            "doc": invno,
            "declno": str(inv.get("declno", "") or ""),
            "debit": float(inv.get("total") or 0),
            "credit": 0.0,
            "status_label": STATUS_LABELS.get(st, ""),
            "status_class": STATUS_CLASS.get(st, ""),
            "sort_key": (str(inv.get("date", "")), 0, invno),
        })
    for p in payments:
        txns.append({
            "date": str(p.get("date", "")),
            "desc": "سند قبض",
            "doc": str(p.get("id", "")),
            "declno": "",
            "debit": 0.0,
            "credit": float(p.get("amount") or 0),
            "status_label": "",
            "status_class": "",
            "sort_key": (str(p.get("date", "")), 1, str(p.get("id", ""))),
        })
    txns.sort(key=lambda t: t["sort_key"])

    # الرصيد الافتتاحي = صافي كل الحركات قبل تاريخ "من" (إن وُجد)
    opening = 0.0
    period_txns = []
    for t in txns:
        if date_from and t["date"] < date_from:
            opening += t["debit"] - t["credit"]
            continue
        if date_to and t["date"] > date_to:
            continue
        period_txns.append(t)

    rows_html = ""
    running = opening
    if date_from:
        rows_html += f"""
        <tr class="opening-row">
          <td class="c">{esc(date_from)}</td>
          <td>رصيد افتتاحي (مرحّل من فترة سابقة)</td>
          <td class="c">—</td>
          <td class="c">—</td>
          <td class="c">—</td>
          <td class="c">—</td>
          <td class="c">{running:.3f}</td>
          <td class="c">—</td>
        </tr>"""

    total_debit = 0.0
    total_credit = 0.0
    for row_idx, t in enumerate(period_txns):
        running += t["debit"] - t["credit"]
        total_debit += t["debit"]
        total_credit += t["credit"]
        row_bg = " style=\"background:#F7FAFD;\"" if row_idx % 2 else ""
        status_html = f'<span class="{t["status_class"]}">{esc(t["status_label"])}</span>' if t["status_label"] else "—"
        rows_html += f"""
        <tr{row_bg}>
          <td class="c">{esc(t['date'])}</td>
          <td>{esc(t['desc'])}</td>
          <td class="c">{esc(t['doc'])}</td>
          <td class="c">{esc(t['declno'])}</td>
          <td class="c">{f"{t['debit']:.3f}" if t['debit'] else '—'}</td>
          <td class="c">{f"{t['credit']:.3f}" if t['credit'] else '—'}</td>
          <td class="c">{running:.3f}</td>
          <td class="c">{status_html}</td>
        </tr>"""

    final_balance = running
    final_balance_words_en = english_currency_words(abs(final_balance))

    if date_from or date_to:
        period_txt = f"من {esc(date_from) if date_from else '—'} إلى {esc(date_to) if date_to else '—'}"
    else:
        period_txt = "كل الفترات"

    balance_word = "مستحق على العميل" if final_balance > 0.0005 else ("رصيد لصالح العميل" if final_balance < -0.0005 else "مسدد بالكامل")

    opening_summary_row = ""
    if date_from:
        opening_summary_row = f'<div><span class="k">الرصيد الافتتاحي: </span><span class="v">{opening:.3f} د.ك</span></div>'

    # ترويسة الشركة (معرّفة في config كقيمة واحدة قابلة للتغيير)
    company_ar = html_module.escape(COMPANY_NAME_AR)
    company_en = html_module.escape(COMPANY_NAME_EN)

    return f"""  <div class="page">
  <div class="letterhead">
    <div class="header">
      <div class="brand-ar">{company_ar}</div>
      <div class="logo">{logo_img_html}</div>
      <div class="brand-en">{company_en}</div>

    </div>
    <div class="title">كشف حساب عميل — Customer Statement</div>
  </div>
  <div class="meta">
    <div><span class="k">العميل: </span><span class="v">{esc(customer)}</span></div>
    <div><span class="k">الفترة: </span><span class="v">{period_txt}</span></div>
    {opening_summary_row}
  </div>
  <table>
    <thead><tr>
      <th>التاريخ</th>
      <th>نوع البيان</th>
      <th>رقم المستند</th>
      <th>رقم البيان الجمركي</th>
      <th>مدين</th>
      <th>دائن</th>
      <th>الرصيد</th>
      <th>حالة السداد</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
  <div class="summary">
    <div><span>إجمالي الفواتير (مدين):</span><span>{total_debit:.3f} د.ك</span></div>
    <div><span>إجمالي المدفوعات (دائن):</span><span>{total_credit:.3f} د.ك</span></div>
    <div class="final"><span>الرصيد النهائي ({balance_word}):</span><span>{abs(final_balance):.3f} د.ك</span></div>
    <div class="final-words"><span>Amount in English:</span><span>{html_module.escape(final_balance_words_en)}</span></div>
  </div>
  <div class="footer">
    الكويت، حولي، شارع ابن خلدون، قطعة (2) مجمع محمود حمد الملا، الدور الثالث، مكتب رقم (11)<br>
    Kuwait, Hawally, Ibn Khaldoon St. Mahmoud Hamad Al Mulla Comp., 3rd Floor, Office No.: (11)<br>
    Tel.: +965 60039333 - +965 65550298 - +965 50508064 — E-mail: alestedama@gmail.com
  </div>
  </div>"""


_STATEMENT_PRINT_STYLE = """
  .st-paid{color:#1E8449;font-weight:bold;}
  .st-partial{color:#B5750B;font-weight:bold;}
  .st-unpaid{color:#C0342A;font-weight:bold;}
  body{font-family:'Tahoma','Arial',sans-serif;color:#1C2530;padding:5px 12px;margin:0px;background:#F3F6FA;}
  .page{max-width:900px;margin:10px auto;}
  .letterhead{border:2px solid #0F2B46;border-radius:10px;padding:0px 8px;background:#fff;}
  .header{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:0px}
  .brand-en{flex:1 1 0;text-align:left;direction:ltr;font-weight:bold;color:#1C2530;font-size:15px;line-height:1.15;}
  .brand-ar{flex:1 1 0;text-align:right;direction:rtl;font-weight:bold;color:#1C2530;font-size:17px;line-height:1.15;}
  .logo{flex:0 0 auto;line-height:0;}
  .logo img{display:block;border-radius:8px;height:70px;}
  .title{text-align:center;font-weight:bold;color:#0F2B46;font-size:16px;border-top:2px solid #0F2B46;margin-top:6px;padding-top:8px;}
  .meta{display:flex;flex-wrap:wrap;justify-content:space-between;gap:6px;margin:14px 0;font-size:13px;background:#F5F8FA;border:1px solid #E7EDF3;border-radius:8px;padding:10px;}
  .meta .k{color:#777;} .meta .v{font-weight:bold;}
  table{width:100%;border-collapse:collapse;font-size:11.5px;margin-top:10px;border:1px solid #E7EDF3;border-radius:8px;overflow:hidden;table-layout:fixed;}
  th{background:#0F2B46;color:#fff;padding:8px 4px;text-align:center;}
  td{padding:6px 4px;border-bottom:1px solid #E7EDF3;word-wrap:break-word;}
  td.c{text-align:center;}
  tr.opening-row td{background:#F5F8FA;font-style:italic;color:#555;}
  .total-row td{font-weight:bold;background:#FBF6EA;border-top:2px solid #C99A3D;font-size:14px;}
  .summary{margin-top:14px;font-size:13px;background:#F5F8FA;border:1px solid #E7EDF3;border-radius:8px;padding:10px 14px;display:inline-block;min-width:280px;float:left;}
  .summary div{display:flex;justify-content:space-between;padding:3px 0;}
  .summary .final{font-weight:bold;color:#0F2B46;border-top:1px solid #C99A3D;margin-top:4px;padding-top:6px;font-size:14px;}
  .summary-words{margin-top:8px;font-size:12px;color:#333;display:flex;justify-content:space-between;gap:10px;}
  .summary-words span{display:inline-block;}
  .footer{clear:both;margin-top:18px;text-align:center;font-size:10px;color:#777;border-top:1px solid #ddd;padding-top:4px;line-height:1.6;}
  .print-btn{background:#0F2B46;color:#fff;border:none;border-radius:8px;padding:11px 30px;font-size:14px;font-weight:bold;font-family:inherit;cursor:pointer;box-shadow:0 2px 6px rgba(15,43,70,.25);}
  .print-btn:hover{background:#081726;}
  .doc-wrap{page-break-after:always;}
  .doc-wrap:last-of-type{page-break-after:auto;}
  @media screen { .doc-wrap + .doc-wrap{margin-top:22px;border-top:3px dashed #C7D2DF;padding-top:22px;} }
  @media print { .noprint{display:none;} body{background:#fff;} }
"""


def generate_and_open_statement(customer, date_from, date_to, invoices, payments):
    """ينشئ كشف حساب لعميل واحد (يستخدم دالة الدفعة أدناه بقائمة من عنصر واحد)."""
    generate_and_open_statements_print([
        {"customer": customer, "date_from": date_from, "date_to": date_to,
         "invoices": invoices, "payments": payments}
    ])


def generate_and_open_statements_print(items):
    """يفتح كشف حساب عميل واحد أو عدة عملاء مختارين دفعة واحدة في مستند HTML
    واحد قابل للطباعة، بحيث يكون كل عميل في صفحته الخاصة (فاصل صفحة تلقائي
    بينها عند الطباعة الورقية) مع زر طباعة واحد يطبع كشوف الجميع دفعة واحدة"""
    if not items:
        return
    logo_img_html = _get_logo_img_html()
    pages_html = "\n".join(
        f'<div class="doc-wrap">'
        + _build_statement_page_html(
            it["customer"], it["date_from"], it["date_to"], it["invoices"], it["payments"], logo_img_html
        )
        + "</div>"
        for it in items
    )
    n = len(items)
    btn_text = "🖨 طباعة الكشف" if n == 1 else f"🖨 طباعة كشوف كل العملاء ({n})"

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl"><head><meta charset="UTF-8">
<style>{_STATEMENT_PRINT_STYLE}</style></head>
<body>
{pages_html}
  <div class="noprint" style="text-align:center;margin-top:20px;clear:both;">
    <button class="print-btn" onclick="window.print()">{btn_text}</button>
  </div>
</body></html>"""

    if n == 1:
        fname = f"statement_{_safe_filename_part(items[0]['customer'])}.html"
    else:
        fname = f"statements_batch_{n}_customers.html"
    tmp_path = os.path.join(tempfile.gettempdir(), fname)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file://{tmp_path}")
