import os
import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.common import read_yaml, create_directories, save_bin
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


class DataValidation:
    def __init__(self, config_path: Path = None):
        """
        Initialize DataValidation with configuration.
        
        Args:
            config_path: Path to params.yaml. If None, uses default path.
        """
        self.project_root = Path(__file__).resolve().parent.parent.parent
        
        if config_path is None:
            config_path = self.project_root / "params.yaml"
        
        self.config = read_yaml(config_path)
        
        # Setup directories
        self.interim_data_path = self.project_root / "data" / "interim"
        self.reports_path = self.project_root / "reports"
        
        create_directories([self.reports_path])
        
        # Validation thresholds
        self.validation_config = self.config.get("data_validation", {})
        self.max_missing_ratio = self.validation_config.get("max_missing_ratio", 0.05)
        self.max_duplicate_ratio = self.validation_config.get("max_duplicate_ratio", 0.10)
        self.min_samples_per_class = self.validation_config.get("min_samples_per_class", 100)
        
        logger.info(f"DataValidation initialized. Project root: {self.project_root}")

    def validate_schema(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate that dataframe has required columns and correct types.
        
        Args:
            df: DataFrame to validate.
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        required_columns = ['clean_comment', 'category']
        
        # Check columns exist
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")
        
        # Check data types
        if 'category' in df.columns:
            if not pd.api.types.is_numeric_dtype(df['category']):
                errors.append("Column 'category' must be numeric")
        
        if 'clean_comment' in df.columns:
            if not pd.api.types.is_string_dtype(df['clean_comment']):
                errors.append("Column 'clean_comment' must be string type")
        
        is_valid = len(errors) == 0
        return is_valid, errors

    def validate_missing_values(self, df: pd.DataFrame) -> Tuple[bool, Dict]:
        """
        Check for missing values within acceptable threshold.
        
        Args:
            df: DataFrame to validate.
            
        Returns:
            Tuple of (is_valid, metrics dict)
        """
        missing = df.isnull().sum()
        total_cells = df.shape[0] * df.shape[1]
        total_missing = missing.sum()
        missing_ratio = total_missing / total_cells
        
        metrics = {
            'total_missing': int(total_missing),
            'missing_ratio': float(missing_ratio),
            'missing_by_column': missing.to_dict()
        }
        
        is_valid = missing_ratio <= self.max_missing_ratio
        
        logger.info(f"Missing values: {total_missing} ({missing_ratio:.4f})")
        if not is_valid:
            logger.warning(f"Missing ratio {missing_ratio:.4f} exceeds threshold {self.max_missing_ratio}")
        
        return is_valid, metrics

    def validate_duplicates(self, df: pd.DataFrame) -> Tuple[bool, Dict]:
        """
        Check for duplicate rows within acceptable threshold.
        
        Args:
            df: DataFrame to validate.
            
        Returns:
            Tuple of (is_valid, metrics dict)
        """
        duplicates = df.duplicated().sum()
        duplicate_ratio = duplicates / len(df)
        
        metrics = {
            'total_duplicates': int(duplicates),
            'duplicate_ratio': float(duplicate_ratio)
        }
        
        is_valid = duplicate_ratio <= self.max_duplicate_ratio
        
        logger.info(f"Duplicate rows: {duplicates} ({duplicate_ratio:.4f})")
        if not is_valid:
            logger.warning(f"Duplicate ratio {duplicate_ratio:.4f} exceeds threshold {self.max_duplicate_ratio}")
        
        return is_valid, metrics

    def validate_class_distribution(self, df: pd.DataFrame) -> Tuple[bool, Dict]:
        """
        Validate that target classes have sufficient samples.
        
        Args:
            df: DataFrame to validate.
            
        Returns:
            Tuple of (is_valid, metrics dict)
        """
        class_counts = df['category'].value_counts().sort_index()
        
        metrics = {
            'num_classes': int(len(class_counts)),
            'class_distribution': class_counts.to_dict(),
            'min_class_count': int(class_counts.min()),
            'max_class_count': int(class_counts.max()),
            'class_balance_ratio': float(class_counts.min() / class_counts.max())
        }
        
        is_valid = class_counts.min() >= self.min_samples_per_class
        
        logger.info(f"Classes: {metrics['num_classes']}, Min count: {metrics['min_class_count']}")
        logger.info(f"Class distribution: {dict(class_counts)}")
        
        if not is_valid:
            logger.warning(f"Minimum class count {class_counts.min()} below threshold {self.min_samples_per_class}")
        
        return is_valid, metrics

    def validate_text_length(self, df: pd.DataFrame) -> Tuple[bool, Dict]:
        """
        Validate text comment lengths.
        
        Args:
            df: DataFrame to validate.
            
        Returns:
            Tuple of (is_valid, metrics dict)
        """
        text_lengths = df['clean_comment'].astype(str).str.len()
        
        metrics = {
            'min_length': int(text_lengths.min()),
            'max_length': int(text_lengths.max()),
            'mean_length': float(text_lengths.mean()),
            'median_length': float(text_lengths.median()),
            'empty_texts': int((text_lengths == 0).sum())
        }
        
        # Flag if there are empty texts
        is_valid = metrics['empty_texts'] == 0
        
        logger.info(f"Text length stats - Min: {metrics['min_length']}, Max: {metrics['max_length']}, Mean: {metrics['mean_length']:.1f}")
        logger.info(f"Empty texts: {metrics['empty_texts']}")
        
        return is_valid, metrics

    def generate_validation_report(self, validation_results: Dict) -> pd.DataFrame:
        """
        Generate a validation report dataframe.
        
        Args:
            validation_results: Dictionary of validation results.
            
        Returns:
            DataFrame with validation summary.
        """
        report_data = []
        for check_name, result in validation_results.items():
            report_data.append({
                'Check': check_name,
                'Passed': 'Yes' if result['is_valid'] else 'No',
                'Details': str(result.get('metrics', {}))[:200]
            })
        
        report_df = pd.DataFrame(report_data)
        return report_df

    def validate_dataset(self, df: pd.DataFrame, dataset_name: str = "dataset") -> Dict:
        """
        Run all validation checks on a dataset.
        
        Args:
            df: DataFrame to validate.
            dataset_name: Name of the dataset for logging.
            
        Returns:
            Dictionary with all validation results.
        """
        logger.info(f"\n{'='*50}")
        logger.info(f"Validating {dataset_name}")
        logger.info(f"{'='*50}")
        logger.info(f"Shape: {df.shape}")
        
        results = {}
        
        # Run all validation checks
        schema_valid, schema_errors = self.validate_schema(df)
        results['schema'] = {
            'is_valid': schema_valid,
            'errors': schema_errors,
            'metrics': {'columns': list(df.columns), 'dtypes': {k: str(v) for k, v in df.dtypes.items()}}
        }
        
        missing_valid, missing_metrics = self.validate_missing_values(df)
        results['missing_values'] = {
            'is_valid': missing_valid,
            'metrics': missing_metrics
        }
        
        duplicates_valid, duplicates_metrics = self.validate_duplicates(df)
        results['duplicates'] = {
            'is_valid': duplicates_valid,
            'metrics': duplicates_metrics
        }
        
        class_valid, class_metrics = self.validate_class_distribution(df)
        results['class_distribution'] = {
            'is_valid': class_valid,
            'metrics': class_metrics
        }
        
        text_valid, text_metrics = self.validate_text_length(df)
        results['text_length'] = {
            'is_valid': text_valid,
            'metrics': text_metrics
        }
        
        # Overall validation status
        all_valid = all(r['is_valid'] for r in results.values())
        results['overall'] = {
            'is_valid': all_valid,
            'total_checks': len(results),
            'passed_checks': sum(1 for r in results.values() if r['is_valid'])
        }
        
        logger.info(f"\nValidation Summary for {dataset_name}:")
        logger.info(f"Total checks: {results['overall']['total_checks']}")
        logger.info(f"Passed: {results['overall']['passed_checks']}")
        logger.info(f"Overall status: {'PASSED' if all_valid else 'FAILED'}")
        
        return results

    def initiate_data_validation(self) -> Dict:
        """
        Orchestrates the complete data validation pipeline.
        
        Returns:
            Dictionary with validation results for train and test sets.
        """
        logger.info("=" * 60)
        logger.info("Starting Data Validation Pipeline")
        logger.info("=" * 60)
        
        try:
            # Configure MLflow
            mlruns_dir = self.project_root / "mlruns"
            mlruns_dir.mkdir(exist_ok=True)
            tracking_uri = f"file:///{mlruns_dir}".replace("\\", "/")
            mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment("sentiment_analysis_data_validation")
            
            with mlflow.start_run(run_name="data_validation"):
                # Load interim data
                logger.info("Loading interim data...")
                train_df = pd.read_csv(self.interim_data_path / "train.csv")
                test_df = pd.read_csv(self.interim_data_path / "test.csv")
                
                # Validate train set
                train_results = self.validate_dataset(train_df, "train")
                
                # Validate test set
                test_results = self.validate_dataset(test_df, "test")
                
                # Log metrics to MLflow
                mlflow.log_metric("train_samples", len(train_df))
                mlflow.log_metric("test_samples", len(test_df))
                mlflow.log_metric("train_checks_passed", train_results['overall']['passed_checks'])
                mlflow.log_metric("test_checks_passed", test_results['overall']['passed_checks'])
                mlflow.log_param("train_overall_valid", train_results['overall']['is_valid'])
                mlflow.log_param("test_overall_valid", test_results['overall']['is_valid'])
                
                # Generate and save report
                train_report = self.generate_validation_report(train_results)
                test_report = self.generate_validation_report(test_results)
                
                report_path = self.reports_path / "data_validation_report.csv"
                combined_report = pd.concat([
                    train_report.assign(dataset='train'),
                    test_report.assign(dataset='test')
                ])
                combined_report.to_csv(report_path, index=False)
                logger.info(f"Validation report saved to: {report_path}")
                
                # Log artifacts
                mlflow.log_artifact(str(report_path))
                
                # Final status
                overall_valid = train_results['overall']['is_valid'] and test_results['overall']['is_valid']
                
                if overall_valid:
                    logger.info("=" * 60)
                    logger.info("Data Validation PASSED - Proceeding to transformation")
                    logger.info("=" * 60)
                else:
                    logger.warning("=" * 60)
                    logger.warning("Data Validation FAILED - Check reports for details")
                    logger.warning("=" * 60)
                
                return {
                    'train': train_results,
                    'test': test_results,
                    'overall_valid': overall_valid
                }
                
        except Exception as e:
            logger.error(f"Data Validation Pipeline failed: {e}")
            raise e


if __name__ == "__main__":
    try:
        validator = DataValidation()
        results = validator.initiate_data_validation()
        
        print(f"\nData Validation Complete!")
        print(f"Train checks passed: {results['train']['overall']['passed_checks']}/{results['train']['overall']['total_checks']}")
        print(f"Test checks passed: {results['test']['overall']['passed_checks']}/{results['test']['overall']['total_checks']}")
        print(f"Overall status: {'PASSED' if results['overall_valid'] else 'FAILED'}")
        
        sys.exit(0 if results['overall_valid'] else 1)
        
    except Exception as e:
        logger.error(f"Failed to complete the data validation process: {e}")
        sys.exit(1)
