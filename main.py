import os
import sys
import time
import random
import subprocess
try:
    from colorama import init, Fore, Back, Style
    import cv2
    import numpy as np
except ImportError:
    import pip
    packages = ['colorama', 'opencv-python', 'numpy']
    for package in packages:
        pip.main(['install', package])
    from colorama import init, Fore, Back, Style
    import cv2
    import numpy as np

init()

class MEmuController:
    def __init__(self):
        self.adb_path = "adb.exe"
        self.all_devices = []
        self.connected_devices = []
        self.screenshot_dir = "screenshots"
        self.template_dir = "templates"
        self.anti_ban_enabled = True
        self.anti_ban_level = 2
        self.max_repeats = 0
        self.rest_interval = 0
        self.rest_duration = 0
        self.current_run_count = 0
        self.running = True
        self.last_activity_time = time.time()
        self.activity_pattern = []
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

    def _get_anti_ban_params(self):
        if not self.anti_ban_enabled:
            return {
                'position_offset': 0,
                'delay_before': 0.1,
                'delay_after': 0.2,
                'action_delay': 0.5
            }
        
        if self.anti_ban_level == 1:
            return {
                'position_offset': random.randint(0, 5),
                'delay_before': random.uniform(0.1, 0.3),
                'delay_after': random.uniform(0.2, 0.4),
                'action_delay': random.uniform(0.5, 1.0)
            }
        elif self.anti_ban_level == 2:
            return {
                'position_offset': random.randint(3, 10),
                'delay_before': random.uniform(0.2, 0.5),
                'delay_after': random.uniform(0.3, 0.6),
                'action_delay': random.uniform(1.0, 2.0)
            }
        else:
            return {
                'position_offset': random.randint(8, 15),
                'delay_before': random.uniform(0.3, 0.8),
                'delay_after': random.uniform(0.5, 1.0),
                'action_delay': random.uniform(2.0, 3.0)
            }

    def _click_position(self, device, position):
        if position is None:
            return False
        x, y = position
        
        params = self._get_anti_ban_params()
        
        x += random.randint(-params['position_offset'], params['position_offset'])
        y += random.randint(-params['position_offset'], params['position_offset'])
        
        time.sleep(params['delay_before'])
        
        self.last_activity_time = time.time()
        self.activity_pattern.append((x, y, self.last_activity_time))
        if len(self.activity_pattern) > 10:
            self.activity_pattern.pop(0)
        
        result = self._run_adb("-s", device, "shell", "input", "tap", str(x), str(y))
        
        time.sleep(params['delay_after'])
        
        return result is not None

    def _wait_for_image(self, device, template_filename, timeout=30, interval=1):
        start_time = time.time()
        while time.time() - start_time < timeout and self.running:
            position = self._find_image(device, template_filename)
            if position is not None:
                return position
                
            params = self._get_anti_ban_params()
            actual_interval = interval * random.uniform(0.8, 1.2) + params['action_delay']
            time.sleep(actual_interval)
        return None

    def _show_status(self, device, message):
        emoji = "⚡" if "start" in message.lower() else \
                "✅" if "success" in message.lower() else \
                "❌" if "fail" in message.lower() else \
                "🔍" if "look" in message.lower() else \
                "🔄" if "process" in message.lower() else \
                "🛡️" if "anti-ban" in message.lower() else "⚙️"
                
        ab_indicator = ""
        if self.anti_ban_enabled and any(word in message.lower() for word in ["click", "tap", "press", "select"]):
            ab_indicator = f" {Fore.CYAN}[AB-Lv{self.anti_ban_level}]{Style.RESET_ALL}"
            
        print(f"\n{Fore.BLUE}{emoji} {device[:5]}...: {Fore.WHITE}{message}{ab_indicator}{Style.RESET_ALL}")

    def clear_fog(self):
        if not self.connected_devices:
            print(f"\n{Fore.RED}⚠️ No devices connected!{Style.RESET_ALL}")
            return False
        
        self.current_run_count += 1
        self.running = True

        if self.rest_interval > 0 and self.current_run_count % self.rest_interval == 0:
            rest_msg = f"💤 Resting for {self.rest_duration}s (Run {self.current_run_count}/{self.max_repeats if self.max_repeats > 0 else '∞'})"
            print(f"\n{Fore.YELLOW}{rest_msg}{Style.RESET_ALL}")
            time.sleep(self.rest_duration)
        
        for device in self.connected_devices:
            if not self.running:
                self._show_status(device, "Stopped by user")
                break
                
            self._show_status(device, "Starting fog clearing process")
            
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
        self._animate_loading("Scanning devices")
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
        
        print(f"\n{Fore.GREEN}📋 Connected Devices:{Style.RESET_ALL}")
        for i, dev in enumerate(self.all_devices, 1):
            status = f"{Fore.GREEN}✓ Connected{Style.RESET_ALL}" if dev in self.connected_devices else f"{Fore.RED}✗ Disconnected{Style.RESET_ALL}"
            print(f"  {i}. {dev[:12]}... - {status}")
            
        print(f"\n{Fore.YELLOW}🛡️ Anti-Ban Status:{Style.RESET_ALL}")
        ab_status = f"{Fore.GREEN}ENABLED (Level {self.anti_ban_level}){Style.RESET_ALL}" if self.anti_ban_enabled else f"{Fore.RED}DISABLED{Style.RESET_ALL}"
        print(f"  Status: {ab_status}")
        print(f"  Last Activity: {time.strftime('%H:%M:%S', time.localtime(self.last_activity_time))}")
        
        if self.activity_pattern:
            print(f"  Activity Pattern: {len(self.activity_pattern)} actions recorded")

    def open_game(self, package_name="com.rok.gp.vn"):
        if not self.connected_devices:
            print(f"\n{Fore.RED}⚠️ No devices connected!{Style.RESET_ALL}")
            return False
        
        success = True
        for device in self.connected_devices:
            self._show_status(device, "Attempting to open game")
            output = self._run_adb("-s", device, "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1")
            if output is None:
                self._show_status(device, "Failed to open game")
                success = False
            else:
                self._show_status(device, "Game opened successfully")
        return success

    def close_game(self, package_name="com.rok.gp.vn"):
        if not self.connected_devices:
            print(f"\n{Fore.RED}⚠️ No devices connected!{Style.RESET_ALL}")
            return False
        
        success = True
        for device in self.connected_devices:
            self._show_status(device, "Attempting to close game")
            output = self._run_adb("-s", device, "shell", "am", "force-stop", package_name)
            if output is None:
                self._show_status(device, "Failed to close game")
                success = False
            else:
                self._show_status(device, "Game closed successfully")
        return success

    def set_anti_ban(self, enabled=None, level=None):
        if enabled is not None:
            self.anti_ban_enabled = enabled
            status = "ON" if enabled else "OFF"
            color = Fore.GREEN if enabled else Fore.RED
            print(f"\n{color}✅ Anti-ban {status}{Style.RESET_ALL}")
            
        if level is not None and 1 <= level <= 3:
            self.anti_ban_level = level
            levels = {1: "Low", 2: "Medium", 3: "High"}
            print(f"\n{Fore.GREEN}✅ Anti-ban level set to {levels[level]}{Style.RESET_ALL}")
            
        if enabled is None and level is None:
            print(f"\n{Fore.YELLOW}Current Anti-ban status:{Style.RESET_ALL}")
            print(f"  Enabled: {self.anti_ban_enabled}")
            print(f"  Level: {self.anti_ban_level}")

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

