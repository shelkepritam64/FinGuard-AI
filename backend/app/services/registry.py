import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from app.config import settings
from app.schemas.models import ModelRegistryEntry, EvaluationMetrics
from app.core.exceptions import ModelNotFoundError, ModelUnavailableError


def _load_metrics_file(metrics_path: Path) -> Optional[EvaluationMetrics]:
    """Safely load and normalize test metrics from artifact JSON."""
    if not metrics_path.exists():
        return None
    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        
        # Normalize key variations: f1 vs f1_score, threshold vs decision_threshold
        f1 = raw.get("f1_score") if "f1_score" in raw else raw.get("f1")
        threshold = raw.get("decision_threshold") if "decision_threshold" in raw else raw.get("threshold")
        
        extra = {k: v for k, v in raw.items() if k not in [
            "accuracy", "precision", "recall", "f1_score", "f1",
            "roc_auc", "pr_auc", "decision_threshold", "threshold",
            "confusion_matrix", "dataset", "dataset_number", "model"
        ]}

        return EvaluationMetrics(
            accuracy=raw.get("accuracy"),
            precision=raw.get("precision"),
            recall=raw.get("recall"),
            f1_score=f1,
            roc_auc=raw.get("roc_auc"),
            pr_auc=raw.get("pr_auc"),
            decision_threshold=threshold,
            confusion_matrix=raw.get("confusion_matrix"),
            extra=extra or None
        )
    except Exception:
        return None


