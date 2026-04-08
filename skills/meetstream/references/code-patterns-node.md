# MeetStream — Node.js / TypeScript Code Patterns

Complete, runnable implementations for common MeetStream use cases.

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

async function createBot(meetingLink: string, callbackUrl: string): Promise<string> {
  const { data } = await axios.post(`${BASE_URL}/bots/create_bot`, {
    meeting_link: meetingLink,
    bot_name: 'Recorder',
    audio_required: true,
    video_required: false,
    callback_url: callbackUrl,
    recording_config: {
      transcript: {
        provider: { deepgram: { language: 'en', model: 'nova-3' } }
      },
      retention: { type: 'timed', hours: 48 }
    },
    automatic_leave: {
      waiting_room_timeout: 300,
      everyone_left_timeout: 60,
      in_call_recording_timeout: 7200,
      recording_permission_denied_timeout: 10
    }
  }, { headers })

  console.log(`Bot created: ${data.bot_id}`)
  return data.bot_id
}

async function getTranscript(botId: string): Promise<any> {
  const { data } = await axios.get(`${BASE_URL}/bots/${botId}/get_bot_transcript`, { headers })
  return data
}

app.post('/webhook', async (req: Request, res: Response) => {
  const { bot_id, event } = req.body
  console.log(`Event: ${event} | Bot: ${bot_id}`)

  if (event === 'transcription.processed') {
    const transcript = await getTranscript(bot_id)
    for (const segment of transcript.transcript ?? []) {
      console.log(`[${segment.speaker}] ${segment.text}`)
    }
  }

  res.json({ status: 'ok' })
})

app.listen(3000, () => console.log('Listening on :3000'))

// Usage: createBot('https://zoom.us/j/123456789', 'https://your-ngrok.ngrok.io/webhook')
```

---

## Pattern 2: Real-Time Transcription (WebSocket Server)

```typescript
// npm install ws express axios @types/ws
import { WebSocketServer, WebSocket } from 'ws'
import axios from 'axios'

const MEETSTREAM_API_KEY = process.env.MEETSTREAM_API_KEY!
const BASE_URL = 'https://api.meetstream.ai/api/v1'
const headers = {
  'Authorization': `Token ${MEETSTREAM_API_KEY}`,
  'Content-Type': 'application/json'
}

interface TranscriptChunk {
  speakerName: string
  timestamp: string
  transcript: string
  words: Array<{
    word: string
    start: number
    end: number
    confidence: number
    speaker: string
  }>
}

// Start WebSocket server for live transcripts
const wss = new WebSocketServer({ port: 8765 })

wss.on('connection', (ws: WebSocket) => {
  console.log('MeetStream connected — streaming transcript...')

  ws.on('message', (raw: Buffer) => {
    const chunk: TranscriptChunk = JSON.parse(raw.toString())
    const { speakerName, timestamp, transcript } = chunk
    console.log(`[${timestamp}] ${speakerName}: ${transcript}`)

    // Add your processing here:
    // - Detect intent signals (pricing, objections, competitor mentions)
    // - Build live summary
    // - Trigger webhooks to your AI pipeline
    processChunk(chunk)
  })
})

function processChunk(chunk: TranscriptChunk) {
  const text = chunk.transcript.toLowerCase()

  // Example: detect key moments
  if (text.includes('follow up') || text.includes('action item')) {
    console.log(`ACTION ITEM detected from ${chunk.speakerName}: "${chunk.transcript}"`)
  }

  if (text.includes('competitor') || text.includes('alternative')) {
    console.log(`COMPETITIVE MENTION from ${chunk.speakerName}: "${chunk.transcript}"`)
  }
}

async function createRealtimeBot(meetingLink: string): Promise<string> {
  const { data } = await axios.post(`${BASE_URL}/bots/create_bot`, {
    meeting_link: meetingLink,
    bot_name: 'AI Assistant',
    audio_required: true,
    video_required: false,
    live_transcription_required: {
      websocket_url: 'wss://your-server.com/transcripts'  // point to this server
    },
    automatic_leave: {
      waiting_room_timeout: 300,
      everyone_left_timeout: 60,
      in_call_recording_timeout: 7200,
      recording_permission_denied_timeout: 10
    }
  }, { headers })

  return data.bot_id
}

