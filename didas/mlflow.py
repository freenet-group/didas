import os
import google.auth.transport.requests
import google.oauth2.id_token


def set_google_tracking_token():
    os.environ["MLFLOW_TRACKING_TOKEN"] = google.oauth2.id_token.fetch_id_token(
        request = google.auth.transport.requests.Request(),
        audience = os.environ["MLFLOW_TRACKING_URI"],
    )
