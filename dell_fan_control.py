import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import threading
import time
from datetime import datetime
import re

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
        
        # Fan speed mappings
        self.fan_speeds = {
            0: "0x00", 5: "0x05", 10: "0x0a", 15: "0x0f", 20: "0x14",
            25: "0x19", 30: "0x1e", 35: "0x23", 40: "0x28", 45: "0x2D", 50: "0x32"
        }
        
        self.setup_ui()
        
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
        ttk.Button(control_frame, text="Enable Dynamic Control", command=self.enable_dynamic_control).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(control_frame, text="Disable Dynamic Control", command=self.disable_dynamic_control).grid(row=0, column=3, padx=(0, 5))
        
        # Manual Fan Control
        fan_frame = ttk.LabelFrame(main_frame, text="Manual Fan Control", padding="10")
        fan_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        fan_frame.columnconfigure(1, weight=1)
        
        ttk.Label(fan_frame, text="Fan Speed (%):").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.fan_speed_var = tk.StringVar(value="20")
        fan_scale = ttk.Scale(fan_frame, from_=0, to=50, variable=self.fan_speed_var, orient=tk.HORIZONTAL)
        fan_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        fan_scale.configure(command=self.update_fan_speed_label)
        
        self.fan_speed_label = ttk.Label(fan_frame, text="20%")
        self.fan_speed_label.grid(row=0, column=2, padx=(5, 0))
        
        ttk.Button(fan_frame, text="Set Fan Speed", command=self.set_manual_fan_speed).grid(row=1, column=0, columnspan=3, pady=(10, 0))
        
        # Automatic Mode
        auto_frame = ttk.LabelFrame(main_frame, text="Automatic Mode", padding="10")
        auto_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Checkbutton(auto_frame, text="Enable Automatic Fan Control", variable=self.auto_mode, command=self.toggle_auto_mode).grid(row=0, column=0, sticky=tk.W)
        
        self.auto_button = ttk.Button(auto_frame, text="Start Monitoring", command=self.toggle_monitoring)
        self.auto_button.grid(row=1, column=0, pady=(5, 0))
        
        # Status Display
        status_frame = ttk.LabelFrame(main_frame, text="Status & Log", padding="10")
        status_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(1, weight=1)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=15, width=70)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure main frame row weight
        main_frame.rowconfigure(5, weight=1)
        
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
        # Round to nearest 5
        speed = round(speed / 5) * 5
        self.fan_speed_label.config(text=f"{speed}%")
        
    def run_ipmitool_command(self, command):
        """Run ipmitool command and return output"""
        try:
            full_command = [
                "ipmitool", "-I", "lanplus", 
                "-H", self.idrac_ip.get(),
                "-U", self.idrac_user.get(),
                "-P", self.idrac_password.get()
            ] + command
            
            result = subprocess.run(full_command, capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
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
        speed = round(speed / 5) * 5  # Round to nearest 5
        
        if speed not in self.fan_speeds:
            messagebox.showerror("Error", "Invalid fan speed. Use values from 0-50 in increments of 5.")
            return
            
        hex_speed = self.fan_speeds[speed]
        self.log_message(f"Setting fan speed to {speed}%...")
        
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
                if 0 <= current_temp <= 19:
                    fan_speed = 15
                elif 20 <= current_temp <= 24:
                    fan_speed = 20
                elif 25 <= current_temp <= 29:
                    fan_speed = 25
                elif 30 <= current_temp <= 34:
                    fan_speed = 30
                elif 35 <= current_temp <= 39:
                    fan_speed = 35
                elif 40 <= current_temp <= 45:
                    fan_speed = 40
                else:
                    fan_speed = 40  # Default
                    
                hex_speed = self.fan_speeds[fan_speed]
                self.log_message(f"Setting fan speed to {fan_speed}%")
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
    
    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Help", menu=help_menu)
    help_menu.add_command(label="About", command=lambda: messagebox.showinfo(
        "About", 
        "Dell Server Fan Control v1.0\n\n"
        "Controls Dell PowerEdge server fan speeds via iDRAC.\n"
        "Requires ipmitool to be installed and in PATH.\n\n"
        "Temperature Sensors:\n"
        "04h - Inlet Temp\n"
        "01h - Exhaust Temp\n"
        "0Eh - CPU 1 Temp\n"
        "0Fh - CPU 2 Temp"
    ))
    
    root.mainloop()

if __name__ == "__main__":
    main()