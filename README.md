
# EIDOLON #015 — Ant Colony

An artificial-life simulation in Python and Pygame exploring swarm intelligence, emergent behavior, and pheromone-based foraging.

Individual ants follow simple local rules. They search for food, return to their nest, and deposit pheromones. Other ants sense these trails, helping successful routes emerge without a central controller.

## Features

- Ant colony with adjustable population
- Food sources and a central nest
- Pheromone deposition, evaporation, and diffusion
- Trail-following and food-return behavior
- Obstacle avoidance
- Mouse-controlled food placement and obstacle creation
- Adjustable simulation speed
- Four color palettes
- Trail and movement-vector visualization
- Procedural sound effects
- Countdown start screen
- Colony statistics and FPS display
- Smoke-test mode

## Requirements

- Python 3.10 or newer
- Pygame 2.6.1

## Installation

Create and activate a virtual environment.

### Windows — Git Bash

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
```

### Windows — PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

```bash
python main.py
```

Press **SPACE** and watch the countdown to begin the simulation.

## Controls

| Key | Action |
|---|---|
| SPACE | Start countdown / pause / resume |
| R | Reset simulation |
| + / - | Increase / decrease simulation speed |
| Q / A | Add / remove 10 ants |
| F | Toggle pheromone trails |
| V | Toggle movement vectors |
| G | Toggle grid |
| H | Toggle HUD |
| C | Change visual palette |
| M | Toggle audio |
| X | Clear pheromones |
| O | Toggle obstacle placement |
| W | Switch to food placement |
| S | Add a random food source |
| N | Move the nest |
| DELETE | Remove all food sources |
| BACKSPACE | Remove all obstacles |
| Mouse wheel | Adjust zoom setting |
| Left-click | Place food or obstacles, depending on mode |
| Right-click | Remove nearby food and obstacles |
| ESC | Quit |

## How It Works

### 1. Exploration

Ants begin around the nest and move with a heading that changes through local sensing and random turns.

### 2. Food collection

When an ant reaches a food source, it collects food and changes direction toward the nest.

### 3. Pheromone deposition

Returning ants deposit pheromones along their route. Pheromones provide a shared environmental signal that other ants can sense.

### 4. Trail following

Searching ants compare pheromone intensity in front of them and to either side. When one direction has a stronger signal, they tend to turn toward it.

### 5. Evaporation and diffusion

Pheromone concentrations gradually decay and diffuse to nearby cells. This makes trail strength change over time instead of remaining permanent.

### 6. Emergent behavior

Repeated local interactions create visible traffic between the nest and food sources. The colony's organization emerges from individual agents rather than a central route planner.

## Run a Smoke Test

```bash
python main.py --smoke-test
```

This starts the application and closes it after a short period, helping verify that initialization and the main loop work.

## Project

**EIDOLON #015 — Ant Colony**

Part of the EIDOLON journey to build 500+ projects, progressively exploring programming, mathematics, simulations, algorithms, graphics, AI, and engineering.

Build. Experiment. Break. Repeat.
