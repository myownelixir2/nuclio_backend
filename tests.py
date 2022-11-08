import json
import re
from urllib import response
import pandas as pd
import librosa
import soundfile as sf
import numpy as np
import pydub
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, BaseSettings, validator, SecretStr, ValidationError
import boto3
import os
import pickle
import math
import random
import glob
import sox
import time
from pathlib import Path

class JobTypeValidator(BaseModel):
    job_type: Literal['job_id_path', 'processed_job_path',
                      'asset_path', 'mixdown_job_path', 'mixdown_job_path_pkl']

    @validator('job_type')
    def job_type_validator(cls, v):
        if v not in ['job_id_path', 'processed_job_path', 'asset_path', 'mixdown_job_path', 'mixdown_job_path_master', 'mixdown_job_path_pkl']:
            raise ValueError(
                'job_type must be either "job_id_path", "processed_job_path", "asset_path", "mixdown_job_path" or "mixdown_job_path_pkl" or "mixdown_job_path_master"')
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
            return False

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
        if not v.isdigit():
            raise ValueError('index input is not a digit')
        else:
            if int(v) > 5 or int(v) < 0:
                raise ValueError('index input is out of scope, should be 0-5')
        return int(v)
    
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
        
        channel_index = self.job_params.channel_index
        bpm = self.job_params.get_job_params()['bpm']

        my_sequence_unpacked = SequenceEngine.validate_sequence(bpm,self.pre_processed_sequence )
    
        vol = self.mix_params.vol[int(channel_index)]/100
        if vol == 0:
            my_sequence_vol_applied = np.zeros(len(my_sequence_unpacked))
        elif vol == 1:
            my_sequence_vol_applied = my_sequence_unpacked
        else:
            my_sequence_vol_applied = np.array(my_sequence_unpacked) * vol
            
            
        return my_sequence_vol_applied
    
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
                    print('FX failed')
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
            sequence_ready = FxEngine(self.mix_params, self.job_params, sequence_vol_applied).apply_fx()
            
            if sequence_ready:
                print('Sequence ready')
                StorageEngine(self.job_params,'mixdown_job_path').upload_object()
                return True
            else:
                print('Sequence not ready')
                return False
            
        except Exception as e:
            print(e)

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
        
        notes_match_table = pd.read_pickle('app/sequence_generator/notes_match_table.pkl')
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
    
    @staticmethod
    def validate_sequence(bpm, new_sequence):  
        
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
        
        bpm = self.sequence_config.job_params.get_job_params()['bpm']
        
        updated_new_audio_sequence = self.__apply_pitch_shift(new_sequence_unlisted, note_sequence_updated)
        validated_audio_sequence = self.validate_sequence(bpm, updated_new_audio_sequence)
        
        return validated_audio_sequence, updated_new_audio_sequence
    
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
    
    def save_to_pkl(self):
        try:
            my_file = self.file_loc
            my_pkl = my_file.replace('.mp3', '.pkl')
            with open(my_pkl,"wb") as f:
                pickle.dump(self.audio_sequence, f)
           
        except Exception as e:
            print(e)
            print('Could not save to pkl')
            
    
    def save_to_wav(self):
        try:
            sf.write(self.file_loc, self.audio_sequence, 44100)
            #librosa.output.write_wav(self.file_loc, self.audio_sequence, sr=44100, norm=self.normalized)     
        except Exception as e:
            print("Error converting to wav", e)
            raise e

    def save_to_mp3(self):
        try:
            audio_seq_array = np.array(self.audio_sequence)
            channels = 2 if (audio_seq_array.ndim == 2 and audio_seq_array.shape[1] == 2) else 1
            if self.normalized:  # normalized array - each item should be a float in [-1, 1)
                y = np.int16(audio_seq_array * 2 ** 15)
            else:
                y = np.int16(audio_seq_array)
            sequence = pydub.AudioSegment(y.tobytes(), frame_rate=44100, sample_width=2, channels=channels)
            sequence.export(self.file_loc, format="mp3", bitrate="128k")
        except Exception as e:
            print("Error converting to mp3", e)
            raise e
    
#### RUN JOB ####

