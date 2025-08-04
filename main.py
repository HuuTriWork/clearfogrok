import os
import sys
import time
import random
import subprocess
import requests
from urllib.parse import urlparse
try:
    from colorama import init, Fore, Back, Style
    import cv2
    import numpy as np
except ImportError:
    import pip
    packages = ['colorama', 'opencv-python', 'numpy', 'requests']
    for package in packages:
        pip.main(['install', package])
    from colorama import init, Fore, Back, Style
    import cv2
    import numpy as np
    import requests

init()

GITHUB_REPO = "https://github.com/HuuTriWork/clearfogrok"
MAIN_SCRIPT_URL = "https://raw.githubusercontent.com/HuuTriWork/clearfogrok/refs/heads/main/main.py"
VERSION_FILE_URL = "https://raw.githubusercontent.com/HuuTriWork/clearfogrok/refs/heads/main/version.txt"
CURRENT_VERSION = "1.2"

class MEmuController:
    def __init__(self):
        self.adb_path = "adb.exe"
        self.all_devices = []
        self.connected_devices = []
        self.screenshot_dir = "screenshots"
        self.template_dir = "templates"
        self.anti_ban_enabled = True
        self.max_repeats = 0
        self.rest_interval = 0
        self.rest_duration = 0
        self.current_run_count = 0
        self.running = True
        os.makedirs(self.screenshot_dir, exist_ok=True)
        os.makedirs(self.template_dir, exist_ok=True)

    def _run_adb(self, *args):
        try:
            result = subprocess.run([self.adb_path] + list(args),
                                  capture_output=True,
                                  text=True,
                                  timeout=5)
            return result.stdout.strip() if result.returncode == 0 else None
        except:
            return None

    def _animate_loading(self, message):
        for i in range(3):
            for char in "⣾⣽⣻⢿⡿⣟⣯⣷":
                sys.stdout.write(f"\r{Fore.YELLOW}{char} {message}{' '*(10-len(message))}{Style.RESET_ALL}")
                sys.stdout.flush()
                time.sleep(0.1)
        print("\r" + " "*50 + "\r", end="")

    def _take_screenshot(self, device, filename):
        try:
            screenshot_path = os.path.join(self.screenshot_dir, filename)
            result = self._run_adb("-s", device, "shell", "screencap", "-p", "/sdcard/screen.png")
            if result is None:
                return False
            
            self._run_adb("-s", device, "pull", "/sdcard/screen.png", screenshot_path)
            self._run_adb("-s", device, "shell", "rm", "/sdcard/screen.png")
            
            try:
                img = cv2.imread(screenshot_path)
                if img is None or img.size == 0:
                    raise ValueError("Empty image")
                return True
            except:
                screenshot_path = os.path.join(self.screenshot_dir, f"alt_{filename}")
                result = self._run_adb("-s", device, "exec-out", "screencap", "-p", ">", screenshot_path)
                if result is None:
                    return False
                return True
        except:
            return False

    def _find_image(self, device, template_filename, threshold=0.8):
        screenshot_path = os.path.join(self.screenshot_dir, "current_screen.png")
        if not self._take_screenshot(device, "current_screen.png"):
            return None
            
        template_path = os.path.join(self.template_dir, template_filename)
        if not os.path.exists(template_path):
            return None
            
        try:
            img = cv2.imread(screenshot_path)
            template = cv2.imread(template_path)
            
            if img is None or template is None:
                return None
                
            result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                h, w = template.shape[:-1]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                return (center_x, center_y)
            return None
        except:
            return None

    def _click_position(self, device, position):
        if position is None:
            return False
        x, y = position
        
        if self.anti_ban_enabled:
            x += random.randint(-10, 10)
            y += random.randint(-10, 10)
            time.sleep(random.uniform(0.1, 0.5))
            
        result = self._run_adb("-s", device, "shell", "input", "tap", str(x), str(y))
        
        if self.anti_ban_enabled:
            time.sleep(random.uniform(0.2, 0.6))
            
        return result is not None

    def _wait_for_image(self, device, template_filename, timeout=30, interval=1):
        start_time = time.time()
        while time.time() - start_time < timeout and self.running:
            position = self._find_image(device, template_filename)
            if position is not None:
                return position
                
            actual_interval = interval
            if self.anti_ban_enabled:
                actual_interval = random.uniform(interval*0.7, interval*1.5)
            time.sleep(actual_interval)
        return None

    def _show_status(self, device, message):
        emoji = "⚡" if "start" in message.lower() else \
                "✅" if "success" in message.lower() else \
                "❌" if "fail" in message.lower() else \
                "🔍" if "look" in message.lower() else \
                "🔄" if "process" in message.lower() else "⚙️"
        print(f"\n{Fore.BLUE}{emoji} {device[:5]}...: {Fore.WHITE}{message}{Style.RESET_ALL}")

    def clear_fog(self):
        if not self.connected_devices:
            print(f"\n{Fore.RED}⚠️ No devices!{Style.RESET_ALL}")
            return False
        
        self.current_run_count += 1
        self.running = True

        if self.rest_interval > 0 and self.current_run_count % self.rest_interval == 0:
            print(f"\n{Fore.YELLOW}💤 Rest {self.rest_duration}s...{Style.RESET_ALL}")
            time.sleep(self.rest_duration)
        
        for device in self.connected_devices:
            if not self.running:
                self._show_status(device, "Stopped by user")
                break
                
            self._show_status(device, "Start fog clear")
            
            home_pos = self._find_image(device, "home.png")
            map_pos = self._find_image(device, "map.png")
            
            if home_pos:
                self._show_status(device, "Home found")
                self._click_position(device, home_pos)
            elif map_pos:
                self._show_status(device, "Map found")
                self._click_position(device, map_pos)
                time.sleep(2)
                home_pos = self._find_image(device, "home.png")
                if home_pos:
                    self._show_status(device, "Home after map")
                    self._click_position(device, home_pos)
            else:
                self._show_status(device, "No home/map")
                continue
                
            time.sleep(2)
            
            found = False
            for i in range(1, 5):
                if not self.running: break
                option_pos = self._find_image(device, f"{i}.png")
                if option_pos:
                    self._show_status(device, f"Option {i}")
                    self._click_position(device, option_pos)
                    found = True
                    break
                    
            if not found:
                self._show_status(device, "No options")
                continue
                
            time.sleep(2)
            
            scout_pos = self._find_image(device, "scout.png")
            if scout_pos:
                self._show_status(device, "Scout found")
                self._click_position(device, scout_pos)
            else:
                self._show_status(device, "No scout")
                
            explore_pos = self._wait_for_image(device, "explore.png")
            if explore_pos:
                self._show_status(device, "Explore")
                self._click_position(device, explore_pos)
                time.sleep(5)
                
                notselected_pos = self._find_image(device, "notselected.png")
                selected_pos = self._find_image(device, "selected.png")
                
                if notselected_pos:
                    self._show_status(device, "Selecting")
                    self._click_position(device, notselected_pos)
                elif selected_pos:
                    self._show_status(device, "Already set")
                else:
                    self._show_status(device, "No selection")
                
                explore_pos = self._find_image(device, "explore.png")
                if explore_pos:
                    self._show_status(device, "Explore again")
                    self._click_position(device, explore_pos)
                    
                    send_pos = self._wait_for_image(device, "send.png")
                    if send_pos:
                        self._show_status(device, "Sending")
                        self._click_position(device, send_pos)
                        
                        home_pos = self._wait_for_image(device, "home.png")
                        if home_pos:
                            self._show_status(device, "Return home")
                            self._click_position(device, home_pos)
                        else:
                            self._show_status(device, "No home after send")
                    else:
                        self._show_status(device, "No send button")
                else:
                    self._show_status(device, "No explore after select")
            else:
                self._show_status(device, "No explore")
                
            self._show_status(device, "Complete")
        
        return True

    def scan_devices(self):
        self._animate_loading("Scanning")
        output = self._run_adb("devices")
        if output:
            self.all_devices = [line.split('\t')[0] 
                             for line in output.splitlines()[1:] 
                             if 'device' in line]
        return self.all_devices

    def connect_devices(self, selection):
        if not self.all_devices:
            self.scan_devices()
            if not self.all_devices:
                return False

        if selection.lower() == 'all':
            self.connected_devices = self.all_devices.copy()
            return True

        try:
            indexes = {int(x)-1 for x in selection.replace('+', ' ').split() if x.isdigit()}
            self.connected_devices = [self.all_devices[i] for i in indexes if 0 <= i < len(self.all_devices)]
            return bool(self.connected_devices)
        except:
            return False

    def disconnect_devices(self, selection):
        if not self.connected_devices:
            return False

        if selection.lower() == 'all':
            self.connected_devices = []
            return True

        try:
            indexes = {int(x)-1 for x in selection.replace('+', ' ').split() if x.isdigit()}
            self.connected_devices = [d for i, d in enumerate(self.connected_devices) if i not in indexes]
            return True
        except:
            return False

    def show_devices(self):
        if not self.all_devices:
            self.scan_devices()
        
        print(f"\n{Fore.GREEN}📋 Devices:{Style.RESET_ALL}")
        for i, dev in enumerate(self.all_devices, 1):
            status = f"{Fore.GREEN}✓{Style.RESET_ALL}" if dev in self.connected_devices else f"{Fore.RED}✗{Style.RESET_ALL}"
            print(f"  {i}. {dev[:12]}... - {status}")

    def open_game(self, package_name="com.rok.gp.vn"):
        if not self.connected_devices:
            print(f"\n{Fore.RED}⚠️ No devices!{Style.RESET_ALL}")
            return False
        
        success = True
        for device in self.connected_devices:
            output = self._run_adb("-s", device, "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1")
            if output is None:
                print(f"\n{Fore.RED}❌ Failed {device[:5]}...{Style.RESET_ALL}")
                success = False
            else:
                print(f"\n{Fore.GREEN}✅ Opened {device[:5]}...{Style.RESET_ALL}")
        return success

    def close_game(self, package_name="com.rok.gp.vn"):
        if not self.connected_devices:
            print(f"\n{Fore.RED}⚠️ No devices!{Style.RESET_ALL}")
            return False
        
        success = True
        for device in self.connected_devices:
            output = self._run_adb("-s", device, "shell", "am", "force-stop", package_name)
            if output is None:
                print(f"\n{Fore.RED}❌ Failed {device[:5]}...{Style.RESET_ALL}")
                success = False
            else:
                print(f"\n{Fore.GREEN}✅ Closed {device[:5]}...{Style.RESET_ALL}")
        return success

    def set_anti_ban(self, enabled):
        self.anti_ban_enabled = enabled
        print(f"\n{Fore.GREEN}✅ Anti-ban {'ON' if enabled else 'OFF'}{Style.RESET_ALL}")

