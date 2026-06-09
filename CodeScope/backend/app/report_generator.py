from html import escape
import datetime
import io
import re
import unicodedata

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PRIMARY = HexColor('#2563eb')
PRIMARY_DARK = HexColor('#1d4ed8')
SUCCESS = HexColor('#16a34a')
WARNING = HexColor('#d97706')
DANGER = HexColor('#dc2626')
DARK = HexColor('#111827')
GRAY = HexColor('#5f6675')
MUTED = HexColor('#94a3b8')
LIGHT_GRAY = HexColor('#f8fafc')
PRIMARY_LIGHT = HexColor('#eff6ff')
SUCCESS_LIGHT = HexColor('#f0fdf4')
WARNING_LIGHT = HexColor('#fffbeb')
DANGER_LIGHT = HexColor('#fef2f2')
BORDER = HexColor('#d9e0ea')
CODE_BG = HexColor('#111827')
CODE_SUCCESS_BG = HexColor('#102016')
WHITE = HexColor('#ffffff')
CODE_BORDER = HexColor('#1f2937')
CODE_SUCCESS_BORDER = HexColor('#14532d')
CODE_CHUNK_LINES = 36


def get_rating_color(rating):
    if rating >= 8:
        return SUCCESS
    if rating >= 5:
        return WARNING
    return DANGER


def get_complexity_color(complexity):
    rank = _complexity_rank(complexity)
    if rank <= 1:
        return SUCCESS
    if rank <= 4:
        return WARNING
    return DANGER


