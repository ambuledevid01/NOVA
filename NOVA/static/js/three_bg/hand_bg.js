/**
 * NOVA 3D Background - 3D Anatomical Hand Skeleton & Finger Joints (Golden Wine Theme)
 */
(function() {
    let scene, camera, renderer, handGroup;

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

        handGroup = new THREE.Group();

        // Joint Node Material
        const nodeMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b });
        const nodeGeo = new THREE.SphereGeometry(4.5, 12, 12);
        const boneMat = new THREE.LineBasicMaterial({ color: 0xd4af37, transparent: true, opacity: 0.7 });

        // Define Hand Skeleton Landmarks (wrist, palm, 5 fingers with joints)
        const handLandmarks = {
            wrist: [0, -90, 0],
            thumb: [[-25, -60, 5], [-50, -35, 15], [-65, -10, 20]],
            index: [[-35, -20, 0], [-42, 20, 0], [-46, 50, 0], [-48, 75, 0]],
            middle: [[-12, -15, 0], [-14, 30, 0], [-15, 65, 0], [-16, 95, 0]],
            ring: [[12, -20, 0], [15, 22, 0], [17, 55, 0], [18, 80, 0]],
            pinky: [[32, -30, 0], [38, 5, 0], [42, 35, 0], [45, 58, 0]]
        };

        function addNode(pos) {
            const m = new THREE.Mesh(nodeGeo, nodeMat);
            m.position.set(pos[0], pos[1], pos[2]);
            handGroup.add(m);
            return new THREE.Vector3(pos[0], pos[1], pos[2]);
        }

        function connectBones(p1, p2) {
            const geo = new THREE.BufferGeometry().setFromPoints([p1, p2]);
            const line = new THREE.Line(geo, boneMat);
            handGroup.add(line);
        }

        const wPos = addNode(handLandmarks.wrist);

        // Build 5 Fingers & Connect to Palm
        Object.keys(handLandmarks).forEach(key => {
            if (key === 'wrist') return;
            const fingerJoints = handLandmarks[key];
            let prevVec = wPos;

            fingerJoints.forEach((jPos, idx) => {
                const curVec = addNode(jPos);
                connectBones(prevVec, curVec);
                prevVec = curVec;
            });
        });

        // Add Floating Golden Particles around Hand
        const pCount = 120;
        const pGeo = new THREE.BufferGeometry();
        const pPos = new Float32Array(pCount * 3);
        for (let i = 0; i < pCount * 3; i++) {
            pPos[i] = (Math.random() - 0.5) * 500;
        }
        pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
        const pMat = new THREE.PointsMaterial({ color: 0xfef08a, size: 2.5, transparent: true, opacity: 0.6 });
        const particles = new THREE.Points(pGeo, pMat);
        scene.add(particles);

        scene.add(handGroup);

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

        // Smooth 3D Hand Gestural Rotation
        handGroup.rotation.y = Math.sin(Date.now() * 0.001) * 0.45;
        handGroup.rotation.z = Math.cos(Date.now() * 0.0008) * 0.15;
        handGroup.rotation.x = Math.sin(Date.now() * 0.0006) * 0.2;

        renderer.render(scene, camera);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
