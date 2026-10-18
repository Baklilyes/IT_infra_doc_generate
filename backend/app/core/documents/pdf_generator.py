"""PDF Generator using ReportLab for official sealed architecture deliverables."""
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

from app.models.project import Project
from app.models.equipment import Equipment
from app.models.network import NetworkSegment, ConfigurationParam
from app.core.network_validator import is_secret_field, mask_secret


class NumberedCanvas:
    """Canvas wrapper to add page numbers 'Page X'."""
    def __init__(self, *args, **kwargs):
        pass


def build_pdf_document(
    output_path: str,
    doc_type: str,  # 'hld', 'lld', 'config_annexes', 'commissioning'
    project: Project,
    equipment_list: list[Equipment],
    segments: list[NetworkSegment],
    configs: list[ConfigurationParam],
    narrative_text: str = ""
) -> str:
    """Build a complete, professionally formatted PDF document."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Heading1'],
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#0f172a'),
        fontName='Helvetica-Bold',
        spaceAfter=10
    )
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=25
    )
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Heading1'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0f294a'),
        fontName='Helvetica-Bold',
        spaceBefore=14,
        spaceAfter=8
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1e293b')
    )
    ai_warning_style = ParagraphStyle(
        'AIWarning',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#b45309'),
        fontName='Helvetica-Oblique',
        spaceAfter=6
    )

    story = []

    # Title Map
    type_meta = {
        "hld": ("Dossier d'Architecture Générale (HLD)", "High Level Design & Principes Directeurs"),
        "lld": ("Dossier d'Architecture Détaillée (LLD)", "Low Level Design & Spécifications"),
        "config_annexes": ("Annexes de Configuration Matérielle", "Paramétrage Technique & Déploiement"),
        "commissioning": ("Dossier de Recette & Mise en Service", "Plan de Validation Opérationnelle")
    }
    main_title, sub_title = type_meta.get(doc_type, ("Document Technique", "Infrastructure"))

    # 1. Cover Page Elements
    story.append(Spacer(1, 40))
    story.append(Paragraph(f"PROJET : {project.reference.upper()}", ParagraphStyle('RefBadge', fontSize=10, textColor=colors.HexColor('#2563eb'), fontName='Helvetica-Bold', spaceAfter=8)))
    story.append(Paragraph(main_title, title_style))
    story.append(Paragraph(sub_title, subtitle_style))
    story.append(Spacer(1, 30))

    # Meta Table
    meta_data = [
        [Paragraph("<b>Nom du Projet :</b>", body_style), Paragraph(project.name, body_style)],
        [Paragraph("<b>Client :</b>", body_style), Paragraph(project.client_name, body_style)],
        [Paragraph("<b>Responsable Technique :</b>", body_style), Paragraph(project.lead_name, body_style)],
        [Paragraph("<b>Version :</b>", body_style), Paragraph("1.0 - Émise pour validation", body_style)],
        [Paragraph("<b>Date de Publication :</b>", body_style), Paragraph(datetime.now().strftime("%d/%m/%Y"), body_style)],
    ]
    meta_table = Table(meta_data, colWidths=[150, 350])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(PageBreak())

    # 2. Document Control & Approvals
    story.append(Paragraph("Contrôle du Document & Approbations", h1_style))
    ctrl_data = [
        [Paragraph("<b>Version</b>", body_style), Paragraph("<b>Date</b>", body_style), Paragraph("<b>Auteur / Rôle</b>", body_style), Paragraph("<b>Statut</b>", body_style)],
        [Paragraph("1.0", body_style), Paragraph(datetime.now().strftime("%d/%m/%Y"), body_style), Paragraph(f"{project.lead_name} (Lead)", body_style), Paragraph("Revue technique", body_style)],
        [Paragraph("1.0-VAL", body_style), Paragraph("-", body_style), Paragraph("Validateur Final", body_style), Paragraph("En attente de signature", body_style)],
    ]
    ctrl_table = Table(ctrl_data, colWidths=[60, 80, 160, 200])
    ctrl_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f294a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(ctrl_table)
    story.append(Spacer(1, 15))

    # 3. Narrative Section
    story.append(Paragraph("1. Synthèse Générale & Contexte Architectural", h1_style))
    if narrative_text:
        if "[Généré par IA" in narrative_text:
            story.append(Paragraph("AVIS DE CONFORMITÉ : Rédigé avec l'assistance d'une IA locale. Doit être vérifié par l'ingénieur.", ai_warning_style))
        for line in narrative_text.splitlines():
            if line.strip():
                story.append(Paragraph(line, body_style))
                story.append(Spacer(1, 4))
    else:
        story.append(Paragraph(f"Architecture technique du projet {project.reference}.", body_style))

    story.append(Spacer(1, 15))

    # 4. Content Specific Sections
    if doc_type in ["hld", "lld"]:
        # Equipment Table
        story.append(Paragraph(f"2. Inventaire Matériel ({len(equipment_list)} équipements)", h1_style))
        eq_data = [[
            Paragraph("<b>Nom</b>", body_style),
            Paragraph("<b>Famille</b>", body_style),
            Paragraph("<b>Modèle</b>", body_style),
            Paragraph("<b>N° Série</b>", body_style),
            Paragraph("<b>IP Management</b>", body_style)
        ]]
        for eq in equipment_list[:30]:
            eq_data.append([
                Paragraph(eq.name, body_style),
                Paragraph(eq.category.value, body_style),
                Paragraph(eq.model or "-", body_style),
                Paragraph(eq.serial_number or "-", body_style),
                Paragraph(eq.management_ip or "-", body_style)
            ])
        eq_table = Table(eq_data, colWidths=[100, 80, 110, 100, 110])
        eq_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f294a')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(eq_table)
        story.append(Spacer(1, 15))

        # VLAN Segments Table
        story.append(Paragraph(f"3. Plan d'Adressage & VLANs ({len(segments)} réseaux)", h1_style))
        seg_data = [[
            Paragraph("<b>VLAN</b>", body_style),
            Paragraph("<b>Nom Réseau</b>", body_style),
            Paragraph("<b>CIDR</b>", body_style),
            Paragraph("<b>Passerelle</b>", body_style),
            Paragraph("<b>Zone</b>", body_style)
        ]]
        for seg in segments:
            seg_data.append([
                Paragraph(str(seg.vlan_id), body_style),
                Paragraph(seg.name, body_style),
                Paragraph(seg.cidr or "-", body_style),
                Paragraph(seg.gateway or "-", body_style),
                Paragraph(seg.zone or "LAN", body_style)
            ])
        seg_table = Table(seg_data, colWidths=[50, 140, 110, 100, 100])
        seg_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f294a')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(seg_table)

    elif doc_type == "config_annexes":
        story.append(Paragraph("2. Paramètres & Configurations Techniques", h1_style))
        cfg_data = [[
            Paragraph("<b>Catégorie</b>", body_style),
            Paragraph("<b>Paramètre (Clé)</b>", body_style),
            Paragraph("<b>Valeur</b>", body_style),
            Paragraph("<b>Sécurité</b>", body_style)
        ]]
        for cfg in configs:
            val = "<SECRET_MASQUÉ>" if (cfg.is_secret or is_secret_field(cfg.key)) else cfg.value
            cfg_data.append([
                Paragraph(cfg.category, body_style),
                Paragraph(cfg.key, body_style),
                Paragraph(val or "-", body_style),
                Paragraph("Confidentiel" if (cfg.is_secret or is_secret_field(cfg.key)) else "Standard", body_style)
            ])
        cfg_table = Table(cfg_data, colWidths=[100, 140, 160, 100])
        cfg_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f294a')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(cfg_table)

    elif doc_type == "commissioning":
        story.append(Paragraph("2. Grille de Recette & Validation Opérationnelle", h1_style))
        test_data = [[
            Paragraph("<b>Test</b>", body_style),
            Paragraph("<b>Équipement</b>", body_style),
            Paragraph("<b>Nature</b>", body_style),
            Paragraph("<b>Attendu</b>", body_style),
            Paragraph("<b>Validation</b>", body_style)
        ]]
        for idx, eq in enumerate(equipment_list[:25]):
            test_data.append([
                Paragraph(f"T-{idx+1:02d}", body_style),
                Paragraph(eq.name, body_style),
                Paragraph("Connectivité & SVI", body_style),
                Paragraph(f"Ping {eq.management_ip or 'OK'}", body_style),
                Paragraph("[  ] Conforme", body_style)
            ])
        test_table = Table(test_data, colWidths=[50, 120, 110, 120, 100])
        test_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f294a')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(test_table)

    # Build PDF
    doc.build(story)
    return output_path
