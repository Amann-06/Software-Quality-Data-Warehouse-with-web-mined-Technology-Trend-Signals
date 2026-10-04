import pytest
import pandas as pd

from src.mining.text_mining import (
    clean_text,
    compute_tfidf,
    extract_top_keywords,
    extract_keywords_by_category,
    get_taxonomy_tree,
)
from src.mining.clustering import cluster_text
from src.mining.association_rules import (
    mine_association_rules,
    mine_technology_associations,
    mine_event_episode_rules,
)

def test_clean_text():
    assert clean_text("Fix https://github.com bug #123!") == "fix bug 123"
    assert clean_text("") == ""
    assert clean_text(None) == ""

def test_tfidf_and_keywords():
    corpus = [
        "Kubernetes deployment docker container infrastructure",
        "Docker container orchestration deployment with kubernetes",
        "React frontend UI javascript typescript web development",
        "React state management web UI frontend hooks",
    ]
    vec, mat, names = compute_tfidf(corpus, max_features=10)
    assert vec is not None
    assert mat.shape[0] == 4
    assert len(names) > 0

    top_kw = extract_top_keywords(corpus, top_n=3)
    assert len(top_kw) == 3
    assert top_kw[0][1] > 0

def test_taxonomy_tree():
    tree = get_taxonomy_tree()
    assert tree["name"] == "Software"
    assert len(tree["children"]) >= 5

def test_clustering_normal():
    corpus = [
        "Docker container deployment kubernetes cluster",
        "Kubernetes orchestration docker pod service",
        "React javascript frontend web application",
        "React components UI typescript web layout",
        "Postgres database sql query performance index",
        "Database table relational schema sql query",
    ]
    res = cluster_text(corpus, n_clusters=3)
    assert res["status"] == "success"
    assert res["n_clusters"] == 3
    assert len(res["cluster_labels"]) == 6
    assert len(res["top_terms_per_cluster"]) == 3

def test_clustering_small_controlled_dataset():
    corpus = ["Docker kubernetes", "React frontend"]
    res = cluster_text(corpus, n_clusters=2)
    assert res["status"] == "success"
    assert res["n_clusters"] == 2
    assert len(res["cluster_labels"]) == 2

def test_clustering_insufficient_data():
    single_doc = ["Only one document here"]
    res = cluster_text(single_doc, n_clusters=3)
    assert res["status"] == "insufficient_data"
    assert res["n_clusters"] == 1
    assert res["cluster_labels"] == [0]

def test_clustering_empty():
    res = cluster_text([], n_clusters=3)
    assert res["status"] == "empty_corpus"
    assert res["n_clusters"] == 0

def test_association_rules_normal():
    txs = [
        ["docker", "kubernetes", "aws"],
        ["docker", "kubernetes"],
        ["docker", "kubernetes", "terraform"],
        ["react", "typescript"],
        ["docker", "kubernetes", "aws"],
    ]
    rules = mine_association_rules(txs, min_support=0.3, min_confidence=0.5)
    assert not rules.empty
    assert "antecedent" in rules.columns
    assert "consequent" in rules.columns
    assert "support" in rules.columns
    assert "confidence" in rules.columns
    assert "lift" in rules.columns
    assert (rules["lift"] > 0).all()

def test_association_rules_insufficient_data():
    empty_rules = mine_association_rules([], min_support=0.5)
    assert empty_rules.empty
    assert list(empty_rules.columns) == [
        "antecedent", "consequent", "support", "confidence", "lift", "antecedent_support", "consequent_support"
    ]

    single_tx = [["docker"]]
    no_pair_rules = mine_association_rules(single_tx, min_support=0.5)
    assert no_pair_rules.empty
