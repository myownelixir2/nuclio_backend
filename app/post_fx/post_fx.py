import os
import pickle
import numpy as np
import math
from pydantic import BaseModel, validator
import pedalboard
import random
from app.sequence_generator.generator import SequenceEngine, AudioEngine
from app.storage.storage import StorageEngine
from app.utils.utils import JobConfig
import logging
from typing import Optional

class FxParamsModel(BaseModel):
    """
    Pydantic model for validating audio FX inputs.

    Attributes:
        audio_fx (str): The audio effect to be applied.
    """
    job_id: str
    fx_input: str
    channel_index: str
    selective_mutism_switch: str
    vol: str
    channel_mute_params: str
    selective_mutism_value: str
    preset: Optional[str] = None

    @validator("job_id")
    def job_id_validator(cls, v):
        if "job_ids" not in v:
            raise ValueError("Job id correct")
        return v

    @validator("fx_input")
    def fx_input_validator(cls, v):
        v = v.split("_")
        if len(v) != 6 and ("0", "1", "2", "3","4","5", "6" "F") not in v:
            raise ValueError("mute_params is not correct")
        return v

    @validator("channel_index")
    def index_validator(cls, v):
        v = int(v)
        if v < 0 or v > 5:
            raise ValueError("index input is not correct")
        return v

    @validator("vol")
    def vol_validator(cls, v):
        v = v.split("_")
        v = [int(x) for x in v]
        if max(v) > 100 and len(v):
            raise ValueError("volume is not correct")
        return v

    @validator("channel_mute_params")
    def channel_mute_params_validator(cls, v):
        v = v.split("_")
        if len(v) != 6 and ("T" or "F") not in v:
            raise ValueError("mute_params is not correct")
        return v

    @validator("selective_mutism_switch")
    def selective_mutism_switch_validator(cls, v):
        if v not in ["T", "F"]:
            raise ValueError("selective_mutism_switch is not correct")
        return v

    @validator("selective_mutism_value")
    def selective_mutism_value_validator(cls, v):
        v = float(v)
        if v > 1 or v < 0:
            raise ValueError("selective_mutism is not correct")
        return v


class MuteEngine:
    """
    Class for applying selective mutism to an audio sequence.

    Attributes:
        mix_params: The mix parameters.
        job_params: The job parameters.
    """
    
    def __init__(self, mix_params, job_params):
        self.mix_params = mix_params
        self.job_params = job_params

    def __perc_to_pulse_mapper(self, seq_len, sequence):
        selective_mutism_value = self.mix_params.selective_mutism_value

        if selective_mutism_value == 0:
            return sequence
        else:
            slices = math.ceil(selective_mutism_value * seq_len)
            # TODO: add better wight system
            random_slices = random.sample(range(seq_len), slices)
            for i in random_slices:
                sequence[i] = np.zeros(len(sequence[i]))
            return sequence

    def apply_selective_mutism(self):
        """
        Applies selective mutism to the audio sequence.

        Returns:
            ndarray: The audio sequence with mutism applied.
        """

        pickle_path = self.job_params.path_resolver()["local_path_processed_pkl"]

        with open(pickle_path, "rb") as f:
            my_sequence = pickle.load(f)

        my_sequence = self.__perc_to_pulse_mapper(len(my_sequence), my_sequence)

        return my_sequence


class VolEngine:
    """
    Class for adjusting the volume of an audio sequence.

    Attributes:
        mix_params: The mix parameters.
        job_params: The job parameters.
        my_sequence: The audio sequence to adjust.
    """
    def __init__(self, mix_params, job_params, my_sequence):
        self.mix_params = mix_params
        self.job_params = job_params
        self.pre_processed_sequence = my_sequence

    def apply_volume(self):
        """
        Adjusts the volume of the audio sequence.

        Returns:
            ndarray: The audio sequence with volume adjusted.
        """

        channel_index = int(self.job_params.channel_index)
        bpm = self.job_params.get_job_params()["bpm"]

        my_sequence_unpacked = SequenceEngine.validate_sequence(
            bpm, self.pre_processed_sequence
        )

     
        vol = self.mix_params.vol[channel_index] / 100
        if vol == 0:
            my_sequence_vol_applied = np.zeros(len(my_sequence_unpacked))
        elif vol == 1:
            my_sequence_vol_applied = my_sequence_unpacked
        else:
            my_sequence_vol_applied = np.array(my_sequence_unpacked) * vol

        if vol == 0:
            my_sequence_vol_applied_normalized = my_sequence_vol_applied
        else:
            my_sequence_vol_applied_normalized = (
                2.0
                * (my_sequence_vol_applied - np.min(my_sequence_vol_applied))
                / np.ptp(my_sequence_vol_applied)
                - 1
            )

        return my_sequence_vol_applied_normalized


