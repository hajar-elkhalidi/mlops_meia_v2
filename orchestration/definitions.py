import os
import subprocess
import sys
from pathlib import Path

import dagster as dg

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_command(
    context: dg.OpExecutionContext,
    command: list[str],
    cwd: Path | None = None,
    env: dict | None = None,
) -> None:
    """
    Execute a command and stream its output into Dagster logs.
    """

    working_directory = cwd or PROJECT_ROOT

    merged_env = os.environ.copy()

    if env:
        merged_env.update(env)

    context.log.info(
        "Running command: %s",
        " ".join(command),
    )

    process = subprocess.Popen(
        command,
        cwd=str(working_directory),
        env=merged_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    assert process.stdout is not None

    for line in process.stdout:
        context.log.info(line.rstrip())

    return_code = process.wait()

    if return_code != 0:
        raise RuntimeError(
            f"Command failed with exit code {return_code}: {' '.join(command)}"
        )


# ============================================================
# 1. DLT INGESTION
# ============================================================


@dg.op
def ingestion(
    context: dg.OpExecutionContext,
) -> str:

    context.log.info("Starting dlt ingestion")

    run_command(
        context,
        [
            sys.executable,
            "ingestion/pipeline.py",
        ],
        cwd=PROJECT_ROOT,
    )

    context.log.info("dlt ingestion completed")

    return "ingestion_completed"


# ============================================================
# 2. DBT TRANSFORMATIONS
# ============================================================


@dg.op
def dbt_transform(
    context: dg.OpExecutionContext,
    ingestion_result: str,
) -> str:

    context.log.info(f"Received: {ingestion_result}")

    context.log.info("Starting dbt transformations")

    run_command(
        context,
        [
            "dbt",
            "run",
            "--profiles-dir",
            ".",
        ],
        cwd=PROJECT_ROOT / "transform",
    )

    context.log.info("dbt transformations completed")

    return "dbt_transform_completed"


# ============================================================
# 3. DATA QUALITY
# ============================================================


@dg.op
def data_quality(
    context: dg.OpExecutionContext,
    transform_result: str,
) -> str:

    context.log.info(f"Received: {transform_result}")

    context.log.info("Starting dbt quality tests")

    run_command(
        context,
        [
            "dbt",
            "test",
            "--profiles-dir",
            ".",
        ],
        cwd=PROJECT_ROOT / "transform",
    )

    context.log.info("Data quality tests completed")

    return "quality_tests_completed"


# ============================================================
# 4. ML TRAINING + MLFLOW REGISTRY
# ============================================================


@dg.op
def train_and_register_model(
    context: dg.OpExecutionContext,
    quality_result: str,
) -> str:

    context.log.info(f"Received: {quality_result}")

    context.log.info("Starting ML training and MLflow registration")

    run_command(
        context,
        [
            sys.executable,
            "ml/tracking/train_with_mlflow.py",
        ],
        cwd=PROJECT_ROOT,
    )

    context.log.info("Training and registration completed")

    return "model_registered"


# ============================================================
# 5. MONITORING READINESS
# ============================================================


@dg.op
def monitoring_ready(
    context: dg.OpExecutionContext,
    model_result: str,
) -> None:

    context.log.info(f"Received: {model_result}")

    baseline_candidates = [
        PROJECT_ROOT / "feature_baseline.json",
        PROJECT_ROOT / "ml" / "tracking" / "feature_baseline.json",
    ]

    baseline = next(
        (path for path in baseline_candidates if path.exists()),
        None,
    )

    if baseline is None:
        raise RuntimeError("Feature baseline was not generated.")

    context.log.info(f"Monitoring baseline available: {baseline}")

    context.log.info("Drift monitoring is ready for incoming production data.")


# ============================================================
# FULL DATAOPS / MLOPS JOB
# ============================================================


@dg.job(
    description=(
        "Pipeline DataOps/MLOps complet : "
        "dlt -> dbt -> qualité -> ML -> "
        "MLflow -> monitoring"
    )
)
def full_mlops_pipeline():

    raw_data = ingestion()

    transformed_data = dbt_transform(raw_data)

    validated_data = data_quality(transformed_data)

    registered_model = train_and_register_model(validated_data)

    monitoring_ready(registered_model)


# ============================================================
# DAGSTER DEFINITIONS
# ============================================================

defs = dg.Definitions(
    jobs=[
        full_mlops_pipeline,
    ]
)
