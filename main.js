// AI-Assisted Code: base logic generated with ChatGPT, human-edited ✅

// Canvas setup
const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");

// Game state
let player = { x: 400, y: 300, hp: 100, speed: 2 };
let keys = {};
let paused = false;

// Input handling
window.addEventListener("keydown", e => {
  if (e.key === "Escape") togglePause();
  keys[e.key.toLowerCase()] = true;
});
window.addEventListener("keyup", e => (keys[e.key.toLowerCase()] = false));

// Main game loop
function update() {
  if (!paused) {
    handleMovement();
    draw();
  }
  requestAnimationFrame(update);
}

function handleMovement() {
  if (keys["w"]) player.y -= player.speed;
  if (keys["s"]) player.y += player.speed;
  if (keys["a"]) player.x -= player.speed;
  if (keys["d"]) player.x += player.speed;
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  // background
  ctx.fillStyle = "#0a0a0a";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // player
  ctx.fillStyle = "#b30000";
  ctx.beginPath();
  ctx.arc(player.x, player.y, 15, 0, Math.PI * 2);
  ctx.fill();

  // placeholder enemy
  ctx.fillStyle = "#444";
  ctx.fillRect(350, 250, 30, 30);

  // UI
  ctx.fillStyle = "#fff";
  ctx.fillText(`HP: ${player.hp}`, 20, 30);
}

// Pause / Help overlay logic
const overlay = document.getElementById("overlay");
const helpSection = document.getElementById("helpSection");

function togglePause() {
  paused = !paused;
  overlay.classList.toggle("hidden", !paused);
}

document.getElementById("resumeBtn").onclick = togglePause;
document.getElementById("quitBtn").onclick = () => location.reload();
document.getElementById("helpBtn").onclick = () =>
  helpSection.classList.toggle("hidden");

// Start loop
update();
