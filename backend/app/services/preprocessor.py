from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd

from app.schemas.models import ModelRegistryEntry
from app.core.exceptions import PreprocessingError

# Known target or non-feature metadata columns that must be ignored during inference
IGNORED_COLUMNS = {
    "fraud",
    "isFraud",
    "isFlaggedFraud",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "nameOrig",
    "nameDest"
}


def validate_and_preprocess_single(
    model_entry: ModelRegistryEntry,
    features: Dict[str, Any]
) -> Tuple[np.ndarray, List[float]]:
    """
    Validate and preprocess a single transaction payload.
    Returns:
        np_vector: 2D numpy array of shape (1, len(ordered_model_features))
        list_vector: Python list of preprocessed floats for serialization
    """
    # Convert single dict to 1-row DataFrame for unified processing
    df = pd.DataFrame([features])
    processed_2d = preprocess_dataframe(model_entry, df)
    row_vector = processed_2d[0].tolist()
    return processed_2d, row_vector


def preprocess_dataframe(
    model_entry: ModelRegistryEntry,
    df: pd.DataFrame
) -> np.ndarray:
    """
    Reproduces exact training-time preprocessing for a batch DataFrame:
    1. Validates presence of required raw features.
    2. Drops target / ignored columns safely.
    3. Handles categorical one-hot encoding for PaySim.
    4. Validates types and finite numerical values (no NaN, null, or inf).
    5. Arranges columns strictly in ordered_model_features sequence.
    """
    if df.empty:
        raise PreprocessingError("Input data contains zero rows.")

    df_clean = df.copy()

    # Drop target columns if user or CSV passed them
    for col in IGNORED_COLUMNS:
        if col in df_clean.columns:
            df_clean = df_clean.drop(columns=[col], errors="ignore")

    # Check for missing required raw features
    missing_raw = [
        col for col in model_entry.required_raw_features
        if col not in df_clean.columns
    ]
    if missing_raw:
        raise PreprocessingError(
            f"Missing required input features for {model_entry.dataset_id}: {missing_raw}"
        )

    # Dataset 1: Credit Card Fraud Detection
    if model_entry.dataset_id == "credit_card_dataset_1":
        ordered_cols = model_entry.ordered_model_features
        try:
            subset = df_clean[ordered_cols].astype(np.float64)
        except (ValueError, TypeError) as e:
            raise PreprocessingError(f"Non-numeric values found in Credit Card features: {str(e)}")

        if subset.isnull().any().any():
            raise PreprocessingError("Input features contain NaN or null values.")
        if np.isinf(subset.to_numpy()).any():
            raise PreprocessingError("Input features contain infinite values.")

        return subset.to_numpy(dtype=np.float32)

    # Dataset 2: PaySim Synthetic Financial Transactions
    elif model_entry.dataset_id == "paysim_dataset_2":
        # Validate 'type' column
        valid_types = {"CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"}
        raw_types = df_clean["type"].astype(str).str.strip()
        invalid_types = set(raw_types) - valid_types
        if invalid_types:
            raise PreprocessingError(
                f"Invalid transaction type(s) '{list(invalid_types)}'. Allowed types: {sorted(list(valid_types))}"
            )

        # Validate numeric columns
        for num_col in ["step", "amount"]:
            try:
                df_clean[num_col] = pd.to_numeric(df_clean[num_col])
            except (ValueError, TypeError) as e:
                raise PreprocessingError(f"Invalid numeric value in column '{num_col}': {str(e)}")
            if df_clean[num_col].isnull().any():
                raise PreprocessingError(f"Column '{num_col}' contains NaN or null values.")
            if np.isinf(df_clean[num_col].to_numpy()).any():
                raise PreprocessingError(f"Column '{num_col}' contains infinite values.")

        # Reproduce exact training-time pd.get_dummies(X, columns=['type'], prefix='type', dtype=int)
        type_dummies = pd.DataFrame(0, index=df_clean.index, columns=[
            "type_CASH_IN", "type_CASH_OUT", "type_DEBIT", "type_PAYMENT", "type_TRANSFER"
        ])
        for t in valid_types:
            dummy_col = f"type_{t}"
            type_dummies[dummy_col] = (raw_types == t).astype(int)

        feature_df = pd.concat([
            df_clean[["step", "amount"]].astype(np.float32),
            type_dummies.astype(np.float32)
        ], axis=1)

        ordered_cols = model_entry.ordered_model_features
        try:
            final_df = feature_df[ordered_cols]
        except KeyError as e:
            raise PreprocessingError(f"Failed to generate required feature column: {str(e)}")

        return final_df.to_numpy(dtype=np.float32)

    else:
        raise PreprocessingError(f"Unsupported dataset ID: {model_entry.dataset_id}")
