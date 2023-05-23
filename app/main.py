# Standard library imports
import os
import logging
# Related third party imports
from fastapi import FastAPI
from starlette.responses import Response
from starlette.requests import Request
# Local application/library specific imports
from app.users.auth import FirebaseSettings
from .audio_processing import audio_processing
from .job_processing import job_processing
from .file_management import file_management
from .user_activity import user_activity

# logger config
logger = logging.getLogger(__name__)

os.environ["FIREBASE_CREDENTIAL_PATH"] = "/Users/wojciechbednarz/Desktop/python_projects/euclidean_rhythm_generator_mobile_python_fastapi/env/firebase_creds.json"
firebase_settings = FirebaseSettings()

app = FastAPI()

app.include_router(job_processing)
app.include_router(audio_processing)
app.include_router(file_management)
app.include_router(user_activity)

async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(e)
        return Response("Internal server error", status_code=500)


app.middleware("http")(catch_exceptions_middleware)

