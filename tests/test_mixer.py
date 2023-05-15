import unittest
from unittest.mock import patch, Mock
from app.mixer.mixer import MixEngine, MixRunner, JobConfig


class TestMixEngine(unittest.TestCase):

    @patch('os.listdir')
    @patch('pickle.load')
    @patch('os.path.exists')
    @patch('pydub.AudioSegment')
    def test_mix_sequences_pkl(self, mock_AudioSegment, mock_exists, mock_pickle_load, mock_listdir):
        # setup
        mock_job_params = Mock(spec=JobConfig)
        mock_job_params.get_job_params.return_value = {"bpm": 120}
        mock_job_params.path_resolver.return_value = {"local_path_mixdown_wav_master": "/tmp/test_output.wav"}
        mock_job_params.random_id = "12345"
        mock_listdir.return_value = ["mixdown_12345.pkl"]
        mock_pickle_load.return_value = []
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

    @patch('app.mixer_engine.StorageEngine')
    @patch('app.mixer_engine.MixEngine')
    @patch('app.mixer_engine.JobConfig')
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



