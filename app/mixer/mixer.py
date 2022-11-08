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
from app.post_fx.post_fx import *

class MixEngine:
    def __init__(self, job_params):
        self.job_params = job_params
        
    def mix_sequences(self):
        random_id = self.job_params.random_id
        
        current_sequences_list = glob.glob(f'temp/mixdown_{random_id}_*.mp3')
        
        input_files = '-i ' + ' -i '.join(current_sequences_list)
        output_file = self.job_params.path_resolver()['local_path_mixdown_mp3_master']
        
        mix_cmd = f"ffmpeg -y {input_files} -filter_complex '[0:0][1:0] amix=inputs=6:duration=longest' -c:a libmp3lame {output_file}"
        
        try:
            returned_value = os.system(mix_cmd)  # returns the exit code in unix
            print('returned value:', returned_value)
                
            if os.path.exists(output_file):
                print('sequences mixed')
                return True
            else:
                print('Something went wrong')
                return False
        except Exception as e:
            print(e)
            return False


class MixRunner:
    def __init__(self, job_id, random_id,):
        self.job_id = job_id
        self.random_id = random_id
        
    def clean_up(self):
        try:
            current_sequences_list = glob.glob(f'temp/*')
            [os.remove(f) for f in current_sequences_list]

            return True
        except Exception as e:
            print(e)
            return False 
        
    def execute(self):
        try:
            job_params = JobConfig(self.job_id, 0, self.random_id)
            mix_ready = MixEngine(job_params).mix_sequences()
            if mix_ready:
                StorageEngine(job_params,'mixdown_job_path_master').upload_object()
            else:
                print('something went wrong')
            
            return True
        except Exception as e:
            print(e)
            return False

