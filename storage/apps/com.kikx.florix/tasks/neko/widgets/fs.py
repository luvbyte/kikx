import os
from pathlib import Path

from neko.ui import Div
from neko.app import JApp
from neko.lib.utils import clean

from neko import panel

from typing import List, Any

class FileSystem(JApp):
  def init(self, directory, multiple, accept="*", title=""):
    self.start_path = Path(os.environ.get("KIKX_HOME_PATH", ""))
    self.current_path = self.start_path

    self.directory = directory
    self.multiple = multiple
    self.selected = list()
    
    self.list_view = True
  
    self.close_flag = False
    
    title_head = "Open "
    if self.directory:
      title_head += "Directory"
    elif self.multiple:
      title_head += "Files"
    else:
      title_head += "File"

    self.frame = Div(f"""
      <div class="p-2 bg-gradient-to-b from-purple-500 to-blue-400 flex justify-between items-center">
        <div class="flex flex-col w-full">
          <div class="w-full flex justify-between items-center">
            <div class="text-lg">{title_head}</div>
            <div {self.on("close")}>
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="currentColor" d="M19 6.41L17.59 5L12 10.59L6.41 5L5 6.41L10.59 12L5 17.59L6.41 19L12 13.41L17.59 19L19 17.59L13.41 12z"/></svg>
            </div>
          </div>
          <div>{clean(title)}</div>
        </div>
      </div>
    """).add_class("absolute w-full h-full insert-0 flex flex-col bg-slate-800")
    
    self.files_div = Div().add_class("flex-1 flex flex-col overflow-hidden")
    self.frame.append(self.files_div)
    
    self.selected_class_style = ""

  def get_icon(self, path):
    if path.is_dir():
      return "/public/app/com.kikx.florix/icons/folder.png"
    else:
      return "/public/app/com.kikx.florix/icons/file.png"

  def display_path(self, path):
    self.current_path = Path(path)

    def get_div(file_path: Path):
      #if self.directory and not file_path.is_dir():
        #return ""
      cleaned_name = clean(file_path.name)
      return f"""
          <div 
            class="p-1 w-full flex gap-1 items-center {'bg-slate-600' if file_path in self.selected else ''}"
            {self.on("select", file_path)}
          >
            <img src="{self.get_icon(file_path)}" class="w-8 h-8" />
            <div class="text-sm">{cleaned_name}</div>
          </div>
        """ if self.list_view else f"""
          <div 
            class="w-14 h-14 flex flex-col items-center {"ring-2 ring-purple-500 rounded" if file_path in self.selected else ''}"
            {self.on("select", file_path)}
          >
            <img src="{self.get_icon(file_path)}" class="w-8 h-8" />
            <div class="text-sm mt-1 truncate w-full text-center">{cleaned_name}</div>
          </div>
        """

    cls_list = "flex flex-col flex-1" if self.list_view else "grid grid-cols-4 gap-1 p-2"
    
    select_button = f'<div {self.on("done")} class="p-2 bg-purple-800 text-center">SELECT</div>'

    self.files_div.replace(f"""
      { select_button if self.directory or (len(self.selected) > 0 and self.multiple) else ''}
      <div class="flex gap-1 p-2 px-2 shadow-2xl">
        <!-- home -->
        <div {self.on("home")} class="active:bg-purple-400/40 rounded">
          <svg xmlns="http://www.w3.org/2000/svg" width="25" height="25" fill="currentColor" class="bi bi-house" viewBox="0 0 16 16"><path d="M8.707 1.5a1 1 0 0 0-1.414 0L.646 8.146a.5.5 0 0 0 .708.708L2 8.207V13.5A1.5 1.5 0 0 0 3.5 15h9a1.5 1.5 0 0 0 1.5-1.5V8.207l.646.647a.5.5 0 0 0 .708-.708L13 5.793V2.5a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v1.293zM13 7.207V13.5a.5.5 0 0 1-.5.5h-9a.5.5 0 0 1-.5-.5V7.207l5-5z" /></svg>
        </div>
        <!-- go up -->
        <div {self.on("back")} class="active:bg-purple-400/40 rounded">
          <svg xmlns="http://www.w3.org/2000/svg" width="25" height="25" fill="currentColor" class="bi bi-arrow-up-circle" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M1 8a7 7 0 1 0 14 0A7 7 0 0 0 1 8m15 0A8 8 0 1 1 0 8a8 8 0 0 1 16 0m-7.5 3.5a.5.5 0 0 1-1 0V5.707L5.354 7.854a.5.5 0 1 1-.708-.708l3-3a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 5.707z" /></svg>
        </div>
        <input class="flex-1 text-sm bg-transparent rounded border px-2 overflow-hidden whitespace-nowrap [direction:rtl] [text-align:left]" value="{self.current_path}" />
        <div {self.on("toggle_view")} class="active:bg-purple-400/40 rounded">
          {'<svg width="25" height="25" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M3 18h6v-2H3zM3 6v2h18V6zm0 7h12v-2H3z"/></svg>' if self.list_view else '<svg width="25" height="25" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 6.75c0-1.768 0-2.652.55-3.2C4.097 3 4.981 3 6.75 3s2.652 0 3.2.55c.55.548.55 1.432.55 3.2s0 2.652-.55 3.2c-.548.55-1.432.55-3.2.55s-2.652 0-3.2-.55C3 9.403 3 8.519 3 6.75m0 10.507c0-1.768 0-2.652.55-3.2c.548-.55 1.432-.55 3.2-.55s2.652 0 3.2.55c.55.548.55 1.432.55 3.2s0 2.652-.55 3.2c-.548.55-1.432.55-3.2.55s-2.652 0-3.2-.55C3 19.91 3 19.026 3 17.258M13.5 6.75c0-1.768 0-2.652.55-3.2c.548-.55 1.432-.55 3.2-.55s2.652 0 3.2.55c.55.548.55 1.432.55 3.2s0 2.652-.55 3.2c-.548.55-1.432.55-3.2.55s-2.652 0-3.2-.55c-.55-.548-.55-1.432-.55-3.2m0 10.507c0-1.768 0-2.652.55-3.2c.548-.55 1.432-.55 3.2-.55s2.652 0 3.2.55c.55.548.55 1.432.55 3.2s0 2.652-.55 3.2c-.548.55-1.432.55-3.2.55s-2.652 0-3.2-.55c-.55-.548-.55-1.432-.55-3.2"/></svg>'}
        </div>
      </div>
      <div class="overflow-y-auto {cls_list}">
        {''.join([get_div(path / name) for name in os.listdir(path)])}
      </div>
    """)
  
  def on_select(self, file_path):
    path = Path(file_path)
    if path.is_dir():
      return self.display_path(path)
    elif self.multiple:
      try:
        self.selected.remove(path)
      except ValueError:
        self.selected.append(path)
    elif not self.directory:
      if path in self.selected:
        return True
      self.selected.clear()
      self.selected.append(path)

    self.display_path(self.current_path)

  def on_home(self):
    self.display_path(self.start_path)
  
  def on_back(self):
    self.display_path(self.current_path.parent)

  def on_toggle_view(self):
    self.list_view = not self.list_view
    self.display_path(self.current_path)
  
  def on_done(self):
    return True

  def on_close(self):
    self.close_flag = True
    return True

  def show(self) -> List[Path]:
    panel.append(self.frame)
    self.display_path(self.start_path)
    self.startloop()
    
    self.frame._js.jfunc("remove()")

    if self.close_flag:
      return None

    return [self.current_path] if self.directory else self.selected

class FSWrapper:
  def ask_file(self, title: str = "", accept="*") -> List[Path]:
    return FileSystem(False, False, accept, title=title).show()

  def ask_files(self, title: str = "", accept="*") -> List[Path]:
    return FileSystem(False, True, accept, title=title).show()

  def ask_directory(self, title: str = "", accept="*") -> List[Path]:
    return FileSystem(True, False, accept, title=title).show()
