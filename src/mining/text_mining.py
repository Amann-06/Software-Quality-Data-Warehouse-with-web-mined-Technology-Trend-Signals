import re
from typing import List, Dict, Tuple, Any, Optional
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from src.utils.config import TECHNOLOGY_TAXONOMY, PARENT_CATEGORY

CATEGORY_HIERARCHY = {
    PARENT_CATEGORY: list(TECHNOLOGY_TAXONOMY.keys())
}

def clean_text(text: Any) -> str:
    if pd.isna(text) or not text:
        return ""
    txt = str(text).lower()
    txt = re.sub(r"https?://\S+|www\.\S+", " ", txt)
    txt = re.sub(r"[^a-zA-Z0-9_\-\.\s]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def compute_tfidf(
    corpus: List[str],
    max_features: int = 100,
    stop_words: str = "english",
    ngram_range: Tuple[int, int] = (1, 2)
) -> Tuple[Optional[TfidfVectorizer], Any, List[str]]:
    cleaned_corpus = [clean_text(t) for t in corpus if clean_text(t)]
    if not cleaned_corpus:
        return None, None, []

    vectorizer = TfidfVectorizer(
        max_features=max_features,
        stop_words=stop_words,
        ngram_range=ngram_range,
        min_df=1
    )
    tfidf_matrix = vectorizer.fit_transform(cleaned_corpus)
    feature_names = vectorizer.get_feature_names_out().tolist()
    return vectorizer, tfidf_matrix, feature_names

def extract_top_keywords(
    corpus: List[str],
    top_n: int = 20,
    max_features: int = 200
) -> List[Tuple[str, float]]:
    vectorizer, tfidf_matrix, feature_names = compute_tfidf(corpus, max_features=max_features)
    if vectorizer is None or tfidf_matrix is None or not feature_names:
        return []

    mean_scores = np.asarray(tfidf_matrix.mean(axis=0)).flatten()
    sorted_indices = mean_scores.argsort()[::-1][:top_n]

    return [(feature_names[i], float(mean_scores[i])) for i in sorted_indices]

def extract_keywords_by_category(
    df: pd.DataFrame,
    text_col: str = "extracted_text",
    category_col: str = "technology_category",
    top_n: int = 5
) -> Dict[str, List[Tuple[str, float]]]:
    results = {}
    if df.empty or text_col not in df.columns or category_col not in df.columns:
        return results

    for category, group in df.groupby(category_col):
        corpus = group[text_col].dropna().tolist()
        keywords = extract_top_keywords(corpus, top_n=top_n)
        results[str(category)] = keywords
    return results

def get_taxonomy_tree() -> Dict[str, Any]:
    return {
        "name": PARENT_CATEGORY,
        "children": [
            {
                "name": cat,
                "technologies": techs
            }
            for cat, techs in TECHNOLOGY_TAXONOMY.items()
        ]
    }
