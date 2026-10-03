# -*- coding: utf-8 -*-
"""هوية الطباعة الموحّدة وثوابت الألوان وقواعد صفحات A4."""

import html, os, tempfile, webbrowser
from . import data as td


# تذييل الطباعة يُبنى من بيانات الشركة المُعدّة (data.paths)، فلا تُثبَّت هنا
# عنوان أو هاتف أو بريد خاص. تُملأ عبر متغيّرات البيئة:
#   TRANSPORT_COMPANY_ADDRESS_AR / _EN, TRANSPORT_COMPANY_PHONE, _EMAIL
def _footer_html():
    parts = []
    if td.COMPANY_ADDRESS_AR:
        parts.append(html.escape(td.COMPANY_ADDRESS_AR))
    if td.COMPANY_ADDRESS_EN:
        parts.append(html.escape(td.COMPANY_ADDRESS_EN))
    contact = []
    if td.COMPANY_PHONE:
        contact.append(f"Tel.: {html.escape(td.COMPANY_PHONE)}")
    if td.COMPANY_EMAIL:
        contact.append(f"E-mail: {html.escape(td.COMPANY_EMAIL)}")
    if contact:
        parts.append(" — ".join(contact))
    return "<br>".join(parts)


PRINT_FOOTER_HTML = _footer_html()

def apply_print_footer(html_content):
    old_footer = (
        f"{html.escape(td.COMPANY_ADDRESS_AR)} — {html.escape(td.COMPANY_ADDRESS_EN)}<br>"
        f"Tel.: {html.escape(td.COMPANY_PHONE)} — E-mail: {html.escape(td.COMPANY_EMAIL)}"
    )
    if not PRINT_FOOTER_HTML:
        return html_content
    return html_content.replace(old_footer, PRINT_FOOTER_HTML)

# ==========================================================
# هوية الطباعة الموحّدة
# كان لكل تقرير ألوانه: بعضهم كحلي #1A2B4A وذهبي #E8A838 (لون شاشات
# البرنامج)، وبعضهم كحلي #0F2B46 وذهبي #C99A3D (لون الفواتير). فبدا كشفان
# من برنامج واحد على أنهما من جهتين مختلفتين. نثبّت الألوان هنا مرة واحدة.
# ==========================================================
PRINT_NAVY = "#0F2B46"        # كحلي: العناوين وترويسة الجداول

PRINT_NAVY_DARK = "#163B5E"   # كحلي داكن: عند المرور على زر الطباعة

PRINT_GOLD = "#C99A3D"        # ذهبي: الخطوط الفاصلة وصفوف الإجمالي

PRINT_INK = "#1C2530"         # نص أساسي

PRINT_MUTED = "#5A6B7C"       # نص ثانوي وتعليقات

PRINT_LINE = "#D8E0E9"        # حدود الجداول

PRINT_ROW_ALT = "#F7FAFC"     # تظليل الصفوف الفردية

PRINT_TOTAL_BG = "#FBF6EA"    # خلفية صف الإجمالي

# قواعد أساس توحّد شكل كل تقرير لا يضع ألوانه بنفسه: خط واحد، عناوين
# موحّدة بخط ذهبي، وترويسة جدول كحلية وصفوف متبادلة وتذييل موحّد.
PRINT_THEME_STYLE = f"""
<style id="unified-print-theme">
:root {{
    --print-navy: {PRINT_NAVY}; --print-gold: {PRINT_GOLD};
    --print-ink: {PRINT_INK}; --print-muted: {PRINT_MUTED};
    --print-line: {PRINT_LINE}; --print-alt: {PRINT_ROW_ALT};
    --print-total: {PRINT_TOTAL_BG};
}}
body {{ font-family: Tahoma, "Segoe UI", Arial, sans-serif; color: {PRINT_INK}; }}
h1 {{ color: {PRINT_NAVY}; font-size: 20px; margin: 0 0 4px; }}
h2 {{ color: {PRINT_NAVY}; font-size: 15px; margin: 18px 0 6px;
      border-bottom: 2px solid {PRINT_GOLD}; padding-bottom: 3px; }}
h3 {{ color: {PRINT_NAVY}; font-size: 13px; margin: 14px 0 5px;
      border-bottom: 1px solid {PRINT_LINE}; padding-bottom: 2px; }}
p, .meta, .intro {{ color: {PRINT_MUTED}; }}
table {{ border-collapse: collapse; width: 100%; font-size: 11px; }}
th {{ background: {PRINT_NAVY}; color: #fff; font-weight: 700; }}
th, td {{ border: 1px solid {PRINT_LINE}; padding: 5px 7px; }}
tr:nth-child(even) {{ background: {PRINT_ROW_ALT}; }}
tfoot td, .total-row td {{ background: {PRINT_TOTAL_BG};
      font-weight: 800; color: {PRINT_NAVY}; border-top: 2px solid {PRINT_GOLD}; }}
.footer {{ color: {PRINT_MUTED}; border-top: 1px solid {PRINT_LINE}; }}
</style>
"""

