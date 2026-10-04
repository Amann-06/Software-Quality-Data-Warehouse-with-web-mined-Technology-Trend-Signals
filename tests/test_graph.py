import pytest
import pandas as pd
import networkx as nx

from src.mining.graph_mining import (
    build_developer_repo_graph,
    build_repo_tech_graph,
    compute_network_metrics,
    get_node_table,
)

@pytest.fixture
def mock_graph_dataframe():
    return pd.DataFrame([
        {"developer": "dev1", "repository": "repoA", "primary_technology": "docker"},
        {"developer": "dev1", "repository": "repoB", "primary_technology": "kubernetes"},
        {"developer": "dev2", "repository": "repoA", "primary_technology": "docker"},
        {"developer": "dev3", "repository": "repoC", "primary_technology": "react"},
        {"developer": "dev1", "repository": "repoA", "primary_technology": "docker"},
    ])

def test_build_developer_repo_graph(mock_graph_dataframe):
    G = build_developer_repo_graph(mock_graph_dataframe)
    assert isinstance(G, nx.Graph)
    assert G.number_of_nodes() == 6
    assert G.number_of_edges() == 4
    # Check weight of edge dev1 - repoA (3 events)
    assert G[ "dev1" ][ "repoA" ][ "weight" ] == 2

def test_build_repo_tech_graph(mock_graph_dataframe):
    G = build_repo_tech_graph(mock_graph_dataframe)
    assert isinstance(G, nx.Graph)
    assert G.has_node("repoA")
    assert G.has_node("docker")
    assert G.has_edge("repoA", "docker")

def test_compute_network_metrics(mock_graph_dataframe):
    G = build_developer_repo_graph(mock_graph_dataframe)
    metrics = compute_network_metrics(G)
    assert metrics["num_nodes"] == 6
    assert metrics["num_edges"] == 4
    assert metrics["density"] > 0
    assert metrics["connected_components"] >= 1
    assert len(metrics["top_degree_centrality"]) > 0

def test_get_node_table(mock_graph_dataframe):
    G = build_developer_repo_graph(mock_graph_dataframe)
    table = get_node_table(G)
    assert not table.empty
    assert "node" in table.columns
    assert "node_type" in table.columns
    assert "degree" in table.columns
    assert "weighted_degree" in table.columns
    assert table.iloc[0]["node"] in ["dev1", "repoA"]

def test_empty_graph():
    empty_df = pd.DataFrame()
    G = build_developer_repo_graph(empty_df)
    assert G.number_of_nodes() == 0
    metrics = compute_network_metrics(G)
    assert metrics["num_nodes"] == 0
    table = get_node_table(G)
    assert table.empty
