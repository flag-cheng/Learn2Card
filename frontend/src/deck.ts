export interface DeckMetaV1 {
  source: string;
  generatedAt: string;
  schemaVersion: "1.0.0" | string;
}

export interface ParagraphV1 {
  id: string;
  idx: number;
  text: string;
  headingLevel?: number;
  sectionPath?: string[];
}

export interface KeypointV1 {
  paragraphId: string;
  sentence: string;
  keywords: string[];
}

export interface TopicV1 {
  id: string;
  title: string;
  memberIds: string[];
  summaryBullets?: string[];
}

export interface CardV1 {
  id: string;
  topicId: string;
  title: string;
  bullets: string[];
}

export interface DeckStatsV1 {
  totalParagraphs: number;
  totalKeypoints: number;
  totalTopics: number;
  totalCards: number;
}

export interface DeckV1 {
  meta: DeckMetaV1;
  paragraphs: ParagraphV1[];
  keypoints: KeypointV1[];
  topics: TopicV1[];
  cards: CardV1[];
  stats: DeckStatsV1;
}

export interface DeckStatsUI {
  totalParagraphs: number;
  totalKeypoints: number;
  totalTopics: number;
  totalCards: number;
}

export interface DeckUI {
  meta?: Partial<DeckMetaV1>;
  topics: TopicV1[];
  cards: CardV1[];
  stats: DeckStatsUI;
}

export class DeckFormatError extends Error {
  readonly details: string[];

  constructor(message: string, details: string[] = []) {
    super(message);
    this.name = "DeckFormatError";
    this.details = details;
  }
}

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asString(value: unknown, field: string, details: string[]): string {
  if (typeof value === "string") return value;
  details.push(`欄位 \`${field}\` 必須是字串`);
  return "";
}

function asNumber(value: unknown, field: string, details: string[]): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  details.push(`欄位 \`${field}\` 必須是數字`);
  return 0;
}

function asStringArray(
  value: unknown,
  field: string,
  details: string[],
): string[] {
  if (Array.isArray(value) && value.every((item) => typeof item === "string")) {
    return value;
  }
  details.push(`欄位 \`${field}\` 必須是字串陣列`);
  return [];
}

function clampBullets(bullets: string[], details: string[], context: string) {
  if (bullets.length >= 1 && bullets.length <= 5) return bullets;
  details.push(`${context} 的 bullets 長度必須是 1–5，目前為 ${bullets.length}`);
  return bullets.slice(0, 5);
}

