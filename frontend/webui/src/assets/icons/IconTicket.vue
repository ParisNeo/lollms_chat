<script setup>
defineProps({
  class: {
    type: String,
    default: 'w-6 h-6'
  }
});
</script>
<template>
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    :class="class" 
    viewBox="0 0 20 20" 
    fill="currentColor"
  >
    <path d="M12.25 10a.75.75 0 0 0-.75-.75H3.143a.75.75 0 0 1 0-1.5h8.357a.75.75 0 0 0 0-1.5H3.143a.75.75 0 0 1 0-1.5h8.357a.75.75 0 0 0 0-1.5H3.143a.75.75 0 0 1 0-1.5h8.357a.75.75 0 0 0 .75-.75V1.25a.75.75 0 0 0-1.5 0v.513a4.49 4.49 0 0 0-3.337 2.237 1.99 1.99 0 0 0-1.732 0 4.49 4.49 0 0 0-3.337-2.237V1.25a.75.75 0 0 0-1.5 0v.513A4.5 4.5 0 0 0 4.3 4.987a1.99 1.99 0 0 0 0 1.732 4.5 4.5 0 0 0-2.513 2.725V10l-1.06.002a.75.75 0 0 0 0 1.5l1.06.002v.268a4.5 4.5 0 0 0 2.513 2.725 1.99 1.99 0 0 0 0 1.732 4.5 4.5 0 0 0-2.513 2.725v.513a.75.75 0 0 0 1.5 0v-.513a4.49 4.49 0 0 0 3.337-2.237 1.99 1.99 0 0 0 1.732 0 4.49 4.49 0 0 0 3.337 2.237v.513a.75.75 0 0 0 1.5 0v-.513a4.5 4.5 0 0 0 2.513-2.725 1.99 1.99 0 0 0 0-1.732 4.5 4.5 0 0 0 2.513-2.725V11.5l1.06-.002a.75.75 0 0 0 0-1.5l-1.06-.002V10Z" />
  </svg>
</template>