class JobRunner:
    def __init__(self, job_id, channel_index, random_id):
        self.job_id = job_id
        self.channel_index = channel_index
        self.random_id = random_id
       
    def get_assets(self):
        try:
            StorageEngine(self.job_params,'job_id_path').get_object()
            StorageEngine(self.job_params,'asset_path').get_object()
        except Exception as e:
            print(e)
    
    def validate(self):
        try:
            
            new_config_test = SequenceConfigRefactor(self.job_params)
            new_audio_frames = SequenceAudioFrameSlicer(new_config_test) 
            validated_audio_sequence, audio_sequence = SequenceEngine(new_config_test, new_audio_frames).generate_audio_sequence()
            
            return validated_audio_sequence, audio_sequence
        except Exception as e:
            print(e)  
            return False 
    
    def result(self, result):
        try:
            if result == True:
                cloud_path = self.job_params.path_resolver()['cloud_path_processed']
                #TODO check if file exists
                return cloud_path
            else:
                return print('Job failed')
        except Exception as e:
            print(e)
            return print('Error')
    
    def clean_up(self):
        self.job_params = JobConfig(self.job_id, self.channel_index, self.random_id)
        
        try:
            #StorageEngine(self.job_params,'job_id_path').delete_local_object()
            StorageEngine(self.job_params,'asset_path').delete_local_object()
            StorageEngine(self.job_params,'processed_job_path').delete_local_object()
        except Exception as e:
            print(e)
    
    def execute(self):
        self.job_params = JobConfig(self.job_id, self.channel_index, self.random_id)
        
        self.get_assets()
        validated_audio, audio_sequence = self.validate()
        
        try:
            #print(self.job_params.path_resolver()['local_path_mixdown_pkl'])
            AudioEngine(audio_sequence, self.job_params.path_resolver()['local_path_processed_pkl'], normalized = None).save_to_pkl()
            AudioEngine(validated_audio, self.job_params.path_resolver()['local_path_processed'], normalized = True).save_to_mp3()
            StorageEngine(self.job_params,'processed_job_path').upload_object()
            
            return True
        except Exception as e:
            print(e)
            return False
   
   
class FxPedalBoardConfig(BaseModel):
    audio_fx : str
    
    @validator('audio_fx')
    def audio_fx_validator(cls, v):
        if v not in ['Bitcrush','Chorus','Delay','Flanger','Phaser','Reverb']:
            raise ValueError('not allowed FX input')
        return v

class JobTypeValidator(BaseModel):
    job_type: Literal['job_id_path', 'processed_job_path',
                      'asset_path', 'mixdown_job_path', 'mixdown_job_path_pkl']

    @validator('job_type')
    def job_type_validator(cls, v):
        if v not in ['job_id_path', 'processed_job_path', 'asset_path', 'mixdown_job_path', 'mixdown_job_path_master', 'mixdown_job_path_pkl']:
            raise ValueError(
                'job_type must be either "job_id_path", "processed_job_path", "asset_path", "mixdown_job_path" or "mixdown_job_path_pkl" or "mixdown_job_path_master"')
        return v


JobTypeValidator('test')

FxPedalBoardConfig('Bitcrush')

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

       

os.environ["STORAGE_URL"] = 'https://s3.eu-central-1.wasabisys.com'
os.environ["STORAGE_KEY"] = 'RXL6X3DFGPU2Y38ZC9IY'
os.environ["STORAGE_SECRET"] = 'weQc1F1uVcwUd7vyOZvKTXpKaun7kT9RSnKVJ9B6'


job_id = 'job_ids/2022-11-08-1667943999_test__1660779844-obtnscky11028TQWO.json'
fx_input='2_4_1_3_1_0'
channel_index='0'
selective_mutism_switch='T'
vol='99_50_76_45_23_99'
channel_mute_params='T_T_T_T_T_T'
selective_mutism_value='0.3'
random_id='fengshui'


mix_params2 = FxParamsModel(job_id= job_id, 
                            fx_input=fx_input, 
                            channel_index='3', 
                            selective_mutism_switch=selective_mutism_switch, 
                            vol=vol, 
                            channel_mute_params=channel_mute_params, 
                            selective_mutism_value=selective_mutism_value)


 

        
job = FxRunner(mix_params2, job_id, channel_index, random_id)


