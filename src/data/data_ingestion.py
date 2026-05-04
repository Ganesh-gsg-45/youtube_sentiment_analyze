import os
import sys
import logging
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.common import read_yaml, create_directories, get_size
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


class DataIngestion:
    def __init__(self, config_path: Path = None):
        """
        Initialize DataIngestion with configuration.
        
        Args:
            config_path: Path to params.yaml. If None, uses default path.
        """
        self.project_root = Path(__file__).resolve().parent.parent.parent
        
        if config_path is None:
            config_path = self.project_root / "params.yaml"
        
        self.config = read_yaml(config_path)
        self.data_ingestion_config = self.config.get("data_ingestion", {})
        
        # Setup directories
        self.raw_data_path = self.project_root / "data" / "raw"
        self.interim_data_path = self.project_root / "data" / "interim"
        self.processed_data_path = self.project_root / "data" / "processed"
        
        create_directories([
            self.raw_data_path,
            self.interim_data_path,
            self.processed_data_path
        ])
        
        # Data URL from the original source
        self.data_url = "https://raw.githubusercontent.com/Himanshu-1703/reddit-sentiment-analysis/refs/heads/main/data/reddit.csv"
        
        logger.info(f"DataIngestion initialized. Project root: {self.project_root}")
        logger.info(f"Config loaded from: {config_path}")

    def download_data(self) -> Path:
        """
        Downloads the raw dataset from URL if not already present.
        
        Returns:
            Path to the downloaded raw CSV file.
        """
        raw_file_path = self.raw_data_path / "reddit.csv"
        
        try:
            if raw_file_path.exists():
                logger.info(f"Raw data already exists at: {raw_file_path}")
                logger.info(f"File size: {get_size(raw_file_path)}")
            else:
                logger.info(f"Downloading data from: {self.data_url}")
                df = pd.read_csv(self.data_url)
                df.to_csv(raw_file_path, index=False)
                logger.info(f"Data downloaded successfully to: {raw_file_path}")
                logger.info(f"File size: {get_size(raw_file_path)}")
            
            return raw_file_path
            
        except Exception as e:
            logger.error(f"Failed to download data: {e}")
            raise e

    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validates and cleans the raw dataframe.
        
        Args:
            df: Raw dataframe.
            
        Returns:
            Cleaned dataframe.
        """
        logger.info(f"Original data shape: {df.shape}")
        
        # Check required columns
        required_columns = ['clean_comment', 'category']
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Remove missing values
        initial_rows = len(df)
        df = df.dropna(subset=required_columns)
        logger.info(f"Dropped {initial_rows - len(df)} rows with missing values")
        
        # Remove duplicates
        initial_rows = len(df)
        df = df.drop_duplicates()
        logger.info(f"Dropped {initial_rows - len(df)} duplicate rows")
        
        # Remove empty comments
        initial_rows = len(df)
        df = df[~(df['clean_comment'].str.strip() == '')]
        logger.info(f"Dropped {initial_rows - len(df)} rows with empty comments")
        
        # Convert category to integer
        df['category'] = df['category'].astype(int)
        
        logger.info(f"Cleaned data shape: {df.shape}")
        logger.info(f"Class distribution:\n{df['category'].value_counts().sort_index()}")
        
        return df

    def split_data(self, df: pd.DataFrame) -> tuple:
        """
        Splits data into train and test sets.
        
        Args:
            df: Cleaned dataframe.
            
        Returns:
            Tuple of (train_df, test_df)
        """
        test_size = self.data_ingestion_config.get("test_size", 0.20)
        random_state = self.data_ingestion_config.get("random_state", 42)
        
        logger.info(f"Splitting data with test_size={test_size}, random_state={random_state}")
        
        train_df, test_df = train_test_split(
            df,
            test_size=test_size,
            random_state=random_state,
            stratify=df['category']
        )
        
        logger.info(f"Train set shape: {train_df.shape}")
        logger.info(f"Test set shape: {test_df.shape}")
        
        return train_df, test_df

    def save_processed_data(self, train_df: pd.DataFrame, test_df: pd.DataFrame):
        """
        Saves train and test data to interim folder.
        
        Args:
            train_df: Training dataframe.
            test_df: Testing dataframe.
        """
        train_path = self.interim_data_path / "train_processed.csv"
        test_path = self.interim_data_path / "test_processed.csv"

        
        train_df.to_csv(train_path, index=False)
        test_df.to_csv(test_path, index=False)
        
        logger.info(f"Train data saved to: {train_path}")
        logger.info(f"Test data saved to: {test_path}")
        logger.info(f"Train file size: {get_size(train_path)}")
        logger.info(f"Test file size: {get_size(test_path)}")

    def initiate_data_ingestion(self) -> tuple:
        """
        Orchestrates the complete data ingestion pipeline.
        
        Returns:
            Tuple of (train_df, test_df) paths.
        """
        logger.info("=" * 60)
        logger.info("Starting Data Ingestion Pipeline")
        logger.info("=" * 60)
        
        try:
            # Configure MLflow to use local directory (fix for paths with spaces)
            mlruns_dir = self.project_root / "mlruns"
            mlruns_dir.mkdir(exist_ok=True)
            tracking_uri = f"file:///{mlruns_dir}".replace("\\", "/")
            mlflow.set_tracking_uri(tracking_uri)
            logger.info(f"MLflow tracking URI: {tracking_uri}")
            
            # Start MLflow run for tracking
            mlflow.set_experiment("sentiment_analysis_data_ingestion")
            
            with mlflow.start_run(run_name="data_ingestion"):
                # Log parameters
                mlflow.log_param("test_size", self.data_ingestion_config.get("test_size", 0.20))
                mlflow.log_param("data_source", self.data_url)
                
                # Step 1: Download data
                raw_path = self.download_data()
                mlflow.log_artifact(str(raw_path), "raw_data")
                
                # Step 2: Load and validate
                df = pd.read_csv(raw_path)
                df = self.validate_data(df)
                mlflow.log_metric("total_samples", len(df))
                mlflow.log_metric("num_features", df.shape[1])
                
                # Step 3: Split data
                train_df, test_df = self.split_data(df)
                mlflow.log_metric("train_samples", len(train_df))
                mlflow.log_metric("test_samples", len(test_df))
                
                # Log class distributions
                for category, count in train_df['category'].value_counts().sort_index().items():
                    mlflow.log_metric(f"train_class_{category}", count)
                
                # Step 4: Save processed data
                self.save_processed_data(train_df, test_df)
                
                # Log artifacts
                mlflow.log_artifact(str(self.interim_data_path / "train_processed.csv"), "interim_data")
                mlflow.log_artifact(str(self.interim_data_path / "test_processed.csv"), "interim_data")

                
                logger.info("Data Ingestion Pipeline completed successfully!")
                logger.info("=" * 60)
                
                return (
                    str(self.interim_data_path / "train_processed.csv"),
                    str(self.interim_data_path / "test_processed.csv")
                )

                
        except Exception as e:
            logger.error(f"Data Ingestion Pipeline failed: {e}")
            raise e


if __name__ == "__main__":
    try:
        ingestion = DataIngestion()
        train_path, test_path = ingestion.initiate_data_ingestion()
        print(f"\nData Ingestion Complete!")
        print(f"Train data: {train_path}")
        print(f"Test data: {test_path}")
    except Exception as e:
        logger.error(f"Failed to complete the data ingestion process: {e}")
        sys.exit(1)
