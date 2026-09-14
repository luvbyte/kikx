from typing import Any

# remove forever
class KVStorage:
  def __init__(self) -> None:
    self.__storage: dict[str, Any] = {}

  def get(self, key: str, fallback: Any | None = None) -> Any | None:
    return self.__storage.get(key, fallback)

  def set(self, key: str, value: Any) -> None:
    self.__storage[key] = value

  def has(self, key: str) -> bool:
    return key in self.__storage

  def get_or_set(self, key: str, value: Any) -> Any:
    if not self.has(key):
      self.set(key, value)

    return self.get(key)

  def pop(self, key: str, raise_error: bool = True) -> Any | None:
    return self.__storage.pop(key) if raise_error else self.__storage.pop(key, None)

  def reset(self) -> None:
    self.__storage = {}