job_params = JobConfig(job_id, channel_index, random_id)
job_params.path_resolver()['local_path_mixdown_pkl']

sequence_mute_applied = MuteEngine(mix_params2, job_params).apply_selective_mutism()

sequence_vol_applied = VolEngine(mix_params2, job_params, sequence_mute_applied).apply_volume()
sequence_ready = FxPedalBoardEngine(mix_params2, job_params, sequence_vol_applied).apply_pedalboard_fx()


fx_mapping = ['Bitcrush', 'Chorus', 'Delay', 'Flanger', 'Phaser', 'Reverb', 'Distortion']
        
channel_index = int(job_params.channel_index)
fx_input = mix_params2.fx_input[channel_index]
  
import pedalboard  
      
if fx_input == 'None':
    print('No FX applied')
    AudioEngine(self.my_sequence, self.job_params.path_resolver()['local_path_mixdown_pkl'], normalized = True).save_to_pkl()

else:
    fx = fx_mapping[int(fx_input)]
       
    validated_fx = FxPedalBoardConfig.parse_obj({'audio_fx': fx}) 
        
    pedalboard_fx = getattr(pedalboard, validated_fx.audio_fx)
    
    
    board = pedalboard.Pedalboard([pedalboard_fx()])
        
    try:
        effected = board(sequence_vol_applied, 44100.0)
    except Exception as e:
        print(e)


    else:
        y_effected = np.int16(effected * 2 ** 15)
        AudioEngine(y_effected, self.job_params.path_resolver()['local_path_mixdown_pkl'], normalized = True).save_to_pkl()



sequence_ready = FxEngine(mix_params2, job_params, sequence_vol_applied).apply_fx()
 
 
input_file = job_params.path_resolver()['local_path_pre_mixdown_mp3']
output_file = job_params.path_resolver()['local_path_mixdown_mp3']
        
            
fx_dict = {
            "reverb": f"ffmpeg -i {input_file} -i sox_utils/stalbans_a_binaural.wav -filter_complex '[0] [1] afir=dry=10:wet=10 [reverb]; [0] [reverb] amix=inputs=2:weights=10 5' {output_file}",
            "chorus": f"ffmpeg -i {input_file} -filter_complex 'chorus=0.5:0.9:50|60|70:0.3|0.22|0.3:0.25|0.4|0.3:2|2.3|1.3' {output_file}",
            "crusher": f"ffmpeg -i {input_file} -filter_complex 'acrusher=level_in=4:level_out=4:bits=8:mode=log:aa=1:mix=0.25' {output_file}",
            "echo_indoor": f"ffmpeg -i {input_file} -filter_complex 'aecho=0.8:0.9:40|50|70:0.4|0.3|0.2' {output_file}",
            "echo_outdoor": f"ffmpeg -i {input_file} -filter_complex 'aecho=0.8:0.9:1000|1500|2000:0.4|0.3|0.2' {output_file}",
            "robot_effect": f"ffmpeg -i {input_file} -filter_complex 'afftfilt=real='hypot(re,im)*sin(0)':imag='hypot(re,im)*cos(0)':win_size=512:overlap=0.75' {output_file}"
            
        }            
output_file = job_params.path_resolver()['local_path_mixdown_mp3']
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
    else:
        print('FX failed')
except Exception as e:
    print(e)
    

random_id = 'fengshui'
current_sequences_list = glob.glob(f'temp/mixdown_{random_id}_*.mp3')
        
input_files = '-i ' + ' -i '.join(current_sequences_list)

output_file = 'temp/mixdown_test' + random_id + '.mp3'

mix_cmd = f"ffmpeg -y {input_files} -filter_complex '[0:0][1:0] amix=inputs=6:duration=shortest:normalize=0' -c:a libmp3lame {output_file}"
returned_value = os.system(mix_cmd)   


import pickle
import os


# MIX FILES
dir_path = r'temp'

# list to store files
res = []
# Iterate directory
for file in os.listdir(dir_path):
    # check only text files
    if file.endswith('.pkl'):
        my_arrays = pickle.load(open(os.path.join(dir_path, file), 'rb'))
        #new_sequence_unpacked = [item for sublist in my_arrays for item in sublist]
        new_seq = SequenceEngine.validate_sequence(96, my_arrays)
        
        res.append(new_seq)




