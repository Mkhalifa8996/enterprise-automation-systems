@echo off
chcp 65001 >nul 2>&1
cd /d "%~p0"
title بناء TransportApp.exe
color 0A

echo ============================================
echo    بناء برنامج إدارة شركة النقل
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [خطأ] لم يتم العثور على Python!
    echo يرجى تثبيت Python من: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] تثبيت المتطلبات...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [خطأ] فشل تثبيت المتطلبات!
    pause
    exit /b 1
)

echo [2/3] تنظيف البناء السابق...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo [3/3] جاري البناء... (قد يستغرق بضع دقائق)
python -m PyInstaller --clean --noconfirm TransportApp.spec
if errorlevel 1 (
    echo.
    echo [خطأ] فشل البناء!
    pause
    exit /b 1
)

echo.
echo ============================================
echo    تم البناء بنجاح
echo ============================================
echo    الملف التنفيذي: dist\TransportApp.exe
echo.
pause