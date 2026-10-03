# -*- coding: utf-8 -*-
"""الاتصال بقاعدة البيانات وإنشاء جداولها.

قاعدة البيانات (SQLite) هي مصدر البيانات الأساسي. ملف إكسل لم يعد
المصدر، بل نسخة مرآة تُحدَّث بعد كل عملية تعديل (انظر excel_mirror.py).
"""

import sqlite3

from .. import config


class SaveError(Exception):
    """يُطلق عند تعذّر الحفظ على قاعدة البيانات """


# مخطط الجداول. ملاحظات:
# - invoice_items تُخزَّن تسميات البنود المخصّصة لكل فاتورة (تسمية عربية
#   وأخرى إنجليزية) على حدة، لأن هذه التسميات قد تُعدَّل لكل فاتورة.
# - payment_invoices تحفظ ترتيب الفواتير المسدَّدة بالدفعة كما اختاره
#   المستخدم، لأن حساب التوزيع يعتمد على هذا الترتيب (FIFO).
SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    name         TEXT PRIMARY KEY,
    phone        TEXT NOT NULL DEFAULT '',
    address      TEXT NOT NULL DEFAULT '',
    notes        TEXT NOT NULL DEFAULT '',
    company_code TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS invoices (
    invno          TEXT PRIMARY KEY,
    date           TEXT NOT NULL DEFAULT '',
    customer       TEXT NOT NULL DEFAULT '',
    declno         TEXT NOT NULL DEFAULT '',
    decldate       TEXT NOT NULL DEFAULT '',
    port           TEXT NOT NULL DEFAULT '',
    containercount TEXT NOT NULL DEFAULT '',
    goodstype      TEXT NOT NULL DEFAULT '',
    origin         TEXT NOT NULL DEFAULT '',
    notes          TEXT NOT NULL DEFAULT '',
    total          REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS invoice_items (
    invno     TEXT    NOT NULL,
    idx       INTEGER NOT NULL,
    label_ar  TEXT    NOT NULL DEFAULT '',
    label_en  TEXT    NOT NULL DEFAULT '',
    dinar     INTEGER NOT NULL DEFAULT 0,
    fils      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (invno, idx),
    FOREIGN KEY (invno) REFERENCES invoices(invno) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS payments (
    id       TEXT PRIMARY KEY,
    customer TEXT NOT NULL DEFAULT '',
    date     TEXT NOT NULL DEFAULT '',
    amount   REAL NOT NULL DEFAULT 0,
    notes    TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS payment_invoices (
    payment_id TEXT    NOT NULL,
    invno      TEXT    NOT NULL,
    position   INTEGER NOT NULL,
    PRIMARY KEY (payment_id, position),
    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer);
CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer);
CREATE INDEX IF NOT EXISTS idx_items_invno ON invoice_items(invno);
"""


def _connect():
    """فتح اتصال محمي بقاعدة البيانات.

    يفعّل وضع WAL ودوام متزامن قوي وانتظار عند الانشغال، مما يحمي البيانات
    من فقدانها عند انقطاع الكهرباء أو إغلاق البرنامج فجأة، ويمنع خطأ
    «قاعدة البيانات مقفلة» عند فتح نسختين في نفس الوقت.

    يُقرأ المسار من `config` عند كل استدعاء (لا عند الاستيراد) ليبقى هناك
    مصدر واحد للمسار، وليُمكن توجيهه في الاختبارات عبر متغيّر البيئة.
    """
    connection = sqlite3.connect(config.DB_FILE, timeout=30.0)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA busy_timeout = 30000")
        current = connection.execute("PRAGMA journal_mode").fetchone()[0]
        if str(current).lower() != "wal":
            try:
                connection.execute("PRAGMA journal_mode = WAL")
            except sqlite3.DatabaseError:
                # بعض الأنظمة (شبكة أو قرص للقراءة فقط) لا تدعم WAL،
                # فنكمل بالإعدادات الأخرى دون إسقاط العملية.
                pass
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA foreign_keys = ON")
    except sqlite3.DatabaseError:
        pass
    return connection


def ensure_database():
    """ينشئ ملف قاعدة البيانات وجداوله إن لم تكن موجودة، ويعيد اتصالاً مفتوحاً."""
    connection = _connect()
    try:
        connection.executescript(SCHEMA)
        connection.commit()
    except sqlite3.Error as exc:
        connection.close()
        raise SaveError(
            "تعذّر تجهيز قاعدة البيانات.\n"
            f"تأكد أن البرنامج يملك صلاحية الكتابة في:\n{config.DB_FILE}\n\n{exc}"
        )
    return connection