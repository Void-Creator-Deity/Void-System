"""HTTP integration checks for the Reward Marketplace purchase contract."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app


class RewardMarketplaceHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "marketplace.db"
        self.client = TestClient(
            create_app(
                ApplicationOptions(
                    database_path=str(database_path),
                    enable_ai_routes=False,
                    enable_langserve_routes=False,
                    bootstrap_admin=False,
                )
            )
        )
        self.client.__enter__()
        registration = self.client.post(
            "/api/auth/register",
            json={
                "email": "buyer@example.com",
                "username": "buyer",
                "password": "secure-password-2026",
            },
        )
        self.assertEqual(registration.status_code, 200)
        self.user_id = registration.json()["data"]["user_id"]
        login = self.client.post(
            "/api/auth/login",
            json={"identifier": "buyer@example.com", "password": "secure-password-2026"},
        )
        self.assertEqual(login.status_code, 200)
        self.headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.temp_dir.cleanup()

    def test_purchase_rejects_unknown_items_and_insufficient_balance(self) -> None:
        unknown = self.client.post(
            "/api/shop/purchase/not-a-real-item",
            headers=self.headers,
            json={"quantity": 1},
        )
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.json()["error_code"], "ITEM_NOT_FOUND")

        insufficient = self.client.post(
            "/api/shop/purchase/item_energy_small",
            headers=self.headers,
            json={"quantity": 1},
        )
        self.assertEqual(insufficient.status_code, 400)
        self.assertEqual(insufficient.json()["error_code"], "INSUFFICIENT_BALANCE")

    def test_purchase_updates_the_profile_balance_and_inventory(self) -> None:
        self.client.app.state.database.add_coins(self.user_id, 100, source="test")

        purchased = self.client.post(
            "/api/shop/purchase/item_energy_small",
            headers=self.headers,
            json={"quantity": 1},
        )
        self.assertEqual(purchased.status_code, 200)
        body = purchased.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["total_price"], 50)
        self.assertEqual(body["data"]["remaining_balance"], 50)

        profile = self.client.get("/api/user/profile", headers=self.headers)
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()["data"]["balance"], 50)
        self.assertEqual(profile.json()["data"]["resources"]["shop_item_energy_small"], 1)


if __name__ == "__main__":
    unittest.main()
