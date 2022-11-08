from dataclasses import dataclass
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
from pedalboard.io import AudioFile
import pedalboard
import random
import boto3
import glob
import sox
import time
from app.sequence_generator.generator import *


#fx_input = '2_4_1_6_1_5'
#index = '1_2_5_6_4_1'
#selective_mutism_switch= 'T'
##selective_mutism_value='0.3'
#cloud_job_id = 'sequences_job_id_path'
#vol = '99_99_98_99_99_99'
#channel_mute_params= 'T_T_T_T_T_T'




class FxParamsModel(BaseModel):
    job_id: str
    fx_input: str
    channel_index: str
    selective_mutism_switch: str
    vol: str
    channel_mute_params: str
    selective_mutism_value: str
    
    @validator('job_id')
    def job_id_validator(cls, v):
        if 'job_ids' not in  v:
            raise ValueError('Job id correct')
        return v

    @validator('fx_input')
    def digit_validator(cls, v):
        v = [x for x in v if x.isdigit()]
        if len(v) != 6:
            raise ValueError('fx input input is not correct')
        return v
    
    @validator('channel_index')
    def index_validator(cls, v):
        v = int(v)
        if v < 0 or v > 5:
            raise ValueError('index input is not correct')
        return v
    
    @validator('vol')
    def vol_validator(cls, v):
        v = v.split('_')
        v = [int(x) for x in v]
        if max(v) > 100 and len(v):
            raise ValueError('volume is not correct')
        return v
    
    @validator('channel_mute_params')
    def channel_mute_params_validator(cls, v):
        v = v.split('_')
        if len(v) != 6 and ('T' or 'F') not in v:
            raise ValueError('mute_params is not correct')
        return v
    
    
    @validator('selective_mutism_switch')
    def selective_mutism_switch_validator(cls, v):
        if v not in ['T','F']:
            raise ValueError('selective_mutism_switch is not correct')
        return v
    
    @validator('selective_mutism_value')
    def selective_mutism_value_validator(cls, v):
        v = float(v)
        if v > 1 or v < 0:
            raise ValueError('selective_mutism is not correct')
        return v
    
class MuteEngine:
    def __init__(self, mix_params, job_params):
        self.mix_params = mix_params
        self.job_params = job_params
     
    def __perc_to_pulse_mapper(self, seq_len, sequence):
        selective_mutism_value = self.mix_params.selective_mutism_value
        
        if selective_mutism_value == 0:
            return sequence
        else:
            slices = math.ceil(selective_mutism_value * seq_len)  
            #TODO: add better wight system     
            random_slices = random.sample(range(seq_len), slices)      
            for i in random_slices:
                sequence[i]=np.zeros(len(sequence[i]))
            return sequence
        
    def apply_selective_mutism(self):
        
        pickle_path = self.job_params.path_resolver()['local_path_processed_pkl']
        
        with open(pickle_path, 'rb') as f:
            my_sequence = pickle.load(f)
        
        my_sequence = self.__perc_to_pulse_mapper(len(my_sequence), my_sequence)
            
        return my_sequence
    
class VolEngine:
    def __init__(self, mix_params, job_params, my_sequence):
        self.mix_params = mix_params
        self.job_params = job_params
        self.pre_processed_sequence = my_sequence
    
     
    def apply_volume(self):
        
        channel_index = int(self.job_params.channel_index)
        bpm = self.job_params.get_job_params()['bpm']

        my_sequence_unpacked = SequenceEngine.validate_sequence(bpm,self.pre_processed_sequence)
     
        vol = self.mix_params.vol[channel_index]/100
        if vol == 0:
            my_sequence_vol_applied = np.zeros(len(my_sequence_unpacked))
        elif vol == 1:
            my_sequence_vol_applied = my_sequence_unpacked
        else:
            my_sequence_vol_applied = np.array(my_sequence_unpacked) * vol
             
        return my_sequence_vol_applied
    
    
class FxPedalBoardConfig(BaseModel):
    audio_fx : str
    
    @validator('audio_fx')
    def job_id_validator(cls, v):
        if v not in ['Bitcrush','Chorus','Delay','Flanger','Phaser','Reverb']:
            raise ValueError('not allowed FX input')
        return v
    

class FxPedalBoardEngine:
    def __init__(self, mix_params, job_params, my_sequence):
        self.mix_params = mix_params
        self.job_params = job_params
        self.my_sequence = my_sequence
       
    def apply_pedalboard_fx(self):
        
        fx_mapping = ['Bitcrush', 'Chorus', 'Delay', 'Flanger', 'Phaser', 'Reverb', 'Distortion']
        
        channel_index = int(self.job_params.channel_index)
        fx_input = self.mix_params.fx_input[channel_index]
        
        if fx_input == 'None':
            print('No FX applied')
            AudioEngine(self.my_sequence, self.job_params.path_resolver()['local_path_mixdown_pkl'], normalized = True).save_to_pkl()
            return True
        else:
            fx = fx_mapping[int(fx_input)]
        
            validated_fx = FxPedalBoardConfig(fx)
        
            pedalboard_fx = getattr(pedalboard, validated_fx)
            board = pedalboard.Pedalboard([pedalboard_fx])
        
            try:
                effected = board(self.my_sequence, 44100.0)
            except Exception as e:
                print(e)
                return False

            else:
                y_effected = np.int16(effected * 2 ** 15)
                AudioEngine(y_effected, self.job_params.path_resolver()['local_path_mixdown_pkl'], normalized = True).save_to_pkl()
                return True
            
    
        
    
