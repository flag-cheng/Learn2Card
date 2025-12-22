import type { Card, Deck, Paragraph, Topic } from "./types";

type ParseResult =
  | { ok: true; deck: Deck }
  | { ok: false; errors: string[] };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function parseDeckV1(input: unknown): ParseResult {
  const errors: string[] = [];

  if (!isRecord(input)) {
    return { ok: false, errors: ["JSON 根節點必須是物件。"] };
  }

  const meta = input.meta;
  if (!isRecord(meta)) {
    errors.push("缺少 meta 物件。");
  } else {
    if (!isNonEmptyString(meta.source)) errors.push("meta.source 必須是非空字串。");
    if (!isNonEmptyString(meta.generatedAt))
      errors.push("meta.generatedAt 必須是非空字串（ISO8601）。");
    if (!isNonEmptyString(meta.schemaVersion))
      errors.push("meta.schemaVersion 必須是非空字串。");
  }

  const paragraphs = input.paragraphs;
  if (!Array.isArray(paragraphs)) {
    errors.push("paragraphs 必須是陣列。");
  }

  const keypoints = input.keypoints;
  if (!Array.isArray(keypoints)) {
    errors.push("keypoints 必須是陣列。");
  }

  const topics = input.topics;
  if (!Array.isArray(topics)) {
    errors.push("topics 必須是陣列。");
  }

  const cards = input.cards;
  if (!Array.isArray(cards)) {
    errors.push("cards 必須是陣列。");
  }

  const stats = input.stats;
  if (!isRecord(stats)) {
    errors.push("stats 必須是物件。");
  } else {
    if (!isFiniteNumber(stats.totalParagraphs))
      errors.push("stats.totalParagraphs 必須是數字。");
    if (!isFiniteNumber(stats.totalKeypoints))
      errors.push("stats.totalKeypoints 必須是數字。");
    if (!isFiniteNumber(stats.totalTopics)) errors.push("stats.totalTopics 必須是數字。");
    if (!isFiniteNumber(stats.totalCards)) errors.push("stats.totalCards 必須是數字。");
  }

  if (errors.length > 0) return { ok: false, errors };

  // 以最小成本做結構化檢查並回傳 Deck（已通過必要欄位驗證）
  const deck = input as unknown as Deck;

  // paragraphs
  const paragraphIds = new Set<string>();
  deck.paragraphs.forEach((p, idx) => {
    if (!isRecord(p)) {
      errors.push(`paragraphs[${idx}] 必須是物件。`);
      return;
    }
    if (!isNonEmptyString((p as Paragraph).id))
      errors.push(`paragraphs[${idx}].id 必須是非空字串。`);
    if (!isFiniteNumber((p as Paragraph).idx))
      errors.push(`paragraphs[${idx}].idx 必須是數字。`);
    if (!isNonEmptyString((p as Paragraph).text))
      errors.push(`paragraphs[${idx}].text 必須是非空字串。`);
    if (isNonEmptyString((p as Paragraph).id)) {
      paragraphIds.add((p as Paragraph).id);
    }
  });

  // keypoints
  deck.keypoints.forEach((kp, idx) => {
    if (!isRecord(kp)) {
      errors.push(`keypoints[${idx}] 必須是物件。`);
      return;
    }
    if (!isNonEmptyString(kp.paragraphId))
      errors.push(`keypoints[${idx}].paragraphId 必須是非空字串。`);
    if (!isNonEmptyString(kp.sentence))
      errors.push(`keypoints[${idx}].sentence 必須是非空字串。`);
    if (!isStringArray(kp.keywords) || kp.keywords.length < 1 || kp.keywords.length > 5) {
      errors.push(`keypoints[${idx}].keywords 必須是 1–5 個字串。`);
    }
  });

  // topics
  const topicIds = new Set<string>();
  deck.topics.forEach((t, idx) => {
    if (!isRecord(t)) {
      errors.push(`topics[${idx}] 必須是物件。`);
      return;
    }
    if (!isNonEmptyString((t as Topic).id))
      errors.push(`topics[${idx}].id 必須是非空字串。`);
    if (!isNonEmptyString((t as Topic).title))
      errors.push(`topics[${idx}].title 必須是非空字串。`);
    if (!Array.isArray((t as Topic).memberIds) || !isStringArray((t as Topic).memberIds)) {
      errors.push(`topics[${idx}].memberIds 必須是字串陣列。`);
    }
    if (Array.isArray((t as Topic).summaryBullets) && !isStringArray((t as Topic).summaryBullets)) {
      errors.push(`topics[${idx}].summaryBullets 若存在，必須是字串陣列。`);
    }
    if (isNonEmptyString((t as Topic).id)) {
      topicIds.add((t as Topic).id);
    }
  });

  // cards + bullets rules
  deck.cards.forEach((c, idx) => {
    if (!isRecord(c)) {
      errors.push(`cards[${idx}] 必須是物件。`);
      return;
    }
    if (!isNonEmptyString((c as Card).id))
      errors.push(`cards[${idx}].id 必須是非空字串。`);
    if (!isNonEmptyString((c as Card).topicId))
      errors.push(`cards[${idx}].topicId 必須是非空字串。`);
    if (!isNonEmptyString((c as Card).title))
      errors.push(`cards[${idx}].title 必須是非空字串。`);
    const bullets = (c as Card).bullets;
    if (!Array.isArray(bullets) || !isStringArray(bullets) || bullets.length < 1 || bullets.length > 5) {
      errors.push(`cards[${idx}].bullets 必須是 1–5 個字串。`);
    }
  });

  // cross refs
  deck.topics.forEach((t, idx) => {
    t.memberIds.forEach((pid) => {
      if (!paragraphIds.has(pid)) {
        errors.push(`topics[${idx}].memberIds 包含不存在的 paragraph id：${pid}`);
      }
    });
  });
  deck.cards.forEach((c, idx) => {
    if (!topicIds.has(c.topicId)) {
      errors.push(`cards[${idx}].topicId 指向不存在的 topic id：${c.topicId}`);
    }
  });

  // stats consistency
  if (deck.stats.totalParagraphs !== deck.paragraphs.length)
    errors.push("stats.totalParagraphs 與 paragraphs 長度不一致。");
  if (deck.stats.totalKeypoints !== deck.keypoints.length)
    errors.push("stats.totalKeypoints 與 keypoints 長度不一致。");
  if (deck.stats.totalTopics !== deck.topics.length)
    errors.push("stats.totalTopics 與 topics 長度不一致。");
  if (deck.stats.totalCards !== deck.cards.length)
    errors.push("stats.totalCards 與 cards 長度不一致。");

  // deterministic-ish rules (basic): 至少 1 topic
  if (deck.topics.length < 1) errors.push("topics 至少需要 1 個主題。");

  if (errors.length > 0) return { ok: false, errors };
  return { ok: true, deck };
}