class FxPedalBoardConfig(BaseModel):
    """
    Pydantic model for validating audio FX inputs.

    Attributes:
        audio_fx (str): The audio effect to be applied.
    """
    audio_fx: str

    @validator("audio_fx")
    def job_id_validator(cls, v):
        if v not in ["Bitcrush", "Chorus", "Delay", "Phaser", "Reverb", "Distortion"]:
            raise ValueError("not allowed FX input")
        return v


class FxPedalBoardEngine:
    """
    Class for applying audio FX using a pedalboard.

    Attributes:
        mix_params: The mix parameters.
        job_params: The job parameters.
        my_sequence: The audio sequence to apply FX to.
    """
    def __init__(self, mix_params, job_params, my_sequence):
        self.mix_params = mix_params
        self.job_params = job_params
        self.my_sequence = my_sequence

    def apply_pedalboard_fx(self):
        """
        Applies the audio FX to the audio sequence.

        Returns:
            bool: True if FX was successfully applied, False otherwise.
        """
        channel_index = int(self.job_params.channel_index)
        fx_input = self.mix_params.fx_input[channel_index]

        if fx_input == "F":
            print("No FX applied")
            self.save_audio(self.my_sequence)
            return True
        else:
            fx_board, fx = self.build_pedalboard(fx_input)
            if not fx_board:
                return False

            effected_audio = self.apply_fx_to_audio(fx_board, fx)
            if effected_audio is None:
                return False

            self.save_audio(effected_audio)
            return True

    def build_pedalboard(self, fx_input):
        """
        Builds the pedalboard for applying the audio FX.

        Args:
            fx_input (str): The audio FX input to use.

        Returns:
            tuple: The built pedalboard and the audio FX.
        """
        fx_mapping = ["Bitcrush", "Chorus", "Delay", "Phaser", "Reverb", "Distortion", "VST_Portal"]
        fx = fx_mapping[int(fx_input)]
        print("printing FX debug", fx)

        if "VST" in fx:
            board = self.build_vst_pedalboard(fx)
        else:
            board = self.build_standard_pedalboard(fx)
        return board, fx

    def build_vst_pedalboard(self, fx):
        """
        Builds a VST pedalboard for applying the audio FX.

        Args:
            fx (str): The audio FX to use.

        Returns:
            Pedalboard: The built VST pedalboard.
        """
        print("using VST FX plugin...")
        my_vst = fx.split("_")[1]
        print(self.mix_params)
        root_folder = os.path.dirname(os.path.abspath(__file__))
        root_folder_sanitized = root_folder.rsplit("/", 2)[0]

        main_path = root_folder_sanitized + "/assets/vsts/" + my_vst.lower() + "/"
        vst_path = main_path + my_vst + ".vst3"
        presets_path = main_path + "presets/"

        if os.path.exists(vst_path):
            print("VST found...")
            vst = pedalboard.load_plugin(vst_path)

            if not self.mix_params.preset:
                raise ValueError("Preset is empty!")
            # my_presets = os.listdir(presets_path)
            selected_preset = presets_path + self.mix_params.preset
            vst.load_preset(selected_preset)

            board = pedalboard.Pedalboard([vst])
            return board
        else:
            print("VST not found...")
            return None

    def build_standard_pedalboard(self, fx):
        """
        Builds a standard pedalboard for applying the audio FX.

        Args:
            fx (str): The audio FX to use.

        Returns:
            Pedalboard: The built standard pedalboard.
        """
        validated_fx = FxPedalBoardConfig.parse_obj({"audio_fx": fx})
        pedalboard_fx = getattr(pedalboard, validated_fx.audio_fx)
        board = pedalboard.Pedalboard([pedalboard_fx()])
        return board
    
    def apply_fx_to_audio(self, fx_board, fx):
        """
        Applies the audio FX to the audio sequence.

        Args:
            fx_board (Pedalboard): The pedalboard to use.
            fx (str): The audio FX to apply.

        Returns:
            ndarray: The audio sequence with FX applied.
        """
        try:
            if "VST" in fx:
                print('applying vst effect...')
                mono_input = self.my_sequence
  
                stereo_audio = np.column_stack((mono_input, mono_input))
                stereo_output = fx_board(stereo_audio, 44100.0)
                effected = np.mean(stereo_output, axis=1)
            else:
                effected = fx_board(self.my_sequence, 44100.0)
        except Exception as e:
            print(e)
            return None
        else:
            y_effected = np.int16(effected * 2**15)
            normalized_y_effected = np.interp(y_effected, (y_effected.min(), y_effected.max()), (-1, +1))
            return normalized_y_effected

    def save_audio(self, audio_data):
        """
        Saves the audio data.

        Args:
            audio_data (ndarray): The audio data to save.
        """
        my_pickle = AudioEngine(
            audio_data,
            self.job_params.path_resolver()["local_path_mixdown_pkl"],
            normalized=True,
        )
        my_pickle.save_to_pkl()

        my_wav = AudioEngine(
            audio_data,
            self.job_params.path_resolver()["local_path_mixdown_wav"],
            normalized=True,
        )
        my_wav.save_to_wav()


