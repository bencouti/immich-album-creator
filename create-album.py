import os
import requests
import argparse

# Configuration constants (replace with your data)
IMMICH_HOST = "<IP and port of Immich server>" # eg. 192.168.1.10:30041
LIBRARY_LOCAL_ROOT = os.path.abspath("<Absolute path of your library root folder from the script point of view>") # eg. /srv/dockermount/photos/Albums
LIBRARY_IMMICH_ROOT = "<Absolute path of your library root folder from immich point of view>" # eg. /Albums
API_KEY = "<Your API key>" # eg. LVonX8XvAI85EST9Ryh3fPpoUliQkSHjeRDs9Hx9I

# Authentication headers
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

def map_local_to_immich_path(local_path: str):
    """Map a local path to its Immich equivalent path."""
    local_path = os.path.abspath(local_path)
    if not local_path.startswith(LIBRARY_LOCAL_ROOT):
        raise ValueError(f"Local path '{local_path}' does not start with LIBRARY_LOCAL_ROOT '{LIBRARY_LOCAL_ROOT}'")
    relative_path = os.path.relpath(local_path, LIBRARY_LOCAL_ROOT)
    immich_path = os.path.join(LIBRARY_IMMICH_ROOT, relative_path)
    immich_path = immich_path.replace(os.sep, "/")  # Ensure forward slashes for Immich API
    return immich_path

def get_folder_assets(abs_folder_path: str):
    """Retrieve asset IDs from a folder using its mapped Immich path."""
    immich_path = map_local_to_immich_path(abs_folder_path)
    url = f"http://{IMMICH_HOST}/api/view/folder"
    params = {"path": immich_path}

    print(f"[DEBUG] Calling {url} with path: {immich_path}")
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        asset_ids = [item["id"] for item in data]
        return asset_ids
    except requests.RequestException as e:
        print(f"[ERROR] Failed to get assets for '{abs_folder_path}' (Immich path: '{immich_path}'): {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[ERROR] Response content: {e.response.text}")
        return []

def album_exists(album_name: str):
    """Check if an album with the given name already exists."""
    url = f"http://{IMMICH_HOST}/api/albums"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        albums = response.json()
        return any(album.get("albumName") == album_name for album in albums)
    except requests.RequestException as e:
        print(f"[ERROR] Failed to check existing albums: {e}")
        return False

def create_album(album_name: str, asset_ids: list, dry_run: bool):
    """Create an album if it does not already exist."""
    if album_exists(album_name):
        print(f"[SKIP] Album '{album_name}' already exists.")
        return

    if dry_run:
        print(f"[DRY-RUN] Simulated creation of album '{album_name}' with {len(asset_ids)} assets.")
        return

    url = f"http://{IMMICH_HOST}/api/albums"
    payload = {
        "albumName": album_name,
        "assetIds": asset_ids,
        "description": ""
    }

    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        print(f"[OK] Album created: {album_name} ({len(asset_ids)} assets)")
    except requests.RequestException as e:
        print(f"[ERROR] Failed to create album '{album_name}': {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[ERROR] Response content: {e.response.text}")

def main(dry_run: bool):
    subdirs = [entry for entry in os.scandir(LIBRARY_LOCAL_ROOT) if entry.is_dir()]
    total = len(subdirs)

    for idx, entry in enumerate(subdirs, start=1):
        abs_path = entry.path
        folder_name = entry.name
        print(f"\n[{idx}/{total}] Processing folder: {abs_path}")

        try:
            asset_ids = get_folder_assets(abs_path)
            if not asset_ids:
                print(f"[SKIP] No assets found in '{abs_path}'")
                continue
            create_album(folder_name, asset_ids, dry_run)
        except ValueError as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Immich albums from local subdirectories.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without creating albums")
    args = parser.parse_args()

    main(dry_run=args.dry_run)

