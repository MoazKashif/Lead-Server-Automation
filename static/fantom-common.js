/**
 * FANTOM AI - SHARED COMMON SCRIPT & INTERACTIVE RUNTIME
 */

// Initialize Lucide Icons
document.addEventListener('DOMContentLoaded', () => {
    if (window.lucide) {
        lucide.createIcons();
    }
    highlightActiveNavLink();
    initBackgroundCanvas();
    initFLogo();
    setupMobileMenu();
});

// Highlight Current Route in Navigation
function highlightActiveNavLink() {
    const currentPath = window.location.pathname.toLowerCase();
    const navLinks = document.querySelectorAll('.nav-links a, .mobile-nav-menu a');

    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (!href) return;
        const linkPath = href.toLowerCase();

        // Exact match or prefix match for offerings / ecosystem
        if (currentPath === linkPath || 
           (linkPath === '/nexus' && (currentPath === '/' || currentPath === '/website')) ||
           (linkPath === '/ecosystem' && currentPath.startsWith('/ecosystem')) ||
           (linkPath === '/ecosystem' && currentPath.startsWith('/offerings'))) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// Mobile Menu Toggle
function setupMobileMenu() {
    const toggle = document.querySelector('.mobile-nav-toggle');
    const menu = document.querySelector('.mobile-nav-menu');
    if (toggle && menu) {
        toggle.addEventListener('click', () => {
            menu.classList.toggle('active');
        });
    }
}

// Background Three.js Constellation Canvas
function initBackgroundCanvas() {
    const canvas = document.getElementById('bg-canvas');
    if (!canvas || !window.THREE) return;

    try {
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.z = 250;

        const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

        const particleCount = 120;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const velocities = [];

        for (let i = 0; i < particleCount; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 500;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 350;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 200;

            velocities.push({
                x: (Math.random() - 0.5) * 0.35,
                y: (Math.random() - 0.5) * 0.35,
                z: (Math.random() - 0.5) * 0.2
            });
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        // Particle Points
        const pMaterial = new THREE.PointsMaterial({
            color: 0x00F2FE,
            size: 3.5,
            transparent: true,
            opacity: 0.65
        });
        const particles = new THREE.Points(geometry, pMaterial);
        scene.add(particles);

        // Dynamic Connecting Lines
        const lineMaterial = new THREE.LineBasicMaterial({
            color: 0x7F00FF,
            transparent: true,
            opacity: 0.2
        });

        const lineGeo = new THREE.BufferGeometry();
        const lines = new THREE.LineSegments(lineGeo, lineMaterial);
        scene.add(lines);

        let mouseX = 0, mouseY = 0;
        window.addEventListener('mousemove', (e) => {
            mouseX = (e.clientX - window.innerWidth / 2) * 0.05;
            mouseY = (e.clientY - window.innerHeight / 2) * 0.05;
        });

        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });

        function animate() {
            requestAnimationFrame(animate);

            const pos = geometry.attributes.position.array;
            const linePositions = [];

            for (let i = 0; i < particleCount; i++) {
                pos[i * 3] += velocities[i].x;
                pos[i * 3 + 1] += velocities[i].y;
                pos[i * 3 + 2] += velocities[i].z;

                if (pos[i * 3] < -250 || pos[i * 3] > 250) velocities[i].x *= -1;
                if (pos[i * 3 + 1] < -180 || pos[i * 3 + 1] > 180) velocities[i].y *= -1;
                if (pos[i * 3 + 2] < -100 || pos[i * 3 + 2] > 100) velocities[i].z *= -1;

                // Check distance to other particles for line connections
                for (let j = i + 1; j < particleCount; j++) {
                    const dx = pos[i * 3] - pos[j * 3];
                    const dy = pos[i * 3 + 1] - pos[j * 3 + 1];
                    const dz = pos[i * 3 + 2] - pos[j * 3 + 2];
                    const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

                    if (dist < 65) {
                        linePositions.push(pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]);
                        linePositions.push(pos[j * 3], pos[j * 3 + 1], pos[j * 3 + 2]);
                    }
                }
            }

            geometry.attributes.position.needsUpdate = true;
            lineGeo.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));

            camera.position.x += (mouseX - camera.position.x) * 0.03;
            camera.position.y += (-mouseY - camera.position.y) * 0.03;
            camera.lookAt(scene.position);

            renderer.render(scene, camera);
        }

        animate();
    } catch (err) {
        console.warn('Three.js canvas init deferred:', err);
    }
}

