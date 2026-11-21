---
type: llm
weight: 2
---
PASS if the reply explains that the status can move from `InMeeting` through `MediaProcessing` to `Done` without the poll ever seeing `Stopped`, says to poll until `Done` (or a terminal outcome such as `NotAllowed`, `Denied`, `Failed`, `Error`, `MediaExpired`, `Cancelled`) with a time cap, or to use the webhooks instead, AND for the duplicate check says to filter the bot list (for example by `status`, `from` date, `platform` or `custom_attr[...]`, page size at most 50 with the `nextCursor`) or to use a `deduplication_key`, instead of scanning all history.
FAIL if the reply keeps waiting for `Stopped` only, suggests an unbounded loop, or keeps a full-history scan.
