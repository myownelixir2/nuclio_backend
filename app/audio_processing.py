from fastapi import APIRouter, Depends, HTTPException
from app.users.auth import get_current_user, UserInDB
from app.utils.utils import JobConfig
from app.storage.storage import StorageEngineDownloader
import logging
from pathlib import Path
from app.sequence_generator.generator import JobRunner
from app.post_fx.post_fx import FxParamsModel, FxRunner
from app.mixer.mixer import MixRunner

logger = logging.getLogger(__name__)
audio_processing = APIRouter()


@audio_processing.post("/get_sequence")
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


@audio_processing.post("/apply_fx")
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
    

@audio_processing.post("/mix_sequences")
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
    

@audio_processing.post("/mix_arrangement")
def mix_arrangement(bucket: str,
                    prefix_: str,
                    suffix_: str,
                    mixdown_ids: str,
                    arrange_id: str,
                    current_user: UserInDB = Depends(get_current_user)):

    downloader = StorageEngineDownloader(bucket)

    # prepare filter params
    full_prefix = f'steams/{prefix_}/mixdown_'
    mixdown_ids = mixdown_ids.split('_')
    file_format = suffix_[-3:]

    # prepare output file
    #timestamp = str(int(time.time()))
    #random_string = downloader.generate_random_string(6)
    output_file = f'steams/{prefix_}/arrangement_{arrange_id}.wav'

    # mixdown
    my_files = downloader.filter_objects(full_prefix)
    my_mixdown_files = downloader.filter_files(my_files, suffix_, mixdown_ids)
    in_memory_arragement = downloader.create_arrangement_file(my_mixdown_files, file_format)

    # mixdown
    downloader.upload_in_memory_object(output_file, in_memory_arragement)
    download_url = downloader.get_presigned_url(output_file)

    return download_url