"""
Automated screenshot generator for all 8 modules.

Uses Playwright + Chromium to:
    1. Launch each Streamlit app
    2. Take screenshots of key views (with fake camera feed)
    3. Save them under docs/screenshots/<module>/
    4. Auto-update each module's README.md with image references

Usage:
    python tools/screenshot_generator.py             # all modules
    python tools/screenshot_generator.py 01 04       # specific modules
"""
import re
import subprocess
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).parent.parent.resolve()
SHOTS_DIR = ROOT / "docs" / "screenshots"
PORT = 8502
URL = f"http://localhost:{PORT}"


# ---------- Pre-cleanup: delete stale DBs so fresh demo data gets created ----------
PRE_CLEANUP = {
    "04_biometric_verification": ["data/biometric.db"],
    "07_auth_rbac": ["data/auth.db"],
    "08_audit_logs": ["data/audit.db"],
}


# ---------- Screenshot plans per module ----------
PLANS = {
    "01_face_capture_recognition": [
        {"name": "01_live_capture.png", "pre": []},
    ],
    "02_fingerprint_scanner": [
        {"name": "02_device_status.png", "pre": []},
        {"name": "02_capture_success.png", "pre": [
            {"type": "click_button", "name": "🔗 Connect"},
            {"type": "wait", "sec": 2},
            {"type": "click_button", "name": "👆 Place Finger"},
            {"type": "wait", "sec": 1},
            {"type": "click_button", "name": "🖐️ Capture Fingerprint"},
            {"type": "wait", "sec": 3},
        ]},
    ],
    "03_quality_indicators": [
        {"name": "03_live_capture.png", "pre": []},
    ],
    "04_biometric_verification": [
        {"name": "04_enroll.png", "pre": []},
        {"name": "04_verify.png", "pre": [
            {"type": "click_tab", "name": "🎯 Verify"},
            {"type": "wait", "sec": 1},
        ]},
        {"name": "04_history.png", "pre": [
            {"type": "click_tab", "name": "📜 History"},
            {"type": "wait", "sec": 1},
        ]},
    ],
    "05_pdf_signing": [
        {"name": "05_upload_sign.png", "pre": []},
        {"name": "05_demo_pdf.png", "pre": [
            {"type": "click_tab", "name": "🧪 Demo PDF"},
            {"type": "wait", "sec": 1},
        ]},
    ],
    "06_signature_verification": [
        {"name": "06_upload.png", "pre": []},
        {"name": "06_fixtures.png", "pre": [
            {"type": "click_tab", "name": "🧪 Test with Fixtures"},
            {"type": "wait", "sec": 1},
        ]},
        {"name": "06_signed_valid.png", "pre": [
            {"type": "click_tab", "name": "🧪 Test with Fixtures"},
            {"type": "wait", "sec": 1},
            {"type": "click_button", "name": "Verify signed"},
            {"type": "wait", "sec": 4},
        ]},
    ],
    "07_auth_rbac": [
        {"name": "07_login.png", "pre": []},
        {"name": "07_dashboard.png", "pre": [
            {"type": "fill", "label": "Email", "value": "admin@portfolio.local"},
            {"type": "fill", "label": "Password", "value": "Admin@12345"},
            {"type": "click_button", "name": "Login"},
            {"type": "wait", "sec": 4},
        ]},
    ],
    "08_audit_logs": [
        {"name": "08_empty.png", "pre": []},
        {"name": "08_dashboard.png", "pre": [
            {"type": "click_button", "name": "🎲 Generate demo data"},
            {"type": "wait", "sec": 4},
        ]},
    ],
}


# ---------- Helpers ----------
def wait_for_server(url: str, timeout: int = 30) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def start_streamlit(module_dir: Path) -> subprocess.Popen:
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


def stop_streamlit(proc: subprocess.Popen):
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:
        proc.kill()


