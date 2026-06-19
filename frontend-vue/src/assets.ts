export const digitalHumanAvatar = "/assets/lingling-avatar-v2.png";
export const digitalHumanAvatarFallback = "/assets/lingling-avatar.png";
export const scenicImageFallback = "/assets/scenic/fallback-scenic.svg";

export function useFallbackImage(event: Event, fallback = scenicImageFallback) {
  const image = event.target;
  if (!(image instanceof HTMLImageElement)) return;
  if (image.dataset.fallbackApplied === "true") return;
  image.dataset.fallbackApplied = "true";
  image.src = fallback;
}
