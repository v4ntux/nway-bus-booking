"""Deployment configuration checks that do not require a running database."""

import os
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import PropertyMock, patch

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from app.core.config import Settings, get_settings


class DatabaseConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.addCleanup(get_settings.cache_clear)
        get_settings.cache_clear()

    def test_postgres_schemes_and_pasted_quotes(self):
        for scheme in ("postgres", "postgresql", "postgresql+asyncpg"):
            for quote in ("", "'", '"'):
                with self.subTest(scheme=scheme, quote=quote):
                    settings = Settings(
                        _env_file=None,
                        DATABASE_URL=f"  {quote}{scheme}://user:password@postgres.railway.internal:5432/app{quote}  ",
                    )
                    settings.ensure_database_configured()
                    self.assertEqual(make_url(settings.database_url).drivername, "postgresql+asyncpg")

    def test_rejects_malformed_urls_without_leaking_credentials(self):
        for url in ("", "secret-password", "DATABASE_URL=postgresql://u:secret-password@host/db", "postgresql://", "postgresql://host", "sqlite:///db", "postgresql://u:secret-password@host:invalid/db"):
            with self.subTest(url=url):
                settings = Settings(_env_file=None, DATABASE_URL=url)
                with self.assertRaises(RuntimeError) as error:
                    settings.ensure_database_configured()
                self.assertIn("complete PostgreSQL connection URL", str(error.exception))
                self.assertNotIn("secret-password", str(error.exception))
                self.assertIsNone(error.exception.__context__)

    def test_unresolved_reference_is_rejected(self):
        settings = Settings(_env_file=None, DATABASE_URL="${{Postgres.DATABASE_URL}}")
        with self.assertRaisesRegex(RuntimeError, "unresolved Railway reference"):
            settings.ensure_database_configured()

    def test_private_override_is_identified_when_invalid(self):
        settings = Settings(
            _env_file=None,
            DATABASE_URL="postgresql://user:password@host/db",
            DATABASE_PRIVATE_URL="bad-value",
        )
        with self.assertRaisesRegex(RuntimeError, "DATABASE_PRIVATE_URL must"):
            settings.ensure_database_configured()

    def test_railway_rejects_loopback_hosts(self):
        os.environ["RAILWAY_SERVICE_NAME"] = "backend"
        for host in ("localhost", "127.0.0.1", "[::1]"):
            with self.subTest(host=host):
                settings = Settings(_env_file=None, DATABASE_URL=f"postgresql://u:p@{host}/db")
                with self.assertRaisesRegex(RuntimeError, "points to localhost"):
                    settings.ensure_database_configured()

    def test_local_development_still_works(self):
        Settings(_env_file=None).ensure_database_configured()

    def test_private_url_takes_precedence_and_uses_private_network(self):
        settings = Settings(
            _env_file=None,
            DATABASE_PRIVATE_URL="postgresql://u:p@postgres.railway.internal/db",
        )
        settings.ensure_database_configured()
        self.assertEqual(make_url(settings.database_url).host, "postgres.railway.internal")
        self.assertEqual(settings.database_connect_args, {})

    def test_alembic_accepts_percent_encoded_password(self):
        os.environ["DATABASE_URL"] = "postgresql://user:p%40ss%25word@postgres.railway.internal/db"
        os.environ["DATABASE_PRIVATE_URL"] = ""
        root = Path(__file__).resolve().parents[1]
        output = StringIO()
        config = Config(str(root / "alembic.ini"), output_buffer=output)
        config.set_main_option("script_location", str(root / "alembic"))
        command.upgrade(config, "head", sql=True)
        self.assertIn("CREATE TABLE", output.getvalue())
        self.assertIn("p%40ss%25word", config.get_main_option("sqlalchemy.url"))

    def test_alembic_uses_the_apps_connection_options(self):
        os.environ["DATABASE_URL"] = "postgresql://user:password@host/db"
        os.environ["DATABASE_PRIVATE_URL"] = ""
        root = Path(__file__).resolve().parents[1]
        config = Config(str(root / "alembic.ini"))
        config.set_main_option("script_location", str(root / "alembic"))
        options = {"ssl": object()}
        # Stop before connecting to a database; inspect migration engine options.
        with (
            patch.object(Settings, "database_connect_args", new_callable=PropertyMock, return_value=options),
            patch("sqlalchemy.ext.asyncio.async_engine_from_config", side_effect=RuntimeError("test engine")) as engine,
        ):
            with self.assertRaisesRegex(RuntimeError, "test engine"):
                command.upgrade(config, "head")
        self.assertIs(engine.call_args.kwargs["connect_args"], options)


if __name__ == "__main__":
    unittest.main()
