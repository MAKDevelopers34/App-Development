import requests
import re
import os
from urllib.parse import quote, urlparse
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

SUPPORTED_EXTENSIONS = [
    '.py', '.pyw',
    '.js', '.jsx', '.mjs', '.cjs',
    '.ts', '.tsx', '.mts', '.cts',
    '.java',
    '.cpp', '.cc', '.cxx', '.c++', '.hpp', '.hh', '.hxx', '.ipp',
    '.c', '.h',
]
MAX_GITHUB_FILES = 20
MAX_SOURCE_BYTES = 250 * 1024
MAX_GITHUB_FOLDERS = 200
SKIP_FOLDERS = {
    'node_modules', '.git', '.hg', '.svn', '__pycache__', '.pytest_cache',
    '.mypy_cache', 'venv', '.venv', 'env', 'dist', 'build', '.next',
    'coverage', 'target', 'out', '.idea', '.vscode',
}

def parse_github_url(url):
    """
    Converts GitHub URL to owner and repo name
    Example: https://github.com/facebook/react → ('facebook', 'react')
    """
    parsed = urlparse(url if re.match(r'https?://', url) else f'https://{url}')
    if parsed.netloc.lower() not in ('github.com', 'www.github.com'):
        return None, None
    parts = [part for part in parsed.path.split('/') if part]
    if len(parts) >= 2:
        owner = parts[0]
        repo = parts[1].replace('.git', '')
        return owner, repo
    return None, None


def parse_github_url_details(url):
    """
    Converts a GitHub URL to repo details. Supports repo URLs and common
    /tree/<branch>/<path> or /blob/<branch>/<path> URLs.
    """
    parsed = urlparse(url if re.match(r'https?://', url) else f'https://{url}')
    if parsed.netloc.lower() not in ('github.com', 'www.github.com'):
        return None

    parts = [part for part in parsed.path.split('/') if part]
    if len(parts) < 2:
        return None

    details = {
        'owner': parts[0],
        'repo': parts[1].replace('.git', ''),
        'ref': None,
        'path': '',
    }
    if len(parts) >= 4 and parts[2] in ('tree', 'blob'):
        details['ref'] = parts[3]
        details['path'] = clean_repo_path('/'.join(parts[4:]))
    return details


def clean_repo_path(path):
    """
    Normalizes a user-selected repo path without allowing parent traversal.
    """
    pieces = []
    for piece in str(path or '').replace('\\', '/').split('/'):
        part = piece.strip()
        if not part or part == '.':
            continue
        if part == '..':
            continue
        pieces.append(part)
    return '/'.join(pieces)


def get_headers():
    """
    Returns headers with GitHub token if available
    """
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if GITHUB_TOKEN and GITHUB_TOKEN != 'your_github_token_here':
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    return headers


def _github_contents(owner, repo, path='', ref=None):
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    params = {'ref': ref} if ref else None
    return requests.get(url, headers=get_headers(), params=params, timeout=10)


def _github_repo(owner, repo):
    url = f'https://api.github.com/repos/{owner}/{repo}'
    return requests.get(url, headers=get_headers(), timeout=10)


def _github_tree(owner, repo, ref):
    url = f'https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}'
    return requests.get(url, headers=get_headers(), params={'recursive': '1'}, timeout=10)


def _default_branch(owner, repo):
    try:
        response = _github_repo(owner, repo)
        if response.status_code == 200:
            return response.json().get('default_branch')
    except Exception as e:
        print(f'Error fetching repository metadata: {e}')
    return None


def _raw_file_url(owner, repo, ref, path):
    safe_ref = quote(ref or 'main', safe='')
    safe_path = quote(clean_repo_path(path), safe='/')
    return f'https://raw.githubusercontent.com/{owner}/{repo}/{safe_ref}/{safe_path}'


def _path_has_skipped_folder(path):
    parts = {part.lower() for part in clean_repo_path(path).split('/') if part}
    return any(folder.lower() in parts for folder in SKIP_FOLDERS)


def _parent_paths(path):
    parts = clean_repo_path(path).split('/')
    parents = []
    for index in range(1, len(parts)):
        parents.append('/'.join(parts[:index]))
    return parents


def get_all_files(owner, repo, path='', files=None, max_files=MAX_GITHUB_FILES, ref=None):
    """
    Recursively gets all files in a GitHub repository
    """
    if files is None:
        files = []
    if len(files) >= max_files:
        return files

    try:
        response = _github_contents(owner, repo, clean_repo_path(path), ref)
        if response.status_code != 200:
            return []

        items = response.json()
        if isinstance(items, dict):
            items = [items]
        for item in items:
            if len(files) >= max_files:
                break
            if item['type'] == 'file':
                ext = os.path.splitext(item['name'])[1].lower()
                if ext in SUPPORTED_EXTENSIONS and item.get('size', 0) <= MAX_SOURCE_BYTES:
                    files.append(item)
            elif item['type'] == 'dir':
                if item['name'] not in SKIP_FOLDERS:
                    get_all_files(owner, repo, item['path'], files, max_files, ref)

        return files

    except Exception as e:
        print(f'Error fetching files: {e}')
        return []


