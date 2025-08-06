"""
PySide6 main window for the Super Image Processor application
Modern Qt-based GUI replacing the original Tkinter interface
"""
import sys
from pathlib import Path
from typing import Optional

try:
    from PySide6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QLabel, QPushButton, QComboBox, QSlider, QSpinBox, QProgressBar,
        QTextEdit, QLineEdit, QFileDialog, QMessageBox, QGroupBox, QFrame,
        QSizePolicy, QApplication
    )
    from PySide6.QtCore import Qt, Signal, QTimer, QThread
    from PySide6.QtGui import QFont, QPalette, QColor, QIcon
except ImportError:
    raise ImportError("PySide6 is required. Install with: pip install PySide6")

from core.utils import CoreConfig, WatermarkConfig, CoreCallbacks, LogLevel
from core.watermark import get_default_watermarks, validate_watermark_file
from gui.worker_thread import WorkerThread


class MainWindow(QMainWindow):
    """
    Main application window with modern PySide6 interface.
    Provides a clean, responsive UI for image processing operations.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Super Processador de Imagens v4.0 - Enhanced Edition")
        self.setMinimumSize(1000, 800)
        self.resize(1200, 900)
        
        # Initialize state
        self.input_folder: Optional[Path] = None
        self.current_worker: Optional[WorkerThread] = None
        self.watermarks = get_default_watermarks()
        
        # Setup UI
        self._setup_ui()
        self._apply_styles()
        self._connect_signals()
        
        # Initialize with first watermark
        self._update_watermark_preview()
    
    def _setup_ui(self):
        """Setup the main user interface layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - horizontal split
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Left panel for controls
        left_panel = self._create_control_panel()
        left_panel.setMaximumWidth(400)
        left_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        
        # Right panel for progress and log
        right_panel = self._create_log_panel()
        right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        # Status bar
        self.statusBar().showMessage("Pronto para processar imagens...")
        
    def _create_control_panel(self) -> QWidget:
        """Create the left control panel with all settings"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        
        # Input folder section
        folder_group = QGroupBox("📁 Configuração de Entrada")
        folder_layout = QVBoxLayout(folder_group)
        
        self.folder_label = QLabel("Nenhuma pasta selecionada")
        self.folder_label.setWordWrap(True)
        self.folder_label.setStyleSheet("color: #666; font-style: italic;")
        
        select_folder_btn = QPushButton("📂 Selecionar Pasta")
        select_folder_btn.clicked.connect(self._select_folder)
        select_folder_btn.setMinimumHeight(40)
        
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(select_folder_btn)
        
        # Direct path input
        direct_path_label = QLabel("Ou digite o caminho diretamente:")
        direct_path_label.setStyleSheet("color: #666; font-size: 10px; margin-top: 10px;")
        self.direct_path_input = QLineEdit()
        self.direct_path_input.setPlaceholderText("D:\caminho\para\pasta...")
        self.direct_path_input.returnPressed.connect(self._on_direct_path_entered)
        self.direct_path_input.setToolTip("Digite o caminho da pasta e pressione Enter")
        
        folder_layout.addWidget(direct_path_label)
        folder_layout.addWidget(self.direct_path_input)
        
        # Watermark settings
        watermark_group = QGroupBox("🖼️ Configurações de Marca d'Água")
        watermark_layout = QGridLayout(watermark_group)
        
        # Watermark selection
        watermark_layout.addWidget(QLabel("Marca d'água:"), 0, 0)
        self.watermark_combo = QComboBox()
        self.watermark_combo.addItems(list(self.watermarks.keys()))
        self.watermark_combo.currentTextChanged.connect(self._on_watermark_changed)
        watermark_layout.addWidget(self.watermark_combo, 0, 1)
        
        # Position
        watermark_layout.addWidget(QLabel("Posição:"), 1, 0)
        self.position_combo = QComboBox()
        positions = [
            "top_left", "top_center", "top_right",
            "center_left", "center", "center_right", 
            "bottom_left", "bottom_center", "bottom_right"
        ]
        self.position_combo.addItems(positions)
        self.position_combo.setCurrentText("top_right")
        watermark_layout.addWidget(self.position_combo, 1, 1)
        
        # Scale slider
        watermark_layout.addWidget(QLabel("Escala:"), 2, 0)
        scale_container = QWidget()
        scale_layout = QHBoxLayout(scale_container)
        scale_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(1, 100)
        self.scale_slider.setValue(35)  # 0.35
        self.scale_label = QLabel("0.35")
        self.scale_slider.valueChanged.connect(lambda v: self.scale_label.setText(f"{v/100:.2f}"))
        
        scale_layout.addWidget(self.scale_slider)
        scale_layout.addWidget(self.scale_label)
        watermark_layout.addWidget(scale_container, 2, 1)
        
        # Opacity slider
        watermark_layout.addWidget(QLabel("Opacidade:"), 3, 0)
        opacity_container = QWidget()
        opacity_layout = QHBoxLayout(opacity_container)
        opacity_layout.setContentsMargins(0, 0, 0, 0)
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(95)  # 0.95
        self.opacity_label = QLabel("0.95")
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_label.setText(f"{v/100:.2f}"))
        
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        watermark_layout.addWidget(opacity_container, 3, 1)
        
        # Margins
        watermark_layout.addWidget(QLabel("Margem X:"), 4, 0)
        self.margin_x_spin = QSpinBox()
        self.margin_x_spin.setRange(0, 500)
        self.margin_x_spin.setValue(20)
        self.margin_x_spin.setSuffix(" px")
        watermark_layout.addWidget(self.margin_x_spin, 4, 1)
        
        watermark_layout.addWidget(QLabel("Margem Y:"), 5, 0)
        self.margin_y_spin = QSpinBox()
        self.margin_y_spin.setRange(0, 500)
        self.margin_y_spin.setValue(20)
        self.margin_y_spin.setSuffix(" px")
        watermark_layout.addWidget(self.margin_y_spin, 5, 1)
        
        # Action buttons
        actions_group = QGroupBox("⚡ Ações Disponíveis")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setSpacing(10)
        
        # Create action buttons with icons and descriptions
        self.extract_btn = QPushButton("📊 Extrair Metadados")
        self.extract_btn.setMinimumHeight(45)
        self.extract_btn.setToolTip("Lê todas as imagens PNG e salva os metadados em arquivos 'metadata.json'.")
        self.extract_btn.clicked.connect(self._extract_metadata)
        
        self.process_btn = QPushButton("🎨 Processar Imagens")
        self.process_btn.setMinimumHeight(45)
        self.process_btn.setToolTip("Aplica marca d'água, recria metadados, gera previews e arquivos ZIP.")
        self.process_btn.clicked.connect(self._process_images)
        
        self.auto_mosaic_btn = QPushButton("🔒 Auto-Mosaico")
        self.auto_mosaic_btn.setMinimumHeight(45)
        self.auto_mosaic_btn.setToolTip("Executa processamento automático de mosaico usando ComfyUI.")
        self.auto_mosaic_btn.clicked.connect(self._auto_mosaic)
        
        self.manual_edit_btn = QPushButton("✏️ Editor Manual")
        self.manual_edit_btn.setMinimumHeight(45)
        self.manual_edit_btn.setToolTip("Abre o editor manual de mosaicos com ferramentas de pincel.")
        self.manual_edit_btn.clicked.connect(self._open_manual_editor)
        
        actions_layout.addWidget(self.extract_btn)
        actions_layout.addWidget(self.process_btn)
        actions_layout.addWidget(self.auto_mosaic_btn)
        actions_layout.addWidget(self.manual_edit_btn)
        
        # Add all groups to panel
        layout.addWidget(folder_group)
        layout.addWidget(watermark_group)
        layout.addWidget(actions_group)
        layout.addStretch()  # Push everything to top
        
        return panel
    
    def _create_log_panel(self) -> QWidget:
        """Create the right panel for progress and logging"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Progress section
        progress_group = QGroupBox("📈 Progresso")
        progress_layout = QVBoxLayout(progress_group)
        
        self.status_label = QLabel("Aguardando ação do usuário...")
        self.status_label.setWordWrap(True)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)
        
        # Log section
        log_group = QGroupBox("📝 Log de Atividades")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        # Note: setMaximumBlockCount is only available on QPlainTextEdit
        
        # Clear log button
        clear_log_btn = QPushButton("🗑️ Limpar Log")
        clear_log_btn.clicked.connect(self.log_text.clear)
        
        log_layout.addWidget(self.log_text)
        log_layout.addWidget(clear_log_btn)
        
        # Add groups to panel
        layout.addWidget(progress_group)
        layout.addWidget(log_group, 1)  # Log takes most space
        
        return panel
    
    def _apply_styles(self):
        """Apply modern styling to the interface"""
        # Main window styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #333;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QComboBox, QSpinBox, QSlider, QLineEdit {
                border: 2px solid #ddd;
                border-radius: 4px;
                padding: 2px;
                background-color: white;
            }
            QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
                border-color: #4CAF50;
            }
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 4px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
            QTextEdit {
                border: 2px solid #ddd;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #4CAF50;
            }
            QLabel {
                color: #333;
            }
        """)
    
    def _connect_signals(self):
        """Connect internal signals and slots"""
        pass  # Additional signal connections can be added here
    
    def _select_folder(self):
        """Open folder selection dialog"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Selecione a pasta de entrada",
            str(Path.home())
        )
        
        if folder:
            self.input_folder = Path(folder)
            self.folder_label.setText(f"📁 {folder}")
            self.folder_label.setStyleSheet("color: #333; font-weight: bold;")
            self._log_message(f"Pasta selecionada: {folder}")
            self._update_button_states()

    
    def _on_direct_path_entered(self):
        """Handle direct path input"""
        path_text = self.direct_path_input.text().strip()
        if not path_text:
            return
            
        try:
            path = Path(path_text)
            if not path.exists():
                QMessageBox.warning(
                    self,
                    "Caminho inválido",
                    f"O caminho especificado não existe:\n{path_text}"
                )
                return
                
            if not path.is_dir():
                QMessageBox.warning(
                    self,
                    "Caminho inválido", 
                    f"O caminho especificado não é uma pasta:\n{path_text}"
                )
                return
                
            # Success - set the folder
            self.input_folder = path
            self.folder_label.setText(f"📁 {path_text}")
            self.folder_label.setStyleSheet("color: #333; font-weight: bold;")
            self._log_message(f"Pasta definida via caminho direto: {path_text}")
            self._update_button_states()
            
            # Clear the input field
            self.direct_path_input.clear()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro ao processar caminho",
                f"Erro ao processar o caminho especificado:\n{str(e)}"
            )
    
    def _update_button_states(self):
        """Update button enabled/disabled states based on current state"""
        has_folder = self.input_folder is not None and self.input_folder.exists()
        is_working = self.current_worker is not None and self.current_worker.isRunning()
        
        # Basic operations require folder selection
        self.extract_btn.setEnabled(has_folder and not is_working)
        self.process_btn.setEnabled(has_folder and not is_working)
        
        if has_folder:
            # Check for original_images in main folder or subfolders
            has_originals = (self.input_folder / "original_images").exists()
            
            if not has_originals:
                # Check subfolders for original_images (multi-pack mode)
                for subfolder in self.input_folder.iterdir():
                    if (subfolder.is_dir() and 
                        not subfolder.name.startswith(('.', 'original_images', 'free_post', 'preview_Images', 'pixiv_safe')) and
                        (subfolder / "original_images").exists()):
                        has_originals = True
                        break
            
            # Check for pixiv_safe in main folder or subfolders  
            has_pixiv_safe = (self.input_folder / "pixiv_safe").exists()
            
            if not has_pixiv_safe:
                # Check subfolders for pixiv_safe (multi-pack mode)
                for subfolder in self.input_folder.iterdir():
                    if (subfolder.is_dir() and 
                        not subfolder.name.startswith(('.', 'original_images', 'free_post', 'preview_Images', 'pixiv_safe')) and
                        (subfolder / "pixiv_safe").exists()):
                        has_pixiv_safe = True
                        break
        else:
            has_originals = False
            has_pixiv_safe = False
        
        # Auto-mosaic requires original_images folder structure
        self.auto_mosaic_btn.setEnabled(has_originals and not is_working)
        
        # Manual editor requires pixiv_safe directory
        self.manual_edit_btn.setEnabled(has_pixiv_safe and not is_working)
    
    def _on_watermark_changed(self, watermark_name: str):
        """Handle watermark selection change"""
        self._update_watermark_preview()
        self._log_message(f"Marca d'água alterada para: {watermark_name}")
    
    def _update_watermark_preview(self):
        """Update watermark preview/validation"""
        current_watermark = self.watermark_combo.currentText()
        if current_watermark in self.watermarks:
            watermark_path = self.watermarks[current_watermark]
            if validate_watermark_file(watermark_path):
                self.watermark_combo.setStyleSheet("border-color: #4CAF50;")
                self.watermark_combo.setToolTip(f"✅ Arquivo válido: {watermark_path}")
            else:
                self.watermark_combo.setStyleSheet("border-color: #f44336;")
                self.watermark_combo.setToolTip(f"❌ Arquivo não encontrado: {watermark_path}")
    
    def _create_core_config(self) -> CoreConfig:
        """Create CoreConfig from current UI settings"""
        watermark_config = WatermarkConfig(
            name=self.watermark_combo.currentText(),
            path=self.watermarks[self.watermark_combo.currentText()],
            position=self.position_combo.currentText(),
            opacity=self.opacity_slider.value() / 100.0,
            scale=self.scale_slider.value() / 100.0,
            margin_x=self.margin_x_spin.value(),
            margin_y=self.margin_y_spin.value()
        )
        
        return CoreConfig(
            input_folder=self.input_folder,
            watermark=watermark_config,
            max_workers=8,
            timeout_seconds=180
        )
    
    def _create_callbacks(self) -> CoreCallbacks:
        """Create CoreCallbacks for communicating with worker threads"""
        return CoreCallbacks(
            progress=self._update_progress,
            log=self._log_message,
            status=self._update_status
        )
    
    def _extract_metadata(self):
        """Start metadata extraction in worker thread"""
        if not self._validate_input():
            return
        
        config = self._create_core_config()
        callbacks = self._create_callbacks()
        
        self.current_worker = WorkerThread("extract_metadata", config, callbacks)
        self.current_worker.finished.connect(self._on_task_finished)
        self.current_worker.success.connect(lambda: self._show_completion_message("Extração de metadados"))
        self.current_worker.error.connect(self._show_error_message)
        
        self.current_worker.start()
        self._update_button_states()
    
    def _process_images(self):
        """Start image processing in worker thread"""
        if not self._validate_input():
            return
        
        config = self._create_core_config()
        callbacks = self._create_callbacks()
        
        self.current_worker = WorkerThread("process_images", config, callbacks)
        self.current_worker.finished.connect(self._on_task_finished)
        self.current_worker.success.connect(lambda: self._show_completion_message("Processamento de imagens"))
        self.current_worker.error.connect(self._show_error_message)
        
        self.current_worker.start()
        self._update_button_states()
    
    def _auto_mosaic(self):
        """Start auto-mosaic processing in worker thread"""
        if not self._validate_input():
            return
        
        # Check for original_images directory
        original_images_dir = self.input_folder / "original_images"
        if not original_images_dir.exists():
            QMessageBox.warning(
                self,
                "Pasta não encontrada",
                f"A pasta 'original_images' não foi encontrada em:\n{self.input_folder}\n\n"
                "Execute primeiro a extração de metadados e processamento de imagens."
            )
            return
        
        config = self._create_core_config()
        callbacks = self._create_callbacks()
        
        self.current_worker = WorkerThread("auto_mosaic", config, callbacks)
        self.current_worker.finished.connect(self._on_task_finished)
        self.current_worker.success.connect(lambda: self._show_completion_message("Auto-mosaico"))
        self.current_worker.error.connect(self._show_error_message)
        
        self.current_worker.start()
        self._update_button_states()
    
    def _open_manual_editor(self):
        """Open the manual mosaic editor"""
        if not self.input_folder or not (self.input_folder / "pixiv_safe").exists():
            QMessageBox.warning(
                self,
                "Pasta não encontrada",
                "A pasta 'pixiv_safe' não foi encontrada.\n\n"
                "Execute primeiro o processamento auto-mosaico."
            )
            return
        
        try:
            from gui.manual_editor import open_manual_editor
            pixiv_safe_dir = self.input_folder / "pixiv_safe"
            self.manual_editor = open_manual_editor(pixiv_safe_dir, self)
            self._log_message(f"Editor manual aberto para: {pixiv_safe_dir}")
        except Exception as e:
            self._log_message(f"Erro ao abrir editor manual: {e}", "ERROR")
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao abrir o editor manual:\n{str(e)}"
            )
    
    def _validate_input(self) -> bool:
        """Validate current input settings"""
        # Debug logging
        self._log_message(f"Validating input folder: {self.input_folder}", "INFO")
        
        if not self.input_folder:
            QMessageBox.warning(
                self,
                "Pasta não selecionada",
                "Por favor, selecione uma pasta de entrada válida."
            )
            return False
            
        if not self.input_folder.exists():
            QMessageBox.warning(
                self,
                "Pasta não encontrada",
                f"A pasta especificada não existe:\n{self.input_folder}"
            )
            return False
        
        # Validate watermark
        current_watermark = self.watermark_combo.currentText()
        if current_watermark not in self.watermarks:
            QMessageBox.warning(
                self,
                "Marca d'água inválida",
                f"Marca d'água '{current_watermark}' não encontrada."
            )
            return False
        
        watermark_path = self.watermarks[current_watermark]
        if not validate_watermark_file(watermark_path):
            QMessageBox.warning(
                self,
                "Arquivo de marca d'água não encontrado",
                f"O arquivo de marca d'água não foi encontrado:\n{watermark_path}\n\n"
                "Verifique se o arquivo existe no caminho especificado."
            )
            return False
        
        return True
    
    def _update_progress(self, value: int):
        """Update progress bar (called from worker thread)"""
        self.progress_bar.setValue(max(0, min(100, value)))
    
    def _update_status(self, message: str):
        """Update status label (called from worker thread)"""
        self.status_label.setText(message)
        self.statusBar().showMessage(message)
    
    def _log_message(self, message: str, level: str = "INFO"):
        """Add message to log with timestamp and color coding"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color coding based on level
        color_map = {
            "INFO": "#000000",
            "SUCCESS": "#4CAF50", 
            "WARN": "#FF9800",
            "ERROR": "#f44336",
            "FATAL": "#9C27B0"
        }
        
        color = color_map.get(level, "#000000")
        formatted_message = f'<span style="color: {color};">[{timestamp}] [{level}] {message}</span>'
        
        self.log_text.append(formatted_message)
    
    def _on_task_finished(self):
        """Handle task completion"""
        self.current_worker = None
        self._update_button_states()
        self._update_progress(0)
    
    def _show_completion_message(self, task_name: str):
        """Show task completion message"""
        QMessageBox.information(
            self,
            "Tarefa Concluída",
            f"{task_name} concluído com sucesso!"
        )
    
    def _show_error_message(self, error_message: str):
        """Show error message"""
        QMessageBox.critical(
            self,
            "Erro na Operação",
            f"Ocorreu um erro durante a operação:\n\n{error_message}"
        )
    
    def closeEvent(self, event):
        """Handle application close"""
        if self.current_worker and self.current_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Operação em Andamento",
                "Existe uma operação em andamento. Deseja realmente fechar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            # Force terminate worker if running
            if self.current_worker.isRunning():
                self.current_worker.terminate()
                self.current_worker.wait(3000)  # Wait up to 3 seconds
        
        event.accept()


def create_application() -> QApplication:
    """Create and configure the QApplication"""
    app = QApplication(sys.argv)
    app.setApplicationName("Super Processador de Imagens")
    app.setApplicationVersion("4.0")
    app.setOrganizationName("ArakisProject")
    
    # Set application icon if available
    icon_path = Path(__file__).parent.parent / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    return app