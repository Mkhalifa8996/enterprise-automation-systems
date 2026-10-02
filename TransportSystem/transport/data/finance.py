# -*- coding: utf-8 -*-
"""الفواتير والمدفوعات والمصروفات والمشروعات والوقود والصيانة."""

import json
from datetime import date
from datetime import datetime
from .schema import CASH_LEDGER_ACCOUNTS, CASH_LEDGER_TYPES, DISABLED_INVOICE_ITEM_KEYS, INVOICE_STANDARD_ITEMS, PAYMENT_TYPES, SERVICE_INVOICE_ITEMS, VEHICLE_SETUP_TARGETS, VOID_STATUSES, safe_float

def load_cash_ledger():
    from .core import _load_rows
    return _load_rows("cash_ledger", "id")

def save_cash_ledger(data, editing_id=None):
    from .core import _next_id, _save_row
    data = data.copy()
    data["amount"] = safe_float(data.get("amount"))
    if data.get("transaction_type") not in CASH_LEDGER_TYPES:
        raise ValueError("نوع حركة النقد غير صحيح.")
    if data.get("account") not in CASH_LEDGER_ACCOUNTS:
        raise ValueError("الحساب غير صحيح.")
    if data["amount"] <= 0:
        raise ValueError("يجب أن يكون المبلغ أكبر من صفر.")
    if editing_id is not None:
        data["id"] = str(editing_id)
    elif not str(data.get("id", "")).strip():
        data["id"] = _next_id(load_cash_ledger())
    _save_row("cash_ledger", "id", data, editing_id)

def delete_cash_ledger(entry_id):
    from .core import _delete_row
    _delete_row("cash_ledger", "id", entry_id)

def load_fuel():
    from .core import _load_rows
    return _load_rows("fuel", "id")

def save_fuel(data, editing_id=None):
    from .core import _next_id, _save_row
    data = data.copy()
    data["id"] = str(editing_id or data.get("id") or _next_id(load_fuel()))
    liters = safe_float(data.get("liters"))
    price = safe_float(data.get("price_per_liter"))
    if liters <= 0 or price < 0:
        raise ValueError("أدخل اللترات وسعر اللتر بشكل صحيح.")
    data["total"] = round(liters * price, 3)
    _save_row("fuel", "id", data, editing_id)

def delete_fuel(row_id):
    from .core import _delete_row
    _delete_row("fuel", "id", row_id)

def load_contracts():
    from .core import _load_rows
    return _load_rows("contracts", "id")

def save_contract(data, editing_id=None):
    from .core import _next_id, _save_row
    data = data.copy()
    data["id"] = str(editing_id or data.get("id") or _next_id(load_contracts()))
    data["value"] = safe_float(data.get("value"))
    _save_row("contracts", "id", data, editing_id)

def delete_contract(row_id):
    from .core import _delete_row
    _delete_row("contracts", "id", row_id)

def load_quotations():
    from .core import _load_rows
    return _load_rows("quotations", "id")

def save_quotation(data, editing_id=None):
    from .core import _next_id, _save_row
    data = data.copy()
    data["id"] = str(editing_id or data.get("id") or _next_id(load_quotations()))
    data["amount"] = safe_float(data.get("amount"))
    if data["amount"] < 0:
        raise ValueError("مبلغ العرض لا يمكن أن يكون سالباً.")
    _save_row("quotations", "id", data, editing_id)

def convert_quotation_to_invoice(quotation_id):
    quotation = next((row for row in load_quotations()
                      if str(row.get("id")) == str(quotation_id)), None)
    if not quotation:
        raise ValueError("عرض السعر غير موجود.")
    if quotation.get("status") == "محوّل إلى فاتورة" and quotation.get("invoice_no"):
        return quotation.get("invoice_no")
    invoice_no = next_invoice_no(quotation.get("customer", ""))
    invoice = {
        "invoice_no": invoice_no,
        "date": quotation.get("date") or date.today().isoformat(),
        "customer": quotation.get("customer", ""),
        "paid": "لا",
        "awb_no": "",
        "container_count": "",
        "items_json": json.dumps([{
            "description": quotation.get("description", ""),
            "amount": safe_float(quotation.get("amount")),
        }], ensure_ascii=False),
        "total": safe_float(quotation.get("amount")),
        "declaration_no": "",
        "notes": f"محول من عرض السعر {quotation.get('quotation_no', quotation_id)}",
    }
    save_invoice(invoice)
    quotation["status"] = "محوّل إلى فاتورة"
    quotation["invoice_no"] = invoice_no
    save_quotation(quotation, editing_id=quotation_id)
    return invoice_no

