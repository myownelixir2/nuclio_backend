import json
import re
from turtle import st
import pandas as pd
import csv
import os
import pickle
import librosa
import soundfile as sf
import numpy as np
import math
import pydub
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, BaseSettings, validator, SecretStr
from collections import Counter
import random
import boto3
import glob

class StorageCreds(BaseSettings):
    endpoint_url : str = Field(..., env="STORAGE_URL")
    access_key_id : str = Field(..., env="STORAGE_KEY")
    secret_access_key : str = Field(..., env="STORAGE_SECRET")


class StorageEngine:
    
    def __init__(self, job_config, asset_type):
        self.job_config = job_config
        self.asset_type = asset_type
        
    
    def client_init(self):
        self.client = boto3.resource('s3',
            endpoint_url=StorageCreds().endpoint_url,
            aws_access_key_id=StorageCreds().access_key_id,
            aws_secret_access_key=StorageCreds().secret_access_key
        )
        return self.client
     
    def __resolve_type(self):
        job_paths = self.job_config.path_resolver()
        
        _check = JobTypeValidator.parse_obj({'job_type': self.asset_type})
        
        if _check.job_type == 'job_id_path':
            d_filter = ['local_path', 'cloud_path']
            d_paths = dict( ((key, job_paths[key]) for key in d_filter ) )
            return d_paths
        elif _check.job_type == 'processed_job_path':
            d_paths = {'cloud_path': job_paths['cloud_path_processed'],
            'local_path': job_paths['local_path_processed']}
            return d_paths
        elif _check.job_type == 'mixdown_job_path':
            d_paths = {'cloud_path': job_paths['cloud_path_mixdown_mp3'],
            'local_path': job_paths['local_path_mixdown_mp3']}
            return d_paths
        elif _check.job_type == 'mixdown_job_path_pkl':
            d_paths = {'cloud_path': job_paths['cloud_path_mixdown_pkl'],
            'local_path': job_paths['local_path_mixdown_pkl']}
            return d_paths
        else:
            asset_paths = self.job_config.get_job_params()
            d_paths = {'cloud_path': asset_paths['cloud_paths'],
            'local_path': asset_paths['local_paths']}
            return d_paths
            
       
    def get_object(self):
        try:
            client = self.client_init()
            bucket = client.Bucket('sample-dump')
            _type = self.__resolve_type()
            bucket.download_file(_type['cloud_path'], _type['local_path'])
            return True
        except Exception as e:
            print(e)
            return False
    
    def delete_local_object(self):
        try:
            _type = self.__resolve_type()
            os.remove(_type['local_path'])
            return True
        except Exception as e:
            print(e)
            return False
    
    def upload_object(self):
        try:
            client = self.client_init()
            bucket = client.Bucket('sample-dump')
            _type = self.__resolve_type()
            bucket.upload_file(_type['local_path'], _type['cloud_path'])
            return True
        except Exception as e:
            print(e)
            return False


 