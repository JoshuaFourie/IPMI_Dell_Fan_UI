import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
from datetime import datetime
import json
import os
import math

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

# Import vendor controllers
try:
    from dell_fan_controller import DellFanControllerUI
    DELL_AVAILABLE = True
except ImportError:
    DELL_AVAILABLE = False

try:
    from hpe_fan_controller import HPEiLOController
    HPE_AVAILABLE = True
except ImportError:
    HPE_AVAILABLE = False

class ModernMultiVendorFanController:
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-Vendor Server Fan Control v2.0")
        self.root.geometry("1200x900")
        self.root.resizable(True, True)
        
        # Modern dark theme colors
        self.colors = {
            'bg_primary': '#0d1117',      # GitHub dark bg
            'bg_secondary': '#161b22',    # Slightly lighter
            'bg_tertiary': '#21262d',     # Card backgrounds
            'accent_blue': '#58a6ff',     # Blue accent
            'accent_green': '#3fb950',    # Green accent
            'accent_orange': '#f85149',   # Orange/red accent
            'text_primary': '#f0f6fc',    # Main text
            'text_secondary': '#8b949e',  # Secondary text
            'border': '#30363d'           # Borders
        }
        
        # Configure root style
        self.root.configure(bg=self.colors['bg_primary'])
        
        # Variables
        self.monitoring = False
        self.servers = {'Dell': [], 'HPE': []}
        self.server_uis = {'Dell': {}, 'HPE': {}}
        
        # Find ipmitool for Dell servers
        self.ipmitool_path = self.find_ipmitool()
        
        # Keyring service name
        self.service_name = "MultiVendor_Fan_Control_v2"
        
        # System tray variables
        self.tray_icon = None
        self.is_closing = False
        
        # Animation variables
        self.pulse_offset = 0
        
        self.setup_modern_ui()
        
        # Load configurations
        self.load_server_configs()
        
        # Setup window behavior
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Create system tray
        if PYSTRAY_AVAILABLE:
            self.setup_system_tray()
            
        # Start animations
        self.animate_ui()
        
    def find_ipmitool(self):
        """Find ipmitool executable for Dell servers"""
        paths_to_check = [
            "C:\\IPMI\\ipmitool.exe",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "IPMI", "ipmitool.exe")
        ]
        
        for path in paths_to_check:
            if os.path.exists(path):
                return path
                
        # Check system PATH
        try:
            import subprocess
            result = subprocess.run(["where", "ipmitool"], capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                return "ipmitool"
        except:
            pass
            
        return None
        
    def setup_modern_ui(self):
        """Setup the modern, visually appealing UI"""
        # Create main container
        self.main_container = tk.Frame(self.root, bg=self.colors['bg_primary'])
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create header
        self.setup_header()
        
        # Create main content area
        self.setup_main_content()
        
        # Create footer with status
        self.setup_footer()
        
    def setup_header(self):
        """Create animated header with branding"""
        header_frame = tk.Frame(self.main_container, bg=self.colors['bg_secondary'], height=100)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        # Left side - Logo and title
        left_header = tk.Frame(header_frame, bg=self.colors['bg_secondary'])
        left_header.pack(side=tk.LEFT, fill=tk.Y, padx=30, pady=20)
        
        # Animated logo canvas
        self.logo_canvas = tk.Canvas(left_header, width=60, height=60, 
                                    bg=self.colors['bg_secondary'], highlightthickness=0)
        self.logo_canvas.pack(side=tk.LEFT, padx=(0, 20))
        
        # Title and subtitle
        title_frame = tk.Frame(left_header, bg=self.colors['bg_secondary'])
        title_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        title_label = tk.Label(title_frame, text="SERVER FAN CONTROL", 
                              font=('Arial', 20, 'bold'), 
                              fg=self.colors['text_primary'], 
                              bg=self.colors['bg_secondary'])
        title_label.pack(anchor=tk.W)
        
        subtitle_label = tk.Label(title_frame, text="Multi-Vendor Management Dashboard", 
                                 font=('Arial', 11), 
                                 fg=self.colors['text_secondary'], 
                                 bg=self.colors['bg_secondary'])
        subtitle_label.pack(anchor=tk.W)
        
        # Right side - Global controls
        right_header = tk.Frame(header_frame, bg=self.colors['bg_secondary'])
        right_header.pack(side=tk.RIGHT, fill=tk.Y, padx=30, pady=20)
        
        # Global monitoring button
        self.global_monitor_btn = self.create_glass_button(
            right_header, "🌐 GLOBAL MONITOR", self.toggle_global_monitoring,
            color=self.colors['accent_blue'], width=180, height=35
        )
        self.global_monitor_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Add server button
        add_server_btn = self.create_glass_button(
            right_header, "+ ADD SERVER", self.show_add_server_dialog,
            color=self.colors['accent_green'], width=140, height=35
        )
        add_server_btn.pack(side=tk.RIGHT)
        
    def setup_main_content(self):
        """Create main content area with server cards"""
        # Create scrollable frame for server cards
        canvas_frame = tk.Frame(self.main_container, bg=self.colors['bg_primary'])
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Canvas and scrollbar for scrolling
        self.main_canvas = tk.Canvas(canvas_frame, bg=self.colors['bg_primary'], 
                                    highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_frame = tk.Frame(self.main_canvas, bg=self.colors['bg_primary'])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        
        self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Vendor sections
        self.setup_vendor_sections()
        
    def setup_vendor_sections(self):
        """Create sections for each vendor"""
        # Dell Section
        dell_section = self.create_vendor_section("Dell PowerEdge", "🖥️", DELL_AVAILABLE)
        dell_section.pack(fill=tk.X, pady=(0, 30))
        
        self.dell_servers_frame = tk.Frame(dell_section, bg=self.colors['bg_primary'])
        self.dell_servers_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # HPE Section
        hpe_section = self.create_vendor_section("HPE ProLiant", "🔧", HPE_AVAILABLE)
        hpe_section.pack(fill=tk.X, pady=(0, 30))
        
        self.hpe_servers_frame = tk.Frame(hpe_section, bg=self.colors['bg_primary'])
        self.hpe_servers_frame.pack(fill=tk.X, padx=20, pady=10)
        
    def create_vendor_section(self, title, icon, available):
        """Create a vendor section with modern styling"""
        section_frame = tk.Frame(self.scrollable_frame, bg=self.colors['bg_tertiary'], 
                                relief=tk.FLAT, bd=1)
        
        # Section header
        header_frame = tk.Frame(section_frame, bg=self.colors['bg_secondary'], height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        # Icon and title
        header_content = tk.Frame(header_frame, bg=self.colors['bg_secondary'])
        header_content.pack(fill=tk.Y, padx=20, pady=15)
        
        icon_label = tk.Label(header_content, text=icon, font=('Arial', 20), 
                             fg=self.colors['accent_blue'], bg=self.colors['bg_secondary'])
        icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        title_label = tk.Label(header_content, text=title, font=('Arial', 16, 'bold'), 
                              fg=self.colors['text_primary'], bg=self.colors['bg_secondary'])
        title_label.pack(side=tk.LEFT)
        
        # Status indicator
        status_text = "AVAILABLE" if available else "DISABLED"
        status_color = self.colors['accent_green'] if available else self.colors['accent_orange']
        
        status_label = tk.Label(header_content, text=status_text, font=('Arial', 10, 'bold'), 
                               fg=status_color, bg=self.colors['bg_secondary'])
        status_label.pack(side=tk.RIGHT)
        
        return section_frame
        
    def create_glass_button(self, parent, text, command, color=None, width=120, height=30):
        """Create a modern glass-morphism style button"""
        if color is None:
            color = self.colors['accent_blue']
            
        # Button container with rounded appearance
        btn_container = tk.Frame(parent, bg=parent['bg'], width=width, height=height)
        btn_container.pack_propagate(False)
        
        # Inner button frame
        btn_frame = tk.Frame(btn_container, bg=color, relief=tk.FLAT)
        btn_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, 
                       relwidth=0.95, relheight=0.8)
        
        # Button label
        btn_label = tk.Label(btn_frame, text=text, font=('Arial', 9, 'bold'), 
                            fg='white', bg=color, cursor='hand2')
        btn_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Hover effects
        def on_enter(e):
            hover_color = self.lighten_color(color, 0.2)
            btn_frame.config(bg=hover_color)
            btn_label.config(bg=hover_color)
            
        def on_leave(e):
            btn_frame.config(bg=color)
            btn_label.config(bg=color)
            
        def on_click(e):
            # Click animation
            btn_frame.config(relief=tk.SUNKEN)
            parent.after(100, lambda: btn_frame.config(relief=tk.FLAT))
            threading.Thread(target=command, daemon=True).start()
            
        # Bind events
        for widget in [btn_frame, btn_label]:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", on_click)
            
        return btn_container
        
    def setup_footer(self):
        """Create footer with status and logs"""
        footer_frame = tk.Frame(self.main_container, bg=self.colors['bg_secondary'], height=200)
        footer_frame.pack(fill=tk.X)
        footer_frame.pack_propagate(False)
        
        # Footer header
        footer_header = tk.Frame(footer_frame, bg=self.colors['bg_secondary'], height=40)
        footer_header.pack(fill=tk.X)
        footer_header.pack_propagate(False)
        
        status_title = tk.Label(footer_header, text="📊 SYSTEM STATUS & LOGS", 
                               font=('Arial', 12, 'bold'), 
                               fg=self.colors['text_primary'], 
                               bg=self.colors['bg_secondary'])
        status_title.pack(side=tk.LEFT, padx=20, pady=10)
        
        # Clear logs button
        clear_btn = self.create_glass_button(
            footer_header, "CLEAR LOGS", self.clear_logs,
            color=self.colors['accent_orange'], width=100, height=25
        )
        clear_btn.pack(side=tk.RIGHT, padx=20, pady=7)
        
        # Logs area
        logs_frame = tk.Frame(footer_frame, bg=self.colors['bg_tertiary'])
        logs_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Custom styled text widget
        self.status_text = scrolledtext.ScrolledText(
            logs_frame, height=8, width=100,
            bg=self.colors['bg_primary'], 
            fg=self.colors['text_primary'],
            font=('Consolas', 9),
            insertbackground=self.colors['text_primary'],
            selectbackground=self.colors['accent_blue'],
            relief=tk.FLAT,
            bd=0
        )
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def animate_ui(self):
        """Animate UI elements"""
        self.pulse_offset += 0.1
        
        # Animate logo
        self.draw_animated_logo()
        
        # Schedule next frame
        self.root.after(50, self.animate_ui)
        
    def draw_animated_logo(self):
        """Draw animated logo in header"""
        self.logo_canvas.delete("all")
        
        center = 30
        time_offset = time.time() * 2
        
        # Outer rotating ring
        for i in range(12):
            angle = (i * 30) + (time_offset * 30)
            radius = 25
            x = center + radius * math.cos(math.radians(angle))
            y = center + radius * math.sin(math.radians(angle))
            
            alpha = (math.sin(time_offset + i * 0.5) + 1) / 2
            intensity = int(255 * alpha)
            color = f"#{intensity:02x}{intensity//2:02x}{255-intensity:02x}"
            
            self.logo_canvas.create_oval(x-2, y-2, x+2, y+2, fill=color, outline="")
            
        # Inner pulsing core
        pulse = 1 + 0.3 * math.sin(time_offset * 3)
        core_radius = 8 * pulse
        
        self.logo_canvas.create_oval(
            center - core_radius, center - core_radius,
            center + core_radius, center + core_radius,
            fill=self.colors['accent_blue'], outline=self.colors['text_primary'], width=2
        )
        
    def lighten_color(self, color, factor):
        """Lighten a hex color"""
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        
    def log_message(self, message):
        """Add message to status log with timestamp and styling"""
        if hasattr(self, 'status_text'):
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Color code messages
            if "✓" in message:
                color_tag = "success"
            elif "✗" in message or "Error" in message:
                color_tag = "error"
            elif "⚠" in message or "Warning" in message:
                color_tag = "warning"
            else:
                color_tag = "info"
                
            log_entry = f"[{timestamp}] {message}\n"
            
            # Configure tags if not already done
            self.status_text.tag_config("success", foreground=self.colors['accent_green'])
            self.status_text.tag_config("error", foreground=self.colors['accent_orange'])
            self.status_text.tag_config("warning", foreground="#f1c40f")
            self.status_text.tag_config("info", foreground=self.colors['text_secondary'])
            
            # Insert with color
            self.status_text.insert(tk.END, log_entry, color_tag)
            self.status_text.see(tk.END)
            self.root.update_idletasks()
            
    def clear_logs(self):
        """Clear the logs display"""
        if hasattr(self, 'status_text'):
            self.status_text.delete(1.0, tk.END)
            self.log_message("📋 Logs cleared")
            
    def show_add_server_dialog(self):
        """Show dialog to add a new server"""
        dialog = ServerConfigDialog(self.root, self.colors, callback=self.on_server_added)
        
    def on_server_added(self, vendor, server_config):
        """Handle new server addition"""
        self.servers[vendor].append(server_config)
        self.save_server_configs()
        self.refresh_server_displays()
        self.log_message(f"✓ Added {vendor} server: {server_config['name']}")
        
    def refresh_server_displays(self):
        """Refresh the display of all server cards"""
        # Clear existing server UIs
        for child in self.dell_servers_frame.winfo_children():
            child.destroy()
        for child in self.hpe_servers_frame.winfo_children():
            child.destroy()
            
        self.server_uis = {'Dell': {}, 'HPE': {}}
        
        # Create Dell server cards
        if DELL_AVAILABLE:
            for server in self.servers['Dell']:
                card = self.create_server_card('Dell', server)
                card.pack(fill=tk.X, pady=10)
                
        # Create HPE server cards
        if HPE_AVAILABLE:
            for server in self.servers['HPE']:
                card = self.create_server_card('HPE', server)
                card.pack(fill=tk.X, pady=10)
                
    def create_server_card(self, vendor, server_config):
        """Create a visual server card"""
        parent_frame = self.dell_servers_frame if vendor == 'Dell' else self.hpe_servers_frame
        
        # Main card container
        card_frame = tk.Frame(parent_frame, bg=self.colors['bg_tertiary'], 
                             relief=tk.RAISED, bd=1)
        
        if vendor == 'Dell' and DELL_AVAILABLE:
            # Create Dell UI controller
            dell_ui = DellFanControllerUI(card_frame, server_config, 
                                        self.log_message, self.ipmitool_path)
            
            # Set callbacks for edit and remove
            dell_ui.set_callbacks(
                edit_callback=lambda config: self.edit_server(vendor, config),
                remove_callback=lambda config: self.remove_server(vendor, config)
            )
            
            self.server_uis['Dell'][server_config['name']] = dell_ui
            
        elif vendor == 'HPE' and HPE_AVAILABLE:
            # Create HPE UI
            self.create_hpe_server_ui(card_frame, server_config, vendor)
            
        return card_frame
        
    def edit_server(self, vendor, server_config):
        """Edit a server configuration"""
        dialog = ServerConfigDialog(self.root, self.colors, 
                                  callback=lambda v, new_config: self.on_server_edited(vendor, server_config, new_config),
                                  edit_mode=True, existing_config=server_config)
        
    def on_server_edited(self, vendor, old_config, new_config):
        """Handle server edit completion"""
        # Find and update the server in the list
        for i, server in enumerate(self.servers[vendor]):
            if server['name'] == old_config['name']:
                self.servers[vendor][i] = new_config
                break
                
        self.save_server_configs()
        self.refresh_server_displays()
        self.log_message(f"✓ Updated {vendor} server: {old_config['name']} -> {new_config['name']}")
        
    def remove_server(self, vendor, server_config):
        """Remove a server"""
        # Remove from servers list
        self.servers[vendor] = [s for s in self.servers[vendor] if s['name'] != server_config['name']]
        
        # Remove from UI tracking
        if server_config['name'] in self.server_uis[vendor]:
            del self.server_uis[vendor][server_config['name']]
            
        self.save_server_configs()
        self.refresh_server_displays()
        self.log_message(f"✓ Removed {vendor} server: {server_config['name']}")
        
    def create_hpe_server_ui(self, parent, server_config, vendor):
        """Create HPE server UI with management controls"""
        info_frame = tk.Frame(parent, bg=self.colors['bg_tertiary'])
        info_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # Header with management controls
        header_frame = tk.Frame(info_frame, bg=self.colors['bg_tertiary'])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Server info
        info_left = tk.Frame(header_frame, bg=self.colors['bg_tertiary'])
        info_left.pack(side=tk.LEFT, fill=tk.Y)
        
        title_label = tk.Label(info_left, text=f"HPE: {server_config['name']}", 
                              font=('Arial', 14, 'bold'), 
                              fg=self.colors['text_primary'], 
                              bg=self.colors['bg_tertiary'])
        title_label.pack(anchor=tk.W)
        
        ip_label = tk.Label(info_left, text=f"iLO IP: {server_config['ip']}", 
                           font=('Arial', 10), 
                           fg=self.colors['text_secondary'], 
                           bg=self.colors['bg_tertiary'])
        ip_label.pack(anchor=tk.W)
        
        # Management controls
        mgmt_frame = tk.Frame(header_frame, bg=self.colors['bg_tertiary'])
        mgmt_frame.pack(side=tk.RIGHT)
        
        edit_btn = self.create_glass_button(
            mgmt_frame, "⚙️", 
            lambda: self.edit_server(vendor, server_config),
            color=self.colors['accent_blue'], width=35, height=30
        )
        edit_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        remove_btn = self.create_glass_button(
            mgmt_frame, "🗑️", 
            lambda: self.confirm_and_remove_server(vendor, server_config),
            color=self.colors['accent_orange'], width=35, height=30
        )
        remove_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Control buttons
        controls_frame = tk.Frame(info_frame, bg=self.colors['bg_tertiary'])
        controls_frame.pack(fill=tk.X, pady=10)
        
        test_btn = self.create_glass_button(
            controls_frame, "TEST CONNECTION", 
            lambda: self.test_hpe_connection(server_config),
            color=self.colors['accent_green'], width=140
        )
        test_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        status_btn = self.create_glass_button(
            controls_frame, "GET STATUS", 
            lambda: self.get_hpe_status(server_config),
            color=self.colors['accent_blue'], width=120
        )
        status_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        profile_btn = self.create_glass_button(
            controls_frame, "THERMAL PROFILE", 
            lambda: self.show_hpe_thermal_controls(server_config),
            color='#aa88ff', width=140
        )
        profile_btn.pack(side=tk.LEFT)
        
    def confirm_and_remove_server(self, vendor, server_config):
        """Confirm and remove server with dialog"""
        if messagebox.askyesno("Confirm Remove", 
                             f"Are you sure you want to remove server '{server_config['name']}'?\n\n"
                             f"This action cannot be undone."):
            self.remove_server(vendor, server_config)
            
    def show_hpe_thermal_controls(self, server_config):
        """Show HPE thermal control dialog"""
        dialog = HPEThermalDialog(self.root, self.colors, server_config, self.log_message)
        
    def test_hpe_connection(self, server_config):
        """Test HPE server connection"""
        if not HPE_AVAILABLE:
            self.log_message("✗ HPE controller not available")
            return
            
        def test_thread():
            controller = HPEiLOController(server_config, self.log_message)
            controller.test_connection()
            controller.close_session()
            
        threading.Thread(target=test_thread, daemon=True).start()
        
    def get_hpe_status(self, server_config):
        """Get HPE server status"""
        if not HPE_AVAILABLE:
            self.log_message("✗ HPE controller not available")
            return
            
        def status_thread():
            controller = HPEiLOController(server_config, self.log_message)
            
            temperatures = controller.get_temperatures()
            if temperatures:
                self.log_message(f"=== {server_config['name']} Temperatures ===")
                for name, temp in temperatures.items():
                    self.log_message(f"{name}: {temp}°C")
                    
            fans = controller.get_fan_status()
            if fans:
                self.log_message(f"=== {server_config['name']} Fans ===")
                for name, fan_info in fans.items():
                    rpm = fan_info['rpm'] or 'N/A'
                    percent = fan_info['percent'] or 'N/A'
                    self.log_message(f"{name}: {rpm} RPM, {percent}%")
                    
            controller.close_session()
            
        threading.Thread(target=status_thread, daemon=True).start()
        
    def toggle_global_monitoring(self):
        """Toggle global monitoring"""
        if not self.monitoring:
            self.start_global_monitoring()
        else:
            self.stop_global_monitoring()
            
    def start_global_monitoring(self):
        """Start monitoring all servers"""
        if not any(self.servers.values()):
            messagebox.showwarning("Warning", "No servers configured for monitoring")
            return
            
        self.monitoring = True
        # Update button text
        for widget in self.global_monitor_btn.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label):
                        child.config(text="🛑 STOP MONITOR")
        
        self.log_message("🌐 Starting global monitoring...")
        threading.Thread(target=self.monitoring_loop, daemon=True).start()
        
    def stop_global_monitoring(self):
        """Stop global monitoring"""
        self.monitoring = False
        # Update button text
        for widget in self.global_monitor_btn.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label):
                        child.config(text="🌐 GLOBAL MONITOR")
        
        self.log_message("🛑 Stopping global monitoring...")
        
    def monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Monitor all servers
                for vendor in ['Dell', 'HPE']:
                    for server in self.servers[vendor]:
                        if not self.monitoring:
                            break
                        self.monitor_server(vendor, server)
                        
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.log_message(f"✗ Error in monitoring loop: {e}")
                time.sleep(30)
                
        self.monitoring = False
        
    def monitor_server(self, vendor, server_config):
        """Monitor a single server"""
        try:
            if vendor == 'Dell' and server_config['name'] in self.server_uis['Dell']:
                ui = self.server_uis['Dell'][server_config['name']]
                monitor_thread = ui.monitor_temperatures(45)
                monitor_thread.start()
                
        except Exception as e:
            self.log_message(f"✗ Error monitoring {vendor} server {server_config['name']}: {e}")
            
    def save_server_configs(self):
        """Save server configurations"""
        if KEYRING_AVAILABLE:
            try:
                config