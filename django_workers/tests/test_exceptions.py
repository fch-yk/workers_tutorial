import pytest

from ..exceptions import TaskError


def test_exception_message_payload():
    try:
        raise TaskError(
            reason_code='unknown_error',
            task_id=999,
            description='Has extra description',
        )
    except TaskError as exc:
        exc_text = str(exc)
        assert 'unknown_error' in exc_text
        assert '999' in exc_text
        assert 'Has extra description' in exc_text


def test_default_task_id():
    with pytest.raises(ValueError, match='task id'):
        TaskError(reason_code='without_task_id')

    with TaskError.set_default_task_id(999):
        TaskError(reason_code='without_task_id')


def test_wrap_all_unhandled_exceptions():
    with pytest.raises(TaskError) as excinfo:
        with TaskError.set_default_task_id(999):
            with TaskError.convert_exceptions('strange_error', description='Has extra description'):
                raise KeyError

    assert 'strange_error' in str(excinfo.value)
    assert '999' in str(excinfo.value)
    assert 'Has extra description' in str(excinfo.value)


def test_wrap_specific_exception():
    with pytest.raises(KeyError):
        with TaskError.set_default_task_id(999):
            with TaskError.convert_exceptions('strange_error', ValueError):
                raise KeyError

    with pytest.raises(TaskError):
        with TaskError.set_default_task_id(999):
            with TaskError.convert_exceptions('strange_error', KeyError):
                raise KeyError
