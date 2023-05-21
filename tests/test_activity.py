import unittest
from unittest.mock import patch, MagicMock
from app.users.activity import UserActivityDB, DatabaseSettings
import pandas as pd

class TestUserActivityDB(unittest.TestCase):

    @patch('activity.psycopg2')
    @patch.object(DatabaseSettings, "__init__", lambda x, y: None)  # Mocking DatabaseSettings
    def test_db_conn(self, mock_psycopg2):
        # Given
        mock_psycopg2.connect.return_value = "test_connection"
        user_activity_db = UserActivityDB()

        # When
        result = user_activity_db.db_conn()

        # Then
        self.assertEqual(result, "test_connection")
        mock_psycopg2.connect.assert_called_once()

    @patch.object(UserActivityDB, 'db_conn')
    def test_get_favourite_sessions(self, mock_db_conn):
        # Given
        mock_cursor = MagicMock()
        mock_db_conn.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [(1,), (2,), (3,)]
        user_activity_db = UserActivityDB()

        # When
        result = user_activity_db.get_favourite_sessions('test_user')

        # Then
        self.assertEqual(result, [1, 2, 3])
        mock_db_conn.assert_called_once()
    
    def test_get_favourite_stems(self, mock_db_conn):
        # Given
        mock_cursor = MagicMock()
        mock_db_conn.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [('path1', 'session1', 'user1'),
                                             ('path2', 'session2', 'user2')]
        user_activity_db = UserActivityDB()

        # When
        result = user_activity_db.get_favourite_stems('test_user', 'test_session')

        # Then
        self.assertEqual(result, ['path1', 'path2'])

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
    def test_update_favourite_sessions(self, mock_db_conn):
        # Given
        mock_cursor = MagicMock()
        mock_db_conn.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        user_activity_db = UserActivityDB()
        updated_data = pd.DataFrame({'paths': ['path1', 'path2'],
                                     'session_id': ['session1', 'session2'],
                                     'user_id': ['user1', 'user2']})

        # When
        user_activity_db.update_favourite_sessions(updated_data, 'test_user', 'test_session')

        # Then
        mock_cursor.execute.assert_called()  # Check if execute is called. Actual call parameters will vary.

    @patch.object(UserActivityDB, 'db_conn')
    def test_insert_to_favourite_sessions(self, mock_db_conn):
        # Given
        mock_cursor = MagicMock()
        mock_db_conn.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        user_activity_db = UserActivityDB()

        # When
        user_activity_db.insert_to_favourite_sessions('test_user', 'test_session', 'test_path')

        # Then
        mock_cursor.executemany.assert_called()  # Check if executemany is called. Actual call parameters will vary.

    def test_transform_file_names(self):
        # Given
        user_activity_db = UserActivityDB()
        data = pd.DataFrame({'paths': ['path1', 'path2'],
                             'session_id': ['session1', 'session2'],
                             'user_id': ['user1', 'user2']})

        # When
        result = user_activity_db.transform_file_names(data)

        # Then
        expected = pd.DataFrame({'paths': ['path1_master.wav', 'path2_master.wav'],
                                 'session_id': ['session1', 'session2'],
                                 'user_id': ['user1', 'user2']})
        pd.testing.assert_frame_equal(result, expected)


if __name__ == '__main__':
    unittest.main()
