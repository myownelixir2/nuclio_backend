from fastapi import APIRouter, Depends, HTTPException

from app.users.auth import get_current_user, UserInDB
from app.utils.utils import JobUtils, purge_all
from app.storage.storage import (
    StoreEngineMultiFile,
    StorageEngineDownloader,
    SnapshotManager,
)

import logging
import re

logger = logging.getLogger(__name__)
file_management = APIRouter()


@file_management.post("/clean_up_assets")
def clean_up_assets(job_id: str, current_user: UserInDB = Depends(get_current_user)):
    try:
        logger.info("Starting to clean up assets...")
        clean_up_job = JobUtils(job_id)

        matching_assets = clean_up_job.list_files_matching_pattern(
            ["*.mp3"], "assets/sounds", "mp3"
        )
        res = clean_up_job.remove_files(matching_assets)
        logger.info("Finished cleaning up assets...")
        return res
    except Exception as e:
        logger.error(e)
        return e


@file_management.post("/clean_up_temp")
def clean_up_temp(
    job_id: str,
    pattern: str,
    random_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    It will remove all files anti-matching the pattern in the temp folder.
    What it means, is that when you request a mixdown, it
    will remove all the other files, retaining only the latest mixdown.
    Like this it will keep the folder clean and only the latest mixdown
    will be available.
    Args:
        job_id (str): job_id
        pattern (str): patern for example "mixdown", "sequence", "fx", "all"
        random_id (str): random_id generate when requesting mixdown job

    Raises:
        HTTPException: if wrong pattern

    Returns:
        _type_: _description_
    """
    try:
        logger.info("Starting to clean up assets...")

        clean_up_job = JobUtils(job_id)
        sanitized_job_id = clean_up_job.sanitize_job_id()
        if pattern == "all":
            patterns_to_match = sanitized_job_id
        else:
            if pattern in ["mixdown", "sequence", "fx"]:
                patterns_to_match = pattern
            else:
                raise HTTPException(status_code=404, detail="pattern not supported")
        matching_files = clean_up_job.list_files_matching_pattern(
            ["*.wav", "*.pkl"], "temp", patterns_to_match
        )

        regex = re.compile(f".*{random_id}.*")
        anti_matching_files = [f for f in matching_files if not regex.match(f)]

        res = clean_up_job.remove_files(anti_matching_files)
        logger.info("Finished cleaning up assets...")
        return res
    except Exception as e:
        logger.error(e)
        return e


@file_management.post("/add_to_favourites")
def add_to_favourites(job_id: str, current_user: UserInDB = Depends(get_current_user)):
    logger.info("Uploading favourites to cloud...")
    gather_assets_job = JobUtils(job_id)
    sanitized_job_id = gather_assets_job.sanitize_job_id()
    matching_files = gather_assets_job.list_files_matching_pattern(
        ["*.wav", "*.json"], "temp", sanitized_job_id
    )
    if not matching_files:
        raise HTTPException(
            status_code=404, detail="Did not find any items with provided job_id"
        )

    # print(matching_files)
    try:
        multi_file_upload_job = StoreEngineMultiFile(job_id)

        upload_path = "steams" + "/" + sanitized_job_id.split("__")[0]

        status = multi_file_upload_job.upload_list_of_objects(matching_files, upload_path)
    except Exception as e:
        logger.error(e)
        status = False

    return status


@file_management.post("/purge")
def purge(current_user: UserInDB = Depends(get_current_user)):
    try:
        logger.info("Starting to purge temp...")
        purge_all(["temp"], ["*.pkl", "*.mp3", "*.wav", "*.json"])
        logger.info("Starting to purge assets...")
        purge_all(["assets", "sounds"], ["*.pkl", "*.mp3", "*.wav"])
        return True
    except Exception as e:
        logger.error(e)
        return e


@file_management.post("/download_from_favourites")
def download_from_favourites(
    bucket: str, prefix_: str, current_user: UserInDB = Depends(get_current_user)
):
    downloader = StorageEngineDownloader(bucket)

    prefix = f"{prefix_}"
    zip_name = f"zip/{prefix_}.zip"

    my_files = downloader.filter_objects(prefix)

    in_memory_zip = downloader.create_zip_file(my_files)

    download_url = downloader.upload_and_get_presigned_url(zip_name, in_memory_zip)

    return download_url


@file_management.post("/download_universal")
def download_universal(
    bucket: str, file_name: str, current_user: UserInDB = Depends(get_current_user)
):
    downloader = StorageEngineDownloader(bucket)

    download_url = downloader.get_presigned_url(file_name, 15)

    return download_url


@file_management.post("/build_snapshots")
def build_snapshots(bucket: str, current_user: UserInDB = Depends(get_current_user)):
    snapshot_manager = SnapshotManager(bucket)

    if snapshot_manager.build_snapshot() and snapshot_manager.get_snapshot_data():
        url_1, url_2 = snapshot_manager.generate_presigned_urls()
        return {"snapshot_url": url_1, "snapshot_files_url": url_2}
    else:
        return {"error": "Failed to build snapshots and generate presigned URLs"}
