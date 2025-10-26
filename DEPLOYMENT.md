# 🧩 Nightfall — Deployment Guide

Welcome to the deployment documentation for **Nightfall**, a 2D pixel art parody inspired by *Bloodborne*.  
This guide explains how to install, configure, and run the project locally.

---

## ⚙️ Requirements
Before running Nightfall, ensure your system meets these requirements:

- **Python** ≥ 3.11  
- **pip** (Python package manager)
- **pygame** installed (`pip install pygame`)
- Minimum display resolution of **960x540** (game window size)

---

## 📁 Project Structure
Your directory should look like this:
Nightfall/
│
├── main.py # Core game logic and loop
├── assets/ # Sprites, backgrounds, UI elements, etc.
│ ├── backgrounds/
│ ├── sprites/
│ └── ui/
├── npcs/ # NPC and character art
│ ├── travis.png
│ ├── joe.png
│ └── genesis.png
├── README.md
└── DEPLOYMENT.md


Make sure the **`assets`** and **`npcs`** folders remain in the project’s root directory.  
If these are missing or renamed, the game will not load images properly.

---

## 💻 Running Locally
Follow these steps to play *Nightfall* on your machine:

### 1. Clone the Repository
git clone https://github.com/<yourusername>/nightfall.git
cd nightfall

2. Install Dependencies
Install pygame using pip:
    pip install pygame

3. Run the Game
python main.py


## Dev notes
Both developers collaborated using ChatGPT and Claude AI to co-design and refine mechanics, structure, and flavor text.