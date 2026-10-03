# -*- coding: utf-8 -*-
"""بناء وطباعة الفاتورة الورقية."""

import html, json, os, re, tempfile, webbrowser
from . import data as td
from .print_letterhead import INVOICE_FORM_ITEMS, LETTERHEAD_PRINT_STYLE, _brand_ar, _brand_en, _contact_line, _deduplicate_invoice_items, _invoice_item_is_disabled, company_letterhead_html
from .print_theme import apply_a4_print_layout
from .ui_helpers import safe_str


# ==================================================================
# طباعة الفاتورة كصفحة HTML مطابقة لتصميم فواتير الشركة
# ==================================================================
# ==================================================================
# طباعة الفاتورة كصفحة HTML مطابقة لتصميم فواتير الشركة
# ==================================================================
def _generate_invoice_print_original(inv):
        items = json.loads(inv.get("items_json") or "[]")

        def money_parts(value):
            amount = td.safe_float(value)
            dinar = int(amount)
            fils = int(round((amount - dinar) * 1000))
            if fils == 1000:
                dinar, fils = dinar + 1, 0
            return f"{dinar:,}", f"{fils:03d}"

        standard_lines = [
            tuple(safe_str(line).split(" — ", 1))
            for line in INVOICE_FORM_ITEMS
        ]
        line_items = [None] * len(standard_lines)
        line_indexes = {safe_str(line).strip(): index for index, line in enumerate(INVOICE_FORM_ITEMS)}
        for it in items:
            description = safe_str(it.get("desc", "")).strip()
            arabic = description.split(" — ", 1)[1].strip() if " — " in description else description
            english = description.split(" — ", 1)[0].strip() if " — " in description else ""
            index = line_indexes.get(description)
            if index is None:
                index = next((i for i, line in enumerate(INVOICE_FORM_ITEMS)
                              if arabic == line.split(" — ", 1)[1] or english == line.split(" — ", 1)[0]), None)
            if index is not None:
                line_items[index] = it
            # استخدم البنود الموجودة في الفاتورة فقط، ولا تعرض قائمة الرسوم الجاهزة.
            standard = [(safe_str(item.get("desc")), safe_str(item.get("desc"))) for item in items]
            rows = []
            for index, (en_desc, ar_desc) in enumerate(standard_lines):
                        it = line_items[index]
                        dinar, fils = money_parts(it.get("amount")) if it else ("", "")
                        rows.append(
                            f"<tr><td class='seq'>{index + 1}</td><td><div class='svc-cell'>"
                            f"<span class='svc-en'>{en_desc}</span><span class='svc-ar'>{ar_desc}</span>"
                            f"</div></td><td class='money'>{dinar or '—'}</td>"
                            f"<td class='money'>{fils if fils and fils != '000' else ('—' if it else '—')}</td></tr>"
                        )
            rows_html = "".join(rows)
            total_dinar, total_fils = money_parts(inv.get("total"))
            logo_svg = """<svg class="logo" viewBox="0 0 150 100" aria-label="logo">
            <path d="M8 70h134M28 64c20-8 42-7 62 1 18 7 31 5 48-2" fill="none" stroke="#1b314c" stroke-width="7"/>
            <path d="M39 61 65 22l18 39M65 22v42M65 35l39-12-17 25 25 8" fill="none" stroke="#1b314c" stroke-width="5"/>
            <path d="M28 72c27 16 65 16 96 0" fill="none" stroke="#1b314c" stroke-width="6"/>
            </svg>"""
            html_content = f"""<!doctype html>
            <html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>فاتورة رقم {html.escape(safe_str(inv.get('invoice_no')))}</title>
            <style>
            @page{{size:A4;margin:7mm}}*{{box-sizing:border-box}}body{{font-family:Tahoma,Arial,sans-serif;color:#1C2530;padding:5px 12px;margin:0;background:#F3F6FA}}.sheet{{max-width:900px;margin:10px auto;background:#fff;min-height:283mm}}.header{{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:0;border:2px solid #0F2B46;border-radius:10px;padding:0 8px}}.brand-en{{flex:1;text-align:left;direction:ltr;font-weight:bold;color:#1C2530;font-size:15px;line-height:1.15}}.brand-en small{{display:block;font-size:11px}}.brand-ar{{flex:1;text-align:right;direction:rtl;font-weight:bold;color:#1C2530;font-size:17px;line-height:1.15}}.brand-ar small{{display:block;font-size:11px}}.logo{{flex:0 0 auto;line-height:0;padding:0 8px;width:110px;height:70px}}.contacts{{font-size:8px;margin-top:3px;white-space:nowrap}}.title-row{{display:flex;justify-content:space-between;align-items:center;border:2px solid #0F2B46;border-top:0;border-radius:0 0 10px 10px;padding:4px 8px;font-size:10px;font-weight:bold}}.number,.date{{direction:rtl;white-space:nowrap}}.number b{{color:#93241F;font-size:15px}}.invoice-title{{text-align:center;font-weight:bold;color:#0F2B46;font-size:10px}}.invoice-title span{{display:block;font-size:10px;font-weight:normal;color:#666;letter-spacing:1px;margin-top:2px}}.details{{direction:rtl;margin:8px 0 5px;font-size:12px;background:#F5F8FA;border:1px solid #E7EDF3;border-radius:8px;padding:8px 10px}}.customer-line{{padding-bottom:6px;border-bottom:1px dotted #9BA8B5}}.meta-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:6px 18px;font-size:12px;padding-top:7px}}.meta-grid .k{{color:#777}}table{{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px;border:1px solid #E7EDF3}}th{{background:#0F2B46;color:#fff;padding:7px 8px;text-align:center}}th small{{display:block;font-weight:normal;font-size:9.5px;color:#C99A3D;margin-top:1px}}td{{padding:6px 8px;border-bottom:1px solid #E7EDF3;height:27px}}.seq{{width:26px;text-align:center}}.svc-cell{{display:flex;justify-content:space-between;align-items:center;gap:10px}}.svc-en{{direction:ltr;text-align:left;color:#333;font-size:11px;flex:1}}.svc-ar{{direction:rtl;text-align:right;font-size:12.5px;flex:1}}.money{{width:60px;text-align:center}}.total td{{font-weight:bold;background:#FBF6EA;border-top:2px solid #C99A3D}}.total-label{{text-align:left}}.notes{{margin-top:10px;font-size:11px}}.signatures{{display:flex;justify-content:space-between;margin:5px 0;font-size:13px;font-weight:bold}}.signature-line{{margin-top:20px;border-top:1px solid #999;padding-top:6px;width:150px;text-align:center}}.footer{{margin-top:18px;text-align:center;font-size:10px;color:#777;border-top:1px solid #ddd;padding-top:4px;line-height:1.6}}.noprint{{text-align:center;margin-top:12px}}button{{background:#0F2B46;color:#fff;border:0;border-radius:8px;padding:11px 30px;font-size:14px;font-weight:bold;cursor:pointer}}@media print{{.noprint{{display:none}}body{{background:#fff}}.sheet{{min-height:0}}}}
            </style></head><body><div class="sheet">
            <div class="header"><div class="brand-en">{_brand_en()}<div class="contacts">Tel.: {html.escape(td.COMPANY_PHONE)}</div></div>{logo_svg}<div class="brand-ar">{_brand_ar()}<div class="contacts">هاتف: {html.escape(td.COMPANY_PHONE)}</div></div></div>
            <div class="title-row"><div class="number">رقم الفاتورة : <b>{html.escape(safe_str(inv.get('invoice_no')))}</b></div><div class="invoice-title">فاتورة نقداً / بالحساب<span>CASH / CREDIT INVOICE</span></div><div class="date">التاريخ : <b>{html.escape(safe_str(inv.get('date')))}</b></div></div>
            <div class="details"><div class="customer-line"><b>السادة:</b> {html.escape(safe_str(inv.get('customer')))}</div><div class="meta-grid"><div><span class="k">رقم البيان الجمركي:</span> <b>{html.escape(safe_str(inv.get('declaration_no')))}</b></div><div><span class="k">تاريخ البيان الجمركي:</span> <b>{html.escape(safe_str(inv.get('date')))}</b></div><div><span class="k">رقم بوليصة الشحن:</span> <b>{html.escape(safe_str(inv.get('awb_no')))}</b></div><div><span class="k">عدد الحاويات:</span> <b>{html.escape(safe_str(inv.get('container_count')))}</b></div><div><span class="k">نوع البضاعة:</span> <b>{html.escape(safe_str(inv.get('goods_type')))}</b></div><div><span class="k">بلد المنشأ:</span> <b>{html.escape(safe_str(inv.get('origin')))}</b></div></div></div>
            <table><thead><tr><th style="width:26px;">م</th><th>نوع الخدمة<small>Kind of Service</small></th><th style="width:60px;">دينار</th><th style="width:60px;">فلس</th></tr></thead><tbody>{rows_html}</tbody><tfoot><tr class="total"><td colspan="2" class="total-label">المجموع — Total</td><td class="money">{total_dinar}</td><td class="money">{total_fils if total_fils != '000' else '—'}</td></tr></tfoot></table>
            <div class="notes"><b>ملاحظات:</b> {html.escape(safe_str(inv.get('notes')))}</div><div class="signatures"><div>المحاسب<div class="signature-line"></div></div><div>المستلم<div class="signature-line"></div></div></div>
            <div class="footer">{td.COMPANY_ADDRESS_AR}{td.COMPANY_ADDRESS_EN}{_contact_line()}</div></div><div class="noprint"><button onclick="window.print()">طباعة الفاتورة</button></div></body></html>"""
            tmp_path = os.path.join(tempfile.gettempdir(), f"transport_invoice_{inv['invoice_no']}.html")
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(apply_a4_print_layout(html_content))
            webbrowser.open(f"file://{tmp_path}")

