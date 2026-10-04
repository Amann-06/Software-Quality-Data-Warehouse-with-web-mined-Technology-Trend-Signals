from typing import Dict, Any, List, Tuple, Optional
import networkx as nx
import pandas as pd

def build_developer_repo_graph(
    df: pd.DataFrame,
    dev_col: str = "developer",
    repo_col: str = "repository",
    min_edge_weight: int = 1,
    max_edges: Optional[int] = 500
) -> nx.Graph:
    G = nx.Graph()
    if df.empty or dev_col not in df.columns or repo_col not in df.columns:
        return G

    edge_counts = df.groupby([dev_col, repo_col]).size().reset_index(name="weight")
    if min_edge_weight > 1:
        edge_counts = edge_counts[edge_counts["weight"] >= min_edge_weight]

    if max_edges and len(edge_counts) > max_edges:
        edge_counts = edge_counts.sort_values(by="weight", ascending=False).head(max_edges)

    for _, row in edge_counts.iterrows():
        dev = str(row[dev_col])
        repo = str(row[repo_col])
        weight = int(row["weight"])

        if not G.has_node(dev):
            G.add_node(dev, node_type="developer")
        if not G.has_node(repo):
            G.add_node(repo, node_type="repository")

        G.add_edge(dev, repo, weight=weight)

    return G

def build_repo_tech_graph(
    df: pd.DataFrame,
    repo_col: str = "repository",
    tech_col: str = "primary_technology",
    max_edges: Optional[int] = 500
) -> nx.Graph:
    G = nx.Graph()
    if df.empty or repo_col not in df.columns or tech_col not in df.columns:
        return G

    valid = df[df[tech_col].notna() & (df[tech_col] != "general")]
    if valid.empty:
        return G

    edge_counts = valid.groupby([repo_col, tech_col]).size().reset_index(name="weight")
    if max_edges and len(edge_counts) > max_edges:
        edge_counts = edge_counts.sort_values(by="weight", ascending=False).head(max_edges)

    for _, row in edge_counts.iterrows():
        repo = str(row[repo_col])
        tech = str(row[tech_col])
        weight = int(row["weight"])

        if not G.has_node(repo):
            G.add_node(repo, node_type="repository")
        if not G.has_node(tech):
            G.add_node(tech, node_type="technology")

        G.add_edge(repo, tech, weight=weight)

    return G

def compute_network_metrics(G: nx.Graph, top_n: int = 10) -> Dict[str, Any]:
    if G.number_of_nodes() == 0:
        return {
            "num_nodes": 0,
            "num_edges": 0,
            "density": 0.0,
            "connected_components": 0,
            "largest_component_size": 0,
            "top_degree_centrality": [],
            "top_weighted_degree": [],
        }

    degree_cent = nx.degree_centrality(G)
    top_deg_cent = sorted(degree_cent.items(), key=lambda x: x[1], reverse=True)[:top_n]

    weighted_degrees = {n: sum(d.get("weight", 1) for _, _, d in G.edges(n, data=True)) for n in G.nodes()}
    top_weighted = sorted(weighted_degrees.items(), key=lambda x: x[1], reverse=True)[:top_n]

    num_components = nx.number_connected_components(G)
    largest_cc = len(max(nx.connected_components(G), key=len)) if num_components > 0 else 0

    return {
        "num_nodes": G.number_of_nodes(),
        "num_edges": G.number_of_edges(),
        "density": round(nx.density(G), 6),
        "connected_components": num_components,
        "largest_component_size": largest_cc,
        "top_degree_centrality": [(k, round(v, 4)) for k, v in top_deg_cent],
        "top_weighted_degree": top_weighted,
    }

def get_node_table(G: nx.Graph) -> pd.DataFrame:
    if G.number_of_nodes() == 0:
        return pd.DataFrame(columns=["node", "node_type", "degree", "weighted_degree"])

    records = []
    for n in G.nodes():
        node_type = G.nodes[n].get("node_type", "unknown")
        degree = G.degree(n)
        weighted_degree = sum(d.get("weight", 1) for _, _, d in G.edges(n, data=True))
        records.append({
            "node": n,
            "node_type": node_type,
            "degree": degree,
            "weighted_degree": weighted_degree,
        })

    return pd.DataFrame(records).sort_values(by="weighted_degree", ascending=False).reset_index(drop=True)
