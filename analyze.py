#!/usr/bin/env python3
"""
Analysis script for the ASCON vs AES-128-GCM benchmark.

Reads the consolidated workbook, reshapes the per-optimization-level columns
into tidy long form, computes summary statistics across the 100 iterations,
and emits:
  - figures/*.pdf         (vector figures for \\includegraphics in LaTeX)
  - tables/timing_summary.csv   (median/min/max/IQR per algo/board/level/size)
  - tables/footprint.csv        (Flash/RAM cost per algo/board/level)

Run:  python analyze.py path/to/workbook.xlsx
Output goes to ./figures and ./tables next to the script.

Assumptions (confirmed with the data owner):
  - Timing sheets: "F072 aes128gcm", "F072 ascon128aead",
                   "L476 aes128gcm", "L476 ascon128aead"
    Columns: algorithm, board, clock_hz, input_size, iteration,
             "ticks (first run)"  -> warmup, DISCARDED
             "ticks (f-O0)"       -> O0 steady state
             "ticks (-O1)" ... "ticks (-Os)"
    100 iterations per input_size.
  - Size sheets: "F072 size", "L476 size"
    Label column A = "{level};  {variant}" (whitespace-robust).
    Has Flash, RAM, "Cost Flash", "Cost RAM" already computed.
  - TIM2 prescaler 0 at SysClk -> 1 tick == 1 cycle, so cycles == ticks.
"""

import sys
import re
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
FIG_DIR = HERE / "figures"
TAB_DIR = HERE / "tables"
FIG_DIR.mkdir(exist_ok=True)
TAB_DIR.mkdir(exist_ok=True)

# Map the raw column headers to clean optimization-level labels.
# "ticks (first run)" is intentionally absent here -> it gets dropped.
LEVEL_COLUMNS = {
    "ticks (f-O0)": "O0",
    "ticks (-O1)": "O1",
    "ticks (-O2)": "O2",
    "ticks (-O3)": "O3",
    "ticks (-Os)": "Os",
}
LEVEL_ORDER = ["O0", "O1", "O2", "O3", "Os"]

TIMING_SHEETS = [
    "F072 aes128gcm",
    "F072 ascon128aead",
    "L476 aes128gcm",
    "L476 ascon128aead",
]
SIZE_SHEETS = {"F072": "F072 size", "L476": "L476 size"}

# Consistent algorithm display names and colors across all figures.
ALGO_LABEL = {"aes": "AES-128-GCM", "ascon": "Ascon-AEAD128"}
ALGO_COLOR = {"aes": "#c0392b", "ascon": "#2471a3"}


def algo_key(name: str) -> str:
    """Normalize whatever the algorithm cell says into 'aes' or 'ascon'."""
    n = str(name).lower()
    if "ascon" in n:
        return "ascon"
    if "aes" in n:
        return "aes"
    return n


# ----------------------------------------------------------------------------
# Load and reshape timing data into tidy long form
# ----------------------------------------------------------------------------
def load_timing(xlsx_path: Path) -> pd.DataFrame:
    """The timing sheets are six CSV blocks glued horizontally.

    Each block has its own [algorithm, board, clock_hz, input_size, iteration,
    ticks] columns. Block order: first-run (discard), O0, O1, O2, O3, Os.
    The ticks column of each block sits at a fixed position. We read with no
    header and pull id columns from the first block plus each ticks column by
    index, which avoids the repeated-id and trailing-space-header problems.
    """
    BLOCK_WIDTH = 6
    # ticks column index within the sheet for each kept level.
    # block k starts at column k*6; ticks is the 6th column (offset 5).
    LEVEL_TICKS_COL = {
        "O0": 1 * BLOCK_WIDTH + 5,   # 11
        "O1": 2 * BLOCK_WIDTH + 5,   # 17
        "O2": 3 * BLOCK_WIDTH + 5,   # 23
        "O3": 4 * BLOCK_WIDTH + 5,   # 29
        "Os": 5 * BLOCK_WIDTH + 5,   # 35
    }
    # First block (offset 0) holds the canonical id columns.
    ID_IDX = {"algorithm": 0, "board": 1, "clock_hz": 2,
              "input_size": 3, "iteration": 4}

    frames = []
    for sheet in TIMING_SHEETS:
        raw = pd.read_excel(xlsx_path, sheet_name=sheet, header=None)
        # Row 0 is the header row; data starts at row 1.
        data = raw.iloc[1:].reset_index(drop=True)

        base = pd.DataFrame({
            "algorithm": data[ID_IDX["algorithm"]],
            "board": data[ID_IDX["board"]],
            "clock_hz": pd.to_numeric(data[ID_IDX["clock_hz"]], errors="coerce"),
            "input_size": pd.to_numeric(data[ID_IDX["input_size"]], errors="coerce"),
            "iteration": pd.to_numeric(data[ID_IDX["iteration"]], errors="coerce"),
        })

        for level, col in LEVEL_TICKS_COL.items():
            if col >= raw.shape[1]:
                continue
            blk = base.copy()
            blk["level"] = level
            blk["ticks"] = pd.to_numeric(data[col], errors="coerce")
            frames.append(blk)

    df = pd.concat(frames, ignore_index=True)
    df["algo"] = df["algorithm"].map(algo_key)
    df = df.dropna(subset=["ticks", "input_size"])
    df["input_size"] = df["input_size"].astype(int)
    # 1 tick == 1 cycle (prescaler 0). cycles/byte for throughput view.
    df["cycles"] = df["ticks"]
    df["cycles_per_byte"] = df["cycles"] / df["input_size"]
    return df


