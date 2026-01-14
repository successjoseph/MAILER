# MAILER: Cloud-Native AI Email Assistant

![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)
![Model: Llama 3.3 70B](https://img.shields.io/badge/Model-Llama--3.3--70B-orange)
![Framework: FastAPI](https://img.shields.io/badge/Framework-FastAPI-green)

**MAILER** is a sophisticated, privacy-first AI agent designed to revolutionize inbox management through autonomous triaging and contextual drafting. Built as a high-intensity technical laboratory, this project explores the intersection of high-speed inference (Groq), cloud-native automation, and Large Language Model (LLM) management.

---

## I. Short Description
MAILER is a cloud-based, AI-driven automation platform designed to revolutionize inbox management through autonomous triaging and contextual drafting. Utilizing a fine-tuned **Llama-3.3-70b** model, the system executes user-defined "Manifestos" to respond to correspondence in real-time, providing users with high-level summaries and an interactive AI interface for seamless oversight.

## II. Comprehensive Purpose
The primary objective of Project **MAILER** is to serve as a high-intensity technical laboratory for mastering the intersection of full-stack web engineering, cloud-native automation, and Large Language Model (LLM) orchestration. This initiative moves beyond theoretical study, challenging the team to architect a secure, production-grade web application that leverages a fine-tuned **Llama-3.3-70b-versatile** model via the **Groq API**.

By constructing **MAILER**, the team will navigate the complexities of real-time data streaming, asynchronous background processing, and secure OAuth2 integration with the Google ecosystem. The project is designed to cultivate expertise in building "Privacy-First" AI systems—utilizing **FastAPI** and **Firestore** to manage user metadata and "Manifesto" logic without the inherent risks of long-term local email storage.

---

## III. System Operations & Workflow
The operational lifecycle of **MAILER** is engineered for frictionless, autonomous execution:

1. **Authentication & Identity:** Secure login via **Firebase** to establish a unique user profile in **Firestore**.
2. **Configuration & The "Manifesto":** Users authorize Google **OAuth2** access and define their "Manifesto"—specialized instructions governing the AI's persona, tone, and response logic.
3. **Autonomous Background Execution:** A **FastAPI** background worker periodically polls the Google API to identify unread threads within a user-defined lookback window (1–7 days).
4. **Action & Logging:** Using **LangChain**, the system fetches thread context and requests a draft from **Groq**. The response is sent via **SMTP**, and a lightweight metadata summary is logged in Firestore. No full email bodies are retained.
5. **Interactive Monitoring:** Users can query the **"AI Bubble"** chat interface for real-time status updates on handled correspondence.
6. **Persistence & Reporting:** Upon returning to the app, users receive a synthesized **"Brief Report"** of all activity handled during their absence.



---

## IV. Organizational Roles & Expectations

| Role | Tech Stack | Expectations |
| :--- | :--- | :--- |
| **Project Manager** | GitHub Projects, WhatsApp | Facilitate real-time communication; manage the 30-day sprint; ensure documentation in GitHub Issues. |
| **Fullstack Developer** | HTML5, Tailwind CSS, JavaScript | Build the Landing Page, Setup Wizard, and "AI Bubble" interface; integrate with the FastAPI backend. |
| **Backend Developer** | Python, FastAPI, Google OAuth2 | Implement "Read-on-Demand" logic; manage the background scheduler for offline monitoring. |
| **AI Quality Specialist** | Groq API, LangChain, Llama-3.3-70b | Design the Summary Engine; optimize prompt chains for "Manifesto" adherence. |
| **Data Engineer** | Firestore, Google Cloud IAM | Manage secure storage of Refresh Tokens and Activity Log schemas; ensure data privacy. |
| **Automations Engineer** | Vercel, Render, GitHub Actions | Set up CI/CD pipelines; deploy frontend to Vercel and backend to Render. |

---

## V. Implementation Timeline (30-Day Sprint)

### **Week 1: Infrastructure & Authentication**
* Initialization of GitHub Projects board and WhatsApp protocols.
* Configuration of FastAPI environment and Firebase Authentication.
* Implementation of Google OAuth2 flow for Refresh Token acquisition.

### **Week 2: Core Logic & AI Integration**
* Development of "Read-on-Demand" logic via the Google API.
* Integration of Llama-3.3-70b-versatile via Groq and LangChain.
* Creation of Firestore schema for user "Manifestos."

### **Week 3: Automation & Interactive UI**
* Deployment of background workers for asynchronous drafting.
* Implementation of the Activity Logging and Summary Engine.
* Finalization of the "AI Bubble" and User Dashboard.

### **Week 4: Deployment & Validation**
* Integration of the "Absence Report" feature.
* Orchestration of CI/CD via GitHub Actions to Vercel and Render.
* Final security audit and technical post-mortem.

---

## VI. License & Attribution
* **License:** This project is licensed under the **Apache License 2.0**.
* **Model Attribution:** Utilizes **Meta Llama 3.3**, subject to the [Meta Llama 3.3 Community License](https://llama.meta.com/llama3/license/).

---

> *"The secret of change is to focus all of your energy, not on fighting the old, but on building the new."* > — **Socrates**
