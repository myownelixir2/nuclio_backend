from fastapi import FastAPI, HTTPException, Depends
import os
import re
import logging
from pathlib import Path
from starlette.responses import Response
from starlette.requests import Request
#from app.sequence_generator.generator import *
#from app.mixer.mixer import *
from app.utils.utils import JobConfig, JobUtils, purge_all
from app.storage.storage import StorageEngine, StoreEngineMultiFile, StorageEngineDownloader
from app.sequence_generator.generator import JobRunner
from app.post_fx.post_fx import FxParamsModel, FxRunner
from app.mixer.mixer import MixRunner
from app.users.auth import get_current_user, FirebaseSettings, UserInDB

# logger config
logger = logging.getLogger(__name__)
os.environ["FIREBASE_CREDENTIAL_PATH"] = "/Users/wojciechbednarz/Desktop/python_projects/euclidean_rhythm_generator_mobile_python_fastapi/env/firebase_creds.json"
firebase_settings = FirebaseSettings()

app = FastAPI()



async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(e)
        return Response("Internal server error", status_code=500)


app.middleware("http")(catch_exceptions_middleware)


@app.get("/hello")
def home(current_user: UserInDB = Depends(get_current_user)):
    return os.getcwd()


@app.post("/job")
def job_id(job_id: str,
           current_user: UserInDB = Depends(get_current_user)):

    logger.info("fetching job id...")
    job_params = JobConfig(job_id, 0, random_id="")
    my_storage = StorageEngine(job_params, "job_id_path")
    my_storage.client_init()
    my_storage.get_object()

    try:
        job_id_file = Path(job_params.path_resolver()["local_path"])
        job_id_file.resolve(strict=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Job ID not found")
    else:
        return {"job_id": job_id}


@app.post("/get_sequence")
def get_sequence(job_id: str, 
                 channel_index: int, 
                 random_id: str, 
                 current_user: UserInDB = Depends(get_current_user)):
    try:
        logger.info("Starting to build sequence...")
        job = JobRunner(job_id, channel_index, random_id)
        res = job.execute()
        processed_job_id = job.result(res)
        logger.info("Finished building sequence...")
        print(processed_job_id)

        if "sequences" not in processed_job_id:
            raise HTTPException(
                status_code=404, detail="problem with sequence generation"
            )
        return processed_job_id

    except IndexError as e:
        logger.error(e)
        raise HTTPException(status_code=404, detail="problem with sequence generation")


@app.post("/apply_fx")
def apply_fx(
    job_id: str,
    channel_index: int,
    random_id: str,
    fx_input: str,
    selective_mutism_switch: str,
    vol: str,
    channel_mute_params: str,
    selective_mutism_value: str,
    current_user: UserInDB = Depends(get_current_user)
):

    mix_params = FxParamsModel(
        job_id=job_id,
        fx_input=fx_input,
        channel_index=channel_index,
        selective_mutism_switch=selective_mutism_switch,
        vol=vol,
        channel_mute_params=channel_mute_params,
        selective_mutism_value=selective_mutism_value,
    )
    try:
        logger.info("Starting to apply fx...")
        job_params = JobConfig(job_id, channel_index, random_id=random_id)

        fx = FxRunner(mix_params, job_id, channel_index, random_id)
        res = fx.execute()

        print(res)

        mixdown_file = Path(job_params.path_resolver()["local_path_mixdown_pkl"])
        mixdown_file.resolve(strict=True)

    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail="mixdown file not found, job failed ;("
        )
    else:
        return mix_params


@app.post("/mix_sequences")
def mix_sequences(job_id: str, 
                  random_id: str,
                  current_user: UserInDB = Depends(get_current_user)):
    try:
        logger.info("Starting to mix sequences...")

        job = MixRunner(job_id, random_id)
        res = job.execute()

        logger.info("Finished mixing sequences...")

        if not res:
            raise HTTPException(
                status_code=404, detail="Something went wrong with mixing sequences"
            )
        else:
            return res
    except Exception as e:
        logger.error(e)
        return e


@app.post("/clean_up_assets")
def clean_up_assets(job_id: str,
                    current_user: UserInDB = Depends(get_current_user)):
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


@app.post("/clean_up_temp")
def clean_up_temp(job_id: str, 
                  pattern: str, 
                  random_id: str,
                  current_user: UserInDB = Depends(get_current_user)):
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


@app.post("/purge")
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

@app.post("/add_to_favourites")
def add_to_favourites(job_id: str,
                      current_user: UserInDB = Depends(get_current_user)):
    logger.info("Uploading favourites to cloud...")
    gather_assets_job = JobUtils(job_id)
    sanitized_job_id = gather_assets_job.sanitize_job_id()
    matching_files = gather_assets_job.list_files_matching_pattern(
        ["*.wav", "*.json"], "temp", sanitized_job_id
    )
    if not matching_files:
        raise HTTPException(status_code=404, detail="Did not find any items with provided job_id")

    print(matching_files)
    try:
        multi_file_upload_job = StoreEngineMultiFile(job_id)

        upload_path = "steams" + "/" + sanitized_job_id.split('__')[0]

        status = multi_file_upload_job.upload_list_of_objects(
            matching_files, upload_path
        )
    except Exception as e:
        logger.error(e)
        status = False

    return status

@app.post("/download_from_favourites")
def download_from_favourites(bucket: str,
                             prefix_: str,
                             current_user: UserInDB = Depends(get_current_user)):
    downloader = StorageEngineDownloader(bucket)

    prefix = f"{prefix_}"
    zip_name = f"zip/{prefix_}.zip"

    my_files = downloader.filter_objects(prefix)

    in_memory_zip = downloader.create_zip_file(my_files)

    download_url = downloader.upload_and_get_presigned_url(zip_name, in_memory_zip)

    return(download_url)

@app.post("/download_universal")
def download_universal(bucket: str,
                       file_name: str,
                       current_user: UserInDB = Depends(get_current_user)):
    downloader = StorageEngineDownloader(bucket)

    download_url = downloader.get_presigned_url(file_name, 15)

    return(download_url)
