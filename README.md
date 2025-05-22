# Dell Fan Control - Setup Instructions

## Prerequisites

1. **Python 3.7+** installed on your system
2. **ipmitool.exe** placed in `C:\IPMI\`

## Building the Executable

### Method 1: Using the Build Script (Easiest)

1. Save all files in the same folder:
   - `dell_fan_control.py`
   - `requirements.txt`
   - `build_exe.bat`

2. Run `build_exe.bat` as Administrator (right-click → "Run as administrator")

3. The executable will be created in the `dist` folder

### Method 2: Manual Build

1. Install required packages:
   ```bash
   pip install keyring pyinstaller pystray pillow
   ```

2. Build the executable:
   ```bash
   pyinstaller --onefile --windowed --name "Dell_Fan_Control" dell_fan_control.py
   ```

3. Create IPMI folder and copy ipmitool:
   ```bash
   mkdir dist\IPMI
   copy C:\IPMI\ipmitool.exe dist\IPMI\
   ```

## New Features Added (v1.5)

### System Tray Integration
- **Minimize to Tray**: Closing the window minimizes to system tray instead of exiting
- **Tray Menu**: Right-click the tray icon for quick actions:
  - Show/Hide window
  - Get temperature
  - Enable/Disable dynamic control
  - Exit application
- **Quick Access**: Control your server fans without keeping the window open

### Exit Options
- **Exit Application Button**: Completely closes the application (in the UI)
- **File Menu**: New File menu with minimize and exit options
- **Tray Context Menu**: Exit option in the tray right-click menu

### Secure Credential Storage
- **Save Credentials**: Stores your iDRAC IP, username, and password securely in Windows Credential Manager
- **Load Credentials**: Automatically loads saved credentials when you start the app
- **Clear Saved**: Removes stored credentials from the system

## How to Use System Tray

### Minimizing to Tray
- **Method 1**: Click the X button (window close button)
- **Method 2**: Use File → Minimize to Tray
- The application will disappear from the taskbar but continue running in the system tray

### Accessing from Tray
- **Show Window**: Left-click the tray icon OR right-click → Show
- **Quick Actions**: Right-click the tray icon for:
  - Get current temperature
  - Enable/disable dynamic control
  - Exit completely

### Completely Exiting
- **From Window**: Click "Exit Application" button OR File → Exit
- **From Tray**: Right-click tray icon → Exit

## Features Overview

### 🔐 **Secure Credential Storage**
- Uses Windows Credential Manager (same as browsers)
- Automatically loads credentials on startup
- Encrypted password storage

### 🎯 **System Tray Integration**
- Minimize to tray instead of closing
- Quick actions from tray menu
- Background monitoring while minimized

### 🌡️ **Temperature Control**
- Full 0-100% fan speed range
- Automatic temperature-based control
- Real-time monitoring and logging

## Distribution

The executable in the `dist` folder is completely portable:
- Copy the entire `dist` folder to any Windows machine
- Make sure `IPMI\ipmitool.exe` is included
- No Python installation required on target machine

## File Structure After Build
```
dist/
├── Dell_Fan_Control.exe
└── IPMI/
    └── ipmitool.exe
```

## Troubleshooting

### "Keyring not available" message
- Run: `pip install keyring`
- Rebuild the executable

### "System tray not available" 
- Run: `pip install pystray pillow`
- Rebuild the executable
- App will still work but won't minimize to tray

### "ipmitool.exe not found"
- Ensure `ipmitool.exe` is in the `IPMI` folder next to the executable
- Or place it in `C:\IPMI\`

### Tray Icon Not Appearing
- Check Windows notification area settings
- Look for hidden icons in the system tray
- Some Windows versions hide new tray icons by default

### Antivirus False Positives
- Some antivirus software may flag PyInstaller executables
- Add exception for the executable if needed
- This is a common false positive with Python executables

## Security Notes

- Credentials are stored using Windows Credential Manager
- Only your Windows user account can access stored credentials
- Password is encrypted by the operating system
- Same security level as storing passwords in web browsers
- System tray functionality doesn't store any additional data