from typing import Literal

from pydantic import BaseModel, Field


# ---------------------- Quick Run
class QuickRunModel(BaseModel):
  cmd: str
  can_sudo: bool = False
  timeout: float | None = None
  input_args: list[str] = Field(default_factory=list)


# ---------------------- Create Task
class CreateTaskModel(BaseModel):
  cmd: str
  can_sudo: bool = False
  output_mode: Literal["send", "save", "*"] = "send"


# ---------------------- Task Input
class TaskInputModel(BaseModel):
  task_id: str
  input_text: str


# ---------------------- Task Command
class TaskCommandModel(BaseModel):
  task_id: str
  event: str
  payload: dict