my_input = [(a + b + c + d + e + f) / 6 for a, b, c, d, e, f in zip(res[0], res[1], res[2], res[3], res[4], res[5])]

audio_seq_array = np.array(my_input)

channels = 2 if (audio_seq_array.ndim == 2 and audio_seq_array.shape[1] == 2) else 1
if self.normalized:  # normalized array - each item should be a float in [-1, 1)
    y = np.int16(audio_seq_array * 2 ** 15)
else:
    y = np.int16(audio_seq_array)

    
path = '/Users/wojciechbednarz/Desktop/python_projects/euclidean_rhythm_generator_mobile_python_fastapi/temp/test.mp3'

sequence = pydub.AudioSegment(y.tobytes(), frame_rate=44100, sample_width=2, channels=channels)
sequence.export(path, format="mp3", bitrate="128k")

len(res[4])




one_bar = 60/96*4
original_sample_len = round(44100*one_bar/1)

A = np.array([[2, 1], [5, 4]])
output = np.mean(A)
print(output)

# PEDALBOARD FX TEST
from pedalboard import Pedalboard, Chorus, Bitcrush, Reverb, load_plugin, Compressor, Gain, LadderFilter, Phaser, Convolution
from pedalboard.io import AudioFile

from pydub import AudioSegment


vst = load_plugin("/Library/Audio/Plug-Ins/VST3/Portal.vst3")
vst_preset = '/Users/wojciechbednarz/Music/Ableton/User Library/portal_2.vstpreset'
vst.load_preset(vst_preset)

print(vst.parameters.keys())



board = Pedalboard([
    Compressor(threshold_db=-50, ratio=25),
    Gain(gain_db=30),
    Chorus(),
    LadderFilter(mode=LadderFilter.Mode.HPF12, cutoff_hz=900),
    Phaser(),
    Reverb(room_size=0.25),
])

effected = board(np.array(res[0]), 44100.0)
y_effected = np.int16(effected * 2 ** 15)

path = '/Users/wojciechbednarz/Desktop/python_projects/euclidean_rhythm_generator_mobile_python_fastapi/temp/pedalboard_test.mp3'
file_input = '/Users/wojciechbednarz/Desktop/python_projects/euclidean_rhythm_generator_mobile_python_fastapi/temp/sequences_2022-11-04-1667602303_test__1660779844-obtnscky11028TQWO_2.mp3'
file_output = '/Users/wojciechbednarz/Desktop/python_projects/euclidean_rhythm_generator_mobile_python_fastapi/temp/test_stereo_output.mp3'


left_channel = AudioSegment.from_mp3(file_input)
right_channel = AudioSegment.from_mp3(file_input)

stereo_sound = AudioSegment.from_mono_audiosegments(left_channel, right_channel)
stereo_sound.export(file_output, format="mp3", bitrate="128k")


with AudioFile(file_output) as f:
  audio = f.read(f.frames)
  samplerate = f.samplerate
  
board = Pedalboard([vst])

effected = board(audio, samplerate)
y_effected = np.int16(effected * 2 ** 15)
  
path_vst_test = '/Users/wojciechbednarz/Desktop/python_projects/euclidean_rhythm_generator_mobile_python_fastapi/temp/pedalboard_vst3_plugin_test.mp3'
sequence = pydub.AudioSegment(y_effected.tobytes(), frame_rate=44100, sample_width=2, channels=1)
sequence.export(path_vst_test, format="mp3", bitrate="128k")



class Foo(object):
  
    def dynamic_call(self, attribute_name):
        method_name = 'calculate_' + attribute_name # e.g. given attribute name "baz" call method "calculate_baz" 
        func = getattr(self, method_name)           # find method that located within the class
        func() 
        
       
import pedalboard


getattr(pedalboard, 'Chorus')

class 

def apply_pedalboard_fx(audio_array, fx):

    board = pedalboard.Pedalboard([fx])
    try:
        effected = board(audio_array, 44100.0)
    except Exception as e:
        print(e)

    y_effected = np.int16(effected * 2 ** 15)
    
    return y_effected

