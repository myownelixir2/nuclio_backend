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
from app.storage.storage import *

class MixEngine:
    def __init__(self, mix_params, job_params):
        self.mix_params = mix_params
        self.job_params = job_params
        
    def mix_sequences(self):
        random_id = self.job_params.random_id
        
        current_sequences_list = glob.glob(f'temp/mixdown_{random_id}_*.mp3')
        
        input_files = '-i ' + ' -i '.join(current_sequences_list)
        output_file = self.job_params.path_resolver()['local_path_mixdown_mp3_master']
        
        mix_cmd = f"ffmpeg -y {input_files} -filter_complex '[0:0][1:0] amix=inputs=2:duration=longest' -c:a libmp3lame {output_file}"
        
        try:
            returned_value = os.system(mix_cmd)  # returns the exit code in unix
            print('returned value:', returned_value)
                
            if os.path.exists(output_file):
                return True
                print('sequences mixed')
            else:
                return False
        except Exception as e:
            print(e)
            return False
        