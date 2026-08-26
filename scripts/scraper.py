import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
    },
]

INDIAN_CITIES = [
    "Bangalore", "Mumbai", "Pune", "Hyderabad", "Chennai",
    "Noida", "Gurgaon", "Delhi", "Kolkata", "Ahmedabad",
    "Jaipur", "Kochi", "Coimbatore", "Indore", "Bhopal",
]

TOP_INDIAN_COMPANIES = [
    "TCS", "Infosys", "Wipro", "HCL Technologies", "Tech Mahindra",
    "Accenture", "Cognizant", "IBM India", "Amazon India", "Google India",
    "Microsoft India", "Flipkart", "Razorpay", "Swiggy", "Zomato",
    "Paytm", "BYJU'S", "Ola", "Reliance Jio", "Samsung India",
    "SAP India", "Oracle India", "Cisco India", "Intel India", "Adobe India",
    "Goldman Sachs India", "Morgan Stanley India", "Deloitte India",
    "EY India", "PwC India", "KPMG India", "Atlassian India",
]

JOB_TITLES_BY_DOMAIN = {
    "Software Development": [
        "Full Stack Developer", "Backend Developer", "Frontend Developer",
        "Software Engineer", "Senior Software Engineer", "Lead Developer",
        "Java Developer", "Python Developer", "React Developer",
        "Node.js Developer", "Android Developer", "iOS Developer",
    ],
    "Data & AI": [
        "Data Analyst", "Data Scientist", "Data Engineer",
        "Machine Learning Engineer", "AI Research Scientist",
        "Business Intelligence Analyst", "MLOps Engineer",
        "NLP Engineer", "Computer Vision Engineer",
    ],
    "Cloud & DevOps": [
        "Cloud Architect", "DevOps Engineer", "SRE",
        "Platform Engineer", "Infrastructure Engineer",
        "Kubernetes Engineer", "AWS Solutions Architect",
    ],
    "Cybersecurity": [
        "Cybersecurity Analyst", "Security Engineer",
        "Penetration Tester", "SOC Analyst", "Security Architect",
    ],
    "Design": [
        "UI/UX Designer", "Product Designer", "UX Researcher",
        "Interaction Designer", "Visual Designer",
    ],
    "Management": [
        "Product Manager", "Project Manager", "Scrum Master",
        "Engineering Manager", "Technical Program Manager",
    ],
}

SKILLS_BY_DOMAIN = {
    "Software Development": {
        "programming": ["Python", "Java", "JavaScript", "TypeScript", "C++", "Go", "Rust", "Kotlin", "Swift"],
        "frameworks": ["React", "Angular", "Vue.js", "Node.js", "Spring Boot", "Django", "Flask", "FastAPI", "Next.js"],
        "databases": ["MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch", "DynamoDB"],
        "tools": ["Git", "Docker", "Kubernetes", "Jenkins", "CI/CD", "REST API", "GraphQL", "Microservices"],
        "concepts": ["Data Structures", "Algorithms", "System Design", "OOP", "Design Patterns"],
    },
    "Data & AI": {
        "programming": ["Python", "R", "SQL", "Scala", "Julia"],
        "ml_frameworks": ["TensorFlow", "PyTorch", "Scikit-learn", "Keras", "XGBoost", "Hugging Face"],
        "data_tools": ["Pandas", "NumPy", "Spark", "Hadoop", "Airflow", "dbt", "Kafka"],
        "visualization": ["Tableau", "Power BI", "Matplotlib", "Seaborn", "Plotly", "Looker"],
        "cloud_ai": ["AWS SageMaker", "Google Vertex AI", "Azure ML", "MLflow", "Weights & Biases"],
    },
    "Cloud & DevOps": {
        "cloud": ["AWS", "Azure", "GCP", "DigitalOcean", "Heroku"],
        "containers": ["Docker", "Kubernetes", "Helm", "Istio", "Podman"],
        "iac": ["Terraform", "Pulumi", "CloudFormation", "Ansible", "Chef"],
        "monitoring": ["Prometheus", "Grafana", "Datadog", "New Relic", "ELK Stack"],
        "cicd": ["Jenkins", "GitHub Actions", "GitLab CI", "ArgoCD", "Spinnaker"],
    },
    "Cybersecurity": {
        "core": ["Network Security", "Application Security", "Cloud Security", "Incident Response"],
        "tools": ["SIEM", "Wireshark", "Nmap", "Burp Suite", "Metasploit", "Splunk"],
        "certifications": ["CEH", "CISSP", "CompTIA Security+", "OSCP", "CISA"],
        "compliance": ["GDPR", "ISO 27001", "SOC 2", "NIST", "PCI DSS"],
    },
    "Design": {
        "design_tools": ["Figma", "Adobe XD", "Sketch", "InVision", "Zeplin"],
        "ui_skills": ["HTML", "CSS", "JavaScript", "Responsive Design", "Wireframing"],
        "ux_skills": ["User Research", "Usability Testing", "A/B Testing", "Prototyping", "Information Architecture"],
        "visual": ["Adobe Photoshop", "Adobe Illustrator", "After Effects", "Motion Design"],
    },
    "Management": {
        "methodology": ["Agile", "Scrum", "Kanban", "Waterfall", "SAFe"],
        "tools": ["Jira", "Confluence", "Trello", "Asana", "Monday.com"],
        "skills": ["SQL", "Excel", "Data Analysis", "Stakeholder Management", "Communication"],
        "product": ["Product Strategy", "Roadmap Planning", "User Stories", "Market Research", "OKRs"],
    },
}

