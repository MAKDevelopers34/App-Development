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
MAX_GITHUB_FILE_OPTIONS = 500
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


def _path_is_inside(path, folder):
    clean_path = clean_repo_path(path)
    clean_folder = clean_repo_path(folder)
    if not clean_folder:
        return bool(clean_path)
    return clean_path == clean_folder or clean_path.startswith(f'{clean_folder}/')


def _file_option(path, selected_path=''):
    clean_path = clean_repo_path(path)
    clean_selected = clean_repo_path(selected_path)
    prefix = f'{clean_selected}/' if clean_selected else ''
    return {
        'path': clean_path,
        'label': clean_path[len(prefix):] if prefix and clean_path.startswith(prefix) else clean_path,
        'type': 'file',
    }


def _folder_file_map(file_paths):
    files_by_folder = {}
    for path in sorted(clean_repo_path(item) for item in file_paths):
        if not path:
            continue
        folders = [''] + _parent_paths(path)
        for folder in folders:
            bucket = files_by_folder.setdefault(folder, [])
            if len(bucket) < MAX_GITHUB_FILE_OPTIONS:
                bucket.append(_file_option(path, folder))
    return files_by_folder


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


def get_selectable_files(owner, repo, path='', max_files=MAX_GITHUB_FILE_OPTIONS, ref=None):
    """
    Gets supported source file paths for a dropdown. This uses the contents
    API so selected folders still show files when GitHub's recursive tree is
    truncated for large repositories.
    """
    return [
        {
            'path': clean_repo_path(item.get('path', '')),
            'size': item.get('size', 0),
        }
        for item in get_all_files(owner, repo, path, max_files=max_files, ref=ref)
        if clean_repo_path(item.get('path', ''))
    ]


def get_direct_selectable_files(owner, repo, path='', max_files=MAX_GITHUB_FILE_OPTIONS, ref=None):
    """
    Gets supported files directly inside the selected folder. This is the
    fastest path for the UI dropdown because it uses one GitHub contents call
    for the exact folder the user selected.
    """
    response = _github_contents(owner, repo, clean_repo_path(path), ref)
    if response.status_code != 200:
        return None

    items = response.json()
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        return None

    files = []
    for item in items:
        if len(files) >= max_files:
            break
        if not isinstance(item, dict) or item.get('type') != 'file':
            continue

        file_path = clean_repo_path(item.get('path') or '')
        if not file_path or _path_has_skipped_folder(file_path):
            continue

        ext = os.path.splitext(file_path)[1].lower()
        if ext in SUPPORTED_EXTENSIONS and item.get('size', 0) <= MAX_SOURCE_BYTES:
            files.append({
                'path': file_path,
                'size': item.get('size', 0),
            })

    return sorted(files, key=lambda item: item['path'])


def get_selectable_files_from_tree(owner, repo, path='', max_files=MAX_GITHUB_FILE_OPTIONS, ref=None):
    """
    Gets supported source file paths from GitHub's recursive tree endpoint.
    This is usually one request, so it is much faster for the frontend file
    dropdown than walking every directory through the contents API.
    """
    selected_ref = ref or _default_branch(owner, repo) or 'main'
    selected_path = clean_repo_path(path)
    prefix = f'{selected_path}/' if selected_path else ''

    response = _github_tree(owner, repo, selected_ref)
    if response.status_code != 200:
        return None, False

    payload = response.json()
    if isinstance(payload, list):
        files = []
        for item in payload:
            if len(files) >= max_files:
                break
            if not isinstance(item, dict) or item.get('type') != 'file':
                continue
            file_path = clean_repo_path(item.get('path', ''))
            if not file_path or _path_has_skipped_folder(file_path):
                continue
            ext = os.path.splitext(file_path)[1].lower()
            if ext in SUPPORTED_EXTENSIONS and item.get('size', 0) <= MAX_SOURCE_BYTES:
                files.append({
                    'path': file_path,
                    'size': item.get('size', 0),
                })
        return files, False

    if not isinstance(payload, dict):
        return None, False

    files = []
    for item in payload.get('tree', []):
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
        if ext in SUPPORTED_EXTENSIONS and item.get('size', 0) <= MAX_SOURCE_BYTES:
            files.append({
                'path': file_path,
                'size': item.get('size', 0),
            })

    return files, bool(payload.get('truncated'))


