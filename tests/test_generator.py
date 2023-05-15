import unittest
from unittest.mock import Mock, patch, mock_open, MagicMock
import numpy as np
from app.storage.storage import StorageEngine
from app.utils.utils import JobConfig
from app.sequence_generator.generator import (SequenceConfigRefactor,
                                              SequenceAudioFrameSlicer,
                                              SequenceEngine,
                                              AudioEngine,
                                              JobRunner)

class TestSequenceConfigRefactor(unittest.TestCase):
    def setUp(self):
        self.job_params_mock = MagicMock()
        self.job_params_mock.get_job_params.return_value = {
            "rythm_config_list": [8, 12],
            "scale_value": 'A',
            "key_value": 'B',
            "bpm": 120,
            "local_paths": "/path/to/audio/file.wav",
        }
        self.seq_refactor = SequenceConfigRefactor(self.job_params_mock)

    def test_euclead_rhythm_generator(self):
        result = self.seq_refactor.euclead_rhythm_generator()
        self.assertIsInstance(result, list)

    def test_get_note_sequence(self):
        result = self.seq_refactor.get_note_sequence()
        self.assertIsInstance(result, list)

    def test_grid_validate(self):
        result = self.seq_refactor.grid_validate()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_get_audio_frames_length(self):
        result = self.seq_refactor.get_audio_frames_length()
        self.assertIsInstance(result, list)

    def test_get_audio_frames_reps(self):
        result = self.seq_refactor.get_audio_frames_reps()
        self.assertIsInstance(result, list)

    def test_generate_euclidean_rhythm(self):
        result = self.seq_refactor._generate_euclidean_rhythm(8, 12)
        self.assertIsInstance(result, list)
        self.assertEqual(sum(result), 8)

    def test_extract_note_sequence(self):
        result = self.seq_refactor._extract_note_sequence('A', 'B')
        self.assertIsInstance(result, list)

    def test_load_audio(self):
        self.seq_refactor._load_audio = MagicMock(return_value=np.array([0, 1, 0, 1]))
        result = self.seq_refactor._load_audio("/path/to/audio/file.wav")
        self.assertIsInstance(result, np.ndarray)

    def test_validate_grid(self):
        self.seq_refactor._load_audio = MagicMock(return_value=np.array([0, 1, 0, 1]))
        result = self.seq_refactor._validate_grid(np.array([0, 1, 0, 1]), 120, 12)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_calculate_audio_frames_length(self):
        result = self.seq_refactor._calculate_audio_frames_length([1, 0, 0, 1, 0], 2)
        self.assertIsInstance(result, list)

    def test_calculate_audio_frames_reps(self):
        result = self.seq_refactor._calculate_audio_frames_reps(10, [1, 2, 3, 4, 5])
        self.assertIsInstance(result, list)

class TestSequenceAudioFrameSlicer(unittest.TestCase):
    def setUp(self):
        # Mocking SequenceConfigRefactor to isolate testing to SequenceAudioFrameSlicer
        self.mock_sequence_config = Mock()
        self.mock_sequence_config.get_audio_frames_length.return_value = [44100, 88200]
        self.mock_sequence_config.get_audio_frames_reps.return_value = [1, 2]
        self.mock_sequence_config.job_params.get_job_params.return_value = {"local_paths": "path/to/audio.wav"}

        self.audio_frame_slicer = SequenceAudioFrameSlicer(self.mock_sequence_config)

    @patch('librosa.load')
    def test_get_audio_frame_sequence_list(self, mock_load):
        # Mock librosa.load return value
        mock_load.return_value = (np.zeros((44100 * 3,)), 44100)

        result = self.audio_frame_slicer.get_audio_frame_sequence_list()
        
        expected_result = [np.arange(0, 44100, 44100), np.arange(0, 88200 * 2, 88200)]
        
        np.testing.assert_equal(result, expected_result)

    @patch('librosa.load')
    def test_frames_list(self, mock_load):
        # Mock librosa.load return value
        mock_load.return_value = (np.zeros((44100 * 3,)), 44100)

        result = self.audio_frame_slicer.frames_list([0, 44100], 44100)
        
        # Check each frame has the expected length
        for frame in result:
            self.assertEqual(len(frame), 44100)

    @patch('librosa.load')
    def test_get_audio_frames(self, mock_load):
        # Mock librosa.load return value
        mock_load.return_value = (np.zeros((44100 * 3,)), 44100)

        result = self.audio_frame_slicer.get_audio_frames()
        
        # Check each frame has the expected length
        for frame_group in result:
            for frame in frame_group:
                self.assertEqual(len(frame), 44100 * len(frame_group))

