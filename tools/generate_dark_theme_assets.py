"""
generate_dark_theme_assets.py
Regenerates all project assets in a unified, high-tech dark theme (#0F172A / #1E293B)
matching the executive dark presentation aesthetic.
"""

import os
import sys
import math
import time
import numpy as np
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

sys.path.insert(0, os.path.abspath('mac_app'))
from core.collision_zone import CollisionZone, HazardAlert
from core.inference_engine import Detection
from spatial.room_map_renderer import RoomMapRenderer
from spatial.keyframe_selector import Keyframe, SensorData
from spatial.angular_dedup import SpatialObject

OUTPUT_DIR = "assets/fresh_presentation_assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Theme Colors
BG_DARK = "#0F172A"       # Canvas background
SURFACE_DARK = "#1E293B"  # Card/Plot background
BORDER_DARK = "#334155"   # Grid/borders
TEXT_WHITE = "#FFFFFF"
TEXT_SLATE = "#CBD5E1"
TEXT_MUTED = "#94A3B8"
C_CYAN = "#06B6D4"
C_SKY = "#38BDF8"
C_GREEN = "#10B981"
C_AMBER = "#F59E0B"
C_RED = "#EF4444"


def generate_dark_charts():
    # -------------------------------------------------------------
    # 1. Kinematic Stopping Distance Chart (Dark Theme)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8.5, 5.0), dpi=220)
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(SURFACE_DARK)

    v_kmh = np.linspace(10, 100, 100)
    v_ms = v_kmh / 3.6
    g = 9.81

    s_dry = (v_ms ** 2) / (2 * 0.80 * g)
    s_wet = (v_ms ** 2) / (2 * 0.35 * g)

    ax.plot(v_kmh, s_dry, color=C_GREEN, linewidth=3.2, label='Dry Asphalt (μ = 0.80) — Safe Grip')
    ax.plot(v_kmh, s_wet, color=C_RED, linewidth=3.2, label='Wet Pavement (μ = 0.35) — 2.3x Danger')
    ax.fill_between(v_kmh, s_dry, s_wet, color=C_RED, alpha=0.18, label='Excess Stopping Distance Deficit')

    # Annotate 60 km/h
    s_dry_60 = ((60 / 3.6) ** 2) / (2 * 0.80 * g)
    s_wet_60 = ((60 / 3.6) ** 2) / (2 * 0.35 * g)
    ax.scatter([60, 60], [s_dry_60, s_wet_60], color=[C_GREEN, C_RED], s=80, zorder=5)

    ax.annotate(f'60 km/h Dry: {s_dry_60:.1f}m', xy=(60, s_dry_60), xytext=(22, s_dry_60 + 12),
                arrowprops=dict(facecolor=C_GREEN, edgecolor=C_GREEN, shrink=0.08, width=1.5, headwidth=6),
                fontsize=9.5, fontweight='bold', color=C_GREEN)
    ax.annotate(f'60 km/h Wet: {s_wet_60:.1f}m (+{s_wet_60 - s_dry_60:.1f}m!)', xy=(60, s_wet_60), xytext=(22, s_wet_60 + 12),
                arrowprops=dict(facecolor=C_RED, edgecolor=C_RED, shrink=0.08, width=1.5, headwidth=6),
                fontsize=9.5, fontweight='bold', color=C_RED)

    ax.set_xlabel('Initial Vehicle Velocity v (km/h)', fontsize=10.5, fontweight='bold', color=TEXT_WHITE, labelpad=8)
    ax.set_ylabel('Stopping Distance s = v² / (2μg)  [Meters]', fontsize=10.5, fontweight='bold', color=TEXT_WHITE, labelpad=8)
    ax.set_title('Vehicle Kinematics: Stopping Distance Surges by 2.3× on Wet Roads', fontsize=12, fontweight='bold', color=TEXT_WHITE, pad=12)

    ax.tick_params(colors=TEXT_MUTED, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(BORDER_DARK)
    ax.grid(True, color=BORDER_DARK, linestyle='--', alpha=0.5)
    ax.legend(loc='upper left', facecolor=SURFACE_DARK, edgecolor=BORDER_DARK, labelcolor=TEXT_WHITE, fontsize=9.2)

    fig.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "chart_stopping_distance.png"), facecolor=fig.get_facecolor(), dpi=220)
    plt.close()

    # -------------------------------------------------------------
    # 2. Tribology Chart: Moisture vs Friction (Dark Theme)
    # -------------------------------------------------------------
    fig, ax1 = plt.subplots(figsize=(8.5, 5.0), dpi=220)
    fig.patch.set_facecolor(BG_DARK)
    ax1.set_facecolor(SURFACE_DARK)

    adc_vals = np.linspace(0, 1023, 100)
    mu_vals = 0.80 - (0.80 - 0.35) * (adc_vals / 1023.0)
    mult_vals = 0.80 / mu_vals

    ax1.set_xlabel('Arduino Analog Moisture Reading (ADC 0 to 1023)', fontsize=10.5, fontweight='bold', color=TEXT_WHITE, labelpad=8)
    ax1.set_ylabel('Friction Coefficient (μ)', color=C_SKY, fontsize=10.5, fontweight='bold')
    ax1.plot(adc_vals, mu_vals, color=C_SKY, linewidth=3.2, label='Friction (μ)')
    ax1.tick_params(axis='y', labelcolor=C_SKY)
    ax1.tick_params(axis='x', colors=TEXT_MUTED)
    ax1.set_ylim(0.2, 0.9)
    ax1.axhline(0.80, color=C_GREEN, linestyle='--', alpha=0.8, label='Dry Asphalt (μ = 0.80)')
    ax1.axhline(0.35, color=C_RED, linestyle='--', alpha=0.8, label='Flooded / Wet Limit (μ = 0.35)')

    ax2 = ax1.twinx()
    ax2.set_ylabel('Safety Zone Expansion Multiplier (M_stop)', color=C_AMBER, fontsize=10.5, fontweight='bold')
    ax2.plot(adc_vals, mult_vals, color=C_AMBER, linewidth=3.2, linestyle='-.', label='Stopping Multiplier')
    ax2.tick_params(axis='y', labelcolor=C_AMBER)
    ax2.set_ylim(0.8, 2.6)

    ax1.set_title('Roadway Tribology: Dynamic Friction Loss & Safety Zone Multiplier', fontsize=12, fontweight='bold', color=TEXT_WHITE, pad=12)

    for spine in ax1.spines.values():
        spine.set_color(BORDER_DARK)
    ax1.grid(True, color=BORDER_DARK, linestyle='--', alpha=0.5)

    fig.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "chart_friction_tribology.png"), facecolor=fig.get_facecolor(), dpi=220)
    plt.close()


