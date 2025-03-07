"this module provides utility functions for MLflow"

import os
from typing import Any, Dict, Optional

import google.auth.transport.requests
import google.oauth2.id_token
import mlflow.tracking
import pandas as pd
from mlflow.entities.model_registry import ModelVersion


def set_google_tracking_token(
    tracking_uri: Optional[str] = None,
    tracking_token: Optional[str] = None,
    google_application_credentials: Optional[str] = None,
) -> None:
    """
    Set the Google tracking token for MLflow. If the tracking token is not provided, it is fetched from the Google Application Credentials.

    Args:
        tracking_uri (Optional[str], optional): The tracking URI. Defaults to None - in which case the environment variable MLFLOW_TRACKING_URI is used.
        tracking_token (Optional[str], optional): The tracking token. Defaults to None - in which case the token is fetched from the Google Application Credentials.
        google_application_credentials (Optional[str], optional): The Google application credentials. Defaults to None - in which case the environment variable GOOGLE_APPLICATION_CREDENTIALS is used.
    """
    if google_application_credentials is not None:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_application_credentials
    if tracking_uri is not None:
        os.environ["MLFLOW_TRACKING_URI"] = tracking_uri
    if tracking_token is None:
        os.environ["MLFLOW_TRACKING_TOKEN"] = google.oauth2.id_token.fetch_id_token(
            request=google.auth.transport.requests.Request(),
            audience=os.environ["MLFLOW_TRACKING_URI"],
        )
    else:
        os.environ["MLFLOW_TRACKING_TOKEN"] = tracking_token


def get_latest_versions(model_name: str) -> Dict[str, ModelVersion]:
    """Get the latest versions of a model."""
    return {
        v.current_stage: v
        for v in mlflow.tracking.MlflowClient().get_latest_versions(model_name)
    }


def get_latest_version(model_name: str) -> ModelVersion:
    """Get the latest version of a model."""
    versions = {
        v.version: v
        for v in mlflow.tracking.MlflowClient().get_latest_versions(model_name)
    }
    return versions[max(versions)]


def run_info(experiment_name: str) -> pd.DataFrame:
    """Get the run info for an experiment."""
    experiment_ids = {e.name: e.experiment_id for e in mlflow.search_experiments()}
    all_runs: list[Dict[str, Any]] = []
    runs = mlflow.tracking.MlflowClient().search_runs(
        [experiment_ids[experiment_name]], max_results=1000
    )
    all_runs += [run.to_dictionary() for run in runs]

    while runs.token is not None:
        runs = mlflow.tracking.MlflowClient().search_runs(
            [experiment_ids[experiment_name]], page_token=runs.token
        )
        all_runs += [run.to_dictionary() for run in runs]

    return pd.json_normalize(all_runs)
