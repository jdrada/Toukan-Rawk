# Toukan iOS App — MVP Spec

## Overview

Native iOS app (Swift + SwiftUI) that records meeting audio via voice commands (Siri) and uploads it to the backend for AI processing. The mobile app is exclusively for **capturing** — reviewing happens on the web.

**Core principle**: Recording must be resilient. Once started, it continues in the background — phone locked, screen off, app backgrounded. The audio is never lost.

---

## User Flow

### Happy Path

1. User says **"Hey Siri, start recording with Toukan"**
2. Siri launches the app (or brings it to foreground) and starts recording immediately
3. Screen shows a minimal recording indicator (waveform/timer) — no interaction needed
4. **User locks phone, puts it in pocket** — recording continues in background
5. User says **"Hey Siri, stop recording with Toukan"**
6. Recording stops, audio file is saved locally
7. App uploads the .m4a file to the backend in the background
8. User sees the recording appear in the history list with upload status
9. Hours later: user opens the **web app** to review summary, key points, and transcript

### Offline Path

1. Same as above, but device has no connectivity
2. Audio is saved locally, marked as "pending upload"
3. When connectivity returns, the app auto-uploads queued recordings
4. User can open the app anytime to see the queue status

---

## Screens

### Screen 1: Recording Screen (Home)

This is the main and default screen. Minimal UI — just what's needed.

**Idle State:**
- App name/logo at the top
- Large circular "Start Recording" button in the center (manual fallback)
- Subtle text: _"Or say 'Hey Siri, start recording with Toukan'"_
- Bottom: link/tab to recording history

**Recording State:**
- Background color changes subtly (e.g., slight red/warm tint) to indicate active recording
- Elapsed time counter (MM:SS)
- Simple audio level indicator (waveform or pulsing circle)
- "Stop Recording" button
- No other interactive elements — the screen should be glanceable and non-distracting
- **This state persists even when the app is backgrounded or screen is off** — when the user returns, they see the timer still running

**Transition after stopping:**
- Brief confirmation ("Recording saved") with a checkmark animation
- Returns to idle state
- Upload begins in background

### Screen 2: Recording History

A simple list of all recordings stored locally.

**Each row shows:**
- Date and time of recording
- Duration (e.g., "12m 34s")
- Upload status indicator:
  - **Pending** — saved locally, waiting to upload (gray)
  - **Uploading** — transfer in progress with progress indicator (blue)
  - **Uploaded** — successfully sent to backend (green checkmark)
  - **Failed** — upload failed, will retry (red, with manual retry button)

**List behavior:**
- Sorted by most recent first
- Pull-to-refresh triggers upload retry for any pending/failed items
- No playback or detail view in MVP (review happens on web)

---

## Background Recording

This is a critical feature. The app **must** keep recording when:
- User locks the phone
- Screen turns off
- User switches to another app
- User receives a phone call (pause and resume after call ends)

### Implementation

1. **AVAudioSession** category: `.playAndRecord` with `.defaultToSpeaker` option
   - `.playAndRecord` is required (not just `.record`) to keep the audio session active in background
2. **Background mode**: `UIBackgroundModes: audio` in Info.plist
   - This tells iOS the app needs to keep running for audio tasks
3. **Audio session activation**: Call `setActive(true)` when recording starts, `setActive(false)` when done
4. **Interruption handling**: Observe `AVAudioSession.interruptionNotification`
   - On interruption began (phone call): pause recording
   - On interruption ended: resume recording automatically if possible
5. **Route change handling**: Observe `AVAudioSession.routeChangeNotification`
   - Handle headphone disconnect, Bluetooth changes, etc.

### What the User Sees

