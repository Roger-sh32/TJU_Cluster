import argparse
from pathlib import Path

import pandas as pd
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
HDBSCAN_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = HDBSCAN_ROOT.parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review nuScenes scenes from clustering result tables."
    )
    parser.add_argument(
        "--dataroot",
        default=str(PROJECT_ROOT / "nuScenes"),
        help="nuScenes dataroot.",
    )
    parser.add_argument(
        "--results",
        default=str(HDBSCAN_ROOT / "tables" / "scene_features_umap_hdbscan.csv"),
        help="CSV file with scene_token and optional clustering scores.",
    )
    parser.add_argument(
        "--scene-name",
        help="Specific nuScenes scene name, e.g. scene-0061.",
    )
    parser.add_argument(
        "--scene-token",
        help="Specific scene_token to inspect.",
    )
    parser.add_argument(
        "--cluster",
        type=int,
        help="Inspect a cluster and list the top scenes in it.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="How many scenes to show when filtering by cluster.",
    )
    parser.add_argument(
        "--sort-by",
        default="scene_token",
        help="Column used to sort scenes inside a cluster, e.g. min_ttc or corner_score_norm.",
    )
    parser.add_argument(
        "--ascending",
        action="store_true",
        help="Sort ascending instead of descending.",
    )
    parser.add_argument(
        "--channel",
        default="CAM_FRONT",
        help="Camera channel used for exports.",
    )
    parser.add_argument(
        "--export-dir",
        help="Directory for exported images.",
    )
    parser.add_argument(
        "--render-first-sample",
        action="store_true",
        help="Export the first sample image of each selected scene.",
    )
    parser.add_argument(
        "--play",
        action="store_true",
        help="Play the selected scene like a video with render_scene_channel.",
    )
    parser.add_argument(
        "--freq",
        type=int,
        default=2,
        help="Playback frequency for render_scene_channel.",
    )
    parser.add_argument(
        "--fallback-dir",
        default=str(PROJECT_ROOT / "exports"),
        help="Directory used when GUI playback is unavailable and a GIF is exported.",
    )
    parser.add_argument(
        "--version",
        default="v1.0-trainval",
        help="nuScenes dataset version.",
    )
    return parser


def load_results(results_path: Path) -> pd.DataFrame:
    df = pd.read_csv(results_path)
    if "scene_token" not in df.columns:
        raise ValueError(f"{results_path} does not contain a 'scene_token' column.")
    return df


def select_rows(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    if args.scene_name:
        rows = df[df.get("scene_name", pd.Series(dtype=str)) == args.scene_name].copy()
        if not rows.empty:
            return rows

    if args.scene_token:
        rows = df[df["scene_token"] == args.scene_token].copy()
        if rows.empty:
            raise ValueError(f"scene_token not found: {args.scene_token}")
        return rows

    if args.cluster is not None:
        if "cluster" not in df.columns:
            raise ValueError("The results file has no 'cluster' column.")
        rows = df[df["cluster"] == args.cluster].copy()
        if rows.empty:
            raise ValueError(f"cluster not found: {args.cluster}")
        if args.sort_by not in rows.columns:
            raise ValueError(f"sort column not found: {args.sort_by}")
        rows = rows.sort_values(args.sort_by, ascending=args.ascending)
        return rows.head(args.top_k)

    raise ValueError("Provide --scene-name, --scene-token, or --cluster.")


def print_scene_summary(nusc, row: pd.Series) -> None:
    scene = nusc.get("scene", row["scene_token"])
    print("=" * 80)
    print(f"scene_token : {row['scene_token']}")
    print(f"scene_name  : {scene['name']}")
    print(f"description : {scene['description']}")
    print(f"nbr_samples : {scene['nbr_samples']}")

    for key in ["cluster", "corner_score_norm", "min_ttc", "min_headway", "avg_vehicle_count"]:
        if key in row.index:
            print(f"{key:12}: {row[key]}")


def find_scene_by_name(nusc, scene_name: str) -> dict:
    for scene in nusc.scene:
        if scene["name"] == scene_name:
            return scene
    raise ValueError(f"scene name not found: {scene_name}")


def export_first_sample(nusc, row: pd.Series, export_dir: Path, channel: str) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)
    scene = nusc.get("scene", row["scene_token"])
    sample = nusc.get("sample", scene["first_sample_token"])

    # render_sample_data saves a quick visual check without requiring notebook tooling.
    sample_data_token = sample["data"][channel]
    out_path = export_dir / f"{scene['name']}_{channel}.png"
    nusc.render_sample_data(sample_data_token, out_path=str(out_path))
    print(f"exported    : {out_path}")


def export_scene_gif(nusc, scene: dict, channel: str, freq: int, fallback_dir: Path) -> Path:
    fallback_dir.mkdir(parents=True, exist_ok=True)
    gif_path = fallback_dir / f"{scene['name']}_{channel}.gif"

    sample = nusc.get("sample", scene["first_sample_token"])
    frames = []

    while True:
        sample_data = nusc.get("sample_data", sample["data"][channel])
        image_path = Path(nusc.dataroot) / sample_data["filename"]
        with Image.open(image_path) as img:
            frames.append(img.convert("RGB").copy())

        if sample["next"] == "":
            break
        sample = nusc.get("sample", sample["next"])

    duration_ms = max(1, int(1000 / max(freq, 1)))
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
    )
    return gif_path


def play_scene(nusc, scene: dict, channel: str, freq: int) -> None:
    print(f"playing     : {scene['name']} ({channel}, freq={freq})")
    nusc.render_scene_channel(scene["token"], channel=channel, freq=freq)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        from nuscenes import NuScenes
    except ImportError as exc:
        raise SystemExit(
            "nuscenes package is not available in the current Python environment."
        ) from exc

    nusc = NuScenes(version=args.version, dataroot=args.dataroot, verbose=True)

    if args.scene_name and args.play:
        scene = find_scene_by_name(nusc, args.scene_name)
        print("=" * 80)
        print(f"scene_name  : {scene['name']}")
        print(f"description : {scene['description']}")
        print(f"nbr_samples : {scene['nbr_samples']}")
        try:
            play_scene(nusc, scene, args.channel, args.freq)
        except Exception as exc:
            print(f"playback GUI unavailable: {exc}")
            gif_path = export_scene_gif(
                nusc, scene, args.channel, args.freq, Path(args.fallback_dir)
            )
            print(f"fallback gif: {gif_path}")
        return

    if args.scene_name and not args.play:
        scene = find_scene_by_name(nusc, args.scene_name)
        print("=" * 80)
        print(f"scene_name  : {scene['name']}")
        print(f"scene_token : {scene['token']}")
        print(f"description : {scene['description']}")
        print(f"nbr_samples : {scene['nbr_samples']}")
        return

    results_path = Path(args.results)
    df = load_results(results_path)

    rows = select_rows(df, args)

    export_dir = Path(args.export_dir) if args.export_dir else None
    for _, row in rows.iterrows():
        print_scene_summary(nusc, row)
        if args.play:
            scene = nusc.get("scene", row["scene_token"])
            try:
                play_scene(nusc, scene, args.channel, args.freq)
            except Exception as exc:
                print(f"playback GUI unavailable: {exc}")
                gif_path = export_scene_gif(
                    nusc, scene, args.channel, args.freq, Path(args.fallback_dir)
                )
                print(f"fallback gif: {gif_path}")
        if args.render_first_sample:
            if export_dir is None:
                raise ValueError("--render-first-sample requires --export-dir.")
            export_first_sample(nusc, row, export_dir, args.channel)


if __name__ == "__main__":
    main()
