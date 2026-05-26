# MeetStream — Node.js / TypeScript Code Patterns

Complete, runnable implementations for common MeetStream use cases.

All endpoint paths, field names, response shapes, and WebSocket protocols are verified against `docs.meetstream.ai`. Nothing here is invented.

---

## Pattern 1: Record a Meeting and Get the Transcript (Express + TypeScript)

```typescript
// npm install express axios @types/express @types/node typescript ts-node
import express, { Request, Response } from 'express'
import axios from 'axios'

const app = express()
app.use(express.json())

const MEETSTREAM_API_KEY = process.env.MEETSTREAM_API_KEY!
const BASE_URL = 'https://api.meetstream.ai/api/v1'
const headers = {
  'Authorization': `Token ${MEETSTREAM_API_KEY}`,
  'Content-Type': 'application/json'
}

// Idempotency dedup for webhooks (no automatic retries, but defense in depth)
const seenEvents = new Set<string>()

async function createBot(meetingLink: string, callbackUrl: string): Promise<string> {
  // We don't need to store transcript_id from the response. The canonical
  // fetch flow uses bot_details.transcript_id at retrieval time, so the
  // create call only needs to return the bot_id.
  const { data } = await axios.post(`${BASE_URL}/bots/create_bot`, {
    meeting_link: meetingLink,
    bot_name: 'Recorder',
    video_required: false,
    callback_url: callbackUrl,
    recording_config: {
      transcript: {
        provider: { deepgram: { language: 'en', model: 'nova-3' } }
      },
      retention: { type: 'timed', hours: 48 }
    },
    automatic_leave: {
      waiting_room_timeout: 600,
      everyone_left_timeout: 600,
      voice_inactivity_timeout: 600,
      in_call_recording_timeout: 14400,
      recording_permission_denied_timeout: 300
    }
  }, { headers })

  // BotResponse fields: { bot_id, transcript_id, meeting_url, status }
  console.log(`Bot created: ${data.bot_id} (status=${data.status})`)
  return data.bot_id
}

async function getTranscript(botId: string): Promise<any[]> {
  // Stateless flow — two API calls, no in-memory state:
  //   1) GET /bots/{bot_id}/detail → bot_details.transcript_id (canonical)
  //   2) GET /transcript/{transcript_id}/get_transcript
  const { data: detail } = await axios.get(`${BASE_URL}/bots/${botId}/detail`, { headers })
  const transcriptId = detail?.bot_details?.transcript_id
  if (!transcriptId) {
    throw new Error(`No transcript_id on bot_details for ${botId} — likely meeting_captions provider or no transcription configured`)
  }
  // Response is a top-level JSON array of segments per the OpenAPI spec.
  const { data } = await axios.get(`${BASE_URL}/transcript/${transcriptId}/get_transcript`, { headers })
  return data  // Array<{speaker, transcript, start_time, end_time, words[]}>
}

app.post('/webhook', async (req: Request, res: Response) => {
  // ALWAYS 200 first — webhooks are NOT retried
  res.json({ status: 'ok' })

  const { bot_id, event, bot_status, timestamp } = req.body
  const dedupeKey = `${bot_id}:${event}:${timestamp}`
  if (seenEvents.has(dedupeKey)) return
  seenEvents.add(dedupeKey)

  console.log(`Event: ${event} | Bot: ${bot_id} | Status: ${bot_status ?? '-'}`)

  try {
    // Lifecycle events (live-verified order):
    //   bot.joining → bot.inmeeting → bot.recording → bot.leaving → bot.stopped
    //   → manifest.completed → audio.processed → transcription.processed (or .failed)
    //   → video.processed → bot.done → data_deletion (after manual /delete)
    switch (event) {
      case 'bot.joining':    console.log(`Bot ${bot_id} connecting...`); break
      case 'bot.inmeeting':  console.log(`Bot ${bot_id} joined the meeting`); break
      case 'bot.recording':  console.log(`Bot ${bot_id} started recording`); break
      case 'bot.leaving':    console.log(`Bot ${bot_id} is leaving`); break

      case 'bot.stopped':
        if (bot_status !== 'Stopped') {
          // NotAllowed / Denied / Error surfaced via bot_status here
          console.error(`Bot did not exit cleanly: ${bot_status} — ${req.body.message}`)
        }
        break

      case 'manifest.completed': console.log(`Manifest uploaded for ${bot_id}`); break
      case 'audio.processed':    console.log(`Audio ready for ${bot_id}`); break
      case 'video.processed':    console.log(`Video ready for ${bot_id}`); break

      case 'transcription.processed': {
        // transcript_id is NOT in this payload — resolve via bot_details.transcript_id
        const segments = await getTranscript(bot_id)
        for (const seg of segments) {
          console.log(`[${seg.speaker}] ${seg.transcript}`)  // field is `transcript`, not `text`
        }
        break
      }

      case 'transcription.failed':
        // Live-verified failure event — status_code=500
        console.error(`Transcription FAILED for ${bot_id}: ${req.body.message}`)
        break

      case 'bot.done':
        if (req.body.status_code === 200) console.log(`Bot ${bot_id} done successfully`)
        else console.error(`Bot ${bot_id} done with error: ${req.body.message}`)
        break

      case 'data_deletion':
        console.log(`Bot ${bot_id} data deleted (${req.body.deleted_objects} objects)`)
        break

      default:
        if (event?.startsWith('participant_events.')) {
          // Different shape: bot_id under data.bot.id, action under data.data.action
          const inner = req.body?.data?.data
          console.log(`${inner?.action}: ${inner?.participant?.full_name} (${inner?.participant?.platform})`)
        }
    }
  } catch (err) {
    console.error('Handler error (already 200ed):', err)
  }
})

app.listen(3000, () => console.log('Listening on :3000'))

// Usage: createBot('https://meet.google.com/abc-defg-hij', 'https://your-ngrok.ngrok.io/webhook')
```

