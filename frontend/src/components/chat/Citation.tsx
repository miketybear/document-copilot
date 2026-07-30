import { useEffect, useState } from 'react'

import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import type { CitationData } from '@/lib/citations'

const EXCERPT_PREVIEW_LENGTH = 220

function CitationCard({ citation, highlighted }: { citation: CitationData; highlighted: boolean }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = citation.excerpt.length > EXCERPT_PREVIEW_LENGTH
  const shownExcerpt =
    expanded || !isLong ? citation.excerpt : `${citation.excerpt.slice(0, EXCERPT_PREVIEW_LENGTH)}…`

  return (
    <div
      id={`citation-${citation.chunkId}`}
      className={`border-b border-border p-3 text-sm last:border-b-0 ${highlighted ? 'bg-accent' : ''}`}
    >
      <p className="font-medium text-foreground">{citation.documentTitle}</p>
      <p className="font-mono text-xs text-muted-foreground tabular-nums">
        {[citation.department, citation.version && `v${citation.version}`, citation.effectiveDate]
          .filter(Boolean)
          .join(' · ')}
      </p>
      {citation.headingPath.length > 0 && (
        <p className="mt-1 text-xs text-primary">{citation.headingPath.join(' › ')}</p>
      )}
      <p className="mt-1.5 whitespace-pre-wrap text-muted-foreground">{shownExcerpt}</p>
      {isLong && (
        <button
          type="button"
          className="mt-1 text-xs font-medium text-primary underline"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  )
}

export function CitationCluster({
  citations,
  leading,
  onOpenSources,
}: {
  citations: CitationData[]
  leading?: React.ReactNode
  onOpenSources: (citations: CitationData[], highlightChunkId?: string) => void
}) {
  return (
    <div className="mr-auto flex max-w-[80%] flex-col gap-1.5">
      <div className="flex flex-wrap items-center gap-1.5">
        {leading}
        {citations.map((citation, i) => (
          <button
            key={citation.chunkId}
            type="button"
            aria-label={`Show source ${i + 1}: ${citation.documentTitle}`}
            className="flex size-[18px] items-center justify-center rounded-full bg-accent font-mono text-[11px] tabular-nums text-primary hover:bg-primary hover:text-primary-foreground"
            onClick={() => onOpenSources(citations, citation.chunkId)}
          >
            {i + 1}
          </button>
        ))}
        {citations.length > 0 ? (
          <button
            type="button"
            className="text-xs text-muted-foreground underline hover:text-primary"
            onClick={() => onOpenSources(citations)}
          >
            {`Show sources (${citations.length})`}
          </button>
        ) : (
          <p className="flex items-center gap-1.5 rounded-md bg-warning px-2.5 py-1 text-xs text-warning-foreground">
            <span className="size-[5px] rounded-full bg-warning-foreground" aria-hidden="true" />
            No source passages were cited for this answer.
          </p>
        )}
      </div>
    </div>
  )
}

export function SourcesPanel({
  open,
  citations,
  highlightedChunkId,
  onOpenChange,
}: {
  open: boolean
  citations: CitationData[]
  highlightedChunkId: string | null
  onOpenChange: (open: boolean) => void
}) {
  // Keep rendering the last-opened citations while the sheet is closing (rather than clearing
  // them the instant `open` flips false) so the content doesn't disappear mid slide-out animation.
  useEffect(() => {
    if (!open || !highlightedChunkId) return
    document.getElementById(`citation-${highlightedChunkId}`)?.scrollIntoView({ block: 'nearest' })
  }, [open, highlightedChunkId])

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{`Sources (${citations.length})`}</SheetTitle>
        </SheetHeader>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {citations.map((citation) => (
            <CitationCard
              key={citation.chunkId}
              citation={citation}
              highlighted={citation.chunkId === highlightedChunkId}
            />
          ))}
        </div>
      </SheetContent>
    </Sheet>
  )
}
