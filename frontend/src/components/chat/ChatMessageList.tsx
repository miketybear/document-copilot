import type { ChatStatus, UIMessage } from 'ai'

import { CitationCluster } from '@/components/chat/Citation'
import { MarkdownAnswer } from '@/components/chat/MarkdownAnswer'
import { getCitations } from '@/lib/citations'

const STATUS_LABEL: Record<'submitted' | 'streaming', string> = {
  submitted: 'Searching documents…',
  streaming: 'Answering…',
}

function StatusLine({ status }: { status: 'submitted' | 'streaming' }) {
  return (
    <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
      <span className="size-1.5 animate-pulse rounded-full bg-primary" aria-hidden="true" />
      {STATUS_LABEL[status]}
    </p>
  )
}

export function ChatMessageList({ messages, status }: { messages: UIMessage[]; status: ChatStatus }) {
  const lastMessage = messages.at(-1)
  const isActive = status === 'submitted' || status === 'streaming'

  return (
    <div className="flex flex-col gap-4">
      {messages.map((message) => {
        const isPending = message.id === lastMessage?.id && isActive
        const citations = getCitations(message)
        const text = message.parts
          .filter((part) => part.type === 'text')
          .map((part) => part.text)
          .join('')

        if (message.role === 'user') {
          return (
            <div
              key={message.id}
              className="ml-auto max-w-[78%] rounded-2xl rounded-br-sm border border-border bg-secondary px-3.5 py-2 text-sm text-secondary-foreground"
            >
              <p className="whitespace-pre-wrap">{text}</p>
            </div>
          )
        }

        return (
          <div key={message.id} className="flex max-w-[85%] flex-col gap-2.5 text-[15px] leading-relaxed">
            {isPending && <StatusLine status={status as 'submitted' | 'streaming'} />}

            {text && <MarkdownAnswer text={text} />}

            {!isPending && text && citations.length > 0 && <CitationCluster citations={citations} />}

            {!isPending && text && citations.length === 0 && (
              <p className="flex w-fit items-center gap-1.5 rounded-md bg-warning px-2.5 py-1 text-xs text-warning-foreground">
                <span className="size-[5px] rounded-full bg-warning-foreground" aria-hidden="true" />
                No source passages were cited for this answer.
              </p>
            )}
          </div>
        )
      })}

      {isActive && lastMessage?.role === 'user' && <StatusLine status={status as 'submitted' | 'streaming'} />}
    </div>
  )
}