def delete_quotation(row_id):
    from .core import _delete_row
    _delete_row("quotations", "id", row_id)

def load_maintenance_plans():
    from .core import _load_rows
    return _load_rows("maintenance_plans", "id")

def save_maintenance_plan(data, editing_id=None):
    from .core import _next_id, _save_row
    data = data.copy()
    data["id"] = str(editing_id or data.get("id") or _next_id(load_maintenance_plans()))
    if not str(data.get("car_no", "")).strip() or not str(data.get("due_date", "")).strip():
        raise ValueError("السيارة وتاريخ استحقاق الصيانة حقول مطلوبة.")
    _save_row("maintenance_plans", "id", data, editing_id)

def delete_maintenance_plan(row_id):
    from .core import _delete_row
    _delete_row("maintenance_plans", "id", row_id)

def load_parts():
    from .core import _load_rows
    return _load_rows("parts", "id")

def save_part(data, editing_id=None):
    from .core import _next_id, _save_row
    data = data.copy()
    data["id"] = str(editing_id or data.get("id") or _next_id(load_parts()))
    data["cost"] = safe_float(data.get("cost"))
    if not str(data.get("car_no", "")).strip() or not str(data.get("part_name", "")).strip():
        raise ValueError("السيارة واسم القطعة حقول مطلوبة.")
    _save_row("parts", "id", data, editing_id)

def delete_part(row_id):
    from .core import _delete_row
    _delete_row("parts", "id", row_id)

def cash_ledger_balance(account=""):
    return round(sum(
        (1 if row.get("transaction_type") == "قبض" else -1) * safe_float(row.get("amount"))
        for row in load_cash_ledger()
        if not account or row.get("account") == account
    ), 3)

def approve_financial_period(period_key, summary):
    from .core import _connect, _current_role, _current_user, _ensure_database
    if _current_role != "مدير":
        raise PermissionError("اعتماد التقارير المالية متاح للمدير فقط.")
    key = str(period_key or "").strip()
    if not key:
        raise ValueError("حدد الفترة المالية قبل الاعتماد.")
    _ensure_database()
    connection = _connect()
    try:
        connection.execute(
            "INSERT OR REPLACE INTO financial_approvals "
            "(period_key, summary_json, approved_by, approved_at) VALUES (?, ?, ?, ?)",
            (key, json.dumps(summary, ensure_ascii=False), _current_user,
             datetime.now().isoformat(timespec="seconds")),
        )
        connection.commit()
    finally:
        connection.close()

def load_financial_approval(period_key):
    from .core import _connect, _ensure_database
    _ensure_database()
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT summary_json, approved_by, approved_at FROM financial_approvals "
            "WHERE period_key = ?", (str(period_key).strip(),)
        ).fetchone()
        if not row:
            return None
        result = json.loads(row[0])
        result.update({"approved_by": row[1], "approved_at": row[2]})
        return result
    finally:
        connection.close()

# ------------------------------------------------------------------
# دفعات الشركاء ودفعات السائقين
# ------------------------------------------------------------------
def _normalize_payment(data, party_field, party_label, rows):
    from .core import _next_id
    """تحقق مشترك لحفظ دفعات الشركاء/السائقين قبل الكتابة."""
    data = data.copy()
    data["id"] = str(data.get("id") or "").strip() or None
    if not str(data.get(party_field, "")).strip():
        raise ValueError(f"حقل {party_label} مطلوب.")
    if not str(data.get("date", "")).strip():
        raise ValueError("حقل التاريخ مطلوب.")
    if safe_float(data.get("amount")) <= 0:
        raise ValueError("المبلغ يجب أن يكون أكبر من صفر.")
    if str(data.get("payment_type", "")).strip() not in PAYMENT_TYPES:
        raise ValueError("نوع الدفعة يجب أن يكون «مدين» أو «دائن».")
    if not data["id"]:
        data["id"] = str(_next_id(rows))
    # الدفعات المسجّلة سابقاً قد تخلو من حقول الإشطب قبل إضافتها.
    if str(data.get("voided", "")).strip() not in VOID_STATUSES:
        data["voided"] = VOID_STATUSES[0]
    data.setdefault("void_reason", "")
    return data

