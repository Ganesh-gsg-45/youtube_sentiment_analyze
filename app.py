import os
import sys
import json
import re
import secrets
import logging
from pathlib import Path
from datetime import datetime
from collections import deque, Counter
import math

# Load .env file first so all env vars are available (important for deployed envs)
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, flash, make_response, jsonify, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


# Add project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.pipeline.prediction_pipeline import PredictionPipeline
from src.utils.common import read_yaml
from src.data.youtube_data_extractor import YouTubeDataExtractor
from googleapiclient.errors import HttpError


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# ---------------------------
# Server-side Firebase auth gate
# ---------------------------
FB_ID_TOKEN_COOKIE = "fb_id_token"
_firebase_admin_app = None

def _init_firebase_admin():
    global _firebase_admin_app
    if _firebase_admin_app is not None:
        return _firebase_admin_app

    try:
        import firebase_admin
        from firebase_admin import credentials

        cred_json_str = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
        if cred_json_str:
            cred_dict = json.loads(cred_json_str)
            cred = credentials.Certificate(cred_dict)
        else:
            service_account_path = os.environ.get(
                "GOOGLE_APPLICATION_CREDENTIALS",
                str(project_root / "sentimentscope-ced63-firebase-adminsdk-fbsvc-f54b1903d1.json"),
            )
            cred = credentials.Certificate(service_account_path)

        _firebase_admin_app = firebase_admin.initialize_app(cred)
    except Exception as e:
        logger.warning(f"Firebase Admin init failed: {e}")
        _firebase_admin_app = False

    return _firebase_admin_app


def verify_firebase_id_token():
    """
    Verify Firebase ID token from cookie.
    Returns decoded claims dict on success, else None.
    """
    token = request.cookies.get(FB_ID_TOKEN_COOKIE, "")
    if not token:
        return None

    try:
        import firebase_admin
        from firebase_admin import auth

        if _init_firebase_admin() is False:
            return None

        decoded = auth.verify_id_token(token, check_revoked=False)
        return decoded
    except Exception as e:
        logger.info(f"Firebase ID token verification failed: {type(e).__name__}: {e}")
        return None

def _is_protected_route():
    protected_prefixes = (
        "/predict",
        "/youtube-analyze",
        "/api/predict",
        "/api/youtube-analyze",
        "/history",
        "/clear-history",
    )
    if request.path == "/":
        return True
    if request.path.startswith("/static/"):
        return False
    return any(request.path.startswith(p) for p in protected_prefixes)


@app.before_request
def enforce_server_auth():
    # Allow public auth pages
    if request.path in ("/login", "/signup", "/health"):
        return None

    if not _is_protected_route():
        return None

    claims = verify_firebase_id_token()
    if claims is None:
        if request.path.startswith("/api/"):
            return jsonify({"error": "Unauthorized"}), 401
        # HTML routes: redirect to login
        return redirect(url_for("login"))

_secret = os.environ.get('FLASK_SECRET_KEY', '')
if not _secret or _secret == 'your-super-secret-key-here-change-in-production':
    # Log a loud warning — this will break CSRF with multiple workers
    _secret = secrets.token_hex(32)
    logger.warning(
        "FLASK_SECRET_KEY is not set or is using the placeholder value. "
        "CSRF will fail with multiple Gunicorn workers. "
        "Please set a strong FLASK_SECRET_KEY in your deployment secrets."
    )
app.secret_key = _secret

# Security: disable debug mode in production
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')


# Use Secure cookies only when running over HTTPS (production/HuggingFace).
# On localhost (HTTP), Secure=True blocks cookies entirely — causing flash/session failures.
_is_https = os.environ.get('FLASK_ENV', '').lower() == 'production' or \
            os.environ.get('HTTPS', '').lower() in ('on', 'true', '1') or \
            os.environ.get('HF_SPACE_ID') is not None  # Hugging Face Spaces uses HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'None' if _is_https else 'Lax'
app.config['SESSION_COOKIE_SECURE'] = _is_https
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['WTF_CSRF_ENABLED'] = False  # Disabled: Firebase handles auth client-side

