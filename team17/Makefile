.PHONY: setup samples full-data run-local run-process run-curate run-prod test check viz hooks lint ci inspect-local logs setup-registry docker-push download-model schedule delete-schedule

IMAGE = us-central1-docker.pkg.dev/msba-405-from-society-to-music/society-to-music/pipeline

# ── Spark / Java environment ──────────────────────────────────────────────────
# All targets that touch Spark or Kedro inherit these vars automatically.
# JDK 17 is required — JDK 21+ breaks Spark's Arrow/Netty integration.
JAVA_HOME      = /opt/homebrew/opt/openjdk@17
SPARK_ENV      = PATH="$(JAVA_HOME)/bin:$(PATH)" \
                 JAVA_HOME="$(JAVA_HOME)" \
                 PYSPARK_PYTHON=.venv/bin/python3 \
                 PYSPARK_DRIVER_PYTHON=.venv/bin/python3 \
                 KEDRO_DISABLE_TELEMETRY=1

# ── One-time setup ────────────────────────────────────────────────────────────
setup:
	@echo "→ Checking for JDK 17..."
	@if [ ! -f "$(JAVA_HOME)/bin/java" ]; then \
		echo "  JDK 17 not found — installing via Homebrew..."; \
		brew install openjdk@17; \
	else \
		echo "  JDK 17 found at $(JAVA_HOME)"; \
	fi
	@echo "→ Creating virtual environment..."
	uv venv
	@echo "→ Installing dependencies..."
	uv pip install -r requirements-dev.txt
	@echo "→ Installing project package..."
	uv pip install -e .
	@echo "→ Setting up Kaggle credentials..."
	@mkdir -p ~/.kaggle
	@if [ -f ".kaggle/kaggle.json" ] && [ ! -f "$$HOME/.kaggle/kaggle.json" ]; then \
		cp .kaggle/kaggle.json ~/.kaggle/kaggle.json; \
		echo "  Copied .kaggle/kaggle.json → ~/.kaggle/kaggle.json"; \
	fi
	@if [ -f "$$HOME/.kaggle/kaggle.json" ]; then \
		chmod 600 ~/.kaggle/kaggle.json; \
		echo "  Permissions set: chmod 600 ~/.kaggle/kaggle.json"; \
	else \
		echo "  ⚠️  No kaggle.json found. To download data you'll need one."; \
		echo "      Get it from https://www.kaggle.com/settings → API → Create New Token"; \
		echo "      Then place it at ~/.kaggle/kaggle.json and run: chmod 600 ~/.kaggle/kaggle.json"; \
	fi
	@echo ""
	@echo "✓ Setup complete. Run these next:"
	@echo "  make hooks          — install pre-commit hooks (run once)"
	@echo "  make samples        — download sample data from Kaggle"
	@echo "  make download-model — download the HuggingFace emotion model"
	@echo "  make run-local      — run the full pipeline"

# Download the emotion model from HuggingFace and save to data/models/emotion/.
download-model:
	mkdir -p data/models/emotion
	.venv/bin/python3 -c "\
from transformers import AutoModelForSequenceClassification, AutoTokenizer; \
mid = 'j-hartmann/emotion-english-distilroberta-base'; \
print('Downloading', mid, '...'); \
AutoTokenizer.from_pretrained(mid).save_pretrained('data/models/emotion/'); \
AutoModelForSequenceClassification.from_pretrained(mid).save_pretrained('data/models/emotion/'); \
print('Saved to data/models/emotion/')"

# ── Data download ─────────────────────────────────────────────────────────────
samples:
	.venv/bin/python3 scripts/download_samples.py

full-data:
	.venv/bin/python3 scripts/download_samples.py --full

# ── Pipeline runs ─────────────────────────────────────────────────────────────
run-local:
	rm -f data/local.db && $(SPARK_ENV) .venv/bin/kedro run

run-process:
	$(SPARK_ENV) .venv/bin/kedro run --pipeline process

run-curate:
	$(SPARK_ENV) .venv/bin/kedro run --pipeline curate

run-prod:
	KEDRO_ENV=base .venv/bin/kedro run --env base

# ── Dev tools ─────────────────────────────────────────────────────────────────
test:
	.venv/bin/pytest tests/ --cov=src/society_to_music --cov-report=term-missing

check:
	.venv/bin/python3 scripts/check_before_commit.py

viz:
	$(SPARK_ENV) .venv/bin/kedro viz run

hooks:
	.venv/bin/pre-commit install

lint:
	.venv/bin/ruff check .

ci: lint test

inspect-local:
	.venv/bin/python3 scripts/inspect_local_db.py

# ── GCP / infra ───────────────────────────────────────────────────────────────
logs:
	gcloud logging read \
		"resource.type=cloud_dataproc_job" \
		--project=${GCP_PROJECT_ID} \
		--limit=50 \
		--format="table(timestamp,severity,textPayload)"

setup-registry:
	bash scripts/setup_artifact_registry.sh

docker-push:
	docker build --target main -t $(IMAGE):latest . && \
	docker push $(IMAGE):latest

# ── Scheduling ────────────────────────────────────────────────────────────────
# Creates a Cloud Scheduler job that triggers the pipeline every Monday at
# 02:00 UTC. Adjust --schedule to any cron expression as needed.
# Requires: gcloud authed, GCP_PROJECT_ID set in environment.
schedule:
	gcloud scheduler jobs create http run-pipeline-weekly \
		--location=us-central1 \
		--schedule="0 2 * * 1" \
		--description="Weekly Society-to-Music pipeline run (every Monday 02:00 UTC)" \
		--uri="https://workflowexecutions.googleapis.com/v1/projects/msba-405-from-society-to-music/locations/us-central1/workflows/run-pipeline/executions" \
		--message-body='{"argument":"{\"image_tag\":\"latest\",\"branch\":\"main\"}"}' \
		--oauth-service-account-email=kedro-pipeline@msba-405-from-society-to-music.iam.gserviceaccount.com \
		--oauth-token-scope=https://www.googleapis.com/auth/cloud-platform
	@echo "✓ Scheduler job created — runs every Monday at 02:00 UTC"
	@echo "  View: https://console.cloud.google.com/cloudscheduler?project=msba-405-from-society-to-music"

delete-schedule:
	gcloud scheduler jobs delete run-pipeline-weekly --location=us-central1 --quiet
	@echo "✓ Scheduler job deleted"