def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"""{Fore.BLUE}
    ███╗   ███╗███████╗███╗   ███╗██╗   ██╗
    ████╗ ████║██╔════╝████╗ ████║██║   ██║
    ██╔████╔██║█████╗  ██╔████╔██║██║   ██║
    ██║╚██╔╝██║██╔══╝  ██║╚██╔╝██║██║   ██║
    ██║ ╚═╝ ██║███████╗██║ ╚═╝ ██║╚██████╔╝
    ╚═╝     ╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝ 
    {Style.RESET_ALL}""")
    print(f"{Fore.YELLOW}⋆｡ﾟ✶°  MEmu Controller  °✶ﾟ｡⋆{Style.RESET_ALL}\n")

def check_for_updates():
    try:
        script_path = os.path.abspath(__file__)
        
        response = requests.get(VERSION_FILE_URL, timeout=5)
        if response.status_code != 200:
            return False, "Failed to fetch version info"
            
        latest_version = response.text.strip()
        
        if latest_version == CURRENT_VERSION:
            return False, f"Already up-to-date (v{CURRENT_VERSION})"
            
        response = requests.get(MAIN_SCRIPT_URL, timeout=10)
        if response.status_code != 200:
            return False, "Failed to fetch update"
            
        latest_script = response.text
        
        return True, {
            'current_version': CURRENT_VERSION,
            'latest_version': latest_version,
            'latest_script': latest_script,
            'script_path': script_path
        }
        
    except Exception as e:
        return False, f"Update check failed: {str(e)}"

