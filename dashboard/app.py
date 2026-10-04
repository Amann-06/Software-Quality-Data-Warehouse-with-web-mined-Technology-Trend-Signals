import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import (
    PROCESSED_DATA_DIR,
    WAREHOUSE_DB_PATH,
    WAREHOUSE_DB_URI,
    PARENT_CATEGORY,
    TECHNOLOGY_TAXONOMY,
)
from src.etl.load import run_etl_pipeline
from src.warehouse.queries import (
    olap_rollup,
    olap_drilldown,
    olap_slice,
    olap_dice,
    olap_pivot,
)
from src.mining.text_mining import (
    extract_top_keywords,
    extract_keywords_by_category,
    get_taxonomy_tree,
)
from src.mining.clustering import cluster_text
from src.mining.association_rules import (
    mine_technology_associations,
    mine_event_episode_rules,
)
from src.mining.time_series import (
    compute_hourly_activity,
    compute_event_type_series,
    compute_trend_summary,
)
from src.mining.graph_mining import (
    build_developer_repo_graph,
    compute_network_metrics,
    get_node_table,
)

# Page Configuration
st.set_page_config(
    page_title="Software Quality DW & Mining",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (Dark Glassmorphic UI)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
    }
    
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    .metric-title {
        font-size: 0.85rem;
        color: #94a3b8;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #f8fafc;
        margin-top: 4px;
    }
    .metric-subtitle {
        font-size: 0.75rem;
        color: #38bdf8;
        margin-top: 2px;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #0f172a;
        padding: 8px;
        border-radius: 12px;
        border: 1px solid #1e293b;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 8px;
        color: #94a3b8;
        font-size: 0.88rem;
        font-weight: 500;
        padding: 0 16px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important;
        color: #ffffff !important;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner="Loading data warehouse...")
def load_data():
    parquet_path = PROCESSED_DATA_DIR / "processed_events.parquet"
    if not parquet_path.exists() or not WAREHOUSE_DB_PATH.exists():
        run_etl_pipeline()
    df = pd.read_parquet(parquet_path)
    df["created_at_dt"] = pd.to_datetime(df["created_at"], utc=True)
    return df

@st.cache_resource
def get_warehouse_engine():
    return create_engine(WAREHOUSE_DB_URI)

# Load data and engine
df_all = load_data()
engine = get_warehouse_engine()

# Sidebar Navigation and Filters
with st.sidebar:
    st.markdown("### ⚡ Quality DW & Mining")
    st.caption("College Module 5 Reference Implementation")
    st.divider()

    st.markdown("#### 🎯 Filters")
    all_categories = sorted(df_all["technology_category"].unique().tolist())
    selected_categories = st.multiselect(
        "Technology Category",
        options=all_categories,
        default=all_categories
    )

    all_events = sorted(df_all["event_type"].unique().tolist())
    selected_events = st.multiselect(
        "Event Type",
        options=all_events,
        default=all_events
    )

    dev_filter = st.radio(
        "Developer Type",
        options=["All Contributors", "Human Developers Only", "Bots Only"],
        index=0
    )

    hours_available = sorted(df_all["hour"].unique().tolist())
    if len(hours_available) > 1:
        min_hour, max_hour = min(hours_available), max(hours_available)
        selected_hours = st.slider("Hour of Day (UTC)", min_value=min_hour, max_value=max_hour, value=(min_hour, max_hour))
    else:
        selected_hours = (hours_available[0], hours_available[0])

    search_query = st.text_input("Search Repository / Dev", placeholder="e.g. docker, react, abhiyerra")
    st.divider()
    st.caption("📦 50K GitHub Archive Dataset")

# Apply Filters
filtered_df = df_all[
    (df_all["technology_category"].isin(selected_categories)) &
    (df_all["event_type"].isin(selected_events)) &
    (df_all["hour"].between(selected_hours[0], selected_hours[1]))
]

if dev_filter == "Human Developers Only":
    filtered_df = filtered_df[filtered_df["is_bot"] == 0]
elif dev_filter == "Bots Only":
    filtered_df = filtered_df[filtered_df["is_bot"] == 1]

if search_query:
    q = search_query.strip().lower()
    filtered_df = filtered_df[
        filtered_df["repository"].str.lower().str.contains(q) |
        filtered_df["developer"].str.lower().str.contains(q)
    ]

# Header Title
st.title("Software Quality Data Warehouse with Web-Mined Tech Trend Signals")
st.markdown(
    "Analytical intelligence platform combining **Star-Schema OLAP Data Warehousing**, "
    "**Web/Text Mining**, **Unsupervised Clustering**, **Episode/Association Rules**, "
    "**Time-Series Trends**, and **Graph Network Mining** on real-world GitHub Archive activity."
)

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🏛️ Summary & KPIs",
    "🧊 OLAP Cube",
    "🛡️ Quality & Defects",
    "🌐 Web & Text Mining",
    "🧩 Clustering",
    "🔗 Association Rules",
    "📈 Time Series",
    "🕸️ Graph Mining",
    "💾 Schema & Export",
])

