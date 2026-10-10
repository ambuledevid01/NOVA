/**
 * NOVA 3D Background - 3D Neural Synapses & Energy Pulses (Golden Wine Theme)
 */
(function() {
    let scene, camera, renderer, coreSphere, pulseRings = [];

    function init() {
        const canvas = document.createElement('canvas');
        canvas.id = 'three-bg-canvas';
        canvas.style.cssText = 'position:fixed; top:0; left:0; width:100vw; height:100vh; z-index:-1; pointer-events:none; opacity:0.6;';
        document.body.appendChild(canvas);

        scene = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 1000);
        camera.position.z = 320;

        renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);

        // Core Synaptic Wireframe Sphere in Golden Wine
        const sGeo = new THREE.IcosahedronGeometry(85, 3);
        const sMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, wireframe: true, transparent: true, opacity: 0.45 });
        coreSphere = new THREE.Mesh(sGeo, sMat);
        scene.add(coreSphere);

        // Pulsing Golden Energy Rings
        for (let i = 0; i < 4; i++) {
            const rGeo = new THREE.RingGeometry(90 + i * 25, 92 + i * 25, 64);
            const rMat = new THREE.MeshBasicMaterial({ color: 0xd4af37, side: THREE.DoubleSide, transparent: true, opacity: 0.35 });
            const ring = new THREE.Mesh(rGeo, rMat);
            ring.rotation.x = Math.PI / 2;
            scene.add(ring);
            pulseRings.push(ring);
        }

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

        coreSphere.rotation.y += 0.008;
        coreSphere.rotation.x += 0.005;

        pulseRings.forEach((ring, idx) => {
            ring.rotation.z += (idx + 1) * 0.003;
            const scale = 1 + Math.sin(Date.now() * 0.003 + idx) * 0.15;
            ring.scale.set(scale, scale, scale);
        });

        renderer.render(scene, camera);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
