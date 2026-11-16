"""Generate a production-quality animated demo GIF for OpsCopilot.

Renders dark-mode UI frames showcasing:
1. Grounded Runbook Q&A + Provenance Citation
2. Strict Zero-Hallucination Refusal Guardrail
3. Autonomous SRE Action Tools (Telemetry Check + Incident Ticketing)
"""

import os
from PIL import Image, ImageDraw, ImageFont

WIDTH = 840
HEIGHT = 540
BG_COLOR = (14, 17, 23)          # Dark background
WINDOW_BAR = (22, 27, 34)        # Window header
CARD_BG = (26, 32, 44)           # Message bubble
USER_BG = (30, 41, 59)           # User bubble
TEXT_WHITE = (240, 246, 252)     # Primary text
TEXT_MUTED = (139, 148, 158)     # Secondary text
ACCENT_GREEN = (46, 160, 67)     # Success green
ACCENT_BLUE = (88, 166, 255)     # User accent blue
ACCENT_AMBER = (210, 153, 34)    # Warning / refusal amber
ACCENT_RED = (248, 81, 73)       # Alert red
TOOL_BG = (19, 24, 32)           # Tool box background

# Fonts
try:
    FONT_TITLE = ImageFont.truetype("segoeui.ttf", 15)
    FONT_MAIN = ImageFont.truetype("segoeui.ttf", 14)
    FONT_CODE = ImageFont.truetype("consola.ttf", 13)
    FONT_SMALL = ImageFont.truetype("segoeui.ttf", 11)
    FONT_BOLD = ImageFont.truetype("segoeuib.ttf", 14)
except Exception:
    FONT_TITLE = ImageFont.load_default()
    FONT_MAIN = ImageFont.load_default()
    FONT_CODE = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()
    FONT_BOLD = ImageFont.load_default()