# ----------------- TAB 1: SUMMARY & KPIS -----------------
with tab1:
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Filtered Events</div>
            <div class="metric-value">{len(filtered_df):,}</div>
            <div class="metric-subtitle">{round(len(filtered_df)/len(df_all)*100, 1)}% of warehouse</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Active Repositories</div>
            <div class="metric-value">{filtered_df['repository'].nunique():,}</div>
            <div class="metric-subtitle">Across {filtered_df['repo_owner'].nunique():,} owners</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Active Developers</div>
            <div class="metric-value">{filtered_df['developer'].nunique():,}</div>
            <div class="metric-subtitle">{filtered_df[filtered_df['is_bot'] == 1]['developer'].nunique():,} bots identified</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        defect_count = filtered_df['is_defect_proxy'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Quality / Defect Proxies</div>
            <div class="metric-value">{defect_count:,}</div>
            <div class="metric-subtitle">{round(defect_count/max(len(filtered_df), 1)*100, 1)}% issue density</div>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        top_cat = filtered_df['technology_category'].value_counts().index[0] if not filtered_df.empty else "N/A"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Dominant Category</div>
            <div class="metric-value" style="font-size: 1.4rem;">{top_cat}</div>
            <div class="metric-subtitle">{filtered_df['primary_technology'].nunique()} derived tech signals</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    c_left, c_right = st.columns([1, 1])
    with c_left:
        st.subheader("Event Type Distribution")
        if not filtered_df.empty:
            event_counts = filtered_df["event_type"].value_counts().reset_index()
            event_counts.columns = ["Event Type", "Count"]
            fig_event = px.pie(
                event_counts,
                names="Event Type",
                values="Count",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Prism,
            )
            fig_event.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                margin=dict(t=20, b=20, l=20, r=20),
            )
            st.plotly_chart(fig_event, use_container_width=True)
        else:
            st.info("No events match current filter settings.")

    with c_right:
        st.subheader("Technology Category Breakdown")
        if not filtered_df.empty:
            cat_counts = filtered_df["technology_category"].value_counts().reset_index()
            cat_counts.columns = ["Category", "Events"]
            fig_cat = px.bar(
                cat_counts,
                x="Category",
                y="Events",
                color="Category",
                color_discrete_sequence=px.colors.qualitative.Safe,
            )
            fig_cat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="#1e293b"),
                margin=dict(t=20, b=20, l=20, r=20),
                showlegend=False,
            )
            st.plotly_chart(fig_cat, use_container_width=True)

    r_left, r_right = st.columns([1, 1])
    with r_left:
        st.subheader("Top Repositories by Activity")
        if not filtered_df.empty:
            top_repos = filtered_df["repository"].value_counts().head(10).reset_index()
            top_repos.columns = ["Repository", "Activity Count"]
            st.dataframe(top_repos, use_container_width=True, hide_index=True)
    with r_right:
        st.subheader("Top Contributors by Activity")
        if not filtered_df.empty:
            top_devs = filtered_df.groupby(["developer", "is_bot"]).size().reset_index(name="Events")
            top_devs["Type"] = np.where(top_devs["is_bot"] == 1, "🤖 Bot", "👤 Human")
            top_devs = top_devs.sort_values(by="Events", ascending=False).head(10)
            st.dataframe(top_devs[["developer", "Type", "Events"]], use_container_width=True, hide_index=True)

