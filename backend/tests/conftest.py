import os
import pytest


@pytest.fixture(autouse=True)
def _recon_env_isolation():
    """Ensure per-test isolation of mutable RECON_* env vars that affect logging/metrics.

    Prevent leakage of sampling overrides or disable flags set by previous tests.
    Tests that need specific values simply set them after their fixtures run.
    """
    # Clear sampling globals/overrides
    for k in list(os.environ.keys()):
        if k.startswith("RECON_STRUCTURED_LOG_SAMPLE_RECON_"):
            os.environ.pop(k, None)
    for k in [
        "RECON_STRUCTURED_LOG_SAMPLE",
        "RECON_DISABLE_METRICS",
        "RECON_METRICS_DISABLED",
        "RECON_STRUCTURED_LOG_ASYNC",
    ]:
        os.environ.pop(k, None)
    yield
    # (No teardown restoration needed; tests set what they need explicitly.)
