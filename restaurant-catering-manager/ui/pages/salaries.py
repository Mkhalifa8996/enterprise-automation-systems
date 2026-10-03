# -*- coding: utf-8 -*-
"""شاشة الرواتب: الإضافة/التعديل، وسم الدفع، والحذف."""

import tkinter as tk
from tkinter import ttk
from ui import dialogs as messagebox
import restaurant_data as rd
from ui.theme import (
    COLOR_BG,
    COLOR_CARD,
    COLOR_MUTED,
    F_LABEL,
    F_BODY,
    safe_str,
    card_frame,
)


class SalariesPages:
    # ---------------- شاشة الرواتب ----------------
    def _build_salaries_tab(self):
        frame = tk.Frame(self.pages_area, bg=COLOR_BG)

        card = card_frame(frame, "إضافة / تعديل راتب")
        card.pack(fill="x", padx=16, pady=(16, 8))
        box = card.body
        form = tk.Frame(box, bg=COLOR_CARD)
        form.pack(fill="x", padx=14, pady=(0, 6))

        self.sal_vars = {}
        self.sal_combos = {}
        cols_per_row = 4
        for idx, (key, label) in enumerate(rd.SALARY_FIELDS):
            r, c = divmod(idx, cols_per_row)
            c = cols_per_row - 1 - c
            cell = tk.Frame(form, bg=COLOR_CARD)
            cell.grid(row=r, column=c, padx=6, pady=6, sticky="ew")
            tk.Label(cell, text=label, font=F_LABEL, bg=COLOR_CARD, fg=COLOR_MUTED,
                     anchor="e", justify="right").pack(fill="x")
            var = tk.StringVar()
            if key == "staff":
                entry = ttk.Combobox(cell, textvariable=var, font=F_BODY, justify="right", state="readonly")
                self.sal_combos["staff"] = entry
            else:
                state = "readonly" if key in ("id", "net_salary") else "normal"
                entry = tk.Entry(cell, textvariable=var, font=F_BODY, justify="right",
                                  state=state, relief="solid", bd=1)
            entry.pack(fill="x", ipady=3)
            self.sal_vars[key] = var
        for c in range(cols_per_row):
            form.grid_columnconfigure(c, weight=1)

        btns = tk.Frame(box, bg=COLOR_CARD)
        btns.pack(fill="x", padx=14, pady=(4, 12), anchor="e")
        ttk.Button(btns, text="حفظ الراتب", style="Accent.TButton", command=self.save_salary).pack(side="right", padx=4)
        ttk.Button(btns, text="مسح الحقول", command=self.clear_salary_form).pack(side="right", padx=4)

        table_card = card_frame(frame, "سجل الرواتب")
        table_card.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        table_wrap = tk.Frame(table_card.body, bg=COLOR_CARD)
        table_wrap.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        cols = [k for k, _ in rd.SALARY_FIELDS]
        self.sal_tree = ttk.Treeview(table_wrap, columns=cols, show="headings", selectmode="browse")
        for k, label in rd.SALARY_FIELDS:
            self.sal_tree.heading(k, text=label)
            self.sal_tree.column(k, anchor="center", width=100)
        vs = ttk.Scrollbar(table_wrap, orient="vertical", command=self.sal_tree.yview)
        self.sal_tree.configure(yscrollcommand=vs.set)
        vs.pack(side="left", fill="y")
        self.sal_tree.pack(fill="both", expand=True)

        btns2 = tk.Frame(table_card.body, bg=COLOR_CARD)
        btns2.pack(fill="x", padx=14, pady=(0, 14), anchor="e")
        ttk.Button(btns2, text="تعليم كمدفوع", command=self.mark_salary_paid).pack(side="right", padx=4)
        ttk.Button(btns2, text="حذف السجل المحدد", style="Danger.TButton",
                   command=self.delete_salary_row).pack(side="right", padx=4)

        def refresh_staff_options():
            self.sal_combos["staff"].config(values=[s["name"] for s in rd.load_staff()])

        self.register_page("salaries", frame, refreshers=[refresh_staff_options, self.refresh_salary_list])

    def save_salary(self):
        data = {k: v.get().strip() for k, v in self.sal_vars.items()}
        if not data.get("staff") or not data.get("month"):
            messagebox.showwarning("تنبيه", "الرجاء اختيار الموظف وإدخال الشهر.")
            return
        try:
            rd.save_salary(data)
        except ValueError as e:
            messagebox.showwarning("تنبيه", str(e))
            return
        messagebox.showinfo("تم", "تم حفظ الراتب بنجاح (يُحدَّث سجل الشهر نفسه إن وُجد).")
        self.clear_salary_form()
        self.refresh_salary_list()

    def clear_salary_form(self):
        for var in self.sal_vars.values():
            var.set("")

    def refresh_salary_list(self):
        for row in self.sal_tree.get_children():
            self.sal_tree.delete(row)
        self._salaries = rd.load_salaries()
        self._sal_iid_map = {}
        for idx, s in enumerate(self._salaries):
            iid = "sal%d" % idx
            self._sal_iid_map[iid] = s
            self.sal_tree.insert("", "end", iid=iid,
                                  values=tuple(safe_str(s.get(k, "")) for k in
                                               ("id", "staff", "month", "base_salary", "bonuses",
                                                "advances", "deductions", "net_salary", "paid")))

    def selected_salary(self):
        sel = self.sal_tree.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "الرجاء اختيار سجل راتب أولاً.")
            return None
        return getattr(self, "_sal_iid_map", {}).get(sel[0])

    def mark_salary_paid(self):
        row = self.selected_salary()
        if not row:
            return
        row["paid"] = "نعم"
        try:
            rd.save_salary(row, editing_id=row.get("id"))
        except ValueError as e:
            messagebox.showwarning("تنبيه", str(e))
            return
        self.refresh_salary_list()

    def delete_salary_row(self):
        row = self.selected_salary()
        if not row:
            return
        if messagebox.askyesno("تأكيد الحذف", "هل تريد حذف سجل الراتب هذا؟"):
            rd.delete_salary(row.get("id"))
            self.refresh_salary_list()