# ----------------- TAB 2: OLAP CUBE -----------------
with tab2:
    st.header("🧊 Multi-Dimensional OLAP Operations")
    st.markdown(
        "Demonstrating core Data Warehousing OLAP primitives directly backed by SQL queries on the star schema."
    )

    olap_choice = st.radio(
        "Choose OLAP Operation",
        options=["Roll-up (Hierarchy Aggregation)", "Drill-down (Hour & Action Decomposition)", "Slice (1-D Filter)", "Dice (Multi-D Range)", "Pivot Matrix (Cross-Tabulation)"],
        horizontal=True
    )

    if "Roll-up" in olap_choice:
        st.subheader("Roll-up Operation: Time Hierarchy Aggregation")
        st.markdown("Aggregates activity metrics moving up the temporal dimension hierarchy: `Hour -> Date -> Week -> Month`.")
        roll_level = st.selectbox("Roll-up Grouping Level", options=["hour", "day", "week", "month"], index=0)
        df_roll = olap_rollup(engine, group_by=roll_level)
        st.dataframe(df_roll, use_container_width=True)

    elif "Drill-down" in olap_choice:
        st.subheader("Drill-down Operation: Hour & Event Decomposition")
        drill_date = st.selectbox("Select Target Date", options=["2026-09-01"], index=0)
        drill_hours = sorted(df_all["hour"].unique().tolist())
        target_h = st.selectbox("Drill into Specific Hour (Optional)", options=[None] + drill_hours)
        df_drill = olap_drilldown(engine, target_date=drill_date, target_hour=target_h)
        st.dataframe(df_drill, use_container_width=True)

    elif "Slice" in olap_choice:
        st.subheader("Slice Operation: 1-Dimensional Filter")
        dim_slice = st.selectbox("Slice Dimension", options=["event_type", "category", "developer", "repository"])
        if dim_slice == "event_type":
            val_options = sorted(df_all["event_type"].unique().tolist())
        elif dim_slice == "category":
            val_options = sorted(df_all["technology_category"].unique().tolist())
        else:
            val_options = df_all[dim_slice].value_counts().head(20).index.tolist()
        slice_val = st.selectbox("Slice Value", options=val_options)
        df_slice_res = olap_slice(engine, dimension=dim_slice, value=slice_val)
        st.dataframe(df_slice_res, use_container_width=True)

    elif "Dice" in olap_choice:
        st.subheader("Dice Operation: Multi-Dimensional Bounding")
        st.markdown("Constrains across multiple dimensions simultaneously (Event Types + Technology Categories + Hour Window).")
        d_events = st.multiselect("Dicing Events", options=all_events, default=["PullRequestEvent", "IssuesEvent"])
        d_cats = st.multiselect("Dicing Categories", options=all_categories, default=["DevOps", "Web"])
        df_dice_res = olap_dice(engine, event_types=d_events, categories=d_cats)
        st.dataframe(df_dice_res, use_container_width=True)

    elif "Pivot" in olap_choice:
        st.subheader("Pivot Operation: 2-Way Cross-Tabulation Matrix")
        row_dim = st.selectbox("Row Dimension", options=["category", "hour", "developer_type"], index=0)
        col_dim = st.selectbox("Column Dimension", options=["event_type", "developer_type", "hour"], index=0)
        df_piv = olap_pivot(engine, row_dimension=row_dim, column_dimension=col_dim)
        st.dataframe(df_piv, use_container_width=True)

        if not df_piv.empty:
            fig_piv = px.imshow(
                df_piv,
                labels=dict(x=col_dim.title(), y=row_dim.title(), color="Events"),
                x=df_piv.columns.tolist(),
                y=df_piv.index.tolist(),
                color_continuous_scale="Purples",
                aspect="auto",
            )
            fig_piv.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"))
            st.plotly_chart(fig_piv, use_container_width=True)

