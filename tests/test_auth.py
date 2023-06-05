import unittest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from app.users.auth import get_current_user, UserInDB, FirebaseSettings


class TestAuth(unittest.TestCase):
    @patch("firebase_admin.auth.verify_id_token")
    @patch("firebase_admin.auth.get_user")
    def test_get_current_user(self, mock_get_user, mock_verify_id_token):
        import asyncio

        mock_token = "test_token"
        mock_uid = "test_uid"
        mock_get_user.return_value = MagicMock(uid=mock_uid)
        mock_verify_id_token.return_value = {"uid": mock_uid}

        result = asyncio.run(get_current_user(mock_token))
        expected_result = UserInDB(username=mock_uid)

        self.assertEqual(result, expected_result)

    @patch("firebase_admin.auth.verify_id_token")
    def test_get_current_user_invalid_token(self, mock_verify_id_token):
        import asyncio

        mock_token = "test_token"
        mock_verify_id_token.side_effect = ValueError("Invalid token")

        with self.assertRaises(HTTPException):
            asyncio.run(get_current_user(mock_token))

    def test_initialize_firebase(self):
        mock_path = "/path/to/mock/firebase_credentials.json"
        with patch("app.users.auth.credentials.Certificate") as mock_certificate, patch(
            "app.users.auth.initialize_app"
        ) as mock_initialize_app:
            settings = FirebaseSettings(firebase_credential_json=mock_path)
            mock_certificate.assert_called_with(mock_path)
            mock_initialize_app.assert_called_with(mock_certificate.return_value)


if __name__ == "__main__":
    unittest.main()
