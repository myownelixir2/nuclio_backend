
import boto3
import glob
import logging
import zipfile
import io
import pandas as pd
from moto import mock_s3
from moto.server import ThreadedMotoServer
from app.storage.storage import (StorageEngine, 
                                 StoreEngineMultiFile, 
                                 StorageEngineDownloader,
                                 SnapshotManager)
import os
from botocore.exceptions import ClientError
from unittest.mock import patch, MagicMock
import unittest
from io import BytesIO
import pydub

@mock_s3
class TestStorageEngine(unittest.TestCase):
    
    def setUp(self):
        # Start the mock S3 service
        self.mock_s3 = mock_s3()
        self.mock_s3.start()

        # Mocking os.environ
        self.mocked_environ = patch.dict(os.environ, {
            "STORAGE_URL": "https://example.com",
            "STORAGE_KEY": "your-access-key",
            "STORAGE_SECRET": "your-secret-key"
        })

        # Start the patch
        self.mocked_environ.start()

        # Create a test bucket
        self.bucket_name = "test-bucket"
        self.s3_client = boto3.client("s3", region_name='us-east-1')
        self.s3_resource = boto3.resource("s3", region_name='us-east-1')  # This is new
        self.s3_client.create_bucket(Bucket=self.bucket_name)

        mock_job_config = MagicMock()
        mock_job_config.path_resolver.return_value = {
            'cloud_path': 'tests/file.txt',
            'local_path': 'tests/file.txt'
        }

        # Initialize StorageEngine with test bucket
        self.storage_engine = StorageEngine(job_config=mock_job_config, asset_type="job_id_path", 
                                            bucket=self.bucket_name, client=self.s3_client, resource=self.s3_resource)
    def tearDown(self):
        # Stop the mock S3 service
        self.mocked_environ.stop()
        self.mock_s3.stop()
        
        # Remove the 'test/file.txt' file if it exists
        if os.path.exists("tests/file.txt"):
            os.remove("tests/file.txt")


    def test_get_object(self):
        # Upload a test file to the bucket
        test_file_key = "tests/file.txt"
        self.s3_client.put_object(Bucket=self.bucket_name, Key=test_file_key, Body=b"Test file content")
        
        # Check the existence of the file in the bucket
        
        # Call get_object method
        self.storage_engine.get_object(bucket_name=self.bucket_name)

        # Assert that the file was downloaded successfully
        self.assertTrue(os.path.exists("tests/file.txt"))

    def test_get_object_error(self):
        # Call get_object method without setting up the bucket

        # Assert that the method raises an exception
        with self.assertRaises(ClientError) as cm:
            self.storage_engine.get_object(bucket_name=self.bucket_name)

        # Check that the exception message includes '404'
        self.assertIn('404', str(cm.exception))

    def test_delete_local_object(self):
        # Create a test file to delete
        test_file_path = "tests/file.txt"
        with open(test_file_path, "w") as file:
            file.write("Test file content")

        # Call delete_local_object method
        self.storage_engine.delete_local_object()

        # Assert that the file was deleted successfully
        self.assertFalse(os.path.exists(test_file_path))

    def test_upload_object_local(self):
        # Create a test file to upload
        test_file_path = "tests/file.txt"
        with open(test_file_path, "w") as file:
            file.write("Test file content")

        # Call upload_object_local method
        self.storage_engine.upload_object_local(local_path=test_file_path, cloud_path="test/file.txt", bucket_name=self.bucket_name)

        # Assert that the file was uploaded successfully
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key="test/file.txt")
        self.assertEqual(response["Body"].read(), b"Test file content")

    def test_upload_object(self):
        # Create a test file to upload
        test_file_path = "tests/file.txt"
        with open(test_file_path, "w") as file:
            file.write("Test file content")

        # Call upload_object method
        self.storage_engine.upload_object(bucket_name=self.bucket_name)

        # Assert that the file was uploaded successfully
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key="tests/file.txt")
        self.assertEqual(response["Body"].read(), b"Test file content")

