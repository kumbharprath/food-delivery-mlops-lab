import pandas as pd
from src.generate_data import generate_dataset
from src.train import train


def test_train_test_split_and_gate(tmp_path):
    data = tmp_path / "orders.csv"
    generate_dataset(rows=100).to_csv(data, index=False)
    info = train(data, tmp_path / "output", max_mae=100)
    assert info["training_rows"] == 80
    assert info["testing_rows"] == 20
    training = pd.read_csv(tmp_path / "output" / "train_rows.csv")
    testing = pd.read_csv(tmp_path / "output" / "test_rows.csv")
    assert len(training) == 80 and len(testing) == 20
    assert (tmp_path / "output" / "model.joblib").exists()
