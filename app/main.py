from typing import Union
from fastapi import FastAPI
import os
from app.sequence_generator.generator import *
import logging

# logger config
logger = logging.getLogger(__name__)


app = FastAPI()
 
@app.get('/')
def home():
  return os.getcwd()
   
@app.post('/get_sequence')
async def get_sequence(job_id: str, channel_index: int):
    try:
        logger.info('Starting to build sequence...')
        job = JobRunner(job_id, channel_index)
        res = job.execute()
        processed_job_id = job.result(res)
        logger.info('Finished building sequence...')
        return processed_job_id
    except Exception as e:
        logger.error(e)
        return e
    
  