SALARY_RANGES = {
    "Fresher (0-2 yrs)": ["3-5 LPA", "4-6 LPA", "5-8 LPA", "6-10 LPA"],
    "Mid-level (3-5 yrs)": ["8-12 LPA", "10-15 LPA", "12-18 LPA", "15-22 LPA"],
    "Senior (6-8 yrs)": ["15-22 LPA", "18-25 LPA", "20-30 LPA", "22-35 LPA"],
    "Lead (8+ yrs)": ["25-40 LPA", "30-50 LPA", "35-60 LPA", "40-70 LPA"],
}


def get_salary_range(experience):
    if experience <= 2:
        return random.choice(SALARY_RANGES["Fresher (0-2 yrs)"])
    elif experience <= 5:
        return random.choice(SALARY_RANGES["Mid-level (3-5 yrs)"])
    elif experience <= 8:
        return random.choice(SALARY_RANGES["Senior (6-8 yrs)"])
    else:
        return random.choice(SALARY_RANGES["Lead (8+ yrs)"])


def get_skills_for_domain(domain, count=None):
    if domain not in SKILLS_BY_DOMAIN:
        return []
    all_skills = []
    for category in SKILLS_BY_DOMAIN[domain].values():
        all_skills.extend(category)
    if count is None:
        count = random.randint(3, 6)
    return random.sample(all_skills, min(count, len(all_skills)))


def generate_realistic_jobs(target_count=200):
    jobs = []
    domains = list(JOB_TITLES_BY_DOMAIN.keys())

    for i in range(1, target_count + 1):
        domain = random.choice(domains)
        title = random.choice(JOB_TITLES_BY_DOMAIN[domain])
        company = random.choice(TOP_INDIAN_COMPANIES)
        location = random.choice(INDIAN_CITIES)
        experience = random.choices(
            [random.randint(0, 2), random.randint(3, 5), random.randint(6, 8), random.randint(9, 12)],
            weights=[30, 40, 20, 10]
        )[0]
        skills = get_skills_for_domain(domain)
        salary = get_salary_range(experience)
        days_ago = random.randint(0, 90)
        posting_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        job_type = random.choices(["Full-time", "Contract", "Remote"], weights=[70, 15, 15])[0]

        jobs.append({
            "job_id": i,
            "title": title,
            "company": company,
            "skills": ", ".join(skills),
            "experience_years": experience,
            "location": location,
            "salary_range": salary,
            "posting_date": posting_date,
            "job_type": job_type,
            "domain": domain,
        })

    return jobs


