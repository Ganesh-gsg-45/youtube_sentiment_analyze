/* ============================================================
   SCRIPT.JS — SentimentScope Dashboard
   ============================================================ */

let allComments = [];
let filteredComments = [];
let currentPage = 1;
const PAGE_SIZE = 10;
let activeTab = 'all';

// ----------------------------------------------------------------
// MAIN TAB SWITCHING (Video / Text)
// ----------------------------------------------------------------
function switchMainTab(tab) {
    const videoBtn = document.getElementById('main-tab-video');
    const textBtn  = document.getElementById('main-tab-text');
    const heroVideo = document.getElementById('hero-video');
    const heroText  = document.getElementById('hero-text');
    const contentVideo = document.getElementById('content-video');
    const contentText  = document.getElementById('content-text');

    if (tab === 'video') {
        videoBtn?.classList.add('active');
        textBtn?.classList.remove('active');
        heroVideo?.classList.remove('hidden');
        heroText?.classList.add('hidden');
        contentVideo?.classList.remove('hidden');
        contentText?.classList.add('hidden');
    } else {
        videoBtn?.classList.remove('active');
        textBtn?.classList.add('active');
        heroVideo?.classList.add('hidden');
        heroText?.classList.remove('hidden');
        contentVideo?.classList.add('hidden');
        contentText?.classList.remove('hidden');
    }
}

// ----------------------------------------------------------------
// MODEL INFO TOGGLE
// ----------------------------------------------------------------
function toggleModelInfo() {
    const content = document.getElementById('modelInfoContent');
    const icon = document.getElementById('modelInfoIcon');
    if (!content || !icon) return;

    if (content.classList.contains('hidden')) {
        content.classList.remove('hidden');
        icon.style.transform = 'rotate(180deg)';
    } else {
        content.classList.add('hidden');
        icon.style.transform = 'rotate(0deg)';
    }
}


