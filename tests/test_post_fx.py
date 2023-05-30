import io
import unittest
from pydantic import ValidationError
import unittest
import pickle
from unittest.mock import MagicMock, patch, Mock, mock_open
import numpy as np
from app.post_fx.post_fx import (
    FxParamsModel, 
    MuteEngine, 
    VolEngine, 
    FxPedalBoardConfig,
    FxPedalBoardEngine,
    FxRunner
    )

class TestFxParamsModel(unittest.TestCase):
    def setUp(self):
        self.valid_data = {
            'job_id': 'job_ids',
            'fx_input': '0_1_2_3_4_F',
            'channel_index': '3',
            'selective_mutism_switch': 'T',
            'vol': '50_50_50_50_50_50',
            'channel_mute_params': 'T_T_T_T_T_T',
            'selective_mutism_value': '0.5'
        }

    def test_valid_data(self):
        FxParamsModel(**self.valid_data)

    def test_invalid_job_id(self):
        self.valid_data['job_id'] = 'wrong'
        with self.assertRaises(ValidationError):
            FxParamsModel(**self.valid_data)

    def test_invalid_fx_input(self):
        self.valid_data['fx_input'] = 'invalid'
        with self.assertRaises(ValidationError):
            FxParamsModel(**self.valid_data)

    def test_invalid_channel_index(self):
        self.valid_data['channel_index'] = '6'
        with self.assertRaises(ValidationError):
            FxParamsModel(**self.valid_data)

    def test_invalid_vol(self):
        self.valid_data['vol'] = '101_101_101_101_101_101'
        with self.assertRaises(ValidationError):
            FxParamsModel(**self.valid_data)

    def test_invalid_channel_mute_params(self):
        self.valid_data['channel_mute_params'] = 'invalid'
        with self.assertRaises(ValidationError):
            FxParamsModel(**self.valid_data)

    def test_invalid_selective_mutism_switch(self):
        self.valid_data['selective_mutism_switch'] = 'invalid'
        with self.assertRaises(ValidationError):
            FxParamsModel(**self.valid_data)

    def test_invalid_selective_mutism_value(self):
        self.valid_data['selective_mutism_value'] = '1.5'
        with self.assertRaises(ValidationError):
            FxParamsModel(**self.valid_data)

class TestMuteEngine(unittest.TestCase):
    @patch('pickle.load')
    @patch('builtins.open', new_callable=mock_open)
    def test_apply_selective_mutism(self, mock_open, mock_load):
        # Mock the sequence loaded from pickle
        mock_sequences = [
            np.array([1, 2, 3, 4, 5]),
            np.array([6, 7, 8, 9, 10]),
            np.array([11, 12, 13, 14, 15]),
            # Add as many mock sequences as needed
        ]
        mock_load.return_value = mock_sequences

        # Mock mix_params and job_params
        mock_mix_params = MagicMock()
        mock_mix_params.selective_mutism_value = 0.3
        mock_job_params = MagicMock()
        mock_job_params.path_resolver.return_value = {"local_path_processed_pkl": "some_path"}

        mute_engine = MuteEngine(mock_mix_params, mock_job_params)
        result_sequences = mute_engine.apply_selective_mutism()

        # Check that approximately 30% of the sequences have been zeroed out
        zero_sequences = sum(1 for sequence in result_sequences if np.all(sequence == 0))
        expected_zero_sequences = round(mock_mix_params.selective_mutism_value * len(mock_sequences))
        self.assertEqual(zero_sequences, expected_zero_sequences)



class TestVolEngine(unittest.TestCase):
    @patch('app.post_fx.post_fx.SequenceEngine.validate_sequence')
    def test_apply_volume(self, mock_validate_sequence):
        # Mock the sequence validated from SequenceEngine
        mock_sequence = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        mock_validate_sequence.return_value = mock_sequence

        # Mock mix_params and job_params
        mock_mix_params = MagicMock()
        mock_mix_params.vol = [100, 75, 50, 25, 0]  # Testing for different volume levels
        mock_job_params = MagicMock()
        mock_job_params.channel_index = '1'
        mock_job_params.get_job_params.return_value = {"bpm": 120}

        # Testing for different volume levels
        for i in range(5):
            mock_job_params.channel_index = str(i)
            vol_engine = VolEngine(mock_mix_params, mock_job_params, mock_sequence)
            result_sequence = vol_engine.apply_volume()

            # Check that the sequence has been correctly adjusted according to the volume level
            if mock_mix_params.vol[i] != 0:
                expected_sequence = mock_sequence * (mock_mix_params.vol[i] / 100)
                expected_sequence = 2.0 * (expected_sequence - np.min(expected_sequence)) / np.ptp(expected_sequence) - 1
            else:
                expected_sequence = np.zeros_like(mock_sequence)

            np.testing.assert_almost_equal(result_sequence, expected_sequence, decimal=5)



