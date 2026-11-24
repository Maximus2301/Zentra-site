"""
Convenience CLI for Dr. Himani J Bharti Personal Brand Engine.
Generates, renders, and dispatches clinical authority Instagram carousels to Telegram.

Usage:
  python run_drhimani.py --topic "When Is the Right Time for Cataract Surgery?"
  python run_drhimani.py --topic "Choosing Between Monofocal and Multifocal IOLs" --wait
  python run_drhimani.py --topic "Why Diabetics Need Annual Dilated Retina Exams" --no-telegram
"""
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PERSONAL_BRAND_ROOT = CURRENT_DIR.parent
WORKSPACE_ROOT = PERSONAL_BRAND_ROOT.parent

if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from Personal_Brand.main import run_pipeline
import argparse

def main():
    parser = argparse.ArgumentParser(description="Dr. Himani J Bharti — Clinical Instagram Carousel Generator")
    parser.add_argument(
        "--topic",
        type=str,
        default="When Is the Right Time for Cataract (Motiabind) Surgery?",
        help="Medical topic or patient FAQ to generate",
    )
    parser.add_argument(
        "--pillar",
        type=str,
        default="cataract_iol_guidance",
        help="Pillar ID: cataract_iol_guidance, diabetic_retina_health, pediatric_myopia_screens, glaucoma_preventive_care",
    )
    parser.add_argument("--no-telegram", action="store_true", help="Render locally without sending to Telegram")
    parser.add_argument("--wait", action="store_true", help="Wait for mobile interactive review decision")
    parser.add_argument("--timeout", type=int, default=120, help="Wait timeout in seconds")

    args = parser.parse_args()

    run_pipeline(
        topic=args.topic,
        pillar_id=args.pillar,
        brand_id="drhimanibharti",
        send_telegram=not args.no_telegram,
        wait_for_decision=args.wait,
        wait_timeout=args.timeout,
    )

if __name__ == "__main__":
    main()