# قالب الفاتورة المرجعي (مستوحى من تصميم فواتير الشركة)
_REFERENCE_INVOICE_STYLE = """
    @page{size:A4;margin:6mm}
    *{box-sizing:border-box}
    body{font-family:'Tahoma','Arial',sans-serif;color:#1C2530;padding:0;margin:0;background:#E5E9F0}
    .page{max-width:900px;margin:12px auto;background:#fff;border-radius:12px;padding:18px 22px;box-shadow:0 4px 18px rgba(15,43,70,0.08)}
    .letterhead{border:2px solid #0F2B46;border-radius:12px;overflow:hidden;background:#fff;margin-bottom:14px}
    .header{display:grid;grid-template-columns:1fr 110px 1fr;align-items:center;direction:ltr;padding:10px 14px;background:linear-gradient(180deg,#ffffff,#F7FAFC);border-bottom:2px solid #0F2B46;gap:10px}
    .brand-en{direction:ltr;text-align:left;color:#0F2B46;font-weight:800;font-size:15px;line-height:1.15;letter-spacing:.3px}
    .brand-ar{direction:rtl;text-align:right;color:#0F2B46;font-weight:800;font-size:16px;line-height:1.15}
    .logo{display:flex;align-items:center;justify-content:center}
    .logo svg{display:block;height:62px;width:100px;object-fit:contain}
    .contacts{font-size:9px;margin-top:4px;color:#5A6B7C;white-space:nowrap}
    .subheader{display:flex;justify-content:space-between;align-items:center;border-top:2px solid #0F2B46;padding:8px 14px;font-size:11px;font-weight:700;background:#FAFBFC;direction:rtl;gap:10px}
    .invno{color:#9B2C2C;font-weight:800;font-size:16px;white-space:nowrap}
    .title{text-align:center;color:#0F2B46;font-weight:800;font-size:12px;letter-spacing:.5px}
    .title-en{display:block;font-size:10px;font-weight:600;color:#6B7A8F;letter-spacing:1px;margin-top:2px}
    .date{text-align:left;white-space:nowrap;direction:ltr}
    .rtl-block{direction:rtl}
    .customer{font-size:13px;margin:10px 0 6px;padding:8px 10px;background:#F5F8FA;border-radius:8px;border:1px solid #E7EDF3}
    .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px 16px;font-size:12px;padding:10px 12px;background:#F5F8FA;border-radius:10px;border:1px solid #E7EDF3;margin:8px 0 10px}
    .grid .k{color:#6B7A8F;font-size:11px}
    .grid .v{font-weight:700;color:#1C2530}
    table{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px;border:1px solid #D8E0E9;border-radius:10px;overflow:hidden}
    th{background:#0F2B46;color:#fff;padding:9px 10px;text-align:center;font-weight:700;font-size:11px;letter-spacing:.3px}
    th .th-en{display:block;font-weight:600;font-size:9px;color:#C99A3D;margin-top:1px;letter-spacing:.5px}
    td{padding:8px 10px;border-bottom:1px solid #E7EDF3;color:#1C2530}
    td.c{text-align:center}
    tr:nth-child(even){background:#F7FAFC}
    .seq{width:32px;text-align:center;font-weight:700;color:#5A6B7C}
    .money{text-align:center;font-weight:700;font-variant-numeric:tabular-nums;color:#0F2B46}
    .svc-cell{display:flex;justify-content:space-between;align-items:center;gap:10px;text-align:right}
    .svc-en{direction:ltr;text-align:left;font-size:10.5px;flex:1;color:#5A6B7C}
    .svc-ar{direction:rtl;text-align:right;font-size:12.5px;flex:1;font-weight:600;color:#1C2530}
    .total-row td{font-weight:800;background:#FBF6EA;border-top:2px solid #C99A3D;color:#0F2B46;font-size:13px}
    .total-label{color:#0F2B46;font-weight:800;letter-spacing:.3px}
    .total-words{font-size:11px;color:#4A5568;margin-top:4px}
    .sign{display:flex;justify-content:space-between;margin-top:18px;font-size:13px;font-weight:700;color:#0F2B46;gap:40px}
    .sign div{border-top:2px solid #A0AEC0;padding-top:8px;width:160px;text-align:center;color:#4A5568;font-weight:600}
    .notes{margin-top:10px;padding:8px 10px;background:#FFFBEB;border-radius:8px;border:1px solid #FDE68A;font-size:11px;color:#6B5A1F}
    .footer{margin-top:22px;text-align:center;font-size:10px;color:#5A6B7C;border-top:1px solid #D8E0E9;padding-top:8px;line-height:1.7;background:#FAFBFC;border-radius:10px;padding:10px}
    .noprint{text-align:center;margin-top:22px}
    .print-btn{background:#0F2B46;color:#fff;border:0;border-radius:10px;padding:12px 34px;font-weight:700;font-size:14px;cursor:pointer;box-shadow:0 2px 0 rgba(15,43,70,0.25)}
    .print-btn:hover{background:#163B5E}
    @media print{.noprint{display:none}body{background:#fff}.page{box-shadow:none;margin:0;border-radius:0;padding:0}}
    """

