import os

import google.auth.transport.requests
import google.oauth2.id_token
import mlflow.tracking


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
