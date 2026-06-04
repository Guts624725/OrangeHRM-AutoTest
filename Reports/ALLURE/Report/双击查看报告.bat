@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动 Allure 报告查看器...

if exist "C:\Program Files\Microsoft\Edge\Application\msedge.exe" (
    set "BROWSER=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
) else if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    set "BROWSER=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
) else if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "BROWSER=C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set "BROWSER=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else (
    echo 未检测到 Edge 或 Chrome 浏览器，请安装后重试。
    pause
    exit /b 1
)

set "TEMP_PROFILE=%TEMP%\allure_report_%RANDOM%"
mkdir "%TEMP_PROFILE%" 2>nul
start "" "%BROWSER%" --allow-file-access-from-files --user-data-dir="%TEMP_PROFILE%" --no-first-run --no-default-browser-check "%~dp0index.html"

echo 报告已打开，关闭浏览器即可。
timeout /t 3 >nul
