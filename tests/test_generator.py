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

    @patch.object(SequenceConfigRefactor, '_extract_note_sequence')
    @patch.object(JobConfig, 'get_job_params')
    def test_get_note_sequence(self, mock_get_job_params, mock_extract_note_sequence):
        # Mock get_job_params return value
        mock_get_job_params.return_value = {'local_paths': 'assets/sounds/PITCH_C__BPM_120__nn2_120_drum_loop_inland_full.mp3',
                                            'cloud_paths': 'loop__drums_full/PITCH_C__BPM_120__nn2_120_drum_loop_inland_full.mp3',
                                            'bpm': 120,
                                            'scale_value': 'dominant-diminished',
                                            'key_value': 'E',
                                            'rythm_config_list': [12, 16],
                                            'pitch_temperature_knob_list': [0]}
        # Mock _extract_note_sequence return value
        mock_extract_note_sequence.return_value = [0, 2, 4, 5, 7, 9, 11, 12]

        result = self.seq_refactor.get_note_sequence()

        self.assertIsInstance(result, list)

    @patch('librosa.load')
    def test_grid_validate(self, mock_load):
        mock_load.return_value = (np.zeros((44100 * 3,)), 44100)
        result = self.seq_refactor.grid_validate()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    @patch('librosa.load')
    def test_get_audio_frames_length(self, mock_load):
        # Mock librosa.load return value
        mock_load.return_value = (np.zeros((44100 * 3,)), 44100)

        result = self.seq_refactor.get_audio_frames_length()
        
        self.assertIsInstance(result, list)

    @patch('librosa.load')
    def test_get_audio_frames_reps(self, mock_load):
        # Mock librosa.load return value
        mock_load.return_value = (np.zeros((44100 * 3,)), 44100)

        result = self.seq_refactor.get_audio_frames_reps()
        self.assertIsInstance(result, list)

    def test_generate_euclidean_rhythm(self):
        result = self.seq_refactor._generate_euclidean_rhythm(8, 12)
        self.assertIsInstance(result, list)
        self.assertEqual(sum(result), 8)
  
    def test_extract_note_sequence(self):
        result = self.seq_refactor._extract_note_sequence("dominant-diminished", "E")
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
    @patch('librosa.load')
    def setUp(self, mock_load):
        # Mock librosa.load return value
        mock_load.return_value = (np.zeros((44100 * 3,)), 44100)

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

        # Adjust mock return values
        self.mock_sequence_config.get_audio_frames_length.return_value = [11025.0, 5512.5, 5512.5, 11025.0, 5512.5, 5512.5, 11025.0, 5512.5, 5512.5, 11025.0, 5512.5, 5512.5]
        self.mock_sequence_config.get_audio_frames_reps.return_value = [22, 11]

        result = self.audio_frame_slicer.get_audio_frame_sequence_list()
        
        # Expected result based on your earlier output
        expected_result = [np.array([     0,   5512,  11024,  16536,  22048,  27560,  33072,  38584,
            44096,  49608,  55120,  60632,  66144,  71656,  77168,  82680,
            88192,  93704,  99216, 104728, 110240, 115752]),
        np.array([    0, 11025, 22050, 33075, 44100, 55125, 66150, 77175, 88200,
            99225])]

        # Compare each array in the list one by one
        for r, e in zip(result, expected_result):
            np.testing.assert_array_equal(r, e)

    def test_frames_list(self):
        result = self.audio_frame_slicer.frames_list([0, 44100], 44100)
        # Check each frame has the expected length
        for frame in result:
            self.assertEqual(len(frame), 44100)

    @patch('librosa.load')
    def test_get_audio_frames(self, mock_load):
        # Mock librosa.load return value
        mock_load.return_value = (np.zeros((44100 * 3,)), 44100)

        result = self.audio_frame_slicer.get_audio_frames()
        
        # Expected lengths
        expected_lengths = [44100, 88200]
        
        # Check each frame group has the expected length
        for frame_group, expected_length in zip(result, expected_lengths):
            for frame in frame_group:
                self.assertEqual(len(frame), expected_length)

