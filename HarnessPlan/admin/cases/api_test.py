#!/usr/bin/env python3
"""
Admin API E2E Test Script

Run against a running API server:
    python api_test.py --base-url http://localhost:8000 --admin-user admin --admin-pass Malin123456
"""

import argparse
import sys

import requests


class AdminAPITest:
    def __init__(self, base_url: str, admin_user: str, admin_pass: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.admin_user = admin_user
        self.admin_pass = admin_pass
        self.company_id = None
        self.user_id = None
        self.library_id = None
        self.tag_group_id = None
        self.tag_id = None
        self.custom_group_id = None

    def login(self) -> bool:
        """Login as admin"""
        resp = self.session.post(
            f"{self.base_url}/auth/login",
            json={"username": self.admin_user, "password": self.admin_pass},
        )
        if resp.status_code == 200:
            print("✅ Login successful")
            return True
        print(f"❌ Login failed: {resp.status_code} {resp.text}")
        return False

    def test_companies(self) -> bool:
        """Test Company CRUD"""
        print("\n=== Testing Companies ===")

        # Create
        resp = self.session.post(
            f"{self.base_url}/admin/api/companies",
            json={
                "company_name": "Test Company",
                "monthly_video_quota": 100,
                "monthly_video_remaining": 100,
                "billing_cycle_start_date": "2026-04-01",
                "tts_enabled": True,
                "status": "active",
            },
        )
        if resp.status_code != 201:
            print(f"❌ Create company failed: {resp.status_code} {resp.text}")
            return False
        self.company_id = resp.json()["company_id"]
        print(f"✅ Company created: {self.company_id}")

        # List
        resp = self.session.get(f"{self.base_url}/admin/api/companies")
        if resp.status_code != 200:
            print(f"❌ List companies failed: {resp.status_code}")
            return False
        print(f"✅ Listed {len(resp.json())} companies")

        # Get
        resp = self.session.get(f"{self.base_url}/admin/api/companies/{self.company_id}")
        if resp.status_code != 200:
            print(f"❌ Get company failed: {resp.status_code}")
            return False
        print(f"✅ Got company: {resp.json()['company_name']}")

        # Update
        resp = self.session.put(
            f"{self.base_url}/admin/api/companies/{self.company_id}",
            json={"company_name": "Updated Company"},
        )
        if resp.status_code != 200:
            print(f"❌ Update company failed: {resp.status_code}")
            return False
        print("✅ Company updated")

        return True

    def test_users(self) -> bool:
        """Test User CRUD"""
        print("\n=== Testing Users ===")

        # Create
        resp = self.session.post(
            f"{self.base_url}/admin/api/users",
            json={
                "company_id": self.company_id,
                "login_account": "testuser",
                "password": "testpass123",
                "user_name": "Test User",
                "status": "active",
                "role": "user",
            },
        )
        if resp.status_code != 201:
            print(f"❌ Create user failed: {resp.status_code} {resp.text}")
            return False
        self.user_id = resp.json()["user_id"]
        print(f"✅ User created: {self.user_id}")

        # List
        resp = self.session.get(f"{self.base_url}/admin/api/users")
        if resp.status_code != 200:
            print(f"❌ List users failed: {resp.status_code}")
            return False
        print(f"✅ Listed {len(resp.json())} users")

        # Get
        resp = self.session.get(f"{self.base_url}/admin/api/users/{self.user_id}")
        if resp.status_code != 200:
            print(f"❌ Get user failed: {resp.status_code}")
            return False
        print(f"✅ Got user: {resp.json()['login_account']}")

        # Update
        resp = self.session.put(
            f"{self.base_url}/admin/api/users/{self.user_id}",
            json={"user_name": "Updated User"},
        )
        if resp.status_code != 200:
            print(f"❌ Update user failed: {resp.status_code}")
            return False
        print("✅ User updated")

        return True

    def test_libraries(self) -> bool:
        """Test AssetLibrary CRUD"""
        print("\n=== Testing Libraries ===")

        # Create
        resp = self.session.post(
            f"{self.base_url}/admin/api/libraries",
            json={
                "company_id": self.company_id,
                "library_name": "Test Library",
                "root_path": "/data/library1",
                "config_path": "/data/library1/config.json",
                "description": "Test library description",
            },
        )
        if resp.status_code != 201:
            print(f"❌ Create library failed: {resp.status_code} {resp.text}")
            return False
        self.library_id = resp.json()["asset_library_id"]
        print(f"✅ Library created: {self.library_id}")

        # List
        resp = self.session.get(f"{self.base_url}/admin/api/libraries")
        if resp.status_code != 200:
            print(f"❌ List libraries failed: {resp.status_code}")
            return False
        print(f"✅ Listed {len(resp.json())} libraries")

        # Import
        resp = self.session.post(f"{self.base_url}/admin/api/libraries/{self.library_id}/import")
        if resp.status_code != 200:
            print(f"❌ Import library failed: {resp.status_code}")
            return False
        print(f"✅ Library imported: {resp.json()['config_import_status']}")

        return True

    def test_tag_groups(self) -> bool:
        """Test TagGroup CRUD"""
        print("\n=== Testing Tag Groups ===")

        # Create
        resp = self.session.post(
            f"{self.base_url}/admin/api/tag-groups",
            json={
                "asset_library_id": self.library_id,
                "group_key": "customer_site",
                "group_name": "客户现场",
                "allow_multi_select": True,
                "allow_select_all": True,
            },
        )
        if resp.status_code != 201:
            print(f"❌ Create tag group failed: {resp.status_code} {resp.text}")
            return False
        self.tag_group_id = resp.json()["tag_group_id"]
        print(f"✅ Tag group created: {self.tag_group_id}")

        # List by library
        resp = self.session.get(f"{self.base_url}/admin/api/libraries/{self.library_id}/tag-groups")
        if resp.status_code != 200:
            print(f"❌ List tag groups failed: {resp.status_code}")
            return False
        print(f"✅ Listed {len(resp.json())} tag groups")

        return True

    def test_tags(self) -> bool:
        """Test Tag CRUD"""
        print("\n=== Testing Tags ===")

        # Create
        resp = self.session.post(
            f"{self.base_url}/admin/api/tags",
            json={
                "asset_library_id": self.library_id,
                "tag_group_id": self.tag_group_id,
                "tag_key": "guangzhou",
                "tag_name": "广州",
                "filter_condition": "path LIKE '%广州%'",
                "is_default_selected": False,
            },
        )
        if resp.status_code != 201:
            print(f"❌ Create tag failed: {resp.status_code} {resp.text}")
            return False
        self.tag_id = resp.json()["tag_id"]
        print(f"✅ Tag created: {self.tag_id}")

        # List by tag group
        resp = self.session.get(f"{self.base_url}/admin/api/tag-groups/{self.tag_group_id}/tags")
        if resp.status_code != 200:
            print(f"❌ List tags failed: {resp.status_code}")
            return False
        print(f"✅ Listed {len(resp.json())} tags")

        return True

    def test_custom_groups(self) -> bool:
        """Test CustomGroup CRUD"""
        print("\n=== Testing Custom Groups ===")

        # Create
        resp = self.session.post(
            f"{self.base_url}/admin/api/custom-groups",
            json={
                "company_id": self.company_id,
                "user_id": self.user_id,
                "asset_library_id": self.library_id,
                "group_name": "My Custom Group",
                "description": "Test custom group",
                "tag_ids": [self.tag_id],
            },
        )
        if resp.status_code != 201:
            print(f"❌ Create custom group failed: {resp.status_code} {resp.text}")
            return False
        self.custom_group_id = resp.json()["custom_tag_group_id"]
        print(f"✅ Custom group created: {self.custom_group_id}")

        # List
        resp = self.session.get(f"{self.base_url}/admin/api/custom-groups")
        if resp.status_code != 200:
            print(f"❌ List custom groups failed: {resp.status_code}")
            return False
        print(f"✅ Listed {len(resp.json())} custom groups")

        # Get
        resp = self.session.get(f"{self.base_url}/admin/api/custom-groups/{self.custom_group_id}")
        if resp.status_code != 200:
            print(f"❌ Get custom group failed: {resp.status_code}")
            return False
        print(f"✅ Got custom group with {len(resp.json()['tag_ids'])} tags")

        return True

    def cleanup(self) -> bool:
        """Clean up test data"""
        print("\n=== Cleanup ===")

        # Delete custom group
        if self.custom_group_id:
            resp = self.session.delete(f"{self.base_url}/admin/api/custom-groups/{self.custom_group_id}")
            print(f"{'✅' if resp.status_code == 204 else '❌'} Delete custom group")

        # Delete tag
        if self.tag_id:
            resp = self.session.delete(f"{self.base_url}/admin/api/tags/{self.tag_id}")
            print(f"{'✅' if resp.status_code == 204 else '❌'} Delete tag")

        # Delete tag group
        if self.tag_group_id:
            resp = self.session.delete(f"{self.base_url}/admin/api/tag-groups/{self.tag_group_id}")
            print(f"{'✅' if resp.status_code == 204 else '❌'} Delete tag group")

        # Delete library
        if self.library_id:
            resp = self.session.delete(f"{self.base_url}/admin/api/libraries/{self.library_id}")
            print(f"{'✅' if resp.status_code == 204 else '❌'} Delete library")

        # Delete user
        if self.user_id:
            resp = self.session.delete(f"{self.base_url}/admin/api/users/{self.user_id}")
            print(f"{'✅' if resp.status_code == 204 else '❌'} Delete user")

        # Delete company
        if self.company_id:
            resp = self.session.delete(f"{self.base_url}/admin/api/companies/{self.company_id}")
            print(f"{'✅' if resp.status_code == 204 else '❌'} Delete company")

        return True

    def run_all(self) -> bool:
        """Run all tests"""
        print("=" * 50)
        print("Admin API E2E Tests")
        print("=" * 50)

        if not self.login():
            return False

        tests = [
            self.test_companies,
            self.test_users,
            self.test_libraries,
            self.test_tag_groups,
            self.test_tags,
            self.test_custom_groups,
        ]

        for test in tests:
            if not test():
                print(f"\n❌ Test failed: {test.__name__}")
                self.cleanup()
                return False

        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)

        self.cleanup()
        return True


def main():
    parser = argparse.ArgumentParser(description="Admin API E2E Tests")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--admin-user", default="admin", help="Admin username")
    parser.add_argument("--admin-pass", default="Malin123456", help="Admin password")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip cleanup")

    args = parser.parse_args()

    tester = AdminAPITest(args.base_url, args.admin_user, args.admin_pass)
    success = tester.run_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
