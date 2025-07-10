# will remove
# base error
class Error(Exception):
  def __init__(self, desc):
    super().__init__(desc)

# sends error to task
class TaskError(Error):
  pass

# sends error to app in clinet
class AppError(Error):
  pass

# sends error message to client
class ClientError(Error):
  pass

# raise error
def raise_error(desc, error_type = Error):
  raise error_type(desc)


