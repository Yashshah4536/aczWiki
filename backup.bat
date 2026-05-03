@echo off
title AczWiki Backup

cd /d "%~dp0"

:: Get today's date in YYYY-MM-DD format
for /f "tokens=2 delims==" %%a in ('wmic os get LocalDateTime /value') do set DT=%%a
set TODAY=%DT:~0,4%-%DT:~4,2%-%DT:~6,2%

set BACKUP_DIR=backups\%TODAY%

echo.
echo  ================================================
echo   AczWiki Backup
echo   Destination: %BACKUP_DIR%
echo  ================================================
echo.

:: Create backup directory
if not exist "backups" mkdir backups
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

:: Back up the database
if exist "knowledge_base.db" (
    copy /Y "knowledge_base.db" "%BACKUP_DIR%\knowledge_base.db" >nul
    echo   [OK] knowledge_base.db copied.
) else (
    echo   [SKIP] knowledge_base.db not found.
)

:: Back up the uploads folder
if exist "uploads" (
    xcopy /E /I /Y "uploads" "%BACKUP_DIR%\uploads" >nul
    echo   [OK] uploads\ folder copied.
) else (
    echo   [SKIP] uploads\ folder not found.
)

echo.
echo   Backup complete: %BACKUP_DIR%
echo.
echo   Tip: Schedule this script in Windows Task Scheduler
echo        to run automatically every day.
echo.
echo  ================================================
echo.
pause
