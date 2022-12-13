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
from app.storage.storage import *


#### SEQUENCE ENGINE ####


class SequenceConfigRefactor:
    def __init__(self, job_params):
        self.job_params = job_params

    def euclead_rhythm_generator(self) -> list:
        rhythm_config = self.job_params.get_job_params()["rythm_config_list"]
        n: int = rhythm_config[0]
        k: int = rhythm_config[1]
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

    def get_note_sequence(self) -> list:

        scale_value = self.job_params.get_job_params()["scale_value"]
        keynote = self.job_params.get_job_params()["key_value"]

        notes_match_table = pd.read_pickle(
            "app/sequence_generator/notes_match_table.pkl"
        )
        notes_sequence_raw = notes_match_table.query(
            "scale_name==@scale_value & key==@keynote"
        ).filter(["notes"])

        notes_sequence_extracted_str = notes_sequence_raw["notes"].values[0].split(", ")
        notes_sequence_extracted_int = [int(i) for i in notes_sequence_extracted_str]
        notes_sequence_extracted_int_octave_down = [
            (i - 12) for i in notes_sequence_extracted_int
        ]

        notes_sequence_complete = (
            notes_sequence_extracted_int_octave_down + notes_sequence_extracted_int
        )
        return notes_sequence_complete

    def grid_validate(self):
        """
        check if onset is equal
        to total length of the sample track
        """
        bpm = self.job_params.get_job_params()["bpm"]
        rhythm_config = self.job_params.get_job_params()["rythm_config_list"]
        audio, sr = librosa.load(
            self.job_params.get_job_params()["local_paths"], sr=44100
        )

        one_bar = 60 / bpm * 4
        k = rhythm_config[1]
        pulse_length_samples = 44100 * one_bar / k

        equal_to_total = (
            True if (math.floor(len(audio) / pulse_length_samples)) <= 1 else False
        )
        grid_value = (
            len(audio)
            if equal_to_total
            else math.floor(len(audio) / pulse_length_samples) * pulse_length_samples
            - pulse_length_samples
        )
        return grid_value, pulse_length_samples

    def get_audio_frames_length(self) -> list:
        pulse_sequence = self.euclead_rhythm_generator()
        __, pulse_length_samples = self.grid_validate()

        onsets_loc = [i for i, e in enumerate(pulse_sequence) if e == 1]
        onsets_loc_arr = np.array(onsets_loc)
        silence_loc_arr_temp = np.subtract(onsets_loc_arr[1:], 1)
        silence_loc_arr = np.append(silence_loc_arr_temp, len(pulse_sequence) - 1)

        audio_frames_lengths = []
        for onsets, silence in zip(onsets_loc_arr, silence_loc_arr):
            # print(len(pulse_sequence[onsets:silence]))
            audio_frames_lengths.append((silence - onsets + 1) * pulse_length_samples)
        return audio_frames_lengths

    def get_audio_frames_reps(self) -> list:
        grid_value, __ = self.grid_validate()
        audio_frames_lens = self.get_audio_frames_length()
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

        self.sequence_config = sequence_config

    def get_audio_frame_sequence_list(self):

        audio_frames_lengths = self.sequence_config.get_audio_frames_length()
        audio_frames_reps = self.sequence_config.get_audio_frames_reps()
        unique_audio_frames_lengths = np.unique(audio_frames_lengths)

        sequence_l = []
        for audio_lengths, audio_reps in zip(
            unique_audio_frames_lengths, audio_frames_reps
        ):
            test_stop_range = (audio_lengths * audio_reps) - audio_lengths

            stop_range = audio_lengths if test_stop_range == 0 else test_stop_range
            step_range = audio_lengths
            sequence_l.append(np.arange(0, stop_range, step_range))
        return sequence_l

    def frames_list(self, individual_frames: list, unique_frame_length: float):
        sliced_frames = []

        audio, sr = librosa.load(
            self.sequence_config.job_params.get_job_params()["local_paths"], sr=44100
        )

        for frame in individual_frames:
            if unique_frame_length > len(audio):
                empty_array = np.zeros(int(unique_frame_length) - int(len(audio)))
                audio = np.append(audio, empty_array)

            sliced_frames.append(
                audio[int(frame) : int(frame) + int(unique_frame_length)]
            )
            # sliced_frames.append(self.sequence_config.audio[int(frame):int(frame)+int(unique_frame_length)])
        return sliced_frames

    def get_audio_frames(self):
        sequence_l = self.get_audio_frame_sequence_list()
        audio_frames_lengths = self.sequence_config.get_audio_frames_length()
        unique_audio_frames_lengths = np.unique(audio_frames_lengths)
        audio_frames = [
            self.frames_list(x, y)
            for x, y in zip(sequence_l, unique_audio_frames_lengths)
        ]
        return audio_frames


