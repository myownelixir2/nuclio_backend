import pytest
import boto3
from moto import mock_s3
from app.storage.storage import (StorageEngine, 
                                 StorageCreds, 
                                 StoreEngineMultiFile, 
                                 StorageEngineDownloader,
                                 SnapshotManager)
from app.utils.utils import JobConfig
import os
from botocore.exceptions import BotoCoreError
from unittest.mock import patch, MagicMock
import unittest
from io import BytesIO
import pydub

@mock_s3
class TestStorageEngine:
    @pytest.fixture(autouse=True)
    def setup(self):
        # Creating test bucket
        self.bucket_name = 'test-bucket'
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.s3_client.create_bucket(Bucket=self.bucket_name)
        self.job_config = JobConfig('test_job_id', 1, 'test_random_id')  # Assuming JobConfig requires these parameters
        self.asset_type = 'test_asset_type'  # Replace with a valid asset type for your tests

    def test_get_object(self):
        # Creating a test object in the bucket
        self.s3_client.put_object(Bucket=self.bucket_name, Key='test_key', Body=b'test_content')

        storage_engine = StorageEngine(self.job_config, self.asset_type)
        storage_engine.get_object(self.bucket_name)

        # Asserting that the file was correctly downloaded
        with open(self.job_config.path_resolver()['local_path'], 'rb') as file:
            assert file.read() == b'test_content'

    def test_upload_object_local(self):
        # Creating a test file to upload
        with open('test_file', 'wb') as file:
            file.write(b'test_content')

        storage_engine = StorageEngine(self.job_config, self.asset_type)
        storage_engine.upload_object_local('test_file', 'test_key', self.bucket_name)

        # Asserting that the file was correctly uploaded
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key='test_key')
        assert response['Body'].read() == b'test_content'

    def test_delete_local_object(self):
        # Create a dummy local file
        with open('dummy_file.txt', 'w') as file:
            file.write('Dummy file content')
        
        # Set the local path in the job_config to the dummy file path
        self.job_config.local_path = 'dummy_file.txt'
        
        # Delete the local file
        self.assertTrue(self.storage_engine.delete_local_object())
        
        # Assert the file has been deleted
        self.assertFalse(os.path.exists('dummy_file.txt'))
    
    @mock_s3
    @patch.object(StorageEngine, "client_init")
    def test_upload_object_local(self, mock_client):
        conn = boto3.resource('s3', region_name='us-west-2')
        conn.create_bucket(Bucket='sample-dump')

        # Create a dummy file
        with open('dummy_file.txt', 'w') as file:
            file.write('Dummy file content')

        # Assume client_init is working fine
        mock_client.return_value = conn

        # Create a StorageEngine instance
        storage_engine = StorageEngine(JobConfig(job_id="123", channel_index=1, random_id="random_123"), 'job_id_path')

        # Call upload_object_local
        local_path = 'dummy_file.txt'
        cloud_path = 'dummy_file_s3.txt'
        self.assertTrue(storage_engine.upload_object_local(local_path, cloud_path))

        # Verify the file exists in S3
        body = conn.Object('sample-dump', cloud_path).get()['Body'].read().decode("utf-8") 
        self.assertEqual(body, 'Dummy file content')

class TestStoreEngineMultiFile(unittest.TestCase):
    @mock_s3
    def test_upload_list_of_objects(self):
        # Create a mock S3 bucket
        conn = boto3.resource('s3', region_name='us-west-2')
        conn.create_bucket(Bucket='favs-dump')

        job_id = '123'
        store_engine = StoreEngineMultiFile(job_id)

        # Create some temporary files for testing
        files = []
        for i in range(3):
            with open(f'test{i}.txt', 'w') as f:
                f.write('This is a test file.')
                files.append(f.name)

        bucket_path = 'test_bucket_path'
        status = store_engine.upload_list_of_objects(files, bucket_path)

        # Assert upload status
        self.assertTrue(status)

        # Assert files are in the bucket
        s3_client = boto3.client('s3', region_name='us-west-2')
        response = s3_client.list_objects(Bucket='favs-dump')

        s3_files = [item['Key'] for item in response['Contents']]
        for file in files:
            self.assertIn(os.path.join(bucket_path, os.path.basename(file)), s3_files)

        # Cleanup local files
        for file in files:
            os.remove(file)

