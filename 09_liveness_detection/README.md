# 🎭 Project 09: Liveness Detection Results
<img width="1308" height="585" alt="Landing_gage" src="https://github.com/user-attachments/assets/ca0e1393-f9b4-472c-88f7-545aac4435ea" />

<img width="1312" height="608" alt="Liveness_detection_steps" src="https://github.com/user-attachments/assets/7c412428-08bf-4b8c-9a9c-c3807fe24b97" />

<img width="1355" height="598" alt="Captured_results" src="https://github.com/user-attachments/assets/cb02c4bc-c7d4-424e-97f5-4c4d2a526e31" />


<img width="1317" height="583" alt="Liveness_results" src="https://github.com/user-attachments/assets/4b21eb14-68ae-4b2c-9edd-07ba568371f9" />

<img width="1320" height="575" alt="How_it_works" src="https://github.com/user-attachments/assets/7b16fde5-1ee0-4d43-92e7-0318071102d7" />

<img width="1258" height="566" alt="Wrong_step _follow" src="https://github.com/user-attachments/assets/955346c6-ff8d-4d36-ba29-0f42ba252584" />

<img width="1329" height="553" alt="Wrong_step _follow2" src="https://github.com/user-attachments/assets/6d67bb8d-6f66-430b-8a63-ff0fabc168b2" />

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
