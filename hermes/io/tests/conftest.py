import pytest
from prefect.logging import disable_run_logger
from prefect.testing.utilities import prefect_test_harness


@pytest.fixture(scope="class", autouse=True)
def prefect():
    with prefect_test_harness():
        with disable_run_logger():
            yield