def is_voided(row):
    """هل السجل مشطوب؟ السجلات القديمة تُعامل كسليمة."""
    return str((row or {}).get("voided", "")).strip() == VOID_STATUSES[1]

def set_payment_voided(sheet_key, row_id, voided=True, reason=""):
    from .core import _load_rows, _save_row
    """يشطب أو يعيد دفعة دون حذفها حتى تبقى في كشف الفترة التي صدرت فيه."""
    rows = _load_rows(sheet_key, "id")
    row = next((item for item in rows if str(item.get("id")) == str(row_id)), None)
    if not row:
        raise ValueError("سجل الدفعة غير موجود.")
    row = row.copy()
    row["voided"] = VOID_STATUSES[1] if voided else VOID_STATUSES[0]
    row["void_reason"] = str(reason or "").strip() if voided else ""
    if voided and not row["void_reason"]:
        raise ValueError("سبب الإشطب مطلوب.")
    _save_row(sheet_key, "id", row, row_id)
    return row

def void_partner_payment(row_id, reason=""):
    return set_payment_voided("partner_payments", row_id, True, reason)

def restore_partner_payment(row_id):
    return set_payment_voided("partner_payments", row_id, False)

def void_driver_payment(row_id, reason=""):
    return set_payment_voided("driver_payments", row_id, True, reason)

def restore_driver_payment(row_id):
    return set_payment_voided("driver_payments", row_id, False)

def load_partner_payments(include_voided=True):
    from .core import _load_rows
    rows = _load_rows("partner_payments", "id")
    return rows if include_voided else [row for row in rows if not is_voided(row)]

def save_partner_payment(data, editing_id=None):
    from .core import _save_row
    rows = load_partner_payments()
    data = _normalize_payment(data, "partner", "اسم الشريك", rows)
    if editing_id is not None:
        data["id"] = str(editing_id)
    data.setdefault("car_no", "")
    # الإشطب حالة مستقلة لا تُمسح بمجرد تعديل المبلغ.
    if editing_id is not None:
        previous = next((row for row in rows if str(row.get("id")) == str(editing_id)), None)
        if previous:
            data["voided"] = str(previous.get("voided", VOID_STATUSES[0]))
            data["void_reason"] = str(previous.get("void_reason", ""))
    _save_row("partner_payments", "id", data, editing_id)
    return data["id"]

def delete_partner_payment(row_id):
    from .core import _delete_row
    _delete_row("partner_payments", "id", row_id)

def load_driver_payments(include_voided=True):
    from .core import _load_rows
    rows = _load_rows("driver_payments", "id")
    return rows if include_voided else [row for row in rows if not is_voided(row)]

def save_driver_payment(data, editing_id=None):
    from .core import _save_row
    from .entities import driver_type_of
    rows = load_driver_payments()
    data = _normalize_payment(data, "driver", "اسم السائق", rows)
    if editing_id is not None:
        data["id"] = str(editing_id)
    data.setdefault("car_no", "")
    # نوع السائق يُستكمل من سجل السائقين عند تركه فارغاً.
    if not str(data.get("driver_type", "")).strip():
        data["driver_type"] = driver_type_of(data.get("driver"))
    if editing_id is not None:
        previous = next((row for row in rows if str(row.get("id")) == str(editing_id)), None)
        if previous:
            data["voided"] = str(previous.get("voided", VOID_STATUSES[0]))
            data["void_reason"] = str(previous.get("void_reason", ""))
    _save_row("driver_payments", "id", data, editing_id)
    return data["id"]

def delete_driver_payment(row_id):
    from .core import _delete_row
    _delete_row("driver_payments", "id", row_id)

# ------------------------------------------------------------------
# صيانة السيارات
# ------------------------------------------------------------------
def load_maintenance():
    from .core import _load_rows
    return _load_rows("maintenance", "id")