class SequenceEngine:
    def __init__(self, sequence_config, audio_frames):
        self.audio_frames = audio_frames
        self.sequence_config = sequence_config

    @staticmethod
    def validate_sequence(bpm, new_sequence):

        one_bar = 60 / bpm * 4
        original_sample_len = round(44100 * one_bar / 1)

        try:
            new_sequence_unpacked = [
                item for sublist in new_sequence for item in sublist
            ]
        except TypeError:
            new_sequence_unpacked = new_sequence

        new_sequence_len = len(new_sequence_unpacked)

        if new_sequence_len == original_sample_len:
            validated_sequence = new_sequence_unpacked[:original_sample_len]
        elif new_sequence_len < original_sample_len:
            empty_array = np.zeros(original_sample_len - new_sequence_len)

            validated_sequence = np.append(new_sequence_unpacked, empty_array)
        else:
            validated_sequence = new_sequence_unpacked
        return validated_sequence

    def __unpack_multi_level_list(self, my_list):
        unpacked_list = []
        for i in range(len(my_list)):
            for j in range(len(my_list[i])):
                unpacked_list.append(my_list[i][j])
                return unpacked_list

    def __pitch_shift(self, audio, pitch_shift):
        return librosa.effects.pitch_shift(audio, sr=44100, n_steps=pitch_shift)

    def __apply_pitch_shift(
        self, audio_frames: List[float], pitch_shift: Optional[list]
    ):

        pitch_temperature = self.sequence_config.job_params.get_job_params()[
            "pitch_temperature_knob_list"
        ][0]

        if (random.random() > pitch_temperature / 100) and (pitch_temperature != 0):
            pitch_shifted_audio_sequence = []
            for i in range(len(audio_frames)):

                pitch_shifted_audio_sequence.append(
                    self.__pitch_shift(audio_frames[i], pitch_shift[i])
                )
            return pitch_shifted_audio_sequence
        else:
            return audio_frames

    def generate_audio_sequence(self):

        my_audio_frames_lengths = self.sequence_config.get_audio_frames_length()
        my_audio_frames = self.audio_frames.get_audio_frames()
        my_audio_frames_lengths_sanitized = [
            int(item) for item in my_audio_frames_lengths
        ]
        occurences_of_distinct_frames = Counter(my_audio_frames_lengths_sanitized)

        new_audio_sequence = []
        for i in range(len(my_audio_frames)):
            nr_elements_to_select = list(occurences_of_distinct_frames.values())[i]
            temp_sequence = random.choices(my_audio_frames[i], k=nr_elements_to_select)
            new_audio_sequence.append(temp_sequence)

        new_sequence_unlisted = [
            item for sublist in new_audio_sequence for item in sublist
        ]
        note_sequence = self.sequence_config.get_note_sequence()
        note_sequence_updated = random.choices(
            note_sequence, k=len(new_sequence_unlisted)
        )

        bpm = self.sequence_config.job_params.get_job_params()["bpm"]

        updated_new_audio_sequence = self.__apply_pitch_shift(
            new_sequence_unlisted, note_sequence_updated
        )
        validated_audio_sequence = self.validate_sequence(
            bpm, updated_new_audio_sequence
        )

        return validated_audio_sequence, updated_new_audio_sequence

    def generate_audio_sequence_auto(self):
        audio_frames = self.audio_frames.get_audio_frames()
        audio_frames_lengths = self.sequence_config.get_audio_frames_length()
        unique_audio_frames_lengths = np.unique(audio_frames_lengths)

        audio_frames_sequence = []
        for i in range(len(audio_frames)):
            audio_frames_sequence.append(
                np.random.choice(
                    audio_frames[i], int(unique_audio_frames_lengths[i]), replace=False
                )
            )
        return self.__unpack_multi_level_list(audio_frames_sequence)


