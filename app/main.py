from fastapi import FastAPI, HTTPException
import os
import logging
from app.sequence_generator.generator import *
from app.mixer.mixer import *


# logger config
logger = logging.getLogger(__name__)


app = FastAPI()


@app.get('/')
def home():
    return os.getcwd()


@app.post('/job')
def job_id(job_id: str):

    logger.info('fetching job id...')
    job_params = JobConfig(job_id, 0, random_id='')
    my_storage = StorageEngine(job_params, 'job_id_path')
    error = my_storage.client_init()
    
    if isinstance(error, bool):
        raise HTTPException(status_code=500, detail='missing storage credentials')
    else:
        my_storage.get_object()
        return True



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
            raise HTTPException(status_code=404, detail="problem with sequence generation")
        return processed_job_id

    except Exception as e:
        logger.error(e)
        return e


@app.post('/apply_fx')
def apply_fx(job_id: str, 
             channel_index: int, 
             random_id: str, 
             fx_input: str, 
             selective_mutism_switch: str, 
             vol: str,
             channel_mute_params: str,
             selective_mutism_value: str
             ):
    try:
        logger.info('Starting to apply fx...')
        
        mix_params = FxParamsModel(job_id, fx_input, channel_index, selective_mutism_switch, vol, channel_mute_params, selective_mutism_value)
        
        job = FxRunner(mix_params, job_id, channel_index, random_id)
        res = job.execute()
        
        logger.info('Finished applying fx...')

        if not res:
            raise HTTPException(status_code=404, detail="Something went wrong with applying fx")
        else:
            return res
    except Exception as e:
        logger.error(e)
        return e
    

@app.post('/mix_sequences')
def mix_sequences(job_id: str, random_id: str ):
    try:
        logger.info('Starting to mix sequences...')
 
        job = MixRunner(job_id, random_id)
        res = job.execute()
        
        logger.info('Finished mixing sequences...')

        if not res:
            raise HTTPException(status_code=404, detail="Something went wrong with mixing sequences")
        else:
            return res
    except Exception as e:
        logger.error(e)
        return e