# Fix for running behind Hugging Face reverse proxy
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)


# Validate YouTube API key at startup
_yt_api_key = os.environ.get('YOUTUBE_API_KEY', '')
if not _yt_api_key:
    logger.warning(
        "YOUTUBE_API_KEY is not set in .env! "
        "YouTube video analysis will fail. "
        "Get a key at: https://console.cloud.google.com/apis/library/youtube.googleapis.com"
    )
else:
    logger.info(f"YouTube API key loaded (prefix: {_yt_api_key[:8]}...)")

# Initialize prediction pipeline
pipeline = None

# Per-session prediction history — keyed by Flask session, NOT a shared global.
# Session is signed with SECRET_KEY so clients cannot tamper with it.
# Max 20 items per session stored as a list in session['history'].
_HISTORY_MAX = 20

def get_session_history() -> list:
    """Return this session's prediction history (most-recent first)."""
    return session.get('history', [])

def add_to_session_history(entry: dict) -> None:
    """Prepend an entry to this session's history, capping at _HISTORY_MAX."""
    history = session.get('history', [])
    history.insert(0, entry)
    session['history'] = history[:_HISTORY_MAX]
    session.modified = True

def clear_session_history() -> None:
    """Wipe this session's prediction history."""
    session['history'] = []
    session.modified = True

# Icon mapping for sentiments
SENTIMENT_ICONS = {
    'Positive': 'smile',
    'Negative': 'frown',
    'Neutral': 'meh'
}


def _sanitize_error(msg: str) -> str:
    """Strip API keys and secrets from error messages before showing to users."""
    # Remove &key=... or ?key=... from URLs embedded in error strings
    msg = re.sub(r'[?&]key=[A-Za-z0-9_-]+', '&key=***REDACTED***', msg)
    # Remove any raw AIzaSy... pattern (Google API key format)
    msg = re.sub(r'AIzaSy[A-Za-z0-9_-]{30,}', '***REDACTED***', msg)
    return msg

def sanitize_input(text: str, max_length: int = 500) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        text: Raw input text.
        max_length: Maximum allowed length.
        
    Returns:
        Sanitized text string.
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Strip whitespace
    text = text.strip()
    
    # Truncate to max length
    text = text[:max_length]
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Remove control characters except newlines and tabs
    text = ''.join(char for char in text if char == '\n' or char == '\t' or (ord(char) >= 32 and ord(char) <= 126) or ord(char) > 127)
    
    return text


def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # X-Frame-Options removed to allow embedding in Hugging Face Spaces
    response.headers['X-XSS-Protection'] = '1; mode=block'
    if _is_https:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://www.gstatic.com https://apis.google.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https://i.ytimg.com https://img.youtube.com https://lh3.googleusercontent.com; "
        "connect-src 'self' https://cdn.jsdelivr.net https://www.googleapis.com https://identitytoolkit.googleapis.com "
        "https://securetoken.googleapis.com https://firestore.googleapis.com https://www.gstatic.com https://apis.google.com; "
        "frame-src 'self' https://sentimentscope-ced63.firebaseapp.com https://*.firebaseapp.com;"
    )
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response


@app.after_request
def after_request(response):
    "Apply security headers and disable HTML caching."
    if response.content_type and 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return add_security_headers(response)


def get_model_info():

    """Load model information from saved files."""
    models_dir = project_root / "models"
    info_path = models_dir / "best_model_info.json"
    
    default_info = {
        'name': 'LinearSVM',
        'accuracy': 0.7983,
        'f1': 0.7918,
        'features': 1000
    }
    
    if info_path.exists():
        try:
            with open(info_path, 'r') as f:
                info = json.load(f)
                return {
                    'name': info.get('best_model_name', default_info['name']),
                    'accuracy': info.get('best_accuracy', default_info['accuracy']),
                    'f1': info.get('best_f1', default_info['f1']),
                    'features': default_info['features']
                }
        except Exception as e:
            logger.warning(f"Could not load model info: {e}")
    
    # Try to load from model comparison CSV
    comparison_path = models_dir / "model_comparison.csv"
    if comparison_path.exists():
        try:
            import pandas as pd
            df = pd.read_csv(comparison_path)
            if not df.empty:
                best = df.iloc[0]
                return {
                    'name': best.get('Model', default_info['name']),
                    'accuracy': best.get('Accuracy', default_info['accuracy']),
                    'f1': best.get('F1_Weighted', default_info['f1']),
                    'features': default_info['features']
                }
        except Exception as e:
            logger.warning(f"Could not load comparison CSV: {e}")
    
    return default_info