---

## Pattern 2: Real-Time Transcription (HTTPS Webhook)

Live transcription is delivered as HTTPS POSTs to your `webhook_url`. It is **not** a WebSocket.

```typescript
// npm install express axios
import express, { Request, Response } from 'express'
import axios from 'axios'

const app = express()
app.use(express.json())

const MEETSTREAM_API_KEY = process.env.MEETSTREAM_API_KEY!
const BASE_URL = 'https://api.meetstream.ai/api/v1'
const headers = {
  'Authorization': `Token ${MEETSTREAM_API_KEY}`,
  'Content-Type': 'application/json'
}

interface LiveTranscriptChunk {
  bot_id: string
  speakerName?: string
  timestamp: string
  new_text?: string
  transcript: string
  words: Array<{
    word: string
    start: number
    end: number
    confidence: number
    speaker?: string
    punctuated_word?: string
    word_is_final?: boolean
  }>
  end_of_turn?: boolean
  transcription_mode?: string
  custom_attributes?: Record<string, string>
}

app.post('/live-transcript', (req: Request, res: Response) => {
  res.json({ status: 'ok' })

  const chunk = req.body as LiveTranscriptChunk
  const speaker = chunk.speakerName ?? 'Unknown'
  console.log(`[${chunk.timestamp}] ${speaker}: ${chunk.transcript}`)

  if (chunk.end_of_turn) processFinalUtterance(chunk)
})

function processFinalUtterance(chunk: LiveTranscriptChunk) {
  const text = chunk.transcript.toLowerCase()
  if (text.includes('action item') || text.includes('follow up')) {
    console.log(`ACTION ITEM from ${chunk.speakerName}: "${chunk.transcript}"`)
  }
}

async function createRealtimeBot(meetingLink: string, webhookUrl: string): Promise<string> {
  const { data } = await axios.post(`${BASE_URL}/bots/create_bot`, {
    meeting_link: meetingLink,
    bot_name: 'AI Assistant',
    video_required: false,
    live_transcription_required: { webhook_url: webhookUrl },
    recording_config: {
      transcript: {
        provider: {
          deepgram_streaming: {
            transcription_mode: 'sentence',
            model: 'nova-2',
            language: 'en',
            punctuate: true,
            smart_format: true,
            endpointing: 300,
            vad_events: true,
            utterance_end_ms: 1000,
            encoding: 'linear16',
            channels: 1
          }
        }
      }
    },
    automatic_leave: {
      waiting_room_timeout: 600,
      everyone_left_timeout: 600,
      in_call_recording_timeout: 14400,
      recording_permission_denied_timeout: 300
    }
  }, { headers })

  return data.bot_id
}

app.listen(3000, () => console.log('Live transcript webhook on :3000/live-transcript'))
```

