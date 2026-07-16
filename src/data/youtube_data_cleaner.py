import os
import sys
import re
import logging
import pandas as pd
from pathlib import Path

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.common import read_yaml, create_directories, save_bin, get_size

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


class YouTubeDataCleaner:
    """
    Cleans and preprocesses YouTube comments for sentiment analysis.
    
    Applies the same preprocessing as the Reddit pipeline, plus
    YouTube-specific cleaning for mentions, timestamps, and emojis.
    """
    
    def __init__(self, config_path: Path = None):
        """
        Initialize YouTubeDataCleaner.
        
        Args:
            config_path: Path to params.yaml. If None, uses default path.
        """
        self.project_root = Path(__file__).resolve().parent.parent.parent
        
        if config_path is None:
            config_path = self.project_root / "params.yaml"
        
        self.config = read_yaml(config_path)
        
        # Setup directories
        self.raw_data_path = self.project_root / "data" / "raw"
        self.interim_data_path = self.project_root / "data" / "interim"
        create_directories([self.interim_data_path])
        
        # Download NLTK data if not present
        self._ensure_nltk_data()
        
        # Initialize preprocessing components
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english')) - {'not', 'but', 'however', 'no', 'yet'}
        
        logger.info(f"YouTubeDataCleaner initialized. Project root: {self.project_root}")

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
        Apply text preprocessing steps (same as Reddit pipeline).
        
        Args:
            text: Raw text string.
            
        Returns:
            Cleaned and preprocessed text string.
        """
        if pd.isna(text) or not isinstance(text, str):
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

    def clean_youtube_specific(self, text: str) -> str:
        """
        Apply YouTube-specific cleaning.
        
        Args:
            text: Raw YouTube comment text.
            
        Returns:
            Cleaned text.
        """
        if pd.isna(text) or not isinstance(text, str):
            return ""
        
        # Remove @mentions (e.g., @username)
        text = re.sub(r'@\w+', '', text)
        
        # Remove timestamps (e.g., 0:42, 12:34, 1:23:45)
        text = re.sub(r'\b\d{1,2}:\d{2}(?::\d{2})?\b', '', text)
        
        # Remove emoji (various patterns)
        # Remove Unicode emojis
        text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)  # Emoticons
        text = re.sub(r'[\U0001F300-\U0001F5FF]', '', text)  # Symbols & pictographs
        text = re.sub(r'[\U0001F680-\U0001F6FF]', '', text)  # Transport & map symbols
        text = re.sub(r'[\U0001F1E0-\U0001F1FF]', '', text)  # Flags
        text = re.sub(r'[\U00002702-\U000027B0]', '', text)  # Dingbats
        text = re.sub(r'[\U000024C2-\U0001F251]', '', text)  # Enclosed characters
        
        # Remove ASCII emoticons
        text = re.sub(r'[:;=]-?[)(/\[\]{}|DPp@#$*]', '', text)
        
        # Remove excessive punctuation (more than 2 consecutive)
        text = re.sub(r'([!?.,])\1{2,}', r'\1\1', text)
        
        # Remove "first", "second", "early" spam comments (common YouTube spam)
        spam_patterns = [
            r'\b(first|second|third|early)\s*comment?\b',
            r'\bfirst\s*here\b',
            r'\bwho.*watching.*\d{4}\b',
            r'\blike.*comment.*sub\b',
        ]
        for pattern in spam_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def clean_comment(self, text: str) -> str:
        """
        Full cleaning pipeline for a single comment.
        
        Args:
            text: Raw comment text.
            
        Returns:
            Fully cleaned text.
        """
        # Step 1: YouTube-specific cleaning
        text = self.clean_youtube_specific(text)
        
        # Step 2: General preprocessing (same as Reddit)
        text = self.preprocess_text(text)
        
        return text

    def load_raw_data(self) -> pd.DataFrame:
        """
        Load raw YouTube comments from latest extraction.
        
        Returns:
            DataFrame with raw comments.
        """
        # Try latest first, then fallback to any youtube_comments file
        raw_path = self.raw_data_path / "youtube_comments_latest.csv"
        
        if not raw_path.exists():
            # Find any youtube_comments file
            files = list(self.raw_data_path.glob("youtube_comments_*.csv"))
            if not files:
                raise FileNotFoundError(
                    "No YouTube comments file found in data/raw/. "
                    "Run youtube_data_extractor.py first."
                )
            raw_path = max(files, key=lambda p: p.stat().st_mtime)
        
        df = pd.read_csv(raw_path)
        logger.info(f"Loaded raw comments: {len(df)} rows from {raw_path}")
        return df

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean all comments in a DataFrame.
        
        Args:
            df: DataFrame with 'text' column.
            
        Returns:
            DataFrame with cleaned comments.
        """
        logger.info("Starting YouTube data cleaning...")
        
        # Create a copy
        df = df.copy()
        
        # Rename 'text' column to 'clean_comment' after processing
        logger.info("Applying YouTube-specific cleaning and general preprocessing...")
        df['clean_comment'] = df['text'].astype(str).apply(self.clean_comment)
        
        # Remove empty comments after cleaning
        initial_rows = len(df)
        df = df[df['clean_comment'].str.strip() != '']
        logger.info(f"Dropped {initial_rows - len(df)} empty comments after cleaning")
        
        # Remove duplicates
        initial_rows = len(df)
        df = df.drop_duplicates(subset=['clean_comment'])
        logger.info(f"Dropped {initial_rows - len(df)} duplicate comments")
        
        # Select relevant columns
        output_df = df[['comment_id', 'video_id', 'clean_comment', 'author', 
                        'like_count', 'published_at', 'reply_count']].copy()
        
        logger.info(f"Final cleaned data shape: {output_df.shape}")
        logger.info(f"Average comment length: {output_df['clean_comment'].str.len().mean():.1f} chars")
        
        return output_df

    def save_cleaned_data(self, df: pd.DataFrame):
        """
        Save cleaned comments to CSV.
        
        Args:
            df: DataFrame with cleaned comments.
        """
        output_path = self.interim_data_path / "youtube_cleaned.csv"
        df.to_csv(output_path, index=False)
        logger.info(f"Cleaned comments saved to: {output_path}")
        logger.info(f"File size: {get_size(output_path)}")
        return str(output_path)

    def initiate_cleaning(self) -> str:
        """
        Orchestrate the complete YouTube data cleaning pipeline.
        
        Returns:
            Path to saved cleaned comments CSV.
        """
        logger.info("=" * 60)
        logger.info("Starting YouTube Data Cleaning")
        logger.info("=" * 60)
        
        try:
            # Load raw data
            df = self.load_raw_data()
            
            # Clean data
            cleaned_df = self.clean_dataframe(df)
            
            if cleaned_df.empty:
                logger.warning("No comments remaining after cleaning!")
                return None
            
            # Save cleaned data
            output_path = self.save_cleaned_data(cleaned_df)
            
            logger.info("=" * 60)
            logger.info("YouTube Data Cleaning completed successfully!")
            logger.info("=" * 60)
            
            return output_path
            
        except Exception as e:
            logger.error(f"YouTube Data Cleaning failed: {e}")
            raise e


def main():
    """Run YouTube data cleaning from command line."""
    try:
        cleaner = YouTubeDataCleaner()
        output_path = cleaner.initiate_cleaning()
        
        if output_path:
            print(f"\nCleaning complete! Saved to: {output_path}")
        else:
            print("\nNo comments to clean!")
            
    except Exception as e:
        logger.error(f"Failed to complete cleaning: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
