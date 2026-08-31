import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit,
    QGroupBox, QGridLayout, QMessageBox, QComboBox, QListWidget,
    QListWidgetItem, QFileDialog, QDialog, QDialogButtonBox,
    QAbstractItemView
)
from PyQt6.QtCore import pyqtSlot, Qt, QThread, pyqtSignal

from osc.client import OscClient
from osc.server import OscServer
from core.language import LANG
from core.config import ConfigManager
from version import APP_NAME, VERSION


class EditOscItemDialog(QDialog):
    def __init__(self, item_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OSC 항목 수정 / Edit OSC Item")
        self.setModal(True)
        self.resize(300, 280)

        layout = QGridLayout(self)
        parts = [p.strip() for p in item_text.split("|")]
        tag, ip, port, addr, val, vtype, delay = "-", "", "", "", "", "Auto", "0.0"

        try:
            # 1. 신규 포맷: 태그 | IP:Port | 주소 | 값 | 타입 | 딜레이
            if len(parts) >= 4 and ":" in parts[1]:
                tag = parts[0]
                ip, port = parts[1].split(":")
                addr = parts[2]
                val = parts[3]
                if len(parts) > 4: vtype = parts[4]
                if len(parts) > 5: delay = parts[5]
            # 2. 중간 호환 포맷: IP:Port | 주소 | 값 | 타입 | 딜레이
            elif len(parts) >= 3 and ":" in parts[0]:
                ip, port = parts[0].split(":")
                addr = parts[1]
                val = parts[2]
                if len(parts) > 3: vtype = parts[3]
                if len(parts) > 4: delay = parts[4]
            # 3. 구형 포맷: 주소 | 값 | 타입 | 딜레이
            elif len(parts) >= 2:
                addr = parts[0]
                val = parts[1]
                if len(parts) > 2: vtype = parts[2]
                if len(parts) > 3: delay = parts[3]
        except Exception:
            pass

        self.tag_input = QLineEdit(tag)
        self.ip_input = QLineEdit(ip)
        self.port_input = QLineEdit(port)
        self.addr_input = QLineEdit(addr)
        self.val_input = QLineEdit(val)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Auto", "int", "float", "str", "bool"])
        self.type_combo.setCurrentText(vtype)
        self.delay_input = QLineEdit(delay)

        layout.addWidget(QLabel("Tag:"), 0, 0)
        layout.addWidget(self.tag_input, 0, 1)
        layout.addWidget(QLabel("IP:"), 1, 0)
        layout.addWidget(self.ip_input, 1, 1)
        layout.addWidget(QLabel("Port:"), 2, 0)
        layout.addWidget(self.port_input, 2, 1)
        layout.addWidget(QLabel("Address:"), 3, 0)
        layout.addWidget(self.addr_input, 3, 1)
        layout.addWidget(QLabel("Value:"), 4, 0)
        layout.addWidget(self.val_input, 4, 1)
        layout.addWidget(QLabel("Type:"), 5, 0)
        layout.addWidget(self.type_combo, 5, 1)
        layout.addWidget(QLabel("Delay (sec):"), 6, 0)
        layout.addWidget(self.delay_input, 6, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, 7, 0, 1, 2)

    def get_result(self):
        tag_val = self.tag_input.text().strip() or "-"
        return (f"{tag_val} | {self.ip_input.text().strip()}:{self.port_input.text().strip()} | "
                f"{self.addr_input.text().strip()} | {self.val_input.text().strip()} | "
                f"{self.type_combo.currentText()} | {self.delay_input.text().strip()}")


class OscSendWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, osc_client, items, mode, current_lang, main_window):
        super().__init__()
        self.osc_client = osc_client
        self.items = items
        self.mode = mode
        self.current_lang = current_lang
        self.main_window = main_window
        self.is_running = True

    def run(self):
        lang = LANG[self.current_lang]
        count = len(self.items)

        if self.mode == "concurrent":
            self.log_signal.emit(lang["msg_concurrent_ready"].format(count=count))
        else:
            self.log_signal.emit(lang["msg_sequential_ready"].format(count=count))

        targets = []
        for item_text in self.items:
            parts = [p.strip() for p in item_text.split("|")]
            try:
                delay = 0.0
                tag = "-"

                # 1. 신규 포맷
                if len(parts) >= 4 and ":" in parts[1]:
                    tag = parts[0]
                    ip, port_str = parts[1].split(":")
                    port = int(port_str)
                    addr = parts[2]
                    val_str = parts[3]
                    vtype = parts[4] if len(parts) > 4 else "Auto"
                    delay = float(parts[5]) if len(parts) > 5 else 0.0
                # 2. 중간 호환 포맷
                elif len(parts) >= 3 and ":" in parts[0]:
                    ip, port_str = parts[0].split(":")
                    port = int(port_str)
                    addr = parts[1]
                    val_str = parts[2]
                    vtype = parts[3] if len(parts) > 3 else "Auto"
                    delay = float(parts[4]) if len(parts) > 4 else 0.0
                # 3. 구형 포맷
                elif len(parts) >= 2:
                    ip = self.main_window.send_ip_input.text()
                    port = int(self.main_window.send_port_input.text())
                    addr = parts[0]
                    val_str = parts[1]
                    vtype = parts[2] if len(parts) > 2 else "Auto"
                    delay = float(parts[3]) if len(parts) > 3 else 0.0
                else:
                    continue

                val = self.main_window.parse_value(val_str, vtype)
                # tag 정보를 추가해서 전달
                targets.append((tag, ip, port, addr, val, delay))
            except Exception as e:
                self.log_signal.emit(lang["err_parse"].format(item=item_text, error=str(e)))

        if not targets:
            self.log_signal.emit(lang["msg_no_targets"])
            self.finished_signal.emit()
            return

        if self.mode == "concurrent":
            osc_targets = [(t[1], t[2], t[3], t[4]) for t in targets]
            self.osc_client.send_concurrently(osc_targets)

            for t in targets:
                type_name = type(t[4]).__name__
                # 로그에 태그(t[0]) 표시
                self.log_signal.emit(f"[READY] [{t[0]}] {t[1]}:{t[2]} -> {t[3]} | {t[4]} ({type_name})")
            self.log_signal.emit(lang["msg_concurrent_done"].format(count=len(targets)))

        elif self.mode == "sequential":
            for i, target in enumerate(targets):
                if not self.is_running:
                    self.log_signal.emit(lang["msg_stopped"])
                    break

                tag, ip, port, addr, val, item_delay = target

                self.osc_client.send(ip, port, addr, val)

                type_name = type(val).__name__
                delay_msg = f" (Delay: {item_delay}s)" if item_delay > 0 else ""
                self.log_signal.emit(
                    f"[SEND {i + 1}/{len(targets)}] [{tag}] {ip}:{port} -> {addr} | {val} ({type_name}){delay_msg}")

                if item_delay > 0:
                    start_time = time.time()
                    while (time.time() - start_time) < item_delay and self.is_running:
                        time.sleep(0.01)

            if self.is_running:
                self.log_signal.emit(lang["msg_seq_done"])

        self.finished_signal.emit()

    def stop(self):
        self.is_running = False


class OSCMasterTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.current_lang = self.config_manager.get("language") or "ko"

        self.osc_client = OscClient()
        self.osc_server = OscServer()
        self.send_worker = None

        self._active_send_btn = None
        self._inactive_send_btn = None

        self.init_ui()
        self.load_saved_values()
        self.apply_language()

        self.osc_server.log_signal.connect(self.append_log)

    def init_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.resize(650, 750)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        lang_layout = QHBoxLayout()
        lang_layout.addStretch()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["한국어", "English"])
        if self.current_lang == "en":
            self.lang_combo.setCurrentIndex(1)
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        lang_layout.addWidget(self.lang_combo)
        main_layout.addLayout(lang_layout)

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

        self.item_delay_label = QLabel()
        self.item_delay_input = QLineEdit("0.0")

        # --- 태그 입력 UI 추가 ---
        self.send_tag_label = QLabel()
        self.send_tag_input = QLineEdit()

        self.add_btn = QPushButton()

        self.msg_list = QListWidget()
        self.msg_list.setFixedHeight(120)
        self.msg_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.msg_list.itemDoubleClicked.connect(self.edit_list_item)

        self.move_up_btn = QPushButton("▲")
        self.move_up_btn.setFixedWidth(30)
        self.move_down_btn = QPushButton("▼")
        self.move_down_btn.setFixedWidth(30)
        self.move_up_btn.clicked.connect(self.move_item_up)
        self.move_down_btn.clicked.connect(self.move_item_down)

        list_container = QWidget()
        list_h_layout = QHBoxLayout(list_container)
        list_h_layout.setContentsMargins(0, 0, 0, 0)
        list_h_layout.addWidget(self.msg_list)

        btn_v_layout = QVBoxLayout()
        btn_v_layout.addWidget(self.move_up_btn)
        btn_v_layout.addWidget(self.move_down_btn)
        btn_v_layout.addStretch()
        list_h_layout.addLayout(btn_v_layout)

        self.delete_sel_btn = QPushButton()
        self.clear_list_btn = QPushButton()
        self.save_list_btn = QPushButton()
        self.load_list_btn = QPushButton()

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["동시 전송 (Concurrent)", "순차 전송 (Sequential)"])

        self.send_sel_btn = QPushButton()
        self.send_all_btn = QPushButton()

        self.add_btn.clicked.connect(self.add_to_list)
        self.delete_sel_btn.clicked.connect(self.delete_selected)
        self.clear_list_btn.clicked.connect(self.msg_list.clear)
        self.save_list_btn.clicked.connect(self.save_list_to_file)
        self.load_list_btn.clicked.connect(self.load_list_from_file)
        self.send_sel_btn.clicked.connect(self.send_selected_osc)
        self.send_all_btn.clicked.connect(self.send_all_osc)

        send_layout.addWidget(self.send_ip_label, 0, 0)
        send_layout.addWidget(self.send_ip_input, 0, 1)
        send_layout.addWidget(self.send_port_label, 0, 2)
        send_layout.addWidget(self.send_port_input, 0, 3)
        send_layout.addWidget(self.send_addr_label, 1, 0)
        send_layout.addWidget(self.send_addr_input, 1, 1)
        send_layout.addWidget(self.send_val_label, 1, 2)
        send_layout.addWidget(val_widget, 1, 3)

        # 지연 입력칸과 태그 입력칸을 나란히 배치
        send_layout.addWidget(self.item_delay_label, 2, 0)
        send_layout.addWidget(self.item_delay_input, 2, 1)
        send_layout.addWidget(self.send_tag_label, 2, 2)
        send_layout.addWidget(self.send_tag_input, 2, 3)

        send_layout.addWidget(self.add_btn, 3, 0, 1, 4)
        send_layout.addWidget(list_container, 4, 0, 1, 4)
        send_layout.addWidget(self.delete_sel_btn, 5, 0)
        send_layout.addWidget(self.clear_list_btn, 5, 1)
        send_layout.addWidget(self.save_list_btn, 5, 2)
        send_layout.addWidget(self.load_list_btn, 5, 3)
        send_layout.addWidget(self.mode_combo, 6, 0, 1, 4)
        send_layout.addWidget(self.send_sel_btn, 7, 0, 1, 2)
        send_layout.addWidget(self.send_all_btn, 7, 2, 1, 2)

        self.send_group.setLayout(send_layout)
        main_layout.addWidget(self.send_group)

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

    def move_item_up(self):
        row = self.msg_list.currentRow()
        if row > 0:
            item = self.msg_list.takeItem(row)
            self.msg_list.insertItem(row - 1, item)
            self.msg_list.setCurrentRow(row - 1)

    def move_item_down(self):
        row = self.msg_list.currentRow()
        if row >= 0 and row < self.msg_list.count() - 1:
            item = self.msg_list.takeItem(row)
            self.msg_list.insertItem(row + 1, item)
            self.msg_list.setCurrentRow(row + 1)

    def edit_list_item(self, item):
        dialog = EditOscItemDialog(item.text(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_text = dialog.get_result()
            item.setText(new_text)

    def load_saved_values(self):
        self.send_ip_input.setText(self.config_manager.get("send_ip"))
        self.send_port_input.setText(self.config_manager.get("send_port"))
        self.send_addr_input.setText(self.config_manager.get("send_address"))
        self.send_val_input.setText(self.config_manager.get("send_value"))
        self.send_tag_input.setText(self.config_manager.get("send_tag") or "")

        self.recv_ip_input.setText(self.config_manager.get("recv_ip"))
        self.recv_port_input.setText(self.config_manager.get("recv_port"))

        saved_type = self.config_manager.get("send_type")
        if saved_type:
            self.send_type_combo.setCurrentText(saved_type)
        saved_mode = self.config_manager.get("send_mode")
        if saved_mode == "sequential":
            self.mode_combo.setCurrentIndex(1)
        saved_delay = self.config_manager.get("send_delay")
        if saved_delay:
            self.item_delay_input.setText(saved_delay)

    def save_current_values(self):
        self.config_manager.set("send_ip", self.send_ip_input.text())
        self.config_manager.set("send_port", self.send_port_input.text())
        self.config_manager.set("send_address", self.send_addr_input.text())
        self.config_manager.set("send_value", self.send_val_input.text())
        self.config_manager.set("send_tag", self.send_tag_input.text())
        self.config_manager.set("send_type", self.send_type_combo.currentText())

        self.config_manager.set("recv_ip", self.recv_ip_input.text())
        self.config_manager.set("recv_port", self.recv_port_input.text())
        mode_val = "sequential" if self.mode_combo.currentIndex() == 1 else "concurrent"
        self.config_manager.set("send_mode", mode_val)
        self.config_manager.set("send_delay", self.item_delay_input.text())

    def apply_language(self):
        lang = LANG[self.current_lang]
        self.send_group.setTitle(lang.get("send", "전송"))
        self.send_ip_label.setText(lang.get("ip", "IP"))
        self.send_port_label.setText(lang.get("port", "Port"))
        self.send_addr_label.setText(lang.get("address", "주소"))
        self.send_val_label.setText(lang.get("value", "값"))
        self.item_delay_label.setText(lang.get("delay", "Delay (sec):"))
        self.send_tag_label.setText(lang.get("tag", "태그 (이름)"))

        self.add_btn.setText(lang.get("add_list", "추가"))
        self.delete_sel_btn.setText(lang.get("delete_selected", "선택 삭제"))
        self.clear_list_btn.setText(lang.get("clear_list", "전체 삭제"))
        self.save_list_btn.setText(lang.get("save_list", "리스트 저장"))
        self.load_list_btn.setText(lang.get("load_list", "리스트 불러오기"))

        if self.send_worker and self.send_worker.isRunning():
            if self._active_send_btn == self.send_all_btn:
                self.send_all_btn.setText(lang.get("stop_send", "중지"))
                self.send_sel_btn.setText(lang.get("send_selected", "선택 전송"))
            elif self._active_send_btn == self.send_sel_btn:
                self.send_sel_btn.setText(lang.get("stop_send", "중지"))
                self.send_all_btn.setText(lang.get("send_all", "전체 전송"))
        else:
            self.send_all_btn.setText(lang.get("send_all", "전체 전송"))
            self.send_sel_btn.setText(lang.get("send_selected", "선택 전송"))

        self.recv_group.setTitle(lang.get("receive", "수신"))
        self.recv_ip_label.setText(lang.get("ip", "IP"))
        self.recv_port_label.setText(lang.get("port", "Port"))
        self.recv_start_btn.setText(lang.get("start", "시작"))
        self.recv_stop_btn.setText(lang.get("stop", "중지"))

        self.log_group.setTitle(lang.get("log", "로그"))
        self.clear_btn.setText(lang.get("clear", "지우기"))

    def change_language(self, index):
        self.current_lang = "ko" if index == 0 else "en"
        self.config_manager.set("language", self.current_lang)
        self.apply_language()

    def add_to_list(self):
        lang = LANG[self.current_lang]
        ip = self.send_ip_input.text().strip()
        port = self.send_port_input.text().strip()
        addr = self.send_addr_input.text().strip()
        val = self.send_val_input.text().strip()
        vtype = self.send_type_combo.currentText()
        tag = self.send_tag_input.text().strip() or "-"

        delay_text = self.item_delay_input.text().strip()
        try:
            delay_val = float(delay_text)
            if delay_val < 0: raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Warning", lang["warn_delay_invalid"])
            return

        if not ip or not port or not addr:
            QMessageBox.warning(self, "Warning", lang["warn_input_empty"])
            return

        # 리스트에 [태그 | IP:Port | 주소 ...] 형식으로 추가
        self.add_item_to_widget(f"{tag} | {ip}:{port} | {addr} | {val} | {vtype} | {delay_val}")
        self.save_current_values()

    def add_item_to_widget(self, text):
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDragEnabled)
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
        else:
            try:
                if '.' in val_str:
                    return float(val_str)
                else:
                    return int(val_str)
            except ValueError:
                return val_str

    def send_selected_osc(self):
        lang = LANG[self.current_lang]
        if self.send_worker and self.send_worker.isRunning():
            self.send_worker.stop()
            return

        count = self.msg_list.count()
        if count == 0:
            QMessageBox.warning(self, "Warning", lang["warn_list_empty"])
            return

        items = [self.msg_list.item(i).text() for i in range(count) if
                 self.msg_list.item(i).checkState() == Qt.CheckState.Checked]

        if not items:
            QMessageBox.warning(self, "Warning", lang["warn_no_selected"])
            return

        self._execute_send(items, active_btn=self.send_sel_btn, inactive_btn=self.send_all_btn)

    def send_all_osc(self):
        lang = LANG[self.current_lang]
        if self.send_worker and self.send_worker.isRunning():
            self.send_worker.stop()
            return

        count = self.msg_list.count()
        if count == 0:
            QMessageBox.warning(self, "Warning", lang["warn_list_empty"])
            return

        items = [self.msg_list.item(i).text() for i in range(count)]
        self._execute_send(items, active_btn=self.send_all_btn, inactive_btn=self.send_sel_btn)

    def _execute_send(self, items, active_btn, inactive_btn):
        mode = "concurrent" if self.mode_combo.currentIndex() == 0 else "sequential"
        self.send_worker = OscSendWorker(self.osc_client, items, mode, self.current_lang, self)
        self.send_worker.log_signal.connect(self.append_log)
        self.send_worker.finished_signal.connect(self.on_send_finished)

        self._active_send_btn = active_btn
        self._inactive_send_btn = inactive_btn

        self.send_worker.start()

        active_btn.setText(LANG[self.current_lang].get("stop_send", "중지"))
        inactive_btn.setEnabled(False)
        self.set_ui_enabled_during_send(False)

    def on_send_finished(self):
        lang = LANG[self.current_lang]
        if self._active_send_btn == self.send_all_btn:
            self.send_all_btn.setText(lang.get("send_all", "전체 전송"))
        elif self._active_send_btn == self.send_sel_btn:
            self.send_sel_btn.setText(lang.get("send_selected", "선택 전송"))

        if self._inactive_send_btn:
            self._inactive_send_btn.setEnabled(True)

        self.set_ui_enabled_during_send(True)
        self.save_current_values()

    def set_ui_enabled_during_send(self, enabled):
        self.add_btn.setEnabled(enabled)
        self.delete_sel_btn.setEnabled(enabled)
        self.clear_list_btn.setEnabled(enabled)
        self.save_list_btn.setEnabled(enabled)
        self.load_list_btn.setEnabled(enabled)
        self.msg_list.setEnabled(enabled)
        self.mode_combo.setEnabled(enabled)
        self.move_up_btn.setEnabled(enabled)
        self.move_down_btn.setEnabled(enabled)
        self.send_tag_input.setEnabled(enabled)

    def save_list_to_file(self):
        lang = LANG[self.current_lang]
        count = self.msg_list.count()
        if count == 0:
            QMessageBox.warning(self, "Warning", lang["warn_no_save_list"])
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save OSC List", "", "OSC Playback Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    for i in range(count):
                        f.write(self.msg_list.item(i).text() + "\n")
                self.append_log(lang["sys_save_success"].format(path=file_path))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Save failed / 파일 저장 실패:\n{str(e)}")

    def load_list_from_file(self):
        lang = LANG[self.current_lang]
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load OSC List", "", "OSC Playback Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()

                if lines:
                    self.msg_list.clear()
                    for line in lines:
                        if line.strip():
                            self.add_item_to_widget(line)
                    self.append_log(lang["sys_load_success"].format(path=file_path))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Load failed / 파일 읽기 실패:\n{str(e)}")

    def start_server(self):
        ip = self.recv_ip_input.text()
        try:
            port = int(self.recv_port_input.text())
            self.osc_server.start(ip, port)

            self.recv_start_btn.setEnabled(False)
            self.recv_stop_btn.setEnabled(True)
            self.save_current_values()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Server start failed / 서버 시작 실패:\n{str(e)}")

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