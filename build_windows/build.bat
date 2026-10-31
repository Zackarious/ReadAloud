@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo   ReadAloud - Microsoft Windows Build & Packaging Script
echo =======================================================

cd /d "%~dp0\.."
set "REPO_ROOT=%CD%"

echo [1/5] Verifying build toolchain...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Python was not found in PATH. Please install Python 3.10+ (64-bit).
    exit /b 1
)

where glib-compile-resources >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [2/5] Compiling binary GResource bundle...
    glib-compile-resources src\readaloud.gresource.xml --target=src\readaloud.gresource --sourcedir=src
) else (
    echo [2/5] Warning: glib-compile-resources not found in PATH; skipping resource compilation.
)

echo [3/5] Synchronizing Windows dependencies...
python -m pip install -r requirements-windows.txt

echo [4/5] Executing PyInstaller build...
python -m PyInstaller build_windows\ReadAloud.spec --clean -y
if %ERRORLEVEL% neq 0 (
    echo Error: PyInstaller build failed.
    exit /b %ERRORLEVEL%
)

echo [5/5] Post-build runtime enforcement...
set "INTERNAL_DIR=dist\ReadAloud\_internal"
if exist "%INTERNAL_DIR%" (
    rem Overwrite modern MSVC 2022 runtimes from System32 to prevent 0xC0000005 crash
    for %%D in (msvcp140.dll msvcp140_1.dll vcruntime140.dll vcruntime140_1.dll) do (
        if exist "%SystemRoot%\System32\%%D" (
            copy /Y "%SystemRoot%\System32\%%D" "%INTERNAL_DIR%\" >nul
        )
    )

    rem Harvest espeak-ng-data phoneme tables and tashkeel
    for /f "delims=" %%I in ('python -c "import piper, pathlib; print(pathlib.Path(piper.__file__).parent)" 2^>nul') do (
        set "PIPER_PKG=%%I"
        if exist "!PIPER_PKG!\espeak-ng-data" (
            if not exist "%INTERNAL_DIR%\piper\espeak-ng-data" mkdir "%INTERNAL_DIR%\piper\espeak-ng-data"
            xcopy /E /I /Y "!PIPER_PKG!\espeak-ng-data\*" "%INTERNAL_DIR%\piper\espeak-ng-data\" >nul
        )
        if exist "!PIPER_PKG!\tashkeel" (
            if not exist "%INTERNAL_DIR%\piper\tashkeel" mkdir "%INTERNAL_DIR%\piper\tashkeel"
            xcopy /E /I /Y "!PIPER_PKG!\tashkeel\*" "%INTERNAL_DIR%\piper\tashkeel\" >nul
        )
    )
)

rem Deploy offline voice models for standalone portable distribution
if not exist "dist\ReadAloud\models" mkdir "dist\ReadAloud\models"
xcopy /E /I /Y "models\*" "dist\ReadAloud\models\" >nul

if exist "build_windows\ReadAloud.ico" (
    copy /Y "build_windows\ReadAloud.ico" "dist\ReadAloud\" >nul
)

echo.
echo =======================================================
echo   Standalone Application Ready:
echo   %REPO_ROOT%\dist\ReadAloud\ReadAloud.exe
echo =======================================================

rem Locate Inno Setup compiler
set "ISCC_PATH="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if defined ISCC_PATH (
    echo.
    echo Compiling Setup Installer with Inno Setup 6...
    "%ISCC_PATH%" "build_windows\installer.iss"
    if %ERRORLEVEL% equ 0 (
        echo Setup Installer successfully generated in %REPO_ROOT%\dist\
    ) else (
        echo Error: Inno Setup compilation failed.
    )
) else (
    echo.
    echo Notice: Inno Setup 6 ISCC.exe compiler not found in standard paths.
    echo To generate Setup Installer, install Inno Setup 6 and run:
    echo   ISCC.exe build_windows\installer.iss
)

exit /b 0
