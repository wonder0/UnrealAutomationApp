import sys
import os
import time
import socket
import json
import ast
from pathlib import Path
from PySide6.QtCore import QObject, QThread, Signal

try:
    import remote_execution as remote
except ImportError:
    remote = None

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    full_path = Path(base_path) / relative_path
    print(f"get_resource_path: base_path={base_path}, relative_path={relative_path}, full_path={full_path}")
    return full_path

def parse_manifest(script_path):
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'SCRIPT_MANIFEST':
                        return ast.literal_eval(node.value)
        return None
    except Exception as e:
        print(f"Error parsing manifest: {e}")
        return None

class NodeScanner(QThread):
    nodes_updated = Signal(list)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.remote_exec = None
    
    def run(self):
        if not remote:
            self.nodes_updated.emit([])
            return
        
        self.remote_exec = remote.RemoteExecution()
        self.remote_exec.start()
        
        while self.running:
            time.sleep(2)
            if self.remote_exec:
                nodes = self.remote_exec.remote_nodes
                self.nodes_updated.emit(nodes)
    
    def stop(self):
        self.running = False
        if self.remote_exec:
            self.remote_exec.stop()
        self.wait()

class CommunicationServer(QThread):
    log_received = Signal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.port = 9999
        self.client_socket = None

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(('127.0.0.1', self.port))
            server.listen(1)
            server.settimeout(1.0) 
            
            while self.running:
                try:
                    client, addr = server.accept()
                    client.settimeout(1.0)
                    self.client_socket = client
                    
                    while self.running:
                        try:
                            data = client.recv(4096)
                            if not data:
                                break
                            self.log_received.emit(data.decode('utf-8', errors='ignore').strip())
                        except socket.timeout:
                            continue
                        except socket.error:
                            break
                    
                    if self.client_socket:
                        try: self.client_socket.close()
                        except: pass
                        self.client_socket = None
                        
                except socket.timeout:
                    continue
                except Exception:
                    pass
        finally:
            server.close()

    def send_command(self, command):
        if self.client_socket:
            try:
                self.client_socket.sendall(command.encode('utf-8'))
            except Exception as e:
                self.log_received.emit(f"Error sending command: {e}")

    def stop(self):
        self.running = False
        self.wait()

class Worker(QObject):
    finished = Signal()
    progress = Signal(str)

    def __init__(self, script_path, node_id, params_dict):
        super().__init__()
        self.script_path = script_path
        self.node_id = node_id
        self.params_dict = params_dict

    def run(self):
        if not remote:
            self.progress.emit("ERROR: 'remote_execution.py' not found!")
            self.finished.emit()
            return

        self.progress.emit(f"Connecting to Node: {self.node_id}...")
        
        remote_exec = remote.RemoteExecution()
        remote_exec.start()
        
        time.sleep(1)
        
        try:
            remote_exec.open_command_connection(self.node_id)
            self.progress.emit(f"Connected to UE Node: {self.node_id}")
        except Exception as e:
            self.progress.emit(f"ERROR: Could not connect to node: {e}")
            remote_exec.stop()
            self.finished.emit()
            return

        try:
            with open(self.script_path, 'r') as f:
                script_content = f.read()
            
            script_dir = self.script_path.parent.resolve()
            app_dir = script_dir.parent.resolve()
            path_to_add = str(app_dir).replace('\\', '/')

            params_json = json.dumps(self.params_dict)
            argv_list = [self.script_path.name, '--params', params_json]
            
            injection_code = (
                f"import sys\n"
                f"if '{path_to_add}' not in sys.path: sys.path.append('{path_to_add}')\n"
                f"sys.argv = {repr(argv_list)}\n"
            )
            
            script_content = injection_code + script_content
            self.progress.emit(f"Sending {self.script_path.name} to Unreal...")
            response = remote_exec.run_command(script_content, unattended=False)
            
            if response.get('success'):
                self.progress.emit("[UE]: Executed Successfully")
            else:
                self.progress.emit("Execution Failed in Unreal.")
                
        except Exception as e:
            self.progress.emit(f"Error: {e}")
        
        remote_exec.stop()
        self.finished.emit()