"""
Automated screenshot generator for all 8 modules.

Features:
    - Converts a face image to Y4M and feeds it to Chromium as fake webcam
      (so camera widgets show a REAL FACE, not the default green pattern)
    - Clicks "Take Photo" on camera widgets (st.camera_input)
    - Clicks buttons, fills forms, navigates tabs
    - Captures comprehensive test cases per module
    - Auto-updates each module's README with image references
    - Screenshot size validation with retry

Usage:
    python tools/screenshot_generator.py             # all modules
    python tools/screenshot_generator.py 01 04       # specific modules
    python tools/screenshot_generator.py --debug 01  # verbose
"""
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


ROOT = Path(__file__).parent.parent.resolve()
SHOTS_DIR = ROOT / "docs" / "screenshots"
FACES_DIR = ROOT / "tools" / "sample_faces"
PORT = 8502
URL = f"http://localhost:{PORT}"

DEBUG = "--debug" in sys.argv
MIN_VALID_SIZE_KB = 15


# ---------- Pre-cleanup: delete stale DBs ----------
PRE_CLEANUP = {
    "04_biometric_verification": ["data/biometric.db"],
    "07_auth_rbac": ["data/auth.db"],
    "08_audit_logs": ["data/audit.db"],
}


# ---------- Find a face image ----------
def find_face_image():
    for d in (FACES_DIR, ROOT / "01_face_capture_recognition" / "data" / "registered_faces"):
        if d.exists():
            for ext in ("jpg", "jpeg", "png"):
                files = list(d.glob(f"*.{ext}"))
                if files:
                    return str(files[0])
    return None


FACE_IMG = find_face_image()


# ---------- Convert face image to Y4M video ----------
def image_to_y4m(image_path, output_path, width=640, height=480, frames=50):
    """
    Convert a still image into a looping Y4M video file.
    Chromium's --use-file-for-fake-video-capture expects Y4M.
    """
    img = Image.open(image_path).convert("RGB")
    img = img.resize((width, height), Image.LANCZOS)
    rgb = np.array(img)

    r = rgb[:, :, 0].astype(float)
    g = rgb[:, :, 1].astype(float)
    b = rgb[:, :, 2].astype(float)

    # RGB → YUV
    y = np.clip(0.299 * r + 0.587 * g + 0.114 * b, 0, 255).astype(np.uint8)
    u = np.clip(-0.169 * r - 0.331 * g + 0.500 * b + 128, 0, 255).astype(np.uint8)
    v = np.clip(0.500 * r - 0.419 * g - 0.081 * b + 128, 0, 255).astype(np.uint8)

    # 4:2:0 chroma subsampling
    u_sub = u[::2, ::2]
    v_sub = v[::2, ::2]

    header = f"YUV4MPEG2 W{width} H{height} F25:1 Ip A1:1 C420jpeg\n".encode()
    frame_header = b"FRAME\n"
    frame_payload = y.tobytes() + u_sub.tobytes() + v_sub.tobytes()

    with open(output_path, "wb") as f:
        f.write(header)
        for _ in range(frames):
            f.write(frame_header)
            f.write(frame_payload)


def prepare_y4m():
    """Generate Y4M once and return path."""
    if not FACE_IMG:
        return None

    y4m_path = FACES_DIR / "face1.y4m"
    if y4m_path.exists() and y4m_path.stat().st_size > 100_000:
        return str(y4m_path)

    log(f"  Converting face image to Y4M: {y4m_path.name}")
    FACES_DIR.mkdir(parents=True, exist_ok=True)
    image_to_y4m(FACE_IMG, str(y4m_path))
    size_mb = y4m_path.stat().st_size / (1024 * 1024)
    log(f"  Y4M created ({size_mb:.1f} MB)")
    return str(y4m_path)


