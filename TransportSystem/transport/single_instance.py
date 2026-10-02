"""حماية البرنامج من التشغيل المزدوج.

يمنع فتح نسختين في وقت واحد على نفس قاعدة البيانات، لأن ذلك يسبب تلفاً
في ملف Excel عند تصديره في اللحظة نفسها، أو رسائل «قاعدة مقفلة».
القفل ملفّي ويستخدم إنشاء ذرّي، فإن مات البرنامج قفله يُعتبر قديماً
ويُحذف تلقائياً في التشغيل التالي.
"""
import json
import os
import time

LOCK_NAME = "transport_data.lock"


def lock_path(app_dir):
    return os.path.join(app_dir, LOCK_NAME)


def _read_lock(path):
    """يقرأ محتوى القفل، أو None إن لم يكن موجوداً/صالحاً."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read().strip()
        return json.loads(content) if content else None
    except (OSError, ValueError):
        return None


def _process_exists(pid):
    """هل العملية ما زالت تعمل؟"""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        # على ويندوز لا يوجد os.kill(pid, 0) موثوق، نستعمل ctypes.
        try:
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            try:
                code = ctypes.c_ulong()
                if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return False
                return code.value == STILL_ACTIVE
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            # عند فشل الفحص نعتبر العملية موجودة احتياطاً.
            return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def acquire(app_dir, stale_after_seconds=6 * 60 * 60):
    """يحاول حجز النسخة الوحيدة. يعيد (نجح, رسالة).

    عند النجاح تُكتب معلومات العملية داخل الملف، وعند الفشل تُعاد رسالة
    عربية واضحة يعرضها البرنامج قبل الخروج.
    """
    path = lock_path(app_dir)
    payload = {
        "pid": os.getpid(),
        "started_at": time.time(),
        "started_text": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    for attempt in range(2):
        try:
            # الإنشاء الذرّي: ينجح لعملية واحدة فقط في كل مرة.
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            existing = _read_lock(path)
            pid = (existing or {}).get("pid")
            age = time.time() - float((existing or {}).get("started_at") or 0)
            if existing is not None and _process_exists(pid):
                return False, (
                    f"البرنامج يعمل بالفعل الآن (رقم العملية {pid}).\n\n"
                    "لا يمكن فتح نسختين في الوقت نفسه لأن ذلك قد يضرّ البيانات.\n"
                    "استخدم النسخة المفتوحة، أو أغلقها أولاً ثم أعد التشغيل."
                )
            # قفل قديم من إغلاق غير طبيعي: نحذفه ونحاول مرة أخرى.
            try:
                if age > stale_after_seconds or existing is None or not _process_exists(pid):
                    os.unlink(path)
            except OSError:
                return False, ("تعذر تحرير ملف القفل. تأكد أن لديك صلاحية الكتابة "
                               "في مجلد البرنامج ثم أعد التشغيل.")
            continue
        except OSError as exc:
            return False, f"تعذر إنشاء ملف القفل: {exc}"
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
        except OSError:
            pass
        return True, ""
    return False, "تعذر حجز نسخة واحدة من البرنامج. أعد المحاولة."


def release(app_dir):
    """يحرّر القفل، مع التأكد أنه يخص هذه العملية."""
    path = lock_path(app_dir)
    existing = _read_lock(path)
    if existing is None:
        return False
    if int(existing.get("pid") or 0) != os.getpid():
        # القفل صار لغيرنا (حالة نادرة) — لا نلمسه.
        return False
    try:
        os.unlink(path)
    except OSError:
        return False
    return True


def is_locked_by_other(app_dir):
    """هل توجد نسخة أخرى تعمل الآن؟"""
    existing = _read_lock(lock_path(app_dir))
    if existing is None:
        return False
    return int(existing.get("pid") or 0) != os.getpid() and _process_exists(
        existing.get("pid"))
