from core.models.ui import UIConfigModel


class ClientUI:
  def __init__(self, name: str, config: UIConfigModel) -> None:
    self.name: str = name
    self.config: UIConfigModel = config