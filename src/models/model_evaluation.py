import os
import sys
import logging
import pickle
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Tuple

from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.common import read_yaml, create_directories, load_bin
import mlflow
import mlflow.sklearn

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


class ModelEvaluation:
    def __init__(self, config_path: Path = None):
        """
        Initialize ModelEvaluation with configuration.
        
        Args:
            config_path: Path to params.yaml. If None, uses default path.
        """
        self.project_root = Path(__file__).resolve().parent.parent.parent
        
        if config_path is None:
            config_path = self.project_root / "params.yaml"
        
        self.config = read_yaml(config_path)
        
        # Setup directories
        self.processed_data_path = self.project_root / "data" / "processed"
        self.models_path = self.project_root / "models"
        self.reports_path = self.project_root / "reports"
        
        create_directories([self.reports_path])
        
        # Label mapping
        self.label_map = {-1: 0, 0: 1, 1: 2}
        self.inverse_label_map = {0: -1, 1: 0, 2: 1}
        self.class_names = ['Negative', 'Neutral', 'Positive']
        
        logger.info(f"ModelEvaluation initialized. Project root: {self.project_root}")

    def load_model_and_data(self) -> Tuple[Any, Any, Any]:
        """
        Load best model and test data.
        
        Returns:
            Tuple of (model, X_test, y_test)
        """
        logger.info("Loading best model and test data...")
        
        # Load model
        with open(self.models_path / "best_model.pkl", 'rb') as f:
            model = pickle.load(f)
        
        # Load model info
        with open(self.models_path / "best_model_info.json", 'r') as f:
            model_info = json.load(f)
        
        self.best_model_name = model_info['best_model_name']
        logger.info(f"Loaded best model: {self.best_model_name}")
        
        # Load test data
        X_test = load_bin(self.processed_data_path / "X_test.pkl")
        y_test = load_bin(self.processed_data_path / "y_test.pkl")
        
        # Remap labels for consistency
        y_test = np.array([self.label_map[y] for y in y_test])
        
        logger.info(f"Test data: X_test {X_test.shape}, y_test {len(y_test)}")
        
        return model, X_test, y_test, model_info

    def evaluate_model(self, model, X_test, y_test) -> Dict[str, Any]:
        """
        Perform comprehensive model evaluation.
        
        Args:
            model: Trained model.
            X_test: Test features.
            y_test: Test labels.
            
        Returns:
            Dictionary with evaluation metrics and predictions.
        """
        logger.info("Evaluating model on test set...")
        
        y_pred = model.predict(X_test)
        
        # Overall metrics
        metrics = {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'precision_macro': float(precision_score(y_test, y_pred, average='macro', zero_division=0)),
            'precision_weighted': float(precision_score(y_test, y_pred, average='weighted', zero_division=0)),
            'recall_macro': float(recall_score(y_test, y_pred, average='macro', zero_division=0)),
            'recall_weighted': float(recall_score(y_test, y_pred, average='weighted', zero_division=0)),
            'f1_macro': float(f1_score(y_test, y_pred, average='macro', zero_division=0)),
            'f1_weighted': float(f1_score(y_test, y_pred, average='weighted', zero_division=0))
        }
        
        # Per-class metrics
        report = classification_report(y_test, y_pred, 
                                       target_names=self.class_names,
                                       output_dict=True)
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        
        logger.info(f"Accuracy: {metrics['accuracy']:.4f}")
        logger.info(f"F1-Weighted: {metrics['f1_weighted']:.4f}")
        logger.info(f"F1-Macro: {metrics['f1_macro']:.4f}")
        
        return {
            'metrics': metrics,
            'predictions': y_pred,
            'classification_report': report,
            'confusion_matrix': cm
        }

    def generate_confusion_matrix_plot(self, cm: np.ndarray) -> str:
        """
        Generate confusion matrix visualization.
        
        Args:
            cm: Confusion matrix array.
            
        Returns:
            Path to saved plot.
        """
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=self.class_names,
                   yticklabels=self.class_names,
                   cbar_kws={'label': 'Count'})
        plt.title(f'Confusion Matrix - {self.best_model_name} (Best Model)', fontsize=14)
        plt.ylabel('Actual Label', fontsize=12)
        plt.xlabel('Predicted Label', fontsize=12)
        plt.tight_layout()
        
        cm_path = self.reports_path / f"best_model_confusion_matrix.png"
        plt.savefig(cm_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Confusion matrix plot saved to: {cm_path}")
        return str(cm_path)

    def generate_evaluation_report(self, results: Dict) -> str:
        """
        Generate comprehensive evaluation report.
        
        Args:
            results: Evaluation results dictionary.
            
        Returns:
            Path to saved report.
        """
        report_lines = [
            "=" * 60,
            "MODEL EVALUATION REPORT",
            "=" * 60,
            f"Best Model: {self.best_model_name}",
            "",
            "OVERALL METRICS",
            "-" * 40,
            f"Accuracy:           {results['metrics']['accuracy']:.4f}",
            f"Precision (Macro):  {results['metrics']['precision_macro']:.4f}",
            f"Precision (Weighted): {results['metrics']['precision_weighted']:.4f}",
            f"Recall (Macro):     {results['metrics']['recall_macro']:.4f}",
            f"Recall (Weighted):  {results['metrics']['recall_weighted']:.4f}",
            f"F1-Score (Macro):   {results['metrics']['f1_macro']:.4f}",
            f"F1-Score (Weighted): {results['metrics']['f1_weighted']:.4f}",
            "",
            "PER-CLASS METRICS",
            "-" * 40,
        ]
        
        for class_name in self.class_names:
            class_metrics = results['classification_report'][class_name]
            report_lines.extend([
                f"{class_name}:",
                f"  Precision: {class_metrics['precision']:.4f}",
                f"  Recall:    {class_metrics['recall']:.4f}",
                f"  F1-Score:  {class_metrics['f1-score']:.4f}",
                f"  Support:   {int(class_metrics['support'])}",
                ""
            ])
        
        report_lines.extend([
            "CONFUSION MATRIX",
            "-" * 40,
            str(results['confusion_matrix']),
            "",
            "=" * 60,
        ])
        
        report_text = "\n".join(report_lines)
        
        report_path = self.reports_path / "model_evaluation_report.txt"
        with open(report_path, 'w') as f:
            f.write(report_text)
        
        logger.info(f"Evaluation report saved to: {report_path}")
        return str(report_path)

    def save_detailed_results(self, results: Dict):
        """
        Save detailed results to CSV files.
        
        Args:
            results: Evaluation results dictionary.
        """
        # Save per-class metrics
        report_df = pd.DataFrame(results['classification_report']).transpose()
        report_path = self.reports_path / "best_model_classification_report.csv"
        report_df.to_csv(report_path)
        logger.info(f"Classification report saved to: {report_path}")
        
        # Save confusion matrix
        cm_df = pd.DataFrame(
            results['confusion_matrix'],
            index=[f'Actual_{c}' for c in self.class_names],
            columns=[f'Predicted_{c}' for c in self.class_names]
        )
        cm_path = self.reports_path / "best_model_confusion_matrix.csv"
        cm_df.to_csv(cm_path)
        logger.info(f"Confusion matrix CSV saved to: {cm_path}")

    def initiate_model_evaluation(self) -> Dict[str, Any]:
        """
        Orchestrate the complete model evaluation pipeline.
        
        Returns:
            Dictionary with evaluation results.
        """
        logger.info("=" * 60)
        logger.info("Starting Model Evaluation Pipeline")
        logger.info("=" * 60)
        
        try:
            # Configure MLflow
            mlruns_dir = self.project_root / "mlruns"
            mlruns_dir.mkdir(exist_ok=True)
            tracking_uri = f"file:///{mlruns_dir}".replace("\\", "/")
            mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment("sentiment_analysis_model_evaluation")
            
            with mlflow.start_run(run_name="model_evaluation"):
                # Load model and data
                model, X_test, y_test, model_info = self.load_model_and_data()
                
                # Log model info
                mlflow.log_param("best_model_name", self.best_model_name)
                mlflow.log_params(model_info.get('best_model_metrics', {}))
                
                # Evaluate
                results = self.evaluate_model(model, X_test, y_test)
                
                # Log metrics
                mlflow.log_metrics(results['metrics'])
                
                # Generate visualizations
                cm_path = self.generate_confusion_matrix_plot(results['confusion_matrix'])
                mlflow.log_artifact(cm_path, "evaluation_plots")
                
                # Generate and save reports
                report_path = self.generate_evaluation_report(results)
                mlflow.log_artifact(report_path, "evaluation_reports")
                
                # Save detailed results
                self.save_detailed_results(results)
                
                # Log classification report as artifact
                report_csv = self.reports_path / "best_model_classification_report.csv"
                mlflow.log_artifact(str(report_csv), "evaluation_reports")
                
                logger.info("=" * 60)
                logger.info("Model Evaluation Pipeline completed successfully!")
                logger.info("=" * 60)
                
                return results
                
        except Exception as e:
            logger.error(f"Model Evaluation Pipeline failed: {e}")
            raise e


if __name__ == "__main__":
    try:
        evaluator = ModelEvaluation()
        results = evaluator.initiate_model_evaluation()
        
        print(f"\nModel Evaluation Complete!")
        print(f"Best Model: {evaluator.best_model_name}")
        print(f"Accuracy: {results['metrics']['accuracy']:.4f}")
        print(f"F1-Weighted: {results['metrics']['f1_weighted']:.4f}")
        print(f"F1-Macro: {results['metrics']['f1_macro']:.4f}")
        print(f"\nPer-Class F1-Scores:")
        for class_name in evaluator.class_names:
            f1 = results['classification_report'][class_name]['f1-score']
            print(f"  {class_name:12s}: {f1:.4f}")
        
    except Exception as e:
        logger.error(f"Failed to complete the model evaluation process: {e}")
        sys.exit(1)
