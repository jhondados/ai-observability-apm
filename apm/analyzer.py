"""AI APM anomaly detection and root cause analysis."""
from sklearn.ensemble import IsolationForest
from langchain_google_vertexai import ChatVertexAI
from typing import List, Dict
import numpy as np
import json

class AIObservabilityEngine:
    def __init__(self):
        self.llm = ChatVertexAI(model_name="gemini-1.5-pro-002")
        self.isolation_forest = IsolationForest(contamination=0.05, random_state=42, n_estimators=200)
        self.baseline_fitted = False

    def fit_baseline(self, metrics_history: np.ndarray):
        """Fit anomaly detector on historical metrics."""
        self.isolation_forest.fit(metrics_history)
        self.baseline_fitted = True

    def detect_anomalies(self, current_metrics: np.ndarray) -> Dict:
        """Detect anomalies in current metric values."""
        if not self.baseline_fitted: return {"anomaly": False, "reason": "No baseline"}
        scores = self.isolation_forest.decision_function(current_metrics.reshape(1, -1))
        is_anomaly = self.isolation_forest.predict(current_metrics.reshape(1, -1))[0] == -1
        return {"anomaly": bool(is_anomaly), "anomaly_score": float(scores[0]),
                "severity": "critical" if scores[0] < -0.3 else "warning" if is_anomaly else "normal"}

    def root_cause_analysis(self, incident: Dict, traces: List[Dict], logs: List[str]) -> Dict:
        """LLM-powered root cause analysis."""
        traces_str = json.dumps(traces[:10], default=str)[:2000]
        logs_str = "\n".join(logs[:20])[:2000]
        prompt = f"""Analyze this production incident and identify root cause.

Incident: {json.dumps(incident)}
Traces (sample): {traces_str}
Recent logs: {logs_str}

Provide:
1. Root cause (specific, technical)
2. Contributing factors
3. Immediate mitigation steps
4. Long-term fixes
Return JSON: {{root_cause, contributing_factors: [], mitigation: [], permanent_fix: []}}"""
        resp = self.llm.invoke(prompt).content
        data = json.loads(resp.split("```json")[-1].split("```")[0] if "```" in resp else resp)
        return data

    def predict_failure(self, metrics_trend: np.ndarray, prediction_window_min: int = 30) -> Dict:
        """Predict if system will fail in next N minutes."""
        # Simple trend analysis: check if metrics moving toward anomaly threshold
        if len(metrics_trend) < 5: return {"failure_predicted": False}
        recent_scores = [self.isolation_forest.decision_function(m.reshape(1,-1))[0] for m in metrics_trend[-5:]]
        trend = np.polyfit(range(5), recent_scores, 1)[0]  # slope
        current_score = recent_scores[-1]
        predicted_score = current_score + trend * prediction_window_min / 5
        return {"failure_predicted": predicted_score < -0.3, "current_health_score": float(current_score),
                "predicted_health_score": float(predicted_score), "trend": "degrading" if trend < 0 else "stable",
                "prediction_window_min": prediction_window_min}
