<script setup lang="ts">
import { ExternalLink } from "lucide-vue-next";
import { scenicPhotos } from "../photos";
</script>

<template>
  <section class="attribution-strip" aria-label="图片来源">
    <div>
      <p class="section-kicker">图片来源</p>
      <h2>实景照片保留来源、作者与授权信息</h2>
    </div>
    <ul>
      <li v-for="photo in scenicPhotos" :key="photo.key">
        <a :href="photo.pageUrl" target="_blank" rel="noreferrer">
          <span>{{ photo.title }}</span>
          <small>{{ photo.license }}</small>
          <ExternalLink :size="14" />
        </a>
      </li>
    </ul>
  </section>
</template>