def _build_reference_invoice_page(inv):
    items = json.loads(inv.get("items_json") or "[]")
    standard = [
    ("DELIVERY ORDER SHIPPING", "إذن تسليم بوليصة الشحن"),
    ("REVIEWING CHARGE - DELIVERY ORDER", "أجور استلام إذن التسليم"),
    ("FREIGHT CHARGE SHIPPING LOGISTIC", "أجور الشحن للخدمات اللوجستية"),
    ("FREIGHT FORWARDWE FLOORING - FEES", "أرضيات الوكيل أو محطة الحاويات"),
    ("LEGALIZATION FEES INVOICE", "رسوم تصديقات الفاتورة والمنشأ"),
    ("LEGALIZATION CHARGES", "أجور تصديقات الفواتير"),
    ("GLOBAL FEES", "رسوم جلوبال"), ("CUSTOMS DUTY", "الرسوم الجمركية (الجمارك)"),
    ("BANK COMMISSION", "عمولة البنك للرسوم الجمركية"), ("EXEMPTION FROM LANDUSTRY", "أجور الإعفاء الجمركي"),
    ("APPROVAL OF LANDUSTRY", "رسوم إفراج الصناعة أو الهيئة"), ("APPROVAL OF INDUSTRIAL - FEES", "رسوم خدمات الإفراج"),
    ("PORT SERVICE - FEES", "رسوم خدمات الميناء"), ("CUSTOMS CHARGE", "أجور كشف جمركي"),
    ("TRANSPORTATION CHARGE", "أجور خدمات النقل"), ("SERVICE - FEES", "أجور خدمات العمال"),
    ("FORKLIFT AND CRANE - FEES", "أجور الرافعة والكرين"), ("FINE FOR DRUMS", "غرامة طبالي"),
    ("CUSTOMS - FEES", "أجور البيان الجمركي"), ("CUSTOMS SERVICE - FEES", "رسوم خدمات جمركية سحب اسكان"),
    ("CLEARANCE FEES CHARGE", "أجور التخليص والإفراج"), ("PRINTING AND COPYING - FEES", "طباعة وتصوير المستندات"),
    ("RECEIVING & FOLLOW UP SERVICE", "أجور الاستلام والمتابعة"), ("OTHER SERVICE CHARGES", "خدمات أخرى"),
    ]
    # اعرض البنود المحفوظة فعلياً في الفاتورة فقط، ولا تستخدم قائمة الرسوم
    # القياسية القديمة التي كانت تظهر حتى عندما لا تكون موجودة في الفاتورة.
    standard = [(safe_str(item.get("desc")), safe_str(item.get("desc"))) for item in items]
    values = [None] * len(standard)
    for idx, item in enumerate(items):
        if idx < len(values):
            values[idx] = item

    rows = []
    for idx, (en_label, ar_label) in enumerate(standard):
        item = values[idx]
        amount = td.safe_float(item.get("amount")) if item else 0
        dinar = int(amount)
        fils = int(round((amount - dinar) * 1000))
        rows.append(f"<tr><td class='c'>{idx + 1}</td><td><div class='svc-cell'><span class='svc-en'>{html.escape(en_label)}</span><span class='svc-ar'>{html.escape(ar_label)}</span></div></td><td class='c'>{dinar if item else '—'}</td><td class='c'>{fils if item and fils else '—'}</td></tr>")
    total = td.safe_float(inv.get("total"))
    total_d, total_f = int(total), int(round((total - int(total)) * 1000))
    logo = """<svg viewBox='0 0 150 100'><path d='M8 70h134M28 64c20-8 42-7 62 1 18 7 31 5 48-2' fill='none' stroke='#1b314c' stroke-width='7'/><path d='M39 61 65 22l18 39M65 22v42M65 35l39-12-17 25 25 8' fill='none' stroke='#1b314c' stroke-width='5'/><path d='M28 72c27 16 65 16 96 0' fill='none' stroke='#1b314c' stroke-width='6'/></svg>"""
    return f"""<div class='page'><div class='letterhead'><div class='header'><div class='brand-en'>{_brand_en()}</div><div class='logo'>{logo}</div><div class='brand-ar'>{_brand_ar()}</div></div><div class='subheader'><div>رقم الفاتورة : <span class='invno'>{html.escape(safe_str(inv.get('invoice_no')))}</span></div><div class='title'>فاتورة نقداً / بالحساب<span class='title-en'>CASH / CREDIT INVOICE</span></div><div>التاريخ : <b>{html.escape(safe_str(inv.get('date')))}</b></div></div></div><div class='rtl-block'><div class='customer'>السادة: <b>{html.escape(safe_str(inv.get('customer')))}</b></div><div class='grid'><div><span class='k'>رقم البيان الجمركي:</span> <span class='v'>{html.escape(safe_str(inv.get('declaration_no')) or '—')}</span></div><div><span class='k'>تاريخ البيان الجمركي:</span> <span class='v'>{html.escape(safe_str(inv.get('date')))}</b></div><div><span class='k'>المنفذ:</span> <span class='v'>—</span></div><div><span class='k'>عدد الحاويات:</span> <span class='v'>—</span></div><div><span class='k'>نوع البضاعة:</span> <span class='v'>—</span></div><div><span class='k'>بلد المنشأ:</span> <span class='v'>—</span></div></div></div><table><thead><tr><th style='width:26px'>م</th><th>نوع الخدمة<span class='th-en'>Kind of Service</span></th><th style='width:60px'>دينار</th><th style='width:60px'>فلس</th></tr></thead><tbody>{''.join(rows)}</tbody><tfoot><tr class='total-row'><td colspan='2'>المجموع — Total</td><td class='c'>{total_d}</td><td class='c'>{total_f or '—'}</td></tr></tfoot></table><div class='sign'><div>المحاسب</div><div>المستلم</div></div><div class='footer'>{td.COMPANY_ADDRESS_AR}{td.COMPANY_ADDRESS_EN}{_contact_line()}</div></div>"""

