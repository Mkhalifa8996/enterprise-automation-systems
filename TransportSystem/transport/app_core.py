# -*- coding: utf-8 -*-
"""جوهر التطبيق: التهيئة، المزامنة السحابية، التنقّل، وشاشة البداية."""

import json, os, threading, webbrowser
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from datetime import date
from tkinter import filedialog
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk
from . import data as td
from .data import demo_data
from . import single_instance
from .app_config import APP_LOCK_DIR, COLOR_ACCENT, COLOR_BG, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_CARD, COLOR_DANGER, COLOR_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_SHADOW, COLOR_SUCCESS, COLOR_TEXT, FONT_NAME, F_BODY, F_BOLD, F_H2, F_LABEL, F_STAT_LABEL, F_SUBTITLE, F_TITLE, NAV_ITEMS, PAGE_TITLES, WHEEL_OWNED_WIDGETS
from .print_letterhead import NO_CUSTOMER
from .ui_sidebar import Sidebar
from .app_registry import _ALL_CRUD_TABS, refresh_all_registers
from .ui_widgets import _is_descendant_of, _nearest_canvas, card_frame, center_dialog, make_btn, modern_entry, scrollable_pane
from .ui_text_edit import install_text_edit_bindings
from .ui_helpers import log_exception, safe_str