def summarize_timing(df: pd.DataFrame) -> pd.DataFrame:
    grp = df.groupby(["board", "algo", "level", "input_size"])["ticks"]
    summary = grp.agg(
        median="median", mean="mean", min="min", max="max",
        q1=lambda s: s.quantile(0.25),
        q3=lambda s: s.quantile(0.75),
        n="count",
    ).reset_index()
    summary["iqr"] = summary["q3"] - summary["q1"]
    summary["cycles_per_byte_median"] = summary["median"] / summary["input_size"]
    summary["level"] = pd.Categorical(summary["level"],
                                       categories=LEVEL_ORDER, ordered=True)
    return summary.sort_values(["board", "algo", "level", "input_size"])


# ----------------------------------------------------------------------------
# Load footprint (size) data
# ----------------------------------------------------------------------------
def load_size(xlsx_path: Path) -> pd.DataFrame:
    frames = []
    for board, sheet in SIZE_SHEETS.items():
        raw = pd.read_excel(xlsx_path, sheet_name=sheet)
        raw.columns = [str(c).strip() for c in raw.columns]
        label_col = raw.columns[0]  # first column holds "{level};  {variant}"

        def parse_label(s):
            parts = re.split(r"[;]+", str(s))
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 2:
                return parts[0], parts[1]
            return (parts[0] if parts else None), None

        lv = raw[label_col].apply(parse_label)
        raw["level"] = [p[0] for p in lv]
        raw["variant"] = [p[1] for p in lv]
        raw["board"] = board
        frames.append(raw)

    df = pd.concat(frames, ignore_index=True)
    # Normalize level like "O0"/"Os"; variant like "AES"/"ASCON"/"None"
    df["level"] = df["level"].astype(str).str.strip()
    df["variant"] = df["variant"].astype(str).str.strip()
    for c in ["Flash", "RAM", "Cost Flash", "Cost RAM"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# ----------------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------------
def fig_runtime_vs_size(summary: pd.DataFrame, level: str = "O2"):
    """Log-log median ticks vs input size, one panel per board."""
    boards = sorted(summary["board"].unique())
    fig, axes = plt.subplots(1, len(boards), figsize=(5 * len(boards), 4.2),
                             squeeze=False)
    for ax, board in zip(axes[0], boards):
        sub = summary[(summary["board"] == board) & (summary["level"] == level)]
        for algo in ["aes", "ascon"]:
            d = sub[sub["algo"] == algo].sort_values("input_size")
            if d.empty:
                continue
            ax.plot(d["input_size"], d["median"], marker="o",
                    color=ALGO_COLOR[algo], label=ALGO_LABEL[algo])
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Input size (bytes)")
        ax.set_ylabel("Median time (cycles)")
        ax.set_title(f"{board} @ {level}")
        ax.grid(True, which="both", ls=":", alpha=0.5)
        ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"runtime_vs_size_{level}.pdf")
    plt.close(fig)


def fig_cycles_per_byte(summary: pd.DataFrame, level: str = "O2"):
    """Cycles per byte vs input size, one panel per board.

    The fixed per-call cost shows up as a high value at small sizes that
    decays toward a flat asymptote (the true per-byte cost) as the message
    grows and the fixed cost amortizes. x is log; y is log so the wide range
    from the size-1 spike to the large-input plateau stays legible.
    """
    boards = sorted(summary["board"].unique())
    fig, axes = plt.subplots(1, len(boards), figsize=(5 * len(boards), 4.2),
                             squeeze=False)
    for ax, board in zip(axes[0], boards):
        sub = summary[(summary["board"] == board) & (summary["level"] == level)]
        for algo in ["aes", "ascon"]:
            d = sub[sub["algo"] == algo].sort_values("input_size")
            if d.empty:
                continue
            ax.plot(d["input_size"], d["cycles_per_byte_median"], marker="o",
                    color=ALGO_COLOR[algo], label=ALGO_LABEL[algo])
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Input size (bytes)")
        ax.set_ylabel("Cycles per byte (median)")
        ax.set_title(f"{board} @ {level}")
        ax.grid(True, which="both", ls=":", alpha=0.5)
        ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"cycles_per_byte_{level}.pdf")
    plt.close(fig)