function parseDeckV1(raw: unknown): { deck: DeckV1; warnings: string[] } {
  const details: string[] = [];
  const warnings: string[] = [];

  if (!isRecord(raw)) {
    throw new DeckFormatError("JSON 根節點必須是物件", ["根節點不是物件"]);
  }

  const metaRaw = raw.meta;
  if (!isRecord(metaRaw)) {
    details.push("缺少 `meta` 或 `meta` 不是物件");
  }

  const paragraphsRaw = raw.paragraphs;
  const keypointsRaw = raw.keypoints;
  const topicsRaw = raw.topics;
  const cardsRaw = raw.cards;
  const statsRaw = raw.stats;

  if (!Array.isArray(paragraphsRaw)) details.push("缺少 `paragraphs` 或 `paragraphs` 不是陣列");
  if (!Array.isArray(keypointsRaw)) details.push("缺少 `keypoints` 或 `keypoints` 不是陣列");
  if (!Array.isArray(topicsRaw)) details.push("缺少 `topics` 或 `topics` 不是陣列");
  if (!Array.isArray(cardsRaw)) details.push("缺少 `cards` 或 `cards` 不是陣列");
  if (!isRecord(statsRaw)) details.push("缺少 `stats` 或 `stats` 不是物件");

  if (details.length) {
    throw new DeckFormatError("deck.json 格式不符合預期（v1.0.0）", details);
  }

  const metaObj = metaRaw as UnknownRecord;
  const statsObj = statsRaw as UnknownRecord;

  const meta: DeckMetaV1 = {
    source: asString(metaObj.source, "meta.source", details),
    generatedAt: asString(metaObj.generatedAt, "meta.generatedAt", details),
    schemaVersion: asString(metaObj.schemaVersion, "meta.schemaVersion", details),
  };

  const paragraphs: ParagraphV1[] = (paragraphsRaw as unknown[]).map((item, idx) => {
    if (!isRecord(item)) {
      details.push(`paragraphs[${idx}] 必須是物件`);
      return { id: "", idx, text: "" };
    }
    const p: ParagraphV1 = {
      id: asString(item.id, `paragraphs[${idx}].id`, details),
      idx: asNumber(item.idx, `paragraphs[${idx}].idx`, details),
      text: asString(item.text, `paragraphs[${idx}].text`, details),
    };
    if (item.headingLevel !== undefined) {
      if (typeof item.headingLevel === "number") p.headingLevel = item.headingLevel;
      else details.push(`paragraphs[${idx}].headingLevel 必須是數字（可選）`);
    }
    if (item.sectionPath !== undefined) {
      p.sectionPath = asStringArray(item.sectionPath, `paragraphs[${idx}].sectionPath`, details);
    }
    return p;
  });

  const keypoints: KeypointV1[] = (keypointsRaw as unknown[]).map((item, idx) => {
    if (!isRecord(item)) {
      details.push(`keypoints[${idx}] 必須是物件`);
      return { paragraphId: "", sentence: "", keywords: [] };
    }
    return {
      paragraphId: asString(item.paragraphId, `keypoints[${idx}].paragraphId`, details),
      sentence: asString(item.sentence, `keypoints[${idx}].sentence`, details),
      keywords: asStringArray(item.keywords, `keypoints[${idx}].keywords`, details),
    };
  });

  const topics: TopicV1[] = (topicsRaw as unknown[]).map((item, idx) => {
    if (!isRecord(item)) {
      details.push(`topics[${idx}] 必須是物件`);
      return { id: "", title: "", memberIds: [] };
    }
    const topic: TopicV1 = {
      id: asString(item.id, `topics[${idx}].id`, details),
      title: asString(item.title, `topics[${idx}].title`, details),
      memberIds: asStringArray(item.memberIds, `topics[${idx}].memberIds`, details),
    };
    if (item.summaryBullets !== undefined) {
      topic.summaryBullets = asStringArray(
        item.summaryBullets,
        `topics[${idx}].summaryBullets`,
        details,
      );
    }
    return topic;
  });

  const cards: CardV1[] = (cardsRaw as unknown[]).map((item, idx) => {
    if (!isRecord(item)) {
      details.push(`cards[${idx}] 必須是物件`);
      return { id: "", topicId: "", title: "", bullets: [] };
    }
    const bullets = asStringArray(item.bullets, `cards[${idx}].bullets`, details);
    return {
      id: asString(item.id, `cards[${idx}].id`, details),
      topicId: asString(item.topicId, `cards[${idx}].topicId`, details),
      title: asString(item.title, `cards[${idx}].title`, details),
      bullets: clampBullets(bullets, details, `cards[${idx}]`),
    };
  });

  const stats: DeckStatsV1 = {
    totalParagraphs: asNumber(statsObj.totalParagraphs, "stats.totalParagraphs", details),
    totalKeypoints: asNumber(statsObj.totalKeypoints, "stats.totalKeypoints", details),
    totalTopics: asNumber(statsObj.totalTopics, "stats.totalTopics", details),
    totalCards: asNumber(statsObj.totalCards, "stats.totalCards", details),
  };

  if (details.length) {
    throw new DeckFormatError("deck.json 內容不合法（欄位型別或規則錯誤）", details);
  }

  // 引用關係驗證（作為 warnings / errors）
  const topicIdSet = new Set(topics.map((t) => t.id));
  const paragraphIdSet = new Set(paragraphs.map((p) => p.id));

  const missingTopicRefs = cards.filter((c) => !topicIdSet.has(c.topicId));
  if (missingTopicRefs.length > 0) {
    throw new DeckFormatError("cards.topicId 找不到對應 topics.id", [
      ...missingTopicRefs.slice(0, 10).map((c) => `card ${c.id || "(no id)"} → ${c.topicId}`),
      missingTopicRefs.length > 10 ? "..." : "",
    ].filter(Boolean));
  }

  const missingParagraphRefs = topics
    .flatMap((t) => t.memberIds.map((pid) => ({ topicId: t.id, paragraphId: pid })))
    .filter((x) => !paragraphIdSet.has(x.paragraphId));
  if (missingParagraphRefs.length > 0) {
    warnings.push(
      `topics.memberIds 有 ${missingParagraphRefs.length} 筆找不到對應 paragraphs.id（UI 仍可顯示，但資料可能不完整）`,
    );
  }

  // stats 一致性（嚴格：v1 直接要求一致）
  const computed = {
    totalParagraphs: paragraphs.length,
    totalKeypoints: keypoints.length,
    totalTopics: topics.length,
    totalCards: cards.length,
  };
  const mismatch = Object.entries(computed).filter(([k, v]) => (stats as any)[k] !== v);
  if (mismatch.length > 0) {
    throw new DeckFormatError("stats 與實際數量不一致", mismatch.map(([k, v]) => `${k} 應為 ${v}`));
  }

  return { deck: { meta, paragraphs, keypoints, topics, cards, stats }, warnings };
}

