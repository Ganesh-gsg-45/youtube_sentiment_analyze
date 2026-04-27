# YouTube Sentiment Insights

A production-ready machine learning pipeline and web application for sentiment analysis of YouTube comments. The system classifies text into **Positive**, **Negative**, or **Neutral** sentiments using ensemble ML models, and provides an interactive Flask web interface for real-time text and YouTube video analysis.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Running the Web Application](#running-the-web-application)
  - [Using the Prediction API](#using-the-prediction-api)
  - [YouTube Video Analysis](#youtube-video-analysis)
  - [Running the ML Pipeline](#running-the-ml-pipeline)
- [DVC Pipeline Stages](#dvc-pipeline-stages)
- [Model Training & Experiments](#model-training--experiments)
- [MLflow Tracking](#mlflow-tracking)
- [Security Features](#security-features)
- [API Endpoints](#api-endpoints)
- [Screenshots](#screenshots)
- [License](#license)

---

## Features

- **Real-time Sentiment Prediction** — Analyze any text input instantly via web UI or REST API
- **YouTube Video Comment Analysis** — Fetch and analyze up to 200 comments from any YouTube video
- **Rich Visual Dashboard** — Interactive charts showing sentiment distribution, keyword clouds, trend analysis, and audience score
- **Ensemble ML Models** — Trained with LinearSVM, Logistic Regression, LightGBM, and XGBoost with hyperparameter tuning
- **Dual TF-IDF Vectorization** — Word-level (1-3 grams) + Character-level (2-5 grams) for robust feature extraction
- **Production-Ready Pipeline** — DVC-managed reproducible data science pipeline
- **MLflow Experiment Tracking** — Log metrics, parameters, and artifacts for every experiment
- **Security Hardened** — CSRF protection, rate limiting, input sanitization, security headers
- **Prediction History** — In-memory history of recent predictions with quick re-analysis

---

## Tech Stack

| Category | Technologies |
|----------|-------------|
| **Backend** | Python 3.10+, Flask, Flask-WTF, Flask-Limiter |
| **Machine Learning** | scikit-learn, LightGBM, XGBoost, NLTK |
| **Feature Engineering** | TF-IDF (word + character n-grams) |
| **Data** | pandas, NumPy, YouTube Data API v3 |
| **MLOps** | DVC, MLflow, Dagshub |
| **Frontend** | HTML5, CSS3, JavaScript, Chart.js |
| **Deployment** | Gunicorn (production), environment-based config |

---

## Project Structure

```
video-sentiment-analysis/
├── app.py                          # Flask web application entry point
├── patch_app.py                    # App patch utilities
├── params.yaml                     # Centralized configuration parameters
├── requirements.txt                # Python dependencies
├── setup.py                        # Package setup
├── dvc.yaml                        # DVC pipeline definition
├── dvc.lock                        # DVC pipeline lock file
├── .gitignore                      # Git ignore rules
├── .dvcignore                      # DVC ignore rules
│
├── data/                           # Data directory (DVC-tracked)
│   ├── raw/                        # Raw YouTube comments
│   ├── interim/                    # Processed/cleaned data
│   └── processed/                  # Final train/test splits + vectorizer
│
├── models/                         # Trained model artifacts
│   ├── best_model.pkl              # Best performing model
│   ├── best_model_info.json        # Model metadata
│   └── model_comparison.csv        # Model comparison results
│
├── notebooks/                      # Jupyter notebooks for EDA & experiments
│   ├── 1_Preprocessing_&_EDA.ipynb
│   ├── 2_experiment_1_baseline_model.ipynb
│   └── model.ipynb
│
├── reports/                        # Generated reports
│   ├── data_validation_report.csv
│   ├── model_evaluation_report.txt
│   ├── best_model_classification_report.csv
│   └── best_model_confusion_matrix.png
│
├── scripts/                        # Utility scripts
│   ├── start_mlflow_ui.py          # Start MLflow UI locally
│   ├── mlflow_utils.py             # MLflow helper functions
│   ├── get_best_mlflow_runs.py     # Retrieve best experiments
│   ├── connect_dagshub_direct.py   # Dagshub connection
│   ├── migrate_to_dagshub.py       # Migrate experiments to Dagshub
│   └── sync_to_dagshub.py          # Sync MLflow to Dagshub
│
├── src/                            # Source code package
│   ├── __init__.py
│   ├── data/                       # Data processing modules
│   │   ├── data_ingestion.py
│   │   ├── data_validation.py
│   │   ├── data_transformation.py
│   │   ├── youtube_data_extractor.py
│   │   ├── youtube_data_cleaner.py
│   │   └── youtube_pseudo_labeler.py
│   ├── models/                     # Model training & evaluation
│   │   ├── model_trainer.py
│   │   └── model_evaluation.py
│   ├── pipeline/                   # Prediction pipeline
│   │   ├── __init__.py
│   │   └── prediction_pipeline.py
│   └── utils/                      # Common utilities
│       ├── __init__.py
│       └── common.py
│
├── static/                         # Static web assets
│   ├── css/style.css
│   └── js/script.js
│
├── templates/                      # Flask HTML templates
│   └── index.html
│
└── test_youtube.py                 # YouTube extractor tests
```

---

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd video-sentiment-analysis
```

### 2. Create a Virtual Environment

```bash
# Using venv
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install the Package (Editable Mode)

```bash
pip install -e .
```

### 5. Download NLTK Data

The application automatically downloads required NLTK data on first run, but you can pre-download:

```python
import nltk
nltk.download('stopwords')
nltk.download('wordnet')
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Required for YouTube Data API
YOUTUBE_API_KEY=your_youtube_api_key_here

# Flask Configuration (optional)
FLASK_SECRET_KEY=your-secret-key-here
FLASK_DEBUG=False
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
```

### params.yaml

The main configuration file controls pipeline behavior:

```yaml
data_ingestion:
  test_size: 0.20

model_building:
  # Word-level TF-IDF
  ngram_range: [1, 3]
  max_features: 30000

  # Character-level TF-IDF
  char_ngram_range: [2, 5]
  char_max_features: 20000

  # LightGBM hyperparameters
  learning_rate: 0.09
  max_depth: 20
  n_estimators: 367

  # LinearSVC
  svc_c: 1.0

  # LogisticRegression
  lr_c: 5.0

youtube_data:
  video_ids:
    - "dQw4w9WgXcQ"
  max_comments_per_video: 1000
  max_videos: 5
  api_key_env: "YOUTUBE_API_KEY"
```

---

## Usage

### Running the Web Application

```bash
# Development mode
python app.py

# Production mode (recommended)
# Set FLASK_DEBUG=False and use a WSGI server
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

The application will be available at `http://127.0.0.1:5000`.

### Using the Prediction API

**Endpoint:** `POST /api/predict`

**Request:**
```bash
curl -X POST http://127.0.0.1:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "This video is absolutely amazing!"}'
```

**Response:**
```json
{
  "success": true,
  "text": "This video is absolutely amazing!",
  "sentiment": "Positive",
  "predicted_label": 1,
  "confidence": 0.9234,
  "processed_text": "video absolutely amazing"
}
```

### YouTube Video Analysis

**Web UI:**
1. Navigate to the home page
2. Enter a YouTube video URL in the "YouTube Video Analysis" section
3. Click "Analyze Video"
4. View comprehensive sentiment dashboard with charts and insights

**API Endpoint:** `POST /api/youtube-analyze`

```bash
curl -X POST http://127.0.0.1:5000/api/youtube-analyze \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

### Running the ML Pipeline

Execute the full DVC pipeline:

```bash
# Run all stages
dvc repro

# Run specific stage
dvc repro model_trainer

# View pipeline DAG
dvc dag
```

---

## DVC Pipeline Stages

| Stage | Description | Outputs |
|-------|-------------|---------|
| `data_ingestion` | Load and split raw dataset | `train_processed.csv`, `test_processed.csv` |
| `data_validation` | Validate data schema and quality | `data_validation_report.csv` |
| `youtube_data_extraction` | Fetch comments via YouTube API | `youtube_comments_latest.csv` |
| `youtube_data_cleaning` | Clean and normalize raw comments | `youtube_cleaned.csv` |
| `youtube_labeling` | Pseudo-label comments using weak supervision | `youtube_labeled.csv` |
| `data_transformation` | TF-IDF vectorization and feature engineering | `X_train.pkl`, `X_test.pkl`, `y_train.pkl`, `y_test.pkl`, `vectorizer.pkl` |
| `model_trainer` | Train and compare multiple ML models | `best_model.pkl`, `best_model_info.json`, `model_comparison.csv` |
| `model_evaluation` | Evaluate best model on test set | `model_evaluation_report.txt`, `confusion_matrix.png` |

---

## Model Training & Experiments

The project experiments with multiple algorithms:

| Model | Key Characteristics |
|-------|---------------------|
| **LinearSVM** | Fast, high-dimensional sparse data performance |
| **Logistic Regression** | Interpretable, probabilistic output |
| **LightGBM** | Gradient boosting, handles non-linear patterns |
| **XGBoost** | Robust ensemble, excellent generalization |

### Feature Engineering

- **Word TF-IDF**: 1-3 gram range, 30,000 max features
- **Character TF-IDF**: 2-5 gram range, 20,000 max features
- **FeatureUnion**: Combines both vectorizers for rich representation

### Text Preprocessing

- Lowercasing and whitespace normalization
- URL removal
- Special character filtering
- Stopword removal (preserving negations: *not*, *but*, *however*)
- Lemmatization with WordNet

---

## MLflow Tracking

Experiments are tracked with MLflow. Connect to Dagshub for cloud tracking:

```bash
# Set Dagshub credentials
export MLFLOW_TRACKING_URI=https://dagshub.com/your-username/your-repo.mlflow
export MLFLOW_TRACKING_USERNAME=your-username
export MLFLOW_TRACKING_PASSWORD=your-token

# Or use the helper scripts
python scripts/connect_dagshub_direct.py
```

View experiments locally:

```bash
python scripts/start_mlflow_ui.py
```

---

## Security Features

The application implements multiple security layers:

| Feature | Implementation |
|---------|---------------|
| **CSRF Protection** | Flask-WTF token validation |
| **Rate Limiting** | Flask-Limiter (10/min for predictions, 30/min for API) |
| **Input Sanitization** | Length limits, null byte removal, control character filtering |
| **Security Headers** | HSTS, CSP, X-Frame-Options, X-Content-Type-Options, XSS Protection |
| **Path Traversal Prevention** | Model path validation with `resolve()` and `relative_to()` checks |
| **Secure Secrets** | Environment-based secret keys with fallback to `secrets.token_hex()` |

---

## API Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/` | GET | Main web interface | Default |
| `/predict` | POST | Text sentiment prediction (web) | 10/min |
| `/api/predict` | POST | Text sentiment prediction (API) | 30/min |
| `/youtube-analyze` | POST | YouTube video analysis (web) | 10/min |
| `/api/youtube-analyze` | POST | YouTube video analysis (API) | 10/min |
| `/health` | GET | Health check | Default |
| `/history` | GET | Prediction history | Default |
| `/clear-history` | POST | Clear history | 10/min |

---

## Screenshots

*Main Dashboard with Text Prediction*

*YouTube Video Analysis Results*

*Sentiment Distribution Charts*

*Keyword Cloud & Trend Analysis*

---

## License

This project is licensed under the MIT License.

---

## Acknowledgments

- [YouTube Data API](https://developers.google.com/youtube/v3) for comment access
- [scikit-learn](https://scikit-learn.org/) for ML algorithms
- [DVC](https://dvc.org/) for pipeline management
- [MLflow](https://mlflow.org/) for experiment tracking
- [Dagshub](https://dagshub.com/) for MLflow hosting

---

## Contact

For questions or contributions, please open an issue or contact the maintainer.

**Author:** Ganesh  
**Email:** contact@example.com
