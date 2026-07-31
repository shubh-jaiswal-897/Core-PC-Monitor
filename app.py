import os
import sys
import threading
import time
import customtkinter as ctk
from tkinter import messagebox, ttk
import psutil
import optimizer_core

# Set theme and color options
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ApexOptimizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Admin check & self-elevation
        if not optimizer_core.is_admin():
            # Show a brief dialog or immediately try to elevate
            optimizer_core.run_as_admin()

        self.title("Apex PC Optimizer & Speed Booster")
        self.geometry("1100x700")
        self.minsize(1000, 650)

        # State variables
        self.selected_tab = "dashboard"
        self.files_scanned = []
        self.scanned_bytes = 0
        self.startup_items = []
        self.power_plans = []
        self.active_power_guid = None
        self.monitoring_active = True

        # Custom Styling Colors
        self.bg_color_sidebar = "#111111"
        self.bg_color_content = "#1A1A1A"
        self.accent_color = "#3B82F6"  # Bright Blue
        self.danger_color = "#EF4444"  # Red
        self.success_color = "#10B981"  # Green
        self.text_muted = "#9CA3AF"

        # Build UI layout
        self.configure(fg_color=self.bg_color_content)
        self.grid_columnconfigure(0, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=1) # Main Content
        self.grid_rowconfigure(0, weight=1)    # Height fills

        # ----------------- SIDEBAR -----------------
        self.sidebar_frame = ctk.CTkFrame(self, fg_color=self.bg_color_sidebar, corner_radius=0, width=220)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        # Title / Logo
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="APEX PC", font=ctk.CTkFont(size=22, weight="bold", family="Outfit"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 5))
        
        self.logo_sub = ctk.CTkLabel(self.sidebar_frame, text="PC SPEED BOOSTER", font=ctk.CTkFont(size=10, weight="bold", family="Inter"), text_color=self.accent_color)
        self.logo_sub.grid(row=1, column=0, padx=20, pady=(0, 30))

        # Navigation Buttons
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "📊 Dashboard"),
            ("cleaner", "🧹 System Cleaner"),
            ("processes", "⚙️ Startup & Processes"),
            ("tweaks", "⚡ Performance Tweaks")
        ]

        for i, (tab_id, label) in enumerate(nav_items):
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=label,
                font=ctk.CTkFont(size=14, weight="bold"),
                fg_color="transparent",
                text_color="#FFFFFF",
                hover_color="#2B2B2B",
                height=45,
                anchor="w",
                corner_radius=8,
                command=lambda tid=tab_id: self.select_tab(tid)
            )
            btn.grid(row=i+2, column=0, padx=15, pady=6, sticky="ew")
            self.nav_buttons[tab_id] = btn

        # Admin Badge
        self.admin_badge = ctk.CTkFrame(self.sidebar_frame, fg_color="#1E293B", corner_radius=6)
        self.admin_badge.grid(row=7, column=0, padx=15, pady=20, sticky="ew")
        
        self.admin_label = ctk.CTkLabel(
            self.admin_badge,
            text="🛡️ ADMINISTRATOR MODE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.success_color
        )
        self.admin_label.pack(padx=10, pady=8)

        # ----------------- MAIN CONTENT FRAME -----------------
        self.content_frame = ctk.CTkFrame(self, fg_color=self.bg_color_content, corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1) # Tab Content
        self.content_frame.grid_rowconfigure(1, weight=0) # Log Box

        # Create Tab Frames
        self.frames = {
            "dashboard": self.create_dashboard_frame(),
            "cleaner": self.create_cleaner_frame(),
            "processes": self.create_processes_frame(),
            "tweaks": self.create_tweaks_frame()
        }

        # Show Dashboard by default
        self.select_tab("dashboard")

        # ----------------- LOG CONSOLE PANEL (Bottom) -----------------
        self.log_panel = ctk.CTkFrame(self.content_frame, fg_color="#141414", corner_radius=10, height=130)
        self.log_panel.grid(row=1, column=0, sticky="ew", pady=(15, 0))
        self.log_panel.grid_propagate(False)
        self.log_panel.grid_columnconfigure(0, weight=1)
        self.log_panel.grid_rowconfigure(1, weight=1)

        self.log_header = ctk.CTkLabel(
            self.log_panel,
            text="💻 SYSTEM OPTIMIZATION CONSOLE LOGS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.accent_color
        )
        self.log_header.grid(row=0, column=0, padx=15, pady=(8, 2), sticky="w")

        self.log_text = ctk.CTkTextbox(
            self.log_panel,
            font=ctk.CTkFont(size=11, family="Consolas"),
            fg_color="#141414",
            text_color="#A7F3D0", # Light Mint Green
            activate_scrollbars=True
        )
        self.log_text.grid(row=1, column=0, padx=15, pady=(0, 8), sticky="nsew")
        self.log_text.configure(state="disabled")

        # Log system information
        self.log("Apex PC Optimizer initiated successfully.")
        self.log(f"Current OS: Windows {psutil.win_service_get('DiagTrack').name if 'DiagTrack' in dir(psutil) else ''} System Platform")

        # Start Realtime stats monitoring thread
        self.stats_thread = threading.Thread(target=self.update_hardware_stats, daemon=True)
        self.stats_thread.start()


    def log(self, message):
        """Thread-safe logging helper."""
        def append_log():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(0, append_log)


    def select_tab(self, tab_id):
        """Switches the active frame in the content view."""
        self.selected_tab = tab_id
        
        # Update tab visual indicators
        for tid, btn in self.nav_buttons.items():
            if tid == tab_id:
                btn.configure(fg_color=self.accent_color, text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color="#E5E7EB")

        # Show selected frame, hide others
        for tid, frame in self.frames.items():
            if tid == tab_id:
                frame.grid(row=0, column=0, sticky="nsew")
                # Trigger specific tab entry behaviors
                if tid == "processes":
                    self.refresh_startup_and_processes()
                elif tid == "tweaks":
                    self.refresh_tweaks_view()
            else:
                frame.grid_forget()


    # ==========================================
    # CREATING TAB VIEWS
    # ==========================================

    def create_dashboard_frame(self):
        """Creates the Dashboard UI layout."""
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        # Welcome Text
        welcome_lbl = ctk.CTkLabel(
            frame,
            text="📊 System Performance Dashboard",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        welcome_lbl.grid(row=0, column=0, columnspan=2, pady=(10, 20), sticky="w")

        # Hardware Info Meters Frame
        meters_frame = ctk.CTkFrame(frame, fg_color="#222222", corner_radius=12)
        meters_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 20), padx=2)
        meters_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # CPU Monitor Card
        cpu_card = ctk.CTkFrame(meters_frame, fg_color="transparent")
        cpu_card.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.cpu_lbl = ctk.CTkLabel(cpu_card, text="CPU Usage: 0.0%", font=ctk.CTkFont(size=14, weight="bold"))
        self.cpu_lbl.pack(pady=(0, 8))
        self.cpu_bar = ctk.CTkProgressBar(cpu_card, width=180, height=12, progress_color=self.accent_color)
        self.cpu_bar.set(0.0)
        self.cpu_bar.pack(pady=5)

        # RAM Monitor Card
        ram_card = ctk.CTkFrame(meters_frame, fg_color="transparent")
        ram_card.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.ram_lbl = ctk.CTkLabel(ram_card, text="RAM Usage: 0% (0 / 0 GB)", font=ctk.CTkFont(size=14, weight="bold"))
        self.ram_lbl.pack(pady=(0, 8))
        self.ram_bar = ctk.CTkProgressBar(ram_card, width=180, height=12, progress_color=self.accent_color)
        self.ram_bar.set(0.0)
        self.ram_bar.pack(pady=5)

        # Disk C: Monitor Card
        disk_card = ctk.CTkFrame(meters_frame, fg_color="transparent")
        disk_card.grid(row=0, column=2, padx=20, pady=20, sticky="nsew")
        self.disk_lbl = ctk.CTkLabel(disk_card, text="Disk C: Free: 0 GB", font=ctk.CTkFont(size=14, weight="bold"))
        self.disk_lbl.pack(pady=(0, 8))
        self.disk_bar = ctk.CTkProgressBar(disk_card, width=180, height=12, progress_color=self.accent_color)
        self.disk_bar.set(0.0)
        self.disk_bar.pack(pady=5)

        # Actions Panel (Bottom Half)
        actions_frame = ctk.CTkFrame(frame, fg_color="#1E1E1E", corner_radius=12)
        actions_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=2, pady=5)
        actions_frame.grid_columnconfigure((0, 1), weight=1)
        actions_frame.grid_rowconfigure(1, weight=1)

        actions_title = ctk.CTkLabel(
            actions_frame, 
            text="⚡ Direct Optimization & Safety Options",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.accent_color
        )
        actions_title.grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 10), sticky="w")

        # Column 1: Restore Point Creation
        rp_card = ctk.CTkFrame(actions_frame, fg_color="#262626", corner_radius=10)
        rp_card.grid(row=1, column=0, padx=20, pady=(5, 20), sticky="nsew")
        
        rp_desc = ctk.CTkLabel(
            rp_card,
            text="🛡️ System Restore Point\n\nCreate a safety backup point in Windows before executing cleanups or altering registry policies.",
            font=ctk.CTkFont(size=13),
            wraplength=300,
            justify="center"
        )
        rp_desc.pack(padx=20, pady=(20, 15))

        self.btn_restore = ctk.CTkButton(
            rp_card,
            text="Create Restore Point",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#475569", # Slate color
            hover_color="#334155",
            height=40,
            command=self.trigger_restore_point
        )
        self.btn_restore.pack(padx=20, pady=(5, 20), fill="x")

        # Column 2: One-Click Quick Optimize
        opt_card = ctk.CTkFrame(actions_frame, fg_color="#262626", corner_radius=10)
        opt_card.grid(row=1, column=1, padx=20, pady=(5, 20), sticky="nsew")

        opt_desc = ctk.CTkLabel(
            opt_card,
            text="🚀 One-Click Speed Booster\n\nInstantly empty application RAM cache, flush DNS network routes, and safely clear standard Windows junk files.",
            font=ctk.CTkFont(size=13),
            wraplength=300,
            justify="center"
        )
        opt_desc.pack(padx=20, pady=(20, 15))

        self.btn_optimize = ctk.CTkButton(
            opt_card,
            text="Quick Optimize",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.success_color,
            hover_color="#059669",
            height=40,
            command=self.trigger_quick_optimize
        )
        self.btn_optimize.pack(padx=20, pady=(5, 20), fill="x")

        return frame


    def create_cleaner_frame(self):
        """Creates the System Junk Cleaner UI layout."""
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=2) # Checkboxes and Buttons
        frame.grid_columnconfigure(1, weight=3) # Scanned files Preview list
        frame.grid_rowconfigure(1, weight=1)

        # Title
        title_lbl = ctk.CTkLabel(
            frame,
            text="🧹 System Junk & Cache Cleaner",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_lbl.grid(row=0, column=0, columnspan=2, pady=(10, 15), sticky="w")

        # Left Card: Category Selection
        left_panel = ctk.CTkFrame(frame, fg_color="#222222", corner_radius=12)
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(2, 10), pady=2)
        left_panel.grid_columnconfigure(0, weight=1)
        left_panel.grid_rowconfigure(2, weight=1)

        cat_title = ctk.CTkLabel(
            left_panel,
            text="Select Junk Types to Clean",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.accent_color
        )
        cat_title.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")

        # Category Checkboxes
        chk_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        chk_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        self.junk_checkboxes = {}
        categories = optimizer_core.get_junk_categories()
        for idx, (cat_name, info) in enumerate(categories.items()):
            var = ctk.StringVar(value="on") # Checked by default
            chk = ctk.CTkCheckBox(
                chk_frame, 
                text=f"{cat_name}\n({info['description']})",
                font=ctk.CTkFont(size=12),
                variable=var,
                onvalue="on",
                offvalue="off",
                checkbox_height=20,
                checkbox_width=20
            )
            chk.grid(row=idx, column=0, pady=12, sticky="w")
            self.junk_checkboxes[cat_name] = var

        # Action Buttons Area
        btn_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=20, pady=(15, 20), sticky="s")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_scan = ctk.CTkButton(
            btn_frame,
            text="Scan & Preview",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.accent_color,
            width=120,
            height=38,
            command=self.trigger_scan
        )
        self.btn_scan.grid(row=0, column=0, padx=8, pady=5)

        self.btn_clean = ctk.CTkButton(
            btn_frame,
            text="Clean Junk",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.danger_color,
            hover_color="#DC2626",
            width=120,
            height=38,
            state="disabled",
            command=self.trigger_clean
        )
        self.btn_clean.grid(row=0, column=1, padx=8, pady=5)

        # Right Card: Scan Results list & Summary
        right_panel = ctk.CTkFrame(frame, fg_color="#222222", corner_radius=12)
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 2), pady=2)
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(2, weight=1)

        # Summary Header
        self.clean_summary_lbl = ctk.CTkLabel(
            right_panel,
            text="Scan Preview: Not Scanned Yet",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FFFFFF"
        )
        self.clean_summary_lbl.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        # Progress bar
        self.clean_progress = ctk.CTkProgressBar(right_panel, height=8, progress_color=self.accent_color)
        self.clean_progress.set(0.0)
        self.clean_progress.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        # Files Scanned Text Box
        self.files_textbox = ctk.CTkTextbox(
            right_panel,
            fg_color="#1E1E1E",
            text_color=self.text_muted,
            font=ctk.CTkFont(size=11, family="Consolas")
        )
        self.files_textbox.grid(row=2, column=0, padx=20, pady=(5, 20), sticky="nsew")
        self.files_textbox.configure(state="disabled")

        return frame


    def create_processes_frame(self):
        """Creates the Startup Programs and Processes Manager UI layout."""
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        # Title
        title_lbl = ctk.CTkLabel(
            frame,
            text="⚙️ Process & Startup Manager",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_lbl.grid(row=0, column=0, columnspan=2, pady=(10, 15), sticky="w")

        # Left Card: Startup Programs
        startup_panel = ctk.CTkFrame(frame, fg_color="#222222", corner_radius=12)
        startup_panel.grid(row=1, column=0, sticky="nsew", padx=(2, 10), pady=2)
        startup_panel.grid_columnconfigure(0, weight=1)
        startup_panel.grid_rowconfigure(2, weight=1)

        startup_header_frame = ctk.CTkFrame(startup_panel, fg_color="transparent")
        startup_header_frame.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        startup_header_frame.grid_columnconfigure(0, weight=1)

        startup_title = ctk.CTkLabel(
            startup_header_frame,
            text="🚀 Non-Essential Startup Programs",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.accent_color
        )
        startup_title.grid(row=0, column=0, sticky="w")

        btn_refresh_startup = ctk.CTkButton(
            startup_header_frame,
            text="🔄 Refresh",
            width=70,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            command=self.refresh_startup_items
        )
        btn_refresh_startup.grid(row=0, column=1, sticky="e")

        # Scrollable container for Startup items
        self.startup_scroll = ctk.CTkScrollableFrame(startup_panel, fg_color="#1E1E1E", corner_radius=8)
        self.startup_scroll.grid(row=1, column=0, padx=15, pady=(5, 15), sticky="nsew")
        self.startup_scroll.grid_columnconfigure(0, weight=1)

        # Right Card: Running Processes
        proc_panel = ctk.CTkFrame(frame, fg_color="#222222", corner_radius=12)
        proc_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 2), pady=2)
        proc_panel.grid_columnconfigure(0, weight=1)
        proc_panel.grid_rowconfigure(2, weight=1)

        proc_header_frame = ctk.CTkFrame(proc_panel, fg_color="transparent")
        proc_header_frame.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        proc_header_frame.grid_columnconfigure(0, weight=1)

        proc_title = ctk.CTkLabel(
            proc_header_frame,
            text="🔥 Active High-Resource Processes",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.accent_color
        )
        proc_title.grid(row=0, column=0, sticky="w")

        btn_refresh_proc = ctk.CTkButton(
            proc_header_frame,
            text="🔄 Refresh",
            width=70,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            command=self.refresh_process_items
        )
        btn_refresh_proc.grid(row=0, column=1, sticky="e")

        # Scrollable container for processes
        self.proc_scroll = ctk.CTkScrollableFrame(proc_panel, fg_color="#1E1E1E", corner_radius=8)
        self.proc_scroll.grid(row=1, column=0, padx=15, pady=(5, 15), sticky="nsew")
        self.proc_scroll.grid_columnconfigure(0, weight=1)

        return frame


    def create_tweaks_frame(self):
        """Creates the Windows Performance Tweaks UI layout."""
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        # Title
        title_lbl = ctk.CTkLabel(
            frame,
            text="⚡ Windows Performance Tweaks",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_lbl.grid(row=0, column=0, columnspan=2, pady=(10, 15), sticky="w")

        # Left Panel: Telemetry & Windows Policies
        telemetry_panel = ctk.CTkFrame(frame, fg_color="#222222", corner_radius=12)
        telemetry_panel.grid(row=1, column=0, sticky="nsew", padx=(2, 10), pady=2)
        telemetry_panel.grid_columnconfigure(0, weight=1)

        tel_title = ctk.CTkLabel(
            telemetry_panel,
            text="Privacy & Telemetry Blocking",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.accent_color
        )
        tel_title.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        tel_desc = ctk.CTkLabel(
            telemetry_panel,
            text="Disabling Microsoft tracking and usage diagnostics improves system privacy and eliminates background tracking network requests.",
            font=ctk.CTkFont(size=12),
            text_color=self.text_muted,
            wraplength=350,
            justify="left"
        )
        tel_desc.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        # Telemetry switch widget
        self.telemetry_switch_var = ctk.StringVar(value="off")
        self.telemetry_switch = ctk.CTkSwitch(
            telemetry_panel,
            text="Disable Telemetry & Diagnostics Services",
            font=ctk.CTkFont(size=13, weight="bold"),
            variable=self.telemetry_switch_var,
            onvalue="on",
            offvalue="off",
            command=self.toggle_telemetry
        )
        self.telemetry_switch.grid(row=2, column=0, padx=20, pady=10, sticky="w")

        # Info Box
        info_box = ctk.CTkFrame(telemetry_panel, fg_color="#1E293B", corner_radius=8)
        info_box.grid(row=3, column=0, padx=20, pady=(30, 20), sticky="ew")
        
        info_lbl = ctk.CTkLabel(
            info_box,
            text="🔒 Note: This tweak will stop DiagTrack, dmwappushservice, and WerSvc Windows services, and write to registry policies to prevent automatic data collection.",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#93C5FD",
            wraplength=320,
            justify="left"
        )
        info_lbl.pack(padx=15, pady=15)

        # Right Panel: Power Plans & Network Tweaks
        power_panel = ctk.CTkFrame(frame, fg_color="#222222", corner_radius=12)
        power_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 2), pady=2)
        power_panel.grid_columnconfigure(0, weight=1)

        pwr_title = ctk.CTkLabel(
            power_panel,
            text="Power Schemes & Cache Flushers",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.accent_color
        )
        pwr_title.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")

        # Power Plan Dropdown selection
        pwr_lbl = ctk.CTkLabel(power_panel, text="Active Power Plan:", font=ctk.CTkFont(size=13, weight="bold"))
        pwr_lbl.grid(row=1, column=0, padx=20, pady=(10, 2), sticky="w")

        self.power_dropdown = ctk.CTkOptionMenu(
            power_panel,
            values=["Loading..."],
            command=self.change_power_plan,
            width=250
        )
        self.power_dropdown.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="w")

        # Button to force Ultimate Performance plan
        self.btn_ultimate_power = ctk.CTkButton(
            power_panel,
            text="Enable Ultimate Performance",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#B45309", # Amber color
            hover_color="#92400E",
            command=self.activate_ultimate_power
        )
        self.btn_ultimate_power.grid(row=3, column=0, padx=20, pady=(5, 20), sticky="w")

        # Dividers
        divider = ctk.CTkFrame(power_panel, height=2, fg_color="#334155")
        divider.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        # Flusher Actions
        flushers_lbl = ctk.CTkLabel(power_panel, text="Cache Flush Tools:", font=ctk.CTkFont(size=13, weight="bold"))
        flushers_lbl.grid(row=5, column=0, padx=20, pady=(5, 5), sticky="w")

        self.btn_flush_dns = ctk.CTkButton(
            power_panel,
            text="Flush DNS Resolver Cache",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            height=32,
            command=self.trigger_dns_flush
        )
        self.btn_flush_dns.grid(row=6, column=0, padx=20, pady=6, sticky="ew")

        self.btn_flush_ram = ctk.CTkButton(
            power_panel,
            text="Empty Memory Cache (Standby List)",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            height=32,
            command=self.trigger_mem_flush
        )
        self.btn_flush_ram.grid(row=7, column=0, padx=20, pady=6, sticky="ew")

        return frame


    # ==========================================
    # WORKER LOGICS & THREADS
    # ==========================================

    def update_hardware_stats(self):
        """Runs in background thread. Periodically pulls CPU, RAM, Disk data."""
        while self.monitoring_active:
            try:
                # CPU
                cpu = psutil.cpu_percent(interval=1)
                
                # RAM
                mem = psutil.virtual_memory()
                ram_percent = mem.percent
                ram_used_gb = mem.used / (1024 * 1024 * 1024)
                ram_total_gb = mem.total / (1024 * 1024 * 1024)
                
                # Disk C:
                disk = psutil.disk_usage("C:\\")
                disk_percent = disk.percent
                disk_free_gb = disk.free / (1024 * 1024 * 1024)

                # Thread safe widget updates
                def update_widgets():
                    if self.selected_tab == "dashboard":
                        self.cpu_lbl.configure(text=f"CPU Usage: {cpu:.1f}%")
                        self.cpu_bar.set(cpu / 100.0)

                        self.ram_lbl.configure(text=f"RAM Usage: {ram_percent}% ({ram_used_gb:.1f} / {ram_total_gb:.1f} GB)")
                        self.ram_bar.set(ram_percent / 100.0)

                        self.disk_lbl.configure(text=f"Disk C: Free: {disk_free_gb:.1f} GB")
                        self.disk_bar.set((100 - disk_percent) / 100.0) # Free ratio
                
                self.after(0, update_widgets)
            except Exception:
                pass
            time.sleep(1)


    def trigger_restore_point(self):
        """Creates System Restore point in a separate thread."""
        self.btn_restore.configure(state="disabled", text="Creating Backup...")
        self.log("Initializing System Restore Point creation...")

        def worker():
            success, msg = optimizer_core.create_restore_point()
            self.log(msg)
            
            def done():
                self.btn_restore.configure(state="normal", text="Create Restore Point")
                if success:
                    messagebox.showinfo("Success", "System Restore Point created successfully.")
                else:
                    messagebox.showwarning("Failed", f"Could not create Restore Point.\nMake sure System Protection is enabled on drive C:.\nError details: {msg}")
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


    def trigger_quick_optimize(self):
        """Triggers combined Quick Speed booster in background."""
        self.btn_optimize.configure(state="disabled", text="Optimizing...")
        self.log("Starting quick optimization...")

        def worker():
            # 1. Flush DNS
            self.log("Flushing DNS Resolver cache...")
            dns_ok, dns_msg = optimizer_core.flush_dns()
            self.log(dns_msg)

            # 2. Flush RAM memory
            self.log("Purging inactive memory cache (Standby list) & Working sets...")
            mem_res = optimizer_core.optimize_memory()
            if mem_res.get("working_sets_success"):
                self.log(f"Emptied RAM working sets for {mem_res['processes_flushed']} processes.")
            if mem_res.get("standby_cleared"):
                self.log("Windows Standby List purged successfully.")
            else:
                self.log(f"Warning: Standby List clear error: {mem_res.get('standby_error', 'Access Denied')}")

            # 3. Quick Temp cleaner (default User & System Temp)
            self.log("Scanning temporary directories for basic cleanup...")
            files, bytes_scanned = optimizer_core.scan_junk(["User Temp", "System Temp"])
            freed, errs, _ = optimizer_core.clean_junk(files)
            freed_mb = freed / (1024 * 1024)
            self.log(f"Quick Cleanup Complete! Safely deleted {len(files) - errs} files ({freed_mb:.1f} MB freed).")

            def done():
                self.btn_optimize.configure(state="normal", text="Quick Optimize")
                messagebox.showinfo(
                    "Optimization Complete", 
                    f"Speed Boost Successful!\n\n• DNS flushed\n• RAM cache cleared\n• Safely freed {freed_mb:.1f} MB disk space."
                )
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


    # ==========================================
    # CLEANER LOGIC
    # ==========================================

    def trigger_scan(self):
        """Scans selected directories in a background thread."""
        selected = []
        for cat_name, var in self.junk_checkboxes.items():
            if var.get() == "on":
                selected.append(cat_name)

        if not selected:
            messagebox.showwarning("Selection Required", "Please select at least one junk category to scan.")
            return

        self.btn_scan.configure(state="disabled", text="Scanning...")
        self.btn_clean.configure(state="disabled")
        self.files_textbox.configure(state="normal")
        self.files_textbox.delete("1.0", "end")
        self.files_textbox.configure(state="disabled")
        self.clean_progress.set(0.0)
        self.clean_summary_lbl.configure(text="Scanning file system...")
        self.log(f"Scanning junk categories: {', '.join(selected)}")

        def worker():
            files, total_size = optimizer_core.scan_junk(selected)
            self.files_scanned = files
            self.scanned_bytes = total_size

            size_mb = total_size / (1024 * 1024)
            size_gb = size_mb / 1024

            self.log(f"Scan complete. Found {len(files)} files ({size_mb:.1f} MB / {size_gb:.2f} GB potential freed space).")

            def done():
                self.btn_scan.configure(state="normal", text="Scan & Preview")
                self.clean_summary_lbl.configure(text=f"Total Space to Free: {size_mb:.1f} MB ({len(files)} files)")
                self.clean_progress.set(1.0)
                
                # Show list in textbox
                self.files_textbox.configure(state="normal")
                for f in files[:200]: # Limit display to top 200 files for responsiveness
                    sz_kb = f["size"] / 1024
                    self.files_textbox.insert("end", f"[{f['category']}] ({sz_kb:.1f} KB) - {f['path']}\n")
                
                if len(files) > 200:
                    self.files_textbox.insert("end", f"\n... and {len(files) - 200} more files (see Console for details) ...\n")
                
                self.files_textbox.configure(state="disabled")

                if len(files) > 0:
                    self.btn_clean.configure(state="normal")
                else:
                    self.btn_clean.configure(state="disabled")
                    messagebox.showinfo("Scan Completed", "No junk files found in selected categories.")

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


    def trigger_clean(self):
        """Executes deletion of the scanned files in a background thread."""
        if not self.files_scanned:
            return

        confirm = messagebox.askyesno(
            "Confirm Cleanup", 
            f"Are you sure you want to delete {len(self.files_scanned)} junk files?\nThis will clear caches and system logs."
        )
        if not confirm:
            return

        self.btn_clean.configure(state="disabled", text="Cleaning...")
        self.btn_scan.configure(state="disabled")
        self.log(f"Starting deletion of {len(self.files_scanned)} scanned files...")

        def worker():
            total = len(self.files_scanned)
            
            def progress_cb(current, total_files, file_path):
                # Update progress bar occasionally to avoid throttling
                if current % 10 == 0 or current == total_files:
                    def update():
                        self.clean_progress.set(current / total_files)
                        self.clean_summary_lbl.configure(text=f"Deleting: {current} / {total_files} files...")
                    self.after(0, update)

            freed, errs, skipped_details = optimizer_core.clean_junk(self.files_scanned, progress_callback=progress_cb)
            freed_mb = freed / (1024 * 1024)

            self.log(f"Cleanup finished. Successfully freed {freed_mb:.1f} MB disk space. Skipped {errs} locked files.")
            for detail in skipped_details[:10]: # Log first 10 skipped files in console
                self.log(detail)

            def done():
                self.btn_clean.configure(state="disabled", text="Clean Junk")
                self.btn_scan.configure(state="normal", text="Scan & Preview")
                self.clean_summary_lbl.configure(text=f"Clean Completed! Freed: {freed_mb:.1f} MB")
                self.files_scanned = []
                self.scanned_bytes = 0
                
                self.files_textbox.configure(state="normal")
                self.files_textbox.delete("1.0", "end")
                self.files_textbox.insert("end", f"Cleanup Successful!\n\nDisk Space Freed: {freed_mb:.1f} MB\nLocked Files Skipped: {errs}\n\nAll temporary cache databases have been safely flushed.")
                self.files_textbox.configure(state="disabled")
                
                messagebox.showinfo("Cleanup Finished", f"Successfully cleared junk files.\nFreed: {freed_mb:.1f} MB.")
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


    # ==========================================
    # PROCESSES & STARTUP LOGIC
    # ==========================================

    def refresh_startup_and_processes(self):
        """Loads startup programs and process info concurrently."""
        self.refresh_startup_items()
        self.refresh_process_items()


    def refresh_startup_items(self):
        """Retrieves and populates the startup program items list."""
        self.log("Scanning registry and folders for startup items...")
        
        # Clear current scrollview widgets
        for widget in self.startup_scroll.winfo_children():
            widget.destroy()

        def worker():
            items = optimizer_core.get_startup_items()
            self.startup_items = items

            def populate():
                if not items:
                    lbl = ctk.CTkLabel(self.startup_scroll, text="No startup items found.", font=ctk.CTkFont(size=12, slant="italic"))
                    lbl.pack(pady=20)
                    return

                for idx, item in enumerate(items):
                    item_frame = ctk.CTkFrame(self.startup_scroll, fg_color="#2A2A2A" if item["enabled"] else "#151515", corner_radius=6)
                    item_frame.pack(fill="x", pady=4, padx=5)

                    text_color = "#FFFFFF" if item["enabled"] else self.text_muted
                    lbl_name = ctk.CTkLabel(
                        item_frame,
                        text=item["name"][:35],
                        font=ctk.CTkFont(size=12, weight="bold"),
                        text_color=text_color,
                        anchor="w"
                    )
                    lbl_name.pack(side="left", padx=10, pady=8)

                    lbl_src = ctk.CTkLabel(
                        item_frame,
                        text=f"({item['source']})",
                        font=ctk.CTkFont(size=10),
                        text_color=self.text_muted,
                        anchor="w"
                    )
                    lbl_src.pack(side="left", padx=5)

                    # Toggle Switch
                    switch_var = ctk.StringVar(value="on" if item["enabled"] else "off")
                    sw = ctk.CTkSwitch(
                        item_frame,
                        text="",
                        variable=switch_var,
                        onvalue="on",
                        offvalue="off",
                        width=36,
                        command=lambda itm=item, svar=switch_var: self.toggle_startup(itm, svar)
                    )
                    sw.pack(side="right", padx=10)

            self.after(0, populate)

        threading.Thread(target=worker, daemon=True).start()


    def toggle_startup(self, item, var):
        """Toggles enable/disable state of startup item."""
        enable = var.get() == "on"
        action_word = "Enabling" if enable else "Disabling"
        self.log(f"{action_word} startup program: {item['name']}")

        def worker():
            success = optimizer_core.toggle_startup_item(item, enable)
            if success:
                self.log(f"Successfully changed startup status for {item['name']}.")
            else:
                self.log(f"Failed to modify startup status for {item['name']}.")
                # Revert toggle visually
                def revert():
                    var.set("off" if enable else "on")
                    messagebox.showerror("Error", f"Failed to modify startup program: {item['name']}.\nEnsure you have administrative privileges.")
                self.after(0, revert)

            # Refresh lists
            self.after(0, self.refresh_startup_items)

        threading.Thread(target=worker, daemon=True).start()


    def refresh_process_items(self):
        """Retrieves and populates the high-resource process list."""
        self.log("Gathering active process stats...")
        
        for widget in self.proc_scroll.winfo_children():
            widget.destroy()

        def worker():
            procs = optimizer_core.get_high_resources_processes(limit=15)

            def populate():
                if not procs:
                    lbl = ctk.CTkLabel(self.proc_scroll, text="No processes returned.", font=ctk.CTkFont(size=12, slant="italic"))
                    lbl.pack(pady=20)
                    return

                for idx, p in enumerate(procs):
                    proc_frame = ctk.CTkFrame(self.proc_scroll, fg_color="#2A2A2A", corner_radius=6)
                    proc_frame.pack(fill="x", pady=4, padx=5)

                    lbl_text = f"{p['name'][:18]} (PID: {p['pid']})\nRAM: {p['ram_mb']} MB | CPU: {p['cpu']}%"
                    lbl_info = ctk.CTkLabel(
                        proc_frame,
                        text=lbl_text,
                        font=ctk.CTkFont(size=11),
                        justify="left",
                        anchor="w"
                    )
                    lbl_info.pack(side="left", padx=10, pady=6)

                    # Kill Button
                    btn_kill = ctk.CTkButton(
                        proc_frame,
                        text="Kill",
                        font=ctk.CTkFont(size=11, weight="bold"),
                        fg_color=self.danger_color,
                        hover_color="#DC2626",
                        width=50,
                        height=24,
                        command=lambda pid=p['pid'], name=p['name']: self.kill_selected_process(pid, name)
                    )
                    btn_kill.pack(side="right", padx=10)

            self.after(0, populate)

        threading.Thread(target=worker, daemon=True).start()


    def kill_selected_process(self, pid, name):
        """Terminates selected background process."""
        confirm = messagebox.askyesno("Confirm Task Kill", f"Are you sure you want to end process '{name}' (PID: {pid})?")
        if not confirm:
            return

        self.log(f"Attempting to terminate process: {name} (PID: {pid})...")
        
        def worker():
            success, msg = optimizer_core.kill_process(pid)
            self.log(msg)
            
            def done():
                if success:
                    messagebox.showinfo("Process Ended", f"Ended task: {name}")
                else:
                    messagebox.showerror("Error", f"Failed to terminate process.\nError: {msg}")
                self.refresh_process_items()

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


    # ==========================================
    # TWEAKS LOGIC
    # ==========================================

    def refresh_tweaks_view(self):
        """Refreshes status flags for telemetry and power plans."""
        self.log("Loading telemetry state and active power policies...")
        
        def worker():
            # 1. Get Telemetry status
            status = optimizer_core.get_telemetry_status()
            
            # If any telemetry service/registry is active, switch is "off" (meaning NOT disabled)
            # If all are disabled, switch is "on" (meaning Disabled)
            is_disabled = not (status["diag_track"] or status["dmwap_push"] or status["wer_svc"] or status["telemetry_reg"])
            
            # 2. Get Power plans
            plans, active_guid = optimizer_core.get_power_plans()
            self.power_plans = plans
            self.active_power_guid = active_guid

            dropdown_values = [f"{p['name']} ({p['guid'][:8]}...)" for p in plans]
            
            # Find active plan text
            active_plan_text = "Unknown"
            for p in plans:
                if p["active"]:
                    active_plan_text = f"{p['name']} ({p['guid'][:8]}...)"

            def update_ui():
                self.telemetry_switch_var.set("on" if is_disabled else "off")
                
                if dropdown_values:
                    self.power_dropdown.configure(values=dropdown_values)
                    self.power_dropdown.set(active_plan_text)
                else:
                    self.power_dropdown.configure(values=["Unavailable"])
                    self.power_dropdown.set("Unavailable")

            self.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()


    def toggle_telemetry(self):
        """Disables or restores telemetry services."""
        disable = self.telemetry_switch_var.get() == "on"
        action = "disabling" if disable else "restoring"
        self.log(f"Executing telemetry tweak: {action} Windows diagnostics telemetry...")

        def worker():
            success = optimizer_core.set_telemetry_status(disable)
            if success:
                self.log(f"Telemetry settings successfully updated (Telemetry Disabled: {disable}).")
            else:
                self.log("Warning: Some telemetry configuration failed to apply. Check Windows policies.")
            
            def done():
                if success:
                    msg = "Windows Telemetry services and group policy trackers disabled successfully!" if disable else "Windows Telemetry services restored to standard defaults."
                    messagebox.showinfo("Tweak Applied", msg)
                else:
                    messagebox.showwarning("Tweak Warning", "Tweak applied partially. Some background diagnostics services could not be stopped.")
                self.refresh_tweaks_view()

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


    def change_power_plan(self, selection):
        """Callback when user selects a different power scheme from dropdown."""
        # Find matching guid
        guid = None
        for p in self.power_plans:
            display_val = f"{p['name']} ({p['guid'][:8]}...)"
            if display_val == selection:
                guid = p["guid"]
                break

        if not guid:
            return

        self.log(f"Setting active power plan to GUID: {guid}")
        
        def worker():
            success = optimizer_core.set_power_plan(guid)
            if success:
                self.log("Power scheme updated successfully.")
            else:
                self.log("Error changing power scheme.")
                
            def done():
                if not success:
                    messagebox.showerror("Error", "Could not set power scheme. Run as Administrator.")
                self.refresh_tweaks_view()
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


    def activate_ultimate_power(self):
        """Unlocks and sets the Windows Ultimate Performance plan."""
        self.log("Attempting to unlock Ultimate Performance power scheme...")
        
        def worker():
            success, msg = optimizer_core.enable_ultimate_performance()
            self.log(msg)
            
            def done():
                if success:
                    messagebox.showinfo("Success", "Ultimate Performance Power Plan activated successfully!")
                else:
                    messagebox.showerror("Error", f"Failed to activate power scheme: {msg}")
                self.refresh_tweaks_view()
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


    def trigger_dns_flush(self):
        """Flushes DNS cache."""
        self.log("Flushing DNS Resolver Cache...")
        
        def worker():
            success, msg = optimizer_core.flush_dns()
            self.log(msg)
            
            def done():
                if success:
                    messagebox.showinfo("DNS Flushed", "DNS Resolver cache flushed successfully!")
                else:
                    messagebox.showerror("Error", f"Failed to flush DNS cache: {msg}")
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


    def trigger_mem_flush(self):
        """Clears Standby list & empty working sets."""
        self.log("Flushing memory caches and working sets...")
        
        def worker():
            results = optimizer_core.optimize_memory()
            
            # Log outcomes
            if results.get("working_sets_success"):
                self.log(f"Cleaned working sets for {results['processes_flushed']} active processes.")
            else:
                self.log(f"Working set cleaning failure: {results.get('working_sets_error')}")

            if results.get("standby_cleared"):
                self.log("Windows RAM Standby memory list purged successfully.")
            else:
                self.log(f"Failed to purge Standby List: {results.get('standby_error', 'Access Denied')}")

            def done():
                success_msg = f"Memory Optimizations Complete!\n\n• Flushed process working sets ({results['processes_flushed']} applications)\n"
                if results.get("standby_cleared"):
                    success_msg += "• Purged Standby List system cache."
                else:
                    success_msg += "• Purged Standby List system cache (Failed - Requires SeProfileSingleProcessPrivilege)."

                messagebox.showinfo("Memory Flushed", success_msg)
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


    # Close Window Event handler
    def destroy(self):
        self.monitoring_active = False
        super().destroy()


if __name__ == "__main__":
    app = ApexOptimizerApp()
    app.mainloop()