##### AUDIO ENGINE #####


class AudioEngine:
    def __init__(self, validated_audio_sequence, file_loc, normalized=None):
        self.audio_sequence = validated_audio_sequence
        self.file_loc = file_loc
        self.normalized = normalized

    def read_audio(self):
        return librosa.load(self.file_loc, sr=44100)

    def save_to_pkl(self):
        try:
            my_file = self.file_loc
            my_pkl = my_file.replace(".mp3", ".pkl")
            with open(my_pkl, "wb") as f:
                pickle.dump(self.audio_sequence, f)

        except Exception as e:
            print(e)
            print("Could not save to pkl")

    def save_to_wav(self):
        try:
            sf.write(self.file_loc, self.audio_sequence, 44100)
            # librosa.output.write_wav(self.file_loc, self.audio_sequence, sr=44100, norm=self.normalized)
        except Exception as e:
            print("Error converting to wav", e)
            raise e

    def save_to_mp3(self):
        try:
            audio_seq_array = np.array(self.audio_sequence)
            channels = (
                2
                if (audio_seq_array.ndim == 2 and audio_seq_array.shape[1] == 2)
                else 1
            )
            if (
                self.normalized
            ):  # normalized array - each item should be a float in [-1, 1)
                y = np.int16(audio_seq_array * 2**15)
            else:
                y = np.int16(audio_seq_array)
            sequence = pydub.AudioSegment(
                y.tobytes(), frame_rate=44100, sample_width=2, channels=channels
            )
            sequence.export(self.file_loc, format="mp3", bitrate="128k")
        except Exception as e:
            print("Error converting to mp3", e)
            raise e


#### RUN JOB ####


class JobRunner:
    def __init__(self, job_id, channel_index, random_id):
        self.job_id = job_id
        self.channel_index = channel_index
        self.random_id = random_id

    def get_assets(self):
        try:
            StorageEngine(self.job_params, "job_id_path").get_object()
            StorageEngine(self.job_params, "asset_path").get_object()
        except Exception as e:
            print(e)

    def validate(self):
        try:

            new_config_test = SequenceConfigRefactor(self.job_params)
            new_audio_frames = SequenceAudioFrameSlicer(new_config_test)
            validated_audio_sequence, audio_sequence = SequenceEngine(
                new_config_test, new_audio_frames
            ).generate_audio_sequence()

            return validated_audio_sequence, audio_sequence
        except Exception as e:
            print(e)
            return False

    def result(self, result):
        try:
            if result == True:
                cloud_path = self.job_params.path_resolver()["cloud_path_processed"]
                # TODO check if file exists
                return cloud_path
            else:
                return print("Job failed")
        except Exception as e:
            print(e)
            return print("Error")

    def clean_up(self):
        self.job_params = JobConfig(self.job_id, self.channel_index, self.random_id)
        try:
            StorageEngine(self.job_params, "asset_path").delete_local_object()
        except Exception as e:
            print(e)

    def execute(self):
        self.job_params = JobConfig(self.job_id, self.channel_index, self.random_id)

        self.get_assets()
        validated_audio, audio_sequence = self.validate()

        try:
            AudioEngine(
                audio_sequence,
                self.job_params.path_resolver()["local_path_processed_pkl"],
                normalized=None,
            ).save_to_pkl()

            return True
        except Exception as e:
            print(e)
            return False
