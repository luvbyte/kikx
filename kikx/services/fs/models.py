from typing import Literal

from pydantic import BaseModel


# ---------------------- File Write
class FileWriteRequest(BaseModel):
  filename: str
  content: str
  ensure_dir: bool = False
  mode: Literal["write", "append"] = "write"


# ---------------------- Create Directory
class DirectoryCreateRequest(BaseModel):
  dirname: str


# ---------------------- Copy / Move
class CopyMoveRequest(BaseModel):
  source: str | list[str]
  dest: str


# ---------------------- Copy File
class CopyFileRequest(BaseModel):
  source: str
  dest: str
  override: bool = False


# ---------------------- Rename
class RenameRequest(BaseModel):
  source: str
  new_name: str


# ---------------------- Delete Paths
class DeleteListModel(BaseModel):
  paths: list[str]


# ---------------------- Create File
class FileCreateRequest(BaseModel):
  filename: str


# ---------------------- Batch
class BatchOperation(BaseModel):
  action: str
  path: str | None = None
  source: str | None = None
  dest: str | None = None
  new_name: str | None = None


# ---------------------- Expose
class ExposeRouteModel(BaseModel):
  path: str
  expires: float | None = None