---

## Pattern 3: Interactive Bot — All 5 WebSocket Commands

The bot **connects to your WebSocket as a client** when it joins, sends a `ready` handshake, then accepts JSON commands.

```typescript
// npm install ws axios @types/ws
import { WebSocketServer, WebSocket } from 'ws'
import axios from 'axios'

const MEETSTREAM_API_KEY = process.env.MEETSTREAM_API_KEY!
const BASE_URL = 'https://api.meetstream.ai/api/v1'
const headers = {
  'Authorization': `Token ${MEETSTREAM_API_KEY}`,
  'Content-Type': 'application/json'
}

const botSockets = new Map<string, WebSocket>()

const wss = new WebSocketServer({ port: 8766, path: '/bot-control' })

wss.on('connection', (ws: WebSocket) => {
  ws.on('message', async (raw: Buffer) => {
    const msg = JSON.parse(raw.toString())
    if (msg.type === 'ready') {
      const botId: string = msg.bot_id
      console.log(`Bot ${botId} ready: ${msg.message ?? ''}`)
      botSockets.set(botId, ws)

      // Once ready, you can issue commands. Example: greet via sendmsg.
      sendChatMessage(botId, "Hi everyone! I'm taking notes.")
    }
  })

  ws.on('close', () => {
    for (const [botId, sock] of botSockets) {
      if (sock === ws) botSockets.delete(botId)
    }
  })
})

// ─── COMMAND 1: sendaudio ───────────────────────────────────────────────────
// Play raw PCM16 LE @ 48kHz mono audio. base64-encoded. No WAV header.
function sendAudio(botId: string, pcm16LeBytes: Buffer): void {
  const ws = botSockets.get(botId)
  if (!ws) throw new Error(`No active socket for bot ${botId}`)
  ws.send(JSON.stringify({
    command: 'sendaudio',
    bot_id: botId,
    audiochunk: pcm16LeBytes.toString('base64'),
    sample_rate: 48000,
    encoding: 'pcm16',
    channels: 1,
    endianness: 'little'
  }))
}

// Chunked streaming: 0.5-2s chunks, pace slightly below real-time
async function streamAudio(botId: string, pcm16LeBytes: Buffer): Promise<void> {
  const CHUNK_BYTES = 48000 * 2  // 1 second of 48kHz int16 mono
  for (let i = 0; i < pcm16LeBytes.length; i += CHUNK_BYTES) {
    sendAudio(botId, pcm16LeBytes.subarray(i, i + CHUNK_BYTES))
    await new Promise(r => setTimeout(r, 800))  // 0.8s per 1s chunk
  }
}

// Convert Float32Array (-1.0 to 1.0) → PCM16 LE Buffer
function float32ToPcm16(samples: Float32Array): Buffer {
  const pcm = Buffer.alloc(samples.length * 2)
  for (let i = 0; i < samples.length; i++) {
    const clamped = Math.max(-1, Math.min(1, samples[i]))
    pcm.writeInt16LE(Math.round(clamped * 32767), i * 2)
  }
  return pcm
}

// ─── COMMAND 2: sendmsg ─────────────────────────────────────────────────────
// Both `message` AND `msg` must be set to the same value for cross-platform compat.
function sendChatMessage(botId: string, text: string): void {
  const ws = botSockets.get(botId)
  if (!ws) throw new Error(`No active socket for bot ${botId}`)
  ws.send(JSON.stringify({
    command: 'sendmsg',
    bot_id: botId,
    message: text,
    msg: text
  }))
}

// ─── COMMAND 3: sendchat (role + streaming) ────────────────────────────────
function sendChatStream(botId: string, role: 'assistant' | 'user', text: string, isFinal: boolean): void {
  const ws = botSockets.get(botId)
  if (!ws) throw new Error(`No active socket for bot ${botId}`)
  ws.send(JSON.stringify({
    command: 'sendchat',
    bot_id: botId,
    role,
    text,
    is_final: isFinal
  }))
}

// Streaming LLM response example
async function streamAssistantReply(botId: string, tokenStream: AsyncIterable<string>): Promise<void> {
  let accumulated = ''
  for await (const token of tokenStream) {
    accumulated += token
    sendChatStream(botId, 'assistant', accumulated, false)  // interim
  }
  sendChatStream(botId, 'assistant', accumulated, true)  // final commit
}

// ─── COMMAND 4: interrupt (barge-in) ────────────────────────────────────────
// Google Meet only fully clears the queue. Zoom/Teams accept but no-op.
function interrupt(botId: string): void {
  const ws = botSockets.get(botId)
  if (!ws) throw new Error(`No active socket for bot ${botId}`)
  ws.send(JSON.stringify({
    command: 'interrupt',
    bot_id: botId,
    action: 'clear_audio_queue'
  }))
}

// ─── COMMAND 5: sendimg / sendimg_url (set bot's video frame) ───────────────
function setBotVideoFrameFromUrl(botId: string, imgUrl: string): void {
  const ws = botSockets.get(botId)
  if (!ws) throw new Error(`No active socket for bot ${botId}`)
  ws.send(JSON.stringify({
    command: 'sendimg_url',
    bot_id: botId,
    img_url: imgUrl
  }))
}

function setBotVideoFrameFromBase64(botId: string, jpegOrPngBase64: string): void {
  const ws = botSockets.get(botId)
  if (!ws) throw new Error(`No active socket for bot ${botId}`)
  ws.send(JSON.stringify({
    command: 'sendimg',
    bot_id: botId,
    img: jpegOrPngBase64
  }))
}

// ─── REST EQUIVALENTS for chat / image into the chat panel ──────────────────
async function postChatViaRest(botId: string, message: string): Promise<void> {
  await axios.post(`${BASE_URL}/bots/${botId}/send_message`, {
    message,
    metadata: { message_type: 'text' }
  }, { headers })
}

async function postImageViaRest(botId: string, imgUrl: string, displayDuration?: number): Promise<void> {
  // IMPORTANT: field is `img_url`, NOT `image_url`
  await axios.post(`${BASE_URL}/bots/${botId}/send_image`, {
    img_url: imgUrl,
    display_duration: displayDuration,
    metadata: { message_type: 'image' }
  }, { headers })
}

async function createInteractiveBot(meetingLink: string, controlWsUrl: string): Promise<string> {
  const { data } = await axios.post(`${BASE_URL}/bots/create_bot`, {
    meeting_link: meetingLink,
    bot_name: 'Meeting Assistant',
    video_required: false,
    socket_connection_url: { websocket_url: controlWsUrl },
    automatic_leave: {
      waiting_room_timeout: 600,
      everyone_left_timeout: 600,
      recording_permission_denied_timeout: 300
    }
  }, { headers })
  return data.bot_id
}

console.log('Bot control WS: ws://localhost:8766/bot-control')
```

