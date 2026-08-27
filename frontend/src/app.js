const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api'
    : 'https://skillalign-us1c.onrender.com/api';
let currentPage = 'home';
let cachedJobs = [];

document.addEventListener('DOMContentLoaded', () => {
    loadHeroStats();
    loadFreshness();
});

async function loadFreshness() {
    const data = await fetchAPI('/data/freshness');
    const banner = document.getElementById('freshnessBar');
    if (!banner || !data) return;
    const jobsStatus = data.jobs?.last_update_status;
    const jobsOk = jobsStatus === 'success' || jobsStatus === 'no_data';
    const barrier = document.getElementById('freshnessJobs');
    const currBar = document.getElementById('freshnessCurr');
    if (barrier) {
        barrier.innerHTML = data.jobs?.last_update
            ? `Jobs last updated: ${new Date(data.jobs.last_update).toLocaleString()} · ${data.jobs.active_jobs ?? 0} active jobs`
            : 'Jobs: not yet updated';
        barrier.classList.toggle('stale', !jobsOk);
    }
    if (currBar) {
        currBar.innerHTML = data.curriculum?.last_check
            ? `Curriculum last checked: ${new Date(data.curriculum.last_check).toLocaleString()}`
            : 'Curriculum: not yet checked';
    }
}

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
    if (page === 'industry') loadIndustry();
    if (page === 'recommendations') loadRecommendations();
    if (page === 'careerguidance') loadCareerGuidance();
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

async function fetchPOST(endpoint, body) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
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

// ==================== SHARED FILTER HELPERS ====================
let districtOptions = [];
let sectorOptions = [];

async function ensureFilters() {
    if (districtOptions.length || sectorOptions.length) return;
    const [d, s] = await Promise.all([fetchAPI('/districts'), fetchAPI('/sectors')]);
    districtOptions = (d && d.districts) ? d.districts : [];
    sectorOptions = (s && s.sectors) ? s.sectors : [];
    return { districtOptions, sectorOptions };
}

function fillDistrictSelect(el) {
    if (!el) return;
    el.innerHTML = '<option value="">All Districts</option>' +
        districtOptions.map(x => `<option value="${x.district}">${x.district}</option>`).join('');
}

function fillSectorSelect(el, { includeAll = true } = {}) {
    if (!el) return;
    const all = includeAll ? '<option value="">All Sectors</option>' : '<option value="">Any Sector</option>';
    el.innerHTML = all + sectorOptions.map(x => `<option value="${x.sector}">${x.sector}</option>`).join('');
}

// ==================== DASHBOARD ====================
async function loadDashboard() {
    await ensureFilters();
    const dist = document.getElementById('filterDistrict');
    const sec = document.getElementById('filterSector');
    if (dist && !dist.value) fillDistrictSelect(dist);
    if (sec && !sec.value) fillSectorSelect(sec);
    await loadDashboardData();
}

async function loadDashboardData() {
    const district = document.getElementById('filterDistrict').value;
    const sector = document.getElementById('filterSector').value;
    const period = document.getElementById('filterPeriod').value;
    const q = new URLSearchParams();
    if (district) q.set('district', district);
    if (sector) q.set('sector', sector);
    if (period && period !== 'all') q.set('time_period', period);

    const data = await fetchAPI(`/dashboard?${q.toString()}`);
    if (!data) return;
    renderDashSummary(data.summary);
    renderDashSkills(data.top_skills);
    renderDashCompanies(data.companies);
    renderDashExperience(data.experience_distribution);
    renderDashTrend(data.job_trend);
}

async function applyDashboardFilters() {
    await loadDashboardData();
}

function renderDashSummary(s) {
    const el = document.getElementById('dashSummary');
    const salaryText = (s.average_salary || 0) > 0 ? `₹${(s.average_salary / 100000).toFixed(1)} LPA avg` : 'Salary N/A (not disclosed)';
    el.innerHTML = `<div class="insights-grid">
        <div class="insight-card"><h4>Active Job Posts</h4><div class="value">${s.total_jobs.toLocaleString()}</div><div class="detail">from live intake</div></div>
        <div class="insight-card"><h4>Unique Skills</h4><div class="value">${s.unique_skills}</div><div class="detail">across current openings</div></div>
        <div class="insight-card"><h4>Companies Hiring</h4><div class="value">${s.top_companies_count}</div><div class="detail">unique employers</div></div>
        <div class="insight-card"><h4>Market Signals</h4><div class="value" style="font-size:1rem">${salaryText}</div><div class="detail">${s.sectors_present.length} sectors present</div></div>
    </div>`;
}

function renderDashSkills(skills) {
    const container = document.getElementById('dashTopSkills');
    if (!skills || !skills.length) { container.innerHTML = '<p>No data</p>'; return; }
    const maxCount = skills[0].count;
    container.innerHTML = `<div class="bar-chart">${skills.map(s => `
        <div class="bar-row">
            <span class="bar-label" style="min-width:150px">${s.skill}</span>
            <div class="bar-track"><div class="bar-fill skill-bar" style="width:${(s.count / maxCount) * 100}%">${s.count} (${s.percentage}%)</div></div>
        </div>`).join('')}</div>`;
}

