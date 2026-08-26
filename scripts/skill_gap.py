import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from curriculum_db import INDIAN_CURRICULUM, get_all_curriculum_names, get_curriculum_skills

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"

INDUSTRY_NEEDS = {
    "programming": ["Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "Kotlin", "Swift"],
    "frameworks": ["React", "Angular", "Vue.js", "Node.js", "Spring Boot", "Django", "Flask", "FastAPI", "Next.js", ".NET"],
    "cloud": ["AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Ansible", "Helm"],
    "data": ["SQL", "NoSQL", "Spark", "Hadoop", "Airflow", "Kafka", "MongoDB", "Redis", "Elasticsearch"],
    "ml_ai": ["TensorFlow", "PyTorch", "Scikit-learn", "NLP", "Computer Vision", "Generative AI", "LLMs", "MLOps"],
    "devops": ["CI/CD", "Jenkins", "GitHub Actions", "GitLab CI", "ArgoCD", "Prometheus", "Grafana", "Datadog"],
    "security": ["OWASP", "SIEM", "Penetration Testing", "Compliance", "Zero Trust", "SOC"],
    "soft_skills": ["System Design", "API Design", "Agile", "Scrum", "Communication", "Leadership"],
    "web": ["HTML5", "CSS3", "SASS", "REST API", "GraphQL", "WebSocket", "PWA"],
    "mobile": ["React Native", "Flutter", "Kotlin", "Swift", "iOS", "Android"],
    "tools": ["Git", "Jira", "Confluence", "VS Code", "Postman", "Docker Desktop"],
}

TECH_TREND_2026 = {
    "hot_skills": [
        "Generative AI / LLMs", "Prompt Engineering", "RAG Systems",
        "AI Agents", "Vector Databases", "MLOps",
        "Cloud Native Development", "Platform Engineering",
        "Cybersecurity (Zero Trust)", "Data Engineering",
        "Full Stack Development", "System Design",
    ],
    "declining_skills": [
        "Manual Testing", "Waterfall methodology",
        "Basic HTML/CSS only", "Legacy PHP",
        "On-premise only skills", "Boilerplate coding",
    ],
    "emerging_areas": [
        "AI/ML Engineering", "Quantum Computing basics",
        "Edge Computing", "Blockchain for Enterprise",
        "Sustainability Tech", "HealthTech AI",
    ],
}


def load_jobs_from_csv(filepath=None):
    if filepath is None:
        filepath = DATA_DIR / "sample_data.csv"
    with open(filepath, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def get_all_industry_skills():
    all_skills = set()
    for category in INDUSTRY_NEEDS.values():
        all_skills.update(category)
    return all_skills


def analyze_skill_gap(jobs, curriculum_name=None):
    industry_skills = Counter()
    for job in jobs:
        for skill in job["skills"].split(","):
            industry_skills[skill.strip()] += 1

    if curriculum_name and curriculum_name in INDIAN_CURRICULUM:
        education_skills = set(INDIAN_CURRICULUM[curriculum_name]["core_skills_taught"])
        education_source = curriculum_name
    else:
        education_skills = set()
        for curriculum in INDIAN_CURRICULUM.values():
            education_skills.update(curriculum["core_skills_taught"])
        education_source = "All Indian Curricula Combined"

    industry_set = set(industry_skills.keys())
    industry_needs_all = get_all_industry_skills()

    gap_skills = industry_needs_all - education_skills
    overlap_skills = industry_needs_all & education_skills
    education_only = education_skills - industry_needs_all

    gap_from_jobs = industry_set - education_skills
    overlap_from_jobs = industry_set & education_skills

    return {
        "curriculum_selected": education_source,
        "total_industry_skills": len(industry_needs_all),
        "total_education_skills": len(education_skills),
        "overlap_count": len(overlap_skills),
        "gap_count": len(gap_skills),
        "gap_skills": sorted(gap_skills),
        "overlap_skills": sorted(overlap_skills),
        "education_only_skills": sorted(education_only),
        "industry_demand": {s: industry_skills[s] for s in sorted(industry_skills, key=industry_skills.get, reverse=True)[:20]},
        "gap_severity": round(len(gap_skills) / max(len(industry_needs_all), 1) * 100, 1),
        "education_skills_list": sorted(education_skills),
    }


def analyze_domain_gap(jobs, curriculum_name=None):
    domain_analysis = defaultdict(lambda: {"industry": Counter()})

    domain_skill_map = {
        "Software Development": ["Python", "Java", "JavaScript", "React", "Node.js", "Docker", "SQL", "Git"],
        "Data & AI": ["Python", "SQL", "TensorFlow", "PyTorch", "Tableau", "Spark", "AWS"],
        "Cloud & DevOps": ["AWS", "Docker", "Kubernetes", "Terraform", "Python", "Jenkins", "Linux"],
        "Cybersecurity": ["Network Security", "Python", "SIEM", "CEH", "Linux", "Cloud Security"],
    }

    for job in jobs:
        title = job.get("title", "")
        skills = [s.strip() for s in job["skills"].split(",")]
        for domain, keywords in domain_skill_map.items():
            if any(kw.lower() in title.lower() for kw in domain.split()):
                for skill in skills:
                    domain_analysis[domain]["industry"][skill] += 1

    if curriculum_name and curriculum_name in INDIAN_CURRICULUM:
        edu_skills = set(INDIAN_CURRICULUM[curriculum_name]["core_skills_taught"])
    else:
        edu_skills = set()
        for curriculum in INDIAN_CURRICULUM.values():
            edu_skills.update(curriculum["core_skills_taught"])

    results = {}
    for domain, data in domain_analysis.items():
        top_industry = data["industry"].most_common(10)
        gap = set(s for s, _ in top_industry) - edu_skills
        results[domain] = {
            "top_industry_skills": [{"skill": s, "count": c} for s, c in top_industry],
            "education_gap": sorted(gap),
            "gap_size": len(gap),
        }

    return results


def generate_recommendations(gap_analysis, domain_gap):
    recommendations = []

    if gap_analysis["gap_severity"] > 30:
        recommendations.append({
            "priority": "HIGH",
            "area": "Curriculum Update",
            "recommendation": f"Over {gap_analysis['gap_severity']}% of industry-needed skills are NOT taught in {gap_analysis['curriculum_selected']}. Immediate curriculum revision needed.",
            "skills_to_add": gap_analysis["gap_skills"][:15],
        })

    hot_not_taught = [s for s in TECH_TREND_2026["hot_skills"]
                      if any(g.lower() in s.lower() for g in gap_analysis["gap_skills"])]
    if hot_not_taught:
        recommendations.append({
            "priority": "HIGH",
            "area": "Emerging Technologies",
            "recommendation": f"Hot 2026 skills missing from your education: {', '.join(hot_not_taught[:5])}",
            "skills_to_add": hot_not_taught,
        })

    recommendations.append({
        "priority": "MEDIUM",
        "area": "Practical Experience",
        "recommendation": "University teaches theory but NOT practical tools. Learn Docker, Git, CI/CD, cloud deployment through projects.",
        "skills_to_add": ["Docker", "Git", "CI/CD", "AWS", "System Design", "API Design"],
    })

    recommendations.append({
        "priority": "LOW",
        "area": "Self-Learning Path",
        "recommendation": "Supplement your degree with NPTEL/Coursera courses on ML, Cloud, and Modern Web Development.",
        "skills_to_add": [],
    })

    return recommendations


def generate_full_report(jobs, curriculum_name=None, output_dir=None):
    if output_dir is None:
        output_dir = REPORT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    gap_analysis = analyze_skill_gap(jobs, curriculum_name)
    domain_gap = analyze_domain_gap(jobs, curriculum_name)
    recommendations = generate_recommendations(gap_analysis, domain_gap)

    report = []
    report.append("=" * 70)
    report.append("PS 26134 - PERSONALIZED SKILL GAP ANALYSIS")
    report.append("Smart India Hackathon 2026 | Government of Maharashtra")
    report.append(f"Curriculum: {gap_analysis['curriculum_selected']}")
    report.append(f"Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("=" * 70)

    report.append(f"\nTotal Jobs Analyzed: {len(jobs)}")
    report.append(f"Industry Skills Required: {gap_analysis['total_industry_skills']}")
    report.append(f"Your Curriculum Teaches: {gap_analysis['total_education_skills']}")
    report.append(f"OVERLAP (you have): {gap_analysis['overlap_count']}")
    report.append(f"GAP (you need to learn): {gap_analysis['gap_count']}")
    report.append(f"Gap Severity: {gap_analysis['gap_severity']}%")

    report.append("\n" + "-" * 70)
    report.append("YOUR CURRICULUM SKILLS (what you learned)")
    report.append("-" * 70)
    for skill in gap_analysis["education_skills_list"]:
        report.append(f"  [HAVE] {skill}")

    report.append("\n" + "-" * 70)
    report.append("SKILLS YOU NEED TO LEARN (GAP)")
    report.append("-" * 70)
    for skill in gap_analysis["gap_skills"]:
        report.append(f"  [LEARN] {skill}")

    report.append("\n" + "-" * 70)
    report.append("TOP INDUSTRY DEMAND")
    report.append("-" * 70)
    for skill, count in sorted(gap_analysis["industry_demand"].items(), key=lambda x: x[1], reverse=True):
        marker = " [GAP]" if skill in gap_analysis["gap_skills"] else " [OK]"
        report.append(f"  {skill:30s} : {count:3d} mentions{marker}")

    report.append("\n" + "-" * 70)
    report.append("DOMAIN-WISE GAP")
    report.append("-" * 70)
    for domain, data in domain_gap.items():
        report.append(f"\n  {domain}:")
        report.append(f"    Top Skills: {', '.join(s['skill'] for s in data['top_industry_skills'][:5])}")
        report.append(f"    Your Gap ({data['gap_size']}): {', '.join(data['education_gap'][:5])}")

    report.append("\n" + "-" * 70)
    report.append("RECOMMENDATIONS")
    report.append("-" * 70)
    for rec in recommendations:
        report.append(f"\n  [{rec['priority']}] {rec['area']}")
        report.append(f"    {rec['recommendation']}")
        if rec["skills_to_add"]:
            report.append(f"    Learn: {', '.join(rec['skills_to_add'][:10])}")

    report.append("\n" + "=" * 70)

    report_text = "\n".join(report)
    report_path = output_dir / "skill_gap_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    json_data = {
        "gap_analysis": gap_analysis,
        "domain_gap": domain_gap,
        "recommendations": recommendations,
        "tech_trends": TECH_TREND_2026,
        "available_curricula": get_all_curriculum_names(),
    }
    json_path = output_dir / "skill_gap_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, default=str)

    print(f"Report saved: {report_path}")
    print(f"JSON data saved: {json_path}")
    return report_text, json_data


if __name__ == "__main__":
    print("Available curricula:")
    for i, name in enumerate(get_all_curriculum_names(), 1):
        print(f"  {i}. {name}")

    choice = input("\nSelect curriculum (number or name): ").strip()
    try:
        idx = int(choice) - 1
        curriculum_name = get_all_curriculum_names()[idx]
    except (ValueError, IndexError):
        curriculum_name = choice if choice in INDIAN_CURRICULUM else None

    print(f"\nUsing curriculum: {curriculum_name or 'All Combined'}")
    jobs = load_jobs_from_csv()
    print(f"Loaded {len(jobs)} jobs")

    report_text, json_data = generate_full_report(jobs, curriculum_name)
    print(report_text)
