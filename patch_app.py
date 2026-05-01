
import re
from pathlib import Path
def main():
    app_path = Path("app.py")
    content = app_path.read_text(encoding="utf-8")
    
    # 1. Add MLflow import
    if "MLFLOW_AVAILABLE" not in content:
        marker = "from googleapiclient.errors import HttpError"
        import_block = (
            "from googleapiclient.errors import HttpError\n\n"
            "# MLflow for insights\n"
            "try:\n"
            "    import mlflow\n"
            "    MLFLOW_AVAILABLE = True\n"
            "except ImportError:\n"
            "    MLFLOW_AVAILABLE = False"
        )
        content = content.replace(marker, import_block)
        print("[patch] Added MLflow import")
    
    # 2. Add get_mlflow_insights function and route
    if "def get_mlflow_insights():" not in content:
        marker = "    return default_info\n\n\n@app.route('/')\ndef index():"
        helper = '''    return default_info


def get_mlflow_insights():
    """Query MLflow for experiment insights."""
    if not MLFLOW_AVAILABLE:
        return {"error": "MLflow not installed"}
    try:
        from pathlib import Path
        project_root = Path(__file__).resolve().parent
        
        sqlite_db = project_root / "mlflow.db"
        mlruns_dir = project_root / "mlruns"
        if sqlite_db.exists():
            tracking_uri = f"sqlite:///{sqlite_db}".replace("\\\\", "/")
        elif mlruns_dir.exists():
            tracking_uri = "mlruns"

        else:
            return {"error": "No MLflow tracking data found"}
        
        mlflow.set_tracking_uri(tracking_uri)
        experiment = mlflow.get_experiment_by_name("sentiment_analysis_model_training")
        if experiment is None:
            return {"error": "Experiment not found"}
        
        runs_df = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
        if runs_df.empty:
            return {"error": "No runs found"}
        
        metrics = ["accuracy", "f1_weighted", "f1_macro", "precision_weighted", "recall_weighted"]
        metric_labels = {
            "accuracy": "Accuracy",
            "f1_weighted": "F1 Weighted",
            "f1_macro": "F1 Macro",
            "precision_weighted": "Precision Weighted",
            "recall_weighted": "Recall Weighted"
        }
        
        best_by_metric = {}
        for m in metrics:
            col = f"metrics.{m}"
            if col not in runs_df.columns:
                continue
            valid = runs_df.dropna(subset=[col])
            if valid.empty:
                continue
            best = valid.sort_values(col, ascending=False).iloc[0]
            best_by_metric[m] = {
                "run_id": best["run_id"],
n                "run_name": best.get("tags.mlflow.runName", ""),\n                "model": best.get("tags.mlflow.runName", "").replace("train_", ""),\n                "value": round(best[col], 5)\n            }\n        \n        leaderboard = []\n        for _, run in runs_df.iterrows():\n            row = {\n                "run_id": run["run_id"],\n                "run_name": run.get("tags.mlflow.runName", ""),\n                "model": run.get("tags.mlflow.runName", "").replace("train_", ""),\n                "status": run.get("status", "")\n            }\n            for m in metrics:\n                col = f"metrics.{m}"\n                val = run.get(col, None)\n                row[m] = round(val, 5) if hasattr(val, "__float__") or isinstance(val, (int, float)) else None\n            leaderboard.append(row)\n        \n        leaderboard.sort(key=lambda x: x.get("f1_weighted") or 0, reverse=True)\n        \n        return {\n            "experiment_name": experiment.name,\n            "experiment_id": experiment.experiment_id,\n            "total_runs": len(runs_df),\n            "best_by_metric": best_by_metric,\n            "leaderboard": leaderboard,\n            "metric_labels": metric_labels\n        }\n        \n    except Exception as e:\n        return {"error": str(e)}


@app.route("/api/mlflow-insights")\ndef api_mlflow_insights():\n    """API endpoint for MLflow experiment insights."""\n    insights = get_mlflow_insights()\n    from flask import jsonify\n    return jsonify(insights)\n\n\n@app.route('/')\ndef index():'''
        
        content = content.replace(marker, helper)
        print("[patch] Added get_mlflow_insights and /api/mlflow-insights route")
    
    app_path.write_text(content, encoding="utf-8")
    print("[patch] app.py updated successfully")


if __name__ == "__main__":
    main()