class TestSequenceEngine(unittest.TestCase):
    
    @patch('app.sequence_generator.generator.SequenceConfigRefactor')  # Replace with the actual module where SequenceConfig is defined
    @patch('app.sequence_generator.generator.SequenceAudioFrameSlicer')  # Replace with the actual module where AudioFrameSlicer is defined
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
        self.job_params_mock = MagicMock()
        self.job_params_mock.get_job_params.return_value = {
            "local_paths": "/path/to/audio/file.wav",
            "cloud_paths": "loop__drums_full/PITCH_C__BPM_120__nn2_120_drum_loop_inland_full.mp3",
            "bpm": 120,
            "scale_value": "dominant-diminished",
            "key_value": 'E',
            "rythm_config_list": [12, 16],
            "pitch_temperature_knob_list": [0]
        }

        self.engine = SequenceEngine(self.mock_config, self.mock_frames)

    # @patch.object(SequenceConfigRefactor, 'get_audio_frames_length')
    # @patch.object(SequenceAudioFrameSlicer, 'get_audio_frames')
    # def test_generate_audio_sequence_auto(self, mock_get_audio_frames, mock_get_audio_frames_length):
    #     """
    #     Test the generate_audio_sequence_auto method.
    #     """

    #     # Mocking get_audio_frames_length return value
    #     mock_get_audio_frames_length.return_value = [11025.0, 5512.5, 5512.5, 11025.0, 5512.5, 5512.5]

    #     # Mocking get_audio_frames return value
    #     mock_get_audio_frames.return_value = [[np.random.rand(10) for _ in range(5)], [np.random.rand(20) for _ in range(5)]]

    #     # Call the method under test
    #     result = self.engine.generate_audio_sequence_auto()

    #     # Perform your assertions
    #     # Here, we'll just check that the method doesn't return None
    #     # Update this based on your requirements
    #     self.assertIsNotNone(result)

    #     # Check that the mock methods were called
    #     self.mock_config.get_audio_frames_length.assert_called_once()
    #     self.mock_frames.get_audio_frames.assert_called_once()
    #     self.mock_random_choice.assert_called()
    
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
    
    @patch('librosa.load')
    @patch.object(SequenceConfigRefactor, 'get_audio_frames_length')
    @patch.object(SequenceConfigRefactor, 'get_note_sequence')
    @patch.object(SequenceAudioFrameSlicer, 'get_audio_frames')
    def test_generate_audio_sequence(self, mock_get_audio_frames, mock_get_note_sequence, mock_get_audio_frames_length, mock_load):
        # Mocking librosa.load return value
        mock_load.return_value = (np.zeros((44100 * 3,)), 44100)

        # Mocking get_audio_frames_length return value
        mock_get_audio_frames_length.return_value = [11025.0, 5512.5, 5512.5, 11025.0, 5512.5, 5512.5]

        # Mocking get_audio_frames return value
        mock_get_audio_frames.return_value = [[np.random.rand(10) for _ in range(5)], [np.random.rand(20) for _ in range(5)]]

        # Mocking get_note_sequence return value
        mock_get_note_sequence.return_value = [0, 2, 4, 5, 7, 9, 11, 12]

        # Creating an instance of your class under test
        sequence_config_refactor = SequenceConfigRefactor(self.job_params_mock)
        audio_frame_slicer = SequenceAudioFrameSlicer(sequence_config_refactor)
        engine = SequenceEngine(sequence_config_refactor, audio_frame_slicer)

        # Calling the method under test
        result = engine.generate_audio_sequence()

        # Checking the result
        self.assertIsNotNone(result)

        # Assert the mock methods were called
        mock_get_audio_frames_length.assert_called_once()
        mock_get_audio_frames.assert_called_once()
        mock_get_note_sequence.assert_called_once()

