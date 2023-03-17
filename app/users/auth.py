from fastapi import HTTPException, Depends, status
import firebase_admin
from firebase_admin import auth, credentials, initialize_app
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, BaseSettings, Field


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



class UserInDB(BaseModel):
    username: str
    
class FirebaseSettings(BaseSettings):
    firebase_credential_json: str = Field(..., env="FIREBASE_CREDENTIAL_PATH")

    def __init__(self, **data):
        super().__init__(**data)
        self.initialize_firebase()

    def initialize_firebase(self):
        #cred_json = json.loads(self.firebase_credential_json)
        firebase_credentials = credentials.Certificate(self.firebase_credential_json)
        initialize_app(firebase_credentials)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token["uid"]
    except (ValueError, KeyError, TypeError, firebase_admin.auth.AuthError):
        raise credentials_exception

    user = auth.get_user(uid)
  
    if user is None:
        raise credentials_exception

    user_info = UserInDB(username=user.email)

    return user_info

