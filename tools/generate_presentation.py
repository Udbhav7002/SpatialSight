"""
generate_presentation.py
Generates the 10-slide PowerPoint presentation (.pptx) for SpatialSight:
Sensor-Guided Object Detection & Adaptive Collision Avoidance System.
Strictly customized for Techknow / SRM IST Physics & Nanotechnology project evaluation.
"""

import os
from PIL import Image
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

# ---------------------------------------------------------
# CONSTANTS & PALETTE
# ---------------------------------------------------------
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

# Colors
C_DARK_BG = RGBColor(15, 23, 42)        # Slate 900
C_DARK_SURFACE = RGBColor(30, 41, 59)   # Slate 800
C_DARK_CARD = RGBColor(39, 53, 76)      # Slate 700/800
C_LIGHT_BG = RGBColor(248, 250, 252)    # Slate 50
C_WHITE = RGBColor(255, 255, 255)
C_CARD_BG = RGBColor(255, 255, 255)
C_CARD_BORDER = RGBColor(226, 232, 240) # Slate 200

C_PRIMARY = RGBColor(14, 116, 144)      # Cyan 700
C_ACCENT_BLUE = RGBColor(2, 132, 199)   # Sky 600
C_ACCENT_CYAN = RGBColor(6, 182, 212)   # Cyan 500
C_NAVY_TEXT = RGBColor(15, 23, 42)      # Deep Navy
C_BODY_TEXT = RGBColor(51, 65, 85)      # Slate 700
C_MUTED_TEXT = RGBColor(100, 116, 139)  # Slate 500

C_ALERT_GREEN = RGBColor(22, 163, 74)   # Green 600
C_ALERT_YELLOW = RGBColor(217, 119, 6)  # Amber 600
C_ALERT_RED = RGBColor(220, 38, 38)     # Red 600

FONT_MAIN = "Helvetica"
FONT_CODE = "Courier New"


