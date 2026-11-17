# Cambridge Crime Trends — Part A (through notebook Cell 27)

This folder contains the runnable Python code for the notebook's extraction,
validation, and transformation stages, plus Mac setup instructions for the
PostgreSQL and Docker environment checks up to Cell 27.

**Scope boundary:** The notebook says “Complete upto this only” in Cell 27.
This project intentionally does not include the Docker Compose file that starts
at Cell 28, the PostgreSQL table/load code later in the notebook, Prefect flow
deployment, or Metabase.

## 1. Create and activate a virtual environment

````bash
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt```

## 2. Configure Socrata

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
````

Edit `.env` and set `SOCRATA_APP_TOKEN` to your own Socrata application token.
Do not commit `.env` to Git. The dataset is Cambridge Police Log,
dataset ID `3gki-wyrb`, on `data.cambridgema.gov`.

## 3. Run extraction, validation, and transformation

```bash
python run_pipeline.py
python -m streamlit run dashboard.py
```

The script prints the first rows at each stage and the row counts. It does not
load data into PostgreSQL because the notebook's actual loading implementation
is after the Cell 27 stopping point.

## 4. macOS equivalent of the PostgreSQL setup/check (Cells 16–20)

The notebook uses Linux commands (`apt-get`, `service`, and `sudo -u postgres`).
Do not run those commands on macOS.

Install Homebrew PostgreSQL:

```bash
brew install postgresql@16
brew services start postgresql@16
```

Create a local login role for the connection test. First, connect to the local
PostgreSQL server as your macOS account:

```bash
psql postgres
```

At the `postgres=#` prompt, run the following SQL. Replace the password with
your own value:

```sql
CREATE ROLE cpd_user WITH LOGIN PASSWORD 'replace_with_a_strong_local_password';
```

If the role already exists, use:

```sql
ALTER ROLE cpd_user WITH LOGIN PASSWORD 'replace_with_a_strong_local_password';
```

Exit psql with `\\q`. Set the same username and password in `.env`:

```env
POSTGRES_USER=cpd_user
POSTGRES_PASSWORD=replace_with_a_strong_local_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=postgres
```

Run the connection test:

```bash
python check_postgres.py
```

## 5. macOS equivalent of Docker setup/check (Cells 21–26)

Install Docker Desktop:

```bash
brew install --cask docker
open -a Docker
```

Wait until Docker Desktop reports that the engine is running, then verify:

```bash
docker --version
docker compose version
docker info
```

On macOS, Docker Desktop provides the Docker engine and the Compose plugin.
You do not need the Linux `dockerd` command or the notebook's manual
`docker-compose` binary download.

**Do not run `docker compose up` for this scope.** The Compose configuration
starts at Cell 28, after the notebook's explicit stopping point.

## Notes about validation

- The notebook says non-numeric IDs should be converted to missing values and
  removed during transformation. Therefore, `id` is not treated as a fatal
  missing field during validation.
- Required date/time, incident type, and location values fail validation if
  they are null or blank.
- Invalid timestamps fail validation with example values.
- Duplicate IDs keep the first row, matching the notebook. This does not decide
  whether the first row is the newest version; that policy can be improved later.

## Files

- `extract.py` — Socrata extraction task
- `validate.py` — schema and data-quality checks
- `transform.py` — deduplication, invalid-ID removal, date/time columns
- `run_pipeline.py` — runs the three ETL stages
- `check_postgres.py` — verifies a local PostgreSQL connection
