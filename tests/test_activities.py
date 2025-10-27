"""
Tests for the activities data and business logic.
"""

import pytest
from fastapi.testclient import TestClient


class TestActivitiesData:
    """Tests for the activities data structure and validation."""
    
    def test_all_activities_have_required_fields(self, client: TestClient):
        """Test that all activities have the required fields."""
        response = client.get("/activities")
        activities = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_data in activities.items():
            for field in required_fields:
                assert field in activity_data, f"Activity '{activity_name}' missing field '{field}'"
    
    def test_activities_data_types(self, client: TestClient):
        """Test that activity data has correct types."""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            assert isinstance(activity_name, str)
            assert isinstance(activity_data["description"], str)
            assert isinstance(activity_data["schedule"], str)
            assert isinstance(activity_data["max_participants"], int)
            assert isinstance(activity_data["participants"], list)
            
            # Test that max_participants is positive
            assert activity_data["max_participants"] > 0
            
            # Test that all participants are strings (emails)
            for participant in activity_data["participants"]:
                assert isinstance(participant, str)
                assert "@" in participant  # Basic email validation
    
    def test_activity_names_are_unique(self, client: TestClient):
        """Test that all activity names are unique."""
        response = client.get("/activities")
        activities = response.json()
        
        activity_names = list(activities.keys())
        unique_names = set(activity_names)
        
        assert len(activity_names) == len(unique_names), "Duplicate activity names found"
    
    def test_participants_do_not_exceed_max(self, client: TestClient):
        """Test that current participants never exceed max_participants."""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            current_count = len(activity_data["participants"])
            max_count = activity_data["max_participants"]
            
            assert current_count <= max_count, (
                f"Activity '{activity_name}' has {current_count} participants "
                f"but max is {max_count}"
            )
    
    def test_participant_emails_are_valid_format(self, client: TestClient):
        """Test that participant emails follow basic email format."""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            for participant in activity_data["participants"]:
                assert "@" in participant, f"Invalid email format: {participant}"
                assert "." in participant.split("@")[1], f"Invalid domain format: {participant}"
    
    def test_no_duplicate_participants_in_same_activity(self, client: TestClient):
        """Test that no activity has duplicate participants."""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            participants = activity_data["participants"]
            unique_participants = set(participants)
            
            assert len(participants) == len(unique_participants), (
                f"Activity '{activity_name}' has duplicate participants"
            )


class TestBusinessLogic:
    """Tests for business logic and rules."""
    
    def test_signup_increases_participant_count(self, client: TestClient):
        """Test that signup increases participant count by exactly 1."""
        # Get initial count
        response = client.get("/activities")
        initial_count = len(response.json()["Chess Club"]["participants"])
        
        # Sign up new participant
        signup_response = client.post(
            "/activities/Chess Club/signup?email=newparticipant@test.com"
        )
        assert signup_response.status_code == 200
        
        # Check final count
        response = client.get("/activities")
        final_count = len(response.json()["Chess Club"]["participants"])
        
        assert final_count == initial_count + 1
    
    def test_remove_decreases_participant_count(self, client: TestClient):
        """Test that removal decreases participant count by exactly 1."""
        # Add a participant first
        email = "toremove@test.com"
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Get count after addition
        response = client.get("/activities")
        count_after_add = len(response.json()["Chess Club"]["participants"])
        
        # Remove the participant
        remove_response = client.delete(f"/activities/Chess Club/participants/{email}")
        assert remove_response.status_code == 200
        
        # Check final count
        response = client.get("/activities")
        final_count = len(response.json()["Chess Club"]["participants"])
        
        assert final_count == count_after_add - 1
    
    def test_cannot_signup_twice_for_same_activity(self, client: TestClient):
        """Test that a participant cannot sign up twice for the same activity."""
        email = "duplicate@test.com"
        
        # First signup should succeed
        response1 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_can_signup_for_different_activities(self, client: TestClient):
        """Test that a participant can sign up for multiple different activities."""
        email = "multi@test.com"
        
        # Sign up for first activity
        response1 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Sign up for second activity
        response2 = client.post(f"/activities/Programming Class/signup?email={email}")
        assert response2.status_code == 200
        
        # Verify participant is in both activities
        activities_response = client.get("/activities")
        activities = activities_response.json()
        
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Programming Class"]["participants"]
    
    def test_remove_from_one_activity_does_not_affect_others(self, client: TestClient):
        """Test that removing from one activity doesn't affect others."""
        email = "crossactivity@test.com"
        
        # Sign up for two activities
        client.post(f"/activities/Chess Club/signup?email={email}")
        client.post(f"/activities/Programming Class/signup?email={email}")
        
        # Remove from one activity
        remove_response = client.delete(f"/activities/Chess Club/participants/{email}")
        assert remove_response.status_code == 200
        
        # Verify still in the other activity
        activities_response = client.get("/activities")
        activities = activities_response.json()
        
        assert email not in activities["Chess Club"]["participants"]
        assert email in activities["Programming Class"]["participants"]


class TestErrorHandling:
    """Tests for error handling and edge cases."""
    
    def test_missing_email_parameter(self, client: TestClient):
        """Test signup without email parameter."""
        response = client.post("/activities/Chess Club/signup")
        # FastAPI will return 422 for missing required query parameter
        assert response.status_code == 422
    
    def test_url_encoding_in_activity_names(self, client: TestClient):
        """Test that URL encoding works correctly for activity names."""
        # Test with spaces encoded as %20
        response = client.post(
            "/activities/Chess%20Club/signup?email=urltest@test.com"
        )
        assert response.status_code == 200
        
        # Test with spaces encoded as + (this actually doesn't work in path parameters)
        # + encoding only works in query parameters, not path parameters
        response = client.post(
            "/activities/Programming+Class/signup?email=urltest2@test.com"
        )
        # This should fail because + is not decoded in path parameters
        assert response.status_code == 404
    
    def test_url_encoding_in_email_addresses(self, client: TestClient):
        """Test that URL encoding works correctly for email addresses."""
        # Test with + in email (should be encoded as %2B)
        email = "test%2Bspecial@test.com"  # This represents test+special@test.com
        response = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response.status_code == 200