import { useMemo, useState } from "react";
import sampleDeck from "./sampleDeck";
import "./App.css";

type TopicFilter = "all" | string;

const App = () => {
  const [currentTopicId, setCurrentTopicId] = useState<TopicFilter>("all");
  const [currentCardIndex, setCurrentCardIndex] = useState(0);

  const visibleCards = useMemo(() => {
    if (currentTopicId === "all") {
      return sampleDeck.cards;
    }
    return sampleDeck.cards.filter((card) => card.topicId === currentTopicId);
  }, [currentTopicId]);

  const totalCards = visibleCards.length;
  const currentCard = visibleCards[currentCardIndex];

  const resolveTopicTitle = () => {
    if (currentTopicId === "all" && !currentCard) {
      return "全部主題";
    }
    const topicId =
      currentTopicId === "all" ? currentCard?.topicId : currentTopicId;
    const topic = sampleDeck.topics.find((item) => item.id === topicId);
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

  const disablePrev = totalCards === 0 || currentCardIndex === 0;
  const disableNext = totalCards === 0 || currentCardIndex >= totalCards - 1;

  return (
    <div className="app">
      <div className="app-shell">
        <header className="app-header">
          <div className="app-title">文件歸納切卡機 · Demo UI Shell</div>
          <div className="app-subtitle">資料來源：內建 sampleDeck（P0 假資料）</div>
        </header>

        <div className="main-layout">
          <aside className="sidebar">
            <section className="panel panel-static">
              <div className="panel-title">統計資訊</div>
              <div className="stats-grid">
                <div className="stat-item">
                  <div className="stat-label">段落數</div>
                  <div className="stat-value">
                    {sampleDeck.stats.paragraphCount}
                  </div>
                </div>
                <div className="stat-item">
                  <div className="stat-label">主題數</div>
                  <div className="stat-value">{sampleDeck.stats.topicCount}</div>
                </div>
                <div className="stat-item">
                  <div className="stat-label">卡片數</div>
                  <div className="stat-value">{sampleDeck.stats.cardCount}</div>
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
                {sampleDeck.topics.map((topic) => (
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


