# src/core/config.py
import json
import os

class ConfigManager:
    def __init__(self, filename="config.json"):
        self.filepath = filename
        self.defaults = {
            "language": "ko",
            "send_ip": "127.0.0.1",
            "send_port": "5005",
            "send_address": "/test",
            "send_value": "1.0",
            "recv_ip": "0.0.0.0",
            "recv_port": "5006"
        }
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, val in self.defaults.items():
                        if key not in data:
                            data[key] = val
                    return data
            except Exception:
                return self.defaults.copy()
        return self.defaults.copy()

    def save_config(self):
        try:
            # ensure_safe가 아니라 ensure_ascii=False 가 올바른 옵션입니다.
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def get(self, key):
        return self.config.get(key, self.defaults.get(key))

    def set(self, key, value):
        self.config[key] = str(value)
        self.save_config()