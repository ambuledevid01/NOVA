/**
 * NOVA 3D Background - Neural Grid / Cyber Network (Golden Wine Theme)
 */
(function() {
    let scene, camera, renderer, particles, lines;
    let particleCount = 130;
    let particlePositions, particleVelocities;
    let mouseX = 0, mouseY = 0;

    function init() {
        const canvas = document.createElement('canvas');
        canvas.id = 'three-bg-canvas';
        canvas.style.cssText = 'position:fixed; top:0; left:0; width:100vw; height:100vh; z-index:-1; pointer-events:none; opacity:0.65;';
        document.body.appendChild(canvas);

        scene = new THREE.Scene();
        scene.fog = new THREE.FogExp2(0x120307, 0.0015);

        camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 1000);
        camera.position.z = 400;

        renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

        // Create Nodes
        const geometry = new THREE.BufferGeometry();
        particlePositions = new Float32Array(particleCount * 3);
        particleVelocities = [];

        for (let i = 0; i < particleCount; i++) {
            particlePositions[i * 3] = (Math.random() - 0.5) * 800;
            particlePositions[i * 3 + 1] = (Math.random() - 0.5) * 800;
            particlePositions[i * 3 + 2] = (Math.random() - 0.5) * 800;

            particleVelocities.push({
                x: (Math.random() - 0.5) * 0.8,
                y: (Math.random() - 0.5) * 0.8,
                z: (Math.random() - 0.5) * 0.8
            });
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));

        // Node Material - Golden Amber
        const pMaterial = new THREE.PointsMaterial({
            color: 0xf59e0b,
            size: 4.5,
            transparent: true,
            opacity: 0.85
        });

        particles = new THREE.Points(geometry, pMaterial);
        scene.add(particles);

        // Lines Geometry - Warm Gold
        const lineGeometry = new THREE.BufferGeometry();
        const lineMaterial = new THREE.LineBasicMaterial({
            color: 0xd4af37,
            transparent: true,
            opacity: 0.3
        });

        lines = new THREE.LineSegments(lineGeometry, lineMaterial);
        scene.add(lines);

        window.addEventListener('resize', onWindowResize);
        document.addEventListener('mousemove', onMouseMove);

        animate();
    }

    function onMouseMove(e) {
        mouseX = (e.clientX - window.innerWidth / 2) * 0.1;
        mouseY = (e.clientY - window.innerHeight / 2) * 0.1;
    }

    function onWindowResize() {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    }

    function animate() {
        requestAnimationFrame(animate);

        const positions = particles.geometry.attributes.position.array;
        let linePositions = [];

        for (let i = 0; i < particleCount; i++) {
            positions[i * 3] += particleVelocities[i].x;
            positions[i * 3 + 1] += particleVelocities[i].y;
            positions[i * 3 + 2] += particleVelocities[i].z;

            // Bounce off boundaries
            if (Math.abs(positions[i * 3]) > 400) particleVelocities[i].x *= -1;
            if (Math.abs(positions[i * 3 + 1]) > 400) particleVelocities[i].y *= -1;
            if (Math.abs(positions[i * 3 + 2]) > 400) particleVelocities[i].z *= -1;

            // Connect nearby nodes
            for (let j = i + 1; j < particleCount; j++) {
                const dx = positions[i * 3] - positions[j * 3];
                const dy = positions[i * 3 + 1] - positions[j * 3 + 1];
                const dz = positions[i * 3 + 2] - positions[j * 3 + 2];
                const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

                if (dist < 140) {
                    linePositions.push(
                        positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2],
                        positions[j * 3], positions[j * 3 + 1], positions[j * 3 + 2]
                    );
                }
            }
        }

        particles.geometry.attributes.position.needsUpdate = true;
        lines.geometry.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));

        camera.position.x += (mouseX - camera.position.x) * 0.03;
        camera.position.y += (-mouseY - camera.position.y) * 0.03;
        camera.lookAt(scene.position);

        renderer.render(scene, camera);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
