import json
import re


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


res = dict((k, job_id_dict[k]) for k in ['bpm', 'key_value']
           if k in job_id_dict)

res
