from datetime import datetime

import numpy as np
import pandas as pd


class InjectionPlanBuilder:
    def __init__(self, template: dict, data: dict | None = None):
        self.template = template

        self.data = data

    def build(self, start: datetime, end: datetime) -> dict:
        pass


def build_fixed(start: datetime,
                end: datetime,
                interval: int,
                config: dict,
                hydraulics: pd.DataFrame) -> dict:
    # Create a time range based on start, end, and interval
    time_index = pd.date_range(start=start, end=end, freq=f"{interval}s")

    # Convert nested JSON into a DataFrame
    plan_df = pd.json_normalize(config.get("plan", []), sep="_")
    # Rename columns to match expected format
    plan_df["datetime_value"] = pd.to_datetime(plan_df["datetime_value"])
    plan_df = plan_df.set_index("datetime_value")

    # # Reindex the plan_df to match the full time range
    result_df = pd.DataFrame(index=time_index)
    result_df = result_df.join(plan_df, how="outer")

    # Handle interpolation
    interpolation = config.get("interpolation", "none")
    if interpolation == "none":
        result_df = result_df.ffill()
    elif interpolation == "linear":
        # Interpolate linearly between values for numeric columns
        for column in result_df.columns:
            if result_df[column].dtype in [np.float64, np.int64]:
                result_df[column] = result_df[column].interpolate(
                    method="time")
    else:
        raise ValueError(
            "Invalid interpolation type. Must be 'none' or 'linear'.")

    # # Ensure no remaining NaN values (fill with the last known value)
    result_df = result_df.bfill()

    return result_df.rename(columns=lambda col:
                            col.removesuffix('_value'))


def build_constant(start: datetime,
                   end: datetime,
                   interval: int,
                   config: dict,
                   hydraulics: pd.DataFrame) -> dict:
    # Create a time range based on start, end, and interval
    time_index = pd.date_range(start=start, end=end, freq=f"{interval}s")

    # Convert nested JSON into a DataFrame
    plan_df = pd.json_normalize(config.get("plan", []), sep="_")
    row = plan_df.iloc[0]

    # Create a DataFrame with the same index as the time range
    result_df = pd.DataFrame([row.values] * len(time_index),
                             columns=plan_df.columns, index=time_index)

    return result_df.rename(columns=lambda col:
                            col.removesuffix('_value'))


def build_multiply(start: datetime,
                   end: datetime,
                   interval: int,
                   config: dict,
                   hydraulics: pd.DataFrame) -> dict:
    # Create a time range based on start, end, and interval
    time_index = pd.date_range(start=start, end=end, freq=f"{interval}s")

    # Convert nested JSON into a DataFrame
    plan_df = pd.json_normalize(config.get("plan", []), sep="_")
    row = plan_df.iloc[0]

    # Create a DataFrame with the same index as the time range
    result_df = pd.DataFrame([row.values] * len(time_index),
                             columns=plan_df.columns, index=time_index)
    result_df = result_df.rename(columns=lambda col:
                                 col.removesuffix('_value'))

    lookback = config.get("lookback_window", 1)
    method = config.get("mode", "mean")

    if method == "mean":
        lb_val = hydraulics.iloc[-lookback:].mean(skipna=True).fillna(0)
    elif method == "ewma":
        lb_val = hydraulics.ewm(
            span=lookback, ignore_na=True).mean().iloc[-1].fillna(0)

    result_df = result_df * \
        lb_val[lb_val.index.intersection(result_df.columns)]

    result_df.fillna(0, inplace=True)

    return result_df
