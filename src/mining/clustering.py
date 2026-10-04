from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.feature_extraction.text import TfidfVectorizer

from src.mining.text_mining import clean_text

def cluster_text(
    corpus: List[str],
    n_clusters: int = 4,
    max_features: int = 150,
    random_state: int = 42
) -> Dict[str, Any]:
    cleaned = [clean_text(t) for t in corpus]
    valid_texts = [t for t in cleaned if t]

    if not valid_texts:
        return {
            "status": "empty_corpus",
            "n_clusters": 0,
            "cluster_labels": [],
            "cluster_sizes": {},
            "top_terms_per_cluster": {},
            "silhouette_score": None,
            "terms": [],
        }

    n_samples = len(valid_texts)
    effective_clusters = min(n_clusters, n_samples)

    if effective_clusters < 2:
        return {
            "status": "insufficient_data",
            "n_clusters": 1,
            "cluster_labels": [0] * n_samples,
            "cluster_sizes": {0: n_samples},
            "top_terms_per_cluster": {0: []},
            "silhouette_score": None,
            "terms": [],
        }

    try:
        vectorizer = TfidfVectorizer(max_features=max_features, stop_words="english", min_df=1)
        tfidf_matrix = vectorizer.fit_transform(valid_texts)
        feature_names = vectorizer.get_feature_names_out()

        if len(feature_names) == 0:
            return {
                "status": "insufficient_features",
                "n_clusters": 1,
                "cluster_labels": [0] * n_samples,
                "cluster_sizes": {0: n_samples},
                "top_terms_per_cluster": {0: []},
                "silhouette_score": None,
                "terms": [],
            }

        kmeans = KMeans(n_clusters=effective_clusters, random_state=random_state, n_init=10)
        labels = kmeans.fit_predict(tfidf_matrix)

        sizes = {}
        for lbl in labels:
            sizes[int(lbl)] = sizes.get(int(lbl), 0) + 1

        order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
        top_terms = {}
        for i in range(effective_clusters):
            top_terms[i] = [feature_names[ind] for ind in order_centroids[i, :6]]

        sil_score = None
        if effective_clusters > 1 and n_samples > effective_clusters:
            try:
                sil_score = float(silhouette_score(tfidf_matrix, labels, metric="euclidean"))
            except Exception:
                sil_score = None

        return {
            "status": "success",
            "n_clusters": effective_clusters,
            "cluster_labels": labels.tolist(),
            "cluster_sizes": sizes,
            "top_terms_per_cluster": top_terms,
            "silhouette_score": sil_score,
            "terms": feature_names.tolist(),
        }
    except Exception as e:
        return {
            "status": f"error: {str(e)}",
            "n_clusters": 0,
            "cluster_labels": [],
            "cluster_sizes": {},
            "top_terms_per_cluster": {},
            "silhouette_score": None,
            "terms": [],
        }
