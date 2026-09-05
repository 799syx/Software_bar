export type ScenicPhoto = {
  key: string;
  title: string;
  subject: string;
  url: string;
  sourceUrl?: string;
  pageUrl: string;
  author: string;
  license: string;
  licenseUrl: string;
  attribution: string;
};

type SpotImageInput = {
  name?: string;
  tags?: string[];
  image?: string;
  mapZone?: string | null;
};

type SemanticPhotoMatch = {
  key: string;
  fixed: boolean;
};

export const scenicPhotos: ScenicPhoto[] = [
  {
    key: "grand-buddha",
    title: "灵山大佛",
    subject: "灵山大佛",
    url: "/assets/scenic/photos/lingshan-grand-buddha.png",
    pageUrl: "/assets/scenic/photos/lingshan-grand-buddha.png",
    author: "项目提供素材",
    license: "项目内置演示素材",
    licenseUrl: "",
    attribution: "项目提供素材"
  },
  {
    key: "lingshan-screen-wall",
    title: "灵山大照壁",
    subject: "灵山大照壁",
    url: "/assets/scenic/photos/lingshan-screen-wall.jpg",
    pageUrl: "/assets/scenic/photos/lingshan-screen-wall.jpg",
    author: "项目提供素材",
    license: "项目内置演示素材",
    licenseUrl: "",
    attribution: "项目提供素材"
  },
  {
    key: "five-brightness-bridge",
    title: "五明桥",
    subject: "五明桥",
    url: "/assets/scenic/photos/five-brightness-bridge.png",
    pageUrl: "/assets/scenic/photos/five-brightness-bridge.png",
    author: "项目提供素材",
    license: "项目内置演示素材",
    licenseUrl: "",
    attribution: "项目提供素材"
  },
  {
    key: "buddha-foot-altar",
    title: "佛足坛",
    subject: "佛足坛",
    url: "/assets/scenic/photos/buddha-foot-altar.png",
    pageUrl: "/assets/scenic/photos/buddha-foot-altar.png",
    author: "项目提供素材",
    license: "项目内置演示素材",
    licenseUrl: "",
    attribution: "项目提供素材"
  },
  {
    key: "five-wisdom-gate",
    title: "五智门",
    subject: "五智门",
    url: "/assets/scenic/photos/five-wisdom-gate.jpg",
    pageUrl: "/assets/scenic/photos/five-wisdom-gate.jpg",
    author: "项目提供素材",
    license: "项目内置演示素材",
    licenseUrl: "",
    attribution: "项目提供素材"
  },
  {
    key: "bodhi-avenue",
    title: "菩提大道",
    subject: "菩提大道",
    url: "/assets/scenic/photos/bodhi-avenue.png",
    pageUrl: "/assets/scenic/photos/bodhi-avenue.png",
    author: "项目提供素材",
    license: "项目内置演示素材",
    licenseUrl: "",
    attribution: "项目提供素材"
  },
  {
    key: "demon-subduing-relief",
    title: "降魔浮雕",
    subject: "降魔浮雕",
    url: "/assets/scenic/photos/demon-subduing-relief.png",
    pageUrl: "/assets/scenic/photos/demon-subduing-relief.png",
    author: "项目提供素材",
    license: "项目内置演示素材",
    licenseUrl: "",
    attribution: "项目提供素材"
  },
  {
    key: "ashoka-pillar",
    title: "阿育王柱",
    subject: "阿育王柱",
    url: "/assets/scenic/photos/ashoka-pillar.png",
    pageUrl: "/assets/scenic/photos/ashoka-pillar.png",
    author: "项目提供素材",
    license: "项目内置演示素材",
    licenseUrl: "",
    attribution: "项目提供素材"
  },
  {
    key: "children-mitreya",
    title: "百子戏弥勒",
    subject: "百子戏弥勒",
    url: "/assets/scenic/photos/children-mitreya.png",
    pageUrl: "/assets/scenic/photos/children-mitreya.png",
    author: "项目提供素材",
    license: "项目内置演示素材",
    licenseUrl: "",
    attribution: "项目提供素材"
  },
  {
    key: "buddhist-culture-museum",
    title: "佛教文化博览馆",
    subject: "佛教文化博览馆",
    url: "/assets/scenic/photos/buddhist-culture-museum.jpg",
    pageUrl: "/assets/scenic/photos/buddhist-culture-museum.jpg",
    author: "项目提供素材",
    license: "项目内置演示素材",
    licenseUrl: "",
    attribution: "项目提供素材"
  },
  {
    key: "brahma-palace",
    title: "灵山梵宫",
    subject: "灵山梵宫",
    url: "/assets/scenic/photos/brahma-palace.jpg",
    sourceUrl: "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f5/%E7%81%B5%E5%B1%B1%E6%A2%B5%E5%AE%AB_-_panoramio.jpg/960px-%E7%81%B5%E5%B1%B1%E6%A2%B5%E5%AE%AB_-_panoramio.jpg",
    pageUrl: "https://commons.wikimedia.org/wiki/File:%E7%81%B5%E5%B1%B1%E6%A2%B5%E5%AE%AB_-_panoramio.jpg",
    author: "gdczjkk",
    license: "CC BY 3.0",
    licenseUrl: "https://creativecommons.org/licenses/by/3.0/deed.en",
    attribution: "gdczjkk, CC BY 3.0, via Wikimedia Commons"
  },
  {
    key: "five-seal-mandala",
    title: "五印坛城",
    subject: "五印坛城",
    url: "/assets/scenic/photos/five-seal-mandala.jpg",
    sourceUrl: "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/%E7%81%B5%E5%B1%B1%E4%BA%94%E5%8D%B0%E5%9D%9B%E5%9F%8E.jpg/960px-%E7%81%B5%E5%B1%B1%E4%BA%94%E5%8D%B0%E5%9D%9B%E5%9F%8E.jpg",
    pageUrl: "https://commons.wikimedia.org/wiki/File:%E7%81%B5%E5%B1%B1%E4%BA%94%E5%8D%B0%E5%9D%9B%E5%9F%8E.jpg",
    author: "西安兵马俑",
    license: "CC BY-SA 4.0",
    licenseUrl: "https://creativecommons.org/licenses/by-sa/4.0/deed.en",
    attribution: "西安兵马俑, CC BY-SA 4.0, via Wikimedia Commons"
  },
  {
    key: "xiangfu-temple",
    title: "祥符禅寺",
    subject: "祥符禅寺",
    url: "/assets/scenic/photos/xiangfu-temple.jpg",
    sourceUrl: "https://upload.wikimedia.org/wikipedia/commons/e/e4/Wuxi_Xiangfu_Temple.jpg",
    pageUrl: "https://commons.wikimedia.org/wiki/File:Wuxi_Xiangfu_Temple.jpg",
    author: "王波波",
    license: "CC BY-SA 3.0",
    licenseUrl: "https://creativecommons.org/licenses/by-sa/3.0/deed.en",
    attribution: "王波波, CC BY-SA 3.0, via Wikimedia Commons"
  },
  {
    key: "nine-dragons",
    title: "九龙灌浴",
    subject: "九龙灌浴",
    url: "/assets/scenic/photos/nine-dragons-bath.jpg",
    sourceUrl: "https://upload.wikimedia.org/wikipedia/commons/e/ea/Ling_shan_Buddha%27s_birth.jpg",
    pageUrl: "https://commons.wikimedia.org/wiki/File:Ling_shan_Buddha%27s_birth.jpg",
    author: "Synyan",
    license: "CC BY 3.0",
    licenseUrl: "https://creativecommons.org/licenses/by/3.0/deed.en",
    attribution: "Synyan, CC BY 3.0, via Wikimedia Commons"
  },
  {
    key: "nianhua-bay",
    title: "拈花湾",
    subject: "拈花湾",
    url: "/assets/scenic/photos/nianhua-bay.jpg",
    sourceUrl: "https://commons.wikimedia.org/wiki/Special:FilePath/%E7%81%B5%E5%B1%B1%E5%B0%8F%E9%95%87%E6%8B%88%E8%8A%B1%E6%B9%BE20200913_36.jpg?width=960",
    pageUrl: "https://commons.wikimedia.org/wiki/File:%E7%81%B5%E5%B1%B1%E5%B0%8F%E9%95%87%E6%8B%88%E8%8A%B1%E6%B9%BE20200913_36.jpg",
    author: "Nissangeniss",
    license: "CC BY-SA 4.0",
    licenseUrl: "https://creativecommons.org/licenses/by-sa/4.0/deed.en",
    attribution: "Nissangeniss, CC BY-SA 4.0, via Wikimedia Commons"
  },
  {
    key: "nianhua-plaza",
    title: "拈花广场",
    subject: "拈花广场",
    url: "/assets/scenic/photos/nianhua-plaza.png",
    pageUrl: "/assets/scenic/photos/nianhua-plaza.png",
    author: "项目提供素材",
    license: "项目内置演示素材",
    licenseUrl: "",
    attribution: "项目提供素材"
  },
  {
    key: "nianhua-hall",
    title: "拈花堂",
    subject: "拈花堂",
    url: "/assets/scenic/photos/nianhua-hall.png",
    pageUrl: "/assets/scenic/photos/nianhua-hall.png",
    author: "项目提供素材",
    license: "项目内置演示素材",
    licenseUrl: "",
    attribution: "项目提供素材"
  },
  {
    key: "nianhua-street",
    title: "香月花街",
    subject: "香月花街",
    url: "/assets/scenic/photos/nianhua-street.jpg",
    sourceUrl: "https://commons.wikimedia.org/wiki/Special:FilePath/%E7%81%B5%E5%B1%B1%E5%B0%8F%E9%95%87%E6%8B%88%E8%8A%B1%E6%B9%BE20200913_40.jpg?width=960",
    pageUrl: "https://commons.wikimedia.org/wiki/File:%E7%81%B5%E5%B1%B1%E5%B0%8F%E9%95%87%E6%8B%88%E8%8A%B1%E6%B9%BE20200913_40.jpg",
    author: "Nissangeniss",
    license: "CC BY-SA 4.0",
    licenseUrl: "https://creativecommons.org/licenses/by-sa/4.0/deed.en",
    attribution: "Nissangeniss, CC BY-SA 4.0, via Wikimedia Commons"
  },
  {
    key: "nianhua-flower-sea",
    title: "梵天花海",
    subject: "梵天花海",
    url: "/assets/scenic/photos/brahma-flower-sea.png",
    pageUrl: "/assets/scenic/photos/brahma-flower-sea.png",
    author: "项目现有演示素材",
    license: "项目内置演示素材",
    licenseUrl: "",
    attribution: "项目现有演示素材"
  },
  {
    key: "manfeilong-pagoda",
    title: "曼飞龙塔",
    subject: "曼飞龙塔",
    url: "/assets/scenic/photos/manfeilong-pagoda.png",
    pageUrl: "/assets/scenic/photos/manfeilong-pagoda.png",
    author: "项目提供素材",
    license: "项目内置演示素材",
    licenseUrl: "",
    attribution: "项目提供素材"
  },
  {
    key: "wujinyi-zhai",
    title: "无尽意斋",
    subject: "无尽意斋",
    url: "/assets/scenic/photos/wujinyi-zhai.png",
    pageUrl: "/assets/scenic/photos/wujinyi-zhai.png",
    author: "项目提供素材",
    license: "项目内置演示素材",
    licenseUrl: "",
    attribution: "项目提供素材"
  }
];

