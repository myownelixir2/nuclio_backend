import io
import zipfile
import logging
from botocore.exceptions import BotoCoreError, ClientError
import os
import numpy as np
import pandas as pd
from pydantic import Field, BaseSettings, validator
from typing import Any
import boto3
import pydub
from typing import List
import time
import string
import random
#from app.utils.utils import *
from app.utils.utils import JobTypeValidator

class StorageCreds(BaseSettings):
    """
    A class used to manage and validate storage credentials.

    Attributes:
    -----------
    endpoint_url : str
        The URL of the storage endpoint.
    access_key_id : str
        The access key ID for the storage.
    secret_access_key : str
        The secret access key for the storage.
    """
    endpoint_url: str = Field(..., env="STORAGE_URL")
    access_key_id: str = Field(..., env="STORAGE_KEY")
    secret_access_key: str = Field(..., env="STORAGE_SECRET")
   

    @validator("endpoint_url", "access_key_id", "secret_access_key")
    def creds_validator(cls, v: Any) -> Any:
        """
        Validates the provided storage credentials.

        Parameters:
        -----------
        v : Any
            The value of the attribute being validated.

        Returns:
        --------
        Any
            The validated value.
        """

        if v is None:
            raise ValueError(
                "endpoint_url, access_key_id and secret_access_key must be set"
            )
        return v

import logging
from botocore.exceptions import BotoCoreError, ClientError

class StorageEngine:
    """
    Class to manage storage operations with an S3-compatible storage system.

    Attributes:
    -----------
    job_config : object
        Configuration settings for the job.
    asset_type : str
        Type of the asset.
    client : object
        Boto3 S3 resource object.
    """

    def __init__(self, job_config, asset_type):
        self.job_config = job_config
        self.asset_type = asset_type
        self.client = self.client_init()
        self.logger = logging.getLogger(__name__)

    def client_init(self):
        """Initialize S3 client using storage credentials."""
        try:
            client = boto3.resource(
                "s3",
                endpoint_url=StorageCreds().endpoint_url,
                aws_access_key_id=StorageCreds().access_key_id,
                aws_secret_access_key=StorageCreds().secret_access_key,
            )
            return client
        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"Error initializing S3 client: {e}")
            raise e

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

    def get_object(self, bucket_name="sample-dump"):
        """Download file from S3 to local."""
        try:
            bucket = self.client.Bucket(bucket_name)
            _type = self.__resolve_type()
            bucket.download_file(_type["cloud_path"], _type["local_path"])
            return True
        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"Error getting object from S3: {e}")
            raise e

    def delete_local_object(self):
        """Delete local file."""
        try:
            _type = self.__resolve_type()
            os.remove(_type["local_path"])
            return True
        except OSError as e:
            self.logger.error(f"Error deleting local object: {e}")
            raise e

    def upload_object_local(self, local_path, cloud_path, bucket_name="sample-dump"):
        """Upload local file to S3."""
        try:
            bucket = self.client.Bucket(bucket_name)
            bucket.upload_file(local_path, cloud_path)
            return True
        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"Error uploading local object to S3: {e}")
            raise e

    def upload_object(self, bucket_name="sample-dump"):
        """Upload local file to S3 based on job config."""
        try:
            bucket = self.client.Bucket(bucket_name)
            _type = self.__resolve_type()
            bucket.upload_file(_type["local_path"], _type["cloud_path"])
            return True
        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"Error uploading object to S3: {e}")
            raise e

        
