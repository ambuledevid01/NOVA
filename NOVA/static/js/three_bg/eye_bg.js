/**
 * NOVA 3D Background - 3D Anatomical Eye Structure & Iris Grid (Golden Wine Theme)
 */
(function() {
    let scene, camera, renderer;
    let eyeGroup, irisMesh, pupilMesh, orbitRings = [];

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

        eyeGroup = new THREE.Group();

        // 1. Eyeball Sclera (Outer Sphere Wireframe)
        const scleraGeo = new THREE.SphereGeometry(85, 32, 24);
        const scleraMat = new THREE.MeshBasicMaterial({ color: 0xd4af37, wireframe: true, transparent: true, opacity: 0.25 });
        const scleraMesh = new THREE.Mesh(scleraGeo, scleraMat);
        eyeGroup.add(scleraMesh);

        // 2. Iris Ring (Golden Wine Ring Geometry)
        const irisGeo = new THREE.RingGeometry(25, 55, 48);
        const irisMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, side: THREE.DoubleSide, transparent: true, opacity: 0.75, wireframe: true });
        irisMesh = new THREE.Mesh(irisGeo, irisMat);
        irisMesh.position.z = 82;
        eyeGroup.add(irisMesh);

        // 3. Pupil (Inner Dark Core)
        const pupilGeo = new THREE.CircleGeometry(24, 32);
        const pupilMat = new THREE.MeshBasicMaterial({ color: 0x160509, side: THREE.DoubleSide });
        pupilMesh = new THREE.Mesh(pupilGeo, pupilMat);
        pupilMesh.position.z = 83;
        eyeGroup.add(pupilMesh);

        // 4. Orbital Target Rings
        for (let i = 1; i <= 3; i++) {
            const rGeo = new THREE.TorusGeometry(85 + i * 30, 1.2, 16, 80);
            const rMat = new THREE.MeshBasicMaterial({ color: 0xfbbf24, transparent: true, opacity: 0.35 - i * 0.08 });
            const ring = new THREE.Mesh(rGeo, rMat);
            ring.rotation.x = Math.PI / 4 * i;
            eyeGroup.add(ring);
            orbitRings.push(ring);
        }

        // 5. Floating Optics Particles
        const pCount = 180;
        const pGeo = new THREE.BufferGeometry();
        const pPos = new Float32Array(pCount * 3);
        for (let i = 0; i < pCount * 3; i++) {
            pPos[i] = (Math.random() - 0.5) * 600;
        }
        pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
        const pMat = new THREE.PointsMaterial({ color: 0xfef08a, size: 2.5, transparent: true, opacity: 0.7 });
        const particles = new THREE.Points(pGeo, pMat);
        scene.add(particles);

        scene.add(eyeGroup);

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

        // Natural Eye Gaze Micro-Movement
        eyeGroup.rotation.y = Math.sin(Date.now() * 0.0012) * 0.35;
        eyeGroup.rotation.x = Math.cos(Date.now() * 0.001) * 0.2;

        orbitRings.forEach((r, idx) => {
            r.rotation.z += (idx + 1) * 0.003;
        });

        renderer.render(scene, camera);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
