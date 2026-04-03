---
# spell-checker: words Culley, Lange
---
# 6 Second Scribbles (Online Multiplayer)

A fast, real-time multiplayer web version of the **Six Second Scribbles** party game.

## 🎨 What is this?

This is a fast-paced drawing game for 2-10 players. These are the rules:

1. Everyone gets a card with 10 items to draw (from a specific category).
2. You get **60 seconds** to draw as many of them as you can.
3. After time's up, everyone guesses what someone *else* drew.
4. You get points for good drawings (what people guessed correctly) AND for being a good guesser!

## 🎯 Features

* **Real-time multiplayer** for 2-10 players.
* **Simple drawing canvas** with touch/mouse support, colors, and brush sizes.
* **Smart(ish) guessing:** Handles plurals and minor typos.
* **111+ categories** across Easy, Medium, and Hard difficulties.
* **Fully responsive:** Works on desktop, tablet, and mobile.
* **Simple room codes:** 6-char codes to join games.
* **Modern stack:** Built with Vue 3, TypeScript, Pinia, and FastAPI.

## 🚀 Quick Start

### Prerequisites

* **Node.js:** v24 or later. Download the latest LTS version from [nodejs.org](https://nodejs.org/).
* **Python:** 3.8 or later. Download from [python.org](https://www.python.org/).

### Installation

```bash
# Install dependencies
just install

# Start everything (Docker + frontend + backend)
just dev
```

`pnpm install` at the repo root also installs the configured `lefthook` Git hooks via the root `prepare` script, so local commits run formatting, contract generation/validation, linting, type-checking, and cspell automatically.

Open `http://localhost:3001` in your browser and start drawing!

## 🏗️ How It's Built

### The Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Framework** | Vue 3 | 3.5.22 |
| **State** | Pinia | 3.0.4 |
| **Routing** | Vue Router | 5.0.4 |
| **Language** | TypeScript | 6.0.2 |
| **Bundler** | Vite | 8.0.3 |
| **Backend** | FastAPI | 0.115.6 |
| **Protocol** | WebSockets | - |

## 📁 Project Structure

```sh
six-second-scribbles/
├── frontend/
│   ├── src/
│   │   ├── main.ts               # Vue app entry point
│   │   ├── App.vue               # Root component
│   │   ├── router/
│   │   │   └── index.ts          # Vue Router config
│   │   ├── stores/
│   │   │   └── game.ts           # Pinia store (all game state)
│   │   ├── composables/
│   │   │   ├── useGameConnection.ts # WebSocket logic
│   │   │   └── useDrawingCanvas.ts  # Canvas drawing logic
│   │   ├── views/
│   │   │   ├── LobbyView.vue     # Home screen
│   │   │   ├── WaitingRoomView.vue # Pre-game lobby
│   │   │   ├── GameView.vue      # The main game
│   │   │   └── ResultsView.vue   # Final scores
│   │   ├── data/
│   │   │   └── deck.ts           # All 111+ game cards
│   │   ├── shared/
│   │   │   └── types.ts          # Shared TS types
│   │   └── assets/
│   │       └── main.css          # Global styles
│   └── package.json
│
├── backend/
│   ├── app/
│   └── pyproject.toml
│
├── justfile
├── package.json
└── pnpm-lock.yaml
```

## 🎮 How to Play

### Creating a Room

1. Go to the site.
2. Enter your name.
3. Click "Create Room".
4. Share the 6-character room code with your friends.

### Joining a Room

1. Enter your name.
2. Paste the room code.
3. Click "Join Room".

### Gameplay

1. **Drawing** (60 seconds): You'll get a category card. Draw as many of the 10 items as you can before time runs out.
2. **Guessing:** You'll see another player's drawing. Type your guesses (up to 10) for what they drew.
3. **Scoring:** You get 1 point for each correct guess you make. The original drawer *also* gets 1 point for every guess you got right.
4. **Repeat:** The game runs for the number of rounds set by the host.
5. **Winner:** Highest score at the end wins!

## 🔧 Dev Setup

### Available Scripts

```bash
just dev               # Start Docker + frontend + backend
just build             # Build the frontend
just check             # Run frontend and backend checks
just format            # Format frontend and backend
```

### Backend Testing

The FastAPI backend includes a comprehensive test suite:

```bash
# Run all backend tests
cd backend
pytest

# Run with coverage report
pytest --cov=. --cov-report=html

# Run specific test categories
pytest -m integration     # Integration tests
pytest -m "not slow"      # Skip slow tests

# Using just (recommended)
just test                 # Run all backend tests
just check                # Run frontend and backend checks
just format               # Format frontend and backend
```

See `backend/README.md` for detailed testing documentation.

### Dev Tips

* Vite's HMR means your frontend changes are instant.
* The FastAPI server will auto-reload when you change its code (thanks to `--reload` flag).
* Use the Vue DevTools browser extension to inspect the Pinia store state.
* Check the Network tab in your browser's devtools to monitor WebSocket messages.
* FastAPI provides automatic API documentation at `http://localhost:8000/docs`.
* Run backend tests frequently to ensure API stability.

## 🚀 Deployment

Deploying involves two parts: the **backend** (FastAPI server) and the **frontend** (Vue site).

### Step 1: Deploy the Backend Server

The FastAPI backend can be deployed to various platforms:

#### Option 1: Deploy to a VPS or Cloud Provider

1. Choose a hosting provider (AWS EC2, DigitalOcean, Heroku, etc.)

2. Install Python 3.8+ on your server

3. Install dependencies:

    ```bash
    pip install -r backend/requirements.txt
    ```

4. Run the server:

    ```bash
    cd backend
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```

5. For production, use a process manager like systemd or supervisor to keep the server running.

6. Set up a reverse proxy (nginx or Cloudflare) to handle SSL/TLS for secure WebSocket connections (wss://).

#### Option 2: Deploy to Railway/Render

Services like [Railway](https://railway.app/) or [Render](https://render.com/) make Python deployment simple:

1. Create a new Python web service
2. Point it to your repository
3. Set the start command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Deploy and note your backend URL

### Step 2: Configure, Build, and Deploy the Frontend

Now you'll prepare and deploy the website.

#### 1. Configure the Backend URL

* Create a `.env.production` file (or configure via your hosting provider).

* Add your **FastAPI backend URL**. Remember to use `wss://` for secure websockets.

    ```sh
    # .env.production
    VITE_BACKEND_HOST=wss://your-backend-domain.com
    ```

#### 2. Build the Frontend

Run the build command to package your website into a static `dist/` folder.

```bash
just build
```

#### 3. Deploy the Static Site

Host the `dist/` folder on any static site provider.

* Services like [Vercel](https://vercel.com/) or [Netlify](https://www.netlify.com/) are free and easy.
* Sign up, find the "Add new site" button, and **drag and drop your `dist/` folder** to deploy.

Your provider will give you a public URL, and your game will be live.

## 📜 Attribution

This project is a real-time, multiplayer web version inspired by two wonderful creations:

1. **The original physical game:** *Six Second Scribbles*, created by **Hazel Reynolds** and published by [Gamely Games](https://gamelygames.com/products/six-second-scribbles).
1. **The original solo web version:** by **Oliver Culley de Lange**, which you can find [on GitHub](https://github.com/OliverCulleyDeLange/6ss).

This implementation rebuilds the game from the ground up as a multiplayer experience using Vue 3, Pinia, and FastAPI.

## 🤝 Contributing

Got ideas? Contributions are definitely welcome. Feel free to open an issue or send a PR. Some things on my mind:

* More card decks
* Smarter fuzzy-matching for guesses
* Animations, sound effects, or a spectator mode
* Game history and player stats

## 📝 License

The code for *this* multiplayer implementation is released under the **MIT License**.

The *Six Second Scribbles* game concept, brand, and original card content remain the property of their respective owners.
