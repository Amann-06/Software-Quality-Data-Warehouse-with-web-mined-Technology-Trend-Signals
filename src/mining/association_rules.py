from typing import List, Dict, Set, Tuple, Optional
from collections import Counter
from itertools import combinations
import pandas as pd

RULE_COLUMNS = [
    "antecedent",
    "consequent",
    "support",
    "confidence",
    "lift",
    "antecedent_support",
    "consequent_support",
]

def mine_association_rules(
    transactions: List[List[str]],
    min_support: float = 0.005,
    min_confidence: float = 0.05
) -> pd.DataFrame:
    cleaned_txs = [sorted(list(set(tx))) for tx in transactions if tx]
    n_txs = len(cleaned_txs)

    if n_txs == 0:
        return pd.DataFrame(columns=RULE_COLUMNS)

    item_counts = Counter()
    for tx in cleaned_txs:
        for item in tx:
            item_counts[item] += 1

    freq_items = {
        item: count / n_txs
        for item, count in item_counts.items()
        if (count / n_txs) >= min_support
    }

    if len(freq_items) < 2:
        return pd.DataFrame(columns=RULE_COLUMNS)

    pair_counts = Counter()
    for tx in cleaned_txs:
        valid_items = [it for it in tx if it in freq_items]
        if len(valid_items) >= 2:
            for pair in combinations(valid_items, 2):
                pair_counts[pair] += 1

    rules = []
    for (item_a, item_b), count in pair_counts.items():
        pair_support = count / n_txs
        if pair_support < min_support:
            continue

        supp_a = freq_items[item_a]
        supp_b = freq_items[item_b]

        # Rule A -> B
        conf_a_b = pair_support / supp_a
        lift_a_b = conf_a_b / supp_b if supp_b > 0 else 0
        if conf_a_b >= min_confidence:
            rules.append({
                "antecedent": item_a,
                "consequent": item_b,
                "support": round(pair_support, 4),
                "confidence": round(conf_a_b, 4),
                "lift": round(lift_a_b, 4),
                "antecedent_support": round(supp_a, 4),
                "consequent_support": round(supp_b, 4),
            })

        # Rule B -> A
        conf_b_a = pair_support / supp_b
        lift_b_a = conf_b_a / supp_a if supp_a > 0 else 0
        if conf_b_a >= min_confidence:
            rules.append({
                "antecedent": item_b,
                "consequent": item_a,
                "support": round(pair_support, 4),
                "confidence": round(conf_b_a, 4),
                "lift": round(lift_b_a, 4),
                "antecedent_support": round(supp_b, 4),
                "consequent_support": round(supp_a, 4),
            })

    if not rules:
        return pd.DataFrame(columns=RULE_COLUMNS)

    df_rules = pd.DataFrame(rules).sort_values(by=["lift", "confidence"], ascending=False).reset_index(drop=True)
    return df_rules

def mine_technology_associations(
    df: pd.DataFrame,
    group_col: str = "repository",
    tech_col: str = "technologies",
    min_support: float = 0.001,
    min_confidence: float = 0.05
) -> pd.DataFrame:
    if df.empty or tech_col not in df.columns or group_col not in df.columns:
        return pd.DataFrame(columns=RULE_COLUMNS)

    transactions = []
    for _, group in df.groupby(group_col):
        items = set()
        for raw in group[tech_col].dropna():
            parts = [p.strip() for p in str(raw).split(";") if p.strip() and p.strip() != "general"]
            items.update(parts)
        if len(items) >= 2:
            transactions.append(list(items))

    if not transactions:
        return pd.DataFrame(columns=RULE_COLUMNS)

    return mine_association_rules(transactions, min_support=min_support, min_confidence=min_confidence)

def mine_event_episode_rules(
    df: pd.DataFrame,
    group_col: str = "repository",
    event_col: str = "event_type",
    min_support: float = 0.005,
    min_confidence: float = 0.05
) -> pd.DataFrame:
    if df.empty or event_col not in df.columns or group_col not in df.columns:
        return pd.DataFrame(columns=RULE_COLUMNS)

    transactions = []
    for _, group in df.groupby(group_col):
        events = group[event_col].dropna().unique().tolist()
        if len(events) >= 2:
            transactions.append(events)

    return mine_association_rules(transactions, min_support=min_support, min_confidence=min_confidence)
