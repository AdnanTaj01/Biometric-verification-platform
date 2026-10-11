"""
Enroll a new identity from a reference image.
Usage:
    python enroll.py --name "Ali Khan" --image path/to/photo.jpg

Covers SRS requirement FR-02 (Test Identity Registration) — CLI version.
"""
import argparse
import cv2
from pathlib import Path

from face_engine import (
    detect_faces,
    get_largest_face,
    load_embeddings,
    save_embeddings,
)


def enroll(name: str, image_path: str):
    print(f"[*] Loading image: {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        print(f"[!] Could not read image: {image_path}")
        return False

    print("[*] Detecting faces...")
    faces = detect_faces(image)
    if not faces:
        print("[!] No face detected in image.")
        return False

    if len(faces) > 1:
        print(f"[!] Warning: {len(faces)} faces detected. Using the largest one.")

    face = get_largest_face(faces)
    print(f"[+] Face detected. Embedding shape: {face.embedding.shape}")

    # Save reference image
    ref_dir = Path("data/registered_faces")
    ref_dir.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace(" ", "_").replace("/", "_")
    ref_path = ref_dir / f"{safe_name}.jpeg"
    cv2.imwrite(str(ref_path), image)
    print(f"[+] Reference image saved: {ref_path}")

    # Save embedding
    registered = load_embeddings()
    if name in registered:
        print(f"[i] Identity '{name}' already exists. Overwriting.")
    registered[name] = face.embedding
    save_embeddings(registered)
    print(f"[+] Embedding saved. Total registered: {len(registered)}")
    print(f"[+] Enrolled identities: {list(registered.keys())}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enroll a new face identity.")
    parser.add_argument("--name", required=True, help="Identity display name")
    parser.add_argument("--image", required=True, help="Path to reference image")
    args = parser.parse_args()

    success = enroll(args.name, args.image)
    if success:
        print("\n✅ Enrollment successful!")
    else:
        print("\n❌ Enrollment failed.")