class StoreEngineMultiFile:
    """
    This class handles the upload of multiple files to S3 storage.

    Attributes:
    -----------
    job_id : str
        Unique identifier for the job.
    logger : object
        Logger instance for logging status and error messages.
    client : object
        S3 client instance.

    Methods:
    --------
    client_init():
        Initializes and returns the S3 client.
    upload_list_of_objects(files: List[str], bucket_path: str):
        Uploads a list of files to a specified bucket path on S3.
    """
    def __init__(self, job_id):
        """
        Initialize the S3 client.

        Returns:
        --------
        boto3.resource
            S3 client instance.
        
        Raises:
        -------
        Exception
            If any error occurs during the client initialization.
        """
        self.job_id: str = job_id
        self.logger = logging.getLogger(__name__)
        self.client = self.client_init()

    def client_init(self):
        """Initialize the S3 client."""
        try:
            client = boto3.resource(
                "s3",
                endpoint_url=StorageCreds().endpoint_url,
                aws_access_key_id=StorageCreds().access_key_id,
                aws_secret_access_key=StorageCreds().secret_access_key,
            )
            return client
        except Exception as e:
            self.logger.error(f"Error initializing S3 client: {e}")
            raise e

    def upload_list_of_objects(self, files: List[str], bucket_path: str) -> bool:
        """
        Uploads a list of files to a specified bucket path on S3.

        Parameters:
        -----------
        files : List[str]
            List of local file paths to upload.
        bucket_path : str
            The cloud bucket path to upload files.

        Returns:
        --------
        bool
            True if all files are uploaded successfully, False otherwise.

        Raises:
        -------
        Exception
            If any error occurs during the file upload.
        """
        def sanitize_list(file_list: List[str]) -> List[str]:
            return [os.path.basename(file) for file in file_list]

        sanitized_files = sanitize_list(files)
        cloud_paths = [os.path.join(bucket_path, file) for file in sanitized_files]
        
        try:
            bucket = self.client.Bucket("favs-dump")
            for file, cloud_path in zip(files, cloud_paths):
                try:
                    bucket.upload_file(file, cloud_path)
                except Exception as e:
                    self.logger.error(f"Error uploading file {file} to S3: {e}")
                    raise e
            return True
        except Exception as e:
            self.logger.error(f"Error during S3 operations: {e}")
            raise e

import boto3
import io
import zipfile
from botocore.exceptions import ClientError

class StorageBase:
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

def handle_client_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            print(e)
            return None
    return wrapper

class StorageEngineDownloader(StorageBase):
    """
    This class represents a storage engine designed for downloading, manipulating, and uploading files 
    using Amazon S3 storage. 

    Attributes:
        bucket (str): The name of the S3 bucket to use for storage operations.

    Methods:
        resource_init(): Initialize a boto3 resource object.
        client_init(): Initialize a boto3 client object.
        copy_objects(source_key, destination_key): Copy an object within the bucket.
        download_in_memory_objects(key): Download an object from the bucket into memory.
        create_arrangement_file(my_files, format): Create an audio file by concatenating multiple audio files.
        upload_in_memory_object(output_file, in_memory_object): Upload an in-memory file to the bucket.
        filter_objects(prefix_): Filter the objects in the bucket by a prefix.
        generate_random_string(length): Generate a random string of a given length.
        filter_files(file_list, suffix, mixdown_ids): Filter a list of files by suffix and mixdown id.
        create_zip_file(my_files): Create a zip file from multiple files in the bucket.
        get_presigned_url(file_name, expires_in): Generate a presigned URL for a file in the bucket.
        upload_and_get_presigned_url(zip_name, in_memory_zip, expires_in): Upload a file to the bucket and generate a presigned URL for it.
    """
    def __init__(self, bucket):
        super().__init__(bucket)

    @handle_client_error
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

    @handle_client_error
    def upload_in_memory_object(self, output_file: str, in_memory_object: io.BytesIO):
        client = self.client_init()
        client.upload_fileobj(in_memory_object, self.bucket, output_file)
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
        return [file for file in file_list if file.endswith(suffix) and any(id_str in file for id_str in mixdown_ids)]

    def create_zip_file(self, my_files):
        client = self.client_init()
        in_memory_zip = io.BytesIO()
        with zipfile.ZipFile(in_memory_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for obj in my_files:
                file = client.get_object(Bucket=self.bucket, Key=obj)
                archive.writestr(obj, file["Body"].read())
        in_memory_zip.seek(0)
        return in_memory_zip

    @handle_client_error
    def get_presigned_url(self, file_name, expires_in=15):
        client = self.client_init()
        response = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": file_name},
            ExpiresIn=expires_in,
        )
        return response

    @handle_client_error
    def upload_and_get_presigned_url(self, zip_name, in_memory_zip, expires_in=300):
        client = self.client_init()
        client.upload_fileobj(in_memory_zip, self.bucket, zip_name)
        response = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": zip_name},
            ExpiresIn=expires_in,
        )
        return response



