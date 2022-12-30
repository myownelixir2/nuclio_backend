from pydantic import BaseModel, validator

class FxParamsModel_Test(BaseModel):
    fx_input: str

    @validator("fx_input")
    def channel_mute_params_validator(cls, v):
        v = v.split("_")
        if len(v) != 6 and ("0", "1", "2", "3","4","5", "F") not in v:
            raise ValueError("mute_params is not correct")
        return v