def _english_number_words(number):
    number = int(number)
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    teens = [
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen",
        "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen",
    ]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    if number == 0:
        return "Zero"
    if number < 10:
        return ones[number]
    if number < 20:
        return teens[number - 10]
    if number < 100:
        unit = number % 10
        ten = number // 10
        return tens[ten] if unit == 0 else f"{tens[ten]} {ones[unit]}"
    if number < 1000:
        rest = number % 100
        head = f"{ones[number // 100]} Hundred"
        return head if rest == 0 else f"{head} {_english_number_words(rest)}"
    if number < 1000000:
        thousands = number // 1000
        rest = number % 1000
        head = f"{_english_number_words(thousands)} Thousand"
        return head if rest == 0 else f"{head} {_english_number_words(rest)}"
    millions = number // 1000000
    rest = number % 1000000
    head = f"{_english_number_words(millions)} Million"
    return head if rest == 0 else f"{head} {_english_number_words(rest)}"

def _invoice_amount_in_english_words(amount):
    amount = round(td.safe_float(amount), 3)
    dinar = int(amount)
    fils = int(round((amount - dinar) * 1000))
    if fils == 1000:
        dinar += 1
        fils = 0
    dinar_unit = "Kuwaiti Dinar" if dinar == 1 else "Kuwaiti Dinars"
    parts = [f"{_english_number_words(dinar)} {dinar_unit}"]
    if fils:
        fils_unit = "Fil" if fils == 1 else "Fils"
        parts.append(f"{_english_number_words(fils)} {fils_unit}")
    return " and ".join(parts) + " Only"