class SnapshotManager:
    """
    This class represents a manager for handling snapshots in Amazon S3 storage.
    """
    def __init__(self, bucket_name):
        self.bucket = bucket_name
        self.resource = self.resource_init()
        self.client = self.client_init()
        self.bucket_obj = self.resource.Bucket(self.bucket)
        self.snapshot_df = None
        self.snapshot_files_df = None

    def resource_init(self):
        try:
            resource = boto3.resource(
                "s3",
                endpoint_url=StorageCreds().endpoint_url,
                aws_access_key_id=StorageCreds().access_key_id,
                aws_secret_access_key=StorageCreds().secret_access_key,
            )
            return resource
        except Exception as e:
            print(e)
            return False

    def client_init(self):
        try:
            client = boto3.client(
                "s3",
                endpoint_url=StorageCreds().endpoint_url,
                aws_access_key_id=StorageCreds().access_key_id,
                aws_secret_access_key=StorageCreds().secret_access_key,
            )
            return client
        except Exception as e:
            print(e)
            return False
        
    def build_snapshot(self):
        try:
            files_list = [f.key for f in self.bucket_obj.objects.all()]
            self.snapshot_df = pd.DataFrame(files_list, columns=['paths'])

            # Save the snapshot_df to a CSV in memory
            csv_buffer = io.StringIO()
            self.snapshot_df.to_csv(csv_buffer, index=False)

            # Upload the CSV to S3
            s3_key = 'database_snapshot.csv'
            self.resource.Object('snapshots-dump', s3_key).put(Body=csv_buffer.getvalue())
            return True
        except ClientError as e:
            print(f"Error building snapshot: {e}")
            return False

    def get_snapshot_data(self):
        try:
            if self.snapshot_df is None:
                # Read the snapshot CSV from S3
                s3_key = 'database_snapshot.csv'
                csv_obj = self.resource.Object(self.bucket, s3_key).get()['Body']
                csv_buffer = io.StringIO(csv_obj.read().decode('utf-8'))
                self.snapshot_df = pd.read_csv(csv_buffer)

            self.snapshot_files_df = self.snapshot_df[self.snapshot_df['paths'].str.endswith('.mp3')].copy()
            self.snapshot_files_df['bucket'] = self.bucket
            self.snapshot_files_df[['label', 'file']] = self.snapshot_files_df['paths'].str.split('/', expand=True)
            
            # Filter out specific labels
            filter_out = ["sequences", "favourite", "my_favourites", "mixdown"]
            self.snapshot_files_df = self.snapshot_files_df[~self.snapshot_files_df['label'].isin(filter_out)]

            # Save the snapshot_files_df to a CSV in memory
            csv_buffer = io.StringIO()
            self.snapshot_files_df.to_csv(csv_buffer, index=False)

            # Upload the CSV to S3
            s3_key = 'database_snapshot_files.csv'
            self.resource.Object('snapshots-dump', s3_key).put(Body=csv_buffer.getvalue())
            return True
        except ClientError as e:
            print(f"Error getting snapshot data: {e}")
            return False

    def generate_presigned_urls(self):
        """
        Generate pre-signed URLs for database snapshot and snapshot files.
        """
        try:
            url_1 = self.client.generate_presigned_url('get_object', Params={'Bucket': 'snapshots-dump', 'Key': 'database_snapshot.csv'}, ExpiresIn=3600)
            url_2 = self.client.generate_presigned_url('get_object', Params={'Bucket': 'snapshots-dump', 'Key': 'database_snapshot_files.csv'}, ExpiresIn=3600)
            return url_1, url_2
        except ClientError as e:
            self.logger.error(f"Error generating presigned urls: {e}")
            raise e


