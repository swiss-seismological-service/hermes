from datetime import datetime

import numpy as np
import pandas as pd
from hydws.parser import BoreholeHydraulics, SectionHydraulics


class InjectionPlanBuilder:
    def __init__(self, template: dict, data: dict | None = None):
        self.template = template
        self.hydraulics = None

        if data is not None:
            data = next(d for d in data if d['name']
                        == template['borehole_name'])
            self.observed_hydraulics = BoreholeHydraulics(data)
            self.hydraulics = self.observed_hydraulics.nloc[
                template['section_name']].hydraulics

        self.template_type = template['type']
        valid_types = ['fixed', 'constant', 'multiply']
        if self.template_type not in valid_types:
            raise ValueError(f"Invalid template type: {self.template_type}, "
                             f"must be one of {valid_types}")

    def build(self, start: datetime, end: datetime) -> dict:
        if self.template_type == 'fixed':
            hydraulics = build_fixed(
                start, end, self.template['resolution'],
                self.template['config'], self.hydraulics)
        elif self.template_type == 'constant':
            hydraulics = build_constant(
                start, end, self.template['resolution'],
                self.template['config'], self.hydraulics)
        elif self.template_type == 'multiply':
            hydraulics = build_multiply(
                start, end, self.template['resolution'],
                self.template['config'], self.hydraulics)

        ip = BoreholeHydraulics()
        ip.metadata = self.observed_hydraulics.metadata
        section = SectionHydraulics()
        section.metadata = self.observed_hydraulics.nloc[
            self.template['section_name']].metadata
        section.hydraulics = hydraulics
        ip[section.metadata['publicid']] = section

        return ip.to_json()


def build_fixed(start: datetime,
                end: datetime,
                resolution: int,
                config: dict,
                hydraulics: pd.DataFrame | None) -> dict:
    # Create a time range based on start, end, and resolution
    time_index = pd.date_range(start=start, end=end, freq=f"{resolution}s")

    # Convert nested JSON into a DataFrame
    plan_df = pd.json_normalize(config.get("plan", []), sep="_")
    plan_df["datetime_value"] = pd.to_datetime(plan_df["datetime_value"])
    plan_df = plan_df.set_index("datetime_value")

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

    # Ensure no remaining NaN values (fill with the last known value)
    result_df = result_df.bfill()

    # Trim the DataFrame to the specified start and end times
    result_df = result_df[start:end]

    return result_df.rename(columns=lambda col:
                            col.removesuffix('_value'))


def build_constant(start: datetime,
                   end: datetime,
                   resolution: int,
                   config: dict,
                   hydraulics: pd.DataFrame | None) -> dict:
    # Create a time range based on start, end, and resolution
    time_index = pd.date_range(start=start, end=end, freq=f"{resolution}s")

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
                   resolution: int,
                   config: dict,
                   hydraulics: pd.DataFrame | None) -> dict:

    if hydraulics is None:
        raise ValueError("Hydraulics data must be provided "
                         "for multiply injection plans.")

    # Create a time range based on start, end, and resolution
    time_index = pd.date_range(start=start, end=end, freq=f"{resolution}s")

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
