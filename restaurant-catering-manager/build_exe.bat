@echo off
rem بناء ملف exe توزيعي واحد للبرنامج المكتبي (يتطلب: pip install pyinstaller)
rem الملف الناتج في مجلد dist\ ويعمل على أي جهاز ويندوز دون تثبيت Python.
cd /d "%~dp0"
pyinstaller --onefile --windowed ^
  --name "RestaurantManager" ^
  --add-data "restaurant_data.xlsx;." ^
  restaurant_desktop_app.py
echo.
echo تم البناء: dist\RestaurantManager.exe
pause
