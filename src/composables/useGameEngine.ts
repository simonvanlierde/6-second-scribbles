import { GAME_SETTINGS } from '@/config/gameConfig';
import { cardDecks } from '@/shared/cardDecks';
import type { Card, Difficulty, GuessSubmission, RoundResult } from '@/shared/types';
import { useGameStore } from '@/stores/game';
import { useGameConnection } from './useGameConnection';

/**
 * Game Engine - Handles game logic on the host's client
 * The host coordinates the game and broadcasts state to other players
 */
export function useGameEngine() {
  const store = useGameStore();
  const { send } = useGameConnection();

  // Store guess submissions for scoring
  const guessSubmissions = new Map<string, GuessSubmission[]>();
  let drawingPhaseTimeout = GAME_SETTINGS.roundLengthSeconds.DEFAULT * 1000; // Will be updated by startGame

  function getRandomCard(difficulty: Difficulty): Card {
    const deck = cardDecks[difficulty];
    if (!deck || deck.length === 0) {
      throw new Error(`No cards available for difficulty: ${difficulty}`);
    }
    const index = Math.floor(Math.random() * deck.length);
    return deck[index]!;
  }

  function assignCards(difficulty: Difficulty): Record<string, Card> {
    const cards: Record<string, Card> = {};
    const playerIds = Array.from(store.players.keys());
    const deck = cardDecks[difficulty];

    if (!deck || deck.length === 0) {
      throw new Error(`No cards available for difficulty: ${difficulty}`);
    }

    // Create a shuffled copy of the deck
    const shuffledDeck = [...deck].sort(() => Math.random() - 0.5);

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

  function startRound(roundNumber: number, difficulty: Difficulty) {
    const cards = assignCards(difficulty);
    guessSubmissions.clear();

    // Send start_round to server (server will add roundStartTime and broadcast)
    send({
      type: 'start_round',
      round: roundNumber,
      cards,
      roundStartTime: 0, // Will be replaced by server
    });

    // After drawing phase, start guessing phase
    setTimeout(() => {
      startGuessingPhase();
    }, drawingPhaseTimeout + 2000); // drawing time + 2s buffer
  }

  function startGuessingPhase() {
    // Broadcast to start guessing
    send({
      type: 'start_guessing',
      assignments: {}, // Simple: everyone guesses everyone
      roundStartTime: Date.now(), // Guessing phase start time
    });
  }

  function handleGuessSubmission(submission: GuessSubmission) {
    if (!guessSubmissions.has(submission.playerId)) {
      guessSubmissions.set(submission.playerId, []);
    }
    guessSubmissions.get(submission.playerId)!.push(submission);

    // Check if all players have submitted guesses
    const allPlayersSubmitted = store.playersList.every(player =>
      guessSubmissions.has(player.id)
    );

    if (allPlayersSubmitted) {
      calculateScores();
    }
  }

  function calculateScores() {
    const results: RoundResult[] = [];
    const newScores: Record<string, number> = {};

    // Initialize scores
    store.playersList.forEach(player => {
      newScores[player.id] = player.score;
    });

    // Calculate points for each submission
    for (const [playerId, submissions] of guessSubmissions.entries()) {
      for (const submission of submissions) {
        const targetPlayer = store.players.get(submission.targetPlayerId);
        if (!targetPlayer || !targetPlayer.currentCard || !targetPlayer.currentCard.items) {
          console.warn('[GameEngine] Skipping submission - no card or items for player:', submission.targetPlayerId);
          continue;
        }

        const correctItems = targetPlayer.currentCard.items;
        let correctGuesses = 0;

        // Check each guess against the items (case-insensitive)
        for (const guess of submission.guesses) {
          const normalizedGuess = guess.trim().toLowerCase();
          if (correctItems.some(item => item.toLowerCase() === normalizedGuess)) {
            correctGuesses++;
          }
        }

        // Award points: 10 points per correct guess to both guesser and drawer
        const pointsEarned = correctGuesses * 10;
        newScores[playerId] = (newScores[playerId] || 0) + pointsEarned;
        newScores[submission.targetPlayerId] = (newScores[submission.targetPlayerId] || 0) + pointsEarned;

        results.push({
          playerId,
          targetPlayerId: submission.targetPlayerId,
          correctGuesses,
          totalItems: correctItems.length,
          pointsEarned
        });
      }
    }

    // Broadcast results
    send({
      type: 'round_complete',
      results,
      scores: newScores
    });

    // Move to next round or end game
    setTimeout(() => {
      if (store.currentRound < store.maxRounds) {
        startRound(store.currentRound + 1, store.difficulty);
      } else {
        endGame(newScores);
      }
    }, 5000); // 5 second break between rounds
  }

  function endGame(finalScores: Record<string, number>) {
    const winner = Object.entries(finalScores).reduce((a, b) =>
      a[1] > b[1] ? a : b
    )[0];

    send({
      type: 'game_complete',
      finalScores,
      winner
    });
  }

  function startGame(difficulty: Difficulty, maxRounds: number, roundLengthSeconds: number) {
    // Update the drawing phase timeout based on configured round length
    drawingPhaseTimeout = roundLengthSeconds * 1000;

    store.setDifficulty(difficulty);
    store.setMaxRounds(maxRounds);
    store.startGame(difficulty, maxRounds, roundLengthSeconds);

    // Start the first round
    setTimeout(() => {
      startRound(1, difficulty);
    }, 1000);
  }

  return {
    startGame,
    startRound,
    getRandomCard,
    assignCards,
    handleGuessSubmission,
    startGuessingPhase,
    calculateScores,
    endGame
  };
}
