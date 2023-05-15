import pandas as pd
import pickle
import librosa
import soundfile as sf
import numpy as np
import math
import pydub
from typing import List, Optional
from collections import Counter
import random
#from app.storage.storage import *
from app.storage.storage import StorageEngine
from app.utils.utils import JobConfig
import logging


#### SEQUENCE ENGINE ####

class SequenceConfigRefactor:
    """This class is used to handle the configuration of audio sequences."""
    def __init__(self, job_params):
        """
        Initialize the SequenceConfigRefactor with job parameters.

        :param job_params: parameters for the job
        """
        self.job_params = job_params
        self.sample_rate = 44100

    def euclead_rhythm_generator(self) -> list:
        """
        Generate a Euclidean rhythm based on the rhythm configuration.

        :return: A list representing the generated rhythm.
        """
        rhythm_config = self.job_params.get_job_params()["rythm_config_list"]
        return self._generate_euclidean_rhythm(rhythm_config[0], rhythm_config[1])

    def get_note_sequence(self) -> list:
        """
        Generate a note sequence based on the scale and key values.

        :return: A list representing the note sequence.
        """
        scale_value = self.job_params.get_job_params()["scale_value"]
        keynote = self.job_params.get_job_params()["key_value"]
        return self._extract_note_sequence(scale_value, keynote)

    def grid_validate(self):
        """
        Validate the grid based on bpm and rhythm configuration.

        :return: Grid value and pulse length samples.
        """
        bpm = self.job_params.get_job_params()["bpm"]
        rhythm_config = self.job_params.get_job_params()["rythm_config_list"]
        audio = self._load_audio(self.job_params.get_job_params()["local_paths"])
        return self._validate_grid(audio, bpm, rhythm_config[1])

    def get_audio_frames_length(self) -> list:
        """
        Calculate the length of audio frames based on pulse sequence and pulse length samples.

        :return: A list representing the length of audio frames.
        """
        pulse_sequence = self.euclead_rhythm_generator()
        __, pulse_length_samples = self.grid_validate()
        return self._calculate_audio_frames_length(pulse_sequence, pulse_length_samples)

    def get_audio_frames_reps(self) -> list:
        """
        Calculate the repetitions of audio frames based on grid value and audio frames lengths.

        :return: A list representing the number of repetitions for each audio frame.
        """
        grid_value, __ = self.grid_validate()
        audio_frames_lens = self.get_audio_frames_length()
        return self._calculate_audio_frames_reps(grid_value, audio_frames_lens)

    # Private methods

    def _generate_euclidean_rhythm(self, n: int, k: int) -> list:
        """
        Generate a Euclidean rhythm based on given n and k values.

        :param n: The number of pulses in the rhythm.
        :param k: The number of steps the rhythm should be fitted into.
        :return: A list representing the generated rhythm.
        """
        data = [[1 if i < n else 0] for i in range(k)]
        while True:
            k = k - n
            if k <= 1:
                break
            elif k < n:
                n, k = k, n
            for i in range(n):
                data[i] += data[-1]
                del data[-1]
        return [x for y in data for x in y]

    def _extract_note_sequence(self, scale_value, keynote) -> list:
        """
        Extract a note sequence based on scale value and keynote.

        :param scale_value: The scale value.
        :param keynote: The keynote.
        :return: A list representing the note sequence.
        """
        notes_match_table = pd.read_pickle("app/sequence_generator/notes_match_table.pkl")
        notes_sequence_raw = notes_match_table.query("scale_name==@scale_value & key==@keynote").filter(["notes"])
        notes_sequence_extracted_str = notes_sequence_raw["notes"].values[0].split(", ")
        notes_sequence_extracted_int = [int(i) for i in notes_sequence_extracted_str]
        notes_sequence_extracted_int_octave_down = [(i - 12) for i in notes_sequence_extracted_int]
        return notes_sequence_extracted_int_octave_down + notes_sequence_extracted_int

    def _load_audio(self, path):
        """
        Load audio from given path.

        :param path: The path to the audio file.
        :return: The loaded audio.
        """
        audio, _ = librosa.load(path, sr=self.sample_rate)
        return audio

    def _validate_grid(self, audio, bpm, k):
        """
        Validate the grid based on audio, bpm and k values.

        :param audio: The audio sequence.
        :param bpm: The beats per minute.
        :param k: The number of steps.
        :return: Grid value and pulse length samples.
        """
        one_bar = 60 / bpm * 4
        pulse_length_samples = self.sample_rate * one_bar / k
        equal_to_total = True if (math.floor(len(audio) / pulse_length_samples)) <= 1 else False
        grid_value = len(audio) if equal_to_total else math.floor(len(audio) / pulse_length_samples) * pulse_length_samples - pulse_length_samples
        return grid_value, pulse_length_samples

    def _calculate_audio_frames_length(self, pulse_sequence, pulse_length_samples):
        """
        Calculate the length of audio frames based on pulse sequence and pulse length samples.

        :param pulse_sequence: The sequence of pulses.
        :param pulse_length_samples: The length of a pulse in samples.
        :return: A list representing the length of audio frames.
        """
        onsets_loc = [i for i, e in enumerate(pulse_sequence) if e == 1]
        onsets_loc_arr = np.array(onsets_loc)
        silence_loc_arr_temp = np.subtract(onsets_loc_arr[1:], 1)
        silence_loc_arr = np.append(silence_loc_arr_temp, len(pulse_sequence) - 1)

        audio_frames_lengths = []
        for onsets, silence in zip(onsets_loc_arr, silence_loc_arr):
            audio_frames_lengths.append((silence - onsets + 1) * pulse_length_samples)
        return audio_frames_lengths

    def _calculate_audio_frames_reps(self, grid_value, audio_frames_lens):
        """
        Calculate the repetitions of audio frames based on grid value and audio frames lengths.

        :param grid_value: The grid value.
        :param audio_frames_lens: The lengths of audio frames.
        :return: A list representing the number of repetitions for each audio frame.
        """
        unique_audio_frame_lengths = np.unique(audio_frames_lens)

        audio_frame_rep_nr = []
        for i in range(len(unique_audio_frame_lengths)):
            reps_value = grid_value / unique_audio_frame_lengths[i]
            if reps_value < 1:
                my_reps = math.ceil(reps_value)
            else:
                my_reps = math.floor(reps_value)

            audio_frame_rep_nr.append(my_reps)
        return audio_frame_rep_nr