def generate_pdf_report(analysis_data, report_type='code'):
    """
    Build a multi-page CodeScope PDF report from analyzer data already returned by
    the API. This does not call Groq again; it only formats available results.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.62 * inch,
        leftMargin=0.62 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.62 * inch,
        title='CodeScope Complexity Report',
        author='CodeScope',
    )

    styles = _build_styles()
    elements = []
    analysis_data = analysis_data or {}
    report_type = report_type or 'code'

    _add_report_header(elements, report_type, analysis_data, styles)

    if report_type == 'code':
        filename, result = _unwrap_file_payload(analysis_data)
        _add_single_file_report(elements, result, filename, styles)
    elif report_type in ('zip', 'github'):
        files = analysis_data.get('files') or []
        _add_project_overview(elements, analysis_data, report_type, styles)
        _add_project_intelligence_report(
            elements,
            (analysis_data.get('project_summary') or {}).get('project_intelligence') or {},
            styles,
        )
        _add_file_listing(elements, files, styles)

        for index, file_data in enumerate(files):
            if index > 0 or elements:
                elements.append(PageBreak())
            filename, result = _unwrap_file_payload(file_data)
            _add_single_file_report(
                elements,
                result,
                filename,
                styles,
                section_label=f'File {index + 1} of {len(files)}',
            )
    else:
        elements.append(Paragraph('Unsupported report type.', styles['Body']))

    doc.build(elements, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    buffer.seek(0)
    return buffer.getvalue()


def _build_styles():
    base = getSampleStyleSheet()
    styles = {
        'Title': ParagraphStyle(
            'CodeScopeTitle',
            parent=base['Title'],
            fontSize=25,
            leading=30,
            textColor=PRIMARY,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=5,
        ),
        'Subtitle': ParagraphStyle(
            'CodeScopeSubtitle',
            parent=base['Normal'],
            fontSize=9.5,
            leading=13,
            textColor=GRAY,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        'Section': ParagraphStyle(
            'CodeScopeSection',
            parent=base['Heading2'],
            fontSize=13.5,
            leading=17,
            textColor=DARK,
            fontName='Helvetica-Bold',
            spaceBefore=13,
            spaceAfter=7,
        ),
        'Subsection': ParagraphStyle(
            'CodeScopeSubsection',
            parent=base['Heading3'],
            fontSize=10.5,
            leading=14,
            textColor=DARK,
            fontName='Helvetica-Bold',
            spaceBefore=9,
            spaceAfter=5,
        ),
        'Body': ParagraphStyle(
            'CodeScopeBody',
            parent=base['Normal'],
            fontSize=8.7,
            leading=12.4,
            textColor=DARK,
            spaceAfter=5,
        ),
        'Small': ParagraphStyle(
            'CodeScopeSmall',
            parent=base['Normal'],
            fontSize=7.6,
            leading=10.5,
            textColor=GRAY,
            spaceAfter=4,
        ),
        'TableCell': ParagraphStyle(
            'CodeScopeTableCell',
            parent=base['Normal'],
            fontSize=7.5,
            leading=9.6,
            textColor=DARK,
            alignment=TA_LEFT,
        ),
        'TableHead': ParagraphStyle(
            'CodeScopeTableHead',
            parent=base['Normal'],
            fontSize=7.3,
            leading=9,
            textColor=WHITE,
            fontName='Helvetica-Bold',
            alignment=TA_LEFT,
        ),
        'Code': ParagraphStyle(
            'CodeScopeCode',
            parent=base['Code'],
            fontName='Courier',
            fontSize=7.2,
            leading=9.4,
            textColor=WHITE,
            backColor=CODE_BG,
            leftIndent=6,
            rightIndent=6,
            spaceBefore=3,
            spaceAfter=7,
        ),
        'CodeSuccess': ParagraphStyle(
            'CodeScopeCodeSuccess',
            parent=base['Code'],
            fontName='Courier',
            fontSize=7.2,
            leading=9.4,
            textColor=HexColor('#d9fbe5'),
            backColor=CODE_SUCCESS_BG,
            leftIndent=6,
            rightIndent=6,
            spaceBefore=3,
            spaceAfter=7,
        ),
    }
    return styles


def _draw_footer(canvas, doc):
    canvas.saveState()
    y = 0.38 * inch
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(doc.leftMargin, y + 10, A4[0] - doc.rightMargin, y + 10)
    canvas.setFillColor(GRAY)
    canvas.setFont('Helvetica', 7.5)
    canvas.drawString(doc.leftMargin, y, 'CodeScope Complexity Report')
    canvas.drawRightString(A4[0] - doc.rightMargin, y, f'Page {doc.page}')
    canvas.restoreState()


def _add_report_header(elements, report_type, analysis_data, styles):
    label = {
        'code': 'Single-file complexity report',
        'zip': 'ZIP project complexity report',
        'github': 'GitHub project complexity report',
    }.get(report_type, 'Complexity report')

    elements.append(Paragraph('CodeScope', styles['Title']))
    elements.append(Paragraph(_e(label), styles['Subtitle']))
    generated = datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')

    context = []
    if report_type == 'github' and analysis_data.get('github_url'):
        context.append(f"Repository: {_pdf_text(analysis_data.get('github_url'))}")
    if analysis_data.get('selected_path'):
        context.append(f"Folder: {_pdf_text(analysis_data.get('selected_path'))}")
    if analysis_data.get('branch'):
        context.append(f"Branch: {_pdf_text(analysis_data.get('branch'))}")
    context.append(f'Generated on {generated}')

    elements.append(Paragraph(_e(' | '.join(context)), styles['Subtitle']))
    elements.append(Spacer(1, 0.1 * inch))


def _add_project_overview(elements, analysis_data, report_type, styles):
    project_summary = analysis_data.get('project_summary') or {}
    rows = [
        ['Metric', 'Value'],
        ['Source', 'GitHub URL' if report_type == 'github' else 'ZIP archive'],
        ['Files analyzed', analysis_data.get('total_files', len(analysis_data.get('files') or []))],
        ['Lines analyzed', analysis_data.get('total_lines', 0)],
        ['Issues detected', analysis_data.get('total_issues', 0)],
        ['Average rating', f"{analysis_data.get('average_rating', 0)}/10"],
    ]
    if project_summary.get('worst_time_complexity'):
        rows.append(['Worst Big O time', project_summary.get('worst_time_complexity')])
    if project_summary.get('hotspot_count') is not None:
        rows.append(['Hot code sections', project_summary.get('hotspot_count')])

    elements.append(Paragraph('Project Overview', styles['Section']))
    elements.append(_simple_table(rows, [2.2 * inch, 4.35 * inch], styles))

    summary_text = project_summary.get('summary')
    if summary_text:
        elements.append(Paragraph(_e(summary_text), styles['Body']))
    elements.append(Spacer(1, 0.08 * inch))


def _add_project_intelligence_report(elements, project, styles):
    if not project:
        return

    elements.append(Paragraph('Project Intelligence', styles['Section']))
    confidence = _pdf_text(project.get('project_confidence') or 'unknown').title()
    summary = project.get('summary') or 'Project intelligence was not available for this batch.'
    elements.append(Paragraph(
        f"<b>Confidence:</b> {_e(confidence)}<br/>{_e(summary)}",
        styles['Body'],
    ))

    metrics_data = [
        ['Metric', 'Count'],
        ['Dependency edges', len(project.get('dependency_edges') or [])],
        ['Cross-file calls', len(project.get('cross_file_calls') or [])],
        ['Project bottlenecks', len(project.get('bottlenecks') or [])],
        ['Critical paths', len(project.get('critical_paths') or [])],
        ['Dependency cycles', len(project.get('cycles') or [])],
    ]
    elements.append(_simple_table(metrics_data, [3.15 * inch, 3.4 * inch], styles))

    bottlenecks = project.get('bottlenecks') or []
    if bottlenecks:
        elements.append(Paragraph('Top Project Bottlenecks', styles['Subsection']))
        rows = [['File', 'Function', 'Complexity', 'Referenced By']]
        for item in bottlenecks[:8]:
            rows.append([
                item.get('filename', 'unknown'),
                _function_label(item.get('function')),
                _complexity_html(item.get('complexity', 'O(1)')),
                f"{item.get('called_by_count', 0)} file(s)",
            ])
        elements.append(_styled_table(rows, [2.25 * inch, 1.55 * inch, 1.2 * inch, 1.35 * inch], styles))

    critical_paths = project.get('critical_paths') or []
    if critical_paths:
        elements.append(Paragraph('Critical Paths', styles['Subsection']))
        for item in critical_paths[:6]:
            path = ' -> '.join(_pdf_text(part) for part in item.get('path') or [])
            text = (
                f"{item.get('entrypoint', 'entrypoint')} reaches "
                f"{_function_label(item.get('bottleneck_function'))} in "
                f"{item.get('bottleneck_file', 'unknown')} at "
                f"{item.get('complexity', 'O(1)')}: {path}"
            )
            elements.append(Paragraph(_e(text), styles['Small']))

    limitations = project.get('limitations') or []
    if limitations:
        elements.append(Paragraph('Project-Level Limits', styles['Subsection']))
        for item in limitations[:4]:
            elements.append(Paragraph(_e(item), styles['Small']))

    elements.append(Spacer(1, 0.08 * inch))


def _add_file_listing(elements, files, styles):
    if not files:
        return

    elements.append(Paragraph('Files and Function Coverage', styles['Section']))
    rows = [['File', 'Lang', 'Lines', 'Big O Time', 'Big O Space', 'Functions', 'Hot', 'Modified']]

    for file_data in files:
        filename, result = _unwrap_file_payload(file_data)
        functions = _attach_solutions_to_functions(
            _function_rows_for(result),
            _ai_solutions_for(result),
        )
        rows.append([
            filename,
            str(result.get('language', 'unknown')).upper(),
            result.get('lines_of_code', 0),
            _complexity_html(_overall_time(result)),
            _complexity_html(_overall_space(result)),
            len(functions),
            len(_highest_hotspots(result, functions)),
            sum(1 for item in functions if item.get('ai_solutions')),
        ])

    elements.append(_styled_table(
        rows,
        [2.0 * inch, 0.48 * inch, 0.48 * inch, 0.92 * inch, 0.92 * inch, 0.67 * inch, 0.45 * inch, 0.65 * inch],
        styles,
        font_size=7,
    ))
    elements.append(Spacer(1, 0.08 * inch))


def _add_single_file_report(elements, result, filename, styles, section_label=None):
    result = result or {}
    filename = filename or result.get('filename') or 'Unknown File'
    source_code = result.get('source_code') or ''
    language = result.get('language') or ''
    functions = _function_rows_for(result)
    functions = _hydrate_function_snippets(functions, source_code, language)
    solutions = _ai_solutions_for(result)
    functions = _attach_solutions_to_functions(functions, solutions)
    hotspots = _highest_hotspots(result, functions)
    hotspots = _attach_solutions_to_hotspots(hotspots, solutions, functions)

    title = f"{section_label}: {filename}" if section_label else f"File Report: {filename}"
    elements.append(Paragraph(_e(title), styles['Section']))

    elements.append(_file_metrics_table(result, styles))
    _add_explanation_summary(elements, result, styles)
    _add_hot_code_section(elements, hotspots, styles)
    _add_function_summary_table(elements, functions, styles)
    _add_function_details(elements, functions, styles)
    _add_issues_and_suggestions(elements, result, styles)


def _file_metrics_table(result, styles):
    overall = result.get('overall_complexity') or {}
    allocation = result.get('memory_allocation_analysis') or {}
    reported_space = _overall_space(result)
    peak_space = overall.get('peak_space') or allocation.get('peak_live_auxiliary_space') or reported_space
    total_allocation = overall.get('total_allocation') or allocation.get('total_allocated_space') or reported_space
    rating = result.get('rating', 0)

    rows = [
        ['Metric', 'Value'],
        ['Language', str(result.get('language', 'unknown')).upper()],
        ['Lines of code', result.get('lines_of_code', 0)],
        ['Big O time', _complexity_html(_overall_time(result))],
        ['Big O space', _complexity_html(reported_space)],
        ['Peak live auxiliary memory', peak_space],
        ['Total allocated/copied memory', total_allocation],
        ['Performance rating', f'{rating}/10'],
    ]
    return _simple_table(rows, [2.25 * inch, 4.3 * inch], styles)


def _add_explanation_summary(elements, result, styles):
    reason = result.get('time_complexity_reason') or ''
    memory_model = (
        (result.get('overall_complexity') or {}).get('memory_model') or
        (result.get('memory_allocation_analysis') or {}).get('summary') or
        result.get('space_complexity_reason') or
        ''
    )

    if reason:
        elements.append(Paragraph('<b>Why this time complexity:</b> ' + _e(reason), styles['Body']))
    if memory_model:
        elements.append(Paragraph('<b>Space model:</b> ' + _e(memory_model), styles['Body']))


def _add_hot_code_section(elements, hotspots, styles):
    elements.append(Paragraph('Hot Code Sections', styles['Section']))
    if not hotspots:
        elements.append(Paragraph('No high-complexity hotspot was detected for this file.', styles['Body']))
        return

    for index, hotspot in enumerate(hotspots, 1):
        heading = (
            f"{index}. {_function_label(hotspot.get('function'))} "
            f"at line {hotspot.get('line') or 1} - {hotspot.get('complexity', 'O(1)')}"
        )
        elements.append(Paragraph(_e(heading), styles['Subsection']))
        reason = hotspot.get('reason')
        if reason:
            elements.append(Paragraph(_e(reason), styles['Small']))
        if hotspot.get('snippet'):
            elements.append(Paragraph('Function code', styles['Small']))
            _add_code_block(elements, hotspot.get('snippet'), styles)
        for solution in hotspot.get('ai_solutions') or []:
            _add_solution_block(elements, solution, styles)


def _add_function_summary_table(elements, functions, styles):
    elements.append(Paragraph('Function-by-Function Complexity', styles['Section']))
    if not functions:
        elements.append(Paragraph('No named functions were detected. File-level complexity is shown above.', styles['Body']))
        return

    rows = [['Function', 'Line', 'Direct Time', 'With Calls', 'Calls', 'Modified']]
    for item in functions:
        calls = item.get('calls') or []
        call_count = len(calls)
        rows.append([
            _function_label(item.get('function')),
            item.get('line') or '',
            _complexity_html(item.get('own_complexity') or item.get('complexity') or 'O(1)'),
            _complexity_html(item.get('effective_complexity') or item.get('complexity') or 'O(1)'),
            call_count,
            'Yes' if item.get('ai_solutions') else 'No',
        ])

    elements.append(_styled_table(
        rows,
        [1.85 * inch, 0.48 * inch, 1.05 * inch, 1.05 * inch, 0.55 * inch, 0.72 * inch],
        styles,
        font_size=7.2,
    ))


def _add_function_details(elements, functions, styles):
    if not functions:
        return

    elements.append(Paragraph('Function Details', styles['Section']))
    for item in functions:
        heading = (
            f"{_function_label(item.get('function'))} - line {item.get('line') or 1} - "
            f"direct {item.get('own_complexity') or item.get('complexity') or 'O(1)'}, "
            f"with calls {item.get('effective_complexity') or item.get('complexity') or 'O(1)'}"
        )
        elements.append(Paragraph(_e(heading), styles['Subsection']))
        explanation = item.get('explanation') or item.get('reason') or ''
        if explanation:
            elements.append(Paragraph(_e(explanation), styles['Small']))

        calls = item.get('calls') or []
        if calls:
            call_text = ', '.join(
                f"{_function_label(call.get('function'))} x {call.get('multiplier', 'O(1)')} at {call.get('complexity', 'O(1)')}"
                for call in calls
                if call.get('function')
            )
            if call_text:
                elements.append(Paragraph('<b>Calls:</b> ' + _e(call_text), styles['Small']))

        if item.get('snippet'):
            elements.append(Paragraph('Function code', styles['Small']))
            _add_code_block(elements, item.get('snippet'), styles)

        for solution in item.get('ai_solutions') or []:
            _add_solution_block(elements, solution, styles)


def _add_solution_block(elements, solution, styles):
    source = solution.get('source_label') or solution.get('source') or 'AI'
    title = solution.get('title') or 'Lower-complexity modified function'
    before = solution.get('complexity_before') or 'current'
    after = solution.get('complexity_after') or 'lower'

    elements.append(Paragraph(
        f"<b>{_e(source)} modified function:</b> {_e(title)}",
        styles['Body'],
    ))
    elements.append(_simple_table([
        ['Before', 'After'],
        [_complexity_html(before), _complexity_html(after)],
    ], [1.7 * inch, 1.7 * inch], styles, header_color=SUCCESS))

    description = solution.get('description') or solution.get('solution') or solution.get('notes') or ''
    if description:
        elements.append(Paragraph(_e(description), styles['Small']))
    if solution.get('code'):
        _add_code_block(elements, solution.get('code'), styles, success=True)


def _add_issues_and_suggestions(elements, result, styles):
    issues = result.get('issues') or []
    if issues:
        elements.append(Paragraph('Issues Found', styles['Section']))
        for issue in issues:
            severity = str(issue.get('severity') or 'low').upper()
            line = issue.get('line') or ''
            message = issue.get('message') or ''
            elements.append(Paragraph(
                f"<b>[{_e(severity)}]</b> Line {_e(line)}: {_e(message)}",
                styles['Small'],
            ))

    suggestions = result.get('suggestions') or []
    if suggestions:
        elements.append(Paragraph('Suggestions', styles['Section']))
        for index, suggestion in enumerate(suggestions, 1):
            elements.append(Paragraph(f'{index}. {_e(suggestion)}', styles['Small']))

    elements.append(Spacer(1, 0.12 * inch))


def _add_code_block(elements, code, styles, success=False):
    text = _code_text(code)
    if not text:
        return
    style = styles['CodeSuccess'] if success else styles['Code']
    background = CODE_SUCCESS_BG if success else CODE_BG
    border = CODE_SUCCESS_BORDER if success else CODE_BORDER

    for chunk in _chunk_code(text):
        preformatted = Preformatted(chunk, style, maxLineLength=96)
        table = Table([[preformatted]], colWidths=[6.55 * inch], hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), background),
            ('BOX', (0, 0), (-1, -1), 0.5, border),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.04 * inch))


def _simple_table(rows, col_widths, styles, header_color=PRIMARY):
    return _styled_table(rows, col_widths, styles, header_color=header_color)


def _styled_table(rows, col_widths, styles, header_color=PRIMARY, font_size=7.6):
    converted = []
    for row_index, row in enumerate(rows):
        style = styles['TableHead'] if row_index == 0 else styles['TableCell']
        converted.append([
            cell if isinstance(cell, Paragraph) else Paragraph(_cell_html(cell), style)
            for cell in row
        ])

    table = Table(converted, colWidths=col_widths, repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), font_size),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ('GRID', (0, 0), (-1, -1), 0.35, BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return table


def _chunk_code(text):
    lines = str(text or '').splitlines()
    if not lines:
        return []
    return [
        '\n'.join(lines[index:index + CODE_CHUNK_LINES])
        for index in range(0, len(lines), CODE_CHUNK_LINES)
    ]


def _cell_html(value):
    if isinstance(value, str) and '<font ' in value:
        return value
    return _e(value)


def _function_rows_for(result):
    result = result or {}
    details = result.get('function_complexity_details') or []
    explanations = result.get('function_explanations') or []

    if isinstance(details, dict):
        details = list(details.values())
    if isinstance(explanations, dict):
        explanations = list(explanations.values())

    if not details:
        return [
            {
                **item,
                'own_complexity': item.get('own_complexity') or item.get('complexity') or 'O(1)',
                'effective_complexity': (
                    item.get('effective_complexity') or
                    item.get('complexity') or
                    item.get('own_complexity') or
                    'O(1)'
                ),
                'snippet': item.get('snippet') or '',
                'calls': item.get('calls') or [],
            }
            for item in explanations
            if isinstance(item, dict)
        ]

    rows = []
    for detail in details:
        if not isinstance(detail, dict):
            continue
        explanation = next(
            (item for item in explanations if _names_match(item.get('function'), detail.get('function'))),
            {},
        )
        own = (
            detail.get('own_complexity') or
            detail.get('complexity') or
            explanation.get('own_complexity') or
            explanation.get('complexity') or
            'O(1)'
        )
        effective = (
            detail.get('effective_complexity') or
            detail.get('complexity') or
            explanation.get('effective_complexity') or
            explanation.get('complexity') or
            own
        )
        rows.append({
            **explanation,
            **detail,
            'own_complexity': own,
            'effective_complexity': effective,
            'complexity': effective,
            'explanation': detail.get('reason') or explanation.get('explanation') or '',
            'snippet': detail.get('snippet') or explanation.get('snippet') or '',
            'calls': detail.get('calls') or explanation.get('calls') or [],
        })
    return rows


def _hydrate_function_snippets(functions, source_code='', language=''):
    if not source_code:
        return functions
    hydrated = []
    for item in functions:
        current = _code_text(item.get('snippet'))
        named_line = _find_function_line(source_code, item.get('function'), language)
        line = named_line or item.get('line') or 1
        rebuilt = _source_function_snippet(source_code, line, language)
        if rebuilt and (not current or current.count('\n') < rebuilt.count('\n')):
            hydrated.append({**item, 'line': line, 'snippet': rebuilt})
        else:
            hydrated.append(item)
    return hydrated


def _highest_hotspots(result, functions):
    raw = result.get('hotspots') or []
    merged = []
    for item in functions or []:
        hotspot = next((raw_item for raw_item in raw if _names_match(raw_item.get('function'), item.get('function'))), {})
        complexity = item.get('effective_complexity') or item.get('complexity') or hotspot.get('complexity')
        merged.append({
            'function': item.get('function') or hotspot.get('function'),
            'line': item.get('line') or hotspot.get('line') or 1,
            'complexity': complexity or 'O(1)',
            'reason': item.get('explanation') or hotspot.get('reason') or '',
            'snippet': item.get('snippet') or hotspot.get('snippet') or '',
        })

    if not merged:
        merged = [
            {
                'function': item.get('function'),
                'line': item.get('line') or 1,
                'complexity': item.get('complexity') or 'O(1)',
                'reason': item.get('reason') or '',
                'snippet': item.get('snippet') or '',
            }
            for item in raw
        ]

    ranked = [
        {**item, '_rank': _complexity_rank(item.get('complexity'))}
        for item in merged
        if item.get('function') and _complexity_rank(item.get('complexity')) > _complexity_rank('O(n)')
    ]
    if not ranked:
        return []
    max_rank = max(item['_rank'] for item in ranked)
    output = []
    for item in ranked:
        if item['_rank'] == max_rank:
            clean = dict(item)
            clean.pop('_rank', None)
            output.append(clean)
    return output


def _ai_solutions_for(result):
    result = result or {}
    candidates = []

    transformed = result.get('ai_transformed_code') or {}
    if transformed.get('available') and (transformed.get('code') or transformed.get('example')):
        candidates.append(transformed)

    for item in result.get('ai_optimized_functions') or []:
        candidates.append(item)
    for item in result.get('optimizations') or []:
        if item.get('ai_generated') or item.get('example') or item.get('code'):
            candidates.append(item)
    for item in result.get('hotspots') or []:
        if item.get('ai_solution'):
            candidates.append(item.get('ai_solution'))
        candidates.extend(item.get('ai_solutions') or [])
    for issue in result.get('issues') or []:
        if issue.get('ai_solution'):
            candidates.append(issue.get('ai_solution'))

    normalized = [_normalize_solution(item) for item in candidates]
    return _unique_solutions([item for item in normalized if item])


def _normalize_solution(solution):
    if not isinstance(solution, dict):
        return None
    code = solution.get('code') or solution.get('example')
    if not code:
        return None
    source = solution.get('source') or 'ai'
    source_label = solution.get('source_label') or ('Groq' if str(source).lower() == 'groq' else 'AI')
    return {
        **solution,
        'code': code,
        'source_label': source_label,
        'description': solution.get('description') or solution.get('solution') or solution.get('problem') or '',
    }


def _attach_solutions_to_functions(functions, solutions):
    rows = [{**item, 'ai_solutions': []} for item in functions]
    for solution in solutions:
        target = next(
            (item for item in rows if _solution_matches_function(solution, item)),
            None,
        )
        if target:
            target['ai_solutions'].append(solution)

    for item in rows:
        item['ai_solutions'] = _unique_solutions(item.get('ai_solutions') or [])
    return rows


def _attach_solutions_to_hotspots(hotspots, solutions, functions):
    output = []
    for hotspot in hotspots:
        matched_function = next(
            (item for item in functions if _names_match(item.get('function'), hotspot.get('function'))),
            None,
        )
        matched = [
            solution for solution in solutions
            if _solution_matches_function(solution, hotspot) or
            (matched_function and solution in (matched_function.get('ai_solutions') or []))
        ]
        output.append({**hotspot, 'ai_solutions': _unique_solutions(matched)})
    return output


def _solution_matches_function(solution, item):
    if not solution or not item or not item.get('function'):
        return False
    if solution.get('function') and _names_match(solution.get('function'), item.get('function')):
        return True
    if _code_mentions_function(solution.get('code'), item.get('function')):
        return True
    text = ' '.join(_pdf_text(solution.get(key)) for key in ('title', 'description', 'solution', 'notes')).lower()
    return any(alias in text for alias in _aliases_for(item.get('function')))


def _unique_solutions(solutions):
    seen = set()
    output = []
    for solution in solutions or []:
        key = (
            str(solution.get('function') or '').lower(),
            re.sub(r'\s+', ' ', _code_text(solution.get('code'))),
            str(solution.get('complexity_before') or ''),
            str(solution.get('complexity_after') or ''),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(solution)
    return output


def _overall_time(result):
    overall = result.get('overall_complexity') or {}
    return overall.get('scalable_time') or overall.get('time') or result.get('time_complexity') or 'O(1)'


def _overall_space(result):
    overall = result.get('overall_complexity') or {}
    return overall.get('scalable_space') or overall.get('space') or result.get('space_complexity') or 'O(1)'


def _unwrap_file_payload(data):
    data = data or {}
    result = data.get('result') if isinstance(data.get('result'), dict) else data
    filename = (
        data.get('filename') or
        result.get('filename') if isinstance(result, dict) else None
    )
    return filename or 'Unknown File', result or {}


def _find_function_line(source_code, function_name, language=''):
    name = str(function_name or '').strip()
    if not name:
        return 0
    escaped = re.escape(name.split('.')[-1])
    patterns = [
        re.compile(rf'^\s*(?:async\s+def|def|class)\s+{escaped}\s*[\(:]'),
        re.compile(rf'^\s*function\s+\*?\s*{escaped}\s*\('),
        re.compile(rf'^\s*(?:const|let|var)\s+{escaped}\s*='),
        re.compile(rf'^\s*(?:(?:public|private|protected)\s+)?(?:static\s+)?[\w:<>,\[\] ?&*]+\s+{escaped}\s*\('),
    ]
    for index, line in enumerate(str(source_code or '').splitlines(), 1):
        if any(pattern.search(line) for pattern in patterns):
            return index
    return 0


def _source_function_snippet(source_code, start_line=1, language=''):
    lines = str(source_code or '').replace('\r\n', '\n').split('\n')
    if not lines:
        return ''
    start = max(0, int(start_line or 1) - 1)
    if start >= len(lines):
        return ''
    first = lines[start]
    base_indent = _line_indent(first)
    is_python = language == 'python' or _line_starts_python_block(first)

    if is_python:
        seen_body = False
        for index in range(start + 1, len(lines)):
            line = lines[index]
            if not line.strip():
                continue
            if (
                seen_body and
                _line_indent(line) <= base_indent and
                _line_starts_python_section_boundary(line)
            ):
                return '\n'.join(lines[start:index]).strip()
            if _line_indent(line) <= base_indent and _line_starts_python_block(line):
                return '\n'.join(lines[start:index]).strip()
            if _line_indent(line) > base_indent:
                seen_body = True
        return '\n'.join(lines[start:]).strip()

    depth = 0
    seen_open = False
    for index in range(start, len(lines)):
        line = lines[index]
        if '{' in line:
            seen_open = True
        depth += line.count('{') - line.count('}')
        if seen_open and depth <= 0:
            return '\n'.join(lines[start:index + 1]).strip()
        if not seen_open and index > start and _looks_like_function_boundary(line):
            return '\n'.join(lines[start:index]).strip()
    return '\n'.join(lines[start:]).strip()


def _line_indent(line):
    expanded = str(line or '').expandtabs(4)
    return len(expanded) - len(expanded.lstrip())


def _line_starts_python_block(line):
    stripped = str(line or '').strip()
    return stripped.startswith(('def ', 'async def ', 'class '))


def _line_starts_python_section_boundary(line):
    stripped = str(line or '').strip()
    if not stripped.startswith('#'):
        return False
    marker = stripped.lstrip('#').strip()
    if not marker:
        return False
    if set(marker) <= {'=', '-', '_', '*'}:
        return True
    return marker.isupper() or marker.endswith(('FUNCTIONS', 'DEMO FUNCTIONS', 'MAIN MENU'))


def _looks_like_function_boundary(line):
    text = str(line or '').strip()
    if _line_starts_python_block(text):
        return True
    return bool(re.match(
        r'^(?:function\s+\*?\s+\w+|(?:const|let|var)\s+\w+\s*=|'
        r'(?:(?:public|private|protected)\s+)?(?:static\s+)?[\w:<>,\[\] ?&*]+\s+\w+\s*\()',
        text,
    ))


def _aliases_for(name):
    raw = str(name or '').strip().lower()
    if not raw:
        return []
    return list(dict.fromkeys([raw, raw.split('.')[-1]]))


def _names_match(left, right):
    right_aliases = set(_aliases_for(right))
    return any(alias in right_aliases for alias in _aliases_for(left))


def _code_mentions_function(code, function_name):
    text = str(code or '')
    for alias in _aliases_for(function_name):
        escaped = re.escape(alias)
        if re.search(rf'\b{escaped}\s*\(', text, re.IGNORECASE):
            return True
        if re.search(rf'\bdef\s+{escaped}\s*\(', text, re.IGNORECASE):
            return True
        if re.search(rf'\bfunction\s+{escaped}\s*\(', text, re.IGNORECASE):
            return True
    return False


def _function_label(name):
    value = _pdf_text(name or 'file scope')
    return f'{value}()' if value and not value.endswith('()') and value != 'file scope' else value


def _complexity_html(value):
    color = _hex_for_color(get_complexity_color(value))
    return f'<b><font color="{color}">{_e(value)}</font></b>'


def _complexity_rank(value):
    label = _normalize_complexity(value)
    if not label or 'unknown' in label:
        return 0
    if 'ackermann' in label or 'a(m,n)' in label:
        return 12
    if 'n!' in label:
        return 11
    if '3^n' in label:
        return 10
    if '2^n' in label or 'phi' in label:
        return 9
    if 'n^3' in label or 'v^3' in label:
        return 8
    if 'n^2log' in label:
        return 7
    if 'n^2' in label or 'v*e' in label or 'n*w' in label:
        return 6
    if 'nlog' in label or '(v+e)log' in label or 'elog' in label:
        return 4
    if 'v+e' in label or 'n+k' in label or 'n+m' in label or 'o(n)' in label:
        return 3
    if 'sqrt' in label:
        return 2
    if 'log' in label:
        return 1
    return 3 if 'n' in label else 0


def _normalize_complexity(value):
    text = _pdf_text(value).lower()
    replacements = {
        ' ': '',
        '\u00b2': '^2',
        '\u00b3': '^3',
        '\u00d7': '*',
        '\u03c6': 'phi',
        '\u03b1': 'alpha',
        '\u221a': 'sqrt',
        '\u00c2\u00b2': '^2',
        '\u00c2\u00b3': '^3',
        '\u00c3\u2014': '*',
        '\u00ce\u00b1': 'alpha',
        '\u00cf\u2020': 'phi',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace('**', '^')
    return text


def _hex_for_color(color):
    value = getattr(color, 'hexval', None)
    raw = value() if callable(value) else '#111827'
    return f"#{raw[2:]}" if isinstance(raw, str) and raw.startswith('0x') else raw


def _pdf_text(value):
    text = '' if value is None else str(value)
    replacements = {
        '\u00b2': '^2',
        '\u00b3': '^3',
        '\u207f': '^n',
        '\u221a': 'sqrt',
        '\u03b1': 'alpha',
        '\u03c6': 'phi',
        '\u00d7': 'x',
        '\u2192': '->',
        '\u2014': '-',
        '\u2013': '-',
        '\u2022': '-',
        '\u00c2\u00b2': '^2',
        '\u00c2\u00b3': '^3',
        '\u00c3\u2014': 'x',
        '\u00ce\u00b1': 'alpha',
        '\u00cf\u2020': 'phi',
        '\u00e2\u20ac\u201d': '-',
        '\u00e2\u20ac\u201c': '-',
        '\u00e2\u2020\u2019': '->',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = unicodedata.normalize('NFKD', text)
    return text.encode('ascii', 'ignore').decode('ascii')


def _code_text(value):
    text = _pdf_text(value).replace('\r\n', '\n').replace('\t', '    ')
    return text.strip()


def _e(value):
    return escape(_pdf_text(value))