def main():
    controller = MEmuController()
    
    while True:
        print_banner()
        
        conn_status = f"{Fore.GREEN}Connected: {len(controller.connected_devices)}/{len(controller.all_devices)}{Style.RESET_ALL}" if controller.all_devices else f"{Fore.RED}No devices found{Style.RESET_ALL}"
        
        ab_status = f"{Fore.GREEN}ON (Lv{controller.anti_ban_level}){Style.RESET_ALL}" if controller.anti_ban_enabled else f"{Fore.RED}OFF{Style.RESET_ALL}"
        
        print(f"{Fore.CYAN}📊 Status: {conn_status} | 🛡️ Anti-Ban: {ab_status}\n")
        
        print(f"{Fore.CYAN}1. {Fore.WHITE}📋 Show Devices & Status")
        print(f"{Fore.CYAN}2. {Fore.WHITE}🔌 Connect Devices")
        print(f"{Fore.CYAN}3. {Fore.WHITE}❌ Disconnect Devices")
        print(f"{Fore.CYAN}4. {Fore.WHITE}🎮 Open Game")
        print(f"{Fore.CYAN}5. {Fore.WHITE}🛑 Close Game")
        print(f"{Fore.CYAN}6. {Fore.WHITE}🌫️ Clear Fog")
        print(f"{Fore.CYAN}7. {Fore.WHITE}🛡️ Configure Anti-Ban")
        print(f"{Fore.CYAN}8. {Fore.WHITE}🚪 Exit")
        
        choice = input(f"\n{Fore.YELLOW}👉 Your choice (1-8): {Style.RESET_ALL}").strip()
        
        if choice == "1":
            controller.show_devices()
            
        elif choice == "2":
            controller.scan_devices()
            if controller.all_devices:
                controller.show_devices()
                selection = input(f"\n{Fore.YELLOW}👉 Select devices (1, 1+2+3, all): {Style.RESET_ALL}")
                if controller.connect_devices(selection):
                    print(f"\n{Fore.GREEN}✅ Devices connected successfully!{Style.RESET_ALL}")
                    controller.show_devices()
                else:
                    print(f"\n{Fore.RED}❌ Invalid selection{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}⚠️ No devices detected{Style.RESET_ALL}")
                
        elif choice == "3":
            if controller.connected_devices:
                print(f"\n{Fore.GREEN}📋 Currently connected devices:{Style.RESET_ALL}")
                for i, dev in enumerate(controller.connected_devices, 1):
                    print(f"  {i}. {dev[:12]}...")
                
                selection = input(f"\n{Fore.YELLOW}👉 Select devices to disconnect (1, 1+2+3, all): {Style.RESET_ALL}")
                if controller.disconnect_devices(selection):
                    print(f"\n{Fore.GREEN}✅ Devices disconnected successfully!{Style.RESET_ALL}")
                    controller.show_devices()
                else:
                    print(f"\n{Fore.RED}❌ Invalid selection{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}⚠️ No devices currently connected{Style.RESET_ALL}")
                
        elif choice == "4":
            controller.open_game()
            
        elif choice == "5":
            controller.close_game()
            
        elif choice == "6":
            try:
                max_repeats = int(input(f"\n{Fore.YELLOW}👉 Number of runs (0 for unlimited): {Style.RESET_ALL}"))
                controller.max_repeats = max_repeats
                
                if controller.max_repeats > 0:
                    rest_interval = int(input(f"{Fore.YELLOW}👉 Rest after how many runs? (0 for no rest): {Style.RESET_ALL}"))
                    if rest_interval > 0:
                        controller.rest_interval = rest_interval
                        controller.rest_duration = int(input(f"{Fore.YELLOW}👉 Rest duration (seconds): {Style.RESET_ALL}"))
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
                    cmd = input(f"\n{Fore.YELLOW}👉 {repeat_count} runs completed. Continue? (y/n/stop): {Style.RESET_ALL}").strip().lower()
                    if cmd == 'stop':
                        controller.running = False
                        break
                    elif cmd != 'y':
                        break
            
        elif choice == "7":
            print(f"\n{Fore.YELLOW}🛡️ Anti-Ban Configuration:{Style.RESET_ALL}")
            print(f"1. {Fore.GREEN}Enable Anti-Ban{Style.RESET_ALL}")
            print(f"2. {Fore.RED}Disable Anti-Ban{Style.RESET_ALL}")
            print(f"3. Set Anti-Ban Level (Current: {controller.anti_ban_level})")
            
            ab_choice = input(f"{Fore.YELLOW}👉 Your choice (1-3): {Style.RESET_ALL}").strip()
            
            if ab_choice == "1":
                controller.set_anti_ban(enabled=True)
            elif ab_choice == "2":
                controller.set_anti_ban(enabled=False)
            elif ab_choice == "3":
                level = input(f"{Fore.YELLOW}👉 Set level (1-3, 1=Low, 2=Medium, 3=High): {Style.RESET_ALL}").strip()
                if level in ['1', '2', '3']:
                    controller.set_anti_ban(level=int(level))
                else:
                    print(f"{Fore.RED}⚠️ Invalid level!{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}⚠️ Invalid choice!{Style.RESET_ALL}")
            
        elif choice == "8":
            print(f"\n{Fore.MAGENTA}✨ Goodbye!{Style.RESET_ALL}")
            break
            
        else:
            print(f"\n{Fore.RED}⚠️ Invalid choice!{Style.RESET_ALL}")
        
        input(f"\n{Fore.YELLOW}↵ Press Enter to continue...{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
