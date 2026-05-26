# MeetStream — Node.js / TypeScript Code Patterns

Complete, runnable implementations for common MeetStream use cases.

All endpoint paths and field names are verified against `docs.meetstream.ai`.

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

// Map bot_id -> transcript_id (returned by create_bot)
const transcriptIds = new Map<string, string>()

async function createBot(meetingLink: string, callbackUrl: string): Promise<{ botId: string; transcriptId: string | null }> {
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
      everyone_left_timeout: 300,
      voice_inactivity_timeout: 100,
      in_call_recording_timeout: 14400,
      recording_permission_denied_timeout: 60
    }
  }, { headers })

  console.log(`Bot created: ${data.bot_id} (transcript_id: ${data.transcript_id ?? 'pending'})`)
  if (data.transcript_id) transcriptIds.set(data.bot_id, data.transcript_id)
  return { botId: data.bot_id, transcriptId: data.transcript_id ?? null }
}

async function getTranscript(botId: string): Promise<any> {
  let transcriptId = transcriptIds.get(botId)

  if (!transcriptId) {
    // Try /transcriptions first
    try {
      const { data: list } = await axios.get(`${BASE_URL}/bots/${botId}/transcriptions`, { headers })
      const successful = (list.transcriptions ?? []).find((t: any) => t.status === 'Success')
      if (successful) transcriptId = successful.transcript_id
    } catch { /* fall through */ }

    // Some deployments expose it on /detail as bot_details.transcript_id
    if (!transcriptId) {
      const { data: detail } = await axios.get(`${BASE_URL}/bots/${botId}/detail`, { headers })
      transcriptId = detail.bot_details?.transcript_id ?? detail.transcript_id
    }

    if (!transcriptId) throw new Error(`No transcript_id found for bot ${botId}`)
    transcriptIds.set(botId, transcriptId!)
  }

  // Canonical path per docs. Alternate fallback observed in production:
  //   `${BASE_URL}/bots/${botId}/get_bot_transcript/${transcriptId}`
  const { data } = await axios.get(`${BASE_URL}/transcript/${transcriptId}/get_transcript`, { headers })
  return data
}

app.post('/webhook', async (req: Request, res: Response) => {
  // Always 200 ASAP — webhooks are NOT retried on non-2xx
  res.json({ status: 'ok' })

  const { bot_id, event, bot_status } = req.body
  console.log(`Event: ${event} | Bot: ${bot_id} | Status: ${bot_status ?? '-'}`)

  if (event === 'transcription.processed') {
    try {
      const transcript = await getTranscript(bot_id)
      for (const segment of transcript.transcript ?? []) {
        console.log(`[${segment.speaker}] ${segment.text}`)
      }
    } catch (err) {
      console.error('Transcript fetch failed:', err)
    }
  } else if (event === 'bot.stopped' && bot_status !== 'Stopped') {
    console.error(`Bot did not exit cleanly: bot_status=${bot_status}, message=${req.body.message}`)
  }
})

app.listen(3000, () => console.log('Listening on :3000'))

