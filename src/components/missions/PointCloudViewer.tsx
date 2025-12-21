import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js';

interface PointCloudViewerProps {
  url: string;
}

export function PointCloudViewer({ url }: PointCloudViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pointCount, setPointCount] = useState(0);

  useEffect(() => {
    if (!containerRef.current) return;

    let renderer: THREE.WebGLRenderer | null = null;
    let animationId: number | null = null;

    const init = async () => {
      try {
        const container = containerRef.current!;
        const width = container.clientWidth || 800;
        const height = container.clientHeight || 600;

        // Scene setup
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0a0a0a);

        // Camera
        const camera = new THREE.PerspectiveCamera(60, width / height, 0.01, 1000);
        camera.position.set(0, 2, 5);

        // Renderer
        renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(width, height);
        renderer.setPixelRatio(window.devicePixelRatio);
        container.innerHTML = '';
        container.appendChild(renderer.domElement);

        // Controls
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.autoRotate = true;
        controls.autoRotateSpeed = 0.5;

        // Grid helper
        const gridHelper = new THREE.GridHelper(10, 20, 0x444444, 0x222222);
        scene.add(gridHelper);

        // Axes helper
        const axesHelper = new THREE.AxesHelper(2);
        scene.add(axesHelper);

        // Ambient light
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        scene.add(ambientLight);

        // Load PLY
        console.log('Loading PLY from:', url);
        const loader = new PLYLoader();
        
        loader.load(
          url,
          (geometry) => {
            // Center the geometry
            geometry.computeBoundingBox();
            const center = new THREE.Vector3();
            geometry.boundingBox!.getCenter(center);
            geometry.translate(-center.x, -center.y, -center.z);

            // Create point cloud material
            const material = new THREE.PointsMaterial({
              size: 0.02,
              vertexColors: true,
              sizeAttenuation: true,
            });

            // Use vertex colors if available
            if (geometry.hasAttribute('color')) {
              material.vertexColors = true;
            } else {
              material.color = new THREE.Color(0x00ff88);
              material.vertexColors = false;
            }

            const points = new THREE.Points(geometry, material);
            scene.add(points);

            // Update camera to fit the model
            const box = new THREE.Box3().setFromObject(points);
            const size = box.getSize(new THREE.Vector3());
            const maxDim = Math.max(size.x, size.y, size.z);
            camera.position.set(maxDim, maxDim, maxDim);
            controls.target.set(0, 0, 0);
            controls.update();

            setPointCount(geometry.attributes.position.count);
            setLoading(false);
            console.log('PLY loaded:', geometry.attributes.position.count, 'points');
          },
          (xhr) => {
            console.log(`Loading: ${(xhr.loaded / xhr.total * 100).toFixed(1)}%`);
          },
          (err) => {
            console.error('PLY load error:', err);
            setError('Failed to load PLY file. Check if file exists.');
            setLoading(false);
          }
        );

        // Animation loop
        const animate = () => {
          animationId = requestAnimationFrame(animate);
          controls.update();
          renderer!.render(scene, camera);
        };
        animate();

        // Handle resize
        const handleResize = () => {
          const w = container.clientWidth;
          const h = container.clientHeight;
          camera.aspect = w / h;
          camera.updateProjectionMatrix();
          renderer!.setSize(w, h);
        };
        window.addEventListener('resize', handleResize);

        return () => {
          window.removeEventListener('resize', handleResize);
        };

      } catch (e: any) {
        console.error('PointCloudViewer init error:', e);
        setError(e.message);
        setLoading(false);
      }
    };

    init();

    return () => {
      if (animationId) cancelAnimationFrame(animationId);
      if (renderer) {
        renderer.dispose();
      }
    };
  }, [url]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-black/50 text-destructive p-4">
        <p className="font-bold text-red-500">3D Viewer Error</p>
        <p className="text-sm font-mono text-gray-400">{error}</p>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full min-h-[400px] bg-black rounded-lg overflow-hidden">
      <div ref={containerRef} className="w-full h-full" />
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/70">
          <div className="text-center">
            <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-2" />
            <p className="text-sm text-gray-400">Loading Point Cloud...</p>
          </div>
        </div>
      )}
      {!loading && pointCount > 0 && (
        <div className="absolute bottom-2 left-2 bg-black/70 px-2 py-1 rounded text-xs text-gray-300">
          {pointCount.toLocaleString()} points
        </div>
      )}
    </div>
  );
}
