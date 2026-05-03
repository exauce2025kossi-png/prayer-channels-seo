"""Base class for all MediaAI Corp agents."""
from datetime import datetime


class BaseAgent:
    def __init__(self, name: str, emoji: str, role: str):
        self.name  = name
        self.emoji = emoji
        self.role  = role
        self.logs  = []

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {self.emoji} {self.name}: {msg}"
        self.logs.append(line)
        print(line)
        return line

    def header(self, title=""):
        label = title or self.role
        print(f"\n{'─'*55}")
        print(f"  {self.emoji}  {self.name} — {label}")
        print(f"{'─'*55}")

    def success(self, msg):
        self.log(f"✅ {msg}")

    def warn(self, msg):
        self.log(f"⚠️  {msg}")

    def error(self, msg):
        self.log(f"❌ {msg}")