// Usage: createBot('https://zoom.us/j/123456789', 'https://your-ngrok.ngrok.io/webhook')
```

---

## Pattern 2: Real-Time Transcription (HTTPS Webhook)

Live transcription is delivered as HTTPS POSTs, **not** over WebSocket.

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
  custom_attributes?: Record<string, unknown>
}

app.post('/live-transcript', (req: Request, res: Response) => {
  res.json({ status: 'ok' })

  const chunk = req.body as LiveTranscriptChunk
  const speaker = chunk.speakerName ?? 'Unknown'
  console.log(`[${chunk.timestamp}] ${speaker}: ${chunk.transcript}`)

  processChunk(chunk)
})

function processChunk(chunk: LiveTranscriptChunk) {
  const text = chunk.transcript.toLowerCase()

  if (text.includes('follow up') || text.includes('action item')) {
    console.log(`ACTION ITEM detected from ${chunk.speakerName}: "${chunk.transcript}"`)
  }

  if (text.includes('competitor') || text.includes('alternative')) {
    console.log(`COMPETITIVE MENTION from ${chunk.speakerName}: "${chunk.transcript}"`)
  }
}

async function createRealtimeBot(meetingLink: string, webhookUrl: string): Promise<string> {
  const { data } = await axios.post(`${BASE_URL}/bots/create_bot`, {
    meeting_link: meetingLink,
    bot_name: 'AI Assistant',
    video_required: false,
    live_transcription_required: {
      webhook_url: webhookUrl  // HTTPS POST endpoint
    },
    recording_config: {
      transcript: {
        provider: {
          deepgram_streaming: {
            model: 'nova-2',
            language: 'en',
            punctuate: true,
            smart_format: true,
            endpointing: 300,
            utterance_end_ms: 1000,
            encoding: 'linear16',
            channels: 1
          }
        }
      }
    },
    automatic_leave: {
      waiting_room_timeout: 600,
      everyone_left_timeout: 300,
      in_call_recording_timeout: 14400,
      recording_permission_denied_timeout: 60
    }
  }, { headers })

  return data.bot_id
}

app.listen(3000, () => console.log('Live transcript webhook on :3000/live-transcript'))
```

---

## Pattern 3: Interactive Bot (Control via WebSocket)

The bot connects **to your WebSocket server as a client** when it joins. Use the REST endpoints (`send_message`, `send_image`) for chat — `sendaudio` over the WebSocket is for TTS or pre-recorded audio playback.

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

// Track bot WebSocket connections by bot_id
const botSockets = new Map<string, WebSocket>()

const controlServer = new WebSocketServer({ port: 8766, path: '/bot-control' })

controlServer.on('connection', (ws: WebSocket) => {
  ws.on('message', async (raw: Buffer) => {
    const data = JSON.parse(raw.toString())

    if (data.type === 'ready') {
      const botId: string = data.bot_id
      console.log(`Bot ${botId} ready: ${data.message ?? ''}`)
      botSockets.set(botId, ws)

      // Greet the meeting via REST (chat lives behind the REST endpoint)
      await axios.post(`${BASE_URL}/bots/${botId}/send_message`, {
        message: "Hi everyone! I'm your meeting assistant. I'll be taking notes today.",
        metadata: { message_type: 'text' }
      }, { headers })
    }
  })

  ws.on('close', () => {
    for (const [botId, sock] of botSockets) {
      if (sock === ws) botSockets.delete(botId)
    }
  })
})

