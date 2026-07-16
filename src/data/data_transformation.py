import os
import sys
import re
import logging
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.pipeline import FeatureUnion

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.common import read_yaml, create_directories, save_bin, get_size
import mlflow

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


class DataTransformation:
    def __init__(self, config_path: Path = None):
        """
        Initialize DataTransformation with configuration.
        
        Args:
            config_path: Path to params.yaml. If None, uses default path.
        """
        self.project_root = Path(__file__).resolve().parent.parent.parent
        
        if config_path is None:
            config_path = self.project_root / "params.yaml"
        
        self.config = read_yaml(config_path)
        self.model_config = self.config.get("model_building", {})
        
        # Setup directories
        self.interim_data_path = self.project_root / "data" / "interim"
        self.processed_data_path = self.project_root / "data" / "processed"
        
        create_directories([self.processed_data_path])
        
        # Download NLTK data if not present
        self._ensure_nltk_data()
        
        # Initialize preprocessing components
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english')) - {'not', 'but', 'however', 'no', 'yet'}
        
        logger.info(f"DataTransformation initialized. Project root: {self.project_root}")

    def _ensure_nltk_data(self):
        """Download required NLTK data if not already present."""
        os.environ.setdefault('NLTK_DATA', str(self.project_root / 'nltk_data'))
        nltk.data.path.append(os.environ['NLTK_DATA'])
        Path(os.environ['NLTK_DATA']).mkdir(parents=True, exist_ok=True)

        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            logger.info("Downloading NLTK stopwords...")
            nltk.download('stopwords', download_dir=os.environ['NLTK_DATA'], quiet=True)
        
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            logger.info("Downloading NLTK wordnet...")
            nltk.download('wordnet', download_dir=os.environ['NLTK_DATA'], quiet=True)

    def preprocess_text(self, text: str) -> str:
        """
        Apply text preprocessing steps.
        
        Args:
            text: Raw text string.
            
        Returns:
            Cleaned and preprocessed text string.
        """
        if pd.isna(text):
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

    def apply_preprocessing(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply preprocessing to the dataframe.
        
        Args:
            df: DataFrame with 'clean_comment' column.
            
        Returns:
            DataFrame with preprocessed 'clean_comment' column.
        """
        logger.info("Applying text preprocessing...")
        
        # Create a copy to avoid modifying original
        df = df.copy()
        
        # Apply preprocessing
        df['clean_comment'] = df['clean_comment'].astype(str).apply(self.preprocess_text)
        
        # Remove any rows that became empty after preprocessing
        initial_rows = len(df)
        df = df[df['clean_comment'].str.strip() != '']
        logger.info(f"Dropped {initial_rows - len(df)} rows that became empty after preprocessing")
        
        logger.info(f"Preprocessed data shape: {df.shape}")
        return df

    def load_and_combine_youtube_data(self, train_df: pd.DataFrame) -> pd.DataFrame:
        """
        Load YouTube labeled data and combine with Reddit training data.
        
        Args:
            train_df: Preprocessed Reddit training dataframe.
            
        Returns:
            Combined dataframe with Reddit + YouTube data.
        """
        youtube_path = self.interim_data_path / "youtube_labeled.csv"
        
        if not youtube_path.exists():
            logger.info("No YouTube labeled data found. Using only Reddit data.")
            return train_df
        
        logger.info("Loading YouTube labeled data...")
        youtube_df = pd.read_csv(youtube_path)
        
        # Select only needed columns
        youtube_df = youtube_df[['clean_comment', 'category']].copy()
        
        # Ensure clean_comment is string
        youtube_df['clean_comment'] = youtube_df['clean_comment'].astype(str)
        
        # Remove empty comments
        youtube_df = youtube_df[youtube_df['clean_comment'].str.strip() != '']
        
        logger.info(f"YouTube data loaded: {len(youtube_df)} comments")
        
        # Combine with train data
        combined_df = pd.concat([train_df, youtube_df], ignore_index=True)
        
        # Remove duplicates
        initial_rows = len(combined_df)
        combined_df = combined_df.drop_duplicates(subset=['clean_comment'])
        logger.info(f"Dropped {initial_rows - len(combined_df)} duplicate comments after combining")
        
        logger.info(f"Combined training data shape: {combined_df.shape}")
        logger.info(f"  Reddit: {len(train_df)}")
        logger.info(f"  YouTube: {len(youtube_df)}")
        
        return combined_df

    def vectorize_data(self, train_df: pd.DataFrame, test_df: pd.DataFrame):
        """
        Vectorize text data using a FeatureUnion of word-level and
        character-level TF-IDF vectorizers.

        Combining both types captures:
        - Word n-grams: standard semantic/sentiment signals
        - Char n-grams: subword patterns, slang, typos, morphology

        Args:
            train_df: Training dataframe.
            test_df: Testing dataframe.

        Returns:
            Tuple of (X_train, X_test, y_train, y_test, vectorizer)
        """
        # Word-level parameters
        word_ngram_range = tuple(self.model_config.get("ngram_range", [1, 3]))
        word_max_features = self.model_config.get("max_features", 30000)

        # Character-level parameters
        char_ngram_range = tuple(self.model_config.get("char_ngram_range", [2, 5]))
        char_max_features = self.model_config.get("char_max_features", 20000)

        logger.info(
            f"Building FeatureUnion vectorizer:\n"
            f"  Word TF-IDF: ngram_range={word_ngram_range}, max_features={word_max_features}\n"
            f"  Char TF-IDF: ngram_range={char_ngram_range}, max_features={char_max_features}"
        )

        # Word-level TF-IDF
        word_vectorizer = TfidfVectorizer(
            max_features=word_max_features,
            ngram_range=word_ngram_range,
            min_df=2,
            max_df=0.95,
            sublinear_tf=True,
            analyzer='word'
        )

        # Character-level TF-IDF  (analyzer='char_wb' respects word boundaries)
        char_vectorizer = TfidfVectorizer(
            max_features=char_max_features,
            ngram_range=char_ngram_range,
            min_df=3,
            max_df=0.95,
            sublinear_tf=True,
            analyzer='char_wb'
        )

        # Combine both into a single transformer with the same .transform() interface
        vectorizer = FeatureUnion([
            ('word', word_vectorizer),
            ('char', char_vectorizer)
        ])

        # Fit on train, transform both
        X_train = vectorizer.fit_transform(train_df['clean_comment'])
        X_test = vectorizer.transform(test_df['clean_comment'])

        y_train = train_df['category'].values
        y_test = test_df['category'].values

        total_features = X_train.shape[1]
        logger.info(f"Train features shape: {X_train.shape}")
        logger.info(f"Test features shape:  {X_test.shape}")
        logger.info(f"Total combined features: {total_features}")

        return X_train, X_test, y_train, y_test, vectorizer

    def save_processed_data(self, X_train, X_test, y_train, y_test, vectorizer):
        """
        Save processed data and vectorizer.
        
        Args:
            X_train, X_test: Feature matrices.
            y_train, y_test: Label arrays.
            vectorizer: Fitted vectorizer object.
        """
        # Save sparse matrices
        save_bin(X_train, self.processed_data_path / "X_train.pkl")
        save_bin(X_test, self.processed_data_path / "X_test.pkl")
        save_bin(y_train, self.processed_data_path / "y_train.pkl")
        save_bin(y_test, self.processed_data_path / "y_test.pkl")

        # Save combined FeatureUnion vectorizer
        save_bin(vectorizer, self.processed_data_path / "vectorizer.pkl")

        # Save feature names from each sub-vectorizer for interpretability
        try:
            word_names = vectorizer.transformer_list[0][1].get_feature_names_out()
            char_names = vectorizer.transformer_list[1][1].get_feature_names_out()
            all_names = [f"word__{n}" for n in word_names] + [f"char__{n}" for n in char_names]
            pd.DataFrame({'feature': all_names}).to_csv(
                self.processed_data_path / "feature_names.csv", index=False
            )
        except Exception as e:
            logger.warning(f"Could not save feature names: {e}")
        
        logger.info(f"Processed data saved to: {self.processed_data_path}")
        logger.info(f"Files saved: X_train.pkl, X_test.pkl, y_train.pkl, y_test.pkl, vectorizer.pkl")

    def initiate_data_transformation(self) -> tuple:
        """
        Orchestrates the complete data transformation pipeline.
        
        Returns:
            Tuple of (X_train_path, X_test_path, y_train_path, y_test_path, vectorizer_path)
        """
        logger.info("=" * 60)
        logger.info("Starting Data Transformation Pipeline")
        logger.info("=" * 60)
        
        try:
            # Configure MLflow
            mlruns_dir = self.project_root / "mlruns"
            mlruns_dir.mkdir(exist_ok=True)
            tracking_uri = f"file:///{mlruns_dir}".replace("\\", "/")
            mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment("sentiment_analysis_data_transformation")
            
            with mlflow.start_run(run_name="data_transformation"):
                # Log parameters
                mlflow.log_param("word_ngram_range", self.model_config.get("ngram_range", [1, 3]))
                mlflow.log_param("word_max_features", self.model_config.get("max_features", 30000))
                mlflow.log_param("char_ngram_range", self.model_config.get("char_ngram_range", [2, 5]))
                mlflow.log_param("char_max_features", self.model_config.get("char_max_features", 20000))
                mlflow.log_param("vectorizer_type", "FeatureUnion(word_tfidf + char_tfidf)")
                
                # Step 1: Load interim data
                logger.info("Loading interim data...")
                train_df = pd.read_csv(self.interim_data_path / "train.csv")
                test_df = pd.read_csv(self.interim_data_path / "test.csv")
                
                logger.info(f"Loaded train: {train_df.shape}, test: {test_df.shape}")
                mlflow.log_metric("raw_train_samples", len(train_df))
                mlflow.log_metric("raw_test_samples", len(test_df))
                
                # Step 2: Apply preprocessing
                train_df = self.apply_preprocessing(train_df)
                test_df = self.apply_preprocessing(test_df)
                
                # Step 2b: Load and combine YouTube data if available
                train_df = self.load_and_combine_youtube_data(train_df)
                
                mlflow.log_metric("processed_train_samples", len(train_df))
                mlflow.log_metric("processed_test_samples", len(test_df))
                
                # Step 3: Vectorize

                X_train, X_test, y_train, y_test, vectorizer = self.vectorize_data(train_df, test_df)
                
                mlflow.log_metric("train_features", X_train.shape[1])
                mlflow.log_metric("total_features", X_train.shape[1])  # FeatureUnion: use shape, not .vocabulary_
                
                # Step 4: Save processed data
                self.save_processed_data(X_train, X_test, y_train, y_test, vectorizer)
                
                # Log artifacts
                mlflow.log_artifact(str(self.processed_data_path / "feature_names.csv"))
                
                logger.info("Data Transformation Pipeline completed successfully!")
                logger.info("=" * 60)
                
                return (
                    str(self.processed_data_path / "X_train.pkl"),
                    str(self.processed_data_path / "X_test.pkl"),
                    str(self.processed_data_path / "y_train.pkl"),
                    str(self.processed_data_path / "y_test.pkl"),
                    str(self.processed_data_path / "vectorizer.pkl")
                )
                
        except Exception as e:
            logger.error(f"Data Transformation Pipeline failed: {e}")
            raise e


if __name__ == "__main__":
    try:
        transformation = DataTransformation()
        paths = transformation.initiate_data_transformation()
        print(f"\nData Transformation Complete!")
        print(f"X_train: {paths[0]}")
        print(f"X_test: {paths[1]}")
        print(f"y_train: {paths[2]}")
        print(f"y_test: {paths[3]}")
        print(f"Vectorizer: {paths[4]}")
    except Exception as e:
        logger.error(f"Failed to complete the data transformation process: {e}")
        sys.exit(1)
