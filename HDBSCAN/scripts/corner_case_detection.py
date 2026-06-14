'''计算场景的 corner case 得分的脚本'''
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler

SCRIPT_DIR = Path(__file__).resolve().parent
HDBSCAN_ROOT = SCRIPT_DIR.parent
TABLES_DIR = HDBSCAN_ROOT / "tables"
TABLES_DIR.mkdir(exist_ok=True)

# ==========================================
# 1. 加载聚类后的特征文件
# ==========================================
df = pd.read_csv(TABLES_DIR / "scene_features_umap_hdbscan.csv")

# 特征列（排除 cluster 列）
feature_cols = [c for c in df.columns if c not in ["cluster"]]

# 聚类标签
labels = df["cluster"].values
unique_clusters = sorted(df["cluster"].unique())
N = len(df)

# ==========================================
# 2. 计算簇稀有度 rarity_k
#    rarity_k = 1 - (簇大小 / 总场景数)
# ==========================================
cluster_sizes = df["cluster"].value_counts().to_dict()
rarity_map = {k: 1 - (cluster_sizes[k] / N) for k in cluster_sizes}

df["rarity"] = df["cluster"].map(rarity_map)

# ==========================================
# 3. 计算簇内中心 + 簇内距离（簇内异类程度）
#    atypical_i = normalized distance to centroid
# ==========================================
atypical_scores = np.zeros(N)

for c in unique_clusters:
    cluster_df = df[df["cluster"] == c][feature_cols]
    mu = cluster_df.mean().values  # cluster centroid
    
    # 欧氏距离
    distances = np.linalg.norm(cluster_df.values - mu, axis=1)
    
    # z-score 归一
    if distances.std() > 1e-6:
        atypical_scores[df["cluster"] == c] = (distances - distances.mean()) / distances.std()
    else:
        atypical_scores[df["cluster"] == c] = 0

df["atypical"] = atypical_scores

# ==========================================
# 4. 基于风险特征计算 risk score
#    包含 min_ttc, dangerous_ttc_ratio, avg_vehicle_count...
# ==========================================
risk_features = [
    "min_ttc", 
    "dangerous_ttc_ratio",
    "avg_vehicle_count",
    "truck_bus_ratio",
    "ego_hard_brake_ratio"
]

# 对这些风险特征做 0-1 归一化（小心 min_ttc：越小越危险）
scaler = MinMaxScaler()
risk_matrix = scaler.fit_transform(df[risk_features])

# 反转 min_ttc（min_ttc 越小越危险）
min_ttc_norm = risk_matrix[:, risk_features.index("min_ttc")]
min_ttc_norm = 1 - min_ttc_norm  # 越小越危险 → 得分越大
risk_matrix[:, risk_features.index("min_ttc")] = min_ttc_norm

# 风险得分 = 五个风险特征的平均
risk_score = risk_matrix.mean(axis=1)
df["risk"] = risk_score

# ==========================================
# 5. 综合 corner_score
#    corner_score = α * rarity + β * atypical + γ * risk
# ==========================================
α, β, γ = 1.0, 1.0, 1.0  # 默认都设为 1，可以调优

df["corner_score"] = (
    α * df["rarity"] +
    β * df["atypical"] +
    γ * df["risk"]
)

# 正常化方便排序
df["corner_score_norm"] = MinMaxScaler().fit_transform(df[["corner_score"]])

# ==========================================
# 6. 输出结果
# ==========================================
output_path = TABLES_DIR / "scene_features_with_corner_score.csv"
df.to_csv(output_path, index=False)

print(f"Corner score 计算完成！已保存至 {output_path}")

# ==========================================
# 7. 打印 Top 20 corner case 场景
# ==========================================
df_sorted = df.sort_values("corner_score_norm", ascending=False)
print("\n===== Top 20 Corner Cases =====")
print(df_sorted.head(20)[["corner_score_norm", "cluster"] + risk_features])
