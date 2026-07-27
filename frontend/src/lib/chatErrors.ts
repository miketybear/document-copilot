import { ApiError } from '@/lib/http'

const DETAIL_MESSAGES: Record<string, string> = {
  'Thread not found': 'This chat could not be found.',
  'Missing bearer token': 'Your session expired. Please sign in again.',
  'Invalid or expired token': 'Your session expired. Please sign in again.',
}

// Fixed strings the backend streams via stream_error() (app/chat/orchestrator.py) — already
// written to be shown to end users as-is, so they pass through unchanged.
const KNOWN_STREAM_MESSAGES = [
  'The assistant is unavailable right now. Please try again.',
  "The assistant couldn't produce a fully grounded answer. Please rephrase your question and try again.",
]

const GENERIC_MESSAGE = 'Something went wrong. Please try again.'
const NETWORK_MESSAGE = "Can't reach the server. Check your connection and try again."

/** Extracts FastAPI's `{"detail": "..."}` error body shape, if the text is JSON of that shape. */
function extractDetail(text: string): string | undefined {
  try {
    const parsed: unknown = JSON.parse(text)
    if (parsed && typeof parsed === 'object' && typeof (parsed as { detail?: unknown }).detail === 'string') {
      return (parsed as { detail: string }).detail
    }
  } catch {
    // not JSON
  }
  return undefined
}

/** Maps a raw error from the chat stream (network failure, HTTP error body, or a stream error event) to user-facing text. */
export function describeChatError(error: Error): string {
  if (KNOWN_STREAM_MESSAGES.includes(error.message)) {
    return error.message
  }

  const detail = extractDetail(error.message)
  if (detail !== undefined) {
    return DETAIL_MESSAGES[detail] ?? GENERIC_MESSAGE
  }

  console.error('Unrecognized chat error:', error.message)
  return NETWORK_MESSAGE
}

export function describeApiError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.isNetworkError) return NETWORK_MESSAGE
    const detail = extractDetail(error.message)
    if (detail !== undefined) return DETAIL_MESSAGES[detail] ?? GENERIC_MESSAGE
    if (error.status === 404) return 'This chat could not be found.'
  }
  console.error('Unrecognized API error:', error)
  return GENERIC_MESSAGE
}