# شريط أدوات الطباعة أسفل كل تقرير: زر واحد في مكان واحد، ويختفي عند الطباعة
# نفسه حتى لا يُطبع مع الورقة. يضاف مرة واحدة فيستفيد منه كل تقرير.
A4_PRINT_ACTION_BAR = f"""
<div class="noprint a4-print-actions">
  <p class="a4-print-hint">المقاس: A4 — تأكد من اختيار ورق A4 في نافذة الطباعة</p>
  <button class="a4-print-btn" type="button" onclick="window.print()">&#128424; طباعة</button>
</div>
"""

def _ensure_a4_print_button(html_content):
    """يضيف زر الطباعة أسفل التقرير إن لم يكن التقرير قد أضافه بنفسه.

    بعض التقارير تُبنى كصفحة كاملة، وبعضها كجزء فقط بلا وسم إغلاق، فنضع
    الزر قبل وسم الإغلاق إن وُجد وإلا في نهاية النص.
    """
    if "window.print()" in html_content:
        return html_content
    for closing in ("</body>", "</html>"):
        if closing in html_content:
            return html_content.replace(closing, A4_PRINT_ACTION_BAR + closing, 1)
    return html_content + A4_PRINT_ACTION_BAR

def apply_a4_print_layout(html_content):
    """Apply one predictable A4 print layout to every generated HTML report.

    كل تقرير يمرّ من هنا، فتُوحَّد مقاس الورقة وألوان الهوية البصرية، ويضمن
    وجود زر طباعة في موضع واحد بدل الاعتماد على كل تقرير بنسخه بنفسه.
    التقارير التي تضع زرها تُترك كما هي.
    """
    # نستخدم بدائل نصية بدل f-string لأن أقواس CSS تتعارض معها.
    a4_style = """
    <style id="a4-print-layout">
    @page { size: A4 portrait; margin: 10mm; }
    * { box-sizing: border-box; }
    html, body { width: 100%; max-width: 190mm; }
    body { margin: 0 auto; padding: 0; direction: rtl; }
    table { max-width: 100%; page-break-inside: auto; }
    tr { page-break-inside: avoid; page-break-after: auto; }
    thead { display: table-header-group; }
    img, svg { max-width: 100%; }
    .noprint { page-break-inside: avoid; }
    /* شريط الطباعة على الشاشة: زر واضح أسفل التقرير. */
    .a4-print-actions { text-align: center; margin: 26px 0 44px; }
    .a4-print-hint { color: __PRINT_MUTED__; font-size: 12px; margin: 0 0 12px; }
    .a4-print-btn { background: __PRINT_NAVY__; color: #fff; border: 0; border-radius: 10px;
        padding: 12px 34px; font: inherit; font-size: 15px; font-weight: 700;
        cursor: pointer; box-shadow: 0 2px 0 rgba(15, 43, 70, 0.25); }
    .a4-print-btn:hover { background: __PRINT_NAVY_DARK__; }
    @media print {
        html, body { width: 190mm; max-width: 190mm; background: #fff !important; }
        body { padding: 0 !important; margin: 0 !important; }
        .noprint, .a4-print-actions { display: none !important; }
        .page { max-width: 190mm !important; width: 100% !important; margin: 0 !important;
                box-shadow: none !important; border-radius: 0 !important; }
        /* قيود تمنع تجاوز الجداول لحدود الورقة أو قطع الصفوف والمدخلات. */
        table { width: 100% !important; max-width: 100% !important; }
        th, td { overflow-wrap: anywhere; word-break: break-word; }
        h1, h2, h3, h4 { page-break-after: avoid; break-after: avoid; }
        .footer { page-break-inside: avoid; break-inside: avoid; }
        img, svg { max-width: 100% !important; height: auto !important; }
    }
    </style>
    """
    a4_style = (a4_style.replace("__PRINT_NAVY_DARK__", PRINT_NAVY_DARK)
                .replace("__PRINT_NAVY__", PRINT_NAVY)
                .replace("__PRINT_MUTED__", PRINT_MUTED))
    if "</head>" in html_content:
        html_content = html_content.replace(
            "</head>", PRINT_THEME_STYLE + a4_style + "</head>", 1)
    else:
        html_content = html_content.replace(
            "<html", PRINT_THEME_STYLE + a4_style + "<html", 1)
    return _ensure_a4_print_button(html_content)

