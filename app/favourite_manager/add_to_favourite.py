from turtle import st
import pandas as pd
import soundfile as sf
import numpy as np
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, BaseSettings, validator, SecretStr
from collections import Counter
from app.storage.storage import *


class AddToFavouriteManager:
    def __init__(self, job_params):
        self.job_params = job_params
        
    def add_to_favourite(self):
        # get the favourite list
        # add the job id to the list
        # save the list
        # return the list
        pass