"""
Semantic relevance scoring using TF-IDF cosine similarity.
Scores each job description against a curated AI/ML job corpus.
Jobs that don't match regex patterns but score above SEMANTIC_THRESHOLD
are still included under "AI-Related (Semantic Match)".
"""
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Curated corpus that represents AI/ML roles broadly.
# The vectorizer trains on this at startup — no model download needed.
_CORPUS = [
    "machine learning engineer python tensorflow pytorch deep learning neural networks model training inference serving",
    "AI engineer artificial intelligence model deployment production MLOps kubernetes docker CI/CD",
    "data scientist statistical modeling predictive analytics regression classification clustering feature engineering",
    "NLP engineer natural language processing text classification sentiment analysis BERT GPT transformer fine-tuning",
    "MLOps engineer model deployment CI/CD kubeflow mlflow sagemaker vertex ai model registry pipeline automation",
    "generative AI engineer large language models LLM fine-tuning prompt engineering RAG chat application",
    "GenAI developer generative AI GPT-4 Claude Gemini chatbot conversational AI assistant",
    "data engineer ETL pipeline Apache Spark BigQuery Snowflake data warehouse cloud Databricks dbt",
    "computer vision engineer image recognition object detection CNN YOLO OpenCV PyTorch segmentation",
    "LLM engineer language model GPT Claude Llama fine-tuning RLHF retrieval augmented generation vector database",
    "AI architect solution architect machine learning platform design scalable distributed systems",
    "RAG developer retrieval augmented generation vector database embeddings pinecone weaviate chroma semantic search",
    "prompt engineer prompt optimization chain of thought few-shot LLM interaction evaluation",
    "deep learning researcher transformer architecture attention mechanism BERT GPT self-supervised learning",
    "cloud AI engineer GCP AWS Azure machine learning services vertex AI sagemaker bedrock",
    "Python developer AI machine learning pandas numpy scikit-learn FastAPI Django REST API",
    "data analyst SQL business intelligence visualization Tableau Power BI metrics dashboards reporting",
    "Azure OpenAI developer cognitive services bot framework Azure AI Foundry copilot studio",
    "vector database engineer pinecone weaviate chroma qdrant milvus embeddings similarity search ANN",
    "agentic AI developer autonomous agents multi-agent systems LangChain AutoGen CrewAI orchestration tools",
    "foundation model engineer pretraining fine-tuning RLHF reinforcement learning from human feedback",
    "multimodal AI engineer vision language model image text audio generation diffusion stable diffusion",
    "AI product engineer full stack AI application backend inference pipeline API deployment",
    "MLOps platform engineer model monitoring drift detection A/B testing feature store",
    "robotics AI engineer reinforcement learning ROS simulation autonomous systems perception planning",
    "speech AI engineer ASR TTS speech recognition text to speech Whisper audio processing NLP",
    "recommendation system engineer collaborative filtering matrix factorization ranking retrieval",
    "knowledge graph engineer ontology RDF SPARQL entity extraction relation classification",
    "AI safety researcher alignment interpretability RLHF red-teaming evaluation robustness",
    "quantitative analyst machine learning finance trading signal generation time series forecasting",
    "bioinformatics AI scientist genomics protein structure prediction AlphaFold deep learning biology",
    "AI infrastructure engineer GPU cluster kubernetes distributed training model serving optimization",
    "Copilot developer Microsoft 365 copilot GitHub copilot plugin extension Teams bot",
    "data platform engineer Databricks Apache Kafka Airflow streaming batch processing lakehouse",
    "synthetic data engineer data augmentation simulation generative models training data quality",
    "reinforcement learning engineer reward modeling policy optimization game AI robotics",
]

_vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    max_features=8000,
    sublinear_tf=True,
)
_corpus_matrix = _vectorizer.fit_transform(_CORPUS)

SEMANTIC_THRESHOLD = 0.10  # jobs scoring above this are kept even without regex match
AI_RELATED_LABEL   = "AI-Related (Semantic Match)"

_HTML_RE = re.compile(r"<[^>]+>")
_WS_RE   = re.compile(r"\s+")


def semantic_score(title: str, desc: str) -> float:
    """Return cosine similarity of the job to the AI/ML corpus (0–1)."""
    text = _HTML_RE.sub(" ", f"{title} {desc[:2000]}")
    text = _WS_RE.sub(" ", text).strip()
    if not text:
        return 0.0
    try:
        vec  = _vectorizer.transform([text])
        sims = cosine_similarity(vec, _corpus_matrix)
        return float(np.max(sims))
    except Exception:
        return 0.0
