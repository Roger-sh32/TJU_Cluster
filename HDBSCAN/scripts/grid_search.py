'''UMAP + HDBSCAN 超参数网格搜索脚本'''
import pandas as pd
import numpy as np
import umap
import hdbscan
from pathlib import Path
from itertools import product
from sklearn.preprocessing import StandardScaler
from hdbscan import validity
import traceback
import warnings
warnings.filterwarnings("ignore")

SCRIPT_DIR = Path(__file__).resolve().parent
HDBSCAN_ROOT = SCRIPT_DIR.parent
TABLES_DIR = HDBSCAN_ROOT / "tables"
TABLES_DIR.mkdir(exist_ok=True)

# =============================
# 1. 加载特征表 + 限幅处理
# =============================
print("Loading features...")
df = pd.read_csv(TABLES_DIR / "scene_features.csv")
df = df.select_dtypes(include=[np.number])
df = df.replace([np.inf, -np.inf], 30).fillna(0.0)

# --- 限幅：避免噪声破坏 UMAP/HDBSCAN 密度结构 ---
clip_cols = {
    "ego_max_abs_acc": 10.0,
    "ego_jerk_std": 10.0,
    "min_ttc": 30.0,
    "min_headway": 10.0
}
for col, up in clip_cols.items():
    if col in df.columns:
        df[col] = df[col].clip(0, up)

# =============================
# 2. StandardScaler 标准化
# =============================
print("Scaling features...")
scaler = StandardScaler()
X = scaler.fit_transform(df)

# =============================
# 3. 搜索空间定义
# =============================
umap_neighbors = [5, 10, 15, 30]
umap_min_dist = [0.0, 0.05, 0.1, 0.2]
umap_metrics = ['euclidean', 'manhattan', 'cosine']
umap_n_components = [5, 10]          # ★ 新特征更适合的维度搜索

hdb_min_cluster_size = [5, 10, 20, 30]
hdb_min_samples = [1, 5, 10]

# =============================
# 4. 评估函数
# =============================
def evaluate(labels, clusterer):
    """计算 cluster 数、噪声比例、persistence 稳定性"""
    unique_clusters = [c for c in set(labels) if c != -1]
    n_clusters = len(unique_clusters)
    noise_ratio = np.mean(labels == -1)

    try:
        persistence = validity.validity_index(X_umap, labels)
    except:
        persistence = 0.0

    return n_clusters, noise_ratio, persistence

# =============================
# 5. Grid Search
# =============================
results = []
total_runs = (len(umap_neighbors) * len(umap_min_dist) *
              len(umap_metrics) * len(umap_n_components) *
              len(hdb_min_cluster_size) * len(hdb_min_samples))

print(f"\nTotal search combinations: {total_runs}\n")

run_id = 0
for n_nb, md, metric, nc, mcs, ms in product(
    umap_neighbors, umap_min_dist, umap_metrics,
    umap_n_components, hdb_min_cluster_size, hdb_min_samples):

    run_id += 1
    print(f"[{run_id}/{total_runs}] Running: "
          f"UMAP(nn={n_nb}, md={md}, metric={metric}, nc={nc}) | "
          f"HDBSCAN(mcs={mcs}, ms={ms})")

    try:
        # ===== UMAP 降维 =====
        reducer = umap.UMAP(
            n_neighbors=n_nb,
            min_dist=md,
            n_components=nc,
            metric=metric,
            random_state=42
        )
        X_umap = reducer.fit_transform(X)

        # ===== HDBSCAN 聚类 =====
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=mcs,
            min_samples=ms,
            prediction_data=True
        )
        labels = clusterer.fit_predict(X_umap)

        # ===== 评估 =====
        n_clusters, noise_ratio, persistence = evaluate(labels, clusterer)

        results.append({
            'n_neighbors': n_nb,
            'min_dist': md,
            'metric': metric,
            'n_components': nc,
            'min_cluster_size': mcs,
            'min_samples': ms,
            'clusters': n_clusters,
            'noise_ratio': noise_ratio,
            'persistence': persistence
        })

        print(f"   ⇒ clusters={n_clusters}, noise={noise_ratio:.2f}, "
              f"persistence={persistence:.3f}")

    except Exception as e:
        print("   [ERROR] Failed:", e)
        traceback.print_exc()
        results.append({
            'n_neighbors': n_nb,
            'min_dist': md,
            'metric': metric,
            'n_components': nc,
            'min_cluster_size': mcs,
            'min_samples': ms,
            'clusters': -1,
            'noise_ratio': 1.0,
            'persistence': 0.0
        })
        continue

# =============================
# 6. 保存结果
# =============================
df_res = pd.DataFrame(results)
output_path = TABLES_DIR / "umap_hdbscan_grid_search.csv"
df_res.to_csv(output_path, index=False)

print("\n===== Grid Search 完成！======")
print(f"结果已保存到 {output_path}")
print(df_res.head())
