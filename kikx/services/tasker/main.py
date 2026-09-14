import asyncio
import logging

from typing import Any

from fastapi import Depends, Query, Request

from lib.service import create_service

from .models import (
  CreateTaskModel,
  QuickRunModel,
  TaskInputModel,
)
from .tasks import Tasks


logger = logging.getLogger(__name__)

srv = create_service(__file__, "Tasker service")


# ---------------------- Tasker
class Tasker:
  def __init__(self) -> None:
    # app_id: Tasks
    self._active: dict[str, Tasks] = {}

  def create_app_tasker(self, app) -> Tasks:
    if app.id in self._active:
      return self._active[app.id]

    tasks = Tasks(app)
    self._active[app.id] = tasks

    return tasks

  def get(self, app_id: str) -> Tasks | None:
    return self._active.get(app_id)

  # ---------------------- Lifecycle
  async def on_app_close(self, app_id: str) -> None:
    tasks = self._active.get(app_id)

    if tasks is None:
      return

    await tasks.on_close()
    self._active.pop(app_id, None)

  async def on_shutdown(self) -> None:
    await asyncio.gather(
      *(tasks.on_close() for tasks in self._active.values()),
      return_exceptions=True,
    )

    self._active.clear()


tasker = Tasker()


# ---------------------- Utils
def get_app(request: Request):
  _, app = srv.get_client_app(request)

  if not app.config.has_service("tasker"):
    srv.exception(403, "Service 'tasker' not found in config")

  return app


def get_tasks(request: Request) -> Tasks:
  app = get_app(request)

  tasks = tasker.get(app.id)

  if tasks is None:
    srv.exception(404, "App tasks not found")

  return tasks


# ---------------------- Lifecycle
@srv.on("startup")
def startup(core):
  core.events.add_event("app:close", tasker.on_app_close)


@srv.on("shutdown")
async def shutdown(core: Any) -> None:
  await tasker.on_shutdown()


# ---------------------- Routes
@srv.router.get("/init")
def create_tasker(app=Depends(get_app)):
  try:
    tasker.create_app_tasker(app)
    return srv.ok("Tasker initialized")
  except Exception as e:
    srv.exception(500, e)


@srv.router.post("/quick")
async def quick_run(
  payload: QuickRunModel,
  tasks=Depends(get_tasks),
):
  try:
    return await tasks.quick_run(
      payload.cmd,
      timeout=payload.timeout,
      can_sudo=payload.can_sudo,
      input_args=payload.input_args,
    )
  except Exception as e:
    srv.exception(500, e)


@srv.router.post("/create")
async def create_task(
  payload: CreateTaskModel,
  tasks=Depends(get_tasks),
):
  try:
    return await tasks.create_task(
      payload.cmd,
      can_sudo=payload.can_sudo,
      output_mode=payload.output_mode,
    )
  except Exception as e:
    srv.exception(500, e)


@srv.router.get("/run")
async def run_task(
  task_id: str = Query(...),
  handler_id: str = Query(...),
  tasks=Depends(get_tasks),
):
  try:
    return await tasks.run_task(task_id, handler_id)
  except Exception as e:
    srv.exception(500, e)


@srv.router.get("/kill")
async def kill_task(
  task_id: str = Query(...),
  remove: str = Query(...),
  tasks=Depends(get_tasks),
):
  try:
    return await tasks.kill(task_id, remove)
  except Exception as e:
    srv.exception(500, e)


@srv.router.post("/send")
async def send_task_input(
  payload: TaskInputModel,
  tasks=Depends(get_tasks),
):
  try:
    return await tasks.send_input(
      payload.task_id,
      payload.input_text,
    )
  except Exception as e:
    srv.exception(500, e)


@srv.router.get("/info")
def get_task_info(
  task_id: str = Query(...),
  tasks=Depends(get_tasks),
):
  try:
    return tasks.get_task_info(task_id)
  except Exception as e:
    srv.exception(500, e)


@srv.router.get("/output")
def get_task_output(
  task_id: str = Query(...),
  tasks=Depends(get_tasks),
):
  try:
    return tasks.get_task_output(task_id)
  except Exception as e:
    srv.exception(500, e)


@srv.router.get("/clear")
def clear_task_output(
  task_id: str = Query(...),
  tasks=Depends(get_tasks),
):
  try:
    tasks.clear_task_output(task_id)
    return srv.ok()
  except Exception as e:
    srv.exception(500, e)