@mock_s3
class TestStoreEngineMultiFile(unittest.TestCase):
    
    def setUp(self):
        self.server = ThreadedMotoServer()
        self.server.start()
        # Start the mock S3 service
        self.mock_s3 = mock_s3()
        self.mock_s3.start()

        self.logger = logging.getLogger(__name__)

        # Mocking os.environ
        self.mocked_environ = patch.dict(os.environ, {
            "STORAGE_URL": "http://127.0.0.1:5000",
            "STORAGE_KEY": "your-access-key",
            "STORAGE_SECRET": "your-secret-key"
        })

        # Start the patch
        self.mocked_environ.start()
        

        # Create a test bucket
        self.bucket_name = "bucket-test"
        self.resource = boto3.resource("s3", region_name='us-east-1')
        self.client = boto3.client("s3", region_name='us-east-1')

        self.client.create_bucket(Bucket=self.bucket_name)
        self.job_id = '123'
        self.store_engine = StoreEngineMultiFile(self.job_id, bucket=self.bucket_name, resource=self.resource)

    def tearDown(self):
        # Stop the mock S3 service
        self.mocked_environ.stop()
        self.mock_s3.stop()
        self.server.stop()

        for file in glob.glob('tests/*.txt'):
            try:
                os.remove(file)
            except OSError as e:
                self.logger.error(f"Error removing file {file}: {e}")

    def test_upload_list_of_objects(self):
        # Create some temporary files for testing

        files = []
        for i in range(3):
            with open(f'tests/test_upload_{i}.txt', 'w') as f:
                f.write('This is a test file.')
                files.append(f.name)

        bucket_path = 'test'
        status = self.store_engine.upload_list_of_objects(files, bucket_path)

        # Assert upload status
        self.assertTrue(status)

        # Assert files are in the bucket
        response = self.client.list_objects(Bucket=self.bucket_name)

        s3_files = [item['Key'] for item in response['Contents']]
        for file in files:
            self.assertIn(os.path.join(bucket_path, os.path.basename(file)), s3_files)


