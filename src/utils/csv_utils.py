import os
from typing import List

import pandas as pd

current_datetime = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
header = pd.DataFrame(
    [{"datetimestamp": "Results", "Power Usage (kW)": current_datetime}]
)


def save_updates_to_csv(file_name: str, power_updates: List[float]) -> None:
    data_dir = os.path.join(os.path.dirname(__file__), "../data")
    data_path = os.path.join(data_dir, f"{file_name}.csv")
    os.makedirs(data_dir, exist_ok=True)

    df = pd.DataFrame(power_updates)

    with open(data_path, "a") as f:
        if header is not None:
            header.to_csv(f, header=False, index=False)
        df.to_csv(f, mode="a", index=False)
