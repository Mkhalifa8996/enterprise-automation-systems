# -*- coding: utf-8 -*-
"""طباعة الفاتورة كصفحة HTML مطابقة لتصميم فواتير المطعم."""

import os
import tempfile
import webbrowser
import restaurant_data as rd
from ui.theme import (
    safe_str,
)


# ==================================================================
# طباعة الفاتورة كصفحة HTML مطابقة لتصميم فواتير المطعم
# ==================================================================
def generate_and_open_invoice_print(inv):
    items = rd.invoice_items(inv)
    rows_html = "".join(
        f"""<tr><td>{it.get('desc', '')}</td><td class="c">{rd.safe_float(it.get('amount')):.3f}</td></tr>"""
        for it in items
    )
    # سطور التحصيل: تظهر فقط إذا سُجّلت دفعات على الفاتورة
    paid = rd.safe_float(inv.get('paid_amount'))
    if paid > 0:
        total_f = rd.safe_float(inv.get('total'))
        balance = max(total_f - paid, 0.0)
        status = safe_str(inv.get('status', ''))
        paid_block = f"""
  <table style="margin-top:6px;">
    <tr><td style="width:60%;"><b>المدفوع — Paid</b> ({status})</td><td class="c">{paid:.3f}</td></tr>
    <tr><td><b>المتبقي — Balance Due</b></td><td class="c"><b>{balance:.3f}</b></td></tr>
  </table>"""
    else:
        paid_block = ""
    logo_svg = """
    <svg viewBox="0 0 120 120" style="width:70px;height:70px;">
      <circle cx="60" cy="60" r="57" fill="#FFFFFF" stroke="#6B2B1F" stroke-width="3"/>
      <circle cx="60" cy="60" r="50" fill="none" stroke="#D9A441" stroke-width="1.3"/>
      <ellipse cx="60" cy="70" rx="34" ry="10" fill="#6B2B1F"/>
      <circle cx="60" cy="46" r="20" fill="none" stroke="#8C4632" stroke-width="3"/>
      <path d="M60 26 L60 46" stroke="#8C4632" stroke-width="3"/>
      <text x="60" y="98" font-size="9" font-weight="700" fill="#6B2B1F" text-anchor="middle">CATERING</text>
      <text x="60" y="112" font-size="7" font-weight="600" fill="#8C4632" text-anchor="middle" letter-spacing="1">& EVENTS</text>
    </svg>
    """
    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl"><head><meta charset="UTF-8">
<title>فاتورة رقم {inv['invoice_no']}</title>
<style>
  body{{font-family:'Tahoma','Arial',sans-serif;color:#2A1E19;padding:24px;}}
  .brandrow{{display:flex;justify-content:space-between;align-items:flex-start;padding-bottom:8px;}}
  .brand-en{{font-size:12px;font-weight:bold;text-align:left;}}
  .brand-ar{{font-size:15px;font-weight:bold;color:#6B2B1F;text-align:right;}}
  .metarow{{display:flex;justify-content:space-between;align-items:center;border-top:2px solid #6B2B1F;border-bottom:2px solid #6B2B1F;padding:8px 4px;margin-top:6px;}}
  .invno{{color:#9C2B20;font-weight:bold;font-size:20px;border:1.5px solid #6B2B1F;border-radius:4px;padding:2px 14px;}}
  .title-ar{{font-weight:bold;color:#6B2B1F;font-size:13px;text-align:center;}}
  table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:14px;}}
  th{{background:#6B2B1F;color:#fff;padding:8px;text-align:right;}}
  td{{padding:7px 8px;border-bottom:1px solid #ddd;}}
  td.c{{text-align:center;width:110px;}}
  .total-row td{{font-weight:bold;background:#FBF1DE;border-top:2px solid #D9A441;font-size:14px;}}
  .sign{{display:flex;justify-content:space-between;margin-top:60px;font-size:13px;font-weight:bold;}}
  .sign div{{border-top:1px solid #999;padding-top:6px;width:150px;text-align:center;}}
  .footer{{margin-top:30px;text-align:center;font-size:10px;color:#777;border-top:1px solid #ddd;padding-top:8px;}}
  @media print {{ .noprint{{display:none;}} }}
</style></head>
<body>
  <div class="brandrow">
    <div class="brand-en">{rd.COMPANY_NAME_EN}</div>
    {logo_svg}
    <div class="brand-ar">{rd.COMPANY_NAME_AR}</div>
  </div>
  <div class="metarow">
    <div class="invno">{inv['invoice_no']}</div>
    <div class="title-ar">فاتورة وجبات وضيافة<br><span style="font-size:9.5px;font-weight:normal;color:#666;">CATERING SERVICES INVOICE</span></div>
    <div>التاريخ: <b>{inv.get('date','')}</b></div>
  </div>
  <div style="margin-top:10px;font-size:13px;">السادة: <b>{inv.get('customer','')}</b></div>
  <table>
    <thead><tr><th>البيان</th><th style="width:110px;">المبلغ (د.ك)</th></tr></thead>
    <tbody>{rows_html}</tbody>
    <tfoot><tr class="total-row"><td>الإجمالي — Total</td><td class="c">{rd.safe_float(inv.get('total')):.3f}</td></tr></tfoot>
  </table>
  {paid_block}
  {'<div style="margin-top:10px;font-size:11px;"><b>ملاحظات:</b> ' + safe_str(inv.get('notes','')) + '</div>' if inv.get('notes') else ''}
  <div class="sign"><div>المحاسب</div><div>المستلم</div></div>
  <div class="footer">
    {rd.COMPANY_ADDRESS_AR} — {rd.COMPANY_ADDRESS_EN}<br>
    Tel.: {rd.COMPANY_PHONE} — E-mail: {rd.COMPANY_EMAIL}
  </div>
  <div class="noprint" style="text-align:center;margin-top:20px;">
    <button onclick="window.print()" style="padding:10px 24px;font-size:14px;">طباعة الفاتورة</button>
  </div>
</body></html>"""
    tmp_path = os.path.join(tempfile.gettempdir(), f"restaurant_invoice_{inv['invoice_no']}.html")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file://{tmp_path}")
