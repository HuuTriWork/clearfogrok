import subprocess 
import os
import time
from colorama import init, Fore, Back, Style
import sys
import cv2
import numpy as np
import random

init()  

class MEmuController:
    def __init__(self):
        self.adb_path = r"C:\Microvirt\MEmu\adb.exe"
        self.all_devices = []
        self.connected_devices = []
        self.screenshot_dir = "screenshots"
        self.template_dir = "templates"
        self.anti_ban_enabled = True
        self.max_repeats = 0 
        self.rest_interval = 0  
        self.rest_duration = 0 
        self.current_run_count = 0
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
            x += random.randint(-5, 5)
            y += random.randint(-5, 5)
            
       
        if self.anti_ban_enabled:
            time.sleep(random.uniform(0.1, 0.3))
            
        result = self._run_adb("-s", device, "shell", "input", "tap", str(x), str(y))
        
      
        if self.anti_ban_enabled:
            time.sleep(random.uniform(0.1, 0.3))
            
        return result is not None

    def _wait_for_image(self, device, template_filename, timeout=30, interval=1):
        start_time = time.time()
        while time.time() - start_time < timeout:
            position = self._find_image(device, template_filename)
            if position is not None:
                return position
                
         
            actual_interval = interval
            if self.anti_ban_enabled:
                actual_interval = random.uniform(interval*0.8, interval*1.2)
            time.sleep(actual_interval)
        return None

    def _show_status(self, device, message):
        print(f"\n{Fore.BLUE}⚙️ Device {device}: {Fore.WHITE}{message}{Style.RESET_ALL}")

    def clear_fog(self):
        if not self.connected_devices:
            print(f"\n{Fore.RED}⚠️ No connected devices{Style.RESET_ALL}")
            return False
        
        self.current_run_count += 1
        
       
        if self.rest_interval > 0 and self.current_run_count % self.rest_interval == 0:
            print(f"\n{Fore.YELLOW}⏳ Resting for {self.rest_duration} seconds...{Style.RESET_ALL}")
            time.sleep(self.rest_duration)
        
        for device in self.connected_devices:
            self._show_status(device, "Starting fog clearing process")
            
          
            self._show_status(device, "Looking for home or map")
            home_pos = self._find_image(device, "home.png")
            map_pos = self._find_image(device, "map.png")
            
            if home_pos:
                self._show_status(device, "Found home screen, clicking")
                self._click_position(device, home_pos)
            elif map_pos:
                self._show_status(device, "Found map screen, clicking")
                self._click_position(device, map_pos)
                time.sleep(2) 
               
                home_pos = self._find_image(device, "home.png")
                if home_pos:
                    self._show_status(device, "Found home screen after map, clicking")
                    self._click_position(device, home_pos)
            else:
                self._show_status(device, "Neither home nor map found")
                continue
                
            time.sleep(2)  
            
           
            self._show_status(device, "Looking for options 1-4")
            found = False
            for i in range(1, 5):
                option_pos = self._find_image(device, f"{i}.png")
                if option_pos:
                    self._show_status(device, f"Found option {i}, clicking")
                    self._click_position(device, option_pos)
                    found = True
                    break
                    
            if not found:
                self._show_status(device, "No options 1-4 found")
                continue
                
            time.sleep(2)  
            
            
            scout_pos = self._find_image(device, "scout.png")
            if scout_pos:
                self._show_status(device, "Found scout, clicking")
                self._click_position(device, scout_pos)
            else:
                self._show_status(device, "Scout not found after option selection")
                
            
            self._show_status(device, "Starting exploration process")
            
            
            explore_pos = self._wait_for_image(device, "explore.png")
            if explore_pos:
                self._show_status(device, "Found explore button, clicking")
                self._click_position(device, explore_pos)
                time.sleep(5) 
                
                
                selected_pos = self._find_image(device, "selected.png")
                notselected_pos = self._find_image(device, "notselected.png")
                
                if notselected_pos:
                    self._show_status(device, "Found not selected, clicking")
                    self._click_position(device, notselected_pos)
                elif selected_pos:
                    self._show_status(device, "Already selected, skipping")
                else:
                    self._show_status(device, "Couldn't determine selection status")
                
                
                explore_pos = self._find_image(device, "explore.png")
                if explore_pos:
                    self._show_status(device, "Found explore button again, clicking")
                    self._click_position(device, explore_pos)
                    
                    
                    send_pos = self._wait_for_image(device, "send.png")
                    if send_pos:
                        self._show_status(device, "Found send button, clicking")
                        self._click_position(device, send_pos)
                        
                       
                        home_pos = self._wait_for_image(device, "home.png")
                        if home_pos:
                            self._show_status(device, "Found home button, clicking")
                            self._click_position(device, home_pos)
                        else:
                            self._show_status(device, "Home button not found after sending")
                    else:
                        self._show_status(device, "Send button not found")
                else:
                    self._show_status(device, "Explore button not found after selection")
            else:
                self._show_status(device, "Explore button not found")
                
            self._show_status(device, "Fog clearing completed")
        
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
        
        print(f"\n{Fore.GREEN}📋 All Available Devices:{Style.RESET_ALL}")
        for i, dev in enumerate(self.all_devices, 1):
            status = f"{Fore.GREEN}✓ Connected{Style.RESET_ALL}" if dev in self.connected_devices else f"{Fore.RED}✗ Disconnected{Style.RESET_ALL}"
            print(f"  {Fore.CYAN}{i}. {Fore.MAGENTA}{dev}{Style.RESET_ALL} - {status}")

    def open_game(self, package_name="com.rok.gp.vn"):
        if not self.connected_devices:
            print(f"\n{Fore.RED}⚠️ No connected devices{Style.RESET_ALL}")
            return False
        
        success = True
        for device in self.connected_devices:
            output = self._run_adb("-s", device, "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1")
            if output is None:
                print(f"\n{Fore.RED}❌ Failed to open game on device {device}{Style.RESET_ALL}")
                success = False
            else:
                print(f"\n{Fore.GREEN}✅ Successfully opened game on device {device}{Style.RESET_ALL}")
        return success

    def close_game(self, package_name="com.rok.gp.vn"):
        if not self.connected_devices:
            print(f"\n{Fore.RED}⚠️ No connected devices{Style.RESET_ALL}")
            return False
        
        success = True
        for device in self.connected_devices:
            output = self._run_adb("-s", device, "shell", "am", "force-stop", package_name)
            if output is None:
                print(f"\n{Fore.RED}❌ Failed to close game on device {device}{Style.RESET_ALL}")
                success = False
            else:
                print(f"\n{Fore.GREEN}✅ Successfully closed game on device {device}{Style.RESET_ALL}")
        return success

    def set_anti_ban(self, enabled):
        self.anti_ban_enabled = enabled
        status = "ENABLED" if enabled else "DISABLED"
        print(f"\n{Fore.GREEN}✅ Anti-ban features {status}{Style.RESET_ALL}")

    def set_repeat_settings(self, max_repeats, rest_interval, rest_duration):
        self.max_repeats = max_repeats
        self.rest_interval = rest_interval
        self.rest_duration = rest_duration
        print(f"\n{Fore.GREEN}✅ Repeat settings updated:{Style.RESET_ALL}")
        print(f"  Max repeats: {'Infinite' if max_repeats == 0 else max_repeats}")
        print(f"  Rest after every {rest_interval} runs" if rest_interval > 0 else "  No resting")
        print(f"  Rest duration: {rest_duration} seconds" if rest_interval > 0 else "")

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
    print(f"{Fore.YELLOW}⋆｡ﾟ✶°  MEmu Device Controller  °✶ﾟ｡⋆{Style.RESET_ALL}\n")

