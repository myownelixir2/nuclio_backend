from fastapi import FastAPI, HTTPException
import os
import logging
from pydantic import ValidationError, validator
from pathlib import Path
from starlette.responses import Response
from starlette.requests import Request
from fastapi.responses import JSONResponse
from app.sequence_generator.generator import *
from app.mixer.mixer import *


# logger config
logger = logging.getLogger(__name__)



app = FastAPI()

async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(e)
        return Response("Internal server error", status_code=500)

app.middleware('http')(catch_exceptions_middleware)

@app.get('/')
def home():
    return os.getcwd()


@app.post('/job')
def job_id(job_id: str):

    logger.info('fetching job id...')
    job_params = JobConfig(job_id, 0, random_id='')
    my_storage = StorageEngine(job_params, 'job_id_path')
    my_storage.client_init()
    my_storage.get_object()
    
    try:
        job_id_file = Path(job_params.path_resolver()['local_path'])
        job_id_file.resolve(strict=True)   
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Job ID not found")
    else:
        return {'job_id': job_id}
        


@app.post('/get_sequence')
def get_sequence(job_id: str, channel_index: int, random_id: str):
    try:
        logger.info('Starting to build sequence...')
        job = JobRunner(job_id, channel_index, random_id)
        res = job.execute()
        processed_job_id = job.result(res)
        logger.info('Finished building sequence...')
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

    mix_params = FxParamsModel(job_id=job_id, 
                                   fx_input=fx_input, 
                                   channel_index=channel_index, 
                                   selective_mutism_switch=selective_mutism_switch, 
                                   vol=vol, 
                                   channel_mute_params=channel_mute_params, 
                                   selective_mutism_value=selective_mutism_value)
    try: 
        logger.info('Starting to apply fx...')
        job_params = JobConfig(job_id, channel_index, random_id=random_id)
        
        fx = FxRunner(mix_params, job_id, channel_index, random_id)
        res=fx.execute()
        
        print(res)
        
        mixdown_file = Path(job_params.path_resolver()['local_path_mixdown_pkl'])
        mixdown_file.resolve(strict=True)     
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="mixdown file not found, job failed ;(")
    else:
        return mix_params

    
    

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
    

@app.post('/clean_up_assets')
def clean_up_assets(job_id: str):
    try:
        logger.info('Starting to clean up assets...')
        clean_up_job = JobCleanUp(job_id)
        res = clean_up_job.assets()
        logger.info('Finished cleaning up assets...')
        return res
    except Exception as e:
        logger.error(e)
        return e
    
@app.post('/clean_up_temp')
def clean_up_temp(job_id: str):
    try:
        logger.info('Starting to clean up assets...')
        clean_up_job = JobCleanUp(job_id)
        res = clean_up_job.temp()
        logger.info('Finished cleaning up assets...')
        return res
    except Exception as e:
        logger.error(e)
        return e