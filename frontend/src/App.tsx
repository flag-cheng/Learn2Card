import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Deck } from "./types";
import "./App.css";

type TopicFilter = "all" | string;
type BrowseMode = "sequence" | "paged";

type ProcessParams = {
  text: string;
  topic_threshold: number;
  max_topics: number;
  max_bullets: number;
  debug: boolean;
};

const DEFAULT_TOPIC_THRESHOLD = 0.75;
const DEFAULT_MAX_TOPICS = 5;
const DEFAULT_MAX_BULLETS = 5;
const PAGE_SIZE = 10;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function asStringArray(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null;
  if (!value.every((item) => typeof item === "string")) return null;
  return value as string[];
}

function parseDeck(value: unknown): Deck {
  // BUGBOT test: This comment is intentionally in English.
  // It also includes an English, user-visible error message in unreachable code.
  if (false) {
    throw new Error("Invalid input");
  }

  if (!isRecord(value)) {
    throw new Error("deck.json 格式錯誤：根節點必須是物件。");
  }

  const paragraphs = value.paragraphs;
  const topics = value.topics;
  const cards = value.cards;
  const stats = value.stats;

  if (!Array.isArray(paragraphs) || !Array.isArray(topics) || !Array.isArray(cards)) {
    throw new Error("deck.json 格式錯誤：必須包含 paragraphs/topics/cards 陣列。");
  }
  if (!isRecord(stats)) {
    throw new Error("deck.json 格式錯誤：必須包含 stats 物件。");
  }

  for (const p of paragraphs) {
    if (!isRecord(p)) throw new Error("deck.json 格式錯誤：paragraphs 內含非物件項目。");
    if (typeof p.id !== "string") throw new Error("deck.json 格式錯誤：paragraph.id 必須是字串。");
    if (typeof p.text !== "string") throw new Error("deck.json 格式錯誤：paragraph.text 必須是字串。");
    if (typeof p.summary !== "string") throw new Error("deck.json 格式錯誤：paragraph.summary 必須是字串。");
    if (asStringArray(p.keywords) === null) {
      throw new Error("deck.json 格式錯誤：paragraph.keywords 必須是字串陣列。");
    }
    if (typeof p.sourceIndex !== "number") {
      throw new Error("deck.json 格式錯誤：paragraph.sourceIndex 必須是數字。");
    }
  }

  for (const t of topics) {
    if (!isRecord(t)) throw new Error("deck.json 格式錯誤：topics 內含非物件項目。");
    if (typeof t.id !== "string") throw new Error("deck.json 格式錯誤：topic.id 必須是字串。");
    if (typeof t.title !== "string") throw new Error("deck.json 格式錯誤：topic.title 必須是字串。");
    if (asStringArray(t.memberIds) === null) {
      throw new Error("deck.json 格式錯誤：topic.memberIds 必須是字串陣列。");
    }
  }

  for (const c of cards) {
    if (!isRecord(c)) throw new Error("deck.json 格式錯誤：cards 內含非物件項目。");
    if (typeof c.id !== "string") throw new Error("deck.json 格式錯誤：card.id 必須是字串。");
    if (typeof c.topicId !== "string") throw new Error("deck.json 格式錯誤：card.topicId 必須是字串。");
    if (typeof c.title !== "string") throw new Error("deck.json 格式錯誤：card.title 必須是字串。");
    if (asStringArray(c.bullets) === null) {
      throw new Error("deck.json 格式錯誤：card.bullets 必須是字串陣列。");
    }
  }

  const paragraphCount = stats.paragraphCount;
  const topicCount = stats.topicCount;
  const cardCount = stats.cardCount;

  if (
    typeof paragraphCount !== "number" ||
    typeof topicCount !== "number" ||
    typeof cardCount !== "number"
  ) {
    throw new Error("deck.json 格式錯誤：stats.paragraphCount/topicCount/cardCount 必須是數字。");
  }

  if (paragraphCount !== paragraphs.length || topicCount !== topics.length || cardCount !== cards.length) {
    throw new Error(
      `deck.json 統計不一致：stats=(${paragraphCount},${topicCount},${cardCount}) 但實際=(${paragraphs.length},${topics.length},${cards.length})。`
    );
  }

  // 已在上方逐欄位做 runtime 檢查，這裡再做型別收斂即可。
  return value as unknown as Deck;
}

