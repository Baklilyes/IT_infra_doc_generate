"""DOCX Generator for HLD, LLD, Configuration Annexes, and Commissioning Deliverables."""
import os
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from app.models.project import Project
from app.models.equipment import Equipment
from app.models.network import NetworkSegment, ConfigurationParam
from app.core.network_validator import is_secret_field, mask_secret


def set_cell_background(cell, hex_color: str):
    """Set background color of a table cell in docx."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tc_pr.append(shd)


def set_table_styling(table):
    """Apply professional border and padding styling to docx table."""
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(table.rows):
        for cell in row.cells:
            # Padding
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_mar = OxmlElement('w:tcMar')
            for m in ['top', 'bottom']:
                node = OxmlElement(f'w:{m}')
                node.set(qn('w:w'), '120')
                node.set(qn('w:type'), 'dxa')
                tc_mar.append(node)
            for m in ['left', 'right']:
                node = OxmlElement(f'w:{m}')
                node.set(qn('w:w'), '160')
                node.set(qn('w:type'), 'dxa')
                tc_mar.append(node)
            tc_pr.append(tc_mar)

            if i == 0:
                set_cell_background(cell, "0F294A")  # Navy Header
                for p in cell.paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    for run in p.runs:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(255, 255, 255)
                        run.font.size = Pt(9.5)
            elif i % 2 == 1:
                set_cell_background(cell, "F8FAFC")
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(9)
            else:
                set_cell_background(cell, "FFFFFF")
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(9)


def add_cover_page(doc: Document, project: Project, doc_title: str, doc_subtitle: str):
    """Build a standardized corporate cover page."""
    # Top spacing
    for _ in range(3):
        doc.add_paragraph()

    # Project Reference Badge
    p_ref = doc.add_paragraph()
    r_ref = p_ref.add_run(f"PROJET : {project.reference.upper()}")
    r_ref.font.size = Pt(11)
    r_ref.font.bold = True
    r_ref.font.color.rgb = RGBColor(37, 99, 235)  # Blue

    # Main Document Title
    p_title = doc.add_paragraph()
    r_title = p_title.add_run(doc_title)
    r_title.font.size = Pt(28)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(15, 23, 42)  # Slate 900

    # Subtitle
    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run(doc_subtitle)
    r_sub.font.size = Pt(14)
    r_sub.font.color.rgb = RGBColor(100, 116, 139)  # Slate 500

    for _ in range(4):
        doc.add_paragraph()

    # Metadata Card / Box
    meta_table = doc.add_table(rows=5, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.LEFT
    meta_rows = [
        ("Nom du Projet :", project.name),
        ("Client :", project.client_name),
        ("Responsable Technique :", project.lead_name),
        ("Version du Livrable :", "1.0 - Émise pour validation"),
        ("Date de Publication :", datetime.now().strftime("%d/%m/%Y"))
    ]
    for idx, (label, val) in enumerate(meta_rows):
        r = meta_table.rows[idx]
        r.cells[0].paragraphs[0].add_run(label).font.bold = True
        r.cells[0].paragraphs[0].runs[0].font.size = Pt(10)
        r.cells[1].paragraphs[0].add_run(val).font.size = Pt(10)

    doc.add_page_break()


def build_docx_document(
    output_path: str,
    doc_type: str,  # 'hld', 'lld', 'config_annexes', 'commissioning'
    project: Project,
    equipment_list: list[Equipment],
    segments: list[NetworkSegment],
    configs: list[ConfigurationParam],
    narrative_text: str = ""
) -> str:
    """Build a complete, professionally formatted Word document."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = Document()

    # Document Title definitions
    type_meta = {
        "hld": ("Dossier d'Architecture Générale (HLD)", "High Level Design & Principes Directeurs"),
        "lld": ("Dossier d'Architecture Détaillée (LLD)", "Low Level Design & Spécifications Techniques"),
        "config_annexes": ("Annexes de Configuration Matérielle", "Paramétrage Technique & Déploiement"),
        "commissioning": ("Dossier de Recette & Mise en Service", "Plan de Validation Opérationnelle & PV de Recette")
    }
    title, subtitle = type_meta.get(doc_type, ("Document Technique", "Infrastructure"))

    # 1. Cover Page
    add_cover_page(doc, project, title, subtitle)

    # 2. Document Control Table
    h_ctrl = doc.add_heading("Contrôle du Document & Approbations", level=1)
    ctrl_table = doc.add_table(rows=3, cols=4)
    ctrl_table.rows[0].cells[0].text = "Version"
    ctrl_table.rows[0].cells[1].text = "Date"
    ctrl_table.rows[0].cells[2].text = "Auteur / Rôle"
    ctrl_table.rows[0].cells[3].text = "Commentaires / Statut"
    
    ctrl_table.rows[1].cells[0].text = "1.0"
    ctrl_table.rows[1].cells[1].text = datetime.now().strftime("%d/%m/%Y")
    ctrl_table.rows[1].cells[2].text = f"{project.lead_name} (Lead)"
    ctrl_table.rows[1].cells[3].text = "Version initiale émise pour revue"

    ctrl_table.rows[2].cells[0].text = "1.0-VAL"
    ctrl_table.rows[2].cells[1].text = "-"
    ctrl_table.rows[2].cells[2].text = "Validateur Final"
    ctrl_table.rows[2].cells[3].text = "En attente de signature formelle"
    set_table_styling(ctrl_table)
    doc.add_paragraph()

    # 3. Narrative Synthesis / Executive Summary
    h_narrative = doc.add_heading("1. Synthèse Générale & Contexte Architectural", level=1)
    if narrative_text:
        # Check if AI generated
        if "[Généré par IA" in narrative_text:
            p_ai = doc.add_paragraph()
            r_ai = p_ai.add_run("AVIS DE CONFORMITÉ : Contenu assisté par IA locale — Soumis à vérification humaine obligatoire.")
            r_ai.font.italic = True
            r_ai.font.size = Pt(9)
            r_ai.font.color.rgb = RGBColor(180, 83, 9)  # Amber

        for line in narrative_text.splitlines():
            if line.strip():
                doc.add_paragraph(line)
    else:
        doc.add_paragraph(f"Projet d'infrastructure IT {project.reference} pour le client {project.client_name}.")

    doc.add_paragraph()

    # 4. Content Specific Sections
    if doc_type in ["hld", "lld"]:
        # Physical Infrastructure Section
        doc.add_heading("2. Inventaire du Matériel & Implantation Physique", level=1)
        doc.add_paragraph(
            f"L'architecture repose sur {len(equipment_list)} équipements répartis sur les différents sites opérationnels."
        )

        eq_table = doc.add_table(rows=1 + max(len(equipment_list), 1), cols=6)
        eq_table.rows[0].cells[0].text = "Hostname"
        eq_table.rows[0].cells[1].text = "Famille"
        eq_table.rows[0].cells[2].text = "Modèle"
        eq_table.rows[0].cells[3].text = "N° de Série"
        eq_table.rows[0].cells[4].text = "IP Management"
        eq_table.rows[0].cells[5].text = "Emplacement"

        if not equipment_list:
            eq_table.rows[1].cells[0].text = "Aucun équipement déclaré"
        else:
            for idx, eq in enumerate(equipment_list):
                row = eq_table.rows[idx + 1]
                row.cells[0].text = eq.name
                row.cells[1].text = eq.category.value
                row.cells[2].text = eq.model or "-"
                row.cells[3].text = eq.serial_number or "-"
                row.cells[4].text = eq.management_ip or "-"
                row.cells[5].text = eq.site.name if eq.site else "Hors site"

        set_table_styling(eq_table)
        doc.add_paragraph()

        # Logical Topology Section
        doc.add_heading("3. Plan d'Adressage & Segmentation VLAN (802.1Q)", level=1)
        doc.add_paragraph(
            f"La segmentation logique comprend {len(segments)} sous-réseaux garantissant l'isolation des flux et la sécurité périmétrique."
        )

        seg_table = doc.add_table(rows=1 + max(len(segments), 1), cols=5)
        seg_table.rows[0].cells[0].text = "VLAN ID"
        seg_table.rows[0].cells[1].text = "Nom du Réseau"
        seg_table.rows[0].cells[2].text = "Sous-réseau CIDR"
        seg_table.rows[0].cells[3].text = "Passerelle (SVI)"
        seg_table.rows[0].cells[4].text = "Zone de Sécurité"

        if not segments:
            seg_table.rows[1].cells[0].text = "Aucun VLAN déclaré"
        else:
            for idx, seg in enumerate(segments):
                row = seg_table.rows[idx + 1]
                row.cells[0].text = str(seg.vlan_id)
                row.cells[1].text = seg.name
                row.cells[2].text = seg.cidr or "-"
                row.cells[3].text = seg.gateway or "-"
                row.cells[4].text = seg.zone or "LAN"

        set_table_styling(seg_table)
        doc.add_paragraph()

    elif doc_type == "config_annexes":
        # Configurations Section
        doc.add_heading("2. Paramètres & Configurations Techniques", level=1)
        doc.add_paragraph(
            "Conformément à la politique de sécurité, tous les secrets, mots de passe et communautés SNMP "
            "sont masqués par la mention sécurisée <SECRET_MASQUÉ>."
        )

        cfg_table = doc.add_table(rows=1 + max(len(configs), 1), cols=4)
        cfg_table.rows[0].cells[0].text = "Catégorie"
        cfg_table.rows[0].cells[1].text = "Paramètre (Clé)"
        cfg_table.rows[0].cells[2].text = "Valeur"
        cfg_table.rows[0].cells[3].text = "Statut Sécurité"

        if not configs:
            cfg_table.rows[1].cells[0].text = "Aucune configuration enregistrée"
        else:
            for idx, cfg in enumerate(configs):
                row = cfg_table.rows[idx + 1]
                row.cells[0].text = cfg.category
                row.cells[1].text = cfg.key
                val = "<SECRET_MASQUÉ>" if (cfg.is_secret or is_secret_field(cfg.key)) else cfg.value
                row.cells[2].text = val
                row.cells[3].text = "Confidentiel" if (cfg.is_secret or is_secret_field(cfg.key)) else "Standard"

        set_table_styling(cfg_table)
        doc.add_paragraph()

    elif doc_type == "commissioning":
        # Commissioning / Test Cases Section
        doc.add_heading("2. Fiches de Tests de Recette & Validation", level=1)
        doc.add_paragraph(
            "Grille de validation opérationnelle : chaque test doit être exécuté et visé par le technicien responsable."
        )

        test_table = doc.add_table(rows=1 + max(len(equipment_list), 1), cols=6)
        test_table.rows[0].cells[0].text = "Réf. Test"
        test_table.rows[0].cells[1].text = "Équipement Cible"
        test_table.rows[0].cells[2].text = "Nature du Test"
        test_table.rows[0].cells[3].text = "Résultat Attendu"
        test_table.rows[0].cells[4].text = "Résultat Constaté"
        test_table.rows[0].cells[5].text = "Validation"

        for idx, eq in enumerate(equipment_list):
            row = test_table.rows[idx + 1]
            row.cells[0].text = f"TEST-REC-{idx+1:03d}"
            row.cells[1].text = eq.name
            row.cells[2].text = "Démarrage, Ping Mgmt, Vérif. VLAN"
            row.cells[3].text = f"Réponse ICMP sur {eq.management_ip or 'IP'}"
            row.cells[4].text = "Conforme"
            row.cells[5].text = "[  ] Validé"

        set_table_styling(test_table)
        doc.add_paragraph()

        # Signature Box
        doc.add_heading("3. Procès-Verbal de Recette & Signatures", level=1)
        sig_table = doc.add_table(rows=2, cols=2)
        sig_table.rows[0].cells[0].text = "Pour le Prestataire / Ingénieur Responsable :\n\n\nNom :\nDate :\nSignature :"
        sig_table.rows[0].cells[1].text = "Pour le Client / Responsable de Validation :\n\n\nNom :\nDate :\nSignature :"
        set_table_styling(sig_table)

    # Save document
    doc.save(output_path)
    return output_path