def draw_window_base() -> Image.Image:
    """Create base canvas with window chrome and header."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Top window bar
    draw.rectangle([(0, 0), (WIDTH, 36)], fill=WINDOW_BAR)
    # Window controls (macOS style dots)
    draw.ellipse([(14, 12), (24, 22)], fill=(255, 95, 86))
    draw.ellipse([(30, 12), (40, 22)], fill=(255, 189, 46))
    draw.ellipse([(46, 12), (56, 22)], fill=(39, 201, 63))

    # Window title
    draw.text((WIDTH // 2 - 170, 9), "OpsCopilot — SRE Incident Assistant (Streamlit :8501)", fill=TEXT_MUTED, font=FONT_TITLE)

    # Top App Header
    draw.rectangle([(0, 36), (WIDTH, 78)], fill=(18, 22, 30))
    draw.text((24, 48), "🤖 OpsCopilot Incident Response Assistant", fill=TEXT_WHITE, font=FONT_BOLD)
    draw.ellipse([(WIDTH - 145, 54), (WIDTH - 137, 62)], fill=ACCENT_GREEN)
    draw.text((WIDTH - 130, 50), "Backend Connected", fill=ACCENT_GREEN, font=FONT_SMALL)

    # Bottom chat input bar
    draw.rectangle([(0, HEIGHT - 52), (WIDTH, HEIGHT)], fill=(18, 22, 30))
    draw.rounded_rectangle([(24, HEIGHT - 44), (WIDTH - 24, HEIGHT - 14)], radius=6, fill=WINDOW_BAR, outline=(48, 54, 61))
    draw.text((38, HEIGHT - 37), "Ask an incident question or trigger SRE actions...", fill=TEXT_MUTED, font=FONT_MAIN)
    draw.text((WIDTH - 55, HEIGHT - 37), "Send ↵", fill=ACCENT_BLUE, font=FONT_SMALL)

    return img


def create_scene_1_frames() -> list[tuple[Image.Image, int]]:
    """Scene 1: Grounded Q&A with real-time streaming and citation."""
    frames = []
    base = draw_window_base()

    # Step 1: User asks question
    f1 = base.copy()
    d1 = ImageDraw.Draw(f1)
    # User bubble
    d1.rounded_rectangle([(WIDTH - 540, 96), (WIDTH - 24, 140)], radius=8, fill=USER_BG, outline=ACCENT_BLUE)
    d1.text((WIDTH - 524, 107), "What is the command to promote the PostgreSQL replica node?", fill=TEXT_WHITE, font=FONT_MAIN)
    frames.append((f1, 1000))

    # Typewriter streaming text lines
    lines = [
        "Based on verified runbooks retrieved from ChromaDB:",
        "1. Isolate the degraded primary to avoid split-brain clustering.",
        "2. Promote synchronous replica command:",
        "   /usr/lib/postgresql/16/bin/pg_ctl promote -D /var/lib/postgresql/16/main",
        "3. Update PgBouncer upstream routing configuration.",
        "[Source: database_failover_runbook.md, Section: 4.2 Promote Replica]"
    ]

    for i in range(1, len(lines) + 1):
        f = f1.copy()
        d = ImageDraw.Draw(f)

        # Assistant bubble
        box_h = 160 + (i * 24)
        d.rounded_rectangle([(24, 156), (WIDTH - 120, box_h)], radius=8, fill=CARD_BG, outline=(48, 54, 61))
        d.text((40, 168), "🤖 OpsCopilot (Streaming via SSE):", fill=ACCENT_BLUE, font=FONT_BOLD)

        y = 196
        for j in range(i):
            line = lines[j]
            if "Source:" in line:
                d.text((40, y), line, fill=ACCENT_GREEN, font=FONT_SMALL)
            elif "pg_ctl" in line:
                d.text((40, y), line, fill=(230, 237, 243), font=FONT_CODE)
            else:
                d.text((40, y), line, fill=TEXT_WHITE, font=FONT_MAIN)
            y += 24

        duration = 500 if i < len(lines) else 2500
        frames.append((f, duration))

    return frames


def create_scene_2_frames() -> list[tuple[Image.Image, int]]:
    """Scene 2: Out-of-domain Zero-Hallucination Refusal Guardrail."""
    frames = []
    base = draw_window_base()

    # User asks out of domain query
    f1 = base.copy()
    d1 = ImageDraw.Draw(f1)
    d1.rounded_rectangle([(WIDTH - 460, 96), (WIDTH - 24, 140)], radius=8, fill=USER_BG, outline=ACCENT_BLUE)
    d1.text((WIDTH - 444, 107), "How do I configure the company 401(k) retirement match?", fill=TEXT_WHITE, font=FONT_MAIN)
    frames.append((f1, 1000))

    # Refusal response
    f2 = f1.copy()
    d2 = ImageDraw.Draw(f2)
    d2.rounded_rectangle([(24, 156), (WIDTH - 180, 270)], radius=8, fill=CARD_BG, outline=(48, 54, 61))
    d2.text((40, 168), "🤖 OpsCopilot (Refusal Guardrail):", fill=ACCENT_AMBER, font=FONT_BOLD)
    d2.text((40, 200), "I cannot find the answer in the provided runbooks.", fill=TEXT_WHITE, font=FONT_MAIN)

    # Refusal badge
    d2.rounded_rectangle([(40, 230), (390, 256)], radius=4, fill=(45, 30, 15), outline=ACCENT_AMBER)
    d2.text((50, 236), "🛡️ ZERO-HALLUCINATION GUARDRAIL ACTIVE", fill=ACCENT_AMBER, font=FONT_SMALL)
    frames.append((f2, 2500))

    return frames


def create_scene_3_frames() -> list[tuple[Image.Image, int]]:
    """Scene 3: Autonomous SRE Action Tools (Telemetry check & Ticket creation)."""
    frames = []
    base = draw_window_base()

    # User request
    f1 = base.copy()
    d1 = ImageDraw.Draw(f1)
    d1.rounded_rectangle([(WIDTH - 610, 96), (WIDTH - 24, 140)], radius=8, fill=USER_BG, outline=ACCENT_BLUE)
    d1.text((WIDTH - 594, 107), "Database latency is spiking. Check postgres-primary and file an urgent ticket.", fill=TEXT_WHITE, font=FONT_MAIN)
    frames.append((f1, 1000))

    # Tool 1: Telemetry check
    f2 = f1.copy()
    d2 = ImageDraw.Draw(f2)
    d2.rounded_rectangle([(24, 156), (WIDTH - 60, 230)], radius=6, fill=TOOL_BG, outline=(56, 139, 253))
    d2.text((38, 166), "⚡ Action Executed: get_service_status(service_name='postgres-primary')", fill=ACCENT_BLUE, font=FONT_CODE)
    d2.text((38, 192), "-> Status: DOWN | Latency: 5200.0ms | Error Rate: 99.4% | Alert: Patroni heartbeat expired", fill=ACCENT_RED, font=FONT_SMALL)
    frames.append((f2, 1200))

    # Tool 2: Incident Ticket Created
    f3 = f2.copy()
    d3 = ImageDraw.Draw(f3)
    d3.rounded_rectangle([(24, 240), (WIDTH - 60, 314)], radius=6, fill=TOOL_BG, outline=ACCENT_GREEN)
    d3.text((38, 250), "⚡ Action Executed: create_incident_ticket(title='postgres-primary outage', severity='P0')", fill=ACCENT_GREEN, font=FONT_CODE)
    d3.text((38, 276), "-> Incident Ticket INC-9812 (P0) opened | Escalated to: VP Infra & Primary On-Call", fill=TEXT_WHITE, font=FONT_SMALL)
    frames.append((f3, 1400))

    # Final Assistant Synthesis
    f4 = f3.copy()
    d4 = ImageDraw.Draw(f4)
    d4.rounded_rectangle([(24, 326), (WIDTH - 60, 440)], radius=8, fill=CARD_BG, outline=(48, 54, 61))
    d4.text((38, 338), "🤖 OpsCopilot Final Synthesis:", fill=ACCENT_BLUE, font=FONT_BOLD)
    d4.text((38, 368), "Service postgres-primary is confirmed DOWN (port 5432 refused, latency 5200ms).", fill=TEXT_WHITE, font=FONT_MAIN)
    d4.text((38, 394), "Incident ticket INC-9812 (P0) successfully dispatched. Failover runbook recommendations ready.", fill=ACCENT_GREEN, font=FONT_MAIN)
    frames.append((f4, 3200))

    return frames


def build_gif() -> str:
    os.makedirs("docs", exist_ok=True)
    output_path = os.path.join("docs", "demo.gif")

    print("[1/4] Generating Scene 1 frames (Grounded Q&A + Citation)...")
    s1 = create_scene_1_frames()

    print("[2/4] Generating Scene 2 frames (Refusal Guardrail)...")
    s2 = create_scene_2_frames()

    print("[3/4] Generating Scene 3 frames (Autonomous Tools)...")
    s3 = create_scene_3_frames()

    all_frames_with_durations = s1 + s2 + s3
    images = [f[0] for f in all_frames_with_durations]
    durations = [f[1] for f in all_frames_with_durations]

    print(f"[4/4] Compiling {len(images)} frames into '{output_path}'...")
    images[0].save(
        output_path,
        save_all=True,
        append_images=images[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )

    file_size_kb = os.path.getsize(output_path) / 1024
    print(f"[SUCCESS] Demo GIF generated successfully at: {output_path} ({file_size_kb:.1f} KB)")
    return output_path


if __name__ == "__main__":
    build_gif()
