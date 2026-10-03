# -*- coding: utf-8 -*-
"""ترويسة الشركة وبنود الفاتورة المستخدمة في الطباعة."""

import base64, html, os
from . import data as td
from .ui_helpers import safe_str


def _brand_en():
    """الاسم الإنجليزي للشركة، مقسوماً على سطرين كما تظهر في الترويسة."""
    name = html.escape(td.COMPANY_NAME_EN)
    if not name:
        return ""
    words = name.split()
    if len(words) > 1:
        half = len(words) // 2
        return "<br>".join([" ".join(words[:half]), " ".join(words[half:])])
    return name


def _brand_ar():
    """الاسم العربي للشركة كما يظهر في الترويسة."""
    return html.escape(td.COMPANY_NAME_AR)


def _contact_line():
    """سطر الهاتف والبريد الإلكتروني كما يظهر أسفل كل مستند مطبوع."""
    parts = []
    if td.COMPANY_PHONE:
        parts.append(f"Tel.: {html.escape(td.COMPANY_PHONE)}")
    if td.COMPANY_EMAIL:
        parts.append(f"E-mail: {html.escape(td.COMPANY_EMAIL)}")
    return " — ".join(parts)


def _deduplicate_invoice_items(items):
    """Merge repeated invoice descriptions and preserve their summed amount."""
    merged = []
    positions = {}
    for raw_item in items or []:
        item = dict(raw_item)
        description = safe_str(item.get("desc")).strip()
        # المقارنة تكون حسب الوصف العربي فقط، حتى لو اختلفت الترجمة الإنجليزية.
        arabic_description = description.split(" — ", 1)[1].strip() if " — " in description else description
        key = arabic_description.casefold()
        if key in positions:
            existing = merged[positions[key]]
            existing["amount"] = round(
                td.safe_float(existing.get("amount")) + td.safe_float(item.get("amount")), 3
            )
        else:
            item["desc"] = description
            item["amount"] = round(td.safe_float(item.get("amount")), 3)
            positions[key] = len(merged)
            merged.append(item)
    return merged

# بنود نموذج الفاتورة الورقي، وتظهر كبنود قابلة للتعديل في شاشة الفاتورة.
INVOICE_FORM_ITEMS = [
    "CUSTOMS CHARGES — رسوم جمارك",
    "MUNICIPAL CLEARANCE CHARGES — أجور تخليص بلدية",
    "INSPECTION CHARGES — أجور كشف",
    "LEGALIZATION DUTIES & CHARGES — أجور ورسوم تصديق",
    "AGENT CHARGES — أجور أرضيات وكيل",
    "HARBOR FLOORING CHARGES — أجور أرضيات ميناء",
    "RELEASE CHARGES — أجور إفراجات",
    "ENVIRONMENTAL RELEASE CHARGES — أجور إفراج بيئة",
    "AGRICULTURAL RELEASE CHARGES — أجور إفراج زراعة",
    "CLEARANCE CHARGES — أجور تخليص",
    "TRANSPORTATION CHARGES — أجور نقل",
    "FORKLIFT CHARGES — رافعة شوكية",
    "CRANE CHARGES — كرين",
    "CONCRETE CRANE CHARGES — كرين خرسانة",
    "CONTAINER WASHING CHARGES — غسيل حاوية",
    "LABOUR CHARGES — أجور عمال",
    "DELAYED TRUCK CHARGES — تأخير شاحنة",
    "OTHER CHARGES — مصاريف أخرى",
]

def _invoice_item_is_disabled(item):
    description = safe_str(item.get("desc", "") if isinstance(item, dict) else item).strip()
    english = description.split(" — ", 1)[0].strip().upper()
    arabic = description.split(" — ", 1)[1].strip() if " — " in description else ""
    return english in {"DELIVERY ORDER", "RECEIPT CHARGES", "BANK COMMISSION", "INSPECTION CHARGES"} or \
        (arabic and arabic in {"إذن تسليم", "أجور استلام", "عمولة بنك", "أجور كشف"})

