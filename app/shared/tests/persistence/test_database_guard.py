import pytest

from app.shared.persistence.database_guard import require_test_database


class TestRequireTestDatabase:
    def test_accepts_a_name_ending_in_test(self):
        require_test_database("payflow_db_test")

    @pytest.mark.parametrize("name", ["payflow_db_dev", "payflow", "", "testing", "test_payflow"])
    def test_rejects_a_name_that_does_not_end_in_test(self, name: str):
        with pytest.raises(RuntimeError):
            require_test_database(name)

    def test_message_names_the_database_and_the_fix(self):
        with pytest.raises(RuntimeError) as error:
            require_test_database("payflow_db_dev")

        message = str(error.value)
        assert "payflow_db_dev" in message
        assert ".env.test" in message
        assert "Refusing to run the test suite" in message

    def test_message_points_to_env_test_without_repeating_its_values(self):
        with pytest.raises(RuntimeError) as error:
            require_test_database("payflow_db_dev")

        message = str(error.value)
        assert ".env.test" in message
        # .env.test, compose and the README own these values; repeating them here goes stale.
        assert "payflow_db_test" not in message
        assert "5433" not in message
        assert "exported" not in message