---

## Pattern 4: Full Note-Taking Agent (Next.js API Route)

```typescript
// pages/api/webhook.ts
import type { NextApiRequest, NextApiResponse } from 'next'
import axios from 'axios'
import OpenAI from 'openai'

const MEETSTREAM_API_KEY = process.env.MEETSTREAM_API_KEY!
const BASE_URL = 'https://api.meetstream.ai/api/v1'
const meetstreamHeaders = {
  'Authorization': `Token ${MEETSTREAM_API_KEY}`,
  'Content-Type': 'application/json'
}

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY })

// Idempotency dedup — in production, persist to Redis / Postgres
const seenEvents = new Set<string>()

async function generateSummary(botId: string): Promise<string> {
  // Stateless transcript fetch: /detail → bot_details.transcript_id → /transcript
  const { data: detail } = await axios.get(
    `${BASE_URL}/bots/${botId}/detail`,
    { headers: meetstreamHeaders }
  )
  const transcriptId = detail?.bot_details?.transcript_id
  if (!transcriptId) {
    throw new Error(`No transcript_id on bot_details for ${botId}`)
  }

  // Response is a top-level array of segments. Per-segment text is `transcript`.
  const { data: segments } = await axios.get(
    `${BASE_URL}/transcript/${transcriptId}/get_transcript`,
    { headers: meetstreamHeaders }
  )

  const formatted = (segments as any[])
    .map(seg => `${seg.speaker}: ${seg.transcript}`)
    .join('\n')

  const completion = await openai.chat.completions.create({
    model: 'gpt-4o',
    messages: [
      {
        role: 'system',
        content: 'Extract: 1) Key decisions, 2) Action items with owners and deadlines, 3) Open questions. Format as markdown.'
      },
      { role: 'user', content: `Meeting transcript:\n\n${formatted}` }
    ]
  })

  return completion.choices[0].message.content ?? ''
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') return res.status(405).end()

  // ACK first — webhooks are NOT retried
  res.json({ status: 'ok' })

  const { bot_id, event, timestamp } = req.body
  const dedupeKey = `${bot_id}:${event}:${timestamp}`
  if (seenEvents.has(dedupeKey)) return
  seenEvents.add(dedupeKey)

  if (event === 'transcription.processed') {
    try {
      const summary = await generateSummary(bot_id)
      console.log('Meeting summary:', summary)
      // await sendToSlack(summary); await saveToNotion(summary);
    } catch (err) {
      console.error('Summary generation failed:', err)
    }
  }
}
```

