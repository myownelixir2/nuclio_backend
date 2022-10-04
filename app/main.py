from typing import Union
from fastapi import FastAPI
import os
from app.helper.listener_utils import *
import logging

# logger config
logger = logging.getLogger(__name__)


app = FastAPI()
 
@app.get('/')
def home():
  return os.getcwd()
   
@app.post('/get_snapshot')
def get_snapshot():
  build_snapshot()
  logger.info('Snapshot build...')
  ts=int(time.time())
  dest_file=str(ts) + '_' + 'database_snapshot.csv'
  upload_object('database_snapshot.csv', dest_file)
  logger.info('Snapshot uploaded...')
  status_='succes'
  return status_