class SequenceAudioFrameSlicer:
    
    def __init__(self, sequence_config):
        """
        Initialize the SequenceAudioFrameSlicer with sequence configuration.

        :param sequence_config: An instance of SequenceConfigRefactor class.
        """
        self.sequence_config = sequence_config
        self.audio, _ = librosa.load(
            self.sequence_config.job_params.get_job_params()["local_paths"], sr=44100
        )

    def get_audio_frame_sequence_list(self):
        """
        Generate a list of sequences based on audio frame lengths and repetitions.

        :return: A list of numpy arrays containing the sequences.
        """
        audio_frames_lengths = self.sequence_config.get_audio_frames_length()
        audio_frames_reps = self.sequence_config.get_audio_frames_reps()
        unique_audio_frames_lengths = np.unique(audio_frames_lengths)

        sequence_l = []
        for audio_lengths, audio_reps in zip(unique_audio_frames_lengths, audio_frames_reps):
            stop_range = int(audio_lengths * (1 if audio_lengths * audio_reps - audio_lengths == 0 else audio_reps - 1))
            sequence_l.append(np.arange(0, stop_range, int(audio_lengths)))
        return sequence_l

    def frames_list(self, individual_frames: list, unique_frame_length: float):
        """
        Slice the audio into frames based on the individual frames and unique frame length.

        :param individual_frames: A list of individual frames.
        :param unique_frame_length: The unique length of the frame.
        :return: A list of numpy arrays containing the sliced audio frames.
        """
        sliced_frames = []

        if unique_frame_length > len(self.audio):
            self.audio = np.append(self.audio, np.zeros(int(unique_frame_length) - len(self.audio)))

        for frame in individual_frames:
            sliced_frames.append(self.audio[int(frame):int(frame) + int(unique_frame_length)])
        return sliced_frames

    def get_audio_frames(self):
        """
        Generate a list of audio frames.

        :return: A list of lists containing numpy arrays of sliced audio frames.
        """
        sequence_l = self.get_audio_frame_sequence_list()
        unique_audio_frames_lengths = np.unique(self.sequence_config.get_audio_frames_length())
        return [self.frames_list(x, y) for x, y in zip(sequence_l, map(int, unique_audio_frames_lengths))]