def perform_update(update_info):
    try:
        backup_path = update_info['script_path'] + ".bak"
        if os.path.exists(backup_path):
            os.remove(backup_path)
        os.rename(update_info['script_path'], backup_path)
        
        with open(update_info['script_path'], 'w', encoding='utf-8') as f:
            f.write(update_info['latest_script'])
            
        return True, f"Updated to v{update_info['latest_version']}. Please restart the script."
    except Exception as e:
        if os.path.exists(backup_path):
            os.rename(backup_path, update_info['script_path'])
        return False, f"Update failed: {str(e)}"

def ask_for_update():
    print(f"\n{Fore.YELLOW}🔍 Checking for updates...{Style.RESET_ALL}")
    update_available, update_info = check_for_updates()
    
    if isinstance(update_info, str):
        print(f"{Fore.BLUE}ℹ️ {update_info}{Style.RESET_ALL}")
        return False
        
    if update_available:
        print(f"\n{Fore.GREEN}🎉 Update available!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Current version: {Fore.YELLOW}v{update_info['current_version']}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Latest version: {Fore.GREEN}v{update_info['latest_version']}{Style.RESET_ALL}")
        
        choice = input(f"\n{Fore.YELLOW}👉 Do you want to update now? (y/n): {Style.RESET_ALL}").strip().lower()
        if choice == 'y':
            success, message = perform_update(update_info)
            if success:
                print(f"\n{Fore.GREEN}✅ {message}{Style.RESET_ALL}")
                input(f"\n{Fore.YELLOW}↵ Press Enter to exit...{Style.RESET_ALL}")
                sys.exit(0)
            else:
                print(f"\n{Fore.RED}❌ {message}{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.BLUE}ℹ️ Update skipped. Continuing with current version.{Style.RESET_ALL}")
    else:
        print(f"{Fore.BLUE}ℹ️ {update_info}{Style.RESET_ALL}")