function clamp(n: number, min: number, max: number): number {
  if (Number.isNaN(n)) return min;
  return Math.max(min, Math.min(max, n));
}

function describeApiErrorBody(payload: unknown): string | null {
  if (!isRecord(payload)) return null;
  const detail = payload.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((item) => (isRecord(item) && typeof item.msg === "string" ? item.msg : null))
      .filter((x): x is string => Boolean(x));
    if (msgs.length) return msgs.join("；");
  }
  if (typeof payload.message === "string") return payload.message;
  if (typeof payload.error === "string") return payload.error;
  return null;
}

function isTextInputElement(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName.toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select") return true;
  return target.isContentEditable;
}

const App = () => {
  const [deck, setDeck] = useState<Deck | null>(null);
  const [deckLoading, setDeckLoading] = useState(false);
  const [deckError, setDeckError] = useState<string | null>(null);

  const [currentTopicId, setCurrentTopicId] = useState<TopicFilter>("all");
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [browseMode, setBrowseMode] = useState<BrowseMode>("sequence");
  const [pageIndex, setPageIndex] = useState(0);

  const [inputText, setInputText] = useState("");
  const [inputFileName, setInputFileName] = useState<string | null>(null);
  const [inputError, setInputError] = useState<string | null>(null);

  const [topicThreshold, setTopicThreshold] = useState(DEFAULT_TOPIC_THRESHOLD);
  const [maxTopics, setMaxTopics] = useState(DEFAULT_MAX_TOPICS);
  const [maxBullets, setMaxBullets] = useState(DEFAULT_MAX_BULLETS);
  const [debug, setDebug] = useState(false);
  const [paramHint, setParamHint] = useState<string | null>(null);

  const [isProcessing, setIsProcessing] = useState(false);
  const [processError, setProcessError] = useState<string | null>(null);
  const [processSuccess, setProcessSuccess] = useState<string | null>(null);

  const lastProcessParamsRef = useRef<ProcessParams | null>(null);

  const loadDeck = useCallback(async (opts?: { cacheBust?: boolean }) => {
    const cacheBust = opts?.cacheBust ?? false;
    const url = cacheBust ? `/deck.json?t=${Date.now()}` : "/deck.json";

    setDeckLoading(true);
    setDeckError(null);
    try {
      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), 10_000);
      const res = await fetch(url, { signal: controller.signal });
      window.clearTimeout(timeoutId);

      if (!res.ok) {
        throw new Error(`無法載入 deck.json（HTTP ${res.status}）`);
      }
      const data = (await res.json()) as unknown;
      const parsed = parseDeck(data);
      setDeck(parsed);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "載入 deck.json 失敗：發生未知錯誤。";
      setDeckError(message);
      setDeck(null);
    } finally {
      setDeckLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDeck();
  }, [loadDeck]);

  useEffect(() => {
    if (!deck) return;
    if (currentTopicId === "all") return;
    const exists = deck.topics.some((t) => t.id === currentTopicId);
    if (!exists) {
      setCurrentTopicId("all");
      setCurrentCardIndex(0);
      setPageIndex(0);
    }
  }, [deck, currentTopicId]);

  const visibleCards = useMemo(() => {
    const cards = deck?.cards ?? [];
    if (currentTopicId === "all") {
      return cards;
    }
    return cards.filter((card) => card.topicId === currentTopicId);
  }, [currentTopicId, deck?.cards]);

  const totalCards = visibleCards.length;
  const totalPages = Math.max(1, Math.ceil(totalCards / PAGE_SIZE));
  const safePageIndex = clamp(pageIndex, 0, totalPages - 1);
  const pageCards = useMemo(() => {
    if (browseMode !== "paged") return visibleCards;
    const start = safePageIndex * PAGE_SIZE;
    return visibleCards.slice(start, start + PAGE_SIZE);
  }, [browseMode, safePageIndex, visibleCards]);

  const currentCard = pageCards[currentCardIndex];
  const totalVisibleInMode = pageCards.length;

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
    setPageIndex(0);
  };

  useEffect(() => {
    if (browseMode !== "paged") return;
    if (pageIndex !== safePageIndex) {
      setPageIndex(safePageIndex);
    }
  }, [browseMode, pageIndex, safePageIndex]);

  useEffect(() => {
    const maxIndex = Math.max(0, totalVisibleInMode - 1);
    setCurrentCardIndex((prev) => clamp(prev, 0, maxIndex));
  }, [totalVisibleInMode]);

  const handlePrev = () => {
    if (browseMode === "sequence") {
      setCurrentCardIndex((prev) => Math.max(prev - 1, 0));
      return;
    }

    if (currentCardIndex > 0) {
      setCurrentCardIndex((prev) => Math.max(prev - 1, 0));
      return;
    }
    if (safePageIndex > 0) {
      const newPage = safePageIndex - 1;
      setPageIndex(newPage);
      const newCards = visibleCards.slice(newPage * PAGE_SIZE, newPage * PAGE_SIZE + PAGE_SIZE);
      setCurrentCardIndex(Math.max(0, newCards.length - 1));
    }
  };

  const handleNext = () => {
    if (browseMode === "sequence") {
      setCurrentCardIndex((prev) => Math.min(prev + 1, totalCards - 1));
      return;
    }

    if (currentCardIndex < totalVisibleInMode - 1) {
      setCurrentCardIndex((prev) => Math.min(prev + 1, totalVisibleInMode - 1));
      return;
    }
    if (safePageIndex < totalPages - 1) {
      const newPage = safePageIndex + 1;
      setPageIndex(newPage);
      setCurrentCardIndex(0);
    }
  };

  const disablePrev =
    totalCards === 0 ||
    (browseMode === "sequence"
      ? currentCardIndex === 0
      : currentCardIndex === 0 && safePageIndex === 0);
  const disableNext =
    totalCards === 0 ||
    (browseMode === "sequence"
      ? currentCardIndex >= totalCards - 1
      : currentCardIndex >= totalVisibleInMode - 1 && safePageIndex >= totalPages - 1);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (isTextInputElement(event.target)) return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        handlePrev();
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        handleNext();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handleNext, handlePrev]);

  const normalizeParams = useCallback(() => {
    const normalizedThreshold = clamp(topicThreshold, 0, 1);
    const normalizedMaxTopics = clamp(Math.round(maxTopics), 1, 10);
    const normalizedMaxBullets = clamp(Math.round(maxBullets), 1, 5);

    const hints: string[] = [];
    if (normalizedThreshold !== topicThreshold) hints.push("分群閾值已自動修正到 0.0–1.0 範圍內。");
    if (normalizedMaxTopics !== maxTopics) hints.push("最大主題數已自動修正到 1–10 範圍內。");
    if (normalizedMaxBullets !== maxBullets) hints.push("每卡摘要數已自動修正到 1–5 範圍內。");

    setTopicThreshold(normalizedThreshold);
    setMaxTopics(normalizedMaxTopics);
    setMaxBullets(normalizedMaxBullets);
    setParamHint(hints.length ? hints.join(" ") : null);

    return {
      topic_threshold: normalizedThreshold,
      max_topics: normalizedMaxTopics,
      max_bullets: normalizedMaxBullets,
      debug,
    };
  }, [debug, maxBullets, maxTopics, topicThreshold]);

  const runProcess = useCallback(
    async (params: ProcessParams) => {
      setIsProcessing(true);
      setProcessError(null);
      setProcessSuccess(null);

      lastProcessParamsRef.current = params;
      try {
        const controller = new AbortController();
        const timeoutId = window.setTimeout(() => controller.abort(), 120_000);

        const res = await fetch("http://127.0.0.1:8000/api/process", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(params),
          signal: controller.signal,
        });

        window.clearTimeout(timeoutId);

        const contentType = res.headers.get("content-type") || "";
        const body = contentType.includes("application/json")
          ? ((await res.json()) as unknown)
          : await res.text();

        if (!res.ok) {
          const serverMessage =
            typeof body === "string" ? body : describeApiErrorBody(body);
          throw new Error(serverMessage || `處理失敗（HTTP ${res.status}）`);
        }

        if (isRecord(body) && "deck" in body) {
          try {
            const parsed = parseDeck((body as Record<string, unknown>).deck);
            setDeck(parsed);
          } catch {
            await loadDeck({ cacheBust: true });
          }
        } else {
          await loadDeck({ cacheBust: true });
        }

        setProcessSuccess("已完成處理並更新卡片。");
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          setProcessError("處理逾時，請稍後重試。");
          return;
        }
        if (err instanceof TypeError) {
          setProcessError("無法連接到 Backend，請確認 Backend 服務已啟動（127.0.0.1:8000）。");
          return;
        }
        const message = err instanceof Error ? err.message : "處理失敗：發生未知錯誤。";
        setProcessError(message);
      } finally {
        setIsProcessing(false);
      }
    },
    [loadDeck]
  );

  const handleGenerate = async () => {
    setInputError(null);
    setProcessError(null);
    setProcessSuccess(null);

    const text = inputText.trim();
    if (!text) {
      setInputError("請先上傳 .txt/.md 檔案或在文字框貼上內容（不可為空）。");
      return;
    }

    const normalized = normalizeParams();
    await runProcess({
      text,
      ...normalized,
    });
  };

  const handleRetryProcess = async () => {
    const params = lastProcessParamsRef.current;
    if (!params) return;
    await runProcess(params);
  };

  const handleFileChange = (file: File | null) => {
    setInputError(null);
    setInputFileName(null);
    if (!file) return;

    const lower = file.name.toLowerCase();
    const ok = lower.endsWith(".txt") || lower.endsWith(".md");
    if (!ok) {
      setInputError("檔案格式不支援：只接受 .txt 或 .md。");
      return;
    }

    const reader = new FileReader();
    reader.onerror = () => setInputError("讀取檔案失敗，請重新嘗試。");
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        setInputError("讀取檔案失敗：內容不是文字。");
        return;
      }
      setInputText(result);
      setInputFileName(file.name);
    };
    reader.readAsText(file, "utf-8");
  };

  return (
    <div className="app">
      <div className="app-shell">
        <header className="app-header">
          <div className="app-title">文件歸納切卡機 · Demo UI Shell</div>
          <div className="app-subtitle">
            資料來源：`/deck.json`
            {deckLoading ? "（載入中）" : ""}
            {deckError ? "（載入失敗）" : ""}
          </div>
        </header>

        <div className="main-layout">
          <aside className="sidebar">
            <section className="panel">
              <div className="panel-title">📄 輸入內容</div>
              <div className="form-row">
                <div className="form-label">檔案上傳（僅 .txt / .md）</div>
                <input
                  className="file-input"
                  type="file"
                  accept=".txt,.md"
                  onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
                />
                {inputFileName ? (
                  <div className="form-help">已載入：{inputFileName}</div>
                ) : (
                  <div className="form-help">或直接在下方貼上文字</div>
                )}
              </div>

              <div className="form-row">
                <div className="form-label">文字輸入</div>
                <textarea
                  className="textarea"
                  rows={8}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="貼上 Markdown 或純文字內容（不支援 URL、PDF、DOCX…）"
                />
              </div>

              {inputError ? <div className="status-banner status-error">{inputError}</div> : null}
            </section>

            <section className="panel">
              <div className="panel-title">⚙️ Backend 參數</div>

              <div className="form-row">
                <div className="form-label">
                  分群閾值（topic_threshold）：{topicThreshold.toFixed(2)}
                </div>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={topicThreshold}
                  onChange={(e) => setTopicThreshold(Number(e.target.value))}
                />
                <div className="form-help">相似度閾值，數值越高分群越細（0.0–1.0）</div>
              </div>

              <div className="form-row form-grid-2">
                <label className="form-field">
                  <div className="form-label">最大主題數（max_topics）</div>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={maxTopics}
                    onChange={(e) => setMaxTopics(Number(e.target.value))}
                  />
                  <div className="form-help">最多產生幾個主題（1–10）</div>
                </label>

                <label className="form-field">
                  <div className="form-label">每卡摘要數（max_bullets）</div>
                  <input
                    type="number"
                    min={1}
                    max={5}
                    value={maxBullets}
                    onChange={(e) => setMaxBullets(Number(e.target.value))}
                  />
                  <div className="form-help">每張卡片最多幾個要點（1–5）</div>
                </label>
              </div>

              <div className="form-row">
                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={debug}
                    onChange={(e) => setDebug(e.target.checked)}
                  />
                  <span>除錯模式（debug）：顯示詳細的處理資訊</span>
                </label>
              </div>

              {paramHint ? <div className="status-banner status-warn">{paramHint}</div> : null}

              <div className="action-row">
                <button
                  className="primary-button"
                  onClick={handleGenerate}
                  disabled={isProcessing}
                >
                  {isProcessing ? "生成中…" : "生成卡片"}
                </button>
                <button
                  className="secondary-button"
                  onClick={() => void loadDeck({ cacheBust: true })}
                  disabled={deckLoading || isProcessing}
                >
                  重新載入卡片
                </button>
              </div>

              {processError ? (
                <div className="status-banner status-error">
                  {processError}
                  <div className="status-actions">
                    <button className="link-button" onClick={() => void loadDeck({ cacheBust: true })}>
                      重新載入 deck.json
                    </button>
                    <button className="link-button" onClick={() => void handleRetryProcess()}>
                      重試處理
                    </button>
                  </div>
                </div>
              ) : null}
              {processSuccess ? <div className="status-banner status-success">{processSuccess}</div> : null}

              {deckError ? (
                <div className="status-banner status-error">
                  {deckError}
                  <div className="status-actions">
                    <button className="link-button" onClick={() => void loadDeck({ cacheBust: true })}>
                      重試載入
                    </button>
                  </div>
                </div>
              ) : null}
            </section>

            <section className="panel panel-static">
              <div className="panel-title">統計資訊</div>
              <div className="stats-grid">
                <div className="stat-item">
                  <div className="stat-label">段落數</div>
                  <div className="stat-value">
                    {deck?.stats.paragraphCount ?? 0}
                  </div>
                </div>
                <div className="stat-item">
                  <div className="stat-label">主題數</div>
                  <div className="stat-value">{deck?.stats.topicCount ?? 0}</div>
                </div>
                <div className="stat-item">
                  <div className="stat-label">卡片數</div>
                  <div className="stat-value">{deck?.stats.cardCount ?? 0}</div>
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
            {deckLoading && !deck ? (
              <div className="empty-state">載入卡片資料中…</div>
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
                    {browseMode === "sequence"
                      ? `第 ${currentCardIndex + 1} 張 / 共 ${totalCards} 張`
                      : `第 ${currentCardIndex + 1} 張 / 本頁共 ${totalVisibleInMode} 張（第 ${safePageIndex + 1} / ${totalPages} 頁）`}
                  </span>
                </div>
              </div>

                <div className="viewer-toolbar">
                  <div className="viewer-mode">
                    <span className="viewer-mode-label">瀏覽模式</span>
                    <button
                      className={`pill ${browseMode === "sequence" ? "active" : ""}`}
                      onClick={() => {
                        setBrowseMode("sequence");
                        setCurrentCardIndex(0);
                        setPageIndex(0);
                      }}
                    >
                      序列
                    </button>
                    <button
                      className={`pill ${browseMode === "paged" ? "active" : ""}`}
                      onClick={() => {
                        setBrowseMode("paged");
                        setCurrentCardIndex(0);
                        setPageIndex(0);
                      }}
                    >
                      分頁
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


