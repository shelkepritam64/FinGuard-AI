import pytest
import numpy as np
import pandas as pd

from app.services.registry import registry_service
from app.services.preprocessor import (
    validate_and_preprocess_single,
    preprocess_dataframe
)
from app.core.exceptions import PreprocessingError


def test_credit_card_valid_preprocessing():
    """Verify Credit Card features are ordered and converted to float array."""
    model_entry = registry_service.get_model("credit_1_xgboost")
    raw_input = {
        "distance_from_home": 57.8,
        "distance_from_last_transaction": 0.31,
        "ratio_to_median_purchase_price": 1.94,
        "repeat_retailer": 1.0,
        "used_chip": 1.0,
        "used_pin_number": 0.0,
        "online_order": 0.0
    }
    np_matrix, vec = validate_and_preprocess_single(model_entry, raw_input)
    assert np_matrix.shape == (1, 7)
    assert len(vec) == 7
    assert np_matrix[0, 0] == pytest.approx(57.8, rel=1e-2)
    assert np_matrix[0, 3] == 1.0


def test_credit_card_missing_feature():
    """Verify missing required column raises PreprocessingError."""
    model_entry = registry_service.get_model("credit_1_xgboost")
    incomplete_input = {
        "distance_from_home": 10.0
        # missing other 6 columns
    }
    with pytest.raises(PreprocessingError) as exc:
        validate_and_preprocess_single(model_entry, incomplete_input)
    assert "Missing required input features" in str(exc.value)


def test_credit_card_nan_inf_rejected():
    """Verify NaN and Inf values are rejected."""
    model_entry = registry_service.get_model("credit_1_mlp")
    bad_input = {
        "distance_from_home": float("nan"),
        "distance_from_last_transaction": 0.31,
        "ratio_to_median_purchase_price": 1.94,
        "repeat_retailer": 1.0,
        "used_chip": 1.0,
        "used_pin_number": 0.0,
        "online_order": 0.0
    }
    with pytest.raises(PreprocessingError) as exc:
        validate_and_preprocess_single(model_entry, bad_input)
    assert "NaN or null" in str(exc.value)


def test_credit_card_target_column_ignored():
    """Verify 'fraud' target column is never required and dropped if present."""
    model_entry = registry_service.get_model("credit_1_autoencoder")
    input_with_target = {
        "distance_from_home": 12.5,
        "distance_from_last_transaction": 1.2,
        "ratio_to_median_purchase_price": 0.8,
        "repeat_retailer": 1.0,
        "used_chip": 0.0,
        "used_pin_number": 1.0,
        "online_order": 1.0,
        "fraud": 1  # Should be safely ignored
    }
    np_matrix, _ = validate_and_preprocess_single(model_entry, input_with_target)
    assert np_matrix.shape == (1, 7)


def test_paysim_exact_dummy_encoding_and_ordering():
    """Verify PaySim transaction type is one-hot encoded into exact 5 dummies in order."""
    model_entry = registry_service.get_model("paysim_2_xgboost")
    raw_input = {
        "step": 1,
        "amount": 9839.64,
        "type": "PAYMENT"
    }
    np_matrix, vec = validate_and_preprocess_single(model_entry, raw_input)
    assert np_matrix.shape == (1, 7)
    # Order: ["step", "amount", "type_CASH_IN", "type_CASH_OUT", "type_DEBIT", "type_PAYMENT", "type_TRANSFER"]
    assert vec[0] == 1.0       # step
    assert vec[1] == pytest.approx(9839.64, rel=1e-2)  # amount
    assert vec[2] == 0.0       # type_CASH_IN
    assert vec[3] == 0.0       # type_CASH_OUT
    assert vec[4] == 0.0       # type_DEBIT
    assert vec[5] == 1.0       # type_PAYMENT
    assert vec[6] == 0.0       # type_TRANSFER


def test_paysim_invalid_type_rejected():
    """Verify invalid transaction type string raises PreprocessingError."""
    model_entry = registry_service.get_model("paysim_2_mlp")
    bad_type_input = {
        "step": 1,
        "amount": 100.0,
        "type": "CRYPTO_TRANSFER"  # Invalid type
    }
    with pytest.raises(PreprocessingError) as exc:
        validate_and_preprocess_single(model_entry, bad_type_input)
    assert "Invalid transaction type" in str(exc.value)


def test_paysim_target_columns_ignored():
    """Verify 'isFraud' and 'isFlaggedFraud' are dropped and never required."""
    model_entry = registry_service.get_model("paysim_2_autoencoder")
    raw_input = {
        "step": 10,
        "amount": 50000.0,
        "type": "TRANSFER",
        "isFraud": 1,
        "isFlaggedFraud": 1,
        "nameOrig": "C12345",
        "oldbalanceOrg": 50000.0
    }
    np_matrix, vec = validate_and_preprocess_single(model_entry, raw_input)
    assert np_matrix.shape == (1, 7)
    # TRANSFER should have vec[6] == 1.0
    assert vec[6] == 1.0
