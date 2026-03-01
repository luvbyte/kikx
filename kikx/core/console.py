import shutil

B1 = r"""
.-. .-')          .-. .-') ) (`-.      
\  ( OO )         \  ( OO ) ( OO ).    
,--. ,--.  ,-.-') ,--. ,--.(_/.  \_)-. 
|  .'   /  |  |OO)|  .'   / \  `.'  /  
|      /,  |  |  \|      /,  \     /\  
|     ' _) |  |(_/|     ' _)  \   \ |  
|  .   \  ,|  |_.'|  .   \   .'    \_) 
|  |\   \(_|  |   |  |\   \ /  .'.  \  
`--' '--'  `--'   `--' '--''--'   '--' """

class Console:
  def __init__(self, width=None):
    # Auto-detect terminal width if not provided
    self.width = width or shutil.get_terminal_size().columns

  def print_center(self, text):
    if not isinstance(text, str):
      text = str(text)

    lines = text.split("\n")
    for line in lines:
      print(line.center(self.width))
  
  def print_divider(self, text):
    self.print_center(f"\n[ ======== [ {text} ] ======== ]\n")

  def print_banner(self, version, author):
    self.print_center(B1)
    self.print_divider(f"ᥫ᭡ {author} - v{version}")

  def print(self, *text):
    print(*text)