// Send raw PCM16 LE @ 48000 Hz mono. base64-encoded. No WAV header.
function sendAudioChunk(botId: string, pcm16LeBytes: Buffer) {
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

async function createInteractiveBot(meetingLink: string, controlWsUrl: string): Promise<string> {
  const { data } = await axios.post(`${BASE_URL}/bots/create_bot`, {
    meeting_link: meetingLink,
    bot_name: 'Meeting Assistant',
    video_required: false,
    socket_connection_url: { websocket_url: controlWsUrl },  // bot dials INTO this URL
    automatic_leave: {
      waiting_room_timeout: 600,
      everyone_left_timeout: 300,
      recording_permission_denied_timeout: 60
    }
  }, { headers })

  return data.bot_id
}

console.log('Bot control WebSocket: ws://localhost:8766/bot-control')
```

---

## Pattern 4: Full Note-Taking Agent (Next.js API Route)

```typescript
// pages/api/webhook.ts (Next.js)
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

async function findTranscriptId(botId: string): Promise<string> {
  const { data } = await axios.get(
    `${BASE_URL}/bots/${botId}/transcriptions`,
    { headers: meetstreamHeaders }
  )
  const successful = (data.transcriptions ?? []).find((t: any) => t.status === 'Success')
  if (!successful) throw new Error(`No completed transcript for bot ${botId}`)
  return successful.transcript_id
}

async function generateSummary(botId: string): Promise<string> {
  const transcriptId = await findTranscriptId(botId)

  const { data: transcriptData } = await axios.get(
    `${BASE_URL}/transcript/${transcriptId}/get_transcript`,
    { headers: meetstreamHeaders }
  )

  const formatted = (transcriptData.transcript ?? [])
    .map((seg: { speaker: string; text: string }) => `${seg.speaker}: ${seg.text}`)
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

  const { bot_id, event } = req.body

  if (event === 'transcription.processed') {
    try {
      const summary = await generateSummary(bot_id)
      console.log('Meeting summary:', summary)
      // await sendToSlack(summary)
      // await saveToNotion(summary)
    } catch (err) {
      console.error('Summary generation failed:', err)
    }
  }
}
```

---

## Pattern 5: Minimal Bot (30-Second Integration)

Just want to quickly test? Minimum viable integration:

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

## Pattern 6: Calendar Auto-Scheduling

```typescript
// npm install axios
import axios from 'axios'

const MEETSTREAM_API_KEY = process.env.MEETSTREAM_API_KEY!
const BASE_URL = 'https://api.meetstream.ai/api/v1'
const headers = {
  'Authorization': `Token ${MEETSTREAM_API_KEY}`,
  'Content-Type': 'application/json'
}

async function connectCalendar(googleRefreshToken: string, googleClientId: string, googleClientSecret: string) {
  // Field names MUST be prefixed with google_
  const { data } = await axios.post(`${BASE_URL}/calendar/create_calendar`, {
    google_refresh_token: googleRefreshToken,
    google_client_id: googleClientId,
    google_client_secret: googleClientSecret
  }, { headers })

  console.log('Calendar connected:', data.user_email)
  return data
}

async function listCalendars() {
  const { data } = await axios.get(`${BASE_URL}/calendar`, { headers })
  return data
}

async function listUpcomingEvents() {
  const { data } = await axios.get(`${BASE_URL}/calendar/events`, { headers })
  for (const ev of data.results ?? []) {
    console.log(`${ev.start_time} — ${ev.meeting_platform} — ${ev.meeting_url}`)
  }
  return data
}

async function scheduleBotForEvent(eventId: string) {
  // Manually schedule a bot for a specific calendar event
  const { data } = await axios.post(`${BASE_URL}/calendar/schedule/${eventId}`, {}, { headers })
  console.log(`Scheduled bot ${data.bot_id} for event ${eventId} at ${data.scheduled_time}`)
  return data
}

async function rescheduleBot(botId: string, newJoinTime: string) {
  const { data } = await axios.patch(
    `${BASE_URL}/calendar/scheduled_bots/${botId}`,
    { scheduled_join_time: newJoinTime },
    { headers }
  )
  return data
}
```

---

## Utility: Poll Bot Status + Fetch Transcript

```typescript
async function waitForTranscript(botId: string, transcriptId: string | null, timeoutMs = 600_000): Promise<any> {
  const start = Date.now()
  const headers = { 'Authorization': `Token ${process.env.MEETSTREAM_API_KEY}` }

  while (Date.now() - start < timeoutMs) {
    const { data: statusData } = await axios.get(
      `https://api.meetstream.ai/api/v1/bots/${botId}/status`,
      { headers }
    )
    console.log(`Status: ${statusData.status}`)

    if (['Stopped', 'NotAllowed', 'Denied', 'Error'].includes(statusData.status)) {
      // Resolve transcript_id if we don't have it
      let tid = transcriptId
      if (!tid) {
        try {
          const { data: list } = await axios.get(
            `https://api.meetstream.ai/api/v1/bots/${botId}/transcriptions`,
            { headers }
          )
          const successful = (list.transcriptions ?? []).find((t: any) => t.status === 'Success')
          if (successful) tid = successful.transcript_id
        } catch { /* keep polling */ }
      }

      if (tid) {
        try {
          const { data: transcript } = await axios.get(
            `https://api.meetstream.ai/api/v1/transcript/${tid}/get_transcript`,
            { headers }
          )
          return transcript
        } catch { /* processing not done yet */ }
      }
    }

    await new Promise(resolve => setTimeout(resolve, 5000))
  }

  throw new Error('Timed out waiting for transcript')
}
```
