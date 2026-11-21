---
type: regex
pattern: '\bv?\d+\.\d+(?:\.\d+)?\+?[^\n]{0,80}\b(?:stable|unstable|broken|breaks?|breaking|buggy|regress\w*|safer|risky)\b|\b(?:stable|unstable|broken|breaks?|breaking|buggy|safer|risky)\b[^\n]{0,80}\bv?\d+\.\d+(?:\.\d+)?\b'
flags: i
match: not_contains
target: last_message
arm: both
---
Fails if the reply ties a version number to a stability or breakage claim.