def save_maintenance(data, editing_id=None):
    from .core import _next_id, _save_row
    rows = load_maintenance()
    if editing_id is None:
        data["id"] = str(_next_id(rows))
    else:
        data["id"] = str(editing_id)
    _save_row("maintenance", "id", data, editing_id)

def delete_maintenance(row_id):
    from .core import _delete_row
    _delete_row("maintenance", "id", row_id)

# ------------------------------------------------------------------
# مصاريف تجهيز السيارات (قبل بدء العمل الفعلي)
# ------------------------------------------------------------------
def load_vehicle_setup_expenses():
    from .core import _load_rows
    return _load_rows("vehicle_setup_expenses", "id")

def save_vehicle_setup_expense(data, editing_id=None):
    from .core import _next_id, _save_row
    data = data.copy()
    rows = load_vehicle_setup_expenses()
    data["id"] = str(editing_id or data.get("id") or _next_id(rows))
    car_no = str(data.get("car_no", "")).strip()
    if not car_no:
        raise ValueError("الرجاء اختيار رقم السيارة.")
    amount = safe_float(data.get("amount"))
    if amount <= 0:
        raise ValueError("أدخل مبلغ تجهيز أكبر من صفر.")
    category = str(data.get("category", "")).strip() or "أخرى"
    data["category"] = category
    # الجهة تُشتق من البند ما لم يحدّدها المستخدم، حتى لا تتناقض البيانات.
    data["setup_target"] = (str(data.get("setup_target", "")).strip()
                            or VEHICLE_SETUP_TARGETS.get(category, "سيارة"))
    data["amount"] = round(amount, 3)
    _save_row("vehicle_setup_expenses", "id", data, editing_id)
    return data

def delete_vehicle_setup_expense(row_id):
    from .core import _delete_row
    _delete_row("vehicle_setup_expenses", "id", row_id)

def vehicle_setup_expenses_for_car(car_no):
    """مصاريف تجهيز سيارة واحدة مجمّعة حسب البند."""
    car_no = str(car_no or "").strip()
    totals, total = {}, 0.0
    for row in load_vehicle_setup_expenses():
        if car_no and str(row.get("car_no", "")).strip() != car_no:
            continue
        amount = safe_float(row.get("amount"))
        if not amount:
            continue
        category = str(row.get("category", "")).strip() or "أخرى"
        totals[category] = round(totals.get(category, 0.0) + amount, 3)
        total = round(total + amount, 3)
    return {"totals": totals, "total": total}

def all_vehicle_setup_expenses_summary():
    """مصاريف التجهيز لكل السيارات، مع الإجمالي العام."""
    per_car = {}
    for row in load_vehicle_setup_expenses():
        car_no = str(row.get("car_no", "")).strip() or "(بلا رقم)"
        amount = safe_float(row.get("amount"))
        if not amount:
            continue
        per_car[car_no] = round(per_car.get(car_no, 0.0) + amount, 3)
    return {"per_car": per_car,
            "total": round(sum(per_car.values()), 3)}

# ------------------------------------------------------------------
# الفواتير
# ------------------------------------------------------------------
def load_invoices():
    from .core import _load_rows
    return _load_rows("invoices", "invoice_no")

def next_invoice_no(customer=""):
    from .entities import load_customers
    """Return a six-digit invoice number: customer code + private sequence."""
    customer = str(customer or "").strip()
    customers = load_customers()
    customer_index = next(
        (index for index, row in enumerate(customers, start=1)
         if str(row.get("name", "")).strip() == customer),
        None,
    )
    if customer_index is None:
        customer_index = 1
    if customer_index > 99:
        raise ValueError("لا يمكن إصدار رقم فاتورة لأكثر من 99 عميلاً.")

    prefix = f"{customer_index:02d}"
    rows = load_invoices()
    customer_suffixes = []
    for row in rows:
        number = str(row.get("invoice_no", "")).strip()
        if (len(number) == 6 and number.isdigit()
                and number[:2] == prefix
                and str(row.get("customer", "")).strip() == customer):
            customer_suffixes.append(int(number[2:]))
    suffix = max(customer_suffixes, default=0) + 1
    if suffix > 9999:
        raise ValueError("تم تجاوز الحد الأقصى لأرقام فواتير هذا العميل.")
    return f"{prefix}{suffix:04d}"

