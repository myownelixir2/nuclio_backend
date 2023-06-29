# Neucl.io - Modern Euclidean Rhythm Generator 🎶🐍
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)
![Firebase](https://img.shields.io/badge/firebase-%23039BE5.svg?style=for-the-badge&logo=firebase)

# About

Hello there, music enthusiasts and code ninjas! 👋🎵 Welcome to ```Neucl.io``` - modern euclidean sequencer, an open-source project designed to empower the modern musician with the power of Python. This repository contains code for an API that generates Euclidean rhythms, providing a fresh take on music production and programming. 🎼💻


## Euclidean Rhythms: Mathematics Meets Music 🎼📐
Euclidean rhythms are an intriguing way we leverage mathematical algorithms to create compelling rhythms. Here's the lowdown:

- Not so novel: While the concept might seem fresh, it's a time-honored technique in music production. 🕰️🎶
- Mathematical music: The method applies mathematical algorithms to music creation. 🧮🎵
- Even spreading: It's like spreading butter evenly over a piece of bread - every beat finds its perfect place in the rhythmic cycle. 🍞🥁

## Supercharging Your Music Production Workflow 🖥️🎹
``Neucl.io`` is your personal maestro in music automation, covering tasks from sample research to pattern arrangement. Here's how Neucl.io changes the game:

- Automated Efficiency: Wave goodbye to manual labor. With ```Neucl.io```, you're all about automated music idea generations. 🤖🎧
- Quick Iterations: Random selector, zips through your sample library in no time, finding the perfect sounds for your pattern. 🚀🎼
- Auto-Generate & Arrange: Craft and arrange rhythmic sequences automatically. Let the creativity flow! 🧩🎹
- Skyrocketing Output: Boost your creative output by 100x. It's your time to shine. 💥🎵


## How Does It Work? 🤔💡
Neucl.io transforms your music production workflow in just a few straightforward steps:

- Query and Pull Samples: Neucl.io dives into your sample library, swiftly pulling out 6 random samples based on your specifics - be it Kicks, Snares, Tops, Claps, Hi-hats, or Bass. You name it, ```Neucl.io``` retrieves it. 🗄️🎵

- Generate Rhythms and Sequences: From your selected samples, the app generates unique Euclidean rhythm for each track, forming a seamless sequence. Your beat starts to take shape. 🥁🎚️

- Add Variations and Effects: ```Neucl.io``` brings life to your beat with instant variations and effects, adding that unique touch to your sound. 🎛️⚡

- Save and Iterate: Once your creation is complete, ```Neucl.io``` instantly saves it to the cloud. Safe and secure, you're free to move onto the next beat without a hitch. 🌐🔄

## Embrace the Chaos 🎶🌌

- Unpredictability is Your Muse 🎭: In music creation, randomness is a dance with the unpredictable. It's about surrendering control and letting the unexpected take the lead.

- Set Your Sonic Vision 🧭: Your imagination is your compass. Navigate through the soundscape of the unforeseen and discover unexpected melodies and harmonies.

- Break Free 🚀: Step out of the familiar grooves of your musical reality. Let randomness recalibrate your creative process and lead you on an exhilarating adventure.

- Power of Happy Accidents 🎉: Every 'mistake' is a potential masterpiece, every unexpected note a chance for a new harmony. Find beauty in discord, rhythm in noise, and music in chaos.

Embrace the chaos, tune into the frequency of the unexpected, and let the Symphony of Serendipity begin! 🎵🌠

Time to unleash your creative beast with ```Neucl.io```! 🧠🔥🎼

🎵🎶🎵🎶🎵🎶🎵🎶🎵🎶🎵

# 🛠️ Let's Get Technical! 💻🔧
Are you ready to roll up your sleeves and dive into the technicalities? Excellent! It's time to explore how Neuclio works under the hood. Let's unlock the power of automated music production together. Buckle up, and let's code our way to new rhythms! 🎧👨‍💻🎹

## Getting Started
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.



### Prerequisites
You will need the following software installed:

- Python 3.8+
- Pip
- Virtualenv (optional but recommended)
- Docker
- S3 bucket (AWS, Google Cloud, Azure, Minio, Wasabi etc)
- Postgress data base (local or serverless)
- Firebase account, learn how to set it up [here](https://firebase.google.com/docs/web/setup) (do not worry, it's free)

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

## ⚠️ Under Development!
This project is under active development and may still have issues. We appreciate your understanding and patience. If you encounter any problems, please first check the open issues. If your issue is not listed, kindly create a new issue detailing the error or problem you experienced. Thank you for your support!

## Contributing
Please feel free to contribute to this project by submitting issues or pull requests.

## License
This project is licensed under the MIT License - see the LICENSE.md file for details.



