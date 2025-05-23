import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import threading
import time
from datetime import datetime
import re
import os
import math

class DellFanControllerUI:
    def __init__(self, parent_frame, server_config, log_callback=None, ipmitool_path=None):
        self.parent_frame = parent_frame
        self.server_config = server_config
        self.log_callback = log_callback
        self.ipmitool_path = ipmitool_path
        
        # Animation variables
        self.fan_angle = 0
        self.temp_animation = 0
        self.connection_status = "disconnected"  # disconnected, connecting, connected, error
        
        # Data variables
        self.current_temp = 0
        self.current_fan_speed = 0
        self.fan_rpm = 0
        self.auto_mode = False
        self.monitoring = False
        
        # Create the UI
        self.setup_ui()
        
        # Start animation loop
        self.animate()
        
    def log_message(self, message):
        """Log message with server name prefix"""
        if self.log_callback:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] [DELL:{self.server_config['name']}] {message}"
            self.log_callback(log_entry)
    
    def setup_ui(self):
        """Setup the modern, graphical UI"""
        # Main container with dark theme
        self.main_frame = tk.Frame(self.parent_frame, bg='#1a1a1a')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header with server info and status
        self.setup_header()
        
        # Main content area with visual elements
        self.setup_main_content()
        
        # Control panel
        self.setup_control_panel()
        
    def setup_header(self):
        """Create animated header with server status"""
        header_frame = tk.Frame(self.main_frame, bg='#2d2d2d', height=80)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)
        
        # Server name and model
        info_frame = tk.Frame(header_frame, bg='#2d2d2d')
        info_frame.pack(side=tk.LEFT, fill=tk.Y, padx=20, pady=10)
        
        server_name_label = tk.Label(info_frame, text=self.server_config['name'], 
                                    font=('Arial', 16, 'bold'), fg='#ffffff', bg='#2d2d2d')
        server_name_label.pack(anchor=tk.W)
        
        model_label = tk.Label(info_frame, text="Dell PowerEdge Server", 
                              font=('Arial', 10), fg='#888888', bg='#2d2d2d')
        model_label.pack(anchor=tk.W)
        
        ip_label = tk.Label(info_frame, text=f"iDRAC: {self.server_config['ip']}", 
                           font=('Arial', 9), fg='#666666', bg='#2d2d2d')
        ip_label.pack(anchor=tk.W)
        
        # Server management controls
        mgmt_frame = tk.Frame(header_frame, bg='#2d2d2d')
        mgmt_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=20, pady=10)
        
        # Edit/Remove server buttons
        edit_btn = self.create_modern_button(mgmt_frame, "⚙️", self.edit_server, 
                                           color='#ffaa00', width=35)
        edit_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        remove_btn = self.create_modern_button(mgmt_frame, "🗑️", self.remove_server, 
                                             color='#ff4444', width=35)
        remove_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Fan curve button
        curve_btn = self.create_modern_button(mgmt_frame, "📈 CURVE", self.show_fan_curve, 
                                            color='#aa88ff', width=80)
        curve_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Connection status indicator
        status_frame = tk.Frame(header_frame, bg='#2d2d2d')
        status_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=20, pady=10)
        
        self.status_canvas = tk.Canvas(status_frame, width=60, height=60, bg='#2d2d2d', 
                                      highlightthickness=0)
        self.status_canvas.pack()
        
        status_text_label = tk.Label(status_frame, text="Connection Status", 
                                    font=('Arial', 9), fg='#888888', bg='#2d2d2d')
        status_text_label.pack()
        
    def setup_main_content(self):
        """Create visual dashboard with animated elements"""
        content_frame = tk.Frame(self.main_frame, bg='#1a1a1a')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Left side - Temperature visualization
        temp_frame = tk.Frame(content_frame, bg='#2d2d2d', width=300)
        temp_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        temp_frame.pack_propagate(False)
        
        temp_title = tk.Label(temp_frame, text="TEMPERATURE MONITOR", 
                             font=('Arial', 12, 'bold'), fg='#ffffff', bg='#2d2d2d')
        temp_title.pack(pady=(15, 10))
        
        # Circular temperature gauge
        self.temp_canvas = tk.Canvas(temp_frame, width=200, height=200, bg='#2d2d2d',
                                    highlightthickness=0)
        self.temp_canvas.pack(pady=10)
        
        self.temp_value_label = tk.Label(temp_frame, text="--°C", 
                                        font=('Arial', 24, 'bold'), fg='#00ff88', bg='#2d2d2d')
        self.temp_value_label.pack()
        
        self.temp_status_label = tk.Label(temp_frame, text="Monitoring...", 
                                         font=('Arial', 10), fg='#888888', bg='#2d2d2d')
        self.temp_status_label.pack(pady=(5, 15))
        
        # Right side - Fan visualization
        fan_frame = tk.Frame(content_frame, bg='#2d2d2d')
        fan_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        fan_title = tk.Label(fan_frame, text="FAN CONTROL", 
                            font=('Arial', 12, 'bold'), fg='#ffffff', bg='#2d2d2d')
        fan_title.pack(pady=(15, 10))
        
        # Animated fan visualization
        self.fan_canvas = tk.Canvas(fan_frame, width=250, height=200, bg='#2d2d2d',
                                   highlightthickness=0)
        self.fan_canvas.pack(pady=10)
        
        # Fan info
        fan_info_frame = tk.Frame(fan_frame, bg='#2d2d2d')
        fan_info_frame.pack(pady=10)
        
        self.fan_speed_label = tk.Label(fan_info_frame, text="Speed: --%", 
                                       font=('Arial', 14, 'bold'), fg='#00aaff', bg='#2d2d2d')
        self.fan_speed_label.pack()
        
        self.fan_rpm_label = tk.Label(fan_info_frame, text="RPM: ----", 
                                     font=('Arial', 11), fg='#888888', bg='#2d2d2d')
        self.fan_rpm_label.pack()
        
        self.fan_mode_label = tk.Label(fan_info_frame, text="Mode: Manual", 
                                      font=('Arial', 10), fg='#ffaa00', bg='#2d2d2d')
        self.fan_mode_label.pack(pady=(5, 0))
        
    def setup_control_panel(self):
        """Create sleek control panel"""
        control_frame = tk.Frame(self.main_frame, bg='#2d2d2d', height=120)
        control_frame.pack(fill=tk.X)
        control_frame.pack_propagate(False)
        
        # Left controls
        left_controls = tk.Frame(control_frame, bg='#2d2d2d')
        left_controls.pack(side=tk.LEFT, fill=tk.Y, padx=20, pady=15)
        
        # Connection controls
        conn_label = tk.Label(left_controls, text="CONNECTION", 
                             font=('Arial', 9, 'bold'), fg='#888888', bg='#2d2d2d')
        conn_label.pack(anchor=tk.W)
        
        conn_btn_frame = tk.Frame(left_controls, bg='#2d2d2d')
        conn_btn_frame.pack(anchor=tk.W, pady=(5, 10))
        
        self.test_btn = self.create_modern_button(conn_btn_frame, "TEST", self.test_connection, 
                                                 color='#00ff88', width=60)
        self.test_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.temp_btn = self.create_modern_button(conn_btn_frame, "TEMP", self.get_temperature, 
                                                 color='#ffaa00', width=60)
        self.temp_btn.pack(side=tk.LEFT)
        
        # Fan mode controls
        mode_label = tk.Label(left_controls, text="FAN MODE", 
                             font=('Arial', 9, 'bold'), fg='#888888', bg='#2d2d2d')
        mode_label.pack(anchor=tk.W)
        
        mode_btn_frame = tk.Frame(left_controls, bg='#2d2d2d')
        mode_btn_frame.pack(anchor=tk.W, pady=5)
        
        self.auto_btn = self.create_modern_button(mode_btn_frame, "AUTO", self.enable_dynamic_control, 
                                                 color='#00aaff', width=60)
        self.auto_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.manual_btn = self.create_modern_button(mode_btn_frame, "MANUAL", self.disable_dynamic_control, 
                                                   color='#ff6644', width=60)
        self.manual_btn.pack(side=tk.LEFT)
        
        # Right controls - Fan speed slider
        right_controls = tk.Frame(control_frame, bg='#2d2d2d')
        right_controls.pack(side=tk.RIGHT, fill=tk.Y, padx=20, pady=15)
        
        speed_label = tk.Label(right_controls, text="MANUAL FAN SPEED", 
                              font=('Arial', 9, 'bold'), fg='#888888', bg='#2d2d2d')
        speed_label.pack(anchor=tk.W)
        
        # Custom slider
        slider_frame = tk.Frame(right_controls, bg='#2d2d2d')
        slider_frame.pack(anchor=tk.W, pady=5)
        
        self.speed_var = tk.StringVar(value="30")
        self.speed_scale = ttk.Scale(slider_frame, from_=0, to=100, variable=self.speed_var, 
                                    orient=tk.HORIZONTAL, length=200,
                                    command=self.update_speed_display)
        self.speed_scale.pack(side=tk.LEFT, padx=(0, 10))
        
        self.speed_display = tk.Label(slider_frame, text="30%", 
                                     font=('Arial', 12, 'bold'), fg='#00aaff', bg='#2d2d2d')
        self.speed_display.pack(side=tk.LEFT)
        
        self.set_speed_btn = self.create_modern_button(right_controls, "SET SPEED", self.set_fan_speed, 
                                                      color='#ff6644', width=100)
        self.set_speed_btn.pack(anchor=tk.W, pady=(10, 0))
        
        # Auto monitoring controls
        auto_controls = tk.Frame(control_frame, bg='#2d2d2d')
        auto_controls.pack(side=tk.LEFT, fill=tk.Y, padx=20, pady=15)
        
        auto_label = tk.Label(auto_controls, text="AUTO MONITOR", 
                             font=('Arial', 9, 'bold'), fg='#888888', bg='#2d2d2d')
        auto_label.pack(anchor=tk.W)
        
        # Temperature threshold
        threshold_frame = tk.Frame(auto_controls, bg='#2d2d2d')
        threshold_frame.pack(anchor=tk.W, pady=(5, 5))
        
        tk.Label(threshold_frame, text="Threshold:", font=('Arial', 8), 
                fg='#666666', bg='#2d2d2d').pack(side=tk.LEFT)
        
        self.temp_threshold_var = tk.StringVar(value="45")
        threshold_entry = tk.Entry(threshold_frame, textvariable=self.temp_threshold_var, 
                                  width=5, font=('Arial', 8),
                                  bg='#444444', fg='#ffffff', relief=tk.FLAT)
        threshold_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        tk.Label(threshold_frame, text="°C", font=('Arial', 8), 
                fg='#666666', bg='#2d2d2d').pack(side=tk.LEFT)
        
        # Auto monitoring button
        self.auto_monitor_btn = self.create_modern_button(auto_controls, "START AUTO", self.toggle_auto_monitoring, 
                                                         color='#88ff88', width=80)
        self.auto_monitor_btn.pack(anchor=tk.W, pady=(5, 0))
        
    def create_modern_button(self, parent, text, command, color='#00aaff', width=80):
        """Create a modern flat button with hover effects"""
        btn_frame = tk.Frame(parent, bg=color, width=width, height=30)
        btn_frame.pack_propagate(False)
        
        btn_label = tk.Label(btn_frame, text=text, font=('Arial', 8, 'bold'), 
                            fg='#ffffff', bg=color, cursor='hand2')
        btn_label.pack(expand=True)
        
        def on_enter(e):
            # Lighter shade on hover
            hover_color = self.lighten_color(color, 0.2)
            btn_frame.config(bg=hover_color)
            btn_label.config(bg=hover_color)
            
        def on_leave(e):
            btn_frame.config(bg=color)
            btn_label.config(bg=color)
            
        def on_click(e):
            threading.Thread(target=command, daemon=True).start()
            
        btn_label.bind("<Enter>", on_enter)
        btn_label.bind("<Leave>", on_leave)
        btn_label.bind("<Button-1>", on_click)
        
        return btn_frame
        
    def lighten_color(self, color, factor):
        """Lighten a hex color by a factor"""
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        
    def update_speed_display(self, value):
        """Update speed display when slider changes"""
        speed = int(float(value))
        self.speed_display.config(text=f"{speed}%")
        
    def animate(self):
        """Main animation loop"""
        self.draw_connection_status()
        self.draw_temperature_gauge()
        self.draw_fan_animation()
        
        # Schedule next frame
        self.parent_frame.after(50, self.animate)
        
    def draw_connection_status(self):
        """Draw animated connection status indicator"""
        self.status_canvas.delete("all")
        
        center_x, center_y = 30, 30
        radius = 20
        
        if self.connection_status == "connected":
            # Solid green circle with pulse
            pulse = 1 + 0.1 * math.sin(time.time() * 3)
            self.status_canvas.create_oval(center_x - radius * pulse, center_y - radius * pulse,
                                         center_x + radius * pulse, center_y + radius * pulse,
                                         fill='#00ff88', outline='#00cc66', width=2)
            # Checkmark
            self.status_canvas.create_line(22, 30, 28, 36, fill='#ffffff', width=3)
            self.status_canvas.create_line(28, 36, 38, 24, fill='#ffffff', width=3)
            
        elif self.connection_status == "connecting":
            # Rotating spinner
            angle = time.time() * 5
            for i in range(8):
                a = angle + i * math.pi / 4
                x1 = center_x + 15 * math.cos(a)
                y1 = center_y + 15 * math.sin(a)
                x2 = center_x + 20 * math.cos(a)
                y2 = center_y + 20 * math.sin(a)
                alpha = 1 - (i / 8)
                color = f"#{int(255 * alpha):02x}{int(170 * alpha):02x}00"
                self.status_canvas.create_line(x1, y1, x2, y2, fill=color, width=3)
                
        elif self.connection_status == "error":
            # Red circle with X
            self.status_canvas.create_oval(center_x - radius, center_y - radius,
                                         center_x + radius, center_y + radius,
                                         fill='#ff4444', outline='#cc0000', width=2)
            # X mark
            self.status_canvas.create_line(22, 22, 38, 38, fill='#ffffff', width=3)
            self.status_canvas.create_line(38, 22, 22, 38, fill='#ffffff', width=3)
            
        else:  # disconnected
            # Gray circle with dot
            self.status_canvas.create_oval(center_x - radius, center_y - radius,
                                         center_x + radius, center_y + radius,
                                         fill='#444444', outline='#666666', width=2)
            self.status_canvas.create_oval(center_x - 5, center_y - 5,
                                         center_x + 5, center_y + 5,
                                         fill='#888888', outline='')
                
    def draw_temperature_gauge(self):
        """Draw animated temperature gauge"""
        self.temp_canvas.delete("all")
        
        center_x, center_y = 100, 100
        radius = 80
        
        # Background circle
        self.temp_canvas.create_oval(center_x - radius, center_y - radius,
                                   center_x + radius, center_y + radius,
                                   outline='#444444', width=3, fill='#333333')
        
        # Temperature range arcs (colored segments)
        temp_ranges = [
            (0, 30, '#00ff88'),    # Cold - Green
            (30, 45, '#ffff00'),   # Warm - Yellow
            (45, 65, '#ffaa00'),   # Hot - Orange
            (65, 85, '#ff4444'),   # Very Hot - Red
            (85, 100, '#ff0088')   # Critical - Magenta
        ]
        
        for temp_min, temp_max, color in temp_ranges:
            start_angle = 135 + (temp_min / 100) * 270
            extent = ((temp_max - temp_min) / 100) * 270
            self.temp_canvas.create_arc(center_x - radius + 10, center_y - radius + 10,
                                      center_x + radius - 10, center_y + radius - 10,
                                      start=start_angle, extent=extent,
                                      outline=color, width=6, style='arc')
        
        # Current temperature needle
        if self.current_temp > 0:
            temp_angle = 135 + (min(self.current_temp, 100) / 100) * 270
            needle_angle = math.radians(temp_angle)
            needle_x = center_x + 60 * math.cos(needle_angle)
            needle_y = center_y + 60 * math.sin(needle_angle)
            
            self.temp_canvas.create_line(center_x, center_y, needle_x, needle_y,
                                       fill='#ffffff', width=3)
            
        # Center dot
        self.temp_canvas.create_oval(center_x - 8, center_y - 8,
                                   center_x + 8, center_y + 8,
                                   fill='#ffffff', outline='')
        
        # Temperature markings
        for temp in [0, 25, 50, 75, 100]:
            angle = 135 + (temp / 100) * 270
            rad = math.radians(angle)
            x1 = center_x + 70 * math.cos(rad)
            y1 = center_y + 70 * math.sin(rad)
            x2 = center_x + 75 * math.cos(rad)
            y2 = center_y + 75 * math.sin(rad)
            self.temp_canvas.create_line(x1, y1, x2, y2, fill='#888888', width=2)
            
            # Temperature labels
            x_text = center_x + 85 * math.cos(rad)
            y_text = center_y + 85 * math.sin(rad)
            self.temp_canvas.create_text(x_text, y_text, text=str(temp),
                                       fill='#888888', font=('Arial', 8))
        
    def draw_fan_animation(self):
        """Draw animated fan blades"""
        self.fan_canvas.delete("all")
        
        center_x, center_y = 125, 100
        
        # Fan housing
        self.fan_canvas.create_oval(center_x - 60, center_y - 60,
                                  center_x + 60, center_y + 60,
                                  outline='#666666', width=3, fill='#2a2a2a')
        
        # Animate fan blades based on speed
        if self.current_fan_speed > 0:
            rotation_speed = self.current_fan_speed / 100 * 10  # Adjust speed
            self.fan_angle += rotation_speed
            
            # Draw fan blades
            for i in range(6):
                blade_angle = self.fan_angle + i * 60
                blade_rad = math.radians(blade_angle)
                
                # Blade outer point
                x1 = center_x + 45 * math.cos(blade_rad)
                y1 = center_y + 45 * math.sin(blade_rad)
                
                # Blade inner points
                angle_offset = 15
                x2 = center_x + 20 * math.cos(math.radians(blade_angle - angle_offset))
                y2 = center_y + 20 * math.sin(math.radians(blade_angle - angle_offset))
                x3 = center_x + 20 * math.cos(math.radians(blade_angle + angle_offset))
                y3 = center_y + 20 * math.sin(math.radians(blade_angle + angle_offset))
                
                # Blade color based on speed
                speed_intensity = min(255, int(self.current_fan_speed / 100 * 255))
                blade_color = f"#{speed_intensity:02x}{speed_intensity//2:02x}00"
                
                self.fan_canvas.create_polygon(x1, y1, x2, y2, x3, y3,
                                             fill=blade_color, outline='#444444')
        
        # Center hub
        self.fan_canvas.create_oval(center_x - 15, center_y - 15,
                                  center_x + 15, center_y + 15,
                                  fill='#444444', outline='#666666', width=2)
        
        # Speed indicator rings
        for i in range(3):
            if self.current_fan_speed > i * 33:
                ring_radius = 70 + i * 8
                alpha = min(1, (self.current_fan_speed - i * 33) / 33)
                ring_color = f"#{int(255 * alpha):02x}{int(170 * alpha):02x}00"
                self.fan_canvas.create_oval(center_x - ring_radius, center_y - ring_radius,
                                          center_x + ring_radius, center_y + ring_radius,
                                          outline=ring_color, width=2)
        
    def run_ipmitool_command(self, command):
        """Run ipmitool command and return output"""
        if not self.ipmitool_path:
            return False, "", "ipmitool.exe not found"
            
        try:
            full_command = [
                self.ipmitool_path, "-I", "lanplus", 
                "-H", self.server_config['ip'],
                "-U", self.server_config['username'],
                "-P", self.server_config['password']
            ] + command
            
            result = subprocess.run(full_command, capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
            
    def test_connection(self):
        """Test connection to server"""
        self.connection_status = "connecting"
        self.log_message("Testing connection...")
        
        def test_thread():
            success, stdout, stderr = self.run_ipmitool_command(["sdr", "list"])
            if success:
                self.connection_status = "connected"
                self.log_message("✓ Connection successful")
            else:
                self.connection_status = "error"
                self.log_message(f"✗ Connection failed: {stderr}")
                
        threading.Thread(target=test_thread, daemon=True).start()
        
    def get_temperature(self):
        """Get current temperature"""
        self.log_message("Getting temperature...")
        
        def temp_thread():
            success, stdout, stderr = self.run_ipmitool_command(["sdr", "type", "temperature"])
            if success:
                max_temp = 0
                for line in stdout.split('\n'):
                    if '0Eh' in line or 'CPU' in line:  # CPU temperature
                        temp_match = re.search(r'\|\s*(\d+)\s*degrees', line)
                        if temp_match:
                            temp = int(temp_match.group(1))
                            max_temp = max(max_temp, temp)
                            
                if max_temp > 0:
                    self.current_temp = max_temp
                    self.temp_value_label.config(text=f"{max_temp}°C")
                    
                    # Update status based on temperature
                    if max_temp < 35:
                        self.temp_status_label.config(text="Optimal", fg='#00ff88')
                    elif max_temp < 50:
                        self.temp_status_label.config(text="Normal", fg='#ffaa00')
                    elif max_temp < 70:
                        self.temp_status_label.config(text="Warm", fg='#ff6644')
                    else:
                        self.temp_status_label.config(text="Hot!", fg='#ff4444')
                        
                    self.log_message(f"Temperature: {max_temp}°C")
                else:
                    self.log_message("No temperature data found")
            else:
                self.log_message(f"✗ Failed to get temperature: {stderr}")
                
        threading.Thread(target=temp_thread, daemon=True).start()
        
    def enable_dynamic_control(self):
        """Enable automatic fan control"""
        self.log_message("Enabling automatic fan control...")
        
        def enable_thread():
            success, stdout, stderr = self.run_ipmitool_command(["raw", "0x30", "0x30", "0x01", "0x01"])
            if success:
                self.auto_mode = True
                self.fan_mode_label.config(text="Mode: Automatic", fg='#00aaff')
                self.log_message("✓ Automatic fan control enabled")
            else:
                self.log_message(f"✗ Failed to enable automatic control: {stderr}")
                
        threading.Thread(target=enable_thread, daemon=True).start()
        
    def disable_dynamic_control(self):
        """Disable automatic fan control"""
        self.log_message("Disabling automatic fan control...")
        
        def disable_thread():
            success, stdout, stderr = self.run_ipmitool_command(["raw", "0x30", "0x30", "0x01", "0x00"])
            if success:
                self.auto_mode = False
                self.fan_mode_label.config(text="Mode: Manual", fg='#ffaa00')
                self.log_message("✓ Manual fan control enabled")
            else:
                self.log_message(f"✗ Failed to disable automatic control: {stderr}")
                
        threading.Thread(target=disable_thread, daemon=True).start()
        
    def set_fan_speed(self):
        """Set manual fan speed"""
        speed = int(float(self.speed_var.get()))
        hex_speed = f"0x{speed:02x}"
        
        self.log_message(f"Setting fan speed to {speed}%...")
        
        def set_speed_thread():
            success, stdout, stderr = self.run_ipmitool_command(["raw", "0x30", "0x30", "0x02", "0xff", hex_speed])
            if success:
                self.current_fan_speed = speed
                self.fan_speed_label.config(text=f"Speed: {speed}%")
                self.fan_rpm = speed * 50  # Approximate RPM
                self.fan_rpm_label.config(text=f"RPM: ~{self.fan_rpm}")
                self.log_message(f"✓ Fan speed set to {speed}%")
            else:
                self.log_message(f"✗ Failed to set fan speed: {stderr}")
                
        threading.Thread(target=set_speed_thread, daemon=True).start()
        
    def toggle_auto_monitoring(self):
        """Start or stop automatic monitoring"""
        if not self.monitoring:
            self.monitoring = True
            self.auto_monitor_btn = self.create_modern_button(self.auto_monitor_btn.master, "STOP AUTO", self.toggle_auto_monitoring, 
                                                             color='#ff4444', width=80)
            self.log_message("Starting automatic monitoring...")
            threading.Thread(target=self.auto_monitoring_loop, daemon=True).start()
        else:
            self.monitoring = False
            self.auto_monitor_btn = self.create_modern_button(self.auto_monitor_btn.master, "START AUTO", self.toggle_auto_monitoring, 
                                                             color='#88ff88', width=80)
            self.log_message("Stopping automatic monitoring...")
            
    def auto_monitoring_loop(self):
        """Automatic monitoring loop for temperature-based fan control"""
        while self.monitoring:
            try:
                threshold = int(self.temp_threshold_var.get())
                
                # Get current temperature
                success, stdout, stderr = self.run_ipmitool_command(["sdr", "type", "temperature"])
                if not success:
                    self.log_message(f"✗ Failed to get temperature: {stderr}")
                    time.sleep(30)
                    continue
                    
                # Parse temperature
                current_temp = None
                for line in stdout.split('\n'):
                    if '0Eh' in line or 'CPU' in line:  # CPU temperature
                        temp_match = re.search(r'\|\s*(\d+)\s*degrees', line)
                        if temp_match:
                            current_temp = int(temp_match.group(1))
                            break
                            
                if current_temp is None:
                    self.log_message("Could not parse temperature")
                    time.sleep(30)
                    continue
                    
                self.current_temp = current_temp
                self.temp_value_label.config(text=f"{current_temp}°C")
                self.log_message(f"Auto Monitor: Current temperature: {current_temp}°C")
                
                # Temperature-based fan control
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
                    fan_speed = 50
                    
                hex_speed = f"0x{fan_speed:02x}"
                self.log_message(f"Auto: Setting fan speed to {fan_speed}%")
                self.run_ipmitool_command(["raw", "0x30", "0x30", "0x02", "0xff", hex_speed])
                
                self.current_fan_speed = fan_speed
                self.fan_speed_label.config(text=f"Speed: {fan_speed}%")
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.log_message(f"✗ Error in auto monitoring: {e}")
                time.sleep(30)
                
        self.monitoring = False
        
    def edit_server(self):
        """Edit server configuration"""
        if hasattr(self, 'edit_callback') and self.edit_callback:
            self.edit_callback(self.server_config)
        else:
            self.log_message("Edit functionality not available")
            
    def remove_server(self):
        """Remove this server"""
        if hasattr(self, 'remove_callback') and self.remove_callback:
            if messagebox.askyesno("Confirm Remove", 
                                 f"Are you sure you want to remove server '{self.server_config['name']}'?"):
                self.remove_callback(self.server_config)
        else:
            self.log_message("Remove functionality not available")
            
    def show_fan_curve(self):
        """Show fan curve editor"""
        FanCurveEditor(self.parent_frame, self.server_config, self.log_message, self.run_ipmitool_command)
        
    def get_all_sensors(self):
        """Get all temperature sensors and their readings"""
        self.log_message("Getting all temperature sensors...")
        
        def sensors_thread():
            success, stdout, stderr = self.run_ipmitool_command(["sdr", "type", "temperature"])
            if success:
                self.log_message("=== All Temperature Sensors ===")
                for line in stdout.split('\n'):
                    if line.strip() and '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 5:
                            sensor_name = parts[0].strip()
                            sensor_id = parts[1].strip()
                            sensor_value = parts[4].strip()
                            self.log_message(f"{sensor_name} ({sensor_id}): {sensor_value}")
                self.log_message("=== End Sensors ===")
            else:
                self.log_message(f"✗ Failed to get sensors: {stderr}")
                
        threading.Thread(target=sensors_thread, daemon=True).start()
        
    def monitor_temperatures(self, threshold=45):
        """Monitor temperatures and return status"""
        def monitor_thread():
            success, stdout, stderr = self.run_ipmitool_command(["sdr", "type", "temperature"])
            if success:
                max_temp = 0
                for line in stdout.split('\n'):
                    if '0Eh' in line or 'CPU' in line:
                        temp_match = re.search(r'\|\s*(\d+)\s*degrees', line)
                        if temp_match:
                            temp = int(temp_match.group(1))
                            max_temp = max(max_temp, temp)
                            
                if max_temp > 0:
                    self.current_temp = max_temp
                    self.temp_value_label.config(text=f"{max_temp}°C")
                    
                    return {
                        'max_temperature': max_temp,
                        'above_threshold': max_temp > threshold,
                        'server_name': self.server_config['name'],
                        'status': 'Normal' if max_temp < threshold else 'High Temp'
                    }
            return None
            
        return threading.Thread(target=monitor_thread, daemon=True)
        
    def set_callbacks(self, edit_callback=None, remove_callback=None):
        """Set callbacks for edit and remove operations"""
        self.edit_callback = edit_callback
        self.remove_callback = remove_callback


class FanCurveEditor:
    def __init__(self, parent, server_config, log_callback, ipmitool_command):
        self.server_config = server_config
        self.log_callback = log_callback
        self.ipmitool_command = ipmitool_command
        
        # Create the editor window
        self.window = tk.Toplevel(parent)
        self.window.title(f"Fan Curve Editor - {server_config['name']}")
        self.window.geometry("600x500")
        self.window.configure(bg='#1a1a1a')
        self.window.transient(parent)
        self.window.grab_set()
        
        # Fan curve points (temperature -> fan speed %)
        self.curve_points = [
            (25, 10),   # 25°C -> 10%
            (35, 25),   # 35°C -> 25%
            (45, 40),   # 45°C -> 40%
            (55, 60),   # 55°C -> 60%
            (65, 80),   # 65°C -> 80%
            (75, 100)   # 75°C -> 100%
        ]
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the fan curve editor UI"""
        # Header
        header_frame = tk.Frame(self.window, bg='#2d2d2d', height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="📈 FAN CURVE EDITOR", 
                              font=('Arial', 16, 'bold'), 
                              fg='#ffffff', bg='#2d2d2d')
        title_label.pack(pady=15)
        
        # Main content
        content_frame = tk.Frame(self.window, bg='#1a1a1a')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Graph area
        graph_frame = tk.Frame(content_frame, bg='#2d2d2d')
        graph_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        graph_title = tk.Label(graph_frame, text="Temperature vs Fan Speed Curve", 
                              font=('Arial', 12, 'bold'), 
                              fg='#ffffff', bg='#2d2d2d')
        graph_title.pack(pady=10)
        
        # Canvas for curve visualization
        self.curve_canvas = tk.Canvas(graph_frame, width=500, height=300, 
                                     bg='#333333', highlightthickness=0)
        self.curve_canvas.pack(pady=10)
        
        # Control points editor
        points_frame = tk.Frame(content_frame, bg='#2d2d2d')
        points_frame.pack(fill=tk.X, pady=(0, 20))
        
        points_title = tk.Label(points_frame, text="Curve Control Points", 
                               font=('Arial', 12, 'bold'), 
                               fg='#ffffff', bg='#2d2d2d')
        points_title.pack(pady=(10, 5))
        
        # Scrollable frame for points
        points_scroll_frame = tk.Frame(points_frame, bg='#2d2d2d')
        points_scroll_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Headers
        headers_frame = tk.Frame(points_scroll_frame, bg='#2d2d2d')
        headers_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(headers_frame, text="Temperature (°C)", font=('Arial', 10, 'bold'), 
                fg='#888888', bg='#2d2d2d').pack(side=tk.LEFT, padx=(0, 80))
        tk.Label(headers_frame, text="Fan Speed (%)", font=('Arial', 10, 'bold'), 
                fg='#888888', bg='#2d2d2d').pack(side=tk.LEFT, padx=(0, 80))
        tk.Label(headers_frame, text="Actions", font=('Arial', 10, 'bold'), 
                fg='#888888', bg='#2d2d2d').pack(side=tk.LEFT)
        
        # Points list
        self.points_frame = tk.Frame(points_scroll_frame, bg='#2d2d2d')
        self.points_frame.pack(fill=tk.X)
        
        # Buttons
        buttons_frame = tk.Frame(content_frame, bg='#1a1a1a')
        buttons_frame.pack(fill=tk.X)
        
        # Add point button
        add_btn = tk.Button(buttons_frame, text="+ Add Point", 
                           font=('Arial', 10, 'bold'),
                           bg='#00ff88', fg='#000000',
                           relief=tk.FLAT, bd=0, padx=20, pady=8,
                           command=self.add_point)
        add_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Preset buttons
        preset_btn = tk.Button(buttons_frame, text="🔧 Load Presets", 
                              font=('Arial', 10, 'bold'),
                              bg='#ffaa00', fg='#000000',
                              relief=tk.FLAT, bd=0, padx=20, pady=8,
                              command=self.show_presets)
        preset_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Apply button
        apply_btn = tk.Button(buttons_frame, text="✓ Apply Curve", 
                             font=('Arial', 10, 'bold'),
                             bg='#58a6ff', fg='#ffffff',
                             relief=tk.FLAT, bd=0, padx=20, pady=8,
                             command=self.apply_curve)
        apply_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Cancel button
        cancel_btn = tk.Button(buttons_frame, text="✗ Cancel", 
                              font=('Arial', 10, 'bold'),
                              bg='#ff4444', fg='#ffffff',
                              relief=tk.FLAT, bd=0, padx=20, pady=8,
                              command=self.window.destroy)
        cancel_btn.pack(side=tk.RIGHT)
        
        self.refresh_ui()
        
    def refresh_ui(self):
        """Refresh the UI with current curve points"""
        # Clear existing point editors
        for widget in self.points_frame.winfo_children():
            widget.destroy()
            
        # Sort points by temperature
        self.curve_points.sort(key=lambda x: x[0])
        
        # Create point editors
        for i, (temp, speed) in enumerate(self.curve_points):
            point_frame = tk.Frame(self.points_frame, bg='#333333')
            point_frame.pack(fill=tk.X, pady=2)
            
            # Temperature entry
            temp_var = tk.StringVar(value=str(temp))
            temp_entry = tk.Entry(point_frame, textvariable=temp_var, width=10,
                                 bg='#444444', fg='#ffffff', relief=tk.FLAT, bd=5)
            temp_entry.pack(side=tk.LEFT, padx=(10, 20))
            
            # Speed entry
            speed_var = tk.StringVar(value=str(speed))
            speed_entry = tk.Entry(point_frame, textvariable=speed_var, width=10,
                                  bg='#444444', fg='#ffffff', relief=tk.FLAT, bd=5)
            speed_entry.pack(side=tk.LEFT, padx=(0, 20))
            
            # Update button
            update_btn = tk.Button(point_frame, text="Update",
                                  font=('Arial', 8, 'bold'),
                                  bg='#58a6ff', fg='#ffffff',
                                  relief=tk.FLAT, bd=0, padx=10, pady=2,
                                  command=lambda idx=i, t=temp_var, s=speed_var: self.update_point(idx, t, s))
            update_btn.pack(side=tk.LEFT, padx=(0, 5))
            
            # Remove button
            remove_btn = tk.Button(point_frame, text="Remove",
                                  font=('Arial', 8, 'bold'),
                                  bg='#ff4444', fg='#ffffff',
                                  relief=tk.FLAT, bd=0, padx=10, pady=2,
                                  command=lambda idx=i: self.remove_point(idx))
            remove_btn.pack(side=tk.LEFT)
            
        self.draw_curve()
        
    def draw_curve(self):
        """Draw the fan curve visualization"""
        self.curve_canvas.delete("all")
        
        # Graph dimensions
        margin = 50
        graph_width = 400
        graph_height = 200
        
        # Draw axes
        # X-axis (temperature)
        self.curve_canvas.create_line(margin, graph_height + margin, 
                                     graph_width + margin, graph_height + margin,
                                     fill='#666666', width=2)
        # Y-axis (fan speed)
        self.curve_canvas.create_line(margin, margin, 
                                     margin, graph_height + margin,
                                     fill='#666666', width=2)
        
        # Draw grid lines and labels
        for i in range(0, 101, 20):  # Fan speed grid (0-100%)
            y = margin + graph_height - (i / 100) * graph_height
            self.curve_canvas.create_line(margin - 5, y, graph_width + margin, y,
                                         fill='#444444', width=1)
            self.curve_canvas.create_text(margin - 15, y, text=f"{i}%", 
                                         fill='#888888', font=('Arial', 8))
            
        for i in range(0, 81, 10):  # Temperature grid (0-80°C)
            x = margin + (i / 80) * graph_width
            self.curve_canvas.create_line(x, margin, x, graph_height + margin + 5,
                                         fill='#444444', width=1)
            self.curve_canvas.create_text(x, graph_height + margin + 15, text=f"{i}°C", 
                                         fill='#888888', font=('Arial', 8))
        
        # Draw curve
        if len(self.curve_points) >= 2:
            points = []
            for temp, speed in sorted(self.curve_points):
                x = margin + (temp / 80) * graph_width
                y = margin + graph_height - (speed / 100) * graph_height
                points.extend([x, y])
                
                # Draw point
                self.curve_canvas.create_oval(x - 4, y - 4, x + 4, y + 4,
                                             fill='#00ff88', outline='#ffffff', width=2)
                
            # Draw curve line
            if len(points) >= 4:
                self.curve_canvas.create_line(points, fill='#58a6ff', width=3, smooth=True)
        
        # Labels
        self.curve_canvas.create_text(margin + graph_width / 2, graph_height + margin + 35,
                                     text="Temperature (°C)", fill='#ffffff', font=('Arial', 10, 'bold'))
        
        # Y-axis label
        self.curve_canvas.create_text(15, margin + graph_height / 2,
                                     text="Fan Speed (%)", fill='#ffffff', font=('Arial', 10, 'bold'))
        
    def add_point(self):
        """Add a new curve point"""
        # Find a good default temperature
        temps = [point[0] for point in self.curve_points]
        if temps:
            new_temp = max(temps) + 5
        else:
            new_temp = 30
            
        self.curve_points.append((new_temp, 50))  # Default to 50% speed
        self.refresh_ui()
        
    def update_point(self, index, temp_var, speed_var):
        """Update a curve point"""
        try:
            temp = int(temp_var.get())
            speed = int(speed_var.get())
            
            if not (0 <= temp <= 100):
                messagebox.showerror("Error", "Temperature must be between 0-100°C")
                return
                
            if not (0 <= speed <= 100):
                messagebox.showerror("Error", "Fan speed must be between 0-100%")
                return
                
            self.curve_points[index] = (temp, speed)
            self.refresh_ui()
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")
            
    def remove_point(self, index):
        """Remove a curve point"""
        if len(self.curve_points) <= 2:
            messagebox.showwarning("Warning", "Must have at least 2 points for a curve")
            return
            
        del self.curve_points[index]
        self.refresh_ui()
        
    def show_presets(self):
        """Show preset curve options"""
        presets = {
            "Silent": [(25, 5), (35, 15), (45, 25), (55, 35), (65, 50), (75, 70)],
            "Balanced": [(25, 10), (35, 25), (45, 40), (55, 60), (65, 80), (75, 100)],
            "Performance": [(25, 20), (35, 40), (45, 60), (55, 80), (65, 95), (75, 100)],
            "Aggressive": [(25, 30), (35, 50), (45, 70), (55, 90), (65, 100), (75, 100)]
        }
        
        preset_window = tk.Toplevel(self.window)
        preset_window.title("Fan Curve Presets")
        preset_window.geometry("400x300")
        preset_window.configure(bg='#1a1a1a')
        preset_window.transient(self.window)
        preset_window.grab_set()
        
        title_label = tk.Label(preset_window, text="Select a Preset Curve", 
                              font=('Arial', 14, 'bold'), 
                              fg='#ffffff', bg='#1a1a1a')
        title_label.pack(pady=20)
        
        for name, points in presets.items():
            btn = tk.Button(preset_window, text=f"{name} Curve",
                           font=('Arial', 12, 'bold'),
                           bg='#58a6ff', fg='#ffffff',
                           relief=tk.FLAT, bd=0, padx=30, pady=10,
                           command=lambda p=points, w=preset_window: self.load_preset(p, w))
            btn.pack(pady=5)
            
    def load_preset(self, points, window):
        """Load a preset curve"""
        self.curve_points = points.copy()
        self.refresh_ui()
        window.destroy()
        
    def apply_curve(self):
        """Apply the fan curve (for future implementation)"""
        if len(self.curve_points) < 2:
            messagebox.showerror("Error", "Need at least 2 points to create a curve")
            return
            
        # For now, just log the curve points
        self.log_callback("📈 Fan curve configuration:")
        for temp, speed in sorted(self.curve_points):
            self.log_callback(f"   {temp}°C -> {speed}%")
            
        # Future: Implement actual curve application via iDRAC
        messagebox.showinfo("Info", 
                          "Fan curve logged. Actual curve implementation requires "
                          "advanced iDRAC scripting and will be added in future updates.")
        
        self.window.destroy()