@app.route('/')
def index():
    """Render the main page with prediction form and history."""
    model_info = get_model_info()
    return render_template(
        'index.html',
        result=None,
        history=get_session_history(),
        model_info=model_info
    )


@app.route('/login')
def login():
    """Render login page."""
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    """Handle login form POST (CSRF safe fallback)."""
    email = request.form.get('email')
    logger.info(f"Login attempt: {email}")
    # Firebase handles auth client-side, just log + redirect
    flash('Login processed. Check Firebase auth.', 'info')
    return redirect(url_for('index'))


@app.route('/signup')
def signup():
    """Render signup page."""
    return render_template('signup.html')


@app.route('/signup', methods=['POST'])
def signup_post():
    """
    Safety fallback: if the signup JS module fails to load the browser may
    submit the form here. We never process credentials server-side — just
    redirect back to /signup with a visible message so the user knows JS is
    required. This prevents the browser's GET-fallback which would append
    the password to the URL query string.
    """
    flash('JavaScript is required for sign-up. Please enable it and try again.', 'warning')
    return redirect(url_for('signup'))


@app.route('/predict', methods=['POST'])
@limiter.limit("10 per minute")
def predict():

    """Handle prediction request."""
    global pipeline
    
    # Initialize pipeline if not already done
    if pipeline is None:
        try:
            pipeline = PredictionPipeline()
        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}")
            flash("Error: Could not load prediction model. Please ensure models are trained.", "error")
            return redirect(url_for('index'))
    
    # Get and sanitize input text
    text = sanitize_input(request.form.get('text', ''), max_length=500)
    
    if not text:
        flash("Please enter some text to analyze.", "warning")
        return redirect(url_for('index'))
    
    if len(request.form.get('text', '')) > 500:
        flash("Text was truncated to 500 characters.", "info")

    
    try:
        # Make prediction
        result = pipeline.predict(text)
        
        # Add icon to result
        result['icon'] = SENTIMENT_ICONS.get(result['sentiment'], 'circle')
        
        # Add to session history (per-user, not shared)
        add_to_session_history({
            'text': text,
            'sentiment': result['sentiment'],
            'predicted_label': result['predicted_label'],
            'confidence': result['confidence'] or 0,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
        logger.info(f"Prediction: '{text[:50]}...' -> {result['sentiment']} ({result['confidence']})")
        
        model_info = get_model_info()
        
        return render_template(
            'index.html',
            result=result,
            history=get_session_history(),
            model_info=model_info
        )
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        flash("An error occurred during prediction. Please try again.", "error")
        return redirect(url_for('index'))


@app.route('/api/predict', methods=['POST'])
@limiter.limit("30 per minute")
def api_predict():

    """API endpoint for programmatic access."""
    global pipeline
    
    if pipeline is None:
        try:
            pipeline = PredictionPipeline()
        except Exception as e:
            return {'error': f'Pipeline initialization failed: {str(e)}'}, 500
    
    # Support both JSON and form data
    if request.is_json:
        data = request.get_json()
        text = data.get('text', '').strip()
    else:
        text = request.form.get('text', '').strip()
    
    if not text:
        return {'error': 'No text provided'}, 400
    
    try:
        result = pipeline.predict(text)

        # Save to this user's session history
        add_to_session_history({
            'text': text,
            'sentiment': result['sentiment'],
            'predicted_label': result['predicted_label'],
            'confidence': result['confidence'] or 0,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })

        return {
            'success': True,
            'text': result['text'],
            'sentiment': result['sentiment'],
            'predicted_label': result['predicted_label'],
            'confidence': result['confidence'],
            'processed_text': result['processed_text']
        }
    except Exception as e:
        return {'error': str(e)}, 500


@app.route('/health')
def health():
    """Health check endpoint."""
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}


@app.route('/history')
def get_history():
    """Return this session's prediction history (never another user's)."""
    history = get_session_history()
    return {
        'history': history,
        'count': len(history)
    }


# Common English stop words for keyword extraction
STOP_WORDS = {
    'the','a','an','and','or','but','in','on','at','to','for','of','with',
    'is','are','was','were','be','been','being','have','has','had','do','does',
    'did','will','would','could','should','may','might','shall','can','need',
    'i','you','he','she','it','we','they','me','him','her','us','them',
    'my','your','his','its','our','their','this','that','these','those',
    'what','which','who','how','when','where','why','not','no','so','if',
    'just','like','very','really','also','get','got','then','than','more',
    'some','all','one','two','new','good','great','video','watch','comment',
    'from','about','up','out','as','by','im','its','dont','its','this',
    'here','there','now','make','way','see','know','think','time','people'
}


def extract_keywords(comment_results: list, top_n: int = 20) -> list:
    """Extract top N keywords from comment texts."""
    word_freq = Counter()
    for c in comment_results:
        words = re.findall(r'\b[a-zA-Z]{3,}\b', c['text'].lower())
        for w in words:
            if w not in STOP_WORDS:
                word_freq[w] += 1
    
    keywords = []
    max_count = word_freq.most_common(1)[0][1] if word_freq else 1
    for word, count in word_freq.most_common(top_n):
        # Normalize size 1-5 for visual weight in cloud
        size = max(1, min(5, math.ceil(count / max_count * 5)))
        keywords.append({'word': word, 'count': count, 'size': size})
    return keywords


def compute_trend_data(comment_results: list, segments: int = 5) -> dict:
    """Split comments into time-ordered segments and compute sentiment % per segment."""
    total = len(comment_results)
    if total < segments:
        segments = max(1, total)
    
    chunk_size = math.ceil(total / segments)
    labels = []
    pos_data, neg_data, neu_data = [], [], []
    
    for i in range(segments):
        chunk = comment_results[i * chunk_size: (i + 1) * chunk_size]
        if not chunk:
            continue
        n = len(chunk)
        pos = round(sum(1 for c in chunk if c['sentiment'] == 'Positive') / n * 100, 1)
        neg = round(sum(1 for c in chunk if c['sentiment'] == 'Negative') / n * 100, 1)
        neu = round(sum(1 for c in chunk if c['sentiment'] == 'Neutral') / n * 100, 1)
        labels.append(f'Seg {i + 1}')
        pos_data.append(pos)
        neg_data.append(neg)
        neu_data.append(neu)
    
    return {'labels': labels, 'positive': pos_data, 'negative': neg_data, 'neutral': neu_data}


def generate_insights(sentiment_distribution: dict, total: int, keywords: list) -> list:
    """Generate human-readable insight bullets from the analysis."""
    insights = []
    pos_pct = sentiment_distribution['Positive']['percentage']
    neg_pct = sentiment_distribution['Negative']['percentage']
    neu_pct = sentiment_distribution['Neutral']['percentage']
    pos_conf = sentiment_distribution['Positive']['avg_confidence']
    neg_conf = sentiment_distribution['Negative']['avg_confidence']

    # Dominant sentiment
    dominant = max(sentiment_distribution, key=lambda k: sentiment_distribution[k]['percentage'])
    insights.append({
        'icon': 'fa-chart-pie',
        'text': f"{pos_pct}% of {total} analyzed comments are positive — the audience response is {'overwhelmingly' if pos_pct > 70 else 'mostly' if pos_pct > 50 else 'somewhat'} positive."
        if dominant == 'Positive' else
        f"{neg_pct}% of {total} comments are negative — the audience has {'strong' if neg_pct > 60 else 'notable'} criticism."
        if dominant == 'Negative' else
        f"{neu_pct}% of {total} comments are neutral — the audience is largely indifferent or informational."
    })

    # Confidence insight
    if pos_conf > 0.7:
        insights.append({'icon': 'fa-star', 'text': f"High model confidence ({pos_conf*100:.0f}%) on positive comments — sentiment is clear and unambiguous."})
    if neg_conf > 0.7:
        insights.append({'icon': 'fa-exclamation-triangle', 'text': f"Negative comments show strong conviction ({neg_conf*100:.0f}% confidence) — core concerns are clearly expressed."})

    # Engagement mix
    if pos_pct > 0 and neg_pct > 0:
        ratio = round(pos_pct / neg_pct, 1) if neg_pct > 0 else float('inf')
        insights.append({'icon': 'fa-balance-scale', 'text': f"Positive-to-negative ratio: {ratio}:1 — {'healthy engagement' if ratio >= 2 else 'mixed reception' if ratio >= 1 else 'more critics than fans'}."})

    # Top keyword
    if keywords:
        top_word = keywords[0]['word']
        insights.append({'icon': 'fa-key', 'text': f"Most discussed topic: '{top_word}' — appears {keywords[0]['count']} times across comments."})

    return insights


def compute_final_score(sentiment_distribution: dict) -> dict:
    """Compute a 0-100 audience sentiment score."""
    pos = sentiment_distribution['Positive']['percentage']
    neu = sentiment_distribution['Neutral']['percentage']
    score = round((pos * 1.0 + neu * 0.5), 1)  # Max 100 when all positive
    score = min(100, score)  # Clamp

    if score >= 75:
        label, color = 'Excellent', '#22c55e'
    elif score >= 55:
        label, color = 'Good', '#84cc16'
    elif score >= 40:
        label, color = 'Mixed', '#f59e0b'
    elif score >= 25:
        label, color = 'Poor', '#f97316'
    else:
        label, color = 'Critical', '#ef4444'
    
    return {'score': score, 'label': label, 'color': color}


def analyze_youtube_video(video_url: str, max_comments: int = 200) -> dict:
   
    global pipeline
    
    # Initialize pipeline if not already done
    if pipeline is None:
        try:
            pipeline = PredictionPipeline()
        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}")
            raise e
    
    # Extract video ID
    extractor = YouTubeDataExtractor()
    video_id = extractor.extract_video_id(video_url)
    
    if not video_id:
        raise ValueError("Invalid YouTube URL. Could not extract video ID.")
    
    # Get video details (this also validates the API key is working)
    try:
        video_details = extractor.get_video_details(video_id)
    except HttpError as e:
        status = e.resp.status if hasattr(e, 'resp') else 0
        details = str(e)
        if status == 403:
            if 'quotaExceeded' in details:
                raise ValueError(
                    "YouTube API quota exceeded for today. "
                    "Free tier allows 10,000 units/day. Try again tomorrow."
                )
            else:
                raise ValueError(
                    "YouTube API key is blocked or restricted. "
                    "Please create a new API key at https://console.cloud.google.com "
                    "and update YOUTUBE_API_KEY in your .env file."
                )
        elif status == 404:
            raise ValueError("Video not found. Please check the URL.")
        else:
            raise ValueError(f"YouTube API error ({status}): {_sanitize_error(details[:200])}")
    
    # Fetch comments (limited for web request)
    logger.info(f"Fetching up to {max_comments} comments for video {video_id}")
    try:
        comments_data = extractor.fetch_comments(video_id, max_results=max_comments)
    except HttpError as e:
        status = e.resp.status if hasattr(e, 'resp') else 0
        details = str(e)
        if status == 403:
            if 'quotaExceeded' in details:
                raise ValueError(
                    "YouTube API quota exceeded for today. "
                    "Free tier allows 10,000 units/day. Try again tomorrow."
                )
            elif 'forbidden' in details.lower() or 'blocked' in details.lower():
                raise ValueError(
                    "YouTube API key is blocked or restricted. "
                    "Please create a new API key at https://console.cloud.google.com "
                    "and update YOUTUBE_API_KEY in your .env file."
                )
            else:
                raise ValueError(f"YouTube API access denied (403): {_sanitize_error(details[:200])}")
        elif status == 404:
            raise ValueError("Video not found, or comments are disabled for this video.")
        else:
            raise
    except Exception:
        raise

    if not comments_data:
        return {
            'video_id': video_id,
            'video_title': video_details.get('title', 'Unknown'),
            'channel': video_details.get('channel', 'Unknown'),
            'published_at': video_details.get('published_at', ''),
            'view_count': video_details.get('view_count', 0),
            'like_count': video_details.get('like_count', 0),
            'comment_count': video_details.get('comment_count', 0),
            'total_comments_fetched': 0,
            'error': 'No comments found or comments are disabled for this video.'
        }

    
    # Predict sentiment for each comment
    texts = [c['text'] for c in comments_data]
    results = pipeline.predict(texts)
    
    # Aggregate results
    sentiment_counts = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    sentiment_confidences = {'Positive': [], 'Negative': [], 'Neutral': []}
    comment_results = []
    
    for comment, result in zip(comments_data, results):
        sentiment = result['sentiment']
        confidence = result['confidence'] or 0
        
        # Guard: map unexpected labels (e.g. 'Unknown' from empty text) to Neutral
        if sentiment not in sentiment_counts:
            sentiment = 'Neutral'
        
        sentiment_counts[sentiment] += 1
        sentiment_confidences[sentiment].append(confidence)
        
        comment_results.append({
            'text': comment['text'][:200],
            'author': comment['author'],
            'sentiment': sentiment,
            'confidence': confidence,
            'likes': comment['like_count']
        })
    
    # Calculate percentages
    total = len(comment_results)
    sentiment_distribution = {
        'Positive': {
            'count': sentiment_counts['Positive'],
            'percentage': round(sentiment_counts['Positive'] / total * 100, 1) if total > 0 else 0,
            'avg_confidence': round(sum(sentiment_confidences['Positive']) / len(sentiment_confidences['Positive']), 4) if sentiment_confidences['Positive'] else 0
        },
        'Negative': {
            'count': sentiment_counts['Negative'],
            'percentage': round(sentiment_counts['Negative'] / total * 100, 1) if total > 0 else 0,
            'avg_confidence': round(sum(sentiment_confidences['Negative']) / len(sentiment_confidences['Negative']), 4) if sentiment_confidences['Negative'] else 0
        },
        'Neutral': {
            'count': sentiment_counts['Neutral'],
            'percentage': round(sentiment_counts['Neutral'] / total * 100, 1) if total > 0 else 0,
            'avg_confidence': round(sum(sentiment_confidences['Neutral']) / len(sentiment_confidences['Neutral']), 4) if sentiment_confidences['Neutral'] else 0
        }
    }
    
    # Sort comments by confidence for top examples
    top_positive = sorted(
        [c for c in comment_results if c['sentiment'] == 'Positive'],
        key=lambda x: x['confidence'],
        reverse=True
    )[:3]
    
    top_negative = sorted(
        [c for c in comment_results if c['sentiment'] == 'Negative'],
        key=lambda x: x['confidence'],
        reverse=True
    )[:3]

    # --- New enriched data ---
    keywords = extract_keywords(comment_results, top_n=20)
    trend_data = compute_trend_data(comment_results, segments=5)
    insights = generate_insights(sentiment_distribution, total, keywords)
    final_score = compute_final_score(sentiment_distribution)
    
    return {
        'video_id': video_id,
        'video_title': video_details.get('title', 'Unknown'),
        'channel': video_details.get('channel', 'Unknown'),
        'published_at': video_details.get('published_at', ''),
        'view_count': video_details.get('view_count', 0),
        'like_count': video_details.get('like_count', 0),
        'comment_count': video_details.get('comment_count', 0),
        'total_comments_fetched': total,
        'sentiment_distribution': sentiment_distribution,
        'top_positive_comments': top_positive,
        'top_negative_comments': top_negative,
        'comments': comment_results,  # All comments for tab display
        'keywords': keywords,
        'trend_data': trend_data,
        'insights': insights,
        'final_score': final_score
    }


