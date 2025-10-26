"""Integration tests for wagtail-lms full workflows."""

import json

import pytest
from django.urls import reverse

from wagtail_lms.models import CourseEnrollment, SCORMAttempt, SCORMData


@pytest.mark.django_db
class TestFullCourseWorkflow:
    """Test complete course enrollment and completion workflow."""

    def test_complete_course_workflow(self, client, user, course_page, scorm_package):
        """Test full workflow from enrollment to course completion."""
        client.force_login(user)

        # Step 1: Enroll in course
        enroll_url = reverse("wagtail_lms:enroll_course", args=[course_page.id])
        response = client.get(enroll_url)
        assert response.status_code == 302

        enrollment = CourseEnrollment.objects.get(user=user, course=course_page)
        assert enrollment is not None

        # Step 2: Start course (access player)
        player_url = reverse("wagtail_lms:scorm_player", args=[course_page.id])
        response = client.get(player_url)
        assert response.status_code == 200

        attempt = SCORMAttempt.objects.get(user=user, scorm_package=scorm_package)
        assert attempt.completion_status == "incomplete"

        # Step 3: Simulate SCORM interactions
        api_url = reverse("wagtail_lms:scorm_api", args=[attempt.id])

        # Initialize
        response = client.post(
            api_url,
            json.dumps({"method": "Initialize"}),
            content_type="application/json",
        )
        assert response.json()["result"] == "true"

        # Set progress
        response = client.post(
            api_url,
            json.dumps(
                {
                    "method": "SetValue",
                    "parameters": ["cmi.core.lesson_location", "page3"],
                }
            ),
            content_type="application/json",
        )
        assert response.json()["result"] == "true"

        # Set score
        response = client.post(
            api_url,
            json.dumps(
                {
                    "method": "SetValue",
                    "parameters": ["cmi.core.score.raw", "95"],
                }
            ),
            content_type="application/json",
        )
        assert response.json()["result"] == "true"

        # Complete course
        response = client.post(
            api_url,
            json.dumps(
                {
                    "method": "SetValue",
                    "parameters": ["cmi.core.lesson_status", "completed"],
                }
            ),
            content_type="application/json",
        )
        assert response.json()["result"] == "true"

        # Commit data
        response = client.post(
            api_url,
            json.dumps({"method": "Commit"}),
            content_type="application/json",
        )
        assert response.json()["result"] == "true"

        # Terminate
        response = client.post(
            api_url,
            json.dumps({"method": "Terminate"}),
            content_type="application/json",
        )
        assert response.json()["result"] == "true"

        # Step 4: Verify completion
        attempt.refresh_from_db()
        assert attempt.completion_status == "completed"
        assert attempt.score_raw == 95.0
        assert attempt.location == "page3"

        # Verify SCORMData was created
        assert SCORMData.objects.filter(attempt=attempt).count() > 0

    def test_suspend_and_resume(self, client, user, course_page, scorm_package):
        """Test suspending and resuming course progress."""
        client.force_login(user)

        # Start course
        player_url = reverse("wagtail_lms:scorm_player", args=[course_page.id])
        client.get(player_url)

        attempt = SCORMAttempt.objects.get(user=user, scorm_package=scorm_package)
        api_url = reverse("wagtail_lms:scorm_api", args=[attempt.id])

        # Set suspend data
        client.post(
            api_url,
            json.dumps(
                {
                    "method": "SetValue",
                    "parameters": ["cmi.suspend_data", "bookmark:page5|score:50"],
                }
            ),
            content_type="application/json",
        )

        # Set location
        client.post(
            api_url,
            json.dumps(
                {
                    "method": "SetValue",
                    "parameters": ["cmi.core.lesson_location", "page5"],
                }
            ),
            content_type="application/json",
        )

        # Verify data is saved
        attempt.refresh_from_db()
        assert attempt.suspend_data == "bookmark:page5|score:50"
        assert attempt.location == "page5"

        # Simulate returning to course (new session)
        # Get values
        response = client.post(
            api_url,
            json.dumps(
                {
                    "method": "GetValue",
                    "parameters": ["cmi.suspend_data"],
                }
            ),
            content_type="application/json",
        )
        assert response.json()["result"] == "bookmark:page5|score:50"

        response = client.post(
            api_url,
            json.dumps(
                {
                    "method": "GetValue",
                    "parameters": ["cmi.core.lesson_location"],
                }
            ),
            content_type="application/json",
        )
        assert response.json()["result"] == "page5"

    def test_multiple_users_same_course(
        self, client, django_user_model, course_page, scorm_package
    ):
        """Test multiple users taking the same course independently."""
        # Create two users
        user1 = django_user_model.objects.create_user(
            username="student1", password="pass"
        )
        user2 = django_user_model.objects.create_user(
            username="student2", password="pass"
        )

        # User 1: Start and complete
        client.force_login(user1)
        player_url = reverse("wagtail_lms:scorm_player", args=[course_page.id])
        client.get(player_url)

        attempt1 = SCORMAttempt.objects.get(user=user1, scorm_package=scorm_package)
        api_url1 = reverse("wagtail_lms:scorm_api", args=[attempt1.id])

        client.post(
            api_url1,
            json.dumps(
                {
                    "method": "SetValue",
                    "parameters": ["cmi.core.lesson_status", "completed"],
                }
            ),
            content_type="application/json",
        )

        # User 2: Start but not complete
        client.force_login(user2)
        client.get(player_url)

        attempt2 = SCORMAttempt.objects.get(user=user2, scorm_package=scorm_package)
        api_url2 = reverse("wagtail_lms:scorm_api", args=[attempt2.id])

        client.post(
            api_url2,
            json.dumps(
                {
                    "method": "SetValue",
                    "parameters": ["cmi.core.lesson_status", "incomplete"],
                }
            ),
            content_type="application/json",
        )

        # Verify independent progress
        attempt1.refresh_from_db()
        attempt2.refresh_from_db()

        assert attempt1.completion_status == "completed"
        assert attempt2.completion_status == "incomplete"
        assert attempt1.id != attempt2.id

    def test_course_page_context_with_progress(
        self, client, user, course_page, scorm_package, rf
    ):
        """Test course page shows correct enrollment and progress info."""
        # Enroll and create progress
        enrollment = CourseEnrollment.objects.create(user=user, course=course_page)
        attempt = SCORMAttempt.objects.create(
            user=user,
            scorm_package=scorm_package,
            completion_status="incomplete",
            score_raw=75.0,
        )

        # Get page context
        request = rf.get("/")
        request.user = user
        context = course_page.get_context(request)

        assert context["enrollment"] == enrollment
        assert context["progress"] == attempt
        assert context["progress"].score_raw == 75.0


