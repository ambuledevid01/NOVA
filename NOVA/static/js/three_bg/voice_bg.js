/**
 * NOVA 3D Background - Dynamic Audio Wave Spectrum (Golden Wine Theme)
 */
(function() {
    let scene, camera, renderer, planeMesh;
    const widthSegments = 40;
    const heightSegments = 40;

    function init() {
        const canvas = document.createElement('canvas');
        canvas.id = 'three-bg-canvas';
        canvas.style.cssText = 'position:fixed; top:0; left:0; width:100vw; height:100vh; z-index:-1; pointer-events:none; opacity:0.55;';
        document.body.appendChild(canvas);

        scene = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 1000);
        camera.position.set(0, -120, 180);
        camera.lookAt(0, 50, 0);

        renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);

        // 3D Wave Grid Plane in Golden Wine
        const geometry = new THREE.PlaneGeometry(600, 600, widthSegments, heightSegments);
        const material = new THREE.MeshBasicMaterial({
            color: 0xf59e0b,
            wireframe: true,
            transparent: true,
            opacity: 0.45
        });

        planeMesh = new THREE.Mesh(geometry, material);
        scene.add(planeMesh);

        window.addEventListener('resize', onWindowResize);
        animate();
    }

    function onWindowResize() {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    }

    function animate() {
        requestAnimationFrame(animate);

        const time = Date.now() * 0.002;
        const pos = planeMesh.geometry.attributes.position;

        for (let i = 0; i < pos.count; i++) {
            const x = pos.getX(i);
            const y = pos.getY(i);
            const z = Math.sin(x * 0.03 + time) * 22 + Math.cos(y * 0.03 + time * 1.2) * 22;
            pos.setZ(i, z);
        }

        pos.needsUpdate = true;
        renderer.render(scene, camera);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