// ----------------------------------------------------------------
// TEXT PREDICTION — AJAX (no page reload)
// ----------------------------------------------------------------
async function runTextAnalysis() {
    const textarea = document.getElementById('inputText');
    const text = textarea ? textarea.value.trim() : '';
    if (!text) { textarea && textarea.focus(); return; }

    const btn     = document.getElementById('analyzeBtn');
    const loading = document.getElementById('loading');
    const errBox  = document.getElementById('textErrorBox');
    const errMsg  = document.getElementById('textErrorMsg');

    // Show loading state
    if (btn)     { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Analyzing…'; }
    if (loading) loading.classList.remove('hidden');
    if (errBox)  errBox.classList.add('hidden');

    // Make sure text tab content is visible
    switchMainTab('text');

    try {
        const body = new URLSearchParams({ text });
        const resp = await fetch('/api/predict', { method: 'POST', body });
        const data = await resp.json();

        if (!resp.ok || data.error) {
            throw new Error(data.error || 'Server error');
        }

        // Populate result card
        const sentMap = {
            'Positive': { cls: 'bg-pos/10 text-pos', borderCls: 'border-l-pos', icon: 'fa-smile' },
            'Negative': { cls: 'bg-neg/10 text-neg', borderCls: 'border-l-neg', icon: 'fa-frown' },
            'Neutral':  { cls: 'bg-neu/10 text-neu', borderCls: 'border-l-neu', icon: 'fa-meh'  }
        };
        const s = sentMap[data.sentiment] || { cls: 'bg-brand/10 text-brand', borderCls: 'border-l-brand', icon: 'fa-circle' };
        const pct = Math.round((data.confidence || 0) * 100);

        const card   = document.getElementById('resultCard');
        const badge  = document.getElementById('sentimentBadge');
        const icon   = document.getElementById('sentimentIcon');
        const label  = document.getElementById('sentimentLabel');
        const bar    = document.getElementById('confidenceBar');
        const pctEl  = document.getElementById('confidencePct');
        const origEl = document.getElementById('originalText');
        const procEl = document.getElementById('processedText');

        if (card)   { card.className = `glass-card p-6 border-l-4 ${s.borderCls}`; }
        if (badge)  { badge.className = `inline-flex items-center gap-3 px-5 py-2.5 rounded-xl ${s.cls}`; }
        if (icon)   { icon.className = `fas ${s.icon}`; }
        if (label)  label.textContent = data.sentiment;
        if (pctEl)  pctEl.textContent = pct + '%';
        if (bar)    { bar.style.width = '0%'; setTimeout(() => { bar.style.width = pct + '%'; }, 50); }
        if (origEl) origEl.textContent = data.text || text;
        if (procEl) procEl.textContent = data.processed_text || '';

        // Show the result section
        const rs = document.getElementById('resultSection');
        if (rs) {
            rs.classList.remove('hidden');
            setTimeout(() => rs.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
        }

        // Prepend to history list
        const historyList  = document.getElementById('historyList');
        const historyEmpty = document.getElementById('historyEmpty');
        if (historyList && data.sentiment) {
            if (historyEmpty) historyEmpty.remove();
            const sentCls = data.sentiment === 'Positive' ? 'bg-pos/15 text-pos'
                          : data.sentiment === 'Negative' ? 'bg-neg/15 text-neg'
                          : 'bg-neu/15 text-neu';
            const shortened = text.length > 80 ? text.slice(0, 80) + '…' : text;
            const item = document.createElement('div');
            item.className = `history-item sentiment-${data.sentiment.toLowerCase()}`;
            item.innerHTML = `
                <div class="text-sm text-slate-300 flex-1 min-w-0 truncate">${shortened}</div>
                <div class="flex items-center gap-2 flex-shrink-0">
                    <span class="px-2.5 py-1 rounded-full text-xs font-bold ${sentCls}">${data.sentiment}</span>
                    <span class="text-xs text-slate-500">${pct}%</span>
                </div>`;
            historyList.prepend(item);
        }

    } catch (err) {
        if (errBox && errMsg) {
            errMsg.textContent = err.message || 'Analysis failed. Please try again.';
            errBox.classList.remove('hidden');
        }
    } finally {
        if (btn)     { btn.disabled = false; btn.innerHTML = '<i class="fas fa-magic mr-2"></i> Analyze Sentiment'; }
        if (loading) loading.classList.add('hidden');
    }
}

function clearForm() {
    const textarea = document.getElementById('inputText');
    const charCount = document.getElementById('charCount');
    if (textarea) { textarea.value = ''; textarea.focus(); }
    if (charCount) { charCount.textContent = '0'; charCount.style.color = '#64748b'; }
    const rs = document.getElementById('resultSection');
    if (rs) rs.classList.add('hidden');
    const errBox = document.getElementById('textErrorBox');
    if (errBox) errBox.classList.add('hidden');
}



// ----------------------------------------------------------------
// YOUTUBE FORM — LOADING STATE
// ----------------------------------------------------------------
const youtubeForm = document.getElementById('youtubeForm');
const youtubeLoading = document.getElementById('youtubeLoading');
const ytSubmitBtn = document.getElementById('ytSubmitBtn');

if (youtubeForm) {
    youtubeForm.addEventListener('submit', function () {
        if (youtubeLoading) youtubeLoading.classList.remove('hidden');
        if (ytSubmitBtn) {
            ytSubmitBtn.disabled = true;
            ytSubmitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Fetching…';
        }
    });
}

// ----------------------------------------------------------------
// ANIMATE PROGRESS BARS ON LOAD
// ----------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function () {
    // Char counter for text textarea
    const ta = document.getElementById('inputText');
    const cc = document.getElementById('charCount');
    if (ta && cc) {
        ta.addEventListener('input', function () {
            const len = this.value.length;
            cc.textContent = len;
            cc.style.color = len > 400 ? '#ef4444' : len > 300 ? '#f59e0b' : '#64748b';
        });
        // Ctrl+Enter shortcut
        ta.addEventListener('keydown', function (e) {
            if (e.ctrlKey && e.key === 'Enter') runTextAnalysis();
        });
    }

    // Animate progress bars on load
    document.querySelectorAll('.progress-fill, .score-bar-fill').forEach(el => {
        const w = el.style.width;
        el.style.width = '0%';
        requestAnimationFrame(() => { setTimeout(() => { el.style.width = w; }, 120); });
    });
});

