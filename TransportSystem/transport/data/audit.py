# -*- coding: utf-8 -*-
"""سجل التدقيق، فترات الإغلاق المقفلة، والتراجع عن التعديلات."""

import json
from datetime import date
from datetime import datetime
from .core import _connect, _current_role, _current_user, _ensure_database, _log_audit, _period_from_data, is_period_closed
from .finance import load_maintenance_plans
from .entities import load_vehicle_assignments, load_vehicle_partners, load_vehicles

def close_period(period_month):
    if _current_role != "مدير":
        raise PermissionError("إقفال الفترات متاح للمدير فقط.")
    month = str(period_month or "").strip()[:7]
    if len(month) != 7 or month[4] != "-":
        raise ValueError("صيغة الشهر يجب أن تكون YYYY-MM.")
    _ensure_database()
    connection = _connect()
    try:
        connection.execute(
            "INSERT OR REPLACE INTO closed_periods "
            "(period_month, closed_by, closed_at) VALUES (?, ?, ?)",
            (month, _current_user, datetime.now().isoformat(timespec="seconds")),
        )
        connection.commit()
    finally:
        connection.close()

def reopen_period(period_month):
    if _current_role != "مدير":
        raise PermissionError("فتح الفترات متاح للمدير فقط.")
    _ensure_database()
    connection = _connect()
    try:
        connection.execute("DELETE FROM closed_periods WHERE period_month = ?",
                           (str(period_month).strip()[:7],))
        connection.commit()
    finally:
        connection.close()

def list_closed_periods():
    _ensure_database()
    connection = _connect()
    try:
        return [row[0] for row in connection.execute(
            "SELECT period_month FROM closed_periods ORDER BY period_month DESC"
        )]
    finally:
        connection.close()

def load_audit_logs(limit=200):
    _ensure_database()
    connection = _connect()
    try:
        return [
            {"id": row[0], "action": row[1], "sheet_key": row[2],
             "record_key": row[3], "details": json.loads(row[4]),
             "actor": row[5], "created_at": row[6]}
            for row in connection.execute(
                "SELECT id, action, sheet_key, record_key, details_json, actor, created_at "
                "FROM audit_logs ORDER BY id DESC LIMIT ?", (int(limit),)
            )
        ]
    finally:
        connection.close()

def load_audit_logs_by_ids(log_ids):
    """تحميل سجلات عمليات محددة بواسطة IDs"""
    if not log_ids:
        return []
    _ensure_database()
    connection = _connect()
    try:
        placeholders = ','.join('?' for _ in log_ids)
        return [
            {"id": row[0], "action": row[1], "sheet_key": row[2],
             "record_key": row[3], "details": json.loads(row[4]),
             "actor": row[5], "created_at": row[6]}
            for row in connection.execute(
                f"SELECT id, action, sheet_key, record_key, details_json, actor, created_at "
                f"FROM audit_logs WHERE id IN ({placeholders}) "
                f"ORDER BY id DESC", tuple(log_ids)
            )
        ]
    finally:
        connection.close()

def get_log_for_record(sheet_key, record_key):
    """الحصول على آخر سجل عمليات لسجل محدد (لغرض التراجع السريع)."""
    _ensure_database()
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT id, action, details_json FROM audit_logs "
            "WHERE sheet_key = ? AND record_key = ? "
            "ORDER BY id DESC LIMIT 1",
            (sheet_key, str(record_key))
        ).fetchone()
        if row:
            return {
                "id": row[0],
                "action": row[1],
                "details": json.loads(row[2])
            }
        return None
    finally:
        connection.close()

