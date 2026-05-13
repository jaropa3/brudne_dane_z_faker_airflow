import logging

import pytest

from src.step import step


def test_returns_value_unchanged():
    @step("add")
    def add(a, b):
        return a + b

    assert add(2, 3) == 5


def test_preserves_function_name():
    @step()
    def my_func():
        return None

    assert my_func.__name__ == "my_func"


def test_logs_start_and_ok(caplog):
    @step("ok_step")
    def fn():
        return 42

    with caplog.at_level(logging.INFO, logger="src.step"):
        fn()

    messages = [r.message for r in caplog.records]
    assert "step.start" in messages
    assert "step.ok" in messages


def test_logs_fail_and_reraises(caplog):
    @step("bad_step")
    def boom():
        raise ValueError("bum")

    with caplog.at_level(logging.INFO, logger="src.step"):
        with pytest.raises(ValueError, match="bum"):
            boom()

    fail = [r for r in caplog.records if r.message == "step.fail"]
    assert len(fail) == 1
    assert fail[0].levelno == logging.ERROR
    assert fail[0].exc_info is not None
