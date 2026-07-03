# src/ui/main_window.py
import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit,
    QGroupBox, QGridLayout, QMessageBox, QComboBox, QListWidget,
    QListWidgetItem, QFileDialog
)
from PyQt6.QtCore import pyqtSlot, Qt, QThread, pyqtSignal

from osc.client import OscClient
from osc.server import OscServer
from core.language import LANG
from core.config import ConfigManager
from version import APP_NAME, VERSION


class OscSendWorker(QThread):
    """UI 멈춤을 방지하고 순차 전송을 백그라운드에서 처리하는 스레드"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, osc_client, ip, port, items, delay_sec, main_window):
        super().__init__()
        self.osc_client = osc_client
        self.ip = ip
        self.port = port
        self.items = items
        self.delay_sec = delay_sec
        self.main_window = main_window
        self.is_running = True

    def run(self):
        count = len(self.items)
        self.log_signal.emit(f"=== 시작: {count}개의 메시지 연속 전송 (Delay: {self.delay_sec}s) ===")

        for i, item_text in enumerate(self.items):
            if not self.is_running:
                self.log_signal.emit("=== 전송이 사용자에 의해 중지되었습니다 ===")
                break

            parts = item_text.split(" | ")
            if len(parts) >= 2:
                addr = parts[0]
                val_str = parts[1]
                vtype = parts[2] if len(parts) > 2 else "Auto"

                try:
                    val = self.main_window.parse_value(val_str, vtype)
                    self.osc_client.send(self.ip, self.port, addr, val)

                    type_name = type(val).__name__
                    self.log_signal.emit(f"[SEND {i + 1}/{count}] {addr} | {val} ({type_name})")

                    # 지연 시간 동안 대기 (중지 체크를 위해 짧게 쪼개서 대기)
                    elapsed = 0.0
                    while elapsed < self.delay_sec and self.is_running:
                        time.sleep(0.01)
                        elapsed += 0.01
                except Exception as e:
                    self.log_signal.emit(f"[ERROR] {addr} 전송 실패: {str(e)}")

        if self.is_running:
            self.log_signal.emit("=== 전송 완료 ===")
        self.finished_signal.emit()

    def stop(self):
        self.is_running = False


class OSCMasterTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.current_lang = self.config_manager.get("language")

        self.osc_client = OscClient()
        self.osc_server = OscServer()
        self.send_worker = None

        self.init_ui()
        self.load_saved_values()
        self.apply_language()

        self.osc_server.log_signal.connect(self.append_log)

    def init_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.resize(650, 700)  # 버튼 배치 공간 확보를 위해 세로 살짝 확장

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

        # 2. OSC 전송 그룹
        self.send_group = QGroupBox()
        send_layout = QGridLayout()
        self.send_ip_label = QLabel()
        self.send_ip_input = QLineEdit()
        self.send_port_label = QLabel()
        self.send_port_input = QLineEdit()
        self.send_addr_label = QLabel()
        self.send_addr_input = QLineEdit()
        self.send_val_label = QLabel()

        val_layout = QHBoxLayout()
        self.send_type_combo = QComboBox()
        self.send_type_combo.addItems(["Auto", "int", "float", "str", "bool"])
        self.send_type_combo.setFixedWidth(70)
        self.send_val_input = QLineEdit()
        val_layout.addWidget(self.send_type_combo)
        val_layout.addWidget(self.send_val_input)
        val_layout.setContentsMargins(0, 0, 0, 0)
        val_widget = QWidget()
        val_widget.setLayout(val_layout)

        self.add_btn = QPushButton()
        self.msg_list = QListWidget()
        self.msg_list.setFixedHeight(120)

        self.delete_sel_btn = QPushButton()
        self.clear_list_btn = QPushButton()
        self.send_all_btn = QPushButton()

        # 파일 저장/불러오기 버튼 추가
        self.save_list_btn = QPushButton()
        self.load_list_btn = QPushButton()

        # 딜레이 설정 레이아웃
        self.delay_label = QLabel()
        self.delay_input = QLineEdit("0.05")
        self.delay_input.setFixedWidth(50)
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(self.delay_label)
        delay_layout.addWidget(self.delay_input)
        delay_layout.setContentsMargins(0, 0, 0, 0)
        delay_widget = QWidget()
        delay_widget.setLayout(delay_layout)

        self.add_btn.clicked.connect(self.add_to_list)
        self.delete_sel_btn.clicked.connect(self.delete_selected)
        self.clear_list_btn.clicked.connect(self.msg_list.clear)
        self.send_all_btn.clicked.connect(self.send_all_osc)
        self.save_list_btn.clicked.connect(self.save_list_to_file)
        self.load_list_btn.clicked.connect(self.load_list_from_file)

        send_layout.addWidget(self.send_ip_label, 0, 0)
        send_layout.addWidget(self.send_ip_input, 0, 1)
        send_layout.addWidget(self.send_port_label, 0, 2)
        send_layout.addWidget(self.send_port_input, 0, 3)
        send_layout.addWidget(self.send_addr_label, 1, 0)
        send_layout.addWidget(self.send_addr_input, 1, 1)
        send_layout.addWidget(self.send_val_label, 1, 2)
        send_layout.addWidget(val_widget, 1, 3)

        send_layout.addWidget(self.add_btn, 2, 0, 1, 4)
        send_layout.addWidget(self.msg_list, 3, 0, 1, 4)

        # 버튼 그리드 배치 최적화
        send_layout.addWidget(self.delete_sel_btn, 4, 0)
        send_layout.addWidget(self.clear_list_btn, 4, 1)
        send_layout.addWidget(self.save_list_btn, 4, 2)
        send_layout.addWidget(self.load_list_btn, 4, 3)

        send_layout.addWidget(delay_widget, 5, 0, 1, 2)
        send_layout.addWidget(self.send_all_btn, 5, 2, 1, 2)

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

        saved_type = self.config_manager.get("send_type")
        if saved_type:
            self.send_type_combo.setCurrentText(saved_type)

        saved_delay = self.config_manager.get("send_delay")
        if saved_delay:
            self.delay_input.setText(saved_delay)

    def save_current_values(self):
        self.config_manager.set("send_ip", self.send_ip_input.text())
        self.config_manager.set("send_port", self.send_port_input.text())
        self.config_manager.set("send_address", self.send_addr_input.text())
        self.config_manager.set("send_value", self.send_val_input.text())
        self.config_manager.set("send_type", self.send_type_combo.currentText())
        self.config_manager.set("send_delay", self.delay_input.text())
        self.config_manager.set("recv_ip", self.recv_ip_input.text())
        self.config_manager.set("recv_port", self.recv_port_input.text())

    def apply_language(self):
        lang = LANG[self.current_lang]
        self.send_group.setTitle(lang["send"])
        self.send_ip_label.setText(lang["ip"])
        self.send_port_label.setText(lang["port"])
        self.send_addr_label.setText(lang["address"])
        self.send_val_label.setText(lang["value"])

        self.add_btn.setText(lang["add_list"])
        self.delete_sel_btn.setText(lang["delete_selected"])
        self.clear_list_btn.setText(lang["clear_list"])
        self.save_list_btn.setText(lang["save_list"])
        self.load_list_btn.setText(lang["load_list"])

        # 워커 동작 여부에 따른 텍스트 분기 처리
        if self.send_worker and self.send_worker.isRunning():
            self.send_all_btn.setText(lang["stop_send"])
        else:
            self.send_all_btn.setText(lang["send_all"])

        self.delay_label.setText(lang["delay"])

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
        vtype = self.send_type_combo.currentText()

        if not addr:
            QMessageBox.warning(self, "Warning", "OSC 주소를 입력해주세요.")
            return

        self.add_item_to_widget(f"{addr} | {val} | {vtype}")
        self.save_current_values()

    def add_item_to_widget(self, text):
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Unchecked)
        self.msg_list.addItem(item)

    def delete_selected(self):
        for i in range(self.msg_list.count() - 1, -1, -1):
            item = self.msg_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                self.msg_list.takeItem(i)

    def parse_value(self, val_str, vtype):
        if vtype == "int":
            return int(val_str)
        elif vtype == "float":
            return float(val_str)
        elif vtype == "bool":
            return val_str.lower() in ("true", "1", "t", "yes", "on")
        elif vtype == "str":
            return val_str
        else:  # Auto
            try:
                if '.' in val_str:
                    return float(val_str)
                else:
                    return int(val_str)
            except ValueError:
                return val_str

    def send_all_osc(self):
        # 만약 이미 백그라운드 전송이 실행 중이라면 '중지' 요청으로 작동합니다.
        if self.send_worker and self.send_worker.isRunning():
            self.send_worker.stop()
            return

        ip = self.send_ip_input.text()
        try:
            port = int(self.send_port_input.text())
        except ValueError:
            QMessageBox.warning(self, "Error", "포트는 숫자여야 합니다.")
            return

        try:
            delay_sec = float(self.delay_input.text())
            if delay_sec < 0:
                raise ValueError
        except ValueError:
            delay_sec = 0.05
            self.delay_input.setText("0.05")

        count = self.msg_list.count()
        if count == 0:
            QMessageBox.warning(self, "Warning", "전송할 리스트가 비어있습니다.")
            return

        # 리스트 아이템 추출
        items = [self.msg_list.item(i).text() for i in range(count)]

        # 백그라운드 스레드 생성 및 실행
        self.send_worker = OscSendWorker(self.osc_client, ip, port, items, delay_sec, self)
        self.send_worker.log_signal.connect(self.append_log)
        self.send_worker.finished_signal.connect(self.on_send_finished)

        # 버튼 상태 및 텍스트 전환
        self.send_worker.start()
        self.send_all_btn.setText(LANG[self.current_lang]["stop_send"])
        self.set_ui_enabled_during_send(False)

    def on_send_finished(self):
        """백그라운드 전송 스레드가 종료되었을 때 호출"""
        self.send_all_btn.setText(LANG[self.current_lang]["send_all"])
        self.set_ui_enabled_during_send(True)
        self.save_current_values()

    def set_ui_enabled_during_send(self, enabled):
        """전송 중 리스트가 오염되는 것을 막기 위해 위젯 비활성화 제어"""
        self.add_btn.setEnabled(enabled)
        self.delete_sel_btn.setEnabled(enabled)
        self.clear_list_btn.setEnabled(enabled)
        self.save_list_btn.setEnabled(enabled)
        self.load_list_btn.setEnabled(enabled)
        self.msg_list.setEnabled(enabled)
        self.delay_input.setEnabled(enabled)

    def save_list_to_file(self):
        """현재 리스트 목록을 텍스트 파일로 저장합니다."""
        count = self.msg_list.count()
        if count == 0:
            QMessageBox.warning(self, "Warning", "저장할 리스트가 없습니다.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save OSC List", "", "OSC Playback Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    for i in range(count):
                        f.write(self.msg_list.item(i).text() + "\n")
                self.append_log(f"[SYSTEM] 리스트가 성공적으로 저장되었습니다: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"파일 저장 실패:\n{str(e)}")

    def load_list_from_file(self):
        """텍스트 파일로부터 리스트 목록을 불러와 추가합니다."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load OSC List", "", "OSC Playback Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()

                if lines:
                    self.msg_list.clear()  # 기존 큐 비우기
                    for line in lines:
                        if line.strip():
                            self.add_item_to_widget(line)
                    self.append_log(f"[SYSTEM] 리스트를 성공적으로 불러왔습니다: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"파일 읽기 실패:\n{str(e)}")

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
        if self.send_worker and self.send_worker.isRunning():
            self.send_worker.stop()
            self.send_worker.wait()
        self.save_current_values()
        self.stop_server()
        event.accept()