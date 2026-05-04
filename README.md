# SentimentScope — YouTube Comment Sentiment Analysis

A Flask web app that analyzes YouTube video comments using a trained ML model (LinearSVM) to classify sentiment as **Positive**, **Negative**, or **Neutral**.

---

## Tech Stack

| Layer | Tools |
|-------|-------|
| Backend | Python, Flask |
| ML | scikit-learn (LinearSVM), TF-IDF |
| MLOps | DVC, MLflow, Dagshub |
| Data | YouTube Data API v3, pandas |
| Frontend | HTML, CSS, JS, Chart.js, Firebase Auth |
| Container | Docker, docker-compose |

---

## Project Structure

```
video-sentiment-analysis/
├── app.py                    # Flask application
├── params.yaml               # Pipeline configuration
├── dvc.yaml                  # DVC pipeline stages
├── requirements.txt          # Dependencies
├── Dockerfile                # Docker config
├── docker-compose.yml        # Docker compose
├── data/                     # raw/interim/processed/
├── notebook/models/          # best_model.pkl etc.
├── reports/                  # Evaluation reports & plots
├── scripts/                  # MLflow/Dagshub utils
├── src/
│   ├── data/                 # Data ingestion, validation, transformation, YouTube utils
│   ├── models/               # Model trainer & evaluation
│   ├── pipeline/             # Prediction pipeline
│   └── utils/                # Common utilities
├── static/                   # CSS & JS (incl. Firebase auth)
├── templates/                # HTML (index, login, signup)
└── notebook/                 # EDA & experiment notebooks
```

---

## Installation

```bash
git clone <repo-url>
cd video-sentiment-analysis
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
pip install -e .
```

---

## Configuration

Create a `.env` file:

```env
YOUTUBE_API_KEY=your_youtube_api_key
FLASK_SECRET_KEY=your_secret_key
FLASK_DEBUG=False
FLASK_PORT=5000
```

---

## Authentication

User login/signup via Firebase Auth.

## Run the App

```bash
python app.py
```

Open `http://127.0.0.1:5000`.

## Docker

```bash
docker-compose up --build
```

---

## ML Pipeline (DVC)

```bash
dvc repro          # Run full pipeline
dvc dag            # View pipeline graph
```

**Stages:** `data_ingestion` → `data_validation` → `data_transformation` → `model_trainer` → `model_evaluation`

---

## Model Results

| Model | Accuracy | F1-Weighted |
|-------|----------|-------------|
| **LinearSVM** ⭐ | **86.3%** | **86.1%** |
| LogisticRegression | 85.1% | 84.9% |
| SGDClassifier | 80.4% | 79.5% |
| NaiveBayes | 70.8% | 70.4% |

---

## MLflow Tracking

```bash
python -m mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000
```

Open `http://127.0.0.1:5000` → go to **`sentiment_analysis_model_training`** experiment.

---

## API

**Predict text:**
```bash
POST /api/predict
{"text": "This video is great!"}
```

**Analyze YouTube video:**
```bash
POST /api/youtube-analyze
{"video_url": "https://www.youtube.com/watch?v=VIDEO_ID"}
```
