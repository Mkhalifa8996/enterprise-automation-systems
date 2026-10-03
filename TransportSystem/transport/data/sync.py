# -*- coding: utf-8 -*-
"""المزامنة السحابية مع Google Sheets وFirebase."""

import json, os, urllib
import urllib.error, urllib.parse, urllib.request
from .paths import FIREBASE_CONFIG_FILE, FIREBASE_DATABASE_URL, SYNC_CONFIG_FILE
from .core import _connect, _ensure_database, _invalidate_rows_cache

def get_sync_config():
    if not os.path.isfile(SYNC_CONFIG_FILE):
        return {"endpoint": "", "token": ""}
    try:
        with open(SYNC_CONFIG_FILE, "r", encoding="utf-8") as config_file:
            value = json.load(config_file)
    except (OSError, ValueError):
        return {"endpoint": "", "token": ""}
    return {"endpoint": str(value.get("endpoint", "")).strip(),
            "token": str(value.get("token", "")).strip()}

def configure_google_sync(endpoint, token=""):
    endpoint = str(endpoint or "").strip()
    if not endpoint.startswith(("https://", "http://")):
        raise ValueError("أدخل رابط Google Apps Script صحيحاً.")
    with open(SYNC_CONFIG_FILE, "w", encoding="utf-8") as config_file:
        json.dump({"endpoint": endpoint, "token": str(token or "").strip()},
                  config_file, ensure_ascii=False, indent=2)

def _local_sync_payload():
    _ensure_database()
    connection = _connect()
    try:
        records = [
            {"sheet_key": row[0], "record_key": row[1],
             "data": json.loads(row[2]), "updated_at": row[3]}
            for row in connection.execute(
                "SELECT sheet_key, record_key, data_json, updated_at FROM records")
        ]
        deleted = [
            {"sheet_key": row[0], "record_key": row[1], "deleted_at": row[2]}
            for row in connection.execute(
                "SELECT sheet_key, record_key, deleted_at FROM sync_tombstones")
        ]
    finally:
        connection.close()
    return {"records": records, "deleted": deleted}

def _apply_remote_sync_payload(payload):
    records = payload.get("records", []) if isinstance(payload, dict) else []
    deleted = payload.get("deleted", []) if isinstance(payload, dict) else []
    _ensure_database()
    connection = _connect()
    applied = 0
    try:
        for item in records:
            sheet_key = str(item.get("sheet_key", "")).strip()
            record_key = str(item.get("record_key", "")).strip()
            updated_at = str(item.get("updated_at", "")).strip()
            if not sheet_key or not record_key or not updated_at:
                continue
            current = connection.execute(
                "SELECT updated_at FROM records WHERE sheet_key = ? AND record_key = ?",
                (sheet_key, record_key)).fetchone()
            tombstone = connection.execute(
                "SELECT deleted_at FROM sync_tombstones "
                "WHERE sheet_key = ? AND record_key = ?",
                (sheet_key, record_key)).fetchone()
            if max(current[0] if current else "", tombstone[0] if tombstone else "") >= updated_at:
                continue
            connection.execute(
                "INSERT OR REPLACE INTO records "
                "(sheet_key, record_key, data_json, updated_at) VALUES (?, ?, ?, ?)",
                (sheet_key, record_key, json.dumps(item.get("data", {}), ensure_ascii=False),
                 updated_at))
            connection.execute(
                "DELETE FROM sync_tombstones WHERE sheet_key = ? AND record_key = ?",
                (sheet_key, record_key))
            applied += 1
        for item in deleted:
            sheet_key = str(item.get("sheet_key", "")).strip()
            record_key = str(item.get("record_key", "")).strip()
            deleted_at = str(item.get("deleted_at", "")).strip()
            if not sheet_key or not record_key or not deleted_at:
                continue
            current = connection.execute(
                "SELECT updated_at FROM records WHERE sheet_key = ? AND record_key = ?",
                (sheet_key, record_key)).fetchone()
            if current and current[0] >= deleted_at:
                continue
            connection.execute(
                "DELETE FROM records WHERE sheet_key = ? AND record_key = ?",
                (sheet_key, record_key))
            connection.execute(
                "INSERT OR REPLACE INTO sync_tombstones "
                "(sheet_key, record_key, deleted_at) VALUES (?, ?, ?)",
                (sheet_key, record_key, deleted_at))
            applied += 1
        connection.commit()
    finally:
        connection.close()
    _invalidate_rows_cache()
    return applied

