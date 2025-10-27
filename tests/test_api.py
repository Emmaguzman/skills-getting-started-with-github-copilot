"""
Tests for the FastAPI endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestRootEndpoint:
    """Tests for the root endpoint."""
    
    def test_root_redirect(self, client: TestClient):
        """Test that root endpoint redirects to static index.html."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for the activities endpoint."""
    
    def test_get_activities_success(self, client: TestClient):
        """Test successful retrieval of activities."""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Check structure of first activity
        first_activity = list(data.values())[0]
        assert "description" in first_activity
        assert "schedule" in first_activity
        assert "max_participants" in first_activity
        assert "participants" in first_activity
        assert isinstance(first_activity["participants"], list)
        assert isinstance(first_activity["max_participants"], int)
    
    def test_activities_contain_expected_fields(self, client: TestClient):
        """Test that all activities contain required fields."""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert isinstance(activity_name, str)
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            
            # Validate data types
            assert isinstance(activity_data["description"], str)
            assert isinstance(activity_data["schedule"], str)
            assert isinstance(activity_data["max_participants"], int)
            assert isinstance(activity_data["participants"], list)


class TestSignupEndpoint:
    """Tests for the activity signup endpoint."""
    
    def test_signup_success(self, client: TestClient):
        """Test successful signup for an activity."""
        # Use an activity that exists and add a new participant
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
    
    def test_signup_nonexistent_activity(self, client: TestClient):
        """Test signup for non-existent activity returns 404."""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@test.com"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_duplicate_participant(self, client: TestClient):
        """Test that duplicate signup returns 400."""
        # First signup
        client.post("/activities/Chess Club/signup?email=duplicate@test.com")
        
        # Second signup with same email
        response = client.post(
            "/activities/Chess Club/signup?email=duplicate@test.com"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student is already signed up"
    
    def test_signup_adds_participant_to_list(self, client: TestClient):
        """Test that signup actually adds participant to the activity."""
        email = "verify@test.com"
        
        # Get initial participant count
        activities_response = client.get("/activities")
        initial_participants = activities_response.json()["Chess Club"]["participants"]
        initial_count = len(initial_participants)
        
        # Sign up
        signup_response = client.post(f"/activities/Chess Club/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify participant was added
        activities_response = client.get("/activities")
        updated_participants = activities_response.json()["Chess Club"]["participants"]
        assert len(updated_participants) == initial_count + 1
        assert email in updated_participants


class TestRemoveParticipantEndpoint:
    """Tests for the remove participant endpoint."""
    
    def test_remove_participant_success(self, client: TestClient):
        """Test successful removal of a participant."""
        # First add a participant
        email = "remove@test.com"
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Then remove them
        response = client.delete(f"/activities/Chess Club/participants/{email}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Chess Club" in data["message"]
    
    def test_remove_participant_nonexistent_activity(self, client: TestClient):
        """Test removal from non-existent activity returns 404."""
        response = client.delete(
            "/activities/Nonexistent Activity/participants/test@test.com"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_remove_nonexistent_participant(self, client: TestClient):
        """Test removal of non-existent participant returns 404."""
        response = client.delete(
            "/activities/Chess Club/participants/nonexistent@test.com"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Participant not found in this activity"
    
    def test_remove_participant_actually_removes(self, client: TestClient):
        """Test that removal actually removes participant from the activity."""
        email = "actualremove@test.com"
        
        # Add participant
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Verify participant was added
        activities_response = client.get("/activities")
        participants = activities_response.json()["Chess Club"]["participants"]
        assert email in participants
        initial_count = len(participants)
        
        # Remove participant
        remove_response = client.delete(f"/activities/Chess Club/participants/{email}")
        assert remove_response.status_code == 200
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        updated_participants = activities_response.json()["Chess Club"]["participants"]
        assert email not in updated_participants
        assert len(updated_participants) == initial_count - 1


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_signup_with_special_characters_in_email(self, client: TestClient):
        """Test signup with special characters in email."""
        # Note: + in query parameters gets decoded to space by FastAPI/Starlette
        # So test+special becomes "test special" 
        email = "test+special@example-domain.co.uk"
        response = client.post(f"/activities/Chess Club/signup?email={email}")
        
        assert response.status_code == 200
        
        # Verify participant was added (note: + becomes space in query params)
        activities_response = client.get("/activities")
        participants = activities_response.json()["Chess Club"]["participants"]
        # The email will be decoded as "test special@example-domain.co.uk"
        assert "test special@example-domain.co.uk" in participants
    
    def test_activity_name_with_spaces_and_special_chars(self, client: TestClient):
        """Test operations with activity names containing spaces."""
        # Test with URL encoding for spaces
        response = client.post(
            "/activities/Chess%20Club/signup?email=spaces@test.com"
        )
        assert response.status_code == 200
    
    def test_case_sensitivity(self, client: TestClient):
        """Test case sensitivity of activity names."""
        # Should fail because case doesn't match
        response = client.post(
            "/activities/chess club/signup?email=case@test.com"
        )
        assert response.status_code == 404
    
    def test_empty_email_parameter(self, client: TestClient):
        """Test signup with empty email parameter."""
        response = client.post("/activities/Chess Club/signup?email=")
        # This should still work as FastAPI will pass empty string
        assert response.status_code == 200


class TestDataIntegrity:
    """Tests for data integrity and consistency."""
    
    def test_participant_count_consistency(self, client: TestClient):
        """Test that participant counts remain consistent."""
        # Get initial state
        response = client.get("/activities")
        initial_data = response.json()
        
        for activity_name, activity_data in initial_data.items():
            participant_count = len(activity_data["participants"])
            max_participants = activity_data["max_participants"]
            
            # Ensure we never exceed max participants (this is a business rule we might want to add)
            assert participant_count <= max_participants
    
    def test_multiple_operations_consistency(self, client: TestClient):
        """Test consistency after multiple operations."""
        email1 = "multi1@test.com"
        email2 = "multi2@test.com"
        
        # Add two participants
        client.post(f"/activities/Chess Club/signup?email={email1}")
        client.post(f"/activities/Chess Club/signup?email={email2}")
        
        # Remove one
        client.delete(f"/activities/Chess Club/participants/{email1}")
        
        # Verify final state
        response = client.get("/activities")
        participants = response.json()["Chess Club"]["participants"]
        
        assert email1 not in participants
        assert email2 in participants