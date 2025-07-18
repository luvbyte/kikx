# base error
class Error(Exception):
  def __init__(self, desc):
    super().__init__(desc)

# raise error
def raise_error(desc, error_type = Error):
  raise error_type(desc)


