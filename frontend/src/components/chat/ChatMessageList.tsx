import type { UIMessage } from 'ai'

export function ChatMessageList({ messages }: { messages: UIMessage[] }) {
  return (
    <div className="flex flex-1 flex-col gap-3 overflow-y-auto">
      {messages.map((message) => (
        <div
          key={message.id}
          className={
            message.role === 'user'
              ? 'ml-auto max-w-[80%] rounded-lg bg-primary px-3 py-2 text-primary-foreground'
              : 'mr-auto max-w-[80%] rounded-lg bg-muted px-3 py-2 text-foreground'
          }
        >
          {message.parts.map((part, i) => (part.type === 'text' ? <p key={i}>{part.text}</p> : null))}
        </div>
      ))}
    </div>
  )
}