def _do_action(page, action):
    t = action["type"]
    try:
        if t == "click_text":
            page.get_by_text(action["text"], exact=False).first.click(timeout=5000)
        elif t == "click_button":
            page.get_by_role("button", name=action["name"]).first.click(timeout=5000)
        elif t == "click_tab":
            page.get_by_role("tab", name=action["name"]).first.click(timeout=5000)
        elif t == "fill":
            page.get_by_label(action["label"], exact=False).first.fill(action["value"])
        elif t == "wait":
            time.sleep(action["sec"])
    except Exception as e:
        print(f"      ⚠ action failed ({t}): {str(e)[:120]}")


# ---------- README updater ----------
def update_readme(module_key: str, shot_names: list):
    readme = ROOT / module_key / "README.md"
    if not readme.exists():
        return

    content = readme.read_text(encoding="utf-8")

    section = "\n## 📸 Screenshots\n\n"
    for shot in shot_names:
        title = shot.replace(".png", "").replace("_", " ").title()
        section += f"### {title}\n\n"
        section += f"![{title}](../docs/screenshots/{module_key}/{shot})\n\n"

    marker = "## 📸 Screenshots"
    if marker in content:
        pattern = r"## 📸 Screenshots.*?(?=\n## |\Z)"
        content = re.sub(pattern, section.strip() + "\n", content, flags=re.DOTALL)
    else:
        content = content.rstrip() + "\n" + section

    readme.write_text(content, encoding="utf-8")


# ---------- Main loop ----------
def run_module(module_key: str):
    plan = PLANS.get(module_key)
    if not plan:
        print(f"  (no plan for {module_key})")
        return

    module_dir = ROOT / module_key
    if not (module_dir / "app.py").exists():
        print(f"  ERROR: {module_dir}/app.py not found")
        return

    out_dir = SHOTS_DIR / module_key
    out_dir.mkdir(parents=True, exist_ok=True)

    # Clean stale DB
    for rel in PRE_CLEANUP.get(module_key, []):
        p = module_dir / rel
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

    print(f"\n=== {module_key} ===")
    proc = start_streamlit(module_dir)

    if not wait_for_server(URL):
        print("  ERROR: streamlit did not start in time")
        stop_streamlit(proc)
        return

    print("  Server up. Running browser...")

    shot_names = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                args=[
                    "--use-fake-ui-for-media-stream",
                    "--use-fake-device-for-media-stream",
                ],
                headless=True,
            )
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                permissions=["camera"],
            )
            page = context.new_page()
            page.goto(URL, wait_until="networkidle", timeout=30000)
            time.sleep(4)

            for shot in plan:
                for action in shot.get("pre", []):
                    _do_action(page, action)
                time.sleep(1.5)

                out_path = out_dir / shot["name"]
                page.screenshot(path=str(out_path), full_page=False)
                print(f"    ✓ {shot['name']}  ({out_path.stat().st_size // 1024} KB)")
                shot_names.append(shot["name"])

            browser.close()
    except Exception as e:
        print(f"  ERROR: {e}")
    finally:
        stop_streamlit(proc)

    if shot_names:
        update_readme(module_key, shot_names)
        print(f"  ✓ README updated with {len(shot_names)} screenshots")


def main():
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)

    targets = sys.argv[1:] if len(sys.argv) > 1 else list(PLANS.keys())

    # Allow shorthand "01" -> "01_face_capture_recognition"
    expanded = []
    for t in targets:
        if t.isdigit():
            match = next((k for k in PLANS if k.startswith(f"{t}_")), None)
            if match:
                expanded.append(match)
            else:
                print(f"Unknown module: {t}")
        else:
            expanded.append(t)

    for module_key in expanded:
        try:
            run_module(module_key)
        except KeyboardInterrupt:
            print("\nInterrupted.")
            return
        except Exception as e:
            print(f"  FATAL for {module_key}: {e}")

    print("\n✅ Screenshot generation complete.")
    print(f"   Output: {SHOTS_DIR}")


if __name__ == "__main__":
    main()