---

## Pattern 5: Minimal Bot (30-Second Integration)

```javascript
// node -e "$(cat this-file.js)"
const MEETSTREAM_API_KEY = 'YOUR_API_KEY'

fetch('https://api.meetstream.ai/api/v1/bots/create_bot', {
  method: 'POST',
  headers: {
    'Authorization': `Token ${MEETSTREAM_API_KEY}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    meeting_link: 'YOUR_MEETING_LINK',
    bot_name: 'Test Bot',
    video_required: false
  })
})
.then(r => r.json())
.then(data => console.log('Bot ID:', data.bot_id, '| Transcript ID:', data.transcript_id))
.catch(err => console.error('Error:', err))
```

---

## Pattern 6: Calendar Auto-Scheduling (Full Surface)

```typescript
import axios from 'axios'

const MEETSTREAM_API_KEY = process.env.MEETSTREAM_API_KEY!
const BASE_URL = 'https://api.meetstream.ai/api/v1'
const headers = {
  'Authorization': `Token ${MEETSTREAM_API_KEY}`,
  'Content-Type': 'application/json'
}

// ─── Connect ────────────────────────────────────────────────────────────────
async function connectCalendar(refreshToken: string, clientId: string, clientSecret: string) {
  const { data } = await axios.post(`${BASE_URL}/calendar/create_calendar`, {
    google_refresh_token: refreshToken,
    google_client_id: clientId,
    google_client_secret: clientSecret
  }, { headers })
  console.log('Connected:', data.user_email)
  return data
}

// ─── Disconnect (method inconsistency: try POST, fall back to DELETE) ───────
async function disconnectCalendar(refreshToken: string, clientId: string, clientSecret: string) {
  const body = {
    google_refresh_token: refreshToken,
    google_client_id: clientId,
    google_client_secret: clientSecret
  }
  try {
    return (await axios.post(`${BASE_URL}/calendar/disconnect`, body, { headers })).data
  } catch (err: any) {
    if (err.response?.status === 405) {
      return (await axios.delete(`${BASE_URL}/calendar/disconnect`, { headers, data: body })).data
    }
    throw err
  }
}

// ─── List calendars / events ────────────────────────────────────────────────
async function listCalendars() {
  return (await axios.get(`${BASE_URL}/calendar/calendars`, { headers })).data
}

async function listEvents() {
  // /calendar/events syncs from Google; /calendar/get_events reads local DB only
  const { data } = await axios.get(`${BASE_URL}/calendar/events`, { headers })
  for (const ev of data.results ?? []) {
    console.log(`${ev.start_time} — ${ev.meeting_platform} — ${ev.meeting_url}`)
  }
  return data
}

// ─── Schedule per event with full bot_config + recurring options ────────────
async function scheduleBotForEvent(eventId: string, botConfig: object, options: {
  occurrenceDate?: string
  scheduleAllOccurrences?: boolean
  occurrenceLimit?: number
  recurringEvent?: boolean
} = {}) {
  try {
    const { data } = await axios.post(`${BASE_URL}/calendar/schedule/${eventId}`, {
      bot_config: botConfig,
      occurrence_date: options.occurrenceDate,
      schedule_all_occurrences: options.scheduleAllOccurrences,
      occurrence_limit: options.occurrenceLimit,
      recurring_event: options.recurringEvent
    }, { headers })
    return data
  } catch (err: any) {
    if (err.response?.status === 409) {
      // Already scheduled — get the existing bot_id and PATCH instead
      console.log('Already scheduled. Existing bot_id:', err.response.data.bot_id)
      return err.response.data
    }
    throw err
  }
}