console.log('WebSocket server listening on ws://localhost:8765')
```

---

## Pattern 3: Interactive Bot (Control via WebSocket)

```typescript
// npm install ws axios
import { WebSocketServer, WebSocket } from 'ws'
import axios from 'axios'

const MEETSTREAM_API_KEY = process.env.MEETSTREAM_API_KEY!
const BASE_URL = 'https://api.meetstream.ai/api/v1'
const headers = {
  'Authorization': `Token ${MEETSTREAM_API_KEY}`,
  'Content-Type': 'application/json'
}

const controlServer = new WebSocketServer({ port: 8766 })

controlServer.on('connection', (ws: WebSocket) => {
  ws.on('message', (raw: Buffer) => {
    const data = JSON.parse(raw.toString())

    if (data.type === 'ready') {
      const botId: string = data.bot_id
      console.log(`Bot ${botId} is ready in the meeting`)

      // Send greeting to meeting chat
      ws.send(JSON.stringify({
        command: 'sendmsg',
        message: "Hi everyone! I'm your meeting assistant. I'll be capturing notes today.",
        bot_id: botId
      }))
    }
  })
})

async function createInteractiveBot(meetingLink: string): Promise<string> {
  const { data } = await axios.post(`${BASE_URL}/bots/create_bot`, {
    meeting_link: meetingLink,
    bot_name: 'Meeting Assistant',
    audio_required: true,
    video_required: false,
    socket_connection_url: { url: 'wss://your-server.com/bot-control' },
    live_transcription_required: {
      websocket_url: 'wss://your-server.com/transcripts'
    },
    automatic_leave: {
      everyone_left_timeout: 60,
      recording_permission_denied_timeout: 10
    }
  }, { headers })

  return data.bot_id
}

console.log('Bot control WebSocket: ws://localhost:8766')
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

async function generateSummary(botId: string): Promise<string> {
  // Fetch transcript
  const { data: transcriptData } = await axios.get(
    `${BASE_URL}/bots/${botId}/get_bot_transcript`,
    { headers: meetstreamHeaders }
  )

  // Format for LLM
  const formatted = (transcriptData.transcript ?? [])
    .map((seg: { speaker: string; text: string }) => `${seg.speaker}: ${seg.text}`)
    .join('\n')

  // Generate structured summary
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

  const { bot_id, event } = req.body

  if (event === 'transcription.processed') {
    const summary = await generateSummary(bot_id)
    console.log('Meeting summary:', summary)

    // Send to Slack, Notion, email, etc.
    // await sendToSlack(summary)
    // await saveToNotion(summary)
  }

  res.json({ status: 'ok' })
}
```

---

## Pattern 5: Minimal Bot (30-Second Integration)

Just want to quickly test? This is the minimum viable integration:

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
    audio_required: true,
    video_required: false
  })
})
.then(r => r.json())
.then(data => console.log('Bot ID:', data.bot_id))
.catch(err => console.error('Error:', err))
```

---

## Utility: Poll Bot Status

```typescript
async function waitForTranscript(botId: string, timeoutMs = 300000): Promise<any> {
  const start = Date.now()
  
  while (Date.now() - start < timeoutMs) {
    const { data } = await axios.get(
      `https://api.meetstream.ai/api/v1/bots/${botId}/status`,
      { headers: { 'Authorization': `Token ${process.env.MEETSTREAM_API_KEY}` } }
    )

    console.log(`Status: ${data.status}`)

    if (data.status === 'Stopped') {
      // Try to fetch transcript
      try {
        const { data: transcript } = await axios.get(
          `https://api.meetstream.ai/api/v1/bots/${botId}/get_bot_transcript`,
          { headers: { 'Authorization': `Token ${process.env.MEETSTREAM_API_KEY}` } }
        )
        return transcript
      } catch {
        // Processing not done yet, keep waiting
      }
    }

    await new Promise(resolve => setTimeout(resolve, 5000))
  }

  throw new Error('Timed out waiting for transcript')
}
```
