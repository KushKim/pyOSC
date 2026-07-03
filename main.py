import sys
import socket
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QGridLayout,
                             QMessageBox)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import pyqtSignal

from pythonosc import udp_client
from pythonosc import dispatcher
from pythonosc import osc_server

# --- 🌍 언어팩 데이터 사전 (Language Dictionary) ---
LANG = {
    'ko': {
        'title': 'OSC 마스터 툴 (PyQt6)',
        'send_group': 'OSC 송출 (Client)',
        'ip_label': '보낼 IP:',
        'port_label': '보낼 포트:',
        'addr_label': 'OSC 주소:',
        'val_label': '보낼 값 (콤마 구분):',
        'val_placeholder': '예: 123, 3.14, test',
        'send_btn': '전송하기',
        'recv_group': 'OSC 수신 (Server)',
        'my_ip': 'ℹ️ 내 컴퓨터 IP 주소 (호스트): <b>{ip}</b>',
        'my_port': '내 수신 포트:',
        'server_on': '서버 켜기',
        'server_off': '서버 끄기',
        'clear_btn': '로그 화면 지우기',
        'menu_settings': '설정 (Settings)',
        'menu_credit': '프로그램 정보 (Credits)',
        'credit_title': '크레딧',
        'credit_body': '<b>OSC Master Tool v1.1</b><br><br>An OSC communication utility built with Python and PyQt6.<br><br>Made by KushKim 2026',
        'err_port': "⚠️ [에러] 포트 번호는 숫자만 입력해 주세요.",
        'err_addr': "⚠️ [에러] OSC 주소는 반드시 '/'로 시작해야 합니다.",
        'msg_server_started': "✅ 서버 시작됨 (포트: {port} 에서 수신 대기 중...)",
        'msg_server_failed': "❌ 서버 시작 실패: 해당 포트가 사용 중일 수 있습니다.",
        'msg_server_stopped': "🛑 서버가 안전하게 종료되었습니다."
    },
    'en': {
        'title': 'OSC Master Tool (PyQt6)',
        'send_group': 'OSC Send (Client)',
        'ip_label': 'Target IP:',
        'port_label': 'Target Port:',
        'addr_label': 'OSC Address:',
        'val_label': 'Values (comma separated):',
        'val_placeholder': 'e.g.: 123, 3.14, test',
        'send_btn': 'Send',
        'recv_group': 'OSC Receive (Server)',
        'my_ip': 'ℹ️ My Local IP Address: <b>{ip}</b>',
        'my_port': 'Listen Port:',
        'server_on': 'Start Server',
        'server_off': 'Stop Server',
        'clear_btn': 'Clear Log',
        'menu_settings': 'Settings',
        'menu_credit': 'About / Credits',
        'credit_title': 'Credits',
        'credit_body': '<b>OSC Master Tool v1.1</b><br><br>An OSC communication utility built with Python and PyQt6.<br><br>Made by KushKim 2026',
        'err_port': "⚠️ [Error] Port must be a valid number.",
        'err_addr': "⚠️ [Error] OSC Address must start with '/'.",
        'msg_server_started': "✅ Server started (Listening on port {port}...)",
        'msg_server_failed': "❌ Server start failed: Port might be in use.",
        'msg_server_stopped': "🛑 Server has been stopped safely."
    }
}


