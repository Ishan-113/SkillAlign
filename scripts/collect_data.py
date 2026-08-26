import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scraper import generate_realistic_jobs, save_jobs_to_csv, save_jobs_to_mongodb
from skill_gap import load_jobs_from_csv, generate_full_report


def run_full_pipeline():
    print("=" * 60)
    print("PS 26134 - Full Data Collection & Analysis Pipeline")
    print("=" * 60)

    print("\n[STEP 1] Generating realistic job market data...")
    jobs = generate_realistic_jobs(200)
    csv_path = save_jobs_to_csv(jobs, "realistic_jobs.csv")
    print(f"  Generated {len(jobs)} job postings")

    print("\n[STEP 2] Saving to MongoDB Atlas...")
    try:
        save_jobs_to_mongodb(jobs)
    except Exception as e:
        print(f"  MongoDB: Skipped ({e})")
        print("  Set MONGO_URI in backend/.env to enable cloud storage")

    print("\n[STEP 3] Running skill gap analysis...")
    loaded_jobs = load_jobs_from_csv(csv_path)
    report_text, json_data = generate_full_report(loaded_jobs)

    print("\n[STEP 4] Summary:")
    gap = json_data["gap_analysis"]
    print(f"  Total jobs analyzed: {len(loaded_jobs)}")
    print(f"  Industry skills found: {gap['total_industry_skills']}")
    print(f"  Skills in CS curriculum: {gap['total_education_skills']}")
    print(f"  OVERLAP (good): {gap['overlap_count']}")
    print(f"  GAP (bad): {gap['gap_count']}")
    print(f"  Gap severity: {gap['gap_severity']}%")

    print(f"\n  Reports saved to:")
    print(f"    data/realistic_jobs.csv")
    print(f"    reports/skill_gap_report.txt")
    print(f"    reports/skill_gap_data.json")
    print(f"    MongoDB: sih134.jobs collection")

    print("\nDone!")
    return jobs, report_text, json_data


if __name__ == "__main__":
    run_full_pipeline()
