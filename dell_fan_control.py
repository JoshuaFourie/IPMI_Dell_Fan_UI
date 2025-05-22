import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import threading
import time
from datetime import datetime
import re
import os
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False

class DellFanController:
    def __init__(self, root):
        self.root = root
        self.root.title("Dell Server Fan Control")
        self.root.geometry("600x700")
        self.root.resizable(True, True)
        
        # Variables
        self.idrac_ip = tk.StringVar()
        self.idrac_user = tk.StringVar()
        self.idrac_password = tk.StringVar()
        self.temp_threshold = tk.StringVar(value="45")
        self.temp_sensor = tk.StringVar(value="0Eh")  # CPU 1 Temp
        self.auto_mode = tk.BooleanVar(value=False)
        self.monitoring = False
        
        # Fan speed mappings - Full range 0-100%
        self.fan_speeds = {}
        for i in range(0, 101):
            self.fan_speeds[i] = f"0x{i:02x}"
        
        # Set ipmitool path
        self.ipmitool_path = self.find_ipmitool()
        
        # Keyring service name for storing credentials
        self.service_name = "Dell_Fan_Control"
        
        # System tray variables
        self.tray_icon = None
        self.is_closing = False
        
        self.setup_ui()
        
        # Check if ipmitool was found
        if not self.ipmitool_path:
            self.log_message("⚠ Warning: ipmitool.exe not found in C:\\IPMI\\ or system PATH")
            messagebox.showwarning("ipmitool Not Found", 
                                 "ipmitool.exe was not found in C:\\IPMI\\ or system PATH.\n"
                                 "Please ensure ipmitool.exe is placed in C:\\IPMI\\")
        else:
            self.log_message(f"✓ Found ipmitool at: {self.ipmitool_path}")
            
        # Load saved credentials
        self.load_credentials()
        
        # Setup window close behavior
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Create system tray if available
        if PYSTRAY_AVAILABLE:
            self.setup_system_tray()
            
    def find_ipmitool(self):
        """Find ipmitool executable in IPMI folder or system PATH"""
        # First check the IPMI folder in root
        ipmi_path = "C:\\IPMI\\ipmitool.exe"
        if os.path.exists(ipmi_path):
            return ipmi_path
            
        # Check if it's in the same directory as the script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_ipmi_path = os.path.join(script_dir, "IPMI", "ipmitool.exe")
        if os.path.exists(local_ipmi_path):
            return local_ipmi_path
            
        # Check system PATH
        try:
            result = subprocess.run(["where", "ipmitool"], capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                return "ipmitool"  # Found in PATH
        except:
            pass
            
        return None
        
    def save_credentials(self):
        """Save credentials to system keyring"""
        if not KEYRING_AVAILABLE:
            messagebox.showerror("Error", "Keyring not available. Install with: pip install keyring")
            return
            
        if not self.idrac_ip.get() or not self.idrac_user.get() or not self.idrac_password.get():
            messagebox.showwarning("Warning", "Please fill in all connection settings before saving")
            return
            
        try:
            # Save IP and username in a combined key
            keyring.set_password(self.service_name, "connection_info", f"{self.idrac_ip.get()}|{self.idrac_user.get()}")
            # Save password separately for security
            keyring.set_password(self.service_name, self.idrac_user.get(), self.idrac_password.get())
            
            self.log_message("✓ Credentials saved securely")
            messagebox.showinfo("Success", "Credentials saved securely to system keyring")
        except Exception as e:
            self.log_message(f"✗ Failed to save credentials: {e}")
            messagebox.showerror("Error", f"Failed to save credentials: {e}")
            
    def load_credentials(self):
        """Load credentials from system keyring"""
        if not KEYRING_AVAILABLE:
            return
            
        try:
            # Load connection info
            conn_info = keyring.get_password(self.service_name, "connection_info")
            if conn_info:
                parts = conn_info.split("|")
                if len(parts) == 2:
                    ip, username = parts
                    self.idrac_ip.set(ip)
                    self.idrac_user.set(username)
                    
                    # Load password
                    password = keyring.get_password(self.service_name, username)
                    if password:
                        self.idrac_password.set(password)
                        self.log_message("✓ Credentials loaded from keyring")
        except Exception as e:
            self.log_message(f"Note: Could not load saved credentials: {e}")
            
    def clear_credentials(self):
        """Clear saved credentials from keyring"""
        if not KEYRING_AVAILABLE:
            return
            
        if messagebox.askyesno("Confirm", "Are you sure you want to clear saved credentials?"):
            try:
                # Get current username to clear password
                username = self.idrac_user.get()
                if username:
                    keyring.delete_password(self.service_name, username)
                    
                # Clear connection info
                keyring.delete_password(self.service_name, "connection_info")
                
                # Clear form fields
                self.idrac_ip.set("")
                self.idrac_user.set("")
                self.idrac_password.set("")
                
                self.log_message("✓ Saved credentials cleared")
                messagebox.showinfo("Success", "Saved credentials cleared")
            except Exception as e:
                self.log_message(f"Note: {e}")
                messagebox.showinfo("Info", "No saved credentials found or already cleared")
                
    def create_tray_icon(self):
        """Create a simple icon for the system tray"""
        # Create a simple fan icon
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Draw a simple fan icon
        center = (width // 2, height // 2)
        radius = width // 3
        
        # Fan blades
        for i in range(4):
            angle = i * 90
            blade_length = radius - 5
            x1 = center[0] + (blade_length * 0.3) * (1 if i % 2 == 0 else -1)
            y1 = center[1] + (blade_length * 0.3) * (1 if i < 2 else -1)
            x2 = center[0] + blade_length * (1 if i % 2 == 0 else -1)
            y2 = center[1] + blade_length * (1 if i < 2 else -1)
            draw.ellipse([x1-8, y1-8, x2+8, y2+8], fill='blue')
        
        # Center hub
        draw.ellipse([center[0]-6, center[1]-6, center[0]+6, center[1]+6], fill='black')
        
        return image
        
    def setup_system_tray(self):
        """Setup system tray icon and menu"""
        if not PYSTRAY_AVAILABLE:
            return
            
        # Create tray icon
        icon_image = self.create_tray_icon()
        
        menu = pystray.Menu(
            item('Show', self.show_window),
            item('Temperature', self.tray_get_temperature),
            item('Enable Dynamic Control', self.tray_enable_dynamic),
            item('Disable Dynamic Control', self.tray_disable_dynamic),
            pystray.Menu.SEPARATOR,
            item('Exit', self.exit_application)
        )
        
        self.tray_icon = pystray.Icon("Dell Fan Control", icon_image, "Dell Fan Control", menu)
        
    def on_closing(self):
        """Handle window close event - minimize to tray instead of closing"""
        if PYSTRAY_AVAILABLE and not self.is_closing:
            self.hide_window()
        else:
            self.exit_application()
            
    def hide_window(self):
        """Hide window to system tray"""
        self.root.withdraw()
        if self.tray_icon and not self.tray_icon.visible:
            # Start tray icon in a separate thread
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            
    def show_window(self, icon=None, item=None):
        """Show window from system tray"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        if self.tray_icon and self.tray_icon.visible:
            self.tray_icon.stop()
            
    def tray_get_temperature(self, icon=None, item=None):
        """Get temperature from tray menu"""
        self.get_temperature()
        
    def tray_enable_dynamic(self, icon=None, item=None):
        """Enable dynamic control from tray menu"""
        self.enable_dynamic_control()
        
    def tray_disable_dynamic(self, icon=None, item=None):
        """Disable dynamic control from tray menu"""
        self.disable_dynamic_control()
        
    def exit_application(self):
        """Completely exit the application"""
        self.is_closing = True
        
        # Stop monitoring if running
        if self.monitoring:
            self.monitoring = False
            
        # Stop tray icon
        if self.tray_icon and self.tray_icon.visible:
            self.tray_icon.stop()
            
        # Destroy the window
        self.root.quit()
        self.root.destroy()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Connection Settings
        conn_frame = ttk.LabelFrame(main_frame, text="iDRAC Connection Settings", padding="10")
        conn_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        conn_frame.columnconfigure(1, weight=1)
        
        ttk.Label(conn_frame, text="iDRAC IP:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Entry(conn_frame, textvariable=self.idrac_ip, width=30).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Label(conn_frame, text="Username:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Entry(conn_frame, textvariable=self.idrac_user, width=30).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=(5, 0))
        
        ttk.Label(conn_frame, text="Password:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Entry(conn_frame, textvariable=self.idrac_password, show="*", width=30).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=(5, 0))
        
        # Save/Load credentials buttons
        cred_frame = ttk.Frame(conn_frame)
        cred_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        
        if KEYRING_AVAILABLE:
            ttk.Button(cred_frame, text="Save Credentials", command=self.save_credentials).grid(row=0, column=0, padx=(0, 5))
            ttk.Button(cred_frame, text="Load Credentials", command=self.load_credentials).grid(row=0, column=1, padx=(0, 5))
            ttk.Button(cred_frame, text="Clear Saved", command=self.clear_credentials).grid(row=0, column=2, padx=(0, 5))
        else:
            ttk.Label(cred_frame, text="Install 'keyring' package to save credentials", foreground="orange").grid(row=0, column=0)
        
        # Temperature Settings
        temp_frame = ttk.LabelFrame(main_frame, text="Temperature Settings", padding="10")
        temp_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        temp_frame.columnconfigure(1, weight=1)
        
        ttk.Label(temp_frame, text="Temperature Sensor:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        sensor_combo = ttk.Combobox(temp_frame, textvariable=self.temp_sensor, values=["04h", "01h", "0Eh", "0Fh"], state="readonly")
        sensor_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 5))
        
        ttk.Label(temp_frame, text="Threshold (°C):").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Entry(temp_frame, textvariable=self.temp_threshold, width=10).grid(row=1, column=1, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        
        # Control Buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10))
        
        ttk.Button(control_frame, text="Test Connection", command=self.test_connection).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(control_frame, text="Get Temperature", command=self.get_temperature).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(control_frame, text="Get All Sensors", command=self.get_all_sensors).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(control_frame, text="Chassis Status", command=self.get_chassis_status).grid(row=0, column=3, padx=(0, 5))
        
        # Second row of control buttons
        control_frame2 = ttk.Frame(main_frame)
        control_frame2.grid(row=3, column=0, columnspan=2, pady=(5, 10))
        
        ttk.Button(control_frame2, text="Enable Dynamic Control", command=self.enable_dynamic_control).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(control_frame2, text="Disable Dynamic Control", command=self.disable_dynamic_control).grid(row=0, column=1, padx=(0, 5))
        
        # Manual Fan Control
        fan_frame = ttk.LabelFrame(main_frame, text="Manual Fan Control", padding="10")
        fan_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        fan_frame.columnconfigure(1, weight=1)
        
        ttk.Label(fan_frame, text="Fan Speed (%):").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.fan_speed_var = tk.StringVar(value="20")
        fan_scale = ttk.Scale(fan_frame, from_=0, to=100, variable=self.fan_speed_var, orient=tk.HORIZONTAL)
        fan_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        fan_scale.configure(command=self.update_fan_speed_label)
        
        self.fan_speed_label = ttk.Label(fan_frame, text="20%")
        self.fan_speed_label.grid(row=0, column=2, padx=(5, 0))
        
        ttk.Button(fan_frame, text="Set Fan Speed", command=self.set_manual_fan_speed).grid(row=1, column=0, columnspan=3, pady=(10, 0))
        
        # Automatic Mode
        auto_frame = ttk.LabelFrame(main_frame, text="Automatic Mode", padding="10")
        auto_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Checkbutton(auto_frame, text="Enable Automatic Fan Control", variable=self.auto_mode, command=self.toggle_auto_mode).grid(row=0, column=0, sticky=tk.W)
        
        self.auto_button = ttk.Button(auto_frame, text="Start Monitoring", command=self.toggle_monitoring)
        self.auto_button.grid(row=1, column=0, pady=(5, 0))
        
        # Exit button
        exit_frame = ttk.Frame(auto_frame)
        exit_frame.grid(row=2, column=0, pady=(10, 0))
        ttk.Button(exit_frame, text="Exit Application", command=self.exit_application).grid(row=0, column=0)
        
        # Status Display
        status_frame = ttk.LabelFrame(main_frame, text="Status & Log", padding="10")
        status_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(1, weight=1)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=15, width=70)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure main frame row weight
        main_frame.rowconfigure(6, weight=1)
        
    def log_message(self, message):
        """Add message to status log with timestamp"""
        timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.status_text.insert(tk.END, log_entry)
        self.status_text.see(tk.END)
        self.root.update_idletasks()
        
    def update_fan_speed_label(self, value):
        """Update fan speed label when scale changes"""
        speed = int(float(value))
        self.fan_speed_label.config(text=f"{speed}%")
        
    def run_ipmitool_command(self, command):
        """Run ipmitool command and return output"""
        if not self.ipmitool_path:
            return False, "", "ipmitool.exe not found"
            
        try:
            full_command = [
                self.ipmitool_path, "-I", "lanplus", 
                "-H", self.idrac_ip.get(),
                "-U", self.idrac_user.get(),
                "-P", self.idrac_password.get()
            ] + command
            
            result = subprocess.run(full_command, capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except FileNotFoundError:
            return False, "", f"ipmitool.exe not found at: {self.ipmitool_path}"
        except Exception as e:
            return False, "", str(e)
            
    def test_connection(self):
        """Test connection to iDRAC"""
        if not self.validate_connection_settings():
            return
            
        self.log_message("Testing connection to iDRAC...")
        
        def test_thread():
            success, stdout, stderr = self.run_ipmitool_command(["sdr", "list"])
            if success:
                self.log_message("✓ Connection successful!")
            else:
                self.log_message(f"✗ Connection failed: {stderr}")
                
        threading.Thread(target=test_thread, daemon=True).start()
        
    def validate_connection_settings(self):
        """Validate that connection settings are provided"""
        if not self.idrac_ip.get() or not self.idrac_user.get() or not self.idrac_password.get():
            messagebox.showerror("Error", "Please fill in all connection settings")
            return False
        return True
        
    def get_temperature(self):
        """Get current temperature from the selected sensor"""
        if not self.validate_connection_settings():
            return
            
        self.log_message(f"Getting temperature from sensor {self.temp_sensor.get()}...")
        
        def temp_thread():
            success, stdout, stderr = self.run_ipmitool_command(["sdr", "type", "temperature"])
            if success:
                # Parse temperature from output
                for line in stdout.split('\n'):
                    if self.temp_sensor.get() in line:
                        # Extract temperature value
                        temp_match = re.search(r'\|\s*(\d+)\s*degrees', line)
                        if temp_match:
                            temp = temp_match.group(1)
                            self.log_message(f"Current temperature: {temp}°C")
                            return temp
                self.log_message(f"Temperature sensor {self.temp_sensor.get()} not found")
            else:
                self.log_message(f"Failed to get temperature: {stderr}")
                
        threading.Thread(target=temp_thread, daemon=True).start()
        
    def get_all_sensors(self):
        """Get all temperature sensors and their readings"""
        if not self.validate_connection_settings():
            return
            
        self.log_message("Getting all temperature sensors...")
        
        def sensors_thread():
            success, stdout, stderr = self.run_ipmitool_command(["sdr", "type", "temperature"])
            if success:
                self.log_message("=== All Temperature Sensors ===")
                for line in stdout.split('\n'):
                    if line.strip() and '|' in line:
                        # Parse and format sensor data
                        parts = line.split('|')
                        if len(parts) >= 5:
                            sensor_name = parts[0].strip()
                            sensor_id = parts[1].strip()
                            sensor_value = parts[4].strip()
                            self.log_message(f"{sensor_name} ({sensor_id}): {sensor_value}")
                self.log_message("=== End Sensors ===")
            else:
                self.log_message(f"Failed to get sensors: {stderr}")
                
        threading.Thread(target=sensors_thread, daemon=True).start()
        
    def get_chassis_status(self):
        """Get chassis status information"""
        if not self.validate_connection_settings():
            return
            
        self.log_message("Getting chassis status...")
        
        def chassis_thread():
            success, stdout, stderr = self.run_ipmitool_command(["chassis", "status"])
            if success:
                self.log_message("=== Chassis Status ===")
                for line in stdout.split('\n'):
                    if line.strip():
                        self.log_message(line.strip())
                self.log_message("=== End Status ===")
            else:
                self.log_message(f"Failed to get chassis status: {stderr}")
                
        threading.Thread(target=chassis_thread, daemon=True).start()
        
    def enable_dynamic_control(self):
        """Enable iDRAC dynamic fan control"""
        if not self.validate_connection_settings():
            return
            
        self.log_message("Enabling dynamic fan control...")
        
        def enable_thread():
            success, stdout, stderr = self.run_ipmitool_command(["raw", "0x30", "0x30", "0x01", "0x01"])
            if success:
                self.log_message("✓ Dynamic fan control enabled")
            else:
                self.log_message(f"✗ Failed to enable dynamic control: {stderr}")
                
        threading.Thread(target=enable_thread, daemon=True).start()
        
    def disable_dynamic_control(self):
        """Disable iDRAC dynamic fan control"""
        if not self.validate_connection_settings():
            return
            
        self.log_message("Disabling dynamic fan control...")
        
        def disable_thread():
            success, stdout, stderr = self.run_ipmitool_command(["raw", "0x30", "0x30", "0x01", "0x00"])
            if success:
                self.log_message("✓ Dynamic fan control disabled")
            else:
                self.log_message(f"✗ Failed to disable dynamic control: {stderr}")
                
        threading.Thread(target=disable_thread, daemon=True).start()
        
    def set_manual_fan_speed(self):
        """Set manual fan speed"""
        if not self.validate_connection_settings():
            return
            
        speed = int(float(self.fan_speed_var.get()))
        
        if speed < 0 or speed > 100:
            messagebox.showerror("Error", "Fan speed must be between 0-100%")
            return
            
        hex_speed = self.fan_speeds[speed]
        self.log_message(f"Setting fan speed to {speed}% (hex: {hex_speed})...")
        
        def set_speed_thread():
            success, stdout, stderr = self.run_ipmitool_command(["raw", "0x30", "0x30", "0x02", "0xff", hex_speed])
            if success:
                self.log_message(f"✓ Fan speed set to {speed}%")
            else:
                self.log_message(f"✗ Failed to set fan speed: {stderr}")
                
        threading.Thread(target=set_speed_thread, daemon=True).start()
        
    def toggle_auto_mode(self):
        """Toggle automatic mode checkbox"""
        if not self.auto_mode.get() and self.monitoring:
            self.toggle_monitoring()
            
    def toggle_monitoring(self):
        """Start or stop automatic monitoring"""
        if not self.monitoring:
            if not self.validate_connection_settings():
                return
            if not self.auto_mode.get():
                messagebox.showwarning("Warning", "Please enable automatic fan control first")
                return
                
            self.monitoring = True
            self.auto_button.config(text="Stop Monitoring")
            self.log_message("Starting automatic monitoring...")
            threading.Thread(target=self.monitoring_loop, daemon=True).start()
        else:
            self.monitoring = False
            self.auto_button.config(text="Start Monitoring")
            self.log_message("Stopping automatic monitoring...")
            
    def monitoring_loop(self):
        """Main monitoring loop for automatic mode"""
        while self.monitoring and self.auto_mode.get():
            try:
                # Get current temperature
                success, stdout, stderr = self.run_ipmitool_command(["sdr", "type", "temperature"])
                if not success:
                    self.log_message(f"Failed to get temperature: {stderr}")
                    time.sleep(30)
                    continue
                    
                # Parse temperature
                current_temp = None
                for line in stdout.split('\n'):
                    if self.temp_sensor.get() in line:
                        temp_match = re.search(r'\|\s*(\d+)\s*degrees', line)
                        if temp_match:
                            current_temp = int(temp_match.group(1))
                            break
                            
                if current_temp is None:
                    self.log_message("Could not parse temperature")
                    time.sleep(30)
                    continue
                    
                threshold = int(self.temp_threshold.get())
                self.log_message(f"Current temperature: {current_temp}°C")
                
                # Check if above threshold
                if current_temp > threshold:
                    self.log_message(f"Temperature above {threshold}°C - enabling dynamic control")
                    self.run_ipmitool_command(["raw", "0x30", "0x30", "0x01", "0x01"])
                    time.sleep(60)  # Wait longer when in dynamic mode
                    continue
                    
                # Temperature below threshold - set manual control
                self.log_message(f"Temperature below {threshold}°C - using manual control")
                self.run_ipmitool_command(["raw", "0x30", "0x30", "0x01", "0x00"])
                
                # Determine fan speed based on temperature
                if current_temp < 30:
                    fan_speed = 10
                elif 30 <= current_temp <= 34:
                    fan_speed = 20
                elif 35 <= current_temp <= 39:
                    fan_speed = 25
                elif 40 <= current_temp <= 45:
                    fan_speed = 30
                else:
                    fan_speed = 50  # Higher default for safety
                    
                hex_speed = self.fan_speeds[fan_speed]
                self.log_message(f"Setting fan speed to {fan_speed}% (hex: {hex_speed})")
                self.run_ipmitool_command(["raw", "0x30", "0x30", "0x02", "0xff", hex_speed])
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.log_message(f"Error in monitoring loop: {e}")
                time.sleep(30)
                
        self.monitoring = False
        if self.auto_button.winfo_exists():
            self.auto_button.config(text="Start Monitoring")

def main():
    root = tk.Tk()
    app = DellFanController(root)
    
    # Add menu bar
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    
    # File menu
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="Minimize to Tray", command=app.hide_window)
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=app.exit_application)
    
    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Help", menu=help_menu)
    help_menu.add_command(label="About", command=lambda: messagebox.showinfo(
        "About", 
        "Dell Server Fan Control v1.6\n\n"
        "Controls Dell PowerEdge server fan speeds via iDRAC.\n"
        "Requires ipmitool.exe in C:\\IPMI\\ folder.\n\n"
        "Features:\n"
        "• Secure credential storage using system keyring\n"
        "• System tray integration (minimize to tray)\n"
        "• Full 0-100% fan speed control\n"
        "• Automatic temperature-based fan control\n"
        "• Real-time monitoring and logging\n\n"
        "Fan Speed Range: 0-100% (0x00-0x64)\n\n"
        "Automatic Mode Temperature Ranges:\n"
        "• Below 30°C: 10% fan speed (very quiet)\n"
        "• 30-34°C: 20% fan speed\n"
        "• 35-39°C: 25% fan speed\n"
        "• 40-45°C: 30% fan speed\n"
        "• >45°C: Dynamic control enabled\n\n"
        "Temperature Sensors:\n"
        "04h - Inlet Temp\n"
        "01h - Exhaust Temp\n"
        "0Eh - CPU 1 Temp\n"
        "0Fh - CPU 2 Temp\n\n"
        "System Tray:\n"
        "• Close window to minimize to tray\n"
        "• Right-click tray icon for quick actions\n"
        "• Use 'Exit Application' to completely close"
    ))
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.exit_application()

if __name__ == "__main__":
    main()