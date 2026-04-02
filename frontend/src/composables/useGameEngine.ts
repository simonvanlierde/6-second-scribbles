import { cardDecks } from "@/shared/cardDecks";
import type { Card, Difficulty } from "@/shared/types";
import { useGameStore } from "@/stores/game";
import { useGameConnection } from "./useGameConnection";

/**
 * Game Engine - Handles card assignment and round timing on the host's client.
 * Scoring is performed server-side; the host only drives round progression.
 */
export function useGameEngine() {
  const store = useGameStore();
  const { send } = useGameConnection();

  function getRandomCard(difficulty: Difficulty): Card {
    const deck = cardDecks[difficulty];
    if (!deck || deck.length === 0) {
      throw new Error(`No cards available for difficulty: ${difficulty}`);
    }
    const index = Math.floor(Math.random() * deck.length);
    const card = deck[index];
    if (!card) throw new Error(`No card at index ${index}`);
    return card;
  }

  function assignCards(difficulty: Difficulty): Record<string, Card> {
    const cards: Record<string, Card> = {};
    const playerIds = Array.from(store.players.keys());
    const deck = cardDecks[difficulty];

    if (!deck || deck.length === 0) {
      throw new Error(`No cards available for difficulty: ${difficulty}`);
    }

    // Fisher-Yates shuffle for unbiased randomization
    const shuffledDeck = [...deck];
    for (let i = shuffledDeck.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const tmp = shuffledDeck[i];
      shuffledDeck[i] = shuffledDeck[j] as (typeof shuffledDeck)[number];
      shuffledDeck[j] = tmp as (typeof shuffledDeck)[number];
    }

    // Assign unique cards to each player (or reuse if more players than cards)
    for (let i = 0; i < playerIds.length; i++) {
      const playerId = playerIds[i];
      if (!playerId) continue;

      // Use modulo to cycle through deck if more players than cards
      const card = shuffledDeck[i % shuffledDeck.length];
      if (card) {
        cards[playerId] = card;
      }
    }

    return cards;
  }

  function startRound(roundNumber: number, difficulty: Difficulty, roundLengthSeconds: number) {
    const cards = assignCards(difficulty);

    // Send start_round to server (server will add roundStartTime and broadcast)
    send({
      type: "start_round",
      round: roundNumber,
      cards,
      roundStartTime: 0, // Will be replaced by server
    });

    // After drawing phase, start guessing phase
    setTimeout(
      () => {
        startGuessingPhase();
      },
      roundLengthSeconds * 1000 + 2000,
    ); // drawing time + 2s buffer
  }

  function startGuessingPhase() {
    // Broadcast to start guessing
    send({
      type: "start_guessing",
      assignments: {}, // Simple: everyone guesses everyone
      roundStartTime: Date.now(), // Guessing phase start time
    });
  }

  function startGame(difficulty: Difficulty, maxRounds: number, roundLengthSeconds: number) {
    store.setDifficulty(difficulty);
    store.setMaxRounds(maxRounds);
    store.startGame(difficulty, maxRounds, roundLengthSeconds);

    // Start the first round
    setTimeout(() => {
      startRound(1, difficulty, roundLengthSeconds);
    }, 1000);
  }

  return {
    startGame,
    startRound,
    getRandomCard,
    assignCards,
    startGuessingPhase,
  };
}