# ---------- Screenshot plans ----------
PLANS = {
    "01_face_capture_recognition": {
        "wait_text": "Live Face Capture",
        "shots": [
            {"name": "01_initial.png", "steps": []},
            {"name": "01_live_capture.png", "steps": [
                {"type": "take_camera_photo"},
                {"type": "wait", "sec": 10},
            ]},
        ],
    },
    "02_fingerprint_scanner": {
        "wait_text": "Fingerprint Scanner",
        "shots": [
            {"name": "02_initial.png", "steps": []},
            {"name": "02_connected.png", "steps": [
                {"type": "click_button", "text": "Connect"},
                {"type": "wait", "sec": 3},
            ]},
            {"name": "02_finger_no_place.png", "steps": [
                {"type": "click_button", "text": "Capture Fingerprint"},
                {"type": "wait", "sec": 3},
            ]},
            {"name": "02_capture_success.png", "steps": [
                {"type": "click_button", "text": "Place Finger"},
                {"type": "wait", "sec": 1},
                {"type": "click_button", "text": "Capture Fingerprint"},
                {"type": "wait", "sec": 4},
            ]},
        ],
    },
    "03_quality_indicators": {
        "wait_text": "Quality Indicators",
        "shots": [
            {"name": "03_initial.png", "steps": []},
            {"name": "03_live_capture.png", "steps": [
                {"type": "take_camera_photo"},
                {"type": "wait", "sec": 12},
            ]},
        ],
    },
    "04_biometric_verification": {
        "wait_text": "Biometric Verification Engine",
        "shots": [
            {"name": "04_enroll_tab.png", "steps": []},
            {"name": "04_verify_tab.png", "steps": [
                {"type": "click_tab", "text": "Verify"},
                {"type": "wait", "sec": 3},
            ]},
            {"name": "04_history_tab.png", "steps": [
                {"type": "click_tab", "text": "History"},
                {"type": "wait", "sec": 3},
            ]},
        ],
    },
    "05_pdf_signing": {
        "wait_text": "PDF Digital Signature",
        "shots": [
            {"name": "05_upload_tab.png", "steps": []},
            {"name": "05_demo_tab.png", "steps": [
                {"type": "click_tab", "text": "Demo"},
                {"type": "wait", "sec": 3},
            ]},
        ],
    },
    "06_signature_verification": {
        "wait_text": "PDF Signature Verification",
        "shots": [
            {"name": "06_upload_tab.png", "steps": []},
            {"name": "06_fixtures_tab.png", "steps": [
                {"type": "click_tab", "text": "Fixtures"},
                {"type": "wait", "sec": 3},
            ]},
            {"name": "06_verify_signed.png", "steps": [
                {"type": "click_tab", "text": "Fixtures"},
                {"type": "wait", "sec": 2},
                {"type": "click_button", "text": "Verify signed"},
                {"type": "wait", "sec": 5},
            ]},
            {"name": "06_verify_tampered.png", "steps": [
                {"type": "click_button", "text": "Verify tampered"},
                {"type": "wait", "sec": 5},
            ]},
        ],
    },
    "07_auth_rbac": {
        "wait_text": "Authentication",
        "shots": [
            {"name": "07_login.png", "steps": []},
            {"name": "07_dashboard.png", "steps": [
                {"type": "fill", "label": "Email", "value": "admin@portfolio.local"},
                {"type": "fill", "label": "Password", "value": "Admin@12345"},
                {"type": "click_button", "text": "Login"},
                {"type": "wait", "sec": 5},
            ]},
            {"name": "07_audit_logs.png", "steps": [
                {"type": "click_sidebar", "text": "Audit Logs"},
                {"type": "wait", "sec": 3},
            ]},
        ],
    },
    "08_audit_logs": {
        "wait_text": "Audit Logs",
        "shots": [
            {"name": "08_empty_state.png", "steps": []},
            {"name": "08_dashboard.png", "steps": [
                {"type": "click_button", "text": "Generate demo data"},
                {"type": "wait", "sec": 6},
            ]},
            {"name": "08_event_log.png", "steps": [
                {"type": "click_tab", "text": "Event Log"},
                {"type": "wait", "sec": 3},
            ]},
            {"name": "08_export.png", "steps": [
                {"type": "click_tab", "text": "Export"},
                {"type": "wait", "sec": 3},
            ]},
        ],
    },
}


# ---------- Helpers ----------
def log(msg):
    print(msg, flush=True)


