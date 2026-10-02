# -*- coding: utf-8 -*-
"""المستخدمون والصلاحيات وكلمات المرور."""

import secrets
from .core import _connect, _current_role, _ensure_database, _hash_password, set_current_user

def authenticate_user(username, password):
    _ensure_database()
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT role, password_hash, active FROM app_users WHERE username = ?",
            (str(username).strip(),),
        ).fetchone()
    finally:
        connection.close()
    if not row or not row[2] or "$" not in row[1]:
        return False
    salt, expected = row[1].split("$", 1)
    actual = _hash_password(password, salt).split("$", 1)[1]
    if not secrets.compare_digest(actual, expected):
        return False
    set_current_user(username, row[0])
    return True

def load_users():
    _ensure_database()
    connection = _connect()
    try:
        return [{"username": row[0], "role": row[1], "active": bool(row[2])}
                for row in connection.execute(
                    "SELECT username, role, active FROM app_users ORDER BY username"
                )]
    finally:
        connection.close()

def save_user(username, role, password=None, active=True):
    if _current_role != "مدير":
        raise PermissionError("إدارة المستخدمين متاحة للمدير فقط.")
    username, role = str(username).strip(), str(role).strip()
    if not username or role not in ("مدير", "محاسب", "إدخال"):
        raise ValueError("اسم المستخدم والصلاحية غير صحيحين.")
    _ensure_database()
    if password is None:
        password = "ChangeMe123!"
    connection = _connect()
    try:
        connection.execute(
            "INSERT OR REPLACE INTO app_users "
            "(username, role, password_hash, active) VALUES (?, ?, ?, ?)",
            (username, role, _hash_password(password), 1 if active else 0),
        )
        connection.commit()
    finally:
        connection.close()