function renderDashCompanies(companies) {
    const container = document.getElementById('dashCompanies');
    if (!companies || !companies.length) { container.innerHTML = '<p>No data</p>'; return; }
    container.innerHTML = `<div class="heatmap">${companies.map(c =>
        `<div class="heat-cell" style="background:rgba(139,92,246,0.2);color:#a78bfa">${c.company} · ${c.count}</div>`).join('')}</div>`;
}

function renderDashExperience(dist) {
    const container = document.getElementById('dashExperience');
    if (!dist || !dist.length) { container.innerHTML = '<p>No data</p>'; return; }
    const total = dist.reduce((a, b) => a + b.count, 0) || 1;
    const colors = ['#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe'];
    let cumulative = 0;
    const segs = dist.map((d, i) => {
        const pct = (d.count / total) * 100;
        const off = cumulative; cumulative += pct;
        return `<circle cx="80" cy="80" r="58" fill="none" stroke="${colors[i]}" stroke-width="20"
            stroke-dasharray="${pct * 3.64} ${364 - pct * 3.64}" stroke-dashoffset="${-off * 3.64}"/>`;
    });
    container.innerHTML = `<div class="donut-container" style="justify-content:center">
        <svg viewBox="0 0 160 160" width="170" height="170">
            <circle cx="80" cy="80" r="58" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="20"/>
            ${segs.join('')}
            <text x="80" y="85" text-anchor="middle" fill="white" font-size="18" font-weight="700">${total}</text>
        </svg>
        <div class="donut-legend">${dist.map((d, i) => `
            <div class="legend-item"><div class="legend-dot" style="background:${colors[i]}"></div><span>${d.range}: ${d.count}</span></div>`).join('')}
        </div></div>`;
}

function renderDashTrend(trend) {
    const container = document.getElementById('dashTrend');
    if (!trend || !trend.length) { container.innerHTML = '<p>No data</p>'; return; }
    const maxCount = Math.max(...trend.map(t => t.count));
    container.innerHTML = `<div class="bar-chart">${trend.map(t => `
        <div class="bar-row">
            <span class="bar-label" style="min-width:90px">${t.period}</span>
            <div class="bar-track"><div class="bar-fill loc-bar" style="width:${(t.count / maxCount) * 100}%">${t.count}</div></div>
        </div>`).join('')}</div>`;
}

// ==================== INDUSTRY DEMAND ====================
async function loadIndustry() {
    await ensureFilters();
    const sec = document.getElementById('indSector');
    const dist = document.getElementById('indDistrict');
    if (!sec.value) fillSectorSelect(sec);
    if (!dist.value) fillDistrictSelect(dist);

    const q = new URLSearchParams();
    if (sec.value) q.set('sector', sec.value);
    if (dist.value) q.set('district', dist.value);
    const data = await fetchAPI(`/industry-demand?${q.toString()}`);
    renderIndustry(data);
}

function renderIndustry(data) {
    const container = document.getElementById('indBars');
    if (!data || !data.industry_demand || !data.industry_demand.length) {
        container.innerHTML = '<p>No data for this selection</p>';
        return;
    }
    const jobs = data.total_jobs;
    const maxCount = data.industry_demand[0].count;
    container.innerHTML = `<div style="margin-bottom:14px;color:#94a3b8">Based on <strong style="color:#a78bfa">${jobs}</strong> active postings</div>
        <div class="bar-chart">${data.industry_demand.map(s => {
        const salary = s.avg_salary > 0 ? ` · ₹${(s.avg_salary / 100000).toFixed(1)}L` : '';
        return `<div class="bar-row">
            <span class="bar-label" style="min-width:150px">${s.skill}${salary}</span>
            <div class="bar-track"><div class="bar-fill skill-bar" style="width:${(s.count / maxCount) * 100}%">${s.count} (${s.percentage}%)</div></div>
        </div>`;}).join('')}</div>`;
}

// ==================== RECOMMENDATIONS ====================
async function loadRecommendations() {
    await ensureFilters();
    const sec = document.getElementById('recSector');
    const dist = document.getElementById('recDistrict');
    if (!sec.value) fillSectorSelect(sec);
    if (!dist.value) fillDistrictSelect(dist);

    const q = new URLSearchParams();
    if (sec.value) q.set('sector', sec.value);
    if (dist.value) q.set('district', dist.value);
    const data = await fetchAPI(`/recommendations?${q.toString()}`);
    renderRecommendations(data);
}

