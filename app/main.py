from typing import Union
from fastapi import FastAPI
import os
import logging
from app.sequence_generator.generator import *
from app.storage.storage import *
from app.utils.utils import *



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
        StorageEngine(job_params,'job_id_path').get_object()
        return True
    except Exception as e:
        logger.error(e)
        return e
      
      
@app.post('/get_sequence')
def get_sequence(job_id: str, channel_index: int):
    try:
        logger.info('Starting to build sequence...')
        job = JobRunner(job_id, channel_index)
        res =  job.execute()
        processed_job_id = job.result(res)
        logger.info('Finished building sequence...')
        
        job.clean_up()
        logger.info('clean up done...')
        
        return processed_job_id
    except Exception as e:
        logger.error(e)
        return e
      

  