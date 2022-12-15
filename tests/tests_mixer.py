import unittest
from unittest.mock import patch
import os
from app.mixer.mixer import MixEngine

 
class TestMixSequencesPKL(unittest.TestCase):
    def setUp(self):
        # Set up any necessary objects, variables, etc. before each test
        #self.job_params = JobParams()
        self.job_params.random_id = 123456
        self.job_params.get_job_params = lambda: {"bpm": 120}
        self.job_params.path_resolver = lambda: {"local_path_mixdown_mp3_master": "temp/output.mp3"}

    @patch("mix_sequences_pkl.SequenceEngine.validate_sequence")
    def test_mix_sequences_pkl(self, mock_validate_sequence):
        # Test the mix_sequences_pkl method
        # Set up the mock to return a valid sequence
        mock_validate_sequence.return_value = [1, 2, 3, 4, 5, 6]

        result = MixEngine.mix_sequences_pkl(self)
        self.assertTrue(result)
        self.assertTrue(os.path.exists("temp/output.mp3"))