# ----------------- TAB 3: QUALITY & DEFECTS -----------------
with tab3:
    st.header("🛡️ Software Quality & Issue Activity Proxy Analysis")
    st.caption("Addressing Module 5 defect proxy identification from issue actions, review comments, and defect keywords.")

    q_col1, q_col2, q_col3 = st.columns(3)
    with q_col1:
        st.metric("Total Issue Events", f"{len(filtered_df[filtered_df['has_issue_flag'] == 1]):,}")
    with q_col2:
        st.metric("Total Pull Request Events", f"{len(filtered_df[filtered_df['has_pr_flag'] == 1]):,}")
    with q_col3:
        st.metric("Total Issue Discussion Comments", f"{int(filtered_df['issue_comments_count'].sum()):,}")

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("Defect Proxy Concentration by Category")
        defect_by_cat = filtered_df.groupby("technology_category")["is_defect_proxy"].sum().reset_index()
        defect_by_cat.columns = ["Category", "Defect Proxies"]
        fig_def = px.bar(
            defect_by_cat,
            x="Category",
            y="Defect Proxies",
            color="Category",
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig_def.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"), showlegend=False)
        st.plotly_chart(fig_def, use_container_width=True)

    with c2:
        st.subheader("Top Repositories by Defect Proxy Volume")
        top_def_repos = filtered_df.groupby("repository")["is_defect_proxy"].sum().reset_index()
        top_def_repos = top_def_repos.sort_values(by="is_defect_proxy", ascending=False).head(10)
        top_def_repos.columns = ["Repository", "Defect Proxy Count"]
        st.dataframe(top_def_repos, use_container_width=True, hide_index=True)

    st.subheader("Extracted Unstructured Issue Titles & Comments Sample")
    issues_sample = filtered_df[filtered_df["has_issue_flag"] == 1][
        ["repository", "developer", "action", "issue_title", "issue_labels", "issue_comments_count"]
    ].head(25)
    st.dataframe(issues_sample, use_container_width=True, hide_index=True)

# ----------------- TAB 4: WEB & TEXT MINING -----------------
with tab4:
    st.header("🌐 Web Mining & Technology Signals")
    st.markdown("Category taxonomy hierarchy and Term Frequency-Inverse Document Frequency (TF-IDF) keyword extraction across 86 derived technology signals.")
    st.caption("ℹ️ Syllabus Context: GitHub Archive does not contain browser clickstream/navigation logs. The usage analysis in this system evaluates GitHub platform activity telemetry (developer actions, review workflows) rather than traditional web clickstream mining.")

    st.subheader("Hierarchy of Technology Categories")
    tree = get_taxonomy_tree()
    sunburst_data = []
    for cat in tree["children"]:
        for tech in cat["technologies"]:
            sunburst_data.append({
                "Parent": tree["name"],
                "Category": cat["name"],
                "Technology": tech,
                "Value": 1
            })
    df_sunburst = pd.DataFrame(sunburst_data)
    fig_sun = px.sunburst(
        df_sunburst,
        path=["Parent", "Category", "Technology"],
        values="Value",
        color="Category",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig_sun.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"))
    st.plotly_chart(fig_sun, use_container_width=True)

    st.divider()
    st.subheader("TF-IDF Keyword Extraction across Filtered Events")
    sample_size = min(len(filtered_df), 1500)
    if sample_size > 0:
        corpus = filtered_df["extracted_text"].dropna().sample(sample_size, random_state=42).tolist()
        top_kws = extract_top_keywords(corpus, top_n=15)
        df_kw = pd.DataFrame(top_kws, columns=["Term / Keyword", "Mean TF-IDF Score"])

        kw_col1, kw_col2 = st.columns([1, 1])
        with kw_col1:
            st.dataframe(df_kw, use_container_width=True, hide_index=True)
        with kw_col2:
            fig_kw = px.bar(
                df_kw,
                x="Mean TF-IDF Score",
                y="Term / Keyword",
                orientation="h",
                color="Mean TF-IDF Score",
                color_continuous_scale="Viridis",
            )
            fig_kw.update_layout(
                yaxis=dict(autorange="reversed"),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                showlegend=False,
            )
            st.plotly_chart(fig_kw, use_container_width=True)

# ----------------- TAB 5: CLUSTERING -----------------
with tab5:
    st.header("🧩 Unsupervised Text Clustering (K-Means)")
    st.caption("Segments unstructured event titles, comment snippets, and repo metadata using TF-IDF + KMeans.")

    k_clusters = st.slider("Select Number of Clusters (k)", min_value=2, max_value=6, value=4)
    cluster_sample_size = min(len(filtered_df), 800)

    if cluster_sample_size >= k_clusters:
        corpus = filtered_df["extracted_text"].dropna().sample(cluster_sample_size, random_state=42).tolist()
        cluster_res = cluster_text(corpus, n_clusters=k_clusters)

        if cluster_res["status"] == "success":
            c_m1, c_m2, c_m3 = st.columns(3)
            with c_m1:
                st.metric("Clusters Formed", cluster_res["n_clusters"])
            with c_m2:
                sil = cluster_res.get("silhouette_score")
                st.metric("Silhouette Score", f"{sil:.3f}" if sil is not None else "N/A")
            with c_m3:
                st.metric("Sampled Texts", cluster_sample_size)

            st.subheader("Cluster Distribution & Top Terms")
            terms_records = []
            for c_id, size in cluster_res["cluster_sizes"].items():
                terms_records.append({
                    "Cluster ID": f"Cluster {c_id}",
                    "Size": size,
                    "Percentage": f"{round(size/cluster_sample_size*100, 1)}%",
                    "Top Discriminative Terms": ", ".join(cluster_res["top_terms_per_cluster"].get(c_id, [])[:5]),
                })
            st.dataframe(pd.DataFrame(terms_records), use_container_width=True, hide_index=True)
        else:
            st.warning(f"Clustering fallback status: {cluster_res['status']}")
    else:
        st.info("Insufficient data under current filters to perform clustering.")

# ----------------- TAB 6: ASSOCIATION RULES -----------------
with tab6:
    st.header("🔗 Association & Episode Rule Discovery")
    st.caption("Discovers frequent co-occurrence patterns of technologies and event types across software repositories.")

    rule_type = st.radio("Rule Mining Target", options=["Technology Co-occurrences", "Event Episode Sequences"], horizontal=True)
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        min_supp = st.slider("Minimum Support", min_value=0.0005, max_value=0.05, value=0.001, step=0.0005, format="%.4f")
    with r_col2:
        min_conf = st.slider("Minimum Confidence", min_value=0.05, max_value=1.0, value=0.1, step=0.05)

    if rule_type == "Technology Co-occurrences":
        rules_df = mine_technology_associations(filtered_df, min_support=min_supp, min_confidence=min_conf)
    else:
        rules_df = mine_event_episode_rules(filtered_df, min_support=min_supp, min_confidence=min_conf)

    if not rules_df.empty:
        st.write(f"Discovered **{len(rules_df)} rules** meeting thresholds:")
        st.dataframe(rules_df, use_container_width=True, hide_index=True)

        fig_rules = px.scatter(
            rules_df,
            x="support",
            y="confidence",
            size="lift",
            color="lift",
            hover_data=["antecedent", "consequent"],
            color_continuous_scale="Plasma",
            labels=dict(support="Support", confidence="Confidence", lift="Lift"),
        )
        fig_rules.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"))
        st.plotly_chart(fig_rules, use_container_width=True)
    else:
        st.info("No rules found meeting the specified support and confidence thresholds. Try lowering the thresholds.")

# ----------------- TAB 7: TIME SERIES -----------------
with tab7:
    st.header("📈 Time Series Analysis & Rolling Trends")
    st.caption("Temporal decomposition of event volume, moving averages, and activity velocity.")

    hourly_df = compute_hourly_activity(filtered_df)
    if not hourly_df.empty:
        summary = compute_trend_summary(hourly_df)

        ts_c1, ts_c2, ts_c3, ts_c4 = st.columns(4)
        with ts_c1:
            st.metric("Mean Hourly Volume", f"{summary['mean_hourly_events']:,.0f}")
        with ts_c2:
            st.metric("Peak Hour", f"{str(summary['peak_hour'])[:16]}")
        with ts_c3:
            st.metric("Peak Hour Volume", f"{summary['peak_count']:,}")
        with ts_c4:
            st.metric("Overall Trend Direction", summary['trend_direction'].title())

        st.subheader("Hourly Activity with 3-Period Rolling Average")
        fig_ts = go.Figure()
        fig_ts.add_trace(go.Bar(
            x=hourly_df["time_bucket"],
            y=hourly_df["event_count"],
            name="Raw Activity",
            marker_color="rgba(99, 102, 241, 0.5)",
        ))
        fig_ts.add_trace(go.Scatter(
            x=hourly_df["time_bucket"],
            y=hourly_df["rolling_mean"],
            mode="lines+markers",
            name="Rolling Mean",
            line=dict(color="#38bdf8", width=3),
        ))
        fig_ts.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8"),
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor="#1e293b"),
        )
        st.plotly_chart(fig_ts, use_container_width=True)

        st.subheader("Event Type Composition Over Time")
        event_ts = compute_event_type_series(filtered_df)
        if not event_ts.empty:
            fig_comp = px.area(
                event_ts,
                x="time_bucket",
                y=[c for c in event_ts.columns if c != "time_bucket"],
                color_discrete_sequence=px.colors.qualitative.Prism,
            )
            fig_comp.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
            )
            st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("No time series data available for the current filter selection.")