SERVICE_INVOICE_ITEMS = {
    "رافعة شوكية": "FORKLIFT CHARGES — رافعة شوكية",
    "كرين": "CRANE CHARGES — كرين",
    "كرين خرسانة": "CONCRETE CRANE CHARGES — كرين خرسانة",
    "غسيل حاوية": "CONTAINER WASHING CHARGES — غسيل حاوية",
    "عمال": "LABOUR CHARGES — أجور عمال",
}

LETTERHEAD_ICON_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "icon.png"
)

_letterhead_icon_uri = None

def company_letterhead_html(title, document_number="", document_date=""):
    """Build the invoice/statement letterhead and embed only the company icon."""
    global _letterhead_icon_uri
    if _letterhead_icon_uri is None:
        try:
            with open(LETTERHEAD_ICON_PATH, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode("ascii")
            _letterhead_icon_uri = f"data:image/png;base64,{encoded}"
        except FileNotFoundError:
            _letterhead_icon_uri = ""

    number_html = (
        f"<div class='letterhead-number'>رقم الفاتورة : <b>{html.escape(safe_str(document_number))}</b></div>"
        if document_number else "<div></div>"
    )
    date_html = f"<div class='letterhead-date'>التاريخ : <b>{html.escape(safe_str(document_date))}</b></div>"
    subtitle = "CASH / CREDIT INVOICE" if document_number else "CUSTOMER STATEMENT"
    return f"""<div class='company-letterhead'>
<div class='letterhead-main'>
<div class='letterhead-brand-en'>{_brand_en()}</div>
<div class='letterhead-logo'><img src='{_letterhead_icon_uri}' alt='{html.escape(td.COMPANY_NAME_EN)}'></div>
<div class='letterhead-brand-ar'>{_brand_ar()}</div>
</div>
<div class='letterhead-details'>{number_html}<div class='letterhead-title'>{html.escape(title)}<span>{subtitle}</span></div>{date_html}</div>
</div>"""

LETTERHEAD_PRINT_STYLE = """
.company-letterhead{margin:0 0 12px;background:#fff;border:2px solid #0F2B46;border-radius:12px;overflow:hidden;box-shadow:0 2px 10px rgba(15,43,70,0.06)}
.letterhead-main{height:64px;display:grid;grid-template-columns:1fr 120px 1fr;align-items:center;direction:ltr;padding:0 14px;background:linear-gradient(180deg,#ffffff,#F7FAFC);border-bottom:2px solid #0F2B46}
.letterhead-brand-en{direction:ltr;text-align:left;color:#0F2B46;font-weight:800;font-size:14px;line-height:1.15;letter-spacing:.3px}
.letterhead-brand-ar{direction:rtl;text-align:right;color:#0F2B46;font-weight:800;font-size:15px;line-height:1.15}
.letterhead-logo{height:60px;display:flex;align-items:center;justify-content:center;overflow:hidden}
.letterhead-logo img{display:block;width:80px;height:60px;object-fit:contain}
.letterhead-details{display:grid;grid-template-columns:1fr 1.4fr 1fr;align-items:center;direction:rtl;padding:6px 14px;font-size:11px;font-weight:700;min-height:24px;background:#FAFBFC}
.letterhead-number{text-align:right;white-space:nowrap}.letterhead-number b{color:#9B2C2C;font-size:15px;font-weight:800}
.letterhead-date{text-align:left;white-space:nowrap;direction:ltr}
.letterhead-title{text-align:center;color:#0F2B46;font-weight:800;font-size:11px;letter-spacing:.5px}
.letterhead-title span{display:block;font-size:10px;font-weight:600;color:#6B7A8F;letter-spacing:1px;margin-top:1px}
"""

NO_CUSTOMER = "بدون عميل"
