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

function pick(items: readonly string[]): string {
  return items[Math.floor(Math.random() * items.length)] ?? "";
}

export function generateRandomName(): string {
  return `${pick(ADJECTIVES)} ${pick(NOUNS)}`;
}
