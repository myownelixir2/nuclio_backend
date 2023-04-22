import io
import zipfile
from botocore.exceptions import ClientError
import os
import numpy as np
import pandas as pd
from pydantic import Field, BaseSettings, validator
import boto3
import pydub
from typing import List
import time
import string
import random
#from app.utils.utils import *
from app.utils.utils import JobTypeValidator

class StorageCreds(BaseSettings):
    endpoint_url: str = Field(..., env="STORAGE_URL")
    access_key_id: str = Field(..., env="STORAGE_KEY")
    secret_access_key: str = Field(..., env="STORAGE_SECRET")
    
    @validator("endpoint_url", "access_key_id", "secret_access_key")
    def creds_validator(cls, v):

        if v is None:
            raise ValueError(
                "endpoint_url, access_key_id and secret_access_key must be set"
            )
        return v


class StorageEngine:
    def __init__(self, job_config, asset_type):
        self.job_config = job_config
        self.asset_type = asset_type

    def client_init(self):
        try:
            self.client = boto3.resource(
                "s3",
                endpoint_url=StorageCreds().endpoint_url,
                aws_access_key_id=StorageCreds().access_key_id,
                aws_secret_access_key=StorageCreds().secret_access_key,
            )
            return self.client
        except Exception as e:
            print(e)
            return True

    def __resolve_type(self):
        job_paths = self.job_config.path_resolver()

        _check = JobTypeValidator.parse_obj({"job_type": self.asset_type})

        if _check.job_type == "job_id_path":
            d_filter = ["local_path", "cloud_path"]
            d_paths = dict(((key, job_paths[key]) for key in d_filter))
            return d_paths
        elif _check.job_type == "processed_job_path":
            d_paths = {
                "cloud_path": job_paths["cloud_path_processed"],
                "local_path": job_paths["local_path_processed"],
            }
            return d_paths
        elif _check.job_type == "mixdown_job_path":
            d_paths = {
                "cloud_path": job_paths["cloud_path_mixdown_mp3"],
                "local_path": job_paths["local_path_mixdown_mp3"],
            }
            return d_paths
        elif _check.job_type == "mixdown_job_path_master":
            d_paths = {
                "cloud_path": job_paths["cloud_path_mixdown_wav_master"],
                "local_path": job_paths["local_path_mixdown_wav_master"],
            }
            return d_paths
        elif _check.job_type == "mixdown_job_path_pkl":
            d_paths = {
                "cloud_path": job_paths["cloud_path_mixdown_pkl"],
                "local_path": job_paths["local_path_mixdown_pkl"],
            }
            return d_paths
        else:
            asset_paths = self.job_config.get_job_params()
            d_paths = {
                "cloud_path": asset_paths["cloud_paths"],
                "local_path": asset_paths["local_paths"],
            }
            return d_paths

    def get_object(self):
        try:
            client = self.client_init()
            bucket = client.Bucket("sample-dump")
            _type = self.__resolve_type()
            bucket.download_file(_type["cloud_path"], _type["local_path"])
            return True
        except Exception as e:
            print(e)
            return False

    def delete_local_object(self):
        try:
            _type = self.__resolve_type()
            os.remove(_type["local_path"])
            return True
        except Exception as e:
            print(e)
            return False

    def upload_object(self):
        try:
            client = self.client_init()
            bucket = client.Bucket("sample-dump")
            _type = self.__resolve_type()
            bucket.upload_file(_type["local_path"], _type["cloud_path"])
            return True
        except Exception as e:
            print(e)
            return False
        
class StoreEngineMultiFile:
    def __init__(self, job_id):
        self.job_id: str = job_id

    def client_init(self):
        try:
            self.client = boto3.resource(
                "s3",
                endpoint_url=StorageCreds().endpoint_url,
                aws_access_key_id=StorageCreds().access_key_id,
                aws_secret_access_key=StorageCreds().secret_access_key,
            )
            return self.client
        except Exception as e:
            print(e)
            return False

    def upload_list_of_objects(self, files: List[str], bucket_path: str) -> bool:
        def sanitize_list(file_list: List[str]) -> List[str]:
            return [os.path.basename(file) for file in file_list]

        sanitized_files = sanitize_list(files)
        cloud_paths = [os.path.join(bucket_path, file) for file in sanitized_files]
        status = True
        try:
            client = self.client_init()
            bucket = client.Bucket("favs-dump")

        except Exception as e:
            print(f"An error occurred while initiating an s3 client: {e}")
            status = False
        else:
            for file, cloud_path in zip(files, cloud_paths):
                try:
                    bucket.upload_file(file, cloud_path)
                except Exception as e:
                    print(
                        f"An error occurred while uploading the file {file} to S3: {e}"
                    )
                    status = False
        return status