def _invoice_container_count(inv):
    """Calculate containers as the number of unique trips in the invoice."""
    invoice_no = safe_str(inv.get("invoice_no")).strip()
    trip_ids = {safe_str(trip.get("id")).strip() for trip in td.load_trips()
            if safe_str(trip.get("invoice_no")).strip() == invoice_no
            and safe_str(trip.get("id")).strip()}
    return len(trip_ids) or td.safe_int(inv.get("container_count"))

def _invoice_money_parts(value):
    amount = round(td.safe_float(value), 3)
    dinar = int(amount)
    fils = int(round((amount - dinar) * 1000))
    if fils == 1000:
        dinar += 1
        fils = 0
    return dinar, fils

def _invoice_description_pair(description):
    """Return (English, Arabic) for one invoice item."""
    text = safe_str(description).strip()
    if " — " in text:
        english, arabic = text.split(" — ", 1)
        return english.strip(), arabic.strip()

    standard_translations = {
        safe_str(item).split(" — ", 1)[1]: safe_str(item).split(" — ", 1)[0]
        for item in INVOICE_FORM_ITEMS if " — " in safe_str(item)
    }
    if text in standard_translations:
        return standard_translations[text], text
    if text.startswith("رحلة"):
        return "Transportation Trip", text
    if text.startswith("عمال"):
        return "Labour Service", text
    if text.startswith("رافعة"):
        return "Forklift Service", text
    if text.startswith("كرين"):
        return "Crane Service", text
    if text.startswith("غسيل"):
        return "Container Washing Service", text
    return "Other Charges", text

