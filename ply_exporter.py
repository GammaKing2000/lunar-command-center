"""
PLY Point Cloud Exporter
Converts COLMAP reconstruction output to PLY format for web viewing.
Replaces gaussian_splatting_worker.py for simpler, reliable 3D visualization.
"""
import os
import sys
import time
import numpy as np

def log(msg):
    """Log with timestamp (ASCII-safe for Windows)"""
    ts = time.strftime("%H:%M:%S")
    print(f"[PLY Export {ts}] {msg}")

def export_colmap_to_ply(colmap_path, output_path):
    """
    Export COLMAP reconstruction to PLY file.
    
    Args:
        colmap_path: Path to COLMAP output directory (contains cameras.bin, images.bin, points3D.bin)
        output_path: Path for output .ply file
    """
    log("=" * 50)
    log("Starting PLY Export from COLMAP")
    log(f"  COLMAP path: {colmap_path}")
    log(f"  Output: {output_path}")
    log("=" * 50)
    
    start_time = time.time()
    
    # Try to import pycolmap
    try:
        import pycolmap
    except ImportError:
        log("ERROR: pycolmap not installed. Run: pip install pycolmap")
        return False
    
    # Load COLMAP reconstruction
    log("Loading COLMAP reconstruction...")
    try:
        recon = pycolmap.Reconstruction(colmap_path)
    except Exception as e:
        log(f"ERROR loading reconstruction: {e}")
        return False
    
    # Extract 3D points
    points3D = recon.points3D
    num_points = len(points3D)
    
    if num_points == 0:
        log("ERROR: No 3D points found in reconstruction!")
        return False
    
    log(f"Found {num_points} 3D points")
    
    # Extract positions and colors
    positions = []
    colors = []
    
    for point_id, point in points3D.items():
        positions.append(point.xyz)
        # COLMAP stores colors as RGB uint8
        colors.append(point.color)
    
    positions = np.array(positions, dtype=np.float32)
    colors = np.array(colors, dtype=np.uint8)
    
    log(f"Extracted {len(positions)} points with colors")
    
    # Write PLY file
    log(f"Writing PLY to {output_path}...")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # PLY Header
    header = f"""ply
format ascii 1.0
element vertex {len(positions)}
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
end_header
"""
    
    with open(output_path, 'w') as f:
        f.write(header)
        for i in range(len(positions)):
            x, y, z = positions[i]
            r, g, b = colors[i]
            f.write(f"{x} {y} {z} {r} {g} {b}\n")
    
    # Get file size
    file_size = os.path.getsize(output_path)
    total_time = time.time() - start_time
    
    log("=" * 50)
    log(f"[OK] PLY EXPORT COMPLETE")
    log(f"  Points: {num_points}")
    log(f"  File size: {file_size / 1024:.1f} KB")
    log(f"  Time: {total_time:.1f}s")
    log("=" * 50)
    
    return True

def export_colmap_to_ply_binary(colmap_path, output_path):
    """
    Export COLMAP reconstruction to binary PLY file (smaller, faster to load).
    """
    log("=" * 50)
    log("Starting Binary PLY Export from COLMAP")
    log(f"  COLMAP path: {colmap_path}")
    log(f"  Output: {output_path}")
    log("=" * 50)
    
    start_time = time.time()
    
    try:
        import pycolmap
    except ImportError:
        log("ERROR: pycolmap not installed.")
        return False
    
    log("Loading COLMAP reconstruction...")
    try:
        recon = pycolmap.Reconstruction(colmap_path)
    except Exception as e:
        log(f"ERROR loading reconstruction: {e}")
        return False
    
    points3D = recon.points3D
    num_points = len(points3D)
    
    if num_points == 0:
        log("ERROR: No 3D points found!")
        return False
    
    log(f"Found {num_points} 3D points")
    
    # Extract data
    positions = []
    colors = []
    
    for point_id, point in points3D.items():
        positions.append(point.xyz)
        colors.append(point.color)
    
    positions = np.array(positions, dtype=np.float32)
    colors = np.array(colors, dtype=np.uint8)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Binary PLY Header
    header = f"""ply
format binary_little_endian 1.0
element vertex {len(positions)}
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
end_header
"""
    
    with open(output_path, 'wb') as f:
        f.write(header.encode('ascii'))
        for i in range(len(positions)):
            # Write position as 3 floats
            f.write(positions[i].tobytes())
            # Write color as 3 bytes
            f.write(colors[i].tobytes())
    
    file_size = os.path.getsize(output_path)
    total_time = time.time() - start_time
    
    log("=" * 50)
    log(f"[OK] BINARY PLY EXPORT COMPLETE")
    log(f"  Points: {num_points}")
    log(f"  File size: {file_size / 1024:.1f} KB")
    log(f"  Time: {total_time:.1f}s")
    log("=" * 50)
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ply_exporter.py <colmap_path> <output_ply_path> [--binary]")
        print("  colmap_path: Directory containing COLMAP output (cameras.bin, images.bin, points3D.bin)")
        print("  output_ply_path: Path for output .ply file")
        print("  --binary: Use binary PLY format (smaller file)")
        sys.exit(1)
    
    colmap_path = sys.argv[1]
    output_path = sys.argv[2]
    use_binary = "--binary" in sys.argv
    
    if use_binary:
        success = export_colmap_to_ply_binary(colmap_path, output_path)
    else:
        success = export_colmap_to_ply(colmap_path, output_path)
    
    sys.exit(0 if success else 1)
