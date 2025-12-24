import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";
import { fetchDeckJson, normalizeDeck } from "./deck";
import type { NormalizedDeck } from "./types";

type TopicFilter = "all" | string;

const DEFAULT_DECK_URLS = ["/deck.json", "/deck.sample.json"] as const;

function isEditableTarget(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) return false;
  const tag = target.tagName.toLowerCase();
  return tag === "input" || tag === "textarea" || tag === "select" || target.isContentEditable;
}

const App = () => {
  const [deck, setDeck] = useState<NormalizedDeck | null>(null);
  const [sourceLabel, setSourceLabel] = useState<string>("（尚未載入）");
  const [urlInput, setUrlInput] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [currentTopicId, setCurrentTopicId] = useState<TopicFilter>("all");
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const loadFromUrl = useCallback(async (url: string, label?: string) => {
    setLoading(true);
    setError(null);
    try {
      const raw = await fetchDeckJson(url);
      const normalized = normalizeDeck(raw);
      setDeck(normalized);
      setSourceLabel(label ?? url);
      setCurrentTopicId("all");
      setCurrentCardIndex(0);
    } catch (e) {
      const message = e instanceof Error ? e.message : "未知錯誤";
      setError(message);
      setDeck(null);
      setSourceLabel(label ?? url);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDefault = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      for (const url of DEFAULT_DECK_URLS) {
        try {
          const raw = await fetchDeckJson(url);
          const normalized = normalizeDeck(raw);
          setDeck(normalized);
          setSourceLabel(url);
          setCurrentTopicId("all");
          setCurrentCardIndex(0);
          return;
        } catch (e) {
          // 若 deck.json 不存在，會在此被捕捉並繼續嘗試下一個
          if (url === DEFAULT_DECK_URLS[DEFAULT_DECK_URLS.length - 1]) {
            throw e;
          }
        }
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : "未知錯誤";
      setError(message);
      setDeck(null);
      setSourceLabel("（預設載入失敗）");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDefault();
  }, [loadDefault]);

  const visibleCards = useMemo(() => {
    if (!deck) return [];
    if (currentTopicId === "all") {
      return deck.cards;
    }
    return deck.cards.filter((card) => card.topicId === currentTopicId);
  }, [currentTopicId, deck]);

  const totalCards = visibleCards.length;
  const currentCard = visibleCards[currentCardIndex];

  const totalPages = totalCards === 0 ? 0 : Math.ceil(totalCards / pageSize);
  const currentPage = totalCards === 0 ? 0 : Math.floor(currentCardIndex / pageSize) + 1;

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

  const handlePrev = useCallback(() => {
    setCurrentCardIndex((prev) => Math.max(prev - 1, 0));
  }, []);

  const handleNext = useCallback(() => {
    setCurrentCardIndex((prev) => Math.min(prev + 1, totalCards - 1));
  }, [totalCards]);

  const goToPage = useCallback(
    (page: number) => {
      if (totalCards === 0) return;
      const safe = Math.max(1, Math.min(page, totalPages));
      const nextIndex = (safe - 1) * pageSize;
      setCurrentCardIndex(Math.min(nextIndex, totalCards - 1));
    },
    [pageSize, totalCards, totalPages],
  );

  const handlePrevPage = useCallback(() => {
    if (currentPage <= 1) return;
    goToPage(currentPage - 1);
  }, [currentPage, goToPage]);

  const handleNextPage = useCallback(() => {
    if (currentPage >= totalPages) return;
    goToPage(currentPage + 1);
  }, [currentPage, goToPage, totalPages]);

  const handleFileChange = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as unknown;
      const normalized = normalizeDeck(parsed);
      setDeck(normalized);
      setSourceLabel(file.name);
      setCurrentTopicId("all");
      setCurrentCardIndex(0);
    } catch (e) {
      const message = e instanceof Error ? e.message : "未知錯誤";
      setError(message);
      setDeck(null);
      setSourceLabel(file.name);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (loading) return;
      if (totalCards === 0) return;
      if (isEditableTarget(e.target)) return;

      if (e.key === "ArrowLeft") {
        e.preventDefault();
        handlePrev();
      }
      if (e.key === "ArrowRight") {
        e.preventDefault();
        handleNext();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handleNext, handlePrev, loading, totalCards]);

  const disablePrev = totalCards === 0 || currentCardIndex === 0;
  const disableNext = totalCards === 0 || currentCardIndex >= totalCards - 1;
  const disablePrevPage = totalCards === 0 || currentPage <= 1;
  const disableNextPage = totalCards === 0 || currentPage >= totalPages;

  const stats = deck?.stats ?? {
    totalParagraphs: 0,
    totalKeypoints: 0,
    totalTopics: 0,
    totalCards: 0,
  };

  return (
    <div className="app">
      <div className="app-shell">
        <header className="app-header">
            <div className="app-title">文件歸納切卡機 · Demo UI Shell</div>
            <div className="app-subtitle">
              {loading
                ? "資料載入中…"
                : error
                  ? "資料載入失敗（請見下方錯誤訊息）"
                  : `資料來源：${sourceLabel}`}
              {deck ? ` · schema ${deck.meta.schemaVersion}` : ""}
            </div>
        </header>

        <div className="main-layout">
          <aside className="sidebar">
            <section className="panel">
              <div className="panel-title">資料載入</div>
              <div className="source-controls">
                <div className="control-row">
                  <button
                    className="secondary-button"
                    onClick={() => void loadDefault()}
                    disabled={loading}
                  >
                    重新載入預設（deck.json → deck.sample.json）
                  </button>
                </div>

                <div className="control-row">
                  <label className="file-label">
                    <span className="file-label-text">選擇本機 JSON</span>
                    <input
                      className="file-input"
                      type="file"
                      accept=".json,application/json"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (!file) return;
                        void handleFileChange(file);
                        e.currentTarget.value = "";
                      }}
                      disabled={loading}
                    />
                  </label>
                </div>

                <div className="control-row">
                  <input
                    className="text-input"
                    placeholder="輸入 URL（例如 http://localhost:8000/deck.json）"
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                    disabled={loading}
                  />
                  <button
                    className="secondary-button"
                    onClick={() => void loadFromUrl(urlInput.trim() || "/deck.json")}
                    disabled={loading}
                  >
                    從 URL 載入
                  </button>
                </div>

                <div className="hint-text">提示：翻卡也支援鍵盤 ← / →</div>
              </div>
            </section>

            <section className="panel panel-static">
              <div className="panel-title">統計資訊</div>
              <div className="stats-grid">
                <div className="stat-item">
                  <div className="stat-label">重點數</div>
                  <div className="stat-value">{stats.totalKeypoints}</div>
                </div>
                <div className="stat-item">
                  <div className="stat-label">主題數</div>
                  <div className="stat-value">{stats.totalTopics}</div>
                </div>
                <div className="stat-item">
                  <div className="stat-label">卡片數</div>
                  <div className="stat-value">{stats.totalCards}</div>
                </div>
              </div>
              <div className="stats-footnote">
                段落數：{stats.totalParagraphs}
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
                  disabled={!deck || loading}
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
                    disabled={loading}
                  >
                    {topic.title || "未命名主題"}
                  </button>
                ))}
              </div>
            </section>
          </aside>

          <main className="main-panel">
            {loading ? (
              <div className="loading-state">資料載入中…</div>
            ) : error ? (
              <div className="error-state">
                <div className="error-title">載入/驗證失敗</div>
                <pre className="error-message">{error}</pre>
                <div className="error-hint">
                  請確認 JSON 符合 schema（topics/cards/stats 必填；bullets 需 1–5 條；id 關聯需對應）。
                </div>
              </div>
            ) : totalCards === 0 ? (
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
                    {totalPages > 0 ? ` · 第 ${currentPage} / ${totalPages} 頁` : ""}
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

                <div className="controls controls-wrap">
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

                  <div className="controls-spacer" />

                  <button
                    className="secondary-button"
                    onClick={handlePrevPage}
                    disabled={disablePrevPage}
                    title="上一頁"
                  >
                    ← 上一頁
                  </button>
                  <select
                    className="select"
                    value={currentPage}
                    onChange={(e) => goToPage(Number(e.target.value))}
                    disabled={totalPages <= 1}
                    title="跳轉頁面"
                  >
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                      <option key={p} value={p}>
                        第 {p} 頁
                      </option>
                    ))}
                  </select>
                  <button
                    className="secondary-button"
                    onClick={handleNextPage}
                    disabled={disableNextPage}
                    title="下一頁"
                  >
                    下一頁 →
                  </button>

                  <div className="page-size">
                    <span className="page-size-label">每頁</span>
                    <select
                      className="select"
                      value={pageSize}
                      onChange={(e) => setPageSize(Number(e.target.value))}
                      title="每頁卡片數"
                    >
                      {[1, 5, 10, 20, 50].map((n) => (
                        <option key={n} value={n}>
                          {n}
                        </option>
                      ))}
                    </select>
                    <span className="page-size-label">張</span>
                  </div>
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