class AppCoreMixin:
    """جوهر التطبيق: التهيئة، المزامنة السحابية، التنقّل، وشاشة البداية."""

    def __init__(self):
        super().__init__()
        self.title("نظام إدارة شركة النقل")
        self.geometry("1340x780")
        self.configure(bg=COLOR_BG)
        self.minsize(1080, 660)

        self._session_daily_backup_done = False

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError as _log_exc: log_exception("__init__", _log_exc)

        install_text_edit_bindings(self)

        # --- تنسيق الجداول (Treeview) ---
        self.style.configure("Treeview", font=(FONT_NAME, 10), rowheight=30,
                              background=COLOR_CARD, fieldbackground=COLOR_CARD,
                              borderwidth=0, relief="flat")
        self.style.configure("Treeview.Heading", padding=(10, 9))
        self.style.configure("Treeview.Heading", font=(FONT_NAME, 10, "bold"),
                              background=COLOR_PRIMARY, foreground="white",
                              relief="flat", padding=(10, 9))
        self.style.map("Treeview.Heading", background=[("active", COLOR_PRIMARY_LIGHT)])
        self.style.map("Treeview", background=[("selected", COLOR_PRIMARY_LIGHT)],
                        foreground=[("selected", "white")])

        # --- تنسيق الأزرار ---
        self.style.configure("TButton", font=F_BODY, padding=8, relief="flat",
                              background=COLOR_BORDER_LIGHT, foreground=COLOR_TEXT)
        self.style.map("TButton",
                        background=[("active", COLOR_BORDER)],
                        foreground=[("active", COLOR_PRIMARY)])

        self.style.configure("Accent.TButton", font=F_BOLD, padding=9,
                              background=COLOR_ACCENT, foreground=COLOR_PRIMARY,
                              relief="flat")
        self.style.map("Accent.TButton",
                        background=[("active", "#D49B30"), ("pressed", "#D49B30")])

        self.style.configure("Secondary.TButton", font=F_BODY, padding=8,
                              background=COLOR_BORDER_LIGHT, foreground=COLOR_TEXT,
                              relief="flat")
        self.style.map("Secondary.TButton",
                        background=[("active", COLOR_BORDER)])

        self.style.configure("Danger.TButton", font=F_BODY, padding=8,
                              background="#FED7D7", foreground=COLOR_DANGER,
                              relief="flat")
        self.style.map("Danger.TButton",
                        background=[("active", "#FEB2B2")])

        # --- تنسيق القوائم المنسدلة ---
        self.style.configure("TCombobox", padding=5, relief="flat")
        self.style.map("TCombobox",
                        fieldbackground=[("readonly", COLOR_CARD)],
                        selectbackground=[("readonly", COLOR_PRIMARY_LIGHT)],
                        selectforeground=[("readonly", "white")])

        # --- تنسيق مربعات الاختيار ---
        self.style.configure("TCheckbutton", background=COLOR_CARD, font=F_BODY)
        self.style.configure("TNotebook", background=COLOR_BG, borderwidth=0, tabmargins=(4, 4, 4, 0))
        self.style.configure("TNotebook.Tab", font=F_BOLD, padding=(16, 8),
                             background=COLOR_BORDER_LIGHT, foreground=COLOR_MUTED)
        self.style.map("TNotebook.Tab",
                       background=[("selected", COLOR_PRIMARY)],
                       foreground=[("selected", "white")])
        self.style.configure("TSeparator", background=COLOR_BORDER)
        self.style.configure("Vertical.TScrollbar", troughcolor=COLOR_BG,
                             background=COLOR_BORDER, borderwidth=0, arrowsize=13)

        td.ensure_workbook()
        td.sync_excel(force=False)
        td.remove_disabled_invoice_items()

        # -------- تخطيط الشاشة الرئيسي: قائمة يمين + محتوى يسارها --------
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        content = tk.Frame(self, bg=COLOR_BG)
        content.grid(row=0, column=0, sticky="nsew")

        self.sidebar = Sidebar(self, NAV_ITEMS, self.show_page)
        self.sidebar.grid(row=0, column=1, sticky="ns")

        # --- شريط علوي عصري ---
        topbar = tk.Frame(content, bg=COLOR_CARD, height=58)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        self.page_title_lbl = tk.Label(topbar, text="", font=F_TITLE, bg=COLOR_CARD,
                                        fg=COLOR_PRIMARY, anchor="e")
        self.page_title_lbl.pack(side="right", padx=24, pady=12)
        # الشريط العلوي: العنوان يميناً والأزرار والمعلومات إلى يساره كما في العربية.
        make_btn(topbar, "نسخ احتياطي", self._create_backup, variant="secondary",
                 padx=8, pady=3).pack(side="right", padx=4)
        make_btn(topbar, "استعادة", self._restore_backup, variant="secondary",
                 padx=8, pady=3).pack(side="right", padx=4)
        make_btn(topbar, "مزامنة Firebase", self._sync_firebase_data, variant="secondary",
                 padx=8, pady=3).pack(side="right", padx=4)
        make_btn(topbar, "التنبيهات", self._show_alerts, variant="secondary",
                 padx=8, pady=3).pack(side="right", padx=4)
        make_btn(topbar, "إدارة النظام", self._show_admin_tools, variant="secondary",
                 padx=8, pady=3).pack(side="right", padx=4)
        make_btn(topbar, "تحديث", self.refresh_linked_data, variant="secondary",
                 padx=8, pady=3).pack(side="right", padx=4)
        self.data_status_lbl = tk.Label(
            topbar, text="● قاعدة البيانات جاهزة", bg=COLOR_CARD, fg=COLOR_SUCCESS,
            font=(FONT_NAME, 9, "bold"), anchor="e")
        self.data_status_lbl.pack(side="right", padx=(4, 12))
        tk.Label(topbar, text=f"المستخدم: {td.current_user()['username']}",
                 bg=COLOR_CARD, fg=COLOR_MUTED, font=(FONT_NAME, 8)).pack(side="right", padx=8)
        tk.Label(topbar, text=date.today().strftime("%Y-%m-%d"), bg=COLOR_CARD,
                 fg=COLOR_MUTED, font=(FONT_NAME, 9)).pack(side="right", padx=10)
        tk.Label(topbar, text="نسخة Excel احتياطية مفعّلة", bg=COLOR_CARD, fg=COLOR_MUTED,
                 font=(FONT_NAME, 8)).pack(side="left", padx=10)
        tk.Frame(content, bg=COLOR_BORDER, height=1).pack(fill="x")

        self.pages_area = tk.Frame(content, bg=COLOR_BG)
        self.pages_area.pack(fill="both", expand=True)
        self.pages_area.grid_rowconfigure(0, weight=1)
        self.pages_area.grid_columnconfigure(0, weight=1)

        self.pages = {}
        self.page_refreshers = {}  # key -> list[callable] تُنفَّذ عند فتح الشاشة
        self._page_canvases = {}    # key -> Canvas لتمرير محتوى الشاشة
        # عجلة الفأرة تمرّر الشاشة الحالية، مع استثناء الجداول والحقول.
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(sequence, self._on_page_wheel, add="+")

        # ---- حالة شاشة الرواتب ----
        # _salary_calc_redraw: دالة إعادة رسم حصر الراتب المفتوح حالياً.
        # _salary_calc_dirty: تغيّرت بيانات مرتبطة (سيارة/رحلة/مصروف) ويجب
        #   إعادة بناء الحصر عند فتح الشاشة إن كانت مغلقة الآن.
        # _salary_expense_overrides: تعديلات بنود المصروفات داخل شاشة الرواتب
        #   فقط — لا تُكتب في ملف البيانات ولا تؤثر على شاشة يومية السيارات
        #   أو شاشة الرحلات اليومية.
        self._salary_calc_redraw = None
        self._salary_calc_dirty = False
        self._salary_calc_context = {}
        self._salary_expense_overrides = {}
        self._firebase_sync_in_progress = False
        # -1 triggers a first upload after Firebase authentication is configured.
        self._last_firebase_change_revision = -1
        # نوافذ الإدارة تسجّل هنا دوال تحديث تُستدعى عند تغيّر أي بيانات.
        self._refresh_callbacks = []

        self._build_home_page()
        self._build_trips_page()
        self._build_daily_cars_tab()
        # تجميع الشاشات الأساسية (السائقون، السيارات، العملاء، الشركات) ضمن شاشة واحدة ذات تابات
        self._build_entities_tab()
        self._build_revenue_tab()
        self._build_invoices_tab()
        self._build_salaries_tab()
        self._build_partners_tab()
        self._build_reports_tab()

        self.refresh_linked_data()
        self.show_page("home")
        self._schedule_cloud_sync()
        self.after(350, self._prompt_firebase_setup_if_needed)

        # -------- ربط حدث تغيير حجم النافذة لإعادة توزيع الأعمدة --------
        self.bind("<Configure>", self._on_window_resize)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _prompt_firebase_setup_if_needed(self):
        """Open Firebase sign-in once when its project is configured locally."""
        config = td.get_firebase_sync_config()
        # إذا لم تكن بيانات Firebase مُعدّة بعد (لا يوجد رابط ولا مفتاح)
        if not config["database_url"] or not config["api_key"]:
            self._sync_firebase_data()
        elif not td.is_firebase_sync_configured(config):
            # إذا كانت البيانات موجودة ولكن لم يتم تسجيل الدخول بعد
            self._sync_firebase_data()

    def _create_backup(self):
        try:
            path = td.create_timestamped_backup()
        except Exception as exc:
            messagebox.showerror("النسخ الاحتياطي", str(exc), parent=self)
            return
        messagebox.showinfo("تم", f"تم إنشاء النسخة الاحتياطية:\n{path}", parent=self)
        self._session_daily_backup_done = True

    def _is_session_daily_backup_today(self):
        if not self._session_daily_backup_done:
            return False
        if td._last_excel_snapshot_date() == date.today():
            return True
        self._session_daily_backup_done = False
        return False

    def _sync_google_data(self):
        config = td.get_sync_config()
        if not config["endpoint"]:
            dialog = tk.Toplevel(self)
            dialog.title("إعداد مزامنة Google Sheets")
            dialog.geometry("620x230")
            dialog.configure(bg=COLOR_BG)
            dialog.transient(self)
            dialog.grab_set()
            center_dialog(dialog, self)
            body = tk.Frame(dialog, bg=COLOR_BG)
            body.pack(fill="both", expand=True, padx=18, pady=18)
            tk.Label(body, text="رابط Google Apps Script المنشور",
                     font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED,
                     anchor="e").pack(fill="x")
            endpoint_var = tk.StringVar()
            endpoint_entry = modern_entry(body, endpoint_var)
            tk.Label(body, text="رمز المزامنة السري",
                     font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED,
                     anchor="e").pack(fill="x", pady=(8, 0))
            token_var = tk.StringVar()
            modern_entry(body, token_var, state="normal")

            def save_and_sync():
                try:
                    td.configure_google_sync(endpoint_var.get(), token_var.get())
                except ValueError as exc:
                    messagebox.showwarning("إعداد المزامنة", str(exc), parent=dialog)
                    return
                dialog.destroy()
                self._sync_google_data()

            buttons = tk.Frame(body, bg=COLOR_BG)
            buttons.pack(fill="x", pady=(14, 0))
            make_btn(buttons, "حفظ ومزامنة", save_and_sync,
                     variant="accent").pack(side="right", padx=4)
            make_btn(buttons, "إلغاء", dialog.destroy,
                     variant="secondary").pack(side="right", padx=4)
            endpoint_entry.focus_set()
            return
        try:
            result = td.sync_with_google_sheets()
        except (RuntimeError, ValueError) as exc:
            messagebox.showerror("مزامنة Google", str(exc), parent=self)
            return
        self.refresh_linked_data()
        messagebox.showinfo(
            "مزامنة Google",
            f"اكتملت المزامنة.\nتم استلام: {result['pulled']}\n"
            f"تم رفع: {result['pushed']}",
            parent=self,
        )

    def _firebase_phone_login(self, database_url, api_key, setup_dialog):
        database_url = database_url.strip()
        api_key = api_key.strip()
        if not database_url or not api_key:
            messagebox.showwarning(
                "تسجيل الهاتف", "أدخل رابط قاعدة Firebase وWeb API Key أولاً.",
                parent=setup_dialog,
            )
            return
        project_id = database_url.split("//", 1)[-1].split(".", 1)[0]
        auth_domain = f"{project_id}.firebaseapp.com"
        result_holder = {}
        result_event = threading.Event()

        page = f"""<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>تسجيل الدخول برقم الهاتف</title>
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-auth-compat.js"></script>
<style>body{{font-family:Arial;max-width:520px;margin:40px auto;padding:20px}}
input,button{{width:100%;padding:12px;margin:7px 0;box-sizing:border-box}}
button{{background:#e8a838;border:0;cursor:pointer}}#recaptcha-container{{margin:10px 0}}</style>
</head><body><h2>تسجيل الدخول برقم الهاتف</h2>
<p>أدخل الرقم بصيغة دولية، ثم رمز SMS.</p>
<input id="phone" placeholder="+965XXXXXXXX">
<div id="recaptcha-container"></div><button id="send">إرسال رمز SMS</button>
<input id="code" placeholder="رمز التحقق" style="display:none">
<button id="verify" style="display:none">تأكيد الدخول</button><p id="status"></p>
<script>
const app=firebase.initializeApp({{apiKey:{json.dumps(api_key)},authDomain:{json.dumps(auth_domain)},
databaseURL:{json.dumps(database_url)}}});
const auth=app.auth(); let confirmation=null;
const status=document.getElementById('status');
document.getElementById('send').onclick=async()=>{{
 try{{window.recaptchaVerifier=new firebase.auth.RecaptchaVerifier('recaptcha-container',
 {{size:'normal'}},auth); const phone=document.getElementById('phone').value.trim();
 confirmation=await auth.signInWithPhoneNumber(phone,window.recaptchaVerifier);
 document.getElementById('code').style.display='block';document.getElementById('verify').style.display='block';
 status.textContent='تم إرسال الرمز.';}}catch(e){{status.textContent=e.message;}}
}};
document.getElementById('verify').onclick=async()=>{{
 try{{const result=await confirmation.confirm(document.getElementById('code').value.trim());
 await fetch('/callback',{{method:'POST',headers:{{'Content-Type':'application/json'}},
 body:JSON.stringify({{refreshToken:result.user.refreshToken}})}});status.textContent='تم الدخول، يمكنك إغلاق الصفحة.';}}
 catch(e){{status.textContent=e.message;}}
}};
</script></body></html>"""

        class PhoneHandler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                return

            def do_GET(self):
                if self.path != "/":
                    self.send_error(404)
                    return
                payload = page.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_POST(self):
                if self.path != "/callback":
                    self.send_error(404)
                    return
                length = int(self.headers.get("Content-Length", "0"))
                try:
                    result_holder.update(json.loads(self.rfile.read(length).decode("utf-8")))
                    payload = b"OK"
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    result_event.set()
                except (ValueError, UnicodeDecodeError):
                    self.send_error(400)

        try:
            server = ThreadingHTTPServer(("127.0.0.1", 0), PhoneHandler)
        except OSError as exc:
            messagebox.showerror("تسجيل الهاتف", str(exc), parent=setup_dialog)
            return
        threading.Thread(target=server.serve_forever, daemon=True).start()
        webbrowser.open(f"http://127.0.0.1:{server.server_port}/")

        def wait_for_result():
            if not result_event.wait(300):
                server.shutdown()
                self.after(0, lambda: messagebox.showwarning(
                    "تسجيل الهاتف", "انتهت مهلة التحقق.", parent=setup_dialog))
                return
            server.shutdown()
            refresh_token = result_holder.get("refreshToken", "")
            if not refresh_token:
                self.after(0, lambda: messagebox.showerror(
                    "تسجيل الهاتف", "لم يتم استلام جلسة Firebase.", parent=setup_dialog))
                return
            try:
                td.save_firebase_phone_session(database_url, api_key, refresh_token)
            except ValueError as exc:
                self.after(0, lambda: messagebox.showerror(
                    "تسجيل الهاتف", str(exc), parent=setup_dialog))
                return
            self.after(0, lambda: (setup_dialog.destroy(), self._sync_firebase_data()))

        threading.Thread(target=wait_for_result, daemon=True).start()

    def _sync_firebase_data(self):
        config = td.get_firebase_sync_config()
        if not td.is_firebase_sync_configured(config):
            project_configured = bool(config["database_url"] and config["api_key"])
            dialog = tk.Toplevel(self)
            dialog.title("تسجيل الدخول" if project_configured else "إعداد مزامنة Firebase")
            dialog.geometry("520x310" if project_configured else "700x430")
            dialog.configure(bg=COLOR_BG)
            dialog.transient(self)
            dialog.grab_set()
            center_dialog(dialog, self)
            body = tk.Frame(dialog, bg=COLOR_BG)
            body.pack(fill="both", expand=True, padx=18, pady=18)
            url_var = tk.StringVar()
            url_var.set(config["database_url"])
            api_key_var = tk.StringVar()
            api_key_var.set(config["api_key"])
            url_entry = None
            if project_configured:
                tk.Label(body, text="تسجيل الدخول لتفعيل الحفظ التلقائي",
                         font=F_H2, bg=COLOR_BG, fg=COLOR_PRIMARY,
                         anchor="e").pack(fill="x", pady=(4, 12))
                tk.Label(body, text="بيانات ربط النظام مُعدّة مسبقًا.",
                         font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED,
                         anchor="e").pack(fill="x", pady=(0, 8))
            else:
                tk.Label(body, text="رابط Firebase Realtime Database",
                         font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED,
                         anchor="e").pack(fill="x")
                url_entry = modern_entry(body, url_var)
                tk.Label(body, text="Web API Key من إعدادات مشروع Firebase",
                         font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED,
                         anchor="e").pack(fill="x", pady=(8, 0))
                modern_entry(body, api_key_var, state="normal")
            tk.Label(body, text="البريد الإلكتروني لمستخدم Firebase",
                     font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED,
                     anchor="e").pack(fill="x", pady=(8, 0))
            email_var = tk.StringVar()
            email_var.set(config["email"])
            modern_entry(body, email_var, state="normal")
            tk.Label(body, text="كلمة مرور Firebase",
                     font=F_LABEL, bg=COLOR_BG, fg=COLOR_MUTED,
                     anchor="e").pack(fill="x", pady=(8, 0))
            password_var = tk.StringVar()
            password_entry = tk.Entry(
                body, textvariable=password_var, show="*", font=F_BODY,
                justify="right", relief="flat", bd=0,
                highlightthickness=2, highlightbackground=COLOR_BORDER,
                highlightcolor=COLOR_PRIMARY_LIGHT)
            password_entry.pack(fill="x", ipady=4)
            tk.Label(
                body,
                text=("أدخل بياناتك أو استخدم تسجيل الهاتف."
                      if project_configured else
                      "فعّل Email/Password في Authentication واضبط قواعد Realtime Database للمستخدمين الموثقين."),
                font=F_LABEL, bg=COLOR_BG,
                fg=COLOR_MUTED if project_configured else COLOR_DANGER,
                anchor="e", justify="right",
            ).pack(fill="x", pady=(10, 0))

            def save_and_sync():
                try:
                    td.configure_firebase_sync(
                        url_var.get(), api_key_var.get(), email_var.get(),
                        password_var.get())
                except ValueError as exc:
                    messagebox.showwarning("إعداد Firebase", str(exc), parent=dialog)
                    return
                dialog.destroy()
                self._sync_firebase_data()

            buttons = tk.Frame(body, bg=COLOR_BG)
            buttons.pack(fill="x", pady=(14, 0))
            make_btn(buttons, "تسجيل برقم الهاتف", lambda: self._firebase_phone_login(
                url_var.get(), api_key_var.get(), dialog),
                     variant="secondary").pack(side="right", padx=4)
            make_btn(buttons, "تسجيل الدخول" if project_configured else "حفظ ومزامنة", save_and_sync,
                     variant="accent").pack(side="right", padx=4)
            make_btn(buttons, "إلغاء", dialog.destroy,
                     variant="secondary").pack(side="right", padx=4)
            if project_configured:
                password_entry.focus_set()
            else:
                url_entry.focus_set()
            return
        try:
            result = td.sync_with_firebase()
        except (RuntimeError, ValueError) as exc:
            messagebox.showerror("مزامنة Firebase", str(exc), parent=self)
            return
        self.refresh_linked_data()
        messagebox.showinfo(
            "مزامنة Firebase",
            f"اكتملت المزامنة.\nتم استلام: {result['pulled']}\n"
            f"تم رفع: {result['pushed']}",
            parent=self,
        )

    def _schedule_cloud_sync(self):
        self._cloud_sync_after_id = self.after(2000, self._auto_sync_cloud_data)

    def _auto_sync_cloud_data(self):
        firebase_config = td.get_firebase_sync_config()
        revision = td.local_change_revision()
        _firebase_ready = td.is_firebase_sync_configured(firebase_config)
        _no_sync_in_progress = not self._firebase_sync_in_progress
        _has_changes = revision != self._last_firebase_change_revision
        print(f"[DEBUG] Firebase ready: {_firebase_ready}, No sync: {_no_sync_in_progress}, Has changes: _has_changes (rev={revision}, last={self._last_firebase_change_revision})")
        if (_firebase_ready and _no_sync_in_progress and _has_changes):
            self._firebase_sync_in_progress = True
            self.data_status_lbl.config(
                text="● جاري حفظ التغييرات تلقائياً...", fg=COLOR_MUTED)

            def sync_in_background():
                try:
                    result = td.sync_with_firebase(timeout=20)
                    self.after(0, lambda: self._finish_auto_firebase_sync(
                        result=result))
                except (RuntimeError, ValueError) as exc:
                    self.after(0, lambda: self._finish_auto_firebase_sync(
                        error=str(exc)))
                except Exception as exc:
                    self.after(0, lambda: self._finish_auto_firebase_sync(
                        error=str(exc)))

            threading.Thread(target=sync_in_background, daemon=True).start()
        self._schedule_cloud_sync()

    def _finish_auto_firebase_sync(self, result=None, error=""):
        self._firebase_sync_in_progress = False
        if error:
            self.data_status_lbl.config(text="● تعذر الحفظ التلقائي", fg=COLOR_DANGER)
            self._last_sync_error = error
            # إعادة تعيين شريط الحالة بعد 5 ثواني
            self.after(5000, lambda: self.data_status_lbl.config(
                text="● قاعدة البيانات جاهزة", fg=COLOR_SUCCESS))
        else:
            self._last_firebase_change_revision = td.local_change_revision()
            self.data_status_lbl.config(
                text=f"● حُفظ تلقائياً ({result['pulled']} مستلم / {result['pushed']} مرفوع)",
                fg=COLOR_SUCCESS,
            )
            self.refresh_linked_data()
            # إعادة تعيين شريط الحالة بعد 3 ثواني
            self.after(3000, lambda: self.data_status_lbl.config(
                text="● قاعدة البيانات جاهزة", fg=COLOR_SUCCESS))

    def _show_undo_result(self, result, refresh_callback=None):
        """إظهار نتيجة عملية التراجع للمستخدم."""
        success = result.get("success", 0)
        failed = result.get("failed", [])
        skipped = result.get("skipped", [])
        
        message_parts = [f"تم التراجع عن {success} عملية بنجاح."]
        
        if failed:
            failed_text = "\n".join(f"• الخطأ ({f['id']}): {f['reason']}" for f in failed)
            message_parts.append(f"\nالفشل ({len(failed)}):\n{failed_text}")
        
        if skipped:
            skipped_text = "\n".join(f"• '{f['reason']}'" for f in skipped)
            message_parts.append(f"\nتخطى ({len(skipped)}):\n{skipped_text}")
        
        messagebox.showinfo(
            "نتيجة التراجع",
            "\n".join(message_parts),
            parent=self
        )
        
        if refresh_callback:
            refresh_callback()

    def _show_alerts(self):
        alerts = td.get_alerts()
        dlg = tk.Toplevel(self)
        dlg.title("التنبيهات")
        dlg.geometry("720x430")
        dlg.transient(self)
        body = tk.Frame(dlg, bg=COLOR_BG)
        body.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(body, text=f"التنبيهات الحالية ({len(alerts)})", font=F_H2,
                 bg=COLOR_BG, fg=COLOR_PRIMARY, anchor="e").pack(fill="x", pady=(0, 10))
        tree = ttk.Treeview(body, columns=("type", "item", "date", "message"),
                            show="headings", height=14)
        for col, title, width in (
            ("type", "النوع", 120), ("item", "السيارة", 120),
            ("date", "التاريخ", 110), ("message", "التفاصيل", 320),
        ):
            tree.heading(col, text=title)
            tree.column(col, width=width, anchor="e")
        tree.pack(fill="both", expand=True)
        for alert in alerts:
            tree.insert("", "end", values=(alert["type"], alert["item"],
                                           alert["date"], alert["message"]))
        make_btn(body, "إغلاق", dlg.destroy, variant="secondary").pack(pady=(10, 0))

    def _show_admin_tools(self):
        dlg = tk.Toplevel(self)
        dlg.title("إدارة النظام")
        dlg.geometry("760x520")
        dlg.transient(self)
        body = tk.Frame(dlg, bg=COLOR_BG)
        body.pack(fill="both", expand=True, padx=16, pady=16)
        tabs = ttk.Notebook(body)
        tabs.pack(fill="both", expand=True)

        periods = tk.Frame(tabs, bg=COLOR_CARD)
        tabs.add(periods, text="الفترات المالية")
        tk.Label(periods, text="الشهر YYYY-MM", font=F_LABEL,
                 bg=COLOR_CARD).pack(anchor="e", padx=12, pady=(14, 4))
        month_var = tk.StringVar(value=date.today().strftime("%Y-%m"))
        tk.Entry(periods, textvariable=month_var, justify="right",
                 font=F_BODY).pack(anchor="e", padx=12, ipadx=30)
        actions = tk.Frame(periods, bg=COLOR_CARD)
        actions.pack(anchor="e", padx=12, pady=10)
        def close_month():
            try:
                td.close_period(month_var.get())
                refresh_periods()
                messagebox.showinfo("تم", "تم إقفال الفترة.", parent=dlg)
            except (ValueError, PermissionError) as exc:
                messagebox.showerror("الفترات", str(exc), parent=dlg)
        def reopen_month():
            try:
                td.reopen_period(month_var.get())
                refresh_periods()
                messagebox.showinfo("تم", "تم فتح الفترة.", parent=dlg)
            except PermissionError as exc:
                messagebox.showerror("الفترات", str(exc), parent=dlg)
        make_btn(actions, "إقفال الشهر", close_month, variant="accent").pack(side="right", padx=4)
        make_btn(actions, "فتح الشهر", reopen_month, variant="secondary").pack(side="right", padx=4)
        period_list = tk.Listbox(periods, font=F_BODY, height=12, justify="right")
        period_list.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        def refresh_periods():
            period_list.delete(0, "end")
            for month in td.list_closed_periods():
                period_list.insert("end", f"مغلق: {month}")
        refresh_periods()

        audit = tk.Frame(tabs, bg=COLOR_CARD)
        tabs.add(audit, text="سجل العمليات")
        
        # أزرار التحكم
        audit_actions = tk.Frame(audit, bg=COLOR_CARD)
        audit_actions.pack(fill="x", padx=12, pady=(0, 8))
        
        undo_btn = make_btn(audit_actions, "تراجع عن المحددين", None, variant="danger")
        undo_btn.pack(side="right", padx=4)
        select_all_btn = make_btn(audit_actions, "تحديد الكل", None, variant="secondary")
        select_all_btn.pack(side="right", padx=4)
        clear_btn = make_btn(audit_actions, "إزالة التحديد", None, variant="secondary")
        clear_btn.pack(side="right", padx=4)
        
        # إحصائيات التحديد
        audit_status = tk.Label(audit_actions, text="0 محدد", font=F_LABEL, 
                                bg=COLOR_CARD, fg=COLOR_MUTED, anchor="e")
        audit_status.pack(side="right", padx=8)
        
        # شجرة السجلات مع دعم التحديد
        audit_tree = ttk.Treeview(
            audit, columns=("at", "actor", "action", "sheet", "key", "id"),
            show="headings",
            selectmode="extended",
        )
        for col, title, width in (("at", "التاريخ", 130), ("actor", "المستخدم", 130),
                                   ("action", "العملية", 120), ("sheet", "الجدول", 120),
                                   ("key", "المفتاح", 150), ("id", "ID", 60)):
            audit_tree.heading(col, text=title)
            audit_tree.column(col, width=width, anchor="e")
        audit_tree.pack(fill="both", expand=True, padx=12, pady=12)
        
        # تحديث حالة التحديد
        def update_selection_status():
            selected = audit_tree.selection()
            count = len(selected)
            audit_status.config(text=f"{count} محدد" if count > 0 else "0 محدد")
            undo_btn.config(state="normal" if count > 0 else "disabled")
        
        audit_tree.bind("<<TreeviewSelect>>", lambda e: update_selection_status())
        
        # تحميل السجلات
        def load_audit_logs():
            for item in audit_tree.get_children():
                audit_tree.delete(item)
            for row in td.load_audit_logs(limit=500):
                audit_tree.insert("", "end", values=(
                    row["created_at"], row["actor"],
                    row["action"], row["sheet_key"], row["record_key"], row["id"]
                ))
        
        load_audit_logs()
        
        # تحديد الكل
        select_all_btn.config(command=lambda: (
            audit_tree.select_all(), update_selection_status()
        ))
        
        # إزالة التحديد
        clear_btn.config(command=lambda: (
            audit_tree.selection_remove(audit_tree.selection()), update_selection_status()
        ))
        
        # دالة التراجع
        def undo_selected():
            selected_ids = []
            for item in audit_tree.selection():
                values = audit_tree.item(item, "values")
                if len(values) >= 6:
                    try:
                        selected_ids.append(int(values[5]))  # عمود ID
                    except (ValueError, IndexError):
                        continue
            
            if not selected_ids:
                return
            
            # عرض تفاصيل العمليات المحددة
            selected_logs = td.load_audit_logs_by_ids(selected_ids)
            if not selected_logs:
                messagebox.showwarning("تراجع", "لا يمكن تحميل تفاصيل العمليات المحددة.", parent=dlg)
                return
            
            # بناء نص التفاصيل
            details_text = "العمليات المحددة للتراجع:\n\n"
            for log in selected_logs:
                details_text += f"• {log['created_at']} - {log['actor']} - {log['action']} "
                details_text += f"- {log['sheet_key']} - {log['record_key']}\n"
            details_text += f"\nعدد العمليات: {len(selected_logs)}\n"
            details_text += "تحذير: هذا الإجراء سيقوم بإلغاء هذه العمليات!"
            
            if not messagebox.askyesno("تأكيد التراجع", details_text, parent=dlg):
                return
            
            # تنفيذ التراجع
            import threading
            undo_btn.config(state="disabled", text="جارٍ التراجع...")
            
            def do_undo():
                try:
                    result = td.undo_audit_logs(selected_ids)
                    self.after(0, lambda: self._show_undo_result(result, load_audit_logs))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("تراجع", str(e), parent=dlg))
                    self.after(0, lambda: (undo_btn.config(state="normal", text="تراجع عن المحددين"), 
                                           update_selection_status()))
            
            threading.Thread(target=do_undo, daemon=True).start()
        
        undo_btn.config(command=undo_selected)
        
        # تحديث الصفحة عند besoin
        def refresh_audit():
            load_audit_logs()
            update_selection_status()
        
        self._refresh_callbacks.append(refresh_audit)

        users = tk.Frame(tabs, bg=COLOR_CARD)
        tabs.add(users, text="المستخدمون والصلاحيات")
        tk.Label(users, text="المستخدم الحالي مدير النظام. الصلاحيات تطبق على مستوى طبقة البيانات.",
                 font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(anchor="e", padx=12, pady=12)
        user_tree = ttk.Treeview(users, columns=("username", "role", "active"),
                                 show="headings", height=8)
        for col, title in (("username", "المستخدم"), ("role", "الصلاحية"), ("active", "نشط")):
            user_tree.heading(col, text=title)
            user_tree.column(col, width=180, anchor="e")
        user_tree.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        for user in td.load_users():
            user_tree.insert("", "end", values=(user["username"], user["role"],
                                                "نعم" if user["active"] else "لا"))
        editor = tk.Frame(users, bg=COLOR_CARD)
        editor.pack(fill="x", padx=12, pady=(0, 12))
        user_name = tk.StringVar()
        user_password = tk.StringVar()
        user_role = tk.StringVar(value="إدخال")
        tk.Entry(editor, textvariable=user_name, justify="right",
                 font=F_BODY).pack(side="right", padx=4, ipadx=35)
        tk.Entry(editor, textvariable=user_password, show="*", justify="right",
                 font=F_BODY).pack(side="right", padx=4, ipadx=35)
        ttk.Combobox(editor, textvariable=user_role, state="readonly",
                     values=("مدير", "محاسب", "إدخال"), width=12).pack(side="right", padx=4)
        def add_user():
            try:
                td.save_user(user_name.get(), user_role.get(), user_password.get() or None)
                user_tree.insert("", "end", values=(user_name.get(), user_role.get(), "نعم"))
                user_name.set("")
                user_password.set("")
            except (ValueError, PermissionError) as exc:
                messagebox.showerror("المستخدمون", str(exc), parent=dlg)
        make_btn(editor, "إضافة / تحديث", add_user, variant="accent").pack(side="right", padx=4)

        # تبويب البيانات التجريبية: تعبئة شاملة أو حذف آمن ببيانات المستخدم.
        demo_tab = tk.Frame(tabs, bg=COLOR_CARD)
        tabs.add(demo_tab, text="بيانات تجريبية")
        tk.Label(demo_tab, text=(
            "تعبئة كل جداول النظام بعشرة سجلات فأكثر لتجربة الشاشات والتقارير.\n"
            "البيانات التجريبية موسومة ويمكن حذفها بالكامل دون المساس ببياناتك."),
            font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED, justify="right",
            anchor="e").pack(fill="x", padx=14, pady=(14, 6))
        demo_actions = tk.Frame(demo_tab, bg=COLOR_CARD)
        demo_actions.pack(fill="x", padx=14, pady=(0, 8))

        def run_seed():
            try:
                report = demo_data.seed(verbose=False)
            except Exception as exc:
                messagebox.showerror("البيانات التجريبية", str(exc), parent=dlg)
                return
            refresh_demo_table()
            self.refresh_linked_data()
            messagebox.showinfo(
                "البيانات التجريبية",
                "تمت تعبئة البيانات التجريبية في جميع الجداول.",
                parent=dlg)

        def run_clear():
            counts = demo_data.demo_counts()
            total = sum(counts.values())
            if not total:
                messagebox.showinfo("البيانات التجريبية", "لا توجد بيانات تجريبية لحذفها.",
                                    parent=dlg)
                return
            if not messagebox.askyesno(
                    "تأكيد الحذف",
                    f"سيتم حذف {total} سجلاً تجريبياً فقط.\n"
                    "بياناتك الحقيقية لن تتأثر.\n\nهل تريد المتابعة؟", parent=dlg):
                return
            try:
                result = demo_data.clear(verbose=False)
            except Exception as exc:
                messagebox.showerror("البيانات التجريبية", str(exc), parent=dlg)
                return
            refresh_demo_table()
            self.refresh_linked_data()
            messagebox.showinfo(
                "البيانات التجريبية",
                f"تم حذف {result['removed']} سجلاً تجريبياً.", parent=dlg)

        make_btn(demo_actions, "تعبئة بيانات تجريبية", run_seed, variant="accent").pack(side="right", padx=4)
        make_btn(demo_actions, "حذف البيانات التجريبية", run_clear, variant="danger").pack(side="right", padx=4)
        demo_tree = ttk.Treeview(demo_tab, columns=("sheet", "count"),
                                 show="headings", height=16)
        for col, title, width in (("sheet", "الجدول", 260), ("count", "سجلات تجريبية", 150)):
            demo_tree.heading(col, text=title)
            demo_tree.column(col, width=width, anchor="e")
        demo_tree.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        def refresh_demo_table():
            for row in demo_tree.get_children():
                demo_tree.delete(row)
            for sheet, count in sorted(demo_data.demo_counts().items()):
                demo_tree.insert("", "end", values=(sheet, count))

        refresh_demo_table()

        attachments = tk.Frame(tabs, bg=COLOR_CARD)
        tabs.add(attachments, text="المرفقات")
        attachment_tree = ttk.Treeview(
            attachments, columns=("type", "key", "name", "by", "at"),
            show="headings",
        )
        for col, title, width in (("type", "النوع", 110), ("key", "المفتاح", 120),
                                  ("name", "الملف", 220), ("by", "أضافه", 120),
                                  ("at", "التاريخ", 150)):
            attachment_tree.heading(col, text=title)
            attachment_tree.column(col, width=width, anchor="e")
        attachment_tree.pack(fill="both", expand=True, padx=12, pady=12)
        for item in td.load_attachments():
            attachment_tree.insert("", "end", iid=str(item["id"]),
                                   values=(item["entity_type"], item["record_key"],
                                           item["file_name"], item["created_by"],
                                           item["created_at"]))
        attachment_tree.bind("<Double-1>", lambda _event: self._open_selected_attachment(
            attachment_tree))
        attachment_actions = tk.Frame(attachments, bg=COLOR_CARD)
        attachment_actions.pack(fill="x", padx=12, pady=(0, 12))
        def add_file():
            source = filedialog.askopenfilename(parent=dlg, title="اختيار مستند")
            if not source:
                return
            try:
                item = td.add_attachment("عام", "عام", source)
                attachment_tree.insert("", 0, values=(item["entity_type"], item["record_key"],
                                                      item["file_name"], td.current_user()["username"],
                                                      date.today().isoformat()))
            except (ValueError, OSError) as exc:
                messagebox.showerror("المرفقات", str(exc), parent=dlg)
        make_btn(attachment_actions, "إضافة مستند", add_file, variant="accent").pack(side="right")

    @staticmethod
    def _open_selected_attachment(tree):
        selection = tree.selection()
        if not selection:
            return
        item = next((row for row in td.load_attachments() if str(row["id"]) == selection[0]), None)
        if item and os.path.isfile(item["path"]):
            os.startfile(item["path"])

    def _restore_backup(self):
        path = filedialog.askopenfilename(
            parent=self, title="اختيار نسخة احتياطية",
            initialdir=td.BACKUP_DIR if os.path.isdir(td.BACKUP_DIR) else td.APP_DIR,
            filetypes=[("Excel", "*.xlsx")],
        )
        if not path:
            return
        if not messagebox.askyesno(
            "تأكيد الاستعادة",
            "سيتم استبدال بيانات SQLite الحالية ببيانات النسخة المحددة. متابعة؟",
            parent=self,
        ):
            return
        try:
            skipped = td.restore_from_excel(path)
            self.refresh_linked_data()
            self.show_page(getattr(self, "current_page", "home"))
        except Exception as exc:
            messagebox.showerror("الاستعادة", str(exc), parent=self)
            return
        message = "تمت استعادة البيانات بنجاح."
        if skipped:
            # جداول أُضيفت بعد تاريخ النسخة فلم تكن داخلها.
            message += ("\nالجداول التالية لم تكن في النسخة وتم اعتبارها فارغة:"
                        "\n" + "\n".join(f"• {name}" for name in skipped))
        messagebox.showinfo("تم", message, parent=self)

    def _on_close(self):
        """عند الإغلاق: نسخة احتياطية محلية ثم محاولة مزامنة سحابية أخيرة."""
        sync_after_id = getattr(self, "_cloud_sync_after_id", None)
        if sync_after_id:
            try:
                self.after_cancel(sync_after_id)
            except tk.TclError as _log_exc: log_exception("_on_close", _log_exc)
        # نحفظ نسخة محلية أولاً حتى لا تضيع عمل الجلسة عند إغلاق مفاجئ.
        if not self._is_session_daily_backup_today():
            try:
                self._pending_backup_path = td.create_timestamped_backup()
                self._session_daily_backup_done = True
            except Exception as exc:
                log_exception("نسخة احتياطية عند الإغلاق", exc)
                if not messagebox.askyesno(
                    "تعذر النسخ الاحتياطي",
                    f"تعذر إنشاء نسخة قبل الإغلاق:\n{exc}\nهل تريد الإغلاق رغم ذلك؟",
                    parent=self,
                ):
                    return
        # المزامنة السحابية اختيارية ولا يجب أن تمنع الإغلاق.
        try:
            if td.is_firebase_sync_configured(td.get_firebase_sync_config()):
                td.sync_with_firebase(timeout=10)
        except Exception as exc:
            log_exception("مزامنة Firebase عند الإغلاق", exc)
        self.destroy()
        # تحرير القفل أخيراً حتى لا يمنع التشغيل التالي.
        try:
            single_instance.release(APP_LOCK_DIR)
        except Exception as exc:
            log_exception("تحرير قفل النسخة الواحدة", exc)

    def _on_window_resize(self, event=None):
        """يُستدعى عند تغيير حجم النافذة. إعادة توزيع الأعمدة تتم تلقائياً
        عبر الربط <Configure> في جدول كل شاشة، لذلك لا حاجة لمنطق إضافي هنا."""
        if event is None or event.widget != self:
            return

    @staticmethod
    def _auto_size_tree(tree, cols):
        """توزيع عرض أعمدة جدول معين تلقائياً حسب العرض المتاح."""
        try:
            w = tree.winfo_width()
            if w <= 1:
                return
            n = len(cols)
            if n == 0:
                return
            avg = max(80, w // n)
            for c in cols:
                tree.column(c, width=avg, stretch=True)
        except Exception as _log_exc: log_exception("_auto_size_tree", _log_exc)

    # ---------------- التنقّل بين الشاشات ----------------
    def register_page(self, key, frame, refreshers=None, canvas=None):
        frame.grid(row=0, column=0, sticky="nsew")
        self.pages[key] = frame
        self.page_refreshers[key] = refreshers or []
        # اللوحة تُستعمل في تمرير الصفحة بالماوس وتُصفَّّر عند فتح الشاشة.
        if canvas is not None:
            self._page_canvases[key] = canvas

    def show_page(self, key):
        if key not in self.pages:
            return
        self.current_page = key
        self.pages[key].tkraise()
        self.sidebar.set_active(key)
        self.page_title_lbl.config(text=PAGE_TITLES.get(key, ""))
        canvas = self._page_canvases.get(key)
        if canvas is not None:
            # كل شاشة تبدأ من أعلى محتواها حتى لا يبقى المستخدم في منتصف شاشة أخرى.
            canvas.yview_moveto(0.0)
        for fn in self.page_refreshers.get(key, []):
            try:
                fn()
            except Exception as exc:
                # فشل تحديث شاشة يجب أن يُسجَّل لا أن يختفي بصمت.
                log_exception(f"تحديث شاشة {key}", exc)

    def _scroll_target_for(self, event):
        """يحدّد اللوحة التي يجب أن تمرّرها عجلة الفأرة عند هذا الحدث."""
        try:
            widget = self.nametowidget(event.widget)
        except (KeyError, tk.TclError):
            return None
        # الجداول والحقول لها تمريرها الخاص؛ لا نزاحمها.
        if widget.winfo_class() in WHEEL_OWNED_WIDGETS:
            return None
        nearest = _nearest_canvas(widget)
        if widget.winfo_toplevel() is not self:
            # نافذة مستقلة: نمرّر أقرب لوحة داخلها فقط ولا نحرّك الشاشة خلفها.
            return nearest
        page_canvas = self._page_canvases.get(getattr(self, "current_page", ""))
        if page_canvas is None:
            return None
        # لو كان المؤشر فوق لوحة متداخلة (مثل منطقة الرحلات) نمرّرها هي.
        if nearest is not None and _is_descendant_of(nearest, page_canvas):
            return nearest
        return page_canvas

    def _on_page_wheel(self, event):
        canvas = self._scroll_target_for(event)
        if canvas is None:
            return
        if getattr(event, "num", None) == 4:
            steps = -3
        elif getattr(event, "num", None) == 5:
            steps = 3
        else:
            delta = getattr(event, "delta", 0)
            steps = int(-delta / 120) * 3 if delta else 0
        if steps:
            canvas.yview_scroll(steps, "units")

    def refresh_linked_data(self):
        """Refresh every control whose options come from another screen."""
        if getattr(self, "_linked_refresh_pending", False):
            return
        self._linked_refresh_pending = True
        try:
            self._refresh_linked_data_now()
        finally:
            self._linked_refresh_pending = False

    def _run_refresh_callbacks(self):
        """يستدعي دوال التحديث المسجّلة من نوافذ الإدارة (مثل سجل العمليات)."""
        for callback in list(getattr(self, "_refresh_callbacks", [])):
            try:
                callback()
            except tk.TclError:
                # أُغلقت النافذة المسجِّلة، فلا داعي لإبقائها.
                self._refresh_callbacks.remove(callback)
            except Exception as exc:
                log_exception("تحديث نافذة الإدارة", exc)

    def _refresh_linked_data_now(self):
        """Refresh all data-backed pages after any save, edit, or delete."""
        self._run_refresh_callbacks()
        drivers = [d.get("name", "") for d in td.load_drivers() if d.get("name", "")]
        vehicles = [v.get("car_no", "") for v in td.load_vehicles() if v.get("car_no", "")]
        # إعادة بناء كل شاشات الإدخال وقوائم السائق/السيارة فيها، حتى تعكس
        # أي تعديل جديداً فوراً في كل التبويبات المفتوحة لا في الحالية فقط.
        for _tab in list(_ALL_CRUD_TABS):
            _tab.refresh_driver_options()
        refresh_all_registers()
        customers = [c.get("name", "") for c in td.load_customers() if c.get("name", "")]
        companies = [c.get("name", "") for c in td.load_companies() if c.get("name", "")]
        brokers = [c.get("name", "") for c in td.load_customers() if c.get("name", "")]

        def update(combo, values):
            # بعض الحقول مستثناة من النماذج (مثل سائق السيارة)، فيكون الدمج None.
            if combo is None:
                return
            try:
                combo.config(values=values)
            except Exception as _log_exc: log_exception("update", _log_exc)

        if hasattr(self, "vehicles_tab"):
            update(self.vehicles_tab.combos.get("driver"), drivers)
            if getattr(self, "current_page", "") == "entities":
                self.vehicles_tab.refresh()
        if hasattr(self, "drivers_tab"):
            update(self.drivers_tab.combos.get("car_no"), vehicles)
            if getattr(self, "current_page", "") == "entities":
                self.drivers_tab.refresh()
        if hasattr(self, "vehicle_assignments_tab"):
            # تكليفات السائقين وشركاء السيارات يعتمدان قائمتي السيارات والسائقين.
            update(self.vehicle_assignments_tab.combos.get("car_no"), vehicles)
            update(self.vehicle_assignments_tab.combos.get("driver"), drivers)
            if hasattr(self, "vehicle_partners_tab"):
                update(self.vehicle_partners_tab.combos.get("car_no"), vehicles)
            if getattr(self, "current_page", "") == "entities":
                self.vehicle_assignments_tab.refresh()
                if hasattr(self, "vehicle_partners_tab"):
                    self.vehicle_partners_tab.refresh()
        if hasattr(self, "companies_tab"):
            update(self.companies_tab.combos.get("customs_broker"), brokers)
            if getattr(self, "current_page", "") == "entities":
                self.companies_tab.refresh()
        if hasattr(self, "cash_ledger_tab"):
            # الطرف قد يكون عميلاً أو سائقاً أو شركة.
            update(self.cash_ledger_tab.combos.get("party"),
                   customers + drivers + companies)
            if getattr(self, "current_page", "") == "entities":
                self.cash_ledger_tab.refresh()
        if hasattr(self, "quotations_tab"):
            update(self.quotations_tab.combos.get("customer"), customers)
            if getattr(self, "current_page", "") == "entities":
                self.quotations_tab.refresh()
        if hasattr(self, "trips_tab"):
            self.trips_tab.refresh_customers_drivers()
            self.trips_tab.refresh_car_options()
            self.trips_tab.refresh_place_options()
            if getattr(self, "current_page", "") == "trips":
                self.trips_tab.refresh()
            if hasattr(self.trips_tab, "services_tab") and self.trips_tab.services_tab:
                service_customer_combo = self.trips_tab.services_tab.combos.get("customer")
                if service_customer_combo is not None:
                    update(service_customer_combo, [NO_CUSTOMER] + customers)
                service_company_combo = self.trips_tab.services_tab.combos.get("company")
                if service_company_combo is not None:
                    update(service_company_combo, companies)
                if getattr(self, "current_page", "") == "trips":
                    self.trips_tab.services_tab.refresh()
        if hasattr(self, "daily_cars_tab"):
            # كانت هذه الاستدعاءات تمرّر include_summary لملخص قديم حُذف،
            # فكانت ترمي خطأ عند كل تحديث. نستدعي التحديث بلا وسائط الآن.
            if getattr(self, "current_page", "") == "daily_cars":
                self.daily_cars_tab.refresh()
        if getattr(self, "current_page", "") == "invoices":
            # العملاء الجدد/المحذوفون يظهر انعكاسهم في كشوف الحساب فوراً،
            # وقوائم الرحلات غير المفوترة تُحدَّث عند فتح شاشة الفواتير.
            self.refresh_unbilled_lists()
            self.refresh_statement_customers()
            self.refresh_statement_companies()
        if hasattr(self, "sal_driver_combo"):
            update(self.sal_driver_combo, drivers)
            # السيارات والسائقون الجدد يظهرون فوراً في شاشة الرواتب.
            if hasattr(self, "sal_car_combo"):
                update(self.sal_car_combo, vehicles)
            if hasattr(self, "salary_driver_filter_combo"):
                update(self.salary_driver_filter_combo, ["الكل"] + drivers)
            if getattr(self, "current_page", "") == "salaries":
                self.refresh_salary_list()
            # حصر الراتب يعتمد على الرحلات والسيارات؛ نعيد بناءه فوراً إذا كانت
            # شاشة الرواتب مفتوحة، وإلا نؤجّله إلى حين فتحها.
            self.mark_salary_calculator_dirty()
        if getattr(self, "current_page", "") == "home" and hasattr(self, "refresh_home_stats"):
            self.refresh_home_stats()
        if hasattr(self, "partners_notebook"):
            # شاشة الشركاء تعتمد على جداول الشراكات والدفعات والرحلات والمصاريف.
            self.refresh_partner_payments()
            self.refresh_partner_share_matrix()
            if getattr(self, "current_page", "") == "partners":
                self.refresh_partner_vehicle_details()
                self.refresh_driver_accounts()
        if getattr(self, "current_page", "") == "reports" and hasattr(self, "_run_current_report"):
            # خيارات الفلاتر (سائقون/سيارات/عملاء...) تُحدَّث قبل إعادة التشغيل.
            if hasattr(self, "_refresh_report_options"):
                self._refresh_report_options()
            self._run_current_report()

    # ---------------- الشاشة الرئيسية (لوحة سريعة) ----------------
    def _build_home_page(self):
        frame, content = scrollable_pane(self.pages_area)
        home_canvas = frame.canvas
        self.home_frame = content

        welcome = tk.Frame(self.home_frame, bg=COLOR_BG)
        welcome.pack(fill="x", padx=22, pady=(22, 8))
        tk.Label(welcome, text=f"مرحباً بك في {td.COMPANY_NAME_AR}", font=(FONT_NAME, 15, "bold"),
                 bg=COLOR_BG, fg=COLOR_PRIMARY, anchor="e").pack(fill="x")
        tk.Label(welcome, text="ملخص عام لكل وحدات النظام: الرحلات، الفواتير، الدفعات، الصيانة، العقود، الرواتب والمزيد.",
                 font=F_SUBTITLE, bg=COLOR_BG, fg=COLOR_MUTED, anchor="e").pack(fill="x", pady=(4, 0))

        self.stats_wrap = tk.Frame(self.home_frame, bg=COLOR_BG)
        self.stats_wrap.pack(fill="x", padx=22, pady=12)

        # قسم ملخص عام لكل وحدات البرنامج (يُملأ في refresh_home_stats).
        self.home_modules_wrap = tk.Frame(self.home_frame, bg=COLOR_BG)
        self.home_modules_wrap.pack(fill="x", padx=22, pady=(0, 8))

        # قسم تفصيل مصاريف السيارات والمولدات (يُملأ في refresh_home_stats).
        self.home_expenses_wrap = tk.Frame(self.home_frame, bg=COLOR_BG)
        self.home_expenses_wrap.pack(fill="x", padx=22, pady=(0, 8))

        self.home_insights_wrap = tk.Frame(self.home_frame, bg=COLOR_BG)
        self.home_insights_wrap.pack(fill="both", expand=True, padx=22, pady=(0, 8))

        self.home_charts_wrap = tk.Frame(self.home_frame, bg=COLOR_BG)
        self.home_charts_wrap.pack(fill="x", padx=22, pady=(0, 8))

        self.register_page("home", frame, refreshers=[self.refresh_home_stats],
                           canvas=home_canvas)

    def _stat_card(self, parent, title, value, color, icon="📊", empty=False):
        """بطاقة إحصائية مضغوطة: أيقونة وعنوان في سطر، ثم القيمة تحته."""
        outer = tk.Frame(parent, bg=COLOR_SHADOW)
        inner = tk.Frame(outer, bg=COLOR_CARD)
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        # شريط لوني علوي
        bar = tk.Frame(inner, bg=color if not empty else COLOR_BORDER, height=3)
        bar.pack(fill="x")

        body = tk.Frame(inner, bg=COLOR_CARD)
        body.pack(fill="both", expand=True, padx=12, pady=9)

        # الأيقونة والعنوان في سطر واحد لتوفير الارتفاع
        head = tk.Frame(body, bg=COLOR_CARD)
        head.pack(fill="x")
        tk.Label(head, text=icon, font=(FONT_NAME, 10), bg=COLOR_CARD,
                 fg=COLOR_MUTED).pack(side="right", padx=(0, 5))
        tk.Label(head, text=title, font=F_STAT_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED,
                 anchor="e").pack(side="right", fill="x", expand=True)

        # القيمة: خط أصغر يناسب عرض البطاقة حتى لا تُقتطع الأرقام
        tk.Label(body, text=value, font=(FONT_NAME, 15, "bold"), bg=COLOR_CARD,
                 fg=COLOR_MUTED if empty else color,
                 anchor="e").pack(fill="x", pady=(2, 0))

        return outer

    @staticmethod
    def _money_card(value, empty_text="لا يوجد"):
        """بطاقة مبلغ: الأصفار تُعرض كـ«لا يوجد» بدل 0.000.
        العملة تُكتب في العنوان لتبقى القيمة قصيرة فلا تُقتطع."""
        if abs(td.safe_float(value)) < 0.0005:
            return empty_text, True
        return f"{td.safe_float(value):.3f}", False

    def _module_tile(self, parent, icon, title, count, metric, color):
        """مربّع ملخص مصغّر يعرض وحدة من وحدات البرنامج في الشاشة الرئيسية."""
        outer = tk.Frame(parent, bg=COLOR_SHADOW)
        inner = tk.Frame(outer, bg=COLOR_CARD)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        head = tk.Frame(inner, bg=COLOR_CARD)
        head.pack(fill="x", padx=10, pady=(9, 0))
        if icon:
            tk.Label(head, text=icon, font=(FONT_NAME, 12), bg=COLOR_CARD, fg=color).pack(side="right")
        tk.Label(head, text=title, font=F_LABEL, bg=COLOR_CARD, fg=COLOR_TEXT,
                 anchor="e").pack(side="right", fill="x", expand=True, padx=(6, 0))
        tk.Label(inner, text=count, font=(FONT_NAME, 14, "bold"), bg=COLOR_CARD, fg=color,
                 anchor="e").pack(fill="x", padx=10, pady=(3, 0))
        tk.Label(inner, text=metric, font=(FONT_NAME, 8), bg=COLOR_CARD, fg=COLOR_MUTED,
                 anchor="e", wraplength=160).pack(fill="x", padx=10, pady=(0, 9))
        return outer

    def refresh_home_stats(self):
        for w in self.stats_wrap.winfo_children():
            w.destroy()
        for w in self.home_modules_wrap.winfo_children():
            w.destroy()
        for w in self.home_expenses_wrap.winfo_children():
            w.destroy()
        for w in self.home_insights_wrap.winfo_children():
            w.destroy()
        for w in self.home_charts_wrap.winfo_children():
            w.destroy()
        today_iso = date.today().isoformat()
        trips_today = td.trips_for_date(today_iso)
        all_trips = td.load_trips()
        vehicles = td.load_vehicles()
        drivers = td.load_drivers()
        customers = td.load_customers()
        companies = td.load_companies()
        services = td.load_services()
        salaries = td.load_salaries()
        payments = td.load_payments()
        invoices = td.load_invoices()
        daily_expenses = td.load_daily_expenses()
        maintenance_rows = td.load_maintenance()
        maintenance_plans = td.load_maintenance_plans()
        parts = td.load_parts()
        contracts = td.load_contracts()
        quotations = td.load_quotations()
        places = td.load_places()
        cash_rows = td.load_cash_ledger()
        fuel_rows = td.load_fuel()
        assignments = td.load_vehicle_assignments()
        partners = td.load_vehicle_partners()
        internal_today = [t for t in trips_today if t.get("trip_category") == td.TRIP_CATEGORIES[0]]
        intl_today = [t for t in trips_today if t.get("trip_category") == td.TRIP_CATEGORIES[1]]
        summary = td.financial_summary()
        gross_trip_revenue = sum(td.safe_float(t.get("fee")) for t in all_trips)

        cards = [
            ("رحلات اليوم (الكل)", (str(len(trips_today)), False), COLOR_PRIMARY, "🚛"),
            ("شحن داخلي اليوم", (str(len(internal_today)), False), COLOR_PRIMARY_LIGHT, "📦"),
            ("شحن دولي بري اليوم", (str(len(intl_today)), False), COLOR_ACCENT, "🌍"),
            ("عدد السيارات", (str(len(vehicles)), False), COLOR_PRIMARY, "🚗"),
            ("إجمالي إيراد الرحلات د.ك", self._money_card(gross_trip_revenue), COLOR_ACCENT, "💳"),
            ("صافي الربح الإجمالي د.ك", self._money_card(summary["net_profit"]), COLOR_SUCCESS, "💰"),
        ]
        for i, (title, (value, empty), color, icon) in enumerate(cards):
            c = self._stat_card(self.stats_wrap, title, value, color, icon, empty)
            c.grid(row=0, column=len(cards) - 1 - i, padx=8, sticky="ew")
        for i in range(len(cards)):
            self.stats_wrap.grid_columnconfigure(i, weight=1)

        self.stats_wrap.grid_rowconfigure(0, weight=1)

        # مؤشرات الوحدات المالية والتشغيلية التي لم تكن تظهر في الرئيسية سابقاً.
        month_key = today_iso[:7]
        month_payments_total = sum(td.safe_float(p.get("amount")) for p in payments
                                   if str(p.get("date", "")).startswith(month_key))
        month_maintenance_cost = sum(td.safe_float(m.get("cost")) for m in maintenance_rows
                                     if str(m.get("date", "")).startswith(month_key))
        active_contracts = [c for c in contracts if str(c.get("status", "")).strip() == "نشط"]
        contracts_active_value = sum(td.safe_float(c.get("value")) for c in active_contracts)
        open_quotations = [q for q in quotations
                           if str(q.get("status", "")).strip() in ("مسودة", "تم الإرسال")]
        accepted_quotations = [q for q in quotations if str(q.get("status", "")).strip() == "مقبول"]
        cash_balance = {}
        for cash_row in cash_rows:
            account = str(cash_row.get("account", "")).strip() or "نقدي"
            amount = td.safe_float(cash_row.get("amount"))
            if str(cash_row.get("transaction_type", "")).strip() == "صرف":
                amount = -amount
            cash_balance[account] = cash_balance.get(account, 0.0) + amount
        cash_total = sum(cash_balance.values())
        expiring_alerts = [a for a in td.get_alerts(30) if a.get("type") != "صيانة"]

        today_date = date.today()
        horizon_date = date.fromordinal(today_date.toordinal() + 30)

        def _iso_date(value):
            try:
                return date.fromisoformat(str(value).strip())
            except ValueError:
                return None

        plans_pending = [p for p in maintenance_plans if str(p.get("status", "")).strip() != "منجز"]
        plans_due, plans_overdue = [], []
        for plan in plans_pending:
            plan_date = _iso_date(plan.get("due_date"))
            if plan_date and plan_date <= horizon_date:
                plans_due.append(plan)
            if plan_date and plan_date < today_date:
                plans_overdue.append(plan)
        next_plan = min(plans_due, key=lambda p: str(p.get("due_date", ""))) if plans_due else None

        cards2 = [
            ("دفعات هذا الشهر د.ك", self._money_card(month_payments_total), COLOR_SUCCESS, "💵"),
            ("صيانة هذا الشهر د.ك", self._money_card(month_maintenance_cost), COLOR_DANGER, "🛠"),
            ("عقود نشطة", (f"{len(active_contracts)} من {len(contracts)}", False), COLOR_PRIMARY, "📄"),
            ("عروض قيد المتابعة", (str(len(open_quotations)), False), COLOR_ACCENT, "📑"),
            ("رصيد النقد والبنك د.ك", self._money_card(cash_total), COLOR_PRIMARY_LIGHT, "🏦"),
            ("تنبيهات انتهاء (30 يوم)", (str(len(expiring_alerts)), False),
             COLOR_DANGER if expiring_alerts else COLOR_SUCCESS, "⏰"),
        ]
        for i, (title, (value, empty), color, icon) in enumerate(cards2):
            c = self._stat_card(self.stats_wrap, title, value, color, icon, empty)
            c.grid(row=1, column=len(cards2) - 1 - i, padx=8, pady=(8, 0), sticky="ew")

        # لوحة تغطية النظام تُبنى في نهاية التحديث بعد اكتمال كل المؤشرات.

        # مؤشرات تشغيلية تساعد على اتخاذ الإجراء من الصفحة الرئيسية.
        current_month = today_iso[:7]
        month_trips = [t for t in all_trips if str(t.get("date", "")).startswith(current_month)]
        unbilled_trips = [t for t in all_trips if t.get("invoiced") != "نعم"]
        unbilled_value = sum(td.safe_float(t.get("fee")) for t in unbilled_trips)
        unbilled_services = [s for s in td.load_services() if s.get("invoiced") != "نعم"]
        unbilled_services_value = sum(td.safe_float(s.get("total")) for s in unbilled_services)
        unpaid_salaries = [s for s in td.load_salaries() if s.get("paid") != "نعم"]
        month_invoices = [i for i in td.load_invoices() if str(i.get("date", "")).startswith(current_month)]
        month_summary = td.financial_summary(f"{current_month}-01", today_iso)
        profit_margin = ((month_summary["net_profit"] / month_summary["revenue"]) * 100
                         if month_summary["revenue"] else 0.0)
        incomplete_trips = [t for t in all_trips if not str(t.get("driver", "")).strip()
                            or not str(t.get("car_no", "")).strip()]
        active_drivers = {str(t.get("driver", "")).strip() for t in month_trips if str(t.get("driver", "")).strip()}
        active_cars = {str(t.get("car_no", "")).strip() for t in month_trips if str(t.get("car_no", "")).strip()}
        idle_cars = max(0, len(vehicles) - len(active_cars))
        brokers = [c for c in companies if c.get("customs_broker")]
        direct_companies = [c for c in companies if not c.get("customs_broker")]
        def vehicle_has(vehicle, item, legacy_key=None):
            contents = {part.strip() for part in safe_str(vehicle.get("contents", "")).split("،") if part.strip()}
            if contents:
                return item in contents
            return vehicle.get(legacy_key) == "نعم" if legacy_key else False

        generator_cars = [v for v in vehicles if vehicle_has(v, "مولد", "has_generator")]
        no_generator_cars = [v for v in vehicles if not vehicle_has(v, "مولد", "has_generator")]
        non_flatbed_cars = [v for v in vehicles if not vehicle_has(v, "ساطحة", "is_flatbed")]

        receivables_by_debtor = {}
        for trip in all_trips:
            customer = str(trip.get("customer", "")).strip()
            company = str(trip.get("company", "")).strip()
            # المخلص هو المدين عند اختياره، وإلا فالشركة المباشرة هي المدين.
            debtor = company or customer
            if debtor:
                receivables_by_debtor[debtor] = receivables_by_debtor.get(debtor, 0.0) + td.safe_float(trip.get("fee"))
        top_debtor, top_debt = (max(receivables_by_debtor.items(), key=lambda item: item[1])
                                  if receivables_by_debtor else ("لا توجد بيانات", 0.0))

        car_counts = {}
        customer_totals = {}
        for trip in month_trips:
            car_no = str(trip.get("car_no", "")).strip()
            customer = str(trip.get("customer", "")).strip()
            if car_no:
                car_counts[car_no] = car_counts.get(car_no, 0) + 1
            if customer:
                customer_totals[customer] = customer_totals.get(customer, 0) + td.safe_float(trip.get("fee"))
        busiest_car, busiest_count = (max(car_counts.items(), key=lambda item: item[1])
                                      if car_counts else ("لا توجد بيانات", 0))
        top_customer, top_customer_value = (max(customer_totals.items(), key=lambda item: item[1])
                                            if customer_totals else ("لا توجد بيانات", 0.0))

        alerts_box = card_frame(self.home_insights_wrap, "تنبيهات تحتاج إجراء")
        alerts_box.pack(side="right", fill="both", expand=True, padx=(0, 8))
        performance_box = card_frame(self.home_insights_wrap, "مؤشرات الأداء لهذا الشهر")
        performance_box.pack(side="left", fill="both", expand=True, padx=(8, 0))

        def add_insight(parent, icon, title, value, detail, color):
            row = tk.Frame(parent, bg=COLOR_CARD)
            row.pack(fill="x", padx=16, pady=7)
            tk.Label(row, text=icon, font=(FONT_NAME, 16), bg=COLOR_CARD, fg=color).pack(side="right", padx=(0, 10))
            text_wrap = tk.Frame(row, bg=COLOR_CARD)
            text_wrap.pack(side="right", fill="x", expand=True)
            tk.Label(text_wrap, text=title, font=F_LABEL, bg=COLOR_CARD, fg=COLOR_TEXT,
                     anchor="e").pack(fill="x")
            tk.Label(text_wrap, text=detail, font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED,
                     anchor="e").pack(fill="x", pady=(2, 0))
            tk.Label(row, text=value, font=(FONT_NAME, 12, "bold"), bg=COLOR_CARD, fg=color,
                     anchor="w").pack(side="left")

        add_insight(alerts_box.body, "🧾", "رحلات غير مفوترة", str(len(unbilled_trips)),
                    f"قيمة قابلة للفوترة: {unbilled_value:.3f} د.ك", COLOR_DANGER if unbilled_trips else COLOR_SUCCESS)
        add_insight(alerts_box.body, "⚠", "سجلات تحتاج استكمال", str(len(incomplete_trips)),
                    "رحلات بلا سائق أو رقم سيارة", COLOR_DANGER if incomplete_trips else COLOR_SUCCESS)
        add_insight(alerts_box.body, "📅", "نشاط اليوم", str(len(trips_today)),
                    "لا توجد رحلات مسجلة اليوم" if not trips_today else "الرحلات المسجلة لهذا اليوم", COLOR_ACCENT)
        add_insight(alerts_box.body, "🛠", "خدمات غير مفوترة", str(len(unbilled_services)),
                    f"قيمة قابلة للفوترة: {unbilled_services_value:.3f} د.ك",
                    COLOR_DANGER if unbilled_services else COLOR_SUCCESS)
        add_insight(alerts_box.body, "💳", "رواتب بانتظار الدفع", str(len(unpaid_salaries)),
                    f"إجمالي مستحق: {sum(td.safe_float(s.get('net_salary')) for s in unpaid_salaries):.3f} د.ك",
                    COLOR_ACCENT if unpaid_salaries else COLOR_SUCCESS)
        add_insight(alerts_box.body, "🚗", "سيارات بلا نشاط شهري", str(idle_cars),
                    f"سيارات نشطة: {len(active_cars)} من {len(vehicles)}",
                    COLOR_ACCENT if idle_cars else COLOR_SUCCESS)
        add_insight(alerts_box.body, "💳", "ذمم الرحلات قبل التحصيل", f"{gross_trip_revenue:.3f} د.ك",
                    f"أعلى مدين: {top_debtor} ({top_debt:.3f} د.ك)", COLOR_DANGER if gross_trip_revenue else COLOR_SUCCESS)
        add_insight(alerts_box.body, "📅", "مواعيد صيانة مستحقة", str(len(plans_due)),
                    (f"متأخرة: {len(plans_overdue)} | أقرب: {next_plan.get('car_no', '')} بتاريخ {next_plan.get('due_date', '')}"
                     if next_plan else "لا توجد مواعيد صيانة خلال 30 يوماً"),
                    COLOR_DANGER if plans_overdue else (COLOR_ACCENT if plans_due else COLOR_SUCCESS))
        nearest_expiry = (min(expiring_alerts, key=lambda a: str(a.get("date", "")))
                          if expiring_alerts else None)
        add_insight(alerts_box.body, "⏰", "تراخيص وتكليفات تنتهي قريباً", str(len(expiring_alerts)),
                    (f"أقرب: {nearest_expiry.get('type', '')} - {nearest_expiry.get('item', '')} ({nearest_expiry.get('date', '')})"
                     if nearest_expiry else "لا توجد تنبيهات خلال 30 يوماً"),
                    COLOR_DANGER if expiring_alerts else COLOR_SUCCESS)

        add_insight(performance_box.body, "🚛", "رحلات الشهر", str(len(month_trips)),
                    f"قيمة الرحلات: {sum(td.safe_float(t.get('fee')) for t in month_trips):.3f} د.ك", COLOR_PRIMARY)
        add_insight(performance_box.body, "🚗", "السيارة الأكثر نشاطاً", str(busiest_count),
                    busiest_car, COLOR_PRIMARY_LIGHT)
        add_insight(performance_box.body, "👥", "العميل الأعلى قيمة", f"{top_customer_value:.3f} د.ك",
                    top_customer, COLOR_SUCCESS)
        add_insight(performance_box.body, "🧾", "فواتير الشهر", str(len(month_invoices)),
                    f"إيرادات مفوترة: {month_summary['revenue']:.3f} د.ك", COLOR_PRIMARY)
        add_insight(performance_box.body, "📉", "مصروفات الشهر", f"{month_summary['expenses']:.3f} د.ك",
                    f"صافي الربح: {month_summary['net_profit']:.3f} د.ك", COLOR_DANGER)
        add_insight(performance_box.body, "📊", "هامش الربح الشهري", f"{profit_margin:.1f}%",
                    "نسبة صافي الربح إلى الإيرادات المفوترة", COLOR_SUCCESS if profit_margin >= 0 else COLOR_DANGER)
        add_insight(performance_box.body, "👤", "السائقون النشطون", str(len(active_drivers)),
                    "سائقون لديهم رحلة مسجلة هذا الشهر", COLOR_PRIMARY_LIGHT)
        add_insight(performance_box.body, "👥", "السائقون المسجلون", str(len(drivers)),
                    f"المخلصون: {len(brokers)} | الشركات المباشرة: {len(direct_companies)}", COLOR_PRIMARY)
        add_insight(performance_box.body, "🏢", "الشركات المسجلة", str(len(companies)),
                    "سجل الشركات المستقل", COLOR_PRIMARY_LIGHT)
        add_insight(performance_box.body, "🚚", "السيارات العاملة", str(len(active_cars)),
                    f"المتوقفة هذا الشهر: {idle_cars}", COLOR_SUCCESS)
        add_insight(performance_box.body, "⚙", "سيارات تحتوي مولد", str(len(generator_cars)),
                    f"بدون مولد: {len(no_generator_cars)}", COLOR_ACCENT)
        add_insight(performance_box.body, "🚛", "سيارات بدون ساطحة", str(len(non_flatbed_cars)),
                    f"سيارات ساطحة: {len(vehicles) - len(non_flatbed_cars)}", COLOR_PRIMARY)

        # استهلاك الديزل خلال الشهر من سجل التزود (الوقود في التطبيق يسمى ديزل).
        month_fuel_rows = [f for f in fuel_rows if str(f.get("date", "")).startswith(current_month)]
        month_fuel_liters = sum(td.safe_float(f.get("liters")) for f in month_fuel_rows)
        month_fuel_cost = sum(td.safe_float(f.get("total")) for f in month_fuel_rows)
        add_insight(performance_box.body, "⛽", "استهلاك الديزل (الشهر)",
                    f"{month_fuel_liters:.1f} لتر",
                    f"تكلفة: {month_fuel_cost:.3f} د.ك | عدد التزود: {len(month_fuel_rows)}",
                    COLOR_DANGER if month_fuel_rows else COLOR_MUTED)

        # ---------- تفصيل مصاريف السيارات والمولدات: ديزل / زيت / صيانة / قطع غيار ----------
        month_daily = [e for e in daily_expenses if str(e.get("date", "")).startswith(month_key)]
        month_maint_rows = [m for m in maintenance_rows if str(m.get("date", "")).startswith(month_key)]
        month_parts_rows = [p for p in parts if str(p.get("install_date", "")).startswith(month_key)]

        def _sum_rows(rows, amount_key, predicate):
            return sum(td.safe_float(r.get(amount_key)) for r in rows if predicate(r))

        def _daily_sum(rows, exact=None, groups=None):
            def _match(expense):
                category = str(expense.get("category", "")).strip()
                if exact and category in exact:
                    return True
                if groups and category in groups and td.daily_expense_owner(expense) == "سيارة":
                    return True
                return False
            return _sum_rows(rows, "amount", _match)

        car_maint_cats = {"زجاج أمامي", "صيانة كهرباء", "صيانة تكييف", "بطارية السيارة",
                          "صيانة عامة", "لحام السيارة", "أخرى"}
        gen_maint_cats = {"بطارية المولد", "صيانة المولد", "لحام المولد"}
        gen_parts_rows = [p for p in parts if "مولد" in str(p.get("part_type", ""))]
        all_car_parts_rows = [p for p in parts if "مولد" not in str(p.get("part_type", ""))]
        month_gen_parts_rows = [p for p in month_parts_rows if "مولد" in str(p.get("part_type", ""))]
        month_car_parts_rows = [p for p in month_parts_rows if "مولد" not in str(p.get("part_type", ""))]

        def car_diesel_of(daily, maint, trips):
            """ديزل السيارات: المصاريف اليومية + سجل الصيانة + مصاريف الرحلات."""
            return (_daily_sum(daily, exact={"ديزل السيارة"})
                    + _sum_rows(maint, "cost", lambda m: "ديزل" in str(m.get("type", "")))
                    + _sum_rows(trips, "car_expense_amount",
                                lambda t: "ديزل" in str(t.get("car_expense_type", ""))))

        def car_oil_of(daily, maint):
            return (_daily_sum(daily, exact={"زيت السيارة"})
                    + _sum_rows(maint, "cost", lambda m: str(m.get("type", "")).strip() == "زيت"))

        def car_maint_of(daily, maint):
            return (_daily_sum(daily, groups=car_maint_cats)
                    + _sum_rows(maint, "cost",
                                lambda m: str(m.get("type", "")).strip() in ("صيانة عامة", "أخرى")))

        def car_parts_of(daily, maint, parts_rows):
            return (_daily_sum(daily, exact={"إطارات السيارة"})
                    + _sum_rows(maint, "cost", lambda m: str(m.get("type", "")).strip() == "إطارات")
                    + _sum_rows(parts_rows, "cost", lambda p: True))

        car_diesel_month = car_diesel_of(month_daily, month_maint_rows, month_trips)
        car_diesel_total = car_diesel_of(daily_expenses, maintenance_rows, all_trips)
        car_oil_month = car_oil_of(month_daily, month_maint_rows)
        car_oil_total = car_oil_of(daily_expenses, maintenance_rows)
        car_maint_month = car_maint_of(month_daily, month_maint_rows)
        car_maint_total = car_maint_of(daily_expenses, maintenance_rows)
        car_parts_month = car_parts_of(month_daily, month_maint_rows, month_car_parts_rows)
        car_parts_total = car_parts_of(daily_expenses, maintenance_rows, all_car_parts_rows)

        gen_diesel_month = _daily_sum(month_daily, exact={"ديزل المولد"})
        gen_diesel_total = _daily_sum(daily_expenses, exact={"ديزل المولد"})
        gen_oil_month = _daily_sum(month_daily, exact={"زيت المولد"})
        gen_oil_total = _daily_sum(daily_expenses, exact={"زيت المولد"})
        gen_maint_month = _daily_sum(month_daily, groups=gen_maint_cats)
        gen_maint_total = _daily_sum(daily_expenses, groups=gen_maint_cats)
        gen_parts_month = _sum_rows(month_gen_parts_rows, "cost", lambda p: True)
        gen_parts_total = _sum_rows(gen_parts_rows, "cost", lambda p: True)

        expense_box = card_frame(self.home_expenses_wrap, "تفصيل مصاريف السيارات والمولدات")
        expense_box.pack(fill="x")
        expense_cols = tk.Frame(expense_box.body, bg=COLOR_CARD)
        expense_cols.pack(fill="both", expand=True, padx=8, pady=(0, 12))
        cars_exp_box = card_frame(expense_cols, "مصاريف السيارات")
        cars_exp_box.pack(side="right", fill="both", expand=True, padx=(6, 0))
        gens_exp_box = card_frame(expense_cols, "مصاريف المولدات")
        gens_exp_box.pack(side="left", fill="both", expand=True, padx=(0, 6))

        add_insight(cars_exp_box.body, "⛽", "ديزل السيارات", f"{car_diesel_month:.3f} د.ك",
                    f"الإجمالي: {car_diesel_total:.3f} د.ك", COLOR_PRIMARY)
        add_insight(cars_exp_box.body, "🛢", "زيت السيارات", f"{car_oil_month:.3f} د.ك",
                    f"الإجمالي: {car_oil_total:.3f} د.ك", COLOR_PRIMARY_LIGHT)
        add_insight(cars_exp_box.body, "🛠", "مصاريف صيانة", f"{car_maint_month:.3f} د.ك",
                    f"الإجمالي: {car_maint_total:.3f} د.ك", COLOR_ACCENT)
        add_insight(cars_exp_box.body, "⚙", "قطع غيار وإطارات", f"{car_parts_month:.3f} د.ك",
                    f"الإجمالي: {car_parts_total:.3f} د.ك", COLOR_DANGER)
        add_insight(cars_exp_box.body, "🧮", "إجمالي مصاريف السيارات",
                    f"{car_diesel_month + car_oil_month + car_maint_month + car_parts_month:.3f} د.ك",
                    "مجموع البنود الأربعة لهذا الشهر", COLOR_TEXT)

        add_insight(gens_exp_box.body, "⛽", "ديزل المولدات", f"{gen_diesel_month:.3f} د.ك",
                    f"الإجمالي: {gen_diesel_total:.3f} د.ك", COLOR_PRIMARY)
        add_insight(gens_exp_box.body, "🛢", "زيت المولدات", f"{gen_oil_month:.3f} د.ك",
                    f"الإجمالي: {gen_oil_total:.3f} د.ك", COLOR_PRIMARY_LIGHT)
        add_insight(gens_exp_box.body, "🛠", "صيانة المولد", f"{gen_maint_month:.3f} د.ك",
                    f"الإجمالي: {gen_maint_total:.3f} د.ك", COLOR_ACCENT)
        add_insight(gens_exp_box.body, "⚙", "قطع غيار المولد", f"{gen_parts_month:.3f} د.ك",
                    f"الإجمالي: {gen_parts_total:.3f} د.ك", COLOR_DANGER)
        add_insight(gens_exp_box.body, "🧮", "إجمالي مصاريف المولدات",
                    f"{gen_diesel_month + gen_oil_month + gen_maint_month + gen_parts_month:.3f} د.ك",
                    "مجموع البنود الأربعة لهذا الشهر", COLOR_TEXT)
        # ---------- لوحة موحّدة لكل وحدات النظام (بدون تكرار) ----------
        # القيم المشتقّة (unbilled_trips / plans_due / idle_cars / generator_cars
        # / brokers) معرَّفة أعلاه وتُستخدَم هنا كما هي دون إعادة حساب.
        invoices_total = sum(td.safe_float(i.get("total")) for i in invoices)
        payments_total = sum(td.safe_float(p.get("amount")) for p in payments)
        services_total = sum(td.safe_float(s.get("total")) for s in services)
        salaries_total = sum(td.safe_float(s.get("net_salary")) for s in salaries)
        daily_total = sum(td.safe_float(e.get("amount")) for e in daily_expenses)
        maintenance_total = sum(td.safe_float(m.get("cost")) for m in maintenance_rows)
        parts_total = sum(td.safe_float(pt.get("cost")) for pt in parts)
        fuel_total = sum(td.safe_float(f.get("total")) for f in fuel_rows)
        fuel_liters = sum(td.safe_float(f.get("liters")) for f in fuel_rows)
        local_places = [p for p in places if str(p.get("type", "")).strip() == "محلي"]
        intl_places = [p for p in places if str(p.get("type", "")).strip() == "دولي"]

        def _open_payments(rows):
            """صافي الدفعات غير المشطوبة: المدين ناقص الدائن."""
            total = 0.0
            for row in rows:
                if td.is_voided(row):
                    continue
                amount = td.safe_float(row.get("amount"))
                total += amount if str(row.get("payment_type", "")).strip() == "مدين" else -amount
            return total

        partner_payments = td.load_partner_payments()
        driver_payments = td.load_driver_payments()
        partner_open = _open_payments(partner_payments)
        driver_open = _open_payments(driver_payments)
        partner_profit = td.partner_profit_report()
        voided_payments = sum(1 for p in partner_payments if td.is_voided(p)) \
            + sum(1 for p in driver_payments if td.is_voided(p))
        internal_drivers = [d for d in drivers
                            if str(d.get("driver_type", "")).strip() == "داخلي"]
        external_drivers = [d for d in drivers
                            if str(d.get("driver_type", "")).strip() == "خارجي"]
        partner_cars = {str(p.get("car_no", "")).strip() for p in partners
                        if str(p.get("car_no", "")).strip()}

        # كل رقم يظهر في مكان واحد فقط داخل هذه اللوحة.
        domains = [
            ("🚛", "التشغيل اليومي", COLOR_PRIMARY, [
                ("الرحلات", len(all_trips), f"اليوم {len(trips_today)} · غير مفوترة {len(unbilled_trips)}"),
                ("السائقون", len(drivers),
                 f"داخلي {len(internal_drivers)} · خارجي {len(external_drivers)}"),
                ("السيارات", len(vehicles), f"بمولد {len(generator_cars)} · متوقفة {idle_cars}"),
                ("تكليفات السائقين", len(assignments), "ربط السائقين بالسيارات"),
                ("الخدمات", len(services), f"بقيمة {services_total:.3f} د.ك"),
            ]),
            ("💰", "المالية والتحصيل", COLOR_SUCCESS, [
                ("الفواتير", len(invoices), f"بقيمة {invoices_total:.3f} د.ك"),
                ("دفعات العملاء", len(payments), f"محصّل {payments_total:.3f} د.ك"),
                ("الرواتب", len(salaries), f"صافي {salaries_total:.3f} د.ك"),
                ("النقد والبنك", len(cash_rows),
                 f"نقدي {cash_balance.get('نقدي', 0.0):.3f} · بنك {cash_balance.get('بنك', 0.0):.3f}"),
            ]),
            ("🤝", "الشراكة والسائقون", COLOR_ACCENT, [
                ("شركاء السيارات", len(partners), f"تغطي {len(partner_cars)} سيارة"),
                ("حصص الشركاء", f"{partner_profit['total']:.3f}",
                 f"د.ك لـ {len(partner_profit['by_partner'])} شريك"),
                ("دفعات الشركاء", len(partner_payments), f"صافي مفتوح {partner_open:.3f} د.ك"),
                ("دفعات السائقين", len(driver_payments), f"صافي مفتوح {driver_open:.3f} د.ك"),
            ]),
            ("🔧", "الأسطول والصيانة", COLOR_DANGER, [
                ("المصاريف اليومية", len(daily_expenses), f"بقيمة {daily_total:.3f} د.ك"),
                ("سجل الصيانة", len(maintenance_rows), f"تكلفة {maintenance_total:.3f} د.ك"),
                ("خطط الصيانة", len(maintenance_plans),
                 f"مستحقة {len(plans_due)} · متأخرة {len(plans_overdue)}"),
                ("قطع الغيار", len(parts), f"تكلفة {parts_total:.3f} د.ك"),
                ("الوقود", len(fuel_rows),
                 f"{fuel_liters:.1f} لتر · {fuel_total:.3f} د.ك"),
            ]),
            ("📋", "الإدارة والأطراف", COLOR_PRIMARY_LIGHT, [
                ("العملاء والشركات", f"{len(customers)} / {len(companies)}",
                 f"مخلصون {len(brokers)}"),
                ("العقود", len(contracts), f"نشطة {len(active_contracts)}"),
                ("عروض الأسعار", len(quotations), f"مقبولة {len(accepted_quotations)}"),
                ("أماكن التحميل", len(places),
                 f"محلي {len(local_places)} · دولي {len(intl_places)}"),
            ]),
        ]

        modules_box = card_frame(self.home_modules_wrap, "وحدات النظام — كل الأرقام في مكان واحد")
        modules_box.pack(fill="x")
        for title, icon, color, tiles in domains:
            section = tk.Frame(modules_box.body, bg=COLOR_CARD)
            section.pack(fill="x", padx=16, pady=(10, 0))
            head = tk.Frame(section, bg=COLOR_CARD)
            head.pack(fill="x")
            tk.Frame(head, bg=color, width=4, height=15).pack(side="right", fill="y", padx=(8, 0))
            tk.Label(head, text=f"{icon}  {title}", font=F_LABEL, bg=COLOR_CARD,
                     fg=color, anchor="e").pack(side="right")
            row = tk.Frame(section, bg=COLOR_CARD)
            row.pack(fill="x", pady=(7, 12))
            for tile_index, (name, value, metric) in enumerate(tiles):
                self._module_tile(row, "", name, str(value), metric, color).grid(
                    row=0, column=len(tiles) - 1 - tile_index, padx=5, sticky="nsew")
            for column in range(len(tiles)):
                row.grid_columnconfigure(column, weight=1)

        totals_line = tk.Label(
            modules_box.body,
            text=(f"تنبيهات تحتاج إجراء: {len(expiring_alerts)} · "
                  f"دفعات مشطوبة: {voided_payments} · "
                  f"سيارات بلا رحلات هذا الشهر: {idle_cars}"),
            font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED, anchor="e")
        totals_line.pack(fill="x", padx=16, pady=(2, 14))

        charts_box = card_frame(self.home_charts_wrap, "رسوم تحليلية")
        charts_box.pack(fill="x")
        charts_row = tk.Frame(charts_box.body, bg=COLOR_CARD)
        charts_row.pack(fill="x", padx=18, pady=(0, 16))

        trend_frame = tk.Frame(charts_row, bg=COLOR_CARD)
        trend_frame.pack(side="right", fill="both", expand=True, padx=(0, 8))
        tk.Label(trend_frame, text="قيمة الرحلات — آخر 6 أشهر", font=F_H2,
                 bg=COLOR_CARD, fg=COLOR_TEXT, anchor="e").pack(fill="x", pady=(0, 6))
        trend_chart = tk.Canvas(trend_frame, height=230, bg=COLOR_CARD, highlightthickness=1,
                                highlightbackground=COLOR_BORDER)
        trend_chart.pack(fill="both", expand=True)

        mix_frame = tk.Frame(charts_row, bg=COLOR_CARD)
        mix_frame.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(mix_frame, text="توزيع أنواع الرحلات — هذا الشهر", font=F_H2,
                 bg=COLOR_CARD, fg=COLOR_TEXT, anchor="e").pack(fill="x", pady=(0, 6))
        mix_chart = tk.Canvas(mix_frame, height=230, bg=COLOR_CARD, highlightthickness=1,
                              highlightbackground=COLOR_BORDER)
        mix_chart.pack(fill="both", expand=True)

        month_keys = []
        year, month = date.today().year, date.today().month
        for offset in range(5, -1, -1):
            m = month - offset
            y = year
            while m <= 0:
                m += 12
                y -= 1
            month_keys.append(f"{y:04d}-{m:02d}")
        # لوحة موحّدة لكل وحدات النظام، موزّعة على مجالات بدل تكرار الأرقام.
        trend_values = [sum(td.safe_float(t.get("fee")) for t in all_trips
                            if str(t.get("date", "")).startswith(key)) for key in month_keys]
        category_values = [sum(1 for t in month_trips if t.get("trip_category") == category)
                           for category in td.TRIP_CATEGORIES]

        def draw_charts():
            trend_chart.delete("all")
            width = max(trend_chart.winfo_width(), 320)
            height = 230
            left, right, top, bottom = 42, 18, 18, 38
            max_value = max(trend_values) if any(trend_values) else 1
            chart_width = width - left - right
            bar_width = max(18, chart_width / (len(trend_values) * 1.7))
            for index, value in enumerate(trend_values):
                x = left + (index + 0.5) * chart_width / len(trend_values)
                bar_height = (value / max_value) * (height - top - bottom)
                trend_chart.create_rectangle(x - bar_width / 2, height - bottom - bar_height,
                                             x + bar_width / 2, height - bottom,
                                             fill=COLOR_PRIMARY_LIGHT, outline="")
                trend_chart.create_text(x, height - 18, text=month_keys[index][5:],
                                        font=(FONT_NAME, 8), fill=COLOR_MUTED)
                trend_chart.create_text(x, height - bottom - bar_height - 9, text=f"{value:.0f}",
                                        font=(FONT_NAME, 8), fill=COLOR_TEXT)
            trend_chart.create_line(left, height - bottom, width - right, height - bottom, fill=COLOR_BORDER)

            mix_chart.delete("all")
            total = sum(category_values)
            colors = [COLOR_PRIMARY, COLOR_ACCENT, COLOR_SUCCESS]
            labels = ["داخلي", "دولي", "ضرب فله"]
            if total:
                start = 0
                for index, value in enumerate(category_values):
                    extent = (value / total) * 360
                    mix_chart.create_arc(35, 20, 190, 175, start=start, extent=extent,
                                         fill=colors[index], outline=COLOR_CARD)
                    start += extent
                    mix_chart.create_rectangle(220, 38 + index * 36, 234, 52 + index * 36,
                                               fill=colors[index], outline="")
                    mix_chart.create_text(242, 45 + index * 36, text=f"{labels[index]}: {value}",
                                           anchor="w", font=(FONT_NAME, 9), fill=COLOR_TEXT)
            else:
                mix_chart.create_text(160, 105, text="لا توجد رحلات مسجلة لهذا الشهر",
                                      font=F_BODY, fill=COLOR_MUTED)

        trend_chart.after_idle(draw_charts)
        mix_chart.after_idle(draw_charts)

        shortcuts = card_frame(self.home_frame, "اختصارات سريعة")
        for old in getattr(self, "_home_shortcuts", []):
            old.destroy()
        shortcuts.pack(fill="x", padx=22, pady=12)
        self._home_shortcuts = [shortcuts]
        row = tk.Frame(shortcuts.body, bg=COLOR_CARD)
        row.pack(fill="x", padx=18, pady=16, anchor="e")
        make_btn(row, "إضافة رحلة يومية", lambda: self.show_page("trips"), variant="accent").pack(side="right", padx=6)
        make_btn(row, "يومية السيارات", lambda: self.show_page("daily_cars"), variant="secondary").pack(side="right", padx=6)
        make_btn(row, "عرض الفواتير", lambda: self.show_page("invoices"), variant="secondary").pack(side="right", padx=6)
        make_btn(row, "التقارير", lambda: self.show_page("reports"), variant="secondary").pack(side="right", padx=6)
        make_btn(row, "البيانات الأساسية", lambda: self.show_page("entities"), variant="secondary").pack(side="right", padx=6)
