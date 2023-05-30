import unittest
from unittest.mock import patch, Mock, mock_open, MagicMock
from app.mixer.mixer import MixEngine, MixRunner, JobConfig, StorageEngine, SequenceEngine
import numpy as np

class TestMixEngine(unittest.TestCase):

    @patch('os.listdir')
    @patch('pickle.load')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)  # ensure we're mocking the correct 'open'
    @patch('pydub.AudioSegment')
    def test_mix_sequences_pkl(self, mock_AudioSegment, mock_open, mock_exists, mock_pickle_load, mock_listdir):
        # setup
        mock_job_params = Mock(spec=JobConfig)
        mock_job_params.get_job_params.return_value = {"bpm": 120}
        mock_job_params.path_resolver.return_value = {"local_path_mixdown_wav_master": "/tmp/test_output.wav"}
        mock_job_params.random_id = "12345"
        mock_listdir.return_value = ["mixdown_12345.pkl", "mixdown_12345.pkl", "mixdown_12345.pkl", "mixdown_12345.pkl", "mixdown_12345.pkl", "mixdown_12345.pkl"]
        mock_pickle_load.side_effect = [
            np.array([0.06873822, 0.0775969 , 0.11674154]), 
            np.array([-0.00858092, -0.01676106, -0.02365756]),
            np.array([0.00524747, -0.01671952, -0.00353223]),
            np.array([-0.11494309, -0.16739362, -0.19740874]),
            np.array([-0.18956006, -0.18455303, -0.17906487]),
            np.array([0.07217887, 0.07220143, 0.07216715])
        ]
        mock_exists.return_value = True
        mix_engine = MixEngine(mock_job_params)

        # execution
        result = mix_engine.mix_sequences_pkl()

        # validation
        self.assertTrue(result)


    @patch('os.system')
    @patch('os.path.exists')
    @patch('glob.glob')
    def test_mix_sequences(self, mock_glob, mock_exists, mock_system):
        # setup
        mock_job_params = Mock(spec=JobConfig)
        mock_job_params.random_id = "12345"
        mock_job_params.path_resolver.return_value = {"local_path_mixdown_mp3_master": "/tmp/test_output.mp3"}
        mock_glob.return_value = ["mixdown_12345_1.mp3", "mixdown_12345_2.mp3"]
        mock_exists.return_value = True
        mock_system.return_value = 0
        mix_engine = MixEngine(mock_job_params)

        # execution
        result = mix_engine.mix_sequences()

        # validation
        self.assertTrue(result)


class TestMixRunner(unittest.TestCase):

    @patch('os.remove')
    @patch('glob.glob')
    def test_clean_up(self, mock_glob, mock_remove):
        # setup
        mock_glob.return_value = ["file1", "file2", "file3"]
        mix_runner = MixRunner(1, "12345")

        # execution
        result = mix_runner.clean_up()

        # validation
        self.assertTrue(result)

    @patch('app.mixer.mixer.StorageEngine')
    @patch('app.mixer.mixer.MixEngine')
    @patch('app.mixer.mixer.JobConfig')
    def test_execute(self, mock_JobConfig, mock_MixEngine, mock_StorageEngine):
        # setup
        mock_JobConfig.return_value = Mock(spec=JobConfig)
        mock_MixEngine.return_value = Mock(spec=MixEngine)
        mock_MixEngine.return_value.mix_sequences_pkl.return_value = True
        mock_StorageEngine.return_value = Mock(spec=StorageEngine)
        mix_runner = MixRunner(1, "12345")

        # execution
        result = mix_runner.execute()

        # validation
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()