async function unscheduleEvent(eventId: string, options: {
  cancelAllOccurrences?: boolean
  fromDate?: string
} = {}) {
  return (await axios.delete(`${BASE_URL}/calendar/schedule/${eventId}`, {
    headers,
    data: {
      cancel_all_occurrences: options.cancelAllOccurrences,
      from_date: options.fromDate
    }
  })).data
}

// ─── Scheduled bot management ──────────────────────────────────────────────
async function listScheduledBots() {
  return (await axios.get(`${BASE_URL}/calendar/scheduled_bots`, { headers })).data
}

async function rescheduleBot(botId: string, opts: {
  scheduledJoinTime?: string
  botUsername?: string
  customAttributes?: Record<string, string>
}) {
  return (await axios.patch(`${BASE_URL}/calendar/scheduled_bots/${botId}`, {
    scheduled_join_time: opts.scheduledJoinTime,
    bot_username: opts.botUsername,
    custom_attributes: opts.customAttributes
  }, { headers })).data
}

async function deleteScheduledBot(botId: string) {
  return (await axios.delete(`${BASE_URL}/calendar/scheduled_bots/${botId}`, { headers })).data
}

// ─── Auto-scheduling ───────────────────────────────────────────────────────
async function enableAutoSchedule(defaultBotConfig: object) {
  return (await axios.post(`${BASE_URL}/calendar/auto-schedule/enable`, {
    default_bot_config: defaultBotConfig
  }, { headers })).data
}

async function disableAutoSchedule() {
  return (await axios.post(`${BASE_URL}/calendar/auto-schedule/disable`, {}, { headers })).data
}

async function getAutoScheduleSettings() {
  return (await axios.get(`${BASE_URL}/calendar/auto-schedule/settings`, { headers })).data
}

// ─── Recurring events ──────────────────────────────────────────────────────
async function toggleRecurrence(eventId: string, recurringEnabled: boolean) {
  // NOTE: path has no event_id; event_id goes in the body
  return (await axios.post(`${BASE_URL}/calendar/toggle-recurrence`, {
    event_id: eventId,
    recurring_enabled: recurringEnabled
  }, { headers })).data
}

async function autoRescheduleNextOccurrence() {
  return (await axios.post(`${BASE_URL}/calendar/auto-reschedule`, {}, { headers })).data
}
```

---

## Pattern 7: Live Audio Receiver (binary frame decoder)

`live_audio_required` streams binary frames over a WebSocket. Decode with this exact wire format.

```typescript
// npm install ws @types/ws
import { WebSocketServer, WebSocket } from 'ws'
import { writeFileSync, appendFileSync } from 'fs'

interface AudioFrame {
  speakerId: string
  speakerName: string
  pcmData: Buffer  // raw PCM16 LE @ 48kHz mono
}

function decodeAudioFrame(buffer: Buffer): AudioFrame | null {
  if (buffer.length < 5 || buffer[0] !== 0x01) return null  // msg_type must be 0x01

  // Speaker ID: 2-byte length prefix + UTF-8 string
  const sidLen = buffer.readUInt16LE(1)
  const speakerId = buffer.subarray(3, 3 + sidLen).toString('utf-8')

  // Speaker Name: 2-byte length prefix + UTF-8 string
  let off = 3 + sidLen
  const snameLen = buffer.readUInt16LE(off)
  off += 2
  const speakerName = buffer.subarray(off, off + snameLen).toString('utf-8')
  off += snameLen

  // Remaining bytes are raw PCM16 LE @ 48kHz mono
  const pcmData = buffer.subarray(off)
  return { speakerId, speakerName, pcmData }
}

const wss = new WebSocketServer({ port: 8765, path: '/audio' })

wss.on('connection', (ws: WebSocket) => {
  let botId: string | null = null
  const perSpeakerBuffers = new Map<string, Buffer[]>()

  ws.on('message', (raw: Buffer, isBinary: boolean) => {
    if (!isBinary) {
      // First message is the JSON handshake
      const msg = JSON.parse(raw.toString())
      if (msg.type === 'ready') {
        botId = msg.bot_id
        console.log(`Live audio connected for bot ${botId}`)
      }
      return
    }

    const frame = decodeAudioFrame(raw)
    if (!frame) return

    // "NoSpeaker" is a sentinel when MeetStream can't attribute audio
    if (frame.speakerName === 'NoSpeaker') return

    const buf = perSpeakerBuffers.get(frame.speakerName) ?? []
    buf.push(frame.pcmData)
    perSpeakerBuffers.set(frame.speakerName, buf)

    const durationSec = (frame.pcmData.length / 2) / 48000
    console.log(`${frame.speakerName} (${frame.speakerId}): ${durationSec.toFixed(2)}s`)
  })

  ws.on('close', (code: number) => {
    console.log(`Audio stream closed for bot ${botId} with code ${code}`)
    // Persist or process the accumulated per-speaker buffers here
  })
})

