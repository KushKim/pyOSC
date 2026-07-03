# src/osc/client.py
from pythonosc import udp_client

class OscClient:
    def __init__(self):
        self.client = None

    def send(self, ip: str, port: int, address: str, value):
        """OSC 메시지를 전송합니다. (타입 강제 변환 제거)"""
        self.client = udp_client.SimpleUDPClient(ip, port)
        self.client.send_message(address, value)