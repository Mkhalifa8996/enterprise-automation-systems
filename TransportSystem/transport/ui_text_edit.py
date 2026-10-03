# -*- coding: utf-8 -*-
"""اختصارات تحرير النص (نسخ/قص/لصق) وقراءة قيم العناصر."""

import tkinter as tk
from .ui_helpers import log_exception, safe_str


def _widget_value(widget):
    try:
        return widget.get()
    except TypeError:
        try:
            return widget.get("1.0", "end-1c")
        except Exception:
            return ""
    except Exception:
        return ""

def _entry_selection(widget):
    try:
        if widget.selection_present():
            return widget.selection_get()
    except Exception as _log_exc: log_exception("_entry_selection", _log_exc)
    try:
        selected = widget.tag_ranges("sel")
        if selected:
            return widget.get(selected[0], selected[1])
    except Exception as _log_exc: log_exception("_entry_selection", _log_exc)
    return ""

def _widget_full_value(widget):
    """إرجاع كل نص الحقل بأمان (سطر واحد أو متعدد الأسطر)."""
    try:
        return widget.get()
    except TypeError:
        try:
            return widget.get("1.0", "end-1c")
        except Exception:
            return ""
    except Exception:
        return ""

def _entry_is_editable(widget):
    try:
        return str(widget.cget("state")) not in ("readonly", "disabled")
    except Exception:
        return True

def _copy_widget_value(widget):
    value = _entry_selection(widget)
    if not value:
        value = _widget_full_value(widget)
    if value:
        widget.clipboard_clear()
        widget.clipboard_append(value)

def _copy_listbox_value(widget):
    try:
        selected = [str(widget.get(i)) for i in widget.curselection()]
    except Exception:
        return
    if selected:
        widget.clipboard_clear()
        widget.clipboard_append("\n".join(selected))

def _cut_widget_value(widget):
    if not _entry_is_editable(widget) or isinstance(widget, tk.Listbox):
        return
    selected = _entry_selection(widget)
    if not selected:
        return
    try:
        widget.clipboard_clear()
        widget.clipboard_append(selected)
        widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
    except Exception:
        try:
            current = _widget_full_value(widget)
            widget.delete(0, tk.END)
            widget.insert(0, current.replace(selected, "", 1))
        except Exception as _log_exc: log_exception("_cut_widget_value", _log_exc)

def _paste_widget_value(widget):
    if not _entry_is_editable(widget) or isinstance(widget, tk.Listbox):
        return
    try:
        value = widget.clipboard_get()
    except Exception:
        return
    if not value:
        return
    selected = _entry_selection(widget)
    anchor = None
    if selected:
        try:
            anchor = widget.index(tk.SEL_FIRST)
        except Exception:
            anchor = None
    try:
        if selected:
            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
        # أعد المؤشر لبداية التحديد حتى يُلصق النص في مكانه الصحيح
        if anchor is not None:
            try:
                widget.icursor(anchor)
            except Exception as _log_exc: log_exception("_paste_widget_value", _log_exc)
        widget.insert(tk.INSERT, value)
    except Exception:
        try:
            widget.set(_widget_full_value(widget) + value)
        except Exception as _log_exc: log_exception("_paste_widget_value", _log_exc)

def select_all_text(event):
    widget = event.widget
    if isinstance(widget, tk.Listbox):
        try:
            widget.selection_set(0, tk.END)
        except Exception as _log_exc: log_exception("select_all_text", _log_exc)
        return "break"
    try:
        widget.selection_range(0, tk.END)
        widget.icursor(tk.END)
    except Exception:
        try:
            widget.tag_add("sel", "1.0", "end-1c")
        except Exception as _log_exc: log_exception("select_all_text", _log_exc)
    return "break"

def copy_text(event):
    widget = event.widget
    if isinstance(widget, tk.Listbox):
        _copy_listbox_value(widget)
    else:
        _copy_widget_value(widget)
    return "break"

def cut_text(event):
    _cut_widget_value(event.widget)
    return "break"

def paste_text(event):
    _paste_widget_value(event.widget)
    return "break"

def show_text_edit_menu(event):
    widget = event.widget
    menu = tk.Menu(widget, tearoff=0)
    editable = _entry_is_editable(widget) and not isinstance(widget, tk.Listbox)

    menu.add_command(label="تحديد الكل", command=lambda: select_all_text(event))
    menu.add_command(label="نسخ", command=lambda: copy_text(event))
    menu.add_command(label="قص", command=lambda: cut_text(event), state="normal" if editable else "disabled")
    menu.add_command(label="لصق", command=lambda: paste_text(event), state="normal" if editable else "disabled")
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()
        menu.destroy()
    return "break"

def install_text_edit_bindings(root):
    """كّل حقول البرنامج تدعم تحديد الكل / نسخ / قص / لصق:
    اختصارات لوحة المفاتيح + قائمة الزر الأيمن + الأحداث الافتراضية.
    نستبدل أي binding قديم بدلاً من الإضافة حتى لا يحدث النسخ مرتين."""
    key_handlers = {
        "<Control-a>": select_all_text,
        "<Control-c>": copy_text,
        "<Control-x>": cut_text,
        "<Control-v>": paste_text,
        "<Button-3>": show_text_edit_menu,
    }
    classes = ("Spinbox", "Entry", "Text", "TEntry", "TSpinbox", "TCombobox", "Listbox")
    for widget_class in classes:
        for sequence, handler in key_handlers.items():
            root.bind_class(widget_class, sequence, handler)
    # الأحداث الافتراضية للمعالجة الموحدة (<<Copy>>/<<Cut>>/<<Paste>>)
    for widget_class in ("Spinbox", "Entry", "Text", "TEntry", "TSpinbox", "TCombobox"):
        root.bind_class(widget_class, "<<Copy>>", copy_text)
        root.bind_class(widget_class, "<<Cut>>", cut_text)
        root.bind_class(widget_class, "<<Paste>>", paste_text)

def set_combo_values(combo, values):
    if combo is None:
        return
    normalized = [safe_str(v) for v in (values or []) if safe_str(v).strip()]
    current = safe_str(combo.get()).strip()
    try:
        combo.config(values=normalized)
    except (tk.TclError, AttributeError):
        return
    if current and current not in normalized:
        try:
            combo.set("")
        except (tk.TclError, AttributeError) as _log_exc: log_exception("set_combo_values", _log_exc)

def refresh_related_screens(widget):
    """Schedule a single shared refresh after a record changes anywhere."""
    try:
        app = widget.winfo_toplevel()
        if hasattr(app, "refresh_linked_data"):
            app.after_idle(app.refresh_linked_data)
    except tk.TclError as exc:
        log_exception("جدولة تحديث الشاشات", exc)
