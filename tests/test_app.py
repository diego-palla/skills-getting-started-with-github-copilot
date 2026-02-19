from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


_INITIAL_ACTIVITIES = deepcopy(activities)


@pytest.fixture(autouse=True)
def reset_activities_state():
    activities.clear()
    activities.update(deepcopy(_INITIAL_ACTIVITIES))
    yield
    activities.clear()
    activities.update(deepcopy(_INITIAL_ACTIVITIES))


@pytest.fixture
def client():
    return TestClient(app)


def test_root_redirects_to_static_index(client):
    # Arrange
    endpoint = "/"

    # Act
    response = client.get(endpoint, follow_redirects=False)

    # Assert
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_activity_mapping(client):
    # Arrange
    endpoint = "/activities"

    # Act
    response = client.get(endpoint)
    payload = response.json()

    # Assert
    assert response.status_code == 200
    assert isinstance(payload, dict)
    assert len(payload) > 0

    first_activity = next(iter(payload.values()))
    assert {"description", "schedule", "max_participants", "participants"}.issubset(first_activity.keys())


def test_signup_adds_participant_for_existing_activity(client):
    # Arrange
    activity_name = "Basketball Team"
    email = "new-student@mergington.edu"

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == f"Signed up {email} for {activity_name}"
    assert email in activities[activity_name]["participants"]


def test_signup_returns_404_for_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"
    email = "student@mergington.edu"

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": email})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_returns_400_for_duplicate_participant(client):
    # Arrange
    activity_name = "Basketball Team"
    existing_email = activities[activity_name]["participants"][0]

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": existing_email})

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up"


def test_signup_returns_422_when_email_is_missing(client):
    # Arrange
    activity_name = "Basketball Team"

    # Act
    response = client.post(f"/activities/{activity_name}/signup")

    # Assert
    assert response.status_code == 422


def test_signup_supports_url_encoded_activity_name(client):
    # Arrange
    encoded_activity_name = "Basketball%20Team"
    email = "encoded-name@mergington.edu"

    # Act
    response = client.post(f"/activities/{encoded_activity_name}/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert email in activities["Basketball Team"]["participants"]


def test_unregister_removes_existing_participant(client):
    # Arrange
    activity_name = "Soccer Club"
    email = activities[activity_name]["participants"][0]

    # Act
    response = client.delete(f"/activities/{activity_name}/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == f"Unregistered {email} from {activity_name}"
    assert email not in activities[activity_name]["participants"]


def test_unregister_returns_404_for_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"
    email = "student@mergington.edu"

    # Act
    response = client.delete(f"/activities/{activity_name}/signup", params={"email": email})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_returns_404_when_student_not_signed_up(client):
    # Arrange
    activity_name = "Drama Club"
    email = "not-registered@mergington.edu"

    # Act
    response = client.delete(f"/activities/{activity_name}/signup", params={"email": email})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Student not signed up"


def test_unregister_returns_422_when_email_is_missing(client):
    # Arrange
    activity_name = "Drama Club"

    # Act
    response = client.delete(f"/activities/{activity_name}/signup")

    # Assert
    assert response.status_code == 422


def test_unregister_change_is_reflected_in_activities_response(client):
    # Arrange
    activity_name = "Art Studio"
    email = activities[activity_name]["participants"][0]

    # Act
    delete_response = client.delete(f"/activities/{activity_name}/signup", params={"email": email})
    activities_response = client.get("/activities")
    updated_payload = activities_response.json()

    # Assert
    assert delete_response.status_code == 200
    assert activities_response.status_code == 200
    assert email not in updated_payload[activity_name]["participants"]