class TestFxPedalBoardConfig(unittest.TestCase):
    def test_audio_fx_validator(self):
        # Check that valid audio_fx values pass the validation
        for fx in ["Bitcrush", "Chorus", "Delay", "Phaser", "Reverb", "Distortion"]:
            try:
                FxPedalBoardConfig(audio_fx=fx)
            except ValidationError:
                self.fail(f"ValidationError raised for valid audio_fx value {fx}")

        # Check that invalid audio_fx values raise a ValidationError
        with self.assertRaises(ValidationError):
            FxPedalBoardConfig(audio_fx="InvalidFx")

class TestFxPedalBoardEngine(unittest.TestCase):
    def setUp(self):
        self.mix_params = Mock()
        self.job_params = Mock()
        self.my_sequence = Mock()

        self.engine = FxPedalBoardEngine(self.mix_params, self.job_params, self.my_sequence)

    @patch.object(FxPedalBoardEngine, 'save_audio')
    def test_apply_pedalboard_fx_no_fx(self, mock_save_audio):
        self.job_params.channel_index = '0'
        self.mix_params.fx_input = ['F']

        result = self.engine.apply_pedalboard_fx()

        self.assertTrue(result)
        mock_save_audio.assert_called_once_with(self.my_sequence)

    @patch.object(FxPedalBoardEngine, 'build_pedalboard', return_value=(Mock(), 'Bitcrush'))
    @patch.object(FxPedalBoardEngine, 'apply_fx_to_audio', return_value=Mock())
    @patch.object(FxPedalBoardEngine, 'save_audio')
    def test_apply_pedalboard_fx_with_fx(self, mock_save_audio, mock_apply_fx_to_audio, mock_build_pedalboard):
        self.job_params.channel_index = '0'
        self.mix_params.fx_input = ['0']

        result = self.engine.apply_pedalboard_fx()

        self.assertTrue(result)
        mock_build_pedalboard.assert_called_once_with('0')
        mock_apply_fx_to_audio.assert_called_once()
        mock_save_audio.assert_called_once()


class TestFxRunner(unittest.TestCase):
    def setUp(self):
        self.mix_params = Mock()
        self.job_id = "123"
        self.channel_index = "0"
        self.random_id = "456"

        self.runner = FxRunner(self.mix_params, self.job_id, self.channel_index, self.random_id)
    
    @patch.object(FxPedalBoardEngine, 'apply_pedalboard_fx', return_value=True)
    @patch.object(VolEngine, 'apply_volume', return_value=Mock())
    @patch.object(MuteEngine, 'apply_selective_mutism', return_value=Mock())
    def test_execute(self, mock_mute_engine, mock_vol_engine, mock_fx_pedalboard_engine):
        result = self.runner.execute()

        self.assertTrue(result)
        mock_mute_engine.assert_called_once_with()
        mock_vol_engine.assert_called_once_with()
        mock_fx_pedalboard_engine.assert_called_once_with()

    @patch.object(FxPedalBoardEngine, 'apply_pedalboard_fx', return_value=False)
    @patch.object(VolEngine, 'apply_volume', return_value=Mock())
    @patch.object(MuteEngine, 'apply_selective_mutism', return_value=Mock())
    def test_execute_sequence_not_ready(self, mock_mute_engine, mock_vol_engine, mock_fx_pedalboard_engine):
        result = self.runner.execute()

        self.assertFalse(result)
        mock_mute_engine.assert_called_once_with()
        mock_vol_engine.assert_called_once_with()
        mock_fx_pedalboard_engine.assert_called_once_with()

class TestFxRunner2(unittest.TestCase):

    @patch('app.post_fx.post_fx.MuteEngine')
    @patch('app.post_fx.post_fx.VolEngine')
    @patch('app.post_fx.post_fx.FxPedalBoardEngine')
    def test_execute_success(self, mock_fx_pedal_board_engine, mock_vol_engine, mock_mute_engine):
        # Arrange
        mix_params = {}  # Your mix params
        job_id = "job1"
        channel_index = 0
        random_id = "random1"

        mock_mute_engine.return_value.apply_selective_mutism.return_value = "mute_sequence"
        mock_vol_engine.return_value.apply_volume.return_value = "vol_sequence"
        mock_fx_pedal_board_engine.return_value.apply_pedalboard_fx.return_value = True

        runner = FxRunner(mix_params, job_id, channel_index, random_id)

        # Act
        result = runner.execute()

        # Assert
        self.assertTrue(result)
        mock_mute_engine.assert_called_once_with(mix_params, runner.job_params)
        mock_vol_engine.assert_called_once_with(mix_params, runner.job_params, "mute_sequence")
        mock_fx_pedal_board_engine.assert_called_once_with(mix_params, runner.job_params, "vol_sequence")

    @patch('app.post_fx.post_fx.MuteEngine')
    def test_execute_failure_in_mute_engine(self, mock_mute_engine):
        # Arrange
        mix_params = {}  # Your mix params
        job_id = "job1"
        channel_index = 0
        random_id = "random1"

        mock_mute_engine.return_value.apply_selective_mutism.side_effect = Exception('mute_engine_error')

        runner = FxRunner(mix_params, job_id, channel_index, random_id)

        # Act & Assert
        with self.assertRaises(Exception) as context:
            runner.execute()
        self.assertTrue('mute_engine_error' in str(context.exception))


if __name__ == '__main__':
    unittest.main()
