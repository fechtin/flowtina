<script setup lang="ts" generic="T">
interface Column {
  key: string
  label: string
  class?: string
}
defineProps<{ columns: Column[]; rows: T[] }>()
</script>

<template>
  <div class="card overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full text-left text-sm">
        <thead class="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500 dark:border-gray-800 dark:bg-gray-800/50 dark:text-gray-400">
          <tr>
            <th v-for="col in columns" :key="col.key" class="px-4 py-3 font-medium" :class="col.class">
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-800">
          <tr
            v-for="(row, idx) in rows"
            :key="idx"
            class="hover:bg-gray-50 dark:hover:bg-gray-800/40"
          >
            <td v-for="col in columns" :key="col.key" class="px-4 py-3 align-middle" :class="col.class">
              <slot :name="`cell-${col.key}`" :row="row">
                {{ (row as Record<string, unknown>)[col.key] }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
