export interface Paragraph {
  id: string;
  text: string;
  summary: string;
  keywords: string[];
  sourceIndex: number;
}

export interface Topic {
  id: string;
  title: string;
  memberIds: string[];
}

export interface Card {
  id: string;
  topicId: string;
  title: string;
  bullets: string[];
}

export interface DeckStats {
  paragraphCount: number;
  topicCount: number;
  cardCount: number;
}

export interface Deck {
  paragraphs: Paragraph[];
  topics: Topic[];
  cards: Card[];
  stats: DeckStats;
}


