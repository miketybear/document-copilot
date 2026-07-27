import type { UIMessage, UIMessagePart, UITools } from 'ai'

export type CitationData = {
  chunkId: string
  documentId: string
  documentTitle: string
  documentType: string
  department: string | null
  version: string | null
  effectiveDate: string | null
  headingPath: string[]
  excerpt: string
}

export type CitationPart = { type: 'data-citation'; id?: string; data: CitationData }

export function isCitationPart(
  part: UIMessagePart<Record<string, unknown>, UITools>,
): part is CitationPart {
  return part.type === 'data-citation'
}

export function getCitations(message: UIMessage): CitationData[] {
  return message.parts.filter(isCitationPart).map((part) => part.data)
}