const photoKeywordMap: Array<[string[], string]> = [
  [["九龙", "灌浴", "太子佛", "诞生"], "nine-dragons"],
  [["香月", "花街", "餐饮", "购物"], "nianhua-street"],
  [["拈花堂"], "nianhua-hall"],
  [["梵天", "花海", "花田"], "nianhua-flower-sea"],
  [["拈花广场", "广场"], "nianhua-plaza"],
  [["拈花", "拈花湾", "拈花堂", "小镇"], "nianhua-bay"],
  [["五明桥", "五明", "智慧桥"], "five-brightness-bridge"],
  [["佛足坛", "佛足"], "buddha-foot-altar"],
  [["五智门", "五智"], "five-wisdom-gate"],
  [["菩提大道", "菩提"], "bodhi-avenue"],
  [["降魔浮雕", "降魔"], "demon-subduing-relief"],
  [["阿育王柱", "阿育王"], "ashoka-pillar"],
  [["百子戏弥勒", "百子弥勒戏", "弥勒"], "children-mitreya"],
  [["佛教文化博览馆", "佛教文化博物馆", "博览馆", "博物馆", "万佛"], "buddhist-culture-museum"],
  [["梵宫", "吉祥颂"], "brahma-palace"],
  [["坛城", "五印", "藏传"], "five-seal-mandala"],
  [["祥符", "禅寺", "古刹"], "xiangfu-temple"],
  [["大佛", "抱佛脚"], "grand-buddha"],
  [["照壁", "山门", "入口"], "lingshan-screen-wall"],
  [["曼飞龙", "白塔", "南传"], "manfeilong-pagoda"],
  [["无尽意斋", "无尽意"], "wujinyi-zhai"]
];

