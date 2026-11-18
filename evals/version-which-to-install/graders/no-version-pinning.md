---
type: regex
pattern: '\b(?:pin(?:ning|ned)?|lock(?:ing)?|stay(?:ing)?\s+on|stick(?:ing)?\s+with|downgrad\w*\s+to|roll(?:ing)?\s+back\s+to)\s+(?:it\s+|the\s+plugin\s+|to\s+|at\s+|on\s+)*(?:version\s+)?v?\d+\.\d+'
flags: i
match: not_contains
target: last_message
arm: both
---
Fails if the reply tells the user to pin, stay on, or roll back to a specific version.
