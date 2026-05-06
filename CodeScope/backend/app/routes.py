from flask import Blueprint, request, jsonify, send_file
from app.analyzer import CodeAnalyzer
from app.github_fetcher import fetch_github_code
from app.ai_explainer import get_ai_explanation, get_function_level_explanations
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
        'version': '2.0.0',
        'endpoints': [
            '/api/analyze/code',
            '/api/analyze/inputs',
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
        concrete_inputs = (
            data.get('concrete_inputs') or
            data.get('input_values') or
            data.get('inputs')
        )

        if not code.strip():
            return jsonify({'error': 'Code is empty'}), 400

        # Run full analysis
        result = analyzer.analyze(code, filename, concrete_inputs)

        # Add AI explanation
        language = result.get('language', 'unknown')
        ai_explanation = get_ai_explanation(result, code, language)
        result['ai_explanation'] = ai_explanation

        # Add call graph analysis
        call_graph_report = analyzer.call_graph_analyzer.get_call_chain_report(
            code,
            analyzer.last_func_complexities,
            language
        )
        result['call_chain_report'] = call_graph_report

        # Add function level explanations
        result['function_explanations'] = get_function_level_explanations(
            analyzer.last_func_complexities,
            call_graph_report,
            language
        )

        return jsonify({'success': True, 'filename': filename, 'result': result})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/api/analyze/inputs', methods=['POST'])
def infer_inputs():
    try:
        data = request.get_json()
        if not data or 'code' not in data:
            return jsonify({'error': 'No code provided'}), 400

        code = data['code']
        filename = data.get('filename', 'code.py')
        language = analyzer.detect_language(code, filename)
        schema = analyzer.infer_input_schema(code, language)
        return jsonify({'success': True, 'filename': filename, 'input_schema': schema})

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
        supported_extensions = [
            '.py', '.js', '.java', '.cpp', '.c', '.ts', '.jsx', '.tsx'
        ]

        with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
            for filename in zip_ref.namelist():
                ext = os.path.splitext(filename)[1].lower()
                if ext not in supported_extensions:
                    continue
                if filename.startswith('.') or '/__pycache__/' in filename:
                    continue

                with zip_ref.open(filename) as f:
                    try:
                        code = f.read().decode('utf-8')
                        if not code.strip():
                            continue

                        result = analyzer.analyze(code, filename)
                        language = result.get('language', 'unknown')

                        # AI explanation per file
                        result['ai_explanation'] = get_ai_explanation(
                            result, code, language)

                        # Call graph per file
                        call_graph_report = analyzer.call_graph_analyzer.get_call_chain_report(
                            code,
                            analyzer.last_func_complexities,
                            language
                        )
                        result['call_chain_report'] = call_graph_report
                        result['function_explanations'] = get_function_level_explanations(
                            analyzer.last_func_complexities,
                            call_graph_report,
                            language
                        )

                        results.append({'filename': filename, 'result': result})

                    except UnicodeDecodeError:
                        continue

        if not results:
            return jsonify({'error': 'No supported code files found in ZIP'}), 400

        avg_rating = round(
            sum(r['result']['rating'] for r in results) / len(results))
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
            return jsonify({'error': 'Could not fetch code from GitHub'}), 400

        results = []
        for file in files:
            result = analyzer.analyze(file['code'], file['filename'])
            language = result.get('language', 'unknown')

            result['ai_explanation'] = get_ai_explanation(
                result, file['code'], language)

            call_graph_report = analyzer.call_graph_analyzer.get_call_chain_report(
                file['code'],
                analyzer.last_func_complexities,
                language
            )
            result['call_chain_report'] = call_graph_report
            result['function_explanations'] = get_function_level_explanations(
                analyzer.last_func_complexities,
                call_graph_report,
                language
            )

            results.append({'filename': file['filename'], 'result': result})

        avg_rating = round(
            sum(r['result']['rating'] for r in results) / len(results))
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


# ─── Generate PDF Report ────────────────────────────────────
@main.route('/api/report', methods=['POST'])
def generate_report():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        analysis_data = data.get('analysis_data')
        report_type = data.get('report_type', 'code')

        if not analysis_data:
            return jsonify({'error': 'No analysis data provided'}), 400

        from app.report_generator import generate_pdf_report
        pdf_bytes = generate_pdf_report(analysis_data, report_type)

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='codescope_report.pdf'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500
