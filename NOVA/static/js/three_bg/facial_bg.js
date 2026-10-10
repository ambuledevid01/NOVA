/**
 * NOVA 3D Background - 3D Facial Landmark Matrix (Golden Wine Theme)
 */
(function() {
    let scene, camera, renderer, faceGroup;

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

        faceGroup = new THREE.Group();

        // 3D Facial Landmark Matrix Points
        const pointCount = 300;
        const pGeo = new THREE.BufferGeometry();
        const positions = new Float32Array(pointCount * 3);

        for (let i = 0; i < pointCount; i++) {
            const u = Math.random() * Math.PI * 2;
            const v = (Math.random() - 0.5) * Math.PI;

            const x = 110 * Math.cos(v) * Math.cos(u);
            const y = 150 * Math.sin(v);
            const z = 70 * Math.cos(v) * Math.sin(u);

            positions[i * 3] = x;
            positions[i * 3 + 1] = y;
            positions[i * 3 + 2] = z;
        }

        pGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const pMat = new THREE.PointsMaterial({ color: 0xf59e0b, size: 3.5, transparent: true, opacity: 0.8 });
        const facePoints = new THREE.Points(pGeo, pMat);
        faceGroup.add(facePoints);

        // Eye Grid Guidelines
        const eyeGeo = new THREE.TorusGeometry(20, 1, 8, 32);
        const eyeMat = new THREE.MeshBasicMaterial({ color: 0xd4af37, wireframe: true, transparent: true, opacity: 0.6 });
        const leftEye = new THREE.Mesh(eyeGeo, eyeMat);
        leftEye.position.set(-35, 30, 45);
        const rightEye = new THREE.Mesh(eyeGeo, eyeMat);
        rightEye.position.set(35, 30, 45);
        faceGroup.add(leftEye);
        faceGroup.add(rightEye);

        // Mouth Outline
        const mouthGeo = new THREE.TorusGeometry(28, 1, 6, 24);
        const mouthMat = new THREE.MeshBasicMaterial({ color: 0xfbbf24, wireframe: true, transparent: true, opacity: 0.5 });
        const mouth = new THREE.Mesh(mouthGeo, mouthMat);
        mouth.position.set(0, -45, 45);
        mouth.scale.set(1.5, 0.6, 1);
        faceGroup.add(mouth);

        scene.add(faceGroup);

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

        faceGroup.rotation.y = Math.sin(Date.now() * 0.001) * 0.4;
        faceGroup.rotation.x = Math.cos(Date.now() * 0.0008) * 0.15;

        renderer.render(scene, camera);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
