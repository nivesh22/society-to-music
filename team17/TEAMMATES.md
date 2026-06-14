# MSBA 405 — Society to Music: Team Guide

Hi everyone! Follow this guide **top to bottom** in order. Everything is numbered so you always know what to do next. Reach out on WhatsApp if anything is confusing — don't spend more than 30 minutes stuck.

---

## Who Does What

| Name            | File to edit                                                          | Node                     |
|-----------------|-----------------------------------------------------------------------|--------------------------|
| **Shivathmika** | `src/society_to_music/pipelines/process/clean_gdelt.py`             | `clean_gdelt`            |
| **Bhavika**     | `src/society_to_music/pipelines/process/clean_spotify.py`           | `clean_spotify`          |
| **Nisha**       | `src/society_to_music/pipelines/process/score_lyrics_emotions.py`   | `score_lyrics_emotions`  |
| **Sai**         | `src/society_to_music/pipelines/curate/` (all three files)          | `validate_and_load_*`    |
| **Nivesh**      | Everything else — do not touch these files                           | —                        |

**Only edit your own file. Do not touch anyone else's.**

---

## How the Pipeline Works

```
LOCAL (your laptop)                     GCP / PRODUCTION
──────────────────────────────────      ────────────────────────────────────────
CSV files in data/01_raw/               GCS bucket /raw/ (charts, lyrics, gdelt)
        │                                       │
        ▼                                       ▼
  [process pipeline]                      [process pipeline]
  clean_gdelt                             clean_gdelt
  clean_spotify              ══════►      clean_spotify
  score_lyrics_emotions                   score_lyrics_emotions
        │                                       │
  Parquet in data/02_intermediate/        GCS bucket /processed/
        │                                       │
        ▼                                       ▼
  [curate pipeline]                       [curate pipeline]
  validate_and_load_*        ══════►      validate_and_load_*
        │                                       │
  DuckDB (data/local.db)                  Snowflake CURATED schema
```

The **code is identical** in both environments. What changes is only the data source and destination — Kedro swaps those automatically based on the environment. You never need to change code to run locally vs on GCP.

### Who owns which step

| Pipeline | Node                     | Owner       | Input                                  | Output                  |
|----------|--------------------------|-------------|----------------------------------------|-------------------------|
| process  | clean_gdelt              | Shivathmika | raw_gdelt                              | daily_news_sentiment    |
| process  | clean_spotify            | Bhavika     | raw_spotify_charts, raw_audio_features | daily_music_features    |
| process  | score_lyrics_emotions    | Nisha       | raw_lyrics, raw_spotify_charts         | lyrics_emotion_scores   |
| curate   | validate_and_load_news   | Sai         | daily_news_sentiment                   | CURATED.NEWS_SENTIMENT  |
| curate   | validate_and_load_music  | Sai         | daily_music_features                   | CURATED.MUSIC_FEATURES  |
| curate   | validate_and_load_lyrics | Sai         | lyrics_emotion_scores                  | CURATED.LYRICS_EMOTIONS |

---

## Local vs GCP — What's Different

This table shows exactly what changes between running on your laptop vs production. **You do not need to do anything differently** — Kedro handles the switch.

| What                  | Local (your laptop)                        | GCP / Production                            |
|-----------------------|--------------------------------------------|---------------------------------------------|
| **Run command**       | `make run-local`                           | `KEDRO_ENV=base kedro run --env base`       |
| **Raw data source**   | Parquet files in `data/01_raw/`           | GCS bucket `msba405-society-music-2026`     |
| **Data processing**   | Spark DataFrames (local[*] mode)           | Spark DataFrames on Dataproc                |
| **Intermediate data** | Parquet files in `data/02_intermediate/`  | Parquet files in GCS `/processed/`          |
| **Final output**      | DuckDB file at `data/local.db`            | Snowflake — `CURATED` schema                |
| **Secrets**           | Not needed                                 | Pulled from GCP Secret Manager automatically|
| **Logs**              | Console (human readable)                   | GCP Cloud Logging (JSON, searchable)        |
| **Spark**             | Skipped — not needed locally              | Full Spark cluster on Dataproc              |
| **Credentials file**  | `conf/local/credentials.yml` (DuckDB)     | `conf/base/credentials.yml` (Snowflake)     |

> **The most important thing to know:** `data/local.db` is your personal local database — it is gitignored and never shared. Every teammate has their own. On GCP, the real Snowflake tables are shared.

---

# ONE-TIME SETUP
*Do these steps once when you first join the project.*

---

## Step 1 — Install Git

