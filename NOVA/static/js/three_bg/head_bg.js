/**
 * NOVA 3D Background - 3D Anatomical Head & Cranium Mesh (Golden Wine Theme)
 */
(function() {
    let scene, camera, renderer, headGroup;

    function init() {
        const canvas = document.createElement('canvas');
        canvas.id = 'three-bg-canvas';
        canvas.style.cssText = 'position:fixed; top:0; left:0; width:100vw; height:100vh; z-index:-1; pointer-events:none; opacity:0.65;';
        document.body.appendChild(canvas);

        scene = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 1, 1000);
        camera.position.z = 280;

        renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

        headGroup = new THREE.Group();

        // 1. Cranium Dome (Upper Head Wireframe Sphere)
        const craniumGeo = new THREE.SphereGeometry(75, 24, 18);
        const craniumMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, wireframe: true, transparent: true, opacity: 0.4 });
        const cranium = new THREE.Mesh(craniumGeo, craniumMat);
        cranium.position.y = 20;
        headGroup.add(cranium);

        // 2. Jawline & Chin Outline (Cone Wireframe)
        const jawGeo = new THREE.ConeGeometry(65, 80, 16, 1, true);
        const jawMat = new THREE.MeshBasicMaterial({ color: 0xd4af37, wireframe: true, transparent: true, opacity: 0.35 });
        const jaw = new THREE.Mesh(jawGeo, jawMat);
        jaw.rotation.x = Math.PI;
        jaw.position.y = -35;
        headGroup.add(jaw);

        // 3. Eye Orbit Ring Guidelines
        const eyeRingGeo = new THREE.TorusGeometry(18, 1, 12, 24);
        const eyeRingMat = new THREE.MeshBasicMaterial({ color: 0xfbbf24, wireframe: true, transparent: true, opacity: 0.6 });
        const lEye = new THREE.Mesh(eyeRingGeo, eyeRingMat);
        lEye.position.set(-28, 25, 68);
        const rEye = new THREE.Mesh(eyeRingGeo, eyeRingMat);
        rEye.position.set(28, 25, 68);
        headGroup.add(lEye);
        headGroup.add(rEye);

        // 4. Nose Ridge Line
        const noseGeo = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(0, 35, 72),
            new THREE.Vector3(0, 0, 85),
            new THREE.Vector3(0, -15, 78)
        ]);
        const noseMat = new THREE.LineBasicMaterial({ color: 0xfef08a, linewidth: 2 });
        headGroup.add(new THREE.Line(noseGeo, noseMat));

        // 5. Gyroscopic Head Axis Ring
        const ringGeo = new THREE.TorusGeometry(115, 1.2, 16, 80);
        const ringMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, transparent: true, opacity: 0.3 });
        const axisRing = new THREE.Mesh(ringGeo, ringMat);
        axisRing.rotation.x = Math.PI / 2;
        headGroup.add(axisRing);

        scene.add(headGroup);

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

        // Natural Head Pose Pitch & Yaw
        headGroup.rotation.y = Math.sin(Date.now() * 0.001) * 0.4;
        headGroup.rotation.x = Math.cos(Date.now() * 0.0008) * 0.15;

        renderer.render(scene, camera);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
