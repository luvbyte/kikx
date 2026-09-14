from manager.main import manager


def main():
  import uvicorn
  
  uvicorn.run(manager, port=8012)


if __name__ == "__main__":
  main()
