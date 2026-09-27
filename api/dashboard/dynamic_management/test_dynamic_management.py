import uuid
from datetime import timedelta
import jwt
from django.conf import settings
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from db.organization import Country, State, Zone, District
from db.user import User, Role, DynamicRole, DynamicUser
from utils.types import RoleType


class BaseDynamicManagementTestCase(TransactionTestCase):
    UNMANAGED_MODELS = [
        User,
        Country,
        State,
        Zone,
        District,
        Role,
        DynamicRole,
        DynamicUser,
    ]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._created_models = []
        try:
            with connection.schema_editor() as editor:
                for model in cls.UNMANAGED_MODELS:
                    editor.create_model(model)
                    cls._created_models.append(model)
        except Exception:
            cls._cleanup_tables()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            cls._cleanup_tables()
        finally:
            super().tearDownClass()

    @classmethod
    def _cleanup_tables(cls):
        if hasattr(cls, "_created_models") and cls._created_models:
            with connection.schema_editor() as editor:
                for model in reversed(cls._created_models):
                    try:
                        editor.delete_model(model)
                    except Exception:
                        pass
            cls._created_models = []

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.admin_user = User.objects.create(
            id=str(uuid.uuid4()),
            full_name="Admin User",
            email="admin@example.com",
            muid="admin@mulearn",
            created_at=timezone.now(),
        )

        payload = {
            "id": self.admin_user.id,
            "expiry": (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S%z"),
            "roles": [RoleType.ADMIN.value],
            "muid": self.admin_user.muid
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def tearDown(self):
        DynamicUser.objects.all().delete()
        DynamicRole.objects.all().delete()
        Role.objects.all().delete()
        User.objects.all().delete()
        super().tearDown()


class TestDynamicRolePaginationSorting(BaseDynamicManagementTestCase):
    def setUp(self):
        super().setUp()

        self.role_admin = Role.objects.create(
            id=str(uuid.uuid4()),
            title="Admin Role",
            created_at=timezone.now(),
            created_by=self.admin_user,
            updated_at=timezone.now(),
            updated_by=self.admin_user,
        )
        self.role_user = Role.objects.create(
            id=str(uuid.uuid4()),
            title="User Role",
            created_at=timezone.now(),
            created_by=self.admin_user,
            updated_at=timezone.now(),
            updated_by=self.admin_user,
        )

        # Create dynamic roles across multiple types with duplicate minimum role_titles
        # Types C, A, D, B all share minimum role "Admin Role"
        # Type E has minimum role "User Role"
        types_and_roles = [
            ("TypeC", self.role_admin),
            ("TypeA", self.role_admin),
            ("TypeD", self.role_admin),
            ("TypeB", self.role_admin),
            ("TypeE", self.role_user),
        ]

        for t_name, role in types_and_roles:
            DynamicRole.objects.create(
                id=str(uuid.uuid4()),
                type=t_name,
                role=role,
                created_by=self.admin_user,
                updated_by=self.admin_user,
            )

    def test_sort_by_role_ascending_pagination_deterministic(self):
        res_page1 = self.client.get("/api/v1/dashboard/dynamic-management/dynamic-role/?sortBy=role&perPage=2&pageIndex=1")
        self.assertEqual(res_page1.status_code, 200)
        types_p1 = [item["type"] for item in res_page1.json()["response"]["data"]]

        res_page2 = self.client.get("/api/v1/dashboard/dynamic-management/dynamic-role/?sortBy=role&perPage=2&pageIndex=2")
        self.assertEqual(res_page2.status_code, 200)
        types_p2 = [item["type"] for item in res_page2.json()["response"]["data"]]

        res_page3 = self.client.get("/api/v1/dashboard/dynamic-management/dynamic-role/?sortBy=role&perPage=2&pageIndex=3")
        self.assertEqual(res_page3.status_code, 200)
        types_p3 = [item["type"] for item in res_page3.json()["response"]["data"]]

        self.assertEqual(types_p1, ["TypeA", "TypeB"])
        self.assertEqual(types_p2, ["TypeC", "TypeD"])
        self.assertEqual(types_p3, ["TypeE"])

        all_returned = types_p1 + types_p2 + types_p3
        self.assertEqual(len(all_returned), len(set(all_returned)))
        self.assertEqual(set(all_returned), {"TypeA", "TypeB", "TypeC", "TypeD", "TypeE"})

    def test_sort_by_role_descending_pagination_deterministic(self):
        res_page1 = self.client.get("/api/v1/dashboard/dynamic-management/dynamic-role/?sortBy=-role&perPage=2&pageIndex=1")
        self.assertEqual(res_page1.status_code, 200)
        types_p1 = [item["type"] for item in res_page1.json()["response"]["data"]]

        res_page2 = self.client.get("/api/v1/dashboard/dynamic-management/dynamic-role/?sortBy=-role&perPage=2&pageIndex=2")
        self.assertEqual(res_page2.status_code, 200)
        types_p2 = [item["type"] for item in res_page2.json()["response"]["data"]]

        res_page3 = self.client.get("/api/v1/dashboard/dynamic-management/dynamic-role/?sortBy=-role&perPage=2&pageIndex=3")
        self.assertEqual(res_page3.status_code, 200)
        types_p3 = [item["type"] for item in res_page3.json()["response"]["data"]]

        self.assertEqual(types_p1, ["TypeE", "TypeD"])
        self.assertEqual(types_p2, ["TypeC", "TypeB"])
        self.assertEqual(types_p3, ["TypeA"])

        all_returned = types_p1 + types_p2 + types_p3
        self.assertEqual(len(all_returned), len(set(all_returned)))
        self.assertEqual(set(all_returned), {"TypeA", "TypeB", "TypeC", "TypeD", "TypeE"})


class TestDynamicUserPaginationSorting(BaseDynamicManagementTestCase):
    def setUp(self):
        super().setUp()

        self.user_a = User.objects.create(
            id=str(uuid.uuid4()),
            full_name="Alice Alpha",
            email="alice@example.com",
            muid="alice@mulearn",
            created_at=timezone.now(),
        )
        self.user_z = User.objects.create(
            id=str(uuid.uuid4()),
            full_name="Zack Zeta",
            email="zack@example.com",
            muid="zack@mulearn",
            created_at=timezone.now(),
        )

        # Types C, A, D, B all share minimum user name "Alice Alpha"
        # Type E has minimum user name "Zack Zeta"
        types_and_users = [
            ("TypeC", self.user_a),
            ("TypeA", self.user_a),
            ("TypeD", self.user_a),
            ("TypeB", self.user_a),
            ("TypeE", self.user_z),
        ]

        for t_name, u in types_and_users:
            DynamicUser.objects.create(
                id=str(uuid.uuid4()),
                type=t_name,
                user=u,
                created_by=self.admin_user,
                updated_by=self.admin_user,
            )

    def test_sort_by_user_ascending_pagination_deterministic(self):
        res_page1 = self.client.get("/api/v1/dashboard/dynamic-management/dynamic-user/?sortBy=user&perPage=2&pageIndex=1")
        self.assertEqual(res_page1.status_code, 200)
        types_p1 = [item["type"] for item in res_page1.json()["response"]["data"]]

        res_page2 = self.client.get("/api/v1/dashboard/dynamic-management/dynamic-user/?sortBy=user&perPage=2&pageIndex=2")
        self.assertEqual(res_page2.status_code, 200)
        types_p2 = [item["type"] for item in res_page2.json()["response"]["data"]]

        res_page3 = self.client.get("/api/v1/dashboard/dynamic-management/dynamic-user/?sortBy=user&perPage=2&pageIndex=3")
        self.assertEqual(res_page3.status_code, 200)
        types_p3 = [item["type"] for item in res_page3.json()["response"]["data"]]

        self.assertEqual(types_p1, ["TypeA", "TypeB"])
        self.assertEqual(types_p2, ["TypeC", "TypeD"])
        self.assertEqual(types_p3, ["TypeE"])

        all_returned = types_p1 + types_p2 + types_p3
        self.assertEqual(len(all_returned), len(set(all_returned)))
        self.assertEqual(set(all_returned), {"TypeA", "TypeB", "TypeC", "TypeD", "TypeE"})

    def test_sort_by_user_descending_pagination_deterministic(self):
        res_page1 = self.client.get("/api/v1/dashboard/dynamic-management/dynamic-user/?sortBy=-user&perPage=2&pageIndex=1")
        self.assertEqual(res_page1.status_code, 200)
        types_p1 = [item["type"] for item in res_page1.json()["response"]["data"]]

        res_page2 = self.client.get("/api/v1/dashboard/dynamic-management/dynamic-user/?sortBy=-user&perPage=2&pageIndex=2")
        self.assertEqual(res_page2.status_code, 200)
        types_p2 = [item["type"] for item in res_page2.json()["response"]["data"]]

        res_page3 = self.client.get("/api/v1/dashboard/dynamic-management/dynamic-user/?sortBy=-user&perPage=2&pageIndex=3")
        self.assertEqual(res_page3.status_code, 200)
        types_p3 = [item["type"] for item in res_page3.json()["response"]["data"]]

        self.assertEqual(types_p1, ["TypeE", "TypeD"])
        self.assertEqual(types_p2, ["TypeC", "TypeB"])
        self.assertEqual(types_p3, ["TypeA"])

        all_returned = types_p1 + types_p2 + types_p3
        self.assertEqual(len(all_returned), len(set(all_returned)))
        self.assertEqual(set(all_returned), {"TypeA", "TypeB", "TypeC", "TypeD", "TypeE"})
