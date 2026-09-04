@echo off
rem DocVault 一键打包：前端构建 -> PyInstaller -> 单目录产物（内含 DocVault.exe）
setlocal
cd /d "%~dp0.."

echo [1/3] building frontend ...
pushd frontend
call npm run build
if errorlevel 1 goto :fail
popd

echo [2/3] ensuring pyinstaller ...
python -c "import PyInstaller" 2>nul || python -m pip install pyinstaller

echo [3/3] packaging ...
python -m PyInstaller --noconfirm --clean DocVault.spec
if errorlevel 1 goto :fail

copy /y backend\projects.json dist\projects.json >nul
echo.
echo OK =^> dist\DocVault.exe
exit /b 0

:fail
popd 2>nul
echo BUILD FAILED
exit /b 1
