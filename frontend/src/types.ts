/**
 * 固定 Deck JSON schema（v1.0.0）
 * - 規格來源：docs/spec/technical-spec.md
 */

export interface DeckMeta {
  source: string;
  generatedAt: string; // ISO8601
  schemaVersion: string; // e.g. "1.0.0"
}

export interface Paragraph {
  id: string;
  idx: number;
  text: string;
  headingLevel?: number;
  sectionPath?: string[];
}

export interface Keypoint {
  paragraphId: string;
  sentence: string;
  keywords: string[];
}

export interface Topic {
  id: string;
  title: string;
  memberIds: string[];
  summaryBullets?: string[];
}

export interface Card {
  id: string;
  topicId: string;
  title: string;
  bullets: string[]; // 1–5
}

export interface DeckStats {
  totalParagraphs: number;
  totalKeypoints: number;
  totalTopics: number;
  totalCards: number;
}

export interface Deck {
  meta: DeckMeta;
  paragraphs: Paragraph[];
  keypoints: Keypoint[];
  topics: Topic[];
  cards: Card[];
  stats: DeckStats;
}


