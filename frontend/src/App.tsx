import { useCallback, useEffect, useMemo, useState } from "react";
import type { Deck } from "./types";
import "./App.css";

type TopicFilter = "all" | string;

const DEFAULT_TOPIC_THRESHOLD = 0.75;
const DEFAULT_MAX_TOPICS = 5;
const DEFAULT_MAX_BULLETS = 5;

type BrowseMode = "sequence" | "paged";

function escapeShellArg(text: string): string {
  return text
    .replace(/\\/g, "\\\\")
    .replace(/"/g, '\\"')
    .replace(/\n/g, "\\n")
    .replace(/\r/g, "\\r");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function parseDeckJson(value: unknown): Deck {
  if (!isRecord(value)) {
    throw new Error("deck.json 必須是 JSON object。");
  }

  const paragraphs = value.paragraphs;
  const topics = value.topics;
  const cards = value.cards;
  const stats = value.stats;

  if (!Array.isArray(paragraphs)) throw new Error("deck.json 缺少 paragraphs[]。");
  if (!Array.isArray(topics)) throw new Error("deck.json 缺少 topics[]。");
  if (!Array.isArray(cards)) throw new Error("deck.json 缺少 cards[]。");
  if (!isRecord(stats)) throw new Error("deck.json 缺少 stats。");

  for (const [idx, p] of paragraphs.entries()) {
    if (!isRecord(p)) throw new Error(`paragraphs[${idx}] 必須是 object。`);
    if (typeof p.id !== "string") throw new Error(`paragraphs[${idx}].id 必須是字串。`);
    if (typeof p.text !== "string") throw new Error(`paragraphs[${idx}].text 必須是字串。`);
    if (typeof p.summary !== "string") throw new Error(`paragraphs[${idx}].summary 必須是字串。`);
    if (!isStringArray(p.keywords)) throw new Error(`paragraphs[${idx}].keywords 必須是字串陣列。`);
    if (typeof p.sourceIndex !== "number" || Number.isNaN(p.sourceIndex)) {
      throw new Error(`paragraphs[${idx}].sourceIndex 必須是數字。`);
    }
  }

  for (const [idx, t] of topics.entries()) {
    if (!isRecord(t)) throw new Error(`topics[${idx}] 必須是 object。`);
    if (typeof t.id !== "string") throw new Error(`topics[${idx}].id 必須是字串。`);
    if (typeof t.title !== "string") throw new Error(`topics[${idx}].title 必須是字串。`);
    if (!isStringArray(t.memberIds)) throw new Error(`topics[${idx}].memberIds 必須是字串陣列。`);
  }

  for (const [idx, c] of cards.entries()) {
    if (!isRecord(c)) throw new Error(`cards[${idx}] 必須是 object。`);
    if (typeof c.id !== "string") throw new Error(`cards[${idx}].id 必須是字串。`);
    if (typeof c.topicId !== "string") throw new Error(`cards[${idx}].topicId 必須是字串。`);
    if (typeof c.title !== "string") throw new Error(`cards[${idx}].title 必須是字串。`);
    if (!isStringArray(c.bullets)) throw new Error(`cards[${idx}].bullets 必須是字串陣列。`);
  }

  const paragraphCount = stats.paragraphCount;
  const topicCount = stats.topicCount;
  const cardCount = stats.cardCount;

  if (typeof paragraphCount !== "number" || Number.isNaN(paragraphCount)) {
    throw new Error("stats.paragraphCount 必須是數字。");
  }
  if (typeof topicCount !== "number" || Number.isNaN(topicCount)) {
    throw new Error("stats.topicCount 必須是數字。");
  }
  if (typeof cardCount !== "number" || Number.isNaN(cardCount)) {
    throw new Error("stats.cardCount 必須是數字。");
  }

  if (paragraphCount !== paragraphs.length) {
    throw new Error(
      `stats.paragraphCount (${paragraphCount}) 與 paragraphs.length (${paragraphs.length}) 不一致。`
    );
  }
  if (topicCount !== topics.length) {
    throw new Error(`stats.topicCount (${topicCount}) 與 topics.length (${topics.length}) 不一致。`);
  }
  if (cardCount !== cards.length) {
    throw new Error(`stats.cardCount (${cardCount}) 與 cards.length (${cards.length}) 不一致。`);
  }

  return value as unknown as Deck;
}

const App = () => {
  const [deck, setDeck] = useState<Deck | null>(null);
  const [deckLoading, setDeckLoading] = useState(false);
  const [deckError, setDeckError] = useState<string | null>(null);
  const [deckLoadedAt, setDeckLoadedAt] = useState<string | null>(null);

  const [currentTopicId, setCurrentTopicId] = useState<TopicFilter>("all");
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [browseMode, setBrowseMode] = useState<BrowseMode>("sequence");
  const [pageSize, setPageSize] = useState(5);

  const [inputText, setInputText] = useState("");
  const [inputError, setInputError] = useState<string | null>(null);
  const [inputFileName, setInputFileName] = useState<string | null>(null);

  const [topicThreshold, setTopicThreshold] = useState(DEFAULT_TOPIC_THRESHOLD);
  const [maxTopicsRaw, setMaxTopicsRaw] = useState(String(DEFAULT_MAX_TOPICS));
  const [maxBulletsRaw, setMaxBulletsRaw] = useState(String(DEFAULT_MAX_BULLETS));
  const [debug, setDebug] = useState(false);

  const [copyHint, setCopyHint] = useState<string | null>(null);

  const loadDeck = useCallback(async () => {
    setDeckLoading(true);
    setDeckError(null);
    try {
      const res = await fetch(`/deck.json?t=${Date.now()}`, { cache: "no-store" });
      if (!res.ok) {
        throw new Error(`載入失敗：HTTP ${res.status}`);
      }
      const json = (await res.json()) as unknown;
      const parsed = parseDeckJson(json);
      setDeck(parsed);
      setDeckLoadedAt(new Date().toLocaleString());
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setDeckError(message);
    } finally {
      setDeckLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDeck();
  }, [loadDeck]);

  useEffect(() => {
    if (!deck) return;
    if (currentTopicId !== "all" && !deck.topics.some((t) => t.id === currentTopicId)) {
      setCurrentTopicId("all");
      setCurrentCardIndex(0);
    }
  }, [deck, currentTopicId]);

  const visibleCards = useMemo(() => {
    if (!deck) return [];
    if (currentTopicId === "all") {
      return deck.cards;
    }
    return deck.cards.filter((card) => card.topicId === currentTopicId);
  }, [currentTopicId, deck]);

  const totalCards = visibleCards.length;
  const safeCardIndex = Math.min(Math.max(currentCardIndex, 0), Math.max(0, totalCards - 1));
  const currentCard = visibleCards[safeCardIndex];

  useEffect(() => {
    const maxIndex = Math.max(0, totalCards - 1);
    if (currentCardIndex > maxIndex) {
      setCurrentCardIndex(maxIndex);
    }
  }, [currentCardIndex, totalCards]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;

      const active = document.activeElement;
      if (
        active instanceof HTMLElement &&
        (active.tagName === "INPUT" ||
          active.tagName === "TEXTAREA" ||
          active.isContentEditable)
      ) {
        return;
      }

      if (event.key === "ArrowLeft") {
        setCurrentCardIndex((prev) => Math.max(prev - 1, 0));
      } else {
        setCurrentCardIndex((prev) => Math.min(prev + 1, Math.max(0, totalCards - 1)));
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [totalCards]);

  const totalPages = Math.max(1, Math.ceil(totalCards / pageSize));
  const currentPageIndex = Math.min(Math.floor(safeCardIndex / pageSize), totalPages - 1);
  const currentIndexInPage = safeCardIndex - currentPageIndex * pageSize;
  const currentPageCount = Math.min(pageSize, Math.max(0, totalCards - currentPageIndex * pageSize));

  const resolveTopicTitle = () => {
    if (currentTopicId === "all" && !currentCard) {
      return "全部主題";
    }
    const topicId =
      currentTopicId === "all" ? currentCard?.topicId : currentTopicId;
    const topic = deck?.topics.find((item) => item.id === topicId);
    return topic?.title || "未命名主題";
  };

  const handleTopicChange = (topicId: TopicFilter) => {
    setCurrentTopicId(topicId);
    setCurrentCardIndex(0);
  };

  const handlePrev = () => {
    setCurrentCardIndex((prev) => Math.max(prev - 1, 0));
  };

  const handleNext = () => {
    setCurrentCardIndex((prev) => Math.min(prev + 1, Math.max(0, totalCards - 1)));
  };

  const handlePrevPage = () => {
    if (totalCards === 0) return;
    const nextIndex = Math.max(0, (currentPageIndex - 1) * pageSize);
    setCurrentCardIndex(nextIndex);
  };

  const handleNextPage = () => {
    if (totalCards === 0) return;
    const nextIndex = Math.min((currentPageIndex + 1) * pageSize, Math.max(0, totalCards - 1));
    setCurrentCardIndex(nextIndex);
  };

  const disablePrev = totalCards === 0 || safeCardIndex === 0;
  const disableNext = totalCards === 0 || safeCardIndex >= totalCards - 1;
  const disablePrevPage = totalCards === 0 || currentPageIndex === 0;
  const disableNextPage = totalCards === 0 || currentPageIndex >= totalPages - 1;

  const maxTopicsParsed = useMemo(() => {
    const parsed = Number.parseInt(maxTopicsRaw, 10);
    if (!Number.isFinite(parsed)) {
      return { value: DEFAULT_MAX_TOPICS, error: "最大主題數必須是整數，已回退為預設值 5。" };
    }
    if (parsed < 1 || parsed > 10) {
      return { value: DEFAULT_MAX_TOPICS, error: "最大主題數範圍為 1–10，已回退為預設值 5。" };
    }
    return { value: parsed, error: null };
  }, [maxTopicsRaw]);

  const maxBulletsParsed = useMemo(() => {
    const parsed = Number.parseInt(maxBulletsRaw, 10);
    if (!Number.isFinite(parsed)) {
      return { value: DEFAULT_MAX_BULLETS, error: "每卡摘要數必須是整數，已回退為預設值 5。" };
    }
    if (parsed < 1 || parsed > 5) {
      return { value: DEFAULT_MAX_BULLETS, error: "每卡摘要數範圍為 1–5，已回退為預設值 5。" };
    }
    return { value: parsed, error: null };
  }, [maxBulletsRaw]);

  const canGenerate = inputText.trim().length > 0;

  const command = useMemo(() => {
    const escapedText = escapeShellArg(inputText);
    let cmd = `cd backend && uv run python main.py --text "${escapedText}"`;

    if (Math.abs(topicThreshold - DEFAULT_TOPIC_THRESHOLD) > 1e-9) {
      cmd += ` --topic-threshold ${topicThreshold.toFixed(2)}`;
    }
    if (maxTopicsParsed.value !== DEFAULT_MAX_TOPICS) {
      cmd += ` --max-topics ${maxTopicsParsed.value}`;
    }
    if (maxBulletsParsed.value !== DEFAULT_MAX_BULLETS) {
      cmd += ` --max-bullets ${maxBulletsParsed.value}`;
    }
    if (debug) {
      cmd += " --debug";
    }
    return cmd;
  }, [debug, inputText, maxBulletsParsed.value, maxTopicsParsed.value, topicThreshold]);

  const handleCopy = useCallback(async () => {
    setCopyHint(null);
    try {
      await navigator.clipboard.writeText(command);
      setCopyHint("已複製到剪貼簿。");
      window.setTimeout(() => setCopyHint(null), 2000);
    } catch {
      setCopyHint("複製失敗：此瀏覽器或環境可能不允許剪貼簿存取。");
    }
  }, [command]);

  const handleFileChange = useCallback((file: File | null) => {
    setInputError(null);
    setInputFileName(null);
    if (!file) return;

    const lower = file.name.toLowerCase();
    const isAllowed = lower.endsWith(".txt") || lower.endsWith(".md");
    if (!isAllowed) {
      setInputError("檔案格式不支援：僅接受 .txt 或 .md 檔案。");
      return;
    }

    const reader = new FileReader();
    reader.onerror = () => {
      setInputError("讀取檔案失敗：請確認檔案權限或重新選擇。");
    };
    reader.onload = () => {
      const content = typeof reader.result === "string" ? reader.result : "";
      if (!content.trim()) {
        setInputError("檔案內容為空：請上傳包含文字的 .txt 或 .md 檔案。");
      }
      setInputText(content);
      setInputFileName(file.name);
    };
    reader.readAsText(file);
  }, []);

  return (
    <div className="app">
      <div className="app-shell">
        <header className="app-header">
            <div className="app-title">文件歸納切卡機 · Demo UI Shell</div>
            <div className="app-subtitle">
              資料來源：<code>/public/deck.json</code>
              {deckLoadedAt ? `（最後載入：${deckLoadedAt}）` : ""}
            </div>
        </header>

        <div className="main-layout">
          <aside className="sidebar">
            <section className="panel">
              <div className="panel-title">📄 上傳檔案或輸入文字</div>
              <div className="form-group">
                <label className="field-label">
                  檔案上傳（僅 .txt / .md）
                  <input
                    className="file-input"
                    type="file"
                    accept=".txt,.md"
                    onChange={(e) => handleFileChange(e.target.files?.item(0) ?? null)}
                  />
                </label>
                {inputFileName ? <div className="hint">已選擇：{inputFileName}</div> : null}
                {inputError ? <div className="error-text">{inputError}</div> : null}
              </div>

              <div className="form-group">
                <label className="field-label">文字輸入（可直接貼上）</label>
                <textarea
                  className="text-area"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="把 Markdown 或純文字貼在這裡（或使用上方上傳檔案）"
                  rows={6}
                />
                {!canGenerate ? <div className="hint">提示：目前文字為空，無法產生可執行指令。</div> : null}
              </div>
            </section>

            <section className="panel">
              <div className="panel-title">⚙️ Backend 處理參數（可選）</div>

              <div className="form-group">
                <div className="field-row">
                  <label className="field-label">分群閾值（0.0–1.0）</label>
                  <div className="field-value">{topicThreshold.toFixed(2)}</div>
                </div>
                <input
                  className="slider"
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={topicThreshold}
                  onChange={(e) => setTopicThreshold(Number.parseFloat(e.target.value))}
                />
                <div className="hint">相似度閾值，數值越高分群越細。</div>
              </div>

              <div className="form-group">
                <label className="field-label">最大主題數（1–10）</label>
                <input
                  className="number-input"
                  type="number"
                  min={1}
                  max={10}
                  value={maxTopicsRaw}
                  onChange={(e) => setMaxTopicsRaw(e.target.value)}
                />
                <div className="hint">最多產生幾個主題。</div>
                {maxTopicsParsed.error ? <div className="error-text">{maxTopicsParsed.error}</div> : null}
              </div>

              <div className="form-group">
                <label className="field-label">每卡摘要數（1–5）</label>
                <input
                  className="number-input"
                  type="number"
                  min={1}
                  max={5}
                  value={maxBulletsRaw}
                  onChange={(e) => setMaxBulletsRaw(e.target.value)}
                />
                <div className="hint">每張卡片最多幾個要點。</div>
                {maxBulletsParsed.error ? <div className="error-text">{maxBulletsParsed.error}</div> : null}
              </div>

              <label className="checkbox-row">
                <input type="checkbox" checked={debug} onChange={(e) => setDebug(e.target.checked)} />
                <span>除錯模式（顯示詳細的處理資訊）</span>
              </label>
            </section>

            <section className="panel">
              <div className="panel-title">📋 Backend 執行指令</div>
              <pre className="code-block">{canGenerate ? command : "（請先上傳檔案或貼上文字後再產生指令）"}</pre>

              <div className="button-row">
                <button className="action-button" onClick={handleCopy} disabled={!canGenerate}>
                  複製指令
                </button>
                <button className="action-button secondary" onClick={loadDeck} disabled={deckLoading}>
                  {deckLoading ? "載入中…" : "重新載入卡片"}
                </button>
              </div>
              {copyHint ? <div className="hint">{copyHint}</div> : null}

              <div className="hint steps">
                1. 點擊「複製指令」<br />
                2. 開啟終端<br />
                3. 貼上並執行指令<br />
                4. 執行完成後，點擊「重新載入卡片」
              </div>

              {deckError ? <div className="error-text">卡片載入錯誤：{deckError}</div> : null}
            </section>

            <section className="panel panel-static">
              <div className="panel-title">統計資訊</div>
              <div className="stats-grid">
                <div className="stat-item">
                  <div className="stat-label">段落數</div>
                  <div className="stat-value">
                    {deck?.stats.paragraphCount ?? "-"}
                  </div>
                </div>
                <div className="stat-item">
                  <div className="stat-label">主題數</div>
                  <div className="stat-value">{deck?.stats.topicCount ?? "-"}</div>
                </div>
                <div className="stat-item">
                  <div className="stat-label">卡片數</div>
                  <div className="stat-value">{deck?.stats.cardCount ?? "-"}</div>
                </div>
              </div>
            </section>

            <section className="panel">
              <div className="panel-title">主題列表</div>
              <div className="topics-list">
                <button
                  className={`topic-button ${
                    currentTopicId === "all" ? "active" : ""
                  }`}
                  onClick={() => handleTopicChange("all")}
                >
                  全部主題
                </button>
                {(deck?.topics ?? []).map((topic) => (
                  <button
                    key={topic.id}
                    className={`topic-button ${
                      currentTopicId === topic.id ? "active" : ""
                    }`}
                    onClick={() => handleTopicChange(topic.id)}
                  >
                    {topic.title || "未命名主題"}
                  </button>
                ))}
              </div>
            </section>
          </aside>

          <main className="main-panel">
            {totalCards === 0 ? (
              <div className="empty-state">
                目前沒有卡片可顯示（可能是資料尚未產生）。
              </div>
            ) : (
              <div className="card-viewer">
              <div className="card-meta">
                <div className="card-topic">
                  <span className="card-topic-text">{resolveTopicTitle()}</span>
                  <span className="card-counter">
                    {browseMode === "sequence" ? (
                      <>第 {safeCardIndex + 1} 張 / 共 {totalCards} 張</>
                    ) : (
                      <>
                        第 {currentIndexInPage + 1} 張 / 本頁 {currentPageCount} 張（第{" "}
                        {currentPageIndex + 1} 頁 / 共 {totalPages} 頁）
                      </>
                    )}
                  </span>
                </div>
              </div>

                <div className="card">
                  <h2 className="card-title">
                    {currentCard?.title || "未命名卡片"}
                  </h2>
                  {currentCard?.bullets?.length ? (
                    <ul className="card-bullets">
                      {currentCard.bullets.map((bullet, idx) => (
                        <li key={idx}>{bullet}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="card-empty">（此卡片目前沒有內容）</p>
                  )}
                </div>

                <div className="controls">
                  <div className="mode-toggle">
                    <span className="mode-label">瀏覽模式</span>
                    <button
                      className={`mode-button ${browseMode === "sequence" ? "active" : ""}`}
                      onClick={() => setBrowseMode("sequence")}
                    >
                      序列
                    </button>
                    <button
                      className={`mode-button ${browseMode === "paged" ? "active" : ""}`}
                      onClick={() => setBrowseMode("paged")}
                    >
                      分頁
                    </button>
                    {browseMode === "paged" ? (
                      <>
                        <span className="mode-label">每頁</span>
                        <select
                          className="select-input"
                          value={pageSize}
                          onChange={(e) => setPageSize(Number.parseInt(e.target.value, 10))}
                        >
                          {[3, 5, 8, 10].map((n) => (
                            <option key={n} value={n}>
                              {n}
                            </option>
                          ))}
                        </select>
                      </>
                    ) : null}
                  </div>

                  {browseMode === "paged" ? (
                    <>
                      <button
                        className="nav-button secondary"
                        onClick={handlePrevPage}
                        disabled={disablePrevPage}
                      >
                        ← 上一頁
                      </button>
                      <button
                        className="nav-button secondary"
                        onClick={handleNextPage}
                        disabled={disableNextPage}
                      >
                        下一頁 →
                      </button>
                    </>
                  ) : null}
                  <button
                    className="nav-button"
                    onClick={handlePrev}
                    disabled={disablePrev}
                  >
                    ← 上一張
                  </button>
                  <button
                    className="nav-button"
                    onClick={handleNext}
                    disabled={disableNext}
                  >
                    下一張 →
                  </button>
                </div>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
};

export default App;


