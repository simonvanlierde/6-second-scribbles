# 6 Second Scribbles (Online Multiplayer)

A fast, real-time multiplayer web version of the **Six Second Scribbles** party game.

## 🎨 What is this?

This is a fast-paced drawing game for 2-10 players. These are the rules:

1. Everyone gets a card with 10 items to draw (from a specific category).
2. You get **60 seconds** to draw as many of them as you can.
3. After time's up, everyone guesses what someone _else_ drew.
4. You get points for good drawings (what people guessed correctly) AND for being a good guesser!

## 🎯 Features

- **Real-time multiplayer** for 2-10 players.
- **Simple drawing canvas** with touch/mouse support, colors, and brush sizes.
- **Smart(ish) guessing:** Handles plurals and minor typos.
- **111+ categories** across Easy, Medium, and Hard difficulties.
- **Fully responsive:** Works on desktop, tablet, and mobile.
- **Simple room codes:** 6-char codes to join games.
- **Modern stack:** Built with Vue 3, TypeScript, Pinia, and PartyKit.

## 🚀 Quick Start

### Prerequisites

- **Node.js:**: v24.11.1 or later. Download the latest LTS version from [nodejs.org](https://nodejs.org/).

### Installation

```bash
# Install all the dependencies
npm install

# Terminal 1: Start the frontend (Vite dev server)
npm run dev

# Terminal 2: Start the backend (PartyKit WebSocket server)
npm run dev:server
```

Open `http://localhost:3001` in your browser and start drawing!

## 🧭 Client: PartySocket (new)

This project now uses PartySocket on the client for resilient WebSocket connections to the PartyKit server. PartySocket automatically reconnects, buffers outgoing messages while disconnected, and is multi-platform.

Install (already added to this project's dependencies):

```bash
npm install partysocket@latest
```

Usage (the app's connection logic lives in `src/composables/useGameConnection.ts`):

```ts
import PartySocket from 'partysocket'

// PartySocket expects a host (without protocol) and room id
const ws = new PartySocket({ host: 'draw6s.username.partykit.dev', room: 'ABCDEF' })

ws.addEventListener('open', () => {
  /* connected */
})
ws.addEventListener('message', (e) => {
  /* handle JSON messages */
})

// PartySocket buffers send() calls until the socket is open
ws.send(JSON.stringify({ type: 'join', playerId: 'p1', name: 'Alice' }))
```

## 🏗️ How It's Built

### The Stack

| Layer         | Technology | Version |
| ------------- | ---------- | ------- |
| **Framework** | Vue 3      | 3.5.22  |
| **State**     | Pinia      | 3.0.3   |
| **Routing**   | Vue Router | 4.6.3   |
| **Language**  | TypeScript | 5.9.0   |
| **Bundler**   | Vite       | 7.2.2   |
| **Backend**   | PartyKit   | 0.0.115 |
| **Protocol**  | WebSockets | -       |

## 📁 Project Structure

```sh
six-second-scribbles/
├── src/
│   ├── main.ts                  # Vue app entry point
│   ├── App.vue                  # Root component
│   ├── router/
│   │   └── index.ts            # Vue Router config
│   ├── stores/
│   │   └── game.ts             # Pinia store (all game state)
│   ├── composables/
│   │   ├── useGameConnection.ts # WebSocket logic
│   │   └── useDrawingCanvas.ts  # Canvas drawing logic
│   ├── views/
│   │   ├── HomeView.vue       # Home screen
│   │   ├── WaitingRoomView.vue # Pre-game 'waiting-room'
│   │   ├── GameView.vue        # The main game
│   │   └── FinalResultsView.vue     # Final scores
│   ├── data/
│   │   └── deck.ts             # All 111+ game cards
│   ├── shared/
│   │   └── types.ts            # Shared TS types
│   ├── server/
│   │   └── index.ts            # PartyKit WebSocket server
│   └── assets/
│       └── main.css            # Global styles
│
├── package.json
├── tsconfig.json
├── vite.config.ts
└── partykit.json
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
3. **Scoring:** You get 1 point for each correct guess you make. The original drawer _also_ gets 1 point for every guess you got right.
4. **Repeat:** The game runs for the number of rounds set by the host.
5. **Winner:** Highest score at the end wins!

## 🔧 Dev Setup

### Available Scripts

```bash
npm run dev            # Start Vite dev server (frontend)
npm run dev:server     # Start PartyKit server (backend)
npm run build          # Build production frontend
npm run build-only     # Build without type checking
npm run type-check     # Run TypeScript checks
npm run lint           # Run oxlint + ESLint
npm run format         # Format code with Prettier
npm run preview        # Preview the production build
```

### Dev Tips

- Vite's HMR means your frontend changes are instant.
- The PartyKit server will auto-restart when you change its code.
- Use the Vue DevTools browser extension to inspect the Pinia store state.
- Check the Network tab in your browser's devtools to monitor WebSocket messages.

## 🚀 Deployment

Deploying involves two parts: the **backend** (PartyKit server) and the **frontend** (Vue site).

### Step 1: Deploy the Backend Server

This server handles all real-time messages.

#### Option 1: PartyKit Hosting (Simple)

This is the fastest method.

1. Log in to PartyKit (one-time setup):

   ```bash
   npx partykit login
   ```

2. Run the deploy command:

   ```bash
   npm run deploy:server
   ```

3. PartyKit will give you a live URL, like `https://draw6s.username.partykit.dev`. **Copy this URL.**

#### Option 2: Self-Host on Cloudflare

If you prefer to host on your own Cloudflare account:

1. Ensure your `.env.production` has your Cloudflare details (copy from `.env.example` if needed).

   ```sh
   # .env.production
   CLOUDFLARE_ACCOUNT_ID='your_account_id'
   CLOUDFLARE_API_TOKEN='your_api_token'
   ```

2. Follow the [official PartyKit guide for Cloudflare](https://docs.partykit.io/guides/deploy-to-cloudflare/).

### Step 2: Configure, Build, and Deploy the Frontend

Now you'll prepare and deploy the website.

#### 1. Configure the Backend URL

- Open your `.env.production` file.

- Add your **PartyKit URL** from Step 1.

  ```sh
  # .env.production
  VITE_PARTYKIT_HOST=draw6s.your-username.partykit.dev
  ```

#### 2. Build the Frontend

Run the build command to package your website into a static `dist/` folder.

```bash
npm run build
```

#### 3. Deploy the Static Site

Host the `dist/` folder on any static site provider.

- Services like [Vercel](https://vercel.com/) or [Netlify](https://www.netlify.com/) are free and easy.
- Sign up, find the "Add new site" button, and **drag and drop your `dist/` folder** to deploy.

Your provider will give you a public URL, and your game will be live.

## 📜 Attribution

This project is a real-time, multiplayer web version inspired by two wonderful creations:

1. **The original physical game:** _Six Second Scribbles_, created by **Hazel Reynolds** and published by [Gamely Games](https://gamelygames.com/products/six-second-scribbles).
2. **The original solo web version:** by **Oliver Culley de Lange**, which you can find [on GitHub](https://github.com/OliverCulleyDeLange/6ss).

This implementation rebuilds the game from the ground up as a multiplayer experience using Vue 3, Pinia, and PartyKit.

## 🤝 Contributing

Got ideas? Contributions are definitely welcome. Feel free to open an issue or send a PR. Some things on my mind:

- More card decks
- Smarter fuzzy-matching for guesses
- Animations, sound effects, or a spectator mode
- Game history and player stats

## 📝 License

The code for _this_ multiplayer implementation is released under the **MIT License**.

The _Six Second Scribbles_ game concept, brand, and original card content remain the property of their respective owners.
