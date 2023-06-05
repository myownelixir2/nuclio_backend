import json
import re
from typing import Literal, List

from pydantic import BaseModel, Field, validator
import glob
import os
import pathlib
import itertools


class JobTypeValidator(BaseModel):
    """
    A Pydantic model for validating job types.

    Attributes:
        job_type: A string representing the job type. It must be one of the
            following: "job_id_path", "processed_job_path", "asset_path",
            "mixdown_job_path", "mixdown_job_path_master", or "mixdown_job_path_pkl".
    """

    job_type: Literal[
        "job_id_path",
        "processed_job_path",
        "asset_path",
        "mixdown_job_path",
        "mixdown_job_path_master",
        "mixdown_job_path_pkl",
    ]

    @validator("job_type")
    def job_type_validator(cls, v):
        if v not in [
            "job_id_path",
            "processed_job_path",
            "asset_path",
            "mixdown_job_path",
            "mixdown_job_path_master",
            "mixdown_job_path_pkl",
        ]:
            raise ValueError(
                'job_type must be either "job_id_path", "processed_job_path", "asset_path", "mixdown_job_path" or "mixdown_job_path_pkl" or "mixdown_job_path_master"'
            )
        return v


class JobConfigValidator(BaseModel):
    index_value: int = Field(..., ge=0, le=5)

    @validator("index_value")
    def item_validator(cls, v):
        if v not in [0, 1, 2, 3, 4, 5]:
            raise ValueError("index must be between 0 and 5")
        return v


