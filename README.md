# Neucl.io - Modern Euclidean Rhythm Generator

This repository contains code for an API to generate rhythmic sequences using the Euclidean algorithm.


## Getting Started
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites
You will need the following software installed:

- Python 3.8+
- Pip
- Virtualenv (optional but recommended)

### Installation
1. Clone the repository

```git clone https://github.com/myownelixir2/euclidean_rhythm_generator_mobile_python_fastapi.git```

2. Create a virtual environment (optional)

```virtualenv venv```

```source venv/bin/activate  # On Windows, use `venv\Scripts\activate```

3. Install the requirements

```pip install -r requirements.txt```

4. Run the tests

```python3 -m unittest -v tests```

5. Set all the relevant environment variables:
```bash
#FIREBASE
export FIREBASE_CREDENTIAL_PATH={my_creds.json}

# SQL DB
export DB_HOST={host}
export DB_NAME={db_name}
export DB_USER={db_user}
export DB_PASSWORD={db_pass}
export DB_PORT={db_port}

# S3 BUCKET  
export STORAGE_URL={s3_url}
export STORAGE_KEY={s3_key}
export STORAGE_SECRET={s3_secret}
```

6. Start the API

```uvicorn run:app --reload --workers 4```

The API will be running at http://localhost:8000.

## Usage

Head to ```/example``` folder on how to interact with API in stand alone mode. Follow steps in ```/example/example.ipynb```



## Contributing
Please feel free to contribute to this project by submitting issues or pull requests.

## License
This project is licensed under the MIT License - see the LICENSE.md file for details.




# FX module

This is a comprehensive module developed for processing audio data in Python. It provides a series of classes designed to apply various sound effects to audio sequences.

## Features

- **`MuteEngine`**: This class is designed to selectively mute parts of an audio sequence based on specified parameters.

- **`VolEngine`**: This class enables the adjustment of the volume level of an audio sequence. 

- **`FxPedalBoardConfig` and `FxPedalBoardEngine`**: These classes handle the application of different sound effects to the audio sequence. The effects include Bitcrush, Chorus, Delay, Phaser, Reverb, and Distortion. The FxPedalBoardEngine class also supports loading VST plugins to apply more complex sound effects.

- **`FxEngine`**: This class applies a variety of sound effects to the audio sequence using the ffmpeg software suite. The effects include reverb, chorus, crusher, echo (indoor and outdoor), and a robot effect.

- **`FxRunner`**: This is the main class that ties everything together. It initializes the job parameters and runs through the process of applying selective mutism, volume adjustment, and sound effects. If the process is successful, the result is uploaded to a specified location.

## How to Use

To use this module, you need to import the relevant classes and create instances with appropriate parameters. See the test files for examples of how to create instances of each class and use their methods.

Please note: This module was developed with Python 3.7 and later in mind. Dependencies include the ```numpy```, ```os```, and ```pedalboard``` libraries, among others. 


# Mixer Module
## Features
- **`MixEngine`**: This class is responsible for the mixing of multiple audio sequences. It allows for the mixing of multiple channels with individual volume levels and sound effects applied. The MixEngine class provides a streamlined interface to combine multiple processed sequences into a single output.

- **`MixRunner`**: This class is the driver that orchestrates the entire process of fetching, processing, and mixing the audio sequences. It initializes the job parameters, fetches the sequences, applies the desired sound effects and volume adjustments through the use of the other classes in the module, and finally mixes the sequences using the MixEngine class. If the mixing process is successful, the result is uploaded to a specified location.


# Generator Module
## Features

This module is a core component of the project, responsible for the generation and manipulation of audio sequences. 

It is composed of the following classes:

1. **`SequenceConfigRefactor`**: This class takes care of the sequence configuration. It manages various parameters necessary for the generation of audio sequences.

2. **`SequenceAudioFrameSlicer`**: This class focuses on slicing audio into different frames based on the sequence configuration. It takes the configuration and produces a list of audio frames.

3. **`SequenceEngine`**: This class is the driving force behind audio sequence generation. Using the audio frames and configuration provided, it generates and validates audio sequences.

4. **`AudioEngine`**: This class handles the audio output. It reads audio, saves audio to various file formats, and normalizes audio sequences.

5. **`JobRunner`**: This class orchestrates the entire audio generation process. It is responsible for executing jobs, which involves obtaining assets, validating them, managing the audio sequence generation, and finally, cleaning up afterwards.

Each class is designed to serve a unique purpose in the audio sequence generation process, promoting modularity and maintainability. All classes contain extensive docstrings explaining their role, attributes, and methods to aid in understanding their functionality.

The `generator.py` module is designed for extensibility and adaptability to fit various audio generation scenarios. Regular testing with the associated test cases in the `test_generator.py` module is advised to ensure the robustness of the functionality after any modifications.



# Storage Module
The storage.py module is a robust and flexible solution for working with Amazon S3 storage. It provides a set of classes that allow for efficient and secure management of files in S3 buckets.

## Features
1. **`StorageBase`**: This class provides the foundational functionalities for connecting to and interacting with Amazon S3 resources. It manages S3 clients and resources.

2. **`StorageEngine`**: This class is built on top of StorageBase and provides a set of functions for direct interactions with files in an S3 bucket. Features include file uploads, downloads, deletions, and the generation of pre-signed URLs.

3. **`StorageEngineDownloader`**: This class, also built on top of StorageBase, provides functions to download all files from an S3 bucket locally or to download a file from a pre-signed URL.

4. **`SnapshotManager`**: This class provides functionalities for managing snapshots in S3. It enables creating a snapshot of files in a bucket, processing the snapshot data, and saving the processed data back to S3. It also generates pre-signed URLs for the snapshots.

5. **`StoreEngineMultiFile`**: This class is designed for handling the upload of multiple files to S3 storage. It uses a unique identifier for each job and allows for the uploading of a list of files to a specified bucket path on S3.

# User Activity Module
The activity.py module, is main CRUD engine that allows for various interactions with Postgresql database. 

1. **`DatabseSettings`**: The DatabaseSettings class encapsulates the settings for the PostgreSQL database. These settings include the host, database name, user, password, and port. The values are fetched from the environment variables.

2. **`UserActivityDB`**: is a Python class that provides several methods for interacting with a PostgreSQL database. It manages data related to user activities such as favorite sessions, favorite stems, playlist likes, and plays. It maintains a connection to the database and performs various read and write operations based on user and session data.



# Utils Module
This module provides a collection of utility classes and functions for job management and cleanup.

1. **`JobTypeValidator`**: a class for validating job types. It uses the Literal type hint to enforce a specific set of job types. The job_type_validator validator ensures that only valid job types are accepted.

2. **`JobConfig`** : a class for managing and resolving job configurations. It provides methods for retrieving job parameters and handling file paths.

3. **`purge_all`**: a function for purging all files matching the given patterns in the specified paths. It takes a list of directory paths and a list of file patterns as arguments.