def scrape_naukri(keyword="python developer", location="bangalore", pages=2):
    jobs = []
    base_url = "https://www.naukri.com/jobapi/v3/search"

    for page in range(pages):
        params = {
            "noOfResults": 20,
            "urlType": "search_by_key_loc",
            "searchType": "adv",
            "keyword": keyword,
            "location": location,
            "pageNo": page + 1,
        }
        try:
            headers = random.choice(HEADERS_LIST)
            resp = requests.get(base_url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("jobDetails", []):
                    jobs.append({
                        "title": item.get("title", ""),
                        "company": item.get("companyName", ""),
                        "skills": ", ".join(item.get("skillSet", [])),
                        "experience_years": item.get("experienceDetail", {}).get("minExp", 0),
                        "location": item.get("placeholders", [{}])[0].get("label", ""),
                        "salary_range": item.get("placeholders", [{}])[2].get("label", "") if len(item.get("placeholders", [])) > 2 else "",
                        "source": "naukri",
                    })
            time.sleep(random.uniform(2, 5))
        except Exception as e:
            print(f"Naukri scrape error page {page+1}: {e}")
    return jobs


def scrape_indeed(query="python developer", location="Bangalore", pages=2):
    jobs = []
    base_url = "https://in.indeed.com/jobs"

    for page in range(pages):
        params = {
            "q": query,
            "l": location,
            "start": page * 10,
        }
        try:
            headers = random.choice(HEADERS_LIST)
            resp = requests.get(base_url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_="job_seen_beacon")
                for card in cards:
                    title_el = card.find("h2", class_="jobTitle")
                    company_el = card.find("span", class_="companyName")
                    location_el = card.find("div", class_="companyLocation")
                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    loc = location_el.get_text(strip=True) if location_el else ""
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "source": "indeed",
                    })
            time.sleep(random.uniform(3, 6))
        except Exception as e:
            print(f"Indeed scrape error page {page+1}: {e}")
    return jobs


def save_jobs_to_csv(jobs, filename="scraped_jobs.csv"):
    filepath = DATA_DIR / filename
    fieldnames = ["job_id", "title", "company", "skills", "experience_years",
                  "location", "salary_range", "posting_date", "job_type", "domain"]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(jobs)

    print(f"Saved {len(jobs)} jobs to {filepath}")
    return filepath


def save_jobs_to_mongodb(jobs):
    import pymongo
    from dotenv import load_dotenv
    import os

    load_dotenv()
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("MONGO_DB_NAME", "sih134")

    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db["jobs"]

    collection.create_index("job_id", unique=True, sparse=True)
    collection.create_index("skills")
    collection.create_index("location")
    collection.create_index("experience_years")

    inserted = 0
    for job in jobs:
        try:
            collection.update_one(
                {"job_id": job["job_id"]},
                {"$set": job},
                upsert=True
            )
            inserted += 1
        except Exception as e:
            print(f"  Skip job {job.get('job_id')}: {e}")

    print(f"Saved {inserted} jobs to MongoDB ({DB_NAME}.jobs)")
    client.close()
    return inserted


if __name__ == "__main__":
    print("=" * 60)
    print("PS 26134 - Job Data Scraper")
    print("=" * 60)

    print("\n[1/4] Generating realistic Indian job market data...")
    jobs = generate_realistic_jobs(200)
    print(f"  Generated {len(jobs)} job postings")

    print("\n[2/4] Attempting live scrape from job sites...")
    try:
        naukri_jobs = scrape_naukri("python developer", "bangalore", pages=1)
        print(f"  Naukri: Found {len(naukri_jobs)} jobs")
    except Exception as e:
        print(f"  Naukri: Skipped ({e})")
        naukri_jobs = []

    try:
        indeed_jobs = scrape_indeed("python developer", "Bangalore", pages=1)
        print(f"  Indeed: Found {len(indeed_jobs)} jobs")
    except Exception as e:
        print(f"  Indeed: Skipped ({e})")
        indeed_jobs = []

    all_jobs = jobs + naukri_jobs + indeed_jobs
    for i, job in enumerate(all_jobs, 1):
        job["job_id"] = i

    print(f"\n[3/4] Saving {len(all_jobs)} jobs to CSV...")
    save_jobs_to_csv(all_jobs)

    print("\n[4/4] Saving to MongoDB Atlas...")
    try:
        save_jobs_to_mongodb(all_jobs)
    except Exception as e:
        print(f"  MongoDB: Skipped ({e})")
        print("  Set MONGO_URI in backend/.env to enable cloud storage")

    print("\nDone!")
