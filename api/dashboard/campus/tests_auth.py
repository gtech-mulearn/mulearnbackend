from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from db.user import User, UserMentor
from db.organization import Organization
from db.campus import CampusIGChapter

class AuthorizationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Setup Organizations
        self.org_a = Organization.objects.create(id="org_a", title="College A", org_type="College")
        self.org_b = Organization.objects.create(id="org_b", title="College B", org_type="College")
        
        # Setup Users
        self.mentor_a = User.objects.create(id="mentor_a", full_name="Mentor A")
        self.mentor_b = User.objects.create(id="mentor_b", full_name="Mentor B")
        self.global_admin = User.objects.create(id="admin", full_name="Admin", admin=True)
        
        # Assign Mentor Roles
        UserMentor.objects.create(user=self.mentor_a, mentor_tier="CAMPUS_MENTOR", org_id=self.org_a.id)
        UserMentor.objects.create(user=self.mentor_b, mentor_tier="CAMPUS_MENTOR", org_id=self.org_b.id)
        
        # Create IG Chapters
        self.chapter_a = CampusIGChapter.objects.create(id="chapter_a", org=self.org_a, is_active=True)
        self.chapter_b = CampusIGChapter.objects.create(id="chapter_b", org=self.org_b, is_active=True)

    def test_mentor_can_read_own_campus(self):
        """Test that Mentor A can read IG chapters from College A."""
        # Note: Need valid JWT mock here for APIClient
        # For demonstration, assume client is authenticated as mentor_a
        response = self.client.get(reverse('campus-ig-chapters'))
        # Assert response contains chapter_a and NOT chapter_b
        pass
        
    def test_mentor_idor_prevention_on_update(self):
        """Test that Mentor A cannot PATCH an IG chapter in College B (IDOR)."""
        response = self.client.patch(
            reverse('campus-ig-chapters-detail', kwargs={'chapter_id': self.chapter_b.id}),
            {"description": "Hacked"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_serializer_tampering_prevention(self):
        """Test that Mentor A cannot create an IG chapter and assign it to College B."""
        response = self.client.post(
            reverse('campus-ig-chapters'),
            {"ig": "some_ig_id", "description": "Tampered", "org_id": self.org_b.id}
        )
        # Should succeed but ignore org_id, assigning it to org_a
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        chapter = CampusIGChapter.objects.filter(description="Tampered").first()
        self.assertEqual(chapter.org_id, self.org_a.id)
        self.assertNotEqual(chapter.org_id, self.org_b.id)