class TestAudioEngine(unittest.TestCase):
    @patch('app.sequence_generator.generator.librosa.load')  
    def test_read_audio(self, mock_load):
        mock_load.return_value = (np.array([1, 2, 3]), 44100)
        ae = AudioEngine(None, 'dummy/path')
        result = ae.read_audio()
        mock_load.assert_called_once_with('dummy/path', sr=44100)
        
        # compare the arrays and sampling rates separately
        np.testing.assert_array_equal(result[0], np.array([1, 2, 3]))
        self.assertEqual(result[1], 44100)


    @patch('app.sequence_generator.generator.pickle.dump')  
    @patch('builtins.open', new_callable=mock_open)
    def test_save_to_pkl(self, mock_open, mock_dump):
        ae = AudioEngine(np.array([1, 2, 3]), 'dummy/path.mp3')
        ae.save_to_pkl()
        mock_open.assert_called_once_with('dummy/path.pkl', 'wb')

        # Get the arguments passed to mock_dump
        args, _ = mock_dump.call_args

        # Compare the numpy arrays and file objects separately
        np.testing.assert_array_equal(args[0], np.array([1, 2, 3]))
        self.assertEqual(args[1], mock_open.return_value.__enter__.return_value)

    @patch('app.sequence_generator.generator.sf.write') 
    def test_save_to_wav(self, mock_write):
        ae = AudioEngine(np.array([1, 2, 3]), 'dummy/path')
        ae.save_to_wav()

        # Get the arguments passed to mock_write
        args, _ = mock_write.call_args

        # Compare the numpy arrays and file path separately
        np.testing.assert_array_equal(args[1], np.array([1, 2, 3]))
        self.assertEqual(args[0], 'dummy/path')
        self.assertEqual(args[2], 44100)

    @patch('app.sequence_generator.generator.pydub.AudioSegment') 
    def test_save_to_mp3(self, mock_AudioSegment):
        mock_AudioSegment_instance = mock_AudioSegment.return_value
        mock_AudioSegment_instance.export = MagicMock()

        ae = AudioEngine(np.array([1, 2, 3]), 'dummy/path')
        ae.save_to_mp3()

        mock_AudioSegment.assert_called_once()
        mock_AudioSegment_instance.export.assert_called_once_with('dummy/path', format='mp3', bitrate='128k')

class TestJobRunner(unittest.TestCase):
    @patch('app.sequence_generator.generator.StorageEngine')
    @patch('app.sequence_generator.generator.JobConfig')
    def setUp(self, mock_job_config, mock_storage_engine):
        self.mock_job_config = mock_job_config
        self.mock_storage_engine = mock_storage_engine
        self.mock_storage_engine.return_value = self.mock_storage_engine

        # Mock the path_resolver method to return a dictionary with a key 'asset_path'.
        self.mock_job_config.return_value.path_resolver.return_value = {'local_path': 'some/path',
                                                                        'cloud_path': 'some/cloud/path',
                                                                        'local_path_processed_pkl': 'some/other/path'}

        self.job_runner = JobRunner('folder/job_id.json', 0, 'random_id')
    
    @patch.object(StorageEngine, 'client_init', return_value=None)
    @patch.object(StorageEngine, 'get_object', return_value=True)   
    def test_get_assets(self, mock_get_object, mock_client_init):
    
        self.job_runner.get_assets()
        self.assertEqual(mock_get_object.call_count, 2)

    @patch('app.sequence_generator.generator.SequenceConfigRefactor')
    @patch('app.sequence_generator.generator.SequenceAudioFrameSlicer')
    @patch('app.sequence_generator.generator.SequenceEngine')
    def test_validate(self, mock_sequence_engine, mock_audio_frame_slicer, mock_sequence_config):
        mock_instance = mock_sequence_engine.return_value
        mock_instance.generate_audio_sequence.return_value = ('validated_audio_sequence', 'audio_sequence')
        
        validated_audio_sequence, audio_sequence = self.job_runner.validate()
        self.assertEqual(validated_audio_sequence, 'validated_audio_sequence')
        self.assertEqual(audio_sequence, 'audio_sequence')

    def test_result(self):
        self.mock_job_config.return_value.path_resolver.return_value = {"cloud_path_processed": "cloud_path_processed"}
        result = self.job_runner.result(True)
        self.assertEqual(result, "cloud_path_processed")


    @patch('app.sequence_generator.generator.StorageEngine.delete_local_object')
    def test_clean_up(self, mock_delete_local_object):
        self.job_runner.job_params = self.mock_job_config.return_value
        self.job_runner.clean_up()
        mock_delete_local_object.assert_called_once()

    @patch('app.sequence_generator.generator.AudioEngine')
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
