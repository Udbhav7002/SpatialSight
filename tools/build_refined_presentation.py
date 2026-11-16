"""
build_refined_presentation.py
Rebuilds the entire 10-slide PowerPoint presentation with refined visual hierarchy,
unified dark executive theme, zero empty dead space, and pixel-perfect proportions.
"""

import os
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

# Unified High-Tech Dark Theme
C_BG = RGBColor(11, 17, 32)           # Midnight Slate 950 (#0B1120)
C_CARD_BG = RGBColor(22, 30, 49)      # Slate 900 (#161E31)
C_CARD_BG_ALT = RGBColor(30, 41, 59)  # Slate 800 (#1E293B)
C_BORDER = RGBColor(51, 65, 85)       # Slate 700 (#334155)

C_WHITE = RGBColor(255, 255, 255)
C_TITLE = RGBColor(248, 250, 252)     # Slate 50
C_BODY = RGBColor(203, 213, 225)      # Slate 300
C_MUTED = RGBColor(148, 163, 184)     # Slate 400

C_CYAN = RGBColor(6, 182, 212)        # Cyan 500
C_SKY = RGBColor(56, 189, 248)        # Sky 400
C_GREEN = RGBColor(16, 185, 129)      # Emerald 500
C_AMBER = RGBColor(245, 158, 11)      # Amber 500
C_RED = RGBColor(239, 68, 68)         # Red 500

FONT_MAIN = "Helvetica"
FONT_CODE = "Courier New"
ASSETS_DIR = "assets/fresh_presentation_assets"


def set_slide_bg(slide):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT)
    bg.fill.solid()
    bg.fill.fore_color.rgb = C_BG
    bg.line.fill.background()
    return bg


def add_header(slide, category_tag, title_text, subtitle_text):
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(1.15))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p_tag = tf.paragraphs[0]
    p_tag.space_after = Pt(2)
    r_tag = p_tag.add_run()
    r_tag.text = category_tag.upper()
    r_tag.font.name = FONT_MAIN
    r_tag.font.size = Pt(9.5)
    r_tag.font.bold = True
    r_tag.font.color.rgb = C_CYAN

    p_title = tf.add_paragraph()
    p_title.space_after = Pt(2)
    r_title = p_title.add_run()
    r_title.text = title_text
    r_title.font.name = FONT_MAIN
    r_title.font.size = Pt(20)
    r_title.font.bold = True
    r_title.font.color.rgb = C_WHITE

    p_sub = tf.add_paragraph()
    r_sub = p_sub.add_run()
    r_sub.text = subtitle_text
    r_sub.font.name = FONT_MAIN
    r_sub.font.size = Pt(10.5)
    r_sub.font.color.rgb = C_MUTED


def add_footer(slide, slide_num):
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.733), Inches(0.35))
    tf = tb.text_frame
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    r1 = p.add_run()
    r1.text = "SPATIALSIGHT · B.Tech Biomedical Engineering (Group 1) · SRM IST"
    r1.font.name = FONT_MAIN
    r1.font.size = Pt(9)
    r1.font.color.rgb = C_MUTED

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
    r_num.font.color.rgb = C_CYAN


def add_fitted_image(slide, image_path, left, top, max_w, max_h, border_color=C_BORDER):
    if not os.path.exists(image_path):
        print(f"[WARN] Image not found: {image_path}")
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

    if border_color:
        bg_rect = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            final_left - Inches(0.02),
            final_top - Inches(0.02),
            final_w + Inches(0.04),
            final_h + Inches(0.04)
        )
        bg_rect.fill.solid()
        bg_rect.fill.fore_color.rgb = C_CARD_BG
        bg_rect.line.color.rgb = border_color
        bg_rect.line.width = Pt(1.2)

    pic = slide.shapes.add_picture(image_path, final_left, final_top, final_w, final_h)
    return pic


