"""Clean incident records and create date/time analysis columns."""

import pandas as pd
from prefect import task


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the first row for each non-null incident ID."""
    return df.drop_duplicates(subset=["id"], keep="first").copy()


def remove_invalid_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove records whose IDs could not be converted to numbers."""
    return df.dropna(subset=["id"]).copy()


def split_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Create year, month, day, hour, minute, and second columns."""
    df = df.copy()
    df["date_time"] = pd.to_datetime(df["date_time"], errors="raise")

    df["year"] = df["date_time"].dt.year
    df["month"] = df["date_time"].dt.month
    df["day"] = df["date_time"].dt.day
    df["hour"] = df["date_time"].dt.hour
    df["minute"] = df["date_time"].dt.minute
    df["second"] = df["date_time"].dt.second

    return df


@task
def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the notebook's three transformation steps."""
    df = remove_duplicates(df)
    df = remove_invalid_rows(df)
    df = split_datetime(df)
    return df
