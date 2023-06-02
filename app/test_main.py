# Related third party imports
from fastapi.testclient import TestClient
# Local application/library specific imports
from app.users.auth import get_current_user, UserInDB
from app.audio_processing import audio_processing
from app.job_processing import job_processing
from app.file_management import file_management
from app.user_activity import user_activity
from app.main import app 
from unittest import mock

client = TestClient(app)

app.include_router(job_processing)
app.include_router(job_processing)
app.include_router(audio_processing)
app.include_router(file_management)
app.include_router(user_activity)

def test_create_job():
    # Mock the current_user dependency
    app.dependency_overrides[get_current_user] = lambda: UserInDB(username="test", email="test@example.com")

    response = client.post(
        "/create_job",
        json={
            "job_id": "test_job",
            "payload": {"key": "value"}
        },
    )

    assert response.status_code == 200
    assert response.json() == True


def test_job_id():
    # Mock the current_user dependency
    app.dependency_overrides[get_current_user] = lambda: UserInDB(username="test", email="test@example.com")

    response = client.post(
        "/job",
        json={
            "job_id": "test_job"
        },
    )

    assert response.status_code == 200
    assert response.json() == {"job_id": "test_job"}


def test_clean_up_assets():
    with mock.patch('app.utils.utils.JobUtils.remove_files') as mock_remove_files:
        mock_remove_files.return_value = True
        
        response = client.post("/clean_up_assets", json={"job_id": "test_job_id"})
        
        assert response.status_code == 200
        assert response.json() == True
        mock_remove_files.assert_called()

def test_clean_up_temp_with_invalid_pattern():
    response = client.post("/clean_up_temp", 
                            json={"job_id": "test_job_id", "pattern": "invalid", "random_id": "test_id"})

    assert response.status_code == 404

def test_clean_up_temp_with_valid_pattern():
    with mock.patch('app.utils.utils.JobUtils.remove_files') as mock_remove_files:
        mock_remove_files.return_value = True
        
        response = client.post("/clean_up_temp", 
                                json={"job_id": "test_job_id", "pattern": "mixdown", "random_id": "test_id"})
        
        assert response.status_code == 200
        assert response.json() == True
        mock_remove_files.assert_called()