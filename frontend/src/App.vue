<template>
  <div class="page">
    <div class="container">
      <header class="header">
        <h1 class="title">Emoji Video Maker</h1>
        <p class="subtitle">
          Загрузите короткое видео в формате MP4, и сервис вернёт ролик со смайликом по центру.
        </p>
      </header>

      <form class="form" @submit.prevent="handleSubmit">
        <label class="file-input">
          <span class="file-label">Видео (.mp4, до 50 МБ)</span>
          <input
            type="file"
            accept="video/mp4"
            :disabled="isUploading"
            @change="handleFileChange"
          />
        </label>

        <button class="submit-button" type="submit" :disabled="isUploading">
          <span v-if="isUploading">Обрабатываем…</span>
          <span v-else>Добавить 😊</span>
        </button>
      </form>

      <p v-if="status" class="status">
        {{ status }}
      </p>

      <section v-if="processedUrl" class="result">
        <video class="result-video" :src="processedUrl" controls preload="metadata" />
        <a class="download-link" :href="processedUrl" download="emoji-video.mp4">
          Скачать результат
        </a>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from "vue";

const apiBaseUrl: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";

const selectedFile = ref<File | null>(null);
const status = ref<string>("");
const isUploading = ref<boolean>(false);
const processedUrl = ref<string | null>(null);

const setProcessedUrl = (url: string | null): void => {
  if (processedUrl.value !== null) {
    URL.revokeObjectURL(processedUrl.value);
  }
  processedUrl.value = url;
};

const handleFileChange = (event: Event): void => {
  const target = event.target as HTMLInputElement | null;
  if (target === null) {
    return;
  }
  const file = target.files !== null ? target.files[0] : null;
  selectedFile.value = file;
  status.value = "";
  setProcessedUrl(null);
};

const handleSubmit = async (): Promise<void> => {
  if (selectedFile.value === null) {
    status.value = "Выберите mp4 файл до 50 МБ.";
    return;
  }

  const formData = new FormData();
  formData.append("file", selectedFile.value);

  isUploading.value = true;
  status.value = "Обрабатываем видео…";

  try {
    const response = await fetch(`${apiBaseUrl}/add-emoji`, {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      let message: string | undefined;
      try {
        const data = (await response.json()) as { detail?: string };
        message = data.detail;
      } catch {
        message = undefined;
      }
      throw new Error(message ?? "Не удалось обработать видео");
    }

    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    setProcessedUrl(objectUrl);
    status.value = "Готово! Вы можете посмотреть или скачать результат.";
  } catch (error) {
    if (error instanceof Error) {
      status.value = error.message;
    } else {
      status.value = "Произошла неизвестная ошибка. Попробуйте позже.";
    }
  } finally {
    isUploading.value = false;
  }
};

onUnmounted(() => {
  if (processedUrl.value !== null) {
    URL.revokeObjectURL(processedUrl.value);
  }
});
</script>
