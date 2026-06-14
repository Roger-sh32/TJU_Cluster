'''UMAP + HDBSCAN 聚类脚本'''

import pandas as pd
import numpy as np
import umap
import hdbscan
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.preprocessing import StandardScaler

SCRIPT_DIR = Path(__file__).resolve().parent
HDBSCAN_ROOT = SCRIPT_DIR.parent
TABLES_DIR = HDBSCAN_ROOT / "tables"
PICTURES_DIR = HDBSCAN_ROOT / "pictures"
TABLES_DIR.mkdir(exist_ok=True)
PICTURES_DIR.mkdir(exist_ok=True)

# =========================
# 1. 加载特征表
# =========================
print("Loading features...")
df_raw = pd.read_csv(TABLES_DIR / "scene_features.csv")

# 只保留数值列（非常关键）
df = df_raw.select_dtypes(include=[np.number]).copy()

# 处理 inf 和 nan
df = df.replace([np.inf, -np.inf], 30.0).fillna(0.0)

# =========================
# 2. 限幅（去除噪声尖峰）
# =========================
clip_cols = {
    "ego_max_abs_acc": 10.0,
    "ego_jerk_std": 10.0,
    "min_ttc": 30.0,
    "min_headway": 10.0
}
for col, up in clip_cols.items():
    if col in df.columns:
        df[col] = df[col].clip(0, up)

# =========================
# 3. StandardScaler 标准化
# =========================
print("Scaling...")
scaler = StandardScaler()
X = scaler.fit_transform(df)

# =========================
# 4. ★ 最终聚类参数（从 grid_search 选最佳）
#    你以后可以自动替换下面的参数
# =========================
umap_best_params = dict(
    n_neighbors=15,
    min_dist=0.0,
    n_components=10,
    metric='cosine'
)

hdb_best_params = dict(
    min_cluster_size=20,
    min_samples=1
)

# =========================
# 5. UMAP 降维
# =========================
print("Running UMAP...")
umap_model = umap.UMAP(
    n_neighbors=umap_best_params["n_neighbors"],
    min_dist=umap_best_params["min_dist"],
    n_components=umap_best_params["n_components"],
    metric=umap_best_params["metric"],
    random_state=42
)
X_umap = umap_model.fit_transform(X)

# =========================
# 6. HDBSCAN 聚类
# =========================
print("Running HDBSCAN...")
clusterer = hdbscan.HDBSCAN(
    min_cluster_size=hdb_best_params["min_cluster_size"],
    min_samples=hdb_best_params["min_samples"],
    prediction_data=True
)
labels = clusterer.fit_predict(X_umap)

# =========================
# 7. 保存聚类结果
# =========================
df_out = df_raw.copy()  # 保留原始字符串列：scene_token 等
df_out["cluster"] = labels
df_out.to_csv(TABLES_DIR / "scene_features_umap_hdbscan.csv", index=False)

print("✔ 聚类完成，结果保存到 scene_features_umap_hdbscan.csv")
print("Cluster count:", len(set(labels)))


# =========================
# 8. 可视化
# =========================
plt.figure(figsize=(8, 6))
plt.scatter(X_umap[:, 0], X_umap[:, 1], c=labels, cmap="Spectral", s=12)
plt.title("UMAP + HDBSCAN Clustering")
plt.grid(True)
plt.savefig(PICTURES_DIR / "Figure_1.png", dpi=150, bbox_inches="tight")
plt.show()
