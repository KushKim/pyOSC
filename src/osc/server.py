# src/osc/server.py
import threading
from PyQt6.QtCore import QObject, pyqtSignal
from pythonosc import dispatcher, osc_server


class OscServer(QObject):
    # UI로 로그 텍스트를 전달하기 위한 시그널
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.server = None
        self.server_thread = None
        self.is_running = False

    def start(self, ip: str, port: int):
        """OSC 수신 서버를 시작합니다."""
        if self.is_running:
            return

        disp = dispatcher.Dispatcher()
        disp.set_default_handler(self.osc_handler)

        self.server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        self.is_running = True
        self.log_signal.emit(f"=== Server Started ({ip}:{port}) ===")

    def stop(self):
        """OSC 수신 서버를 종료합니다."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None

        self.is_running = False
        self.log_signal.emit("=== Server Stopped ===")

    def osc_handler(self, address, *args):
        """OSC 메시지가 수신될 때마다 호출되는 콜백"""
        msg = f"[RECV] {address} | {args}"
        self.log_signal.emit(msg)