@echo off
chcp 65001 >nul 2>&1
cd /d "%~p0"
title تشغيل برنامج إدارة شركة النقل

echo جاري تشغيل برنامج إدارة شركة النقل...
echo.

REM Run the packaged executable if it exists
if exist "dist\TransportApp.exe" (
    start "" "dist\TransportApp.exe"
    exit /b 0
)

REM Otherwise fall back to running from source
python --version >nul 2>&1
if errorlevel 1 (
    echo [خطأ] لم يتم العثور على Python!
    echo ثبّت Python أولاً ثم أعد التشغيل
    pause
    exit /b 1
)

echo التحقق من المتطلبات...
pip install -q -r requirements.txt

python main.py