def get_github_file_options(url, selected_path=None, ref=None):
    """
    Returns supported source files for one selected repository folder. This is
    intentionally separate from the repository tree endpoint so the frontend
    can refresh the file dropdown for any folder without relying on a large
    recursive tree response.
    """
    details = parse_github_url_details(url)
    if not details:
        return None

    selected_ref = ref or details.get('ref')
    if not selected_ref:
        selected_ref = _default_branch(details['owner'], details['repo'])
    selected_ref = selected_ref or 'main'
    selected_path = clean_repo_path(
        selected_path if selected_path is not None else details.get('path') or ''
    )
    tree_truncated = False
    source_files = None

    try:
        source_files = get_direct_selectable_files(
            details['owner'],
            details['repo'],
            selected_path,
            max_files=MAX_GITHUB_FILE_OPTIONS,
            ref=selected_ref,
        )
    except Exception as e:
        print(f'Error fetching direct selectable files: {e}')

    if source_files is None or len(source_files) == 0:
        tree_files = None
        try:
            tree_files, tree_truncated = get_selectable_files_from_tree(
                details['owner'],
                details['repo'],
                selected_path,
                max_files=MAX_GITHUB_FILE_OPTIONS,
                ref=selected_ref,
            )
        except Exception as e:
            print(f'Error fetching selectable files from tree: {e}')

        source_files = tree_files if tree_files is not None else []
        if tree_files is None or (not source_files and tree_truncated):
            source_files = get_selectable_files(
                details['owner'],
                details['repo'],
                selected_path,
                max_files=MAX_GITHUB_FILE_OPTIONS,
                ref=selected_ref,
            )

    files = [_file_option(item['path'], selected_path) for item in source_files]

    return {
        **details,
        'ref': selected_ref,
        'selected_path': selected_path,
        'files': files,
        'files_by_folder': {selected_path: files},
        'limits': {
            'max_file_options': MAX_GITHUB_FILE_OPTIONS,
            'max_source_bytes_per_file': MAX_SOURCE_BYTES,
            'file_options_limited': len(files) >= MAX_GITHUB_FILE_OPTIONS,
            'tree_truncated': tree_truncated,
        },
    }


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


def get_github_folders(url, max_folders=MAX_GITHUB_FOLDERS, selected_path=None, ref=None):
    """
    Returns selectable repository folders and code files for the frontend.
    """
    details = parse_github_url_details(url)
    if not details:
        return None

    selected_ref = ref or details.get('ref')
    if not selected_ref:
        selected_ref = _default_branch(details['owner'], details['repo'])
    selected_ref = selected_ref or 'main'
    selected_path = clean_repo_path(
        selected_path if selected_path is not None else details.get('path') or ''
    )

    folder_paths = {''}
    file_paths = set()
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
                ext = os.path.splitext(item_path)[1].lower()
                if ext in SUPPORTED_EXTENSIONS and item.get('size', 0) <= MAX_SOURCE_BYTES:
                    file_paths.add(item_path)
                for parent in _parent_paths(item_path):
                    if not _path_has_skipped_folder(parent):
                        folder_paths.add(parent)
    except Exception as e:
        print(f'Error fetching folders: {e}')
        return None

    sorted_paths = [''] + sorted(path for path in folder_paths if path)
    selectable_file_paths = {
        path for path in file_paths if _path_is_inside(path, selected_path)
    }
    if selected_path:
        for item in get_selectable_files(
            details['owner'],
            details['repo'],
            selected_path,
            max_files=MAX_GITHUB_FILE_OPTIONS,
            ref=selected_ref,
        ):
            selectable_file_paths.add(item['path'])
    sorted_files = sorted(selectable_file_paths)
    directories = [
        {'path': path, 'label': path or 'Repository root', 'type': 'folder'}
        for path in sorted_paths[:max_folders]
    ]
    files = [_file_option(path, selected_path) for path in sorted_files[:MAX_GITHUB_FILE_OPTIONS]]
    files_by_folder = _folder_file_map(file_paths | set(sorted_files))
    selectable_paths = _interleave_github_paths(directories, files)[:max_folders]
    return {
        **details,
        'ref': selected_ref,
        'selected_path': selected_path,
        'folders': selectable_paths,
        'directories': directories,
        'files': files,
        'files_by_folder': files_by_folder,
        'paths': selectable_paths,
        'limits': {
            'max_folders': max_folders,
            'max_paths': max_folders,
            'max_files': MAX_GITHUB_FILES,
            'max_file_options': MAX_GITHUB_FILE_OPTIONS,
            'max_source_bytes_per_file': MAX_SOURCE_BYTES,
            'file_options_limited': len(sorted_files) > MAX_GITHUB_FILE_OPTIONS,
            'tree_truncated': tree_truncated,
        }
    }


def _interleave_github_paths(folders, files):
    root = [item for item in folders if not item.get('path')]
    folder_items = [item for item in folders if item.get('path')]
    combined = list(root)
    max_len = max(len(folder_items), len(files))
    for index in range(max_len):
        if index < len(folder_items):
            combined.append(folder_items[index])
        if index < len(files):
            combined.append(files[index])
    return combined


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