Download from https://git-scm.com/downloads and install with all default settings.

Verify it worked:
```bash
git --version
```

---

## Step 2 — Install Python 3.11

Download from https://www.python.org/downloads/

- **Windows:** during install, tick **"Add Python to PATH"** — this is important
- **Mac:** use the `.pkg` installer

Verify:
```bash
python --version
```

---

## Step 3 — Install `uv` (our package manager)

**Mac / Linux:**
```bash
curl -Lsf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify:
```bash
uv --version
```

---

## Step 4 — Clone the repository

```bash
git clone https://github.com/Prof-Rosario-UCLA/team17.git
cd team17
```

---

## Step 5 — Set up your Python environment

```bash
uv venv
uv pip install -r requirements.txt
```

This installs all Python libraries. Takes a few minutes. Only needed once.

---

## Step 6 — Install pre-commit hooks

```bash
make hooks
```

This installs a code checker that runs **automatically every time you do `git commit`**. It will catch formatting problems before they reach GitHub. You only run this once, but it protects every commit you make from now on.

> See the "Before You Commit" section below to understand exactly what it checks.

---

## Step 7 — Get your Kaggle API key (for sample data)

1. Go to https://www.kaggle.com → sign up or log in
2. Click your profile picture (top right) → **Settings**
3. Scroll to **API** → click **"Create New Token"**
4. A file called `kaggle.json` downloads — place it here:

```
team17/
└── .kaggle/
    └── kaggle.json   ← put it here
```

> This file is gitignored — it will never be pushed to GitHub.

---

## Step 8 — Download sample data

```bash
make samples
```

This downloads small (~5,000 row) CSV files into `data/01_raw/` for local testing. You do not need GCS access for this.

---

## Step 9 — Run the pipeline to confirm your setup works

```bash
make run-local
```

You should see 6 nodes complete successfully. If you see any errors, message me before continuing.

> **Note:** The first time you run this, Spark takes 10–15 seconds to start up before anything happens. This is normal — you will see a `SparkSession ready` log line once it's ready. Subsequent runs are faster because the JVM is already warm.

---

# EVERY TIME YOU START WORKING
*Do these steps at the start of every coding session, before touching any files.*

---

## Step 10 — Always pull the latest code first

Before you write a single line of code, sync with the latest version from GitHub. If you skip this, you might build on outdated code and create conflicts.

```bash
git checkout main
git pull origin main
```

Then create your branch (see Step 11). **Never edit files while you are on the `main` branch.**

---

## Step 11 — Create your own branch

A branch is your personal workspace. It keeps your changes separate from everyone else's until you're ready to share.

```bash
git checkout -b feature/your-name/what-you-did
```

Real examples:
```bash
git checkout -b feature/bhavika/clean-spotify-node
git checkout -b feature/shivathmika/clean-gdelt-node
git checkout -b feature/sai/validate-news
```

**Rules:**
- Always branch off from `main` (Step 10 ensures this)
- Never commit directly to `main`
- One branch per feature or task

---

## Step 12 — Write your code

Open your assigned file and find the `# TODO` comment. That is the only place you need to write code.

**To see the full pipeline visually:**
```bash
make viz
```
Open http://localhost:4141 in your browser.

---

## Step 13 — Test your node locally

Run only your node to check it works:

```bash
# Shivathmika
kedro run --nodes clean_gdelt_node

# Bhavika
kedro run --nodes clean_spotify_node

# Nisha
kedro run --nodes score_lyrics_emotions_node

# Sai
kedro run --pipeline curate
```

Or run the full pipeline end to end:
```bash
make run-local
```

> ⚠️ **Never** run `make run-prod` on your laptop — it hits GCS and costs real money.

---

## Step 14 — Run the pre-commit check

Before you commit anything, run this:

```bash
make check
```

This runs three things and tells you in plain English exactly what to fix:

1. **Formatting** — checks that your code is formatted correctly. If it fails, it tells you to run `ruff format .` (one command, fixes everything automatically).
2. **Style / lint** — checks for common mistakes like unused imports, `print()` instead of `logger`, or lines that are too long. Each error includes a plain-English description of what is wrong and how to fix it.
3. **Tests** — runs all unit tests to make sure your node still works correctly. If a test fails, it tells you the test name and what went wrong.

**If everything passes**, you will see:
```
ALL CHECKS PASSED — safe to commit!
```

**If something fails**, fix the issues it listed, then run `make check` again. Do not commit until it passes.

---

## Step 14b — Check your output quality

