with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    <!-- ==================== HEADER ==================== -->

        <div class="logo">
            <i class="fab fa-youtube"></i>
            <h1>SentimentScope</h1>
        </div>
        <p class="subtitle">AI-Powered YouTube Comment Sentiment Analysis &amp; Audience Intelligence</p>
    </header>'''

new = '''    <!-- ==================== HEADER ==================== -->
    <header class="header">
        <div class="header-content">
            <div class="logo">
                <i class="fab fa-youtube"></i>
                <h1>SentimentScope</h1>
            </div>
            <nav class="header-nav">
                <a href="#panelInput" class="nav-link active"><i class="fas fa-home"></i> <span>Dashboard</span></a>
                <a href="#textPredictSection" class="nav-link"><i class="fas fa-comment-dots"></i> <span>Text Analysis</span></a>
                <button class="theme-toggle" id="themeToggle" title="Toggle Dark/Light Mode">
                    <i class="fas fa-moon"></i>
                </button>
            </nav>
        </div>
    </header>'''

if old in content:
    content = content.replace(old, new, 1)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Fixed header')
else:
    print('Search string not found. Checking header area...')
    idx = content.find('HEADER ')
    if idx >= 0:
        print(repr(content[idx-20:idx+200]))
