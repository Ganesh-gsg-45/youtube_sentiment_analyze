import os
import sys
import re
import hashlib
import logging
import numpy as np
from pathlib import Path
from typing import Union, List, Dict, Any


import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.common import load_bin

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PredictionPipeline:
    """
    End-to-end prediction pipeline for sentiment analysis.
    
    Loads trained model and vectorizer, preprocesses input text,
    and returns sentiment predictions.
    """
    
    def __init__(self, models_dir: Path = None, processed_data_dir: Path = None):
        """
        Initialize prediction pipeline.
        
        Args:
            models_dir: Directory containing saved models. Defaults to project_root/models.
            processed_data_dir: Directory containing processed data. Defaults to project_root/data/processed.
        """
        self.project_root = Path(__file__).resolve().parent.parent.parent
        
        if models_dir is None:
            models_dir = self.project_root / "models"
        if processed_data_dir is None:
            processed_data_dir = self.project_root / "data" / "processed"
        
        self.models_dir = models_dir
        self.processed_data_dir = processed_data_dir
        
        # Label mapping (same as training)
        self.label_map = {-1: 0, 0: 1, 1: 2}
        self.inverse_label_map = {0: -1, 1: 0, 2: 1}
        self.sentiment_labels = {-1: 'Negative', 0: 'Neutral', 1: 'Positive'}
        
        # Initialize preprocessing components
        self._init_preprocessing()
        
        # Load model and vectorizer
        self._load_artifacts()
        
        logger.info("PredictionPipeline initialized successfully")

    def _init_preprocessing(self):
        """Initialize text preprocessing components."""
        # Ensure NLTK_DATA is set so downloads go to a writable path in container environments.
        os.environ.setdefault('NLTK_DATA', str(self.project_root / 'nltk_data'))
        nltk.data.path.append(os.environ['NLTK_DATA'])
        Path(os.environ['NLTK_DATA']).mkdir(parents=True, exist_ok=True)

        # Download NLTK data if not present
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', download_dir=os.environ['NLTK_DATA'], quiet=True)
        
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            nltk.download('wordnet', download_dir=os.environ['NLTK_DATA'], quiet=True)
        
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english')) - {'not', 'but', 'however', 'no', 'yet'}

    def _validate_model_path(self, model_path: Path) -> None:
        """
        Validate model file path for security.
        
        Args:
            model_path: Path to model file.
            
        Raises:
            ValueError: If path validation fails.
        """
        # Resolve paths to absolute
        resolved_model = model_path.resolve()
        resolved_models_dir = self.models_dir.resolve()
        
        # Prevent path traversal - ensure model is within models directory
        try:
            resolved_model.relative_to(resolved_models_dir)
        except ValueError:
            raise ValueError(f"Invalid model path: {model_path} is outside models directory")
        
        # Check file exists and is a regular file
        if not resolved_model.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        if not resolved_model.is_file():
            raise ValueError(f"Model path is not a regular file: {model_path}")
        
        # Check file size to prevent DoS from huge files (max 500MB)
        max_size_mb = 500
        file_size_mb = resolved_model.stat().st_size / (1024 * 1024)
        if file_size_mb > max_size_mb:
            raise ValueError(f"Model file too large: {file_size_mb:.1f}MB (max {max_size_mb}MB)")

    def _safe_load_model(self, model_path: Path):
        """
        Safely load model with validation checks.
        
        Args:
            model_path: Path to model file.
            
        Returns:
            Loaded model object.
        """
        self._validate_model_path(model_path)
        
        # Use joblib instead of pickle for safer deserialization
        try:
            import joblib
            model = joblib.load(model_path)
            logger.info(f"Model loaded safely from: {model_path}")
            return model
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise ValueError(f"Could not load model file: {e}")

    def _load_artifacts(self):
        """Load trained model and vectorizer."""
        logger.info("Loading model and vectorizer...")
        
        # Load model with security checks
        model_path = self.models_dir / "best_model.pkl"
        self.model = self._safe_load_model(model_path)
        
        # Load model info
        info_path = self.models_dir / "best_model_info.json"
        if info_path.exists():
            import json
            with open(info_path, 'r') as f:
                self.model_info = json.load(f)
            self.model_name = self.model_info.get('best_model_name', 'Unknown')
        else:
            self.model_name = 'Unknown'
        
        # Load vectorizer
        self.vectorizer = load_bin(self.processed_data_dir / "vectorizer.pkl")

        logger.info(f"Loaded model: {self.model_name}")
        # FeatureUnion doesn't have .vocabulary_; use transform shape to report feature count
        try:
            sample_features = self.vectorizer.transform(["test"])
            logger.info(f"Vectorizer output features: {sample_features.shape[1]}")
        except Exception:
            logger.info("Vectorizer loaded (feature count unavailable at init)")


    def preprocess_text(self, text: str) -> str:
       
        if not text or not isinstance(text, str):
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove trailing and leading whitespaces
        text = text.strip()
        
        # Remove newline characters
        text = re.sub(r'\n', ' ', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://\S+', '', text)
        
        # Remove non-alphanumeric characters, except punctuation
        text = re.sub(r'[^a-z0-9\s!?.,]', '', text)
        
        # Remove extra whitespaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove stopwords but retain important ones for sentiment
        text = ' '.join([word for word in text.split() if word not in self.stop_words])
        
        # Lemmatize the words
        text = ' '.join([self.lemmatizer.lemmatize(word) for word in text.split()])
        
        return text

    def predict(self, text: Union[str, List[str]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    
        # Handle single text
        if isinstance(text, str):
            return self._predict_single(text)
        
        # Handle batch — vectorize the whole batch in one transform() call
        return self._predict_batch(text)

    def _predict_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Efficiently predict sentiment for a batch of texts.
        Vectorizes all valid texts in a single transform() call instead of one per text.

        Args:
            texts: List of raw text strings.

        Returns:
            List of prediction result dictionaries (same order as input).
        """
        processed = [self.preprocess_text(t) for t in texts]
        valid_indices = [i for i, p in enumerate(processed) if p]

        # Pre-fill results with the "empty input" sentinel
        results: List[Dict[str, Any]] = [
            {
                'text': texts[i],
                'processed_text': '',
                'predicted_label': None,
                'sentiment': 'Unknown',
                'confidence': None
            }
            for i in range(len(texts))
        ]

        if not valid_indices:
            return results

        # Single batch transform
        valid_processed = [processed[i] for i in valid_indices]
        features = self.vectorizer.transform(valid_processed)

        preds_mapped = [int(v) for v in self.model.predict(features)]
        classes = list(self.model.classes_)

        for idx, pred_mapped in zip(valid_indices, preds_mapped):
            pred_original = self.inverse_label_map.get(pred_mapped, 0)
            sentiment = self.sentiment_labels.get(pred_original, 'Neutral')
            # Slice the single-row feature for confidence computation
            pos = valid_indices.index(idx)  # row position inside features
            row_features = features[pos]
            confidence = self._get_confidence(row_features, pred_mapped)
            results[idx] = {
                'text': texts[idx],
                'processed_text': processed[idx],
                'predicted_label': pred_original,
                'sentiment': sentiment,
                'confidence': confidence
            }

        return results

    def _predict_single(self, text: str) -> Dict[str, Any]:
  
        # Preprocess
        processed_text = self.preprocess_text(text)
        
        if not processed_text:
            return {
                'text': text,
                'processed_text': '',
                'predicted_label': None,
                'sentiment': 'Unknown',
                'confidence': None
            }
        
        # Vectorize
        features = self.vectorizer.transform([processed_text])
        
        # Predict — use .get() to guard against unexpected class values
        pred_mapped = int(self.model.predict(features)[0])
        pred_original = self.inverse_label_map.get(pred_mapped, 0)  # default → Neutral
        sentiment = self.sentiment_labels.get(pred_original, 'Neutral')
        
        # Get confidence if available
        confidence = self._get_confidence(features, pred_mapped)
        
        return {
            'text': text,
            'processed_text': processed_text,
            'predicted_label': pred_original,
            'sentiment': sentiment,
            'confidence': confidence
        }

    def _get_confidence(self, features, pred_mapped: int) -> float:
    
        try:
            # Try predict_proba (LogisticRegression, RandomForest, NaiveBayes, XGBoost)
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(features)[0]
                # Index by position in classes_, not by label value
                classes = list(self.model.classes_)
                class_idx = classes.index(pred_mapped) if pred_mapped in classes else 0
                confidence = float(proba[class_idx])
                return round(confidence, 4)
        except Exception:
            pass
        
        try:
            # Try decision_function (LinearSVM, LogisticRegression)
            if hasattr(self.model, 'decision_function'):
                decision = self.model.decision_function(features)[0]
                # Convert to confidence-like score using softmax
                exp_scores = np.exp(decision - np.max(decision))
                proba = exp_scores / exp_scores.sum()
                # Index by position in classes_, not by label value
                classes = list(self.model.classes_)
                class_idx = classes.index(pred_mapped) if pred_mapped in classes else 0
                confidence = float(proba[class_idx])
                return round(confidence, 4)
        except Exception:
            pass
        
        return None


def main():
    """Demo the prediction pipeline."""
    pipeline = PredictionPipeline()
    
    # Sample predictions
    sample_texts = [
        "Modi is doing great work for the country",
        "This is a terrible decision by the government",
        "The meeting was held yesterday at the office",
        "I absolutely love this new policy!",
        "This is the worst thing that could happen"
    ]
    
    print("=" * 60)
    print("SENTIMENT PREDICTION DEMO")
    print("=" * 60)
    
    results = pipeline.predict(sample_texts)
    
    for result in results:
        print(f"\nText: {result['text']}")
        print(f"Sentiment: {result['sentiment']} ({result['predicted_label']})")
        if result['confidence']:
            print(f"Confidence: {result['confidence']:.4f}")
        print("-" * 40)


if __name__ == "__main__":
    main()
