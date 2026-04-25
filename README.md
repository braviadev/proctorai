# ProctorAI: Context-Aware Multimodal Exam Proctoring System

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=flat&logo=flask&logoColor=white)
![Oracle](https://img.shields.io/badge/Oracle-Cloud-red)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📌 Overview
ProctorAI is an intelligent, multimodal AI system designed to ensure the integrity of remote assessments through real-time behavioral understanding. Developed initially as a Master's research project at Kwara State University, this system moves beyond simple binary "cheating" flags by leveraging environmental perception to detect disruptive sounds and unauthorized visual infractions. [https://www.bravía.com/academic-writings/dissertation/proctoring-dissertation.pdf](https://www.bravía.com/academic-writings/dissertation/proctoring-dissertation.pdf).

The core philosophy of this project is advancing **Trustworthy and Explainable AI** in education, reducing false positives, and providing context-aware anomaly detection.

## 🚀 Key Features
* **Real-Time Video Anomaly Detection:** Utilizes computer vision to monitor head pose, gaze diversion, and unauthorized persons in the frame.
* **Audio Signal Processing:** Detects anomalous background noise and secondary speech via WebRTC data streams.
* **Context-Aware Logging:** Records system-level events alongside audio-visual data for comprehensive behavioral analysis.
* **Explainable Outputs:** Rather than opaque decision-making, the system aims to provide confidence scores and contextual justifications for flagged events.

## 🏗️ System Architecture & Stack
ProctorAI operates on a decoupled architecture designed for scalability and real-time processing.

* **Backend / AI Microservice:** Python, Flask, OpenCV 
* **Frontend:** HTML/JS (Currently migrating to a **Next.js / React** architecture for enhanced state management and scalability)
* **Data Streaming:** WebRTC for low-latency audio/video transmission
* **Infrastructure:** Deployed on Oracle Cloud Infrastructure (OCI) Free Tier.
* *Note on v2 Migration:* We are actively integrating **Celery and Redis** to handle heavy, asynchronous AI inference tasks in the background, preventing frontend blocking during intensive frame analysis.

## 📚 Related Publications
The methodologies and foundational research for this repository have been published in peer-reviewed journals:
1. *An Enhanced Web-Based Examination System using Automated Proctoring and Background Activity Detection.* (JIRBDAI) *[https://www.bravía.com/academic-writings/publication/1-toyyib-et-al.pdf](https://www.bravía.com/academic-writings/publication/1-toyyib-et-al.pdf)*.
2. *Implementing an AI-Driven Proctoring System: Real-Time Detection of Disruptive Sounds and Unauthorized Visual Infractions.* (IJERD) *[https://www.bravía.com/academic-writings/publication/4-olanrewaju-et-al.pdf](https://www.bravía.com/academic-writings/publication/4-olanrewaju-et-al.pdf)*.

## 🔮 Roadmap (Future PhD Research Extension)
This repository serves as the foundation for upcoming doctoral research focused on **Multimodal Fusion and Trustworthy AI**. Planned architecture updates include:
- [ ] Implementing temporal sequence modeling (LSTM/Transformers) to analyze behavior over a 10-second sliding window rather than isolated frames.
- [ ] Integrating a dedicated explainability layer (e.g., SHAP) to generate human-readable justifications for automated flags.
- [ ] Full migration to Next.js with a Node.js signaling server.

## 💻 Local Installation & Setup
*(Provide brief instructions here on how to run your code locally. Example below:)*
```bash
# Clone the repository
git clone https://github.com/braviadev/proctorai.git

# Navigate into the directory
cd proctorai

# Install dependencies
pip install -r requirements.txt

# Run the Flask development server
python run.py