console.log('Live audio receiver: ws://localhost:8765/audio')
```

Then on `create_bot`:
```typescript
await axios.post(`${BASE_URL}/bots/create_bot`, {
  meeting_link: '...',
  bot_name: 'Audio Listener',
  live_audio_required: { websocket_url: 'wss://your-server.com/audio' }
}, { headers })
```

---

## Pattern 8: Live Video Receiver (fMP4 over WebSocket)

Supported on **Google Meet + Teams only — NOT Zoom**.

```typescript
// npm install ws @types/ws
import { WebSocketServer, WebSocket } from 'ws'
import { createWriteStream, WriteStream } from 'fs'

const wss = new WebSocketServer({ port: 8767, path: '/video' })

interface VideoSession {
  botId: string
  output: WriteStream | null
  streamInfo?: any
}

wss.on('connection', (ws: WebSocket) => {
  const session: VideoSession = { botId: '', output: null }

  ws.on('message', (raw: Buffer, isBinary: boolean) => {
    if (isBinary) {
      // fMP4 chunk — append in order
      if (session.output) session.output.write(raw)
      return
    }

    const msg = JSON.parse(raw.toString())

    if (msg.type === 'video_stream_start') {
      session.botId = msg.bot_id
      session.streamInfo = msg
      const filename = `video-${msg.bot_id}.mp4`
      session.output = createWriteStream(filename)
      console.log(`Stream start for ${msg.bot_id}:`, {
        codec: msg.codec,
        container: msg.container,
        resolution: `${msg.width}x${msg.height}@${msg.framerate}fps`,
        audio_codec: msg.audio_codec
      })

    } else if (msg.type === 'video_latency_ping') {
      // MUST reply with video_latency_pong
      ws.send(JSON.stringify({
        type: 'video_latency_pong',
        seq: msg.seq,
        sent_at_ms: msg.sent_at_ms,
        server_received_at_ms: Date.now(),
        bot_id: msg.bot_id
      }))

    } else if (msg.type === 'video_stream_end') {
      console.log(`Stream end for ${msg.bot_id}: ${msg.duration_seconds}s`)
      session.output?.end()
    }
  })

  ws.on('close', () => {
    session.output?.end()
  })
})

console.log('Live video receiver: ws://localhost:8767/video')
```

Then on `create_bot`:
```typescript
await axios.post(`${BASE_URL}/bots/create_bot`, {
  meeting_link: 'https://meet.google.com/...',  // Meet or Teams only
  bot_name: 'Video Listener',
  video_required: true,
  live_video_required: { websocket_url: 'wss://your-server.com/video' }
}, { headers })
```

---

## Pattern 9: MIA — AI Agent in a Meeting

```typescript
import axios from 'axios'

const MEETSTREAM_API_KEY = process.env.MEETSTREAM_API_KEY!
const BASE_URL = 'https://api.meetstream.ai/api/v1'
const headers = { 'Authorization': `Token ${MEETSTREAM_API_KEY}`, 'Content-Type': 'application/json' }

// ─── 1. Create a MIA agent configuration ─────────────────────────────────────
async function createPipelineAgent() {
  const { data } = await axios.post(`${BASE_URL}/mia`, {
    agent_name: 'Meeting Assistant',
    mode: 'pipeline',
    model: {
      provider: 'openai',
      model: 'gpt-4.1',
      system_prompt: 'You are a helpful meeting assistant. Summarize decisions and track action items.'
    },
    voice: { provider: 'openai', voice_id: 'nova' },
    transcriber: { provider: 'deepgram', model: 'nova-3', language: 'en' },
    agent: { response_type: 'voice', first_message: "Hello! I'm your meeting assistant." }
  }, { headers })
  return data.agent_config_id as string
}

