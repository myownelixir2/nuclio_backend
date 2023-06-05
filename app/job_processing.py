from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Optional

from app.users.auth import get_current_user, UserInDB
from app.utils.utils import JobConfig
from app.storage.storage import StorageEngine

import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)
job_processing = APIRouter()


@job_processing.post("/create_job")
def create_job(
    job_id: str,
    payload: dict = Body(...),
    current_user: UserInDB = Depends(get_current_user),
):
    try:
        job_params = JobConfig(job_id, 0, random_id="")
        local_path = job_params.path_resolver()["local_path"]

        with open(local_path, "w") as fp:
            json.dump(payload, fp)

        my_storage = StorageEngine(job_params, "job_id_path")
        # my_storage.client_init()
        print(my_storage)
        my_storage.upload_object()
        return True
    except Exception:
        raise HTTPException(status_code=404, detail="problem with Job creation")


@job_processing.post("/job")
def job_id(job_id: str, current_user: UserInDB = Depends(get_current_user)):
    logger.info("fetching job id...")
    job_params = JobConfig(job_id, 0, random_id="")
    my_storage = StorageEngine(job_params, "job_id_path")
    # my_storage.client_init()

    local_path = job_params.path_resolver()["local_path"]
    job_id_file = Path(local_path)

    if not job_id_file.exists():
        try:
            my_storage.get_object()
            job_id_file.resolve(strict=True)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Job ID not found")

    return {"job_id": job_id}