class SequenceEngine:
    """
    This class is used to generate, validate and manipulate audio sequences.
    """
    def __init__(self, sequence_config, audio_frames):
        """
        Initialize the SequenceEngine with sequence configuration and audio frames.

        :param sequence_config: An instance of SequenceConfigRefactor that contains the job parameters.
        :param audio_frames: An instance of AudioFrameSlicer that contains the audio frames.
        """
        self.audio_frames = audio_frames
        self.sequence_config = sequence_config

    def get_job_params(self):
        return self.sequence_config.job_params.get_job_params()

    @staticmethod
    def validate_sequence(bpm, new_sequence):
        """
        Validates the sequence based on bpm and the new sequence. 

        :param bpm: Beats per minute.
        :param new_sequence: The newly generated sequence.
        :return: The validated sequence.
        """
        one_bar = 60 / bpm * 4
        original_sample_len = round(44100 * one_bar)

        new_sequence_unpacked = [
            item for sublist in new_sequence for item in sublist
        ] if isinstance(new_sequence[0], list) else new_sequence

        new_sequence_len = len(new_sequence_unpacked)

        if new_sequence_len < original_sample_len:
            empty_array = np.zeros(original_sample_len - new_sequence_len)
            validated_sequence = np.append(new_sequence_unpacked, empty_array)
        else:
            validated_sequence = new_sequence_unpacked[:original_sample_len]
        return validated_sequence

    @staticmethod
    def __unpack_multi_level_list(my_list):
        """
        Unpacks a multi-level list into a flat list.

        :param my_list: The multi-level list to unpack.
        :return: The unpacked list.
        """
        return [element for sublist in my_list for element in sublist]

    def __pitch_shift(self, audio, pitch_shift):
        """
        Apply a pitch shift to the given audio.

        :param audio: The audio data to shift.
        :param pitch_shift: The number of half-steps to shift the pitch.
        :return: The pitch-shifted audio data.
        """
        return librosa.effects.pitch_shift(audio, sr=44100, n_steps=pitch_shift)

    def __apply_pitch_shift(self, audio_frames: List[float], pitch_shift: Optional[list]):
        """
        Applies a pitch shift to each audio frame based on the given pitch shift list.

        :param audio_frames: The audio frames to shift.
        :param pitch_shift: The list of half-steps to shift each frame.
        :return: The list of pitch-shifted audio frames.
        """
        pitch_temperature = self.get_job_params()["pitch_temperature_knob_list"][0]

        if pitch_temperature and random.random() > pitch_temperature / 100:
            return [
                self.__pitch_shift(audio_frame, shift)
                for audio_frame, shift in zip(audio_frames, pitch_shift)
            ]
        return audio_frames

    def generate_audio_sequence(self):
        """
        Generates an audio sequence based on the sequence configuration and audio frames.

        :return: The generated audio sequence.
        """
        my_audio_frames_lengths = self.sequence_config.get_audio_frames_length()
        my_audio_frames = self.audio_frames.get_audio_frames()

        occurences_of_distinct_frames = Counter(map(int, my_audio_frames_lengths))

        new_audio_sequence = [
            random.choices(my_audio_frames[i], k=nr_elements_to_select)
            for i, nr_elements_to_select in enumerate(occurences_of_distinct_frames.values())
        ]

        new_sequence_unlisted = self.__unpack_multi_level_list(new_audio_sequence)

        note_sequence = self.sequence_config.get_note_sequence()
        note_sequence_updated = random.choices(note_sequence, k=len(new_sequence_unlisted))

        bpm = self.get_job_params()["bpm"]

        updated_new_audio_sequence = self.__apply_pitch_shift(new_sequence_unlisted, note_sequence_updated)
        validated_audio_sequence = self.validate_sequence(bpm, updated_new_audio_sequence)

        return validated_audio_sequence, updated_new_audio_sequence

    def generate_audio_sequence_auto(self):
        """
        Generates an audio sequence automatically based on the audio frames and their lengths.

        :return: The generated audio sequence.
        """
        audio_frames = self.audio_frames.get_audio_frames()
        audio_frames_lengths = self.sequence_config.get_audio_frames_length()
        unique_audio_frames_lengths = np.unique(audio_frames_lengths)

        audio_frames_sequence = [
            np.random.choice(audio_frame, int(unique_length), replace=False)
            for audio_frame, unique_length in zip(audio_frames, unique_audio_frames_lengths)
        ]

        return self.__unpack_multi_level_list(audio_frames_sequence)