class TestSequenceEngine(unittest.TestCase):
    
    @patch('your_module.SequenceConfig')  # Replace with the actual module where SequenceConfig is defined
    @patch('your_module.AudioFrameSlicer')  # Replace with the actual module where AudioFrameSlicer is defined
    @patch('numpy.random.choice')
    @patch('librosa.effects.pitch_shift')
    def setUp(self, mock_pitch_shift, mock_random_choice, mock_config, mock_frames):
        """
        Setup for the tests.
        We initialize our sequence_config and audio_frames mocks here.
        """
        self.mock_pitch_shift = mock_pitch_shift
        self.mock_random_choice = mock_random_choice
        self.mock_config = mock_config
        self.mock_frames = mock_frames

        # Set up some return values for the mocks
        self.mock_config.get_audio_frames_length.return_value = np.array([44100, 88200, 132300])
        self.mock_frames.get_audio_frames.return_value = np.array([1, 2, 3])
        self.mock_random_choice.return_value = np.array([1, 2, 3])
        self.mock_pitch_shift.return_value = np.array([1, 2, 3])

        self.engine = SequenceEngine(self.mock_config, self.mock_frames)

    def test_generate_audio_sequence_auto(self):
        """
        Test the generate_audio_sequence_auto method.
        """
        # Call the method under test
        result = self.engine.generate_audio_sequence_auto()

        # Perform your assertions
        # Here, we'll just check that the method doesn't return None
        # Update this based on your requirements
        self.assertIsNotNone(result)

        # Check that the mock methods were called
        self.mock_config.get_audio_frames_length.assert_called_once()
        self.mock_frames.get_audio_frames.assert_called_once()
        self.mock_random_choice.assert_called()
    
    @patch('numpy.zeros')
    @patch('numpy.append')
    def test_validate_sequence(self, mock_append, mock_zeros):
        """
        Test the validate_sequence method of the SequenceEngine class.
        """
        mock_zeros.return_value = [0, 0, 0]
        mock_append.return_value = [1, 2, 3, 0, 0, 0]

        # Initialize the SequenceEngine with None for config and frames, as they aren't used in this method.
        engine = SequenceEngine(None, None)

        # Define a test bpm and sequence
        bpm = 120
        new_sequence = [1, 2, 3]

        # Call the method under test
        result = engine.validate_sequence(bpm, new_sequence)

        # Perform your assertions
        # Here, we'll just check that the method doesn't return None
        # Update this based on your requirements
        self.assertIsNotNone(result)

        # Check that the mock methods were called
        mock_zeros.assert_called_once()
        mock_append.assert_called_once()
    
    @patch('your_module.SequenceEngine.validate_sequence')  # Path to validate_sequence
    @patch('your_module.SequenceEngine.__apply_pitch_shift')  # Path to __apply_pitch_shift
    @patch('random.choices')
    @patch('your_module.SequenceEngine.__unpack_multi_level_list')  # Path to __unpack_multi_level_list
    def test_generate_audio_sequence(self, mock_unpack, mock_choices, mock_pitch_shift, mock_validate):
        """
        Test the generate_audio_sequence method of the SequenceEngine class.
        """
        # Mock the return values of the external functions
        mock_unpack.return_value = [1, 2, 3]
        mock_choices.return_value = [1, 2, 3]
        mock_pitch_shift.return_value = [1, 2, 3]
        mock_validate.return_value = [1, 2, 3]

        # Mock the sequence_config and audio_frames objects
        mock_config = MagicMock()
        mock_frames = MagicMock()

        # Mock the return values of the sequence_config methods
        mock_config.get_audio_frames_length.return_value = [1, 2, 3]
        mock_config.get_note_sequence.return_value = [1, 2, 3]
        mock_config.job_params.get_job_params.return_value = {'bpm': 120, 'pitch_temperature_knob_list': [0]}

        # Mock the return values of the audio_frames methods
        mock_frames.get_audio_frames.return_value = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

        # Create the SequenceEngine instance
        engine = SequenceEngine(mock_config, mock_frames)

        # Call the method under test
        validated_sequence, updated_sequence = engine.generate_audio_sequence()

        # Perform your assertions
        # Here, we'll just check that the method doesn't return None
        # Update this based on your requirements
        self.assertIsNotNone(validated_sequence)
        self.assertIsNotNone(updated_sequence)

        # Check that the mock methods were called
        mock_unpack.assert_called_once()
        mock_choices.assert_called()
        mock_pitch_shift.assert_called()
        mock_validate.assert_called_once()

