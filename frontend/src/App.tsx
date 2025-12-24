import { useCallback, useEffect, useMemo, useState } from "react";
import sampleDeck from "./sampleDeck";
import type { Deck } from "./types";
import "./App.css";

type TopicFilter = "all" | string;

const isRecord = (value: unknown): value is Record<string, unknown> => {
  return typeof value === "object" && value !== null;
};

const isStringArray = (value: unknown): value is string[] => {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
};

const validateDeck = (value: unknown): { deck: Deck; warnings: string[] } => {
  if (!isRecord(value)) {
    throw new Error("Deck JSON 必須是一個 object。");
  }

  const warnings: string[] = [];

  const paragraphs = value.paragraphs;
  const topics = value.topics;
  const cards = value.cards;
  const stats = value.stats;

  if (!Array.isArray(paragraphs)) throw new Error("Deck JSON 缺少 paragraphs[]。");
  if (!Array.isArray(topics)) throw new Error("Deck JSON 缺少 topics[]。");
  if (!Array.isArray(cards)) throw new Error("Deck JSON 缺少 cards[]。");
  if (!isRecord(stats)) throw new Error("Deck JSON 缺少 stats 物件。");

  for (const [idx, p] of paragraphs.entries()) {
    if (!isRecord(p)) throw new Error(`paragraphs[${idx}] 必須是 object。`);
    if (typeof p.id !== "string") throw new Error(`paragraphs[${idx}].id 必須是 string。`);
    if (typeof p.text !== "string") throw new Error(`paragraphs[${idx}].text 必須是 string。`);
    if (typeof p.summary !== "string") throw new Error(`paragraphs[${idx}].summary 必須是 string。`);
    if (!isStringArray(p.keywords)) throw new Error(`paragraphs[${idx}].keywords 必須是 string[]。`);
    if (typeof p.sourceIndex !== "number") throw new Error(`paragraphs[${idx}].sourceIndex 必須是 number。`);
  }

  for (const [idx, t] of topics.entries()) {
    if (!isRecord(t)) throw new Error(`topics[${idx}] 必須是 object。`);
    if (typeof t.id !== "string") throw new Error(`topics[${idx}].id 必須是 string。`);
    if (typeof t.title !== "string") throw new Error(`topics[${idx}].title 必須是 string。`);
    if (!isStringArray(t.memberIds)) throw new Error(`topics[${idx}].memberIds 必須是 string[]。`);
  }

  for (const [idx, c] of cards.entries()) {
    if (!isRecord(c)) throw new Error(`cards[${idx}] 必須是 object。`);
    if (typeof c.id !== "string") throw new Error(`cards[${idx}].id 必須是 string。`);
    if (typeof c.topicId !== "string") throw new Error(`cards[${idx}].topicId 必須是 string。`);
    if (typeof c.title !== "string") throw new Error(`cards[${idx}].title 必須是 string。`);
    if (!isStringArray(c.bullets)) throw new Error(`cards[${idx}].bullets 必須是 string[]。`);
  }

  if (typeof stats.paragraphCount !== "number") throw new Error("stats.paragraphCount 必須是 number。");
  if (typeof stats.topicCount !== "number") throw new Error("stats.topicCount 必須是 number。");
  if (typeof stats.cardCount !== "number") throw new Error("stats.cardCount 必須是 number。");

  const derived = {
    paragraphCount: paragraphs.length,
    topicCount: topics.length,
    cardCount: cards.length,
  };

  if (
    stats.paragraphCount !== derived.paragraphCount ||
    stats.topicCount !== derived.topicCount ||
    stats.cardCount !== derived.cardCount
  ) {
    warnings.push(
      `警告：stats 與實際資料量不一致（stats=${stats.paragraphCount}/${stats.topicCount}/${stats.cardCount}，實際=${derived.paragraphCount}/${derived.topicCount}/${derived.cardCount}）。`
    );
  }

  return { deck: value as unknown as Deck, warnings };
};