export const fixedSpotPhotoMap: Record<string, string> = {
  灵山大佛: "grand-buddha",
  大佛: "grand-buddha",
  灵山大照壁: "lingshan-screen-wall",
  大照壁: "lingshan-screen-wall",
  五明桥: "five-brightness-bridge",
  佛足坛: "buddha-foot-altar",
  五智门: "five-wisdom-gate",
  菩提大道: "bodhi-avenue",
  降魔浮雕: "demon-subduing-relief",
  阿育王柱: "ashoka-pillar",
  百子戏弥勒: "children-mitreya",
  百子弥勒戏: "children-mitreya",
  佛教文化博览馆: "buddhist-culture-museum",
  佛教文化博物馆: "buddhist-culture-museum",
  灵山梵宫: "brahma-palace",
  梵宫: "brahma-palace",
  五印坛城: "five-seal-mandala",
  坛城: "five-seal-mandala",
  祥符禅寺: "xiangfu-temple",
  祥符寺: "xiangfu-temple",
  九龙灌浴: "nine-dragons",
  九龙: "nine-dragons",
  拈花湾: "nianhua-bay",
  拈花广场: "nianhua-plaza",
  拈花堂: "nianhua-hall",
  香月花街: "nianhua-street",
  梵天花海: "nianhua-flower-sea",
  曼飞龙塔: "manfeilong-pagoda",
  无尽意斋: "wujinyi-zhai"
};

