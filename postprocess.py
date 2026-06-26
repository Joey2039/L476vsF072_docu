#!/usr/bin/env python3
"""Post-process pandoc-generated chapter .tex files.

Fixes:
  1. {[}fig:xxx{]} -> \ref{fig:xxx}  and  {[}tbl:xxx{]} -> \ref{tbl:xxx}
  2. Longtable wrappers -> table floats with caption+label
  3. Figure environments inserted after first-mention paragraphs (chapter 4)
"""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def fix_refs(content: str) -> str:
    return re.sub(r'\{\[}((?:fig|tbl):[\w-]+)\{]\}', r'\\ref{\1}', content)


# ---------------------------------------------------------------------------
# Chapter 3 – platforms table
# ---------------------------------------------------------------------------
CH3_OLD_TABLE = r"""{\def\LTcaptype{none} % do not increment counter
\begin{longtable}[]{@{}lll@{}}
\toprule\noalign{}
Property & NUCLEO-F072RB & NUCLEO-L476RG \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
Microcontroller & STM32F072RBT6 & STM32L476RGT6 \\
Core & Cortex-M0 & Cortex-M4F \\
Maximum clock & 48 MHz & 80 MHz \\
Flash & 128 KB & 1 MB \\
SRAM & 16 KB & 128 KB \\
Hardware AES & None & None \\
Cycle counter (DWT) & Absent & Present \\
Instruction prefetch & None & ART accelerator \\
Floating-point unit & None & Single precision \\
\end{longtable}
}"""

CH3_NEW_TABLE = r"""\begin{table}[htbp]
  \centering
  \caption{Target platform properties.}
  \label{tbl:platforms}
  \begin{tabular}{@{}lll@{}}
    \toprule
    Property & NUCLEO-F072RB & NUCLEO-L476RG \\
    \midrule
    Microcontroller & STM32F072RBT6 & STM32L476RGT6 \\
    Core & Cortex-M0 & Cortex-M4F \\
    Maximum clock & 48 MHz & 80 MHz \\
    Flash & 128 KB & 1 MB \\
    SRAM & 16 KB & 128 KB \\
    Hardware AES & None & None \\
    Cycle counter (DWT) & Absent & Present \\
    Instruction prefetch & None & ART accelerator \\
    Floating-point unit & None & Single precision \\
    \bottomrule
  \end{tabular}
\end{table}"""


# ---------------------------------------------------------------------------
# Chapter 4 – timing-1000 table
# ---------------------------------------------------------------------------
CH4_OLD_TIMING_TABLE = r"""{\def\LTcaptype{none} % do not increment counter
\begin{longtable}[]{@{}lrrrrrr@{}}
\toprule\noalign{}
Level & M0 ASCON & M0 AES & M0 ratio & M4 ASCON & M4 AES & M4 ratio \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
-O0 & 1,387,063 & 2,661,457 & 1.92 & 726,789 & 845,537 & 1.16 \\
-O1 & 170,741 & 792,911 & 4.64 & 104,422 & 242,980 & 2.33 \\
-O2 & 168,921 & 770,536 & 4.56 & 98,262 & 193,311 & 1.97 \\
-O3 & 145,888 & 485,227 & 3.33 & 70,194 & 193,283 & 2.75 \\
-Os & 268,899 & 787,284 & 2.93 & 139,993 & 269,250 & 1.92 \\
\end{longtable}
}"""

CH4_NEW_TIMING_TABLE = r"""\begin{table}[htbp]
  \centering
  \caption{Median execution time (cycles) at 1000\,B and ratio AES-128-GCM/Ascon-AEAD128.}
  \label{tbl:timing-1000}
  \begin{tabular}{@{}lrrrrrr@{}}
    \toprule
    Level & M0 ASCON & M0 AES & M0 ratio & M4 ASCON & M4 AES & M4 ratio \\
    \midrule
    -O0 & 1,387,063 & 2,661,457 & 1.92 & 726,789 & 845,537 & 1.16 \\
    -O1 & 170,741 & 792,911 & 4.64 & 104,422 & 242,980 & 2.33 \\
    -O2 & 168,921 & 770,536 & 4.56 & 98,262 & 193,311 & 1.97 \\
    -O3 & 145,888 & 485,227 & 3.33 & 70,194 & 193,283 & 2.75 \\
    -Os & 268,899 & 787,284 & 2.93 & 139,993 & 269,250 & 1.92 \\
    \bottomrule
  \end{tabular}
\end{table}"""