const App = () => {
  const [deck, setDeck] = useState<Deck>(sampleDeck);
  const [dataSourceLabel, setDataSourceLabel] = useState(
    "內建 sampleDeck（P0 假資料）"
  );
  const [currentTopicId, setCurrentTopicId] = useState<TopicFilter>("all");
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [pageSize, setPageSize] = useState(5);

  const [inputText, setInputText] = useState("");
  const [inputFileName, setInputFileName] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [bannerMessage, setBannerMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const visibleCards = useMemo(() => {
    if (currentTopicId === "all") {
      return deck.cards;
    }
    return deck.cards.filter((card) => card.topicId === currentTopicId);
  }, [currentTopicId, deck.cards]);

  const totalCards = visibleCards.length;
  const currentCard = visibleCards[currentCardIndex];

  useEffect(() => {
    if (totalCards === 0) {
      if (currentCardIndex !== 0) setCurrentCardIndex(0);
      return;
    }
    if (currentCardIndex < 0 || currentCardIndex >= totalCards) {
      setCurrentCardIndex(0);
    }
  }, [currentCardIndex, totalCards]);

  const currentPage = totalCards === 0 ? 0 : Math.floor(currentCardIndex / pageSize) + 1;
  const pageCount = totalCards === 0 ? 0 : Math.ceil(totalCards / pageSize);
  const pageStart = totalCards === 0 ? 0 : (currentPage - 1) * pageSize;
  const pageEnd = totalCards === 0 ? 0 : Math.min(pageStart + pageSize, totalCards);

  const resolveTopicTitle = () => {
    if (currentTopicId === "all" && !currentCard) {
      return "全部主題";
    }
    const topicId =
      currentTopicId === "all" ? currentCard?.topicId : currentTopicId;
    const topic = deck.topics.find((item) => item.id === topicId);
    return topic?.title || "未命名主題";
  };

  const handleTopicChange = (topicId: TopicFilter) => {
    setCurrentTopicId(topicId);
    setCurrentCardIndex(0);
  };

  const handlePrev = useCallback(() => {
    setCurrentCardIndex((prev) => Math.max(prev - 1, 0));
  }, []);

  const handleNext = useCallback(() => {
    setCurrentCardIndex((prev) => Math.min(prev + 1, totalCards - 1));
  }, [totalCards]);

  const handlePrevPage = () => {
    if (totalCards === 0) return;
    const nextIndex = Math.max((currentPage - 2) * pageSize, 0);
    setCurrentCardIndex(nextIndex);
  };

  const handleNextPage = () => {
    if (totalCards === 0) return;
    const nextIndex = currentPage * pageSize;
    if (nextIndex >= totalCards) return;
    setCurrentCardIndex(nextIndex);
  };

  const loadExampleDeck = useCallback(
    async (options?: { silent?: boolean }) => {
      setErrorMessage(null);
      if (!options?.silent) setBannerMessage(null);
      setIsLoading(true);
      try {
        const res = await fetch("/deck.json", { method: "GET" });
        if (!res.ok) {
          throw new Error(`載入失敗（HTTP ${res.status}）`);
        }
        const json = (await res.json()) as unknown;
        const { deck: nextDeck, warnings } = validateDeck(json);
        setDeck(nextDeck);
        setDataSourceLabel("public/deck.json（範例 Deck）");
        setCurrentTopicId("all");
        setCurrentCardIndex(0);
        const msg =
          warnings.length > 0
            ? `已載入範例 deck.json；${warnings.join(" ")}`
            : "已載入範例 deck.json。";
        setBannerMessage(msg);
      } catch (err) {
        if (!options?.silent) {
          setErrorMessage(
            `範例 deck.json 載入失敗：${err instanceof Error ? err.message : String(err)}`
          );
        }
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    void loadExampleDeck({ silent: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFileChange = async (file: File | null) => {
    setErrorMessage(null);
    setBannerMessage(null);
    setInputFileName(null);

    if (!file) return;

    const lower = file.name.toLowerCase();
    const isTxt = lower.endsWith(".txt");
    const isMd = lower.endsWith(".md");
    if (!isTxt && !isMd) {
      setErrorMessage("檔案格式錯誤：僅接受 .txt 或 .md 檔案。");
      return;
    }

    setIsLoading(true);
    try {
      const text = await file.text();
      setInputText(text);
      setInputFileName(file.name);
      setBannerMessage(`已讀取檔案：${file.name}（尚未分析，請按「分析並生成卡片」）。`);
    } catch (err) {
      setErrorMessage(
        `讀取檔案失敗：${err instanceof Error ? err.message : String(err)}`
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleProcessText = async () => {
    setErrorMessage(null);
    setBannerMessage(null);

    const text = inputText.trim();
    if (!text) {
      setErrorMessage("空內容：請貼上文字內容或上傳 .txt/.md 檔案。");
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetch("/api/process", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text }),
      });

      const payload = (await res.json()) as unknown;
      if (!res.ok) {
        const message =
          isRecord(payload) && typeof payload.error === "string"
            ? payload.error
            : `API 呼叫失敗（HTTP ${res.status}）`;
        throw new Error(message);
      }

      const { deck: nextDeck, warnings } = validateDeck(payload);
      setDeck(nextDeck);
      setDataSourceLabel("文字分析（/api/process）");
      setCurrentTopicId("all");
      setCurrentCardIndex(0);

      const msg =
        warnings.length > 0
          ? `分析完成並更新卡片；${warnings.join(" ")}`
          : "分析完成並更新卡片。";
      setBannerMessage(msg);
    } catch (err) {
      setErrorMessage(
        `分析失敗：${err instanceof Error ? err.message : String(err)}`
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleUseSampleDeck = () => {
    setErrorMessage(null);
    setBannerMessage("已切回 sampleDeck（P0 假資料）。");
    setDeck(sampleDeck);
    setDataSourceLabel("內建 sampleDeck（P0 假資料）");
    setCurrentTopicId("all");
    setCurrentCardIndex(0);
  };

  const onKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      const isTyping =
        tag === "input" ||
        tag === "textarea" ||
        (target?.getAttribute?.("contenteditable") ?? "false") === "true";
      if (isTyping) return;

      if (e.key === "ArrowLeft") handlePrev();
      if (e.key === "ArrowRight") handleNext();
    },
    [handleNext, handlePrev]
  );

  useEffect(() => {
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onKeyDown]);

  const disablePrev = totalCards === 0 || currentCardIndex === 0;
  const disableNext = totalCards === 0 || currentCardIndex >= totalCards - 1;
  const disablePrevPage = totalCards === 0 || currentPage <= 1;
  const disableNextPage = totalCards === 0 || currentPage >= pageCount;

  return (
    <div className="app">
      <div className="app-shell">
        <header className="app-header">
          <div className="app-title">文件歸納切卡機 · Agent B</div>
          <div className="app-subtitle">
            資料來源：{dataSourceLabel}
            {isLoading ? <span className="loading-pill">處理中…</span> : null}
          </div>
        </header>

        <div className="main-layout">
          <aside className="sidebar">
            <section className="panel">
              <div className="panel-title">輸入</div>
              <div className="input-stack">
                <div className="input-row">
                  <label className="input-label">
                    上傳檔案（僅 .txt/.md）
                  </label>
                  <input
                    type="file"
                    accept=".txt,.md"
                    onChange={(e) => void handleFileChange(e.target.files?.[0] ?? null)}
                    disabled={isLoading}
                  />
                  {inputFileName ? (
                    <div className="input-hint">已選：{inputFileName}</div>
                  ) : null}
                </div>

                <div className="input-row">
                  <label className="input-label">或貼上純文字</label>
                  <textarea
                    className="text-area"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="把純文字或 Markdown 直接貼在這裡（不支援 URL / PDF / DOCX）"
                    rows={8}
                    disabled={isLoading}
                  />
                </div>

                <div className="button-row">
                  <button
                    className="nav-button"
                    onClick={() => void handleProcessText()}
                    disabled={isLoading}
                  >
                    分析並生成卡片
                  </button>
                  <button
                    className="secondary-button"
                    onClick={() => void loadExampleDeck()}
                    disabled={isLoading}
                  >
                    載入範例 deck.json
                  </button>
                  <button
                    className="secondary-button"
                    onClick={handleUseSampleDeck}
                    disabled={isLoading}
                  >
                    使用 sampleDeck
                  </button>
                </div>

                {bannerMessage ? (
                  <div className="banner banner-ok">{bannerMessage}</div>
                ) : null}
                {errorMessage ? (
                  <div className="banner banner-error">{errorMessage}</div>
                ) : null}
              </div>
            </section>

            <section className="panel panel-static">
              <div className="panel-title">統計資訊</div>
              <div className="stats-grid">
                <div className="stat-item">
                  <div className="stat-label">段落數</div>
                  <div className="stat-value">
                    {deck.stats.paragraphCount}
                  </div>
                </div>
                <div className="stat-item">
                  <div className="stat-label">主題數</div>
                  <div className="stat-value">{deck.stats.topicCount}</div>
                </div>
                <div className="stat-item">
                  <div className="stat-label">卡片數</div>
                  <div className="stat-value">{deck.stats.cardCount}</div>
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
                {deck.topics.map((topic) => (
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
                      第 {currentCardIndex + 1} 張 / 共 {totalCards} 張
                    </span>
                  </div>
                </div>

                <div className="pagination-bar">
                  <div className="pagination-left">
                    <span className="pagination-text">
                      分頁：第 {currentPage} / {pageCount} 頁（本頁 {pageStart + 1}–{pageEnd}）
                    </span>
                  </div>
                  <div className="pagination-right">
                    <label className="pagination-text">
                      每頁
                      <select
                        className="pagination-select"
                        value={pageSize}
                        onChange={(e) => {
                          const next = Number(e.target.value);
                          setPageSize(next);
                          setCurrentCardIndex(0);
                        }}
                        disabled={isLoading}
                      >
                        <option value={1}>1</option>
                        <option value={3}>3</option>
                        <option value={5}>5</option>
                        <option value={10}>10</option>
                      </select>
                      張
                    </label>
                    <button
                      className="secondary-button"
                      onClick={handlePrevPage}
                      disabled={disablePrevPage}
                    >
                      上一頁
                    </button>
                    <button
                      className="secondary-button"
                      onClick={handleNextPage}
                      disabled={disableNextPage}
                    >
                      下一頁
                    </button>
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
                <div className="hint-row">
                  鍵盤快捷：← / → 翻卡（輸入框聚焦時不觸發）
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
