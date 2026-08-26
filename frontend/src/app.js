const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api'
    : 'https://skillalign-us1c.onrender.com/api';
let currentPage = 'home';
let cachedJobs = [];

document.addEventListener('DOMContentLoaded', () => {
    loadHeroStats();
});

function navigateTo(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${page}`).classList.add('active');
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.toggle('active', link.dataset.page === page);
    });
    currentPage = page;
    window.scrollTo({ top: 0, behavior: 'smooth' });
    if (page === 'analytics') loadAnalytics();
    if (page === 'dashboard') loadDashboard();
    if (page === 'skillgap') initSkillGap();
}

function toggleNav() {
    document.getElementById('navLinks').classList.toggle('open');
}

async function fetchAPI(endpoint) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error(`API Error (${endpoint}):`, err);
        return null;
    }
}

async function loadHeroStats() {
    const data = await fetchAPI('/insights');
    if (!data || !data.summary) return;
    animateNumber('statJobs', data.summary.total_jobs_analyzed);
    animateNumber('statSkills', data.summary.unique_skills_found);
    animateNumber('statLocations', data.summary.total_locations);
}

function animateNumber(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    let current = 0;
    const step = Math.max(1, Math.ceil(target / 30));
    const interval = setInterval(() => {
        current += step;
        if (current >= target) { current = target; clearInterval(interval); }
        el.textContent = current;
    }, 40);
}

// ==================== ANALYTICS ====================
async function loadAnalytics() {
    const [skills, experience, locations, insights] = await Promise.all([
        fetchAPI('/skills'),
        fetchAPI('/experience'),
        fetchAPI('/locations'),
        fetchAPI('/insights'),
    ]);
    if (skills) renderSkillsChart(skills);
    if (experience) renderExperienceChart(experience);
    if (locations) renderLocationsChart(locations);
    if (insights) renderInsights(insights);
}

function renderSkillsChart(data) {
    const container = document.getElementById('skillsChart');
    if (!data.top_skills || !data.top_skills.length) { container.innerHTML = '<p>No data</p>'; return; }
    const maxCount = data.top_skills[0].count;
    container.innerHTML = `<div class="bar-chart">${data.top_skills.map(s => `
        <div class="bar-row">
            <span class="bar-label">${s.skill}</span>
            <div class="bar-track">
                <div class="bar-fill skill-bar" style="width: ${(s.count / maxCount) * 100}%">${s.count} (${s.percentage}%)</div>
            </div>
        </div>`).join('')}</div>`;
}

function renderExperienceChart(data) {
    const container = document.getElementById('experienceChart');
    const colors = ['#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe'];
    const total = data.distribution.reduce((a, b) => a + b.count, 0) || 1;
    let cumulative = 0;
    const segments = data.distribution.map((d, i) => {
        const pct = (d.count / total) * 100;
        const offset = cumulative;
        cumulative += pct;
        return `<circle cx="100" cy="100" r="70" fill="none" stroke="${colors[i]}" stroke-width="24"
            stroke-dasharray="${pct * 4.4} ${440 - pct * 4.4}" stroke-dashoffset="${-offset * 4.4}"
            style="transition: stroke-dasharray 1s ease ${i * 0.2}s"/>`;
    });
    container.innerHTML = `<div class="donut-container">
        <svg class="donut-svg" viewBox="0 0 200 200">
            <circle cx="100" cy="100" r="70" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="24"/>
            ${segments.join('')}
            <text x="100" y="95" text-anchor="middle" fill="white" font-size="20" font-weight="700">${data.average_experience}</text>
            <text x="100" y="115" text-anchor="middle" fill="#94a3b8" font-size="11">avg years</text>
        </svg>
        <div class="donut-legend">${data.distribution.map((d, i) => `
            <div class="legend-item"><div class="legend-dot" style="background:${colors[i]}"></div>
            <span>${d.range}: ${d.count} (${d.percentage}%)</span></div>`).join('')}
        </div></div>`;
}

function renderLocationsChart(data) {
    const container = document.getElementById('locationsChart');
    if (!data.distribution || !data.distribution.length) { container.innerHTML = '<p>No data</p>'; return; }
    const maxCount = data.distribution[0].count;
    container.innerHTML = `<div class="bar-chart">${data.distribution.map(l => `
        <div class="bar-row">
            <span class="bar-label">${l.location}</span>
            <div class="bar-track">
                <div class="bar-fill loc-bar" style="width: ${(l.count / maxCount) * 100}%">${l.count} (${l.percentage}%)</div>
            </div>
        </div>`).join('')}</div>`;
}

function renderInsights(data) {
    const container = document.getElementById('insightsContainer');
    if (!data.top_insights) { container.innerHTML = '<p>No data</p>'; return; }
    container.innerHTML = `<div class="insights-grid">${data.top_insights.map(ins => `
        <div class="insight-card">
            <h4>${ins.title}</h4>
            <div class="value">${ins.value}</div>
            <div class="detail">${ins.detail}</div>
        </div>`).join('')}</div>`;
}

// ==================== DASHBOARD ====================
async function loadDashboard() {
    const [skillsData, salaryData, locationsData] = await Promise.all([
        fetchAPI('/skills/top?limit=20'),
        fetchAPI('/experience/salary'),
        fetchAPI('/locations'),
    ]);
    if (skillsData) renderHeatmap(skillsData.top_skills);
    if (salaryData) renderSalaryChart(salaryData);
    if (locationsData) populateLocationFilter(locationsData);
    await loadJobTable();
}

function populateLocationFilter(data) {
    const select = document.getElementById('filterLocation');
    select.innerHTML = '<option value="all">All Locations</option>' +
        data.distribution.map(l => `<option value="${l.location}">${l.location}</option>`).join('');
}

function renderHeatmap(skills) {
    const container = document.getElementById('dashSkillsHeatmap');
    if (!skills || !skills.length) { container.innerHTML = '<p>No data</p>'; return; }
    const maxCount = skills[0].count;
    container.innerHTML = `<div class="heatmap">${skills.map(s => {
        const intensity = s.count / maxCount;
        const r = Math.round(37 + (16 - 37) * intensity);
        const g = Math.round(99 + (185 - 99) * intensity);
        const b = Math.round(235 + (129 - 235) * intensity);
        return `<div class="heat-cell" style="background:rgba(${r},${g},${b},0.25);color:rgb(${r},${g},${b})">${s.skill} (${s.count})</div>`;
    }).join('')}</div>`;
}

function renderSalaryChart(data) {
    const container = document.getElementById('dashSalaryExp');
    if (!data.salary_by_experience) { container.innerHTML = '<p>No data</p>'; return; }
    container.innerHTML = `<div style="display:flex;flex-direction:column;gap:12px;">${data.salary_by_experience.map(s => `
        <div style="background:rgba(139,92,246,0.1);border:1px solid rgba(139,92,246,0.2);border-radius:8px;padding:14px;">
            <div style="font-weight:600;color:#a78bfa;margin-bottom:6px;">${s.experience_years} Years Experience</div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;">
                ${s.salary_ranges.map(r => `<span class="skill-tag">${r}</span>`).join('')}
            </div>
        </div>`).join('')}</div>`;
}

async function loadJobTable() {
    const container = document.getElementById('dashJobTable');
    container.innerHTML = '<div class="loading-spinner"></div>';

    const skillsData = await fetchAPI('/skills');
    if (!skillsData || !skillsData.all_skills) {
        container.innerHTML = '<p>Failed to load jobs</p>';
        return;
    }

    const expData = await fetchAPI('/experience/salary');
    const locData = await fetchAPI('/locations/companies');

    cachedJobs = [];
    let id = 1;

    if (expData && expData.salary_by_experience) {
        for (const expGroup of expData.salary_by_experience) {
            for (const salary of expGroup.salary_ranges) {
                cachedJobs.push({
                    id: id++,
                    exp: expGroup.experience_years,
                    salary: salary
                });
            }
        }
    }

    if (locData && locData.companies_by_location) {
        const locs = Object.keys(locData.companies_by_location);
        cachedJobs.forEach((job, i) => {
            job.location = locs[i % locs.length];
            job.company = locData.companies_by_location[job.location][i % locData.companies_by_location[job.location].length];
        });
    }

    container.innerHTML = `
        <table class="job-table">
            <thead><tr><th>#</th><th>Experience</th><th>Company</th><th>Location</th><th>Salary</th></tr></thead>
            <tbody id="jobTableBody"></tbody>
        </table>`;

    renderJobRows();
}

function renderJobRows() {
    const tbody = document.getElementById('jobTableBody');
    if (!tbody) return;
    const locFilter = document.getElementById('filterLocation').value;
    const expFilter = document.getElementById('filterExperience').value;
    const skillFilter = document.getElementById('filterSkill').value.toLowerCase();

    let filtered = cachedJobs;
    if (locFilter !== 'all') filtered = filtered.filter(j => j.location === locFilter);
    if (expFilter !== 'all') {
        if (expFilter === '0-2') filtered = filtered.filter(j => j.exp <= 2);
        else if (expFilter === '3-5') filtered = filtered.filter(j => j.exp >= 3 && j.exp <= 5);
        else if (expFilter === '6+') filtered = filtered.filter(j => j.exp >= 6);
    }

    tbody.innerHTML = filtered.slice(0, 50).map(j => `
        <tr>
            <td>${j.id}</td>
            <td>${j.exp} yrs</td>
            <td>${j.company || '-'}</td>
            <td>${j.location || '-'}</td>
            <td><span class="skill-tag">${j.salary || '-'}</span></td>
        </tr>`).join('');
}

function applyFilters() {
    renderJobRows();
}

// ==================== SKILL GAP ====================
const EDUCATION_TREE = {
    "12th / Higher Secondary": {
        type: "school",
        options: [
            { name: "CBSE - Science (PCM/PCB)", skills: ["Mathematics", "Physics", "Chemistry", "English", "Computer Science basics"] },
            { name: "CBSE - Commerce", skills: ["Accountancy", "Business Studies", "Economics", "Mathematics", "English"] },
            { name: "State Board - Science", skills: ["Mathematics", "Physics", "Chemistry", "English", "Regional Language"] },
            { name: "ISC - Science", skills: ["Mathematics", "Physics", "Chemistry", "Computer Science", "English"] },
            { name: "NIOS - Science", skills: ["Mathematics", "Physics", "Chemistry", "English", "Data Entry"] },
        ]
    },
    "Diploma (Polytechnic)": {
        type: "diploma",
        filter: ["Diploma in CS - Karnataka State Board", "Diploma in CS - Maharashtra State Board",
                 "Diploma in CS - Tamil Nadu State Board", "Diploma in CS - VJTI Mumbai",
                 "Polytechnic Diploma - Generic"]
    },
    "Bachelor's Degree (B.E./B.Tech/BCA/B.Sc)": {
        type: "degree",
        filter: ["B.E. CSE - VTU (22 Series)", "B.E. CSE - Anna University", "B.Tech CSE - IIT Bombay",
                 "B.Tech CSE - IIT Delhi", "B.Tech CSE - IIT Madras", "B.Tech CSE - NIT Trichy",
                 "B.E. CSE - BITS Pilani", "B.E. CSE - IISc Bengaluru", "B.Tech CSE - JNU New Delhi",
                 "B.Tech CSE - MAHE Manipal", "B.Tech CSE - Jamia Millia Islamia",
                 "B.Tech CSE - BHU Varanasi", "B.Tech CSE - Amrita Vishwa Vidyapeetham",
                 "B.Tech CSE - Jadavpur University", "B.Tech CSE - AMU Aligarh",
                 "B.Tech CSE - LPU Jalandhar", "B.Tech CSE - SRM University",
                 "B.Tech CSE - SLIET", "B.Tech CSE - Autonomous (Generic)",
                 "BCA - Bangalore University", "BCA - Madras University",
                 "BCA - IGNOU (Distance)", "Online BCA - Amity University",
                 "B.Sc Computer Science - Delhi University", "B.Sc IT - Mumbai University"]
    },
    "Master's Degree (M.Tech/MCA/M.Sc)": {
        type: "postgraduate",
        filter: ["MCA - VTU", "MCA - JNTU Hyderabad", "Online MSc Data Science - Manipal"]
    },
    "Online / Self-Learned": {
        type: "online",
        filter: ["Online Certification - Coursera/Udemy (Self-Learned)", "Online Certification - NPTEL (Self-Learned)"]
    }
};

let allCurriculaData = [];

async function initSkillGap() {
    const data = await fetchAPI('/skill-gap/curricula');
    if (!data || !data.curricula) return;
    allCurriculaData = data.curricula;

    const levelSelect = document.getElementById('educationLevel');
    levelSelect.innerHTML = '<option value="">-- Select your education level --</option>' +
        Object.keys(EDUCATION_TREE).map(k => `<option value="${k}">${k}</option>`).join('');

    document.getElementById('educationSub').innerHTML = '<option value="">-- First select level above --</option>';
    document.getElementById('educationSub').disabled = true;
    document.getElementById('curriculumInfo').style.display = 'none';
    document.getElementById('gapResults').style.display = 'none';
}

function onLevelChange() {
    const level = document.getElementById('educationLevel').value;
    const subSelect = document.getElementById('educationSub');
    const infoDiv = document.getElementById('curriculumInfo');
    const gapResults = document.getElementById('gapResults');

    if (!level) {
        subSelect.innerHTML = '<option value="">-- First select level above --</option>';
        subSelect.disabled = true;
        infoDiv.style.display = 'none';
        gapResults.style.display = 'none';
        return;
    }

    const tree = EDUCATION_TREE[level];

    if (tree.type === 'school') {
        subSelect.disabled = false;
        subSelect.innerHTML = '<option value="">-- Select your board/stream --</option>' +
            tree.options.map(o => `<option value="__custom__" data-skills='${JSON.stringify(o.skills)}' data-name="${o.name}">${o.name}</option>`).join('');
    } else {
        const filtered = allCurriculaData.filter(c => tree.filter.includes(c.name));
        subSelect.disabled = false;
        subSelect.innerHTML = '<option value="">-- Select your university --</option>' +
            filtered.map(c => `<option value="${c.name}">${c.name} (${c.skills_count} skills)</option>`).join('');
    }
}

async function onSubChange() {
    const level = document.getElementById('educationLevel').value;
    const subSelect = document.getElementById('educationSub');
    const subVal = subSelect.value;
    const infoDiv = document.getElementById('curriculumInfo');
    const gapResults = document.getElementById('gapResults');

    if (!subVal) {
        infoDiv.style.display = 'none';
        gapResults.style.display = 'none';
        return;
    }

    if (subVal === '__custom__') {
        const selected = subSelect.options[subSelect.selectedIndex];
        const skills = JSON.parse(selected.dataset.skills);
        const name = selected.dataset.name;
        const skillsParam = skills.join(',');
        const data = await fetchAPI(`/skill-gap/personalized?skills=${encodeURIComponent(skillsParam)}&name=${encodeURIComponent(name)}`);
        if (!data || data.error) {
            infoDiv.innerHTML = `<p style="color:#ef4444">${data?.error || 'Failed to load'}</p>`;
            return;
        }
        const ga = data.gap_analysis;
        infoDiv.innerHTML = `<div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:12px;">
            <div class="legend-item"><span style="color:#10b981;font-weight:700">${ga.total_education_skills}</span> skills taught</div>
            <div class="legend-item"><span style="color:#ef4444;font-weight:700">${ga.gap_count}</span> skills missing</div>
            <div class="legend-item"><span style="color:#3b82f6;font-weight:700">${ga.overlap_count}</span> skills overlap</div>
            <div class="legend-item"><span style="color:${ga.gap_severity > 40 ? '#ef4444' : '#f59e0b'};font-weight:700">${ga.gap_severity}%</span> gap severity</div>
        </div>`;
        renderGapSummary(ga);
        renderHaveSkills(ga);
        renderNeedSkills(ga);
        renderGapComparison(ga);
        if (data.domain_gap) renderDomainGap(data.domain_gap);
        if (data.recommendations) renderGapRecommendations(data.recommendations);
        return;
    }

    gapResults.style.display = 'block';
    infoDiv.style.display = 'block';
    infoDiv.innerHTML = '<div class="loading-spinner"></div>';

    const data = await fetchAPI(`/skill-gap/personalized?curriculum=${encodeURIComponent(subVal)}`);
    if (!data || data.error) {
        infoDiv.innerHTML = `<p style="color:#ef4444">${data?.error || 'Failed to load'}</p>`;
        return;
    }

    const ga = data.gap_analysis;
    infoDiv.innerHTML = `<div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:12px;">
        <div class="legend-item"><span style="color:#10b981;font-weight:700">${ga.total_education_skills}</span> skills taught</div>
        <div class="legend-item"><span style="color:#ef4444;font-weight:700">${ga.gap_count}</span> skills missing</div>
        <div class="legend-item"><span style="color:#3b82f6;font-weight:700">${ga.overlap_count}</span> skills overlap</div>
        <div class="legend-item"><span style="color:${ga.gap_severity > 40 ? '#ef4444' : '#f59e0b'};font-weight:700">${ga.gap_severity}%</span> gap severity</div>
    </div>`;

    renderGapSummary(ga);
    renderHaveSkills(ga);
    renderNeedSkills(ga);
    renderGapComparison(ga);
    if (data.domain_gap) renderDomainGap(data.domain_gap);
    if (data.recommendations) renderGapRecommendations(data.recommendations);
}

function renderGapSummary(ga) {
    document.getElementById('gapSummary').innerHTML = `<div class="insights-grid">
        <div class="insight-card"><h4>Curriculum</h4><div class="value" style="font-size:1.1rem">${ga.curriculum_selected}</div><div class="detail">${ga.total_education_skills} skills in your syllabus</div></div>
        <div class="insight-card"><h4>Industry Requires</h4><div class="value">${ga.total_industry_skills}</div><div class="detail">unique skills across job postings</div></div>
        <div class="insight-card"><h4>Your Gap</h4><div class="value" style="color:#ef4444">${ga.gap_count} skills</div><div class="detail">you need to learn these yourself</div></div>
        <div class="insight-card"><h4>Gap Severity</h4><div class="value" style="color:${ga.gap_severity > 40 ? '#ef4444' : '#f59e0b'}">${ga.gap_severity}%</div><div class="detail">of industry skills NOT in your curriculum</div></div>
    </div>`;
}

function renderHaveSkills(ga) {
    document.getElementById('gapHaveSkills').innerHTML = `<div class="heatmap">${ga.education_skills_list.map(s =>
        `<div class="heat-cell" style="background:rgba(16,185,129,0.2);color:#10b981">${s}</div>`).join('')}</div>`;
}

function renderNeedSkills(ga) {
    document.getElementById('gapNeedSkills').innerHTML = `<div class="heatmap">${ga.gap_skills.map(s =>
        `<div class="heat-cell" style="background:rgba(239,68,68,0.2);color:#ef4444">${s}</div>`).join('')}</div>`;
}

function renderGapComparison(ga) {
    const entries = Object.entries(ga.industry_demand);
    if (!entries.length) return;
    const maxCount = Math.max(...entries.map(e => e[1]));
    document.getElementById('gapComparison').innerHTML = `<div class="bar-chart">${entries.map(([skill, count]) => {
        const has = ga.overlap_skills.includes(skill);
        return `<div class="bar-row">
            <span class="bar-label" style="min-width:140px">${skill} ${has ? '<span style="color:#10b981">[OK]</span>' : '<span style="color:#ef4444">[GAP]</span>'}</span>
            <div class="bar-track"><div class="bar-fill" style="width:${(count/maxCount)*100}%;background:${has ? 'linear-gradient(90deg,#10b981,#34d399)' : 'linear-gradient(90deg,#ef4444,#f87171)'}">${count}</div></div>
        </div>`;
    }).join('')}</div>`;
}

function renderDomainGap(domainGap) {
    document.getElementById('gapDomainAnalysis').innerHTML = `<div class="insights-grid">${Object.entries(domainGap).map(([domain, data]) => `
        <div class="insight-card"><h4>${domain}</h4>
        <div class="value" style="font-size:1rem">Top: ${data.top_industry_skills.slice(0,3).map(s=>s.skill).join(', ')}</div>
        <div class="detail" style="color:#ef4444">Gap: ${data.education_gap.length ? data.education_gap.slice(0,5).join(', ') : 'None'}</div></div>
    `).join('')}</div>`;
}

function renderGapRecommendations(recommendations) {
    document.getElementById('gapRecommendations').innerHTML = `<div class="insights-grid">${recommendations.map(rec => `
        <div class="insight-card" style="border-color:${rec.priority === 'HIGH' ? 'rgba(239,68,68,0.4)' : rec.priority === 'MEDIUM' ? 'rgba(245,158,11,0.4)' : 'rgba(59,130,246,0.4)'}">
        <h4 style="color:${rec.priority === 'HIGH' ? '#ef4444' : rec.priority === 'MEDIUM' ? '#f59e0b' : '#3b82f6'}">[${rec.priority}] ${rec.area}</h4>
        <div class="detail">${rec.recommendation}</div>
        ${rec.skills_to_add.length ? `<div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:4px;">${rec.skills_to_add.map(s => `<span class="skill-tag">${s}</span>`).join('')}</div>` : ''}
        </div>`).join('')}</div>`;
}

window.addEventListener('scroll', () => {
    const navbar = document.getElementById('navbar');
    navbar.style.background = window.scrollY > 50 ? 'rgba(15, 23, 42, 0.95)' : 'rgba(15, 23, 42, 0.85)';
});