REPORT_PAGE_STYLE = f"""
<style>
body{{font-family:Tahoma,Arial,sans-serif;color:{PRINT_INK};padding:24px;}}
h1{{color:{PRINT_NAVY};font-size:22px;margin:0 0 6px;}}
h2{{color:{PRINT_NAVY};font-size:17px;margin:20px 0 8px;border-bottom:2px solid {PRINT_GOLD};padding-bottom:4px;}}
h2.driver{{display:flex;align-items:center;gap:8px;page-break-after:avoid;break-after:avoid;}}
h2.driver .badge{{background:{PRINT_GOLD};color:#fff;border-radius:10px;padding:1px 9px;font-size:11px;font-weight:bold;}}
p.intro{{color:{PRINT_MUTED};font-size:12px;margin:0 0 14px;}}
table{{page-break-inside:auto;}}
tr{{page-break-inside:avoid;break-inside:avoid;}}
.meta{{color:{PRINT_MUTED};margin-bottom:18px;font-size:12px;}}
.docno{{float:left;background:{PRINT_NAVY};color:#fff;padding:4px 10px;border-radius:4px;
       font-weight:bold;font-size:12px;}}
table{{border-collapse:collapse;width:100%;font-size:11px;margin-bottom:16px;}}
th{{background:{PRINT_NAVY};color:#fff;}}
th,td{{border:1px solid {PRINT_LINE};padding:7px;text-align:right;vertical-align:top;}}
td.c{{text-align:center;direction:ltr;unicode-bidi:isolate;}}
tr:nth-child(even){{background:{PRINT_ROW_ALT};}}
tr.voided{{background:#FDECEC !important;color:#9B2C2C;text-decoration:line-through;}}
tfoot td{{background:{PRINT_TOTAL_BG};font-weight:800;color:{PRINT_NAVY};}}
.signatures{{display:flex;justify-content:space-between;margin-top:34px;font-size:12px;}}
.signatures div{{flex:1;text-align:center;}}
.signature-line{{border-top:1px solid {PRINT_MUTED};margin:26px 12px 6px;}}
.footer{{margin-top:18px;border-top:1px solid {PRINT_LINE};padding-top:8px;
        color:{PRINT_MUTED};font-size:10px;text-align:center;line-height:1.6;}}
button{{padding:10px 24px;background:{PRINT_GOLD};border:0;cursor:pointer;font-weight:bold;}}
@media print{{.noprint{{display:none;}} body{{padding:0;}} .noprint,button{{display:none;}}}}
</style>"""

def statement_footer_html(doc_no=""):
    """توقيعات وختم الشركة مع رقم المستند لكل كشوف الحساب المطبوعة."""
    badge = f"<div class='docno'>{html.escape(doc_no)}</div>" if doc_no else ""
    return f"""{badge}
<div class="signatures">
  <div>المحاسب<div class="signature-line"></div></div>
  <div>مدير الحسابات<div class="signature-line"></div></div>
  <div>الشريك / السائق<div class="signature-line"></div></div>
  <div>الختم<div class="signature-line"></div></div>
</div>
<div class="footer">{html.escape(td.COMPANY_NAME_AR)} — {html.escape(td.COMPANY_ADDRESS_AR)}<br>
{html.escape(td.COMPANY_PHONE)} — {html.escape(td.COMPANY_EMAIL)}<br>
هذا الكشف صادر آلياً من نظام إدارة شركة النقل ولا يحتاج إلى ختم إضافي.</div>"""

def _open_print_report(title, meta, body, file_name, doc_no="", footer=True):
    """يبني صفحة تقرير عربية ثم يفتحها في المتصفح للطباعة."""
    tail = statement_footer_html(doc_no) if footer else ""
    html_content = f"""<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
{REPORT_PAGE_STYLE}</head><body>
<h1>{html.escape(title)}</h1>
<div class="meta">{html.escape(td.COMPANY_NAME_AR)} — {meta}</div>
{body}
{tail}
<p class="noprint"><button onclick="window.print()">طباعة التقرير</button></p>
</body></html>"""
    tmp_path = os.path.join(tempfile.gettempdir(), file_name)
    with open(tmp_path, "w", encoding="utf-8") as handle:
        handle.write(apply_a4_print_layout(html_content))
    webbrowser.open("file://" + tmp_path)
    return tmp_path
