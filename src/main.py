# src/main.py
import sys
import os
import time

# src 폴더 경로 보장
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit,
    QGroupBox, QGridLayout, QMessageBox, QComboBox, QListWidget
)
from PyQt6.QtCore import pyqtSlot

from osc.client import OscClient
from osc.server import OscServer
from core.language import LANG
from core.config import ConfigManager
from version import APP_NAME, VERSION


class OSCMasterTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.current_lang = self.config_manager.get("language")

        self.osc_client = OscClient()
        self.osc_server = OscServer()

        self.init_ui()
        self.load_saved_values()
        self.apply_language()

        # 서버 로그 시그널 연결
        self.osc_server.log_signal.connect(self.append_log)

    def init_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.resize(600, 650)  # 리스트 추가로 인해 세로 길이 약간 증가

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. 언어 선택
        lang_layout = QHBoxLayout()
        lang_layout.addStretch()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["한국어", "English"])
        if self.current_lang == "en":
            self.lang_combo.setCurrentIndex(1)
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        lang_layout.addWidget(self.lang_combo)
        main_layout.addLayout(lang_layout)

        # 2. OSC 전송 그룹 (매크로 리스트 포함)
        self.send_group = QGroupBox()
        send_layout = QGridLayout()
        self.send_ip_label = QLabel()
        self.send_ip_input = QLineEdit()
        self.send_port_label = QLabel()
        self.send_port_input = QLineEdit()
        self.send_addr_label = QLabel()
        self.send_addr_input = QLineEdit()
        self.send_val_label = QLabel()
        self.send_val_input = QLineEdit()

        # 새로 추가된 리스트 및 버튼들
        self.add_btn = QPushButton()
        self.msg_list = QListWidget()
        self.msg_list.setFixedHeight(100)
        self.clear_list_btn = QPushButton()
        self.send_all_btn = QPushButton()

        self.add_btn.clicked.connect(self.add_to_list)
        self.clear_list_btn.clicked.connect(self.msg_list.clear)
        self.send_all_btn.clicked.connect(self.send_all_osc)

        send_layout.addWidget(self.send_ip_label, 0, 0)
        send_layout.addWidget(self.send_ip_input, 0, 1)
        send_layout.addWidget(self.send_port_label, 0, 2)
        send_layout.addWidget(self.send_port_input, 0, 3)
        send_layout.addWidget(self.send_addr_label, 1, 0)
        send_layout.addWidget(self.send_addr_input, 1, 1)
        send_layout.addWidget(self.send_val_label, 1, 2)
        send_layout.addWidget(self.send_val_input, 1, 3)

        send_layout.addWidget(self.add_btn, 2, 0, 1, 4)
        send_layout.addWidget(self.msg_list, 3, 0, 1, 4)
        send_layout.addWidget(self.clear_list_btn, 4, 0, 1, 2)
        send_layout.addWidget(self.send_all_btn, 4, 2, 1, 2)

        self.send_group.setLayout(send_layout)
        main_layout.addWidget(self.send_group)

        # 3. OSC 수신 그룹
        self.recv_group = QGroupBox()
        recv_layout = QGridLayout()
        self.recv_ip_label = QLabel()
        self.recv_ip_input = QLineEdit()
        self.recv_port_label = QLabel()
        self.recv_port_input = QLineEdit()
        self.recv_start_btn = QPushButton()
        self.recv_stop_btn = QPushButton()
        self.recv_stop_btn.setEnabled(False)

        self.recv_start_btn.clicked.connect(self.start_server)
        self.recv_stop_btn.clicked.connect(self.stop_server)

        recv_layout.addWidget(self.recv_ip_label, 0, 0)
        recv_layout.addWidget(self.recv_ip_input, 0, 1)
        recv_layout.addWidget(self.recv_port_label, 0, 2)
        recv_layout.addWidget(self.recv_port_input, 0, 3)
        recv_layout.addWidget(self.recv_start_btn, 1, 0, 1, 2)
        recv_layout.addWidget(self.recv_stop_btn, 1, 2, 1, 2)
        self.recv_group.setLayout(recv_layout)
        main_layout.addWidget(self.recv_group)

        # 4. 로그 영역
        self.log_group = QGroupBox()
        log_layout = QVBoxLayout()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.clear_btn = QPushButton()
        self.clear_btn.clicked.connect(self.log_area.clear)
        log_layout.addWidget(self.log_area)
        log_layout.addWidget(self.clear_btn)
        self.log_group.setLayout(log_layout)
        main_layout.addWidget(self.log_group)

    def load_saved_values(self):
        self.send_ip_input.setText(self.config_manager.get("send_ip"))
        self.send_port_input.setText(self.config_manager.get("send_port"))
        self.send_addr_input.setText(self.config_manager.get("send_address"))
        self.send_val_input.setText(self.config_manager.get("send_value"))
        self.recv_ip_input.setText(self.config_manager.get("recv_ip"))
        self.recv_port_input.setText(self.config_manager.get("recv_port"))

    def save_current_values(self):
        self.config_manager.set("send_ip", self.send_ip_input.text())
        self.config_manager.set("send_port", self.send_port_input.text())
        self.config_manager.set("send_address", self.send_addr_input.text())
        self.config_manager.set("send_value", self.send_val_input.text())
        self.config_manager.set("recv_ip", self.recv_ip_input.text())
        self.config_manager.set("recv_port", self.recv_port_input.text())

    def apply_language(self):
        lang = LANG[self.current_lang]
        self.send_group.setTitle(lang["send"])
        self.send_ip_label.setText(lang["ip"])
        self.send_port_label.setText(lang["port"])
        self.send_addr_label.setText(lang["address"])
        self.send_val_label.setText(lang["value"])

        # 새 버튼 언어 적용
        self.add_btn.setText(lang["add_list"])
        self.clear_list_btn.setText(lang["clear_list"])
        self.send_all_btn.setText(lang["send_all"])

        self.recv_group.setTitle(lang["receive"])
        self.recv_ip_label.setText(lang["ip"])
        self.recv_port_label.setText(lang["port"])
        self.recv_start_btn.setText(lang["start"])
        self.recv_stop_btn.setText(lang["stop"])

        self.log_group.setTitle(lang["log"])
        self.clear_btn.setText(lang["clear"])

    def change_language(self, index):
        self.current_lang = "ko" if index == 0 else "en"
        self.config_manager.set("language", self.current_lang)
        self.apply_language()

    def add_to_list(self):
        addr = self.send_addr_input.text().strip()
        val = self.send_val_input.text().strip()

        if not addr:
            QMessageBox.warning(self, "Warning", "OSC 주소를 입력해주세요.")
            return

        self.msg_list.addItem(f"{addr} | {val}")
        self.save_current_values()

    def send_all_osc(self):
        ip = self.send_ip_input.text()
        try:
            port = int(self.send_port_input.text())
        except ValueError:
            QMessageBox.warning(self, "Error", "포트는 숫자여야 합니다.")
            return

        count = self.msg_list.count()
        if count == 0:
            QMessageBox.warning(self, "Warning", "전송할 리스트가 비어있습니다.")
            return

        self.append_log(f"=== 시작: {count}개의 메시지 연속 전송 ({ip}:{port}) ===")

        for i in range(count):
            item_text = self.msg_list.item(i).text()
            parts = item_text.split(" | ", 1)
            if len(parts) == 2:
                addr, val = parts
                try:
                    self.osc_client.send(ip, port, addr, val)
                    self.append_log(f"[SEND {i + 1}/{count}] {addr} | {val}")
                    time.sleep(0.05)  # 짧은 딜레이로 패킷 유실 방지
                except Exception as e:
                    self.append_log(f"[ERROR] {addr} 전송 실패: {str(e)}")

        self.append_log("=== 전송 완료 ===")

    def start_server(self):
        ip = self.recv_ip_input.text()
        try:
            port = int(self.recv_port_input.text())
            self.osc_server.start(ip, port)

            self.recv_start_btn.setEnabled(False)
            self.recv_stop_btn.setEnabled(True)
            self.save_current_values()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"서버 시작 실패:\n{str(e)}")

    def stop_server(self):
        self.osc_server.stop()
        self.recv_start_btn.setEnabled(True)
        self.recv_stop_btn.setEnabled(False)

    @pyqtSlot(str)
    def append_log(self, text):
        self.log_area.append(text)

    def closeEvent(self, event):
        self.save_current_values()
        self.stop_server()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = OSCMasterTool()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()