def generate_dark_architecture_diagram():
    fig, ax = plt.subplots(figsize=(9.5, 5.8), dpi=220)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_DARK)

    ax.text(50, 94, "SpatialSight: Hardware & Data Flow Pipeline",
            ha='center', va='center', fontsize=14, fontweight='bold', color=TEXT_WHITE)
    ax.text(50, 89, "Synchronous Optical Perception, Inertial Telemetry, and Physical Sensor Fusion",
            ha='center', va='center', fontsize=9.5, color=C_SKY)

    boxes = [
        (4, 50, 27, 32, "ANDROID SENSING NODE",
         "• CameraX: 720p @ 30 FPS\n• 3-Axis IMU (θ, φ, ψ) Telemetry\n• NanoHTTPD MJPEG Stream\n• Low-power edge capture",
         SURFACE_DARK, C_CYAN),
        (36.5, 50, 27, 32, "HOST COMPUTE ENGINE",
         "• Producer-Consumer Buffer\n• YOLOv8 Inference (60 FPS)\n• Pinhole Depth Z = f·H/h\n• Corridor Hazard Filter",
         SURFACE_DARK, C_SKY),
        (69, 50, 27, 32, "ARDUINO PHYSICAL HUB",
         "• Analog Moisture Sensor (10Hz)\n• Dynamic Friction μ Calculation\n• Tri-Color Traffic Signals\n• Emergency Audio Buzzer",
         SURFACE_DARK, C_GREEN),
        (4, 10, 44, 28, "USB-C LOW-LATENCY BRIDGE (<25ms)",
         "• ADB TCP forward (localhost:8080)\n• Zero Wi-Fi jitter, zero network lag\n• Charges smartphone continuously\n• 100% offline edge privacy",
         SURFACE_DARK, C_AMBER),
        (52, 10, 44, 28, "ACTIVE SAFETY ACTUATION",
         "• Dynamic warning corridor (up to 2.3×)\n• Green (Safe) → Yellow (Caution) → Red (Brake)\n• Emergency audio collision warning\n• Sub-35ms total reaction roundtrip",
         SURFACE_DARK, C_RED)
    ]

    for x, y, bw, bh, title, desc, bg_c, accent_c in boxes:
        rect = patches.FancyBboxPatch((x, y), bw, bh, boxstyle="round,pad=1.2,rounding_size=2",
                                      facecolor=bg_c, edgecolor=accent_c, linewidth=1.6)
        ax.add_patch(rect)
        ax.text(x + bw/2, y + bh - 4.5, title, ha='center', va='top', fontsize=9.5, fontweight='bold', color=accent_c)
        ax.text(x + 2, y + bh - 11, desc, ha='left', va='top', fontsize=8.2, color=TEXT_SLATE, linespacing=1.3)

    # Connecting arrows
    ax.annotate('', xy=(36.5, 66), xytext=(31, 66),
                arrowprops=dict(facecolor=C_CYAN, edgecolor=C_CYAN, width=2.2, headwidth=7))
    ax.text(33.8, 70, "Video+IMU", ha='center', fontsize=7.5, fontweight='bold', color=C_CYAN)

    ax.annotate('', xy=(69, 66), xytext=(63.5, 66),
                arrowprops=dict(facecolor=C_GREEN, edgecolor=C_GREEN, width=2.2, headwidth=7))
    ax.text(66.2, 70, "Alert State", ha='center', fontsize=7.5, fontweight='bold', color=C_GREEN)

    ax.annotate('', xy=(63.5, 62), xytext=(69, 62),
                arrowprops=dict(facecolor=C_SKY, edgecolor=C_SKY, width=1.8, headwidth=6))
    ax.text(66.2, 58, "Moisture ADC", ha='center', fontsize=7.5, fontweight='bold', color=C_SKY)

    # Vertical bridge arrows
    ax.annotate('', xy=(17, 50), xytext=(17, 38),
                arrowprops=dict(facecolor=C_AMBER, edgecolor=C_AMBER, width=2, headwidth=6))
    ax.annotate('', xy=(74, 38), xytext=(74, 50),
                arrowprops=dict(facecolor=C_RED, edgecolor=C_RED, width=2, headwidth=6))

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "diagram_system_architecture.png"), facecolor=fig.get_facecolor(), dpi=220)
    plt.close()


