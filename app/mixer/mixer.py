import os
import glob
import numpy as np
import pickle
import pydub
from app.storage.storage import StorageEngine
from app.utils.utils import JobConfig
from app.sequence_generator.generator import SequenceEngine


class MixEngine:
    """
    MixEngine class mixes audio sequences.
    Parameters:
    job_params (JobConfig): Contains job configuration parameters.
    normalize (bool): If True, normalizes the audio array to be between -1 and 1. Default is True.

    """

    def __init__(self, job_params, normalize=True):
        self.job_params = job_params
        self.normalized = normalize

    def mix_sequences_pkl(self):
        """
        mix_sequences_pkl(): Mixes the audio sequences.
           - Loads the .pkl pickle files in the temp folder that start with mixdown_ and the random ID.
           - Validates and combines the sequences.
           - Exports the mixed audio as a .wav file.
           - Returns True if successful, False otherwise.
        """

        dir_path = r"temp"
        bpm = self.job_params.get_job_params()["bpm"]
        output_file = self.job_params.path_resolver()["local_path_mixdown_wav_master"]
        # output_file = self.job_params.path_resolver()["local_path_mixdown_mp3_master"]
        random_id = self.job_params.random_id

        res = []
        for file in os.listdir(dir_path):
            if file.startswith("mixdown_" + random_id) and file.endswith(".pkl"):
                my_arrays = pickle.load(open(os.path.join(dir_path, file), "rb"))

                new_seq = SequenceEngine.validate_sequence(bpm, my_arrays)

                res.append(new_seq)

        my_input = [
            (a + b + c + d + e + f) / 6
            for a, b, c, d, e, f in zip(res[0], res[1], res[2], res[3], res[4], res[5])
        ]

        audio_seq_array = np.array(my_input)

        channels = (
            2 if (audio_seq_array.ndim == 2 and audio_seq_array.shape[1] == 2) else 1
        )
        if self.normalized:  # normalized array - each item should be a float in [-1, 1)
            y = np.int16(audio_seq_array * 2**15)
        else:
            y = np.int16(audio_seq_array)

        try:
            sequence = pydub.AudioSegment(
                y.tobytes(), frame_rate=44100, sample_width=2, channels=channels
            )
            sequence.export(output_file, format="wav", bitrate="128k")

            if os.path.exists(output_file):
                print("sequences mixed")
                return True
            else:
                print("Something went wrong")
                return False
        except Exception as e:
            print(e)
            return False

    def mix_sequences(self):
        """
        mix_sequences(): Mixes the audio sequences.
            - Gets the list of .mp3 files in the temp folder that start with mixdown_ and the random ID.
            - Constructs an ffmpeg command to mix the sequences.
            - Executes the ffmpeg command.
            - Returns True if successful, False otherwise.
        """
        random_id = self.job_params.random_id

        current_sequences_list = glob.glob(f"temp/mixdown_{random_id}_*.mp3")

        input_files = "-i " + " -i ".join(current_sequences_list)
        output_file = self.job_params.path_resolver()["local_path_mixdown_mp3_master"]

        mix_cmd = f"ffmpeg -y {input_files} -filter_complex '[0:0][1:0] amix=inputs=6:duration=longest' -c:a libmp3lame {output_file}"

        try:
            returned_value = os.system(mix_cmd)  # returns the exit code in unix
            print("returned value:", returned_value)

            if os.path.exists(output_file):
                print("sequences mixed")
                return True
            else:
                print("Something went wrong")
                return False
        except Exception as e:
            print(e)
            return False


class MixRunner:
    """
    MixRunner class executes the mixing process.

        Parameters:
        job_id (int): The job ID.
        random_id (str): The random ID for the job.
    """

    def __init__(
        self,
        job_id,
        random_id,
    ):
        self.job_id = job_id
        self.random_id = random_id

    def clean_up(self):
        """
        clean_up(): Deletes all files in the temp folder. Returns True if successful, False otherwise.
        """
        try:
            current_sequences_list = glob.glob("temp/*")
            [os.remove(f) for f in current_sequences_list]

            return True
        except Exception as e:
            print(e)
            return False

    def execute(self):
        """
        execute(): Executes the mixing process.
            - Gets the job parameters.
            - Mixes the sequences using MixEngine.
            - If successful, uploads the mixed audio file using StorageEngine.
            - Returns True if successful, False otherwise.
        """
        try:
            job_params = JobConfig(self.job_id, 0, self.random_id)
            mix_ready = MixEngine(job_params, normalize=True).mix_sequences_pkl()
            if mix_ready:
                StorageEngine(job_params, "mixdown_job_path_master").upload_object()
                return True
            else:
                print("something went wrong")
                return False

        except Exception as e:
            print(e)
            return False
