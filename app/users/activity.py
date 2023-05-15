import psycopg2
import pandas as pd
from datetime import datetime
from pydantic import Field, BaseSettings
from typing import List

class DatabaseSettings(BaseSettings):
    host: str = Field(..., env="DB_HOST")
    dbname: str = Field(..., env="DB_NAME")
    user: str = Field(..., env="DB_USER")
    password: str = Field(..., env="DB_PASSWORD")
    port: str = Field(..., env="DB_PORT")

class UserActivityDB:
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
    
    def get_favourite_sessions(self, current_user_id):
        # Fetch the favourite session records for the current user
        query = """
        SELECT session_id
        FROM favourite_sessions
        WHERE user_id = %s
        ORDER BY created_at DESC
        """
        my_conn = self.db_conn()
        with my_conn.cursor() as cursor:
            cursor.execute(query, (current_user_id,))
            favourite_sessions = cursor.fetchall()
        # Extract the session ids and return as a list
        return [session_id for (session_id,) in favourite_sessions]

    def update_favourite_sessions(self, current_user_id, current_session_id):
        # Fetch the existing session record, if any
        query = """
        SELECT *
        FROM favourite_sessions
        WHERE user_id = %s
        AND session_id = %s
        """
        my_conn = self.db_conn()
        with my_conn.cursor() as cursor:
            cursor.execute(query, (current_user_id, current_session_id))
            check_session = cursor.fetchall()
        print('checked is session exists in favs...')

        # If no session record exists, create one
        if not check_session:
            self.insert_to_favourite_sessions(current_user_id, current_session_id)


    def insert_to_favourite_sessions(self, current_user_id, current_session_id):

        print('updating db...')
        created_at = datetime.now()
        insert_query = """
        INSERT INTO favourite_sessions (session_id, user_id, created_at)
        VALUES (%s, %s, %s)
        """
        my_conn = self.db_conn()
        with my_conn.cursor() as cursor:
            cursor.execute(insert_query, (current_session_id, current_user_id, created_at))
            cursor.close()
            my_conn.commit()
        my_conn.close()

    def transform_file_names(self, file_names: List[str], folder: str, user_id: str):
        # Create a DataFrame from the list of file names
        file_names_df = pd.DataFrame(file_names, columns=["paths"])

        # Filter the DataFrame based on the specified conditions
        file_names_df = file_names_df[file_names_df["paths"].str.contains(f"{folder}/20")]
        file_names_df = file_names_df[file_names_df["paths"].str.contains(r'\.(wav|mp3)')]

        # Add a new column 'bucket'
        file_names_df["bucket"] = "favs-dump"

        # Add a new column 'user_id'
        file_names_df["user_id"] = user_id

        # Split the 'paths' column into separate columns
        file_names_df[["folder", "session_id", "file"]] = file_names_df["paths"].str.split('/', expand=True)

        # Select the desired columns from the DataFrame
        result_df = file_names_df[["paths", "session_id", "user_id"]]

        return result_df

    def get_favourite_stems(self, current_user_id: str, current_session_id: str):
        my_conn = self.db_conn()

        with my_conn.cursor() as cursor:
            query = """
                SELECT * FROM favourite_stems
                WHERE session_id = %s AND user_id = %s
            """
            cursor.execute(query, (current_session_id, current_user_id))
            my_sessions = cursor.fetchall()
            my_sessions = pd.DataFrame(my_sessions, columns=["paths", "session_id", "user_id"])  

        my_sessions = my_sessions[my_sessions["paths"].str.contains("master.wav|master.mp3")]
        my_sessions = my_sessions.drop_duplicates(subset="paths", keep="first")

        if len(my_sessions["paths"]) > 25:
            my_files = my_sessions["paths"][:25].tolist()
        else:
            my_files = my_sessions["paths"].tolist()

        my_conn.close()
        return my_files

    def update_favourite_stems(self, updated_data, current_user_id, current_session_id):
        my_conn = self.db_conn()
        with my_conn.cursor() as cursor:
            # Check if a record exists for the current user and session
            query = """
                SELECT * FROM favourite_stems
                WHERE user_id = %s AND session_id = %s
            """
            cursor.execute(query, (current_user_id, current_session_id))
            check_session = cursor.fetchall()

            # If no record exists, insert the updated data into the table
            if not check_session:
                data_to_insert = list(updated_data.itertuples(index=False))

                # Define the INSERT query
                insert_query = """
                INSERT INTO favourite_stems (paths, session_id, user_id)  -- Replace with actual column names
                VALUES (%s, %s, %s) -- Update the number of placeholders based on the number of columns
                """
                # Insert the data into the database
                with my_conn.cursor() as cursor:
                    cursor.executemany(insert_query, data_to_insert)
                    my_conn.commit()
            else:
                delete_query = """
                    DELETE FROM favourite_stems
                    WHERE user_id = %s AND session_id = %s
                """
                cursor.execute(delete_query, (current_user_id, current_session_id))
                # If there are new rows to insert, insert them into the table
                if not updated_data.empty:
                    data_to_insert = list(updated_data.itertuples(index=False))

                    # Define the INSERT query
                    insert_query = """
                    INSERT INTO favourite_stems (paths, session_id, user_id)  -- Replace with actual column names
                    VALUES (%s, %s, %s) -- Update the number of placeholders based on the number of columns
                    """
                    with my_conn.cursor() as cursor:
                        cursor.executemany(insert_query, data_to_insert)
                        my_conn.commit()
        my_conn.close()
    
    def update_favourite_arrangements(self, updated_data, current_user_id, current_session_id):
        my_conn = self.db_conn()
        with my_conn.cursor() as cursor:
            # Check if a record exists for the current user and session
            query = """
                SELECT * FROM favourite_arrangements
                WHERE user_id = %s AND session_id = %s
            """
            cursor.execute(query, (current_user_id, current_session_id))
            check_session = cursor.fetchall()

            # If no record exists, insert the updated data into the table
            if not check_session:
                data_to_insert = list(updated_data.itertuples(index=False))

                # Define the INSERT query
                insert_query = """
                INSERT INTO favourite_arrangements (paths, user_id, session_id)  -- Replace with actual column names
                VALUES (%s, %s, %s) -- Update the number of placeholders based on the number of columns
                """
                # Insert the data into the database
                with my_conn.cursor() as cursor:
                    cursor.executemany(insert_query, data_to_insert)
                    my_conn.commit()
            else:
                delete_query = """
                    DELETE FROM favourite_arrangements
                    WHERE user_id = %s AND session_id = %s
                """
                cursor.execute(delete_query, (current_user_id, current_session_id))
                # If there are new rows to insert, insert them into the table
                if not updated_data.empty:
                    data_to_insert = list(updated_data.itertuples(index=False))
                    # Define the INSERT query
                    insert_query = """
                    INSERT INTO favourite_arrangements (paths, user_id, session_id)  -- Replace with actual column names
                    VALUES (%s, %s, %s) -- Update the number of placeholders based on the number of columns
                    """
                    with my_conn.cursor() as cursor:
                        cursor.executemany(insert_query, data_to_insert)
                        my_conn.commit()
        my_conn.close()

    
    def update_playlist_likes(self, current_user_id, session_id_):
        my_conn = self.db_conn()
        created_at_ = datetime.now()
        new_likes = pd.DataFrame({
            "session_id": [session_id_],
            "user_id": [current_user_id],
            "likes": [1],
            "created_at": [created_at_]
        })

        # Convert the DataFrame to a list of tuples
        data_to_insert = list(new_likes.itertuples(index=False))

        # Define the INSERT query
        insert_query = """
            INSERT INTO playlist_likes (session_id, user_id, likes, created_at)
            VALUES (%s, %s, %s, %s)
        """

        # Insert the data into the database
        with my_conn.cursor() as cursor:
            cursor.executemany(insert_query, data_to_insert)
            my_conn.commit()

        print("song added to likes...")
        my_conn.close()
    
    def update_playlist_plays(self, current_user_id, session_id_):
        my_conn = self.db_conn()
        created_at_ = datetime.now()
        new_plays = pd.DataFrame({
            "session_id": [session_id_],
            "user_id": [current_user_id],
            "plays": [1],
            "created_at": [created_at_]
        })

        # Convert the DataFrame to a list of tuples
        data_to_insert = list(new_plays.itertuples(index=False))
        print(data_to_insert)
        # Define the INSERT query
        insert_query = """
            INSERT INTO playlist_plays (session_id, user_id, plays, created_at)
            VALUES (%s, %s, %s, %s)
        """

        # Insert the data into the database
        with my_conn.cursor() as cursor:
            cursor.executemany(insert_query, data_to_insert)
            my_conn.commit()

        print("plays updated...")
        my_conn.close()

    def get_playlist_stats(self, current_user_id):
        my_conn = self.db_conn()
        with my_conn.cursor() as cursor:
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

            # New query: Get one row per group from favourite_arrangement table
            query_arrangement = """
                SELECT user_id, session_id, paths
                FROM favourite_arrangements
                WHERE user_id = %s AND paths LIKE '%%arrangement%%'
                ORDER BY session_id
            """
            cursor.execute(query_arrangement, (current_user_id,))
            my_arrangement = pd.DataFrame(cursor.fetchall(), columns=['user_id', 'session_id', 'paths'])

        my_conn.close()
        print("playlist stats retrieved...")
        # Merge likes, plays, and arrangement DataFrames on the 'session_id' column
        merged_df = pd.merge(my_likes, my_plays, on='session_id', how='outer')
        merged_df = pd.merge(merged_df, my_arrangement[['session_id', 'paths']], on='session_id', how='outer')
        #merged_df.dropna(subset=['paths'], inplace=True)
        json_res = merged_df.to_json(orient='records')
        #my_stats = {"likes": merged_df['likes'].astype(str),
        #            "plays": merged_df['plays'].astype(str),
        #            "session_id": merged_df['session_id'],
        #            "paths": merged_df['paths']}
        return json_res


