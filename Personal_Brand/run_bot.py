"""
Starts the Personal Brand Autonomous Telegram Agent & Onboarding Bot.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Personal_Brand.hitl.onboarding_bot import create_bot_app

if __name__ == "__main__":
    print("👑 Starting Personal Brand Agent on Telegram (@Vyantecbot)...")
    app = create_bot_app()
    app.run_polling()