@app.route('/youtube-analyze', methods=['POST'])
@limiter.limit("10 per minute")
def youtube_analyze():

    """Analyze sentiment of YouTube video comments."""
    video_url = request.form.get('video_url', '').strip()
    
    if not video_url:
        model_info = get_model_info()
        return render_template(
            'index.html',
            youtube_error="Please enter a YouTube video URL.",
            history=get_session_history(),
            model_info=model_info
        )

    
    try:
        logger.info(f"Analyzing YouTube video: {video_url}")
        result = analyze_youtube_video(video_url, max_comments=200)
        
        if result.get('error'):
            model_info = get_model_info()
            return render_template(
                'index.html',
                youtube_error=result['error'],
                history=get_session_history(),
                model_info=model_info
            )

        
        model_info = get_model_info()
        
        return render_template(
            'index.html',
            youtube_result=result,
            history=get_session_history(),
            model_info=model_info
        )
        
    except ValueError as e:
        logger.error(f"Invalid YouTube URL: {e}")
        model_info = get_model_info()
        return render_template(
            'index.html',
            youtube_error=str(e),
            history=get_session_history(),
            model_info=model_info
        )
    except HttpError as e:
        logger.error(f"YouTube API error: {e}")
        error_reason = e.resp.reason if hasattr(e, 'resp') else 'Unknown'
        error_details = e.error_details if hasattr(e, 'error_details') and e.error_details else []
        detail_msg = error_details[0].get('message', '') if error_details else _sanitize_error(str(e))
        
        if 'blocked' in detail_msg.lower() or error_reason == 'forbidden':
            user_msg = "YouTube API access is blocked. Please check your API key restrictions in Google Cloud Console."
        elif 'quotaExceeded' in detail_msg:
            user_msg = "YouTube API quota exceeded. Please try again tomorrow or upgrade your quota."
        elif 'notFound' in detail_msg:
            user_msg = "Video not found or comments are disabled."
        else:
            user_msg = f"YouTube API Error ({error_reason}): {_sanitize_error(detail_msg)}"
        
        model_info = get_model_info()
        return render_template(
            'index.html',
            youtube_error=user_msg,
            history=get_session_history(),
            model_info=model_info
        )
    except Exception as e:
        import traceback
        logger.error(f"YouTube analysis error: {type(e).__name__}: {e}")
        logger.error(traceback.format_exc())
        user_msg = f"Analysis error ({type(e).__name__}): {_sanitize_error(str(e)[:200])}"
        model_info = get_model_info()
        return render_template(
            'index.html',
            youtube_error=user_msg,
            history=get_session_history(),
            model_info=model_info
        )


