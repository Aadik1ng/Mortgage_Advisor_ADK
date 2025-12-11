# 🏠 UAE Mortgage Assistant (Ramy)

**Ramy** is an Agentic AI advisor designed to help expats in the UAE navigate the complex mortgage market. Unlike generic chatbots, Ramy uses **Google ADK** (Agent Development Kit) paired with deterministic Python tools to perform accurate financial calculations, ensuring no "LLM hallucination" on numbers.

Powered by **Groq** via **LiteLLM** for ultra-fast inference.

## ✨ Key Features

- **"Buy vs. Rent" Analysis**: Intelligently calculates whether you should buy or rent based on your stay duration, collecting data conversationally.
- **Accurate Math**: Uses deterministic Python tools for EMI, Upfront Costs, and Affordability calculations.
- **UAE Specific Rules**: Built-in knowledge of UAE mortgage laws (e.g., 20% down payment for expats, LTV limits).
- **Conversational Interface**: A modern, glassmorphism-styled web UI providing a "Smart Friend" experience.
- **Fast & Responsive**: Streaming responses using Server-Sent Events (SSE).
- **Lead Capture**: Unobtrusively asks for contact details at natural stopping points.

## 🛠️ Tech Stack

- **Agent Framework**: [Google ADK](https://github.com/google/adk)
- **LLM Engine**: [LiteLLM](https://github.com/BerriAI/litellm) (configured for Groq `llama-3.3-70b`)
- **Backend API**: FastAPI + Uvicorn
- **Frontend**: Vanilla JS, HTML5, CSS3
- **Testing**: Pytest

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10 or higher
- A [Groq API Key](https://console.groq.com/keys)

### 2. Installation

Clone the repo and set up a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit the `.env` file and add your Groq API key:

```ini
GROQ_API_KEY=gsk_your_key_here
MODEL_NAME=groq/llama-3.3-70b-versatile
```

### 4. Running the Application

Start the FastAPI server (recommended):

```bash
python server.py
```

- **Web UI**: Open [http://localhost:8000](http://localhost:8000)
- **API Docs**: Open [http://localhost:8000/docs](http://localhost:8000/docs)

## 🧮 How It Works (The Tools)

The agent does not guess numbers. It delegates specific questions to these Python tools:

1.  **`tool_calculate_mortgage`**: Calculates monthly EMI, total interest, and verified upfront costs (~7% in UAE).
2.  **`tool_assess_affordability`**: Determines max budget based on income and DBR (Debt Burden Ratio) rules.
3.  **`tool_compare_buy_vs_rent`**: Runs a break-even analysis comparing total rent vs. buying costs over a specific tenure.
4.  **`tool_check_eligibility`**: Validates user eligibility (Expat/National status, age, self-employment).
5.  **`tool_get_uae_mortgage_rules`**: Provides static knowledge about current Central Bank regulations.

## 🧪 Testing

Run the test suite to verify the deterministic tools and agent configuration:

```bash
pytest mortgage_agent/tests/ -v
```

## 🐳 Deployment

### Docker

Build and run the production container:

```bash
# Build
docker build -t uae-mortgage-agent -f mortgage_agent/deployment/Dockerfile .

# Run
docker run -p 8080:8080 --env-file .env uae-mortgage-agent
```

### Google Cloud Run

Use the provided deployment script:

```bash
python mortgage_agent/deployment/deploy.py --project YOUR_PROJECT_ID
```

## � Project Structure

```text
.
├── mortgage_agent/
│   ├── agent.py            # Main ADK Agent definition
│   ├── tools.py            # Deterministic calculation logic
│   ├── prompts/            # System and user prompts
│   ├── deployment/         # Dockerfile and deploy scripts
│   └── tests/              # Unit tests
├── static/                 # Frontend assets (HTML/CSS/JS)
├── server.py               # FastAPI backend
└── requirements.txt        # Dependencies
```
