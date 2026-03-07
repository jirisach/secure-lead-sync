from sls.core.errors import ApiServerError
from sls.core.retry import run_with_retry


class FakeOperation:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.calls < 3:
            raise ApiServerError("temporary failure")
        return "ok"


def test_run_with_retry_eventually_succeeds():
    op = FakeOperation()

    result = run_with_retry(
        op,
        run_id="test_run",
        operation_name="fake_operation",
        max_attempts=4,
        base_delay=0.01,
        max_delay=0.02,
    )

    assert result == "ok"
    assert op.calls == 3