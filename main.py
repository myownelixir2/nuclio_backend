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



test_job_id_cloud = 'job_ids/2022-08-17-1660779803__1660779844-obtnscky11028TQWO.json'

os.environ["STORAGE_URL"] = 'https://s3.eu-central-1.wasabisys.com'
os.environ["STORAGE_KEY"] = 'WATDFANJ80ZDRZSQMVQP'
os.environ["STORAGE_SECRET"] = 'OdBo2cqzZ0hWKIbeAg49m9yS5l0iK9TP84HDlKi4'



#### STORAGE ####

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
        asset_paths = self.job_config.get_job_params()
        
        _check = JobTypeValidator.parse_obj({'job_type': self.asset_type})
        
        if _check.job_type == 'job_id_path':
            d_filter = ['local_path', 'cloud_path']
            d_paths = dict( ((key, job_paths[key]) for key in d_filter ) )
            return d_paths
        elif _check.job_type == 'processed_job_path':
            d_paths = {'cloud_path': job_paths['cloud_path_processed'],
            'local_path': job_paths['local_path_processed']}
            return d_paths
        else:
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


 
#### JOB CONFIG ####

class JobTypeValidator(BaseModel):
    job_type : Literal['job_id_path', 'processed_job_path', 'asset_path']
    
    @validator('job_type')
    def job_type_validator(cls, v):
        if v not in ['job_id_path', 'processed_job_path', 'asset_path']:
            raise ValueError('job_type must be either "single" or "batch"')
        return v
  

class JobConfigValidator(BaseModel):
    index_value: int = Field(..., ge=0, le=5)
    
    @validator('index_value')
    def item_validator(cls, v):
        if v not in [0,1,2,3,4,5]:
            raise ValueError('index must be between 0 and 5')
        return v

class JobConfig:
    def __init__(self, job_id, channel_index):
        self.job_id = job_id
        self.channel_index = channel_index
        
    def path_resolver(self):
        sanitized_job_id = self.job_id.split('/')[1].replace('.json','')
        local_path = f'temp/{sanitized_job_id}.json'
        local_path_processed = f'temp/sequences_{sanitized_job_id}.mp3'
        cloud_path_processed = f'sequences/{sanitized_job_id}.mp3'
        paths_dict = {'cloud_path': self.job_id, 
                'local_path': local_path, 
                'local_path_processed': local_path_processed, 
                'cloud_path_processed': cloud_path_processed}
        return paths_dict
    
    def __psuedo_json_to_dict(self):
        paths = self.path_resolver()
        with open(paths['local_path'],'r') as lst:
                json_psudo = json.load(lst)
                json_sanitized = re.sub(r'("\s*:\s*)undefined(\s*[,}])', '\\1null\\2', json_psudo[0])
                json_dict = json.loads(json_sanitized)
        return json_dict
    
    def get_job_params(self):
        job_id_dict = self.__psuedo_json_to_dict()
        
        _check_index = JobConfigValidator.parse_obj({'index_value': self.channel_index})
        
        params_dict = {'local_paths':job_id_dict["local_paths"][_check_index.index_value], 
                       'cloud_paths':job_id_dict["cloud_paths"][_check_index.index_value], 
                       'bpm':job_id_dict["bpm"][0], 
                       'scale_value':job_id_dict["scale_value"][0], 
                       'key_value':key_value, 
                       'rythm_config_list':job_id_dict["rythm_config_list"][_check_index.index_value], 
                       'pitch_temperature_knob_list':job_id_dict["pitch_temperature_knob_list"][_check_index.index_value]}
        
        return params_dict
     
#### SEQUENCE ENGINE ####

