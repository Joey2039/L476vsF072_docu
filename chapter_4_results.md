# Chapter 4 — Results (Draft)

> Working draft. Figure references use `[fig:...]` and table references use
> `[tbl:...]`. This chapter reports the measurements. Interpretation of what
> they mean for algorithm selection is deferred to Chapter 5.

---

## 4.1 Overview

This chapter presents the measured results in three parts. Section 4.2 reports
the harness validation, which establishes that the timing infrastructure is
trustworthy. Section 4.3 reports the execution-time results across message
sizes and optimization levels. Section 4.4 reports the throughput results in
cycles per byte. Section 4.5 reports the code-size results. All timing figures
are cycle counts at 48 MHz, where one timer tick equals one processor cycle.
All results derive from the single consolidated data set, and every figure and
table is reproducible from it.

## 4.2 Harness Validation

The `memcpy` validation passed all four checks on both boards. The measured time
grew in proportion to the input size, the per-iteration variation was zero after
the discarded warmup run, the smallest input size recorded a non-zero time, and
both boards reported the expected 48 MHz clock. The per-iteration determinism
observed here persisted through all later measurements. Across the cryptographic
benchmarks the median, minimum, and maximum coincided for every measured point,
so the timing results are reported as single median values without dispersion.

The ratio between the two boards for the `memcpy` workload settled at
approximately 2.8 to 1 at the largest size, with the Cortex-M0 slower than the
Cortex-M4F at the same clock. This figure is the architectural baseline against
which the cryptographic ratios in the following sections are read.

## 4.3 Execution Time

### 4.3.1 Runtime Across Message Sizes

Figure [fig:runtime] shows median execution time against input size on
logarithmic axes, with one panel per board, at optimization level `-O2`. On both
boards Ascon-AEAD128 is faster than AES-128-GCM at every measured size. The
curves share a characteristic shape. At the smallest sizes the time is nearly
constant, because the fixed per-call cost dominates. Above approximately 100
bytes the time rises in proportion to the input size, which is the per-byte
encryption cost. The vertical separation between the two algorithms is present
across the whole range and is wider on the Cortex-M0 board than on the
Cortex-M4F board.

### 4.3.2 Effect of Optimization Level

Figure [fig:optsweep] shows median execution time at a fixed message size of
1000 bytes across the five optimization levels, with one panel per board and a
logarithmic time axis. Table [tbl:timing-1000] gives the underlying values.

The dominant effect is the step from `-O0` to `-O1`. On the Cortex-M0 the
Ascon-AEAD128 time at 1000 bytes falls from 1,387,063 cycles at `-O0` to
170,741 cycles at `-O1`, a factor of about eight. The AES-128-GCM time falls
from 2,661,457 to 792,911 cycles over the same step, a factor of about three.
On the Cortex-M4F the same step takes Ascon-AEAD128 from 726,789 to 104,422
cycles and AES-128-GCM from 845,537 to 242,980 cycles.

Between `-O1`, `-O2`, and `-O3` the changes are smaller and not uniform. On the
Cortex-M4F, AES-128-GCM is essentially unchanged from `-O2` to `-O3`, at 193,311
and 193,283 cycles, while Ascon-AEAD128 improves from 98,262 to 70,194 cycles.
On the Cortex-M0, AES-128-GCM improves obviously at `-O3`, from 770,536 to
485,227 cycles, while Ascon-AEAD128 improves modestly, from 168,921 to 145,888
cycles.

At `-Os` both algorithms are slower than at `-O2` on both boards. On the
Cortex-M0 the Ascon-AEAD128 time at `-Os` is 268,899 cycles, which is slower
than its `-O1` time. On the Cortex-M4F the corresponding `-Os` time is 139,993
cycles.

Table [tbl:timing-1000] summarizes the ratio of AES-128-GCM time to
Ascon-AEAD128 time at 1000 bytes for each board and level.

| Level | M0 ASCON | M0 AES | M0 ratio | M4 ASCON | M4 AES | M4 ratio |
|---|---:|---:|---:|---:|---:|---:|
| -O0 | 1,387,063 | 2,661,457 | 1.92 | 726,789 | 845,537 | 1.16 |
| -O1 | 170,741 | 792,911 | 4.64 | 104,422 | 242,980 | 2.33 |
| -O2 | 168,921 | 770,536 | 4.56 | 98,262 | 193,311 | 1.97 |
| -O3 | 145,888 | 485,227 | 3.33 | 70,194 | 193,283 | 2.75 |
| -Os | 268,899 | 787,284 | 2.93 | 139,993 | 269,250 | 1.92 |

