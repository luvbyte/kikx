import getpass


def get_username() -> str:
  return getpass.getuser()