with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Add body, particles, toast container, and container div after </head>
old = '</head>\n\n\n    <!-- ==================== HEADER ==================== -->'
new = '''</head>
<body>
<!-- Floating Particles Background -->
<div class="particles-container">
    <div class="particle"></div>
    <div class="particle"></div>
    <div class="particle"></div>
    <div class="particle"></div>
    <div class="particle"></div>
    <div class="particle"></div>
    <div class="particle"></div>
    <div class="particle"></div>
</div>

<!-- Toast Notifications Container -->
<div class="toast-container" id="toastContainer"></div>

<div class="container">

    <!-- ==================== HEADER ==================== -->'''

if old in content:
    content = content.replace(old, new, 1)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Fixed HTML structure')
else:
    print('WARNING: Search string not found - checking content around </head>')
    idx = content.find('</head>')
    if idx >= 0:
        snippet = content[idx:idx+150]
        print(repr(snippet))
