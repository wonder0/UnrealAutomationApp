from PySide6.QtCore import QThread, Qt
from PySide6.QtGui import QPixmap, QIcon, QPainter
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QLineEdit, QComboBox,
    QSplitter, QScrollArea, QCheckBox, QFileDialog, QDoubleSpinBox,
)
from backend import get_resource_path, CommunicationServer, Worker, NodeScanner, parse_manifest

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Unreal Automation Tool")
        self.setGeometry(100, 100, 1400, 700)

        icon_path = get_resource_path("logo.ico")
        print(f"Icon path: {icon_path}")
        print(f"Icon exists: {icon_path.exists()}")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.scripts_dir = get_resource_path("Scripts")
        self.current_inputs = {}

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        
        top_bar = self.create_top_bar()
        main_layout.addLayout(top_bar, stretch=0)
        
        content_splitter = QSplitter(Qt.Horizontal)
        
        left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()
        
        content_splitter.addWidget(left_panel)
        content_splitter.addWidget(right_panel)
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(content_splitter, stretch=1)

        self.comm_server = CommunicationServer()
        self.comm_server.log_received.connect(self.update_log_realtime)
        self.comm_server.start()

        self.node_scanner = NodeScanner()
        self.node_scanner.nodes_updated.connect(self.update_target_dropdown)
        self.node_scanner.start()

        self.populate_scripts()

    def create_top_bar(self):
        top_layout = QHBoxLayout()
        
        left_top = QVBoxLayout()
        left_top.addWidget(QLabel("Project"))
        self.target_dropdown = QComboBox()
        self.target_dropdown.addItem("Scanning for Unreal Projects...", None)
        left_top.addWidget(self.target_dropdown)
        
        right_top = QVBoxLayout()
        right_top.addWidget(QLabel("Select Script"))
        self.script_dropdown = QComboBox()
        self.script_dropdown.currentIndexChanged.connect(self.on_script_selected)
        right_top.addWidget(self.script_dropdown)
        
        top_layout.addLayout(left_top)
        top_layout.addLayout(right_top)
        
        return top_layout

    def create_left_panel(self):
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        # left_layout.setSpacing(5)
        # left_layout.setContentsMargins(5, 5, 5, 5)
        
        log_label = QLabel("Execution Log")
        log_label.setMaximumHeight(20)
        left_layout.addWidget(log_label)
        
        # Create a container with no layout (for absolute positioning)
        log_container = QWidget()
        log_container.setMinimumSize(400, 300)
        
        # Add the log widget
        self.log_output_widget = QTextEdit(log_container)
        self.log_output_widget.setReadOnly(True)
        
        # Create logo label with absolute positioning
        self.logo_label = QLabel(log_container)
        logo_path = get_resource_path("logo.png")
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            scaled_pixmap = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            # Create transparent version by modifying alpha channel
            transparent_pixmap = QPixmap(scaled_pixmap.size())
            transparent_pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(transparent_pixmap)
            painter.setOpacity(0.15)  # 25% opacity
            painter.drawPixmap(0, 0, scaled_pixmap)
            painter.end()
            
            self.logo_label.setPixmap(transparent_pixmap)
            self.logo_label.resize(transparent_pixmap.size())
        
        # Make logo not block mouse events
        self.logo_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Position logo at bottom right
        self.logo_label.raise_()
        
        # Connect resize event to reposition logo
        def resize_log_container(event):
            self.log_output_widget.setGeometry(0, 0, log_container.width(), log_container.height())
            # Position logo at bottom right with 10px margin
            logo_x = log_container.width() - self.logo_label.width() - 10
            logo_y = log_container.height() - self.logo_label.height() - 10
            self.logo_label.move(logo_x, logo_y)
        
        log_container.resizeEvent = resize_log_container
        
        left_layout.addWidget(log_container)
        
        return left_widget

    def create_right_panel(self):
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        right_layout.addWidget(QLabel("Script Parameters"))
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        right_layout.addWidget(self.scroll_area)
        
        button_layout = QHBoxLayout()
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.on_pause_clicked)
        self.pause_button.setEnabled(False)
        self.resume_button = QPushButton("Resume")
        self.resume_button.clicked.connect(self.on_resume_clicked)
        self.resume_button.setEnabled(False)
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_automation_script)
        
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.resume_button)
        button_layout.addWidget(self.run_button)
        
        right_layout.addLayout(button_layout)
        
        return right_widget

    def populate_scripts(self):
        self.script_dropdown.clear()
        if not self.scripts_dir.exists():
            self.log_output_widget.setText(f"Error: Scripts directory not found.")
            return
            
        for file_path in self.scripts_dir.glob("*.py"):
            self.script_dropdown.addItem(file_path.name, str(file_path))

    def update_target_dropdown(self, nodes):
        current_selection = self.target_dropdown.currentData()
        self.target_dropdown.clear()
        
        if not nodes:
            self.target_dropdown.addItem("No Unreal instances found", None)
            self.run_button.setEnabled(False)
        else:
            for node in nodes:
                node_id = node.get('node_id', 'Unknown')
                project_name = node.get('project_name', 'Unknown Project')
                engine_version = node.get('engine_version', '')
                
                if engine_version:
                    display_text = f"{project_name} (UE {engine_version})"
                else:
                    display_text = project_name
                
                self.target_dropdown.addItem(display_text, node_id)
            
            if current_selection:
                index = self.target_dropdown.findData(current_selection)
                if index >= 0:
                    self.target_dropdown.setCurrentIndex(index)
            
            self.run_button.setEnabled(True)

    def on_script_selected(self):
        script_path = self.script_dropdown.currentData()
        if not script_path:
            return
        
        manifest = parse_manifest(script_path)
        
        if manifest:
            self.build_dynamic_form(manifest)
        else:
            self.build_fallback_form()

    def clear_form(self):
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.current_inputs.clear()

    def build_dynamic_form(self, manifest):
        self.clear_form()
        
        inputs = manifest.get('inputs', [])
        
        for input_def in inputs:
            name = input_def.get('name', '')
            label = input_def.get('label', name)
            input_type = input_def.get('type', 'string')
            default = input_def.get('default', '')
            
            label_widget = QLabel(label)
            self.scroll_layout.addWidget(label_widget)
            
            if input_type == 'folder_path':
                widget = self.create_folder_input(default)
            elif input_type == 'file_path':
                widget = self.create_file_input(default)
            elif input_type == 'bool':
                widget = self.create_bool_input(default)
            elif input_type == 'float':
                widget = self.create_float_input(default)
            elif input_type == 'int':
                widget = self.create_int_input(default)
            else:
                widget = self.create_string_input(default)
            
            self.scroll_layout.addWidget(widget)
            self.current_inputs[name] = widget
        
        self.scroll_layout.addStretch()

    def build_fallback_form(self):
        self.clear_form()
        
        label_widget = QLabel("Parameters (space-separated)")
        self.scroll_layout.addWidget(label_widget)
        
        line_edit = QLineEdit()
        self.scroll_layout.addWidget(line_edit)
        self.current_inputs['_fallback'] = line_edit
        
        self.scroll_layout.addStretch()

    def create_folder_input(self, default):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        line_edit = QLineEdit(str(default))
        browse_btn = QPushButton("Browse")
        
        def browse():
            folder = QFileDialog.getExistingDirectory(self, "Select Folder", line_edit.text())
            if folder:
                line_edit.setText(folder)
        
        browse_btn.clicked.connect(browse)
        
        layout.addWidget(line_edit)
        layout.addWidget(browse_btn)
        
        container.get_value = lambda: line_edit.text()
        return container

    def create_file_input(self, default):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        line_edit = QLineEdit(str(default))
        browse_btn = QPushButton("Browse")
        
        def browse():
            file_path, _ = QFileDialog.getOpenFileName(self, "Select File", line_edit.text())
            if file_path:
                line_edit.setText(file_path)
        
        browse_btn.clicked.connect(browse)
        
        layout.addWidget(line_edit)
        layout.addWidget(browse_btn)
        
        container.get_value = lambda: line_edit.text()
        return container

    def create_bool_input(self, default):
        checkbox = QCheckBox()
        checkbox.setChecked(bool(default))
        checkbox.get_value = lambda: checkbox.isChecked()
        return checkbox

    def create_float_input(self, default):
        spinbox = QDoubleSpinBox()
        spinbox.setRange(-999999, 999999)
        spinbox.setValue(float(default) if default else 0.0)
        spinbox.get_value = lambda: spinbox.value()
        return spinbox

    def create_int_input(self, default):
        line_edit = QLineEdit(str(default) if default else "0")
        line_edit.get_value = lambda: int(line_edit.text()) if line_edit.text().isdigit() else 0
        return line_edit

    def create_string_input(self, default):
        line_edit = QLineEdit(str(default))
        line_edit.get_value = lambda: line_edit.text()
        return line_edit

    def run_automation_script(self):
        node_id = self.target_dropdown.currentData()
        if not node_id:
            self.log_output_widget.append("ERROR: No target selected.")
            return
        
        script_path = self.script_dropdown.currentData()
        if not script_path:
            self.log_output_widget.append("ERROR: No script selected.")
            return
        
        params_dict = {}
        
        if '_fallback' in self.current_inputs:
            fallback_text = self.current_inputs['_fallback'].text()
            params_dict['_args'] = fallback_text.split()
        else:
            for name, widget in self.current_inputs.items():
                params_dict[name] = widget.get_value()
        
        self.log_output_widget.clear()
        self.log_output_widget.append(f"--- Sending {self.script_dropdown.currentText()} to Unreal ---")
        self.log_output_widget.append(f"Target: {self.target_dropdown.currentText()}")
        self.log_output_widget.append(f"Parameters: {params_dict}")
        
        self.run_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.resume_button.setEnabled(False)

        self.thread = QThread()
        self.worker = Worker(self.scripts_dir / self.script_dropdown.currentText(), node_id, params_dict)
        self.worker.moveToThread(self.thread)
        
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress.connect(self.update_log)
        self.thread.finished.connect(self.on_script_finished)

        self.thread.start()

    def on_pause_clicked(self):
        self.comm_server.send_command("PAUSE")
        self.log_output_widget.append("[CMD]: Sent PAUSE signal...")
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(True)

    def on_resume_clicked(self):
        self.comm_server.send_command("RESUME")
        self.log_output_widget.append("[CMD]: Sent RESUME signal...")
        self.pause_button.setEnabled(True)
        self.resume_button.setEnabled(False)

    def update_log(self, text):
        self.log_output_widget.append(text)
    
    def update_log_realtime(self, text):
        self.log_output_widget.append(f"[Live]: {text}")

    def on_script_finished(self):
        self.log_output_widget.append("--- Execution finished. ---")
        self.run_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
    
    def closeEvent(self, event):
        self.comm_server.stop()
        self.node_scanner.stop()
        super().closeEvent(event)