class TestStorageEngineDownloader(unittest.TestCase):
    def setUp(self):
        self.s3 = StorageEngineDownloader(bucket="test-bucket")

    @mock_s3
    def test_client_init(self):
        with patch('boto3.client') as mock_client:
            self.s3.client_init()
            mock_client.assert_called_once()

    @mock_s3
    def test_resource_init(self):
        with patch('boto3.resource') as mock_resource:
            self.s3.resource_init()
            mock_resource.assert_called_once()

    @mock_s3
    def test_filter_objects(self):
        conn = boto3.resource('s3', region_name='us-east-1')
        conn.create_bucket(Bucket="test-bucket")
        conn.Object("test-bucket", "test-key").put(Body="test-body")

        files = self.s3.filter_objects(prefix_="test")
        self.assertEqual(files, ["test-key"])
    
    @mock_s3
    def test_upload_in_memory_object(self):
        in_memory_object = BytesIO(b"test data")
        output_file = "test-output-file"

        with patch('boto3.client') as mock_client:
            mock_client_instance = mock_client.return_value
            mock_upload = mock_client_instance.upload_fileobj = MagicMock()

            self.s3.upload_in_memory_object(output_file, in_memory_object)

            mock_upload.assert_called_once_with(in_memory_object, "test-bucket", output_file)
    
    @mock_s3
    def test_copy_objects(self):
        with patch('boto3.client') as mock_client:
            mock_client_instance = mock_client.return_value
            mock_copy = mock_client_instance.copy_object = MagicMock()

            source_key = "source_key"
            destination_key = "destination_key"
            self.s3.copy_objects(source_key, destination_key)

            mock_copy.assert_called_once_with(Bucket="test-bucket", Key=destination_key, CopySource=f"test-bucket/{source_key}")

    @mock_s3
    def test_download_in_memory_objects(self):
        conn = boto3.resource('s3', region_name='us-east-1')
        conn.create_bucket(Bucket="test-bucket")
        conn.Object("test-bucket", "test-key").put(Body=b"test-body")

        file_data = self.s3.download_in_memory_objects(key="test-key")
        self.assertEqual(file_data.getvalue(), b"test-body")

    @mock_s3
    def test_create_arrangement_file(self):
        with patch('boto3.client') as mock_client:
            mock_client_instance = mock_client.return_value
            mock_get_object = mock_client_instance.get_object = MagicMock()

            # Mock the response of get_object
            mock_get_object.return_value = {'Body': BytesIO(b"test audio data")}

            # Mock the pydub.AudioSegment.from_file method
            with patch.object(pydub.AudioSegment, 'from_file') as mock_from_file:
                # Return a 1-second silent audio segment for testing
                mock_from_file.return_value = pydub.AudioSegment.silent(duration=1000)

                # Call the method with a list of dummy file names
                arrangement = self.s3.create_arrangement_file(["file1", "file2"], format="wav")

                # Verify that the returned arrangement is 2 seconds long (1 second for each file)
                self.assertEqual(len(pydub.AudioSegment.from_file(arrangement, format="wav")), 2000)


class TestSnapshotManager(unittest.TestCase):
    @patch.object(SnapshotManager, '__init__', return_value=None)
    def setUp(self, mock_init):
        self.snapshot_manager = SnapshotManager("test_bucket")

    @patch.object(SnapshotManager, 'resource')
    @patch.object(SnapshotManager, 'client')
    def test_build_snapshot(self, mock_resource, mock_client):
        self.snapshot_manager.build_snapshot()
        mock_resource.Object.assert_called()
        mock_client.put.assert_called()

    @patch.object(SnapshotManager, 'load_snapshot_from_s3')
    @patch.object(SnapshotManager, 'process_snapshot_data')
    @patch.object(SnapshotManager, 'save_snapshot_files_to_s3')
    def test_get_snapshot_data(self, mock_load, mock_process, mock_save):
        self.snapshot_manager.get_snapshot_data()
        mock_load.assert_called()
        mock_process.assert_called()
        mock_save.assert_called()

    @patch.object(SnapshotManager, 'resource')
    def test_load_snapshot_from_s3(self, mock_resource):
        self.snapshot_manager.load_snapshot_from_s3()
        mock_resource.Object.assert_called()

    def test_process_snapshot_data(self):
        self.snapshot_manager.snapshot_df = mock.Mock()
        self.snapshot_manager.process_snapshot_data()
        self.snapshot_manager.snapshot_df.str.endswith.assert_called()

    @patch.object(SnapshotManager, 'resource')
    def test_save_snapshot_files_to_s3(self, mock_resource):
        self.snapshot_manager.save_snapshot_files_to_s3()
        mock_resource.Object.assert_called()

    @patch.object(SnapshotManager, 'client')
    def test_generate_presigned_urls(self, mock_client):
        self.snapshot_manager.generate_presigned_urls()
        mock_client.generate_presigned_url.assert_called()

if __name__ == "__main__":
    unittest.main()