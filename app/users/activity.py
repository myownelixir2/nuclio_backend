import psycopg2
import pandas as pd
from datetime import datetime
from pydantic import Field, BaseSettings

class DatabaseSettings(BaseSettings):
    host: str = Field(..., env="DB_HOST")
    dbname: str = Field(..., env="DB_NAME")
    user: str = Field(..., env="DB_USER")
    password: str = Field(..., env="DB_PASSWORD")
    port: str = Field(..., env="DB_PORT")
    

class UserActivityDB:
    def __init__(self, job_config, asset_type):
        self.job_config = job_config
        self.asset_type = asset_type
    
    def db_conn(self):
        db_settings = DatabaseSettings()

        connection = psycopg2.connect(
            host=db_settings.host,
            dbname=db_settings.dbname,
            user=db_settings.user,
            password=db_settings.password,
            port=db_settings.port
        )
        return connection
    
    def update_favourite_sessions(self, current_user_id, current_session_id):
        # Fetch the existing session record, if any
        query = """
        SELECT *
        FROM favourite_sessions
        WHERE user_id = %s
        AND session_id = %s
        """

        with self.db_conn.cursor() as cursor:
            cursor.execute(query, (current_user_id, current_session_id))
            check_session = cursor.fetchall()

        # If no session record exists, create one
        if not check_session:
            created_at = datetime.now()
            insert_query = """
            INSERT INTO favourite_sessions (session_id, user_id, created_at)
            VALUES (%s, %s, %s)
            """

            with self.db_conn.cursor() as cursor:
                cursor.execute(insert_query, (current_session_id, current_user_id, created_at))
                self.db_conn.commit()
                
    
    def update_favourite_arrangements(self, updated_data, current_user_id, current_session_id):
        with self.db_conn.cursor() as cursor:
            # Check if a record exists for the current user and session
            query = """
                SELECT * FROM favourite_arrangements
                WHERE user_id = %s AND session_id = %s
            """
            cursor.execute(query, (current_user_id, current_session_id))
            check_session = cursor.fetchall()

            # If no record exists, insert the updated data into the table
            if len(check_session) == 0:
                updated_data_df = pd.DataFrame(updated_data)
                updated_data_df.to_sql("favourite_arrangements", self.db_conn, if_exists="append", index=False)
          
    
    def update_playlist_likes(self, current_user_id, session_id_):
        created_at_ = datetime.now()
        new_likes = pd.DataFrame({
            "session_id": [session_id_],
            "user_id": [current_user_id],
            "likes": [1],
            "created_at": [created_at_]
        })

        # Add the new_likes DataFrame to the "playlist_likes" table
        new_likes.to_sql("playlist_likes", self.db_conn, if_exists="append", index=False)
        print("song added to likes...")
    
    def update_playlist_plays(self, current_user_id, session_id_):
        created_at_ = datetime.now()
        new_plays = pd.DataFrame({
            "session_id": [session_id_],
            "user_id": [current_user_id],
            "plays": [1],
            "created_at": [created_at_]
        })

        # Add the new_plays DataFrame to the "playlist_plays" table
        new_plays.to_sql("playlist_plays", self.db_conn, if_exists="append", index=False)
    
    def get_playlist_stats(self, current_user_id):
        with self.db_conn.cursor() as cursor:
            # Get likes
            query_likes = """
                SELECT session_id, COUNT(*) as likes
                FROM playlist_likes
                WHERE user_id = %s
                GROUP BY session_id
            """
            cursor.execute(query_likes, (current_user_id,))
            my_likes = pd.DataFrame(cursor.fetchall(), columns=['session_id', 'likes'])

            # Get plays
            query_plays = """
                SELECT session_id, COUNT(*) as plays
                FROM playlist_plays
                WHERE user_id = %s
                GROUP BY session_id
            """
            cursor.execute(query_plays, (current_user_id,))
            my_plays = pd.DataFrame(cursor.fetchall(), columns=['session_id', 'plays'])

        my_stats = {"likes": my_likes, "plays": my_plays}
        return my_stats