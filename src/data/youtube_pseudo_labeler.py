import os
import sys
import logging
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.common import read_yaml, create_directories, load_bin, get_size

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('errors.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class YouTubePseudoLabeler:
    """
    Auto-labels YouTube comments using an existing trained model.
    
    Loads the best model and vectorizer, predicts sentiment labels
    for cleaned YouTube comments, and saves labeled data for training.
    """
    
    # Label mapping (same as training)
    LABEL_MAP = {-1: 0, 0: 1, 1: 2}
    INVERSE_LABEL_MAP = {0: -1, 1: 0, 2: 1}
    SENTIMENT_LABELS = {-1: 'Negative', 0: 'Neutral', 1: 'Positive'}
    
    def __init__(self, config_path: Path = None):
        """
        Initialize YouTubePseudoLabeler.
        
        Args:
            config_path: Path to params.yaml. If None, uses default path.
        """
        self.project_root = Path(__file__).resolve().parent.parent.parent
        
        if config_path is None:
            config_path = self.project_root / "params.yaml"
        
        self.config = read_yaml(config_path)
        
        # Setup directories
        self.interim_data_path = self.project_root / "data" / "interim"
        self.processed_data_path = self.project_root / "data" / "processed"
        self.models_path = self.project_root / "models"
        
        # Load model and vectorizer
        self.model = None
        self.vectorizer = None
        self.model_name = "Unknown"
        
        self._load_artifacts()
        
        logger.info(f"YouTubePseudoLabeler initialized. Project root: {self.project_root}")
        logger.info(f"Model: {self.model_name}")

    def _load_artifacts(self):
        """Load trained model and vectorizer."""
        logger.info("Loading model and vectorizer for pseudo-labeling...")
        
        # Load model
        model_path = self.models_path / "best_model.pkl"
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
                "Please train a model first using src/models/model_trainer.py"
            )
        
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        
        # Load model info
        info_path = self.models_path / "best_model_info.json"
        if info_path.exists():
            import json
            with open(info_path, 'r') as f:
                model_info = json.load(f)
            self.model_name = model_info.get('best_model_name', 'Unknown')
            self.label_map = model_info.get('label_map', self.LABEL_MAP)
            self.inverse_label_map = model_info.get('inverse_label_map', self.INVERSE_LABEL_MAP)
        else:
            self.label_map = self.LABEL_MAP
            self.inverse_label_map = self.INVERSE_LABEL_MAP
        
        # Load vectorizer
        vectorizer_path = self.processed_data_path / "vectorizer.pkl"
        if not vectorizer_path.exists():
            raise FileNotFoundError(
                f"Vectorizer not found at {vectorizer_path}. "
                "Please run data transformation first."
            )
        
        self.vectorizer = load_bin(vectorizer_path)
        
        logger.info(f"Loaded model: {self.model_name}")
        logger.info(f"Vectorizer vocabulary size: {len(self.vectorizer.vocabulary_)}")

    def predict_labels(self, texts: list) -> np.ndarray:
        """
        Predict sentiment labels for a list of texts.
        
        Args:
            texts: List of preprocessed text strings.
            
        Returns:
            Array of original labels (-1, 0, 1).
        """
        if not texts:
            return np.array([])
        
        # Vectorize
        features = self.vectorizer.transform(texts)
        
        # Predict
        pred_mapped = self.model.predict(features)
        
        # Map back to original labels (-1, 0, 1)
        pred_original = np.array([self.inverse_label_map[int(p)] for p in pred_mapped])
        
        return pred_original

    def get_confidence_scores(self, texts: list) -> list:
        """
        Get confidence scores for predictions if available.
        
        Args:
            texts: List of preprocessed text strings.
            
        Returns:
            List of confidence scores.
        """
        if not texts:
            return []
        
        features = self.vectorizer.transform(texts)
        confidences = []
        
        for i in range(len(texts)):
            feat = features[i:i+1]
            pred_mapped = int(self.model.predict(feat)[0])
            
            confidence = None
            
            # Try predict_proba
            try:
                if hasattr(self.model, 'predict_proba'):
                    proba = self.model.predict_proba(feat)[0]
                    confidence = float(proba[pred_mapped])
            except Exception:
                pass
            
            # Try decision_function
            if confidence is None:
                try:
                    if hasattr(self.model, 'decision_function'):
                        decision = self.model.decision_function(feat)[0]
                        exp_scores = np.exp(decision - np.max(decision))
                        proba = exp_scores / exp_scores.sum()
                        confidence = float(proba[pred_mapped])
                except Exception:
                    pass
            
            confidences.append(round(confidence, 4) if confidence else None)
        
        return confidences

    def label_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add pseudo-labels to a DataFrame of cleaned comments.
        
        Args:
            df: DataFrame with 'clean_comment' column.
            
        Returns:
            DataFrame with added 'category' and 'confidence' columns.
        """
        logger.info(f"Pseudo-labeling {len(df)} YouTube comments...")
        
        # Get texts
        texts = df['clean_comment'].astype(str).tolist()
        
        # Predict labels
        labels = self.predict_labels(texts)
        
        # Get confidence scores
        confidences = self.get_confidence_scores(texts)
        
        # Add to DataFrame
        df = df.copy()
        df['category'] = labels
        df['confidence'] = confidences
        df['sentiment_label'] = df['category'].map(self.SENTIMENT_LABELS)
        
        # Log distribution
        distribution = df['category'].value_counts().sort_index()
        logger.info("Predicted label distribution:")
        for label, count in distribution.items():
            sentiment = self.SENTIMENT_LABELS.get(label, 'Unknown')
            logger.info(f"  {sentiment:10s} ({label:2d}): {count:5d} ({count/len(df)*100:.1f}%)")
        
        # Log average confidence
        valid_conf = [c for c in confidences if c is not None]
        if valid_conf:
            logger.info(f"Average confidence: {np.mean(valid_conf):.4f}")
        
        return df

    def load_cleaned_data(self) -> pd.DataFrame:
        """
        Load cleaned YouTube comments.
        
        Returns:
            DataFrame with cleaned comments.
        """
        cleaned_path = self.interim_data_path / "youtube_cleaned.csv"
        
        if not cleaned_path.exists():
            raise FileNotFoundError(
                f"Cleaned YouTube data not found at {cleaned_path}. "
                "Run youtube_data_cleaner.py first."
            )
        
        df = pd.read_csv(cleaned_path)
        logger.info(f"Loaded cleaned comments: {len(df)} rows")
        return df

    def save_labeled_data(self, df: pd.DataFrame):
        """
        Save labeled YouTube comments.
        
        Args:
            df: DataFrame with labeled comments.
        """
        output_path = self.interim_data_path / "youtube_labeled.csv"
        df.to_csv(output_path, index=False)
        logger.info(f"Labeled comments saved to: {output_path}")
        logger.info(f"File size: {get_size(output_path)}")
        return str(output_path)

    def initiate_labeling(self) -> str:
        """
        Orchestrate the complete pseudo-labeling pipeline.
        
        Returns:
            Path to saved labeled comments CSV.
        """
        logger.info("=" * 60)
        logger.info("Starting YouTube Pseudo-Labeling")
        logger.info("=" * 60)
        
        try:
            # Load cleaned data
            df = self.load_cleaned_data()
            
            if df.empty:
                logger.warning("No cleaned comments to label!")
                return None
            
            # Label data
            labeled_df = self.label_dataframe(df)
            
            # Save labeled data
            output_path = self.save_labeled_data(labeled_df)
            
            logger.info("=" * 60)
            logger.info("YouTube Pseudo-Labeling completed successfully!")
            logger.info("=" * 60)
            
            return output_path
            
        except Exception as e:
            logger.error(f"YouTube Pseudo-Labeling failed: {e}")
            raise e


def main():
    """Run YouTube pseudo-labeling from command line."""
    try:
        labeler = YouTubePseudoLabeler()
        output_path = labeler.initiate_labeling()
        
        if output_path:
            print(f"\nLabeling complete! Saved to: {output_path}")
        else:
            print("\nNo comments to label!")
            
    except Exception as e:
        logger.error(f"Failed to complete labeling: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