def _build_invoice_items_table(inv):
    items = json.loads(inv.get("items_json") or "[]")
    items = _deduplicate_invoice_items(
        [item for item in items if not _invoice_item_is_disabled(item)])
    rows = []
    for idx, item in enumerate(items):
        en_label, ar_label = _invoice_description_pair(item.get("desc"))
        dinar, fils = _invoice_money_parts(item.get("amount")) if item else ("", "")
        rows.append(
            "<tr>"
            f"<td class='c seq-col'>{idx + 1}</td>"
            f"<td class='item-en'>{html.escape(en_label)}</td>"
            f"<td class='item-ar'>{html.escape(ar_label)}</td>"
            f"<td class='c money-col'>{dinar if item else '—'}</td>"
            f"<td class='c money-col'>{f'{fils:03d}' if item and fils else '—'}</td>"
            "</tr>"
        )
    total = td.safe_float(inv.get("total"))
    total_d, total_f = _invoice_money_parts(total)
    total_fils_html = f"{total_f:03d}" if total_f else "—"
    words = html.escape(_invoice_amount_in_english_words(total))
    return (
        "<table class='invoice-items'><thead><tr>"
        "<th class='seq-col'>م</th>"
        "<th>Description</th>"
        "<th>التفاصيل</th>"
        "<th class='money-col'>دينار</th>"
        "<th class='money-col'>فلس</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody>"
        "<tfoot>"
        f"<tr class='total-row'><td colspan='3'><span class='total-label'>Total</span> <span class='total-words'>{words}</span></td><td class='c'>{total_d}</td><td class='c'>{total_fils_html}</td></tr>"
        "</tfoot></table>"
    )