// 3D Metallic/Neon F-Logo rendering in Navbar & Footer
function mountLogoFallback(containerId) {
    const container = document.getElementById(containerId);
    if (!container || container.dataset.logoBuilt === 'true') return;
    container.innerHTML = '<img src="/static/fantom-logo.svg" alt="Fantom AI" style="width:100%;height:100%;object-fit:contain;">';
    container.dataset.logoBuilt = 'true';
}

function initFLogo() {
    try {
        if (window.THREE) {
            buildFLogo('nav-q-logo');
            buildFLogo('footer-q-logo');
        } else {
            mountLogoFallback('nav-q-logo');
            mountLogoFallback('footer-q-logo');
        }
    } catch (err) {
        console.warn('3D logo disabled, using static fallback:', err);
        mountLogoFallback('nav-q-logo');
        mountLogoFallback('footer-q-logo');
    }
}

function buildFLogo(containerId) {
    const container = document.getElementById(containerId);
    if (!container || container.dataset.logoBuilt === 'true') return;

    const w = container.clientWidth || 42;
    const h = container.clientHeight || 42;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(w, h);
    container.appendChild(renderer.domElement);
    container.dataset.logoBuilt = 'true';

    // Vertical stem of F
    const stemGeo = new THREE.BoxGeometry(0.35, 2.4, 0.35);
    const stemMat = new THREE.MeshBasicMaterial({ color: 0x00F2FE, wireframe: true });
    const stem = new THREE.Mesh(stemGeo, stemMat);
    scene.add(stem);

    // Top horizontal bar of F
    const topBarGeo = new THREE.BoxGeometry(1.6, 0.3, 0.3);
    const topBar = new THREE.Mesh(topBarGeo, stemMat);
    topBar.position.set(0.7, 1.05, 0);
    scene.add(topBar);

    // Middle horizontal bar of F
    const midBarGeo = new THREE.BoxGeometry(1.2, 0.3, 0.3);
    const midBar = new THREE.Mesh(midBarGeo, stemMat);
    midBar.position.set(0.5, 0, 0);
    scene.add(midBar);

    camera.position.z = 3.5;

    function anim() {
        requestAnimationFrame(anim);
        stem.rotation.y += 0.015;
        topBar.rotation.y += 0.015;
        midBar.rotation.y += 0.015;
        renderer.render(scene, camera);
    }
    anim();
}

// Appointment Modal Handlers
function openAppointmentModal() {
    const overlay = document.getElementById('appointment-modal-overlay');
    if (overlay) {
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeAppointmentModal() {
    const overlay = document.getElementById('appointment-modal-overlay');
    if (overlay) {
        overlay.classList.remove('active');
        document.body.style.overflow = 'auto';
    }
}

function closeAppointmentModalOnOverlay(event) {
    if (event.target.id === 'appointment-modal-overlay') {
        closeAppointmentModal();
    }
}

// Submit Appointment Form
async function handleAppointmentSubmit(event) {
    event.preventDefault();
    const btn = document.getElementById('appt-submit-btn') || event.target.querySelector('button[type="submit"]');
    const originalText = btn ? btn.innerHTML : 'Submit';

    const name = document.getElementById('appt-name').value;
    const email = document.getElementById('appt-email').value;
    const date = document.getElementById('appt-date').value;
    const time = document.getElementById('appt-time').value;
    const scope = document.getElementById('appt-scope').value;

    const payload = {
        name: name,
        email: email,
        appointment_date: date,
        time_window: time,
        automation_goal: scope
    };

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span>Deploying Genesis Session...</span>`;
    }

    try {
        const response = await fetch('/api/appointments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            if (window.confetti) {
                confetti({
                    particleCount: 100,
                    spread: 70,
                    origin: { y: 0.6 }
                });
            }
            alert(`Genesis Session Requested!\n\nThank you, ${name}. Your appointment for ${date} (${time}) has been registered. Chaudary Moaz Kashif & Umer Siddiqui's team will contact you shortly at ${email}.`);
            closeAppointmentModal();
            event.target.reset();
        } else {
            const err = await response.json();
            alert(`Unable to register session: ${err.detail || 'Please check your inputs and retry.'}`);
        }
    } catch (error) {
        console.error('Submission error:', error);
        alert('Transmission error: Check network connectivity and retry.');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}
