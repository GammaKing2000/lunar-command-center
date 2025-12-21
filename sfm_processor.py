import os
import time
import pycolmap
from pathlib import Path

def log(msg):
    """Log with timestamp"""
    ts = time.strftime("%H:%M:%S")
    print(f"[SfM {ts}] {msg}")

def run_sfm(images_path, output_path):
    """
    Run COLMAP Structure-from-Motion pipeline.
    
    Args:
        images_path (str): Path to directory containing images
        output_path (str): Path to output directory (will contain sparse/0)
        
    Returns:
        reconstruction (pycolmap.Reconstruction): The sparse reconstruction result
    """
    start_time = time.time()
    output_path = Path(output_path)
    database_path = output_path / "database.db"
    
    output_path.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        os.remove(database_path)
        
    log(f"Starting SfM reconstruction")
    log(f"  Input: {images_path}")
    log(f"  Output: {output_path}")
    
    # Check image count
    valid_exts = {'.jpg', '.jpeg', '.png'}
    images = [f for f in os.listdir(images_path) if os.path.splitext(f)[1].lower() in valid_exts]
    log(f"  Found {len(images)} images")
    
    if len(images) < 4:
        log(f"ERROR: Too few images ({len(images)}) for reconstruction. Need at least 4.")
        fail_file = output_path.parent / "reconstruction_failed.txt"
        with open(fail_file, "w") as f:
            f.write(f"Insufficient images: {len(images)} found, need 4+.")
        return None
    
    # 1. Feature Extraction
    log("Step 1/3: Extracting features...")
    t1 = time.time()
    try:
        pycolmap.extract_features(database_path, images_path)
        log(f"  ✓ Feature extraction complete ({time.time()-t1:.1f}s)")
    except Exception as e:
        log(f"  ERROR in feature extraction: {e}")
        return None
    
    # 2. Feature Matching
    log("Step 2/3: Matching features (exhaustive)...")
    t2 = time.time()
    try:
        pycolmap.match_exhaustive(database_path)
        log(f"  ✓ Feature matching complete ({time.time()-t2:.1f}s)")
    except Exception as e:
        log(f"  ERROR in feature matching: {e}")
        return None
    
    # 3. Mapper (SfM)
    log("Step 3/3: Running incremental mapper...")
    t3 = time.time()
    try:
        maps = pycolmap.incremental_mapping(database_path, images_path, output_path)
    except Exception as e:
        log(f"  ERROR in incremental mapping: {e}")
        return None
    
    if not maps:
        log("ERROR: SfM Reconstruction Failed (No maps created)")
        fail_file = output_path.parent / "reconstruction_failed.txt"
        with open(fail_file, "w") as f:
            f.write("SfM incremental mapping failed - no maps created.")
        return None
        
    # We usually take the largest reconstruction (maps[0])
    reconstruction = maps[0]
    log(f"  ✓ Incremental mapping complete ({time.time()-t3:.1f}s)")
    log(f"  Results: {reconstruction.num_points3D()} 3D points, {reconstruction.num_reg_images()} registered images")
    
    # Save binary format (default for loaders)
    reconstruction.write(output_path)
    
    total_time = time.time() - start_time
    log(f"✓ SfM COMPLETE - Total time: {total_time:.1f}s")
    
    return reconstruction

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python sfm_processor.py <images_path> <output_path>")
    else:
        run_sfm(sys.argv[1], sys.argv[2])
