import socket
from concurrent.futures import ThreadPoolExecutor
from pythonosc import udp_client
from pythonosc.osc_message_builder import OscMessageBuilder


class OscClient:
    def __init__(self):
        self.client = None
        # 다중 전송을 위해 재사용할 UDP 소켓을 미리 생성해 둡니다.
        self._shared_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, ip: str, port: int, address: str, value):
        """기존 단일 OSC 메시지 전송 (하위 호환성을 위해 유지)"""
        self.client = udp_client.SimpleUDPClient(ip, port)
        self.client.send_message(address, value)

    def _send_dgram(self, ip: str, port: int, dgram: bytes):
        """스레드 내부에서 바이트(bytes) 데이터만 쏘는 가벼운 전송 함수"""
        try:
            self._shared_sock.sendto(dgram, (ip, port))
        except Exception as e:
            print(f"[SEND ERROR] {ip}:{port} 전송 실패: {e}")

    def send_concurrently(self, targets):
        """
        여러 IP에 각각 다른 OSC 메시지를 최대한 동시에 전송합니다.

        targets 예시:
        [
            ("192.168.0.10", 8000, "/play", 1),
            ("192.168.0.20", 9000, "/color", ["red", 255]),
        ]
        """
        if not targets:
            return

        tasks = []

        # 1. 전송 직전에 딜레이가 없도록 모든 메시지를 미리 빌드(Build)
        for ip, port, address, value in targets:
            builder = OscMessageBuilder(address=address)

            # value가 리스트나 튜플 형태면 여러 인자로 나누어서 추가
            if isinstance(value, (list, tuple)):
                for val in value:
                    builder.add_arg(val)
            # 단일 값이면 그대로 추가
            else:
                builder.add_arg(value)

            msg = builder.build()
            # pythonosc의 .dgram 속성을 쓰면 순수 바이트 데이터로 변환됨
            tasks.append((ip, port, msg.dgram))

        # 2. 스레드 풀을 이용해 미리 준비된 데이터들을 일제히 발사
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            for ip, port, dgram in tasks:
                executor.submit(self._send_dgram, ip, port, dgram)