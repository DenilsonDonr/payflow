import pytest

from app.shared.outbox.infrastructure.relay_worker import RelaySettings

ENV_NAMES = [
    "OUTBOX_BATCH_SIZE",
    "OUTBOX_POLL_INTERVAL_SECONDS",
    "OUTBOX_MAX_ATTEMPTS",
    "OUTBOX_BACKOFF_BASE_SECONDS",
    "OUTBOX_BACKOFF_CAP_SECONDS",
    "OUTBOX_PUBLISH_TIMEOUT_SECONDS",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


class TestRelaySettingsDefaults:
    def test_uses_the_documented_defaults(self):
        settings = RelaySettings.from_env()

        assert settings.batch_size == 20
        assert settings.poll_interval_seconds == 1.0
        assert settings.max_attempts == 10
        assert settings.backoff_base_seconds == 1.0
        assert settings.backoff_cap_seconds == 300.0
        assert settings.publish_timeout_seconds == 2.0

    def test_is_frozen(self):
        settings = RelaySettings.from_env()

        with pytest.raises(AttributeError):
            settings.batch_size = 5  # type: ignore[misc]


class TestRelaySettingsOverrides:
    def test_every_value_can_be_overridden_from_the_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("OUTBOX_BATCH_SIZE", "7")
        monkeypatch.setenv("OUTBOX_POLL_INTERVAL_SECONDS", "0.25")
        monkeypatch.setenv("OUTBOX_MAX_ATTEMPTS", "3")
        monkeypatch.setenv("OUTBOX_BACKOFF_BASE_SECONDS", "2")
        monkeypatch.setenv("OUTBOX_BACKOFF_CAP_SECONDS", "60")
        monkeypatch.setenv("OUTBOX_PUBLISH_TIMEOUT_SECONDS", "1.5")

        settings = RelaySettings.from_env()

        assert settings == RelaySettings(
            batch_size=7,
            poll_interval_seconds=0.25,
            max_attempts=3,
            backoff_base_seconds=2.0,
            backoff_cap_seconds=60.0,
            publish_timeout_seconds=1.5,
        )

    def test_base_equal_to_cap_is_accepted(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("OUTBOX_BACKOFF_BASE_SECONDS", "5")
        monkeypatch.setenv("OUTBOX_BACKOFF_CAP_SECONDS", "5")

        assert RelaySettings.from_env().backoff_cap_seconds == 5.0


class TestRelaySettingsValidation:
    @pytest.mark.parametrize(
        ("name", "value"),
        [
            ("OUTBOX_BATCH_SIZE", "abc"),
            ("OUTBOX_BATCH_SIZE", "1.5"),
            ("OUTBOX_BATCH_SIZE", "0"),
            ("OUTBOX_BATCH_SIZE", "-3"),
            ("OUTBOX_MAX_ATTEMPTS", "abc"),
            ("OUTBOX_MAX_ATTEMPTS", "0"),
            ("OUTBOX_MAX_ATTEMPTS", "-1"),
            ("OUTBOX_POLL_INTERVAL_SECONDS", "abc"),
            ("OUTBOX_POLL_INTERVAL_SECONDS", "0"),
            ("OUTBOX_POLL_INTERVAL_SECONDS", "-1"),
            ("OUTBOX_POLL_INTERVAL_SECONDS", "nan"),
            ("OUTBOX_POLL_INTERVAL_SECONDS", "inf"),
            ("OUTBOX_PUBLISH_TIMEOUT_SECONDS", "abc"),
            ("OUTBOX_PUBLISH_TIMEOUT_SECONDS", "0"),
            ("OUTBOX_PUBLISH_TIMEOUT_SECONDS", "-2"),
            ("OUTBOX_PUBLISH_TIMEOUT_SECONDS", "nan"),
            ("OUTBOX_PUBLISH_TIMEOUT_SECONDS", "inf"),
            ("OUTBOX_BACKOFF_BASE_SECONDS", "abc"),
            ("OUTBOX_BACKOFF_BASE_SECONDS", "0"),
            ("OUTBOX_BACKOFF_BASE_SECONDS", "-1"),
            ("OUTBOX_BACKOFF_BASE_SECONDS", "nan"),
            ("OUTBOX_BACKOFF_BASE_SECONDS", "inf"),
            ("OUTBOX_BACKOFF_CAP_SECONDS", "abc"),
            ("OUTBOX_BACKOFF_CAP_SECONDS", "nan"),
            ("OUTBOX_BACKOFF_CAP_SECONDS", "inf"),
            ("OUTBOX_BACKOFF_CAP_SECONDS", "0.5"),  # below the default base of 1
        ],
    )
    def test_rejects_an_invalid_value_at_load(
        self, monkeypatch: pytest.MonkeyPatch, name: str, value: str
    ):
        monkeypatch.setenv(name, value)

        with pytest.raises(ValueError, match=f"(?i){name.removeprefix('OUTBOX_')}"):
            RelaySettings.from_env()

    def test_rejects_a_base_above_the_cap(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("OUTBOX_BACKOFF_BASE_SECONDS", "10")
        monkeypatch.setenv("OUTBOX_BACKOFF_CAP_SECONDS", "5")

        with pytest.raises(ValueError, match="backoff"):
            RelaySettings.from_env()

    def test_direct_construction_is_validated_too(self):
        with pytest.raises(ValueError, match="batch_size"):
            RelaySettings(
                batch_size=0,
                poll_interval_seconds=1.0,
                max_attempts=1,
                backoff_base_seconds=1.0,
                backoff_cap_seconds=2.0,
                publish_timeout_seconds=1.0,
            )
