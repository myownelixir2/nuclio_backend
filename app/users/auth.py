from fastapi import HTTPException, Depends, status
from firebase_admin import auth, credentials, initialize_app, exceptions
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, BaseSettings, Field


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class UserInDB(BaseModel):
    """
    A Pydantic model representing a user in the database.

    Attributes:
    -----------
    username : str
        The user's username.
    """
    username: str
    
class FirebaseSettings(BaseSettings):
    """
    A Pydantic model for Firebase settings.

    Attributes:
    -----------
    firebase_credential_json : str
        Path to the Firebase credential JSON file.

    Methods:
    --------
    initialize_firebase():
        Initializes Firebase with the provided credentials.
    """
    firebase_credential_json: str = Field(..., env="FIREBASE_CREDENTIAL_PATH")

    

    def __init__(self, **data):
        super().__init__(**data)
        self.initialize_firebase()

    def initialize_firebase(self):
        """
        Initializes Firebase with the provided credentials.
        """
        #cred_json = json.loads(self.firebase_credential_json)
        firebase_credentials = credentials.Certificate(self.firebase_credential_json)
        initialize_app(firebase_credentials)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Function to get the current user based on the provided token.

    Parameters:
    -----------
    token : str
        The token to validate.

    Returns:
    --------
    UserInDB
        A Pydantic model representing the user, if the token is valid. 
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token["uid"]
    except (ValueError, KeyError, TypeError, exceptions.FirebaseError):
        raise credentials_exception

    user = auth.get_user(uid)
  
    if user is None:
        raise credentials_exception

    user_info = UserInDB(username=user.uid)

    return user_info

