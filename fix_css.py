with open('static/css/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the broken end of CSS - replace orphaned properties with proper keyword styles
broken_end = '''.keyword-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  padding: 8px;
}



  transition: var(--transition-fast);
  cursor: default;
}'''

new_end = '''.keyword-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  padding: 8px;
}

.keyword-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 50px;
  color: var(--brand-3);
  font-size: 0.88rem;
  font-weight: 500;
  transition: var(--transition-fast);
  cursor: default;
}

.keyword-pill:hover {
  background: rgba(99, 102, 241, 0.2);
  transform: scale(1.05);
}

.kw-size-1 { font-size: 0.75rem; padding: 4px 10px; opacity: 0.7; }
.kw-size-2 { font-size: 0.85rem; }
.kw-size-3 { font-size: 0.95rem; background: rgba(99, 102, 241, 0.18); }
.kw-size-4 { font-size: 1.05rem; background: rgba(99, 102, 241, 0.22); font-weight: 600; }
.kw-size-5 { font-size: 1.15rem; background: rgba(99, 102, 241, 0.28); font-weight: 700; }

.kw-count {
  font-size: 0.7rem;
  opacity: 0.7;
  font-weight: 400;
}

/* Keyword tabs */
.keyword-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.kw-tab-btn {
  padding: 10px 18px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-fast);
  display: flex;
  align-items: center;
  gap: 6px;
}

.kw-tab-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
.kw-tab-btn.active {
  background: rgba(99, 102, 241, 0.15);
  border-color: rgba(99, 102, 241, 0.3);
  color: var(--brand-3);
}

.kw-tab-count {
  font-size: 0.75rem;
  padding: 2px 8px;
  background: var(--bg-hover);
  border-radius: 10px;
}

.kw-tab-content { display: none; }
.kw-tab-content.active { display: block; animation: fadeIn 0.3s ease; }

/* Sentiment keyword clouds */
.keyword-cloud-sentiment {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
  padding: 16px;
  border-radius: var(--radius-sm);
}

.positive-cloud { background: rgba(34, 197, 94, 0.06); border: 1px solid rgba(34, 197, 94, 0.15); }
.negative-cloud { background: rgba(239, 68, 68, 0.06); border: 1px solid rgba(239, 68, 68, 0.15); }
.neutral-cloud  { background: rgba(245, 158, 11, 0.06); border: 1px solid rgba(245, 158, 11, 0.15); }

.keyword-pill-sentiment {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border-radius: 50px;
  font-size: 0.88rem;
  font-weight: 500;
  transition: var(--transition-fast);
  cursor: default;
}

.keyword-pill-sentiment:hover { transform: scale(1.05); }

.positive-cloud .keyword-pill-sentiment {
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.2);
  color: var(--positive-text);
}

.negative-cloud .keyword-pill-sentiment {
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: var(--negative-text);
}

.neutral-cloud .keyword-pill-sentiment {
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.2);
  color: var(--neutral-text);
}

/* Keyword list with bars */
.keyword-list { margin-top: 16px; }
.keyword-list h4 { font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 12px; }

.keyword-list ol { list-style: none; counter-reset: kw; }
.keyword-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.keyword-list li:last-child { border-bottom: none; }

.kw-word {
  font-weight: 600;
  color: var(--text-primary);
  width: 100px;
  flex-shrink: 0;
}

.kw-bar-track {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  overflow: hidden;
}

.kw-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--brand-1), var(--brand-3));
  border-radius: 3px;
  transition: width 0.8s ease;
}

.kw-count-label {
  font-size: 0.82rem;
  color: var(--text-muted);
  width: 30px;
  text-align: right;
}

/* ----------------------------------------------------------------
   COMMENTS SECTION
   ---------------------------------------------------------------- */
.comment-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.tab-btn {
  padding: 10px 18px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-fast);
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
.tab-btn.active {
  background: rgba(99, 102, 241, 0.15);
  border-color: rgba(99, 102, 241, 0.3);
  color: var(--brand-3);
}

.tab-count {
  font-size: 0.75rem;
  padding: 2px 8px;
  background: var(--bg-hover);
  border-radius: 10px;
}

.comments-list { display: flex; flex-direction: column; gap: 10px; }

.comment-item {
  padding: 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.02);
  transition: var(--transition-fast);
}

.comment-item:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: var(--border-focus);
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.comment-author {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-primary);
}

.comment-date {
  font-size: 0.78rem;
  color: var(--text-muted);
  margin-left: auto;
}

.comment-text {
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

.comment-sentiment-badge {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
  text-transform: uppercase;
}

.comment-sentiment-badge.positive { background: var(--positive-bg); color: var(--positive-text); }
.comment-sentiment-badge.negative { background: var(--negative-bg); color: var(--negative-text); }
.comment-sentiment-badge.neutral  { background: var(--neutral-bg); color: var(--neutral-text); }

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  margin-top: 20px;
  flex-wrap: wrap;
}

.page-btn {
  padding: 8px 14px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.85rem;
  cursor: pointer;
  transition: var(--transition-fast);
}

.page-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
.page-btn.active {
  background: rgba(99, 102, 241, 0.15);
  border-color: rgba(99, 102, 241, 0.3);
  color: var(--brand-3);
}
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* ----------------------------------------------------------------
   FINAL SCORE
   ---------------------------------------------------------------- */
.final-score-wrap {
  display: flex;
  align-items: center;
  gap: 40px;
  flex-wrap: wrap;
}

.score-circle-wrap {
  position: relative;
  width: 180px;
  height: 180px;
  flex-shrink: 0;
}

.score-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.score-track {
  fill: none;
  stroke: rgba(255, 255, 255, 0.08);
  stroke-width: 12;
}

.score-fill {
  fill: none;
  stroke-width: 12;
  stroke-linecap: round;
  transition: stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.score-text-group {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.score-number {
  font-size: 2.5rem;
  font-weight: 800;
  line-height: 1;
}

.score-out-of {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.score-details { flex: 1; min-width: 250px; }

.score-label {
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: 8px;
}

.score-description {
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 20px;
}

.score-breakdown { display: flex; flex-direction: column; gap: 10px; }

.score-bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.score-bar-label {
  font-size: 0.82rem;
  color: var(--text-secondary);
  width: 60px;
  font-weight: 500;
}

.score-bar-track {
  flex: 1;
  height: 8px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  overflow: hidden;
}

.score-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 1s ease;
}

.score-bar-pct {
  font-size: 0.82rem;
  color: var(--text-muted);
  width: 40px;
  text-align: right;
  font-weight: 600;
}

/* ----------------------------------------------------------------
   HISTORY
   ---------------------------------------------------------------- */
.history-list { display: flex; flex-direction: column; gap: 8px; }

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.02);
  transition: var(--transition-fast);
}

.history-item:hover {
  background: rgba(255, 255, 255, 0.04);
  transform: translateX(4px);
}

.history-item.sentiment-positive { border-left: 3px solid var(--positive); }
.history-item.sentiment-negative { border-left: 3px solid var(--negative); }
.history-item.sentiment-neutral  { border-left: 3px solid var(--neutral); }

.history-text {
  font-size: 0.88rem;
  color: var(--text-primary);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.history-badge {
  font-size: 0.72rem;
  padding: 2px 10px;
  border-radius: 10px;
  font-weight: 600;
  text-transform: uppercase;
}

.history-item.sentiment-positive .history-badge { background: var(--positive-bg); color: var(--positive-text); }
.history-item.sentiment-negative .history-badge { background: var(--negative-bg); color: var(--negative-text); }
.history-item.sentiment-neutral  .history-badge { background: var(--neutral-bg); color: var(--neutral-text); }

.history-confidence {
  font-size: 0.78rem;
  color: var(--text-muted);
  font-weight: 500;
}

/* ----------------------------------------------------------------
   MODEL INFO
   ---------------------------------------------------------------- */
.info-card {
  background: linear-gradient(135deg, var(--bg-surface) 0%, rgba(99, 102, 241, 0.08) 100%);
  border-color: rgba(99, 102, 241, 0.15);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.info-item { display: flex; flex-direction: column; gap: 4px; }

.info-label {
  font-size: 0.72rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  font-weight: 700;
}

.info-value {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-primary);
}

/* ----------------------------------------------------------------
   FOOTER
   ---------------------------------------------------------------- */
.footer {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
  font-size: 0.88rem;
}

.footer i { color: #f43f5e; }

/* ----------------------------------------------------------------
   UTILITIES
   ---------------------------------------------------------------- */
.hidden { display: none !important; }
.divider {
  border: none;
  border-top: 1px solid var(--border-color);
  margin: 24px 0;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* ----------------------------------------------------------------
   RESPONSIVE
   ---------------------------------------------------------------- */
@media (max-width: 768px) {
  .header { padding: 12px 16px; }
  .header-nav span { display: none; }
  .logo h1 { font-size: 1.3rem; }
  .chart-stats-grid { grid-template-columns: 1fr; }
  .stat-tiles { grid-template-columns: 1fr; }
  .final-score-wrap { flex-direction: column; align-items: center; text-align: center; }
  .url-input-row { flex-direction: column; }
  .url-input-row input, .url-input-row button { width: 100%; }
}

@media (max-width: 500px) {
  .container { padding: 0 16px 40px; }
  .card { padding: 20px; }
  .stat-tiles { grid-template-columns: 1fr; }
  .comment-tabs, .keyword-tabs { gap: 4px; }
  .tab-btn, .kw-tab-btn { padding: 8px 12px; font-size: 0.8rem; }
  .btn { width: 100%; justify-content: center; }
}'''

if broken_end in content:
    content = content.replace(broken_end, new_end)
    with open('static/css/style.css', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Fixed CSS syntax errors and added missing styles')
else:
    print('Broken end not found. Checking last 200 chars...')
    print(repr(content[-200:]))
