from flask import Blueprint, request, jsonify
from app.analyzer import CodeAnalyzer
from app.github_fetcher import fetch_github_code
import zipfile
import io
import os

main = Blueprint('main', __name__)
analyzer = CodeAnalyzer()

# ─── Health check ───────────────────────────────────────────
@main.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'CodeScope API is running',
        'version': '1.0.0',
        'endpoints': [
            '/api/analyze/code',
            '/api/analyze/zip',
            '/api/analyze/github'
        ]
    })

# ─── Analyze pasted code ────────────────────────────────────
@main.route('/api/analyze/code', methods=['POST'])
def analyze_code():
    try:
        data = request.get_json()

        if not data or 'code' not in data:
            return jsonify({'error': 'No code provided'}), 400

        code = data['code']
        filename = data.get('filename', 'code.py')

        if not code.strip():
            return jsonify({'error': 'Code is empty'}), 400

        result = analyzer.analyze(code, filename)

        return jsonify({
            'success': True,
            'filename': filename,
            'result': result
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─── Analyze ZIP file ───────────────────────────────────────
@main.route('/api/analyze/zip', methods=['POST'])
def analyze_zip():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']

        if not file.filename.endswith('.zip'):
            return jsonify({'error': 'Please upload a .zip file'}), 400

        file_bytes = file.read()
        zip_buffer = io.BytesIO(file_bytes)

        results = []
        supported_extensions = ['.py', '.js', '.java', '.cpp', '.c', '.ts', '.jsx', '.tsx']

        with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
            for filename in zip_ref.namelist():
                ext = os.path.splitext(filename)[1].lower()

                if ext not in supported_extensions:
                    continue

                # Skip hidden files and folders
                if filename.startswith('.') or '/__pycache__/' in filename:
                    continue

                with zip_ref.open(filename) as f:
                    try:
                        code = f.read().decode('utf-8')
                        if code.strip():
                            result = analyzer.analyze(code, filename)
                            results.append({
                                'filename': filename,
                                'result': result
                            })
                    except UnicodeDecodeError:
                        continue

        if not results:
            return jsonify({'error': 'No supported code files found in ZIP'}), 400

        # Overall summary
        avg_rating = round(sum(r['result']['rating'] for r in results) / len(results))
        total_lines = sum(r['result']['lines_of_code'] for r in results)
        all_issues = sum(len(r['result']['issues']) for r in results)

        return jsonify({
            'success': True,
            'total_files': len(results),
            'total_lines': total_lines,
            'total_issues': all_issues,
            'average_rating': avg_rating,
            'files': results
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─── Analyze GitHub repo ────────────────────────────────────
@main.route('/api/analyze/github', methods=['POST'])
def analyze_github():
    try:
        data = request.get_json()

        if not data or 'url' not in data:
            return jsonify({'error': 'No GitHub URL provided'}), 400

        url = data['url']

        if 'github.com' not in url:
            return jsonify({'error': 'Please provide a valid GitHub URL'}), 400

        files = fetch_github_code(url)

        if not files:
            return jsonify({'error': 'Could not fetch code from GitHub URL'}), 400

        results = []
        for file in files:
            result = analyzer.analyze(file['code'], file['filename'])
            results.append({
                'filename': file['filename'],
                'result': result
            })

        avg_rating = round(sum(r['result']['rating'] for r in results) / len(results))
        total_lines = sum(r['result']['lines_of_code'] for r in results)
        all_issues = sum(len(r['result']['issues']) for r in results)

        return jsonify({
            'success': True,
            'github_url': url,
            'total_files': len(results),
            'total_lines': total_lines,
            'total_issues': all_issues,
            'average_rating': avg_rating,
            'files': results
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500