- **Lock screen**: iOS shows a recording indicator (orange dot in status bar + "Toukan is using your microphone" on lock screen)
- **When returning to app**: The recording screen shows the elapsed time, which has been counting the whole time
- **Control Center**: No media controls needed (we're not playing audio)

---

## Siri Integration (AppIntents)

### Intents to Implement

**1. StartRecordingIntent**
- Trigger phrases: "Start recording with Toukan", "Record with Toukan", "Toukan start listening"
- Action: Opens app → immediately starts audio recording
- Siri confirmation: "Recording started" (spoken response)
- If already recording: "Toukan is already recording" (no-op)

**2. StopRecordingIntent**
- Trigger phrases: "Stop recording with Toukan", "Toukan stop listening", "Stop Toukan"
- Action: Stops current recording → saves file → begins upload
- Siri confirmation: "Recording saved. I'll upload it in the background."
- If not recording: "Toukan isn't recording right now" (no-op)

### Implementation Notes

- Use the `AppIntent` protocol (iOS 16+)
- Register intents in an `AppShortcutsProvider` so they appear in Shortcuts app
- Both intents should work when app is in foreground OR background
- Intents must handle the case where the app was not running (cold launch → start recording)
- Target **iOS 17+** minimum to get the best AppIntents support (donate shortcuts automatically)

---

## Audio Recording

### Configuration

| Setting | Value |
|---------|-------|
| Format | AAC (.m4a) |
| Sample rate | 44,100 Hz |
| Channels | Mono (1 channel — sufficient for voice, halves file size) |
| Bit rate | 64 kbps (tested sufficient for Whisper transcription) |
| Max duration | No hard limit |

> **Note on 64 kbps**: Whisper was trained on a wide variety of audio quality and handles compressed audio well. 64 kbps mono AAC is more than sufficient for speech recognition — the bottleneck is room acoustics and background noise, not bitrate.

### Technical Details

- Use `AVAudioRecorder` with `AVAudioSession` category `.playAndRecord`
- Enable background audio mode (`UIBackgroundModes: audio`) — **this is what allows recording to continue when the phone is locked or screen is off**
- File naming: `toukan_{timestamp_iso}.m4a` (e.g., `toukan_2024-01-15T14-30-00.m4a`)
- Save to app's Documents directory for persistence

### Permissions

- Request microphone permission on first launch with a clear explanation
- `NSMicrophoneUsageDescription`: "Toukan needs microphone access to record your meetings"
- If permission denied, show a settings redirect prompt

---

## Upload Pipeline

### Flow

```
Recording stops
    ↓
Save .m4a to local storage
    ↓
Create upload record in local DB (status: pending)
    ↓
Check connectivity
    ├─ Online → Start upload immediately
    └─ Offline → Queue for later (monitor with NWPathMonitor)
         ↓
Upload: POST /upload (multipart/form-data)
    ├─ Success → Mark as "uploaded", store memory_id from response
    └─ Failure → Mark as "failed", schedule retry
```

### Backend API Contract

```
POST /upload
Content-Type: multipart/form-data

Body:
  file: <audio file binary> (field name: "file")

Response (201):
{
  "memory_id": "uuid",
  "status": "processing",
  "message": "Audio uploaded and processing enqueued"
}
```

### Upload Implementation

- Use `URLSession` with background upload configuration (`URLSessionConfiguration.background`)
- This allows uploads to continue even if the app is suspended or terminated
- Retry strategy: exponential backoff (1s, 2s, 4s, 8s, 16s) up to 5 attempts
- Monitor connectivity with `NWPathMonitor` — auto-trigger pending uploads when connection is restored
- Show upload progress in the history list

### Local Storage

- Audio files: app's Documents directory (persists across app launches)
- Upload metadata: **SwiftData** (or UserDefaults for simplicity in MVP)
- Each record stores:
  - `id`: UUID
  - `filePath`: String (relative path to .m4a)
  - `recordedAt`: Date
  - `duration`: TimeInterval
  - `uploadStatus`: enum (pending, uploading, uploaded, failed)
  - `memoryId`: String? (from backend response after upload)
  - `retryCount`: Int
  - `lastAttempt`: Date?

### Storage Cleanup

- After successful upload + confirmation, keep local file for 7 days as safety net
- After 7 days, delete local audio file to free storage
- Never delete a file that hasn't been successfully uploaded

---

## Architecture

```
┌─────────────────────────────────────┐
│             SwiftUI Views           │
│  RecordingView  │  HistoryListView  │
└────────┬────────┴────────┬──────────┘
         │                 │
    ┌────▼─────────────────▼────┐
    │      RecordingManager     │  ← Singleton, owns AVAudioRecorder
    │      UploadManager        │  ← Singleton, owns URLSession background
    └────┬─────────────────┬────┘
         │                 │
    ┌────▼────┐     ┌──────▼──────┐
    │ SwiftData│     │  URLSession │
    │  (local) │     │ (background)│
    └─────────┘     └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Backend   │
                    │ POST /upload │
                    └─────────────┘
```

### Key Classes

| Class | Responsibility |
|-------|---------------|
| `RecordingManager` | Manages AVAudioRecorder lifecycle, audio session, interruption handling, background recording |
| `UploadManager` | Background URLSession, upload queue, retry logic, connectivity monitoring |
| `RecordingStore` | SwiftData persistence for recording metadata |
| `StartRecordingIntent` | Siri AppIntent — triggers RecordingManager.start() |
| `StopRecordingIntent` | Siri AppIntent — triggers RecordingManager.stop() + UploadManager.enqueue() |

### State Management

- Use `@Observable` (Observation framework, iOS 17+) for `RecordingManager` and `UploadManager`
- Views observe state changes reactively
- No need for heavy architecture (MVVM is fine, no Redux/TCA overhead for 2 screens)

---

## Edge Cases & Error Handling

| Scenario | Behavior |
|----------|----------|
| Phone locked during recording | Recording continues via background audio mode. Orange dot shown in status bar. |
| Screen turns off during recording | Same — recording is unaffected. AVAudioRecorder keeps running. |
| App backgrounded during recording | Same — background audio mode keeps the process alive. |
| Phone call during recording | Pause recording on interruption, resume automatically when call ends. |
| App force-killed during recording | Partial file is saved by AVAudioRecorder automatically. Marked as pending upload on next launch. |
| App killed during upload | Background URLSession continues the upload independently of the app process. |
| Phone runs out of storage | Check available space before recording. Show warning if < 100MB free. |
| Upload fails 5 times | Mark as "failed", stop retrying automatically. Show manual retry in history. |
| User starts new recording while one is active | Ignore / show brief "already recording" message. |
| Backend is down | Same as offline — queue and retry. |
| Very long recording (2+ hours) | Works fine with AAC at ~0.5MB/min. A 2-hour meeting ≈ 60MB. Monitor file size, warn at 500MB. |

---

## iOS Project Configuration

| Setting | Value |
|---------|-------|
| Minimum deployment target | iOS 17.0 |
| Language | Swift 5.9+ |
| UI framework | SwiftUI |
| Background modes | Audio (`UIBackgroundModes: audio`) |
| Capabilities | Siri (for AppIntents) |
| Dependencies | None (all Apple frameworks) |

### Info.plist Keys

- `NSMicrophoneUsageDescription`: "Toukan needs microphone access to record your meetings"
- `NSSiriUsageDescription`: "Toukan uses Siri to start and stop recording hands-free"

---

## Out of Scope (MVP)

These are explicitly **not** in the iOS MVP:

- Audio playback on device
- Viewing transcripts/summaries on mobile (web only per bitacora)
- Speaker diarization
- Real-time transcription
- Push notifications when processing completes
- User authentication (single-user for now, no device identifier)
- Android version
- Apple Watch companion