def fig_opt_sweep(summary: pd.DataFrame, input_size: int = 1000):
    """Median ticks across optimization levels at a fixed size, per board."""
    boards = sorted(summary["board"].unique())
    fig, axes = plt.subplots(1, len(boards), figsize=(5 * len(boards), 4.2),
                             squeeze=False)
    x = range(len(LEVEL_ORDER))
    for ax, board in zip(axes[0], boards):
        sub = summary[(summary["board"] == board) &
                      (summary["input_size"] == input_size)]
        width = 0.38
        for i, algo in enumerate(["aes", "ascon"]):
            d = sub[sub["algo"] == algo].set_index("level").reindex(LEVEL_ORDER)
            vals = d["median"].values
            offs = [xi + (i - 0.5) * width for xi in x]
            ax.bar(offs, vals, width=width, color=ALGO_COLOR[algo],
                   label=ALGO_LABEL[algo])
        ax.set_xticks(list(x))
        ax.set_xticklabels(LEVEL_ORDER)
        ax.set_xlabel("Optimization level")
        ax.set_ylabel(f"Median time at {input_size} B (cycles)")
        ax.set_yscale("log")
        ax.set_title(board)
        ax.grid(True, axis="y", which="both", ls=":", alpha=0.5)
        ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"opt_sweep_{input_size}B.pdf")
    plt.close(fig)


def fig_footprint(size_df: pd.DataFrame, level: str = "Os"):
    """Marginal Flash cost per algorithm at a chosen level, both boards."""
    sub = size_df[size_df["level"].str.upper() == level.upper()]
    sub = sub[sub["variant"].str.upper().isin(["AES", "ASCON"])]
    boards = sorted(sub["board"].unique())
    fig, ax = plt.subplots(figsize=(6, 4.2))
    width = 0.38
    x = range(len(boards))
    for i, variant in enumerate(["AES", "ASCON"]):
        algo = "aes" if variant == "AES" else "ascon"
        vals = []
        for b in boards:
            row = sub[(sub["board"] == b) &
                      (sub["variant"].str.upper() == variant)]
            vals.append(row["Cost Flash"].iloc[0] if not row.empty else 0)
        offs = [xi + (i - 0.5) * width for xi in x]
        ax.bar(offs, vals, width=width, color=ALGO_COLOR[algo],
               label=ALGO_LABEL[algo])
    ax.set_xticks(list(x))
    ax.set_xticklabels(boards)
    ax.set_ylabel("Marginal Flash cost (bytes)")
    ax.set_title(f"Code-size cost at -{level} (over baseline)")
    ax.grid(True, axis="y", ls=":", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"footprint_flash_{level}.pdf")
    plt.close(fig)


def fig_footprint_across_levels(size_df: pd.DataFrame, board: str = "F072"):
    """Flash cost across optimization levels - shows ASCON unrolling effect."""
    sub = size_df[(size_df["board"] == board) &
                  (size_df["variant"].str.upper().isin(["AES", "ASCON"]))]
    fig, ax = plt.subplots(figsize=(6, 4.2))
    for variant in ["AES", "ASCON"]:
        algo = "aes" if variant == "AES" else "ascon"
        d = sub[sub["variant"].str.upper() == variant]
        d = d.set_index(d["level"].str.upper()).reindex(
            [l.upper() for l in LEVEL_ORDER])
        ax.plot(LEVEL_ORDER, d["Cost Flash"].values, marker="o",
                color=ALGO_COLOR[algo], label=ALGO_LABEL[algo])
    ax.set_xlabel("Optimization level")
    ax.set_ylabel("Marginal Flash cost (bytes)")
    ax.set_title(f"Code size vs optimization level ({board})")
    ax.grid(True, ls=":", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"footprint_across_levels_{board}.pdf")
    plt.close(fig)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze.py path/to/workbook.xlsx")
        sys.exit(1)
    xlsx_path = Path(sys.argv[1])

    timing = load_timing(xlsx_path)
    summary = summarize_timing(timing)
    summary.to_csv(TAB_DIR / "timing_summary.csv", index=False)

    size_df = load_size(xlsx_path)
    keep_cols = ["board", "level", "variant", "text", "data", "bss",
                 "Flash", "RAM", "Cost Flash", "Cost RAM"]
    keep_cols = [c for c in keep_cols if c in size_df.columns]
    size_df[keep_cols].to_csv(TAB_DIR / "footprint.csv", index=False)

    # Figures
    fig_runtime_vs_size(summary, level="O2")
    fig_cycles_per_byte(summary, level="O2")
    fig_opt_sweep(summary, input_size=1000)
    fig_footprint(size_df, level="Os")
    fig_footprint_across_levels(size_df, board="F072")
    fig_footprint_across_levels(size_df, board="L476")

    print("Wrote:")
    for p in sorted(FIG_DIR.glob("*.pdf")):
        print("  figure:", p)
    for p in sorted(TAB_DIR.glob("*.csv")):
        print("  table :", p)


if __name__ == "__main__":
    main()