def create_presentation():
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    blank_layout = prs.slide_layouts[6]

    def set_slide_bg(slide, color):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT)
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        return bg

    def add_header(slide, category_tag, title_text, subtitle_text):
        # Header banner text container
        tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(1.15))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        # Category pill / label
        p_tag = tf.paragraphs[0]
        p_tag.space_after = Pt(2)
        r_tag = p_tag.add_run()
        r_tag.text = category_tag.upper()
        r_tag.font.name = FONT_MAIN
        r_tag.font.size = Pt(9.5)
        r_tag.font.bold = True
        r_tag.font.color.rgb = C_PRIMARY

        # Title
        p_title = tf.add_paragraph()
        p_title.space_after = Pt(2)
        r_title = p_title.add_run()
        r_title.text = title_text
        r_title.font.name = FONT_MAIN
        r_title.font.size = Pt(21)
        r_title.font.bold = True
        r_title.font.color.rgb = C_NAVY_TEXT

        # Subtitle
        p_sub = tf.add_paragraph()
        r_sub = p_sub.add_run()
        r_sub.text = subtitle_text
        r_sub.font.name = FONT_MAIN
        r_sub.font.size = Pt(11)
        r_sub.font.color.rgb = C_MUTED_TEXT

    def add_footer(slide, slide_num):
        tb = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.733), Inches(0.35))
        tf = tb.text_frame
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        
        r1 = p.add_run()
        r1.text = "SPATIALSIGHT · B.Tech Biomedical Engineering (Group 1) · SRM IST"
        r1.font.name = FONT_MAIN
        r1.font.size = Pt(9)
        r1.font.color.rgb = C_MUTED_TEXT
        
        # Add slide number right aligned
        p.alignment = PP_ALIGN.LEFT
        tb_num = slide.shapes.add_textbox(Inches(10.5), Inches(7.05), Inches(2.0), Inches(0.35))
        tf_num = tb_num.text_frame
        tf_num.margin_left = tf_num.margin_top = tf_num.margin_right = tf_num.margin_bottom = 0
        p_num = tf_num.paragraphs[0]
        p_num.alignment = PP_ALIGN.RIGHT
        r_num = p_num.add_run()
        r_num.text = f"Slide {slide_num} of 10"
        r_num.font.name = FONT_MAIN
        r_num.font.size = Pt(9)
        r_num.font.bold = True
        r_num.font.color.rgb = C_PRIMARY

    def add_fitted_image(slide, image_path, left, top, max_w, max_h, border_color=None):
        if not os.path.exists(image_path):
            return None
        im = Image.open(image_path)
        img_w, img_h = im.size
        ratio = img_w / img_h
        box_ratio = max_w / max_h

        if ratio > box_ratio:
            final_w = max_w
            final_h = max_w / ratio
        else:
            final_h = max_h
            final_w = max_h * ratio

        final_left = left + (max_w - final_w) / 2
        final_top = top + (max_h - final_h) / 2

        # Optional subtle border container
        if border_color:
            bg_rect = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, 
                final_left - Inches(0.04), 
                final_top - Inches(0.04), 
                final_w + Inches(0.08), 
                final_h + Inches(0.08)
            )
            bg_rect.fill.solid()
            bg_rect.fill.fore_color.rgb = C_WHITE
            bg_rect.line.color.rgb = border_color
            bg_rect.line.width = Pt(1)

        pic = slide.shapes.add_picture(image_path, final_left, final_top, final_w, final_h)
        return pic

    # =========================================================================
    # SLIDE 1: TITLE & TEAM INTRO (Dark Executive Theme)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s1, C_DARK_BG)

    # Accent decorative glow bar
    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.8), Inches(0.12), Inches(5.9))
    bar.fill.solid()
    bar.fill.fore_color.rgb = C_ACCENT_CYAN
    bar.line.fill.background()

    # Title Container
    tb1 = s1.shapes.add_textbox(Inches(1.2), Inches(0.7), Inches(7.2), Inches(2.5))
    tf1 = tb1.text_frame
    tf1.word_wrap = True

    p_badge = tf1.paragraphs[0]
    p_badge.space_after = Pt(6)
    r_badge = p_badge.add_run()
    r_badge.text = "SRM IST · TECHKNOW 2026 · MODEL PROJECT EXHIBITION"
    r_badge.font.name = FONT_MAIN
    r_badge.font.size = Pt(10)
    r_badge.font.bold = True
    r_badge.font.color.rgb = C_ACCENT_CYAN

    p_main_title = tf1.add_paragraph()
    p_main_title.space_after = Pt(4)
    r_main_title = p_main_title.add_run()
    r_main_title.text = "SPATIALSIGHT"
    r_main_title.font.name = FONT_MAIN
    r_main_title.font.size = Pt(36)
    r_main_title.font.bold = True
    r_main_title.font.color.rgb = C_WHITE

    p_sub_title = tf1.add_paragraph()
    p_sub_title.space_after = Pt(6)
    r_sub_title = p_sub_title.add_run()
    r_sub_title.text = "Sensor-Guided Object Detection & Adaptive Collision Avoidance System"
    r_sub_title.font.name = FONT_MAIN
    r_sub_title.font.size = Pt(14)
    r_sub_title.font.bold = True
    r_sub_title.font.color.rgb = RGBColor(148, 163, 184) # Slate 400

    p_desc = tf1.add_paragraph()
    r_desc = p_desc.add_run()
    r_desc.text = "A physics-guided, ultra-low-budget ADAS integrating optical neural vision, 3-axis inertial motion telemetry, and real-time roadway tribology."
    r_desc.font.name = FONT_MAIN
    r_desc.font.size = Pt(11)
    r_desc.font.color.rgb = RGBColor(203, 213, 225) # Slate 300

    # Team Members Card
    team_card = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(3.3), Inches(4.3), Inches(3.4))
    team_card.fill.solid()
    team_card.fill.fore_color.rgb = C_DARK_SURFACE
    team_card.line.color.rgb = RGBColor(51, 65, 85)
    tf_team = team_card.text_frame
    tf_team.margin_left = Inches(0.2)
    tf_team.margin_right = Inches(0.2)
    tf_team.margin_top = Inches(0.18)

    p_th = tf_team.paragraphs[0]
    p_th.space_after = Pt(6)
    r_th = p_th.add_run()
    r_th.text = "GROUP MEMBERS (GROUP 1)"
    r_th.font.name = FONT_MAIN
    r_th.font.size = Pt(10)
    r_th.font.bold = True
    r_th.font.color.rgb = C_ACCENT_CYAN

    members = [
        ("NANDHINI SHARAB", "RA2611060010001"),
        ("FIDA FATHIMA", "RA2611060010002"),
        ("D. JAIRUS SAM", "RA2611060010003"),
        ("ANAS HABIBULLAH", "RA2611060010004"),
        ("SALONI SHANKAR", "RA2611060010005"),
        ("MUSKAN", "RA2611060010006")
    ]
    for name, roll in members:
        p_m = tf_team.add_paragraph()
        p_m.space_after = Pt(2)
        r_n = p_m.add_run()
        r_n.text = f"•  {name} "
        r_n.font.name = FONT_MAIN
        r_n.font.size = Pt(9.5)
        r_n.font.bold = True
        r_n.font.color.rgb = C_WHITE
        r_r = p_m.add_run()
        r_r.text = f"—  {roll}"
        r_r.font.name = FONT_MAIN
        r_r.font.size = Pt(9)
        r_r.font.color.rgb = RGBColor(148, 163, 184)

    # Department & Guide Card
    dept_card = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.65), Inches(3.3), Inches(2.75), Inches(3.4))
    dept_card.fill.solid()
    dept_card.fill.fore_color.rgb = C_DARK_SURFACE
    dept_card.line.color.rgb = RGBColor(51, 65, 85)
    tf_dept = dept_card.text_frame
    tf_dept.margin_left = Inches(0.2)
    tf_dept.margin_right = Inches(0.2)
    tf_dept.margin_top = Inches(0.18)

    p_dh = tf_dept.paragraphs[0]
    p_dh.space_after = Pt(4)
    r_dh = p_dh.add_run()
    r_dh.text = "ACADEMIC DETAILS"
    r_dh.font.name = FONT_MAIN
    r_dh.font.size = Pt(10)
    r_dh.font.bold = True
    r_dh.font.color.rgb = C_ACCENT_CYAN

    p_d1 = tf_dept.add_paragraph()
    p_d1.space_after = Pt(8)
    r_d1 = p_d1.add_run()
    r_d1.text = "Department:\nB.Tech Biomedical Engineering\nSection: B Section"
    r_d1.font.name = FONT_MAIN
    r_d1.font.size = Pt(9)
    r_d1.font.color.rgb = RGBColor(226, 232, 240)

    p_gh = tf_dept.add_paragraph()
    p_gh.space_after = Pt(2)
    r_gh = p_gh.add_run()
    r_gh.text = "FACULTY IN-CHARGE"
    r_gh.font.name = FONT_MAIN
    r_gh.font.size = Pt(9.5)
    r_gh.font.bold = True
    r_gh.font.color.rgb = C_ACCENT_CYAN

    p_g1 = tf_dept.add_paragraph()
    p_g1.space_after = Pt(6)
    r_g1 = p_g1.add_run()
    r_g1.text = "DR. A. GEETHA\nDept. of Physics & Nanotechnology\nCollege of Engg. & Technology\nSRM IST, Kattankulathur"
    r_g1.font.name = FONT_MAIN
    r_g1.font.size = Pt(8.5)
    r_g1.font.color.rgb = RGBColor(203, 213, 225)

    # Hero Visual Image
    hero_img = "assets/spatialsight_system_model.jpg"
    if not os.path.exists(hero_img):
        hero_img = "assets/extracted_slide_assets/img-000.png"
    add_fitted_image(s1, hero_img, Inches(8.6), Inches(1.0), Inches(4.0), Inches(5.6), border_color=RGBColor(51, 65, 85))

    # =========================================================================
    # SLIDE 2: PROBLEM STATEMENT & MOTIVATION
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s2, C_LIGHT_BG)
    add_header(s2, "Background & Motivation", "The Road Safety Crisis & The High Cost of ADAS",
               "Why conventional collision avoidance systems fail in affordability, low latency, and weather adaptability")
    add_footer(s2, 2)

    # 3 Column Cards on Left/Center
    card_w = Inches(3.6)
    card_h = Inches(4.9)
    
    # Card 1: Adverse Weather Problem
    c1 = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), card_w, card_h)
    c1.fill.solid()
    c1.fill.fore_color.rgb = C_WHITE
    c1.line.color.rgb = C_CARD_BORDER
    tf_c1 = c1.text_frame
    tf_c1.margin_left = tf_c1.margin_right = Inches(0.25)
    tf_c1.margin_top = Inches(0.25)

    p = tf_c1.paragraphs[0]
    p.space_after = Pt(6)
    r = p.add_run()
    r.text = "1. Wet-Road Collision Crisis"
    r.font.name = FONT_MAIN
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_ALERT_RED

    bullets_c1 = [
        ("24% of Crashes in Rain:", "Over 24% of all highway crashes occur during rain and wet road conditions due to unrecognized friction loss."),
        ("50%+ Traction Loss:", "Tire-road friction coefficient drops from dry asphalt (μ ≈ 0.80) to wet pavement (μ ≈ 0.35), doubling stopping distance."),
        ("Blind Braking Systems:", "Current camera-only systems assume static stopping distances and fail to react when roads are slick.")
    ]
    for b_title, b_desc in bullets_c1:
        p = tf_c1.add_paragraph()
        p.space_after = Pt(8)
        r = p.add_run()
        r.text = f"• {b_title} "
        r.font.name = FONT_MAIN
        r.font.size = Pt(10)
        r.font.bold = True
        r.font.color.rgb = C_NAVY_TEXT
        r2 = p.add_run()
        r2.text = b_desc
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_BODY_TEXT

    # Card 2: Expensive Commercial ADAS
    c2 = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.65), Inches(1.8), card_w, card_h)
    c2.fill.solid()
    c2.fill.fore_color.rgb = C_WHITE
    c2.line.color.rgb = C_CARD_BORDER
    tf_c2 = c2.text_frame
    tf_c2.margin_left = tf_c2.margin_right = Inches(0.25)
    tf_c2.margin_top = Inches(0.25)

    p = tf_c2.paragraphs[0]
    p.space_after = Pt(6)
    r = p.add_run()
    r.text = "2. Cost Prohibitive LiDAR / Radar"
    r.font.name = FONT_MAIN
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_ALERT_YELLOW

    bullets_c2 = [
        ("Exorbitant Hardware Cost:", "Commercial automotive LiDAR units cost ₹4,00,000 to ₹10,00,000+ ($5k-$12k). Dedicated radar adds thousands more."),
        ("Restricted to Luxury Cars:", "Due to high cost, over 85% of commuter vehicles, 2-wheelers, and college testbeds have zero active ADAS."),
        ("Need for Low-Budget Safety:", "A desperate need exists for an affordable system using off-the-shelf consumer sensors costing <₹3,500 ($40).")
    ]
    for b_title, b_desc in bullets_c2:
        p = tf_c2.add_paragraph()
        p.space_after = Pt(8)
        r = p.add_run()
        r.text = f"• {b_title} "
        r.font.name = FONT_MAIN
        r.font.size = Pt(10)
        r.font.bold = True
        r.font.color.rgb = C_NAVY_TEXT
        r2 = p.add_run()
        r2.text = b_desc
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_BODY_TEXT

    # Card 3: Cloud Vision & Latency Bottleneck
    c3 = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.5), Inches(1.8), card_w, card_h)
    c3.fill.solid()
    c3.fill.fore_color.rgb = C_WHITE
    c3.line.color.rgb = C_CARD_BORDER
    tf_c3 = c3.text_frame
    tf_c3.margin_left = tf_c3.margin_right = Inches(0.25)
    tf_c3.margin_top = Inches(0.25)

    p = tf_c3.paragraphs[0]
    p.space_after = Pt(6)
    r = p.add_run()
    r.text = "3. Cloud Latency & Privacy Flaws"
    r.font.name = FONT_MAIN
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_PRIMARY

    bullets_c3 = [
        ("Dangerous Latency:", "Cloud vision APIs (AWS / Google Vision) require 400ms–1500ms network roundtrips. At 60 km/h, a car moves 25m blind."),
        ("Cellular Dependency:", "Tunnels, rural highways, and bad weather sever internet connectivity, shutting down cloud-based driver safety."),
        ("SpatialSight Offline Fix:", "100% offline local edge processing via high-speed USB-C bridge (<25ms latency) ensures reliable real-time protection.")
    ]
    for b_title, b_desc in bullets_c3:
        p = tf_c3.add_paragraph()
        p.space_after = Pt(8)
        r = p.add_run()
        r.text = f"• {b_title} "
        r.font.name = FONT_MAIN
        r.font.size = Pt(10)
        r.font.bold = True
        r.font.color.rgb = C_NAVY_TEXT
        r2 = p.add_run()
        r2.text = b_desc
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_BODY_TEXT

    # =========================================================================
    # SLIDE 3: SYSTEM PREMISE & SENSOR FUSION
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s3, C_LIGHT_BG)
    add_header(s3, "System Premise & Innovation", "SpatialSight: Fusing Machine Vision with Roadway Physics",
               "Real-time object detection alone cannot prevent crashes without understanding road friction, inertia, and stopping kinetics")
    add_footer(s3, 3)

    # Left Side: 3 Tri-Pillar Architecture Cards
    left_w = Inches(7.2)
    
    pillars = [
        ("Pillar 1: Optical Neural Vision (YOLOv8 @ 60 FPS)",
         "Monocular camera capture on Android phone processes at 60 FPS on edge compute. Localizes vehicles, pedestrians, cycles, and obstacles with optical pinhole distance estimation (Z = f·H/h).",
         C_ACCENT_BLUE),
        ("Pillar 2: 3-Axis Inertial Motion Sensing (Gyroscopes @ 30 Hz)",
         "Android rotation vector sensor streams real-time roll, pitch, and yaw (θ, φ, ψ). Tracks phone orientation to eliminate duplicate detections and build true 360° spatial awareness.",
         C_PRIMARY),
        ("Pillar 3: Environmental Road Physics (Arduino Sensor Integration)",
         "Analog moisture and rain sensors continuously monitor pavement wetness. Dynamically updates friction coefficient (μ) to scale vehicle stopping distance formulas in real-time.",
         C_ALERT_GREEN)
    ]
    
    y_pos = Inches(1.8)
    for title, desc, color in pillars:
        p_card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), y_pos, left_w, Inches(1.5))
        p_card.fill.solid()
        p_card.fill.fore_color.rgb = C_WHITE
        p_card.line.color.rgb = C_CARD_BORDER
        tf_p = p_card.text_frame
        tf_p.margin_left = tf_p.margin_right = Inches(0.2)
        tf_p.margin_top = Inches(0.15)
        
        p = tf_p.paragraphs[0]
        p.space_after = Pt(3)
        r = p.add_run()
        r.text = title
        r.font.name = FONT_MAIN
        r.font.size = Pt(12)
        r.font.bold = True
        r.font.color.rgb = color
        
        p2 = tf_p.add_paragraph()
        r2 = p2.add_run()
        r2.text = desc
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_BODY_TEXT
        
        y_pos += Inches(1.65)

    # Right Side: Visual Diagram
    add_fitted_image(s3, "assets/extracted_slide_assets/img-005.png", Inches(8.3), Inches(1.8), Inches(4.2), Inches(4.9), border_color=C_CARD_BORDER)

    # =========================================================================
    # SLIDE 4: END-TO-END SYSTEM ARCHITECTURE
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s4, C_LIGHT_BG)
    add_header(s4, "System Architecture", "End-to-End System Architecture: Sensing to Actuation",
               "From mobile sensor acquisition to host neural inference and hardware alert actuation")
    add_footer(s4, 4)

    # 6 Step Pipeline Cards on Left
    steps_card = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(7.5), Inches(4.9))
    steps_card.fill.solid()
    steps_card.fill.fore_color.rgb = C_WHITE
    steps_card.line.color.rgb = C_CARD_BORDER
    tf_s = steps_card.text_frame
    tf_s.margin_left = tf_s.margin_right = Inches(0.25)
    tf_s.margin_top = Inches(0.2)

    p_sh = tf_s.paragraphs[0]
    p_sh.space_after = Pt(6)
    r_sh = p_sh.add_run()
    r_sh.text = "THE 6-LAYER DATA PROCESSING PIPELINE"
    r_sh.font.name = FONT_MAIN
    r_sh.font.size = Pt(11)
    r_sh.font.bold = True
    r_sh.font.color.rgb = C_PRIMARY

    pipeline_steps = [
        ("1. Android Mobile Node", "CameraX captures 720p @ 30 FPS. Gyroscopes capture 3-axis rotation telemetry. NanoHTTPD streams MJPEG & JSON over port 8080."),
        ("2. Low-Latency USB-C Bridge", "Tethered ADB TCP bridge (adb forward tcp:8080 tcp:8080) delivers sub-25ms latency with zero Wi-Fi dependence, charging phone concurrently."),
        ("3. Producer-Consumer Worker", "Multi-threaded host worker drops stale video frames; processes latest frame with YOLOv8 at 60 FPS on Apple Metal / CUDA."),
        ("4. Pinhole Optics & Trajectory", "Perspective driving corridor isolates obstacles; calculates monocular depth (Z) and closing speed (TTC)."),
        ("5. Arduino Environmental Bridge", "Reads analog road moisture sensor at 10 Hz; calculates road surface friction (μ) and dynamic stopping multiplier."),
        ("6. Hardware Alert Actuation", "Arduino triggers tri-color traffic LEDs (Green → Yellow → Red) and sounds an active piezo buzzer emergency braking alert.")
    ]

    for s_num, s_desc in pipeline_steps:
        p = tf_s.add_paragraph()
        p.space_after = Pt(4)
        r = p.add_run()
        r.text = f"{s_num}: "
        r.font.name = FONT_MAIN
        r.font.size = Pt(10)
        r.font.bold = True
        r.font.color.rgb = C_NAVY_TEXT
        r2 = p.add_run()
        r2.text = s_desc
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_BODY_TEXT

    # Right Side Graphic
    add_fitted_image(s4, "assets/extracted_slide_assets/img-008.png", Inches(8.6), Inches(1.8), Inches(3.9), Inches(4.9), border_color=C_CARD_BORDER)

    # =========================================================================
    # SLIDE 5: OPTICAL VISION & MONOCULAR DISTANCE
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s5, C_LIGHT_BG)
    add_header(s5, "Computer Vision & Kinematics", "Optical Neural Inference & Monocular Distance Estimation",
               "Extracting 3D forward distance and closing velocity from single 2D camera frames without expensive stereo rigs")
    add_footer(s5, 5)

    # Left Column: Neural Network & Corridor
    col1 = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.9))
    col1.fill.solid()
    col1.fill.fore_color.rgb = C_WHITE
    col1.line.color.rgb = C_CARD_BORDER
    tf_c1 = col1.text_frame
    tf_c1.margin_left = tf_c1.margin_right = Inches(0.25)
    tf_c1.margin_top = Inches(0.25)

    p = tf_c1.paragraphs[0]
    p.space_after = Pt(4)
    r = p.add_run()
    r.text = "YOLOv8 Edge Neural Engine"
    r.font.name = FONT_MAIN
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_PRIMARY

    v_points = [
        ("60 FPS Neural Inference:", "Optimized ultralytics YOLOv8n runs locally with MPS/Metal acceleration, achieving <8ms per-frame processing latency."),
        ("Multi-Class Road Detection:", "Classifies cars, trucks, motorcycles, bicycles, pedestrians, dogs, and roadway obstacles with high precision."),
        ("Trapezoidal Driving Corridor:", "Applies perspective road lane geometry to filter out parked roadside vehicles and focus strictly on collision hazards."),
        ("IoU Tracking & Velocity:", "Tracks object bounding boxes across consecutive frames using Intersection-over-Union (IoU) to compute approach speed.")
    ]
    for b_title, b_desc in v_points:
        p = tf_c1.add_paragraph()
        p.space_after = Pt(6)
        r = p.add_run()
        r.text = f"• {b_title} "
        r.font.name = FONT_MAIN
        r.font.size = Pt(10)
        r.font.bold = True
        r.font.color.rgb = C_NAVY_TEXT
        r2 = p.add_run()
        r2.text = b_desc
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_BODY_TEXT

    # Right Column: Optical Pinhole Mathematics
    col2 = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.7), Inches(1.8), Inches(5.8), Inches(4.9))
    col2.fill.solid()
    col2.fill.fore_color.rgb = C_WHITE
    col2.line.color.rgb = C_CARD_BORDER
    tf_c2 = col2.text_frame
    tf_c2.margin_left = tf_c2.margin_right = Inches(0.25)
    tf_c2.margin_top = Inches(0.25)

    p = tf_c2.paragraphs[0]
    p.space_after = Pt(4)
    r = p.add_run()
    r.text = "Optical Pinhole Distance Formulation"
    r.font.name = FONT_MAIN
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_ACCENT_BLUE

    # Formula Box
    p_f = tf_c2.add_paragraph()
    p_f.space_after = Pt(8)
    r_f = p_f.add_run()
    r_f.text = "Distance (Z) = (f · H_real) / h_bbox"
    r_f.font.name = FONT_CODE
    r_f.font.size = Pt(13)
    r_f.font.bold = True
    r_f.font.color.rgb = C_PRIMARY

    p_math = tf_c2.add_paragraph()
    p_math.space_after = Pt(6)
    r_math = p_math.add_run()
    r_math.text = "Where:\n" \
                  "• f = Calibrated focal length of mobile camera lens (~720px)\n" \
                  "• H_real = Real-world average object height (Car: 1.5m, Person: 1.7m, Bike: 1.2m)\n" \
                  "• h_bbox = Detected bounding box pixel height on frame\n\n" \
                  "Relative Velocity & Time-to-Collision (TTC):\n" \
                  "• v_rel = ΔZ / Δt  (rate of forward distance closure)\n" \
                  "• TTC = Z / v_rel  (seconds remaining until physical collision)\n\n" \
                  "Eliminates the requirement for expensive stereo camera baselines or power-hungry LiDAR sensors."
    r_math.font.name = FONT_MAIN
    r_math.font.size = Pt(9.5)
    r_math.font.color.rgb = C_BODY_TEXT

    # =========================================================================
    # SLIDE 6: ENVIRONMENTAL PHYSICS & TRIBOLOGY ENGINE
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s6, C_LIGHT_BG)
    add_header(s6, "Physics & Tribology", "Roadway Tribology & Dynamic Stopping Distance Physics",
               "Applying classical Newtonian mechanics and surface friction to evaluate dynamic collision severity")
    add_footer(s6, 6)

    # Left Side: Physics Formulas & Concept
    left_card = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(7.5), Inches(4.9))
    left_card.fill.solid()
    left_card.fill.fore_color.rgb = C_WHITE
    left_card.line.color.rgb = C_CARD_BORDER
    tf_l = left_card.text_frame
    tf_l.margin_left = tf_l.margin_right = Inches(0.25)
    tf_l.margin_top = Inches(0.25)

    p = tf_l.paragraphs[0]
    p.space_after = Pt(4)
    r = p.add_run()
    r.text = "1. Idealized Kinematic Stopping Distance Formula"
    r.font.name = FONT_MAIN
    r.font.size = Pt(12.5)
    r.font.bold = True
    r.font.color.rgb = C_PRIMARY

    p_f1 = tf_l.add_paragraph()
    p_f1.space_after = Pt(6)
    r_f1 = p_f1.add_run()
    r_f1.text = "s = v² / (2 · μ · g)"
    r_f1.font.name = FONT_CODE
    r_f1.font.size = Pt(14)
    r_f1.font.bold = True
    r_f1.font.color.rgb = C_ACCENT_BLUE

    p_f1_exp = tf_l.add_paragraph()
    p_f1_exp.space_after = Pt(10)
    r_f1_exp = p_f1_exp.add_run()
    r_f1_exp.text = "• v = Vehicle velocity (m/s) — stopping distance scales QUADRATICALLY (v²).\n" \
                    "• μ = Coefficient of friction — stopping distance is INVERSELY proportional (1/μ).\n" \
                    "• g = Acceleration due to gravity (9.81 m/s²)."
    r_f1_exp.font.name = FONT_MAIN
    r_f1_exp.font.size = Pt(9.5)
    r_f1_exp.font.color.rgb = C_BODY_TEXT

    p = tf_l.add_paragraph()
    p.space_after = Pt(4)
    r = p.add_run()
    r.text = "2. Kinetic Energy Dissipation (Collision Severity)"
    r.font.name = FONT_MAIN
    r.font.size = Pt(12.5)
    r.font.bold = True
    r.font.color.rgb = C_ALERT_RED

    p_f2 = tf_l.add_paragraph()
    p_f2.space_after = Pt(6)
    r_f2 = p_f2.add_run()
    r_f2.text = "KE = ½ · m · v²"
    r_f2.font.name = FONT_CODE
    r_f2.font.size = Pt(14)
    r_f2.font.bold = True
    r_f2.font.color.rgb = C_ALERT_RED

    p_f2_exp = tf_l.add_paragraph()
    r_f2_exp = p_f2_exp.add_run()
    r_f2_exp.text = "• A vehicle traveling at 60 km/h possesses 4× the kinetic energy of one at 30 km/h.\n" \
                    "• In wet weather (μ drops from 0.80 to 0.35), available braking force drops by 56%.\n" \
                    "• SpatialSight automatically detects surface water via Arduino and adjusts parameters before disaster occurs."
    r_f2_exp.font.name = FONT_MAIN
    r_f2_exp.font.size = Pt(9.5)
    r_f2_exp.font.color.rgb = C_BODY_TEXT

    # Right Side Graphic
    add_fitted_image(s6, "assets/extracted_slide_assets/img-015.png", Inches(8.6), Inches(1.8), Inches(3.9), Inches(4.9), border_color=C_CARD_BORDER)

    # =========================================================================
    # SLIDE 7: ADAPTIVE SAFETY PERIMETER & DYNAMIC WARNING
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s7, C_LIGHT_BG)
    add_header(s7, "Active Safety Perimeter", "Adaptive Collision Corridor: Expanding Warning Zones Up to 2.3×",
               "Real-time expansion of the forward safety perimeter based on environmental moisture telemetry")
    add_footer(s7, 7)

    # Left Column: Concept & Multiplier
    col1 = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(7.5), Inches(4.9))
    col1.fill.solid()
    col1.fill.fore_color.rgb = C_WHITE
    col1.line.color.rgb = C_CARD_BORDER
    tf_c1 = col1.text_frame
    tf_c1.margin_left = tf_c1.margin_right = Inches(0.25)
    tf_c1.margin_top = Inches(0.22)

    p = tf_c1.paragraphs[0]
    p.space_after = Pt(4)
    r = p.add_run()
    r.text = "Dynamic Stopping Distance Multiplier (M_stop)"
    r.font.name = FONT_MAIN
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = C_PRIMARY

    p_m = tf_c1.add_paragraph()
    p_m.space_after = Pt(6)
    r_m = p_m.add_run()
    r_m.text = "M_stop = μ_dry / μ_measured = 0.80 / 0.35 ≈ 2.29 ≈ 2.3×"
    r_m.font.name = FONT_CODE
    r_m.font.size = Pt(13)
    r_m.font.bold = True
    r_m.font.color.rgb = C_ACCENT_BLUE

    p_stages = tf_c1.add_paragraph()
    p_stages.space_after = Pt(4)
    r_s = p_stages.add_run()
    r_s.text = "Graduated 3-Color Active Alert Hierarchy:"
    r_s.font.name = FONT_MAIN
    r_s.font.size = Pt(11)
    r_s.font.bold = True
    r_s.font.color.rgb = C_NAVY_TEXT

    stages = [
        ("GREEN (Normal Safe Condition):", "Forward corridor is open. Obstacles are well outside safety stopping envelope (Z > s_wet · 1.5). Green signal active.", C_ALERT_GREEN),
        ("YELLOW (Advisory Pre-Crash Warning):", "Obstacle entered outer safety boundary. Amber LED active. Alerts driver to lift off throttle and prepare braking.", C_ALERT_YELLOW),
        ("RED (Critical Emergency Hazard):", "Safe stopping boundary breached (Z ≤ s_wet). Red LED flashes + emergency buzzer sounds. Immediate emergency braking required.", C_ALERT_RED)
    ]
    for st_title, st_desc, st_color in stages:
        p = tf_c1.add_paragraph()
        p.space_after = Pt(5)
        r = p.add_run()
        r.text = f"• {st_title} "
        r.font.name = FONT_MAIN
        r.font.size = Pt(9.5)
        r.font.bold = True
        r.font.color.rgb = st_color
        r2 = p.add_run()
        r2.text = st_desc
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9)
        r2.font.color.rgb = C_BODY_TEXT

    # Right Side Graphic
    add_fitted_image(s7, "assets/extracted_slide_assets/img-018.png", Inches(8.6), Inches(1.8), Inches(3.9), Inches(4.9), border_color=C_CARD_BORDER)

    # =========================================================================
    # SLIDE 8: BILL OF MATERIALS (BOM) & BUDGET ANALYSIS
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s8, C_LIGHT_BG)
    add_header(s8, "Budget & Feasibility Analysis", "Component Bill of Materials (BOM) & Cost Breakdown",
               "Demonstrating extreme affordability (<₹3,500 / $40) compared to commercial ₹5,00,000+ ADAS setups")
    add_footer(s8, 8)

    # Table Container
    table_shape = s8.shapes.add_table(8, 5, Inches(0.8), Inches(1.8), Inches(7.8), Inches(3.3))
    tbl = table_shape.table
    tbl.columns[0].width = Inches(2.3)
    tbl.columns[1].width = Inches(2.7)
    tbl.columns[2].width = Inches(0.7)
    tbl.columns[3].width = Inches(1.05)
    tbl.columns[4].width = Inches(1.05)

    headers = ["Component", "Specification / Function", "Qty", "Cost (INR)", "Cost (USD)"]
    for col_idx, h_text in enumerate(headers):
        cell = tbl.cell(0, col_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_DARK_BG
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if col_idx >= 2 else PP_ALIGN.LEFT
        r = p.add_run()
        r.text = h_text
        r.font.name = FONT_MAIN
        r.font.size = Pt(9.5)
        r.font.bold = True
        r.font.color.rgb = C_WHITE

    bom_rows = [
        ("Arduino Uno R3 / Nano", "Atmega328P Microcontroller & ADC interface", "1", "₹450", "$5.40"),
        ("Analog Rain / Moisture Sensor", "Nickel-plated water sensing board + LM393", "1", "₹120", "$1.45"),
        ("Tri-Color Traffic Signal LED", "Green / Yellow / Red 8mm alert board", "1", "₹80", "$0.95"),
        ("Piezo Buzzer Alarm Unit", "5V 85dB active collision warning buzzer", "1", "₹40", "$0.50"),
        ("USB-C 3.1 Data Cable", "High-speed tether (<25ms latency bridge)", "1", "₹200", "$2.40"),
        ("Prototyping Board & Jumpers", "Interconnect wiring & breadboard module", "1 set", "₹150", "$1.80"),
        ("TOTAL HARDWARE OUTLAY", "Complete functional working safety prototype", "6 units", "₹1,040", "$12.50")
    ]

    for row_idx, row_data in enumerate(bom_rows, start=1):
        is_total = (row_idx == len(bom_rows))
        for col_idx, cell_value in enumerate(row_data):
            cell = tbl.cell(row_idx, col_idx)
            cell.fill.solid()
            if is_total:
                cell.fill.fore_color.rgb = RGBColor(224, 242, 254) # Sky 100
            elif row_idx % 2 == 1:
                cell.fill.fore_color.rgb = C_WHITE
            else:
                cell.fill.fore_color.rgb = RGBColor(241, 245, 249) # Slate 100

            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER if col_idx >= 2 else PP_ALIGN.LEFT
            r = p.add_run()
            r.text = cell_value
            r.font.name = FONT_MAIN
            r.font.size = Pt(9)
            if is_total:
                r.font.bold = True
                r.font.color.rgb = C_PRIMARY
            else:
                r.font.color.rgb = C_NAVY_TEXT

    # Budget Callout Cards on Right
    comp_card = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.9), Inches(1.8), Inches(3.6), Inches(4.9))
    comp_card.fill.solid()
    comp_card.fill.fore_color.rgb = C_WHITE
    comp_card.line.color.rgb = C_CARD_BORDER
    tf_cmp = comp_card.text_frame
    tf_cmp.margin_left = tf_cmp.margin_right = Inches(0.2)
    tf_cmp.margin_top = Inches(0.2)

    p = tf_cmp.paragraphs[0]
    p.space_after = Pt(4)
    r = p.add_run()
    r.text = "Commercial Cost Comparison"
    r.font.name = FONT_MAIN
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = C_ALERT_GREEN

    comparisons = [
        ("Automotive LiDAR System:", "₹4,00,000 to ₹10,00,000+ ($5,000–$12,000)"),
        ("Commercial Radar Unit:", "₹75,000 to ₹2,00,000 ($900–$2,400)"),
        ("Aftermarket Mobileye ADAS:", "₹85,000 to ₹1,50,000 ($1,000–$1,800)"),
        ("SpatialSight Total Outlay:", "₹1,040 (~$12.50)")
    ]
    for c_title, c_val in comparisons:
        p = tf_cmp.add_paragraph()
        p.space_after = Pt(4)
        r = p.add_run()
        r.text = f"• {c_title}\n  "
        r.font.name = FONT_MAIN
        r.font.size = Pt(9)
        r.font.bold = True
        r.font.color.rgb = C_NAVY_TEXT
        r2 = p.add_run()
        r2.text = c_val
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.bold = True
        r2.font.color.rgb = C_PRIMARY if "SpatialSight" in c_title else C_BODY_TEXT

    p_sum = tf_cmp.add_paragraph()
    p_sum.space_after = Pt(4)
    r_sum = p_sum.add_run()
    r_sum.text = "\n> 98.5% Cost Reduction\n" \
                 "By repurposing student smartphones (camera + IMU) and laptops (inference), the system achieves full automotive ADAS functionality at pocket-money scale!"
    r_sum.font.name = FONT_MAIN
    r_sum.font.size = Pt(9)
    r_sum.font.color.rgb = C_BODY_TEXT

    # Lower takeaway banner on Slide 8
    b_banner = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.3), Inches(7.8), Inches(1.4))
    b_banner.fill.solid()
    b_banner.fill.fore_color.rgb = C_WHITE
    b_banner.line.color.rgb = C_CARD_BORDER
    tf_bb = b_banner.text_frame
    tf_bb.margin_left = tf_bb.margin_right = Inches(0.2)
    tf_bb.margin_top = Inches(0.12)
    p = tf_bb.paragraphs[0]
    r = p.add_run()
    r.text = "ECONOMIC FEASIBILITY & SOCIAL IMPACT:"
    r.font.name = FONT_MAIN
    r.font.size = Pt(9.5)
    r.font.bold = True
    r.font.color.rgb = C_PRIMARY
    p2 = tf_bb.add_paragraph()
    r2 = p2.add_run()
    r2.text = "In developing countries like India, expensive LiDAR ADAS will never be installed in low-cost two-wheelers or auto-rickshaws. SpatialSight proves that life-saving active safety can be retrofitted to any vehicle for less than the cost of a tank of fuel."
    r2.font.name = FONT_MAIN
    r2.font.size = Pt(9)
    r2.font.color.rgb = C_BODY_TEXT

    # =========================================================================
    # SLIDE 9: DUAL-MODE VERSATILITY & LIVE TESTING
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s9, C_LIGHT_BG)
    add_header(s9, "Capabilities & Validation", "Dual-Mode Flexibility, 360° Spatial Mapping & Validation",
               "Versatile operation across live driving ADAS and 360-degree spatial room inventory mapping")
    add_footer(s9, 9)

    # Left Column: Dual Modes
    col1 = s9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(7.5), Inches(4.9))
    col1.fill.solid()
    col1.fill.fore_color.rgb = C_WHITE
    col1.line.color.rgb = C_CARD_BORDER
    tf_c1 = col1.text_frame
    tf_c1.margin_left = tf_c1.margin_right = Inches(0.25)
    tf_c1.margin_top = Inches(0.2)

    p = tf_c1.paragraphs[0]
    p.space_after = Pt(4)
    r = p.add_run()
    r.text = "MODE 1: 360° Spatial Room Mapping (Zero Redundancy)"
    r.font.name = FONT_MAIN
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = C_PRIMARY

    p1 = tf_c1.add_paragraph()
    p1.space_after = Pt(8)
    r1 = p1.add_run()
    r1.text = "• Sensor-Guided Angular Binning: Snaps keyframes only when camera orientation rotates by ≥25°.\n" \
              "• Eliminates Duplicate Counts: If a chair is visible in 50 frames, it is cataloged exactly once in spatial coordinates.\n" \
              "• Produces 2D spatial layout maps and exact item inventory for robotics and smart rooms."
    r1.font.name = FONT_MAIN
    r1.font.size = Pt(9.5)
    r1.font.color.rgb = C_BODY_TEXT

    p = tf_c1.add_paragraph()
    p.space_after = Pt(4)
    r = p.add_run()
    r.text = "MODE 2: Live Forward Collision Avoidance (ADAS)"
    r.font.name = FONT_MAIN
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = C_ALERT_GREEN

    p2 = tf_c1.add_paragraph()
    p2.space_after = Pt(8)
    r2 = p2.add_run()
    r2.text = "• Continuous 60 FPS forward road monitoring with trapezoidal lane guidance.\n" \
              "• Dynamic friction multiplier (1.0× to 2.3×) automatically scales warning trigger distance.\n" \
              "• Direct serial transmission to Arduino actuates visual and audible alerts in <100ms."
    r2.font.name = FONT_MAIN
    r2.font.size = Pt(9.5)
    r2.font.color.rgb = C_BODY_TEXT

    p = tf_c1.add_paragraph()
    p.space_after = Pt(4)
    r = p.add_run()
    r.text = "Benchmarked System Performance"
    r.font.name = FONT_MAIN
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = C_NAVY_TEXT

    p3 = tf_c1.add_paragraph()
    r3 = p3.add_run()
    r3.text = "• USB-C Video Latency: <25 ms  |  YOLO Inference: 8 ms  |  Overall Reaction Time: <35 ms\n" \
              "• Network Dependency: 0% (Fully Offline)  |  Cloud Cost: ₹0.00 / $0.00"
    r3.font.name = FONT_MAIN
    r3.font.size = Pt(9)
    r3.font.bold = True
    r3.font.color.rgb = C_PRIMARY

    # Right Side Graphic: Spatial Mapping Radar
    add_fitted_image(s9, "assets/extracted_slide_assets/img-021.png", Inches(8.6), Inches(1.8), Inches(3.9), Inches(4.9), border_color=C_CARD_BORDER)

    # =========================================================================
    # SLIDE 10: CONCLUSION & THANK YOU NOTE (Dark Executive Theme)
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s10, C_DARK_BG)

    # Top Thank You Banner
    tb10 = s10.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.733), Inches(1.4))
    tf10 = tb10.text_frame
    tf10.word_wrap = True
    
    p = tf10.paragraphs[0]
    p.space_after = Pt(2)
    r = p.add_run()
    r.text = "SRM INSTITUTE OF SCIENCE AND TECHNOLOGY · DEPARTMENT OF PHYSICS & NANOTECHNOLOGY"
    r.font.name = FONT_MAIN
    r.font.size = Pt(9.5)
    r.font.bold = True
    r.font.color.rgb = C_ACCENT_CYAN

    p = tf10.add_paragraph()
    p.space_after = Pt(2)
    r = p.add_run()
    r.text = "Thank You!"
    r.font.name = FONT_MAIN
    r.font.size = Pt(32)
    r.font.bold = True
    r.font.color.rgb = C_WHITE

    p = tf10.add_paragraph()
    r = p.add_run()
    r.text = "SpatialSight: Sensor-Guided Object Detection & Adaptive Collision Avoidance System"
    r.font.name = FONT_MAIN
    r.font.size = Pt(13)
    r.font.color.rgb = RGBColor(148, 163, 184)

    # 3 Summary Cards
    col_w = Inches(3.6)
    
    # Card 1: Key Achievements
    c1 = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.1), col_w, Inches(4.5))
    c1.fill.solid()
    c1.fill.fore_color.rgb = C_DARK_SURFACE
    c1.line.color.rgb = RGBColor(51, 65, 85)
    tf_c1 = c1.text_frame
    tf_c1.margin_left = tf_c1.margin_right = Inches(0.2)
    tf_c1.margin_top = Inches(0.2)

    p = tf_c1.paragraphs[0]
    p.space_after = Pt(4)
    r = p.add_run()
    r.text = "Key Achievements"
    r.font.name = FONT_MAIN
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = C_ACCENT_CYAN

    achievements = [
        "Physics-Guided Vision: Successfully fused optical computer vision with dynamic roadway friction (μ).",
        "Adaptive Weather Safety: Scaled braking warning zones dynamically up to 2.3× under wet conditions.",
        "Ultra-Low Budget: Delivered a complete functional system for ₹1,040 (~$12.50), proving extreme affordability.",
        "Zero Cloud Latency: 100% offline edge execution (<25ms) protecting user data privacy."
    ]
    for ach in achievements:
        p = tf_c1.add_paragraph()
        p.space_after = Pt(6)
        r = p.add_run()
        r.text = f"- {ach}"
        r.font.name = FONT_MAIN
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(226, 232, 240)

    # Card 2: Future Scope
    c2 = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.65), Inches(2.1), col_w, Inches(4.5))
    c2.fill.solid()
    c2.fill.fore_color.rgb = C_DARK_SURFACE
    c2.line.color.rgb = RGBColor(51, 65, 85)
    tf_c2 = c2.text_frame
    tf_c2.margin_left = tf_c2.margin_right = Inches(0.2)
    tf_c2.margin_top = Inches(0.2)

    p = tf_c2.paragraphs[0]
    p.space_after = Pt(4)
    r = p.add_run()
    r.text = "Future Scope & Extensions"
    r.font.name = FONT_MAIN
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = C_ACCENT_BLUE

    future_scope = [
        "Vehicle CAN-Bus Integration: Direct interface to vehicle ECU for active automatic emergency braking (AEB).",
        "Night Vision Enhancement: Integration of low-cost thermal sensors for zero-light pedestrian protection.",
        "Two-Wheeler Deployment: Commercial casing for retrofitting onto motorcycles, e-scooters, and auto-rickshaws.",
        "Expanded Fleet Analytics: Aggregating edge friction telemetry to map municipal road slip hazards."
    ]
    for fs in future_scope:
        p = tf_c2.add_paragraph()
        p.space_after = Pt(6)
        r = p.add_run()
        r.text = f"→ {fs}"
        r.font.name = FONT_MAIN
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(226, 232, 240)

    # Card 3: Acknowledgments & Questions
    c3 = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.5), Inches(2.1), col_w, Inches(4.5))
    c3.fill.solid()
    c3.fill.fore_color.rgb = C_DARK_SURFACE
    c3.line.color.rgb = RGBColor(51, 65, 85)
    tf_c3 = c3.text_frame
    tf_c3.margin_left = tf_c3.margin_right = Inches(0.2)
    tf_c3.margin_top = Inches(0.2)

    p = tf_c3.paragraphs[0]
    p.space_after = Pt(4)
    r = p.add_run()
    r.text = "Special Acknowledgments"
    r.font.name = FONT_MAIN
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = C_ALERT_GREEN

    p_ack = tf_c3.add_paragraph()
    p_ack.space_after = Pt(8)
    r_ack = p_ack.add_run()
    r_ack.text = "We extend our deepest gratitude to our faculty supervisor:\n\n" \
                 "DR. A. GEETHA\n" \
                 "Department of Physics and Nanotechnology\n" \
                 "College of Engineering & Technology, SRM IST\n\n" \
                 "for her invaluable guidance, encouragement, and mentorship throughout the development of this project.\n\n" \
                 "We also thank our teachers, department evaluators, and peers for their continuous support."
    r_ack.font.name = FONT_MAIN
    r_ack.font.size = Pt(9)
    r_ack.font.color.rgb = RGBColor(203, 213, 225)

    p_q = tf_c3.add_paragraph()
    p_q.space_before = Pt(6)
    r_q = p_q.add_run()
    r_q.text = "QUESTIONS & ANSWERS\nWe welcome your feedback & questions!"
    r_q.font.name = FONT_MAIN
    r_q.font.size = Pt(10)
    r_q.font.bold = True
    r_q.font.color.rgb = C_ACCENT_CYAN

    # Save presentation
    output_pptx = "SpatialSight_Project_Presentation.pptx"
    prs.save(output_pptx)
    print(f"[SUCCESS] Presentation generated: {output_pptx}")
    return output_pptx

if __name__ == "__main__":
    create_presentation()
