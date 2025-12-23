import { useEffect, useMemo, useState } from "react";
import sampleDeck from "./sampleDeck";
import "./App.css";
import { DeckFormatError, normalizeDeck, type DeckUI } from "./deck";

type TopicFilter = "all" | string;

const App = () => {
  const initial = useMemo(() => normalizeDeck(sampleDeck as unknown), []);

  const [deck, setDeck] = useState<DeckUI>(initial.deck);
  const [deckWarnings, setDeckWarnings] = useState<string[]>(initial.warnings);
  const [dataSourceLabel, setDataSourceLabel] = useState(
    "內建 sampleDeck（P0 假資料）",
  );
  const [statusText, setStatusText] = useState<string | null>(null);
  const [error, setError] = useState<DeckFormatError | Error | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const [inputText, setInputText] = useState("");
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);

  const [currentTopicId, setCurrentTopicId] = useState<TopicFilter>("all");
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [currentPage, setCurrentPage] = useState(0);

  const visibleCards = useMemo(() => {
    if (currentTopicId === "all") {
      return deck.cards;
    }
    return deck.cards.filter((card) => card.topicId === currentTopicId);
  }, [currentTopicId, deck.cards]);

  const totalCards = visibleCards.length;
  const currentCard = visibleCards[currentCardIndex];
  const totalPages = pageSize > 0 ? Math.max(1, Math.ceil(totalCards / pageSize)) : 1;
  const currentPageSafe = Math.min(Math.max(currentPage, 0), totalPages - 1);
  const pageStartIndex = currentPageSafe * pageSize;
  const pageEndIndexExclusive = Math.min(pageStartIndex + pageSize, totalCards);

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
    setCurrentPage(0);
  };

  const handlePageChange = (nextPage: number) => {
    const clamped = Math.min(Math.max(nextPage, 0), totalPages - 1);
    setCurrentPage(clamped);
    setCurrentCardIndex(totalCards === 0 ? 0 : Math.min(clamped * pageSize, totalCards - 1));
  };

  const handlePrev = () => {
    setCurrentCardIndex((prev) => {
      const next = Math.max(prev - 1, 0);
      setCurrentPage(pageSize > 0 ? Math.floor(next / pageSize) : 0);
      return next;
    });
  };

  const handleNext = () => {
    setCurrentCardIndex((prev) => {
      const next = Math.min(prev + 1, totalCards - 1);
      setCurrentPage(pageSize > 0 ? Math.floor(next / pageSize) : 0);
      return next;
    });
  };

  const disablePrev = totalCards === 0 || currentCardIndex === 0;
  const disableNext = totalCards === 0 || currentCardIndex >= totalCards - 1;

  useEffect(() => {
    // 當 deck / topic 變動導致 index 超出範圍時，自動修正
    setCurrentCardIndex((prev) => (totalCards === 0 ? 0 : Math.min(prev, totalCards - 1)));
    setCurrentPage((prev) => (pageSize > 0 ? Math.min(prev, Math.max(0, Math.ceil(totalCards / pageSize) - 1)) : 0));
  }, [totalCards, pageSize]);

  useEffect(() => {
    // 換資料來源時回到起點（避免殘留舊狀態）
    setCurrentTopicId("all");
    setCurrentCardIndex(0);
    setCurrentPage(0);
  }, [deck]);

  useEffect(() => {
    const onKeyDown = (ev: KeyboardEvent) => {
      if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;
      const tag = (document.activeElement?.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea") return;
      if (ev.key === "ArrowLeft") handlePrev();
      if (ev.key === "ArrowRight") handleNext();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [totalCards, pageSize]);

  const presentError = (err: unknown, fallbackMessage: string) => {
    if (err instanceof DeckFormatError) {
      setError(err);
      return;
    }
    if (err instanceof Error) {
      setError(err);
      return;
    }
    setError(new Error(fallbackMessage));
  };

  const loadDeckFromPublic = async (path: "/deck.json" | "/deck.sample.json") => {
    setIsBusy(true);
    setError(null);
    setDeckWarnings([]);
    setStatusText(`載入中：${path}`);
    try {
      const res = await fetch(path, { cache: "no-store" });
      if (!res.ok) {
        throw new Error(`載入失敗：${path}（HTTP ${res.status}）`);
      }
      const json = (await res.json()) as unknown;
      const normalized = normalizeDeck(json);
      setDeck(normalized.deck);
      setDeckWarnings(normalized.warnings);
      setDataSourceLabel(`public${path}`);
      setStatusText(`載入成功：public${path}`);
    } catch (err) {
      presentError(err, "載入 deck JSON 失敗");
      setStatusText(null);
    } finally {
      setIsBusy(false);
    }
  };

  const resetToSample = () => {
    const normalized = normalizeDeck(sampleDeck as unknown);
    setDeck(normalized.deck);
    setDeckWarnings(normalized.warnings);
    setDataSourceLabel("內建 sampleDeck（P0 假資料）");
    setError(null);
    setStatusText("已切回內建 sampleDeck");
  };

  const handleFileChange = async (file: File | null) => {
    if (!file) return;
    const name = file.name.toLowerCase();
    const ok = name.endsWith(".txt") || name.endsWith(".md");
    if (!ok) {
      setSelectedFileName(null);
      setInputText("");
      setStatusText(null);
      setError(
        new DeckFormatError("檔案格式錯誤", ["僅接受 .txt 或 .md 檔案，且不支援 URL / PDF / DOCX 等格式"]),
      );
      return;
    }

    setIsBusy(true);
    setError(null);
    setStatusText(`讀取檔案中：${file.name}`);
    try {
      const text = await file.text();
      const trimmed = text.trim();
      if (!trimmed) {
        throw new DeckFormatError("空內容", ["檔案內容為空，請改用其他檔案或直接貼上文字"]);
      }
      setSelectedFileName(file.name);
      setInputText(text);
      setStatusText(`已載入檔案：${file.name}（可直接按「送出分析」）`);
    } catch (err) {
      presentError(err, "讀取檔案失敗");
      setStatusText(null);
    } finally {
      setIsBusy(false);
    }
  };

  const analyzeTextViaApi = async () => {
    const text = inputText.trim();
    if (!text) {
      setError(new DeckFormatError("空內容", ["請先貼上文字或上傳 .txt/.md 檔案"]));
      return;
    }
    setIsBusy(true);
    setError(null);
    setDeckWarnings([]);
    setStatusText("分析中：呼叫後端 /api/analyze");
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) {
        if (res.status === 404) {
          throw new Error(
            "後端 API（/api/analyze）尚未提供：目前 repo 的 backend 仍是佔位；你可以先用「載入 deck.sample.json / deck.json」驗證 UI。",
          );
        }
        const body = await res.text().catch(() => "");
        throw new Error(`後端回應失敗（HTTP ${res.status}）${body ? `：${body}` : ""}`);
      }
      const json = (await res.json()) as unknown;
      const normalized = normalizeDeck(json);
      setDeck(normalized.deck);
      setDeckWarnings(normalized.warnings);
      setDataSourceLabel(selectedFileName ? `API（${selectedFileName}）` : "API（貼上文字）");
      setStatusText("分析完成並載入卡片");
    } catch (err) {
      presentError(err, "分析失敗");
      setStatusText(null);
    } finally {
      setIsBusy(false);
    }
  };

  return (
    <div className="app">
      <div className="app-shell">
        <header className="app-header">
            <div className="app-title">文件歸納切卡機 · Demo UI Shell</div>
            <div className="app-subtitle">資料來源：{dataSourceLabel}</div>
        </header>

        <div className="main-layout">
          <aside className="sidebar">
            <section className="panel">
              <div className="panel-title">輸入 / 載入</div>
              <div className="io-actions">
                <button
                  className="secondary-button"
                  onClick={() => loadDeckFromPublic("/deck.sample.json")}
                  disabled={isBusy}
                >
                  載入 deck.sample.json
                </button>
                <button
                  className="secondary-button"
                  onClick={() => loadDeckFromPublic("/deck.json")}
                  disabled={isBusy}
                >
                  載入 deck.json
                </button>
                <button className="secondary-button" onClick={resetToSample} disabled={isBusy}>
                  回到 sampleDeck
                </button>
              </div>

              <div className="io-field">
                <div className="io-label">上傳檔案（僅 .txt / .md）</div>
                <input
                  type="file"
                  accept=".txt,.md"
                  onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
                  disabled={isBusy}
                />
              </div>

              <div className="io-field">
                <div className="io-label">或直接貼上純文字</div>
                <textarea
                  className="io-textarea"
                  rows={6}
                  value={inputText}
                  onChange={(e) => {
                    setInputText(e.target.value);
                    setSelectedFileName(null);
                  }}
                  placeholder="貼上 Markdown/純文字內容（不支援 URL 抓取）"
                  disabled={isBusy}
                />
              </div>

              <div className="io-actions">
                <button className="nav-button" onClick={analyzeTextViaApi} disabled={isBusy}>
                  送出分析
                </button>
                <button
                  className="secondary-button"
                  onClick={() => {
                    setInputText("");
                    setSelectedFileName(null);
                    setStatusText(null);
                    setError(null);
                  }}
                  disabled={isBusy}
                >
                  清除
                </button>
              </div>

              {statusText ? <div className="status-banner">{statusText}</div> : null}
              {error ? (
                <div className="error-banner">
                  <div className="error-title">{error.message}</div>
                  {"details" in error && Array.isArray((error as any).details) && (error as any).details.length ? (
                    <ul className="error-details">
                      {(error as any).details.slice(0, 8).map((d: string, i: number) => (
                        <li key={i}>{d}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}
              {deckWarnings.length ? (
                <div className="warning-banner">
                  <div className="warning-title">提醒</div>
                  <ul className="warning-details">
                    {deckWarnings.slice(0, 6).map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </section>

            <section className="panel panel-static">
              <div className="panel-title">統計資訊</div>
              <div className="stats-grid">
                <div className="stat-item">
                  <div className="stat-label">段落數</div>
                  <div className="stat-value">
                    {deck.stats.totalParagraphs}
                  </div>
                </div>
                <div className="stat-item">
                  <div className="stat-label">重點數</div>
                  <div className="stat-value">{deck.stats.totalKeypoints}</div>
                </div>
                <div className="stat-item">
                  <div className="stat-label">主題數</div>
                  <div className="stat-value">{deck.stats.totalTopics}</div>
                </div>
                <div className="stat-item">
                  <div className="stat-label">卡片數</div>
                  <div className="stat-value">{deck.stats.totalCards}</div>
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
                    <span className="pagination-label">每頁</span>
                    <select
                      className="pagination-select"
                      value={pageSize}
                      onChange={(e) => {
                        const next = Number(e.target.value);
                        setPageSize(Number.isFinite(next) && next > 0 ? next : 10);
                        setCurrentPage(0);
                        setCurrentCardIndex(0);
                      }}
                      disabled={isBusy}
                    >
                      {[5, 10, 20, 50].map((n) => (
                        <option key={n} value={n}>
                          {n}
                        </option>
                      ))}
                    </select>
                    <span className="pagination-label">張</span>
                  </div>
                  <div className="pagination-right">
                    <button
                      className="secondary-button"
                      onClick={() => handlePageChange(currentPageSafe - 1)}
                      disabled={isBusy || currentPageSafe <= 0}
                    >
                      上一頁
                    </button>
                    <span className="pagination-text">
                      第 {currentPageSafe + 1} / {totalPages} 頁（本頁 {pageStartIndex + 1}–{pageEndIndexExclusive}）
                    </span>
                    <button
                      className="secondary-button"
                      onClick={() => handlePageChange(currentPageSafe + 1)}
                      disabled={isBusy || currentPageSafe >= totalPages - 1}
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
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
};

export default App;