def undo_audit_logs(log_ids, dry_run=False):
    """تراجع عن عمليات محددة بواسطة IDs.
    
    Args:
        log_ids: قائمة IDs للعمليات المراد التراجع عنها
        dry_run: إذا كان True، لا يتم تطبيق التغييرات ولكن يتم التحقق فقط
    
    Returns:
        dict: يحتوي على:
            - success: عدد العمليات التي تم التراجع عنها بنجاح
            - failed: قائمة العمليات التي فشلت مع أسبابها
            - skipped: قائمة العمليات التي تم تخطيها (مثل الفترات المغلقة)
    """
    if not log_ids:
        return {"success": 0, "failed": [], "skipped": []}
    
    _ensure_database()
    connection = _connect()
    try:
        results = {"success": 0, "failed": [], "skipped": []}
        
        # جلب السجلات مرتبة من الأحدث للأقدم (عكس ترتيب التراجع)
        placeholders = ','.join('?' for _ in log_ids)
        logs = connection.execute(
            f"SELECT id, action, sheet_key, record_key, details_json, actor, created_at "
            f"FROM audit_logs WHERE id IN ({placeholders}) "
            f"ORDER BY id DESC", tuple(log_ids)
        ).fetchall()
        
        for log in logs:
            log_id, action, sheet_key, record_key, details_json, actor, created_at = log
            details = json.loads(details_json)
            
            try:
                # التحقق مما إذا كان يمكن التراجع (فترات مغلقة)
                if action in ("تعديل", "حذف") and "before" in details:
                    before_data = details.get("before")
                    if before_data:
                        period = _period_from_data(before_data)
                        if period and is_period_closed(period) and _current_role != "مدير":
                            results["skipped"].append({
                                "id": log_id,
                                "reason": f"الفترة {period} مغلقة ولا يمكن التراجع"
                            })
                            continue
                
                if action == "إضافة":
                    # حذف السجل الذي تم إضافته
                    if not dry_run:
                        connection.execute(
                            "DELETE FROM records WHERE sheet_key = ? AND record_key = ?",
                            (sheet_key, str(record_key))
                        )
                        # تسجيل عملية التراجع في سجل العمليات
                        _log_audit(connection, "تراجع عن إضافة", sheet_key, str(record_key),
                                   {"original_id": log_id, "data": details.get("after")})
                
                elif action == "حذف":
                    # استعادة السجل المحذوف
                    if not dry_run and "before" in details:
                        before_data = details["before"]
                        connection.execute(
                            "INSERT OR REPLACE INTO records "
                            "(sheet_key, record_key, data_json, updated_at) VALUES (?, ?, ?, ?)",
                            (sheet_key, str(record_key),
                             json.dumps(before_data, ensure_ascii=False),
                             datetime.now().isoformat(timespec="seconds"))
                        )
                        # تسجيل عملية التراجع
                        _log_audit(connection, "تراجع عن حذف", sheet_key, str(record_key),
                                   {"original_id": log_id, "restored_data": before_data})
                
                elif action == "تعديل":
                    # استعادة البيانات القديمة (before)
                    if not dry_run and "before" in details:
                        before_data = details["before"]
                        connection.execute(
                            "UPDATE records SET data_json = ?, updated_at = ? "
                            "WHERE sheet_key = ? AND record_key = ?",
                            (json.dumps(before_data, ensure_ascii=False),
                             datetime.now().isoformat(timespec="seconds"),
                             sheet_key, str(record_key))
                        )
                        # تسجيل عملية التراجع
                        _log_audit(connection, "تراجع عن تعديل", sheet_key, str(record_key),
                                   {"original_id": log_id, "restored_data": before_data})
                
                results["success"] += 1
                
            except Exception as e:
                results["failed"].append({
                    "id": log_id,
                    "action": action,
                    "reason": str(e)
                })
        
        if not dry_run:
            connection.commit()
        
        return results
        
    finally:
        connection.close()

def get_alerts(days=30):
    today = date.today()
    cutoff = date.fromordinal(today.toordinal() + int(days))
    alerts = []

    for vehicle in load_vehicles():
        expiry = str(vehicle.get("license_expiry", "")).strip()
        try:
            expiry_date = date.fromisoformat(expiry)
        except ValueError:
            continue
        if expiry_date <= cutoff:
            alerts.append({"type": "ترخيص", "item": vehicle.get("car_no", ""),
                           "date": expiry, "message": "ترخيص السيارة قريب الانتهاء أو منتهٍ"})

    for sheet_key, loader, label in (
        ("vehicle_assignments", load_vehicle_assignments, "تكليف سائق"),
        ("vehicle_partners", load_vehicle_partners, "شراكة"),
    ):
        for row in loader():
            expiry = str(row.get("end_date", "")).strip()
            if not expiry:
                continue
            try:
                expiry_date = date.fromisoformat(expiry)
            except ValueError:
                continue
            if expiry_date <= cutoff:
                alerts.append({"type": label, "item": row.get("car_no", ""),
                               "date": expiry, "message": f"{label} قريب الانتهاء أو منتهٍ"})
    for row in load_maintenance_plans():
        expiry = str(row.get("due_date", "")).strip()
        try:
            expiry_date = date.fromisoformat(expiry)
        except ValueError:
            continue
        if expiry_date <= cutoff and row.get("status") != "منجز":
            alerts.append({"type": "صيانة", "item": row.get("car_no", ""),
                           "date": expiry, "message": "موعد صيانة مستحق أو قريب"})
    return sorted(alerts, key=lambda item: item["date"])
