"""Extract Cambridge Police Department incident data from Socrata."""

import os

import pandas as pd
from dotenv import load_dotenv
from prefect import task
from sodapy import Socrata

DOMAIN = "data.cambridgema.gov"
DATASET_ID = "3gki-wyrb"


@task(retries=3, retry_delay_seconds=[10, 10, 10])
def extract_data() -> pd.DataFrame:
    """Fetch all available incident records and return them as a DataFrame."""
    load_dotenv()

    app_token = os.getenv("SOCRATA_APP_TOKEN")
    if not app_token:
        raise RuntimeError("SOCRATA_APP_TOKEN is missing. Add it to your .env file.")

    client = Socrata(DOMAIN, app_token, timeout=30)

    try:
        records = client.get_all(DATASET_ID, order=":id ASC")
        df = pd.DataFrame.from_records(records)
    finally:
        client.close()

    if df.empty:
        raise ValueError("The Socrata API returned no records.")

    return df
