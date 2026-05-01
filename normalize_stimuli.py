"""
normalize_stimuli.py
====================
Luminance normalization script for binocular rivalry experiment stimuli.

This script normalizes 8 images (4 faces, 4 houses) so they all share
identical mean luminance (128) and RMS contrast (40), eliminating
low-level visual confounds in the binocular rivalry paradigm.

Requirements: Pillow, numpy, matplotlib
"""

import os
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------------------------

# Define input files and their output names
# Format: (input_filename, output_filename, category_label)
IMAGE_MAP = [
    ("E-01 Canva.jpg",          "house_1_norm.png",  "House 1"),
    ("EV-E02-beige-stucco.jpg", "house_2_norm.png",  "House 2"),
    ("E-03 Canva.jpg",          "house_3_norm.png",  "House 3"),
    ("E-04 Canva.jpg",          "house_4_norm.png",  "House 4"),
    ("AF07NES.JPG",             "face_F1_norm.png",  "Face F1"),
    ("AF17NES.JPG",             "face_F2_norm.png",  "Face F2"),
    ("AM05NES.JPG",             "face_M1_norm.png",  "Face M1"),
    ("AM25NES.JPG",             "face_M2_norm.png",  "Face M2"),
]

# Normalization targets
TARGET_MEAN = 128.0   # Target mean luminance (0-255 scale)
TARGET_STD  = 40.0    # Target RMS contrast (standard deviation)

# Output directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "stimuli_normalized")

# ---------------------------------------------------------------------------
# 2. HELPER FUNCTIONS
# ---------------------------------------------------------------------------

def load_grayscale(filepath):
    """Load an image and convert it to grayscale (luminance channel only)."""
    img = Image.open(filepath).convert("L")  # "L" = 8-bit grayscale
    return np.array(img, dtype=np.float64)


def compute_stats(img_array):
    """Compute mean luminance and RMS contrast (std dev) of an image array."""
    mean_lum = np.mean(img_array)
    rms_contrast = np.std(img_array)
    return mean_lum, rms_contrast


def normalize_image(img_array, target_mean, target_std):
    """
    Normalize an image to a target mean luminance and RMS contrast.

    Formula:  normalized = (image - mean) / std * target_std + target_mean
    Values are clipped to the valid [0, 255] range.
    """
    current_mean = np.mean(img_array)
    current_std  = np.std(img_array)

    # Apply linear normalization
    normalized = (img_array - current_mean) / current_std * target_std + target_mean

    # Clip to valid 8-bit range
    normalized = np.clip(normalized, 0, 255)

    return normalized


def print_stats_table(title, labels, stats_list):
    """Print a formatted table of image statistics."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    print(f"  {'Image':<18} {'Mean Luminance':>16} {'RMS Contrast':>14}")
    print(f"  {'-'*18} {'-'*16} {'-'*14}")
    for label, (mean_l, rms_c) in zip(labels, stats_list):
        print(f"  {label:<18} {mean_l:>16.2f} {rms_c:>14.2f}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# 3. MAIN PROCESSING PIPELINE
# ---------------------------------------------------------------------------

def main():
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- Step 1 & 2: Load images as grayscale and compute BEFORE stats ---
    print("Loading images and computing initial statistics...")

    grayscale_images = []
    labels = []
    before_stats = []

    for input_name, _, label in IMAGE_MAP:
        filepath = os.path.join(SCRIPT_DIR, input_name)
        img_array = load_grayscale(filepath)
        grayscale_images.append(img_array)
        labels.append(label)
        stats = compute_stats(img_array)
        before_stats.append(stats)

    # --- Step 3: Print BEFORE normalization stats ---
    print_stats_table("BEFORE NORMALIZATION", labels, before_stats)

    # --- Step 4: Normalize all images to the common target ---
    print(f"Normalizing all images to: Mean = {TARGET_MEAN}, RMS Contrast = {TARGET_STD}")

    normalized_images = []
    for img_array in grayscale_images:
        norm_img = normalize_image(img_array, TARGET_MEAN, TARGET_STD)
        normalized_images.append(norm_img)

    # --- Step 5: Save normalized images ---
    print("Saving normalized images...")

    for i, (_, output_name, label) in enumerate(IMAGE_MAP):
        output_path = os.path.join(OUTPUT_DIR, output_name)
        # Convert back to uint8 for saving
        pil_img = Image.fromarray(normalized_images[i].astype(np.uint8), mode="L")
        pil_img.save(output_path)
        print(f"  Saved: {output_name}")

    # --- Step 6: Compute and print AFTER normalization stats ---
    # Re-read saved files to confirm on-disk values match expectations
    after_stats = []
    for _, output_name, _ in IMAGE_MAP:
        saved_path = os.path.join(OUTPUT_DIR, output_name)
        saved_array = load_grayscale(saved_path)
        stats = compute_stats(saved_array)
        after_stats.append(stats)

    print_stats_table("AFTER NORMALIZATION (verified from saved files)", labels, after_stats)

    # --- Step 7: Generate quality control figure ---
    print("Generating quality control figure...")

    fig, axes = plt.subplots(2, 8, figsize=(24, 7))

    # Top row: normalized images | Bottom row: luminance histograms
    for i in range(8):
        # -- Image row --
        ax_img = axes[0, i]
        ax_img.imshow(normalized_images[i].astype(np.uint8), cmap="gray", vmin=0, vmax=255)
        ax_img.set_title(labels[i], fontsize=10, fontweight="bold")
        ax_img.axis("off")

        # -- Histogram row --
        ax_hist = axes[1, i]
        ax_hist.hist(
            normalized_images[i].flatten(),
            bins=64,
            range=(0, 255),
            color="#4a90d9",
            edgecolor="none",
            alpha=0.85,
        )
        ax_hist.set_xlim(0, 255)
        ax_hist.set_xlabel("Pixel value", fontsize=8)
        ax_hist.set_ylabel("Count", fontsize=8)
        ax_hist.tick_params(labelsize=7)

        # Add mean and std annotation
        m, s = after_stats[i]
        ax_hist.axvline(m, color="red", linewidth=1.2, linestyle="--", label=f"μ={m:.1f}")
        ax_hist.legend(fontsize=7, loc="upper right")

    fig.suptitle(
        "Quality Control — Luminance Normalization\n"
        f"Target: Mean = {TARGET_MEAN}, RMS Contrast (σ) = {TARGET_STD}",
        fontsize=14,
        fontweight="bold",
        y=1.02,
    )
    plt.tight_layout()
    qc_path = os.path.join(SCRIPT_DIR, "QC_normalization.png")
    fig.savefig(qc_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  QC figure saved: QC_normalization.png")

    # --- Done ---
    print("\nNormalization complete. Files saved to stimuli_normalized/")


if __name__ == "__main__":
    main()