// ----------------------------------------------------------------
// CHART.JS — DONUT CHART
// ----------------------------------------------------------------
function renderDonutChart(positive, negative, neutral) {
    const canvas = document.getElementById('donutChart');
    if (!canvas || typeof Chart === 'undefined') return;

    new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: ['Positive', 'Negative', 'Neutral'],
            datasets: [{
                data: [positive, negative, neutral],
                backgroundColor: ['#22c55e', '#ef4444', '#f59e0b'],
                borderColor: ['#16a34a', '#dc2626', '#d97706'],
                borderWidth: 2,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '68%',
            animation: { animateRotate: true, animateScale: false, duration: 900 },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#f1f5f9',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: ctx => ` ${ctx.label}: ${ctx.parsed}%`
                    }
                }
            }
        }
    });
}

// ----------------------------------------------------------------
// CHART.JS — TREND LINE CHART
// ----------------------------------------------------------------
function renderTrendChart(trendData) {
    const canvas = document.getElementById('trendChart');
    if (!canvas || typeof Chart === 'undefined' || !trendData) return;

    const gridColor = 'rgba(255,255,255,0.06)';
    const tickColor = '#64748b';

    new Chart(canvas, {
        type: 'line',
        data: {
            labels: trendData.labels,
            datasets: [
                {
                    label: 'Positive',
                    data: trendData.positive,
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34,197,94,0.08)',
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#22c55e',
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    borderWidth: 2.5
                },
                {
                    label: 'Negative',
                    data: trendData.negative,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239,68,68,0.08)',
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#ef4444',
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    borderWidth: 2.5
                },
                {
                    label: 'Neutral',
                    data: trendData.neutral,
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245,158,11,0.05)',
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#f59e0b',
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    borderWidth: 2.5
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            animation: { duration: 900, easing: 'easeInOutQuart' },
            scales: {
                x: {
                    grid: { color: gridColor },
                    ticks: { color: tickColor, font: { size: 12 } }
                },
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: gridColor },
                    ticks: {
                        color: tickColor,
                        font: { size: 12 },
                        callback: v => v + '%'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#94a3b8',
                        usePointStyle: true,
                        pointStyleWidth: 10,
                        padding: 20,
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#f1f5f9',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y}%`
                    }
                }
            }
        }
    });
}

// ----------------------------------------------------------------
// SCORE GAUGE — SVG Animated Circle
// ----------------------------------------------------------------
function animateScoreGauge(score, color) {
    const circle = document.getElementById('scoreFillCircle');
    const numEl = document.getElementById('scoreNumber');
    if (!circle || !numEl) return;

    const circumference = 2 * Math.PI * 74; // r=74
    const offset = circumference - (score / 100) * circumference;

    // Animate ring
    setTimeout(() => {
        circle.style.transition = 'stroke-dashoffset 1.4s cubic-bezier(0.4,0,0.2,1)';
        circle.style.strokeDashoffset = offset;
    }, 200);

    // Animate number count-up
    let current = 0;
    const duration = 1400;
    const stepTime = 16;
    const steps = duration / stepTime;
    const increment = score / steps;

    const timer = setInterval(() => {
        current = Math.min(current + increment, score);
        numEl.textContent = Math.round(current);
        if (current >= score) clearInterval(timer);
    }, stepTime);
}

// ----------------------------------------------------------------
// COMMENTS — Tab Switching & Pagination
// ----------------------------------------------------------------
function switchTab(tab) {
    activeTab = tab;
    currentPage = 1;

    // Update tab button styles
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById('tab-' + tab);
    if (activeBtn) activeBtn.classList.add('active');

    // Filter
    if (tab === 'all') {
        filteredComments = allComments;
    } else {
        filteredComments = allComments.filter(c => c.sentiment.toLowerCase() === tab);
    }

    renderComments();
}

