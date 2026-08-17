# UDP Receiver

Receives UTF-8 UDP datagrams and maps expected messages to generated Nodel
events. Source filtering, validation and message routing remain separate from
any downstream action bindings.

## Sender setup

Set the sender's UDP target host to the Nodel host and its target port to the
receiver's configured port. Each datagram is handled as one complete message.

The receiver defaults to port `12345`. Prefer a specific host address over
broadcast.

## Message events

The enabled `ingredient_MessageEvents.py` adds a **Message events** parameter.
Each row contains:

- `message`: required expected UDP message.
- `event`: required local event name.
- `value`: optional string emitted by the event; defaults to `message`.

For example:

```json
{
  "message": "TRIGGER_ON",
  "event": "Trigger On",
  "value": "On"
}
```

Matching is case-sensitive. Trailing CR and LF characters are ignored, so
`TRIGGER_ON`, `TRIGGER_ON\n`, and `TRIGGER_ON\r\n` match the same mapping. Every
matching datagram emits, including consecutive identical messages. The event's
normal Nodel timestamp is its last-received time.

An empty mapping list is valid. Invalid rows, duplicate normalized messages,
equivalent event names, or collisions with existing events disable all mapped
events and set `MessageEventStatus` to an error; the UDP listener keeps running.

## Nodel events

- Generated events: one string event per valid message mapping, grouped under
  **Message Events**.
- `ReceivedCount`: all accepted datagrams.
- `MatchedCount` and `UnmatchedCount`: accepted routing outcomes;
  `ReceivedCount = MatchedCount + UnmatchedCount`.
- `RejectedCount` and `LastRejected`: source or payload validation failures.
- `Status`: listener startup or configuration failure.
- `MessageEventStatus`: mapping configuration health.

Counters reset when the node starts.

## Logging

Use `RaiseLogLevel` and `LowerLogLevel` under **Debug**:

- Level `0`: lifecycle and genuine configuration/startup errors only.
- Level `1`: unmatched accepted messages, with source and escaped payload.
- Level `2`: all accepted routing details and rejection reasons.

Payloads are escaped in the log so line endings remain visible. Raw messages
are deliberately not exposed as always-visible Nodel events.

Use `Allowed source addresses` before connecting events to physical actions. The
allowlist compares sender IP addresses only; UDP sender ports are intentionally
ephemeral.

UDP does not acknowledge or guarantee delivery. Keep downstream commands
idempotent when practical.

## Site-specific name

The script identifies itself as `UDP Receiver`. A node-local custom script can
change that presentation without modifying the shared recipe. For example,
`custom_Exhibit.py` can contain:

```python
_receiverName = 'Exhibit UDP Receiver'
```
