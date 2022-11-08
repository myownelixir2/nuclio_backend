import pandas as pd
import os
import librosa
import soundfile as sf
import numpy as np
import pydub
from pydantic import BaseModel, Field, BaseSettings, validator, SecretStr
import boto3
from app.utils.utils import *


class StorageCreds(BaseSettings):
    endpoint_url: str = Field(..., env="STORAGE_URL")
    access_key_id: str = Field(..., env="STORAGE_KEY")
    secret_access_key: str = Field(..., env="STORAGE_SECRET")

    @validator('endpoint_url', 'access_key_id', 'secret_access_key')
    def creds_validator(cls, v):

        if v is None:
            raise ValueError(
                'endpoint_url, access_key_id and secret_access_key must be set')
        return v






class StorageEngine:

    def __init__(self, job_config, asset_type):
        self.job_config = job_config
        self.asset_type = asset_type

    def client_init(self):
        try:
            self.client = boto3.resource('s3',
                                        endpoint_url=StorageCreds().endpoint_url,
                                        aws_access_key_id=StorageCreds().access_key_id,
                                        aws_secret_access_key=StorageCreds().secret_access_key
                                        )
            return self.client
        except Exception as e:
            print(e)
            return True

    def __resolve_type(self):
        job_paths = self.job_config.path_resolver()

        _check = JobTypeValidator.parse_obj({'job_type': self.asset_type})

        if _check.job_type == 'job_id_path':
            d_filter = ['local_path', 'cloud_path']
            d_paths = dict(((key, job_paths[key]) for key in d_filter))
            return d_paths
        elif _check.job_type == 'processed_job_path':
            d_paths = {'cloud_path': job_paths['cloud_path_processed'],
                       'local_path': job_paths['local_path_processed']}
            return d_paths
        elif _check.job_type == 'mixdown_job_path':
            d_paths = {'cloud_path': job_paths['cloud_path_mixdown_mp3'],
                       'local_path': job_paths['local_path_mixdown_mp3']}
            return d_paths
        elif _check.job_type == 'mixdown_job_path_master':
            d_paths = {'cloud_path': job_paths['cloud_path_mixdown_mp3_master'],
                       'local_path': job_paths['local_path_mixdown_mp3_master']}
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