class TestAudioEngine(unittest.TestCase):
    @patch('your_module.librosa.load')  # Replace 'your_module' with the actual module name
    def test_read_audio(self, mock_load):
        mock_load.return_value = (np.array([1, 2, 3]), 44100)
        ae = AudioEngine(None, 'dummy/path')
        result = ae.read_audio()
        mock_load.assert_called_once_with('dummy/path', sr=44100)
        self.assertEqual(result, (np.array([1, 2, 3]), 44100))

    @patch('your_module.pickle.dump')  # Replace 'your_module' with the actual module name
    @patch('builtins.open', new_callable=mock_open)
    def test_save_to_pkl(self, mock_open, mock_dump):
        ae = AudioEngine(np.array([1, 2, 3]), 'dummy/path.mp3')
        ae.save_to_pkl()
        mock_open.assert_called_once_with('dummy/path.pkl', 'wb')
        mock_dump.assert_called_once_with(np.array([1, 2, 3]), mock_open.return_value.__enter__.return_value)

    @patch('your_module.sf.write')  # Replace 'your_module' with the actual module name
    def test_save_to_wav(self, mock_write):
        ae = AudioEngine(np.array([1, 2, 3]), 'dummy/path')
        ae.save_to_wav()
        mock_write.assert_called_once_with('dummy/path', np.array([1, 2, 3]), 44100)

    @patch('your_module.pydub.AudioSegment')  # Replace 'your_module' with the actual module name
    def test_save_to_mp3(self, mock_AudioSegment):
        mock_AudioSegment_instance = mock_AudioSegment.return_value
        mock_AudioSegment_instance.export = MagicMock()

        ae = AudioEngine(np.array([1, 2, 3]), 'dummy/path')
        ae.save_to_mp3()

        mock_AudioSegment.assert_called_once()
        mock_AudioSegment_instance.export.assert_called_once_with('dummy/path', format='mp3', bitrate='128k')

class TestJobRunner(unittest.TestCase):
    @patch('generator.StorageEngine')
    @patch('generator.JobConfig')
    def setUp(self, mock_job_config, mock_storage_engine):
        self.mock_job_config = mock_job_config
        self.mock_storage_engine = mock_storage_engine
        self.job_runner = JobRunner('job_id', 0, 'random_id')
        
    def test_get_assets(self):
        self.job_runner.get_assets()
        self.mock_storage_engine.assert_any_call(self.mock_job_config.return_value, "job_id_path")
        self.mock_storage_engine.assert_any_call(self.mock_job_config.return_value, "asset_path")
        self.assertEqual(self.mock_storage_engine.return_value.get_object.call_count, 2)

    @patch('generator.SequenceConfigRefactor')
    @patch('generator.SequenceAudioFrameSlicer')
    @patch('generator.SequenceEngine')
    def test_validate(self, mock_sequence_config, mock_audio_frame_slicer, mock_sequence_engine):
        mock_sequence_engine.return_value.generate_audio_sequence.return_value = ('validated_audio_sequence', 'audio_sequence')
        validated_audio_sequence, audio_sequence = self.job_runner.validate()
        self.assertEqual(validated_audio_sequence, 'validated_audio_sequence')
        self.assertEqual(audio_sequence, 'audio_sequence')

    def test_result(self):
        self.mock_job_config.return_value.path_resolver.return_value = {"cloud_path_processed": "cloud_path_processed"}
        result = self.job_runner.result(True)
        self.assertEqual(result, "cloud_path_processed")

    def test_clean_up(self):
        self.job_runner.clean_up()
        self.mock_storage_engine.assert_called_with(self.mock_job_config.return_value, "asset_path")
        self.mock_storage_engine.return_value.delete_local_object.assert_called_once()

    @patch('generator.AudioEngine')
    def test_execute(self, mock_audio_engine):
        with patch.object(self.job_runner, 'get_assets') as mock_get_assets, \
             patch.object(self.job_runner, 'validate') as mock_validate:
            mock_validate.return_value = ('validated_audio_sequence', 'audio_sequence')
            result = self.job_runner.execute()
            mock_get_assets.assert_called_once()
            mock_validate.assert_called_once()
            mock_audio_engine.assert_called_with('audio_sequence',
                                                 self.mock_job_config.return_value.path_resolver.return_value["local_path_processed_pkl"],
                                                 normalized=None)
            self.assertTrue(result)

if __name__ == "__main__":
    unittest.main()