def sync_with_google_sheets(timeout=20):
    config = get_sync_config()
    endpoint = config["endpoint"]
    if not endpoint:
        raise ValueError("لم يتم إعداد رابط المزامنة بعد.")
    query_url = endpoint
    if config["token"]:
        query_url += ("&" if "?" in query_url else "?") + \
            "token=" + urllib.parse.quote(config["token"])
    try:
        with urllib.request.urlopen(
                urllib.request.Request(query_url, method="GET"), timeout=timeout) as response:
            pulled_payload = json.loads(response.read().decode("utf-8"))
        pulled = _apply_remote_sync_payload(pulled_payload)
        body = json.dumps(_local_sync_payload(), ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            query_url, data=body, method="POST",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise RuntimeError(f"فشلت المزامنة: {exc}") from exc
    return {"pulled": pulled, "pushed": int(result.get("records", 0))}

def get_firebase_sync_config():
    """Load Firebase config from environment variables first, then config file."""
    # محاولة القراءة من متغيرات البيئة أولاً
    env_api_key = os.environ.get("FIREBASE_API_KEY", "").strip()
    env_email = os.environ.get("FIREBASE_EMAIL", "").strip()
    env_password = os.environ.get("FIREBASE_PASSWORD", "").strip()
    env_database_url = os.environ.get("FIREBASE_DATABASE_URL", FIREBASE_DATABASE_URL).strip().rstrip("/")
    env_refresh_token = os.environ.get("FIREBASE_REFRESH_TOKEN", "").strip()

    # إذا كانت متغيرات البيئة متوفرة، استخدامها
    if env_api_key:
        return {
            "database_url": env_database_url,
            "api_key": env_api_key,
            "email": env_email,
            "password": env_password,
            "refresh_token": env_refresh_token,
        }

    # محاولة القراءة من ملف التكوين
    if not os.path.isfile(FIREBASE_CONFIG_FILE):
        return {"database_url": FIREBASE_DATABASE_URL, "api_key": "", "email": "", "password": "",
                "refresh_token": ""}
    try:
        with open(FIREBASE_CONFIG_FILE, "r", encoding="utf-8") as config_file:
            value = json.load(config_file)
    except (OSError, ValueError):
        return {"database_url": FIREBASE_DATABASE_URL, "api_key": "", "email": "", "password": "",
                "refresh_token": ""}
    return {
        "database_url": str(value.get("database_url", FIREBASE_DATABASE_URL)).strip().rstrip("/"),
        "api_key": str(value.get("api_key", "")).strip(),
        "email": str(value.get("email", "")).strip(),
        "password": str(value.get("password", "")),
        "refresh_token": str(value.get("refresh_token", "")).strip(),
    }

def is_firebase_sync_configured(config=None):
    """Return whether either supported Firebase sign-in method is ready."""
    config = config or get_firebase_sync_config()
    if not config["database_url"] or not config["api_key"]:
        return False
    return bool(config["refresh_token"] or (
        config["email"] and config["password"]
    ))

def configure_firebase_sync(database_url, api_key, email, password=""):
    database_url = str(database_url or "").strip().rstrip("/")
    if not database_url.startswith("https://"):
        raise ValueError("أدخل رابط Firebase Realtime Database صحيحاً.")
    if not database_url.endswith(".firebaseio.com") and \
            ".firebasedatabase.app" not in database_url:
        raise ValueError("رابط Firebase يجب أن يكون رابط قاعدة Realtime Database.")
    if not str(api_key or "").strip():
        raise ValueError("أدخل Web API Key من إعدادات مشروع Firebase.")
    if not str(email or "").strip() or "@" not in str(email):
        raise ValueError("أدخل بريداً إلكترونياً صحيحاً.")
    if not str(password or "").strip():
        raise ValueError("أدخل كلمة مرور Firebase.")
    with open(FIREBASE_CONFIG_FILE, "w", encoding="utf-8") as config_file:
        json.dump({"database_url": database_url, "api_key": str(api_key).strip(),
                   "email": str(email).strip(), "password": str(password)},
                  config_file, ensure_ascii=False, indent=2)

def save_firebase_phone_session(database_url, api_key, refresh_token):
    database_url = str(database_url or "").strip().rstrip("/")
    api_key = str(api_key or "").strip()
    refresh_token = str(refresh_token or "").strip()
    if not database_url or not api_key or not refresh_token:
        raise ValueError("بيانات جلسة الهاتف غير مكتملة.")
    with open(FIREBASE_CONFIG_FILE, "w", encoding="utf-8") as config_file:
        json.dump({"database_url": database_url, "api_key": api_key,
                   "email": "", "password": "", "refresh_token": refresh_token},
                  config_file, ensure_ascii=False, indent=2)

def sync_with_firebase(timeout=20):
    """Synchronize the local store with Firebase Realtime Database.

    The payload is merged locally by timestamp before being written back.
    Therefore the record with the newest updated_at/deleted_at wins.
    """
    config = get_firebase_sync_config()
    if not config["database_url"]:
        raise ValueError("لم يتم إعداد Firebase بعد.")
    try:
        if config["refresh_token"]:
            auth_url = (
                "https://securetoken.googleapis.com/v1/token?key=" +
                urllib.parse.quote(config["api_key"])
            )
            auth_body = urllib.parse.urlencode({
                "grant_type": "refresh_token",
                "refresh_token": config["refresh_token"],
            }).encode("utf-8")
            auth_request = urllib.request.Request(
                auth_url, data=auth_body, method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"})
        else:
            if not config["api_key"] or not config["email"] or not config["password"]:
                raise ValueError("إعدادات Firebase أو بيانات الدخول غير مكتملة.")
            auth_url = (
                "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
                "?key=" + urllib.parse.quote(config["api_key"])
            )
            auth_body = json.dumps({
                "email": config["email"],
                "password": config["password"],
                "returnSecureToken": True,
            }).encode("utf-8")
            auth_request = urllib.request.Request(
                auth_url, data=auth_body, method="POST",
                headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(auth_request, timeout=timeout) as response:
            auth_result = json.loads(response.read().decode("utf-8"))
        id_token = str(auth_result.get("id_token") or auth_result.get("idToken") or "").strip()
        if not id_token:
            raise ValueError("لم يتم الحصول على رمز دخول Firebase.")
        endpoint = config["database_url"] + "/transport_sync.json?auth=" + \
            urllib.parse.quote(id_token)
        with urllib.request.urlopen(
                urllib.request.Request(endpoint, method="GET"), timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            remote = json.loads(raw) if raw and raw != "null" else {}
        pulled = _apply_remote_sync_payload(remote)
        body = json.dumps(_local_sync_payload(), ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            endpoint, data=body, method="PUT",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            details = json.loads(exc.read().decode("utf-8"))
            reason = str(details.get("error", {}).get("message", "")).strip()
        except (OSError, ValueError, UnicodeDecodeError):
            reason = ""
        suffix = f": {reason}" if reason else ""
        raise RuntimeError(f"فشلت مزامنة Firebase (HTTP {exc.code}){suffix}") from exc
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise RuntimeError(f"فشلت مزامنة Firebase: {exc}") from exc
    return {
        "pulled": pulled,
        "pushed": len(result.get("records", [])) if isinstance(result, dict) else 0,
    }
