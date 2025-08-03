import subprocess
import os
import time
from colorama import init, Fore, Back, Style
import sys
import cv2
import numpy as np
import random
import winreg
import threading
from concurrent.futures import ThreadPoolExecutor

init()

class EmulatorController:
    def __init__(self):
        self.adb_path = self._find_adb_path()
        self.all_devices = []
        self.connected_devices = []
        self.screenshot_dir = "screenshots"
        self.template_dir = "templates"
        self.anti_ban_level = 2  # 0: Off, 1: Basic, 2: Advanced, 3: Extreme
        self.max_repeats = 0
        self.rest_interval = 0
        self.rest_duration = 0
        self.current_run_count = 0
        self.operation_speed = 1.0  # 1.0 = normal, higher = faster
        self.status = {}
        os.makedirs(self.screenshot_dir, exist_ok=True)
        os.makedirs(self.template_dir, exist_ok=True)

    def _find_adb_path(self):
        paths = [
            r"C:\Microvirt\MEmu\adb.exe",
            r"C:\Program Files\Microvirt\MEmu\adb.exe",
            r"C:\LDPlayer\adb.exe",
            r"C:\Program Files\LDPlayer\adb.exe",
            r"C:\leidian\LDPlayer\adb.exe"
        ]
        
        try:
            subprocess.run(["adb", "version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return "adb"
        except:
            pass
            
        for path in paths:
            if os.path.exists(path):
                return path
                
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\leidian\LDPlayer") as key:
                install_path = winreg.QueryValueEx(key, "InstallDir")[0]
                adb_path = os.path.join(install_path, "adb.exe")
                if os.path.exists(adb_path):
                    return adb_path
        except:
            pass
            
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microvirt\MEmu") as key:
                install_path = winreg.QueryValueEx(key, "InstallDir")[0]
                adb_path = os.path.join(install_path, "adb.exe")
                if os.path.exists(adb_path):
                    return adb_path
        except:
            pass
            
        print(f"{Fore.RED}ADB not found.{Style.RESET_ALL}")
        return None

    def _run_adb(self, *args):
        if not self.adb_path:
            return None
            
        try:
            result = subprocess.run([self.adb_path] + list(args),
                                  capture_output=True,
                                  text=True,
                                  timeout=5)
            return result.stdout.strip() if result.returncode == 0 else None
        except:
            return None

    def _random_delay(self, base_time):
        if self.anti_ban_level == 0:
            time.sleep(base_time / self.operation_speed)
            return
            
        multiplier = 1.0
        if self.anti_ban_level == 1:
            multiplier = random.uniform(0.8, 1.2)
        elif self.anti_ban_level == 2:
            multiplier = random.uniform(0.6, 1.4)
        else:
            multiplier = random.uniform(0.4, 1.6)
            
        delay = (base_time * multiplier) / self.operation_speed
        time.sleep(max(0.1, delay))

    def _take_screenshot(self, device, filename):
        try:
            screenshot_path = os.path.join(self.screenshot_dir, f"{device}_{filename}")
            result = self._run_adb("-s", device, "exec-out", "screencap", "-p", ">", screenshot_path)
            return result is not None
        except:
            return False

    def _find_image(self, device, template_filename, threshold=0.8):
        screenshot_path = os.path.join(self.screenshot_dir, f"{device}_current.png")
        if not self._take_screenshot(device, "current.png"):
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
        
        if self.anti_ban_level > 0:
            x += random.randint(-5, 5)
            y += random.randint(-5, 5)
            
        self._random_delay(0.2)
            
        result = self._run_adb("-s", device, "shell", "input", "tap", str(x), str(y))
        
        self._random_delay(0.2)
        return result is not None

    def _wait_for_image(self, device, template_filename, timeout=30):
        start_time = time.time()
        while time.time() - start_time < timeout:
            position = self._find_image(device, template_filename)
            if position is not None:
                return position
            self._random_delay(0.5)
        return None

    def _update_status(self, device, message, success=None):
        self.status[device] = {
            "message": message,
            "timestamp": time.time(),
            "success": success
        }

    def _parallel_task(self, func, *args):
        with ThreadPoolExecutor(max_workers=len(self.connected_devices)) as executor:
            return list(executor.map(func, self.connected_devices, *args))

    def clear_fog_device(self, device):
        self._update_status(device, "Starting fog clearing")
        
        home_pos = self._find_image(device, "home.png")
        map_pos = self._find_image(device, "map.png")
        
        if home_pos:
            self._click_position(device, home_pos)
        elif map_pos:
            self._click_position(device, map_pos)
            self._random_delay(2)
            home_pos = self._find_image(device, "home.png")
            if home_pos:
                self._click_position(device, home_pos)
        
        self._random_delay(2)
        
        for i in range(1, 5):
            option_pos = self._find_image(device, f"{i}.png")
            if option_pos:
                self._click_position(device, option_pos)
                break
        
        self._random_delay(2)
        
        scout_pos = self._find_image(device, "scout.png")
        if scout_pos:
            self._click_position(device, scout_pos)
        
        explore_pos = self._wait_for_image(device, "explore.png")
        if explore_pos:
            self._click_position(device, explore_pos)
            self._random_delay(3)
            
            notselected_pos = self._find_image(device, "notselected.png")
            if notselected_pos:
                self._click_position(device, notselected_pos)
            
            explore_pos = self._find_image(device, "explore.png")
            if explore_pos:
                self._click_position(device, explore_pos)
                
                send_pos = self._wait_for_image(device, "send.png")
                if send_pos:
                    self._click_position(device, send_pos)
                    
                    home_pos = self._wait_for_image(device, "home.png")
                    if home_pos:
                        self._click_position(device, home_pos)
        
        self._update_status(device, "Fog clearing completed", True)
        return True

    def clear_fog(self):
        if not self.connected_devices:
            return False
            
        self.current_run_count += 1
        
        if self.rest_interval > 0 and self.current_run_count % self.rest_interval == 0:
            self._update_status("SYSTEM", f"Resting for {self.rest_duration}s")
            time.sleep(self.rest_duration)
        
        results = self._parallel_task(self.clear_fog_device)
        return all(results)

    def scan_devices(self):
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
        
        print(f"\n{Fore.GREEN}📋 Available Devices:{Style.RESET_ALL}")
        for i, dev in enumerate(self.all_devices, 1):
            status = f"{Fore.GREEN}✓" if dev in self.connected_devices else f"{Fore.RED}✗"
            print(f"  {status} {i}. {Fore.CYAN}{dev}{Style.RESET_ALL}")

    def show_status(self):
        print(f"\n{Fore.BLUE}📊 Current Status:{Style.RESET_ALL}")
        for device, info in self.status.items():
            color = Fore.GREEN if info.get('success', None) else Fore.YELLOW
            elapsed = int(time.time() - info['timestamp'])
            print(f"  {color}⏱️ {device}: {info['message']} ({elapsed}s ago){Style.RESET_ALL}")

    def open_game(self, package_name="com.rok.gp.vn"):
        if not self.connected_devices:
            return False
        
        def open_device(device):
            result = self._run_adb("-s", device, "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1")
            self._update_status(device, "Game opened" if result else "Failed to open game", result)
            return result
            
        return all(self._parallel_task(open_device))

    def close_game(self, package_name="com.rok.gp.vn"):
        if not self.connected_devices:
            return False
        
        def close_device(device):
            result = self._run_adb("-s", device, "shell", "am", "force-stop", package_name)
            self._update_status(device, "Game closed" if result else "Failed to close game", result)
            return result
            
        return all(self._parallel_task(close_device))

    def set_anti_ban(self, level):
        levels = {
            0: ("OFF", Fore.RED),
            1: ("BASIC", Fore.YELLOW),
            2: ("ADVANCED", Fore.GREEN),
            3: ("EXTREME", Fore.BLUE)
        }
        self.anti_ban_level = min(max(0, level), 3)
        name, color = levels[self.anti_ban_level]
        print(f"\n{color}✅ Anti-ban level set to {name}{Style.RESET_ALL}")

    def set_speed(self, speed):
        self.operation_speed = max(0.5, min(3.0, speed))
        print(f"\n{Fore.GREEN}✅ Operation speed set to {self.operation_speed:.1f}x{Style.RESET_ALL}")

    def set_repeat_settings(self, max_repeats, rest_interval, rest_duration):
        self.max_repeats = max_repeats
        self.rest_interval = rest_interval
        self.rest_duration = rest_duration
        print(f"\n{Fore.GREEN}✅ Repeat settings updated:{Style.RESET_ALL}")
        print(f"  Max repeats: {'∞' if max_repeats == 0 else max_repeats}")
        print(f"  Rest every: {rest_interval or 'Never'}")
        print(f"  Rest duration: {rest_duration}s" if rest_interval else "")

def print_menu():
    print(f"\n{Fore.CYAN}⋆ Main Menu ⋆{Style.RESET_ALL}")
    print(f"{Fore.CYAN}1.{Style.RESET_ALL} 📋 Device Management")
    print(f"{Fore.CYAN}2.{Style.RESET_ALL} 🎮 Game Control")
    print(f"{Fore.CYAN}3.{Style.RESET_ALL} ⚙️ Settings")
    print(f"{Fore.CYAN}4.{Style.RESET_ALL} 🌫️ Fog Clearing")
    print(f"{Fore.CYAN}5.{Style.RESET_ALL} 📊 Status")
    print(f"{Fore.CYAN}6.{Style.RESET_ALL} 🚪 Exit")

def device_menu(controller):
    while True:
        print(f"\n{Fore.CYAN}⋆ Device Management ⋆{Style.RESET_ALL}")
        print(f"{Fore.CYAN}1.{Style.RESET_ALL} Scan Devices")
        print(f"{Fore.CYAN}2.{Style.RESET_ALL} Connect Devices")
        print(f"{Fore.CYAN}3.{Style.RESET_ALL} Disconnect Devices")
        print(f"{Fore.CYAN}4.{Style.RESET_ALL} Show Devices")
        print(f"{Fore.CYAN}5.{Style.RESET_ALL} Back")
        
        choice = input(f"{Fore.YELLOW}👉 Choice (1-5): {Style.RESET_ALL}").strip()
        
        if choice == "1":
            controller.scan_devices()
            controller.show_devices()
        elif choice == "2":
            selection = input(f"{Fore.YELLOW}👉 Devices to connect (e.g., 1, 1+2+3, all): {Style.RESET_ALL}")
            if controller.connect_devices(selection):
                print(f"{Fore.GREEN}✅ Connected successfully!{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ Connection failed!{Style.RESET_ALL}")
        elif choice == "3":
            selection = input(f"{Fore.YELLOW}👉 Devices to disconnect (e.g., 1, 1+2+3, all): {Style.RESET_ALL}")
            if controller.disconnect_devices(selection):
                print(f"{Fore.GREEN}✅ Disconnected successfully!{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ Disconnection failed!{Style.RESET_ALL}")
        elif choice == "4":
            controller.show_devices()
        elif choice == "5":
            break
        else:
            print(f"{Fore.RED}⚠ Invalid option!{Style.RESET_ALL}")

def game_menu(controller):
    while True:
        print(f"\n{Fore.CYAN}⋆ Game Control ⋆{Style.RESET_ALL}")
        print(f"{Fore.CYAN}1.{Style.RESET_ALL} Open Game")
        print(f"{Fore.CYAN}2.{Style.RESET_ALL} Close Game")
        print(f"{Fore.CYAN}3.{Style.RESET_ALL} Back")
        
        choice = input(f"{Fore.YELLOW}👉 Choice (1-3): {Style.RESET_ALL}").strip()
        
        if choice == "1":
            if controller.open_game():
                print(f"{Fore.GREEN}✅ Game opened on all devices!{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ Failed to open game!{Style.RESET_ALL}")
        elif choice == "2":
            if controller.close_game():
                print(f"{Fore.GREEN}✅ Game closed on all devices!{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ Failed to close game!{Style.RESET_ALL}")
        elif choice == "3":
            break
        else:
            print(f"{Fore.RED}⚠ Invalid option!{Style.RESET_ALL}")

def settings_menu(controller):
    while True:
        print(f"\n{Fore.CYAN}⋆ Settings ⋆{Style.RESET_ALL}")
        print(f"{Fore.CYAN}1.{Style.RESET_ALL} Anti-Ban Level")
        print(f"{Fore.CYAN}2.{Style.RESET_ALL} Operation Speed")
        print(f"{Fore.CYAN}3.{Style.RESET_ALL} Repeat Settings")
        print(f"{Fore.CYAN}4.{Style.RESET_ALL} Back")
        
        choice = input(f"{Fore.YELLOW}👉 Choice (1-4): {Style.RESET_ALL}").strip()
        
        if choice == "1":
            level = input(f"{Fore.YELLOW}👉 Anti-ban level (0-3): {Style.RESET_ALL}")
            try:
                controller.set_anti_ban(int(level))
            except:
                print(f"{Fore.RED}⚠ Invalid input!{Style.RESET_ALL}")
        elif choice == "2":
            speed = input(f"{Fore.YELLOW}👉 Speed (0.5-3.0): {Style.RESET_ALL}")
            try:
                controller.set_speed(float(speed))
            except:
                print(f"{Fore.RED}⚠ Invalid input!{Style.RESET_ALL}")
        elif choice == "3":
            try:
                max_repeats = int(input(f"{Fore.YELLOW}👉 Max repeats (0=∞): {Style.RESET_ALL}"))
                rest_interval = int(input(f"{Fore.YELLOW}👉 Rest interval (0=off): {Style.RESET_ALL}"))
                rest_duration = 0
                if rest_interval > 0:
                    rest_duration = int(input(f"{Fore.YELLOW}👉 Rest duration (sec): {Style.RESET_ALL}"))
                controller.set_repeat_settings(max_repeats, rest_interval, rest_duration)
            except:
                print(f"{Fore.RED}⚠ Invalid input!{Style.RESET_ALL}")
        elif choice == "4":
            break
        else:
            print(f"{Fore.RED}⚠ Invalid option!{Style.RESET_ALL}")

def main():
    controller = EmulatorController()
    
    if not controller.adb_path:
        return
    
    while True:
        print_menu()
        choice = input(f"{Fore.YELLOW}👉 Main choice (1-6): {Style.RESET_ALL}").strip()
        
        if choice == "1":
            device_menu(controller)
        elif choice == "2":
            game_menu(controller)
        elif choice == "3":
            settings_menu(controller)
        elif choice == "4":
            repeat_count = 0
            while True:
                if controller.max_repeats > 0 and repeat_count >= controller.max_repeats:
                    break
                    
                success = controller.clear_fog()
                repeat_count += 1
                controller.show_status()
                
                if not success or controller.max_repeats == 0:
                    if controller.max_repeats == 0:
                        cont = input(f"{Fore.YELLOW}👉 Continue? (y/n): {Style.RESET_ALL}").strip().lower()
                        if cont != 'y':
                            break
                    else:
                        break
        elif choice == "5":
            controller.show_status()
        elif choice == "6":
            print(f"{Fore.MAGENTA}✨ Goodbye!{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}⚠ Invalid option!{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