# ----------------- TAB 8: GRAPH MINING -----------------
with tab8:
    st.header("🕸️ Graph Mining & Network Analysis")
    st.caption("Bipartite Network Analysis of Developer-Repository collaboration and Repository-Technology affiliations.")

    sample_graph_size = min(len(filtered_df), 2000)
    G = build_developer_repo_graph(filtered_df.head(sample_graph_size))
    metrics = compute_network_metrics(G)

    gm_1, gm_2, gm_3, gm_4 = st.columns(4)
    with gm_1:
        st.metric("Total Nodes", f"{metrics['num_nodes']:,}")
    with gm_2:
        st.metric("Total Edges", f"{metrics['num_edges']:,}")
    with gm_3:
        st.metric("Graph Density", f"{metrics['density']:.6f}")
    with gm_4:
        st.metric("Connected Components", metrics['connected_components'])

    st.subheader("Top Nodes by Centrality and Degree")
    node_table = get_node_table(G)
    st.dataframe(node_table.head(15), use_container_width=True, hide_index=True)

# ----------------- TAB 9: SCHEMA & EXPORT -----------------
with tab9:
    st.header("💾 Warehouse Schema Architecture & Data Export")

    st.subheader("Download Filtered Data")
    csv_bytes = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Filtered Events (CSV)",
        data=csv_bytes,
        file_name="filtered_github_events.csv",
        mime="text/csv",
    )

    st.divider()
    st.subheader("Star Schema vs. Snowflake Schema Comparison")
    st.markdown("""
| Architectural Feature | Implemented Star Schema | Documented Snowflake Schema Alternative |
| :--- | :--- | :--- |
| **Dimension Normalization** | Denormalized (1NF/2NF) for OLAP speed | Normalized (3NF) to reduce data duplication |
| **Technology Hierarchy** | `dim_technology` contains category & parent | Normalized into `dim_technology` -> `dim_category` -> `dim_parent` |
| **Repository Hierarchy** | `dim_repository` contains owner and repo name | Normalized into `dim_repository` -> `dim_owner` |
| **Query Performance** | Fast aggregations, minimal JOIN hops | Slightly more complex multi-hop JOINs |
| **Storage Overhead** | Slight attribute redundancy | Minimal storage redundancy |
    """)

    st.subheader("Database Table Previews")
    preview_table = st.selectbox(
        "Select Table to Preview",
        options=["dim_time", "dim_developer", "dim_repository", "dim_event", "dim_technology", "fact_github_activity"]
    )
    with engine.connect() as conn:
        df_preview = pd.read_sql(f"SELECT * FROM {preview_table} LIMIT 20", conn)
    st.dataframe(df_preview, use_container_width=True, hide_index=True)
