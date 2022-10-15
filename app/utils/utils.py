import json
import re
import pandas as pd
import librosa
import soundfile as sf
import numpy as np
import pydub
from typing import Literal
from pydantic import BaseModel, Field, BaseSettings, validator, SecretStr
import boto3


class JobTypeValidator(BaseModel):
    job_type: Literal['job_id_path', 'processed_job_path',
                      'asset_path', 'mixdown_job_path', 'mixdown_job_path_pkl']

    @validator('job_type')
    def job_type_validator(cls, v):
        if v not in ['job_id_path', 'processed_job_path', 'asset_path', 'mixdown_job_path', 'mixdown_job_path_pkl']:
            raise ValueError(
                'job_type must be either "job_id_path", "processed_job_path", "asset_path", "mixdown_job_path" or "mixdown_job_path_pkl"')
        return v


class JobConfigValidator(BaseModel):
    index_value: int = Field(..., ge=0, le=5)

    @validator('index_value')
    def item_validator(cls, v):
        if v not in [0, 1, 2, 3, 4, 5]:
            raise ValueError('index must be between 0 and 5')
        return v


class JobConfig:
    def __init__(self, job_id: str, channel_index: int, random_id: str):
        self.job_id = job_id
        self.channel_index = channel_index
        self.random_id = random_id

    def path_resolver(self):

        #random_id = ''.join((random.choice('abcdxyzpqr') for i in range(8)))

        sanitized_job_id = self.job_id.split('/')[1].replace('.json', '')
        local_path = f'temp/{sanitized_job_id}.json'

        local_path_processed = f'temp/sequences_{sanitized_job_id}_{self.channel_index}.mp3'
        cloud_path_processed = f'sequences/{sanitized_job_id}_{self.channel_index}.mp3'

        local_path_processed_pkl = f'temp/sequences_{sanitized_job_id}_{self.channel_index}.pkl'
        cloud_path_processed_pkl = f'sequences/{sanitized_job_id}_{self.channel_index}.pkl'

        local_path_mixdown = f'temp/mixdown_{self.random_id}_{sanitized_job_id}'
        cloud_path_mixdown = f'mixdown/mixdown_{self.random_id}_{sanitized_job_id}'
        
        local_path_pre_mixdown_mp3 = f'temp/pre_mixdown_{self.random_id}_{sanitized_job_id}__{self.channel_index}.mp3'

        local_path_mixdown_mp3 = f'{local_path_mixdown}_{self.channel_index}.mp3'
        cloud_path_mixdown_mp3 = f'{cloud_path_mixdown}_{self.channel_index}.mp3'
        
        local_path_mixdown_mp3_master = f'{local_path_mixdown}_master.mp3'
        cloud_path_mixdown_mp3_master = f'{cloud_path_mixdown}_master.mp3'

        paths_dict = {'cloud_path': self.job_id,
                      'local_path': local_path,
                      'local_path_processed': local_path_processed,
                      'cloud_path_processed': cloud_path_processed,
                      'local_path_processed_pkl': local_path_processed_pkl,
                      'cloud_path_processed_pkl': cloud_path_processed_pkl,
                      'local_path_pre_mixdown_mp3': local_path_pre_mixdown_mp3,
                      'local_path_mixdown_mp3': local_path_mixdown_mp3,
                      'cloud_path_mixdown_mp3': cloud_path_mixdown_mp3,
                      'local_path_mixdown_mp3_master': local_path_mixdown_mp3_master,
                      'cloud_path_mixdown_mp3_master': cloud_path_mixdown_mp3_master,
                      'sanitized_job_id': sanitized_job_id}
        return paths_dict

    def __psuedo_json_to_dict(self):
        paths = self.path_resolver()
        with open(paths['local_path'], 'r') as lst:
            json_psudo = json.load(lst)
            json_sanitized = re.sub(
                r'("\s*:\s*)undefined(\s*[,}])', '\\1null\\2', json_psudo[0])
            json_dict = json.loads(json_sanitized)
        return json_dict

    def get_job_params(self):
        job_id_dict = self.__psuedo_json_to_dict()

        _check_index = JobConfigValidator.parse_obj(
            {'index_value': self.channel_index})

        params_dict = {'local_paths': job_id_dict["local_paths"][_check_index.index_value],
                       'cloud_paths': job_id_dict["cloud_paths"][_check_index.index_value],
                       'bpm': job_id_dict["bpm"][0],
                       'scale_value': job_id_dict["scale_value"][0],
                       'key_value': job_id_dict["key_value"][0],
                       'rythm_config_list': job_id_dict["rythm_config_list"][_check_index.index_value],
                       'pitch_temperature_knob_list': job_id_dict["pitch_temperature_knob_list"][_check_index.index_value]}

        return params_dict
