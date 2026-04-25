const ADJECTIVES = [
  "Swift",
  "Brave",
  "Lucky",
  "Mighty",
  "Clever",
  "Fuzzy",
  "Sneaky",
  "Bouncy",
  "Zany",
  "Goofy",
  "Wobbly",
  "Sparkly",
  "Dashing",
  "Jolly",
  "Zippy",
];

const NOUNS = [
  "Panda",
  "Tiger",
  "Eagle",
  "Fox",
  "Wolf",
  "Penguin",
  "Koala",
  "Narwhal",
  "Capybara",
  "Axolotl",
  "Quokka",
  "Llama",
  "Wombat",
  "Gecko",
  "Platypus",
];

export function generateRandomName(): string {
  const adj = ADJECTIVES[Math.floor(Math.random() * ADJECTIVES.length)]!;
  const noun = NOUNS[Math.floor(Math.random() * NOUNS.length)]!;
  return `${adj} ${noun}`;
}
