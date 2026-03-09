import sys
import time
import unreal
import socket
import select
import json

class AutomationHelper:
    def __init__(self, port=9999):
        self.socket = None
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(('127.0.0.1', port))
            self.socket.setblocking(False)
        except Exception:
            self.socket = None
            unreal.log_warning("AutomationHelper: Could not connect to Desktop App.")

    def log(self, message):
        unreal.log(message)
        if self.socket:
            try:
                self.socket.sendall((str(message) + "\n").encode('utf-8'))
            except:
                pass

    def check_signals(self):
        if not self.socket:
            return

        try:
            readable, _, _ = select.select([self.socket], [], [], 0)
            
            if readable:
                data = self.socket.recv(1024).decode('utf-8', errors='ignore')
                
                if "PAUSE" in data:
                    self.log(">>> PAUSED. Waiting for Resume...")
                    
                    while True:
                        ready, _, _ = select.select([self.socket], [], [], 0.1)
                        if ready:
                            cmd = self.socket.recv(1024).decode('utf-8', errors='ignore')
                            if "RESUME" in cmd:
                                self.log(">>> RESUMED.")
                                break
                        time.sleep(0.1)
        except Exception as e:
            self.log(f"Helper Error: {e}")

    def get_params(self):
        if len(sys.argv) >= 3 and sys.argv[1] == '--params':
            try:
                return json.loads(sys.argv[2])
            except:
                return {}
        return {}

    def close(self):
        if self.socket:
            self.socket.close()