# ---------------------------------------------------------------------------
# Chapter 4 – footprint table
# The pandoc output has minipage column headers; replace the whole block.
# ---------------------------------------------------------------------------
CH4_OLD_FOOTPRINT_TABLE_START = r"""{\def\LTcaptype{none} % do not increment counter
\begin{longtable}[]{@{}"""

CH4_OLD_FOOTPRINT_TABLE_END = r"""\end{longtable}
}

The Ascon-AEAD128 marginal Flash cost varies strongly"""

CH4_NEW_FOOTPRINT_TABLE = r"""\begin{table}[htbp]
  \centering
  \caption{Marginal Flash cost (bytes) per algorithm, per board, at each optimization level.}
  \label{tbl:footprint}
  \begin{tabular}{@{}lrrrrrr@{}}
    \toprule
    Level & M0 AES & M0 ASCON & M0 ratio & M4 AES & M4 ASCON & M4 ratio \\
    \midrule
    -O0 & 26,296 & 12,836 & 2.05 & 23,256 & 6,776 & 3.43 \\
    -O1 & 17,396 & 27,924 & 0.62 & 16,496 & 24,208 & 0.68 \\
    -O2 & 17,476 & 27,504 & 0.64 & 16,584 & 23,264 & 0.71 \\
    -O3 & 24,208 & 43,024 & 0.56 & 17,720 & 34,560 & 0.51 \\
    -Os & 16,500 & 4,376 & 3.77 & 15,776 & 4,208 & 3.75 \\
    \bottomrule
  \end{tabular}
\end{table}

The Ascon-AEAD128 marginal Flash cost varies strongly"""


# ---------------------------------------------------------------------------
# Chapter 4 – figure environments
# ---------------------------------------------------------------------------
FIG_RUNTIME = r"""
\begin{figure}[htbp]
  \centering
  \includegraphics[width=\linewidth]{runtime_vs_size_O2.pdf}
  \caption{Median execution time versus input size at \texttt{-O2}, logarithmic axes. One panel per board.}
  \label{fig:runtime}
\end{figure}
"""

FIG_OPTSWEEP = r"""
\begin{figure}[htbp]
  \centering
  \includegraphics[width=\linewidth]{opt_sweep_1000B.pdf}
  \caption{Median execution time at 1000\,B across optimization levels, logarithmic scale. One panel per board.}
  \label{fig:optsweep}
\end{figure}
"""

FIG_CPB = r"""
\begin{figure}[htbp]
  \centering
  \includegraphics[width=\linewidth]{cycles_per_byte_O2.pdf}
  \caption{Median cycles per byte versus input size at \texttt{-O2}, logarithmic axes. One panel per board.}
  \label{fig:cpb}
\end{figure}
"""

FIG_FOOTPRINT = r"""
\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.6\linewidth]{footprint_flash_Os.pdf}
  \caption{Marginal Flash cost at \texttt{-Os} for each algorithm on both boards.}
  \label{fig:footprint}
\end{figure}
"""

FIG_FOOTPRINT_LEVELS = r"""
\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.48\linewidth]{footprint_across_levels_F072.pdf}
  \hfill
  \includegraphics[width=0.48\linewidth]{footprint_across_levels_L476.pdf}
  \caption{Marginal Flash cost across optimization levels: F072 (left) and L476 (right).}
  \label{fig:footprint-levels}
\end{figure}
"""

# Anchors: text that immediately precedes where we want to insert the figure.
# We insert AFTER these paragraphs (add a blank line then the figure).
RUNTIME_ANCHOR = (
    "board.\n\n"
    r"\subsection{4.3.2 Effect of Optimization"
)
RUNTIME_REPLACEMENT = (
    "board.\n"
    + FIG_RUNTIME
    + "\n"
    + r"\subsection{4.3.2 Effect of Optimization"
)

