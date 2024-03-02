from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import ClassVar, Annotated


class TaskError(Exception):
    task_id: int
    reason_code: Annotated[str, 'Program-friendly code of failure reason']
    description: Annotated[str, 'User-friendly description of failure']

    _default_task_id: ClassVar[ContextVar[int]] = ContextVar('_task_id')

    def __init__(self, reason_code: str, *, task_id: int | None = None, description: str = ''):
        """Initialize task error.

        Task id value is loaded from context if not specified in arguments of the function call.
        """
        try:
            self.task_id = task_id if task_id is not None else self._default_task_id.get()
        except LookupError:
            raise ValueError(
                'Can`t guess task id. The value has not been specified directly and context is empty too.',
            )
        self.reason_code = reason_code
        self.description = description
        super().__init__(
            f'Error on task {self.task_id} processing with '
            f'reason_code={self.reason_code!r} and description: {self.description or "empty"}',
        )

    @classmethod
    @contextmanager
    def set_default_task_id(cls, task_id: int):
        """Configure context to use specified task id value as an default one."""
        var_token: Token = cls._default_task_id.set(task_id)
        try:
            yield
        finally:
            cls._default_task_id.reset(var_token)

    @classmethod
    @contextmanager
    def convert_exceptions(cls, reason_code: str, *exception_types, task_id: int | None = None, description: str = ''):
        """Convert unhandled exceptions to TaskError if the original exception matches specified `exception_types`.

        Check the type of occured exception is a subtype of any `exception_types` specified.
        Task id value is loaded from context if not specified in arguments of the function call.
        """
        exception_types = exception_types or (Exception,)
        try:
            yield
        except Exception as exc:
            if any(isinstance(exc, exc_type) for exc_type in exception_types):
                raise cls(task_id=task_id, reason_code=reason_code, description=description) from exc
            else:
                raise