class SequenceConfigRefactor:
    def __init__(self, job_params):
        self.job_params = job_params
        
    def euclead_rhythm_generator(self) -> list:
        rhythm_config = self.job_params.get_job_params()['rythm_config_list']
        n : int = rhythm_config[0]
        k : int  = rhythm_config[1]
        data = [[1 if i < n else 0] for i in range(k)]
        while True:           
            k = k - n
            if k <= 1:
                break
            elif k < n:
                n, k = k, n
            for i in range(n):
                data[i] += data[-1]
                del data[-1]  
        return [x for y in data for x in y] 

    def get_note_sequence(self) -> list:
        
        scale_value = self.job_params.get_job_params()['scale_value']
        keynote = self.job_params.get_job_params()['key_value']
        
        notes_match_table = pd.read_pickle('notes_match_table.pkl')
        notes_sequence_raw = notes_match_table.query("scale_name==@scale_value & key==@keynote").filter(['notes'])
        
        notes_sequence_extracted_str = notes_sequence_raw["notes"].values[0].split(", ")
        notes_sequence_extracted_int = [int(i) for i in notes_sequence_extracted_str]
        notes_sequence_extracted_int_octave_down = [(i-12) for i in notes_sequence_extracted_int]
        
        notes_sequence_complete = notes_sequence_extracted_int_octave_down + notes_sequence_extracted_int 
        return notes_sequence_complete
     
    def grid_validate(self):
        """
        check if onset is equal 
        to total length of the sample track
        """
        bpm = self.job_params.get_job_params()['bpm']
        rhythm_config = self.job_params.get_job_params()['rythm_config_list']
        audio, sr = librosa.load(self.job_params.get_job_params()['local_paths'], sr=44100)
        
           
        one_bar = 60/bpm*4
        k=rhythm_config[1]
        pulse_length_samples = 44100*one_bar/k
        
        equal_to_total = True if (math.floor(len(audio)/pulse_length_samples)) <=1 else False
        grid_value = len(audio) \
            if equal_to_total \
                else math.floor(len(audio)/pulse_length_samples)*pulse_length_samples-pulse_length_samples
        return grid_value, pulse_length_samples
    
    
    def get_audio_frames_length(self) -> list:  
        pulse_sequence=self.euclead_rhythm_generator()
        __, pulse_length_samples = self.grid_validate()
        
        onsets_loc = [i for i, e in enumerate(pulse_sequence) if e == 1]
        onsets_loc_arr = np.array(onsets_loc)
        silence_loc_arr_temp = np.subtract(onsets_loc_arr[1:], 1)
        silence_loc_arr = np.append(silence_loc_arr_temp, len(pulse_sequence)-1)
        
        audio_frames_lengths = []
        for onsets, silence in zip(onsets_loc_arr, silence_loc_arr):
            #print(len(pulse_sequence[onsets:silence]))
            audio_frames_lengths.append((silence-onsets+1)*pulse_length_samples)
        return audio_frames_lengths
    
    def get_audio_frames_reps(self) -> list:
        grid_value, __ = self.grid_validate()
        audio_frames_lens = self.get_audio_frames_length()
        unique_audio_frame_lengths = np.unique(audio_frames_lens)
        
        audio_frame_rep_nr = []
        for i in range(len(unique_audio_frame_lengths)):
            reps_value = grid_value/unique_audio_frame_lengths[i]
            if reps_value < 1:
                my_reps = math.ceil(reps_value)
            else:
                my_reps = math.floor(reps_value)
                
            audio_frame_rep_nr.append(my_reps)
        return audio_frame_rep_nr
 

class SequenceAudioFrameSlicer:
    def __init__(self, sequence_config):
       
        self.sequence_config = sequence_config
        
          
    def get_audio_frame_sequence_list(self):
        
        audio_frames_lengths = self.sequence_config.get_audio_frames_length()
        audio_frames_reps = self.sequence_config.get_audio_frames_reps()  
        unique_audio_frames_lengths = np.unique(audio_frames_lengths)
        
        sequence_l = []
        for audio_lengths, audio_reps in zip(unique_audio_frames_lengths, audio_frames_reps): 
            test_stop_range = (audio_lengths*audio_reps)-audio_lengths
            
            stop_range = audio_lengths if test_stop_range==0 else test_stop_range
            step_range = audio_lengths
            sequence_l.append(np.arange(0, stop_range, step_range))
        return sequence_l
     
    def frames_list(self, individual_frames : list, unique_frame_length : float):
        sliced_frames = []
        
        audio, sr = librosa.load(self.sequence_config.job_params.get_job_params()['local_paths'], sr=44100)
        
        for frame in individual_frames:
            if unique_frame_length > len(audio):
                empty_array = np.zeros(int(unique_frame_length) - int(len(audio)))
                audio = np.append(audio, empty_array)
            
            sliced_frames.append(audio[int(frame):int(frame)+int(unique_frame_length)])
            #sliced_frames.append(self.sequence_config.audio[int(frame):int(frame)+int(unique_frame_length)])
        return sliced_frames   
        
    def get_audio_frames(self):
        sequence_l = self.get_audio_frame_sequence_list()
        audio_frames_lengths = self.sequence_config.get_audio_frames_length()
        unique_audio_frames_lengths = np.unique(audio_frames_lengths)
        audio_frames = [self.frames_list(x, y) for x, y in zip(sequence_l, unique_audio_frames_lengths)]
        return audio_frames

 
