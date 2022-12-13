import pedalboard
import numpy as np
from pydantic import BaseModel, validator


class FxPedalBoardConfig(BaseModel):
    audio_fx: str

    @validator("audio_fx")
    def job_id_validator(cls, v):
        if v not in ["Bitcrush", "Chorus", "Delay", "Flanger", "Phaser", "Reverb"]:
            raise ValueError("not allowed FX input")
        return v


class FxPedalBoardEngine:
    def __init__(self, mix_params, job_params, my_sequence):
        self.mix_params = mix_params
        self.job_params = job_params
        self.my_sequence = my_sequence

    def apply_pedalboard_fx(self):

        fx_mapping = [
            "Bitcrush",
            "Chorus",
            "Delay",
            "Flanger",
            "Phaser",
            "Reverb",
            "Distortion",
        ]

        channel_index = int(self.job_params.channel_index)
        fx_input = self.mix_params.fx_input[channel_index]

        fx = fx_mapping[int(fx_input)]

        validated_fx = FxPedalBoardConfig(fx)

        pedalboard_fx = getattr(pedalboard, validated_fx)
        board = pedalboard.Pedalboard([pedalboard_fx])

        try:
            effected = board(self.my_sequence, 44100.0)
        except Exception as e:
            print(e)

        y_effected = np.int16(effected * 2**15)

        return y_effected