At `-O0` the two algorithms are close, especially on the Cortex-M4F where the
ratio is 1.16. Once optimization is enabled the ratio is larger, and at every
optimized level the ratio is greater on the Cortex-M0 than on the Cortex-M4F.
The largest ratio in favor of Ascon-AEAD128 occurs at `-O1` and `-O2` on the
Cortex-M0, at approximately 4.6.

## 4.4 Throughput

Figure [fig:cpb] shows median cycles per byte against input size on logarithmic
axes, with one panel per board, at `-O2`. At the smallest size the cost per byte
is highest, because the fixed per-call cost is divided across a single byte. As
the message grows the cost per byte falls toward a flat asymptote, which is the
per-byte encryption rate.

In the large-message region the per-byte rates at `-O2` are as follows. On the
Cortex-M0 at 1000 bytes, Ascon-AEAD128 reaches approximately 169 cycles per
byte and AES-128-GCM approximately 771 cycles per byte. On the Cortex-M4F at
10000 bytes, Ascon-AEAD128 reaches approximately 95 cycles per byte and
AES-128-GCM approximately 189 cycles per byte. The Cortex-M0 curve for
Ascon-AEAD128 is still descending at its largest available size, because the
board cannot hold the 10000-byte buffers, so its reported per-byte rate is a
slight overestimate of the rate it would reach for larger messages.

At the smallest message size of one byte, where the figure reflects the fixed
per-call cost, the values at `-O2` are 7410 cycles for Ascon-AEAD128 and 25,185
cycles for AES-128-GCM on the Cortex-M0, and 4219 cycles for Ascon-AEAD128 and
6470 cycles for AES-128-GCM on the Cortex-M4F.

## 4.5 Code Size

Figure [fig:footprint] shows the marginal Flash cost of each algorithm at `-Os`
for both boards, where the marginal cost is the difference between the
algorithm's build variant and the baseline variant. Table [tbl:footprint] gives
the marginal Flash cost at every optimization level.

At `-Os`, Ascon-AEAD128 adds 4376 bytes of Flash on the Cortex-M0 and 4208 bytes
on the Cortex-M4F. AES-128-GCM adds 16,500 bytes on the Cortex-M0 and 15,776
bytes on the Cortex-M4F. The ratio of AES-128-GCM to Ascon-AEAD128 marginal
Flash is approximately 3.8 on both boards. The marginal RAM cost is similar for
both algorithms and is dominated by the fixed measurement buffers rather than
the cryptographic working state, as noted in Section 3.8.

| Level | M0 AES Flash | M0 ASCON Flash | M0 ratio | M4 AES Flash | M4 ASCON Flash | M4 ratio |
|---|---:|---:|---:|---:|---:|---:|
| -O0 | 26,296 | 12,836 | 2.05 | 23,256 | 6,776 | 3.43 |
| -O1 | 17,396 | 27,924 | 0.62 | 16,496 | 24,208 | 0.68 |
| -O2 | 17,476 | 27,504 | 0.64 | 16,584 | 23,264 | 0.71 |
| -O3 | 24,208 | 43,024 | 0.56 | 17,720 | 34,560 | 0.51 |
| -Os | 16,500 | 4,376 | 3.77 | 15,776 | 4,208 | 3.75 |

The Ascon-AEAD128 marginal Flash cost varies strongly with optimization level.
Figure [fig:footprint-levels] shows this for each board. At `-Os` it is the
smallest of the two algorithms by a wide margin. At `-O1`, `-O2`, and `-O3` it
is larger than the AES-128-GCM cost, reaching a maximum at `-O3` of 43,024 bytes
on the Cortex-M0 and 34,560 bytes on the Cortex-M4F. The AES-128-GCM marginal
Flash cost is comparatively stable across levels, between roughly 16,000 and
26,000 bytes. The shape of the Ascon-AEAD128 curve is the same on both boards,
with the cost rising from `-O0` through a peak at `-O3` and then falling sharply
at `-Os`.

## 4.6 Summary of Results

Across both boards and all message sizes, Ascon-AEAD128 executed faster than
AES-128-GCM at every optimization level. The advantage was smallest at `-O0`
and larger once optimization was enabled. At equal clock frequency the advantage
was consistently larger on the Cortex-M0 than on the Cortex-M4F, reaching a
factor of about 4.6 at 1000 bytes on the Cortex-M0. In code size, Ascon-AEAD128
was substantially smaller than AES-128-GCM at `-Os`, by a factor of about 3.8 on
both boards, while at the speed-oriented optimization levels its reference
implementation was larger than AES-128-GCM because of the expansion of the
permutation code. These results are interpreted in relation to the four research
questions in Chapter 5.
