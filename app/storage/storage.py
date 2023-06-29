import io
import zipfile
import logging
from typing import Any, List
import string
import random

import os
import numpy as np
import pandas as pd
import boto3
import pydub

from botocore.exceptions import BotoCoreError, ClientError
from pydantic import Field, BaseSettings, validator

from app.utils.utils import JobTypeValidator


class StorageBase:
    def __init__(self, bucket=None, client=None, resource=None):
        self.bucket = bucket
        self.client = (
            client if client else self.client_init()
        )  # Use provided client, if none provided call client_init
        self.resource = (
            resource if resource else self.resource_init()
        )  # Use provided resource, if none provided call resource_init
        self.logger = logging.getLogger(__name__)  # initialize logger

    def resource_init(self):
        try:
            self.resource = boto3.resource(
                "s3",
                endpoint_url=StorageCreds().endpoint_url,
                aws_access_key_id=StorageCreds().access_key_id,
                aws_secret_access_key=StorageCreds().secret_access_key,
            )
            return self.resource
        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"Error initializing S3 resource: {e}")
            raise e

    def client_init(self):
        try:
            self.client = boto3.client(
                "s3",
                endpoint_url=StorageCreds().endpoint_url,
                aws_access_key_id=StorageCreds().access_key_id,
                aws_secret_access_key=StorageCreds().secret_access_key,
            )
            return self.client
        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"Error initializing S3 client: {e}")
            raise e


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


class StorageEngine(StorageBase):
    """
    Class to manage storage operations with an S3-compatible storage system.

    Attributes:
    -----------
    job_config : object
        Configuration settings for the job.
    asset_type : str
        Type of the asset.
    """

    def __init__(self, job_config, asset_type, bucket=None, client=None, resource=None):
        super().__init__(
            bucket, client, resource
        )  # Call the parent class (StorageBase) constructor
        self.job_config = job_config
        self.asset_type = asset_type
        self.client = self.resource

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


class StoreEngineMultiFile(StorageBase):
    """
    This class handles the upload of multiple files to S3 storage.

    Attributes:
    -----------
    job_id : str
        Unique identifier for the job.
    logger : object
        Logger instance for logging status and error messages.

    Methods:
    --------
    upload_list_of_objects(files: List[str], bucket_path: str):
        Uploads a list of files to a specified bucket path on S3.
    """

    def __init__(self, job_id, bucket="favs-dump", client=None, resource=None):
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
        super().__init__(
            bucket, client, resource
        )  # Call the parent class (StorageBase) constructor
        self.job_id: str = job_id
        self.logger = logging.getLogger(__name__)

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
            bucket_local = self.resource.Bucket(self.bucket)

            for file, cloud_path in zip(files, cloud_paths):
                try:
                    bucket_local.upload_file(Filename=file, Key=cloud_path)
                except Exception as e:
                    self.logger.error(f"Error uploading file {file} to S3: {e}")
                    raise e
            return True
        except Exception as e:
            self.logger.error(f"Error during S3 operations: {e}")
            raise e


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

    def __init__(
        self,
        bucket,
        client=None,
        resource=None,
    ):
        super().__init__(bucket, client, resource)

    @handle_client_error
    def copy_objects(self, source_key: str, destination_key: str):
        client_local = self.client
        client_local.copy_object(
            Bucket=self.bucket,
            Key=destination_key,
            CopySource=f"{self.bucket}/{source_key}",
        )
        return True

    def download_in_memory_objects(self, key: str) -> io.BytesIO:
        client_local = self.client
        obj = client_local.get_object(Bucket=self.bucket, Key=key)
        file_data = io.BytesIO(obj["Body"].read())
        return file_data

    def create_arrangement_file(self, my_files: List[str], format="wav"):
        client_local = self.client
        concatenated_audio = pydub.AudioSegment.empty()
        for obj in my_files:
            file = client_local.get_object(Bucket=self.bucket, Key=obj)
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
        client_local = self.client
        client_local.upload_fileobj(in_memory_object, self.bucket, output_file)
        return output_file

    def filter_objects(self, prefix_):
        resource_local = self.resource
        print(resource_local)
        my_bucket = resource_local.Bucket(self.bucket)
        files_list = []
        for f in my_bucket.objects.filter(Prefix=prefix_):
            files_list.append(f.key)
        my_files = np.array(files_list)
        return my_files

    @staticmethod
    def generate_random_string(length):
        letters = string.ascii_lowercase
        return "".join(random.choice(letters) for i in range(length))

    @staticmethod
    def filter_files(file_list, suffix, mixdown_ids):
        return [
            file
            for file in file_list
            if file.endswith(suffix) and any(id_str in file for id_str in mixdown_ids)
        ]

    def create_zip_file(self, my_files):
        client_local = self.client
        in_memory_zip = io.BytesIO()
        with zipfile.ZipFile(
            in_memory_zip, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for obj in my_files:
                file = client_local.get_object(Bucket=self.bucket, Key=obj)
                archive.writestr(obj, file["Body"].read())
        in_memory_zip.seek(0)
        return in_memory_zip

    @handle_client_error
    def get_presigned_url(self, file_name, expires_in=15):
        client_local = self.client
        response = client_local.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": file_name},
            ExpiresIn=expires_in,
        )
        return response

    @handle_client_error
    def upload_and_get_presigned_url(self, zip_name, in_memory_zip, expires_in=300):
        client_local = self.client
        client_local.upload_fileobj(in_memory_zip, self.bucket, zip_name)
        response = client_local.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": zip_name},
            ExpiresIn=expires_in,
        )
        return response