@pytest.mark.django_db
class TestConcurrentSCORMOperations:
    """Test handling of concurrent SCORM API operations."""

    def test_rapid_set_value_calls(self, client, user, scorm_package):
        """Test rapid consecutive SetValue calls."""
        client.force_login(user)
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        api_url = reverse("wagtail_lms:scorm_api", args=[attempt.id])

        # Simulate rapid API calls
        responses = []
        for i in range(10):
            response = client.post(
                api_url,
                json.dumps(
                    {
                        "method": "SetValue",
                        "parameters": [f"cmi.interactions.{i}.id", f"q{i}"],
                    }
                ),
                content_type="application/json",
            )
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json()["result"] == "true"

        # Verify all data was saved
        assert SCORMData.objects.filter(attempt=attempt).count() == 10

    def test_update_same_key_multiple_times(self, client, user, scorm_package):
        """Test updating the same key multiple times."""
        client.force_login(user)
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        api_url = reverse("wagtail_lms:scorm_api", args=[attempt.id])

        # Update same key 5 times
        for status in ["incomplete", "browsed", "completed", "incomplete", "completed"]:
            response = client.post(
                api_url,
                json.dumps(
                    {
                        "method": "SetValue",
                        "parameters": ["cmi.core.lesson_status", status],
                    }
                ),
                content_type="application/json",
            )
            assert response.json()["result"] == "true"

        # Should only have one record for this key
        assert (
            SCORMData.objects.filter(
                attempt=attempt, key="cmi.core.lesson_status"
            ).count()
            == 1
        )

        # Final value should be "completed"
        data = SCORMData.objects.get(attempt=attempt, key="cmi.core.lesson_status")
        assert data.value == "completed"


@pytest.mark.django_db
class TestErrorHandling:
    """Test error handling in SCORM API."""

    def test_invalid_json(self, client, user, scorm_package):
        """Test handling of invalid JSON."""
        client.force_login(user)
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        api_url = reverse("wagtail_lms:scorm_api", args=[attempt.id])

        response = client.post(api_url, "invalid json", content_type="application/json")

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "false"
        assert data["errorCode"] == "201"

    def test_missing_parameters(self, client, user, scorm_package):
        """Test SetValue with missing parameters."""
        client.force_login(user)
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        api_url = reverse("wagtail_lms:scorm_api", args=[attempt.id])

        response = client.post(
            api_url,
            json.dumps({"method": "SetValue", "parameters": ["only_key"]}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "false"
        assert data["errorCode"] == "201"

    def test_get_request_to_api(self, client, user, scorm_package):
        """Test GET request to SCORM API (should only accept POST)."""
        client.force_login(user)
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        api_url = reverse("wagtail_lms:scorm_api", args=[attempt.id])

        response = client.get(api_url)

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "false"
        assert data["errorCode"] == "201"
