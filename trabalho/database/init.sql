CREATE TABLE IF NOT EXISTS meme_coins (
  id TEXT PRIMARY KEY,
  name TEXT,
  symbol TEXT,
  price TEXT,
  volume TEXT,
  cap TEXT,
  date TEXT,
  is_valid INTEGER
);