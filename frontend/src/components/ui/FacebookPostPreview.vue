<script setup lang="ts">
import { computed, ref } from 'vue'
import { Globe, MessageCircle, MoreHorizontal, Share2, ThumbsUp } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import PostImage from '@/components/ui/PostImage.vue'

/**
 * Renders a post the way it will actually appear once published to Facebook.
 *
 * Fidelity notes (must match backend FacebookService._compose_message and how
 * the Graph API renders a feed/photo story):
 *  - The published caption is `content` + a blank line + `hashtags`; they are a
 *    single text block, not separate fields.
 *  - Facebook does NOT render Markdown, so `**bold**` / `*italic*` show their
 *    literal asterisks — we display the raw text verbatim, only colouring
 *    #hashtags like Facebook does.
 *  - Long captions fold behind a "See more" toggle.
 */
const props = withDefaults(
  defineProps<{
    postId: string
    content: string
    hashtags?: string | null
    imageUrl?: string | null
    hasUploadedImage?: boolean
    pageName?: string
  }>(),
  { hashtags: null, imageUrl: null, hasUploadedImage: false, pageName: '' },
)

const { t } = useI18n()

const FOLD_AT = 280 // Facebook folds long captions; approximate its "See more" point.
const expanded = ref(false)

const pageLabel = computed(() => props.pageName?.trim() || t('posts.fbYourPage'))
const initials = computed(() =>
  pageLabel.value
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w.charAt(0).toUpperCase())
    .join(''),
)

// Mirror backend _compose_message: content, blank line, then hashtags.
const message = computed(() => {
  const parts = [props.content?.trim() ?? '']
  if (props.hashtags?.trim()) parts.push(props.hashtags.trim())
  return parts.filter(Boolean).join('\n\n')
})

const isLong = computed(() => message.value.length > FOLD_AT)
const shownText = computed(() =>
  isLong.value && !expanded.value ? message.value.slice(0, FOLD_AT).trimEnd() : message.value,
)

// Split into plain/hashtag segments so #tags can be coloured without v-html.
type Seg = { text: string; tag: boolean }
const segments = computed<Seg[]>(() => {
  const out: Seg[] = []
  const re = /#[\p{L}\p{N}_]+/gu
  let last = 0
  let m: RegExpExecArray | null
  const text = shownText.value
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push({ text: text.slice(last, m.index), tag: false })
    out.push({ text: m[0], tag: true })
    last = m.index + m[0].length
  }
  if (last < text.length) out.push({ text: text.slice(last), tag: false })
  return out
})
</script>

<template>
  <div
    class="mx-auto w-full max-w-md overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-900"
  >
    <!-- Header -->
    <div class="flex items-center gap-2 px-3 pt-3">
      <div
        class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-sm font-semibold text-white"
      >
        {{ initials }}
      </div>
      <div class="min-w-0 flex-1 leading-tight">
        <p class="truncate text-sm font-semibold text-gray-900 dark:text-gray-100">{{ pageLabel }}</p>
        <p class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
          {{ t('posts.fbJustNow') }} · <Globe class="h-3 w-3" />
        </p>
      </div>
      <MoreHorizontal class="h-5 w-5 text-gray-400" />
    </div>

    <!-- Caption -->
    <div v-if="message" class="px-3 py-2">
      <p class="whitespace-pre-wrap break-words text-[15px] leading-snug text-gray-900 dark:text-gray-100">
        <template v-for="(seg, i) in segments" :key="i">
          <span v-if="seg.tag" class="text-[#1877F2]">{{ seg.text }}</span>
          <template v-else>{{ seg.text }}</template>
        </template><template v-if="isLong && !expanded">…&#8203;</template>
        <button
          v-if="isLong && !expanded"
          type="button"
          class="ml-1 font-medium text-gray-500 hover:underline dark:text-gray-400"
          @click="expanded = true"
        >
          {{ t('posts.fbSeeMore') }}
        </button>
      </p>
    </div>

    <!-- Image (flush, full-bleed like a Facebook photo story) -->
    <PostImage
      :post-id="postId"
      :image-url="imageUrl"
      :has-uploaded-image="hasUploadedImage"
      bare
      img-class="w-full max-h-[480px] object-cover"
    />

    <!-- Action bar -->
    <div class="mt-1 flex items-center justify-around border-t border-gray-100 px-2 py-1.5 dark:border-gray-800">
      <span class="flex items-center gap-2 px-3 py-1 text-sm font-medium text-gray-500 dark:text-gray-400">
        <ThumbsUp class="h-4 w-4" /> {{ t('posts.fbLike') }}
      </span>
      <span class="flex items-center gap-2 px-3 py-1 text-sm font-medium text-gray-500 dark:text-gray-400">
        <MessageCircle class="h-4 w-4" /> {{ t('posts.fbComment') }}
      </span>
      <span class="flex items-center gap-2 px-3 py-1 text-sm font-medium text-gray-500 dark:text-gray-400">
        <Share2 class="h-4 w-4" /> {{ t('posts.fbShare') }}
      </span>
    </div>
  </div>
</template>
