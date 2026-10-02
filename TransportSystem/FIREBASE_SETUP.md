# إعداد المزامنة السحابية مع Firebase

البرنامج **لا يحتوي على أي بيانات Firebase**. كل مستخدم يدخل بيانات مشروعه
الخاص، ولا تُشارك هذه البيانات مع أحد.

## أين تُحفظ بياناتك؟

عند أول تشغيل تظهر نافذة **«إعداد مزامنة Firebase»**. تُحفظ ما تُدخله في ملف
`firebase_sync_config.json` **بجانب البرنامج على جهازك أنت**، وهو مستبعَد من Git.

لحذفها نهائياً: احذف الملف ثم أعد تشغيل البرنامج.

---

## أولاً: أنشئ مشروع Firebase خاصاً بك

1. افتح [Firebase Console](https://console.firebase.google.com) وأنشئ مشروعاً
   جديداً باسمك.
2. من **Build → Realtime Database** أنشئ قاعدة بيانات.
3. انسخ **رابط القاعدة** — يبدو هكذا:

   ```
   https://MY-PROJECT-default-rtdb.europe-west1.firebasedatabase.app
   ```

## ثانياً: فعّل تسجيل الدخول

من **Build → Authentication → Sign-in method** فعّل أحد الخيارين:

- **Email/Password** — الأبسط، وهو الافتراضي في نافذة الإعداد.
- **Phone** — متاح من زر «تسجيل برقم الهاتف» داخل النافذة نفسها.

أضف مستخدماً من **Authentication → Users** إن اخترت Email/Password.

## ثالثاً: انسخ Web API Key

من **Project settings (⚙) → General → Your apps → Web API Key** انسخ المفتاح.

## رابعاً: اضبط قواعد قاعدة البيانات

في **Realtime Database → Rules** الصق:

```json
{
  "rules": {
    "transport_sync": {
      ".read": "auth != null",
      ".write": "auth != null"
    }
  }
}
```

> بدون هذه القواعد سيفشل المزامنة بخطأ `Permission denied`.

## خامساً: أدخل بياناتك في البرنامج

اضغط **حفظ ومزامنة** بعد إدخال:

| الحقل | القيمة |
|---|---|
| رابط Firebase Realtime Database | الرابط المنسوخ في الخطوة الأولى |
| Web API Key | المفتاح المنسوخ في الخطوة الثالثة |
| البريد الإلكتروني | مستخدم Firebase الذي أنشأته |
| كلمة مرور Firebase | كلمة مرور ذلك المستخدم |

تُحفظ محلياً وتُستخدم في كل تشغيل تالٍ.

---

## خيار بديل: الإعداد عبر ملف `.env` (بدون واجهة)

انسخ `.env.example` إلى `.env` ثم املأ:

```
FIREBASE_API_KEY=...
FIREBASE_EMAIL=...
FIREBASE_PASSWORD=...
FIREBASE_DATABASE_URL=https://MY-PROJECT-default-rtdb.europe-west1.firebasedatabase.app
```

يُقرأ ملف `.env` تلقائياً عند التشغيل.

---

## أخطاء شائعة

| الخطأ | السبب |
|---|---|
| `Permission denied` | قواعد قاعدة البيانات غير مضبوطة (راجع الخطوة الرابعة) |
| `400 Invalid API key` | Web API Key غير صحيح أو نُسخ من المكان الخطأ |
| `EMAIL_NOT_FOUND` | المستخدم غير موجود في Authentication → Users |
| `INVALID_LOGIN_CREDENTIALS` | البريد أو كلمة المرور غير صحيحة |
| فشل الاتصال | رابط القاعدة ناقص أو لا ينتهي بـ `firebasedatabase.app` |