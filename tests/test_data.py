import pytest
from src.generate_data import generate_dataset
from src.train import validate_frame


def test_generated_dataset_has_required_fields():
    df = generate_dataset(rows=100)
    validate_frame(df)
    assert len(df) == 100
    assert df["delivery_time_min"].gt(0).all()


def test_missing_feature_is_rejected():
    df = generate_dataset(rows=100).drop(columns=["distance_km"])
    with pytest.raises(ValueError, match="Missing columns"):
        validate_frame(df)


def test_negative_distance_is_rejected():
    df = generate_dataset(rows=100)
    df.loc[0, "distance_km"] = -3
    with pytest.raises(ValueError, match="Distance"):
        validate_frame(df)