class FxEngine:
    def __init__(self, mix_params, job_params, my_sequence):
        self.mix_params = mix_params
        self.job_params = job_params
        self.pre_processed_sequence = my_sequence
    
    def __convert_sequence_array_to_audio(self):
        channel_index = int(self.job_params.channel_index)
        fx_input = self.mix_params.fx_input[channel_index]
        
        if fx_input == 'None':
            output_file = 'local_path_mixdown_mp3'
        else:
            output_file = 'local_path_pre_mixdown_mp3'
        
        try:
            AudioEngine(self.pre_processed_sequence, self.job_params.path_resolver()[output_file], normalized = True).save_to_mp3()
            return True
        except Exception as e:
            print(e)    
            return False
    
    def __fx_dictionary(self):
        
        input_file = self.job_params.path_resolver()['local_path_pre_mixdown_mp3']
        output_file = self.job_params.path_resolver()['local_path_mixdown_mp3']
           
        fx_dict = {
            "reverb": f"ffmpeg -i {input_file} -i sox_utils/stalbans_a_binaural.wav -filter_complex '[0] [1] afir=dry=10:wet=10 [reverb]; [0] [reverb] amix=inputs=2:weights=10 5' {output_file}",
            "chorus": f"ffmpeg -i {input_file} -filter_complex 'chorus=0.5:0.9:50|60|70:0.3|0.22|0.3:0.25|0.4|0.3:2|2.3|1.3' {output_file}",
            "crusher": f"ffmpeg -i {input_file} -filter_complex 'acrusher=level_in=4:level_out=4:bits=8:mode=log:aa=1:mix=0.25' {output_file}",
            "echo_indoor": f"ffmpeg -i {input_file} -filter_complex 'aecho=0.8:0.9:40|50|70:0.4|0.3|0.2' {output_file}",
            "echo_outdoor": f"ffmpeg -i {input_file} -filter_complex 'aecho=0.8:0.9:1000|1500|2000:0.4|0.3|0.2' {output_file}",
            "robot_effect": f"ffmpeg -i {input_file} -filter_complex 'afftfilt=real='hypot(re,im)*sin(0)':imag='hypot(re,im)*cos(0)':win_size=512:overlap=0.75' {output_file}"
            
        }
        
        return fx_dict
        
    
    def apply_fx(self):
        
        channel_index = int(self.job_params.channel_index)
        fx_input = self.mix_params.fx_input[channel_index]
        
        self.__convert_sequence_array_to_audio()
        
        fx_dict = self.__fx_dictionary()
        
        if fx_input == 'None':
            print('No FX applied')
            return True
        else:
            output_file = self.job_params.path_resolver()['local_path_mixdown_mp3']
             # REMOVE IF FILE EXISTS
            if os.path.exists(output_file):
                    os.remove(output_file)
            try:
                
                fx_sox_cmd = list(fx_dict.values())[int(fx_input)]
                returned_value = os.system(fx_sox_cmd)  # returns the exit code in unix
                print('returned value:', returned_value)
                
                time_to_wait=2
                time_counter=0
                
                while not os.path.exists(output_file):
                    time.sleep(0.1)
                    time_counter += 0.1
                    if time_counter > time_to_wait:break
                
                if os.path.exists(output_file):
                    print('FX applied')
                    return True
                    
                else:
                    return False
            except Exception as e:
                print(e)
                return False


class FxRunner:
    def __init__(self, mix_params, job_id, channel_index, random_id):
        self.mix_params = mix_params
        self.job_id = job_id
        self.channel_index = channel_index
        self.random_id = random_id       
    
    def clean_up(self):

        try:
            #StorageEngine(self.job_params,'job_id_path').delete_local_object()
            StorageEngine(self.job_params,'mixdown_job_path_pkl').delete_local_object()
            StorageEngine(self.job_params,'mixdown_job_path').delete_local_object()
        except Exception as e:
            print(e)
        
    
    def execute(self):
        self.job_params = JobConfig(self.job_id, self.channel_index, self.random_id)
        
        try:
            
            sequence_mute_applied = MuteEngine(self.mix_params, self.job_params).apply_selective_mutism()
            sequence_vol_applied = VolEngine(self.mix_params, self.job_params, sequence_mute_applied).apply_volume()
            sequence_ready = FxPedalBoardEngine(self.mix_params, self.job_params, sequence_vol_applied).apply_pedalboard_fx()
            #sequence_ready = FxEngine(self.mix_params, self.job_params, sequence_vol_applied).apply_fx()
            
            if sequence_ready:
                print('Sequence ready')
                #StorageEngine(self.job_params,'mixdown_job_path').upload_object()
                return True
            else:
                print('Sequence not ready')
                return False
            
        except Exception as e:
            print(e)

 
     
    
    
     