class StorageEngineDownloader:
    def __init__(self, bucket):
        self.bucket = bucket

    def resource_init(self):
        try:
            self.resource = boto3.resource(
                "s3",
                endpoint_url=StorageCreds().endpoint_url,
                aws_access_key_id=StorageCreds().access_key_id,
                aws_secret_access_key=StorageCreds().secret_access_key,
            )
            return self.resource
        except Exception as e:
            print(e)
            return False
        
    def client_init(self):
        try:
            self.client = boto3.client(
                "s3",
                endpoint_url=StorageCreds().endpoint_url,
                aws_access_key_id=StorageCreds().access_key_id,
                aws_secret_access_key=StorageCreds().secret_access_key,
            )
            return self.client
        except Exception as e:
            print(e)
            return False

    def copy_objects(self, source_key: str, destination_key: str):
        client = self.client_init()
        client.copy_object(Bucket=self.bucket,
                           Key=destination_key, CopySource=f"{self.bucket}/{source_key}")
        return True

    def download_in_memory_objects(self, key: str) -> io.BytesIO:
        client = self.resource_init()
        obj = client.get_object(Bucket=self.bucket, Key=key)
        file_data = io.BytesIO(obj["Body"].read())
        return file_data

    def create_arrangement_file(self, my_files: List[str], format="wav"):
        client = self.client_init()
        concatenated_audio = pydub.AudioSegment.empty()
        for obj in my_files:
            file = client.get_object(Bucket=self.bucket, Key=obj)
            file_data = file["Body"].read()
            file_like_object = io.BytesIO(file_data)
            audio_data = pydub.AudioSegment.from_file(file_like_object, format=format)
            concatenated_audio += audio_data

        in_memory_arrangement = io.BytesIO()
        concatenated_audio.export(in_memory_arrangement, format="wav")
        in_memory_arrangement.seek(0)
        return in_memory_arrangement

    def upload_in_memory_object(self, output_file: str, in_memory_object: io.BytesIO):
        try:
            client = self.client_init()
            client.upload_fileobj(in_memory_object, self.bucket, output_file)
        except ClientError as e:
            print(e)
            return None
        return output_file

    def filter_objects(self, prefix_):
        resource = self.resource_init()
        my_bucket = resource.Bucket(self.bucket)
        files_list = []
        for f in my_bucket.objects.filter(Prefix=prefix_):
            files_list.append(f.key)
        my_files = np.array(files_list)
        return my_files

    @staticmethod
    def generate_random_string(length):
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(length))


    @staticmethod
    def filter_files(file_list, suffix, mixdown_ids):
        filtered_list = []
        for file in file_list:
            if file.endswith(suffix):
                if any(id_str in file for id_str in mixdown_ids):
                    filtered_list.append(file)
        return filtered_list

    def create_zip_file(self, my_files):
        #client = self.resource_init()
        client = self.client_init()
        in_memory_zip = io.BytesIO()
        with zipfile.ZipFile(in_memory_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for obj in my_files:
                file = client.get_object(Bucket=self.bucket, Key=obj)
                archive.writestr(obj, file["Body"].read())
        in_memory_zip.seek(0)
        return in_memory_zip

    def get_presigned_url(self, file_name, expires_in=15):
        client = self.client_init()
        try:
            response = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": file_name},
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            print(e)
            return None
        return response

    def upload_and_get_presigned_url(self, zip_name, in_memory_zip, expires_in=300):
        client = self.client_init()
        client.upload_fileobj(in_memory_zip, self.bucket, zip_name)
        try:
            response = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": zip_name},
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            print(e)
            return None
        return response