# 기존 QWidget에서 QMainWindow로 변경 (메뉴바 사용을 위해)
class OSCMasterTool(QMainWindow):
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.server = None
        self.server_thread = None
        self.is_server_running = False

        # 현재 언어 설정 (기본값: 한국어)
        self.current_lang = 'ko'

        self.initUI()
        self.log_signal.connect(self.append_log)

    def initUI(self):
        self.resize(650, 620)

        # 1. 메인 위젯 및 레이아웃 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 2. 메뉴바 생성 (Settings)
        menubar = self.menuBar()
        # 맥(Mac) 환경에서는 메뉴바가 앱 내장이 아닌 화면 상단 시스템 메뉴로 분리되는 것을 방지
        menubar.setNativeMenuBar(False)

        self.menu_settings = menubar.addMenu("설정 (Settings)")

        # 언어 변경 액션
        self.action_ko = QAction("한국어 (Korean)", self)
        self.action_ko.triggered.connect(lambda: self.change_language('ko'))
        self.menu_settings.addAction(self.action_ko)

        self.action_en = QAction("English", self)
        self.action_en.triggered.connect(lambda: self.change_language('en'))
        self.menu_settings.addAction(self.action_en)

        self.menu_settings.addSeparator()  # 메뉴 구분선

        # 크레딧 액션
        self.action_credit = QAction("프로그램 정보 (Credits)", self)
        self.action_credit.triggered.connect(self.show_credits)
        self.menu_settings.addAction(self.action_credit)

        # 3. OSC 송출 (Client) UI
        self.send_group = QGroupBox()
        send_layout = QGridLayout()

        self.lbl_send_ip = QLabel()
        send_layout.addWidget(self.lbl_send_ip, 0, 0)
        self.ip_entry = QLineEdit("127.0.0.1")
        send_layout.addWidget(self.ip_entry, 0, 1)

        self.lbl_send_port = QLabel()
        send_layout.addWidget(self.lbl_send_port, 0, 2)
        self.port_entry = QLineEdit("5005")
        send_layout.addWidget(self.port_entry, 0, 3)

        self.lbl_addr = QLabel()
        send_layout.addWidget(self.lbl_addr, 1, 0)
        self.addr_entry = QLineEdit("/test/path")
        send_layout.addWidget(self.addr_entry, 1, 1)

        self.lbl_val = QLabel()
        send_layout.addWidget(self.lbl_val, 1, 2)
        self.val_entry = QLineEdit("10, 20.5, hello")
        send_layout.addWidget(self.val_entry, 1, 3)

        self.send_btn = QPushButton()
        self.send_btn.clicked.connect(self.send_msg)
        send_layout.addWidget(self.send_btn, 0, 4, 2, 1)

        self.send_group.setLayout(send_layout)
        main_layout.addWidget(self.send_group)

        # 4. OSC 수신 (Server) UI
        self.recv_group = QGroupBox()
        recv_layout = QVBoxLayout()

        ip_info_layout = QHBoxLayout()
        self.local_ip = self.get_local_ip()
        self.ip_label = QLabel()
        ip_info_layout.addWidget(self.ip_label)
        ip_info_layout.addStretch()
        recv_layout.addLayout(ip_info_layout)

        port_layout = QHBoxLayout()
        self.lbl_recv_port = QLabel()
        port_layout.addWidget(self.lbl_recv_port)
        self.recv_port_entry = QLineEdit("5005")
        port_layout.addWidget(self.recv_port_entry)

        self.server_toggle_btn = QPushButton()
        self.server_toggle_btn.clicked.connect(self.toggle_server)
        port_layout.addWidget(self.server_toggle_btn)
        port_layout.addStretch()
        recv_layout.addLayout(port_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        recv_layout.addWidget(self.log_text)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.clear_btn = QPushButton()
        self.clear_btn.clicked.connect(self.log_text.clear)
        bottom_layout.addWidget(self.clear_btn)
        recv_layout.addLayout(bottom_layout)

        self.recv_group.setLayout(recv_layout)
        main_layout.addWidget(self.recv_group)

        # 5. UI 초기 텍스트 적용 (언어팩 불러오기)
        self.update_ui_text()

    # --- 🌍 설정 기능 함수들 ---

    def change_language(self, lang_code):
        """언어를 변경하고 화면을 새로고침하는 함수"""
        if self.current_lang != lang_code:
            self.current_lang = lang_code
            self.update_ui_text()
            self.log_signal.emit(f"🌐 Language changed to: {'Korean' if lang_code == 'ko' else 'English'}")

    def update_ui_text(self):
        """현재 언어(self.current_lang)에 맞춰 모든 UI 텍스트를 업데이트"""
        t = LANG[self.current_lang]

        self.setWindowTitle(t['title'])
        self.menu_settings.setTitle(t['menu_settings'])
        self.action_credit.setText(t['menu_credit'])

        self.send_group.setTitle(t['send_group'])
        self.lbl_send_ip.setText(t['ip_label'])
        self.lbl_send_port.setText(t['port_label'])
        self.lbl_addr.setText(t['addr_label'])
        self.lbl_val.setText(t['val_label'])
        self.val_entry.setPlaceholderText(t['val_placeholder'])
        self.send_btn.setText(t['send_btn'])

        self.recv_group.setTitle(t['recv_group'])
        self.ip_label.setText(t['my_ip'].format(ip=self.local_ip))
        self.lbl_recv_port.setText(t['my_port'])
        self.server_toggle_btn.setText(t['server_off'] if self.is_server_running else t['server_on'])
        self.clear_btn.setText(t['clear_btn'])

    def show_credits(self):
        """크레딧 팝업 띄우기"""
        t = LANG[self.current_lang]
        QMessageBox.about(self, t['credit_title'], t['credit_body'])

    # --- ⚙️ 기존 통신 핵심 기능들 ---

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def parse_input_values(self, text):
        if not text.strip(): return ""
        tokens = [t.strip() for t in text.split(',')]
        parsed_list = []
        for t in tokens:
            try:
                parsed_list.append(int(t)); continue
            except ValueError:
                pass
            try:
                parsed_list.append(float(t)); continue
            except ValueError:
                pass
            parsed_list.append(t)
        return parsed_list[0] if len(parsed_list) == 1 else parsed_list

    def send_msg(self):
        t = LANG[self.current_lang]
        ip = self.ip_entry.text().strip()
        address = self.addr_entry.text().strip()

        try:
            port = int(self.port_entry.text().strip())
        except ValueError:
            self.log_signal.emit(t['err_port'])
            return

        if not address.startswith("/"):
            self.log_signal.emit(t['err_addr'])
            return

        value = self.parse_input_values(self.val_entry.text())

        try:
            client = udp_client.SimpleUDPClient(ip, port)
            client.send_message(address, value)
            self.log_signal.emit(f"📤 [{ip}:{port}] {address} -> {value}")
        except Exception as e:
            self.log_signal.emit(f"❌ {e}")

    def default_handler(self, address, *args):
        clean_data = ", ".join(map(str, args))
        self.log_signal.emit(f"📥 [{address}] : {clean_data}")

    def toggle_server(self):
        if not self.is_server_running:
            self.start_server()
        else:
            self.stop_server()

    def start_server(self):
        t = LANG[self.current_lang]
        try:
            port = int(self.recv_port_entry.text().strip())
        except ValueError:
            self.log_signal.emit(t['err_port'])
            return

        disp = dispatcher.Dispatcher()
        disp.set_default_handler(self.default_handler)

        try:
            self.server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", port), disp)
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()

            self.is_server_running = True
            self.log_signal.emit(t['msg_server_started'].format(port=port))

            self.server_toggle_btn.setText(t['server_off'])
            self.recv_port_entry.setEnabled(False)
        except Exception:
            self.log_signal.emit(t['msg_server_failed'])

    def stop_server(self):
        t = LANG[self.current_lang]
        if self.server:
            self.server.shutdown()
            self.server.server_close()

            self.server = None
            self.server_thread = None
            self.is_server_running = False
            self.log_signal.emit(t['msg_server_stopped'])

            self.server_toggle_btn.setText(t['server_on'])
            self.recv_port_entry.setEnabled(True)

    def append_log(self, msg):
        self.log_text.append(msg)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = OSCMasterTool()
    ex.show()
    sys.exit(app.exec())