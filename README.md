# SkillAlign - PS 26134

**Smart India Hackathon 2026 | Government of Maharashtra**

Bridging the skill gap between education and industry through data-driven analysis of job market trends.

## Quick Start

### Backend (Python FastAPI)

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Backend runs at: `http://localhost:8000`

### Frontend (HTML/CSS/JS)

Open `frontend/index.html` in a browser, or serve it:

```bash
cd frontend
python -m http.server 3000
```

Frontend runs at: `http://localhost:3000`

### Run Analysis Script

```bash
python scripts/analyze.py
```

Generates report at `reports/insights.txt`.

## Project Structure

```
sih134/
├── backend/
│   ├── app.py              # FastAPI entry point
│   ├── routes/             # API route handlers
│   │   ├── skills.py       # /api/skills endpoints
│   │   ├── experience.py   # /api/experience endpoints
│   │   ├── locations.py    # /api/locations endpoints
│   │   ├── insights.py     # /api/insights endpoint
│   │   └── auth.py         # /api/auth endpoints
│   ├── models/             # Database models
│   ├── services/
│   │   └── database.py     # SQLite connection & init
│   ├── migrations/         # Future DB migrations
│   ├── requirements.txt    # Python dependencies
│   └── .env                # Environment variables
│
├── frontend/
│   ├── index.html          # Main entry point
│   ├── src/
│   │   ├── app.js          # Application logic
│   │   ├── styles/
│   │   │   └── main.css    # All styles
│   │   ├── components/     # Reusable components
│   │   └── pages/          # Page modules
│   └── public/             # Static assets
│
├── data/
│   └── sample_data.csv     # 20 job postings dataset
│
├── scripts/
│   └── analyze.py          # Python analysis script
│
├── reports/
│   └── insights.txt        # Generated analysis report
│
├── docs/                   # Documentation
│
└── .gitignore
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/skills` | GET | Full skills analysis |
| `/api/skills/top` | GET | Top N skills |
| `/api/experience` | GET | Experience distribution |
| `/api/experience/salary` | GET | Salary by experience |
| `/api/locations` | GET | Location distribution |
| `/api/locations/companies` | GET | Companies per location |
| `/api/insights` | GET | Key insights summary |
| `/api/auth/register` | POST | Register user |
| `/api/auth/login` | POST | Login user |

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, SQLite
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Database**: SQLite (local dev), PostgreSQL (production)

## Database Schema

- **jobs**: job_id, title, company, skills, experience_years, location, salary_range, posting_date, job_type
- **users**: user_id, username, email, password_hash, role, created_at
- **analysis_sessions**: session_id, user_id, run_date, results_summary

## License

SIH 2026 - Government of Maharashtra