class SequenceEngine:
    def __init__(self, sequence_config, audio_frames):
        self.audio_frames = audio_frames
        self.sequence_config = sequence_config   

    def __validate_sequence(self, new_sequence):
        
        bpm = self.sequence_config.job_params.get_job_params()['bpm']
        
        one_bar = 60/bpm*4
        original_sample_len = round(44100*one_bar/1)
        
        new_sequence_unpacked = [item for sublist in new_sequence for item in sublist]
        new_sequence_len = len(new_sequence_unpacked)
        
        if new_sequence_len > original_sample_len:
            validated_sequence = new_sequence_unpacked[:original_sample_len]
        elif new_sequence_len < original_sample_len:
            empty_array = np.zeros(original_sample_len-new_sequence_len)
            
            validated_sequence = np.append(new_sequence_unpacked, empty_array)
        else:
            validated_sequence = new_sequence_unpacked
        return validated_sequence
    
    
    def __unpack_multi_level_list(self, my_list):
        unpacked_list = []
        for i in range(len(my_list)):
            for j in range(len(my_list[i])):
                unpacked_list.append(my_list[i][j])
                return unpacked_list
   
    def __pitch_shift(self, audio, pitch_shift):
        return librosa.effects.pitch_shift(audio, sr=44100, n_steps=pitch_shift)

  
    def __apply_pitch_shift(self, audio_frames : List[float], pitch_shift : Optional[list]):
        
        pitch_temperature = self.sequence_config.job_params.get_job_params()['pitch_temperature_knob_list'][0]
        
        if (random.random() > pitch_temperature/100) and (pitch_temperature != 0):
            pitch_shifted_audio_sequence = []
            for i in range(len(audio_frames)):
                
                pitch_shifted_audio_sequence.append(self.__pitch_shift(audio_frames[i], pitch_shift[i]))
            return pitch_shifted_audio_sequence
        else: 
            return audio_frames
    
    
    def generate_audio_sequence(self):
        
        my_audio_frames_lengths = self.sequence_config.get_audio_frames_length()
        my_audio_frames = self.audio_frames.get_audio_frames()
        my_audio_frames_lengths_sanitized = [int(item) for item in my_audio_frames_lengths]
        occurences_of_distinct_frames = Counter(my_audio_frames_lengths_sanitized)

        new_audio_sequence = []
        for i in range(len(my_audio_frames)):
            nr_elements_to_select = list(occurences_of_distinct_frames.values())[i]
            temp_sequence = random.choices(my_audio_frames[i], k=nr_elements_to_select)
            new_audio_sequence.append(temp_sequence)
            
        new_sequence_unlisted = [item for sublist in new_audio_sequence for item in sublist]
        note_sequence = self.sequence_config.get_note_sequence()
        note_sequence_updated = random.choices(note_sequence, k = len(new_sequence_unlisted))
        
        updated_new_audio_sequence = self.__apply_pitch_shift(new_sequence_unlisted, note_sequence_updated)
        validated_audio_sequence = self.__validate_sequence(updated_new_audio_sequence)
        return validated_audio_sequence
    
    def generate_audio_sequence_auto(self):
        audio_frames = self.audio_frames.get_audio_frames()
        audio_frames_lengths = self.sequence_config.get_audio_frames_length()
        unique_audio_frames_lengths = np.unique(audio_frames_lengths)
        
        audio_frames_sequence = []
        for i in range(len(audio_frames)):
            audio_frames_sequence.append(np.random.choice(audio_frames[i], int(unique_audio_frames_lengths[i]), replace=False))
        return self.__unpack_multi_level_list(audio_frames_sequence)

##### AUDIO ENGINE #####    

class AudioEngine:
    
    def __init__(self, validated_audio_sequence, file_loc, normalized = None):
        self.audio_sequence = validated_audio_sequence
        self.file_loc = file_loc
        self.normalized = normalized
        
    def read_audio(self):
        return librosa.load(self.file_loc, sr=44100)
    
    def save_to_wav(self):
        try:
            sf.write(self.file_loc, self.audio_sequence, 44100)
            #librosa.output.write_wav(self.file_loc, self.audio_sequence, sr=44100, norm=self.normalized)     
        except Exception as e:
            print("Error converting to wav", e)
            raise e
        
    def save_to_mp3(self):
        try:
            channels = 2 if (np.array(self.audio_sequence).ndim == 2 and np.array(self.audio_sequence).shape[1] == 2) else 1
            if self.normalized:  # normalized array - each item should be a float in [-1, 1)
                y = np.int16(self.audio_sequence * 2 ** 15)
            else:
                y = np.int16(self.audio_sequence)
            sequence = pydub.AudioSegment(y.tobytes(), frame_rate=sr, sample_width=2, channels=channels)
            sequence.export(self.file_loc, format="mp3", bitrate="128k")
        except Exception as e:
            print("Error converting to mp3", e)
            raise e
    


   
