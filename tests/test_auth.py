import unittest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from firebase_admin import auth
from app.users.auth import get_current_user, UserInDB, FirebaseSettings


class TestAuth(unittest.TestCase):
    @patch('your_module_path.auth.verify_id_token')
    @patch('your_module_path.auth.get_user')
    def test_get_current_user(self, mock_get_user, mock_verify_id_token):
        mock_token = 'test_token'
        mock_uid = 'test_uid'
        mock_get_user.return_value = auth.UserRecord(MagicMock(), {'uid': mock_uid})
        mock_verify_id_token.return_value = {'uid': mock_uid}

        result = get_current_user(mock_token)
        expected_result = UserInDB(username=mock_uid)

        self.assertEqual(result, expected_result)

    @patch('your_module_path.auth.verify_id_token')
    def test_get_current_user_invalid_token(self, mock_verify_id_token):
        mock_token = 'test_token'
        mock_verify_id_token.side_effect = ValueError('Invalid token')

        with self.assertRaises(HTTPException):
            get_current_user(mock_token)

    def test_initialize_firebase(self):
        mock_path = '/path/to/mock/firebase_credentials.json'
        with patch('your_module_path.credentials.Certificate') as mock_certificate, \
                patch('your_module_path.initialize_app') as mock_initialize_app:
            settings = FirebaseSettings(firebase_credential_json=mock_path)
            mock_certificate.assert_called_with(mock_path)
            mock_initialize_app.assert_called_with(mock_certificate.return_value)


if __name__ == '__main__':
    unittest.main()
