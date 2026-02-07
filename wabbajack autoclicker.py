import sys
import os
import time
import socket
import psutil
import pyautogui
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QComboBox, QPushButton, 
                               QDoubleSpinBox, QTextEdit, QFileDialog, QGroupBox,
                               QFormLayout)
from PySide6.QtCore import QThread, Signal, Qt, QRect, QPoint
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QGuiApplication, QIcon

class Snipper(QWidget):
    """
    A transparent overlay widget to capture a screen region.
    """
    signal_image_captured = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setCursor(Qt.CrossCursor)
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_selecting = False
        
        # Grab the screen content to display
        screen = QGuiApplication.primaryScreen()
        self.original_pixmap = screen.grabWindow(0)
        self.setGeometry(0, 0, self.original_pixmap.width(), self.original_pixmap.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.original_pixmap)
        
        # Draw a dim overlay
        painter.setBrush(QColor(0, 0, 0, 100))
        painter.drawRect(self.rect())

        if self.is_selecting or self.start_point != self.end_point:
            # Clear the dim overlay for the selection
            selection_rect = QRect(self.start_point, self.end_point).normalized()
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(Qt.red, 2))
            painter.drawRect(selection_rect)
            
            # Redraw the original pixmap inside the selection to make it look "clear"
            painter.drawPixmap(selection_rect, self.original_pixmap, selection_rect)

    def mousePressEvent(self, event):
        self.start_point = event.position().toPoint()
        self.end_point = event.position().toPoint()
        self.is_selecting = True
        self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end_point = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        self.is_selecting = False
        self.end_point = event.position().toPoint()
        self.capture_image()
        self.close()

    def capture_image(self):
        rect = QRect(self.start_point, self.end_point).normalized()
        if rect.width() > 0 and rect.height() > 0:
            cropped = self.original_pixmap.copy(rect)
            filename = "slow download button.png"
            cropped.save(filename)
            self.signal_image_captured.emit(os.path.abspath(filename))

