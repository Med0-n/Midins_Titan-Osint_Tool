@echo off
echo Installing Midins Titan...
echo.

pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo Retrying with pre-built binaries...
    pip install --only-binary=:all: -r requirements.txt
)

echo.
echo Installation complete!
echo Run: python app.py
pause