@app.route('/api/youtube-analyze', methods=['POST'])
@limiter.limit("10 per minute")
def api_youtube_analyze():

    """API endpoint for YouTube video sentiment analysis."""
    if request.is_json:
        data = request.get_json()
        video_url = data.get('video_url', '').strip()
    else:
        video_url = request.form.get('video_url', '').strip()
    
    if not video_url:
        return {'error': 'No video URL provided'}, 400
    
    try:
        result = analyze_youtube_video(video_url, max_comments=200)
        return {'success': True, **result}
    except Exception as e:
        return {'error': _sanitize_error(str(e))}, 500


@app.route('/clear-history', methods=['POST'])
@limiter.limit("10 per minute")
def clear_history():
    """
    Clear this session's prediction history.
    Session-scoped: only affects the calling user, never anyone else's history.
    Returns JSON so the frontend can call it via fetch() without a page reload.
    """
    clear_session_history()
    return jsonify({'success': True, 'message': 'History cleared.'})


@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded."""
    if request.is_json:
        return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
    flash("Too many requests. Please try again later.", "warning")
    return redirect(url_for('index'))


if __name__ == '__main__':

    # Ensure required directories exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    logger.info("Starting Sentiment Analysis Flask App...")
    logger.info(f"Project root: {project_root}")
    
    # Use the port from .env (defaults to 5000 for local, 7860 for HF Spaces)
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', '5000'))
    
    logger.info(f"Starting Sentiment Analysis Flask App on {host}:{port}...")
    logger.info(f"Debug mode: {app.config['DEBUG']}")
    
    app.run(
        host=host,
        port=port,
        debug=app.config['DEBUG']
    )



