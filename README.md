# 🌿 GreenPulse AI  
## Real-Time Urban Air Quality Intelligence & Alert System

Hack For Green Bharat Hackathon Project  
Powered by **Pathway · RandomForest AI · FastAPI · Streamlit**

---

## 🚀 Overview

GreenPulse AI is a real-time, AI-driven air quality monitoring system that processes live streaming sensor data using the **Pathway framework** and automatically generates health risk predictions.

Unlike static dashboards, GreenPulse updates instantly when new data arrives.

### Key Idea


Live Data → Pathway Streaming → AI Prediction → Real-Time Dashboard


---

## 🎯 Problem Statement

Existing air quality monitoring systems suffer from:

- ❌ Delayed batch updates (15–60 minutes)
- ❌ No predictive intelligence
- ❌ No automatic alerting
- ❌ Manual refresh systems

GreenPulse AI solves this by providing:

- ⚡ Real-time streaming data processing
- 🤖 AI-based risk classification
- 🚨 Instant health alerts
- 📊 Live monitoring dashboard

---

## 🧠 Core Features

- ✅ Pathway real-time streaming pipeline
- ✅ Auto-update when new data arrives
- ✅ AI risk classification (LOW / MEDIUM / HIGH)
- ✅ FastAPI REST API endpoints
- ✅ Live Streamlit dashboard
- ✅ Real-time alerts generation

---

## 🏗️ System Architecture


IoT / Sensor Stream
↓
Pathway Streaming Engine
↓
Data Processing + AQI Calculation
↓
RandomForest AI Model
↓
FastAPI Output Layer
↓
Streamlit Dashboard


---

## ⚡ Pathway Integration (Hackathon Requirement)

GreenPulse AI uses:

```
pw.io.jsonlines.read(mode="streaming")
```
This ensures:

New data automatically triggers processing

AI inference runs instantly

Outputs update without manual refresh

✔ Fully Pathway-compliant project.

🧩 Tech Stack
- Layer	Technology
- Streaming Engine	Pathway
- AI Model	RandomForest (scikit-learn)
- Backend API	FastAPI
- Dashboard	Streamlit
- Language	Python
- Data Format	JSONL

📁 Project Structure
greenpulse_ai/
│
├── main.py
├── pathway_pipeline.py
├── ai_model.py
├── data_simulator.py
├── api_server.py
├── dashboard.py
├── requirements.txt
│
├── data/
├── models/


▶️ Installation
git clone <repo-url>
cd greenpulse_ai
pip install -r requirements.txt
▶️ Running the Project
1️⃣ Start Backend + Pathway Pipeline
python main.py
2️⃣ Start Dashboard (New Terminal)
streamlit run dashboard.py
🌍 API Endpoints
Endpoint	Description
/api/predictions	Latest AI predictions
/api/alerts	HIGH-risk alerts
/health	System health


🤖 AI Model Logic

Model: RandomForest Classifier

Input Features:

PM2.5

PM10

NO2

CO

Temperature

Humidity

Output:

LOW Risk

MEDIUM Risk

HIGH Risk



🌱 Impact

GreenPulse AI enables:

Faster health alerts

Smart city air monitoring

Real-time pollution intelligence

Better environmental decision-making

Supports Green Bharat sustainability goals.



🔥 Future Enhancements

CPCB / OpenAQ live API integration

Kafka-based distributed streaming

LSTM/Transformer forecasting

Mobile notification system

National scale deployment



👨‍💻 Team

Hack For Green Bharat Hackathon Team


⭐ Built For

Hack For Green Bharat Hackathon
Real-Time AI + Sustainability Innovation
---