def wait_for_server(url, timeout=45):
    start = time.time()
    while time.time() - start < timeout:
        try:
            if requests.get(url, timeout=2).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def start_streamlit(module_dir):
    return subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", str(PORT),
            "--server.headless", "true",
            "--server.runOnSave", "false",
            "--browser.gatherUsageStats", "false",
        ],
        cwd=str(module_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_streamlit(proc):
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:
        proc.kill()


def wait_for_app(page, wait_text, timeout=40000):
    try:
        page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=timeout)
    except PWTimeout:
        log("    ⚠ app container not found")

    if wait_text:
        try:
            page.wait_for_selector(f'text={wait_text}', timeout=timeout)
        except PWTimeout:
            log(f"    ⚠ wait_text not found: '{wait_text}'")

    try:
        page.wait_for_selector('[data-testid="stSpinner"]', state="detached", timeout=8000)
    except PWTimeout:
        pass

    page.wait_for_timeout(3000)


# ---------- Camera handling ----------
def take_camera_photo(page, timeout=10000):
    """Click 'Take Photo' inside st.camera_input widget."""
    try:
        page.wait_for_selector('[data-testid="stCameraInput"]', timeout=timeout)
    except PWTimeout:
        log("    ⚠ camera widget not found")
        return False

    # Give the video stream time to render the fake feed
    page.wait_for_timeout(3500)

    selectors = [
        'button:has-text("Take Photo")',
        'button:has-text("Take photo")',
        'button:has-text("Take")',
        '[data-testid="stCameraInputButton"]',
        '[data-testid="stCameraInput"] button',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                loc.first.click(timeout=3000)
                log(f"    ✓ clicked camera button ({sel})")
                page.wait_for_timeout(2500)
                return True
        except Exception:
            continue

    log("    ⚠ Take Photo button not found")
    return False


def click_button(page, text):
    try:
        page.locator(f'button:has-text("{text}")').first.click(timeout=6000)
        return True
    except Exception:
        try:
            page.get_by_role(
                "button", name=re.compile(re.escape(text), re.IGNORECASE)
            ).first.click(timeout=5000)
            return True
        except Exception:
            log(f"    ⚠ button not found: '{text}'")
            return False


def click_tab(page, text):
    try:
        page.locator(f'[role="tab"]:has-text("{text}")').first.click(timeout=6000)
        return True
    except Exception:
        try:
            page.locator(f'button[role="tab"]:has-text("{text}")').first.click(timeout=5000)
            return True
        except Exception:
            log(f"    ⚠ tab not found: '{text}'")
            return False


def fill_by_label(page, label, value):
    try:
        page.get_by_label(re.compile(re.escape(label), re.IGNORECASE)).first.fill(
            value, timeout=6000
        )
        return True
    except Exception:
        log(f"    ⚠ input not found: '{label}'")
        return False


def click_sidebar_item(page, text):
    try:
        page.locator(
            f'[data-testid="stSidebar"] label:has-text("{text}")'
        ).first.click(timeout=6000)
        return True
    except Exception:
        try:
            page.locator(
                f'[data-testid="stSidebar"] *:has-text("{text}")'
            ).first.click(timeout=4000)
            return True
        except Exception:
            log(f"    ⚠ sidebar item not found: '{text}'")
            return False


def do_step(page, step):
    t = step["type"]
    if t == "wait":
        page.wait_for_timeout(int(step["sec"] * 1000))
    elif t == "click_button":
        click_button(page, step["text"])
        page.wait_for_timeout(1500)
    elif t == "click_tab":
        click_tab(page, step["text"])
        page.wait_for_timeout(2500)
    elif t == "fill":
        fill_by_label(page, step["label"], step["value"])
        page.wait_for_timeout(500)
    elif t == "click_sidebar":
        click_sidebar_item(page, step["text"])
        page.wait_for_timeout(2000)
    elif t == "take_camera_photo":
        take_camera_photo(page)


def update_readme(module_key, shot_names):
    readme = ROOT / module_key / "README.md"
    if not readme.exists():
        log(f"    ⚠ README missing: {readme}")
        return

    content = readme.read_text(encoding="utf-8")
    lines = ["## 📸 Screenshots", ""]
    for shot in shot_names:
        title = shot.replace(".png", "").replace("_", " ").title()
        lines.append(f"### {title}")
        lines.append("")
        lines.append(f"![{title}](../docs/screenshots/{module_key}/{shot})")
        lines.append("")
    section = "\n".join(lines).rstrip() + "\n"

    for marker in ["## 📸 Screenshots", "## Screenshots", "## 📷 Screenshots"]:
        if marker in content:
            start = content.index(marker)
            rest = content[start + len(marker):]
            next_h = re.search(r"\n## ", rest)
            end = start + len(marker) + (next_h.start() if next_h else len(rest))
            content = content[:start] + section + content[end:]
            readme.write_text(content, encoding="utf-8")
            log("    ✓ README updated (replaced)")
            return

    content = content.rstrip() + "\n\n" + section
    readme.write_text(content, encoding="utf-8")
    log("    ✓ README updated (appended)")


def run_module(module_key, y4m_path):
    plan = PLANS.get(module_key)
    if not plan:
        log(f"  (no plan for {module_key})")
        return

    module_dir = ROOT / module_key
    if not (module_dir / "app.py").exists():
        log(f"  ERROR: {module_dir}/app.py not found")
        return

    out_dir = SHOTS_DIR / module_key
    out_dir.mkdir(parents=True, exist_ok=True)

    for rel in PRE_CLEANUP.get(module_key, []):
        p = module_dir / rel
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

    log(f"\n=== {module_key} ===")
    proc = start_streamlit(module_dir)

    if not wait_for_server(URL):
        log("  ERROR: streamlit did not start")
        stop_streamlit(proc)
        return

    log("  Server up. Browser starting...")
    shot_names = []

    try:
        with sync_playwright() as p:
            # Build browser args
            browser_args = [
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--no-sandbox",
            ]
            if y4m_path:
                # THE KEY FLAG — feeds our face image as the webcam
                browser_args.append(f"--use-file-for-fake-video-capture={y4m_path}")

            browser = p.chromium.launch(args=browser_args, headless=True)

            context = browser.new_context(
                viewport={"width": 1440, "height": 1000},
                permissions=["camera", "microphone"],
                ignore_https_errors=True,
            )
            page = context.new_page()

            page.goto(URL, wait_until="domcontentloaded", timeout=40000)
            wait_for_app(page, plan["wait_text"])
            log("  Streamlit ready.")

            if DEBUG:
                try:
                    page.screenshot(path=str(out_dir / "_debug_page.png"), full_page=True)
                except Exception:
                    pass

            for shot in plan["shots"]:
                log(f"  → {shot['name']}")
                for step in shot.get("steps", []):
                    if DEBUG:
                        log(f"      step: {step}")
                    try:
                        do_step(page, step)
                    except Exception as e:
                        log(f"      ⚠ step failed: {str(e)[:120]}")

                page.wait_for_timeout(800)
                out_path = out_dir / shot["name"]
                try:
                    page.screenshot(path=str(out_path), full_page=False)
                    size_kb = out_path.stat().st_size // 1024
                    if size_kb < MIN_VALID_SIZE_KB:
                        log(f"    ⚠ suspicious ({size_kb} KB) — retry in 5s")
                        page.wait_for_timeout(5000)
                        page.screenshot(path=str(out_path), full_page=False)
                        size_kb = out_path.stat().st_size // 1024
                    log(f"    ✓ {size_kb} KB")
                    shot_names.append(shot["name"])
                except Exception as e:
                    log(f"    ✗ screenshot failed: {e}")

            browser.close()
    except Exception as e:
        log(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        stop_streamlit(proc)

    if shot_names:
        update_readme(module_key, shot_names)


def main():
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    targets = args if args else list(PLANS.keys())

    expanded = []
    for t in targets:
        if t.isdigit():
            match = next((k for k in PLANS if k.startswith(f"{t}_")), None)
            if match:
                expanded.append(match)
            else:
                log(f"Unknown module: {t}")
        else:
            expanded.append(t)

    if FACE_IMG:
        log(f"Face image: {FACE_IMG}")
    else:
        log("⚠ No face image found. Place one at: tools/sample_faces/face1.jpg")

    y4m_path = prepare_y4m()
    if y4m_path:
        log(f"Y4M video: {y4m_path}")
    else:
        log("⚠ Proceeding without Y4M — camera will show Chromium's default pattern.")

    for module_key in expanded:
        try:
            run_module(module_key, y4m_path)
        except KeyboardInterrupt:
            log("\nInterrupted.")
            return
        except Exception as e:
            log(f"  FATAL for {module_key}: {e}")

    log("\n✅ Done.")
    log(f"   Screenshots: {SHOTS_DIR}")


if __name__ == "__main__":
    main()