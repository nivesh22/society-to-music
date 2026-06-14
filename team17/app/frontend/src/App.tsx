import { useState, useEffect } from "react";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  Cell,
} from "recharts";
import {
  Activity,
  Globe,
  Clock,
  Settings,
  ChevronDown,
  Smile,
  Music,
  FileText,
} from "lucide-react";

const API_BASE = "/api";

function Dropdown({ label, options, val, setVal, icon: Icon }: any) {
  return (
    <div className="control-item">
      <div className="flex items-center justify-between control-label">
        <span>{label}</span>
        {Icon && <Icon size={14} />}
      </div>
      <div
        className="flex items-center justify-between"
        style={{ marginTop: "auto" }}
      >
        <select
          className="control-select"
          value={val}
          onChange={(e) => setVal(e.target.value)}
        >
          {options.map((opt: string) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
        <ChevronDown size={16} color="#B3B3B3" />
      </div>
    </div>
  );
}

export default function App() {
  const [country, setCountry] = useState("United States");
  const [newsFeature, setNewsFeature] = useState("Positive Emotion");
  const [musicFeature, setMusicFeature] = useState("Valence");
  const [transformType, setTransformType] = useState("Lag");
  const [lag, setLag] = useState("0d (Live)");
  const [rollingWindow, setRollingWindow] = useState("None");

  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [topPosFeatures, setTopPosFeatures] = useState([]);
  const [topNegFeatures, setTopNegFeatures] = useState([]);
  const [lagData, setLagData] = useState([]);
  const [rollingPeriodsData, setRollingPeriodsData] = useState([]);
  const [countryComparisons, setCountryComparisons] = useState([]);
  const [topSongs, setTopSongs] = useState<any[]>([]);
  const [newsExamples, setNewsExamples] = useState<any[]>([]);

  useEffect(() => {
    fetch(
      `${API_BASE}/time_series?country=${country}&news_feature=${newsFeature}&music_feature=${musicFeature}&lag=${lag}&rolling_window=${rollingWindow}`,
    )
      .then((r) => r.json())
      .then((data) => setTimeSeriesData(data))
      .catch(console.error);
  }, [country, newsFeature, musicFeature, lag, rollingWindow]);

  useEffect(() => {
    fetch(
      `${API_BASE}/correlations_top?country=${country}&news_feature=${newsFeature}`,
    )
      .then((r) => r.json())
      .then((data) => {
        const positives = data.pos || [];
        setTopPosFeatures(positives);
        setTopNegFeatures(data.neg || []);

        // Default to the most positively correlated feature
        if (positives.length > 0 && positives[0].name) {
          setMusicFeature(positives[0].name);
        }
      })
      .catch(console.error);
  }, [country, newsFeature]);

  useEffect(() => {
    fetch(
      `${API_BASE}/lag_effect?country=${country}&news_feature=${newsFeature}&music_feature=${musicFeature}`,
    )
      .then((r) => r.json())
      .then((data) => setLagData(data))
      .catch(console.error);
  }, [country, newsFeature, musicFeature]);

  useEffect(() => {
    fetch(
      `${API_BASE}/rolling_effect?country=${country}&news_feature=${newsFeature}&music_feature=${musicFeature}`,
    )
      .then((r) => r.json())
      .then((data) => setRollingPeriodsData(data))
      .catch(console.error);
  }, [country, newsFeature, musicFeature]);

  useEffect(() => {
    fetch(
      `${API_BASE}/country_comparisons?news_feature=${newsFeature}&music_feature=${musicFeature}`,
    )
      .then((r) => r.json())
      .then((data) => setCountryComparisons(data))
      .catch(console.error);
  }, [newsFeature, musicFeature]);

  useEffect(() => {
    fetch(`${API_BASE}/top_songs?music_feature=${musicFeature}`)
      .then((r) => r.json())
      .then((data) => setTopSongs(data))
      .catch(console.error);
  }, [musicFeature]);

  useEffect(() => {
    fetch(`${API_BASE}/news_examples?news_feature=${newsFeature}`)
      .then(r => r.json())
      .then(data => setNewsExamples(data))
      .catch(console.error);
  }, [newsFeature]);

  // Statistics Calculation
  const stats = (() => {
    if (timeSeriesData.length < 2)
      return {
        pearson: "...",
        r2: "...",
        n: 0,
        pValSign: "...",
        strictSign: "...",
      };

    const n = timeSeriesData.length;
    const x = timeSeriesData.map((d: any) => d.newsSentiment);
    const y = timeSeriesData.map((d: any) => d.musicFeature);

    const sumX = x.reduce((a, b) => a + b, 0);
    const sumY = y.reduce((a, b) => a + b, 0);
    const sumXY = x.reduce((sum, v, i) => sum + v * y[i], 0);
    const sumX2 = x.reduce((sum, v) => sum + v * v, 0);
    const sumY2 = y.reduce((sum, v) => sum + v * v, 0);

    const num = n * sumXY - sumX * sumY;
    const den = Math.sqrt(
      (n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY),
    );

    const trueN = 4 * 365; // 4 years of daily data used for the correlation

    if (den === 0)
      return {
        pearson: "0.00",
        r2: "0.00",
        n: trueN,
        pValSign: "No",
        strictSign: "No",
      };

    const r = num / den;
    const tStat = (Math.abs(r) * Math.sqrt(trueN - 2)) / Math.sqrt(1 - r * r);
    const pValSign = tStat > 1.96 ? "Yes" : "No";
    const strictSign = tStat > 3.48 ? "Yes" : "No";

    return {
      pearson: r.toFixed(3),
      r2: (r * r).toFixed(3),
      n: trueN,
      pValSign,
      strictSign,
    };
  })();

  const countryOptions = [
    "United States",
    "Canada",
    "United Kingdom",
    "Ireland",
    "Australia",
    "New Zealand",
  ];
  const newsEmotionOptions = [
    "Positive Emotion",
    "Negative Emotion",
    "General Tone",
    "Positive Tone",
    "Negative Tone",
  ];
  const musicFeatureOptions = [
    "Valence",
    "Energy",
    "Danceability",
    "Acoustics",
    "Tempo",
    "Liveliness",
    "Joy",
    "Sadness",
    "Fear",
    "Anger",
    "Trust",
    "Anticipation",
    "Surprise",
    "Disgust",
    "Celebrate",
    "Fun",
    "Nostalgia",
    "Explore",
    "Desire",
    "Love",
    "Thug",
    "Hope",
  ];

  const lagOptions = [
    "0d (Live)",
    "1d News Lag",
    "2d News Lag",
    "1d Music Lag",
    "2d Music Lag",
  ];
  const rollingOptions = [
    "None",
    "3d Rolling",
    "1w Rolling",
    "2w Rolling",
    "1m Rolling",
  ];

  return (
    <div className="flex flex-col gap-6">
      {/* HEADER */}
      <header className="ds-header flex justify-between items-center">
        <div>
          <h1>Impact of Global News Sentiment on Music</h1>
          <p>
            Exploring how news features influence music mood and streaming
            trends across countries.
          </p>
        </div>
      </header>

      {/* GLOBAL CONTROLS */}
      <div className="controls-bar" style={{ marginBottom: "1rem" }}>
        <Dropdown
          label="Country"
          options={countryOptions}
          val={country}
          setVal={setCountry}
          icon={Globe}
        />
        <Dropdown
          label="News Emotion"
          options={newsEmotionOptions}
          val={newsFeature}
          setVal={setNewsFeature}
          icon={Smile}
        />
      </div>

      {/* TOP CORRELATION TABLES */}
      <div className="grid grid-cols-2 gap-4">
        <div className="card">
          <div className="chart-header" style={{ marginBottom: "1rem" }}>
            <div>
              <div className="chart-title">
                Most Positively Correlated Features
              </div>
              <div className="chart-subtitle">
                Relative to {newsFeature} in {country}
              </div>
            </div>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="data-table" style={{ marginTop: 0 }}>
              <thead>
                <tr>
                  <th>Music Feature</th>
                  <th>Correlation</th>
                  <th>P-Value</th>
                </tr>
              </thead>
              <tbody>
                {topPosFeatures.map((f: any, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600 }}>{f.name}</td>
                    <td className="text-green" style={{ fontWeight: 700 }}>
                      +{f.val.toFixed(2)}
                    </td>
                    <td style={{ color: "#B3B3B3" }}>{f.pval}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="chart-header" style={{ marginBottom: "1rem" }}>
            <div>
              <div className="chart-title">
                Most Negatively Correlated Features
              </div>
              <div className="chart-subtitle">
                Relative to {newsFeature} in {country}
              </div>
            </div>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="data-table" style={{ marginTop: 0 }}>
              <thead>
                <tr>
                  <th>Music Feature</th>
                  <th>Correlation</th>
                  <th>P-Value</th>
                </tr>
              </thead>
              <tbody>
                {topNegFeatures.map((f: any, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600 }}>{f.name}</td>
                    <td className="text-red" style={{ fontWeight: 700 }}>
                      {f.val.toFixed(2)}
                    </td>
                    <td style={{ color: "#B3B3B3" }}>{f.pval}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* MAIN CHART SECTION */}
      <div className="main-chart-container" style={{ marginTop: "1rem" }}>
        <div
          className="card"
          style={{ display: "flex", flexDirection: "column" }}
        >
          <div
            className="chart-header"
            style={{
              borderBottom: "1px solid var(--border-color)",
              paddingBottom: "1.5rem",
              marginBottom: "1.5rem",
            }}
          >
            <div>
              <div className="chart-title">Time Series Analysis</div>
              <div className="chart-subtitle">
                Z-Score Normalized Sentiment vs Music Feature
              </div>
            </div>
          </div>

          {/* Time Series Specific Controls */}
          <div className="controls-bar" style={{ marginBottom: "1.5rem" }}>
            <Dropdown
              label="Target Music Feature"
              options={musicFeatureOptions}
              val={musicFeature}
              setVal={setMusicFeature}
              icon={Music}
            />
            <Dropdown
              label="Analysis Mode"
              options={["Lag", "News Rolling Window"]}
              val={transformType}
              setVal={(v: string) => {
                setTransformType(v);
                if (v === "Lag") setRollingWindow("None");
                else setLag("0d (Live)");
              }}
              icon={Settings}
            />
            {transformType === "Lag" ? (
              <Dropdown
                label="Lag Offset"
                options={lagOptions}
                val={lag}
                setVal={setLag}
                icon={Clock}
              />
            ) : (
              <Dropdown
                label="Rolling Period"
                options={rollingOptions}
                val={rollingWindow}
                setVal={setRollingWindow}
                icon={Activity}
              />
            )}
          </div>

          <div className="flex gap-4 mb-4 justify-end">
            <div className="flex items-center gap-2">
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: "#1DB954",
                }}
              ></div>{" "}
              <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>
                NEWS SENTIMENT
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: "#fff",
                }}
              ></div>{" "}
              <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>
                MUSIC FEATURE
              </span>
            </div>
          </div>
          <div style={{ width: "100%", height: 350, marginTop: "auto" }}>
            <ResponsiveContainer>
              <LineChart data={timeSeriesData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#333"
                  vertical={false}
                />
                <XAxis
                  dataKey="date"
                  stroke="#B3B3B3"
                  tick={{ fontSize: 12 }}
                />
                <YAxis
                  stroke="#B3B3B3"
                  tick={{ fontSize: 12 }}
                  allowDecimals={false}
                />
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: "#181818",
                    borderColor: "#333",
                    borderRadius: 8,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="newsSentiment"
                  stroke="#1DB954"
                  strokeWidth={3}
                  dot={false}
                  activeDot={{ r: 8 }}
                />
                <Line
                  type="monotone"
                  dataKey="musicFeature"
                  stroke="#fff"
                  strokeWidth={3}
                  strokeDasharray="5 5"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="chart-title flex justify-between">
            Statistical Summary
          </div>
          <div className="stats-list">
            <div className="stats-item">
              <span className="stats-label">Sample Size (n)</span>
              <span className="stats-val">{stats.n} days</span>
            </div>
            <div className="stats-item">
              <span className="stats-label">R-Squared Value</span>
              <span className="stats-val">{stats.r2}</span>
            </div>
            <div className="stats-item">
              <span className="stats-label">Pearson Corr.</span>
              <span className="stats-val">{stats.pearson}</span>
            </div>
            <div className="stats-item">
              <span className="stats-label">
                Statistically Significant (p&lt;0.05)
              </span>
              <span
                className={`stats-val ${stats.pValSign === "Yes" ? "text-green" : "text-red"}`}
              >
                {stats.pValSign}
              </span>
            </div>
            <div className="stats-item">
              <span className="stats-label">
                Strict Multi-Hypothesis (p&lt;0.0005)
              </span>
              <span
                className={`stats-val ${stats.strictSign === "Yes" ? "text-green" : "text-red"}`}
              >
                {stats.strictSign}
              </span>
            </div>
            <div className="stats-item" style={{ borderBottom: "none" }}>
              <span className="stats-label">
                Autocorrelation (HAC) Corrected
              </span>
              <span className="stats-val">Yes</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="card">
          <div className="chart-title mb-4">Lead / Lag Effect of News</div>
          <div className="chart-subtitle mb-4">
            Correlation scores over different lags
          </div>
          <div style={{ width: "100%", height: 200 }}>
            <ResponsiveContainer>
              <BarChart data={lagData} margin={{ left: -20 }}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#333"
                  vertical={false}
                />
                <YAxis
                  stroke="#B3B3B3"
                  tick={{ fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={50}
                />
                <XAxis
                  dataKey="lag"
                  stroke="#B3B3B3"
                  tick={{ fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <RechartsTooltip
                  cursor={{ fill: "#282828" }}
                  contentStyle={{
                    backgroundColor: "#181818",
                    borderColor: "#333",
                    borderRadius: 8,
                  }}
                />
                <Bar dataKey="val" fill="#1DB954" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div
            style={{
              textAlign: "center",
              fontSize: "0.8rem",
              color: "#B3B3B3",
              marginTop: "0.5rem",
            }}
          >
            Strongest impact observed 0-24 hours post-event
          </div>
        </div>

        <div className="card">
          <div className="chart-title mb-4">Correlation by Rolling Period</div>
          <div className="chart-subtitle mb-4">
            Impact of different rolling window sizes
          </div>
          <div style={{ width: "100%", height: 200 }}>
            <ResponsiveContainer>
              <LineChart data={rollingPeriodsData} margin={{ left: -20 }}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#333"
                  vertical={false}
                />
                <YAxis
                  stroke="#B3B3B3"
                  tick={{ fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={50}
                />
                <XAxis
                  dataKey="period"
                  stroke="#B3B3B3"
                  tick={{ fontSize: 12 }}
                />
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: "#181818",
                    borderColor: "#333",
                    borderRadius: 8,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="corr"
                  stroke="#1DB954"
                  strokeWidth={3}
                  dot={{ r: 4, fill: "#1DB954" }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="chart-title mb-4">
            Country Comparison Visualization
          </div>
          <div style={{ width: "100%", height: 230 }}>
            <ResponsiveContainer>
              <BarChart
                data={countryComparisons.slice(0, 7)}
                layout="vertical"
                margin={{ left: 10, right: 10, bottom: 0, top: 0 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#333"
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  stroke="#B3B3B3"
                  tick={{ fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  dataKey="name"
                  type="category"
                  stroke="#B3B3B3"
                  tick={{ fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={90}
                />
                <RechartsTooltip
                  cursor={{ fill: "#282828" }}
                  contentStyle={{
                    backgroundColor: "#181818",
                    borderColor: "#333",
                    borderRadius: 8,
                  }}
                />
                <Bar dataKey="corr" radius={[0, 4, 4, 0]} barSize={15}>
                  {countryComparisons
                    .slice(0, 7)
                    .map((entry: any, index: number) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.corr > 0 ? "#1DB954" : "#E22134"}
                      />
                    ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* TABLES */}
      <div className="grid grid-cols-2 gap-4">
        <div className="card">
          <div className="chart-header">
            <div className="chart-title flex gap-2 items-center">
              <FileText size={20} color="#1DB954" /> Example News Events
            </div>
          </div>
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Country</th>
                  <th>Event Snippet</th>
                  <th>Event Type</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {newsExamples && Array.isArray(newsExamples) && newsExamples.length > 0 ? newsExamples.map((n, i) => (
                  <tr key={i}>
                    <td style={{color: '#B3B3B3', fontSize: '0.9rem'}}>{n.date}</td>
                    <td style={{fontSize: '0.9rem'}}>{n.country}</td>
                    <td style={{fontWeight: 500}}>{n.event}</td>
                    <td style={{color: '#B3B3B3', fontSize: '0.9rem'}}>{n.type}</td>
                    <td className={n.score > 0 ? "text-green" : "text-red"} style={{fontWeight: 600}}>
                      {n.score > 0 ? '+' : ''}{typeof n.score === 'number' ? n.score.toFixed(2) : '-'}
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={5} style={{textAlign: 'center', color: '#B3B3B3'}}>No news data available for this filter</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="chart-header">
            <div className="chart-title flex gap-2 items-center">
              <Music size={20} color="#1DB954" /> Example Tracks for{" "}
              {musicFeature}
            </div>
          </div>
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Track</th>
                  <th>Artist</th>
                </tr>
              </thead>
              <tbody>
                {topSongs && Array.isArray(topSongs) && topSongs.length > 0 ? (
                  topSongs.map((s, i) => (
                    <tr key={i}>
                      <td style={{ color: "#B3B3B3", fontWeight: 600 }}>
                        #{s.rank}
                      </td>
                      <td style={{ fontWeight: 600 }}>{s.track}</td>
                      <td style={{ color: "#B3B3B3", fontSize: "0.9rem" }}>
                        {s.artist}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td
                      colSpan={3}
                      style={{ textAlign: "center", color: "#B3B3B3" }}
                    >
                      No data available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
