@echo off
echo Building Dell Fan Control executable...

REM Install required packages
echo Installing required packages...
pip install -r requirements.txt

REM Build the executable
echo Building executable with PyInstaller...
pyinstaller --onefile --windowed --name "Dell_Fan_Control" --icon=fan.ico dell_fan_control.py

REM Copy ipmitool and create IPMI folder in dist
echo Setting up IPMI folder...
if not exist "dist\IPMI" mkdir "dist\IPMI"
if exist "C:\IPMI\ipmitool.exe" (
    copy "C:\IPMI\ipmitool.exe" "dist\IPMI\"
    echo ipmitool.exe copied to dist\IPMI\
) else (
    echo Warning: ipmitool.exe not found in C:\IPMI\
    echo Please copy ipmitool.exe to dist\IPMI\ manually
)

echo.
echo Build complete! Executable is in the 'dist' folder.
echo Make sure to copy ipmitool.exe to the IPMI folder if not done automatically.
pause