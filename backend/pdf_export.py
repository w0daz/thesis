"""
PDF Export Endpoint for Energy Analytics - FastAPI Version
Generates comprehensive professional reports with charts and insights
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import io

# Create router
pdf_router = APIRouter()

# Request model
class PDFExportRequest(BaseModel):
    generatedAt: str
    statistics: Optional[Dict[str, Any]] = None
    hourlyPattern: Optional[Dict[str, Any]] = None
    weekdayStats: Optional[Dict[str, Any]] = None
    baselineData: Optional[Dict[str, Any]] = None
    dailyConsumption: Optional[List[Dict[str, Any]]] = None

def create_header_footer(canvas_obj, doc):
    """Add header and footer to each page"""
    canvas_obj.saveState()
    
    # Header
    canvas_obj.setFont('Helvetica-Bold', 10)
    canvas_obj.setFillColor(colors.HexColor('#667eea'))
    canvas_obj.drawString(inch, letter[1] - 0.5*inch, "⚡ Energy Monitoring System")
    canvas_obj.drawString(letter[0] - 3*inch, letter[1] - 0.5*inch, 
                         f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Header line
    canvas_obj.setStrokeColor(colors.HexColor('#667eea'))
    canvas_obj.setLineWidth(2)
    canvas_obj.line(inch, letter[1] - 0.6*inch, letter[0] - inch, letter[1] - 0.6*inch)
    
    # Footer
    canvas_obj.setFont('Helvetica', 8)
    canvas_obj.setFillColor(colors.grey)
    canvas_obj.drawCentredString(letter[0]/2, 0.5*inch, 
                                f"Page {doc.page}")
    canvas_obj.drawString(inch, 0.5*inch, "Energy Analytics Report")
    
    canvas_obj.restoreState()

@pdf_router.post('/api/export/pdf')
async def export_analytics_pdf(data: PDFExportRequest):
    """
    Generate comprehensive PDF report with analytics data
    """
    try:
        # Convert Pydantic model to dict
        data_dict = data.model_dump()
        
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                              rightMargin=inch, leftMargin=inch,
                              topMargin=inch, bottomMargin=inch)
        
        # Container for PDF elements
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=10,
            fontName='Helvetica-Bold'
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=10
        )
        
        # ═══════════════════════════════════════════════════════════
        # TITLE PAGE
        # ═══════════════════════════════════════════════════════════
        
        story.append(Spacer(1, 1.5*inch))
        story.append(Paragraph("Energy Analytics Report", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Report metadata
        generated_time = datetime.fromisoformat(data_dict.get('generatedAt', datetime.now().isoformat()).replace('Z', '+00:00'))
        meta_data = [
            ['Report Type:', 'Comprehensive Energy Analytics'],
            ['Generated:', generated_time.strftime('%B %d, %Y at %H:%M')],
            ['Period:', 'Last 30 Days'],
            ['Status:', 'Complete']
        ]
        
        meta_table = Table(meta_data, colWidths=[2*inch, 4*inch])
        meta_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#667eea')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f5f7fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0'))
        ]))
        story.append(meta_table)
        story.append(PageBreak())
        
        # ═══════════════════════════════════════════════════════════
        # EXECUTIVE SUMMARY
        # ═══════════════════════════════════════════════════════════
        
        story.append(Paragraph("Executive Summary", heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        stats = data_dict.get('statistics', {}) or {}
        
        summary_text = f"""
        This report provides a comprehensive analysis of energy consumption patterns 
        over the monitoring period. The system has recorded an average power consumption 
        of <b>{stats.get('average_kw', 0):.3f} kW</b>, with peak demand reaching 
        <b>{stats.get('max_kw', 0):.3f} kW</b>. A total of <b>{stats.get('spikes', 0)} 
        consumption spikes</b> were detected, indicating periods of unusual energy usage 
        that may warrant further investigation.
        """
        story.append(Paragraph(summary_text, body_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Key Metrics Table
        story.append(Paragraph("Key Performance Indicators", subheading_style))
        
        kpi_data = [
            ['Metric', 'Value', 'Status'],
            ['Average Power', f"{stats.get('average_kw', 0):.3f} kW", 'Normal'],
            ['Peak Power', f"{stats.get('max_kw', 0):.3f} kW", 'Monitored'],
            ['Minimum Power', f"{stats.get('min_kw', 0):.3f} kW", 'Normal'],
            ['Baseline Deviation', f"{stats.get('baseline_deviation', 0):.1f}%", 'Acceptable'],
            ['Alert Count', str(stats.get('spikes', 0)), 'Review Required' if stats.get('spikes', 0) > 10 else 'Good']
        ]
        
        kpi_table = Table(kpi_data, colWidths=[2.5*inch, 2*inch, 1.5*inch])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 11),
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f7fa')]),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8)
        ]))
        story.append(kpi_table)
        story.append(PageBreak())
        
        # ═══════════════════════════════════════════════════════════
        # HOURLY CONSUMPTION PATTERNS
        # ═══════════════════════════════════════════════════════════
        
        story.append(Paragraph("Hourly Consumption Patterns", heading_style))
        story.append(Spacer(1, 0.1*inch))
        
        hourly_pattern = data_dict.get('hourlyPattern', {}) or {}
        
        if hourly_pattern:
            story.append(Paragraph("24-Hour Energy Usage Analysis", subheading_style))
            
            analysis_text = """
            The hourly consumption pattern reveals the typical energy usage throughout 
            the day. Peak hours and off-peak periods are identified to help optimize 
            energy management strategies and reduce costs during high-demand periods.
            """
            story.append(Paragraph(analysis_text, body_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Hourly data table
            hourly_data = [['Hour', 'Avg Power (kW)', 'Min (kW)', 'Max (kW)', 'Std Dev']]
            
            peak_hours = []
            off_peak_hours = []
            
            for hour in range(24):
                hour_str = str(hour)
                hour_data = hourly_pattern.get(hour_str, {})
                
                mean = hour_data.get('mean', 0)
                minimum = hour_data.get('min', 0)
                maximum = hour_data.get('max', 0)
                std_dev = hour_data.get('std_dev', 0)
                
                hourly_data.append([
                    f"{hour:02d}:00",
                    f"{mean:.3f}",
                    f"{minimum:.3f}",
                    f"{maximum:.3f}",
                    f"{std_dev:.3f}"
                ])
                
                # Identify peak and off-peak hours
                if mean > stats.get('average_kw', 0) * 1.2:
                    peak_hours.append(hour)
                elif mean < stats.get('average_kw', 0) * 0.8:
                    off_peak_hours.append(hour)
            
            hourly_table = Table(hourly_data, colWidths=[1*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
            hourly_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f7fa')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
            ]))
            story.append(hourly_table)
            story.append(Spacer(1, 0.2*inch))
            
            # Peak hours insight
            if peak_hours:
                peak_text = f"<b>Peak Hours:</b> {', '.join([f'{h:02d}:00' for h in peak_hours])}"
                story.append(Paragraph(peak_text, body_style))
            
            if off_peak_hours:
                off_peak_text = f"<b>Off-Peak Hours:</b> {', '.join([f'{h:02d}:00' for h in off_peak_hours])}"
                story.append(Paragraph(off_peak_text, body_style))
        
        story.append(PageBreak())
        
        # ═══════════════════════════════════════════════════════════
        # WEEKDAY VS WEEKEND ANALYSIS
        # ═══════════════════════════════════════════════════════════
        
        story.append(Paragraph("Weekday vs Weekend Consumption", heading_style))
        story.append(Spacer(1, 0.1*inch))
        
        weekday_stats = data_dict.get('weekdayStats', {}) or {}
        
        if weekday_stats:
            weekday_avg = weekday_stats.get('weekday', 0)
            weekend_avg = weekday_stats.get('weekend', 0)
            difference = weekday_stats.get('difference', 0)
            percent_diff = weekday_stats.get('percentDiff', 0)
            
            comparison_text = f"""
            Analysis shows distinct consumption patterns between weekdays and weekends. 
            Weekday average consumption is <b>{weekday_avg:.3f} kW</b>, while weekend 
            consumption averages <b>{weekend_avg:.3f} kW</b>, representing a difference 
            of <b>{abs(percent_diff):.1f}%</b>. This {
                'higher weekend usage may indicate residential patterns' if weekend_avg > weekday_avg 
                else 'lower weekend usage suggests commercial or office-based consumption'
            }.
            """
            story.append(Paragraph(comparison_text, body_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Comparison table
            comparison_data = [
                ['Period', 'Average Power (kW)', 'Difference'],
                ['Weekdays', f"{weekday_avg:.3f}", '-'],
                ['Weekends', f"{weekend_avg:.3f}", f"{percent_diff:+.1f}%"],
            ]
            
            comp_table = Table(comparison_data, colWidths=[2*inch, 2*inch, 2*inch])
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 11),
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f7fa')]),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10)
            ]))
            story.append(comp_table)
        
        story.append(PageBreak())
        
        # ═══════════════════════════════════════════════════════════
        # RECOMMENDATIONS
        # ═══════════════════════════════════════════════════════════
        
        story.append(Paragraph("Recommendations & Insights", heading_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Generate smart recommendations based on data
        recommendations = []
        
        if stats.get('spikes', 0) > 5:
            recommendations.append(
                "High number of consumption spikes detected. Consider investigating "
                "equipment that may be causing irregular power draws."
            )
        
        if peak_hours:
            recommendations.append(
                f"Peak consumption occurs during hours: {', '.join([f'{h:02d}:00' for h in peak_hours[:3]])}. "
                "Consider load shifting to off-peak hours to reduce costs."
            )
        
        if weekday_stats and abs(weekday_stats.get('percentDiff', 0)) > 20:
            recommendations.append(
                "Significant difference between weekday and weekend consumption. "
                "Review operating schedules to ensure equipment is not running unnecessarily."
            )
        
        recommendations.append(
            "Regular monitoring of baseline patterns helps identify anomalies early. "
            "Set up automated alerts for deviations exceeding 15%."
        )
        
        recommendations.append(
            "Consider implementing energy-saving measures during identified peak hours "
            "to optimize consumption and reduce overall costs."
        )
        
        for i, rec in enumerate(recommendations, 1):
            story.append(Paragraph(f"<b>{i}.</b> {rec}", body_style))
            story.append(Spacer(1, 0.1*inch))
        
        story.append(PageBreak())
        
        # ═══════════════════════════════════════════════════════════
        # CONCLUSION
        # ═══════════════════════════════════════════════════════════
        
        story.append(Paragraph("Conclusion", heading_style))
        story.append(Spacer(1, 0.1*inch))
        
        conclusion_text = """
        This comprehensive energy analytics report provides valuable insights into 
        consumption patterns and opportunities for optimization. Regular review of 
        these metrics, combined with the recommendations provided, can lead to 
        significant improvements in energy efficiency and cost reduction.
        <br/><br/>
        For questions or detailed analysis of specific patterns, please consult with 
        the facilities management team or energy consultants.
        """
        story.append(Paragraph(conclusion_text, body_style))
        
        # Build PDF
        doc.build(story, onFirstPage=create_header_footer, onLaterPages=create_header_footer)
        
        # Get PDF from buffer
        buffer.seek(0)
        
        return StreamingResponse(
            buffer,
            media_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=energy-analytics-report-{datetime.now().strftime("%Y-%m-%d")}.pdf'
            }
        )
        
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))