# Enterprise Automation Systems

مستودع يحتوي على مشروعين مستقلين:

| المجلد | المشروع | الوصف |
|---|---|---|
| [`TransportSystem/`](TransportSystem/) | نظام إدارة شركة النقل | تطبيق سطح مكتب لإدارة الرحلات والسائقين والفواتير والرواتب والتقارير |
| [`AlEstidamaInvoices/`](AlEstidamaInvoices/) | نظام الفواتير | نظام فواتير يعمل على ملف Excel |

كل مشروع مستقل تماماً: له ملفات تشغيله ومتطلباته ودليله.

---

## نظام إدارة شركة النقل

```bash
cd TransportSystem
pip install -r requirements.txt
python main.py
```

التفاصيل الكاملة في [`TransportSystem/README.md`](TransportSystem/README.md).

بنية المشروع مقسّمة إلى حزمة `transport/` بدل ملف واحد ضخم:

- `transport/app_*.py` — التطبيق مقسّم إلى طبقات (مزج بين الشاشات)
- `transport/ui_*.py` — عناصر الواجهة وشاشات الإدخال
- `transport/print_*.py` — الطباعة والفواتير والترويسة
- `transport/data/*.py` — طبقة قاعدة البيانات

**لا يحتوي المشروع على أي بيانات خاصة.** كل مستخدم يُدخل بيانات شركته ومشروع
Firebase الخاص به. التفاصيل في [FIREBASE_SETUP.md](TransportSystem/FIREBASE_SETUP.md).

للبناء كملف تنفيذي: `TransportSystem\build_exe.bat` ← ينتج `TransportApp.exe`.

---

## نظام الفواتير

```bash
cd AlEstidamaInvoices
python invoice_desktop_app.py
```

---

## ملاحظات

- [.gitignore](.gitignore) يستثني قواعد البيانات وتصديرات Excel والمرفقات
  وأي ملفات بيانات أو أسرار.
- [.gitattributes](.gitattributes) يوحّد نهايات الأسطر بين الأنظمة.