class JobConfig:
    """
    A class used to manage and resolve job configurations.

    Attributes:
        job_id: A string representing the job's ID.
        channel_index: An integer representing the channel index.
        random_id: A string representing a random ID.
    """

    def __init__(self, job_id: str, channel_index: int, random_id: str):
        """
        The constructor for JobConfig class.

        Parameters:
            job_id (str): The job's ID.
            channel_index (int): The channel index.
            random_id (str): A random ID.
        """
        self.job_id = job_id
        self.channel_index = channel_index
        self.random_id = random_id

    @staticmethod
    def has_initial_index(file_path):
        """
        Checks if a file at the given path has an initial index.

        Parameters:
            file_path (str): The file path to check.

        Returns:
            bool: True if the file has an initial index, False otherwise.
        """
        try:
            with open(file_path, "r") as file:
                json_obj = json.load(file)
                return isinstance(json_obj, list) and len(json_obj) > 0
        except (ValueError, FileNotFoundError):
            return False

    def path_resolver(self):
        """
        Resolves various paths related to the job.

        Returns:
            dict: A dictionary containing resolved paths.
        """

        # random_id = ''.join((random.choice('abcdxyzpqr') for i in range(8)))

        sanitized_job_id = self.job_id.split("/")[1].replace(".json", "")
        local_path = f"temp/{sanitized_job_id}.json"

        local_path_processed = (
            f"temp/sequences_{sanitized_job_id}_{self.channel_index}.mp3"
        )
        cloud_path_processed = f"sequences/{sanitized_job_id}_{self.channel_index}.mp3"

        local_path_processed_pkl = (
            f"temp/sequences_{sanitized_job_id}_{self.channel_index}.pkl"
        )
        cloud_path_processed_pkl = (
            f"sequences/{sanitized_job_id}_{self.channel_index}.pkl"
        )

        local_path_mixdown = f"temp/mixdown_{self.random_id}_{sanitized_job_id}"
        cloud_path_mixdown = f"mixdown/mixdown_{self.random_id}_{sanitized_job_id}"

        local_path_pre_mixdown_mp3 = f"temp/pre_mixdown_{self.random_id}_{sanitized_job_id}__{self.channel_index}.mp3"
        local_path_pre_mixdown_pkl = f"temp/pre_mixdown_{self.random_id}_{sanitized_job_id}__{self.channel_index}.pkl"

        local_path_mixdown_mp3 = f"{local_path_mixdown}_{self.channel_index}.mp3"
        cloud_path_mixdown_mp3 = f"{cloud_path_mixdown}_{self.channel_index}.mp3"

        local_path_mixdown_wav = f"{local_path_mixdown}_{self.channel_index}.wav"
        cloud_path_mixdown_wav = f"{cloud_path_mixdown}_{self.channel_index}.wav"

        local_path_mixdown_pkl = f"{local_path_mixdown}_{self.channel_index}.pkl"
        cloud_path_mixdown_pkl = f"{cloud_path_mixdown}_{self.channel_index}.pkl"

        local_path_mixdown_mp3_master = f"{local_path_mixdown}_master.mp3"
        cloud_path_mixdown_mp3_master = f"{cloud_path_mixdown}_master.mp3"

        local_path_mixdown_wav_master = f"{local_path_mixdown}_master.wav"
        cloud_path_mixdown_wav_master = f"{cloud_path_mixdown}_master.wav"

        paths_dict = {
            "cloud_path": self.job_id,
            "local_path": local_path,
            "local_path_processed": local_path_processed,
            "cloud_path_processed": cloud_path_processed,
            "local_path_processed_pkl": local_path_processed_pkl,
            "cloud_path_processed_pkl": cloud_path_processed_pkl,
            "local_path_pre_mixdown_mp3": local_path_pre_mixdown_mp3,
            "local_path_pre_mixdown_pkl": local_path_pre_mixdown_pkl,
            "local_path_mixdown_pkl": local_path_mixdown_pkl,
            "cloud_path_mixdown_pkl": cloud_path_mixdown_pkl,
            "local_path_mixdown_wav": local_path_mixdown_wav,
            "cloud_path_mixdown_wav": cloud_path_mixdown_wav,
            "local_path_mixdown_mp3": local_path_mixdown_mp3,
            "cloud_path_mixdown_mp3": cloud_path_mixdown_mp3,
            "local_path_mixdown_mp3_master": local_path_mixdown_mp3_master,
            "cloud_path_mixdown_mp3_master": cloud_path_mixdown_mp3_master,
            "local_path_mixdown_wav_master": local_path_mixdown_wav_master,
            "cloud_path_mixdown_wav_master": cloud_path_mixdown_wav_master,
            "sanitized_job_id": sanitized_job_id,
        }
        return paths_dict

    def __psuedo_json_to_dict(self):
        """
        Converts the job's pseudo JSON to a Python dictionary.

        Returns:
            dict: The job's data as a Python dictionary.
        """
        paths = self.path_resolver()
        inital_index = self.has_initial_index(paths["local_path"])
        if inital_index:
            with open(paths["local_path"], "r") as lst:
                json_psudo = json.load(lst)
                json_sanitized = re.sub(
                    r'("\s*:\s*)undefined(\s*[,}])', "\\1null\\2", json_psudo[0]
                )
                json_dict = json.loads(json_sanitized)
        else:
            with open(paths["local_path"], "r") as lst:
                json_dict = json.load(lst)

        return json_dict

    def get_job_params(self):
        """
        Retrieves the job's parameters.

        Returns:
            dict: The job's parameters as a Python dictionary.
        """
        job_id_dict = self.__psuedo_json_to_dict()

        _check_index = JobConfigValidator.parse_obj({"index_value": self.channel_index})

        params_dict = {
            "local_paths": job_id_dict["local_paths"][_check_index.index_value],
            "cloud_paths": job_id_dict["cloud_paths"][_check_index.index_value],
            "bpm": job_id_dict["bpm"][0],
            "scale_value": job_id_dict["scale_value"][0],
            "key_value": job_id_dict["key_value"][0],
            "rythm_config_list": job_id_dict["rythm_config_list"][
                _check_index.index_value
            ],
            "pitch_temperature_knob_list": job_id_dict["pitch_temperature_knob_list"][
                _check_index.index_value
            ],
        }

        return params_dict


class JobUtils:
    """
    A class providing utilities for job management.
    """

    def __init__(self, job_id: str):
        """
        The constructor for JobUtils class.

        Parameters:
            job_id (str): The job's ID.
        """
        self.job_id = job_id

    def sanitize_job_id(self):
        """
        Sanitizes the job's ID.

        Parameters:
            job_id (str): The job's ID.

        Returns:
            str: The sanitized job's ID.
        """
        my_job_id = self.job_id

        sanitized_job_id = my_job_id.replace(".json", "").replace("job_ids/", "")

        return sanitized_job_id

    @staticmethod
    def list_files_matching_pattern(
        extensions: List[str], directory: str, pattern: str
    ) -> List[str]:
        """
        Args:
            extensions (List[str]): list of extensions to search for ['*.mp3', '*.pkl']
            directory (str): directory to search in for example 'temp' or  'assets/sounds'
            pattern (str): pattern to look for in the file name, for example 'job_id_dshfdsk23243'

        Returns:
            List[str]: returns a list of files with the pattern in the directory
        Usage:
            list_files_with_string(extensions=['*.mp3', '*.pkl'], directory='temp', pattern='cyoprs')
        """
        assets_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), directory
        )

        file_paths = []
        for ext in extensions:
            file_paths.extend(glob.glob(os.path.join(assets_path, ext)))

        matching_file_paths = [f for f in file_paths if pattern in f]
        return matching_file_paths

    @staticmethod
    def remove_files(files: List[str]) -> bool:
        """
        Remove a list of files.
        Args:
            files: A list of file paths to be removed.

        Returns:
            True if all files were successfully removed, False otherwise.
        """
        success = True
        for f in files:
            try:
                os.remove(f)
            except OSError as e:
                print("Error: %s : %s" % (f, e.strerror))
                success = False

        return success