def generate_dark_budget_diagram():
    fig, ax = plt.subplots(figsize=(9.5, 5.8), dpi=220)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_DARK)

    ax.text(50, 94, "SpatialSight: Hardware Bill of Materials & Cost Feasibility",
            ha='center', va='center', fontsize=13.5, fontweight='bold', color=TEXT_WHITE)
    ax.text(50, 89, "Comparing Sub-Rs.1,100 ($12.50) SpatialSight Prototype against Commercial ADAS",
            ha='center', va='center', fontsize=9.5, color=C_SKY)

    # Left Card: BOM Table
    rect_bom = patches.FancyBboxPatch((4, 8), 50, 76, boxstyle="round,pad=1.2,rounding_size=2",
                                      facecolor=SURFACE_DARK, edgecolor=C_CYAN, linewidth=1.8)
    ax.add_patch(rect_bom)
    ax.text(29, 80, "HARDWARE BILL OF MATERIALS", ha='center', va='center', fontsize=10.5, fontweight='bold', color=C_CYAN)

    bom_items = [
        ("Arduino Uno / Nano MCU", "Atmega328P Board", "Rs. 450", "$5.40"),
        ("Analog Rain / Moisture Sensor", "Nickel Grid + LM393", "Rs. 120", "$1.45"),
        ("Tri-Color Traffic Signal LED", "8mm Green/Yellow/Red", "Rs. 80", "$0.95"),
        ("Active Piezo Buzzer Module", "5V 85dB Audio Alarm", "Rs. 40", "$0.50"),
        ("USB-C 3.1 Data Cable", "Low-Latency Tether", "Rs. 200", "$2.40"),
        ("Breadboard & Jumper Wire Kit", "Interconnects", "Rs. 150", "$1.80"),
        ("Android Phone (Camera + IMU)", "Repurposed Device", "Rs. 0", "$0.00"),
        ("Host Compute (Mac / PC)", "Student Workstation", "Rs. 0", "$0.00"),
    ]

    y_cur = 73
    for name, spec, inr, usd in bom_items:
        ax.text(6.5, y_cur, f"• {name}", fontsize=8.2, fontweight='bold', color=TEXT_WHITE)
        ax.text(32, y_cur, f"({spec})", fontsize=7.2, color=TEXT_MUTED)
        ax.text(48, y_cur, f"{inr}", fontsize=8.2, fontweight='bold', color=C_SKY, ha='right')
        y_cur -= 6.2

    # Total Banner inside BOM
    rect_tot = patches.Rectangle((6, 12), 46, 10, facecolor='#0284c7', edgecolor='none')
    ax.add_patch(rect_tot)
    ax.text(8, 17, "TOTAL PROTOTYPE OUTLAY:", fontsize=9, fontweight='bold', color=TEXT_WHITE)
    ax.text(50, 17, "Rs. 1,040 (~$12.50)", fontsize=11, fontweight='bold', color=TEXT_WHITE, ha='right')

    # Right Card: Commercial Market Comparison Bar Chart
    rect_comp = patches.FancyBboxPatch((58, 8), 38, 76, boxstyle="round,pad=1.2,rounding_size=2",
                                       facecolor=SURFACE_DARK, edgecolor=BORDER_DARK, linewidth=1.5)
    ax.add_patch(rect_comp)
    ax.text(77, 80, "COST COMPARISON", ha='center', va='center', fontsize=10.5, fontweight='bold', color=TEXT_WHITE)

    ax.text(61, 68, "Commercial LiDAR: Rs. 5,00,000+", fontsize=8.2, fontweight='bold', color=C_RED)
    rect_b1 = patches.Rectangle((61, 62), 32, 4, facecolor=C_RED, edgecolor='none')
    ax.add_patch(rect_b1)

    ax.text(61, 52, "Mobileye 8 ADAS: Rs. 1,00,000", fontsize=8.2, fontweight='bold', color=C_AMBER)
    rect_b2 = patches.Rectangle((61, 46), 18, 4, facecolor=C_AMBER, edgecolor='none')
    ax.add_patch(rect_b2)

    ax.text(61, 36, "SpatialSight: Rs. 1,040 (<Rs. 1.1k!)", fontsize=8.2, fontweight='bold', color=C_GREEN)
    rect_b3 = patches.Rectangle((61, 30), 2.5, 4, facecolor=C_GREEN, edgecolor='none')
    ax.add_patch(rect_b3)

    # Big Savings Callout
    rect_save = patches.Rectangle((60, 12), 34, 13, facecolor='#064e3b', edgecolor=C_GREEN, linewidth=1.2)
    ax.add_patch(rect_save)
    ax.text(77, 21, "> 98.5% COST SAVINGS", ha='center', fontsize=10.5, fontweight='bold', color=TEXT_WHITE)
    ax.text(77, 15.5, "Feasible for 2-Wheelers & Auto-Rickshaws", ha='center', fontsize=7.8, color=C_GREEN)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "diagram_budget_bom.png"), facecolor=fig.get_facecolor(), dpi=220)
    plt.close()


