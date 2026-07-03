# src/osc/client.py
from pythonosc import udp_client


class OscClient:
    def __init__(self):
        self.client = None

    def send(self, ip: str, port: int, address: str, value: str):
        """OSC 메시지를 전송합니다."""
        self.client = udp_client.SimpleUDPClient(ip, port)

        # 입력값이 숫자 형태면 float으로 변환하여 전송
        try:
            val = float(value)
        except ValueError:
            val = value

        self.client.send_message(address, val)