const legacyImageMap: Record<string, string> = {
  "assets/spot-gate.svg": "xiangfu-temple",
  "/assets/spot-gate.svg": "xiangfu-temple",
  "assets/spot-view.svg": "grand-buddha",
  "/assets/spot-view.svg": "grand-buddha",
  "assets/spot-museum.svg": "brahma-palace",
  "/assets/spot-museum.svg": "brahma-palace",
  "assets/spot-lake.svg": "nine-dragons",
  "/assets/spot-lake.svg": "nine-dragons",
  "assets/spot-path.svg": "nianhua-street",
  "/assets/spot-path.svg": "nianhua-street",
  "assets/spot-workshop.svg": "five-seal-mandala",
  "/assets/spot-workshop.svg": "five-seal-mandala"
};

const photoUrlKeyMap = new Map(scenicPhotos.map((photo) => [photo.url, photo.key]));
const photoAssetPathKeyMap = new Map(
  scenicPhotos.map((photo) => [photo.url.replace(/^\/+/, ""), photo.key])
);
const photoTitleKeyMap = new Map(scenicPhotos.flatMap((photo) => [[photo.key, photo.key], [photo.title, photo.key], [photo.subject, photo.key]]));

export function photoByKey(key: string) {
  return scenicPhotos.find((photo) => photo.key === key) || scenicPhotos[0];
}

function configuredPhotoKey(image?: string) {
  const value = (image || "").trim();
  if (!value) return "";
  if (legacyImageMap[value]) return legacyImageMap[value];
  if (photoTitleKeyMap.has(value)) return photoTitleKeyMap.get(value) || "";
  const normalizedPath = value.startsWith("/") ? value : `/${value.replace(/^\/+/, "")}`;
  return photoUrlKeyMap.get(normalizedPath) || photoAssetPathKeyMap.get(normalizedPath.replace(/^\/+/, "")) || "";
}

function isLegacyPlaceholderImage(image?: string) {
  return Boolean(legacyImageMap[(image || "").trim()]);
}

function fallbackPhotoForZone(mapZone?: string | null) {
  if (mapZone === "nianhua") return photoByKey("nianhua-bay");
  return photoByKey("grand-buddha");
}

