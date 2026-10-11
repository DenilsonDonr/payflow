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
