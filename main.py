import json
import re
from turtle import st
import pandas as pd
import csv
import pickle
import librosa
import soundfile as sf
import numpy as np
import math
from pydub import AudioSegment
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, BaseSettings, validator, SecretStr
from collections import Counter
import random
import boto3

def psuedo_json_to_dict(file_path):   
    with open(file_path,'r') as lst:
            json_psudo = json.load(lst)
            json_sanitized = re.sub(r'("\s*:\s*)undefined(\s*[,}])', '\\1null\\2', json_psudo[0])
            json_dict = json.loads(json_sanitized)
    return json_dict
        



job_id_dict = psuedo_json_to_dict('test_job_id2.json')     



local_paths = job_id_dict["local_paths"]
cloud_paths = job_id_dict["cloud_paths"]
bpm = job_id_dict["bpm"][0]
scale_value = job_id_dict["scale_value"][0]
key_value = job_id_dict["key_value"][0]
rythm_config_list = job_id_dict["rythm_config_list"]
pitch_temperature_knob_list = job_id_dict["pitch_temperature_knob_list"]

notes_match_table = pd.read_csv('MASTER_KEY_TO_NOTE_SEQUENCE.csv', delimiter=';')
#notes_match_table.to_pickle('notes_match_table.pkl')    #to save the dataframe, df to 123.pkl
list(notes_match_table)
notes_match_table.filter()
scale_value='major'
keynote='F Major'

notes_match_table.columns.values


sample_mp3 = '/Volumes/DATA VAULT/SAMPLE_DB_STAGING/loop__other/PITCH_B__BPM_125__Drums_Loops_LA_Drums_01_125.mp3'


audio, sr = librosa.load(sample_mp3,sr=44100)
len(audio)



class SerializeInput:    
    def __init__(self, file_path, channel_index):
        self.file_path : str = file_path 
        self.channel_index  : int = channel_index


    def psuedo_json_to_dict(self):   
        with open(self.file_path,'r') as lst:
                json_psudo = json.load(lst)
                json_sanitized = re.sub(r'("\s*:\s*)undefined(\s*[,}])', '\\1null\\2', json_psudo[0])
                json_dict = json.loads(json_sanitized)
        return json_dict
    
    def get_job_params(self):
        job_id_dict = self.psuedo_json_to_dict()
        index = self.channel_index
        
        params_dict = {'local_paths':job_id_dict["local_paths"][index], 
                       'cloud_paths':job_id_dict["cloud_paths"][index], 
                       'bpm':job_id_dict["bpm"][0], 
                       'scale_value':job_id_dict["scale_value"][0], 
                       'key_value':key_value, 
                       'rythm_config_list':job_id_dict["rythm_config_list"][index], 
                       'pitch_temperature_knob_list':job_id_dict["pitch_temperature_knob_list"][index]}
        
        return params_dict
    
test_serialized = SerializeInput('test_job_id2.json', 2).get_job_params()

class StorageCreds(BaseSettings):
    endpoint_url : str = Field(..., env="STORAGE_URL")
    access_key_id : str = Field(..., env="STORAGE_KEY")
    secret_access_key : str = Field(..., env="STORAGE_SECRET")
 
 
   

class JobConfig:
    def __init__(self, job_id):
        self.job_id = job_id
        
    def path_resolver(self):
        sanitized_job_id = self.job_id.replace('job_ids/','')
        local_path = f'temp/{sanitized_job_id}'
        local_path_processed = f'temp/sequences_{sanitized_job_id}'
        cloud_path_processed = f'sequences/{sanitized_job_id}'
        paths_dict = {'cloud_job_id': self.job_id, 
                'local_path': local_path, 
                'local_path_processed': local_path_processed, 
                'cloud_path_processed': cloud_path_processed}
        return paths_dict
            


job_config = JobConfig('job_ids/1234567890').path_resolver()




class StorageEngine:
    
    def __init__(self, job_id):
        self.job_id = job_id
  
    
    def initiatialize_client(self):
        self.client = boto3.resource('s3',
            endpoint_url=StorageCreds().endpoint_url,
            aws_access_key_id=StorageCreds().access_key_id,
            aws_secret_access_key=StorageCreds().secret_access_key
        )
        return self.client
        
       
    def get_object(self):
        try:
            client = self.initiatialize_client()
            bucket = client.Bucket('sample-dump')
            job_config = JobConfig(self.job_id).path_resolver()
            bucket.download_file(job_config['cloud_path_processed'], job_config['local_path_processed'])
            return True
        except Exception as e:
            print(e)
            return False
    
    def upload_object(self):
        try:
            client = self.initiatialize_client()
            bucket = client.Bucket('sample-dump')
            job_config = JobConfig(self.job_id).path_resolver()
            bucket.upload_file(job_config['local_path_processed'], job_config['cloud_path_processed'])
            return True
        except Exception as e:
            print(e)
            return False

        
class StorageAccessError():
    pass

class SequenceConfigError():
    pass




