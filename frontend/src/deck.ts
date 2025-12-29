import type { Deck, DeckMeta, DeckStats, NormalizedDeck, Paragraph } from "./types";

type RecordLike = Record<string, unknown>;

function isRecord(value: unknown): value is RecordLike {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asString(value: unknown, field: string): string {
  if (typeof value !== "string") {
    throw new Error(`欄位 ${field} 必須是字串。`);
  }
  return value;
}

function asNumber(value: unknown, field: string): number {
  if (typeof value !== "number" || Number.isNaN(value)) {
    throw new Error(`欄位 ${field} 必須是數字。`);
  }
  return value;
}

function asStringArray(value: unknown, field: string): string[] {
  if (!Array.isArray(value) || value.some((v) => typeof v !== "string")) {
    throw new Error(`欄位 ${field} 必須是字串陣列。`);
  }
  return value;
}

function normalizeMeta(value: unknown): DeckMeta {
  if (!isRecord(value)) {
    return {
      source: "unknown",
      generatedAt: new Date().toISOString(),
      schemaVersion: "1.0.0",
    };
  }

  const source = typeof value.source === "string" ? value.source : "unknown";
  const generatedAt =
    typeof value.generatedAt === "string" ? value.generatedAt : new Date().toISOString();
  const schemaVersion =
    typeof value.schemaVersion === "string" ? value.schemaVersion : "1.0.0";

  return { source, generatedAt, schemaVersion };
}

function normalizeParagraphs(value: unknown): Paragraph[] {
  if (!Array.isArray(value)) return [];

  return value.map((raw, i) => {
    if (!isRecord(raw)) {
      throw new Error(`paragraphs[${i}] 必須是物件。`);
    }

    // 新 schema：{id, idx, text, headingLevel?, sectionPath?}
    if (typeof raw.id === "string" && typeof raw.text === "string" && typeof raw.idx === "number") {
      const p: Paragraph = {
        id: raw.id,
        idx: raw.idx,
        text: raw.text,
      };
      if (typeof raw.headingLevel === "number") p.headingLevel = raw.headingLevel;
      if (Array.isArray(raw.sectionPath) && raw.sectionPath.every((v) => typeof v === "string")) {
        p.sectionPath = raw.sectionPath as string[];
      }
      return p;
    }

    // P0 相容：{id, text, sourceIndex}
    if (typeof raw.id === "string" && typeof raw.text === "string") {
      const idx = typeof raw.sourceIndex === "number" ? raw.sourceIndex : i;
      return { id: raw.id, idx, text: raw.text };
    }

    throw new Error(`paragraphs[${i}] 缺少必要欄位（id/idx/text）。`);
  });
}

function normalizeKeypoints(value: unknown, fallbackFromParagraphs: Paragraph[], rawDeck: RecordLike) {
  if (Array.isArray(value)) {
    return value.map((raw, i) => {
      if (!isRecord(raw)) throw new Error(`keypoints[${i}] 必須是物件。`);
      return {
        paragraphId: asString(raw.paragraphId, `keypoints[${i}].paragraphId`),
        sentence: asString(raw.sentence, `keypoints[${i}].sentence`),
        keywords: asStringArray(raw.keywords, `keypoints[${i}].keywords`),
      };
    });
  }

  // P0 相容：paragraphs[].summary/keywords
  if (Array.isArray(rawDeck.paragraphs)) {
    const rawParagraphs = rawDeck.paragraphs;
    return rawParagraphs
      .map((raw, i) => {
        if (!isRecord(raw)) return null;
        const paragraphId = typeof raw.id === "string" ? raw.id : fallbackFromParagraphs[i]?.id;
        if (!paragraphId) return null;
        const sentence = typeof raw.summary === "string" ? raw.summary : "";
        const keywords =
          Array.isArray(raw.keywords) && raw.keywords.every((v) => typeof v === "string")
            ? (raw.keywords as string[])
            : [];
        if (!sentence && keywords.length === 0) return null;
        return { paragraphId, sentence: sentence || "(無摘要)", keywords: keywords.slice(0, 5) };
      })
      .filter((v): v is NonNullable<typeof v> => v !== null);
  }

  return [];
}

function normalizeTopics(value: unknown) {
  if (!Array.isArray(value)) {
    throw new Error("缺少 topics（必須是陣列）。");
  }
  return value.map((raw, i) => {
    if (!isRecord(raw)) throw new Error(`topics[${i}] 必須是物件。`);
    const topic: any = {
      id: asString(raw.id, `topics[${i}].id`),
      title: typeof raw.title === "string" ? raw.title : "",
      memberIds: asStringArray(raw.memberIds, `topics[${i}].memberIds`),
    };
    if (Array.isArray(raw.summaryBullets) && raw.summaryBullets.every((v) => typeof v === "string")) {
      topic.summaryBullets = raw.summaryBullets;
    }
    return topic;
  });
}

function normalizeCards(value: unknown) {
  if (!Array.isArray(value)) {
    throw new Error("缺少 cards（必須是陣列）。");
  }

  return value.map((raw, i) => {
    if (!isRecord(raw)) throw new Error(`cards[${i}] 必須是物件。`);
    const bullets = Array.isArray(raw.bullets) ? raw.bullets : [];
    if (!Array.isArray(bullets) || bullets.some((v) => typeof v !== "string")) {
      throw new Error(`cards[${i}].bullets 必須是字串陣列。`);
    }
    if (bullets.length < 1 || bullets.length > 5) {
      throw new Error(`cards[${i}].bullets 長度需為 1–5（目前是 ${bullets.length}）。`);
    }

    return {
      id: asString(raw.id, `cards[${i}].id`),
      topicId: asString(raw.topicId, `cards[${i}].topicId`),
      title: typeof raw.title === "string" ? raw.title : "",
      bullets,
    };
  });
}

function normalizeStats(raw: unknown, computed: DeckStats): DeckStats {
  if (!isRecord(raw)) return computed;

  // P0 相容：paragraphCount/topicCount/cardCount
  if (
    typeof raw.paragraphCount === "number" ||
    typeof raw.topicCount === "number" ||
    typeof raw.cardCount === "number"
  ) {
    const fromP0: DeckStats = {
      totalParagraphs:
        typeof raw.paragraphCount === "number" ? raw.paragraphCount : computed.totalParagraphs,
      totalKeypoints: computed.totalKeypoints,
      totalTopics: typeof raw.topicCount === "number" ? raw.topicCount : computed.totalTopics,
      totalCards: typeof raw.cardCount === "number" ? raw.cardCount : computed.totalCards,
    };
    return fromP0;
  }

  // 新 schema：totalParagraphs/totalKeypoints/totalTopics/totalCards
  const stats: DeckStats = {
    totalParagraphs:
      typeof raw.totalParagraphs === "number" ? raw.totalParagraphs : computed.totalParagraphs,
    totalKeypoints:
      typeof raw.totalKeypoints === "number" ? raw.totalKeypoints : computed.totalKeypoints,
    totalTopics: typeof raw.totalTopics === "number" ? raw.totalTopics : computed.totalTopics,
    totalCards: typeof raw.totalCards === "number" ? raw.totalCards : computed.totalCards,
  };

  return stats;
}

function validateReferences(deck: NormalizedDeck) {
  const topicIds = new Set(deck.topics.map((t) => t.id));
  const paragraphIds = new Set(deck.paragraphs.map((p) => p.id));

  for (const card of deck.cards) {
    if (!topicIds.has(card.topicId)) {
      throw new Error(`cards.topicId 找不到對應 topics.id：${card.topicId}`);
    }
  }

  if (deck.paragraphs.length > 0) {
    for (const topic of deck.topics) {
      for (const pid of topic.memberIds) {
        if (!paragraphIds.has(pid)) {
          throw new Error(`topics.memberIds 找不到對應 paragraphs.id：${pid}（topic=${topic.id}）`);
        }
      }
    }
  }
}

function validateStats(deck: NormalizedDeck) {
  const computed: DeckStats = {
    totalParagraphs: deck.paragraphs.length,
    totalKeypoints: deck.keypoints.length,
    totalTopics: deck.topics.length,
    totalCards: deck.cards.length,
  };

  const mismatch: string[] = [];
  if (deck.stats.totalParagraphs !== computed.totalParagraphs) mismatch.push("totalParagraphs");
  if (deck.stats.totalKeypoints !== computed.totalKeypoints) mismatch.push("totalKeypoints");
  if (deck.stats.totalTopics !== computed.totalTopics) mismatch.push("totalTopics");
  if (deck.stats.totalCards !== computed.totalCards) mismatch.push("totalCards");

  if (mismatch.length > 0) {
    throw new Error(
      `stats 與實際數量不一致（${mismatch.join(", ")}）。` +
        `實際值：P=${computed.totalParagraphs} K=${computed.totalKeypoints} T=${computed.totalTopics} C=${computed.totalCards}`
    );
  }
}

export function normalizeDeck(input: unknown): NormalizedDeck {
  if (!isRecord(input)) {
    throw new Error("JSON 根節點必須是物件。");
  }

  const meta = normalizeMeta(input.meta);
  const paragraphs = normalizeParagraphs(input.paragraphs);
  const keypoints = normalizeKeypoints(input.keypoints, paragraphs, input);
  const topics = normalizeTopics(input.topics);
  const cards = normalizeCards(input.cards);

  const computed: DeckStats = {
    totalParagraphs: paragraphs.length,
    totalKeypoints: keypoints.length,
    totalTopics: topics.length,
    totalCards: cards.length,
  };

  const stats = normalizeStats(input.stats, computed);

  const deck: NormalizedDeck = {
    meta,
    paragraphs,
    keypoints,
    topics,
    cards,
    stats,
  };

  validateReferences(deck);
  validateStats(deck);

  return deck;
}

export async function fetchDeckJson(url: string): Promise<Deck> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`載入失敗：${url}（HTTP ${res.status}）`);
  }
  return (await res.json()) as Deck;
}