##### AUDIO ENGINE #####


class AudioEngine:
    """
    The AudioEngine class provides functionality for loading, saving, and processing audio data.

    Attributes:
        audio_sequence (np.ndarray): The validated audio sequence.
        file_loc (str): The location of the audio file.
        normalized (bool): Whether the audio data is normalized.
    """
    def __init__(self, validated_audio_sequence, file_loc, normalized=False):
        """
        The constructor for the AudioEngine class.

        Parameters:
            validated_audio_sequence (np.ndarray): The validated audio sequence.
            file_loc (str): The location of the audio file.
            normalized (bool, optional): Whether the audio data is normalized. Default is False.
        """

        self.audio_sequence = validated_audio_sequence
        self.file_loc = file_loc
        self.normalized = normalized

    def read_audio(self):
        """
        Reads audio from the provided file location using librosa.

        Returns:
            tuple: A tuple containing the audio time series and the sampling rate.
        """

        return librosa.load(self.file_loc, sr=44100)

    def save_to_pkl(self):
        """
        Saves the audio sequence to a pickle file.

        The file is saved at the same location as the original audio file, but with a .pkl extension.
        """
        pkl_file = self.file_loc.replace(".mp3", ".pkl")
        try:
            with open(pkl_file, "wb") as f:
                pickle.dump(self.audio_sequence, f)
        except IOError as e:
            print(f"Could not save to {pkl_file}. IOError: {e}")

    def save_to_wav(self):
        """
        Saves the audio sequence to a .wav file using the soundfile library.

        The file is saved at the same location as the original audio file.
        """
        try:
            sf.write(self.file_loc, self.audio_sequence, 44100)
        except Exception as e:
            print(f"Error converting to wav: {e}")
            raise

    def save_to_mp3(self):
        """
        Converts and saves the audio sequence to an .mp3 file using pydub.

        The file is saved at the same location as the original audio file.
        """

        try:
            audio_seq_array = np.array(self.audio_sequence)
            channels = 2 if (audio_seq_array.ndim == 2 and audio_seq_array.shape[1] == 2) else 1
            y = np.int16(audio_seq_array * 2**15) if self.normalized else np.int16(audio_seq_array)

            sequence = pydub.AudioSegment(
                y.tobytes(), frame_rate=44100, sample_width=2, channels=channels
            )
            sequence.export(self.file_loc, format="mp3", bitrate="128k")
        except Exception as e:
            print(f"Error converting to mp3: {e}")
            raise


#### RUN JOB ####


class JobRunner:
    def __init__(self, job_id, channel_index, random_id):
        self.job_id = job_id
        self.channel_index = channel_index
        self.random_id = random_id
        self.job_params = JobConfig(self.job_id, self.channel_index, self.random_id)
        self.logger = logging.getLogger(__name__)

    def get_assets(self):
        try:
            StorageEngine(self.job_params, "job_id_path").get_object()
            StorageEngine(self.job_params, "asset_path").get_object()
        except Exception as e:
            self.logger.error(f"Error getting assets: {e}")
            raise e

    def validate(self):
        try:
            new_config_test = SequenceConfigRefactor(self.job_params)
            new_audio_frames = SequenceAudioFrameSlicer(new_config_test)
            validated_audio_sequence, audio_sequence = SequenceEngine(
                new_config_test, new_audio_frames
            ).generate_audio_sequence()

            return validated_audio_sequence, audio_sequence
        except Exception as e:
            self.logger.error(f"Error validating: {e}")
            raise e

    def result(self, result):
        try:
            if result:
                cloud_path = self.job_params.path_resolver()["cloud_path_processed"]
                return cloud_path
            else:
                self.logger.error("Job failed")
        except Exception as e:
            self.logger.error(f"Error processing result: {e}")
            raise e

    def clean_up(self):
        try:
            StorageEngine(self.job_params, "asset_path").delete_local_object()
        except Exception as e:
            self.logger.error(f"Error cleaning up: {e}")
            raise e

    def execute(self):
        try:
            self.get_assets()
            validated_audio, audio_sequence = self.validate()

            AudioEngine(
                audio_sequence,
                self.job_params.path_resolver()["local_path_processed_pkl"],
                normalized=None,
            ).save_to_pkl()

            return True
        except Exception as e:
            self.logger.error(f"Error executing job: {e}")
            return False
