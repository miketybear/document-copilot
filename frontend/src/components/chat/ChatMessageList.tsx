import type { ChatStatus, UIMessage } from 'ai'
import { ArrowDown, Check, Copy } from 'lucide-react'
import { useEffect, useRef, useState, type RefObject } from 'react'

import { CitationCluster } from '@/components/chat/Citation'
import { MarkdownAnswer } from '@/components/chat/MarkdownAnswer'
import { getCitations } from '@/lib/citations'
import { cn } from '@/lib/utils'

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

function CopyButton({ text, className }: { text: string; className?: string }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      return
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      aria-label={copied ? 'Copied' : 'Copy question'}
      className={cn(
        'rounded-md p-1.5 text-muted-foreground opacity-0 transition-opacity hover:bg-secondary hover:text-foreground focus-visible:opacity-100 group-hover/user-message:opacity-100',
        className,
      )}
    >
      {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
    </button>
  )
}

export function ChatMessageList({
  messages,
  status,
  scrollContainerRef,
}: {
  messages: UIMessage[]
  status: ChatStatus
  scrollContainerRef: RefObject<HTMLDivElement | null>
}) {
  const lastMessage = messages.at(-1)
  const isActive = status === 'submitted' || status === 'streaming'

  const userMessageRefs = useRef(new Map<string, HTMLDivElement>())
  const scrolledToIdRef = useRef<string | null>(null)
  const isFirstRenderRef = useRef(true)
  const interruptedRef = useRef(false)
  const [trailingSpacerHeight, setTrailingSpacerHeight] = useState(0)
  const [showJumpToLatest, setShowJumpToLatest] = useState(false)

  // A wheel/touch event only ever fires from real user input, never from our own scrollIntoView
  // calls — so it's an unambiguous signal that the user has taken over scrolling. Once that
  // happens during an active turn, stop fighting them until the next question is sent.
  useEffect(() => {
    const container = scrollContainerRef.current
    if (!container || !isActive) return

    function onManualScroll() {
      interruptedRef.current = true
      setShowJumpToLatest(true)
    }

    container.addEventListener('wheel', onManualScroll, { passive: true })
    container.addEventListener('touchmove', onManualScroll, { passive: true })
    return () => {
      container.removeEventListener('wheel', onManualScroll)
      container.removeEventListener('touchmove', onManualScroll)
    }
  }, [scrollContainerRef, isActive])

  useEffect(() => {
    // Opening a thread (or its first turn firing on mount) just lands at the bottom, like any
    // other chat app — no reserved space, nothing to pin.
    if (isFirstRenderRef.current) {
      isFirstRenderRef.current = false
      scrolledToIdRef.current = [...messages].reverse().find((message) => message.role === 'user')?.id ?? null
      const container = scrollContainerRef.current
      if (container) container.scrollTop = container.scrollHeight
      return
    }

    const lastUserMessage = [...messages].reverse().find((message) => message.role === 'user')
    if (!lastUserMessage) return

    const isNewTurn = lastUserMessage.id !== scrolledToIdRef.current
    // Once a turn is done, stop re-snapping — content above/below it is now stable and the
    // user may have scrolled away on purpose. While it's still streaming, keep re-aligning:
    // content that appears above the bubble (e.g. the previous answer's citation badge, which
    // only renders once it stops being the "pending" message) can otherwise nudge it out of
    // place after the initial jump.
    if (!isNewTurn && !isActive) {
      // The turn's final length is now known — release the reserved space instead of leaving a
      // large gap under a short answer. Animated (see the spacer's className) so it doesn't jump.
      setTrailingSpacerHeight(0)
      setShowJumpToLatest(false)
      return
    }

    // The user took over scrolling — respect it for the rest of this turn instead of yanking
    // them back to the pinned question on every streamed chunk.
    if (!isNewTurn && interruptedRef.current) return

    if (isNewTurn) {
      scrolledToIdRef.current = lastUserMessage.id
      interruptedRef.current = false
      setShowJumpToLatest(false)
      // Reserve enough room below the just-sent question so it can actually reach the top of
      // the viewport — sized to the real scroll container, not a guess. Only done here (not on
      // initial mount) so opening an old thread never shows dead space below its last message.
      setTrailingSpacerHeight(scrollContainerRef.current?.clientHeight ?? 0)
    }

    // Instant, not smooth: the question should already be in place the moment it's sent, not
    // drift there over the next few hundred ms.
    userMessageRefs.current.get(lastUserMessage.id)?.scrollIntoView({ behavior: 'auto', block: 'start' })
  }, [messages, isActive, scrollContainerRef])

  function jumpToLatest() {
    interruptedRef.current = false
    setShowJumpToLatest(false)
    const lastUserMessage = [...messages].reverse().find((message) => message.role === 'user')
    if (lastUserMessage) {
      userMessageRefs.current.get(lastUserMessage.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

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
              ref={(el) => {
                if (el) userMessageRefs.current.set(message.id, el)
                else userMessageRefs.current.delete(message.id)
              }}
              className="group/user-message ml-auto flex max-w-[78%] items-start gap-1"
            >
              <CopyButton text={text} className="mt-1.5 shrink-0" />
              <div className="rounded-2xl rounded-br-sm border border-border bg-secondary px-3.5 py-2 text-sm text-secondary-foreground">
                <p className="whitespace-pre-wrap">{text}</p>
              </div>
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

      <div
        aria-hidden="true"
        style={{
          minHeight: trailingSpacerHeight,
          // Only animate the collapse back to 0 — growing must land at full height instantly so
          // the scroll-to-top calculation above has real room to work with, not a mid-transition value.
          transition: trailingSpacerHeight === 0 ? 'min-height 300ms ease' : undefined,
        }}
      />

      {showJumpToLatest && (
        <button
          type="button"
          onClick={jumpToLatest}
          className="fixed bottom-24 left-1/2 z-10 flex -translate-x-1/2 items-center gap-1.5 rounded-full border border-border bg-secondary px-3.5 py-2 text-sm font-medium text-secondary-foreground shadow-md hover:bg-accent"
        >
          <ArrowDown className="size-4" />
          Jump to latest
        </button>
      )}
    </div>
  )
}