def generate_dark_hero_banner():
    """Generates an aesthetic 16:9 hero image for Slide 1 without awkward black borders."""
    fig, ax = plt.subplots(figsize=(8.0, 6.0), dpi=220)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_DARK)

    # Perspective 3D driving corridor grid
    for x in np.linspace(5, 95, 11):
        ax.plot([50, x], [65, 0], color='#1E293B', linewidth=1.5, alpha=0.8)
    for y in [5, 12, 22, 35, 50, 65]:
        ax.plot([0, 100], [y, y], color='#1E293B', linewidth=1.2, alpha=0.8)

    # Dynamic Green & Red Corridors
    ax.plot([50, 25], [65, 0], color=C_CYAN, linewidth=3, alpha=0.95)
    ax.plot([50, 75], [65, 0], color=C_CYAN, linewidth=3, alpha=0.95)
    ax.fill_between([25, 50, 75], [0, 65, 0], color=C_CYAN, alpha=0.18)

    # Radar Rings at Horizon
    for r in [10, 20, 30]:
        circle = patches.Circle((50, 65), r, fill=False, edgecolor=C_SKY, linestyle=':', alpha=0.45, linewidth=1.3)
        ax.add_patch(circle)

    # Center Vehicle Detection Box
    rect_car = patches.Rectangle((42, 38), 16, 12, facecolor='#dc2626', edgecolor=C_RED, linewidth=2)
    ax.add_patch(rect_car)
    ax.text(50, 44, "HAZARD (Z=16.8m)", ha='center', va='center', fontsize=7.5, fontweight='bold', color=TEXT_WHITE)

    # Overlay HUD Telemetry Cards
    badges = [
        ("INFERENCE: 60 FPS (YOLOv8)", 88, C_CYAN),
        ("ROAD FRICTION: μ = 0.52 (WET)", 80, C_AMBER),
        ("ADAPTIVE SAFETY ZONE: 1.6×", 72, C_RED)
    ]
    for b_text, y_pos, b_col in badges:
        r_b = patches.FancyBboxPatch((15, y_pos - 2.5), 70, 5.5, boxstyle="round,pad=0.5",
                                     facecolor=SURFACE_DARK, edgecolor=b_col, linewidth=1.2)
        ax.add_patch(r_b)
        ax.text(50, y_pos, b_text, ha='center', va='center', fontsize=8.5, fontweight='bold', color=TEXT_WHITE)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "hero_presentation_model.png"), facecolor=fig.get_facecolor(), dpi=220)
    plt.close()


if __name__ == "__main__":
    generate_dark_charts()
    generate_dark_architecture_diagram()
    generate_dark_budget_diagram()
    generate_dark_hero_banner()
    print("[SUCCESS] All dark-theme assets regenerated cleanly!")