class SequenceConfig:
    def __init__(self, audio, rhythm_config, pitch_temperature, bpm, scale_value, keynote):
        self.audio = audio 
        self.rhythm_config : list = rhythm_config
        self.pitch_temperature : int = pitch_temperature
        self.bpm : int = bpm
        self.scale_value: str = scale_value
        self.keynote: str = keynote 
        
    def euclead_rhythm_generator(self) -> list:
        n : int = self.rhythm_config[0]
        k : int  = self.rhythm_config[1]
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
        notes_match_table = pd.read_pickle('notes_match_table.pkl')
        notes_sequence_raw = notes_match_table.query("scale_name==@self.scale_value & key==@self.keynote").filter(['notes'])
        
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
        one_bar = 60/self.bpm*4
        k=self.rhythm_config[1]
        pulse_length_samples = 44100*one_bar/k
        
        equal_to_total = True if (math.floor(len(self.audio)/pulse_length_samples)) <=1 else False
        grid_value = len(self.audio) \
            if equal_to_total \
                else math.floor(len(self.audio)/pulse_length_samples)*pulse_length_samples-pulse_length_samples
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
            audio_frame_rep_nr.append(grid_value/unique_audio_frame_lengths[i])
        return audio_frame_rep_nr
 

class SequenceAudioFrameSlicer:
    def __init__(self, sequence_config):
        #self.audio = audio
        self.sequence_config = sequence_config
        
          
    def get_audio_frame_sequence_list(self):
        audio_frames_lengths = self.sequence_config.get_audio_frames_length()
        audio_frames_reps = self.sequence_config.get_audio_frames_reps()  
        unique_audio_frames_lengths = np.unique(audio_frames_lengths)
        
        sequence_l = []
        for audio_lengths, audio_reps in zip(unique_audio_frames_lengths, audio_frames_reps): 
            stop_range = (audio_lengths*audio_reps)-audio_lengths
            step_range = audio_lengths
            sequence_l.append(np.arange(0, stop_range, step_range))
        return sequence_l
     
    def frames_list(self, individual_frames : list, unique_frame_length : float):
        sliced_frames = []
        for frame in individual_frames:
            sliced_frames.append(self.sequence_config.audio[int(frame):int(frame)+int(unique_frame_length)])
        return sliced_frames   
        
    def get_audio_frames(self):
        sequence_l = self.get_audio_frame_sequence_list()
        audio_frames_lengths = self.sequence_config.get_audio_frames_length()
        unique_audio_frames_lengths = np.unique(audio_frames_lengths)
        audio_frames = [self.frames_list(x, y) for x, y in zip(sequence_l, unique_audio_frames_lengths)]
        return audio_frames

 
class AudioFrameSlicer(SequenceConfig):
    def __init__(self, audio, rhythm_config, pitch_temperature, bpm, scale_value, keynote):
        super().__init__(audio, rhythm_config, pitch_temperature, bpm, scale_value, keynote)    
    
    def get_audio_frame_sequence_list(self):
        audio_frames_lengths = super().get_audio_frames_length()
        audio_frames_reps = super().get_audio_frames_reps()
        unique_audio_frames_lengths = np.unique(audio_frames_lengths)
        
        sequence_l = []
        for audio_lengths, audio_reps in zip(unique_audio_frames_lengths, audio_frames_reps): 
            stop_range = (audio_lengths*audio_reps)-audio_lengths
            step_range = audio_lengths
            sequence_l.append(np.arange(0, stop_range, step_range))
        return sequence_l
     
    def frames_list(self, individual_frames : list, unique_frame_length : float):
            sliced_frames = []
            for frame in individual_frames:
                sliced_frames.append(self.audio[int(frame):int(frame)+int(unique_frame_length)])
            return sliced_frames   
        
    def get_audio_frames(self):
        sequence_l = self.get_audio_frame_sequence_list()
        audio_frames_lengths = super().get_audio_frames_length()
        unique_audio_frames_lengths = np.unique(audio_frames_lengths)
        audio_frames = [self.frames_list(x, y) for x, y in zip(sequence_l, unique_audio_frames_lengths)]
        return audio_frames
     
 
class SequenceEngine:
    def __init__(self, sequence_config, audio_frames):
        self.audio_frames = audio_frames
        self.sequence_config = sequence_config   

    def __validate_sequence(self, new_sequence):
        one_bar = 60/self.sequence_config.bpm*4
        original_sample_len = round(44100*one_bar/1)
        
        new_sequence_unpacked = [item for sublist in new_sequence for item in sublist]
        new_sequence_len = len(new_sequence_unpacked)
        
        if new_sequence_len > original_sample_len:
            validated_sequence = new_sequence_unpacked[:original_sample_len]
        elif new_sequence_len < original_sample_len:
            empty_array = np.zeros(original_sample_len-new_sequence_len)
            
            validated_sequence = np.append(new_sequence_unpacked, empty_array)
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
      
        if (random.random() > self.sequence_config.pitch_temperature[0]/100) and (self.sequence_config.pitch_temperature != 0):
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
    
    
    
#WORKING ON THIS CLASS 
#initialize classes
new_config = SequenceConfig(audio, rythm_config_list[0], pitch_temperature_knob_list[0], bpm, scale_value, key_value)      

new_audio_frames = SequenceAudioFrameSlicer(new_config) 

validated_audio_sequence = SequenceEngine(new_config, new_audio_frames).generate_audio_sequence()

sf.write('test.wav', validated_audio_sequence, 44100)

len(validated_audio_sequence)





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