async function createRealtimeAgent() {
  const { data } = await axios.post(`${BASE_URL}/mia`, {
    agent_name: 'Fast Voice Agent',
    mode: 'realtime',
    model: {
      provider: 'openai',
      model: 'gpt-4o-realtime-preview',
      system_prompt: 'You are a concise, helpful assistant.',
      voice: 'alloy'
    }
  }, { headers })
  return data.agent_config_id as string
}

// ─── 2. List / get / update / delete ─────────────────────────────────────────
async function listAgents() {
  return (await axios.get(`${BASE_URL}/mia`, { headers })).data  // {agent_configs[], count}
}

async function getAgent(agentConfigId: string) {
  return (await axios.get(`${BASE_URL}/mia`, { headers, params: { agent_config_id: agentConfigId } })).data
}

async function updateAgent(agentConfigId: string, updates: object) {
  return (await axios.put(`${BASE_URL}/mia`, { agent_config_id: agentConfigId, ...updates }, { headers })).data
}

async function deleteAgent(agentConfigId: string) {
  // DELETE uses query param, NOT path id
  return (await axios.delete(`${BASE_URL}/mia`, { headers, params: { agent_config_id: agentConfigId } })).data
}

// ─── 3. Attach to a bot using the hosted MeetStream bridge ──────────────────
async function spawnAgentBot(meetingLink: string, agentConfigId: string) {
  const { data } = await axios.post(`${BASE_URL}/bots/create_bot`, {
    meeting_link: meetingLink,
    bot_name: 'AI Agent',
    agent_config_id: agentConfigId,
    socket_connection_url: { websocket_url: 'wss://agent-meetstream-prd-main.meetstream.ai/bridge' },
    live_audio_required: { websocket_url: 'wss://agent-meetstream-prd-main.meetstream.ai/bridge/audio' }
  }, { headers })
  return data.bot_id
}
```

---

## Pattern 10: Webhook Signature Verification (Express)

```typescript
import express, { Request, Response, NextFunction } from 'express'
import crypto from 'crypto'

const app = express()
const WEBHOOK_SECRET = process.env.MEETSTREAM_WEBHOOK_SECRET!

// Capture raw body for HMAC
app.use(express.json({
  verify: (req: any, _res, buf) => { req.rawBody = buf }
}))

function verifySignature(req: Request): boolean {
  const sig = req.headers['x-meetstream-signature'] as string | undefined
  if (!sig || !sig.startsWith('sha256=')) return false
  const received = sig.slice(7)
  const expected = crypto.createHmac('sha256', WEBHOOK_SECRET)
    .update((req as any).rawBody)
    .digest('hex')
  return crypto.timingSafeEqual(Buffer.from(received), Buffer.from(expected))
}

app.post('/webhook', (req: Request, res: Response) => {
  if (!verifySignature(req)) return res.status(401).json({ error: 'invalid signature' })
  // const ts = req.headers['x-meetstream-timestamp']  // check replay window if desired
  res.json({ status: 'ok' })
  console.log('Verified:', req.body.event, 'for bot', req.body.bot_id)
})
```

---

## Utility: Poll Bot Status

```typescript
async function waitForTranscript(botId: string, timeoutMs = 600_000): Promise<any[]> {
  // Stateless polling — uses bot_details.transcript_id, no transcript_id arg needed
  const start = Date.now()
  const h = { 'Authorization': `Token ${process.env.MEETSTREAM_API_KEY}` }

  while (Date.now() - start < timeoutMs) {
    const { data: statusData } = await axios.get(
      `https://api.meetstream.ai/api/v1/bots/${botId}/status`,
      { headers: h }
    )
    console.log(`Status: ${statusData.status}`)

    if (['Stopped', 'NotAllowed', 'Denied', 'Error'].includes(statusData.status)) {
      const { data: detail } = await axios.get(
        `https://api.meetstream.ai/api/v1/bots/${botId}/detail`,
        { headers: h }
      )
      const tid = detail?.bot_details?.transcript_id
      if (tid) {
        try {
          const { data: segments } = await axios.get(
            `https://api.meetstream.ai/api/v1/transcript/${tid}/get_transcript`,
            { headers: h }
          )
          return segments  // top-level array
        } catch { /* not ready yet, keep polling */ }
      }
    }

    await new Promise(r => setTimeout(r, 5000))
  }
  throw new Error('Timed out waiting for transcript')
}
```
