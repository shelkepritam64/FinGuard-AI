import os
from pathlib import Path
from typing import Dict, Any, Tuple
import joblib
import numpy as np
import pandas as pd

# Suppress TF verbose logging
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
import tensorflow as tf

from app.config import settings
from app.schemas.models import ModelRegistryEntry
from app.core.exceptions import ArtifactMissingError, InferenceError


class InferenceEngine:
    """Manages cached model and scaler loading and executes real batch/single inference."""

    def __init__(self, models_base_dir: Path = None):
        self.models_dir = models_base_dir or settings.resolved_models_dir
        self._model_cache: Dict[str, Any] = {}
        self._scaler_cache: Dict[str, Any] = {}

    def _get_dataset_dir(self, dataset_id: str) -> Path:
        return self.models_dir / dataset_id

    def load_scaler(self, model_entry: ModelRegistryEntry):
        """Load and cache the required scaler artifact with joblib."""
        if not model_entry.scaler_artifact_filename:
            return None

        scaler_name = model_entry.scaler_artifact_filename
        cache_key = f"{model_entry.dataset_id}:{scaler_name}"

        if cache_key in self._scaler_cache:
            return self._scaler_cache[cache_key]

        scaler_path = self._get_dataset_dir(model_entry.dataset_id) / scaler_name
        if not scaler_path.exists():
            raise ArtifactMissingError(f"Scaler file '{scaler_name}' does not exist on disk.")

        try:
            scaler = joblib.load(scaler_path)
            self._scaler_cache[cache_key] = scaler
            return scaler
        except Exception as e:
            raise InferenceError(f"Failed to load scaler '{scaler_name}': {str(e)}")

    def load_model(self, model_entry: ModelRegistryEntry):
        """Load and cache model artifact using appropriate deserializer (joblib for XGBoost, Keras for DL)."""
        cache_key = model_entry.model_id
        if cache_key in self._model_cache:
            return self._model_cache[cache_key]

        model_path = self._get_dataset_dir(model_entry.dataset_id) / model_entry.model_artifact_filename
        if not model_path.exists():
            raise ArtifactMissingError(
                f"Model artifact '{model_entry.model_artifact_filename}' not found on disk."
            )

        try:
            if model_entry.model_family == "XGBoost":
                model = joblib.load(model_path)
            elif model_entry.model_family in ["MLP", "Autoencoder", "LSTM"]:
                model = tf.keras.models.load_model(model_path, compile=False)
            else:
                raise InferenceError(f"Unsupported model family: {model_entry.model_family}")

            self._model_cache[cache_key] = model
            return model
        except Exception as e:
            raise InferenceError(f"Failed to load model '{model_entry.model_id}': {str(e)}")

    def predict(
        self,
        model_entry: ModelRegistryEntry,
        X_matrix: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Execute inference on preprocessed 2D numpy matrix X_matrix of shape (N, 7).
        Returns:
            scores: 1D array of float scores (probabilities or MSE reconstruction errors)
            thresholds: 1D array of float thresholds applied
            risk_labels: 1D array of strings ('High Risk' or 'Low Risk')
            explanations: 1D array of decision rule descriptions
        """
        if model_entry.threshold is None:
            raise InferenceError(
                f"Model '{model_entry.model_id}' does not have a configured decision threshold."
            )

        threshold = float(model_entry.threshold)
        model = self.load_model(model_entry)
        scaler = self.load_scaler(model_entry)

        # Apply scaler if model requires one (MLP and Autoencoder)
        if scaler is not None:
            try:
                if hasattr(scaler, "feature_names_in_"):
                    df_for_scaler = pd.DataFrame(X_matrix, columns=model_entry.ordered_model_features)
                    X_transformed = scaler.transform(df_for_scaler)
                else:
                    X_transformed = scaler.transform(X_matrix)
            except Exception as e:
                raise InferenceError(f"Scaler transformation failed: {str(e)}")
        else:
            X_transformed = X_matrix

        # Inference per model family
        if model_entry.model_family == "XGBoost":
            try:
                # predict_proba returns [N, 2], column 1 is fraud probability
                probabilities = model.predict_proba(X_transformed)[:, 1]
                scores = probabilities.astype(float)
            except Exception as e:
                raise InferenceError(f"XGBoost prediction failed: {str(e)}")

        elif model_entry.model_family == "MLP":
            try:
                raw_preds = model.predict(X_transformed, verbose=0)
                scores = raw_preds.ravel().astype(float)
            except Exception as e:
                raise InferenceError(f"MLP prediction failed: {str(e)}")

        elif model_entry.model_family == "Autoencoder":
            try:
                reconstructed = model.predict(X_transformed, verbose=0)
                # Compute Mean Squared Error per row across the 7 feature dimensions
                mse_errors = np.mean(np.square(X_transformed - reconstructed), axis=1)
                scores = mse_errors.astype(float)
            except Exception as e:
                raise InferenceError(f"Autoencoder anomaly scoring failed: {str(e)}")

        else:
            raise InferenceError(f"Inference not implemented for model family {model_entry.model_family}")

        # Vectorized threshold evaluation
        is_high_risk = scores >= threshold
        risk_labels = np.where(is_high_risk, "High Risk", "Low Risk")
        thresholds = np.full_like(scores, threshold)

        # Explanations
        explanations = []
        for score, high in zip(scores, is_high_risk):
            if model_entry.score_type == "fraud_probability":
                comp = "greater than or equal to" if high else "below"
                explanations.append(
                    f"Predicted fraud probability of {score:.4f} is {comp} the decision threshold of {threshold:.4f}."
                )
            else:
                comp = "greater than or equal to" if high else "below"
                explanations.append(
                    f"Reconstruction anomaly error of {score:.6f} is {comp} the decision threshold of {threshold:.6f}."
                )

        return scores, thresholds, risk_labels, np.array(explanations)


inference_engine = InferenceEngine()
