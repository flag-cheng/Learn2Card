import { Deck } from "./types";

const sampleDeck: Deck = {
  meta: {
    source: "sampleDeck（frontend/src/sampleDeck.ts）",
    generatedAt: "2025-12-22T00:00:00.000Z",
    schemaVersion: "1.0.0",
  },
  paragraphs: [
    {
      id: "p1",
      idx: 0,
      text: "專案目標是把長文轉成一疊可翻閱的卡片，方便快速掌握重點。",
    },
    {
      id: "p2",
      idx: 1,
      text: "P0 階段只需前端 UI shell，採用 React + TypeScript 搭配內建假資料。",
    },
    {
      id: "p3",
      idx: 2,
      text: "畫面包含標題列、左側統計與主題列表，以及右側卡片檢視區。",
    },
    {
      id: "p4",
      idx: 3,
      text: "卡片需要支援上一張與下一張按鈕，並根據主題切換可見卡片。",
    },
    {
      id: "p5",
      idx: 4,
      text: "未來會改成讀取 deck.json，現階段只需確保 sampleDeck 可以 demo。",
    },
  ],
  keypoints: [
    {
      paragraphId: "p1",
      sentence: "將長文整理成卡片組，讓讀者能快速掌握重點。",
      keywords: ["摘要", "卡片化", "效率"],
    },
    {
      paragraphId: "p2",
      sentence: "P0 先以 React + TypeScript 的 UI shell 搭配假資料展示。",
      keywords: ["P0", "React", "假資料"],
    },
    {
      paragraphId: "p3",
      sentence: "介面由標題列、左側統計與主題、右側卡片區構成。",
      keywords: ["版面", "統計", "主題"],
    },
    {
      paragraphId: "p4",
      sentence: "卡片支援上一張/下一張並可依主題切換可見集合。",
      keywords: ["互動", "翻卡", "主題"],
    },
    {
      paragraphId: "p5",
      sentence: "後續可切換為讀取 deck.json，維持同一套瀏覽體驗。",
      keywords: ["deck.json", "示範", "未來工作"],
    },
  ],
  topics: [
    {
      id: "t1",
      title: "產品概念",
      memberIds: ["p1", "p2"],
    },
    {
      id: "t2",
      title: "介面布局",
      memberIds: ["p3"],
    },
    {
      id: "t3",
      title: "互動邏輯",
      memberIds: ["p4", "p5"],
    },
  ],
  cards: [
    {
      id: "c1",
      topicId: "t1",
      title: "文件歸納切卡機目標",
      bullets: [
        "將長文整理成可翻閱的卡片組",
        "提升閱讀與分享效率",
        "P0 使用內建 sampleDeck 展示 UI",
      ],
    },
    {
      id: "c2",
      topicId: "t2",
      title: "UI shell 版面",
      bullets: [
        "頂部顯示標題與資料來源說明",
        "左側呈現統計與主題切換",
        "右側為卡片檢視與翻卡按鈕",
      ],
    },
    {
      id: "c3",
      topicId: "t3",
      title: "互動與未來調整",
      bullets: [
        "依主題切換可見卡片並重置索引",
        "上一張/下一張需限制邊界",
        "未來可改讀 deck.json 取代 sampleDeck",
      ],
    },
  ],
  stats: {
    totalParagraphs: 5,
    totalKeypoints: 5,
    totalTopics: 3,
    totalCards: 3,
  },
};

export default sampleDeck;


