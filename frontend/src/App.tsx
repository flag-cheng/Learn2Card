import { useEffect, useMemo, useState } from "react";
import sampleDeck from "./sampleDeck";
import "./App.css";
import type { Deck } from "./types";
import { parseDeckV1 } from "./deckValidator";

type TopicFilter = "all" | string;

const App = () => {
  const [deck, setDeck] = useState<Deck>(sampleDeck);
  const [deckSourceLabel, setDeckSourceLabel] = useState<string>(
    "內建 sampleDeck（fallback）",
  );
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");

  const [pageSize, setPageSize] = useState<number>(5);
  const [currentTopicId, setCurrentTopicId] = useState<TopicFilter>("all");
  const [currentCardIndex, setCurrentCardIndex] = useState(0);

  const [selectedFileName, setSelectedFileName] = useState<string>("");
  const [fileText, setFileText] = useState<string>("");
  const [pastedText, setPastedText] = useState<string>("");

  const setDeckAndResetView = (nextDeck: Deck, sourceLabel: string) => {
    setDeck(nextDeck);
    setDeckSourceLabel(sourceLabel);
    setCurrentTopicId("all");
    setCurrentCardIndex(0);
  };

  const loadDeckFromPublic = async (path: string, label: string) => {
    setErrorMessage("");
    setStatusMessage(`載入中：${path}`);
    try {
      const res = await fetch(path, { cache: "no-store" });
      if (!res.ok) {
        throw new Error(`載入失敗（HTTP ${res.status}）：${path}`);
      }
      const data = (await res.json()) as unknown;
      const parsed = parseDeckV1(data);
      if (!parsed.ok) {
        throw new Error(`JSON 格式錯誤：\n- ${parsed.errors.join("\n- ")}`);
      }
      setDeckAndResetView(parsed.deck, label);
      setStatusMessage(`已載入：${label}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setErrorMessage(message);
      setStatusMessage("");
    }
  };

  useEffect(() => {
    // 優先讀 deck.sample.json，若不存在則維持 sampleDeck fallback（並顯示提示）。
    void loadDeckFromPublic("/deck.sample.json", "public/deck.sample.json");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const visibleCards = useMemo(() => {
    if (currentTopicId === "all") {
      return deck.cards;
    }
    return deck.cards.filter((card) => card.topicId === currentTopicId);
  }, [currentTopicId, deck.cards]);

  const totalCards = visibleCards.length;
  const currentCard = visibleCards[currentCardIndex];

  const totalPages = Math.max(1, Math.ceil(totalCards / pageSize));
  const currentPage = totalCards === 0 ? 0 : Math.floor(currentCardIndex / pageSize);
  const disablePrevPage = totalCards === 0 || currentPage <= 0;
  const disableNextPage = totalCards === 0 || currentPage >= totalPages - 1;

  useEffect(() => {
    if (currentCardIndex >= totalCards && totalCards > 0) {
      setCurrentCardIndex(totalCards - 1);
    }
    if (totalCards === 0) {
      setCurrentCardIndex(0);
    }
  }, [currentCardIndex, totalCards]);

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

  const handlePrev = () => {
    setCurrentCardIndex((prev) => Math.max(prev - 1, 0));
  };

  const handleNext = () => {
    setCurrentCardIndex((prev) => Math.min(prev + 1, totalCards - 1));
  };

  const handlePrevPage = () => {
    const nextIndex = Math.max((currentPage - 1) * pageSize, 0);
    setCurrentCardIndex(nextIndex);
  };

  const handleNextPage = () => {
    const nextIndex = Math.min((currentPage + 1) * pageSize, Math.max(totalCards - 1, 0));
    setCurrentCardIndex(nextIndex);
  };

  const disablePrev = totalCards === 0 || currentCardIndex === 0;
  const disableNext = totalCards === 0 || currentCardIndex >= totalCards - 1;

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const active = document.activeElement;
      const tag = active?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || (active as HTMLElement | null)?.isContentEditable) {
        return;
      }

      if (event.key === "ArrowLeft") {
        if (!disablePrev) handlePrev();
      }
      if (event.key === "ArrowRight") {
        if (!disableNext) handleNext();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [disableNext, disablePrev, totalCards]);

  const handleFileChange = async (file: File | null) => {
    setErrorMessage("");
    setStatusMessage("");
    setSelectedFileName("");
    setFileText("");

    if (!file) return;

    const name = file.name || "";
    const lower = name.toLowerCase();
    const ok = lower.endsWith(".txt") || lower.endsWith(".md");
    if (!ok) {
      setErrorMessage("檔案格式不支援：僅接受 .txt 或 .md");
      return;
    }

    setSelectedFileName(name);
    setStatusMessage(`讀取檔案中：${name}`);
    try {
      const text = await file.text();
      if (!text.trim()) {
        setErrorMessage("檔案內容為空，請上傳有內容的 .txt/.md，或改用貼上文字。");
        setStatusMessage("");
        return;
      }
      setFileText(text);
      setPastedText(text);
      setStatusMessage(`已讀取：${name}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setErrorMessage(`讀取檔案失敗：${message}`);
      setStatusMessage("");
    }
  };

  const handleAnalyze = async () => {
    setErrorMessage("");
    const text = (fileText || pastedText || "").trim();
    if (!text) {
      setErrorMessage("請先上傳 .txt/.md 檔案或貼上純文字內容。");
      return;
    }

    setStatusMessage("分析中：送出文字到後端 /api/generate ...");
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(
          `後端回應失敗（HTTP ${res.status}）。\n` +
            `若尚未啟動後端，請先用「載入 deck.sample.json」驗收 UI。\n` +
            (body ? `\n---\n${body}` : ""),
        );
      }

      const data = (await res.json()) as unknown;
      const parsed = parseDeckV1(data);
      if (!parsed.ok) {
        throw new Error(`後端回傳的 JSON 不符合 schema：\n- ${parsed.errors.join("\n- ")}`);
      }

      setDeckAndResetView(parsed.deck, "後端 API：/api/generate");
      setStatusMessage("完成：已更新卡片內容。");
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setErrorMessage(message);
      setStatusMessage("");
    }
  };

  return (
    <div className="app">
      <div className="app-shell">
        <header className="app-header">
            <div className="app-title">文件歸納切卡機 · Demo UI Shell</div>
            <div className="app-subtitle">資料來源：{deckSourceLabel}</div>
        </header>

        <div className="main-layout">
          <aside className="sidebar">
            <section className="panel panel-input">
              <div className="panel-title">輸入（僅限 txt/md 或貼上文字）</div>

              <div className="input-row">
                <label className="input-label" htmlFor="file-input">
                  檔案上傳（.txt / .md）
                </label>
                <input
                  id="file-input"
                  className="file-input"
                  type="file"
                  accept=".txt,.md"
                  onChange={(e) => void handleFileChange(e.target.files?.[0] ?? null)}
                />
                {selectedFileName ? (
                  <div className="input-hint">已選擇：{selectedFileName}</div>
                ) : (
                  <div className="input-hint">未選擇檔案</div>
                )}
              </div>

              <div className="input-row">
                <label className="input-label" htmlFor="text-input">
                  或貼上純文字
                </label>
                <textarea
                  id="text-input"
                  className="text-area"
                  rows={7}
                  placeholder="貼上 Markdown 或純文字內容（不支援 URL / PDF / DOCX）"
                  value={pastedText}
                  onChange={(e) => setPastedText(e.target.value)}
                />
              </div>

              <div className="input-actions">
                <button className="nav-button" onClick={() => void handleAnalyze()}>
                  送出分析
                </button>
                <button
                  className="secondary-button"
                  onClick={() => void loadDeckFromPublic("/deck.sample.json", "public/deck.sample.json")}
                >
                  載入 deck.sample.json
                </button>
                <button
                  className="secondary-button"
                  onClick={() => void loadDeckFromPublic("/deck.json", "public/deck.json")}
                >
                  載入 deck.json
                </button>
              </div>

              {statusMessage ? <div className="status-banner">{statusMessage}</div> : null}
              {errorMessage ? <div className="error-banner">{errorMessage}</div> : null}
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
                    第 {currentCardIndex + 1} 張 / 共 {totalCards} 張（第{" "}
                    {currentPage + 1} 頁 / 共 {totalPages} 頁）
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

                <div className="controls controls-split">
                  <div className="pagination">
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
                    <label className="page-size">
                      每頁
                      <select
                        className="page-size-select"
                        value={pageSize}
                        onChange={(e) => setPageSize(Number(e.target.value))}
                      >
                        <option value={3}>3</option>
                        <option value={5}>5</option>
                        <option value={10}>10</option>
                      </select>
                      張
                    </label>
                  </div>

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


