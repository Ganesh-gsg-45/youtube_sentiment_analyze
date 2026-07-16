import os
import sys
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Tuple
import json

from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.common import read_yaml, create_directories, save_bin, load_bin
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

# Optional LightGBM
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
    logger.info("LightGBM is available.")
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logger.warning("LightGBM not installed. Skipping LightGBM model.")

# Optional XGBoost
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost not installed. Skipping XGBoost model.")


class ModelTrainer:
    def __init__(self, config_path: Path = None):
      
        self.project_root = Path(__file__).resolve().parent.parent.parent
        
        if config_path is None:
            config_path = self.project_root / "params.yaml"
        
        self.config = read_yaml(config_path)
        self.model_config = self.config.get("model_building", {})
        
        # Setup directories
        self.processed_data_path = self.project_root / "data" / "processed"
        self.models_path = self.project_root / "models"
        self.reports_path = self.project_root / "reports"
        
        create_directories([self.models_path, self.reports_path])
        
        # Results storage
        self.results = {}
        
        # Label mapping for XGBoost compatibility (-1,0,1 -> 0,1,2)
        self.label_map = {-1: 0, 0: 1, 1: 2}
        self.inverse_label_map = {0: -1, 1: 0, 2: 1}
        
        logger.info(f"ModelTrainer initialized. Project root: {self.project_root}")


    def load_processed_data(self) -> Tuple[Any, Any, Any, Any]:
      
        logger.info("Loading processed data...")
        
        X_train = load_bin(self.processed_data_path / "X_train.pkl")
        X_test = load_bin(self.processed_data_path / "X_test.pkl")
        y_train = load_bin(self.processed_data_path / "y_train.pkl")
        y_test = load_bin(self.processed_data_path / "y_test.pkl")
        
        logger.info(f"Loaded X_train: {X_train.shape}, X_test: {X_test.shape}")
        logger.info(f"Loaded y_train: {len(y_train)}, y_test: {len(y_test)}")
        
        # Remap labels from (-1, 0, 1) to (0, 1, 2) for XGBoost compatibility
        y_train = np.array([self.label_map[y] for y in y_train])
        y_test = np.array([self.label_map[y] for y in y_test])
        logger.info("Labels remapped from [-1, 0, 1] to [0, 1, 2]")
        
        return X_train, X_test, y_train, y_test


    def get_models(self) -> Dict[str, Any]:
        
        svc_c   = self.model_config.get("svc_c", 1.0)
        lr_c    = self.model_config.get("lr_c", 5.0)
        n_est   = self.model_config.get("n_estimators", 367)
        lr_rate = self.model_config.get("learning_rate", 0.09)
        depth   = self.model_config.get("max_depth", 20)

        models = {
            # LinearSVC wrapped in calibration to get proper predict_proba
            "LinearSVM": CalibratedClassifierCV(
                LinearSVC(C=svc_c, max_iter=3000, random_state=42),
                cv=3,
                method='sigmoid'
            ),

            # Logistic Regression — higher C works better with large sparse features
            "LogisticRegression": LogisticRegression(
                max_iter=1000,
                C=lr_c,
                solver='saga',   # saga handles large sparse matrices well
                random_state=42,
                n_jobs=-1
            ),

            # NaiveBayes — strong baseline for text
            "NaiveBayes": MultinomialNB(alpha=0.05),

            # SGDClassifier with log loss — fast & strong on sparse text
            "SGDClassifier": SGDClassifier(
                loss='log_loss',
                alpha=1e-4,
                max_iter=100,
                random_state=42,
                n_jobs=-1
            ),
        }

        # LightGBM — gradient boosting, handles high-dimensional sparse features well
        if LIGHTGBM_AVAILABLE:
            models["LightGBM"] = lgb.LGBMClassifier(
                n_estimators=n_est,
                max_depth=depth,
                learning_rate=lr_rate,
                num_leaves=63,
                subsample=0.8,
                colsample_bytree=0.6,
                min_child_samples=20,
                reg_alpha=0.1,
                reg_lambda=0.1,
                random_state=42,
                n_jobs=-1,
                verbose=-1
            )

        
        return models

    def evaluate_model(self, model, X_test, y_test) -> Dict[str, float]:
      
        y_pred = model.predict(X_test)
        
        metrics = {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'precision_macro': float(precision_score(y_test, y_pred, average='macro', zero_division=0)),
            'precision_weighted': float(precision_score(y_test, y_pred, average='weighted', zero_division=0)),
            'recall_macro': float(recall_score(y_test, y_pred, average='macro', zero_division=0)),
            'recall_weighted': float(recall_score(y_test, y_pred, average='weighted', zero_division=0)),
            'f1_macro': float(f1_score(y_test, y_pred, average='macro', zero_division=0)),
            'f1_weighted': float(f1_score(y_test, y_pred, average='weighted', zero_division=0))
        }
        
        return metrics, y_pred

    def log_confusion_matrix(self, y_test, y_pred, model_name: str):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        cm = confusion_matrix(y_test, y_pred)
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=['Negative', 'Neutral', 'Positive'],
                   yticklabels=['Negative', 'Neutral', 'Positive'])
        plt.title(f'Confusion Matrix - {model_name}')
        plt.ylabel('Actual')
        plt.xlabel('Predicted')
        plt.tight_layout()
        
        cm_path = self.reports_path / f"confusion_matrix_{model_name}.png"
        plt.savefig(cm_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return str(cm_path)

    def train_and_evaluate(self, X_train, X_test, y_train, y_test):
        
        models = self.get_models()
        
        for model_name, model in models.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"Training {model_name}")
            logger.info(f"{'='*60}")
            
            with mlflow.start_run(run_name=f"train_{model_name}", nested=True):
                # Log model parameters
                params = model.get_params()
                # Filter out non-serializable params
                serializable_params = {k: v for k, v in params.items() 
                                     if isinstance(v, (int, float, str, bool, type(None)))}
                mlflow.log_params(serializable_params)
                
                # Log vectorizer config (prefix to avoid collision with model params)
                mlflow.log_param("vectorizer_ngram_range", self.model_config.get("ngram_range", [1, 3]))
                mlflow.log_param("vectorizer_max_features", self.model_config.get("max_features", 1000))

                
                # Train model
                logger.info(f"Training {model_name}...")
                model.fit(X_train, y_train)
                
                # Evaluate
                metrics, y_pred = self.evaluate_model(model, X_test, y_test)
                
                # Log metrics
                mlflow.log_metrics(metrics)
                
                logger.info(f"Accuracy: {metrics['accuracy']:.4f}")
                logger.info(f"F1 (Weighted): {metrics['f1_weighted']:.4f}")
                logger.info(f"F1 (Macro): {metrics['f1_macro']:.4f}")
                
                # Log confusion matrix
                cm_path = self.log_confusion_matrix(y_test, y_pred, model_name)
                mlflow.log_artifact(cm_path, "confusion_matrices")
                
                # Log classification report
                report = classification_report(y_test, y_pred, 
                                              target_names=['Negative', 'Neutral', 'Positive'],
                                              output_dict=True)
                report_df = pd.DataFrame(report).transpose()
                report_path = self.reports_path / f"classification_report_{model_name}.csv"
                report_df.to_csv(report_path)
                mlflow.log_artifact(str(report_path), "classification_reports")
                
                # Log model
                mlflow.sklearn.log_model(model, f"{model_name}_model")
                
                # Store results
                self.results[model_name] = {
                    'model': model,
                    'metrics': metrics,
                    'model_name': model_name
                }
                
                logger.info(f"{model_name} training complete.")

    def select_best_model(self) -> Tuple[str, Any]:
      
        if not self.results:
            raise ValueError("No models trained yet.")
        
        best_model_name = max(self.results.keys(), 
                             key=lambda k: self.results[k]['metrics']['f1_weighted'])
        best_model = self.results[best_model_name]['model']
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Best Model: {best_model_name}")
        logger.info(f"F1-Weighted: {self.results[best_model_name]['metrics']['f1_weighted']:.4f}")
        logger.info(f"Accuracy: {self.results[best_model_name]['metrics']['accuracy']:.4f}")
        logger.info(f"{'='*60}")
        
        return best_model_name, best_model

    def save_best_model(self, best_model_name: str, best_model: Any):
       
        best_model_path = self.models_path / "best_model.pkl"
        save_bin(best_model, best_model_path)
        logger.info(f"Best model saved to: {best_model_path}")

        best_metrics = self.results[best_model_name]['metrics']

        model_info = {
            'best_model_name': best_model_name,
            'best_accuracy':   round(best_metrics['accuracy'], 4),
            'best_f1':         round(best_metrics['f1_weighted'], 4),
            'best_model_metrics': best_metrics,
            'label_map': self.label_map,
            'inverse_label_map': self.inverse_label_map,
            'all_model_results': {
                name: result['metrics']
                for name, result in self.results.items()
            }
        }

        with open(self.models_path / "best_model_info.json", 'w') as f:
            json.dump(model_info, f, indent=4)

        # Save comparison results — write to both reports/ (DVC artifact) and models/ (app.py reads from here)
        comparison_df = pd.DataFrame([
            {
                'Model':              name,
                'Accuracy':           result['metrics']['accuracy'],
                'F1_Macro':           result['metrics']['f1_macro'],
                'F1_Weighted':        result['metrics']['f1_weighted'],
                'Precision_Weighted': result['metrics']['precision_weighted'],
                'Recall_Weighted':    result['metrics']['recall_weighted']
            }
            for name, result in self.results.items()
        ]).sort_values('F1_Weighted', ascending=False)

        reports_comparison_path = self.reports_path / "model_comparison.csv"
        models_comparison_path  = self.models_path  / "model_comparison.csv"

        comparison_df.to_csv(reports_comparison_path, index=False)
        comparison_df.to_csv(models_comparison_path,  index=False)
        logger.info(f"Model comparison saved to: {reports_comparison_path} and {models_comparison_path}")

        # Print final leaderboard
        logger.info("\n" + "=" * 60)
        logger.info("FINAL MODEL LEADERBOARD")
        logger.info("=" * 60)
        for _, row in comparison_df.iterrows():
            marker = " <-- BEST" if row['Model'] == best_model_name else ""
            logger.info(
                f"  {row['Model']:20s}  Acc={row['Accuracy']:.4f}  "
                f"F1w={row['F1_Weighted']:.4f}{marker}"
            )
        logger.info("=" * 60)

        return str(best_model_path)

    def initiate_model_training(self) -> str:
        logger.info("=" * 60)
        logger.info("Starting Model Training Pipeline")
        logger.info("=" * 60)
        
        try:
            # Configure MLflow
            # Use SQLite backend (replaces deprecated file store; enables full features)
            mlflow_db = self.project_root / "mlflow.db"
            tracking_uri = f"sqlite:///{mlflow_db}".replace("\\", "/")
            mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment("sentiment_analysis_model_training")
            
            with mlflow.start_run(run_name="model_training"):
                # Load data
                X_train, X_test, y_train, y_test = self.load_processed_data()
                
                mlflow.log_param("train_samples", X_train.shape[0])
                mlflow.log_param("test_samples", X_test.shape[0])
                mlflow.log_param("num_features", X_train.shape[1])
                mlflow.log_param("num_classes", len(np.unique(y_train)))
                
                # Train and evaluate all models
                self.train_and_evaluate(X_train, X_test, y_train, y_test)
                
                # Select best model
                best_model_name, best_model = self.select_best_model()
                
                # Save best model
                best_model_path = self.save_best_model(best_model_name, best_model)
                
                # Log best model artifact
                mlflow.log_artifact(best_model_path, "best_model")
                mlflow.log_param("best_model", best_model_name)
                mlflow.log_metrics(self.results[best_model_name]['metrics'])
                
                logger.info("=" * 60)
                logger.info("Model Training Pipeline completed successfully!")
                logger.info("=" * 60)
                
                return best_model_path
                
        except Exception as e:
            logger.error(f"Model Training Pipeline failed: {e}")
            raise e


if __name__ == "__main__":
    try:
        trainer = ModelTrainer()
        best_model_path = trainer.initiate_model_training()
        print(f"\nModel Training Complete!")
        print(f"Best model saved to: {best_model_path}")
        
        # Print comparison
        print(f"\nModel Comparison:")
        for name, result in trainer.results.items():
            print(f"  {name:20s} - Accuracy: {result['metrics']['accuracy']:.4f}, "
                  f"F1-Weighted: {result['metrics']['f1_weighted']:.4f}")
        
    except Exception as e:
        logger.error(f"Failed to complete the model training process: {e}")
        sys.exit(1)
