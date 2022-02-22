import os

import google.auth.transport.requests
import google.oauth2.id_token


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
