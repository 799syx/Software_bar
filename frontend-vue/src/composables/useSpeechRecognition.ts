import { computed, onBeforeUnmount, ref } from "vue";

type SpeechOptions = {
  onTranscript: (text: string, final: boolean) => void;
};

function friendlySpeechError(code: string) {
  if (code === "not-allowed" || code === "service-not-allowed") return "浏览器没有麦克风权限，请允许后再试。";
  if (code === "no-speech") return "没有识别到语音，可以再说一遍或直接输入文字。";
  if (code === "audio-capture") return "没有检测到可用麦克风。";
  if (code === "network") return "语音识别服务暂时不可用，请改用文字输入。";
  if (code === "aborted") return "浏览器语音识别已中断，请改用文字输入或重新点击麦克风。";
  return "语音识别中断，请改用文字输入或重新点击麦克风。";
}

export function useSpeechRecognition(options: SpeechOptions) {
  const recognitionRef = ref<BrowserSpeechRecognition | null>(null);
  const listening = ref(false);
  const error = ref("");
  const supported = computed(() => typeof window !== "undefined" && Boolean(window.SpeechRecognition || window.webkitSpeechRecognition));

  function ensureRecognition() {
    if (!supported.value) return null;
    if (recognitionRef.value) return recognitionRef.value;

    const Constructor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Constructor) return null;

    const recognition = new Constructor();
    recognition.lang = "zh-CN";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => {
      listening.value = true;
      error.value = "";
    };
    recognition.onresult = (event) => {
      let transcript = "";
      let final = false;
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        transcript += result[0]?.transcript || "";
        final = final || result.isFinal;
      }
      options.onTranscript(transcript.trim(), final);
    };
    recognition.onerror = (event) => {
      listening.value = false;
      error.value = friendlySpeechError(event.error);
    };
    recognition.onend = () => {
      listening.value = false;
    };
    recognitionRef.value = recognition;
    return recognition;
  }

  function start() {
    const recognition = ensureRecognition();
    if (!recognition) {
      error.value = "当前浏览器不支持语音转文字，请使用 Chrome 或 Edge。";
      return;
    }
    if (listening.value) return;
    error.value = "";
    try {
      recognition.start();
    } catch {
      listening.value = false;
      error.value = "语音识别启动失败，请直接输入文字。";
    }
  }

  function stop() {
    if (!recognitionRef.value || !listening.value) return;
    recognitionRef.value.stop();
    listening.value = false;
  }

  onBeforeUnmount(() => {
    recognitionRef.value?.abort();
  });

  return {
    supported,
    listening,
    error,
    start,
    stop
  };
}