@mock_s3
class TestStorageEngineDownloader(unittest.TestCase):
    
    def setUp(self):
        self.server = ThreadedMotoServer()
        self.server.start()
        # Start the mock S3 service
        self.mock_s3 = mock_s3()
        self.mock_s3.start()

        self.logger = logging.getLogger(__name__)

        # Mocking os.environ
        self.mocked_environ = patch.dict(os.environ, {
            "STORAGE_URL": "http://127.0.0.1:5000",
            "STORAGE_KEY": "your-access-key",
            "STORAGE_SECRET": "your-secret-key"
        })

        # Start the patch
        self.mocked_environ.start()
        

        # Create a test bucket
        self.bucket_name = "bucket-test"
        self.resource = boto3.resource("s3", region_name='us-east-1')
        self.client = boto3.client("s3", region_name='us-east-1')
        self.client.create_bucket(Bucket=self.bucket_name) 

        self.client.put_object(Bucket=self.bucket_name, Key="test-key", Body=b"Test file content")
        
        self.storage_downloader = StorageEngineDownloader(bucket=self.bucket_name, client=self.client, resource=self.resource)

    def tearDown(self):
        # Stop the mock S3 service
        self.mocked_environ.stop()
        self.mock_s3.stop()
        self.server.stop()

  
    def test_filter_objects(self):
        
        files = self.storage_downloader.filter_objects(prefix_="test")
        self.assertEqual(files, ["test-key"])
    

    def test_upload_in_memory_object(self):
        in_memory_object = BytesIO(b"test data")
        output_file = "test-output-file"
        self.client.upload_fileobj = MagicMock()
   
        self.storage_downloader.upload_in_memory_object(output_file, in_memory_object)
        
        self.client.upload_fileobj.assert_called_once_with(in_memory_object, self.bucket_name, output_file)
    
 
    def test_copy_objects(self):
        self.client.copy_object = MagicMock()

        source_key = "source_key"
        destination_key = "destination_key"
        self.storage_downloader.copy_objects(source_key, destination_key)

        self.client.copy_object.assert_called_once_with(Bucket=self.bucket_name, Key=destination_key, CopySource=f"bucket-test/{source_key}")

    

    def test_download_in_memory_objects(self):

        file_data = self.storage_downloader.download_in_memory_objects(key="test-key")
        self.assertEqual(file_data.getvalue(), b"Test file content")


    def test_create_arrangement_file(self):
        self.client.get_object = MagicMock()
        # Set the mock return value
        self.client.get_object.return_value = {'Body': BytesIO(b"test audio data")}

        # Mock the pydub.AudioSegment.from_file method
        with patch.object(pydub.AudioSegment, 'from_file') as mock_from_file:
            # Return a 1-second silent audio segment for testing
            mock_from_file.return_value = pydub.AudioSegment.silent(duration=1000)

            # Call the method with a list of dummy file names
            self.storage_downloader.create_arrangement_file(["file1", "file2"], format="wav")

            # Verify that the returned arrangement is 2 seconds long (1 second for each file)
            #self.assertEqual(len(pydub.AudioSegment.from_file(arrangement, format="wav")), 2000)
            assert mock_from_file.call_count == 2

    
  
    def test_create_zip_file(self):
        # Mock a response for the get_object call
        self.client.get_object = MagicMock()
        self.client.get_object.return_value = {"Body": BytesIO(b"file content")}

        # Generate a list of dummy file keys
        file_keys = ["file1.txt", "file2.txt"]

        # Call the method under test
        in_memory_zip = self.storage_downloader.create_zip_file(file_keys)

        # Now, we want to check that the returned in_memory_zip indeed contains the expected files
        with zipfile.ZipFile(in_memory_zip) as zip_file:
            zip_files = zip_file.namelist()

        # Check that the zip file contains the expected files
        self.assertEqual(set(file_keys), set(zip_files))
        
        # Check that the get_object was called twice
        self.assertEqual(self.client.get_object.call_count, 2)

        # Check each call was made with the correct arguments
        self.client.get_object.assert_any_call(Bucket=self.bucket_name, Key="file1.txt")
        self.client.get_object.assert_any_call(Bucket=self.bucket_name, Key="file2.txt")
    
 
    def test_get_presigned_url(self):
        # Mock the generate_presigned_url method of client
        self.client.generate_presigned_url = MagicMock()
        self.client.generate_presigned_url.return_value = "https://presigned-url.com"

        # Call the method under test
        presigned_url = self.storage_downloader.get_presigned_url("test_file.txt", expires_in=100)

        # Assert that the presigned_url is as expected
        self.assertEqual(presigned_url, "https://presigned-url.com")

        # Assert that generate_presigned_url was called with correct arguments
        self.client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": "test_file.txt"},
            ExpiresIn=100,
        )

  
    def test_upload_and_get_presigned_url(self):
        # Mock the upload_fileobj and generate_presigned_url methods of client
        self.client.upload_fileobj = MagicMock()
        self.client.generate_presigned_url = MagicMock()
        self.client.generate_presigned_url.return_value = "https://presigned-url.com"

        # Prepare an in-memory zip file for testing
        in_memory_zip = BytesIO()
        with zipfile.ZipFile(in_memory_zip, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("test_file.txt", b"test data")
        in_memory_zip.seek(0)

        # Call the method under test
        presigned_url = self.storage_downloader.upload_and_get_presigned_url("test.zip", in_memory_zip, expires_in=300)

        # Assert that the presigned_url is as expected
        self.assertEqual(presigned_url, "https://presigned-url.com")

        # Assert that upload_fileobj and generate_presigned_url were called with correct arguments
        self.client.upload_fileobj.assert_called_once_with(in_memory_zip, self.bucket_name, "test.zip")
        self.client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": "test.zip"},
            ExpiresIn=300,
        )