#WORKING ON THIS CLASS 
#initialize classes
import time
job_st = time.time()

job_params = JobConfig(test_job_id_cloud, 5)

job_et = time.time()

download_st = time.time()
StorageEngine(job_params,'job_id_path').get_object()
StorageEngine(job_params,'asset_path').get_object()
download_et = time.time()

processing_st = time.time()
new_config_test = SequenceConfigRefactor(job_params)
new_audio_frames = SequenceAudioFrameSlicer(new_config_test) 
validated_audio_sequence = SequenceEngine(new_config_test, new_audio_frames).generate_audio_sequence()
AudioEngine(validated_audio_sequence, job_params.path_resolver()['local_path_processed'], normalized = True).save_to_wav()
AudioEngine(validated_audio_sequence, job_params.path_resolver()['local_path_processed'], normalized = True).save_to_mp3()

processing_et = time.time()

upload_st = time.time()
StorageEngine(job_params,'processed_job_path').upload_object()

upload_et = time.time()

# get the execution time
job_elapsed_time = job_et - job_st
download_elapsed_time = download_et - download_st
processing_elapsed_time = processing_et - processing_st
upload_elapsed_time = upload_et - upload_st

print('Execution time for "JOB SPECS":', job_elapsed_time, 'seconds')
print('Execution time for "DOWNLOAD ASSETS":', download_elapsed_time, 'seconds')
print('Execution time for "PROCESS":', processing_elapsed_time, 'seconds')
print('Execution time for "UPLOAD ASSETS":', upload_elapsed_time, 'seconds')

np.array(validated_audio_sequence).ndim


#pydantic

with open('environment/data.json') as f:
    data = json.load(f)
    
print(data)

people = [Person(**person) for person in data]

people_as_json = [p.json() for p in people]

class Address(BaseModel):
    street: str
    country: str = "USA"
    zipcode: str 
    

class Person(BaseModel):
    first_name: str
    last_name: Optional[str]
    address: Optional[Address]
    favourite_numbers: List[int]
    

class DbSettings(BaseSettings):
    name: str
    ip_adress: str
    user: Optional[str]
    password: Optional[str]
    
db_setting = DbSettings(_env_file="environment/db.env", _env_file_encoding="utf-8") 



### DEBUG


bpm = job_params.get_job_params()['bpm']
rhythm_config = job_params.get_job_params()['rythm_config_list']
audio, sr = librosa.load(job_params.get_job_params()['local_paths'], sr=44100)
        
           
one_bar = 60/bpm*4
k=rhythm_config[1]
pulse_length_samples = 44100*one_bar/k

equal_to_total = True if (math.floor(len(audio)/pulse_length_samples)) <=1 else False
grid_value = len(audio) \
if equal_to_total \
    else math.floor(len(audio)/pulse_length_samples)*pulse_length_samples-pulse_length_samples
grid_value

    
def get_audio_frame_sequence_list(self):
        
    audio_frames_lengths = new_config_test.get_audio_frames_length()
    audio_frames_reps = new_config_test.get_audio_frames_reps()  
    unique_audio_frames_lengths = np.unique(audio_frames_lengths)
        
    sequence_l = []
    for audio_lengths, audio_reps in zip(unique_audio_frames_lengths, audio_frames_reps): 
        stop_range = (audio_lengths*audio_reps)-audio_lengths
        if stop_range == 0:
            stop_range = audio_lengths
        step_range = audio_lengths
        print(stop_range)
        sequence_l.append(np.arange(0, stop_range, step_range))
    return sequence_l
     
     
     
np.arange(0, 3835, 3834)
     
def frames_list(self, individual_frames : list, unique_frame_length : float):
    sliced_frames = []
        
    audio, sr = librosa.load(self.sequence_config.job_params.get_job_params()['local_paths'], sr=44100)
    for frame in individual_frames:
        sliced_frames.append(audio[int(frame):int(frame)+int(unique_frame_length)])
            #sliced_frames.append(self.sequence_config.audio[int(frame):int(frame)+int(unique_frame_length)])
    return sliced_frames   
        
def get_audio_frames(self):
    sequence_l = self.get_audio_frame_sequence_list()
    audio_frames_lengths = self.sequence_config.get_audio_frames_length()
    unique_audio_frames_lengths = np.unique(audio_frames_lengths)
    audio_frames = [self.frames_list(x, y) for x, y in zip(sequence_l, unique_audio_frames_lengths)]
    return audio_frames