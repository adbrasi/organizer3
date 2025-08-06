"""
Manual Mosaic Editor - Advanced brush-based editing for images
Future implementation of interactive mosaic editing tools
"""
from pathlib import Path
from typing import Optional, List, Tuple

try:
    from PySide6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
        QListWidget, QListWidgetItem, QGraphicsView, QGraphicsScene,
        QGraphicsPixmapItem, QToolBar, QSlider, QComboBox, QPushButton,
        QLabel, QGroupBox, QMessageBox
    )
    from PySide6.QtCore import Qt, QRectF, Signal
    from PySide6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QImage
except ImportError:
    raise ImportError("PySide6 is required. Install with: pip install PySide6")

try:
    import cv2
    import numpy as np
    from PIL import Image
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class MosaicCanvas(QGraphicsPixmapItem):
    """
    Custom graphics item for interactive image editing with brush tools.
    Supports blur, pixelate, and other mosaic effects.
    """
    
    def __init__(self, pixmap: QPixmap):
        super().__init__(pixmap)
        self.setFlags(QGraphicsPixmapItem.ItemIsSelectable | QGraphicsPixmapItem.ItemIsFocusable)
        
        # Brush settings
        self.brush_size = 20
        self.brush_strength = 5
        self.brush_mode = "blur"  # "blur", "pixelate", "erase"
        
        # Drawing state
        self.is_drawing = False
        self.last_point = None
        
        # Store original image for undo operations
        self.original_pixmap = pixmap.copy()
        self.edit_history: List[QPixmap] = [pixmap.copy()]
    
    def set_brush_size(self, size: int):
        """Set brush size"""
        self.brush_size = max(1, min(100, size))
    
    def set_brush_strength(self, strength: int):
        """Set brush effect strength"""
        self.brush_strength = max(1, min(10, strength))
    
    def set_brush_mode(self, mode: str):
        """Set brush mode (blur, pixelate, erase)"""
        if mode in ["blur", "pixelate", "erase"]:
            self.brush_mode = mode
    
    def mousePressEvent(self, event):
        """Start drawing operation"""
        if event.button() == Qt.LeftButton:
            self.is_drawing = True
            self.last_point = event.pos()
            self._save_state()  # Save state for undo
            self._apply_brush_effect(event.pos())
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Continue drawing operation"""
        if self.is_drawing and event.buttons() == Qt.LeftButton:
            self._apply_brush_effect(event.pos())
            self.last_point = event.pos()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """End drawing operation"""
        if event.button() == Qt.LeftButton:
            self.is_drawing = False
            self.last_point = None
        super().mouseReleaseEvent(event)
    
    def _save_state(self):
        """Save current state for undo functionality"""
        self.edit_history.append(self.pixmap().copy())
        # Keep only last 10 states to manage memory
        if len(self.edit_history) > 10:
            self.edit_history.pop(0)
    
    def _apply_brush_effect(self, pos):
        """Apply the selected brush effect at the given position"""
        try:
            # Get current pixmap and convert to PIL Image for processing
            current_pixmap = self.pixmap()
            qimage = current_pixmap.toImage()
            
            # Convert to RGBA format for consistent processing
            if qimage.format() != QImage.Format_RGBA8888:
                qimage = qimage.convertToFormat(QImage.Format_RGBA8888)
            
            width, height = qimage.width(), qimage.height()
            
            # Extract raw bytes from QImage
            ptr = qimage.bits()
            bytes_data = ptr.tobytes()
            
            # Create PIL Image directly from bytes
            from PIL import Image as PILImage
            pil_image = PILImage.frombytes('RGBA', (width, height), bytes_data)
            
            # Convert to RGB for processing (remove alpha channel temporarily)
            rgb_image = PILImage.new('RGB', pil_image.size, (255, 255, 255))
            rgb_image.paste(pil_image, mask=pil_image.split()[3])  # Use alpha as mask
            
            # Calculate brush area
            x, y = int(pos.x()), int(pos.y())
            r = self.brush_size // 2
            
            # Ensure coordinates are within image bounds
            x1, y1 = max(0, x - r), max(0, y - r)
            x2, y2 = min(width, x + r), min(height, y + r)
            
            if x2 <= x1 or y2 <= y1:
                return
            
            # Extract region for processing
            region = rgb_image.crop((x1, y1, x2, y2))
            
            # Apply effect based on mode
            if self.brush_mode == "blur":
                # Use PIL's built-in blur filter
                from PIL import ImageFilter
                blur_radius = max(1, self.brush_strength)
                region = region.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                
            elif self.brush_mode == "pixelate":
                # Apply pixelate effect using resize method
                scale_factor = max(2, self.brush_strength * 2)
                region_w, region_h = region.size
                
                # Downsample to create pixelated effect
                small_w = max(1, region_w // scale_factor)
                small_h = max(1, region_h // scale_factor)
                
                # Create pixelated version
                small_region = region.resize((small_w, small_h), PILImage.Resampling.BILINEAR)
                region = small_region.resize((region_w, region_h), PILImage.Resampling.NEAREST)
                
            elif self.brush_mode == "erase":
                # Restore original image in this region
                orig_qimage = self.original_pixmap.toImage()
                if orig_qimage.format() != QImage.Format_RGBA8888:
                    orig_qimage = orig_qimage.convertToFormat(QImage.Format_RGBA8888)
                
                orig_ptr = orig_qimage.bits()
                orig_bytes = orig_ptr.tobytes()
                orig_pil = PILImage.frombytes('RGBA', (width, height), orig_bytes)
                orig_rgb = PILImage.new('RGB', orig_pil.size, (255, 255, 255))
                orig_rgb.paste(orig_pil, mask=orig_pil.split()[3])
                
                region = orig_rgb.crop((x1, y1, x2, y2))
            
            # Paste the processed region back
            rgb_image.paste(region, (x1, y1))
            
            # Convert back to RGBA
            result_rgba = rgb_image.convert('RGBA')
            
            # Convert back to QPixmap
            qpixmap = self._pil_to_qpixmap(result_rgba)
            self.setPixmap(qpixmap)
            
            # Trigger auto-save callback if available
            if hasattr(self, 'auto_save_callback') and self.auto_save_callback:
                self.auto_save_callback()
            
        except Exception as e:
            print(f"Error applying brush effect: {e}")
            # Fallback to simple effect if there's any error
            self._apply_simple_effect(pos)
    
    def _apply_simple_effect(self, pos):
        """Simple fallback effect using pure Qt operations"""
        try:
            pixmap = self.pixmap()
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing, True)
            
            # Calculate brush area
            x, y = int(pos.x()), int(pos.y())
            r = self.brush_size // 2
            
            if self.brush_mode == "blur":
                # Simple darkening/lightening effect as blur simulation
                painter.setCompositionMode(QPainter.CompositionMode_Multiply)
                brush = QBrush(QColor(200, 200, 200, 30))  # Light gray, semi-transparent
                painter.setBrush(brush)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(x - r, y - r, self.brush_size, self.brush_size)
                
            elif self.brush_mode == "pixelate":
                # Draw pixelated squares by sampling and drawing blocks
                painter.setPen(Qt.NoPen)
                pixel_size = max(4, self.brush_strength * 2)
                
                # Create a mask for the circular brush area
                for px in range(x - r, x + r, pixel_size):
                    for py in range(y - r, y + r, pixel_size):
                        # Check if within circular brush area
                        if (px - x) ** 2 + (py - y) ** 2 <= r ** 2:
                            # Sample color from the center of the pixel block
                            sample_x = min(max(px + pixel_size//2, 0), pixmap.width()-1)
                            sample_y = min(max(py + pixel_size//2, 0), pixmap.height()-1)
                            
                            # Get color from current pixmap
                            sample_color = pixmap.toImage().pixelColor(sample_x, sample_y)
                            painter.setBrush(QBrush(sample_color))
                            painter.drawRect(px, py, pixel_size, pixel_size)
                            
            elif self.brush_mode == "erase":
                # Restore from original using composition mode
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                
                # Draw circular area from original image
                source_rect = QRect(x - r, y - r, self.brush_size, self.brush_size)
                target_rect = QRect(x - r, y - r, self.brush_size, self.brush_size)
                
                # Create circular mask
                mask = QPixmap(self.brush_size, self.brush_size)
                mask.fill(Qt.transparent)
                
                mask_painter = QPainter(mask)
                mask_painter.setRenderHint(QPainter.Antialiasing, True)
                mask_painter.setBrush(Qt.white)
                mask_painter.setPen(Qt.NoPen)
                mask_painter.drawEllipse(0, 0, self.brush_size, self.brush_size)
                mask_painter.end()
                
                # Apply the original image through the mask
                temp_pixmap = QPixmap(self.brush_size, self.brush_size)
                temp_painter = QPainter(temp_pixmap)
                temp_painter.drawPixmap(0, 0, self.original_pixmap, source_rect)
                temp_painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
                temp_painter.drawPixmap(0, 0, mask)
                temp_painter.end()
                
                painter.drawPixmap(target_rect, temp_pixmap)
                
            painter.end()
            self.setPixmap(pixmap)
            
        except Exception as e:
            print(f"Error in simple effect: {e}")
            # Ultimate fallback - just draw a circle
            pixmap = self.pixmap()
            painter = QPainter(pixmap)
            painter.setBrush(QBrush(QColor(128, 128, 128, 50)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(pos.x() - self.brush_size//2), 
                               int(pos.y() - self.brush_size//2),
                               self.brush_size, self.brush_size)
            painter.end()
            self.setPixmap(pixmap)
    
    def _pil_to_qpixmap(self, pil_image):
        """Convert PIL Image to QPixmap safely"""
        try:
            # Ensure image is in RGBA format
            if pil_image.mode != 'RGBA':
                pil_image = pil_image.convert('RGBA')
            
            # Get image data
            w, h = pil_image.size
            img_data = pil_image.tobytes()
            
            # Create QImage from bytes
            qimg = QImage(img_data, w, h, QImage.Format_RGBA8888)
            
            # Convert to QPixmap
            return QPixmap.fromImage(qimg)
            
        except Exception as e:
            print(f"Error converting PIL to QPixmap: {e}")
            # Return a black pixmap as fallback
            fallback = QPixmap(pil_image.size[0] if pil_image else 100, 
                             pil_image.size[1] if pil_image else 100)
            fallback.fill(Qt.black)
            return fallback
    
    def undo(self):
        """Undo last operation"""
        if len(self.edit_history) > 1:
            self.edit_history.pop()  # Remove current state
            self.setPixmap(self.edit_history[-1])  # Restore previous state
    
    def reset(self):
        """Reset to original image"""
        self.setPixmap(self.original_pixmap)
        self.edit_history = [self.original_pixmap.copy()]


class ManualMosaicEditor(QMainWindow):
    """
    Manual mosaic editor window with brush tools and image list.
    Allows fine-grained control over mosaic application.
    """
    
    def __init__(self, images_dir: Path, parent=None):
        super().__init__(parent)
        self.images_dir = images_dir
        self.current_canvas: Optional[MosaicCanvas] = None
        self.current_file_path: Optional[Path] = None
        
        # Create temp directory for storing work in progress
        self.temp_dir = images_dir / ".temp_edits"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Track modified images
        self.modified_images = set()
        
        self.setWindowTitle(f"Editor Manual de Mosaicos - {images_dir.name}")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        self._setup_ui()
        self._load_images()
        
        if not CV2_AVAILABLE:
            QMessageBox.warning(
                self,
                "Recursos Limitados",
                "OpenCV não está instalado. Algumas funcionalidades de edição "
                "serão limitadas.\n\nInstale com: pip install opencv-python"
            )
    
    def _setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - splitter
        splitter = QSplitter(Qt.Horizontal)
        central_widget.setLayout(QHBoxLayout())
        central_widget.layout().addWidget(splitter)
        
        # Left panel - image list and tools
        left_panel = self._create_left_panel()
        left_panel.setMaximumWidth(350)
        
        # Right panel - canvas
        right_panel = self._create_canvas_panel()
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 1050])
        
        # Toolbar
        self._create_toolbar()
        
        # Status bar
        self.statusBar().showMessage("Selecione uma imagem para começar a editar")
    
    def _create_left_panel(self) -> QWidget:
        """Create left panel with image list and brush tools"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Image list
        images_group = QGroupBox("📁 Imagens")
        images_layout = QVBoxLayout(images_group)
        
        self.image_list = QListWidget()
        self.image_list.itemClicked.connect(self._on_image_selected)
        images_layout.addWidget(self.image_list)
        
        # Brush tools
        tools_group = QGroupBox("🖌️ Ferramentas de Pincel")
        tools_layout = QVBoxLayout(tools_group)
        
        # Brush mode
        tools_layout.addWidget(QLabel("Modo:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["blur", "pixelate", "erase"])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        tools_layout.addWidget(self.mode_combo)
        
        # Brush size
        tools_layout.addWidget(QLabel("Tamanho:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(5, 100)
        self.size_slider.setValue(20)
        self.size_slider.valueChanged.connect(self._on_size_changed)
        
        size_layout = QHBoxLayout()
        size_layout.addWidget(self.size_slider)
        self.size_label = QLabel("20")
        size_layout.addWidget(self.size_label)
        tools_layout.addLayout(size_layout)
        
        # Brush strength
        tools_layout.addWidget(QLabel("Intensidade:"))
        self.strength_slider = QSlider(Qt.Horizontal)
        self.strength_slider.setRange(1, 10)
        self.strength_slider.setValue(5)
        self.strength_slider.valueChanged.connect(self._on_strength_changed)
        
        strength_layout = QHBoxLayout()
        strength_layout.addWidget(self.strength_slider)
        self.strength_label = QLabel("5")
        strength_layout.addWidget(self.strength_label)
        tools_layout.addLayout(strength_layout)
        
        # Action buttons
        actions_layout = QVBoxLayout()
        
        undo_btn = QPushButton("↶ Desfazer")
        undo_btn.clicked.connect(self._undo)
        
        reset_btn = QPushButton("🔄 Resetar")
        reset_btn.clicked.connect(self._reset)
        
        save_btn = QPushButton("💾 Salvar")
        save_btn.clicked.connect(self._save_current)
        
        actions_layout.addWidget(undo_btn)
        actions_layout.addWidget(reset_btn)
        actions_layout.addWidget(save_btn)
        
        tools_layout.addLayout(actions_layout)
        
        # Add groups to panel
        layout.addWidget(images_group, 1)
        layout.addWidget(tools_group)
        
        return panel
    
    def _create_canvas_panel(self) -> QWidget:
        """Create canvas panel for image editing"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Graphics view for canvas
        self.graphics_view = QGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        
        layout.addWidget(self.graphics_view)
        
        return panel
    
    def _create_toolbar(self):
        """Create application toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Add common actions to toolbar
        toolbar.addAction("📂 Abrir Pasta", self._open_folder)
        toolbar.addSeparator()
        toolbar.addAction("💾 Salvar Todas", self._save_all)
        toolbar.addAction("🚪 Fechar", self.close)
    
    def _load_images(self):
        """Load images from directory"""
        if not self.images_dir.exists():
            return
        
        image_extensions = {'.png', '.jpg', '.jpeg', '.webp'}
        for file_path in self.images_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                item = QListWidgetItem(file_path.name)
                item.setData(Qt.UserRole, file_path)
                self.image_list.addItem(item)
        
        self.statusBar().showMessage(f"Carregadas {self.image_list.count()} imagens")
    
    def _on_image_selected(self, item: QListWidgetItem):
        """Handle image selection"""
        file_path = item.data(Qt.UserRole)
        if not file_path or not file_path.exists():
            return
        
        # Save current work before switching
        if self.current_canvas and self.current_file_path:
            self._auto_save_current()
        
        try:
            # Check if there's a temp version (work in progress)
            temp_file = self.temp_dir / file_path.name
            
            # Load image - prefer temp version if it exists
            if temp_file.exists():
                pixmap = QPixmap(str(temp_file))
                self.statusBar().showMessage(f"Carregada versão editada: {file_path.name}")
            else:
                pixmap = QPixmap(str(file_path))
                self.statusBar().showMessage(f"Carregada versão original: {file_path.name}")
            
            if pixmap.isNull():
                QMessageBox.warning(self, "Erro", f"Não foi possível carregar a imagem: {file_path.name}")
                return
            
            # Clear previous canvas
            self.graphics_scene.clear()
            
            # Create new canvas
            self.current_canvas = MosaicCanvas(pixmap)
            self.current_file_path = file_path
            
            # Set auto-save callback
            self.current_canvas.auto_save_callback = self._auto_save_current
            
            self.graphics_scene.addItem(self.current_canvas)
            
            # Fit image in view
            self.graphics_view.fitInView(self.current_canvas, Qt.KeepAspectRatio)
            
            # Update tool settings
            self._update_canvas_settings()
            
            # Update UI to show if image has been modified
            if file_path.name in self.modified_images:
                item.setText(f"* {file_path.name}")  # Add asterisk for modified
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar imagem: {str(e)}")

    
    def _auto_save_current(self):
        """Auto-save current image to temp directory"""
        if not self.current_canvas or not self.current_file_path:
            return
        
        try:
            # Save to temp directory
            temp_file = self.temp_dir / self.current_file_path.name
            pixmap = self.current_canvas.pixmap()
            success = pixmap.save(str(temp_file))
            
            if success:
                # Mark as modified
                self.modified_images.add(self.current_file_path.name)
                
                # Update list item to show modification
                for i in range(self.image_list.count()):
                    item = self.image_list.item(i)
                    item_path = item.data(Qt.UserRole)
                    if item_path == self.current_file_path:
                        if not item.text().startswith("* "):
                            item.setText(f"* {self.current_file_path.name}")
                        break
                
                # Update status
                self.statusBar().showMessage(f"Auto-salvo: {self.current_file_path.name}")
            
        except Exception as e:
            print(f"Auto-save error: {e}")
    
    def _get_temp_file_path(self, original_path: Path) -> Path:
        """Get the temp file path for an original image path"""
        return self.temp_dir / original_path.name
    
    def _update_canvas_settings(self):
        """Update canvas with current tool settings"""
        if self.current_canvas:
            self.current_canvas.set_brush_size(self.size_slider.value())
            self.current_canvas.set_brush_strength(self.strength_slider.value())
            self.current_canvas.set_brush_mode(self.mode_combo.currentText())
    
    def _on_mode_changed(self, mode: str):
        """Handle brush mode change"""
        if self.current_canvas:
            self.current_canvas.set_brush_mode(mode)
        self.statusBar().showMessage(f"Modo alterado para: {mode}")
    
    def _on_size_changed(self, size: int):
        """Handle brush size change"""
        self.size_label.setText(str(size))
        if self.current_canvas:
            self.current_canvas.set_brush_size(size)
    
    def _on_strength_changed(self, strength: int):
        """Handle brush strength change"""
        self.strength_label.setText(str(strength))
        if self.current_canvas:
            self.current_canvas.set_brush_strength(strength)
    
    def _undo(self):
        """Undo last edit operation"""
        if self.current_canvas:
            self.current_canvas.undo()
            self.statusBar().showMessage("Operação desfeita")
    
    def _reset(self):
        """Reset current image to original"""
        if self.current_canvas:
            self.current_canvas.reset()
            self.statusBar().showMessage("Imagem restaurada ao original")
    
    def _save_current(self):
        """Save current edited image"""
        if not self.current_canvas:
            QMessageBox.warning(self, "Aviso", "Nenhuma imagem selecionada para salvar.")
            return
        
        try:
            # Get current selected item
            current_item = self.image_list.currentItem()
            if not current_item:
                return
            
            file_path = current_item.data(Qt.UserRole)
            pixmap = self.current_canvas.pixmap()
            
            # Save pixmap
            success = pixmap.save(str(file_path))
            if success:
                self.statusBar().showMessage(f"Imagem salva: {file_path.name}")
                QMessageBox.information(self, "Sucesso", f"Imagem salva com sucesso:\n{file_path.name}")
            else:
                QMessageBox.warning(self, "Erro", "Falha ao salvar a imagem.")
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar imagem: {str(e)}")
    
    def _save_all(self):
        """Save all edited images from temp storage to original locations"""
        if not self.modified_images:
            QMessageBox.information(
                self,
                "Nenhuma Modificação",
                "Não há imagens modificadas para salvar."
            )
            return
        
        # Confirm the operation
        reply = QMessageBox.question(
            self,
            "Confirmar Salvamento",
            f"Salvar {len(self.modified_images)} imagens modificadas?\n\n"
            "Esta ação sobrescreverá os arquivos originais.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            saved_count = 0
            failed_count = 0
            
            # Save each modified image
            for image_name in self.modified_images.copy():
                temp_file = self.temp_dir / image_name
                
                if not temp_file.exists():
                    print(f"Warning: Temp file not found for {image_name}")
                    continue
                
                # Find original file path
                original_file = None
                for i in range(self.image_list.count()):
                    item = self.image_list.item(i)
                    item_path = item.data(Qt.UserRole)
                    if item_path.name == image_name:
                        original_file = item_path
                        break
                
                if not original_file:
                    print(f"Warning: Original file not found for {image_name}")
                    failed_count += 1
                    continue
                
                try:
                    # Load from temp and save to original location
                    pixmap = QPixmap(str(temp_file))
                    if pixmap.isNull():
                        print(f"Error: Could not load temp image {image_name}")
                        failed_count += 1
                        continue
                    
                    success = pixmap.save(str(original_file))
                    if success:
                        saved_count += 1
                        # Remove asterisk from item text
                        for i in range(self.image_list.count()):
                            item = self.image_list.item(i)
                            if item.data(Qt.UserRole) == original_file:
                                item.setText(image_name)
                                break
                    else:
                        failed_count += 1
                        print(f"Error: Failed to save {image_name}")
                        
                except Exception as e:
                    print(f"Error saving {image_name}: {e}")
                    failed_count += 1
            
            # Clear modified list for successfully saved images
            if saved_count > 0:
                self.modified_images.clear()
            
            # Show results
            if failed_count == 0:
                QMessageBox.information(
                    self,
                    "Salvamento Concluído",
                    f"Todas as {saved_count} imagens foram salvas com sucesso!"
                )
                self.statusBar().showMessage(f"Salvamento concluído: {saved_count} imagens salvas")
            else:
                QMessageBox.warning(
                    self,
                    "Salvamento Parcial",
                    f"Salvamento concluído:\n"
                    f"• {saved_count} imagens salvas com sucesso\n"
                    f"• {failed_count} falhas"
                )
                self.statusBar().showMessage(f"Salvamento parcial: {saved_count} sucessos, {failed_count} falhas")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro no Salvamento",
                f"Erro durante o salvamento:\n{str(e)}"
            )
    
    def _open_folder(self):
        """Open new folder (future feature)"""
        QMessageBox.information(
            self,
            "Em Desenvolvimento", 
            "A funcionalidade 'Abrir Pasta' será implementada em breve!"
        )
    
    def _cleanup_temp_directory(self):
        """Clean up temporary files"""
        try:
            if self.temp_dir.exists():
                for temp_file in self.temp_dir.glob("*"):
                    if temp_file.is_file():
                        temp_file.unlink()
                # Remove temp directory if empty
                try:
                    self.temp_dir.rmdir()
                except OSError:
                    pass  # Directory not empty - leave it
        except Exception as e:
            print(f"Warning: Could not clean temp directory: {e}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Check if there are unsaved changes
        if self.modified_images:
            reply = QMessageBox.question(
                self,
                "Alterações Não Salvas",
                f"Existem {len(self.modified_images)} imagens com alterações não salvas.\n\n"
                "Deseja salvar todas antes de fechar?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Cancel:
                event.ignore()
                return
            elif reply == QMessageBox.Yes:
                # Save all changes
                self._save_all()
        
        # Clean up temp files
        self._cleanup_temp_directory()
        
        event.accept()


def open_manual_editor(images_dir: Path, parent=None) -> ManualMosaicEditor:
    """
    Factory function to create and show manual mosaic editor.
    
    Args:
        images_dir: Directory containing images to edit
        parent: Parent widget
        
    Returns:
        ManualMosaicEditor instance
    """
    editor = ManualMosaicEditor(images_dir, parent)
    editor.show()
    return editor