class FxRunner:
    """
    Class for managing the application of audio FX.

    Attributes:
        mix_params: The mix parameters.
        job_id: The ID of the job.
        channel_index: The channel index.
        random_id: The random ID.
    """
    def __init__(self, mix_params, job_id, channel_index, random_id):
        self.mix_params = mix_params
        self.job_id = job_id
        self.channel_index = channel_index
        self.random_id = random_id
        self.job_params = JobConfig(self.job_id, self.channel_index, self.random_id)

    def clean_up(self):
        """
        Cleans up the local objects associated with the job.
        """
        try:
            # StorageEngine(self.job_params,'job_id_path').delete_local_object()
            StorageEngine(self.job_params, "mixdown_job_path_pkl").delete_local_object()
            StorageEngine(self.job_params, "mixdown_job_path").delete_local_object()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

    def _apply_mute_engine(self):
        try:
            return MuteEngine(
                self.mix_params, self.job_params
            ).apply_selective_mutism()
        except Exception as e:
            logging.error(f"Error in MuteEngine: {e}")
            raise

    def _apply_vol_engine(self, sequence):
        try:
            return VolEngine(
                self.mix_params, self.job_params, sequence
            ).apply_volume()
        except Exception as e:
            logging.error(f"Error in VolEngine: {e}")
            raise

    def _apply_fx_pedal_board_engine(self, sequence):
        try:
            return FxPedalBoardEngine(
                self.mix_params, self.job_params, sequence
            ).apply_pedalboard_fx()
        except Exception as e:
            logging.error(f"Error in FxPedalBoardEngine: {e}")
            raise

    def execute(self):
        """
        Executes the job of applying selective mutism, volume adjustment, and audio FX.

        Returns:
            bool: True if the job was successfully executed, False otherwise.
        """
        try:
            sequence_mute_applied = self._apply_mute_engine()
            sequence_vol_applied = self._apply_vol_engine(sequence_mute_applied)
            sequence_ready = self._apply_fx_pedal_board_engine(sequence_vol_applied)

            if sequence_ready:
                logging.info("Sequence ready")
                return True
            else:
                logging.error("Sequence not ready")
                return False
        except Exception as e:
            logging.error(f"Error during execution: {e}")
            raise