def main():
    controller = MEmuController()
    
    while True:
        print_banner()
        print(f"{Fore.CYAN}1. {Fore.WHITE}📋 Show Device List")
        print(f"{Fore.CYAN}2. {Fore.WHITE}🔌 Connect Devices")
        print(f"{Fore.CYAN}3. {Fore.WHITE}❌ Disconnect Devices")
        print(f"{Fore.CYAN}4. {Fore.WHITE}🎮 Open Game (com.rok.gp.vn)")
        print(f"{Fore.CYAN}5. {Fore.WHITE}🛑 Close Game (com.rok.gp.vn)")
        print(f"{Fore.CYAN}6. {Fore.WHITE}🌫️ Clear Fog")
        print(f"{Fore.CYAN}7. {Fore.WHITE}⚙️ Configure Anti-Ban")
        print(f"{Fore.CYAN}8. {Fore.WHITE}🔄 Configure Repeat Settings")
        print(f"{Fore.CYAN}9. {Fore.WHITE}🚪 Exit")
        
        choice = input(f"\n{Fore.YELLOW}👉 Your choice (1-9): {Style.RESET_ALL}").strip()
        
        if choice == "1":
            controller.show_devices()
            
        elif choice == "2":
            controller.scan_devices()
            if controller.all_devices:
                controller.show_devices()
                selection = input(f"\n{Fore.YELLOW}👉 Select devices to connect (1, 1+2+3, or all): {Style.RESET_ALL}")
                if controller.connect_devices(selection):
                    print(f"\n{Fore.GREEN}✅ Successfully connected!{Style.RESET_ALL}")
                    controller.show_devices()
                else:
                    print(f"\n{Fore.RED}❌ Invalid selection{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}⚠️ No devices available{Style.RESET_ALL}")
                
        elif choice == "3":
            if controller.connected_devices:
                print(f"\n{Fore.GREEN}📋 Currently Connected Devices:{Style.RESET_ALL}")
                for i, dev in enumerate(controller.connected_devices, 1):
                    print(f"  {Fore.CYAN}{i}. {Fore.MAGENTA}{dev}{Style.RESET_ALL}")
                
                selection = input(f"\n{Fore.YELLOW}👉 Select devices to disconnect (1, 1+2+3, or all): {Style.RESET_ALL}")
                if controller.disconnect_devices(selection):
                    print(f"\n{Fore.GREEN}✅ Successfully disconnected!{Style.RESET_ALL}")
                    controller.show_devices()
                else:
                    print(f"\n{Fore.RED}❌ Invalid selection{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}⚠️ No connected devices{Style.RESET_ALL}")
                
        elif choice == "4":
            controller.open_game()
            
        elif choice == "5":
            controller.close_game()
            
        elif choice == "6":
            repeat_count = 0
            while True:
                if controller.max_repeats > 0 and repeat_count >= controller.max_repeats:
                    break
                    
                success = controller.clear_fog()
                repeat_count += 1
                
                if not success or controller.max_repeats == 0:
                   
                    if controller.max_repeats == 0:
                        cont = input(f"\n{Fore.YELLOW}👉 Completed {repeat_count} runs. Continue? (y/n): {Style.RESET_ALL}").strip().lower()
                        if cont != 'y':
                            break
                    else:
                        break
            
        elif choice == "7":
            enabled = input(f"\n{Fore.YELLOW}👉 Enable anti-ban features? (y/n): {Style.RESET_ALL}").strip().lower()
            controller.set_anti_ban(enabled == 'y')
            
        elif choice == "8":
            try:
                max_repeats = int(input(f"\n{Fore.YELLOW}👉 Max number of repeats (0 for infinite): {Style.RESET_ALL}"))
                rest_interval = int(input(f"{Fore.YELLOW}👉 Rest after how many runs (0 to disable): {Style.RESET_ALL}"))
                rest_duration = 0
                if rest_interval > 0:
                    rest_duration = int(input(f"{Fore.YELLOW}👉 Rest duration in seconds: {Style.RESET_ALL}"))
                controller.set_repeat_settings(max_repeats, rest_interval, rest_duration)
            except ValueError:
                print(f"\n{Fore.RED}⚠️ Invalid input!{Style.RESET_ALL}")
            
        elif choice == "9":
            print(f"\n{Fore.MAGENTA}✨ Thank you for using MEmu Controller!{Style.RESET_ALL}")
            break
            
        else:
            print(f"\n{Fore.RED}⚠️ Invalid option!{Style.RESET_ALL}")
        
        input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")

if __name__ == "__main__":
    main()