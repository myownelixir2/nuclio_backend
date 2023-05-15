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