def build_refined_deck():
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: PRODUCT TITLE & TEAM (Refined, Zero Empty Space)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s1)

    # Cyan Accent Glow Bar
    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.6), Inches(0.12), Inches(6.2))
    bar.fill.solid()
    bar.fill.fore_color.rgb = C_CYAN
    bar.line.fill.background()

    # Title text box
    tb1 = s1.shapes.add_textbox(Inches(1.2), Inches(0.55), Inches(6.8), Inches(2.2))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    tf1.margin_left = tf1.margin_top = tf1.margin_right = tf1.margin_bottom = 0

    p = tf1.paragraphs[0]
    p.space_after = Pt(3)
    r = p.add_run()
    r.text = "TECHKNOW 2026 · MODEL PROJECT EXHIBITION & DEFENSE"
    r.font.name = FONT_MAIN
    r.font.size = Pt(10)
    r.font.bold = True
    r.font.color.rgb = C_CYAN

    p = tf1.add_paragraph()
    p.space_after = Pt(2)
    r = p.add_run()
    r.text = "SPATIALSIGHT"
    r.font.name = FONT_MAIN
    r.font.size = Pt(38)
    r.font.bold = True
    r.font.color.rgb = C_WHITE

    p = tf1.add_paragraph()
    p.space_after = Pt(5)
    r = p.add_run()
    r.text = "Sensor-Guided Object Detection & Adaptive Collision Avoidance System"
    r.font.name = FONT_MAIN
    r.font.size = Pt(13.5)
    r.font.bold = True
    r.font.color.rgb = C_SKY

    p = tf1.add_paragraph()
    r = p.add_run()
    r.text = "An ultra-low-budget (<Rs.1,100 / $12.50) physics-fused active safety platform combining real-time edge computer vision, 3-axis inertial tracking, and dynamic roadway tribology."
    r.font.name = FONT_MAIN
    r.font.size = Pt(10)
    r.font.color.rgb = C_BODY

    # Team Members Card (2-Column Grid — Compact & Balanced!)
    c_team = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(2.9), Inches(6.8), Inches(2.35))
    c_team.fill.solid()
    c_team.fill.fore_color.rgb = C_CARD_BG
    c_team.line.color.rgb = C_BORDER
    tf_t = c_team.text_frame
    tf_t.margin_left = tf_t.margin_right = Inches(0.25)
    tf_t.margin_top = Inches(0.18)

    p = tf_t.paragraphs[0]
    p.space_after = Pt(6)
    r = p.add_run()
    r.text = "GROUP MEMBERS (GROUP 1) — B.TECH BIOMEDICAL ENGINEERING (B SECTION)"
    r.font.name = FONT_MAIN
    r.font.size = Pt(9.5)
    r.font.bold = True
    r.font.color.rgb = C_CYAN

    col_members = [
        ("NANDHINI SHARAB", "RA2611060010001", "ANAS HABIBULLAH", "RA2611060010004"),
        ("FIDA FATHIMA", "RA2611060010002", "SALONI SHANKAR", "RA2611060010005"),
        ("D. JAIRUS SAM", "RA2611060010003", "MUSKAN", "RA2611060010006")
    ]
    for m1_n, m1_r, m2_n, m2_r in col_members:
        p = tf_t.add_paragraph()
        p.space_after = Pt(4)
        
        # Left Member
        r1 = p.add_run()
        r1.text = f"• {m1_n} "
        r1.font.name = FONT_MAIN
        r1.font.size = Pt(9.5)
        r1.font.bold = True
        r1.font.color.rgb = C_WHITE
        
        r1_id = p.add_run()
        r1_id.text = f"({m1_r}){' ' * 8}"
        r1_id.font.name = FONT_MAIN
        r1_id.font.size = Pt(9)
        r1_id.font.color.rgb = C_MUTED
        
        # Right Member
        r2 = p.add_run()
        r2.text = f"• {m2_n} "
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.bold = True
        r2.font.color.rgb = C_WHITE
        
        r2_id = p.add_run()
        r2_id.text = f"({m2_r})"
        r2_id.font.name = FONT_MAIN
        r2_id.font.size = Pt(9)
        r2_id.font.color.rgb = C_MUTED

    # Academic & Faculty Info Card (Horizontal Bottom Card)
    c_fac = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(5.4), Inches(6.8), Inches(1.4))
    c_fac.fill.solid()
    c_fac.fill.fore_color.rgb = C_CARD_BG
    c_fac.line.color.rgb = C_BORDER
    tf_f = c_fac.text_frame
    tf_f.margin_left = tf_f.margin_right = Inches(0.25)
    tf_f.margin_top = Inches(0.15)

    p = tf_f.paragraphs[0]
    p.space_after = Pt(2)
    r = p.add_run()
    r.text = "FACULTY IN-CHARGE & INSTITUTION"
    r.font.name = FONT_MAIN
    r.font.size = Pt(9.5)
    r.font.bold = True
    r.font.color.rgb = C_CYAN

    p2 = tf_f.add_paragraph()
    r2 = p2.add_run()
    r2.text = "DR. A. GEETHA — Department of Physics and Nanotechnology\n" \
              "College of Engineering & Technology, SRM Institute of Science and Technology, Kattankulathur"
    r2.font.name = FONT_MAIN
    r2.font.size = Pt(9.5)
    r2.font.color.rgb = C_BODY

    # Right Hero Image: Prominent, perfectly fitted!
    hero_p = os.path.join(ASSETS_DIR, "hero_presentation_model.png")
    add_fitted_image(s1, hero_p, Inches(8.3), Inches(0.7), Inches(4.3), Inches(6.1), border_color=C_BORDER)

    # =========================================================================
    # SLIDE 2: BACKGROUND & MOTIVATION
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s2)
    add_header(s2, "Background & Motivation", "The Road Safety Crisis & The High Cost of ADAS",
               "Why conventional collision avoidance systems fail in affordability, low latency, and weather adaptability")
    add_footer(s2, 2)

    # Left Side: 3 Problem Cards
    c2 = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(6.3), Inches(4.9))
    c2.fill.solid()
    c2.fill.fore_color.rgb = C_CARD_BG
    c2.line.color.rgb = C_BORDER
    tf_c2 = c2.text_frame
    tf_c2.margin_left = tf_c2.margin_right = Inches(0.25)
    tf_c2.margin_top = Inches(0.2)

    problems = [
        ("1. Wet-Road Collision Crisis (24% of Highway Crashes)",
         "Rainfall reduces tire-road friction (μ) from 0.80 to 0.35, causing stopping distance to surge quadratically (s = v²/2μg). Vision-only ADAS assumes dry roads and issues braking alerts far too late.",
         C_RED),
        ("2. Prohibitive Hardware Cost of Commercial ADAS",
         "Automotive LiDAR costs Rs. 4,00,000 to Rs. 10,00,000+ ($5k–$12k), while Mobileye units cost Rs. 85,000+. Over 85% of commuter vehicles, two-wheelers, and college testbeds have zero active safety.",
         C_AMBER),
        ("3. Dangerous Cloud Vision Latency & Connectivity Loss",
         "Cloud vision APIs (AWS / Google Vision) suffer 400ms–1500ms roundtrips. At 60 km/h, a vehicle travels 25 meters blind while awaiting a server. Offline edge AI is mandatory for collision safety.",
         C_CYAN)
    ]
    for p_title, p_desc, p_color in problems:
        p = tf_c2.add_paragraph() if tf_c2.paragraphs[0].text else tf_c2.paragraphs[0]
        p.space_after = Pt(2)
        r = p.add_run()
        r.text = p_title
        r.font.name = FONT_MAIN
        r.font.size = Pt(11)
        r.font.bold = True
        r.font.color.rgb = p_color

        p_b = tf_c2.add_paragraph()
        p_b.space_after = Pt(10)
        r_b = p_b.add_run()
        r_b.text = p_desc
        r_b.font.name = FONT_MAIN
        r_b.font.size = Pt(9.5)
        r_b.font.color.rgb = C_BODY

    # Right Side: Dark Kinematic Chart
    add_fitted_image(s2, os.path.join(ASSETS_DIR, "chart_stopping_distance.png"), Inches(7.4), Inches(1.8), Inches(5.1), Inches(4.9), border_color=C_BORDER)

    # =========================================================================
    # SLIDE 3: SYSTEM PREMISE & SENSOR FUSION
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s3)
    add_header(s3, "System Premise & Innovation", "The SpatialSight Solution: Fusing Vision with Roadway Physics",
               "Real-time object detection alone cannot prevent crashes without understanding road friction, inertia, and stopping kinetics")
    add_footer(s3, 3)

    # Left Side: Tri-Pillar Architecture
    c3 = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(6.3), Inches(4.9))
    c3.fill.solid()
    c3.fill.fore_color.rgb = C_CARD_BG
    c3.line.color.rgb = C_BORDER
    tf_c3 = c3.text_frame
    tf_c3.margin_left = tf_c3.margin_right = Inches(0.25)
    tf_c3.margin_top = Inches(0.2)

    pillars = [
        ("Pillar 1: Optical Neural Vision (YOLOv8 @ 60 FPS)",
         "Monocular camera capture on Android phone streams at 720p @ 30 FPS. Edge AI model classifies cars, pedestrians, cycles, and obstacles in <8ms with perspective corridor isolation.",
         C_CYAN),
        ("Pillar 2: 3-Axis Inertial Motion Sensing (Gyroscopes @ 30 Hz)",
         "Android rotation vector telemetry streams yaw, pitch, and roll (θ, φ, ψ). Tracks phone orientation to eliminate duplicate spatial detections and build 360° environmental awareness.",
         C_SKY),
        ("Pillar 3: Environmental Road Physics (Arduino Sensor Fusion)",
         "Analog surface moisture sensor continuously measures water presence. Dynamically computes tire-road friction coefficient (μ) to adjust safety perimeters in real time.",
         C_GREEN)
    ]
    for title, desc, color in pillars:
        p = tf_c3.add_paragraph() if tf_c3.paragraphs[0].text else tf_c3.paragraphs[0]
        p.space_after = Pt(2)
        r = p.add_run()
        r.text = title
        r.font.name = FONT_MAIN
        r.font.size = Pt(11.5)
        r.font.bold = True
        r.font.color.rgb = color

        p_d = tf_c3.add_paragraph()
        p_d.space_after = Pt(12)
        r_d = p_d.add_run()
        r_d.text = desc
        r_d.font.name = FONT_MAIN
        r_d.font.size = Pt(9.5)
        r_d.font.color.rgb = C_BODY

    # Right Side: Dark Architecture Flowchart
    add_fitted_image(s3, os.path.join(ASSETS_DIR, "diagram_system_architecture.png"), Inches(7.4), Inches(1.8), Inches(5.1), Inches(4.9), border_color=C_BORDER)

    # =========================================================================
    # SLIDE 4: END-TO-END SYSTEM ARCHITECTURE
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s4)
    add_header(s4, "System Architecture", "End-to-End System Pipeline: From Sensing to Actuation",
               "Complete hardware & software pipeline from mobile video capture to physical traffic signal alerts")
    add_footer(s4, 4)

    # Left Side: 6-Layer Pipeline
    c4 = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(6.3), Inches(4.9))
    c4.fill.solid()
    c4.fill.fore_color.rgb = C_CARD_BG
    c4.line.color.rgb = C_BORDER
    tf_c4 = c4.text_frame
    tf_c4.margin_left = tf_c4.margin_right = Inches(0.25)
    tf_c4.margin_top = Inches(0.2)

    pipeline_steps = [
        ("Layer 1: Android Sensing Node", "CameraX captures 720p @ 30 FPS. Gyroscope captures 3-axis rotation telemetry. NanoHTTPD streams MJPEG & JSON over port 8080."),
        ("Layer 2: Low-Latency USB-C Bridge", "Tethered ADB TCP bridge (adb forward tcp:8080 tcp:8080) delivers sub-25ms latency with zero network dependency while keeping phone charged."),
        ("Layer 3: Host Edge AI Compute Engine", "Multi-threaded worker drops stale frames; processes latest frame with YOLOv8 at 60 FPS on Apple Silicon Metal MPS / Windows DirectML."),
        ("Layer 4: Corridor Geometry & Distance Model", "Perspective trapezoidal driving corridor isolates obstacles; pinhole optics computes distance Z and closing speed."),
        ("Layer 5: Arduino Physics Sensor Interface", "Streams continuous 10 Hz analog ADC moisture telemetry over serial; calculates dynamic friction μ and stopping multiplier."),
        ("Layer 6: Hardware Alert Actuators", "Arduino triggers tri-color traffic light LEDs (Green → Yellow → Red) and sounds an active piezo buzzer emergency braking alert.")
    ]
    for s_num, s_desc in pipeline_steps:
        p = tf_c4.add_paragraph() if tf_c4.paragraphs[0].text else tf_c4.paragraphs[0]
        p.space_after = Pt(2)
        r = p.add_run()
        r.text = f"{s_num}: "
        r.font.name = FONT_MAIN
        r.font.size = Pt(9.8)
        r.font.bold = True
        r.font.color.rgb = C_CYAN
        r2 = p.add_run()
        r2.text = s_desc
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.2)
        r2.font.color.rgb = C_BODY

    # Right Side: Real Live ADAS Green Screenshot
    add_fitted_image(s4, os.path.join(ASSETS_DIR, "screenshot_live_adas_green.png"), Inches(7.4), Inches(1.8), Inches(5.1), Inches(4.9), border_color=C_BORDER)

    # =========================================================================
    # SLIDE 5: OPTICAL VISION & MONOCULAR DISTANCE
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s5)
    add_header(s5, "Computer Vision & Kinematics", "Optical Neural Inference & Pinhole Distance Geometry",
               "Extracting 3D forward distance, velocity, and Time-to-Collision from 2D frames without costly stereo cameras")
    add_footer(s5, 5)

    c5 = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(6.3), Inches(4.9))
    c5.fill.solid()
    c5.fill.fore_color.rgb = C_CARD_BG
    c5.line.color.rgb = C_BORDER
    tf_c5 = c5.text_frame
    tf_c5.margin_left = tf_c5.margin_right = Inches(0.25)
    tf_c5.margin_top = Inches(0.2)

    p = tf_c5.paragraphs[0]
    p.space_after = Pt(2)
    r = p.add_run()
    r.text = "1. YOLOv8 Edge Neural Detection (60 FPS)"
    r.font.name = FONT_MAIN
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.font.color.rgb = C_CYAN

    p_exp = tf_c5.add_paragraph()
    p_exp.space_after = Pt(8)
    r_exp = p_exp.add_run()
    r_exp.text = "• Runs ultralytics YOLOv8n locally with hardware acceleration (<8ms latency).\n" \
                 "• Detects vehicles, pedestrians, cycles, and obstacles with high accuracy.\n" \
                 "• Perspective driving corridor ignores parked side vehicles, preventing false alerts."
    r_exp.font.name = FONT_MAIN
    r_exp.font.size = Pt(9.5)
    r_exp.font.color.rgb = C_BODY

    p = tf_c5.add_paragraph()
    p.space_after = Pt(2)
    r = p.add_run()
    r.text = "2. Optical Pinhole Distance Formulation"
    r.font.name = FONT_MAIN
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.font.color.rgb = C_CYAN

    p_f = tf_c5.add_paragraph()
    p_f.space_after = Pt(4)
    r_f = p_f.add_run()
    r_f.text = "Distance (Z) = (f · H_real) / h_bbox"
    r_f.font.name = FONT_CODE
    r_f.font.size = Pt(12.5)
    r_f.font.bold = True
    r_f.font.color.rgb = C_SKY

    p_math = tf_c5.add_paragraph()
    p_math.space_after = Pt(8)
    r_math = p_math.add_run()
    r_math.text = "• f = Calibrated camera focal length (~720 px)\n" \
                  "• H_real = Real-world obstacle height (Car: 1.5m, Person: 1.7m, Bike: 1.2m)\n" \
                  "• h_bbox = Detected bounding box pixel height on frame"
    r_math.font.name = FONT_MAIN
    r_math.font.size = Pt(9.5)
    r_math.font.color.rgb = C_BODY

    p = tf_c5.add_paragraph()
    p.space_after = Pt(2)
    r = p.add_run()
    r.text = "3. Relative Velocity & Time-to-Collision (TTC)"
    r.font.name = FONT_MAIN
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.font.color.rgb = C_RED

    p_ttc = tf_c5.add_paragraph()
    r_ttc = p_ttc.add_run()
    r_ttc.text = "• v_rel = ΔZ / Δt  (closing approach speed in m/s)\n" \
                 "• TTC = Z / v_rel  (seconds remaining until collision)\n" \
                 "• Eliminates the need for expensive multi-thousand-dollar radar sensors."
    r_ttc.font.name = FONT_MAIN
    r_ttc.font.size = Pt(9.5)
    r_ttc.font.color.rgb = C_BODY

    # Right Side: Live ADAS Green Screenshot
    add_fitted_image(s5, os.path.join(ASSETS_DIR, "screenshot_live_adas_green.png"), Inches(7.4), Inches(1.8), Inches(5.1), Inches(4.9), border_color=C_BORDER)

    # =========================================================================
    # SLIDE 6: ENVIRONMENTAL PHYSICS & TRIBOLOGY ENGINE
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s6)
    add_header(s6, "Physics & Tribology", "Roadway Tribology & Dynamic Stopping Distance Physics",
               "Applying classical Newtonian mechanics and surface friction to evaluate dynamic collision severity")
    add_footer(s6, 6)

    c6 = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(6.3), Inches(4.9))
    c6.fill.solid()
    c6.fill.fore_color.rgb = C_CARD_BG
    c6.line.color.rgb = C_BORDER
    tf_c6 = c6.text_frame
    tf_c6.margin_left = tf_c6.margin_right = Inches(0.25)
    tf_c6.margin_top = Inches(0.2)

    p = tf_c6.paragraphs[0]
    p.space_after = Pt(2)
    r = p.add_run()
    r.text = "1. Idealized Kinematic Stopping Distance Formula"
    r.font.name = FONT_MAIN
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.font.color.rgb = C_CYAN

    p_f1 = tf_c6.add_paragraph()
    p_f1.space_after = Pt(4)
    r_f1 = p_f1.add_run()
    r_f1.text = "s = v² / (2 · μ · g)"
    r_f1.font.name = FONT_CODE
    r_f1.font.size = Pt(13.5)
    r_f1.font.bold = True
    r_f1.font.color.rgb = C_SKY

    p_f1_exp = tf_c6.add_paragraph()
    p_f1_exp.space_after = Pt(8)
    r_f1_exp = p_f1_exp.add_run()
    r_f1_exp.text = "• v = Initial vehicle velocity (m/s) — stopping distance scales QUADRATICALLY (v²).\n" \
                    "• μ = Coefficient of friction — stopping distance is INVERSELY proportional (1/μ).\n" \
                    "• g = Acceleration due to gravity (9.81 m/s²)."
    r_f1_exp.font.name = FONT_MAIN
    r_f1_exp.font.size = Pt(9.5)
    r_f1_exp.font.color.rgb = C_BODY

    p = tf_c6.add_paragraph()
    p.space_after = Pt(2)
    r = p.add_run()
    r.text = "2. Kinetic Energy Dissipation (Collision Severity)"
    r.font.name = FONT_MAIN
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.font.color.rgb = C_RED

    p_f2 = tf_c6.add_paragraph()
    p_f2.space_after = Pt(4)
    r_f2 = p_f2.add_run()
    r_f2.text = "KE = ½ · m · v²"
    r_f2.font.name = FONT_CODE
    r_f2.font.size = Pt(13.5)
    r_f2.font.bold = True
    r_f2.font.color.rgb = C_RED

    p_f2_exp = tf_c6.add_paragraph()
    r_f2_exp = p_f2_exp.add_run()
    r_f2_exp.text = "• A vehicle traveling at 60 km/h possesses 4× the kinetic energy of one at 30 km/h.\n" \
                    "• In wet weather (μ drops from 0.80 to 0.35), available braking traction drops by 56%.\n" \
                    "• SpatialSight automatically detects road moisture via Arduino and scales warning perimeters before crashes occur."
    r_f2_exp.font.name = FONT_MAIN
    r_f2_exp.font.size = Pt(9.5)
    r_f2_exp.font.color.rgb = C_BODY

    # Right Side: Dark Tribology Chart
    add_fitted_image(s6, os.path.join(ASSETS_DIR, "chart_friction_tribology.png"), Inches(7.4), Inches(1.8), Inches(5.1), Inches(4.9), border_color=C_BORDER)

    # =========================================================================
    # SLIDE 7: ADAPTIVE SAFETY PERIMETER & DYNAMIC WARNING
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s7)
    add_header(s7, "Active Safety Perimeter", "Adaptive Collision Corridor: Expanding Warning Zones Up to 2.3×",
               "Real-time expansion of the forward safety perimeter based on environmental moisture telemetry")
    add_footer(s7, 7)

    c7 = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(6.3), Inches(4.9))
    c7.fill.solid()
    c7.fill.fore_color.rgb = C_CARD_BG
    c7.line.color.rgb = C_BORDER
    tf_c7 = c7.text_frame
    tf_c7.margin_left = tf_c7.margin_right = Inches(0.25)
    tf_c7.margin_top = Inches(0.2)

    p = tf_c7.paragraphs[0]
    p.space_after = Pt(2)
    r = p.add_run()
    r.text = "Dynamic Stopping Distance Multiplier (M_stop)"
    r.font.name = FONT_MAIN
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.font.color.rgb = C_CYAN

    p_m = tf_c7.add_paragraph()
    p_m.space_after = Pt(6)
    r_m = p_m.add_run()
    r_m.text = "M_stop = μ_dry / μ_measured = 0.80 / 0.35 ≈ 2.29 ≈ 2.3×"
    r_m.font.name = FONT_CODE
    r_m.font.size = Pt(12.5)
    r_m.font.bold = True
    r_m.font.color.rgb = C_SKY

    p_h = tf_c7.add_paragraph()
    p_h.space_after = Pt(4)
    r_h = p_h.add_run()
    r_h.text = "Graduated 3-Color Active Alert Hierarchy:"
    r_h.font.name = FONT_MAIN
    r_h.font.size = Pt(10.5)
    r_h.font.bold = True
    r_h.font.color.rgb = C_WHITE

    stages = [
        ("GREEN (Normal Safe Condition):", "Forward corridor is clear. Obstacles are well outside safety stopping envelope (Z > s_wet · 1.5). Green signal active.", C_GREEN),
        ("YELLOW (Advisory Pre-Crash Warning):", "Obstacle entered outer safety boundary. Amber LED active. Advises driver to lift throttle and prepare braking.", C_AMBER),
        ("RED (Critical Emergency Hazard):", "Safe stopping boundary breached (Z ≤ s_wet). Red LED flashes + emergency buzzer sounds. Immediate emergency braking required.", C_RED)
    ]
    for st_title, st_desc, st_color in stages:
        p = tf_c7.add_paragraph()
        p.space_after = Pt(6)
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
        r2.font.color.rgb = C_BODY

    # Right Side: Dual Comparison Screenshots (Stacked Cleanly)
    add_fitted_image(s7, os.path.join(ASSETS_DIR, "screenshot_live_adas_yellow.png"), Inches(7.4), Inches(1.8), Inches(5.1), Inches(2.35), border_color=C_BORDER)
    add_fitted_image(s7, os.path.join(ASSETS_DIR, "screenshot_live_adas_red.png"), Inches(7.4), Inches(4.35), Inches(5.1), Inches(2.35), border_color=C_BORDER)

    # =========================================================================
    # SLIDE 8: BILL OF MATERIALS (BOM) & BUDGET ANALYSIS
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s8)
    add_header(s8, "Budget & Feasibility Analysis", "Component Bill of Materials (BOM) & Cost Breakdown",
               "Proving ultra-low-cost academic and industrial feasibility (Sub-Rs.1,100 / $12.50 System)")
    add_footer(s8, 8)

    # Left Side Dark-Themed Financial Table
    table_shape = s8.shapes.add_table(8, 5, Inches(0.8), Inches(1.8), Inches(6.3), Inches(3.4))
    tbl = table_shape.table
    tbl.columns[0].width = Inches(1.9)
    tbl.columns[1].width = Inches(2.1)
    tbl.columns[2].width = Inches(0.5)
    tbl.columns[3].width = Inches(0.9)
    tbl.columns[4].width = Inches(0.9)

    headers = ["Component", "Function / Spec", "Qty", "Cost (INR)", "Cost (USD)"]
    for col_idx, h_text in enumerate(headers):
        cell = tbl.cell(0, col_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(3, 105, 161) # Sky 700
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if col_idx >= 2 else PP_ALIGN.LEFT
        r = p.add_run()
        r.text = h_text
        r.font.name = FONT_MAIN
        r.font.size = Pt(9)
        r.font.bold = True
        r.font.color.rgb = C_WHITE

    bom_rows = [
        ("Arduino Uno / Nano", "Atmega328P MCU & ADC", "1", "Rs. 450", "$5.40"),
        ("Analog Rain Sensor", "Nickel grid + LM393", "1", "Rs. 120", "$1.45"),
        ("Tri-Color Signal LED", "Green/Yellow/Red 8mm", "1", "Rs. 80", "$0.95"),
        ("Active Piezo Buzzer", "5V 85dB Audio Alert", "1", "Rs. 40", "$0.50"),
        ("USB-C 3.1 Cable", "Low-Latency Tether", "1", "Rs. 200", "$2.40"),
        ("Breadboard & Jumpers", "Interconnects", "1 set", "Rs. 150", "$1.80"),
        ("TOTAL OUTLAY", "Complete Working ADAS", "6 units", "Rs. 1,040", "$12.50")
    ]

    for row_idx, row_data in enumerate(bom_rows, start=1):
        is_total = (row_idx == len(bom_rows))
        for col_idx, cell_value in enumerate(row_data):
            cell = tbl.cell(row_idx, col_idx)
            cell.fill.solid()
            if is_total:
                cell.fill.fore_color.rgb = RGBColor(6, 78, 59) # Emerald 900
            elif row_idx % 2 == 1:
                cell.fill.fore_color.rgb = C_CARD_BG
            else:
                cell.fill.fore_color.rgb = C_CARD_BG_ALT

            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER if col_idx >= 2 else PP_ALIGN.LEFT
            r = p.add_run()
            r.text = cell_value
            r.font.name = FONT_MAIN
            r.font.size = Pt(8.5)
            if is_total:
                r.font.bold = True
                r.font.color.rgb = C_GREEN
            else:
                r.font.color.rgb = C_WHITE

    # Lower Feasibility Card
    c_feas = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.4), Inches(6.3), Inches(1.3))
    c_feas.fill.solid()
    c_feas.fill.fore_color.rgb = C_CARD_BG
    c_feas.line.color.rgb = C_BORDER
    tf_f = c_feas.text_frame
    tf_f.margin_left = tf_f.margin_right = Inches(0.2)
    tf_f.margin_top = Inches(0.12)

    p = tf_f.paragraphs[0]
    r = p.add_run()
    r.text = "SOCIAL IMPACT & FEASIBILITY:"
    r.font.name = FONT_MAIN
    r.font.size = Pt(9.5)
    r.font.bold = True
    r.font.color.rgb = C_GREEN

    p2 = tf_f.add_paragraph()
    r2 = p2.add_run()
    r2.text = "By repurposing existing consumer smartphones (camera + IMU) and student workstations (YOLO inference), SpatialSight eliminates over 98.5% of commercial ADAS costs, making life-saving active safety accessible for two-wheelers and auto-rickshaws."
    r2.font.name = FONT_MAIN
    r2.font.size = Pt(8.8)
    r2.font.color.rgb = C_BODY

    # Right Side: Dark Budget Comparison Diagram
    add_fitted_image(s8, os.path.join(ASSETS_DIR, "diagram_budget_bom.png"), Inches(7.4), Inches(1.8), Inches(5.1), Inches(4.9), border_color=C_BORDER)

    # =========================================================================
    # SLIDE 9: DUAL-MODE VERSATILITY & SPATIAL MAPPING
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s9)
    add_header(s9, "Capabilities & Validation", "Dual-Mode Flexibility, 360° Spatial Mapping & Validation",
               "Versatile operation across live driving ADAS and 360-degree spatial room inventory mapping")
    add_footer(s9, 9)

    c9 = s9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(6.3), Inches(4.9))
    c9.fill.solid()
    c9.fill.fore_color.rgb = C_CARD_BG
    c9.line.color.rgb = C_BORDER
    tf_c9 = c9.text_frame
    tf_c9.margin_left = tf_c9.margin_right = Inches(0.25)
    tf_c9.margin_top = Inches(0.2)

    p = tf_c9.paragraphs[0]
    p.space_after = Pt(2)
    r = p.add_run()
    r.text = "MODE 1: 360° Spatial Room Mapping (Zero Redundancy)"
    r.font.name = FONT_MAIN
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.font.color.rgb = C_CYAN

    p1 = tf_c9.add_paragraph()
    p1.space_after = Pt(8)
    r1 = p1.add_run()
    r1.text = "• Sensor-Guided Angular Binning: Captures keyframes only when camera orientation rotates by ≥25°.\n" \
              "• Eliminates Duplicate Counts: An object seen across 30 frames is cataloged exactly once in spatial coordinates.\n" \
              "• Produces 2D spatial polar radar maps and exact item inventory for robotics and smart facilities."
    r1.font.name = FONT_MAIN
    r1.font.size = Pt(9.2)
    r1.font.color.rgb = C_BODY

    p = tf_c9.add_paragraph()
    p.space_after = Pt(2)
    r = p.add_run()
    r.text = "MODE 2: Live Forward Collision Avoidance (ADAS)"
    r.font.name = FONT_MAIN
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.font.color.rgb = C_GREEN

    p2 = tf_c9.add_paragraph()
    p2.space_after = Pt(8)
    r2 = p2.add_run()
    r2.text = "• Continuous 60 FPS forward road monitoring with trapezoidal driving corridor.\n" \
              "• Dynamic friction multiplier (1.0× to 2.3×) automatically scales warning trigger distance.\n" \
              "• Direct serial transmission to Arduino actuates visual and audible alerts in <100ms."
    r2.font.name = FONT_MAIN
    r2.font.size = Pt(9.2)
    r2.font.color.rgb = C_BODY

    p = tf_c9.add_paragraph()
    p.space_after = Pt(2)
    r = p.add_run()
    r.text = "Benchmarked System Performance"
    r.font.name = FONT_MAIN
    r.font.size = Pt(10.5)
    r.font.bold = True
    r.font.color.rgb = C_WHITE

    p3 = tf_c9.add_paragraph()
    r3 = p3.add_run()
    r3.text = "• USB-C Video Latency: <25 ms  |  YOLO Inference: 8 ms  |  Overall Reaction Time: <35 ms\n" \
              "• Network Dependency: 0% (Fully Offline)  |  Cloud Cost: Rs. 0.00 / $0.00"
    r3.font.name = FONT_MAIN
    r3.font.size = Pt(9)
    r3.font.bold = True
    r3.font.color.rgb = C_SKY

    # Right Side: 2D Polar Room Radar Screenshot from RoomMapRenderer
    add_fitted_image(s9, os.path.join(ASSETS_DIR, "screenshot_room_map_radar.png"), Inches(7.4), Inches(1.8), Inches(5.1), Inches(4.9), border_color=C_BORDER)

    # =========================================================================
    # SLIDE 10: CONCLUSION & THANK YOU NOTE
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s10)

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
    r.font.color.rgb = C_CYAN

    p = tf10.add_paragraph()
    p.space_after = Pt(2)
    r = p.add_run()
    r.text = "Thank You!"
    r.font.name = FONT_MAIN
    r.font.size = Pt(34)
    r.font.bold = True
    r.font.color.rgb = C_WHITE

    p = tf10.add_paragraph()
    r = p.add_run()
    r.text = "SpatialSight: Sensor-Guided Object Detection & Adaptive Collision Avoidance System"
    r.font.name = FONT_MAIN
    r.font.size = Pt(13)
    r.font.color.rgb = C_MUTED

    col_w = Inches(3.7)

    # Card 1: Key Achievements
    c1 = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.1), col_w, Inches(4.5))
    c1.fill.solid()
    c1.fill.fore_color.rgb = C_CARD_BG
    c1.line.color.rgb = C_BORDER
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
    r.font.color.rgb = C_CYAN

    achievements = [
        "Physics-Guided Vision: Successfully fused optical computer vision with dynamic roadway friction (μ).",
        "Adaptive Weather Safety: Scaled braking warning zones dynamically up to 2.3× under wet conditions.",
        "Ultra-Low Budget: Delivered a complete functional system for Rs.1,040 (~$12.50), proving extreme affordability.",
        "Zero Cloud Latency: 100% offline edge execution (<25ms) protecting user data privacy."
    ]
    for ach in achievements:
        p = tf_c1.add_paragraph()
        p.space_after = Pt(8)
        r = p.add_run()
        r.text = f"- {ach}"
        r.font.name = FONT_MAIN
        r.font.size = Pt(9.2)
        r.font.color.rgb = C_BODY

    # Card 2: Future Scope
    c2 = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.8), Inches(2.1), col_w, Inches(4.5))
    c2.fill.solid()
    c2.fill.fore_color.rgb = C_CARD_BG
    c2.line.color.rgb = C_BORDER
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
    r.font.color.rgb = C_SKY

    future_scope = [
        "Vehicle CAN-Bus Integration: Direct interface to vehicle ECU for active automatic emergency braking (AEB).",
        "Night Vision Enhancement: Integration of low-cost thermal sensors for zero-light pedestrian protection.",
        "Two-Wheeler Deployment: Commercial casing for retrofitting onto motorcycles, e-scooters, and auto-rickshaws.",
        "Expanded Fleet Analytics: Aggregating edge friction telemetry to map municipal road slip hazards."
    ]
    for fs in future_scope:
        p = tf_c2.add_paragraph()
        p.space_after = Pt(8)
        r = p.add_run()
        r.text = f"→ {fs}"
        r.font.name = FONT_MAIN
        r.font.size = Pt(9.2)
        r.font.color.rgb = C_BODY

    # Card 3: Acknowledgments & Questions
    c3 = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.8), Inches(2.1), col_w, Inches(4.5))
    c3.fill.solid()
    c3.fill.fore_color.rgb = C_CARD_BG
    c3.line.color.rgb = C_BORDER
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
    r.font.color.rgb = C_GREEN

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
    r_ack.font.color.rgb = C_BODY

    p_q = tf_c3.add_paragraph()
    p_q.space_before = Pt(6)
    r_q = p_q.add_run()
    r_q.text = "QUESTIONS & ANSWERS\nWe welcome your feedback & questions!"
    r_q.font.name = FONT_MAIN
    r_q.font.size = Pt(10)
    r_q.font.bold = True
    r_q.font.color.rgb = C_CYAN

    output_pptx = "SpatialSight_Project_Presentation.pptx"
    prs.save(output_pptx)
    print(f"[SUCCESS] Built refined presentation: {output_pptx}")
    return output_pptx


if __name__ == "__main__":
    build_refined_deck()
