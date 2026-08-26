import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")

from services.curriculum_db import seed_curricula, get_all_curricula_from_db


if __name__ == "__main__":
    print("Seeding curriculum data to MongoDB Atlas...")
    count = seed_curricula()

    print("\nVerifying...")
    curricula = get_all_curricula_from_db()
    print(f"Total curricula in MongoDB: {len(curricula)}")
    for c in curricula:
        print(f"  - {c['name']} ({c['type']}, {len(c['all_skills'])} skills)")

    print("\nDone!")
