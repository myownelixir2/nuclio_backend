import unittest
from pydantic import ValidationError
from app.utils.utils import JobTypeValidator, JobConfig, JobUtils, JobCleanUp, purge_all
import os
import json
import itertools
import glob

class TestJobTypeValidator(unittest.TestCase):
    def test_valid_job_types(self):
        valid_job_types = [
            "job_id_path",
            "processed_job_path",
            "asset_path",
            "mixdown_job_path",
            "mixdown_job_path_master",
            "mixdown_job_path_pkl",
        ]

        for job_type in valid_job_types:
            with self.subTest(job_type=job_type):
                try:
                    JobTypeValidator(job_type=job_type)
                except ValidationError:
                    self.fail(f"ValidationError raised for valid job_type: {job_type}")

    def test_invalid_job_type(self):
        with self.assertRaises(ValidationError):
            JobTypeValidator(job_type="invalid_job_type")

class TestJobConfig(unittest.TestCase):
    def setUp(self):
        self.job_id = 'temp/test.json'
        self.channel_index = 1
        self.random_id = 'random1'
        self.job_config = JobConfig(self.job_id, self.channel_index, self.random_id)
        # write a sample json file for testing
        with open(self.job_id, 'w') as f:
            json.dump(["test"], f)

    def tearDown(self):
        os.remove(self.job_id)

    def test_has_initial_index(self):
        self.assertTrue(self.job_config.has_initial_index(self.job_id))
        self.assertFalse(self.job_config.has_initial_index('invalid/path'))

    def test_path_resolver(self):
        paths = self.job_config.path_resolver()
        self.assertIn('cloud_path', paths)
        self.assertIn('local_path', paths)

    def test_psuedo_json_to_dict(self):
        result = self.job_config.__psuedo_json_to_dict()
        self.assertIsInstance(result, list)

class TestJobUtils(unittest.TestCase):
    def test_sanitize_job_id(self):
        job_id = 'job_ids/test.json'
        sanitized_job_id = JobUtils.sanitize_job_id(job_id)
        self.assertEqual(sanitized_job_id, 'test')

    def test_list_files_matching_pattern(self):
        files = JobUtils.list_files_matching_pattern(['*.py'], '.', 'test')
        self.assertIn('test_job_utils.py', files)

    def test_remove_files(self):
        # write a sample file for testing
        with open('temp_test_file', 'w') as f:
            f.write('test')
        self.assertTrue(JobUtils.remove_files(['temp_test_file']))
        self.assertFalse(os.path.exists('temp_test_file'))

class TestJobCleanUp(unittest.TestCase):
    def setUp(self):
        # Create temporary files for testing
        self.asset_file = 'assets/sounds/test.mp3'
        with open(self.asset_file, 'w') as f:
            f.write('test')

        self.temp_file = 'temp/test.pkl'
        with open(self.temp_file, 'w') as f:
            f.write('test')

    def tearDown(self):
        # Clean up temporary files after testing
        os.remove(self.asset_file)
        os.remove(self.temp_file)

    def test_assets(self):
        job_cleanup = JobCleanUp('job_id')
        status = job_cleanup.assets()
        self.assertTrue(all(status))

    def test_temp(self):
        job_cleanup = JobCleanUp('job_id')
        status = job_cleanup.temp()
        self.assertTrue(all(status))

class TestPurgeAll(unittest.TestCase):
    def setUp(self):
        # Create temporary files for testing
        self.temp_files = [
            'temp/file1.txt',
            'temp/file2.txt',
            'temp/file3.pkl',
            'temp/file4.json',
            'temp/file5.mp3',
        ]
        for file in self.temp_files:
            with open(file, 'w') as f:
                f.write('test')

    def tearDown(self):
        # Clean up temporary files after testing
        for file in self.temp_files:
            os.remove(file)

    def test_purge_all(self):
        my_paths = ['temp']
        my_patterns = ['*.txt', '*.pkl']
        result = purge_all(my_paths, my_patterns)

        files_remaining = list(itertools.chain(*(glob.glob(os.path.join(path, ext)) for path in my_paths for ext in my_patterns)))
        self.assertFalse(files_remaining)
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()