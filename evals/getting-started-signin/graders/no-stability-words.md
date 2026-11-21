---
type: regex
pattern: '\b(stable|unstable|break|breaks|breaking|broken|pin|pinned|pinning|downgrade|downgrading)\b|can.?t promise|always safe|@meetstream\/mcp'
flags: i
match: not_contains
target: last_message
arm: both
---
Fails on any stability or pinning word, "always safe", or the old npm package name in the reply, including a negation such as "no version to pin" or "I can't promise it won't break".
