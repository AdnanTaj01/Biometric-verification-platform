# Project 09: Liveness Detection

A standalone Streamlit demo for a three-step liveness challenge. It validates each camera capture, then reports blink, head-movement, and image-texture signals separately.

**SRS coverage:** FR-05. Liveness is reported independently from face matching; identity matching is handled by other modules in this portfolio.

## Challenge Flow

Complete the guided capture steps in order:

1. **Eyes open:** the app detects a face and checks that the average eye aspect ratio (EAR) is at least `0.20`.
2. **Eyes closed:** the app checks that the average EAR is at most `0.18`.
3. **Head turned:** the app checks that the nose offset is at least `15%` of the measured face width.

If a capture does not pass its step, the app displays a reason and asks you to retake it. After all three captures pass, open the **Result** tab for the overall analysis. Use **Reset all photos** or **Try again with new photos** to start another challenge.

## Analysis Signals

The final analysis checks the accepted captures for:

| Signal | Analysis |
|---|---|
| Blink | Change in eye aspect ratio between the eyes-open and eyes-closed captures |
| Head movement | Nose-tip displacement between the front-facing and turned captures |
| Texture | Laplacian variance and FFT peak ratio, evaluated for all three face regions |

The score adds `0.40` for a detected blink, `0.30` for head movement, and `0.30` when all three texture checks pass. The app reports **LIVE** when the score is at least `0.50` and either blink or head movement is detected. The score is a heuristic, not a calibrated probability.

## Setup

Run these commands from this folder in PowerShell:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install streamlit==1.32.0 numpy==1.26.4 pillow==10.2.0 opencv-python==4.9.0.80 mediapipe==0.10.14
```

The current `requirements.txt` contains `pip install` shell commands rather than standard requirements-file entries, so `pip install -r requirements.txt` will not work with that file as written. The command above installs the same pinned packages without modifying it.

## Run

```powershell
python -m streamlit run app.py
```

Allow camera access in your browser. Use consistent lighting and keep the same person and camera distance across all three captures.

## Tests

Install pytest if it is not already available in the environment, then run:

```powershell
python -m pip install pytest
python -m pytest -q test_liveness.py
```

The tests use synthetic image data and do not require a webcam. Face-detection behavior depends on MediaPipe being installed.

## Files

- `app.py` — Streamlit guided capture and result interface.
- `liveness_engine.py` — face landmarks, per-step validation, and liveness signal analysis.
- `test_liveness.py` — automated tests for the liveness engine.
- `requirements.txt` — pinned runtime dependencies, currently written as install commands.

## Limitations and Privacy

This is an educational demo, not a certified presentation-attack detection system. Texture checks and landmark thresholds can produce false positives or false negatives; passing the challenge does not prove identity or guarantee that a capture is live. Do not use this module as the sole basis for authentication, identity verification, or access decisions.

The app keeps captured frames in the active Streamlit session for the challenge and does not intentionally write them to disk. Run it only in an environment where you trust the host handling the camera images.
