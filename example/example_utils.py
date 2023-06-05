import requests
import json
import urllib.request
from urllib.error import HTTPError
from typing import List, Tuple
from datetime import datetime
import random
import pandas as pd
import string
import time
import concurrent.futures
import re
import os

from pydantic import BaseSettings, BaseModel


class FirebaseConfig(BaseSettings):
    firebase_api_key: str
    firebase_email: str
    firebase_password: str

    class Config:
        env_file = "config.env"


def get_access_token():
    config = FirebaseConfig()
    endpoint = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={config.firebase_api_key}"
    email = config.firebase_email
    password = config.firebase_password
    data = {"email": email, "password": password, "returnSecureToken": True}
    try:
        resp = requests.post(
            endpoint,
            data=json.dumps(data),
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()  # raise an exception if the request failed
        return resp.json()["idToken"]
    except requests.HTTPError as e:
        print(f"Authentication failed: {e}")
        return None


class SessionIdGenerator:
    def __init__(self):
        self.adjectives = pd.read_csv(
            "random_name_generator/english-adjectives.txt", header=None
        )
        self.nouns = pd.read_csv("random_name_generator/english-nouns.txt", header=None)

    def generate_random_id(self):
        random_id = "".join(random.choices(string.ascii_lowercase, k=6))
        return random_id

    def random_project_name(self):
        return f"{random.choice(self.adjectives[0])}_{random.choice(self.nouns[0])}"

    def generate_session_id(self):
        date_string = datetime.now().strftime("%Y_%m_%d")
        return f"{date_string}_{self.random_project_name()}"

    def generate_job_id(self):
        part_1 = "".join(random.choices(string.ascii_lowercase, k=4))
        part_2 = "".join(random.choices(string.ascii_lowercase, k=4))
        part_3 = "".join(random.choices(string.digits, k=4))
        part_4 = "".join(random.choices(string.ascii_uppercase, k=4))

        id = f"{int(time.time())}-{part_1}{part_2}{part_3}{part_4}"

        return id

    def generate_cloud_job_id(self):
        session_id = self.generate_session_id()
        job_id = self.generate_job_id()
        cloud_job_id = f"job_ids/{session_id}__{job_id}.json"
        return cloud_job_id


class JobConfig(BaseModel):
    local_paths: List[str]
    cloud_paths: List[str]
    bpm: List[int]
    scale_value: List[str]
    key_value: List[str]
    rythm_config_list: List[List[int]]
    pitch_temperature_knob_list: List[List[int]]


class JobCreateRequestConfig(BaseSettings):
    host_api_endpoint: str

    class Config:
        env_file = "config.env"


class SequenceGenerator:
    def __init__(self, access_token: str, job_id: str, fx_mix_job_id: str):
        self.access_token = access_token
        self.job_id = job_id
        self.fx_mix_job_id = fx_mix_job_id
        self.config = JobCreateRequestConfig()

    def set_config(self, config: JobCreateRequestConfig):
        self.config = config

    def get_config(self) -> JobCreateRequestConfig:
        return self.config

    def set_job_id(self, job_id: str):
        self.job_id = job_id

    def get_job_id(self) -> str:
        return self.job_id

    def set_fx_mix_job_id(self, fx_mix_job_id: str):
        self.fx_mix_job_id = fx_mix_job_id

    def get_fx_mix_job_id(self) -> str:
        return self.fx_mix_job_id

    def create_job(self, job_config: JobConfig):
        job_create_url = (
            f"{self.config.host_api_endpoint}/create_job?job_id={self.job_id}"
        )
        headers = {"Authorization": f"Bearer {self.access_token}"}
        json_string = dict(job_config)

        try:
            res = requests.post(job_create_url, json=json_string, headers=headers)
            res.raise_for_status()  # raise an exception if the request failed
        except requests.HTTPError as e:
            print(f"Failed to create job: {e}")

        return self.job_id

    def create_sequence(self, channel_index: int, random_id: str = "start"):
        job_create_url = f"{self.config.host_api_endpoint}/get_sequence?job_id={self.job_id}&channel_index={channel_index}&random_id={random_id}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            res = requests.post(job_create_url, headers=headers)
            res.raise_for_status()  # raise an exception if the request failed
        except requests.HTTPError as e:
            print(f"Failed to create sequence: {e}")

        return self.job_id

    def apply_fx(
        self,
        channel_index: int,
        fx_params: str,
        fx_params_preset: str,
        selective_mutism_switch: str,
        selective_mutism_value: str,
        vol_params: str,
        mute_params: str,
    ):
        http_paths = f"{self.config.host_api_endpoint}/apply_fx?job_id={self.job_id}&channel_index={channel_index}&random_id={self.fx_mix_job_id}&fx_input={fx_params}&preset={fx_params_preset}&selective_mutism_switch={selective_mutism_switch}&selective_mutism_value={selective_mutism_value}&vol={vol_params}&channel_mute_params={mute_params}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            res = requests.post(http_paths, headers=headers)
            res.raise_for_status()  # raise an exception if the request failed
        except requests.HTTPError as e:
            print(f"Failed to apply effects: {e}")

        return res.json() if res.status_code == 200 else None

    def mix_sequences(self):
        mix_sequences_url = f"{self.config.host_api_endpoint}/mix_sequences?job_id={self.job_id}&random_id={self.fx_mix_job_id}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            res = requests.post(mix_sequences_url, headers=headers)
            res.raise_for_status()  # raise an exception if the request failed
        except requests.HTTPError as e:
            print(f"Failed to mix sequences: {e}")

        return res.json() if res.status_code == 200 else None


class FileUtils:
    def __init__(self, sequence_generator: SequenceGenerator):
        self.sequence_generator = sequence_generator
        self.access_token = sequence_generator.access_token
        self.host_api_endpoint = sequence_generator.config.host_api_endpoint
        self.job_id = sequence_generator.job_id
        self.fx_mix_job_id = sequence_generator.fx_mix_job_id

    def cleanup_temp(self, pattern: str):
        clean_up_url = f"{self.host_api_endpoint}/clean_up_temp?job_id={self.job_id}&pattern={pattern}&random_id={self.fx_mix_job_id}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            res = requests.post(clean_up_url, headers=headers)
            res.raise_for_status()  # raise an exception if the request failed
        except requests.HTTPError as e:
            print(f"Failed to clean up temporary files: {e}")

    def purge_temp(self):
        purge_temp_url = f"{self.host_api_endpoint}/purge"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            res = requests.post(purge_temp_url, headers=headers)
            res.raise_for_status()  # raise an exception if the request failed
        except requests.HTTPError as e:
            print(f"Failed to purge temporary files: {e}")

    def presigned_url(self, bucket: str):
        if not os.path.exists("temp/mixdown"):
            os.makedirs("temp/mixdown")

        sanitized_mixdown_id = re.sub(
            ".json", "_master.wav", re.sub("job_ids/", "", self.job_id)
        )
        mixdown_job_id = f"mixdown/mixdown_{self.fx_mix_job_id}_{sanitized_mixdown_id}"

        local_mixdown_job_path = os.path.join("temp", mixdown_job_id)
        print(f"Downloading mixdown to {local_mixdown_job_path}")
        my_mixdown_url = f"{self.host_api_endpoint}/download_universal?bucket={bucket}&file_name={mixdown_job_id}"

        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            res = requests.post(my_mixdown_url, headers=headers)
            res.raise_for_status()  # raise an exception if the request failed
        except requests.HTTPError as e:
            print(f"Failed to get presigned URL: {e}")
            return None

        my_presigned_url = res.content.decode("utf-8")
        print(f"Downloading mixdown from {my_presigned_url}")

        try:
            urllib.request.urlretrieve(my_presigned_url, local_mixdown_job_path)
        except HTTPError as e:
            print(f"Failed to download mixdown: {e}")
            return None

        return local_mixdown_job_path


def execute_concurrently(func, *args_list):
    max_workers = 6
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    futures = []

    for args in args_list:
        future = executor.submit(lambda args: func(*args), args)
        futures.append(future)

    results = []
    for future in concurrent.futures.as_completed(futures):
        result = future.result()
        results.append(result)

    return results
