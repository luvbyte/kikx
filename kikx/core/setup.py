import json
import httpx
import shutil
import tempfile
from pathlib import Path

from lib.hash import hash_file

from core.kpm import GITHUB_API, AppInstaller, parse_github_repo, resolve_app_package


PRE_INSTALL_APPS = {
  "com.kikx.appstore": "https://github.com/luvbyte/kikx-appstore-app",
  # "com.kikx.sessions": "https://github.com/luvbyte/kikx-sessions-app"
}

async def pre_check_apps(core):
  apps = core.user.get_installed_apps()

  install_list = {name: url for name, url in PRE_INSTALL_APPS.items() if name not in apps}

  if len(install_list) <= 0:
    return

  core.scr.print_divider("INSTALLING APPS")

  for name, url in install_list.items():
    try:
      core.scr.print(f"[-] App ({name}) not found. Installing...")
      await install_from_github(core, url, name)
    except Exception as e:
      core.scr.print(f"[x] Error installing app ({name}): {e}")

# Optimize move this to kpm
async def install_from_github(core, repo_url: str, name: str):
  owner, repo = parse_github_repo(repo_url)

  url = f"{GITHUB_API}/{owner}/{repo}/releases/latest"

  headers = {
    "Accept": "application/vnd.github+json",
    "User-Agent": (
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/122.0.0.0 Safari/537.36"
    ),
  }

  async with httpx.AsyncClient(follow_redirects=True) as client:
    resp = await client.get(url, headers=headers)
    if resp.status_code != 200:
      raise Exception(f"Release not found ({resp.status_code})")
    release = resp.json()

  kikx_asset = next(
    (a for a in release.get("assets", []) if a["name"].endswith(".kikx")),
    None
  )

  if not kikx_asset:
    raise Exception("No .kikx asset found in release")

  download_url = kikx_asset["browser_download_url"]

  raw_temp = Path(tempfile.mkdtemp()) / kikx_asset["name"]

  async with httpx.AsyncClient(follow_redirects=True) as client:
    async with client.stream("GET", download_url) as r:
      r.raise_for_status()
      with open(raw_temp, "wb") as f:
        async for chunk in r.aiter_bytes():
          f.write(chunk)

  temp_dir = Path(tempfile.mkdtemp())
  extracted_path = resolve_app_package(raw_temp, temp_dir)

  source = {
    "url": repo_url,
    "owner": owner,
    "repo": repo,
    "tag": release.get("tag_name"),
  }

  installer = AppInstaller(core, extracted_path)

  if not installer.is_compatible:
    raise Exception("App not compatible")

  installer.install(source)

  shutil.rmtree(temp_dir, ignore_errors=True)
  raw_temp.unlink(missing_ok=True)
  
  core.scr.print(f"[+] App installed: {name}")