function normalizeLegacyDeck(raw: unknown): { deck: DeckUI; warnings: string[] } {
  const details: string[] = [];
  const warnings: string[] = [];

  if (!isRecord(raw)) {
    throw new DeckFormatError("資料格式錯誤：根節點必須是物件");
  }

  const topicsRaw = raw.topics;
  const cardsRaw = raw.cards;
  const statsRaw = raw.stats;
  const paragraphsRaw = raw.paragraphs;

  if (!Array.isArray(topicsRaw)) details.push("缺少 `topics` 或 `topics` 不是陣列");
  if (!Array.isArray(cardsRaw)) details.push("缺少 `cards` 或 `cards` 不是陣列");
  if (!isRecord(statsRaw)) details.push("缺少 `stats` 或 `stats` 不是物件");
  if (!Array.isArray(paragraphsRaw)) details.push("缺少 `paragraphs` 或 `paragraphs` 不是陣列");

  if (details.length) {
    throw new DeckFormatError("資料格式不符合（可能不是 deck JSON）", details);
  }

  const topics: TopicV1[] = (topicsRaw as unknown[]).map((item, idx) => {
    if (!isRecord(item)) {
      details.push(`topics[${idx}] 必須是物件`);
      return { id: "", title: "", memberIds: [] };
    }
    return {
      id: asString(item.id, `topics[${idx}].id`, details),
      title: typeof item.title === "string" ? item.title : "未命名主題",
      memberIds: Array.isArray(item.memberIds)
        ? item.memberIds.filter((x) => typeof x === "string") as string[]
        : [],
    };
  });

  const cards: CardV1[] = (cardsRaw as unknown[]).map((item, idx) => {
    if (!isRecord(item)) {
      details.push(`cards[${idx}] 必須是物件`);
      return { id: "", topicId: "", title: "", bullets: [] };
    }
    const bullets = Array.isArray(item.bullets)
      ? (item.bullets.filter((x) => typeof x === "string") as string[])
      : [];
    return {
      id: asString(item.id, `cards[${idx}].id`, details),
      topicId: asString(item.topicId, `cards[${idx}].topicId`, details),
      title: typeof item.title === "string" ? item.title : "未命名卡片",
      bullets: clampBullets(bullets.length ? bullets : ["（此卡片目前沒有內容）"], details, `cards[${idx}]`),
    };
  });

  // 舊版 stats: paragraphCount/topicCount/cardCount
  const statsObj = statsRaw as UnknownRecord;
  const paragraphCount =
    typeof statsObj.paragraphCount === "number"
      ? statsObj.paragraphCount
      : (paragraphsRaw as unknown[]).length;
  const topicCount =
    typeof statsObj.topicCount === "number" ? statsObj.topicCount : topics.length;
  const cardCount =
    typeof statsObj.cardCount === "number" ? statsObj.cardCount : cards.length;

  const stats: DeckStatsUI = {
    totalParagraphs: paragraphCount,
    totalKeypoints: (paragraphsRaw as unknown[]).length,
    totalTopics: topicCount,
    totalCards: cardCount,
  };

  const topicIdSet = new Set(topics.map((t) => t.id));
  const missingTopicRefs = cards.filter((c) => !topicIdSet.has(c.topicId));
  if (missingTopicRefs.length > 0) {
    warnings.push(
      `cards.topicId 有 ${missingTopicRefs.length} 筆找不到 topics.id（UI 仍可顯示，但主題標題可能不完整）`,
    );
  }

  // 舊資料允許 stats 不一致，提供 warning
  const computed = { totalParagraphs: (paragraphsRaw as unknown[]).length, totalTopics: topics.length, totalCards: cards.length };
  if (stats.totalTopics !== computed.totalTopics || stats.totalCards !== computed.totalCards) {
    warnings.push("stats 與實際數量不一致（這通常表示資料仍是 P0 假資料格式）");
  }

  if (details.length) {
    throw new DeckFormatError("資料內容不合法", details);
  }

  return { deck: { topics, cards, stats }, warnings };
}

export function normalizeDeck(raw: unknown): { deck: DeckUI; warnings: string[] } {
  // v1 具備 meta/schemaVersion 或 stats.totalCards
  if (isRecord(raw)) {
    const meta = raw.meta;
    const stats = raw.stats;
    if (
      (isRecord(meta) && typeof meta.schemaVersion === "string") ||
      (isRecord(stats) && typeof stats.totalCards === "number")
    ) {
      const { deck, warnings } = parseDeckV1(raw);
      return {
        deck: {
          meta: deck.meta,
          topics: deck.topics,
          cards: deck.cards,
          stats: deck.stats,
        },
        warnings,
      };
    }
  }

  return normalizeLegacyDeck(raw);
}

