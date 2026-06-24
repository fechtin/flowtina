<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ImageOff } from 'lucide-vue-next'
import { postService } from '@/services'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'

/**
 * Renders a post's image the way it will appear once published: a public
 * `image_url` is shown directly, while an uploaded binary is fetched through
 * the auth-protected endpoint (an <img> tag cannot carry the Bearer token) and
 * shown via an object URL that is revoked when no longer needed.
 */
const props = withDefaults(
  defineProps<{
    postId: string
    imageUrl?: string | null
    hasUploadedImage?: boolean
    imgClass?: string
    /** Drop the default rounded border so the image can sit flush (e.g. a Facebook card). */
    bare?: boolean
  }>(),
  { imageUrl: null, hasUploadedImage: false, imgClass: '', bare: false },
)

const objectUrl = ref<string | null>(null)
const loading = ref(false)
const failed = ref(false)

const src = computed(() => props.imageUrl || objectUrl.value)
const hasImage = computed(() => Boolean(props.imageUrl) || props.hasUploadedImage)

function revoke(): void {
  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value)
    objectUrl.value = null
  }
}

async function loadUploaded(): Promise<void> {
  revoke()
  failed.value = false
  if (props.imageUrl || !props.hasUploadedImage) return
  loading.value = true
  try {
    const blob = await postService.fetchImage(props.postId)
    objectUrl.value = URL.createObjectURL(blob)
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.postId, props.imageUrl, props.hasUploadedImage],
  () => loadUploaded(),
  { immediate: true },
)

onBeforeUnmount(revoke)
</script>

<template>
  <div v-if="hasImage">
    <div
      v-if="loading"
      class="flex items-center justify-center rounded-lg border border-gray-200 bg-gray-50 py-6 dark:border-gray-700 dark:bg-gray-800/50"
      :class="imgClass"
    >
      <LoadingSpinner />
    </div>
    <div
      v-else-if="failed || !src"
      class="flex items-center justify-center gap-2 rounded-lg border border-gray-200 bg-gray-50 py-6 text-sm text-gray-400 dark:border-gray-700 dark:bg-gray-800/50"
      :class="imgClass"
    >
      <ImageOff class="h-4 w-4" />
    </div>
    <img
      v-else
      :src="src"
      alt=""
      :class="[bare ? '' : 'rounded-lg border border-gray-200 dark:border-gray-700', imgClass]"
      @error="failed = true"
    />
  </div>
</template>