def get_all_files_from_tree(owner, repo, path='', max_files=MAX_GITHUB_FILES, ref=None):
    selected_ref = ref or _default_branch(owner, repo) or 'main'
    selected_path = clean_repo_path(path)
    prefix = f'{selected_path}/' if selected_path else ''
    files = []

    try:
        response = _github_tree(owner, repo, selected_ref)
        if response.status_code != 200:
            return get_all_files(owner, repo, selected_path, max_files=max_files, ref=ref)

        for item in response.json().get('tree', []):
            if len(files) >= max_files:
                break
            if item.get('type') != 'blob':
                continue

            file_path = clean_repo_path(item.get('path', ''))
            if not file_path or _path_has_skipped_folder(file_path):
                continue
            if selected_path and file_path != selected_path and not file_path.startswith(prefix):
                continue

            ext = os.path.splitext(file_path)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS or item.get('size', 0) > MAX_SOURCE_BYTES:
                continue

            files.append({
                'name': os.path.basename(file_path),
                'path': file_path,
                'size': item.get('size', 0),
                'download_url': _raw_file_url(owner, repo, selected_ref, file_path),
            })
        return files
    except Exception as e:
        print(f'Error fetching files from tree: {e}')
        return get_all_files(owner, repo, selected_path, max_files=max_files, ref=ref)


def fetch_file_content(download_url):
    """
    Downloads and returns the content of a single file
    """
    try:
        response = requests.get(download_url, headers=get_headers(), timeout=10)
        if response.status_code == 200:
            if len(response.content) > MAX_SOURCE_BYTES:
                return None
            return response.text
        return None
    except Exception:
        return None


def get_github_folders(url, max_folders=MAX_GITHUB_FOLDERS):
    """
    Returns selectable repository folders for the frontend.
    """
    details = parse_github_url_details(url)
    if not details:
        return None

    selected_ref = details.get('ref')
    if not selected_ref:
        selected_ref = _default_branch(details['owner'], details['repo'])
    selected_ref = selected_ref or 'main'

    folder_paths = {''}
    tree_truncated = False
    try:
        response = _github_tree(details['owner'], details['repo'], selected_ref)
        if response.status_code != 200:
            return None

        payload = response.json()
        tree_truncated = bool(payload.get('truncated'))
        for item in payload.get('tree', []):
            item_path = clean_repo_path(item.get('path', ''))
            if not item_path or _path_has_skipped_folder(item_path):
                continue

            if item.get('type') == 'tree':
                folder_paths.add(item_path)
            elif item.get('type') == 'blob':
                for parent in _parent_paths(item_path):
                    if not _path_has_skipped_folder(parent):
                        folder_paths.add(parent)

            if len(folder_paths) >= max_folders:
                break
    except Exception as e:
        print(f'Error fetching folders: {e}')
        return None

    sorted_paths = [''] + sorted(path for path in folder_paths if path)
    folders = [
        {'path': path, 'label': path or 'Repository root'}
        for path in sorted_paths[:max_folders]
    ]
    return {
        **details,
        'ref': selected_ref,
        'selected_path': details.get('path') or '',
        'folders': folders,
        'limits': {
            'max_folders': max_folders,
            'max_files': MAX_GITHUB_FILES,
            'max_source_bytes_per_file': MAX_SOURCE_BYTES,
            'tree_truncated': tree_truncated,
        }
    }


def fetch_github_code(url, path=None, ref=None):
    """
    Main function — takes a GitHub URL and returns list of files with code
    """
    details = parse_github_url_details(url)

    if not details:
        return []

    owner = details['owner']
    repo = details['repo']
    selected_ref = ref or details.get('ref')
    selected_path = clean_repo_path(path if path is not None else details.get('path', ''))

    print(f'Fetching repository: {owner}/{repo}')

    # Get all code files in the repo
    all_files = get_all_files_from_tree(owner, repo, path=selected_path, max_files=MAX_GITHUB_FILES, ref=selected_ref)

    if not all_files:
        return []

    result = []
    for file_info in all_files:
        code = fetch_file_content(file_info['download_url'])
        if code and code.strip():
            result.append({
                'filename': file_info['path'],
                'code': code
            })

    print(f'Successfully fetched {len(result)} files')
    return result
