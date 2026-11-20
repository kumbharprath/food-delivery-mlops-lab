"""Create synthetic teaching data. NOT real restaurant/customer data."""
from pathlib import Path
import random
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "food_delivery.csv"


def generate_dataset(rows: int = 600, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    records = []
    traffic_penalty = {"Low": 2, "Medium": 7, "High": 14}
    weather_penalty = {"Clear": 0, "Rainy": 5, "Stormy": 12}
    for _ in range(rows):
        distance = round(rng.uniform(0.8, 15.0), 2)
        traffic = rng.choices(["Low", "Medium", "High"], weights=[30, 45, 25])[0]
        weather = rng.choices(["Clear", "Rainy", "Stormy"], weights=[65, 28, 7])[0]
        prep = rng.randint(5, 25)
        experience = rng.randint(0, 8)
        duration = (8 + 2.6 * distance + traffic_penalty[traffic]
                    + weather_penalty[weather] + 0.65 * prep
                    - 0.7 * experience + rng.gauss(0, 2.0))
        records.append({
            "distance_km": distance,
            "traffic_level": traffic,
            "weather": weather,
            "restaurant_prep_min": prep,
            "courier_experience_years": experience,
            "delivery_time_min": round(max(5.0, duration), 1),
        })
    return pd.DataFrame.from_records(records)


def main():
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame = generate_dataset()
    frame.to_csv(DATA_PATH, index=False)
    print(f"Created {len(frame)} synthetic orders at {DATA_PATH}")
    print(frame.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
