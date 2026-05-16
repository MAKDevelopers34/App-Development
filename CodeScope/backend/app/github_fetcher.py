import requests
import re
import os
from urllib.parse import urlparse
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


def get_headers():
    """
    Returns headers with GitHub token if available
    """
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if GITHUB_TOKEN and GITHUB_TOKEN != 'your_github_token_here':
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    return headers


def get_all_files(owner, repo, path='', files=None, max_files=MAX_GITHUB_FILES):
    """
    Recursively gets all files in a GitHub repository
    """
    if files is None:
        files = []
    if len(files) >= max_files:
        return files

    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    headers = get_headers()

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []

        items = response.json()
        for item in items:
            if len(files) >= max_files:
                break
            if item['type'] == 'file':
                ext = os.path.splitext(item['name'])[1].lower()
                if ext in SUPPORTED_EXTENSIONS and item.get('size', 0) <= MAX_SOURCE_BYTES:
                    files.append(item)
            elif item['type'] == 'dir':
                # Skip common non-code folders
                skip_folders = ['node_modules', '.git', '__pycache__', 
                               'venv', 'dist', 'build', '.next']
                if item['name'] not in skip_folders:
                    get_all_files(owner, repo, item['path'], files, max_files)

        return files

    except Exception as e:
        print(f'Error fetching files: {e}')
        return []


def fetch_file_content(download_url):
    """
    Downloads and returns the content of a single file
    """
    try:
        response = requests.get(download_url, timeout=10)
        if response.status_code == 200:
            if len(response.content) > MAX_SOURCE_BYTES:
                return None
            return response.text
        return None
    except Exception:
        return None


def fetch_github_code(url):
    """
    Main function — takes a GitHub URL and returns list of files with code
    """
    owner, repo = parse_github_url(url)

    if not owner or not repo:
        return []

    print(f'Fetching repository: {owner}/{repo}')

    # Get all code files in the repo
    all_files = get_all_files(owner, repo, max_files=MAX_GITHUB_FILES)

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