function renderComments() {
    const container = document.getElementById('commentsContainer');
    const pagination = document.getElementById('commentPagination');
    if (!container) return;

    const start = (currentPage - 1) * PAGE_SIZE;
    const slice = filteredComments.slice(start, start + PAGE_SIZE);
    const totalPages = Math.ceil(filteredComments.length / PAGE_SIZE);

    if (slice.length === 0) {
        container.innerHTML = '<p class="text-slate-500 text-center py-5">No comments in this category.</p>';
        pagination.innerHTML = '';
        return;
    }

    container.innerHTML = slice.map(c => {
        const sent = c.sentiment.toLowerCase();
        const confPct = Math.round((c.confidence || 0) * 100);
        const confColor = sent === 'positive' ? '#22c55e' : sent === 'negative' ? '#ef4444' : '#f59e0b';
        const icon = sent === 'positive' ? 'fa-smile' : sent === 'negative' ? 'fa-frown' : 'fa-meh';
        const textEsc = escHtml(c.text);
        const author = escHtml(c.author || 'Anonymous');
        return `
            <div class="comment-item ${sent}">
                <div class="flex-1 min-w-0">
                    <div class="comment-author"><i class="fas fa-user-circle text-brand3 mr-1"></i> @${author}</div>
                    <div class="comment-text">${textEsc}</div>
                    <div class="comment-meta">
                        <span class="comment-badge ${sent}"><i class="fas ${icon} mr-1"></i> ${c.sentiment}</span>
                        <span class="text-xs text-slate-500" title="Model confidence"><i class="fas fa-brain mr-1" style="color:${confColor}"></i>${confPct}%</span>
                        ${c.likes ? `<span class="comment-likes"><i class="fas fa-thumbs-up mr-1"></i>${c.likes}</span>` : ''}
                    </div>
                </div>
            </div>`;
    }).join('');

    // Render pagination
    if (totalPages <= 1) { pagination.innerHTML = ''; return; }

    let pages = '';
    // Prev
    pages += `<button class="page-btn" onclick="goPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}><i class="fas fa-chevron-left"></i></button>`;

    const windowSize = 5;
    let startP = Math.max(1, currentPage - Math.floor(windowSize / 2));
    let endP   = Math.min(totalPages, startP + windowSize - 1);
    if (endP - startP < windowSize - 1) startP = Math.max(1, endP - windowSize + 1);

    if (startP > 1) pages += `<button class="page-btn" onclick="goPage(1)">1</button>${startP > 2 ? '<span class="text-slate-600 px-1">…</span>' : ''}`;

    for (let p = startP; p <= endP; p++) {
        pages += `<button class="page-btn ${p === currentPage ? 'active' : ''}" onclick="goPage(${p})">${p}</button>`;
    }

    if (endP < totalPages) pages += `${endP < totalPages - 1 ? '<span class="text-slate-600 px-1">…</span>' : ''}<button class="page-btn" onclick="goPage(${totalPages})">${totalPages}</button>`;

    // Next
    pages += `<button class="page-btn" onclick="goPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}><i class="fas fa-chevron-right"></i></button>`;

    pagination.innerHTML = pages;
}

function goPage(n) {
    const totalPages = Math.ceil(filteredComments.length / PAGE_SIZE);
    if (n < 1 || n > totalPages) return;
    currentPage = n;
    renderComments();
    document.getElementById('panelComments')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function escHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '<')
        .replace(/>/g, '>')
        .replace(/"/g, '"');
}

// ----------------------------------------------------------------
// INITIALISE EVERYTHING ON DOMContentLoaded
// ----------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function () {

    // Auto-switch to text tab if text result is present
    const resultSection = document.getElementById('resultSection');
    if (resultSection && !resultSection.classList.contains('hidden')) {
        switchMainTab('text');
        // Scroll to result so user sees it immediately
        setTimeout(() => resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' }), 200);
    }

    // Only run if YouTube result data exists
    if (typeof YT_DATA === 'undefined') return;

    // Panel 3 — Donut chart
    renderDonutChart(YT_DATA.donut.positive, YT_DATA.donut.negative, YT_DATA.donut.neutral);

    // Panel 4 — Trend chart
    if (YT_DATA.trend && YT_DATA.trend.labels && YT_DATA.trend.labels.length > 1) {
        renderTrendChart(YT_DATA.trend);
    }

    // Panel 7 — Comments
    allComments = YT_DATA.comments || [];
    filteredComments = allComments;
    renderComments();

    // Panel 8 — Score gauge
    if (YT_DATA.score) {
        animateScoreGauge(YT_DATA.score.value, YT_DATA.score.color);
    }

    // Scroll smoothly to results if we just got results
    const panelInfo = document.getElementById('panelVideoInfo');
    if (panelInfo) {
        setTimeout(() => panelInfo.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300);
    }
});

