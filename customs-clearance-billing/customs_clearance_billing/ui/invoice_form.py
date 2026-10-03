# -*- coding: utf-8 -*-
"""نافذة إضافة / تعديل فاتورة."""

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from ..config import get_tk_font
from ..constants import META_FIELDS, SERVICE_ITEMS
from ..data import (
    SaveError, load_customers, load_invoices, next_invoice_number, save_invoice,
)
from ..utils import english_currency_words, fmt_fils3, safe_int
from .theme import (
    COL_BG, COL_BORDER, COL_CARD, COL_CARD_SOFT, COL_NAVY, COL_SUBTEXT, COL_TEXT,
)
from .widgets import build_date_field

if TYPE_CHECKING:  # استيراد نوعي فقط، لتفادي الاستيراد الدائري بين app و invoice_form
    from .app import InvoiceApp


class InvoiceForm(tk.Toplevel):
    """نافذة إضافة / تعديل فاتورة."""

    def __init__(self, app: "InvoiceApp", invoice=None):
        super().__init__(app)
        self.app = app
        self.editing_invno = invoice["invno"] if invoice else None
        self.title("تعديل فاتورة" if invoice else "فاتورة جديدة")
        self.geometry("980x760")
        self.minsize(760, 600)
        self.configure(bg=COL_BG)
        self.transient(app)
        self.grab_set()
        self.lift()
        self.focus_force()

        # ---- منطقة قابلة للتمرير ----
        container = tk.Frame(self, bg=COL_BG)
        container.pack(fill="both", expand=True)
        canvas = tk.Canvas(container, highlightthickness=0, bg=COL_BG)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=COL_BG)
        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._form_canvas = canvas
        self._form_scroll_frame = self.scroll_frame
        self._scroll_anim_id = None

        # ---- عجلة الفأرة: ربط متوافق مع Windows / macOS / Linux ----
        # نربطها على النافذة (self) لا على كامل التطبيق (bind_all)، لأن
        # وسم الربط "toplevel" هو أحد الوسوم الافتراضية لكل عنصر فرعي داخل
        # هذه النافذة تلقائياً، فتصل الأحداث من أي حقل بداخلها دون أن يؤثر
        # الربط على النوافذ الأخرى أو يسبب أخطاء بعد إغلاق هذه النافذة.
        try:
            windowing_system = self.tk.call("tk", "windowingsystem")
        except tk.TclError:
            windowing_system = "win32"

        def _on_mousewheel_windows(event):
            self._cancel_scroll_animation()
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_mac(event):
            self._cancel_scroll_animation()
            canvas.yview_scroll(int(-1 * event.delta), "units")

        def _on_mousewheel_linux(event):
            self._cancel_scroll_animation()
            canvas.yview_scroll(-1 if event.num == 4 else 1, "units")

        if windowing_system == "x11":
            # لينكس لا يرسل حدث <MouseWheel> بل أزراراً افتراضية 4/5
            self.bind("<Button-4>", _on_mousewheel_linux)
            self.bind("<Button-5>", _on_mousewheel_linux)
        elif windowing_system == "aqua":
            self.bind("<MouseWheel>", _on_mousewheel_mac)
        else:
            self.bind("<MouseWheel>", _on_mousewheel_windows)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.vars = {}
        self._build_meta_section(invoice)
        self._build_items_section(invoice)
        self._build_notes_and_actions(invoice)

    def _bind_widget_autoscroll(self, widget):
        widget.bind("<FocusIn>", self._on_widget_focus_in)

    def _on_widget_focus_in(self, event):
        widget = event.widget
        self.after_idle(lambda w=widget: self._ensure_widget_visible(w))

    def _ensure_widget_visible(self, widget):
        """يمرّر تلقائياً وبحركة سلسة حتى يظهر الحقل الذي حصل على التركيز
        كاملاً ضمن منطقة الرؤية، مع هامش مريح أعلى وأسفل"""
        if not widget or not widget.winfo_exists():
            return
        canvas = getattr(self, "_form_canvas", None)
        if canvas is None or not canvas.winfo_exists() or not canvas.winfo_ismapped():
            return
        try:
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if not bbox:
                return
            scroll_height = max(1, int(bbox[3] - bbox[1]))
            view_height = canvas.winfo_height()
            widget_top = widget.winfo_rooty() - canvas.winfo_rooty() + int(canvas.yview()[0] * scroll_height)
            widget_bottom = widget_top + max(widget.winfo_reqheight(), widget.winfo_height())
            view_top = canvas.yview()[0] * scroll_height
            view_bottom = view_top + view_height
            padding = 24

            target = None
            if widget_bottom > view_bottom - padding:
                target = (widget_bottom + padding - view_height) / scroll_height
            elif widget_top < view_top + padding:
                target = (widget_top - padding) / scroll_height

            if target is not None:
                self._animate_scroll_to(canvas, max(0.0, min(1.0, target)))
        except tk.TclError:
            return

    def _cancel_scroll_animation(self):
        anim_id = getattr(self, "_scroll_anim_id", None)
        if anim_id:
            try:
                self.after_cancel(anim_id)
            except tk.TclError:
                pass
            self._scroll_anim_id = None

    def _animate_scroll_to(self, canvas, target_fraction, duration_ms=180, steps=12):
        """تمرير سلس (ease-out) نحو target_fraction بدلاً من القفز المباشر،
        بحيث يشعر المستخدم بحركة طبيعية عند الانتقال بين الحقول بمفتاح Tab
        أو عند النقر على حقل خارج نطاق الرؤية الحالي"""
        self._cancel_scroll_animation()
        start_fraction = canvas.yview()[0]
        distance = target_fraction - start_fraction
        if abs(distance) < 0.0015:
            canvas.yview_moveto(target_fraction)
            return

        interval = max(8, duration_ms // steps)

        def ease_out_cubic(t):
            return 1 - (1 - t) ** 3

        def step(i=0):
            if not canvas.winfo_exists():
                self._scroll_anim_id = None
                return
            t = min(1.0, (i + 1) / steps)
            canvas.yview_moveto(start_fraction + distance * ease_out_cubic(t))
            if t < 1.0:
                self._scroll_anim_id = self.after(interval, lambda: step(i + 1))
            else:
                self._scroll_anim_id = None

        step()

    def _on_close(self):
        self._cancel_scroll_animation()
        self.destroy()

    def _build_meta_section(self, invoice):
        card = tk.Frame(self.scroll_frame, bg=COL_CARD, bd=1, relief="solid")
        card.pack(fill="x", padx=10, pady=(10, 8))

        header = tk.Frame(card, bg=COL_CARD)
        header.pack(fill="x", padx=14, pady=(12, 8))
        tk.Label(header, text="البيانات الأساسية وتفاصيل الشحنة",
                 bg=COL_CARD, fg=COL_NAVY, font=get_tk_font(10, "bold")).pack(side="right")
        tk.Label(header, text="أدخل البيانات الأساسية ثم عدّل بنود الخدمة والأرقام مباشرة قبل الحفظ",
                 bg=COL_CARD, fg=COL_SUBTEXT, font=get_tk_font(8)).pack(side="right", padx=(10, 0))

        fields = tk.Frame(card, bg=COL_CARD)
        fields.pack(fill="x", padx=12, pady=(0, 10))
        cols_per_row = 3
        field_labels = {key: label for key, label in META_FIELDS}
        field_rows = [
            ("invno", "date", "customer"),
            ("declno", "decldate", "port"),
            ("containercount", "goodstype", "origin"),
        ]

        for row_idx, row_keys in enumerate(field_rows):
            for col_idx, key in enumerate(row_keys):
                frame = tk.Frame(fields, bg=COL_CARD)
                frame.grid(row=row_idx, column=col_idx, padx=8, pady=6, sticky="ew")
                tk.Label(frame, text=field_labels[key], bg=COL_CARD, fg=COL_TEXT, font=get_tk_font(9)).pack(anchor="e")
                var = tk.StringVar(value=(invoice.get(key, "") if invoice else self._default_for(key)))

                if key == "customer":
                    entry = ttk.Combobox(
                        frame,
                        textvariable=var,
                        values=self.app.all_customer_names(),
                        font=get_tk_font(10),
                        justify="right",
                        style="TCombobox"
                    )
                    entry.configure(postcommand=lambda cb=entry: cb.configure(values=self.app.all_customer_names()))
                    entry.bind("<<ComboboxSelected>>", self._update_invno_for_customer)
                    entry.bind("<FocusOut>", self._update_invno_for_customer)
                    var.trace_add("write", lambda *a: self._update_invno_for_customer())
                    entry.pack(fill="x")
                elif key in ("date", "decldate"):
                    date_row, entry = build_date_field(frame, var)
                    date_row.pack(fill="x")
                else:
                    entry = ttk.Entry(
                        frame,
                        textvariable=var,
                        font=get_tk_font(10),
                        justify="right",
                        style="Flat.TEntry"
                    )
                    entry.pack(fill="x")

                self._bind_widget_autoscroll(entry)
                self.vars[key] = var
        for c in range(cols_per_row):
            fields.grid_columnconfigure(c, weight=1)

        tk.Label(card, text="رقم الفاتورة يتولد تلقائياً (رمز الشركة + رقم تسلسلي) بعد اختيار العميل، ويمكن تعديله يدوياً عند الحاجة",
                 bg=COL_CARD, fg="#888", font=get_tk_font(8)).pack(anchor="e", padx=14, pady=(0, 12))

    def _update_invno_for_customer(self, event=None):
        # لا نغيّر رقم فاتورة موجودة مسبقاً عند التعديل
        if self.editing_invno is not None:
            return
        customer_name = self.vars["customer"].get().strip()
        if not customer_name:
            return
        customers = {c["name"]: c for c in load_customers()}
        c = customers.get(customer_name)
        if not c or not c.get("company_code"):
            return
        try:
            invno = next_invoice_number(c["company_code"])
        except ValueError as e:
            messagebox.showwarning("تنبيه", str(e))
            return
        self.vars["invno"].set(invno)

    def _default_for(self, key):
        if key == "date":
            return date.today().isoformat()
        # رقم الفاتورة سيُملأ تلقائياً بعد اختيار العميل (رمز الشركة + الرقم التسلسلي)
        return ""

    def _build_items_section(self, invoice):
        box = ttk.Frame(self.scroll_frame, style="Card.TFrame")
        box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        header = ttk.Frame(box, style="Card.TFrame")
        header.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(header, text="بنود الخدمة",
                 bg=COL_CARD, fg=COL_NAVY, font=get_tk_font(10, "bold")).pack(side="right")
        tk.Label(header, text="أدخل الأسماء ثم استخدم Tab بين دينار وفلس.",
                 bg=COL_CARD, fg=COL_SUBTEXT, font=get_tk_font(8)).pack(side="right", padx=(10, 0))

        grid_header = tk.Frame(box, bg=COL_CARD_SOFT)
        grid_header.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(grid_header, text="م", bg=COL_CARD_SOFT, width=4, font=get_tk_font(9, "bold")).grid(row=0, column=0, padx=4, pady=10)
        tk.Label(grid_header, text="الخدمة", bg=COL_CARD_SOFT, font=get_tk_font(9, "bold")).grid(row=0, column=1, padx=4, pady=10, sticky="e")
        tk.Label(grid_header, text="دينار", bg=COL_CARD_SOFT, width=10, font=get_tk_font(9, "bold")).grid(row=0, column=2, padx=4, pady=10)
        tk.Label(grid_header, text="فلس", bg=COL_CARD_SOFT, width=10, font=get_tk_font(9, "bold")).grid(row=0, column=3, padx=4, pady=10)
        grid_header.grid_columnconfigure(1, weight=1)

        self.item_dinar_vars = []
        self.item_fils_vars = []
        self.item_label_ar_vars = []
        self.item_label_en_vars = []
        self.item_numeric_entries = []
        existing_items = invoice.get("items") if invoice else None

        for idx, (ar, en) in enumerate(SERVICE_ITEMS):
            row = ttk.Frame(box, style="Card.TFrame")
            row.pack(fill="x", padx=8, pady=6)
            row.grid_columnconfigure(1, weight=1)

            tk.Label(row, text=str(idx + 1), width=4, font=get_tk_font(9), bg=COL_CARD).grid(row=0, column=0, padx=4, pady=2)

            existing_item = existing_items[idx] if existing_items and idx < len(existing_items) else {}
            ar_value = existing_item.get("label") if existing_item.get("label") not in (None, "") else ar
            en_value = existing_item.get("labelEn") if existing_item.get("labelEn") not in (None, "") else en

            edit_frame = ttk.Frame(row, style="Card.Soft.TFrame")
            edit_frame.grid(row=0, column=1, sticky="ew", padx=4, pady=2)
            ar_var = tk.StringVar(value=ar_value)
            en_var = tk.StringVar(value=en_value)
            self.item_label_ar_vars.append(ar_var)
            self.item_label_en_vars.append(en_var)

            ar_entry = ttk.Entry(edit_frame, textvariable=ar_var, font=get_tk_font(9), justify="right", style="Flat.TEntry")
            en_entry = ttk.Entry(edit_frame, textvariable=en_var, font=("Consolas", 8), justify="left", style="Flat.TEntry")
            ar_entry.pack(fill="x", pady=2, padx=4)
            en_entry.pack(fill="x", pady=2, padx=4)
            ar_entry.configure(takefocus=False)
            en_entry.configure(takefocus=False)
            self._bind_widget_autoscroll(ar_entry)
            self._bind_widget_autoscroll(en_entry)

            dv = tk.StringVar(value=str(existing_item.get("dinar", "")) if existing_item.get("dinar") not in ("", None) else "")
            fv = tk.StringVar(value=fmt_fils3(existing_item.get("fils", "")) if existing_item.get("fils") not in ("", None) else "")
            dv.trace_add("write", lambda *a: self._update_total())
            fv.trace_add("write", lambda *a: self._update_total())
            dinar_entry = ttk.Entry(row, textvariable=dv, width=10, font=("Consolas", 10), justify="center", style="Flat.TEntry")
            fils_entry = ttk.Entry(row, textvariable=fv, width=10, font=("Consolas", 10), justify="center", style="Flat.TEntry")
            dinar_entry.grid(row=0, column=2, padx=4, pady=2)
            fils_entry.grid(row=0, column=3, padx=4, pady=2)
            fils_entry.bind("<FocusOut>", lambda e, var=fv: var.set(fmt_fils3(var.get())))
            self._bind_widget_autoscroll(dinar_entry)
            self._bind_widget_autoscroll(fils_entry)
            self.item_dinar_vars.append(dv)
            self.item_fils_vars.append(fv)
            self.item_numeric_entries.extend([dinar_entry, fils_entry])

        total_frame = ttk.Frame(box, style="Card.Soft.TFrame")
        total_frame.pack(fill="x", padx=8, pady=(8, 10))
        label_wrapper = tk.Frame(total_frame, bg=COL_CARD_SOFT)
        label_wrapper.pack(fill="x", padx=10, pady=10)
        # Grid layout: [ English words (expands) ] [ Arabic — Total ] [ numeric total ]
        self.total_words_var_en = tk.StringVar(value='')
        # make column 0 expand and reserve extra minimum width to avoid wrapping
        label_wrapper.grid_columnconfigure(0, weight=1, minsize=420)
        label_wrapper.grid_columnconfigure(1, weight=0)
        label_wrapper.grid_columnconfigure(2, weight=0)
        self.total_words_label_en = tk.Label(label_wrapper, textvariable=self.total_words_var_en,
                             font=get_tk_font(9, "italic"), bg=COL_CARD_SOFT,
                             fg=COL_SUBTEXT, justify="left", anchor="w")
        self.total_words_label_en.grid(row=0, column=0, sticky="w", padx=(6, 10))
        tk.Label(label_wrapper, text="Total — المجموع", font=get_tk_font(11, "bold"), bg=COL_CARD_SOFT, fg=COL_NAVY).grid(row=0, column=1, sticky="e")
        self.total_label = tk.Label(label_wrapper, text="0.000 د.ك", font=("Consolas", 13, "bold"), bg=COL_CARD_SOFT, fg="#0F2B46")
        self.total_label.grid(row=0, column=2, sticky="e", padx=(10, 0))
        self._update_total()

    def _focus_next_input(self, event, target):
        if target is not None:
            target.focus_set()
            self.after_idle(lambda: self._ensure_widget_visible(target))
        return "break"

    def _bind_numeric_tab_order(self):
        if not getattr(self, "item_numeric_entries", None):
            return
        for idx, entry in enumerate(self.item_numeric_entries):
            next_entry = self.item_numeric_entries[idx + 1] if idx + 1 < len(self.item_numeric_entries) else getattr(self, "notes_text", None)
            prev_entry = self.item_numeric_entries[idx - 1] if idx > 0 else self.item_numeric_entries[-1]
            entry.bind("<Tab>", lambda e, target=next_entry: self._focus_next_input(e, target))
            entry.bind("<Shift-Tab>", lambda e, target=prev_entry: self._focus_next_input(e, target))

    def _update_total(self):
        total_fils = 0
        for dv, fv in zip(self.item_dinar_vars, self.item_fils_vars):
            total_fils += safe_int(dv.get()) * 1000 + safe_int(fv.get())
        total_amount = total_fils / 1000
        self.total_label.config(text=f"{total_amount:.3f} د.ك")
        # do not display Arabic words for the amount (user requested)
        if hasattr(self, "total_words_var_en"):
            self.total_words_var_en.set(english_currency_words(total_amount))

    def _build_notes_and_actions(self, invoice):
        box = ttk.Frame(self.scroll_frame, style="Card.TFrame")
        box.pack(fill="x", padx=10, pady=(0, 10))
        tk.Label(box, text="📝 ملاحظات", bg=COL_CARD, fg=COL_NAVY, font=get_tk_font(10, "bold")).pack(anchor="e", padx=12, pady=(10, 4))
        self.notes_text = tk.Text(box, height=4, font=get_tk_font(10), relief="flat", bd=0,
                                   highlightthickness=1, highlightbackground=COL_BORDER, background=COL_CARD_SOFT)
        self.notes_text.pack(fill="x", padx=12, pady=(0, 12))
        self._bind_widget_autoscroll(self.notes_text)
        if invoice:
            self.notes_text.insert("1.0", invoice.get("notes", ""))
        self._bind_numeric_tab_order()

        actions = tk.Frame(self.scroll_frame, bg=COL_BG)
        actions.pack(fill="x", padx=10, pady=(0, 16))
        ttk.Button(actions, text="💾 حفظ الفاتورة", style="Accent.TButton", command=self.save).pack(side="right", padx=4)
        ttk.Button(actions, text="إلغاء", style="Ghost.TButton", command=self._on_close).pack(side="right", padx=4)

    def save(self):
        customer = self.vars["customer"].get().strip()
        if not customer:
            messagebox.showwarning("تنبيه", "الرجاء إدخال اسم العميل.")
            return
        self._update_invno_for_customer()
        invno = self.vars["invno"].get().strip()
        if not invno:
            messagebox.showwarning(
                "تنبيه",
                "الرجاء اختيار عميل صالح له رمز شركة أو إدخال رقم الفاتورة يدويًا."
            )
            return
        # التحقق من عدم تكرار رقم الفاتورة عند الإضافة أو تغييره
        existing_numbers = [str(i["invno"]) for i in load_invoices()]
        if invno in existing_numbers and invno != str(self.editing_invno):
            messagebox.showwarning("تنبيه", "رقم الفاتورة مستخدم بالفعل، الرجاء اختيار رقم آخر.")
            return

        d = {key: var.get() for key, var in self.vars.items()}
        d["items"] = []
        for i, (ar, en) in enumerate(SERVICE_ITEMS):
            label_ar = self.item_label_ar_vars[i].get().strip() or ar
            label_en = self.item_label_en_vars[i].get().strip() or en
            d["items"].append({"label": label_ar, "labelEn": label_en,
                                "dinar": self.item_dinar_vars[i].get(),
                                "fils": self.item_fils_vars[i].get()})
        d["notes"] = self.notes_text.get("1.0", "end").strip()

        try:
            save_invoice(d, editing_invno=self.editing_invno)
        except SaveError as e:
            messagebox.showerror("خطأ في الحفظ", str(e))
            return
        messagebox.showinfo("تم", "تم حفظ الفاتورة بنجاح في ملف data.xlsx")
        self.app.refresh_invoice_list()
        if hasattr(self.app, "bal_tree"):
            self.app.refresh_balances()
        self.app.refresh_dashboard()
        self._on_close()