class JobCleanUp:
    """
    A class providing cleanup utilities for jobs.
    """

    def __init__(self, job_id: str):
        """
        The constructor for JobCleanUp class.

        Parameters:
            job_id (str): The job's ID.
        """
        self.job_id = job_id

    def assets(self):
        """
        Cleans up assets by removing .mp3 files.

        Returns:
            List[bool]: A list of status indicating whether each file was successfully removed or not.
        """

        assets_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets/sounds/",
        )

        pattern_path = assets_path + "/*.mp3"

        files = glob.glob(pattern_path)
        status = []
        for f in files:
            try:
                file_to_rem = pathlib.Path(f)
                file_to_rem.unlink()
                status.append(True)
            except OSError as e:
                print("Error: %s : %s" % (f, e.strerror))
                status = False
        return status

    def assets_refactor(self):
        """
        Cleans up assets by removing .mp3 files. Refactored version.

        Returns:
            bool: True if all files were successfully removed, False otherwise.
        """
        assets_path = os.path.abspath(os.path.join("assets", "sounds"))
        files = glob.glob(os.path.join(assets_path, "*.mp3"))

        file_to_rem = [pathlib.Path(f).unlink for f in files]

        return all(map(file_to_rem, files))

    def sanitize_job_id(self):
        """
        Sanitizes the job's ID.

        Returns:
            str: The sanitized job's ID.
        """
        my_job_id = self.job_id

        sanitized_job_id = my_job_id.replace(".json", "").replace("job_ids/", "")

        return sanitized_job_id

    @staticmethod
    def filter_list(my_list: List[str], my_string: str) -> List[str]:
        """
        Filters a list of strings based on a given pattern.

        Parameters:
            my_list (List[str]): The list of strings to filter.
            my_string (str): The pattern to search for.

        Returns:
            List[str]: The filtered list of strings.
        """
        pattern = re.compile(my_string)
        filtered_list = [item for item in my_list if pattern.search(item)]

        return filtered_list

    def temp(self):
        """
        Cleans up temporary files by removing .pkl, .mp3, and .json files.

        Returns:
            List[bool]: A list of status indicating whether each file was successfully removed or not.
        """
        # sanitie job id
        my_job_id = self.sanitize_job_id()

        temp_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp/"
        )

        ext_types = ["*.pkl", "*.mp3", "*.json"]  # the tuple of file types

        files_grabbed = []
        for ext_type in ext_types:
            pattern_path = temp_path + ext_type
            files = glob.glob(pattern_path)
            files_grabbed.append(files)

        unpacked_files_grabbed = [item for sublist in files_grabbed for item in sublist]
        # making sure we only grab the files with certain ids
        sanitized_unpacked_files = self.filter_list(
            my_list=unpacked_files_grabbed, my_string=my_job_id
        )
        status = []
        for f in sanitized_unpacked_files:
            try:
                file_to_rem = pathlib.Path(f)
                file_to_rem.unlink()
                status.append(True)
            except OSError as e:
                print("Error: %s : %s" % (f, e.strerror))
                status = False
        return status

    def tempre_factor(self):
        """
        Cleans up temporary files by removing .pkl, .mp3, and .json files. Refactored version.

        Returns:
            bool: True if all files were successfully removed, False otherwise.
        """
        temp_path = os.path.abspath(os.path.join("temp"))

        ext_types = ["*.pkl", "*.mp3", "*.json"]
        files = itertools.chain(
            *(glob.glob(os.path.join(temp_path, ext)) for ext in ext_types)
        )

        file_to_rem = [pathlib.Path(f).unlink for f in files]

        return all(map(file_to_rem, files))


def purge_all(my_paths: List[str], my_patterns: List[str]) -> bool:
    """
    Purges all files matching the given patterns in the specified paths.

    Args:
        my_paths (List[str]): List of directory paths to search in.
        my_patterns (List[str]): List of file patterns to match.

    Returns:
        bool: True if all files were successfully removed, False otherwise.
    """
    # remove all files in temp
    temp_path = os.path.abspath(os.path.join(*my_paths))
    ext_types = my_patterns
    files = itertools.chain(
        *(glob.glob(os.path.join(temp_path, ext)) for ext in ext_types)
    )
    for f in files:
        os.remove(f)

    return True
