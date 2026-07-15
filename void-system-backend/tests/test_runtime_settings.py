"""Tests for injectable runtime settings and application-level authentication isolation."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app
from core.runtime_settings import RuntimeSettings


class RuntimeSettingsTests(unittest.TestCase):
    def test_from_environment_parses_runtime_values_without_mutating_process_state(self) -> None:
        settings = RuntimeSettings.from_environment(
            {
                "ENVIRONMENT": "production",
                "SECRET_KEY": "x" * 32,
                "PORT": "9100",
                "DEBUG": "false",
                "CORS_ORIGINS": "https://app.example, https://admin.example ",
                "DATABASE_URL": "sqlite:///runtime.db",
            },
            base_dir=Path("C:/runtime-root"),
        )

        self.assertEqual(settings.PORT, 9100)
        self.assertFalse(settings.DEBUG)
        self.assertEqual(settings.CORS_ORIGINS, ["https://app.example", "https://admin.example"])
        self.assertEqual(settings.get_database_path(), str(Path("C:/runtime-root") / "runtime.db"))
        settings.validate_runtime()

    def test_apps_with_different_settings_do_not_accept_each_others_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "settings.db"
            alpha_settings = RuntimeSettings(
                SECRET_KEY="a" * 32,
                CORS_ORIGINS=["https://alpha.example"],
            )
            alpha_app = create_app(
                ApplicationOptions(
                    database_path=str(database_path),
                    enable_ai_routes=False,
                    enable_langserve_routes=False,
                    bootstrap_admin=False,
                    settings=alpha_settings,
                )
            )
            with TestClient(alpha_app) as alpha:
                registered = alpha.post(
                    "/api/auth/register",
                    json={
                        "email": "settings@example.com",
                        "username": "settings-user",
                        "password": "secure-password-2026",
                    },
                )
                self.assertEqual(registered.status_code, 200)
                login = alpha.post(
                    "/api/auth/login",
                    json={"identifier": "settings@example.com", "password": "secure-password-2026"},
                )
                self.assertEqual(login.status_code, 200)
                alpha_token = login.json()["data"]["access_token"]
                cors = alpha.options(
                    "/api/health",
                    headers={
                        "Origin": "https://alpha.example",
                        "Access-Control-Request-Method": "GET",
                    },
                )
                self.assertEqual(cors.headers["access-control-allow-origin"], "https://alpha.example")

            beta_settings = RuntimeSettings(SECRET_KEY="b" * 32)
            beta_app = create_app(
                ApplicationOptions(
                    database_path=str(database_path),
                    enable_ai_routes=False,
                    enable_langserve_routes=False,
                    bootstrap_admin=False,
                    settings=beta_settings,
                )
            )
            with TestClient(beta_app) as beta:
                rejected = beta.get(
                    "/api/user/profile",
                    headers={"Authorization": f"Bearer {alpha_token}"},
                )

            self.assertEqual(rejected.status_code, 401)
            self.assertEqual(rejected.json()["error_code"], "INVALID_CREDENTIALS")


if __name__ == "__main__":
    unittest.main()
