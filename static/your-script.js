
document.addEventListener('DOMContentLoaded', function () {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer();
renderer.setSize(window.innerWidth, window.innerHeight);
document.getElementById('container').appendChild(renderer.domElement);

// Create a sphere for the panoramic image
const geometry = new THREE.SphereGeometry(500, 60, 40);
geometry.scale(-1, 1, 1); // Invert the sphere to display correctly
const texture = new THREE.TextureLoader().load('/static/images/panorama2.jpg'); // Replace with your panoramic image URL
const material = new THREE.MeshBasicMaterial({ map: texture });
const sphere = new THREE.Mesh(geometry, material);
scene.add(sphere);

// Initialize PointerLockControls for user interaction
const controls = new THREE.PointerLockControls(camera, renderer.domElement);
scene.add(controls.getObject());

// Set initial camera position
camera.position.set(0, 0, 0.1);

// Handle window resize
window.addEventListener('resize', () => {
    const newWidth = window.innerWidth;
    const newHeight = window.innerHeight;
    camera.aspect = newWidth / newHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(newWidth, newHeight);
});

// Create a render loop to continuously update the scene
const animate = () => {
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
};
animate();

// Enable Pointer Lock for user interaction (click to move the camera)
document.addEventListener('click', () => {
    controls.lock();
}, false);

});