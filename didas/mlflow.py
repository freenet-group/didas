import os

import google.auth.transport.requests
import google.oauth2.id_token
import mlflow.tracking
import pandas as pd


def set_google_tracking_token(tracking_uri=None, tracking_token=None):
    if tracking_uri is not None:
        os.environ["MLFLOW_TRACKING_URI"] = tracking_uri
    if tracking_token is None:
        os.environ["MLFLOW_TRACKING_TOKEN"] = google.oauth2.id_token.fetch_id_token(
            request=google.auth.transport.requests.Request(),
            audience=os.environ["MLFLOW_TRACKING_URI"],
        )
    else:
        os.environ["MLFLOW_TRACKING_TOKEN"] = tracking_token


def get_latest_versions(model_name):
    return {v.current_stage: v for v in mlflow.tracking.MlflowClient().get_latest_versions(model_name)}


def get_latest_version(model_name):
    versions = {v.version: v for v in mlflow.tracking.MlflowClient().get_latest_versions(model_name)}
    return versions[max(versions)]


def run_info(experiment_name):
    experiment_ids = {e.name: e.experiment_id for e in mlflow.list_experiments()}
    all_runs = list()
    runs = mlflow.tracking.MlflowClient().search_runs([experiment_ids[experiment_name]], max_results=1000)
    all_runs += [run.to_dictionary() for run in runs]

    while runs.token is not None:
        runs = mlflow.tracking.MlflowClient().search_runs([experiment_ids[experiment_name]], page_token=runs.token)
        all_runs += [run.to_dictionary() for run in runs]

    return pd.json_normalize(all_runs)
