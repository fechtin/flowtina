/**
 * Flatten Markdown to plain text for the Facebook preview.
 *
 * Mirrors the backend `strip_markdown` (app/utils/text.py) so the preview shows
 * exactly what gets published — Facebook renders no Markdown. Apply to post
 * *content* only; never to a hashtags string, whose leading `#`s are literal.
 */
const CODE_FENCE_RE = /^[ \t]*```[^\n]*$/gm
const INLINE_CODE_RE = /`([^`\n]+)`/g
const HR_RE = /^[ \t]{0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$/gm
const HEADING_RE = /^[ \t]{0,3}#{1,6}[ \t]+/gm
const BLOCKQUOTE_RE = /^[ \t]{0,3}>[ \t]?/gm
const LINK_RE = /\[([^\]]*)\]\(([^)\s]+)\)/g
const ASTERISK_EMPHASIS_RE = /(\*{1,3})(\S(?:[\s\S]*?\S)?)\1/g
const UNDERSCORE_BOLD_RE = /__(\S(?:[\s\S]*?\S)?)__/g
const MULTISPACE_RE = /[ \t]{2,}/g
const MULTINEWLINE_RE = /\n{3,}/g

function linkReplacement(_match: string, label: string, url: string): string {
  const text = label.trim()
  const href = url.trim()
  return !text || text === href ? href : `${text} (${href})`
}

export function stripMarkdown(input: string | null | undefined): string {
  if (!input) return ''
  let text = input.replace(/\r\n/g, '\n')
  text = text.replace(CODE_FENCE_RE, '')
  text = text.replace(HR_RE, '')
  text = text.replace(HEADING_RE, '')
  text = text.replace(BLOCKQUOTE_RE, '')
  text = text.replace(LINK_RE, linkReplacement)
  text = text.replace(INLINE_CODE_RE, '$1')
  // Asterisk emphasis is non-greedy; on the rare chance of nesting, run twice.
  text = text.replace(ASTERISK_EMPHASIS_RE, '$2')
  text = text.replace(UNDERSCORE_BOLD_RE, '$1')
  text = text.replace(MULTISPACE_RE, ' ')
  text = text.replace(MULTINEWLINE_RE, '\n\n')
  return text.trim()
}
