from modules.cuteadb import cdb
from pathlib import Path

def start():
  cdb.main(Path(__file__).resolve().parent / "_scripts")