@mock_s3
class TestSnapshotManager(unittest.TestCase):
    
    def setUp(self):
        # logging.basicConfig(level=logging.DEBUG)
        # logging.getLogger('boto3').setLevel(logging.DEBUG)
        # logging.getLogger('botocore').setLevel(logging.DEBUG)
        # logging.getLogger('moto').setLevel(logging.DEBUG)

        # self.server = ThreadedMotoServer()
        # self.server.start()
        self.mock_s3 = mock_s3()
        self.mock_s3.start()

        self.logger = logging.getLogger(__name__)

        # Mocking os.environ
        self.mocked_environ = patch.dict(os.environ, {
            "STORAGE_URL": "http://127.0.0.1:5000",
            "STORAGE_KEY": "your-access-key",
            "STORAGE_SECRET": "your-secret-key"
        })

        # Start the patch
        self.mocked_environ.start()

        self.bucket_name = "sample-dump"
        self.resource = boto3.resource("s3", region_name='us-east-1')
        self.client = boto3.client("s3", region_name='us-east-1')
        self.client.create_bucket(Bucket=self.bucket_name)
        self.client.create_bucket(Bucket='snapshots-dump')

        # create some objects in the bucket
        for i in range(5):
            self.client.put_object(Bucket=self.bucket_name, Key=f'file{i}.txt', Body=b"some data")
        self.snapshot_manager = SnapshotManager(bucket=self.bucket_name, client=self.client, resource=self.resource)


    def tearDown(self):
        # Clear all the S3 resources in order to isolate tests
        bucket = self.resource.Bucket(self.bucket_name)
        for key in bucket.objects.all():
            key.delete()
        bucket.delete()
        self.mocked_environ.stop()
        self.mock_s3.stop()
        # self.server.stop()

    def test_build_snapshot(self):

        
        print(self.snapshot_manager)
        # call the method under test
        result = self.snapshot_manager.build_snapshot()

        # check that the CSV was correctly uploaded
        s3_key = self.snapshot_manager.SNAPSHOT_CSV
        csv_obj = self.resource.Object(self.snapshot_manager.SNAPSHOTS_DUMP_BUCKET, s3_key).get()['Body']
        csv_data = csv_obj.read().decode('utf-8')
        expected_csv_data = (
            'paths\n'
            'file0.txt\n'
            'file1.txt\n'
            'file2.txt\n'
            'file3.txt\n'
            'file4.txt\n'
        )
        self.assertEqual(csv_data, expected_csv_data)

        # check the method's return value
        self.assertTrue(result)

        # check that the snapshot DataFrame was correctly created
        expected_df = pd.DataFrame([f'file{i}.txt' for i in range(5)], columns=['paths'])
        pd.testing.assert_frame_equal(self.snapshot_manager.snapshot_df, expected_df)

    @patch.object(SnapshotManager, 'load_snapshot_from_s3')
    @patch.object(SnapshotManager, 'process_snapshot_data')
    @patch.object(SnapshotManager, 'save_snapshot_files_to_s3')
    def test_get_snapshot_data_success(self, mock_save, mock_process, mock_load):
        # Mock the methods so they don't actually do anything
        mock_load.return_value = None
        mock_process.return_value = None
        mock_save.return_value = None

        snapshot_manager = SnapshotManager(bucket='test_bucket', client=None, resource=None)
        result = snapshot_manager.get_snapshot_data()

        self.assertTrue(result)
        mock_load.assert_called_once()
        mock_process.assert_called_once()
        mock_save.assert_called_once()

    @patch.object(SnapshotManager, 'load_snapshot_from_s3', side_effect=ClientError({}, ''))
    def test_get_snapshot_data_failure(self, mock_load):
        snapshot_manager = SnapshotManager(bucket='test_bucket', client=None, resource=None)

        with self.assertRaises(ClientError):
            snapshot_manager.get_snapshot_data()

        mock_load.assert_called_once()

    @patch('pandas.read_csv')
    def test_load_snapshot_from_s3(self, mock_read_csv):
      
        self.resource.Object(self.bucket_name, 'database_snapshot.csv').put(Body='some data')

        # Check that there's no DataFrame before we call the method
        self.assertIsNone(self.snapshot_manager.snapshot_df)

        # Now call the method
        self.snapshot_manager.load_snapshot_from_s3()

        # Assuming that read_csv works correctly, the DataFrame should now be set
        self.assertIsNotNone(self.snapshot_manager.snapshot_df)

    def test_process_snapshot_data(self):
        # Setting up the mock snapshot_df with some 'label' values in FILTER_OUT_LABELS
        data = {
            'paths': ['sequences/file1.mp3', 'favourite/file2.mp3', 'my_favourites/file3.mp3', 'mixdown/file4.mp3', 'other/file5.mp3'],
            'other_column': [1, 2, 3, 4, 5]  # just an example, replace with actual other columns
        }
        self.snapshot_manager.snapshot_df = pd.DataFrame(data)

        # Call the method under test
        self.snapshot_manager.process_snapshot_data()

        # Assert that snapshot_files_df is filtered correctly
        assert all(~self.snapshot_manager.snapshot_files_df['label'].isin(self.snapshot_manager.FILTER_OUT_LABELS))
        
        # Assert the remaining labels in snapshot_files_df
        assert set(self.snapshot_manager.snapshot_files_df['label']) == set(['other'])
    
    def test_save_snapshot_files_to_s3(self):
        # Given
   
        self.snapshot_manager.snapshot_files_df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        csv_buffer = io.StringIO()
        self.snapshot_manager.snapshot_files_df.to_csv(csv_buffer, index=False)
        expected_body = csv_buffer.getvalue()

        # Mock S3 resource and Object
        mock_s3_resource = MagicMock()
        mock_s3_object = MagicMock()

        # Mock the resource.Object() method call and make it return mock_s3_object
        mock_s3_resource.Object.return_value = mock_s3_object

        self.snapshot_manager.resource = mock_s3_resource

        # When
        self.snapshot_manager.save_snapshot_files_to_s3()

        # Then
        # Assert the resource.Object() method was called with the expected parameters
        mock_s3_resource.Object.assert_called_once_with(self.snapshot_manager.SNAPSHOTS_DUMP_BUCKET, 
                                                        self.snapshot_manager.SNAPSHOT_FILES_CSV)

        # Assert the object.put() method was called with the expected Body
        mock_s3_object.put.assert_called_once_with(Body=expected_body)

    def test_generate_presigned_urls(self):
     
        # Mock S3 client
        mock_s3_client = MagicMock()
        self.snapshot_manager.client = mock_s3_client

        # Define the mocked response of generate_presigned_url
        mock_s3_client.generate_presigned_url.return_value = "http://mock-url"

        # When
        url_1, url_2 = self.snapshot_manager.generate_presigned_urls()

        # Then
        params1 = {'Bucket': self.snapshot_manager.SNAPSHOTS_DUMP_BUCKET, 'Key': self.snapshot_manager.SNAPSHOT_CSV}
        params2 = {'Bucket': self.snapshot_manager.SNAPSHOTS_DUMP_BUCKET, 'Key': self.snapshot_manager.SNAPSHOT_FILES_CSV}
        mock_s3_client.generate_presigned_url.assert_any_call('get_object', Params=params1, ExpiresIn=3600)
        mock_s3_client.generate_presigned_url.assert_any_call('get_object', Params=params2, ExpiresIn=3600)

        assert url_1 == "http://mock-url"
        assert url_2 == "http://mock-url"

if __name__ == "__main__":
    unittest.main()