class SnapshotManager(StorageBase):
    SNAPSHOT_CSV = "database_snapshot.csv"
    SNAPSHOT_FILES_CSV = "database_snapshot_files.csv"
    SNAPSHOTS_DUMP_BUCKET = "snapshots-dump"
    FILTER_OUT_LABELS = ["sequences", "favourite", "my_favourites", "mixdown"]

    """
    This class represents a manager for handling snapshots in Amazon S3 storage.
    """

    def __init__(self, bucket, client=None, resource=None):
        super().__init__(bucket, client, resource)
        # self.bucket_obj = self.resource.Bucket(self.bucket)
        self.snapshot_df = None
        self.snapshot_files_df = None

    def build_snapshot(self):
        """
        Builds a snapshot of all the objects in the bucket and saves it as a CSV file in S3.
        The snapshot is a pandas DataFrame consisting of the paths of all the files in the bucket.
        """
        try:
            local_resource = self.resource.Bucket(self.bucket)

            files_list = [f.key for f in local_resource.objects.all()]
            self.snapshot_df = pd.DataFrame(files_list, columns=["paths"])
            # Save the snapshot_df to a CSV in memory
            print(self.snapshot_df)
            csv_buffer = io.StringIO()
            self.snapshot_df.to_csv(csv_buffer, index=False)

            # Upload the CSV to S3
            self.resource.Object(self.SNAPSHOTS_DUMP_BUCKET, self.SNAPSHOT_CSV).put(
                Body=csv_buffer.getvalue()
            )
            return True
        except ClientError as e:
            self.logger.error(f"Error building snapshot: {e}")
            raise e

    def get_snapshot_data(self):
        """
        Loads the snapshot data from S3, processes it, and saves the processed data back to S3.
        The processing involves filtering out certain types of files and splitting the file paths into 'label' and 'file' columns.
        """
        try:
            self.load_snapshot_from_s3()
            self.process_snapshot_data()
            self.save_snapshot_files_to_s3()
            return True
        except ClientError as e:
            self.logger.error(f"Error getting snapshot data: {e}")
            raise e

    def load_snapshot_from_s3(self):
        """
        Loads the snapshot CSV from S3 into a pandas DataFrame. If the snapshot data is already loaded, does nothing.
        """

        if self.snapshot_df is not None:
            return
        s3_key = self.SNAPSHOT_CSV
        csv_obj = self.resource.Object(self.bucket, s3_key).get()["Body"]
        csv_buffer = io.StringIO(csv_obj.read().decode("utf-8"))
        self.snapshot_df = pd.read_csv(csv_buffer)

    def process_snapshot_data(self):
        """
        Processes the snapshot data by filtering out certain types of files and splitting the file paths into 'label' and 'file' columns.
        """
        self.snapshot_files_df = self.snapshot_df[
            self.snapshot_df["paths"].str.endswith(".mp3")
        ].copy()
        self.snapshot_files_df["bucket"] = self.bucket
        self.snapshot_files_df[["label", "file"]] = self.snapshot_files_df[
            "paths"
        ].str.split("/", expand=True)
        self.snapshot_files_df = self.snapshot_files_df[
            ~self.snapshot_files_df["label"].isin(self.FILTER_OUT_LABELS)
        ]

    def save_snapshot_files_to_s3(self):
        """
        Saves the processed snapshot data (a DataFrame of file paths, labels, and file names) as a CSV file in S3.
        """
        csv_buffer = io.StringIO()
        self.snapshot_files_df.to_csv(csv_buffer, index=False)
        s3_key = self.SNAPSHOT_FILES_CSV
        self.resource.Object(self.SNAPSHOTS_DUMP_BUCKET, s3_key).put(
            Body=csv_buffer.getvalue()
        )

    def generate_presigned_urls(self):
        """
        Generate pre-signed URLs for database snapshot and snapshot files.
        """
        try:
            url_1 = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.SNAPSHOTS_DUMP_BUCKET, "Key": self.SNAPSHOT_CSV},
                ExpiresIn=3600,
            )
            url_2 = self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.SNAPSHOTS_DUMP_BUCKET,
                    "Key": self.SNAPSHOT_FILES_CSV,
                },
                ExpiresIn=3600,
            )
            return url_1, url_2
        except ClientError as e:
            self.logger.error(f"Error generating presigned urls: {e}")
            raise e




