import unittest
import os
from unittest.mock import patch, MagicMock
from app.users.activity import UserActivityDB, DatabaseSettings
import pandas as pd

class TestDatabaseSettings(unittest.TestCase):
    def test_db_settings(self):
        mock_db_settings = {
            "host": "localhost",
            "dbname": "db_name",
            "user": "db_user",
            "password": "db_password",
            "port": "db_port"
        }
        db_settings = DatabaseSettings.parse_obj(mock_db_settings)
        self.assertEqual(db_settings.host, 'localhost')


class TestUserActivityDB(unittest.TestCase):
    @patch('app.users.activity.psycopg2.connect')
    @patch.dict('os.environ', {
        "DB_HOST": "localhost",
        "DB_NAME": "db_name",
        "DB_USER": "db_user",
        "DB_PASSWORD": "db_password",
        "DB_PORT": "db_port"
    })
    def test_db_conn(self, mock_connect):
        UserActivityDB().db_conn()
        mock_connect.assert_called_once()

    
    @patch.object(UserActivityDB, 'db_conn')
    def test_get_favourite_sessions(self, mock_db_conn):
        # Given
        test_user_id = "test_user"
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [('session_1',), ('session_2',)]
        mock_db_conn.return_value.cursor.return_value.__enter__.return_value = mock_cursor

        # When
        actual_sessions = UserActivityDB().get_favourite_sessions(test_user_id)

        # Then
        expected_sessions = ['session_1', 'session_2']
        self.assertListEqual(actual_sessions, expected_sessions)
        query = """
        SELECT session_id
        FROM favourite_sessions
        WHERE user_id = %s
        ORDER BY created_at DESC
        """
        mock_cursor.execute.assert_called_once_with(
            query, (test_user_id,)
        )


    @patch.object(UserActivityDB, 'db_conn')
    def test_get_favourite_stems(self, mock_db_conn):
        # Given
        mock_cursor = MagicMock()
        mock_db_conn.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ('path1/master.wav', 'session1', 'user1'),
            ('path2/master.mp3', 'session2', 'user2')
        ]
        user_activity_db = UserActivityDB()

        # When
        result = user_activity_db.get_favourite_stems('test_user', 'test_session')

        # Then
        self.assertEqual(result, ['path1/master.wav', 'path2/master.mp3'])

    @patch.object(UserActivityDB, 'db_conn')
    def test_update_favourite_stems(self, mock_db_conn):
        # Given
        mock_cursor = MagicMock()
        mock_db_conn.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        user_activity_db = UserActivityDB()
        updated_data = pd.DataFrame({'paths': ['path1', 'path2'],
                                     'session_id': ['session1', 'session2'],
                                     'user_id': ['user1', 'user2']})

        # When
        user_activity_db.update_favourite_stems(updated_data, 'test_user', 'test_session')

        # Then
        mock_cursor.execute.assert_called() 
    
    @patch.object(UserActivityDB, 'db_conn')
    def test_update_favourite_arrangements(self, mock_db_conn):
        # Given
        mock_cursor = MagicMock()
        mock_db_conn.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        user_activity_db = UserActivityDB()
        updated_data = pd.DataFrame({'paths': ['path1', 'path2'],
                                     'session_id': ['session1', 'session2'],
                                     'user_id': ['user1', 'user2']})

        # When
        user_activity_db.update_favourite_arrangements(updated_data, 'test_user', 'test_session')

        # Then
        mock_cursor.execute.assert_called()  # Check if execute is called. Actual call parameters will vary.

    @patch.object(UserActivityDB, 'db_conn')
    def test_update_playlist_likes(self, mock_db_conn):
        # Given
        mock_cursor = MagicMock()
        mock_db_conn.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        user_activity_db = UserActivityDB()

        # When
        user_activity_db.update_playlist_likes('test_user', 'test_session')

        # Then
        mock_cursor.executemany.assert_called()  # Check if executemany is called. Actual call parameters will vary.

    @patch.object(UserActivityDB, 'db_conn')
    def test_update_playlist_plays(self, mock_db_conn):
        # Given
        mock_cursor = MagicMock()
        mock_db_conn.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        user_activity_db = UserActivityDB()

        # When
        user_activity_db.update_playlist_plays('test_user', 'test_session')

        # Then
        mock_cursor.executemany.assert_called()  # Check if executemany is called. Actual call parameters will vary.

    @patch.object(UserActivityDB, 'db_conn')
    def test_get_playlist_stats(self, mock_db_conn):
        # Given
        mock_cursor = MagicMock()
        mock_db_conn.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.side_effect = [[('session1', 10)], [('session1', 5)], [('user1', 'session1', 'path1')]]
        user_activity_db = UserActivityDB()

        # When
        result = user_activity_db.get_playlist_stats('test_user')

        # Then
        expected = pd.DataFrame({'session_id': ['session1'], 'likes': [10], 'plays': [5], 'paths': ['path1']}).to_json(orient='records')
        self.assertEqual(result, expected)

    @patch.object(UserActivityDB, 'db_conn')
    @patch.object(UserActivityDB, 'insert_to_favourite_sessions')
    def test_update_favourite_sessions(self, mock_insert_to_favourite_sessions, mock_db_conn):
        # Given
        mock_cursor = MagicMock()
        mock_db_conn.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []  # simulate situation where no session record exists
        user_activity_db = UserActivityDB()

        # When
        user_activity_db.update_favourite_sessions('test_user', 'test_session')

        # Then
        mock_insert_to_favourite_sessions.assert_called_once_with('test_user', 'test_session')  # Check if 'insert_to_favourite_sessions' is called.


    @patch.object(UserActivityDB, 'db_conn')
    def test_insert_to_favourite_sessions(self, mock_db_conn):
        # Given
        mock_cursor = MagicMock()
        mock_db_conn.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        user_activity_db = UserActivityDB()

        # When
        user_activity_db.insert_to_favourite_sessions('test_user', 'test_session')

        # Then
        mock_cursor.execute.assert_called()  # Check if execute is called.

    def test_transform_file_names(self):
        # Given
        user_activity_db = UserActivityDB()
        file_names = ['temp/2022_session1/2022_session1_master.wav', 'temp/2022_session2/2022_session2_master.mp3']  # make sure these match the filter conditions


        # When
        result = user_activity_db.transform_file_names(file_names, 'temp', 'test_user')
        print(result)
        # Then
        expected = pd.DataFrame({
            'paths': ['temp/2022_session1/2022_session1_master.wav', 
                    'temp/2022_session2/2022_session2_master.mp3'],
            'session_id': ['2022_session1', '2022_session2'],
            'user_id': ['test_user', 'test_user']
        })
        pd.testing.assert_frame_equal(result, expected)




if __name__ == '__main__':
    unittest.main()
