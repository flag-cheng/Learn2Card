export interface DeckMeta {
  source: string;
  generatedAt: string; // ISO8601
  schemaVersion: "1.0.0" | string;
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
  keywords: string[]; // 1–5
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
  meta?: DeckMeta;
  paragraphs?: Paragraph[];
  keypoints?: Keypoint[];
  topics: Topic[];
  cards: Card[];
  stats?: DeckStats;
}

export interface NormalizedDeck {
  meta: DeckMeta;
  paragraphs: Paragraph[];
  keypoints: Keypoint[];
  topics: Topic[];
  cards: Card[];
  stats: DeckStats;
}