def save_invoice(data, editing_invno=None):
    from .core import _save_row_by_name
    data.setdefault("paid", "لا")
    _save_row_by_name("invoices", data, editing_invno)

def mark_invoices_paid(invoice_numbers):
    from .core import _connect, _ensure_database, _invalidate_rows_cache, _mark_local_change, ensure_workbook
    """Mark all supplied invoice numbers as paid in one database and Excel write."""
    numbers = {str(number).strip() for number in invoice_numbers if str(number).strip()}
    if not numbers:
        return 0
    ensure_workbook()
    _ensure_database()
    connection = _connect()
    updated = 0
    try:
        rows = [
            json.loads(item[0]) for item in connection.execute(
                "SELECT data_json FROM records WHERE sheet_key = 'invoices' ORDER BY rowid"
            )
        ]
        for invoice in rows:
            invoice_no = str(invoice.get("invoice_no", "")).strip()
            if invoice_no in numbers and invoice.get("paid") != "نعم":
                invoice["paid"] = "نعم"
                connection.execute(
                    "UPDATE records SET data_json = ?, updated_at = ? "
                    "WHERE sheet_key = 'invoices' AND record_key = ?",
                    (json.dumps(invoice, ensure_ascii=False),
                     datetime.now().isoformat(timespec="seconds"), invoice_no),
                )
                updated += 1
        connection.commit()
    finally:
        connection.close()
    if updated:
        _invalidate_rows_cache()
        _mark_local_change()
    return updated

def delete_invoice(invoice_no):
    from .core import _delete_row, _save_row
    from .trips import load_services, load_trips
    """يحذف الفاتورة ويعيد الرحلات والخدمات المرتبطة بها إلى حالة غير مفوترة."""
    for trip in load_trips():
        if str(trip.get("invoice_no", "")) == str(invoice_no):
            trip["invoiced"] = "لا"
            trip["invoice_no"] = ""
            _save_row("trips", "id", trip, trip["id"])
    for service in load_services():
        if str(service.get("invoice_no", "")) == str(invoice_no):
            service["invoiced"] = "لا"
            service["invoice_no"] = ""
            _save_row("services", "id", service, service["id"])
    _delete_row("invoices", "invoice_no", invoice_no)

def load_payments():
    from .core import _load_rows
    return _load_rows("payments", "id")

def save_payment(data, editing_id=None):
    from .core import _next_id, _save_row
    rows = load_payments()
    if editing_id is None:
        data["id"] = str(_next_id(rows))
    else:
        data["id"] = str(editing_id)
    data.setdefault("date", date.today().isoformat())
    data["amount"] = round(safe_float(data.get("amount")), 3)
    _save_row("payments", "id", data, editing_id)

def delete_payment(row_id):
    from .core import _delete_row
    _delete_row("payments", "id", row_id)

def build_invoice_items(trip_ids, service_ids):
    from .trips import load_services, load_trips
    """Build editable invoice lines from the selected trips and services."""
    import json
    trips = {str(t["id"]): t for t in load_trips()}
    services = {str(s["id"]): s for s in load_services()}
    items = []
    for tid in trip_ids:
        t = trips.get(str(tid))
        if not t:
            continue
        amount = safe_float(t.get("fee"))
        route = f"{t.get('origin','')} ← {t.get('destination','')}".strip(" ←")
        cat = t.get("trip_category", "")
        desc = f"رحلة {cat} بتاريخ {t.get('date','')} - {route}".strip()
        items.append({"desc": desc, "amount": amount})
    for sid in service_ids:
        s = services.get(str(sid))
        if not s:
            continue
        amount = safe_float(s.get("total"))
        desc = f"{s.get('service_type','')} بتاريخ {s.get('date','')} - الكمية {s.get('quantity','')}"
        items.append({"desc": desc, "amount": amount})
    return items

def _invoice_item_is_disabled(item):
    description = str(item.get("desc", "") if isinstance(item, dict) else item or "").strip()
    english = description.split(" — ", 1)[0].strip().upper()
    arabic = description.split(" — ", 1)[1].strip() if " — " in description else description
    return english in DISABLED_INVOICE_ITEM_KEYS or arabic in DISABLED_INVOICE_ITEM_KEYS

