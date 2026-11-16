"""
Generate SpatialSight Project Abstract Document (.docx & .pdf)
Strictly conforming to SRM Department of Physics & Nanotechnology Techknow Model Abstract Format.
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

def build_abstract(
    output_docx="SpatialSight_Project_Abstract.docx",
    project_title="SPATIALSIGHT: SENSOR-GUIDED OBJECT DETECTION & ADAPTIVE COLLISION AVOIDANCE SYSTEM",
    department="B.TECH BIOMEDICAL ENGINEERING  B SECTION",
    group_label="Group Members (Group 1)",
    group_members="NANDHINI SHARAB - RA2611060010001; FIDA FATHIMA - RA2611060010002; D. JAIRUS SAM - RA2611060010003; ANAS HABIBULLAH - RA2611060010004; SALONI SHANKAR - RA2611060010005; MUSKAN - RA2611060010006",
    faculty_name="DR. A. GEETHA",
    faculty_dept="Department of Physics and Nanotechnology, College of Engineering & Technology,",
    institution="SRM Institute of Science and Technology, Kattankulathur, Chengalpattu Dt, Tamil Nadu",
    image_path=None
):
    doc = docx.Document()
    sec = doc.sections[0]
    sec.page_width = Inches(8.5)
    sec.page_height = Inches(11.0)
    sec.top_margin = Inches(0.7)
    sec.bottom_margin = Inches(0.7)
    sec.left_margin = Inches(0.85)
    sec.right_margin = Inches(0.85)

    def add_p(text, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2, bold=False, size=11, line_sp=1.15):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = line_sp
        r = p.add_run(text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(size)
        r.bold = bold
        return p

    # 1. Project Title
    add_p(project_title, space_after=3, bold=True, size=14)

    # 2. Branch & Section
    add_p(department, space_after=3, bold=True, size=11)

    # 3. Group Members Header
    add_p(group_label, space_after=2, bold=True, size=11)

    # 4. Group Members
    add_p(group_members, space_after=3, bold=True, size=10.5)

    # 5. College Details
    add_p("College of Engineering & Technology,", space_after=0, bold=False, size=11, line_sp=1.1)
    add_p(institution, space_after=4, bold=False, size=11, line_sp=1.1)

    # 6. Faculty Incharge
    add_p("FACULTY INCHARGE", space_after=1, bold=True, size=11)
    add_p(faculty_name, space_after=1, bold=True, size=11)
    add_p(faculty_dept, space_after=0, bold=False, size=11, line_sp=1.1)
    add_p(institution, space_after=5, bold=False, size=11, line_sp=1.1)

    # 7. Summary Paragraph
    p_sum = doc.add_paragraph()
    p_sum.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_sum.paragraph_format.space_before = Pt(0)
    p_sum.paragraph_format.space_after = Pt(4)
    p_sum.paragraph_format.line_spacing = 1.15

    r_sum_lbl = p_sum.add_run("Summary: ")
    r_sum_lbl.font.name = 'Times New Roman'
    r_sum_lbl.font.size = Pt(11)
    r_sum_lbl.bold = True

    summary_text = (
        "This project demonstrates 'SpatialSight ADAS', an intelligent, sensor-guided object detection and collision avoidance "
        "system that couples real-time optical computer vision with environmental physics sensor fusion. A mobile Android device "
        "serves as an active optical and inertial sensor node, capturing 720p video at 30 FPS along with 3-axis rotation vector "
        "telemetry (\u03b8, \u03c6, \u03c8) from embedded gyroscopic sensors, transmitted over a low-latency USB-C bridge (<25 ms) to a host machine. "
        "A high-performance YOLO neural inference engine processes video streams at 60 FPS, extracting bounding boxes, monocular distance "
        "approximations, and relative approach velocities. Crucially, the system incorporates an Arduino Uno interfacing with an analog surface "
        "rain and moisture sensor to dynamically calculate real-time roadway physics. Applying principles of mechanics and tribology, the system "
        "evaluates surface friction (\u03bc), which degrades from dry asphalt (\u03bc \u2248 0.80) to wet conditions (\u03bc \u2248 0.35). Using the kinematic stopping "
        "distance formula s = v\u00b2 / (2\u03bcg) and kinetic energy equations (KE = \u00bdmv\u00b2), the system dynamically scales the emergency collision "
        "warning zone by up to 2.3\u00d7 under adverse weather. When a hazard breaches the safe stopping perimeter, the host computer signals the Arduino "
        "to actuate a tri-color hardware traffic indicator (Green \u2192 Yellow \u2192 Red) and trigger emergency audio braking alerts. Additionally, a "
        "spatial room mapping mode utilizes sensor-guided angular binning to eliminate redundant object tallies during 360\u00b0 sweeps. Operating "
        "entirely offline, SpatialSight highlights a cost-effective, practical implementation of physics-guided machine vision for vehicular safety."
    )
    r_sum_txt = p_sum.add_run(summary_text)
    r_sum_txt.font.name = 'Times New Roman'
    r_sum_txt.font.size = Pt(11)

    # 8. Embedded Diagram
    if image_path and os.path.exists(image_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(3)
        p_img.paragraph_format.space_after = Pt(2)
        p_img.add_run().add_picture(image_path, width=Inches(2.5), height=Inches(2.5))

    # 9. Caption
    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(1)
    p_cap.paragraph_format.space_after = Pt(0)
    r_cap_lbl = p_cap.add_run("Figure. ")
    r_cap_lbl.font.name = 'Times New Roman'
    r_cap_lbl.font.size = Pt(10)
    r_cap_lbl.bold = True
    r_cap_txt = p_cap.add_run("AI-generated 3D architectural model and physics sensor-fusion pipeline of the SpatialSight system.")
    r_cap_txt.font.name = 'Times New Roman'
    r_cap_txt.font.size = Pt(10)

    doc.save(output_docx)
    print(f"[OK] Document generated at: {output_docx}")

if __name__ == "__main__":
    img = "/Users/sanagariudbhav/.gemini/antigravity/brain/a87d9c18-819b-4fd5-8542-8ef1b1d33356/spatialsight_system_model_1790704213692.jpg"
    build_abstract(image_path=img)