def generate_and_open_invoice_print(inv):
    """فتح نسخة الطباعة بتصميم الفاتورة المرجعي."""
    page_html = _build_reference_invoice_page(inv)
    page_html = page_html.replace("</b></div><div><span class='k'>المنفذ:", "</span></div><div><span class='k'>المنفذ:")
    container_count = _invoice_container_count(inv)
    page_html = page_html.replace(
    "المنفذ:</span> <span class='v'>—</span>",
    f"رقم بوليصة الشحن:</span> <span class='v'>{html.escape(safe_str(inv.get('awb_no')) or '—')}</span>",
    )
    page_html = page_html.replace(
    "عدد الحاويات:</span> <span class='v'>—</span>",
    f"عدد الحاويات:</span> <span class='v'>{html.escape(str(container_count) if container_count else '—')}</span>",
    )
    page_html = re.sub(
    r"<table>.*?</table>",
    _build_invoice_items_table(inv),
    page_html,
    count=1,
    flags=re.S,
    )
    letterhead = company_letterhead_html(
    "فاتورة نقداً / بالحساب", inv.get("invoice_no"), inv.get("date")
    )
    page_html = re.sub(
    r"<div class='letterhead'>.*?</div><div class='rtl-block'>",
    letterhead + "<div class='rtl-block'>",
    page_html,
    count=1,
    flags=re.S,
    )
    invoice_table_style = """
    .invoice-items{direction:ltr;border:1px solid #D8E0E9;border-radius:10px;overflow:hidden}
    .invoice-items th,.invoice-items td{text-align:center;padding:9px 10px}
    .invoice-items .seq-col{width:32px;font-weight:700;color:#5A6B7C}
    .invoice-items .money-col{width:64px;font-weight:700;color:#0F2B46;font-variant-numeric:tabular-nums}
    .invoice-items .item-en{direction:ltr;text-align:left;font-size:10.5px;flex:1;color:#5A6B7C}
    .invoice-items .item-ar{direction:rtl;text-align:right;font-size:12.5px;flex:1;font-weight:600;color:#1C2530}
    .invoice-items .total-row td{font-weight:800;background:#FBF6EA;border-top:2px solid #C99A3D;color:#0F2B46;font-size:13px;padding:10px}
    .invoice-items .total-row td:first-child{text-align:left;direction:ltr}
    .invoice-items .total-label{color:#0F2B46;font-weight:800;letter-spacing:.3px}
    .invoice-items .total-words{font-size:11px;color:#4A5568;margin-top:4px}
    """
    html_content = (
    "<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'>"
    f"<style>{_REFERENCE_INVOICE_STYLE}{LETTERHEAD_PRINT_STYLE}{invoice_table_style}</style>"
    f"</head><body>{page_html}<div class='noprint'>"
    "<button class='print-btn' onclick='window.print()'>طباعة الفاتورة</button>"
    "</div></body></html>"
    )
    tmp_path = os.path.join(tempfile.gettempdir(), f"transport_invoice_{inv['invoice_no']}.html")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(apply_a4_print_layout(html_content))
    webbrowser.open(f"file://{tmp_path}")
