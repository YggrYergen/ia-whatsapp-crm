'use client'

/**
 * WhatsApp-style message formatting utilities.
 *
 * Renders WhatsApp markdown:
 *   *bold*     → <strong>bold</strong>
 *   _italic_   → <em>italic</em>
 *   ~strike~   → <del>strike</del>
 *   ```code``` → <code>code</code>
 *   `code`     → <code>code</code>
 *
 * Also handles:
 *   - Line breaks (respects \n)
 *   - URL auto-linking
 *   - Word-break safety for long strings
 */

import React from 'react'

/**
 * Parse WhatsApp-style markdown into React elements.
 * Returns an array of React nodes safe for rendering.
 */
export function formatWhatsAppMessage(text: string): React.ReactNode[] {
  if (!text) return []

  // Split by line breaks first
  const lines = text.split('\n')
  const result: React.ReactNode[] = []

  lines.forEach((line, lineIdx) => {
    if (lineIdx > 0) {
      result.push(<br key={`br-${lineIdx}`} />)
    }

    // Process inline formatting within each line
    const parts = parseInlineFormatting(line)
    parts.forEach((part, partIdx) => {
      result.push(
        <React.Fragment key={`${lineIdx}-${partIdx}`}>
          {part}
        </React.Fragment>
      )
    })
  })

  return result
}

/**
 * Parse inline WhatsApp formatting tokens.
 * Handles: *bold*, _italic_, ~strike~, `code`, ```code blocks```
 */
function parseInlineFormatting(text: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = []
  let remaining = text
  let keyIdx = 0

  // Process formatting tokens in order of appearance
  while (remaining.length > 0) {
    // Find the next formatting token
    let earliestIdx = remaining.length
    let tokenType: 'bold' | 'italic' | 'strike' | 'code_block' | 'code' | 'url' | null = null
    let matchInfo: { start: number; end: number; content: string } | null = null

    // Check for code blocks first (```)
    const codeBlockMatch = remaining.match(/```([\s\S]*?)```/)
    if (codeBlockMatch && codeBlockMatch.index !== undefined && codeBlockMatch.index < earliestIdx) {
      earliestIdx = codeBlockMatch.index
      tokenType = 'code_block'
      matchInfo = {
        start: codeBlockMatch.index,
        end: codeBlockMatch.index + codeBlockMatch[0].length,
        content: codeBlockMatch[1],
      }
    }

    // Check for inline code (`)
    const codeMatch = remaining.match(/`([^`]+)`/)
    if (codeMatch && codeMatch.index !== undefined && codeMatch.index < earliestIdx) {
      earliestIdx = codeMatch.index
      tokenType = 'code'
      matchInfo = {
        start: codeMatch.index,
        end: codeMatch.index + codeMatch[0].length,
        content: codeMatch[1],
      }
    }

    // Check for bold (*text*)
    const boldMatch = remaining.match(/\*([^*\n]+)\*/)
    if (boldMatch && boldMatch.index !== undefined && boldMatch.index < earliestIdx) {
      earliestIdx = boldMatch.index
      tokenType = 'bold'
      matchInfo = {
        start: boldMatch.index,
        end: boldMatch.index + boldMatch[0].length,
        content: boldMatch[1],
      }
    }

    // Check for italic (_text_)
    const italicMatch = remaining.match(/(?<!\w)_([^_\n]+)_(?!\w)/)
    if (italicMatch && italicMatch.index !== undefined && italicMatch.index < earliestIdx) {
      earliestIdx = italicMatch.index
      tokenType = 'italic'
      matchInfo = {
        start: italicMatch.index,
        end: italicMatch.index + italicMatch[0].length,
        content: italicMatch[1],
      }
    }

    // Check for strikethrough (~text~)
    const strikeMatch = remaining.match(/~([^~\n]+)~/)
    if (strikeMatch && strikeMatch.index !== undefined && strikeMatch.index < earliestIdx) {
      earliestIdx = strikeMatch.index
      tokenType = 'strike'
      matchInfo = {
        start: strikeMatch.index,
        end: strikeMatch.index + strikeMatch[0].length,
        content: strikeMatch[1],
      }
    }

    // Check for URLs
    const urlMatch = remaining.match(/(https?:\/\/[^\s<]+[^\s<.,;:'")\]}])/)
    if (urlMatch && urlMatch.index !== undefined && urlMatch.index < earliestIdx) {
      earliestIdx = urlMatch.index
      tokenType = 'url'
      matchInfo = {
        start: urlMatch.index,
        end: urlMatch.index + urlMatch[0].length,
        content: urlMatch[0],
      }
    }

    if (!tokenType || !matchInfo) {
      // No more tokens — add remaining text
      if (remaining) nodes.push(remaining)
      break
    }

    // Add text before the token
    if (matchInfo.start > 0) {
      nodes.push(remaining.slice(0, matchInfo.start))
    }

    // Add the formatted token
    switch (tokenType) {
      case 'bold':
        nodes.push(
          <strong key={`b-${keyIdx++}`} className="font-semibold">
            {matchInfo.content}
          </strong>
        )
        break
      case 'italic':
        nodes.push(
          <em key={`i-${keyIdx++}`}>
            {matchInfo.content}
          </em>
        )
        break
      case 'strike':
        nodes.push(
          <del key={`s-${keyIdx++}`} className="opacity-60">
            {matchInfo.content}
          </del>
        )
        break
      case 'code':
        nodes.push(
          <code key={`c-${keyIdx++}`} className="bg-slate-100 text-slate-700 px-1 py-0.5 rounded text-[12px] font-mono">
            {matchInfo.content}
          </code>
        )
        break
      case 'code_block':
        nodes.push(
          <code key={`cb-${keyIdx++}`} className="block bg-slate-100 text-slate-700 p-2 rounded text-[12px] font-mono mt-1 mb-1 whitespace-pre-wrap">
            {matchInfo.content}
          </code>
        )
        break
      case 'url':
        nodes.push(
          <a
            key={`u-${keyIdx++}`}
            href={matchInfo.content}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 underline hover:text-blue-500 break-all"
          >
            {matchInfo.content}
          </a>
        )
        break
    }

    // Continue with the remaining text
    remaining = remaining.slice(matchInfo.end)
  }

  return nodes
}

/**
 * CSS styles for message bubbles — ensures no text overflow.
 * Apply these as className to the message container.
 */
export const messageBubbleStyles = 'break-words overflow-wrap-anywhere whitespace-pre-wrap'
