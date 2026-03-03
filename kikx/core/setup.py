import json
import httpx
import shutil
import tempfile
from pathlib import Path

from lib.hash import hash_file

from core.kpm import GITHUB_API, AppInstaller, parse_github_repo, resolve_app_package


PRE_INSTALL_APPS = {
  # name: (repo, tag)
  "com.kikx.appstore": ("https://github.com/luvbyte/kikx-appstore-app", "0.0.3"),
  "com.kikx.sessions": ("https://github.com/luvbyte/kikx-sessions-app", "0.1.0"),
  "com.kikx.files": ("https://github.com/luvbyte/kikx-files-app", "0.1.1"),
}

async def pre_check_apps(core):
  apps = core.user.get_installed_apps()

  install_list = {
    name: data for name, data in PRE_INSTALL_APPS.items()
    if name not in apps
  }

  if len(install_list) <= 0:
    return

  core.scr.print_divider("INSTALLING APPS")

  for name, (url, tag) in install_list.items():
    try:
      core.scr.print(f"[-] App ({name}) not found. Installing...")
      await install_from_github(core, url, name, tag)
    except Exception as e:
      core.scr.print(f"[x] Error installing app ({name}): {e}")

# Optimize move this to kpm
async def install_from_github(
  core,
  repo_url: str,
  name: str,
  tag: str | None = None
):
  owner, repo = parse_github_repo(repo_url)

  if tag:
    url = f"{GITHUB_API}/{owner}/{repo}/releases/tags/{tag}"
  else:
    url = f"{GITHUB_API}/{owner}/{repo}/releases/latest"

  headers = {
    "Accept": "application/vnd.github+json",
    "User-Agent": (
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/122.0.0.0 Safari/537.36"
    ),
  }

  raw_temp_dir = Path(tempfile.mkdtemp())
  extract_temp_dir = Path(tempfile.mkdtemp())
  raw_temp = None

  try:
    async with httpx.AsyncClient(
      follow_redirects=True,
      timeout=httpx.Timeout(30.0)
    ) as client:

      resp = await client.get(url, headers=headers)

      if resp.status_code == 403:
        raise Exception("GitHub API rate limit exceeded")

      if resp.status_code == 404:
        raise Exception(f"Release not found ({tag or 'latest'})")

      if resp.status_code != 200:
        raise Exception(f"Release error ({resp.status_code})")

      release = resp.json()
      release_tag = release.get("tag_name")

      if tag and release_tag != tag:
        raise Exception(f"Requested tag {tag}, but got {release_tag}")

      kikx_asset = next(
        (a for a in release.get("assets", [])
         if a["name"].endswith(".kikx")),
        None
      )

      if not kikx_asset:
        raise Exception("No .kikx asset found in release")

      download_url = kikx_asset["browser_download_url"]
      raw_temp = raw_temp_dir / kikx_asset["name"]

      async with client.stream("GET", download_url) as r:
        r.raise_for_status()
        with open(raw_temp, "wb") as f:
          async for chunk in r.aiter_bytes():
            f.write(chunk)

    file_hash = hash_file(raw_temp)

    extracted_path = resolve_app_package(raw_temp, extract_temp_dir)

    source = {
      "url": repo_url,
      "owner": owner,
      "repo": repo,
      "tag": release_tag,
      "hash": file_hash,
    }

    installer = AppInstaller(core, extracted_path)

    installer.install(source)

    core.scr.print(f"[+] App installed: {name} ({release_tag})")

  finally:
    shutil.rmtree(raw_temp_dir, ignore_errors=True)
    shutil.rmtree(extract_temp_dir, ignore_errors=True)