def main():
    ask_for_update()
    
    controller = MEmuController()
    
    while True:
        print_banner()
        print(f"{Fore.CYAN}1. {Fore.WHITE}📋 Devices")
        print(f"{Fore.CYAN}2. {Fore.WHITE}🔌 Connect")
        print(f"{Fore.CYAN}3. {Fore.WHITE}❌ Disconnect")
        print(f"{Fore.CYAN}4. {Fore.WHITE}🎮 Open Game")
        print(f"{Fore.CYAN}5. {Fore.WHITE}🛑 Close Game")
        print(f"{Fore.CYAN}6. {Fore.WHITE}🌫️ Clear Fog")
        print(f"{Fore.CYAN}7. {Fore.WHITE}🛡️ Anti-Ban")
        print(f"{Fore.CYAN}8. {Fore.WHITE}🔄 Check for Updates")
        print(f"{Fore.CYAN}9. {Fore.WHITE}🚪 Exit")
        
        choice = input(f"\n{Fore.YELLOW}👉 Choice (1-9): {Style.RESET_ALL}").strip()
        
        if choice == "1":
            controller.show_devices()
            
        elif choice == "2":
            controller.scan_devices()
            if controller.all_devices:
                controller.show_devices()
                selection = input(f"\n{Fore.YELLOW}👉 Devices (1, 1+2+3, all): {Style.RESET_ALL}")
                if controller.connect_devices(selection):
                    print(f"\n{Fore.GREEN}✅ Connected!{Style.RESET_ALL}")
                    controller.show_devices()
                else:
                    print(f"\n{Fore.RED}❌ Invalid{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}⚠️ No devices{Style.RESET_ALL}")
                
        elif choice == "3":
            if controller.connected_devices:
                print(f"\n{Fore.GREEN}📋 Connected:{Style.RESET_ALL}")
                for i, dev in enumerate(controller.connected_devices, 1):
                    print(f"  {i}. {dev[:12]}...")
                
                selection = input(f"\n{Fore.YELLOW}👉 Devices (1, 1+2+3, all): {Style.RESET_ALL}")
                if controller.disconnect_devices(selection):
                    print(f"\n{Fore.GREEN}✅ Disconnected!{Style.RESET_ALL}")
                    controller.show_devices()
                else:
                    print(f"\n{Fore.RED}❌ Invalid{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}⚠️ None connected{Style.RESET_ALL}")
                
        elif choice == "4":
            controller.open_game()
            
        elif choice == "5":
            controller.close_game()
            
        elif choice == "6":
            try:
                max_repeats = int(input(f"\n{Fore.YELLOW}👉 Number of runs (0 for unlimited): {Style.RESET_ALL}"))
                controller.max_repeats = max_repeats
            except ValueError:
                print(f"\n{Fore.RED}⚠️ Invalid number!{Style.RESET_ALL}")
                continue
                
            repeat_count = 0
            while True:
                if controller.max_repeats > 0 and repeat_count >= controller.max_repeats:
                    break
                    
                success = controller.clear_fog()
                repeat_count += 1
                
                if not success:
                    break
                    
                if controller.max_repeats == 0:
                    cmd = input(f"\n{Fore.YELLOW}👉 {repeat_count} done. Continue? (y/n/stop): {Style.RESET_ALL}").strip().lower()
                    if cmd == 'stop':
                        controller.running = False
                        break
                    elif cmd != 'y':
                        break
            
        elif choice == "7":
            enabled = input(f"\n{Fore.YELLOW}👉 Enable anti-ban? (y/n): {Style.RESET_ALL}").strip().lower()
            controller.set_anti_ban(enabled == 'y')
            
        elif choice == "8":
            ask_for_update()
            
        elif choice == "9":
            print(f"\n{Fore.MAGENTA}✨ Goodbye!{Style.RESET_ALL}")
            break
            
        else:
            print(f"\n{Fore.RED}⚠️ Invalid!{Style.RESET_ALL}")
        
        input(f"\n{Fore.YELLOW}↵ Continue...{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
