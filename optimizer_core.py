import os
import sys
import shutil
import subprocess
import ctypes
from ctypes import wintypes
import winreg
import psutil

# Windows Constants
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x0002
SystemMemoryListInformation = 0x50
MemoryPurgeStandbyList = 4

# Structure for adjusting token privileges
class LUID(ctypes.Structure):
    _fields_ = [("LowPart", ctypes.c_ulong), ("HighPart", ctypes.c_long)]

class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attributes", ctypes.c_ulong)]

class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", ctypes.c_ulong), ("Privileges", LUID_AND_ATTRIBUTES * 1)]


def is_admin():
    """Checks if the script is running with administrative privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def run_as_admin():
    """Restarts the application requesting Administrator rights."""
    if not is_admin():
        # Re-run the script with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)


def create_restore_point(description="Apex PC Optimizer Restore Point"):
    """
    Creates a Windows System Restore Point using PowerShell.
    Returns (success: bool, message: str)
    """
    # Check if System Restore is enabled or check frequency limit
    cmd = f"PowerShell.exe -ExecutionPolicy Bypass -Command \"Checkpoint-Computer -Description '{description}' -RestorePointType 'MODIFY_SETTINGS'\""
    try:
        # Checkpoint-Computer might fail if Restore Points are disabled or too frequent
        # We run it synchronously
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            return True, "System Restore Point created successfully."
        else:
            err = result.stderr.strip() if result.stderr else result.stdout.strip()
            # Often fails if disabled
            return False, f"Failed to create restore point: {err or 'Unknown error'}"
    except Exception as e:
        return False, f"Error launching restore point creation: {str(e)}"


# ==========================================
# SYSTEM JUNK CLEANER
# ==========================================

def get_junk_categories():
    """Returns a dict of junk categories, their descriptions, and directories to clean."""
    user_profile = os.environ.get("USERPROFILE", "")
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    appdata = os.environ.get("APPDATA", "")
    windir = os.environ.get("WINDIR", "C:\\Windows")

    categories = {
        "User Temp": {
            "description": "Temporary files created by user applications",
            "paths": [os.environ.get("TEMP", "")]
        },
        "System Temp": {
            "description": "Temporary files created by Windows system services",
            "paths": [os.path.join(windir, "Temp")]
        },
        "Prefetch": {
            "description": "Windows application launch cache files",
            "paths": [os.path.join(windir, "Prefetch")]
        },
        "Log Files": {
            "description": "System and setup log files",
            "paths": [
                os.path.join(windir, "Logs"),
                os.path.join(windir, "Panther"),
                os.path.join(windir, "inf")
            ],
            "extensions": [".log", ".txt", ".bak", ".tmp"]
        },
        "Browser Caches": {
            "description": "Cache files for Chrome, Edge, and Firefox",
            "paths": [
                # Chrome
                os.path.join(local_appdata, "Google\\Chrome\\User Data\\Default\\Cache"),
                os.path.join(local_appdata, "Google\\Chrome\\User Data\\Default\\Code Cache"),
                os.path.join(local_appdata, "Google\\Chrome\\User Data\\Default\\GPUCache"),
                # Edge
                os.path.join(local_appdata, "Microsoft\\Edge\\User Data\\Default\\Cache"),
                os.path.join(local_appdata, "Microsoft\\Edge\\User Data\\Default\\Code Cache"),
                os.path.join(local_appdata, "Microsoft\\Edge\\User Data\\Default\\GPUCache"),
                # Firefox (Requires finding profile folders)
                os.path.join(local_appdata, "Mozilla\\Firefox\\Profiles")
            ]
        }
    }
    return categories


def scan_junk(selected_categories):
    """
    Scans selected categories for files that can be cleaned.
    Returns (files_list, total_size_bytes)
    """
    categories = get_junk_categories()
    files_to_clean = []
    total_size = 0

    for cat_name in selected_categories:
        if cat_name not in categories:
            continue

        cat_info = categories[cat_name]
        paths = cat_info["paths"]
        extensions = cat_info.get("extensions", None)

        for base_path in paths:
            if not base_path or not os.path.exists(base_path):
                continue

            # Special case for Firefox Profiles (which are dynamic)
            if cat_name == "Browser Caches" and "Mozilla\\Firefox" in base_path:
                try:
                    for profile in os.listdir(base_path):
                        profile_path = os.path.join(base_path, profile)
                        if os.path.isdir(profile_path):
                            # Clean cache2 inside profile
                            cache2 = os.path.join(profile_path, "cache2")
                            if os.path.exists(cache2):
                                for root, _, files in os.walk(cache2):
                                    for file in files:
                                        fp = os.path.join(root, file)
                                        try:
                                            sz = os.path.getsize(fp)
                                            files_to_clean.append({
                                                "path": fp,
                                                "size": sz,
                                                "category": cat_name
                                            })
                                            total_size += sz
                                        except OSError:
                                            pass
                except Exception:
                    pass
                continue

            # General directory walk
            for root, _, files in os.walk(base_path):
                for file in files:
                    fp = os.path.join(root, file)
                    if extensions:
                        _, ext = os.path.splitext(file)
                        if ext.lower() not in extensions:
                            continue
                    try:
                        sz = os.path.getsize(fp)
                        files_to_clean.append({
                            "path": fp,
                            "size": sz,
                            "category": cat_name
                        })
                        total_size += sz
                    except OSError:
                        pass
    return files_to_clean, total_size


def clean_junk(files_list, progress_callback=None):
    """
    Deletes the files listed in files_list.
    Returns (freed_bytes, error_count, details)
    """
    freed_bytes = 0
    error_count = 0
    details = []

    total_files = len(files_list)
    for i, file_info in enumerate(files_list):
        fp = file_info["path"]
        sz = file_info["size"]
        cat = file_info["category"]

        if progress_callback:
            progress_callback(i + 1, total_files, fp)

        try:
            os.remove(fp)
            freed_bytes += sz
        except (PermissionError, FileNotFoundError, OSError) as e:
            # Locked files or system restrictions
            error_count += 1
            details.append(f"Skipped (Locked/Access Denied): {fp}")
            
    # Try cleaning empty folders in the Temp directories as well
    # (Optional, doesn't add to freed bytes size but keeps it clean)
    categories = get_junk_categories()
    for cat_name in ["User Temp", "System Temp"]:
        for base_path in categories[cat_name]["paths"]:
            if base_path and os.path.exists(base_path):
                for root, dirs, _ in os.walk(base_path, topdown=False):
                    for d in dirs:
                        dp = os.path.join(root, d)
                        try:
                            os.rmdir(dp)
                        except OSError:
                            pass # Folder not empty or locked

    return freed_bytes, error_count, details


# ==========================================
# MEMORY & NETWORK FLUSH
# ==========================================

def enable_privilege(privilege_name):
    """Enables a specific privilege in the current process token."""
    hToken = wintypes.HANDLE()
    advapi32 = ctypes.windll.advapi32
    kernel32 = ctypes.windll.kernel32

    if not advapi32.OpenProcessToken(
        kernel32.GetCurrentProcess(),
        TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
        ctypes.byref(hToken)
    ):
        return False

    luid = LUID()
    if not advapi32.LookupPrivilegeValueW(None, privilege_name, ctypes.byref(luid)):
        kernel32.CloseHandle(hToken)
        return False

    tp = TOKEN_PRIVILEGES()
    tp.PrivilegeCount = 1
    tp.Privileges[0].Luid = luid
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED

    res = advapi32.AdjustTokenPrivileges(
        hToken, False, ctypes.byref(tp), ctypes.sizeof(tp), None, None
    )
    kernel32.CloseHandle(hToken)

    # AdjustTokenPrivileges can return True even if it failed to adjust (check GetLastError)
    if not res or kernel32.GetLastError() != 0:
        return False
    return True


def flush_dns():
    """Flushes DNS cache. Returns (success: bool, output: str)"""
    try:
        res = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True, shell=True)
        if res.returncode == 0:
            return True, "DNS Resolver Cache flushed successfully."
        else:
            return False, res.stdout or res.stderr
    except Exception as e:
        return False, str(e)


def empty_working_sets():
    """Empties the working sets of all active user processes. Returns count of freed processes."""
    psapi = ctypes.windll.psapi
    kernel32 = ctypes.windll.kernel32

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_SET_QUOTA = 0x0100

    freed_count = 0
    my_pid = os.getpid()

    for proc in psutil.process_iter(['pid', 'name']):
        try:
            pid = proc.info['pid']
            if pid == 0 or pid == 4 or pid == my_pid:
                continue # Skip System Idle, System, and current app
            
            hProcess = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, pid)
            if hProcess:
                success = psapi.EmptyWorkingSet(hProcess)
                kernel32.CloseHandle(hProcess)
                if success:
                    freed_count += 1
        except Exception:
            pass
    return freed_count


def clear_standby_list():
    """Purges the Windows standby memory list. Returns success status."""
    if not enable_privilege("SeProfileSingleProcessPrivilege"):
        # Try enabling increase quota just in case
        enable_privilege("SeIncreaseQuotaPrivilege")

    ntdll = ctypes.windll.ntdll
    # SystemMemoryListInformation = 80 (0x50), Purge command = 4
    result = ntdll.NtSetSystemInformation(
        SystemMemoryListInformation,
        ctypes.byref(ctypes.c_ulong(MemoryPurgeStandbyList)),
        ctypes.sizeof(ctypes.c_ulong)
    )
    return result == 0


def optimize_memory():
    """
    Combined Memory Flush: Empties process working sets + clears Standby list.
    Returns details dict.
    """
    results = {}
    
    # 1. Empty Working Sets
    try:
        proc_cleared = empty_working_sets()
        results["processes_flushed"] = proc_cleared
        results["working_sets_success"] = True
    except Exception as e:
        results["processes_flushed"] = 0
        results["working_sets_success"] = False
        results["working_sets_error"] = str(e)

    # 2. Clear Standby List
    try:
        standby_cleared = clear_standby_list()
        results["standby_cleared"] = standby_cleared
    except Exception as e:
        results["standby_cleared"] = False
        results["standby_error"] = str(e)

    return results


# ==========================================
# STARTUP & BACKGROUND PROCESS MANAGER
# ==========================================

# Directory to backup disabled startup shortcuts
DISABLED_STARTUP_DIR = os.path.expandvars(r"%LOCALAPPDATA%\ApexPC\DisabledStartup")
# Registry key for backups of disabled registry items
REG_BACKUP_PATH = r"Software\ApexPC\DisabledStartup"

def get_startup_items():
    """
    Gathers startup items from Registry (HKCU/HKLM Run keys) and Startup folders.
    Returns list of dicts: {'name': str, 'command': str, 'source': str, 'enabled': bool, 'type': 'registry'|'folder'}
    """
    items = []
    
    # 1. Registry items
    reg_keys = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU Run Key"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM Run Key")
    ]

    for root, subkey, label in reg_keys:
        try:
            with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        name, val, _ = winreg.EnumValue(key, i)
                        items.append({
                            "name": name,
                            "command": val,
                            "source": label,
                            "enabled": True,
                            "type": "registry",
                            "root_key": "HKCU" if root == winreg.HKEY_CURRENT_USER else "HKLM",
                            "key_path": subkey
                        })
                        i += 1
                    except OSError:
                        break
        except Exception:
            pass

    # Read our disabled registry items to display them in disabled status
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_BACKUP_PATH, 0, winreg.KEY_READ) as key:
            i = 0
            while True:
                try:
                    name, val, _ = winreg.EnumValue(key, i)
                    # Value content contains: "ROOT_KEY|KEY_PATH|COMMAND"
                    parts = val.split("|", 2)
                    if len(parts) == 3:
                        root_label, key_path, cmd = parts
                        items.append({
                            "name": name,
                            "command": cmd,
                            "source": f"{root_label} Run Key (Disabled)",
                            "enabled": False,
                            "type": "registry",
                            "root_key": root_label,
                            "key_path": key_path
                        })
                    i += 1
                except OSError:
                    break
    except Exception:
        pass

    # 2. Startup Folder items
    startup_folders = [
        # User Startup
        (os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"), "User Startup Folder"),
        # Common Startup
        (os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Startup"), "Common Startup Folder")
    ]

    for folder, label in startup_folders:
        if os.path.exists(folder):
            for file in os.listdir(folder):
                if file.lower().endswith(".lnk") or file.lower().endswith(".exe") or file.lower().endswith(".bat"):
                    fp = os.path.join(folder, file)
                    items.append({
                        "name": file,
                        "command": fp,
                        "source": label,
                        "enabled": True,
                        "type": "folder",
                        "folder_path": folder
                    })

    # Read disabled folder items
    if os.path.exists(DISABLED_STARTUP_DIR):
        for file in os.listdir(DISABLED_STARTUP_DIR):
            fp = os.path.join(DISABLED_STARTUP_DIR, file)
            # The file name starts with USER_ or COMMON_ to know where to restore it
            if file.startswith("USER_") or file.startswith("COMMON_"):
                display_name = file.split("_", 1)[1]
                source_label = "User Startup Folder (Disabled)" if file.startswith("USER_") else "Common Startup Folder (Disabled)"
                items.append({
                    "name": display_name,
                    "command": fp,
                    "source": source_label,
                    "enabled": False,
                    "type": "folder",
                    "backup_name": file
                })

    return items


def toggle_startup_item(item, enable):
    """
    Enables or disables a startup item.
    Returns success status.
    """
    if item["type"] == "registry":
        root = winreg.HKEY_CURRENT_USER if item["root_key"] == "HKCU" else winreg.HKEY_LOCAL_MACHINE
        key_path = item["key_path"]
        name = item["name"]
        cmd = item["command"]

        if not enable:
            # Disable: Move to our backup key, delete from original
            try:
                # Create backup key
                with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, REG_BACKUP_PATH, 0, winreg.KEY_SET_VALUE) as backup_key:
                    # Write metadata
                    backup_value = f"{item['root_key']}|{key_path}|{cmd}"
                    winreg.SetValueEx(backup_key, name, 0, winreg.REG_SZ, backup_value)

                # Delete from original
                with winreg.OpenKey(root, key_path, 0, winreg.KEY_SET_VALUE) as orig_key:
                    winreg.DeleteValue(orig_key, name)
                return True
            except Exception as e:
                print(f"Error disabling registry startup item: {e}")
                return False
        else:
            # Enable: Restore to original, delete from backup
            try:
                with winreg.OpenKey(root, key_path, 0, winreg.KEY_SET_VALUE) as orig_key:
                    winreg.SetValueEx(orig_key, name, 0, winreg.REG_SZ, cmd)
                
                # Delete from backup
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_BACKUP_PATH, 0, winreg.KEY_SET_VALUE) as backup_key:
                    winreg.DeleteValue(backup_key, name)
                return True
            except Exception as e:
                print(f"Error enabling registry startup item: {e}")
                return False

    elif item["type"] == "folder":
        if not enable:
            # Disable: Move file to our disabled startup folder
            try:
                if not os.path.exists(DISABLED_STARTUP_DIR):
                    os.makedirs(DISABLED_STARTUP_DIR)
                
                src = item["command"]
                filename = item["name"]
                
                prefix = "USER_" if "User" in item["source"] else "COMMON_"
                dst_name = prefix + filename
                dst = os.path.join(DISABLED_STARTUP_DIR, dst_name)
                
                shutil.move(src, dst)
                return True
            except Exception as e:
                print(f"Error disabling folder startup item: {e}")
                return False
        else:
            # Enable: Move file back to original startup folder
            try:
                src = item["command"] # points to the file in DISABLED_STARTUP_DIR
                filename = item["name"]
                
                is_user = "User" in item["source"]
                orig_folder = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup") if is_user else os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
                
                dst = os.path.join(orig_folder, filename)
                shutil.move(src, dst)
                return True
            except Exception as e:
                print(f"Error enabling folder startup item: {e}")
                return False

    return False


def get_high_resources_processes(limit=15):
    """
    Gets list of high RAM/CPU processes running.
    Returns list of dicts: {'pid': int, 'name': str, 'cpu': float, 'ram_mb': float, 'user': str}
    """
    processes = []
    # Collect CPU and RAM info
    # We call cpu_percent once to initialize, wait a brief moment, then collect.
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'username']):
        try:
            pinfo = proc.info
            # Convert memory to MB
            ram_mb = pinfo['memory_info'].rss / (1024 * 1024) if pinfo['memory_info'] else 0.0
            processes.append({
                "pid": pinfo["pid"],
                "name": pinfo["name"] or "Unknown",
                "cpu": pinfo["cpu_percent"] or 0.0,
                "ram_mb": round(ram_mb, 1),
                "user": pinfo["username"] or "System"
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            pass
            
    # Sort by memory usage first, then CPU
    processes.sort(key=lambda x: x["ram_mb"], reverse=True)
    return processes[:limit]


def kill_process(pid):
    """Terminates a process by its PID. Returns success status."""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=2)
        return True, "Process terminated successfully."
    except psutil.NoSuchProcess:
        return False, "Process does not exist."
    except psutil.AccessDenied:
        # Fall back to taskkill for forced administrative kill
        try:
            res = subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, text=True, shell=True)
            if res.returncode == 0:
                return True, "Process force-terminated successfully."
            else:
                return False, res.stdout or res.stderr
        except Exception as e:
            return False, f"Access Denied. Taskkill failed: {str(e)}"
    except Exception as e:
        return False, str(e)


# ==========================================
# PERFORMANCE TWEAKS
# ==========================================

def get_telemetry_status():
    """
    Checks if telemetry and tracking services/registries are active.
    Returns dict: {'diag_track': bool, 'dmwap_push': bool, 'wer_svc': bool, 'telemetry_reg': bool}
    (True means Enabled/Running, False means Disabled/Stopped)
    """
    status = {}

    # 1. Check services
    services = {
        "diag_track": "DiagTrack",
        "dmwap_push": "dmwappushservice",
        "wer_svc": "WerSvc"
    }

    for key, svc_name in services.items():
        try:
            svc = psutil.win_service_get(svc_name)
            # Service status: 'running', 'stopped', 'paused', etc.
            # Start type: 'automatic', 'manual', 'disabled'
            svc_info = svc.as_dict()
            status[key] = (svc_info["status"] == "running") or (svc_info["start_type"] != "disabled")
        except Exception:
            status[key] = False # Service not found or access denied (assumed disabled)

    # 2. Check Telemetry policies registry key
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, "AllowTelemetry")
            status["telemetry_reg"] = (val != 0)
    except Exception:
        # If key doesn't exist, by default telemetry is enabled in Windows
        status["telemetry_reg"] = True

    return status


def set_telemetry_status(disable):
    """
    Disables or restores Windows telemetry.
    If disable is True, disables everything. If False, restores defaults.
    """
    success = True
    start_type = "disabled" if disable else "demand" # manual
    state_cmd = "stop" if disable else "start"
    
    # 1. Services
    services = ["DiagTrack", "dmwappushservice", "WerSvc"]
    for svc_name in services:
        try:
            # Set Startup type
            # start= disabled / demand / auto
            subprocess.run(f"sc config \"{svc_name}\" start={start_type}", shell=True, capture_output=True)
            # Stop or start service
            subprocess.run(f"net {state_cmd} \"{svc_name}\"", shell=True, capture_output=True)
        except Exception:
            success = False

    # 2. Registry Policies
    reg_paths = [
        r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection"
    ]
    
    for path in reg_paths:
        try:
            if disable:
                with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, "AllowTelemetry", 0, winreg.REG_DWORD, 0)
            else:
                # Restore
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE) as key:
                        winreg.DeleteValue(key, "AllowTelemetry")
                except FileNotFoundError:
                    pass
        except Exception:
            success = False

    # Disable Cortana (Additional Tweak)
    cortana_path = r"SOFTWARE\Policies\Microsoft\Windows\Windows Search"
    try:
        if disable:
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, cortana_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "AllowCortana", 0, winreg.REG_DWORD, 0)
        else:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cortana_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, "AllowCortana")
            except FileNotFoundError:
                pass
    except Exception:
        success = False

    return success


def get_power_plans():
    """
    Queries available power schemes.
    Returns (list_of_plans, active_guid)
    """
    plans = []
    active_guid = None
    try:
        # Run powercfg /list
        res = subprocess.run(["powercfg", "/list"], capture_output=True, text=True, shell=True)
        lines = res.stdout.splitlines()
        for line in lines:
            if "GUID" in line:
                # Example line: "Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced) *"
                parts = line.split("GUID:")
                if len(parts) > 1:
                    guid_part = parts[1].strip()
                    guid = guid_part.split(" ")[0].strip()
                    name_part = guid_part.split("(")[1] if "(" in guid_part else "Unknown"
                    name = name_part.split(")")[0].strip()
                    is_active = "*" in line
                    
                    plans.append({
                        "guid": guid,
                        "name": name,
                        "active": is_active
                    })
                    if is_active:
                        active_guid = guid
    except Exception as e:
        print(f"Error listing power plans: {e}")
        
    return plans, active_guid


def set_power_plan(guid):
    """Sets the active power scheme by GUID."""
    try:
        res = subprocess.run(f"powercfg /setactive {guid}", capture_output=True, text=True, shell=True)
        return res.returncode == 0
    except Exception:
        return False


def enable_ultimate_performance():
    """
    Creates/duplicates the Ultimate Performance power scheme if not present, and sets it active.
    Ultimate Performance scheme GUID: e9a42b02-d5df-448d-aa00-03f14749eb61
    """
    # 1. Try to activate it first
    guid = "e9a42b02-d5df-448d-aa00-03f14749eb61"
    if set_power_plan(guid):
        return True, "Ultimate Performance power scheme activated."

    # 2. If it fails, duplicate/create it
    try:
        res = subprocess.run(f"powercfg /duplicatescheme {guid}", capture_output=True, text=True, shell=True)
        if res.returncode == 0:
            # Try activating again
            if set_power_plan(guid):
                return True, "Ultimate Performance scheme created and activated."
        
        # If duplicating fails, fallback to High Performance GUID
        high_perf_guid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
        if set_power_plan(high_perf_guid):
            return True, "Ultimate Performance unavailable. Balanced/High Performance plan activated."
        
        return False, "Failed to create or activate Ultimate Performance scheme."
    except Exception as e:
        return False, str(e)
