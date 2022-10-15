from fastapi import FastAPI, HTTPException
import os
import logging
from app.sequence_generator.generator import *


# logger config
logger = logging.getLogger(__name__)


app = FastAPI()


@app.get('/')
def home():
    return os.getcwd()


@app.post('/job')
def job_id(job_id: str):
    try:
        logger.info('Starting to build sequence...')
        print(job_id)
        job_params = JobConfig(job_id, 0)
        StorageEngine(job_params, 'job_id_path').get_object()
        return True
    except Exception as e:
        logger.error(e)
        return e


@app.post('/get_sequence')
def get_sequence(job_id: str, channel_index: int, random_id: str):
    try:
        logger.info('Starting to build sequence...')
        job = JobRunner(job_id, channel_index, random_id)
        res = job.execute()
        processed_job_id = job.result(res)
        logger.info('Finished building sequence...')

        # job.clean_up()
        logger.info('clean up done...')
        print(processed_job_id)

        if 'sequences' not in processed_job_id:
            raise HTTPException(status_code=404, detail="Something went wrong")
        return processed_job_id

    except Exception as e:
        logger.error(e)
        return e