function renderRecommendations(data) {
    const container = document.getElementById('recResults');
    if (!data || !data.recommendations || !data.recommendations.length) {
        container.innerHTML = '<p>No recommendations for this selection</p>';
        return;
    }
    container.innerHTML = `<div class="insights-grid">${data.recommendations.map(r => `
        <div class="chart-card" style="margin:0">
            <h3 class="chart-title" style="color:#a78bfa">${r.skill}
                <span class="skill-tag" style="margin-left:8px">${r.demand_count} openings</span></h3>
            <div class="detail" style="margin-top:8px">Level: <strong>${r.level}</strong></div>
            <div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:6px;">
                ${r.suggested_topics.map(t => `<span class="skill-tag">${t}</span>`).join('')}
            </div>
        </div>`).join('')}</div>`;
}

// ==================== CAREER GUIDANCE ====================
async function loadCareerGuidance() {
    await ensureFilters();
    const dist = document.getElementById('cgDistrict');
    const sec = document.getElementById('cgSector');
    if (dist && !dist.value) fillDistrictSelect(dist);
    if (sec && !sec.value) fillSectorSelect(sec, { includeAll: false });
    document.getElementById('cgResults').style.display = 'none';
}

async function runCareerGuidance() {
    const body = {
        location: document.getElementById('cgDistrict').value,
        sector: document.getElementById('cgSector').value,
        education: document.getElementById('cgEducation').value,
        preferred_role: document.getElementById('cgRole').value,
        current_skills: document.getElementById('cgSkills').value.split(',').map(s => s.trim()).filter(Boolean),
    };
    const data = await fetchPOST('/career-guidance', body);
    if (!data) return;
    const results = document.getElementById('cgResults');
    results.style.display = 'block';
    renderCGSummary(data.profile);
    renderCGDemand(data.analysis.in_demand_skills);
    renderCGMissing(data.analysis.skills_to_learn);
    renderCGRoles(data.analysis.top_roles, data.analysis.top_companies);
    renderCGReco(data.recommendation);
    results.scrollIntoView({ behavior: 'smooth' });
}

function renderCGSummary(profile) {
    document.getElementById('cgSummary').innerHTML = `<div class="insights-grid">
        <div class="insight-card"><h4>Location</h4><div class="value" style="font-size:1.1rem">${profile.location}</div></div>
        <div class="insight-card"><h4>Education</h4><div class="value" style="font-size:1.1rem">${profile.education}</div></div>
        <div class="insight-card"><h4>Sector</h4><div class="value" style="font-size:1.1rem">${profile.preferred_sector}</div></div>
        <div class="insight-card"><h4>Target Role</h4><div class="value" style="font-size:1.1rem">${profile.preferred_role}</div></div>
    </div>`;
}

function renderCGDemand(skills) {
    const el = document.getElementById('cgDemand');
    if (!skills || !skills.length) { el.innerHTML = '<p>No data</p>'; return; }
    el.innerHTML = `<div class="heatmap">${skills.map(s =>
        `<div class="heat-cell" style="background:rgba(139,92,246,0.2);color:#a78bfa">${s}</div>`).join('')}</div>`;
}

function renderCGMissing(skills) {
    const el = document.getElementById('cgMissing');
    if (!skills || !skills.length) { el.innerHTML = '<p>You\'re already aligned with demand!</p>'; return; }
    el.innerHTML = `<div class="heatmap">${skills.map(s =>
        `<div class="heat-cell" style="background:rgba(239,68,68,0.2);color:#ef4444">${s}</div>`).join('')}</div>`;
}

function renderCGRoles(topRoles, topCompanies) {
    const container = document.getElementById('cgRoles');
    const roles = (topRoles || []).map(r => `<span class="skill-tag">${r.role} · ${r.count}</span>`).join('');
    const comps = (topCompanies || []).map(c => `<span class="skill-tag">${c.company} · ${c.count}</span>`).join('');
    container.innerHTML = `<div class="insights-grid">
        <div class="insight-card"><h4>Top Roles</h4><div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px">${roles || '-'}</div></div>
        <div class="insight-card"><h4>Hiring Companies</h4><div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px">${comps || '-'}</div></div>
    </div>`;
}

function renderCGReco(text) {
    document.getElementById('cgReco').innerHTML = `<div class="insight-card">
        <h4>Your Recommended Career Path</h4>
        <div class="detail" style="margin-top:10px;line-height:1.7;color:#e2e8f0">${text}</div>
    </div>`;
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
    "Other Engineering Branches (B.E./B.Tech)": {
        type: "degree",
        filter: ["B.E. ECE - VTU", "B.E. ECE - Anna University", "B.Tech EEE - NIT Trichy",
                 "B.E. Mechanical - VTU", "B.E. Civil - Anna University", "B.Tech IT - NIT Trichy",
                 "B.Tech CSE (AI & ML) - SRM University", "B.Tech CSE (Data Science) - VIT",
                 "B.E. E&TC - Pune University"]
    },
    "Diploma - Other Branches": {
        type: "diploma",
        filter: ["Diploma in Mechanical - MSBTE", "Diploma in Electrical - MSBTE"]
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