const photoTagMap: Array<[string[], string]> = [
  [["演艺体验", "亲子游"], "nine-dragons"],
  [["餐饮购物", "小镇", "休闲"], "nianhua-street"],
  [["自然风光", "花海", "轻松休闲"], "nianhua-flower-sea"],
  [["室内参观"], "brahma-palace"],
  [["历史文化", "禅寺"], "xiangfu-temple"],
  [["坛城", "藏传"], "five-seal-mandala"],
  [["佛教文化"], "brahma-palace"],
  [["拍照打卡"], "five-seal-mandala"]
];

function normalizeSpotText(value?: string) {
  return (value || "").replace(/\s+/g, "").replace(/（.*?）/g, "").replace(/\(.*?\)/g, "").toLowerCase();
}

function semanticPhotoKeyForSpot(name?: string, tags: string[] = [], mapZone?: string | null): SemanticPhotoMatch | null {
  const normalized = normalizeSpotText(name);
  const fixedEntry = Object.entries(fixedSpotPhotoMap).find(([keyword]) => normalized.includes(normalizeSpotText(keyword)));
  if (fixedEntry) return { key: fixedEntry[1], fixed: true };

  const keywordMatched = photoKeywordMap.find(([keywords]) => keywords.some((keyword) => normalized.includes(keyword.toLowerCase())));
  if (keywordMatched) return { key: keywordMatched[1], fixed: false };

  const tagText = tags.join(" ").toLowerCase();
  const tagMatched = photoTagMap.find(([keywords]) => keywords.some((keyword) => tagText.includes(keyword.toLowerCase())));
  if (tagMatched) return { key: tagMatched[1], fixed: false };

  const subjectMatch = scenicPhotos.find((photo) => normalized.includes(photo.subject.toLowerCase()));
  if (subjectMatch) return { key: subjectMatch.key, fixed: false };

  if (mapZone) return { key: fallbackPhotoForZone(mapZone).key, fixed: false };
  return null;
}

export function photoForSpot(name?: string, tags: string[] = [], mapZone?: string | null) {
  if (!name && !tags.length) return fallbackPhotoForZone(mapZone);
  const semanticMatch = semanticPhotoKeyForSpot(name, tags, mapZone);
  if (semanticMatch) return photoByKey(semanticMatch.key);
  return fallbackPhotoForZone(mapZone);
}

function configuredPhotoIsExplicit(image?: string) {
  const value = (image || "").trim();
  return Boolean(value && configuredPhotoKey(value) && !isLegacyPlaceholderImage(value));
}

export function photoKeyForImage(image?: string) {
  return configuredPhotoKey(image);
}

export function photoOptions() {
  return scenicPhotos.map((photo) => ({
    key: photo.key,
    title: photo.title,
    url: photo.url
  }));
}

export function imageForSpot(spot?: SpotImageInput | null, usedKeys?: Set<string>) {
  const semanticMatch = semanticPhotoKeyForSpot(spot?.name, spot?.tags || [], spot?.mapZone);
  const semanticPhoto = semanticMatch ? photoByKey(semanticMatch.key) : fallbackPhotoForZone(spot?.mapZone);
  const configuredKey = configuredPhotoKey(spot?.image);
  const configuredPhoto = configuredKey ? photoByKey(configuredKey) : null;
  const preferred =
    semanticMatch?.fixed || !configuredPhotoIsExplicit(spot?.image)
      ? semanticPhoto
      : configuredPhoto || semanticPhoto;
  if (!usedKeys || !usedKeys.has(preferred.key) || semanticMatch?.fixed) {
    usedKeys?.add(preferred.key);
    return preferred.url;
  }

  const tagText = (spot?.tags || []).join(" ");
  const candidates = scenicPhotos.filter((photo) => {
    if (usedKeys.has(photo.key)) return false;
    if (spot?.mapZone === "nianhua") return photo.key.startsWith("nianhua");
    if (tagText.includes("演艺") || tagText.includes("亲子")) return photo.key === "nine-dragons";
    if (tagText.includes("室内")) return photo.key === "brahma-palace";
    if (tagText.includes("历史") || tagText.includes("禅寺")) return photo.key === "xiangfu-temple";
    return !photo.key.startsWith("nianhua");
  });
  const fallback = candidates[0] || scenicPhotos.find((photo) => !usedKeys.has(photo.key)) || preferred;
  usedKeys.add(fallback.key);
  return fallback.url;
}

export function spotImageCards<T extends SpotImageInput>(spots: T[]) {
  return spots.map((spot) => ({ spot, image: imageForSpot(spot) }));
}
