@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ================================================================
echo   بناء ملف تشغيل (.exe) - نظام فواتير شركة التخليص الجمركي للفوترة
echo ================================================================
echo.

rem ---- التأكد من وجود بايثون ----
where python >nul 2>nul
if errorlevel 1 (
    echo [خطأ] لم يتم العثور على بايثون على هذا الجهاز.
    echo رجاءً ثبّت بايثون 3.9 أو أحدث من https://python.org
    echo مهم جداً: فعّل خيار "Add python.exe to PATH" أثناء التثبيت.
    echo.
    pause
    exit /b 1
)

rem ---- التأكد من وجود ملفات المشروع ----
if not exist "main.py" (
    echo [خطأ] لم أجد main.py في نفس مجلد هذا الملف.
    echo انسخ هذا الملف bat بجانب main.py ثم أعد المحاولة.
    pause
    exit /b 1
)
if not exist "customs_clearance_billing\__init__.py" (
    echo [خطأ] لم أجد مجلد customs_clearance_billing بجانب main.py.
    pause
    exit /b 1
)

echo [1/3] تثبيت المكتبات المطلوبة (openpyxl, pyinstaller)...
python -m pip install --upgrade pip >nul 2>nul
python -m pip install --upgrade openpyxl pyinstaller
if errorlevel 1 (
    echo [خطأ] فشل تثبيت المكتبات. تأكد من اتصال الإنترنت وحاول مجدداً.
    pause
    exit /b 1
)

echo.
echo [2/3] تجهيز الأيقونة إن وُجدت...
set ICON_ARG=
if exist "icon.ico" set ICON_ARG=--icon="icon.ico"

echo.
echo [3/3] بناء الملف التنفيذي (قد يستغرق دقيقة أو أكثر)...
if exist "customs-clearance-billing.spec" (
    python -m PyInstaller --noconfirm --clean customs-clearance-billing.spec
) else (
    set ADD_DATA=
    if exist "icon.png" set ADD_DATA=!ADD_DATA! --add-data "icon.png;."
    if exist "logo.png" set ADD_DATA=!ADD_DATA! --add-data "logo.png;."
    python -m PyInstaller --noconfirm --clean --onefile --windowed ^
        --name "customs-clearance-billing" ^
        %ICON_ARG% %ADD_DATA% ^
        main.py
)

if errorlevel 1 (
    echo.
    echo [خطأ] فشلت عملية البناء. راجع الرسائل أعلاه لمعرفة السبب.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo   تم بنجاح! ستجد الملف التنفيذي هنا:
echo   dist\customs-clearance-billing.exe
echo.
echo   انسخ هذا الملف إلى أي جهاز ويندوز وشغّله مباشرة - لا يحتاج
echo   تثبيت بايثون على الجهاز الآخر. عند أول تشغيل سيُنشئ
echo   customs_clearance_billing.db و data.xlsx بجانبه تلقائياً، وينقل أي بيانات
echo   موجودة في data.xlsx إلى قاعدة البيانات.
echo ================================================================
echo.
pause
