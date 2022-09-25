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
from pydantic import BaseModel, Field, BaseSettings, validator
from collections import Counter
import random

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


      #def output_paths(self):
    #    raw_file_output = 0
    #    master_file_output = 0
    #    print() 
     #total_length_samples = round(44100*one_bar/1)


audio, sr = librosa.load(sample_mp3,sr=44100)
len(audio)



def Euclid(n, k):
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

class StorageAccess():
    pass

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
    def __init__(self, audio, sequence_config):
        self.audio = audio
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
            sliced_frames.append(self.audio[int(frame):int(frame)+int(unique_frame_length)])
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
    def __init__(self, audio, sequence_config, audio_frames, pitch_temperature):
        self.audio = audio
        self.audio_frames = audio_frames
        self.pitch_temperature = pitch_temperature
        self.sequence_config = sequence_config
        
    #TODO
    def __validate_sequence(self):
        sequence = self.sequence_config.sequence
        sequence_len = len(sequence)
        audio_frames_len = len(self.audio_frames)
        if sequence_len > audio_frames_len:
            sequence = sequence[:audio_frames_len]
        elif sequence_len < audio_frames_len:
            sequence = sequence*(math.floor(audio_frames_len/sequence_len))
        return sequence
    
    def __unpack_multi_level_list(self, my_list):
        unpacked_list = []
        for i in range(len(my_list)):
            for j in range(len(my_list[i])):
                unpacked_list.append(my_list[i][j])
                return unpacked_list
   
    def __pitch_shift(self, audio, pitch_shift):
        return librosa.effects.pitch_shift(audio, sr=44100, n_steps=pitch_shift)

    #TODO
    def __apply_pitch_shift(self, audio_frames : List[float], pitch_shift : Optional[list]):
        #sequence = self.__validate_sequence()
        #audio_sequence = self.generate_audio_sequence()
        if (random.random() > self.pitch_temperature) and (self.pitch_temperature != 0):
            pitch_shifted_audio_sequence = []
            for i in range(len(audio_frames)):
                pitch_shifted_audio_sequence.append(self.__pitch_shift(audio_frames[i], pitch_shift[i]))
            return pitch_shifted_audio_sequence
        else: 
            return audio_frames
    #TODO
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
        #return self.__unpack_multi_level_list(new_sequence)
        new_sequence_unlisted =  [item for sublist in new_audio_sequence for item in sublist]
        note_sequence = self.sequence_config.get_note_sequence()
        
        updated_new_audio_sequence = self.__apply_pitch_shift(new_sequence_unlisted, note_sequence)
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

new_audio_frames = SequenceAudioFrameSlicer(audio, new_config) 


my_audio_frames_lengths = new_config.get_audio_frames_length()
my_audio_frames = new_audio_frames.get_audio_frames()


my_audio_frames_lengths_sanitized = [int(item) for item in my_audio_frames_lengths]
occurences_of_distinct_frames = Counter(my_audio_frames_lengths_sanitized)

new_sequence = []
for i in range(len(my_audio_frames)):

    nr_elements_to_select = list(occurences_of_distinct_frames.values())[i]
    temp_sequence = random.choices(my_audio_frames[i], k=nr_elements_to_select)
    new_sequence.append(temp_sequence)

len(new_sequence[1]) 
    
def multi_level_list(my_list):
    unpacked_list = []
    for i in range(len(my_list)):
        for j in range(len(my_list[i])):
            unpacked_list.append(my_list[i][j])
            return unpacked_list

multi_level_list(new_sequence)

new_sequence_frames = [item for sublist in new_sequence for item in sublist]







len(my_audio_frames[1])

list(np.concatenate(my_audio_frames).flat)
    
class GeneratorError():
    pass       
        

class wave_reader():
    pass

def generate_random_string():
    print()

def get_note_sequence():
    print()
    
def get_sequence_config():
    print()

def get_sequence_grid_coord():
    print()

def generate_sequqnce_by_track():
    print()


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

