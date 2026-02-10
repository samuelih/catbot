#!/usr/bin/env python3
"""
Camera Test Script

Tests the IMX219-160 CSI camera by capturing frames and optionally
running cat detection.

    python3 scripts/diagnostics/test_camera.py
    python3 scripts/diagnostics/test_camera.py --detect
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def test_basic_capture():
    """Test basic camera capture."""
    print("Testing basic camera capture...")
    from src.camera.capture import Camera

    camera = Camera(use_jetson_utils=False)

    if not camera.is_open():
        print("[FAIL] Camera failed to open!")
        return False

    # Capture 10 frames and measure FPS
    frames = 0
    start = time.time()
    for _ in range(10):
        frame = camera.capture()
        if frame is not None:
            frames += 1

    elapsed = time.time() - start
    camera.close()

    if frames == 0:
        print("[FAIL] No frames captured!")
        return False

    fps = frames / elapsed
    print(f"[OK] Captured {frames}/10 frames in {elapsed:.2f}s ({fps:.1f} FPS)")
    print(f"[OK] Frame shape: {frame.shape}")
    return True


def test_jetson_capture():
    """Test camera capture via jetson_utils."""
    print("Testing jetson_utils camera capture...")
    try:
        from jetson_utils import videoSource
        camera = videoSource("csi://0")

        frames = 0
        start = time.time()
        for _ in range(10):
            img = camera.Capture()
            if img is not None:
                frames += 1

        elapsed = time.time() - start

        if frames == 0:
            print("[FAIL] No frames captured via jetson_utils!")
            return False

        fps = frames / elapsed
        print(f"[OK] Captured {frames}/10 frames in {elapsed:.2f}s ({fps:.1f} FPS)")
        print(f"[OK] Image: {img.width}x{img.height}")
        return True

    except ImportError:
        print("[SKIP] jetson_utils not installed")
        return True
    except Exception as e:
        print(f"[FAIL] jetson_utils capture error: {e}")
        return False


def test_detection():
    """Test cat detection on camera feed."""
    print("Testing cat detection (this may take minutes on first run)...")
    try:
        from jetson_utils import videoSource
        from src.camera.detector import CatDetector

        camera = videoSource("csi://0")
        detector = CatDetector(threshold=0.3)

        print("Running detection for 30 seconds...")
        print("Point the camera at a cat (or a picture of a cat) to test.")
        print("Press Ctrl+C to stop.")
        print()

        start = time.time()
        frame_count = 0

        while time.time() - start < 30:
            img = camera.Capture()
            if img is None:
                continue

            detections = detector.detect_all(img)
            frame_count += 1

            if detections:
                for det in detections:
                    print(f"  Detected: {det.class_name} "
                          f"(confidence={det.confidence:.2f}, "
                          f"pos=({det.center_x:.0f},{det.center_y:.0f}))")

            if frame_count % 30 == 0:
                fps = detector.get_fps()
                print(f"  ... {frame_count} frames processed, "
                      f"detection FPS: {fps:.1f}")

        fps = frame_count / (time.time() - start)
        print(f"\n[OK] Processed {frame_count} frames ({fps:.1f} FPS)")
        return True

    except ImportError as e:
        print(f"[SKIP] Detection test skipped: {e}")
        return True
    except KeyboardInterrupt:
        print("\nDetection test stopped by user.")
        return True
    except Exception as e:
        print(f"[FAIL] Detection error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Camera Test")
    parser.add_argument("--detect", action="store_true",
                        help="Also test cat detection")
    args = parser.parse_args()

    print("=" * 50)
    print("  CatToy Camera Test")
    print("=" * 50)

    ok = True
    ok &= test_basic_capture()
    ok &= test_jetson_capture()

    if args.detect:
        ok &= test_detection()

    print()
    if ok:
        print("Camera tests passed!")
    else:
        print("Some camera tests failed. Check output above.")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
