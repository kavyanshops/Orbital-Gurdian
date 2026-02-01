/**
 * 3D Orbit Visualization Module
 * Uses Three.js to render satellite and debris orbits in 3D
 */

class OrbitViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.earth = null;
        this.orbits = [];
        this.animationId = null;
        this.isInitialized = false;

        // Earth radius in km
        this.EARTH_RADIUS = 6371;
        this.SCALE = 0.001; // Scale factor for visualization
    }

    async init() {
        if (this.isInitialized) return;

        // Import Three.js from CDN
        await this.loadThreeJS();

        const width = this.container.clientWidth;
        const height = this.container.clientHeight || 400;

        // Scene setup
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0a1a);

        // Camera
        this.camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
        this.camera.position.set(20, 15, 20);
        this.camera.lookAt(0, 0, 0);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);

        // Controls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.minDistance = 10;
        this.controls.maxDistance = 100;

        // Create Earth
        this.createEarth();

        // Add ambient light
        const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
        this.scene.add(ambientLight);

        // Add directional light (sun)
        const sunLight = new THREE.DirectionalLight(0xffffff, 1);
        sunLight.position.set(50, 30, 50);
        this.scene.add(sunLight);

        // Add stars background
        this.createStarfield();

        // Handle resize
        window.addEventListener('resize', () => this.onResize());

        this.isInitialized = true;
        this.animate();
    }

    async loadThreeJS() {
        return new Promise((resolve, reject) => {
            if (window.THREE) {
                resolve();
                return;
            }

            // Load Three.js
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
            script.onload = () => {
                // Load OrbitControls
                const controlsScript = document.createElement('script');
                controlsScript.src = 'https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js';
                controlsScript.onload = resolve;
                controlsScript.onerror = reject;
                document.head.appendChild(controlsScript);
            };
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    createEarth() {
        const geometry = new THREE.SphereGeometry(this.EARTH_RADIUS * this.SCALE, 64, 32);

        // Create a gradient texture for Earth
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 256;
        const ctx = canvas.getContext('2d');

        // Earth-like gradient
        const gradient = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
        gradient.addColorStop(0, '#1a4a7a');
        gradient.addColorStop(0.3, '#2d5a8a');
        gradient.addColorStop(0.6, '#1a3a5a');
        gradient.addColorStop(1, '#0a2a4a');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 256, 256);

        // Add some "continents"
        ctx.fillStyle = '#2a5a3a';
        ctx.beginPath();
        ctx.arc(100, 80, 40, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(180, 150, 30, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(60, 180, 25, 0, Math.PI * 2);
        ctx.fill();

        const texture = new THREE.CanvasTexture(canvas);
        const material = new THREE.MeshPhongMaterial({
            map: texture,
            shininess: 5
        });

        this.earth = new THREE.Mesh(geometry, material);
        this.scene.add(this.earth);

        // Add atmosphere glow
        const atmosphereGeometry = new THREE.SphereGeometry(this.EARTH_RADIUS * this.SCALE * 1.02, 32, 32);
        const atmosphereMaterial = new THREE.MeshBasicMaterial({
            color: 0x4488ff,
            transparent: true,
            opacity: 0.15,
            side: THREE.BackSide
        });
        const atmosphere = new THREE.Mesh(atmosphereGeometry, atmosphereMaterial);
        this.scene.add(atmosphere);
    }

    createStarfield() {
        const starsGeometry = new THREE.BufferGeometry();
        const starPositions = [];

        for (let i = 0; i < 2000; i++) {
            const x = (Math.random() - 0.5) * 500;
            const y = (Math.random() - 0.5) * 500;
            const z = (Math.random() - 0.5) * 500;
            starPositions.push(x, y, z);
        }

        starsGeometry.setAttribute('position', new THREE.Float32BufferAttribute(starPositions, 3));

        const starsMaterial = new THREE.PointsMaterial({
            color: 0xffffff,
            size: 0.5,
            transparent: true,
            opacity: 0.8
        });

        const stars = new THREE.Points(starsGeometry, starsMaterial);
        this.scene.add(stars);
    }

    addOrbit(positions, color, name, isWarning = false) {
        if (!positions || positions.length < 2) return;

        // Convert positions to scaled coordinates
        const points = positions.map(p =>
            new THREE.Vector3(p[0] * this.SCALE, p[2] * this.SCALE, p[1] * this.SCALE)
        );

        // Create orbit line
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineBasicMaterial({
            color: color,
            linewidth: 2,
            transparent: true,
            opacity: isWarning ? 1.0 : 0.6
        });

        const line = new THREE.Line(geometry, material);
        this.scene.add(line);
        this.orbits.push(line);

        // Add current position marker
        if (positions.length > 0) {
            const markerGeometry = new THREE.SphereGeometry(isWarning ? 0.15 : 0.1, 16, 16);
            const markerMaterial = new THREE.MeshBasicMaterial({
                color: color,
                emissive: color,
                emissiveIntensity: 0.5
            });
            const marker = new THREE.Mesh(markerGeometry, markerMaterial);
            marker.position.copy(points[0]);
            marker.userData = {
                name: name,
                isWarning: isWarning,
                positions: points,
                currentIndex: 0
            };
            this.scene.add(marker);
            this.orbits.push(marker);
        }
    }

    clearOrbits() {
        this.orbits.forEach(obj => {
            this.scene.remove(obj);
            if (obj.geometry) obj.geometry.dispose();
            if (obj.material) obj.material.dispose();
        });
        this.orbits = [];
    }

    loadOrbitData(data) {
        this.clearOrbits();

        if (!data) return;

        // Add satellite orbit (bright blue)
        if (data.satellite && data.satellite.positions) {
            this.addOrbit(data.satellite.positions, 0x00ffff, data.satellite.name, false);
        }

        // Add debris orbits
        if (data.debris) {
            data.debris.forEach((debris, index) => {
                const isWarning = debris.isWarning || false;
                const color = isWarning ? 0xff4444 : 0xff8800;
                this.addOrbit(debris.positions, color, debris.name, isWarning);
            });
        }
    }

    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());

        if (this.earth) {
            this.earth.rotation.y += 0.001;
        }

        // Animate satellite/debris markers along their orbits
        this.orbits.forEach(obj => {
            if (obj.userData && obj.userData.positions) {
                const positions = obj.userData.positions;
                obj.userData.currentIndex = (obj.userData.currentIndex + 0.5) % positions.length;
                const idx = Math.floor(obj.userData.currentIndex);
                if (positions[idx]) {
                    obj.position.copy(positions[idx]);
                }
            }
        });

        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    onResize() {
        if (!this.container || !this.camera || !this.renderer) return;

        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        this.clearOrbits();
        if (this.renderer) {
            this.renderer.dispose();
        }
    }
}

// Export for use
window.OrbitViewer = OrbitViewer;
