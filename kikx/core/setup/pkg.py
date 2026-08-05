import httpx
import zipfile
import tempfile
import aiofiles
import shutil

from pathlib import Path
from urllib.parse import urlparse

from lib.hash import hash_file



GITHUB_API = "https://api.github.com/repos"

TIMEOUT = httpx.Timeout(
  connect=30,
  read=60,
  write=60,
  pool=60,
)

HEADERS = {
  "Accept": "application/vnd.github+json",
  "User-Agent": (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
  ),
}

# -------------- Parsing
def parse_github_repo(repo_url: str) -> tuple[str, str]:
  parsed = urlparse(repo_url)

  if parsed.netloc not in ("github.com", "www.github.com"):
    raise Exception("Invalid GitHub URL")

  parts = parsed.path.strip("/").split("/")
  if len(parts) < 2:
    raise Exception("Invalid GitHub repository URL")

  return parts[0], parts[1]

# -------------- Unziping
def extract_package(uri: str | Path, temp_dir: Path) -> Path:
  path = Path(uri).resolve()

  if not path.exists():
    raise FileNotFoundError("Package not found")
  
  if path.suffix != ".kikx":
    raise ValueError("Only .kikx packages are supported")
  
  if not temp_dir.exists():
    raise RuntimeError("Failed to create temp directory")

  with zipfile.ZipFile(path, "r") as zip_ref:
    for member in zip_ref.namelist():
      member_path = temp_dir / member

      # Prevent zip-slip
      if not member_path.resolve().is_relative_to(temp_dir.resolve()):
        raise ValueError("Unsafe file detected inside package")

    zip_ref.extractall(temp_dir)

  extracted_dirs = [p for p in temp_dir.iterdir() if p.is_dir()]

  if len(extracted_dirs) != 1:
    raise ValueError("Invalid structure")

  return extracted_dirs[0]

# -------------- Fetching
async def fetch_release_package(
  raw_temp_dir: Path,
  owner: str,
  repo: str,
  tag: str | None
) -> tuple[dict, Path]:
  url = (
    f"{GITHUB_API}/{owner}/{repo}/releases/tags/{tag}"
    if tag
    else f"{GITHUB_API}/{owner}/{repo}/releases/latest"
  )

  async with httpx.AsyncClient(
    timeout=TIMEOUT,
    follow_redirects=True,
  ) as client:

    resp = await client.get(url, headers=HEADERS)

    if resp.status_code == 403:
      raise Exception("GitHub API rate limit exceeded")

    if resp.status_code == 404:
      raise Exception("Release not found")

    resp.raise_for_status()

    release = resp.json()
    release_tag = release.get("tag_name")

    if tag and release_tag != tag:
      raise Exception(f"Requested tag {tag}, but got {release_tag}")

    ui_asset = next(
      (a for a in release.get("assets", [])
       if a["name"].endswith(".kikx")),
      None
    )

    if not ui_asset:
      raise Exception("No .kikx asset found in release")

    download_url = ui_asset["browser_download_url"]
    raw_temp = raw_temp_dir / ui_asset["name"]

    async with client.stream("GET", download_url) as r:
      r.raise_for_status()

      async with aiofiles.open(raw_temp, "wb") as f:
        async for chunk in r.aiter_bytes(chunk_size=1024 * 1024):
          await f.write(chunk)

    return release, raw_temp

async def fetch_from_github(
  repo_url: str,
  name: str,
  func,
  tag: str | None = None,
) -> None:
  owner, repo = parse_github_repo(repo_url)

  raw_temp_dir = Path(tempfile.mkdtemp())
  extract_temp_dir = Path(tempfile.mkdtemp())

  try:
    release, raw_temp = await fetch_release_package(raw_temp_dir, owner, repo, tag)

    file_hash = hash_file(raw_temp)

    source = {
      "url": repo_url,
      "owner": owner,
      "repo": repo,
      "tag": release.get("tag_name"),
      "hash": file_hash,
    }

    # Extracted path
    func(extract_package(raw_temp, extract_temp_dir), source)
  finally:
    shutil.rmtree(raw_temp_dir, ignore_errors=True)
    shutil.rmtree(extract_temp_dir, ignore_errors=True)

# -------------- Validations
def is_outdated(current: str, required: str) -> bool:
  def parse(version: str):
    version = version.removeprefix("v")
    return tuple(map(int, version.split(".")))

  return parse(current) < parse(required)