def remove_disabled_invoice_items():
    from .core import _save_row_by_name
    """Remove retired invoice lines from existing invoices and recalculate totals."""
    import json
    changed = False
    for invoice in load_invoices():
        raw_items = invoice.get("items_json") or "[]"
        try:
            items = json.loads(raw_items)
        except (TypeError, ValueError):
            continue
        filtered = [item for item in items if not _invoice_item_is_disabled(item)]
        if len(filtered) == len(items):
            continue
        invoice["items_json"] = json.dumps(filtered, ensure_ascii=False)
        invoice["total"] = round(sum(safe_float(item.get("amount")) for item in filtered), 3)
        _save_row_by_name("invoices", invoice, invoice.get("invoice_no"))
        changed = True
    return changed

def build_invoice_form_items(trip_ids, service_ids):
    from .trips import load_services, load_trips
    trips = {str(t["id"]): t for t in load_trips()}
    services = {str(s["id"]): s for s in load_services()}
    transport = sum(safe_float(trips[str(tid)].get("fee")) for tid in trip_ids if str(tid) in trips)
    holiday = sum(safe_float(trips[str(tid)].get("holiday_price")) for tid in trip_ids if str(tid) in trips)
    service_totals = {item: 0.0 for item in SERVICE_INVOICE_ITEMS.values()}
    for sid in service_ids:
        service = services.get(str(sid))
        if not service:
            continue
        item = SERVICE_INVOICE_ITEMS.get(str(service.get("service_type", "")).strip())
        if item:
            service_totals[item] += safe_float(service.get("total"))
    mapped = {"TRANSPORTATION CHARGES — أجور نقل": transport,
              "DELAYED TRUCK CHARGES — تأخير شاحنة": holiday,
              **service_totals}
    items = [{"desc": desc, "item_key": desc.split(" — ", 1)[0],
              "amount": round(mapped.get(desc, 0), 3)} for desc in INVOICE_STANDARD_ITEMS]
    for sid in service_ids:
        service = services.get(str(sid))
        if service and str(service.get("service_type", "")).strip() not in SERVICE_INVOICE_ITEMS:
            items.append({"desc": f"{service.get('service_type', '')} — {service.get('date', '')}",
                          "amount": round(safe_float(service.get("total")), 3)})
    return items

def create_invoice_for_customer(customer, trip_ids, service_ids, extra_notes="", items=None, invoice_date=None):
    from .trips import load_trips, mark_service_invoiced, mark_trip_invoiced
    """Save an invoice after its editable lines have been approved by the user."""
    import json
    trips = {str(t["id"]): t for t in load_trips()}
    if items is None:
        items = build_invoice_form_items(trip_ids, service_ids)
    total = sum(safe_float(item.get("amount")) for item in items)

    declaration_no = ", ".join(dict.fromkeys(
        str(trips[str(tid)].get("declaration_no", "")).strip()
        for tid in trip_ids if str(tid) in trips
        and str(trips[str(tid)].get("declaration_no", "")).strip()
    ))
    linked_invoice_no = next((str(trips[str(tid)].get("invoice_no"))
                              for tid in trip_ids if str(tid) in trips
                              and str(trips[str(tid)].get("invoice_no", "")).strip()), "")
    if linked_invoice_no:
        existing_linked = next((inv for inv in load_invoices()
                                if str(inv.get("invoice_no")) == linked_invoice_no), None)
        if existing_linked:
            for tid in trip_ids:
                mark_trip_invoiced(tid, linked_invoice_no)
            for sid in service_ids:
                mark_service_invoiced(sid, linked_invoice_no)
            return existing_linked
    existing = next((inv for inv in load_invoices()
                     if str(inv.get("declaration_no", "")).strip() == declaration_no
                     and str(inv.get("customer", "")).strip() == str(customer).strip()
                     and declaration_no), None)
    if existing:
        for tid in trip_ids:
            mark_trip_invoiced(tid, existing["invoice_no"])
        for sid in service_ids:
            mark_service_invoiced(sid, existing["invoice_no"])
        return existing

    container_count = sum(1 for tid in trip_ids if str(tid) in trips)
    invno = next_invoice_no(customer)
    invoice = {
        "invoice_no": invno,
        "date": invoice_date or date.today().isoformat(),
        "customer": customer,
        "container_count": container_count,
        "items_json": json.dumps(items, ensure_ascii=False),
        "total": round(total, 3),
        "declaration_no": declaration_no,
        "notes": extra_notes,
    }
    save_invoice(invoice)
    for tid in trip_ids:
        mark_trip_invoiced(tid, invno)
    for sid in service_ids:
        mark_service_invoiced(sid, invno)
    return invoice

