import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
from datetime import datetime
import json
import os
import math
import ctypes
from ctypes import wintypes
import platform

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
        
        # Don't set geometry or title yet - do it after theming
        self.root.resizable(True, True)
        
        # Track window state for maximize/restore
        self.is_maximized = False
        self.normal_geometry = "1300x1150"
        
        # Modern dark theme colors
        self.colors = {
            'bg_primary': '#0d1117',
            'bg_secondary': '#161b22',
            'bg_tertiary': '#21262d',
            'accent_blue': '#58a6ff',
            'accent_green': '#3fb950',
            'accent_orange': '#f85149',
            'text_primary': '#f0f6fc',
            'text_secondary': '#8b949e',
            'border': '#30363d'
        }
        
        # Set up themed title bar FIRST
        self.setup_themed_title_bar()
        
        # Now set geometry after theming
        self.root.geometry("1300x1150")
        
        self.root.configure(bg=self.colors['bg_primary'])
        self.setup_dark_theme()
        
        # Variables
        self.monitoring = False
        self.servers = {'Dell': [], 'HPE': []}
        self.server_uis = {'Dell': {}, 'HPE': {}}
        self.ipmitool_path = self.find_ipmitool()
        self.service_name = "MultiVendor_Fan_Control_v2"
        self.tray_icon = None
        self.is_closing = False
        self.pulse_offset = 0
        
        # Setup UI
        self.setup_modern_ui()
        self.load_server_configs()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        if PYSTRAY_AVAILABLE:
            self.setup_system_tray()
            
        # Start animations after UI is fully setup
        self.animate_ui()

    def setup_window_styling(self):
        """Style the native title bar to match our theme"""
        
        # Set a proper title
        self.root.title("Multi-Vendor Server Fan Control v2.0")
        
        # Try to set dark mode title bar (Windows 10/11)
        try:
            import ctypes
            from ctypes import wintypes
            
            # Get window handle
            hwnd = self.root.winfo_id()
            
            # Enable dark mode title bar (Windows 10 version 1903+)
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(1)  # 1 for dark mode, 0 for light mode
            
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, 
                ctypes.byref(value), ctypes.sizeof(value)
            )
            
            # Also try the newer attribute ID for Windows 11
            DWMWA_USE_IMMERSIVE_DARK_MODE_NEW = 1029
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_NEW, 
                ctypes.byref(value), ctypes.sizeof(value)
            )
            
        except Exception as e:
            print(f"Dark title bar setup failed: {e}")
        
        # Create and set a custom icon
        self.create_custom_icon()

    def create_custom_icon(self):
        """Create a custom icon for the title bar"""
        try:
            from PIL import Image, ImageDraw
            import io
            import base64
            
            # Create a simple icon
            size = 32
            image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # Draw a simple server/fan icon
            # Background circle
            draw.ellipse([2, 2, size-2, size-2], fill='#58a6ff', outline='white', width=2)
            
            # Fan blades (simplified)
            center = size // 2
            for i in range(4):
                angle = i * 90
                x1 = center + 8 * (1 if i % 2 == 0 else -1)
                y1 = center + 8 * (1 if i < 2 else -1)
                draw.line([center, center, x1, y1], fill='white', width=2)
            
            # Center dot
            draw.ellipse([center-3, center-3, center+3, center+3], fill='white')
            
            # Save as ICO format in memory
            ico_buffer = io.BytesIO()
            image.save(ico_buffer, format='ICO', sizes=[(32, 32)])
            ico_buffer.seek(0)
            
            # Set the icon
            self.root.iconphoto(True, tk.PhotoImage(data=base64.b64encode(ico_buffer.read())))
            
        except Exception as e:
            print(f"Custom icon creation failed: {e}")
            # Fallback: try to set a simple icon using text
            try:
                # Create a simple text-based icon
                icon_image = tk.PhotoImage(width=32, height=32)
                icon_image.put('#58a6ff', to=(0, 0, 32, 32))
                self.root.iconphoto(True, icon_image)
            except Exception as fallback_error:
                print(f"Fallback icon failed: {fallback_error}")

    def setup_themed_title_bar(self):
        """Complete title bar theming setup"""
        
        # Style the window
        self.setup_window_styling()
        
        # Set window background to match theme immediately
        self.root.configure(bg=self.colors['bg_primary'])
        
        # Update the window after setting up theming
        self.root.update_idletasks()

    def minimize_window(self):
        """Alternative minimize method"""
        self.root.wm_state('iconic')
        
    def toggle_maximize(self):
        """Toggle between maximized and normal window state"""
        try:
            if self.is_maximized:
                # Restore to normal size
                self.root.state('normal')
                self.root.geometry(self.normal_geometry)
                self.is_maximized = False
                # Update maximize button
                self.update_maximize_button_text("□")
            else:
                # Store current geometry before maximizing
                self.normal_geometry = self.root.geometry()
                # Maximize window
                self.root.state('zoomed')
                self.is_maximized = True
                # Update maximize button  
                self.update_maximize_button_text("❐")
        except Exception as e:
            print(f"Maximize error: {e}")

    def update_maximize_button_text(self, text):
        """Helper method to update maximize button text"""
        try:
            for widget in self.maximize_btn.winfo_children():
                if isinstance(widget, tk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label):
                            child.config(text=text)
                            break
        except Exception as e:
            print(f"Button update error: {e}")

    def setup_window_dragging(self):
        """Enable window dragging for the header area only"""
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        def start_drag(event):
            self.drag_start_x = event.x_root - self.root.winfo_x()
            self.drag_start_y = event.y_root - self.root.winfo_y()
            
        def do_drag(event):
            x = event.x_root - self.drag_start_x
            y = event.y_root - self.drag_start_y
            self.root.geometry(f"+{x}+{y}")
        
        # Store these functions so we can bind them to header elements later
        self.start_drag = start_drag
        self.do_drag = do_drag
        
    def setup_dark_theme(self):
        """Configure dark theme for ttk widgets"""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('TLabel', background=self.colors['bg_primary'], foreground=self.colors['text_primary'])
        style.configure('TEntry', fieldbackground=self.colors['bg_tertiary'], background=self.colors['bg_tertiary'],
                       foreground=self.colors['text_primary'], bordercolor=self.colors['border'],
                       insertcolor=self.colors['text_primary'])
        style.configure('TButton', background=self.colors['bg_tertiary'], foreground=self.colors['text_primary'],
                       bordercolor=self.colors['border'], focuscolor='none')
        style.map('TButton', background=[('active', self.colors['accent_blue']), ('pressed', self.colors['accent_blue'])])
        style.configure('TFrame', background=self.colors['bg_primary'], bordercolor=self.colors['border'])
        style.configure('TLabelFrame', background=self.colors['bg_primary'], foreground=self.colors['text_primary'],
                       bordercolor=self.colors['border'])
        style.configure('TScale', background=self.colors['bg_tertiary'], troughcolor=self.colors['bg_primary'],
                       bordercolor=self.colors['border'], lightcolor=self.colors['accent_blue'],
                       darkcolor=self.colors['accent_blue'])
        style.configure('Vertical.TScrollbar', background=self.colors['bg_tertiary'],
                       troughcolor=self.colors['bg_primary'], bordercolor=self.colors['border'],
                       arrowcolor=self.colors['text_secondary'], darkcolor=self.colors['bg_secondary'],
                       lightcolor=self.colors['bg_secondary'])
        
    def find_ipmitool(self):
        """Find ipmitool executable for Dell servers"""
        paths_to_check = [
            "C:\\IPMI\\ipmitool.exe",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "IPMI", "ipmitool.exe")
        ]
        
        for path in paths_to_check:
            if os.path.exists(path):
                return path
                
        try:
            import subprocess
            result = subprocess.run(["where", "ipmitool"], capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                return "ipmitool"
        except:
            pass
            
        return None
        
    def setup_modern_ui(self):
        """Setup the modern UI"""
        self.main_container = tk.Frame(self.root, bg=self.colors['bg_primary'])
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        self.setup_header()
        self.setup_main_content()
        self.setup_footer()

    def setup_header(self):
        """Create header without window controls (use native ones instead)"""
        header_frame = tk.Frame(self.main_container, bg=self.colors['bg_secondary'], height=80)  # Reduced height
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        # Left side - Logo and title
        left_header = tk.Frame(header_frame, bg=self.colors['bg_secondary'])
        left_header.pack(side=tk.LEFT, fill=tk.Y, padx=30, pady=15)  # Reduced padding
        
        self.logo_canvas = tk.Canvas(left_header, width=50, height=50,  # Smaller logo
                                    bg=self.colors['bg_secondary'], highlightthickness=0)
        self.logo_canvas.pack(side=tk.LEFT, padx=(0, 15))
        
        title_frame = tk.Frame(left_header, bg=self.colors['bg_secondary'])
        title_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        title_label = tk.Label(title_frame, text="SERVER FAN CONTROL", 
                            font=('Arial', 16, 'bold'),  # Smaller font
                            fg=self.colors['text_primary'], 
                            bg=self.colors['bg_secondary'])
        title_label.pack(anchor=tk.W)
        
        subtitle_label = tk.Label(title_frame, text="Multi-Vendor Management Dashboard", 
                                font=('Arial', 9),  # Smaller font
                                fg=self.colors['text_secondary'], 
                                bg=self.colors['bg_secondary'])
        subtitle_label.pack(anchor=tk.W)
        
        # Right side - Only the functional buttons (no window controls)
        right_header = tk.Frame(header_frame, bg=self.colors['bg_secondary'])
        right_header.pack(side=tk.RIGHT, fill=tk.Y, padx=30, pady=15)
        
        self.global_monitor_btn = self.create_glass_button(
            right_header, "🌐 GLOBAL MONITOR", self.toggle_global_monitoring,
            color=self.colors['accent_blue'], width=160, height=30
        )
        self.global_monitor_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        add_server_btn = self.create_glass_button(
            right_header, "+ ADD SERVER", self.show_add_server_dialog,
            color=self.colors['accent_green'], width=120, height=30
        )
        add_server_btn.pack(side=tk.RIGHT)

    def create_window_control_button(self, parent, text, command, color):
        """Create window control buttons with better event handling"""
        btn_frame = tk.Frame(parent, bg=color, width=30, height=30)
        btn_frame.pack_propagate(False)
        
        btn_label = tk.Label(btn_frame, text=text, font=('Arial', 12, 'bold'), 
                            fg='white', bg=color, cursor='hand2')
        btn_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        def on_enter(e):
            hover_color = self.lighten_color(color, 0.2)
            btn_frame.config(bg=hover_color)
            btn_label.config(bg=hover_color)
            
        def on_leave(e):
            btn_frame.config(bg=color)
            btn_label.config(bg=color)
            
        def on_click(e):
            try:
                # Stop event propagation
                e.widget.focus_set()
                # Execute command in a thread to prevent blocking
                threading.Thread(target=command, daemon=True).start()
            except Exception as error:
                print(f"Button click error: {error}")
                # Try direct execution as fallback
                try:
                    command()
                except Exception as fallback_error:
                    print(f"Fallback command error: {fallback_error}")
        
        # Bind events to both frame and label
        for widget in [btn_frame, btn_label]:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", on_click)
        
        return btn_frame        
               
    def setup_main_content(self):
        """Create main content with side-by-side layout"""
        content_container = tk.Frame(self.main_container, bg=self.colors['bg_primary'])
        content_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Horizontal layout for vendors
        vendors_frame = tk.Frame(content_container, bg=self.colors['bg_primary'])
        vendors_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Dell servers
        dell_column = tk.Frame(vendors_frame, bg=self.colors['bg_primary'])
        dell_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        dell_header = self.create_vendor_header("Dell PowerEdge", "🖥️", DELL_AVAILABLE)
        dell_header.pack(fill=tk.X, pady=(0, 10))
        
        dell_canvas_frame = tk.Frame(dell_column, bg=self.colors['bg_primary'])
        dell_canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.dell_canvas = tk.Canvas(dell_canvas_frame, bg=self.colors['bg_primary'], highlightthickness=0)
        dell_scrollbar = ttk.Scrollbar(dell_canvas_frame, orient="vertical", command=self.dell_canvas.yview)
        self.dell_scrollable_frame = tk.Frame(self.dell_canvas, bg=self.colors['bg_primary'])
        
        self.dell_scrollable_frame.bind("<Configure>",
            lambda e: self.dell_canvas.configure(scrollregion=self.dell_canvas.bbox("all")))
        
        self.dell_canvas.create_window((0, 0), window=self.dell_scrollable_frame, anchor="nw")
        self.dell_canvas.configure(yscrollcommand=dell_scrollbar.set)
        
        self.dell_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dell_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.dell_servers_frame = tk.Frame(self.dell_scrollable_frame, bg=self.colors['bg_primary'])
        self.dell_servers_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Right side - HPE servers
        hpe_column = tk.Frame(vendors_frame, bg=self.colors['bg_primary'])
        hpe_column.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        hpe_header = self.create_vendor_header("HPE ProLiant", "🔧", HPE_AVAILABLE)
        hpe_header.pack(fill=tk.X, pady=(0, 10))
        
        hpe_canvas_frame = tk.Frame(hpe_column, bg=self.colors['bg_primary'])
        hpe_canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.hpe_canvas = tk.Canvas(hpe_canvas_frame, bg=self.colors['bg_primary'], highlightthickness=0)
        hpe_scrollbar = ttk.Scrollbar(hpe_canvas_frame, orient="vertical", command=self.hpe_canvas.yview)
        self.hpe_scrollable_frame = tk.Frame(self.hpe_canvas, bg=self.colors['bg_primary'])
        
        self.hpe_scrollable_frame.bind("<Configure>",
            lambda e: self.hpe_canvas.configure(scrollregion=self.hpe_canvas.bbox("all")))
        
        self.hpe_canvas.create_window((0, 0), window=self.hpe_scrollable_frame, anchor="nw")
        self.hpe_canvas.configure(yscrollcommand=hpe_scrollbar.set)
        
        self.hpe_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hpe_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.hpe_servers_frame = tk.Frame(self.hpe_scrollable_frame, bg=self.colors['bg_primary'])
        self.hpe_servers_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    def create_vendor_header(self, title, icon, available):
        """Create vendor section header"""
        header_frame = tk.Frame(self.main_container, bg=self.colors['bg_secondary'], height=50)
        header_frame.pack_propagate(False)
        
        header_content = tk.Frame(header_frame, bg=self.colors['bg_secondary'])
        header_content.pack(fill=tk.Y, padx=20, pady=10)
        
        icon_label = tk.Label(header_content, text=icon, font=('Arial', 16), 
                             fg=self.colors['accent_blue'], bg=self.colors['bg_secondary'])
        icon_label.pack(side=tk.LEFT, padx=(0, 10))
        
        title_label = tk.Label(header_content, text=title, font=('Arial', 14, 'bold'), 
                              fg=self.colors['text_primary'], bg=self.colors['bg_secondary'])
        title_label.pack(side=tk.LEFT)
        
        status_text = "AVAILABLE" if available else "DISABLED"
        status_color = self.colors['accent_green'] if available else self.colors['accent_orange']
        
        status_label = tk.Label(header_content, text=status_text, font=('Arial', 9, 'bold'), 
                               fg=status_color, bg=self.colors['bg_secondary'])
        status_label.pack(side=tk.RIGHT)
        
        return header_frame
        
    def create_glass_button(self, parent, text, command, color=None, width=120, height=30):
        """Create modern glass button"""
        if color is None:
            color = self.colors['accent_blue']
            
        btn_container = tk.Frame(parent, bg=parent['bg'], width=width, height=height)
        btn_container.pack_propagate(False)
        
        btn_frame = tk.Frame(btn_container, bg=color, relief=tk.FLAT)
        btn_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, relwidth=0.95, relheight=0.8)
        
        btn_label = tk.Label(btn_frame, text=text, font=('Arial', 9, 'bold'), 
                            fg='white', bg=color, cursor='hand2')
        btn_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        def on_enter(e):
            hover_color = self.lighten_color(color, 0.2)
            btn_frame.config(bg=hover_color)
            btn_label.config(bg=hover_color)
            
        def on_leave(e):
            btn_frame.config(bg=color)
            btn_label.config(bg=color)
            
        def on_click(e):
            btn_frame.config(relief=tk.SUNKEN)
            parent.after(100, lambda: btn_frame.config(relief=tk.FLAT))
            threading.Thread(target=command, daemon=True).start()
            
        for widget in [btn_frame, btn_label]:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", on_click)
            
        return btn_container
        
    def setup_footer(self):
        """Create footer with logs"""
        footer_frame = tk.Frame(self.main_container, bg=self.colors['bg_secondary'], height=180)
        footer_frame.pack(fill=tk.X)
        footer_frame.pack_propagate(False)
        
        footer_header = tk.Frame(footer_frame, bg=self.colors['bg_secondary'], height=35)
        footer_header.pack(fill=tk.X)
        footer_header.pack_propagate(False)
        
        status_title = tk.Label(footer_header, text="📊 SYSTEM STATUS & LOGS", 
                               font=('Arial', 11, 'bold'), 
                               fg=self.colors['text_primary'], 
                               bg=self.colors['bg_secondary'])
        status_title.pack(side=tk.LEFT, padx=20, pady=8)
        
        clear_btn = self.create_glass_button(
            footer_header, "CLEAR LOGS", self.clear_logs,
            color=self.colors['accent_orange'], width=90, height=22
        )
        clear_btn.pack(side=tk.RIGHT, padx=20, pady=6)
        
        logs_frame = tk.Frame(footer_frame, bg=self.colors['bg_tertiary'])
        logs_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        self.status_text = scrolledtext.ScrolledText(
            logs_frame, height=7, width=100,
            bg=self.colors['bg_primary'], 
            fg=self.colors['text_primary'],
            font=('Consolas', 9),
            insertbackground=self.colors['text_primary'],
            selectbackground=self.colors['accent_blue'],
            relief=tk.FLAT, bd=0
        )
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
    def animate_ui(self):
        """Animate UI elements"""
        self.pulse_offset += 0.1
        self.draw_animated_logo()
        self.root.after(50, self.animate_ui)
        
    def draw_animated_logo(self):
        """Draw animated logo"""
        self.logo_canvas.delete("all")
        
        center = 30
        time_offset = time.time() * 2
        
        for i in range(12):
            angle = (i * 30) + (time_offset * 30)
            radius = 25
            x = center + radius * math.cos(math.radians(angle))
            y = center + radius * math.sin(math.radians(angle))
            
            alpha = (math.sin(time_offset + i * 0.5) + 1) / 2
            intensity = int(255 * alpha)
            color = f"#{intensity:02x}{intensity//2:02x}{255-intensity:02x}"
            
            self.logo_canvas.create_oval(x-2, y-2, x+2, y+2, fill=color, outline="")
            
        pulse = 1 + 0.3 * math.sin(time_offset * 3)
        core_radius = 8 * pulse
        
        self.logo_canvas.create_oval(
            center - core_radius, center - core_radius,
            center + core_radius, center + core_radius,
            fill=self.colors['accent_blue'], outline=self.colors['text_primary'], width=2
        )
        
    def lighten_color(self, color, factor):
        """Lighten hex color"""
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        
    def log_message(self, message):
        """Add message to log with styling"""
        if hasattr(self, 'status_text'):
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            if "✓" in message:
                color_tag = "success"
            elif "✗" in message or "Error" in message:
                color_tag = "error"
            elif "⚠" in message or "Warning" in message:
                color_tag = "warning"
            else:
                color_tag = "info"
                
            log_entry = f"[{timestamp}] {message}\n"
            
            self.status_text.tag_config("success", foreground=self.colors['accent_green'])
            self.status_text.tag_config("error", foreground=self.colors['accent_orange'])
            self.status_text.tag_config("warning", foreground="#f1c40f")
            self.status_text.tag_config("info", foreground=self.colors['text_secondary'])
            
            self.status_text.insert(tk.END, log_entry, color_tag)
            self.status_text.see(tk.END)
            self.root.update_idletasks()
            
    def clear_logs(self):
        """Clear logs"""
        if hasattr(self, 'status_text'):
            self.status_text.delete(1.0, tk.END)
            self.log_message("📋 Logs cleared")
            
    def show_add_server_dialog(self):
        """Show add server dialog"""
        dialog = ServerConfigDialog(self.root, self.colors, callback=self.on_server_added)
        
    def on_server_added(self, vendor, server_config):
        """Handle server addition"""
        self.servers[vendor].append(server_config)
        self.save_server_configs()
        self.refresh_server_displays()
        self.log_message(f"✓ Added {vendor} server: {server_config['name']}")
        
    def refresh_server_displays(self):
        """Refresh server displays"""
        for child in self.dell_servers_frame.winfo_children():
            child.destroy()
        for child in self.hpe_servers_frame.winfo_children():
            child.destroy()
            
        self.server_uis = {'Dell': {}, 'HPE': {}}
        
        if DELL_AVAILABLE:
            for server in self.servers['Dell']:
                card = self.create_server_card('Dell', server)
                card.pack(fill=tk.X, pady=10)
                
        if HPE_AVAILABLE:
            for server in self.servers['HPE']:
                card = self.create_server_card('HPE', server)
                card.pack(fill=tk.X, pady=10)
                
    def create_server_card(self, vendor, server_config):
        """Create server card"""
        parent_frame = self.dell_servers_frame if vendor == 'Dell' else self.hpe_servers_frame
        
        card_frame = tk.Frame(parent_frame, bg=self.colors['bg_tertiary'], relief=tk.RAISED, bd=1)
        
        if vendor == 'Dell' and DELL_AVAILABLE:
            dell_ui = DellFanControllerUI(card_frame, server_config, self.log_message, self.ipmitool_path)
            dell_ui.set_callbacks(
                edit_callback=lambda config: self.edit_server(vendor, config),
                remove_callback=lambda config: self.remove_server(vendor, config)
            )
            self.server_uis['Dell'][server_config['name']] = dell_ui
            
        elif vendor == 'HPE' and HPE_AVAILABLE:
            self.create_hpe_server_ui(card_frame, server_config, vendor)
            
        return card_frame
        
    def edit_server(self, vendor, server_config):
        """Edit server"""
        dialog = ServerConfigDialog(self.root, self.colors, 
                                  callback=lambda v, new_config: self.on_server_edited(vendor, server_config, new_config),
                                  edit_mode=True, existing_config=server_config)
        
    def on_server_edited(self, vendor, old_config, new_config):
        """Handle server edit"""
        for i, server in enumerate(self.servers[vendor]):
            if server['name'] == old_config['name']:
                self.servers[vendor][i] = new_config
                break
                
        self.save_server_configs()
        self.refresh_server_displays()
        self.log_message(f"✓ Updated {vendor} server: {old_config['name']} -> {new_config['name']}")
        
    def remove_server(self, vendor, server_config):
        """Remove server"""
        self.servers[vendor] = [s for s in self.servers[vendor] if s['name'] != server_config['name']]
        
        if server_config['name'] in self.server_uis[vendor]:
            del self.server_uis[vendor][server_config['name']]
            
        self.save_server_configs()
        self.refresh_server_displays()
        self.log_message(f"✓ Removed {vendor} server: {server_config['name']}")
        
    def create_hpe_server_ui(self, parent, server_config, vendor):
        """Create HPE server UI"""
        info_frame = tk.Frame(parent, bg=self.colors['bg_tertiary'])
        info_frame.pack(fill=tk.X, padx=20, pady=20)
        
        header_frame = tk.Frame(info_frame, bg=self.colors['bg_tertiary'])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
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
        """Confirm server removal"""
        if messagebox.askyesno("Confirm Remove", 
                             f"Are you sure you want to remove server '{server_config['name']}'?\n\n"
                             f"This action cannot be undone."):
            self.remove_server(vendor, server_config)
            
    def show_hpe_thermal_controls(self, server_config):
        """Show HPE thermal controls"""
        dialog = HPEThermalDialog(self.root, self.colors, server_config, self.log_message)
        
    def test_hpe_connection(self, server_config):
        """Test HPE connection"""
        if not HPE_AVAILABLE:
            self.log_message("✗ HPE controller not available")
            return
            
        def test_thread():
            controller = HPEiLOController(server_config, self.log_message)
            controller.test_connection()
            controller.close_session()
            
        threading.Thread(target=test_thread, daemon=True).start()
        
    def get_hpe_status(self, server_config):
        """Get HPE status"""
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
        """Start global monitoring"""
        if not any(self.servers.values()):
            messagebox.showwarning("Warning", "No servers configured for monitoring")
            return
            
        self.monitoring = True
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
                for vendor in ['Dell', 'HPE']:
                    for server in self.servers[vendor]:
                        if not self.monitoring:
                            break
                        self.monitor_server(vendor, server)
                        
                time.sleep(30)
                
            except Exception as e:
                self.log_message(f"✗ Error in monitoring loop: {e}")
                time.sleep(30)
                
        self.monitoring = False
        
    def monitor_server(self, vendor, server_config):
        """Monitor single server"""
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
                config_data = json.dumps(self.servers)
                keyring.set_password(self.service_name, "server_configs", config_data)
            except Exception as e:
                self.log_message(f"✗ Failed to save configs: {e}")
                
    def load_server_configs(self):
        """Load server configurations"""
        if KEYRING_AVAILABLE:
            try:
                config_data = keyring.get_password(self.service_name, "server_configs")
                if config_data:
                    self.servers = json.loads(config_data)
                    self.refresh_server_displays()
                    self.log_message("✓ Server configurations loaded")
            except Exception as e:
                self.log_message(f"Note: Could not load configs: {e}")
                
    def create_tray_icon(self):
        """Create system tray icon"""
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='black')
        draw = ImageDraw.Draw(image)
        
        for i in range(4):
            y = 12 + i * 12
            draw.rectangle([16, y, 48, y + 8], fill='#58a6ff', outline='white')
            
        return image
        
    def setup_system_tray(self):
        """Setup system tray"""
        if not PYSTRAY_AVAILABLE:
            return
            
        icon_image = self.create_tray_icon()
        
        menu = pystray.Menu(
            item('Show Dashboard', self.show_window),
            item('Global Monitor', self.toggle_global_monitoring),
            pystray.Menu.SEPARATOR,
            item('Exit', self.exit_application)
        )
        
        self.tray_icon = pystray.Icon("Multi-Vendor Fan Control", icon_image, 
                                     "Multi-Vendor Fan Control", menu)
        
    def on_closing(self):
        """Handle window close"""
        if PYSTRAY_AVAILABLE and not self.is_closing:
            self.hide_window()
        else:
            self.exit_application()
            
    def hide_window(self):
        """Hide to system tray"""
        self.root.withdraw()
        if self.tray_icon and not self.tray_icon.visible:
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            
    def show_window(self, icon=None, item=None):
        """Show window from tray"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        if self.tray_icon and self.tray_icon.visible:
            self.tray_icon.stop()
            
    def exit_application(self):
        """Exit application safely"""
        try:
            self.is_closing = True
            
            if self.monitoring:
                self.monitoring = False
                
            if hasattr(self, 'tray_icon') and self.tray_icon and self.tray_icon.visible:
                self.tray_icon.stop()
            
            # Force close after a short delay
            self.root.after(100, self._force_quit)
            
        except Exception as e:
            print(f"Exit error: {e}")
            self._force_quit()

    def _force_quit(self):
        """Force quit the application"""
        try:
            self.root.quit()
        except:
            pass
        try:
            self.root.destroy()
        except:
            pass
        import sys
        sys.exit(0)

class ServerConfigDialog:
    def __init__(self, parent, colors, callback=None, edit_mode=False, existing_config=None):
        self.parent = parent
        self.colors = colors
        self.callback = callback
        self.edit_mode = edit_mode
        self.existing_config = existing_config or {}
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Server" if edit_mode else "Add Server")
        self.dialog.geometry("500x450")
        self.dialog.configure(bg=colors['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_dialog()
        
    def setup_dialog(self):
        """Setup add/edit server dialog"""
        # Header
        header_frame = tk.Frame(self.dialog, bg=self.colors['bg_secondary'], height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_text = "✏️ EDIT SERVER" if self.edit_mode else "➕ ADD NEW SERVER"
        title_label = tk.Label(header_frame, text=title_text, 
                              font=('Arial', 16, 'bold'), 
                              fg=self.colors['text_primary'], 
                              bg=self.colors['bg_secondary'])
        title_label.pack(pady=15)
        
        # Form
        form_frame = tk.Frame(self.dialog, bg=self.colors['bg_primary'])
        form_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        # Vendor selection
        tk.Label(form_frame, text="Vendor:", font=('Arial', 12, 'bold'), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).pack(anchor=tk.W, pady=(0, 5))
        
        self.vendor_var = tk.StringVar(value=self.existing_config.get('vendor', 'Dell'))
        vendor_frame = tk.Frame(form_frame, bg=self.colors['bg_primary'])
        vendor_frame.pack(fill=tk.X, pady=(0, 20))
        
        dell_radio = tk.Radiobutton(vendor_frame, text="Dell PowerEdge", variable=self.vendor_var, 
                                   value="Dell", font=('Arial', 10),
                                   fg=self.colors['text_primary'], bg=self.colors['bg_primary'],
                                   selectcolor=self.colors['bg_tertiary'],
                                   activebackground=self.colors['bg_primary'],
                                   state='disabled' if self.edit_mode else 'normal')
        dell_radio.pack(side=tk.LEFT, padx=(0, 30))
        
        hpe_radio = tk.Radiobutton(vendor_frame, text="HPE ProLiant", variable=self.vendor_var, 
                                  value="HPE", font=('Arial', 10),
                                  fg=self.colors['text_primary'], bg=self.colors['bg_primary'],
                                  selectcolor=self.colors['bg_tertiary'],
                                  activebackground=self.colors['bg_primary'],
                                  state='disabled' if self.edit_mode else 'normal')
        hpe_radio.pack(side=tk.LEFT)
        
        # Server name
        tk.Label(form_frame, text="Server Name:", font=('Arial', 12, 'bold'), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).pack(anchor=tk.W, pady=(0, 5))
        
        self.name_var = tk.StringVar(value=self.existing_config.get('name', ''))
        name_entry = tk.Entry(form_frame, textvariable=self.name_var, font=('Arial', 11),
                             bg=self.colors['bg_tertiary'], fg=self.colors['text_primary'],
                             insertbackground=self.colors['text_primary'], relief=tk.FLAT, bd=5)
        name_entry.pack(fill=tk.X, pady=(0, 20))
        
        # IP Address
        tk.Label(form_frame, text="Management IP:", font=('Arial', 12, 'bold'), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).pack(anchor=tk.W, pady=(0, 5))
        
        self.ip_var = tk.StringVar(value=self.existing_config.get('ip', ''))
        ip_entry = tk.Entry(form_frame, textvariable=self.ip_var, font=('Arial', 11),
                           bg=self.colors['bg_tertiary'], fg=self.colors['text_primary'],
                           insertbackground=self.colors['text_primary'], relief=tk.FLAT, bd=5)
        ip_entry.pack(fill=tk.X, pady=(0, 20))
        
        # Username
        tk.Label(form_frame, text="Username:", font=('Arial', 12, 'bold'), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).pack(anchor=tk.W, pady=(0, 5))
        
        self.username_var = tk.StringVar(value=self.existing_config.get('username', ''))
        username_entry = tk.Entry(form_frame, textvariable=self.username_var, font=('Arial', 11),
                                 bg=self.colors['bg_tertiary'], fg=self.colors['text_primary'],
                                 insertbackground=self.colors['text_primary'], relief=tk.FLAT, bd=5)
        username_entry.pack(fill=tk.X, pady=(0, 20))
        
        # Password
        tk.Label(form_frame, text="Password:", font=('Arial', 12, 'bold'), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).pack(anchor=tk.W, pady=(0, 5))
        
        self.password_var = tk.StringVar(value=self.existing_config.get('password', ''))
        password_entry = tk.Entry(form_frame, textvariable=self.password_var, show="*", font=('Arial', 11),
                                 bg=self.colors['bg_tertiary'], fg=self.colors['text_primary'],
                                 insertbackground=self.colors['text_primary'], relief=tk.FLAT, bd=5)
        password_entry.pack(fill=tk.X, pady=(0, 30))
        
        # Buttons
        button_frame = tk.Frame(form_frame, bg=self.colors['bg_primary'])
        button_frame.pack(fill=tk.X)
        
        cancel_btn = tk.Button(button_frame, text="CANCEL", font=('Arial', 10, 'bold'),
                              bg=self.colors['accent_orange'], fg='white',
                              relief=tk.FLAT, bd=0, padx=30, pady=10,
                              command=self.dialog.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        save_text = "UPDATE SERVER" if self.edit_mode else "ADD SERVER"
        save_btn = tk.Button(button_frame, text=save_text, font=('Arial', 10, 'bold'),
                            bg=self.colors['accent_green'], fg='white',
                            relief=tk.FLAT, bd=0, padx=30, pady=10,
                            command=self.save_server)
        save_btn.pack(side=tk.RIGHT)
        
    def save_server(self):
        """Save server configuration"""
        name = self.name_var.get().strip()
        ip = self.ip_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        vendor = self.vendor_var.get()
        
        if not all([name, ip, username, password]):
            messagebox.showerror("Error", "All fields are required")
            return
            
        server_config = {
            'name': name,
            'ip': ip,
            'username': username,
            'password': password,
            'vendor': vendor
        }
        
        if self.callback:
            self.callback(vendor, server_config)
            
        self.dialog.destroy()


class HPEThermalDialog:
    def __init__(self, parent, colors, server_config, log_callback):
        self.colors = colors
        self.server_config = server_config
        self.log_callback = log_callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"HPE Thermal Controls - {server_config['name']}")
        self.dialog.geometry("500x450")
        self.dialog.configure(bg=colors['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup HPE thermal control dialog"""
        # Header
        header_frame = tk.Frame(self.dialog, bg=self.colors['bg_secondary'], height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="🔧 HPE THERMAL CONTROLS", 
                              font=('Arial', 16, 'bold'), 
                              fg=self.colors['text_primary'], 
                              bg=self.colors['bg_secondary'])
        title_label.pack(pady=15)
        
        # Content
        content_frame = tk.Frame(self.dialog, bg=self.colors['bg_primary'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        # Thermal Profile Selection
        profile_frame = tk.LabelFrame(content_frame, text="Thermal Profile", 
                                     bg=self.colors['bg_tertiary'], fg=self.colors['text_primary'],
                                     font=('Arial', 12, 'bold'))
        profile_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.profile_var = tk.StringVar(value="Acoustic")
        profiles = [("Performance", "Maximum cooling performance"), 
                   ("Acoustic", "Balanced noise and cooling"), 
                   ("Custom", "User-defined settings")]
        
        for profile, description in profiles:
            frame = tk.Frame(profile_frame, bg=self.colors['bg_tertiary'])
            frame.pack(fill=tk.X, padx=10, pady=5)
            
            radio = tk.Radiobutton(frame, text=profile, variable=self.profile_var, value=profile,
                                  font=('Arial', 11, 'bold'), fg=self.colors['text_primary'],
                                  bg=self.colors['bg_tertiary'], selectcolor=self.colors['bg_primary'],
                                  activebackground=self.colors['bg_tertiary'])
            radio.pack(anchor=tk.W)
            
            desc_label = tk.Label(frame, text=description, font=('Arial', 9),
                                 fg=self.colors['text_secondary'], bg=self.colors['bg_tertiary'])
            desc_label.pack(anchor=tk.W, padx=(20, 0))
        
        # Fan Speed Control
        speed_frame = tk.LabelFrame(content_frame, text="Manual Fan Speed", 
                                   bg=self.colors['bg_tertiary'], fg=self.colors['text_primary'],
                                   font=('Arial', 12, 'bold'))
        speed_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(speed_frame, text="Minimum Fan Speed (%):", font=('Arial', 11),
                fg=self.colors['text_primary'], bg=self.colors['bg_tertiary']).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        self.speed_var = tk.StringVar(value="30")
        speed_scale = tk.Scale(speed_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                              variable=self.speed_var, font=('Arial', 10),
                              bg=self.colors['bg_tertiary'], fg=self.colors['text_primary'],
                              troughcolor=self.colors['bg_primary'], 
                              activebackground=self.colors['accent_blue'])
        speed_scale.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Control Buttons
        control_frame = tk.Frame(content_frame, bg=self.colors['bg_primary'])
        control_frame.pack(fill=tk.X, pady=20)
        
        apply_profile_btn = tk.Button(control_frame, text="APPLY PROFILE", 
                                     font=('Arial', 10, 'bold'),
                                     bg=self.colors['accent_blue'], fg='white',
                                     relief=tk.FLAT, bd=0, padx=20, pady=8,
                                     command=self.apply_thermal_profile)
        apply_profile_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        set_speed_btn = tk.Button(control_frame, text="SET FAN SPEED", 
                                 font=('Arial', 10, 'bold'),
                                 bg=self.colors['accent_green'], fg='white',
                                 relief=tk.FLAT, bd=0, padx=20, pady=8,
                                 command=self.set_fan_speed)
        set_speed_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        auto_btn = tk.Button(control_frame, text="ENABLE AUTO", 
                            font=('Arial', 10, 'bold'),
                            bg='#ffaa00', fg='white',
                            relief=tk.FLAT, bd=0, padx=20, pady=8,
                            command=self.enable_auto_control)
        auto_btn.pack(side=tk.LEFT)
        
        close_btn = tk.Button(control_frame, text="CLOSE", 
                             font=('Arial', 10, 'bold'),
                             bg=self.colors['accent_orange'], fg='white',
                             relief=tk.FLAT, bd=0, padx=20, pady=8,
                             command=self.dialog.destroy)
        close_btn.pack(side=tk.RIGHT)
        
    def apply_thermal_profile(self):
        """Apply thermal profile"""
        if not HPE_AVAILABLE:
            self.log_callback("✗ HPE controller not available")
            return
            
        profile = self.profile_var.get()
        
        def apply_thread():
            controller = HPEiLOController(self.server_config, self.log_callback)
            controller.set_thermal_profile(profile)
            controller.close_session()
            
        threading.Thread(target=apply_thread, daemon=True).start()
        
    def set_fan_speed(self):
        """Set fan speed"""
        if not HPE_AVAILABLE:
            self.log_callback("✗ HPE controller not available")
            return
            
        speed = int(self.speed_var.get())
        
        def set_speed_thread():
            controller = HPEiLOController(self.server_config, self.log_callback)
            controller.set_fan_speed_percent(None, speed)
            controller.close_session()
            
        threading.Thread(target=set_speed_thread, daemon=True).start()
        
    def enable_auto_control(self):
        """Enable auto control"""
        if not HPE_AVAILABLE:
            self.log_callback("✗ HPE controller not available")
            return
            
        def enable_thread():
            controller = HPEiLOController(self.server_config, self.log_callback)
            controller.enable_automatic_control()
            controller.close_session()
            
        threading.Thread(target=enable_thread, daemon=True).start()


def main():
    root = tk.Tk()
    
    app = ModernMultiVendorFanController(root)
    
    # No menu bar since we removed the title bar
    # All functionality now accessible through the UI buttons
    
    try:
        # Log startup info
        app.log_message("🚀 Multi-Vendor Server Fan Control v2.0 Started")
        app.log_message(f"📊 Dell Support: {'✓ Available' if DELL_AVAILABLE else '✗ Disabled'}")
        app.log_message(f"🔧 HPE Support: {'✓ Available' if HPE_AVAILABLE else '✗ Disabled'}")
        app.log_message(f"🔐 Keyring: {'✓ Available' if KEYRING_AVAILABLE else '✗ Disabled'}")
        app.log_message(f"📱 System Tray: {'✓ Available' if PYSTRAY_AVAILABLE else '✗ Disabled'}")
        
        if app.ipmitool_path:
            app.log_message(f"🔨 ipmitool: ✓ Found at {app.ipmitool_path}")
        else:
            app.log_message("⚠️ ipmitool: Not found - Dell support limited")
            
        app.log_message("📖 Ready! Add servers using the + ADD SERVER button")
        app.log_message("💡 Use ⚙️ to edit servers and 🗑️ to remove them")
        app.log_message("📈 Dell servers support fan curve editor via CURVE button")
        app.log_message("🖱️ Drag the header to move the window")
        
        root.mainloop()
    except KeyboardInterrupt:
        app.exit_application()

if __name__ == "__main__":
    main()