class Worker(QThread):
    """
    Worker thread to handle the monitoring and clicking loop.
    """
    log_signal = Signal(str)
    speed_signal = Signal(float)
    
    def __init__(self, interface, image_path, speed_limit, sleep_time):
        super().__init__()
        self.interface = interface
        self.image_path = image_path
        self.speed_limit = speed_limit
        self.sleep_time = sleep_time
        self.running = True

    def measure_network_download_rate(self):
        try:
            net_stat = psutil.net_io_counters(pernic=True, nowrap=True)[self.interface]
            net_in_1 = net_stat.bytes_recv
            time.sleep(1)
            net_stat = psutil.net_io_counters(pernic=True, nowrap=True)[self.interface]
            net_in_2 = net_stat.bytes_recv
            net_in = round((net_in_2 - net_in_1) / 1024 / 1024, 3)
            return net_in
        except Exception as e:
            self.log_signal.emit(f"Error reading network stats: {e}")
            return 0.0

    def click_on_image(self):
        try:
            buttonloc = pyautogui.locateOnScreen(self.image_path, confidence=0.8)
            if buttonloc is None:
                self.log_signal.emit("Download button not found.")
            else:
                center = pyautogui.center(buttonloc)
                oldpos = pyautogui.position()
                self.log_signal.emit(f"Clicking button at [{center[0]}, {center[1]}].")
                pyautogui.click(x=center[0], y=center[1])
                pyautogui.moveTo(oldpos)
        except Exception as e:
            self.log_signal.emit(f"Error searching for image: {e}")

    def run(self):
        self.log_signal.emit(f"Started monitoring on {self.interface}...")
        while self.running:
            net_in = self.measure_network_download_rate()
            self.speed_signal.emit(net_in)

            if net_in < self.speed_limit:
                self.log_signal.emit(f"Speed ({net_in} MB/s) < Limit ({self.speed_limit} MB/s). Searching...")
                self.click_on_image()
                # Sleep for the configured time
                for _ in range(int(self.sleep_time * 10)):
                    if not self.running: break
                    time.sleep(0.1)
            else:
                # Short sleep if downloading fast
                time.sleep(0.5)
        
        self.log_signal.emit("Stopped monitoring.")

    def stop(self):
        self.running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wabbajack Autoclicker UI")
        if os.path.exists("icon.png"):
            self.setWindowIcon(QIcon("icon.png"))
        self.resize(500, 500)
        
        self.worker = None
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Network Selection
        net_group = QGroupBox("Network Interface")
        net_layout = QVBoxLayout()
        self.combo_network = QComboBox()
        self.populate_networks()
        net_layout.addWidget(self.combo_network)
        net_group.setLayout(net_layout)
        layout.addWidget(net_group)

        # Image Selection
        img_group = QGroupBox("Target Image")
        img_layout = QHBoxLayout()
        self.lbl_image_path = QLabel("slow download button.png")
        self.lbl_image_path.setWordWrap(True)
        btn_capture = QPushButton("Capture Screenshot")
        btn_capture.clicked.connect(self.start_snipping)
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browse_image)
        
        img_layout.addWidget(self.lbl_image_path)
        img_layout.addWidget(btn_capture)
        img_layout.addWidget(btn_browse)
        img_group.setLayout(img_layout)
        layout.addWidget(img_group)

        # Settings
        settings_group = QGroupBox("Settings")
        form_layout = QFormLayout()
        
        self.spin_speed = QDoubleSpinBox()
        self.spin_speed.setRange(0.1, 100.0)
        self.spin_speed.setValue(1.0)
        self.spin_speed.setSuffix(" MB/s")
        
        self.spin_sleep = QDoubleSpinBox()
        self.spin_sleep.setRange(1.0, 60.0)
        self.spin_sleep.setValue(8.0)
        self.spin_sleep.setSuffix(" s")

        form_layout.addRow("Download Speed Threshold:", self.spin_speed)
        form_layout.addRow("Sleep Time (after click):", self.spin_sleep)
        settings_group.setLayout(form_layout)
        layout.addWidget(settings_group)

        # Controls
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_start.clicked.connect(self.start_worker)
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self.stop_worker)
        self.btn_stop.setEnabled(False)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        layout.addLayout(btn_layout)

        # Log
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        layout.addWidget(self.text_log)

    def populate_networks(self):
        addresses = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        
        default_iface = None
        try:
            # Connect to a public DNS server to determine the outgoing interface IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            for intface, addr_list in addresses.items():
                for addr in addr_list:
                    if addr.address == local_ip:
                        default_iface = intface
                        break
                if default_iface:
                    break
        except Exception:
            pass

        for intface, addr_list in addresses.items():
            if any(getattr(addr, 'address').startswith("169.254") for addr in addr_list):
                continue
            elif intface in stats and getattr(stats[intface], "isup"):
                self.combo_network.addItem(intface)
        
        if default_iface:
            index = self.combo_network.findText(default_iface)
            if index >= 0:
                self.combo_network.setCurrentIndex(index)

    def start_snipping(self):
        self.hide()
        time.sleep(0.2) # Wait for window to hide
        self.snipper = Snipper()
        self.snipper.signal_image_captured.connect(self.image_captured)
        self.snipper.showFullScreen()

    def image_captured(self, path):
        self.lbl_image_path.setText(path)
        self.show()

    def browse_image(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Open file', '.', "Image files (*.png *.jpg)")
        if fname:
            self.lbl_image_path.setText(fname)

    def start_worker(self):
        interface = self.combo_network.currentText()
        image_path = self.lbl_image_path.text()
        speed = self.spin_speed.value()
        sleep = self.spin_sleep.value()

        self.worker = Worker(interface, image_path, speed, sleep)
        self.worker.log_signal.connect(self.log)
        self.worker.speed_signal.connect(lambda s: self.setWindowTitle(f"Wabbajack Autoclicker - {s} MB/s"))
        self.worker.finished.connect(self.worker_finished)
        self.worker.start()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.log("Worker started.")

    def stop_worker(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
    
    def worker_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.log("Worker stopped.")

    def log(self, message):
        self.text_log.append(message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