The curate pipeline (Sai's) will reject your output if:

- Any `date` or `country` column has **blank/null values**
- Any float score is **outside 0.0 to 1.0** (valence, energy, emotion scores, etc.)
- Any date is **outside 2017-01-01 to 2021-12-31**
- Any country code is not a valid 2-letter ISO code (`"US"`, `"GB"`, `"IN"`, `"BR"`, `"AU"`, `"DE"`)

Inspect your local output:
```bash
make inspect-local
```

---

# BEFORE YOU COMMIT
*Read this section carefully — it will save you a lot of frustration.*

---

## Step 15 — What pre-commit does (and what to do when it fails)

When you run `git commit`, a tool called **pre-commit** runs automatically before your code is saved. It checks for:

| Check | What it catches |
|---|---|
| Trailing whitespace | Invisible spaces at the end of lines |
| End of file | Files missing a newline at the end |
| YAML syntax | Broken config files |
| Large files | Accidentally committing data files |
| Merge conflicts | Unresolved `<<<<<<` markers left in code |
| Debug statements | `breakpoint()` or `pdb` left in production code |
| Ruff linter | Python style errors (unused imports, bad formatting, etc.) |
| Ruff formatter | Auto-formats your code to match the project style |

**What happens if a check fails:**

The commit is blocked. You will see output like:
```
ruff format..............................................Failed
- hook id: ruff-format
- files were modified by this hook
```

This means pre-commit **already fixed the file for you**. You just need to re-stage the fixed file and commit again:

```bash
# Re-add the file that was auto-fixed
git add src/society_to_music/pipelines/process/your_file.py

# Commit again — it will pass this time
git commit -m "Your commit message"
```

**If it shows an error you need to fix yourself** (e.g. an unused import or a debug statement), fix the issue in your editor, then:
```bash
git add your_file.py
git commit -m "Your commit message"
```

> **Tip:** Run `make check` before committing — it catches all of these issues early, in plain English, before pre-commit blocks you.

---

## Step 16 — Stage only your file

Only add the file you actually changed. Do not use `git add .` or `git add -A` — that can accidentally include data files, credentials, or other people's work.

```bash
# Correct — add only your file
git add src/society_to_music/pipelines/process/clean_spotify.py

# Wrong — adds everything
git add .
```

---

## Step 17 — Commit with a clear message

```bash
git commit -m "Implement clean_spotify: join charts and audio features, aggregate by date/country"
```

Write what you actually did, not just "update" or "fix". This helps the team understand what changed without reading the code.

---

## Step 18 — Push your branch

```bash
git push origin feature/your-name/what-you-did
```

Example:
```bash
git push origin feature/bhavika/clean-spotify-node
```

If it's your first push on this branch, Git may ask you to set the upstream — just copy and run the command it suggests.

---

## Step 19 — Open a Pull Request

1. Go to https://github.com/Prof-Rosario-UCLA/team17
2. A yellow banner will appear saying **"Compare & pull request"** — click it
3. Set **base branch** to `main`
4. Write a short description of what your code does
5. Add **nivesh22** as a reviewer
6. Click **"Create pull request"**

I will review it and merge it. **Do not merge your own PR.**

Once your PR is merged into `main`, GitHub Actions will automatically build and push a new Docker image. You do not need to do anything for that.

---

# REFERENCE

---

## Useful Commands

| Command              | What it does                                    |
|----------------------|-------------------------------------------------|
| `make run-local`     | Run the full pipeline locally (wipes local.db first) |
| `make run-process`   | Run only the `process` pipeline                |
| `make run-curate`    | Run only the `curate` pipeline                 |
| `make samples`       | Download 5,000-row sample CSV files            |
| `make inspect-local` | Show first 5 rows of each local DuckDB table   |
| `make viz`           | Open visual pipeline diagram in browser        |
| `make check`         | Plain-English pre-commit check (format + lint + tests) |
| `make test`          | Run automated tests with full coverage report  |
| `make lint`          | Check code style only (subset of `make check`) |
| `make hooks`         | Install pre-commit hooks (run once)            |
| `make logs`          | View recent GCP Cloud Logging output           |

---

## Tests

Each node has a test file in `tests/`. You do not need to write new tests — the contract tests are already there. But when you implement your logic, make sure the existing tests still pass by running `make check`.

| Your node | Test file |
|---|---|
| `clean_gdelt` | `tests/pipelines/process/test_clean_gdelt.py` |
| `clean_spotify` | `tests/pipelines/process/test_clean_spotify.py` |
| `score_lyrics_emotions` | `tests/pipelines/process/test_score_emotions.py` |
| `validate_and_load_*` | `tests/pipelines/curate/test_validate_load.py` |

Each test checks two things:
- Your function returns the correct type (Spark DataFrame for process nodes, pandas DataFrame for curate nodes)
- Your function does not crash on empty input

If you want to add more tests for your own logic (optional but encouraged), add them to your test file following the same pattern.

---

## What NOT to Touch 🛑

Do not edit any of these — they are Nivesh's responsibility:

- `src/society_to_music/pipeline_registry.py`
- `src/society_to_music/hooks.py`
- `src/society_to_music/settings.py`
- `src/society_to_music/utils/`
- `conf/base/catalog.yml`
- `conf/base/parameters.yml`
- `conf/base/credentials.yml`
- `conf/logging.yml`
- `Dockerfile`
- `.github/`
- `Makefile`

---

## Logging

Every node automatically logs start, end, row counts, and execution time — you get this for free from the `@log_node` decorator already on your function.

**Local output looks like:**
```
2026-03-07 10:23:01 | INFO | society_to_music.clean_spotify | START | input_0_rows=500
2026-03-07 10:23:03 | INFO | society_to_music.clean_spotify | END | output_rows=487 | elapsed_seconds=2.1
```

**To add your own log lines inside your node:**
```python
from society_to_music.utils.logging import get_logger
logger = get_logger(__name__)

logger.info(f"Processing {len(df)} rows")
logger.warning("Missing values found in country column")
```

**Never log:** passwords, credentials, full DataFrames, or personal data.

---

## Sai — Snowflake Setup

Your curate pipeline writes to Snowflake when running on GCP. Locally it writes to DuckDB (automatic, no setup needed). Here is what you need for each environment.

### Local (DuckDB) — no setup needed

When you run `make run-local`, your three nodes write to `data/local.db` automatically. No credentials, no Snowflake account needed. Use `make inspect-local` to see the output.

### GCP / Production (Snowflake) — credentials required

For production runs, you need the following Snowflake credentials stored in GCP Secret Manager (Nivesh sets these up — you just need to know they exist):

| Secret name          | What it is                              |
|----------------------|-----------------------------------------|
| `SNOWFLAKE_ACCOUNT`  | Account identifier (e.g. `abc123.us-east-1`) |
| `SNOWFLAKE_USER`     | Your Snowflake username                 |
| `SNOWFLAKE_PASSWORD` | Your Snowflake password                 |
| `SNOWFLAKE_WAREHOUSE` | Compute warehouse (e.g. `COMPUTE_WH`) |

These are pulled automatically at runtime — you never write them in code.

### What your nodes write to (Snowflake schema)

| Node                     | Snowflake table              | Key columns expected                                      |
|--------------------------|------------------------------|-----------------------------------------------------------|
| `validate_and_load_news` | `CURATED.NEWS_SENTIMENT`     | `date`, `country`, `tone_pos`, `tone_neg`, `polarity`     |
| `validate_and_load_music`| `CURATED.MUSIC_FEATURES`     | `date`, `country`, `avg_valence`, `avg_energy`, `avg_danceability`, `avg_tempo` |
| `validate_and_load_lyrics`| `CURATED.LYRICS_EMOTIONS`   | `track_id`, `joy`, `sadness`, `anger`                     |

### Validation rules your nodes must enforce

Before writing to Snowflake, your code must check:

- No nulls on `date`, `country`, or `track_id`
- All dates are within `2017-01-01` to `2021-12-31`
- Country codes are valid 2-letter ISO codes only
- All float scores (`joy`, `sadness`, `anger`, `avg_valence`, etc.) are between `0.0` and `1.0`
- No duplicate rows for the same `(date, country)` combination

If any check fails, raise a `ValueError` with a clear message — do not silently drop or fix bad rows.

### How Kedro writes to Snowflake (you don't need to write connection code)

The catalog handles the Snowflake connection automatically. Your function just returns a DataFrame and Kedro does the rest:

```python
# This is all you write — Kedro calls Snowflake for you
def validate_and_load_news(daily_news_sentiment: pd.DataFrame) -> pd.DataFrame:
    # ... your validation logic ...
    return validated_df   # Kedro saves this to Snowflake (or DuckDB locally)
```

---

## Docker Images

Images are built and pushed automatically — **you never need to build or push manually.**

- **Every PR to main** → dev image is built to validate your code compiles correctly
- **Every merge to main** → production image is built and pushed, tagged `:latest` and `:<git-sha>`

You do not need to do anything. Just open a PR and let GitHub Actions handle it.