# opt_sweep: insert after the "-Os" paragraph (before the table anchor)
OPTSWEEP_ANCHOR = (
    "139,993 cycles.\n\n"
    "Table"
)
OPTSWEEP_REPLACEMENT = (
    "139,993 cycles.\n"
    + FIG_OPTSWEEP
    + "\nTable"
)

# cpb: insert after the last sentence of section 4.4
CPB_ANCHOR = (
    "Cortex-M4F.\n\n"
    r"\section{4.5 Code Size}"
)
CPB_REPLACEMENT = (
    "Cortex-M4F.\n"
    + FIG_CPB
    + "\n"
    + r"\section{4.5 Code Size}"
)

# footprint bar chart: insert after the RAM caveat sentence (before the big table)
FOOTPRINT_ANCHOR = (
    "as noted in Section 3.8.\n\n"
    r"{\def\LTcaptype"
)
FOOTPRINT_REPLACEMENT = (
    "as noted in Section 3.8.\n"
    + FIG_FOOTPRINT
    + "\n"
    + r"{\def\LTcaptype"
)

# footprint-levels: insert after the last sentence of the paragraph
FOOTPRINT_LEVELS_ANCHOR = (
    r"then falling sharply at \texttt{-Os}."
    + "\n\n"
    + r"\section{4.6 Summary"
)
FOOTPRINT_LEVELS_REPLACEMENT = (
    r"then falling sharply at \texttt{-Os}."
    + "\n"
    + FIG_FOOTPRINT_LEVELS
    + "\n"
    + r"\section{4.6 Summary"
)


def postprocess_ch3(path: Path):
    content = path.read_text(encoding="utf-8")
    content = fix_refs(content)
    content = content.replace(CH3_OLD_TABLE, CH3_NEW_TABLE)
    path.write_text(content, encoding="utf-8")
    print(f"  processed {path.name}")


def postprocess_ch4(path: Path):
    content = path.read_text(encoding="utf-8")
    content = fix_refs(content)

    # Insert figures before replacing tables (table anchors used below)
    content = content.replace(RUNTIME_ANCHOR, RUNTIME_REPLACEMENT, 1)
    content = content.replace(OPTSWEEP_ANCHOR, OPTSWEEP_REPLACEMENT, 1)
    content = content.replace(CPB_ANCHOR, CPB_REPLACEMENT, 1)
    content = content.replace(FOOTPRINT_ANCHOR, FOOTPRINT_REPLACEMENT, 1)
    content = content.replace(FOOTPRINT_LEVELS_ANCHOR, FOOTPRINT_LEVELS_REPLACEMENT, 1)

    # Replace timing table
    content = content.replace(CH4_OLD_TIMING_TABLE, CH4_NEW_TIMING_TABLE, 1)

    # Replace footprint table (complex minipage headers)
    idx_start = content.find(CH4_OLD_FOOTPRINT_TABLE_START)
    idx_end = content.find(CH4_OLD_FOOTPRINT_TABLE_END)
    if idx_start != -1 and idx_end != -1:
        idx_end_full = idx_end + len(CH4_OLD_FOOTPRINT_TABLE_END)
        content = content[:idx_start] + CH4_NEW_FOOTPRINT_TABLE + content[idx_end_full:]

    path.write_text(content, encoding="utf-8")
    print(f"  processed {path.name}")


def postprocess_generic(path: Path):
    content = path.read_text(encoding="utf-8")
    content = fix_refs(content)
    path.write_text(content, encoding="utf-8")
    print(f"  processed {path.name}")


if __name__ == "__main__":
    print("Post-processing chapters...")
    postprocess_ch3(HERE / "chapter_3_methodology.tex")
    postprocess_ch4(HERE / "chapter_4_results.tex")
    for name in ["chapter_1_proposal.tex", "chapter_2_proposal.tex",
                 "chapter_5_discussion.tex", "chapter_6_conclusion.tex"]:
        postprocess_generic(HERE / name)
    print("Done.")
