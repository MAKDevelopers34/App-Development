from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
import datetime

# ─── Colors ─────────────────────────────────────────────────
PRIMARY     = HexColor('#1a73e8')
SUCCESS     = HexColor('#34a853')
WARNING     = HexColor('#fbbc04')
DANGER      = HexColor('#ea4335')
DARK        = HexColor('#202124')
LIGHT_GRAY  = HexColor('#f8f9fa')
BORDER      = HexColor('#dadce0')

def get_rating_color(rating):
    if rating >= 8:
        return SUCCESS
    elif rating >= 5:
        return WARNING
    else:
        return DANGER

def get_complexity_color(complexity):
    good = ['O(1)', 'O(log n)']
    medium = ['O(n)', 'O(n log n)']
    if complexity in good:
        return SUCCESS
    elif complexity in medium:
        return WARNING
    else:
        return DANGER

def generate_pdf_report(analysis_data, report_type='code'):
    """
    Generates a professional PDF report for CodeScope analysis
    Returns bytes of the PDF file
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch
    )

    styles = getSampleStyleSheet()
    elements = []

    # ─── Title style ────────────────────────────────────────
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=PRIMARY,
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=HexColor('#5f6368'),
        spaceAfter=20,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=DARK,
        spaceBefore=16,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DARK,
        spaceAfter=6,
        leading=16
    )

    # ─── Header ─────────────────────────────────────────────
    elements.append(Paragraph('CodeScope', title_style))
    elements.append(Paragraph('AI-Powered Code Complexity Analysis Report', subtitle_style))

    # Date
    date_str = datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')
    elements.append(Paragraph(f'Generated on {date_str}', subtitle_style))
    elements.append(Spacer(1, 0.2 * inch))

    # ─── Handle single file analysis ────────────────────────
    if report_type == 'code':
        result = analysis_data.get('result', {})
        filename = analysis_data.get('filename', 'Unknown')
        _add_single_file_report(elements, result, filename, 
                                heading_style, normal_style)

    # ─── Handle ZIP or GitHub analysis ──────────────────────
    elif report_type in ['zip', 'github']:
        files = analysis_data.get('files', [])
        elements.append(Paragraph('Summary', heading_style))

        summary_data = [
            ['Total Files', 'Total Lines', 'Total Issues', 'Average Rating'],
            [
                str(analysis_data.get('total_files', 0)),
                str(analysis_data.get('total_lines', 0)),
                str(analysis_data.get('total_issues', 0)),
                f"{analysis_data.get('average_rating', 0)}/10"
            ]
        ]

        summary_table = Table(summary_data, colWidths=[1.5*inch]*4)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), PRIMARY),
            ('TEXTCOLOR', (0,0), (-1,0), HexColor('#ffffff')),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [LIGHT_GRAY, HexColor('#ffffff')]),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER),
            ('ROWHEIGHT', (0,0), (-1,-1), 28),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.15 * inch))

        for file_data in files:
            elements.append(Paragraph(
                f"File: {file_data['filename']}", heading_style))
            _add_single_file_report(
                elements, file_data['result'], 
                file_data['filename'], heading_style, normal_style)

    # ─── Build PDF ──────────────────────────────────────────
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def _add_single_file_report(elements, result, filename, heading_style, normal_style):
    """
    Adds analysis details for a single file to the PDF
    """
    styles = getSampleStyleSheet()

    # Metrics table
    rating = result.get('rating', 0)
    time_c = result.get('time_complexity', 'N/A')
    space_c = result.get('space_complexity', 'N/A')
    language = result.get('language', 'unknown').upper()
    loc = result.get('lines_of_code', 0)

    metrics_data = [
        ['Metric', 'Value'],
        ['Language', language],
        ['Lines of Code', str(loc)],
        ['Time Complexity', time_c],
        ['Space Complexity', space_c],
        ['Performance Rating', f'{rating}/10'],
    ]

    metrics_table = Table(metrics_data, colWidths=[2.5*inch, 3.5*inch])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('TEXTCOLOR', (0,0), (-1,0), HexColor('#ffffff')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [LIGHT_GRAY, HexColor('#ffffff')]),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('ROWHEIGHT', (0,0), (-1,-1), 26),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
    ]))
    elements.append(metrics_table)
    elements.append(Spacer(1, 0.15 * inch))

    # Issues
    issues = result.get('issues', [])
    if issues:
        elements.append(Paragraph('Issues Found', heading_style))
        for issue in issues:
            severity = issue.get('severity', 'low').upper()
            message = issue.get('message', '')
            line = issue.get('line', '')
            elements.append(Paragraph(
                f'<b>[{severity}]</b> Line {line}: {message}', normal_style))

    # Suggestions
    suggestions = result.get('suggestions', [])
    if suggestions:
        elements.append(Paragraph('Suggestions', heading_style))
        for i, suggestion in enumerate(suggestions, 1):
            elements.append(Paragraph(f'{i}. {suggestion}', normal_style))

    elements.append(Spacer(1, 0.2 * inch))