class ModelRegistryService:
    """Centralized service for managing model metadata, artifacts, and evaluation metrics."""

    def __init__(self, models_base_dir: Optional[Path] = None):
        self.models_dir = models_base_dir or settings.resolved_models_dir
        self._registry: Dict[str, ModelRegistryEntry] = {}
        self._initialize_registry()

    def _initialize_registry(self) -> None:
        """Define all registered model definitions and inspect artifact availability on disk."""
        
        # 1. Dataset 1: Credit Card Fraud Detection Models
        cc_dir = self.models_dir / "credit_card_dataset_1"
        cc_raw_features = [
            "distance_from_home",
            "distance_from_last_transaction",
            "ratio_to_median_purchase_price",
            "repeat_retailer",
            "used_chip",
            "used_pin_number",
            "online_order"
        ]

        # 1a. Credit Card XGBoost
        xgb_1_file = "xgboost_model1_1.pkl"  # Exact filename discovered during audit
        xgb_1_path = cc_dir / xgb_1_file
        xgb_1_avail = xgb_1_path.exists()
        self._registry["credit_1_xgboost"] = ModelRegistryEntry(
            model_id="credit_1_xgboost",
            dataset_id="credit_card_dataset_1",
            model_name="Credit Card XGBoost Classifier",
            model_family="XGBoost",
            model_artifact_filename=xgb_1_file,
            scaler_artifact_filename=None,
            required_raw_features=cc_raw_features,
            ordered_model_features=cc_raw_features,
            categorical_encoding_rules={},
            target_column="fraud",
            threshold=0.47209590673446655,
            score_type="fraud_probability",
            prediction_rule="Flag for review if fraud probability >= 0.4720959",
            is_available=xgb_1_avail,
            status="available" if xgb_1_avail else "unavailable",
            unavailable_reason=None if xgb_1_avail else f"Artifact {xgb_1_file} not found on disk",
            metrics_filename="test_metrics_xgboost_1.json",
            evaluation_metrics=_load_metrics_file(cc_dir / "test_metrics_xgboost_1.json")
        )

        # 1b. Credit Card MLP
        mlp_1_file = "mlp_model_1.keras"
        scaler_1_file = "scaler_neural_networks_1.pkl"
        mlp_1_path = cc_dir / mlp_1_file
        scaler_1_path = cc_dir / scaler_1_file
        mlp_1_avail = mlp_1_path.exists() and scaler_1_path.exists()
        self._registry["credit_1_mlp"] = ModelRegistryEntry(
            model_id="credit_1_mlp",
            dataset_id="credit_card_dataset_1",
            model_name="Credit Card Multilayer Perceptron (MLP)",
            model_family="MLP",
            model_artifact_filename=mlp_1_file,
            scaler_artifact_filename=scaler_1_file,
            required_raw_features=cc_raw_features,
            ordered_model_features=cc_raw_features,
            categorical_encoding_rules={},
            target_column="fraud",
            threshold=0.9056363701820374,
            score_type="fraud_probability",
            prediction_rule="Flag for review if fraud probability >= 0.9056364",
            is_available=mlp_1_avail,
            status="available" if mlp_1_avail else "unavailable",
            unavailable_reason=None if mlp_1_avail else "Model or scaler artifact not found on disk",
            metrics_filename="test_metrics_mlp_1.json",
            evaluation_metrics=_load_metrics_file(cc_dir / "test_metrics_mlp_1.json")
        )

        # 1c. Credit Card Autoencoder
        ae_1_file = "autoencoder_model_1.keras"
        ae_scaler_1_file = "scaler_autoencoder_1.pkl"
        ae_1_path = cc_dir / ae_1_file
        ae_scaler_1_path = cc_dir / ae_scaler_1_file
        ae_1_avail = ae_1_path.exists() and ae_scaler_1_path.exists()
        self._registry["credit_1_autoencoder"] = ModelRegistryEntry(
            model_id="credit_1_autoencoder",
            dataset_id="credit_card_dataset_1",
            model_name="Credit Card Autoencoder Anomaly Detector",
            model_family="Autoencoder",
            model_artifact_filename=ae_1_file,
            scaler_artifact_filename=ae_scaler_1_file,
            required_raw_features=cc_raw_features,
            ordered_model_features=cc_raw_features,
            categorical_encoding_rules={},
            target_column="fraud",
            threshold=0.006319875903427601,
            score_type="mean_squared_reconstruction_error",
            prediction_rule="Flag for review if mean squared reconstruction error >= 0.0063199",
            is_available=ae_1_avail,
            status="available" if ae_1_avail else "unavailable",
            unavailable_reason=None if ae_1_avail else "Autoencoder or scaler artifact not found on disk",
            metrics_filename="test_metrics_autoencoder_1.json",
            evaluation_metrics=_load_metrics_file(cc_dir / "test_metrics_autoencoder_1.json")
        )

        # 1d. Credit Card LSTM (Experimental, marked unavailable for primary screening)
        self._registry["credit_1_lstm"] = ModelRegistryEntry(
            model_id="credit_1_lstm",
            dataset_id="credit_card_dataset_1",
            model_name="Credit Card LSTM Feature Sequence (Experimental)",
            model_family="LSTM",
            model_artifact_filename="lstm_model_1.keras",
            scaler_artifact_filename="scaler_neural_networks_1.pkl",
            required_raw_features=cc_raw_features,
            ordered_model_features=cc_raw_features,
            categorical_encoding_rules={},
            target_column="fraud",
            threshold=0.5917874574661255,
            score_type="fraud_probability",
            prediction_rule="Experimental model",
            is_available=False,
            status="unavailable",
            unavailable_reason="Experimental non-temporal feature-sequence model; excluded from primary production screening per audit findings.",
            metrics_filename="test_metrics_lstm_1.json",
            evaluation_metrics=_load_metrics_file(cc_dir / "test_metrics_lstm_1.json")
        )

        # 2. Dataset 2: PaySim Synthetic Financial Transactions Models
        ps_dir = self.models_dir / "paysim_dataset_2"
        ps_raw_features = ["step", "amount", "type"]
        ps_ordered_features = [
            "step",
            "amount",
            "type_CASH_IN",
            "type_CASH_OUT",
            "type_DEBIT",
            "type_PAYMENT",
            "type_TRANSFER"
        ]
        ps_encoding_rules = {
            "type": {
                "categories": ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"],
                "prefix": "type_"
            }
        }

        # 2a. PaySim XGBoost
        xgb_2_file = "xgboost_model_2.pkl"
        xgb_2_path = ps_dir / xgb_2_file
        xgb_2_avail = xgb_2_path.exists()
        self._registry["paysim_2_xgboost"] = ModelRegistryEntry(
            model_id="paysim_2_xgboost",
            dataset_id="paysim_dataset_2",
            model_name="PaySim Mobile Money XGBoost Classifier",
            model_family="XGBoost",
            model_artifact_filename=xgb_2_file,
            scaler_artifact_filename=None,
            required_raw_features=ps_raw_features,
            ordered_model_features=ps_ordered_features,
            categorical_encoding_rules=ps_encoding_rules,
            target_column="isFraud",
            threshold=0.5248706936836243,
            score_type="fraud_probability",
            prediction_rule="Flag for review if fraud probability >= 0.5248707",
            is_available=xgb_2_avail,
            status="available" if xgb_2_avail else "unavailable",
            unavailable_reason=None if xgb_2_avail else f"Artifact {xgb_2_file} not found on disk",
            metrics_filename="test_metrics_xgboost_2.json",
            evaluation_metrics=_load_metrics_file(ps_dir / "test_metrics_xgboost_2.json")
        )

        # 2b. PaySim MLP
        mlp_2_file = "mlp_model_2.keras"
        scaler_2_file = "scaler_neural_networks_2.pkl"
        mlp_2_path = ps_dir / mlp_2_file
        scaler_2_path = ps_dir / scaler_2_file
        mlp_2_avail = mlp_2_path.exists() and scaler_2_path.exists()
        self._registry["paysim_2_mlp"] = ModelRegistryEntry(
            model_id="paysim_2_mlp",
            dataset_id="paysim_dataset_2",
            model_name="PaySim Mobile Money Multilayer Perceptron (MLP)",
            model_family="MLP",
            model_artifact_filename=mlp_2_file,
            scaler_artifact_filename=scaler_2_file,
            required_raw_features=ps_raw_features,
            ordered_model_features=ps_ordered_features,
            categorical_encoding_rules=ps_encoding_rules,
            target_column="isFraud",
            threshold=0.9925500154495239,
            score_type="fraud_probability",
            prediction_rule="Flag for review if fraud probability >= 0.9925500",
            is_available=mlp_2_avail,
            status="available" if mlp_2_avail else "unavailable",
            unavailable_reason=None if mlp_2_avail else "Model or scaler artifact not found on disk",
            metrics_filename="test_metrics_mlp_2.json",
            evaluation_metrics=_load_metrics_file(ps_dir / "test_metrics_mlp_2.json")
        )

        # 2c. PaySim Autoencoder
        ae_2_file = "autoencoder_model_2.keras"
        ae_scaler_2_file = "scaler_autoencoder_2.pkl"
        ae_2_path = ps_dir / ae_2_file
        ae_scaler_2_path = ps_dir / ae_scaler_2_file
        ae_2_avail = ae_2_path.exists() and ae_scaler_2_path.exists()
        self._registry["paysim_2_autoencoder"] = ModelRegistryEntry(
            model_id="paysim_2_autoencoder",
            dataset_id="paysim_dataset_2",
            model_name="PaySim Mobile Money Autoencoder Anomaly Detector",
            model_family="Autoencoder",
            model_artifact_filename=ae_2_file,
            scaler_artifact_filename=ae_scaler_2_file,
            required_raw_features=ps_raw_features,
            ordered_model_features=ps_ordered_features,
            categorical_encoding_rules=ps_encoding_rules,
            target_column="isFraud",
            threshold=0.0790452710390086,
            score_type="mean_squared_reconstruction_error",
            prediction_rule="Flag for review if mean squared reconstruction error >= 0.0790453",
            is_available=ae_2_avail,
            status="available" if ae_2_avail else "unavailable",
            unavailable_reason=None if ae_2_avail else "Autoencoder or scaler artifact not found on disk",
            metrics_filename="test_metrics_autoencoder_2.json",
            evaluation_metrics=_load_metrics_file(ps_dir / "test_metrics_autoencoder_2.json")
        )

        # 2d. PaySim LSTM (Not trained in experimentation)
        self._registry["paysim_2_lstm"] = ModelRegistryEntry(
            model_id="paysim_2_lstm",
            dataset_id="paysim_dataset_2",
            model_name="PaySim Mobile Money LSTM (Not Trained)",
            model_family="LSTM",
            model_artifact_filename="lstm_model_2.keras",
            scaler_artifact_filename=None,
            required_raw_features=ps_raw_features,
            ordered_model_features=ps_ordered_features,
            categorical_encoding_rules=ps_encoding_rules,
            target_column="isFraud",
            threshold=None,
            score_type="fraud_probability",
            prediction_rule="Unavailable",
            is_available=False,
            status="unavailable",
            unavailable_reason="Model was not trained during experimentation; origin-account grouping did not provide suitable sequence histories.",
            metrics_filename=None,
            evaluation_metrics=None
        )

    def list_models(self, dataset_id: Optional[str] = None) -> List[ModelRegistryEntry]:
        """Return all registered model entries, optionally filtered by dataset."""
        models = list(self._registry.values())
        if dataset_id:
            models = [m for m in models if m.dataset_id == dataset_id]
        return models

    def get_model(self, model_id: str) -> ModelRegistryEntry:
        """Fetch a specific model entry by ID."""
        if model_id not in self._registry:
            raise ModelNotFoundError(f"Model ID '{model_id}' is not registered.")
        return self._registry[model_id]

    def get_verified_model(self, model_id: str) -> ModelRegistryEntry:
        """Fetch model entry and ensure it is marked available for inference."""
        model = self.get_model(model_id)
        if not model.is_available:
            reason = model.unavailable_reason or "Model is not marked available for inference."
            raise ModelUnavailableError(f"Model '{model_id}' is unavailable: {reason}")
        return model

    def get_all_metrics(self) -> List[Dict[str, Any]]:
        """Return recorded evaluation test metrics for all models having evaluation files."""
        records = []
        for model in self._registry.values():
            if model.evaluation_metrics:
                records.append({
                    "model_id": model.model_id,
                    "model_name": model.model_name,
                    "dataset_id": model.dataset_id,
                    "model_family": model.model_family,
                    "metrics_file": model.metrics_filename,
                    "metrics": model.evaluation_metrics.model_dump()
                })
        return records


registry_service = ModelRegistryService()
