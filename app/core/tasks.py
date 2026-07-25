"""Background task interface for Mizan.

Future background workers (notification scheduling, cleanup, email, maintenance,
Islamic calendar refresh) should consume this interface.

Do not implement workers here. Only prepare the abstraction.
"""

from typing import Any, Callable, Coroutine


class Task:
    def __init__(self, name: str, func: Callable[..., Any]):
        self.name = name
        self.func = func

    def delay(self, *args, **kwargs) -> Coroutine[Any, Any, Any]:
        raise NotImplementedError


class TaskRegistry:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def register(self, name: str, func: Callable[..., Any]) -> Task:
        task = Task(name, func)
        self._tasks[name] = task
        return task

    def get(self, name: str) -> Task | None:
        return self._tasks.get(name)


task_registry = TaskRegistry()
