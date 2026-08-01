# 04 Recommender System Web Application

This module encompasses the code for a web application designed to showcase the integration of a Knowledge Graph-based Recommender Engine with an interactive web interface and an intelligent AI Tourism Assistant (**Graph RAG Agent**).

## Core Modules Overview

The module consists of several primary Python scripts:

### app.py
Serves as the core web application using Flask. It manages database interactions with Neo4j, user session management, and provides the real-time Server-Sent Events (SSE) Streaming Chat API (`/api/chat`).

### rag_agent.py
Implements the **Graph RAG Agent** - an intelligent travel assistant combining Neo4j Knowledge Graph entity retrieval with Local LLMs (supporting both Python Transformers and Ollama API). Key capabilities include:
- **Accurate Intent & Region Extraction**: Uses Unicode word boundary regex (`(?<!\w)...(?!\w)`) to prevent substring mismatch (e.g., District 1 matching inside District 10).
- **Personalized Recommendation Hybrid Integration**: Merges graph recommendation algorithms (`recommender.py`) with user query filters.
- **Real-Time SSE Token Streaming**: Streams generated tokens live to the frontend interface.

### recommender.py
Defines recommendation algorithms implemented using Neo4j and Graph Data Science (GDS) library (Collaborative Filtering, Content-Based Filtering, FastRP Graph Embeddings, KNN).

### data_loader.py
Handles automatic data loading for nodes, relationships, and constraints into Neo4j from remote CSV files.

### pre_training.py
Encompasses data preparation steps, feature extraction from POI descriptions using pre-trained PhoBERT (`vinai/phobert-base-v2`), and pre-training steps for recommendation models.

### neo4j_tools.py
Contains utility functions to handle Neo4j database connections, credentials, and Cypher execution.

---

## Configuration & Usage

### 1. Configure `neo4j.ini`
Create or update `neo4j.ini` in the `04-Recommender-System-Web-App` directory:
```ini
[NEO4J]
HOST = bolt://localhost:7687
USERNAME = neo4j
DATABASE = neo4j
PASSWORD = your_password

[LOCAL_LLM]
ENABLED = true
MODE = python_transformers
URL = http://localhost:11434/api/generate
MODEL = Qwen/Qwen2.5-7B-Instruct
```

*Mode Options:*
- `python_transformers`: Loads the HuggingFace model directly within the Python process via PyTorch.
- `ollama`: Connects to an external Ollama local server HTTP API (`http://localhost:11434`).

### 2. Run the Application
Execute the following command:
```bash
python app.py
```

- If running on an empty Neo4j database, initial data loading and pre-training will take **5 to 10 minutes**.
- Once ready, access the web app in your browser at `http://127.0.0.1:5000`.

---

## Dependencies

- `Python 3.x`
- `Flask`
- `neo4j`
- `graphdatascience`
- `pandas`
- `scikit-learn`
- `py2neo`
- `torch` (Deep Learning backend for PyTorch)
- `transformers` (For HuggingFace LLMs and PhoBERT embeddings)
- `pyvi` (Vietnamese text segmentation)

---

## Contributors & License

- **Author**: Xiong Ying
- **License**: [MIT License](LICENSE).