def invoice_context_for_declaration(trip_ids):
    from .trips import load_services, load_trips
    """Return source records for a declaration without changing invoice status."""
    selected = [t for t in load_trips() if str(t.get("id")) in {str(i) for i in trip_ids}]
    if not selected:
        raise ValueError("الرجاء تحديد رحلة واحدة على الأقل من البيان.")
    customer = str(selected[0].get("customer", "")).strip()
    if not customer:
        raise ValueError("لا يوجد مخلص/عميل محدد للبيان.")
    if any(str(t.get("customer", "")).strip() != customer for t in selected):
        raise ValueError("لا يمكن إصدار فاتورة لرحلات تخص أكثر من مخلص.")
    if any(str(t.get("invoiced", "")) == "نعم" for t in selected):
        raise ValueError("توجد رحلة مفوترة ضمن البيان المحدد.")
    selected_ids = {str(t.get("id")) for t in selected}
    declarations = {str(t.get("declaration_no", "")).strip() for t in selected}
    service_ids = []
    for service in load_services():
        linked_ids = {part.strip() for part in str(service.get("trip_ids", "")).split(",") if part.strip()}
        same_declaration = str(service.get("declaration_no", "")).strip() in declarations
        if (linked_ids.intersection(selected_ids) or same_declaration) and \
                str(service.get("customer", "")).strip() == customer and \
                str(service.get("invoiced", "")) != "نعم":
            service_ids.append(service.get("id"))
    return {"customer": customer, "trip_ids": [t.get("id") for t in selected],
            "service_ids": service_ids, "declaration_no": ", ".join(sorted(d for d in declarations if d))}

def create_invoice_for_declaration(trip_ids, extra_notes=""):
    """Create one invoice from a daily-declaration selection and its linked services."""
    context = invoice_context_for_declaration(trip_ids)
    return create_invoice_for_customer(context["customer"], context["trip_ids"], context["service_ids"], extra_notes)

def update_invoice_for_service(service_id):
    from .trips import load_services, load_trips, mark_service_invoiced
    """Add a newly linked service to its declaration invoice and recalculate it."""
    services = load_services()
    service = next((s for s in services if str(s.get("id")) == str(service_id)), None)
    if not service:
        return None
    linked_ids = {part.strip() for part in str(service.get("trip_ids", "")).split(",") if part.strip()}
    trips = load_trips()
    linked_trips = [t for t in trips if str(t.get("id")) in linked_ids]
    invoice_no = next((str(t.get("invoice_no")) for t in linked_trips if str(t.get("invoice_no", "")).strip()), "")
    if not invoice_no:
        return None
    invoice = next((i for i in load_invoices() if str(i.get("invoice_no")) == invoice_no), None)
    if not invoice:
        return None
    invoice_trips = [t for t in trips if str(t.get("invoice_no")) == invoice_no]
    trip_ids = [t.get("id") for t in invoice_trips]
    declaration_numbers = {str(t.get("declaration_no", "")).strip() for t in invoice_trips}
    service_ids = [s.get("id") for s in load_services()
                   if str(s.get("invoice_no")) == invoice_no
                   or str(s.get("id")) == str(service_id)
                   or str(s.get("declaration_no", "")).strip() in declaration_numbers]
    items = build_invoice_form_items(trip_ids, service_ids)
    invoice["items_json"] = json.dumps(items, ensure_ascii=False)
    invoice["total"] = round(sum(safe_float(item.get("amount")) for item in items), 3)
    save_invoice(invoice, editing_invno=invoice_no)
    for sid in service_ids:
        mark_service_invoiced(sid, invoice_no)
    return invoice

def unbilled_trips_for_customer(customer):
    from .trips import load_trips
    return [t for t in load_trips() if t.get("customer") == customer and t.get("invoiced") != "نعم"]

def unbilled_services_for_customer(customer):
    from .trips import load_services
    return [s for s in load_services() if s.get("customer") == customer and s.get("invoiced") != "نعم"]
