import { Square } from 'lucide-react'
import { useState, type KeyboardEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

export function ChatInput({
  disabled,
  onSend,
  onStop,
}: {
  disabled: boolean
  onSend: (text: string) => void
  onStop: () => void
}) {
  const [text, setText] = useState('')

  function submit() {
    if (!text.trim()) return
    onSend(text)
    setText('')
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        submit()
      }}
      className="flex items-end gap-2 rounded-lg border border-input bg-secondary p-1.5 pl-3.5"
    >
      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a question..."
        disabled={disabled}
        rows={1}
        className="max-h-40 min-h-0 resize-none overflow-y-auto border-none bg-transparent py-1.5 shadow-none focus-visible:ring-0"
      />
      {disabled ? (
        <Button type="button" onClick={onStop} aria-label="Stop generating">
          <Square className="size-4" />
        </Button>
      ) : (
        <Button type="submit" disabled={!text.trim()}>
          Send
        </Button>
      )}
    </form>
  )
}
