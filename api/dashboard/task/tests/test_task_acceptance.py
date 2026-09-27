import uuid
from datetime import timedelta
import jwt
from django.conf import settings
from django.db import connection
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from db.organization import Country, State, Zone, District, Organization
from db.company import Company, CompanyTaskTemplate
from db.events import Event
from db.user import User, Role, UserRoleLink, UserDomains, MentorApplication, UserMentor, UserEndgoals
from db.task import (
    Channel,
    InterestGroup,
    Level,
    TaskType,
    TaskList,
    TaskAcceptance,
    KarmaActivityLog,
    MucoinActivityLog,
    VoucherLog,
    Category,
)
from db.skill import Skill, TaskSkillLink
from utils.types import RoleType
from utils.utils import DateTimeUtils


class TaskAcceptanceTestCase(TransactionTestCase):
    UNMANAGED_MODELS = [
        Country,
        State,
        Zone,
        District,
        User,
        Role,
        UserRoleLink,
        UserDomains,
        MentorApplication,
        UserMentor,
        UserEndgoals,
        Channel,
        InterestGroup,
        Level,
        TaskType,
        Organization,
        Company,
        CompanyTaskTemplate,
        Skill,
        TaskSkillLink,
        Category,
        Event,
        TaskList,
        KarmaActivityLog,
        MucoinActivityLog,
        VoucherLog,
        TaskAcceptance,
    ]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._created_models = []
        with connection.schema_editor() as editor:
            for model in cls.UNMANAGED_MODELS:
                try:
                    editor.create_model(model)
                    cls._created_models.append(model)
                except Exception:
                    pass

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
            for model in reversed(cls._created_models):
                try:
                    editor.delete_model(model)
                except Exception:
                    pass
        super().tearDownClass()

    def get_client(self, user=None, roles=None):
        client = APIClient()
        if user:
            if roles is None:
                roles = [RoleType.STUDENT.value]
            expiry = (DateTimeUtils.get_current_utc_time() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S%z")
            payload = {
                "id": user.id,
                "expiry": expiry,
                "roles": roles,
                "muid": user.muid,
            }
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def setUp(self):
        super().setUp()
        uid1 = str(uuid.uuid4())
        uid2 = str(uuid.uuid4())
        uid3 = str(uuid.uuid4())

        self.learner_user = User.objects.create(
            id=uid1, muid=f"MU-L1-{uid1[:6]}", full_name="Learner One", email=f"l1-{uid1[:6]}@test.com"
        )
        self.other_learner_user = User.objects.create(
            id=uid2, muid=f"MU-L2-{uid2[:6]}", full_name="Learner Two", email=f"l2-{uid2[:6]}@test.com"
        )
        self.non_learner_user = User.objects.create(
            id=uid3, muid=f"MU-NL-{uid3[:6]}", full_name="Admin User", email=f"nl-{uid3[:6]}@test.com"
        )
        self.task_type = TaskType.objects.create(
            id=str(uuid.uuid4()), title=f"Coding-{uid1[:6]}", created_by=self.learner_user, updated_by=self.learner_user
        )

        self.approved_task = TaskList.objects.create(
            id=str(uuid.uuid4()),
            title="Approved Problem Statement",
            hashtag=f"#ps-approved-{uid1[:6]}",
            description="A great problem statement",
            karma=100,
            type=self.task_type,
            approval_status="approved",
            active=True,
            is_deleted=False,
            created_by=self.learner_user,
            updated_by=self.learner_user,
        )

        self.pending_task = TaskList.objects.create(
            id=str(uuid.uuid4()),
            title="Pending Problem Statement",
            hashtag=f"#ps-pending-{uid1[:6]}",
            description="A pending problem statement",
            karma=100,
            type=self.task_type,
            approval_status="pending",
            active=False,
            is_deleted=False,
            created_by=self.learner_user,
            updated_by=self.learner_user,
        )

        self.rejected_task = TaskList.objects.create(
            id=str(uuid.uuid4()),
            title="Rejected Problem Statement",
            hashtag=f"#ps-rejected-{uid1[:6]}",
            description="A rejected problem statement",
            karma=100,
            type=self.task_type,
            approval_status="rejected",
            active=False,
            is_deleted=False,
            created_by=self.learner_user,
            updated_by=self.learner_user,
        )

        self.inactive_task = TaskList.objects.create(
            id=str(uuid.uuid4()),
            title="Inactive Problem Statement",
            hashtag=f"#ps-inactive-{uid1[:6]}",
            description="An inactive problem statement",
            karma=100,
            type=self.task_type,
            approval_status="approved",
            active=False,
            is_deleted=False,
            created_by=self.learner_user,
            updated_by=self.learner_user,
        )

    def tearDown(self):
        TaskAcceptance.objects.all().delete()
        TaskList.objects.all().delete()
        TaskType.objects.all().delete()
        super().tearDown()

    # 1. Learner can accept an approved active task
    def test_learner_can_accept_approved_active_task(self):
        client = self.get_client(user=self.learner_user, roles=[RoleType.STUDENT.value])
        resp = client.post(f"/api/v1/dashboard/task/{self.approved_task.id}/accept/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["statusCode"], 200)
        self.assertTrue(TaskAcceptance.objects.filter(user=self.learner_user, task=self.approved_task).exists())

    # 2. Learner cannot accept pending task
    def test_learner_cannot_accept_pending_task(self):
        client = self.get_client(user=self.learner_user, roles=[RoleType.STUDENT.value])
        resp = client.post(f"/api/v1/dashboard/task/{self.pending_task.id}/accept/")
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(TaskAcceptance.objects.filter(user=self.learner_user, task=self.pending_task).exists())

    # 3. Learner cannot accept rejected task
    def test_learner_cannot_accept_rejected_task(self):
        client = self.get_client(user=self.learner_user, roles=[RoleType.STUDENT.value])
        resp = client.post(f"/api/v1/dashboard/task/{self.rejected_task.id}/accept/")
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(TaskAcceptance.objects.filter(user=self.learner_user, task=self.rejected_task).exists())

    # 4. Learner cannot accept inactive task
    def test_learner_cannot_accept_inactive_task(self):
        client = self.get_client(user=self.learner_user, roles=[RoleType.STUDENT.value])
        resp = client.post(f"/api/v1/dashboard/task/{self.inactive_task.id}/accept/")
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(TaskAcceptance.objects.filter(user=self.learner_user, task=self.inactive_task).exists())

    # 5. Duplicate acceptance is prevented
    def test_duplicate_acceptance_is_prevented(self):
        client = self.get_client(user=self.learner_user, roles=[RoleType.STUDENT.value])
        first_resp = client.post(f"/api/v1/dashboard/task/{self.approved_task.id}/accept/")
        self.assertEqual(first_resp.status_code, 200)

        second_resp = client.post(f"/api/v1/dashboard/task/{self.approved_task.id}/accept/")
        self.assertEqual(second_resp.status_code, 409)
        self.assertEqual(second_resp.json()["message"]["error_code"], "ALREADY_ACCEPTED")

    # 6. Learner only sees their own accepted tasks
    def test_learner_only_sees_their_own_accepted_tasks(self):
        TaskAcceptance.objects.create(id=str(uuid.uuid4()), user=self.learner_user, task=self.approved_task)
        TaskAcceptance.objects.create(id=str(uuid.uuid4()), user=self.other_learner_user, task=self.approved_task)

        client = self.get_client(user=self.learner_user, roles=[RoleType.STUDENT.value])
        resp = client.get("/api/v1/dashboard/task/accepted/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["response"]["data"]
        user_ids = [item["user_id"] for item in data]
        self.assertEqual(len(data), 1)
        self.assertIn(self.learner_user.id, user_ids)
        self.assertNotIn(self.other_learner_user.id, user_ids)

    # 7. Unauthenticated user cannot accept
    def test_unauthenticated_user_cannot_accept(self):
        client = self.get_client(user=None)
        resp = client.post(f"/api/v1/dashboard/task/{self.approved_task.id}/accept/")
        self.assertIn(resp.status_code, [401, 1000, 403, 200])
        if resp.status_code == 200:
            self.assertIn("statusCode", resp.json())
            self.assertNotEqual(resp.json()["statusCode"], 200)

    # 8. Non-learner role cannot accept
    def test_non_learner_role_cannot_accept(self):
        client = self.get_client(user=self.non_learner_user, roles=[RoleType.FELLOW.value])
        resp = client.post(f"/api/v1/dashboard/task/{self.approved_task.id}/accept/")
        self.assertIn("do not have the required role", str(resp.json().get("message", {})))

    # 9. Public listing does not expose pending or rejected tasks
    def test_public_listing_does_not_expose_pending_or_rejected_tasks(self):
        client = APIClient()
        resp = client.get("/api/v1/dashboard/task/list/")
        self.assertEqual(resp.status_code, 200)

        sections = resp.json()["response"]
        start_journey_ids = [t["id"] for t in sections.get("start_journey", [])]
        become_expert_ids = [t["id"] for t in sections.get("become_expert", [])]
        events_ids = [t["id"] for t in sections.get("events", [])]

        all_public_ids = set(start_journey_ids + become_expert_ids + events_ids)

        self.assertIn(self.approved_task.id, all_public_ids)
        self.assertNotIn(self.pending_task.id, all_public_ids)
        self.assertNotIn(self.rejected_task.id, all_public_ids)
