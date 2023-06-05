import logging
import pandas as pd

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.users.auth import get_current_user, UserInDB
from app.storage.storage import StorageEngineDownloader
from app.users.activity import UserActivityDB


logger = logging.getLogger(__name__)
user_activity = APIRouter()


@user_activity.post("/update_user_sessions")
def update_user_sessions(
    session_id: str, bucket: str, current_user: UserInDB = Depends(get_current_user)
):
    try:
        print("Update user session")
        user_activity = UserActivityDB()
        user_id = current_user.username
        user_activity.update_favourite_sessions(user_id, session_id)

        print("get stems files")
        downloader = StorageEngineDownloader(bucket)
        session_pattern = f"steams/{session_id}"
        my_files = downloader.filter_objects(session_pattern)
        print(my_files)
        user_id = current_user.username
        stems_update = user_activity.transform_file_names(my_files, "steams", user_id)
        print(stems_update)
        print("update stems")
        user_activity.update_favourite_stems(stems_update, user_id, session_id)

        return {"message": "Session table updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@user_activity.post("/update_user_likes")
def update_user_likes(
    session_id: str, current_user: UserInDB = Depends(get_current_user)
):
    try:
        user_activity = UserActivityDB()
        user_id = current_user.username
        user_activity.update_playlist_likes(user_id, session_id)

        return {"message": "Likes table updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@user_activity.post("/update_user_plays")
def update_user_plays(
    session_id: str, current_user: UserInDB = Depends(get_current_user)
):
    try:
        user_activity = UserActivityDB()
        user_id = current_user.username
        user_activity.update_playlist_plays(user_id, session_id)

        return {"message": "Likes table updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@user_activity.post("/update_user_arrangements")
def update_user_arrangements(
    bucket: str,
    session_id: str,
    arrange_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    try:
        # prepare params
        copy_from_file = f"steams/{session_id}/{arrange_id}"
        copy_to_file = f"favs/{session_id}/{arrange_id}"
        prefix_ = f"steams/{session_id}"
        user_id = current_user.username

        downloader = StorageEngineDownloader(bucket)
        user_activity = UserActivityDB()

        # copy file from steams to favs
        downloader.copy_objects(source_key=copy_from_file, destination_key=copy_to_file)

        # Prep update for arrangement table
        my_files = downloader.filter_objects(prefix_)
        fav_arrangement_list = my_files.tolist()
        fav_arrangement_list.append(copy_to_file)

        update_fav_arrangement_data = pd.DataFrame(
            {
                "paths": fav_arrangement_list,
                "user_id": [user_id] * len(fav_arrangement_list),
                "session_id": [session_id] * len(fav_arrangement_list),
            }
        )

        user_activity.update_favourite_arrangements(
            update_fav_arrangement_data, user_id, session_id
        )

        return {"message": "Arragement table updated successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@user_activity.get("/get_favourites_stems")
def get_favourites_stems(
    session_id: str, current_user: UserInDB = Depends(get_current_user)
):
    try:
        user_activity = UserActivityDB()
        user_id = current_user.username

        my_files = user_activity.get_favourite_stems(user_id, session_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )

    return my_files


@user_activity.get("/get_favourites_sessions")
def get_favourites_sessions(current_user: UserInDB = Depends(get_current_user)):
    try:
        user_activity = UserActivityDB()
        user_id = current_user.username

        my_files = user_activity.get_favourite_sessions(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )

    return my_files


@user_activity.get("/get_playlist_stats")
def get_playlist_stats(current_user: UserInDB = Depends(get_current_user)):
    try:
        user_activity = UserActivityDB()
        user_id = current_user.username

        my_files = user_activity.get_playlist_stats(user_id)
        serialize_my_files = jsonable_encoder(my_files)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )

    return JSONResponse(content=serialize_my_files)
