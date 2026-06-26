# Chapter 3 — Methodology (Draft)

> Working draft. Placeholders are marked `[...]`. Citation placeholders use
> `[cite ...]`. Numbers that must be confirmed against the final toolchain are
> marked inline.

---

## 3.1 Overview and Experimental Design

This chapter describes how the benchmark was constructed and how every reported
number was produced. The goal is a fair and reproducible comparison of
Ascon-AEAD128 and AES-128-GCM under matched conditions on two constrained
microcontrollers. Fairness here has a precise meaning. Both algorithms run as
software-only implementations, both are measured through an identical timing
harness, both are compiled with the same toolchain and the same set of
optimization levels, and the one-time setup cost is excluded from the timed
region for both in the same way.

The experimental design varies four factors. The first is the algorithm,
either Ascon-AEAD128 or AES-128-GCM. The second is the hardware platform, a
Cortex-M0 board and a Cortex-M4F board. The third is the input message size,
swept across several orders of magnitude. The fourth is the compiler
optimization level, swept from no optimization through size optimization. Each
combination is measured many times and reduced to summary statistics offline.
Code size is measured separately, as a static property of the compiled
binaries rather than a runtime measurement.

## 3.2 Target Platforms

Two STMicroelectronics Nucleo-64 development boards represent the low and
middle of the constrained range. Their relevant properties are summarized in
Table [tbl:platforms]. Both boards expose an on-board ST-LINK debugger with a
USB virtual COM port routed to USART2, which carries the measurement output.

| Property             | NUCLEO-F072RB | NUCLEO-L476RG    |
| -------------------- | ------------- | ---------------- |
| Microcontroller      | STM32F072RBT6 | STM32L476RGT6    |
| Core                 | Cortex-M0     | Cortex-M4F       |
| Maximum clock        | 48 MHz        | 80 MHz           |
| Flash                | 128 KB        | 1 MB             |
| SRAM                 | 16 KB         | 128 KB           |
| Hardware AES         | None          | None             |
| Cycle counter (DWT)  | Absent        | Present          |
| Instruction prefetch | None          | ART accelerator  |
| Floating-point unit  | None          | Single precision |

### 3.2.1 NUCLEO-F072RB (Cortex-M0)

The F072 carries a Cortex-M0 core with no hardware multiplier for wide
operands, no instruction cache, no branch predictor, and no floating-point
unit. It represents the lower end of the device range, where every cycle and
every kilobyte is scarce. Its 16 KB of SRAM is the binding constraint on this
study, and it limits the largest message size that can be benchmarked on this
board.

### 3.2.2 NUCLEO-L476RG (Cortex-M4F)

The L476 carries a Cortex-M4F core with a single-cycle hardware multiplier, a
single-precision floating-point unit, and the ST ART accelerator, which
prefetches and caches instructions from Flash. It represents the middle of the
range. The L476 has substantially more memory than the F072, so memory is not a
constraint on this board, but it is included to expose how the relative
performance of the two algorithms depends on the processor architecture.

The specific part on the NUCLEO-L476RG does not contain a hardware AES block.
Only the L486 and related parts in the same family include one. This absence is
useful for the study, because it means there is no hardware cryptographic path
that could be engaged accidentally, so the software comparison is consistent
on both boards.

### 3.2.3 Clocking and the Matched-Frequency Decision

Both boards run at 48 MHz for the timing comparison. The L476 is capable of
80 MHz, so it is intentionally underclocked to the F072 ceiling. This choice
removes clock frequency as a variable. Any difference in measured time between
the two boards at the same clock then reflects the processor architecture
alone, not a difference in operating frequency.

The measurements are reported primarily as cycle counts rather than wall-clock
time. This is due to the timer increments once per processor clock, as described in
Section 3.6.1. SO one timer tick equals one clock cycle, and the cycle count is
independent of the operating frequency.

## 3.3 Toolchain and Build System

All firmware was built with a single toolchain to keep the comparison
consistent. The compiler is `arm-none-eabi-gcc` version 14.3.1, supplied with
the STM32CubeCLT bundle. The build is driven by CMake with the Ninja generator,
both bundled with CubeCLT. Project skeletons, including peripheral
initialization and the linker script, were generated with STM32CubeMX
configured for CMake output. The host operating system was Windows.

The base compiler flags follow the CubeMX template. They include
`-ffunction-sections`, `-fdata-sections`, and linker garbage collection
(`-Wl,--gc-sections`), the size-oriented newlib-nano C library
(`--specs=nano.specs`), and the architecture flags appropriate to each core. On
the L476 these include the hardware floating-point ABI, although floating point
is not used by either algorithm.

The optimization level is the one build variable that changes across the
measurement matrix. It is controlled through a single CMake cache variable that
is set per build preset. Each preset reconfigures the build at one optimization
level, from `-O0` through `-Os`, so that the same source produces a family of
binaries that differ only in optimization. The presets also select, for the
footprint builds, which cryptographic implementation is compiled in, as
described in Section 3.8.

## 3.4 Cryptographic Implementations

Both implementations are taken from existing open-source projects rather than
written for this study. This keeps the comparison representative of what a
developer would actually deploy, and it avoids the risk of an unrepresentative
hand-written implementation favoring one side.

### 3.4.1 AES-128-GCM (mbedTLS)

AES-128-GCM is provided by mbedTLS version 3.6.x `[cite mbedTLS; record exact
commit hash]`. mbedTLS was selected because it is a widely deployed,
well-maintained library with a complete and verified AES-GCM implementation,
which lends the comparison credibility. The library was reduced to a minimal
configuration containing only the modules required for AES-128-GCM. In this
version of mbedTLS, GCM reaches the AES block cipher through the generic cipher
layer, so the cipher dispatch modules are required in addition to the AES and
GCM modules.

Three configuration choices affect the measurements and are disclosed here,
because the reported numbers are only interpretable alongside them.

First, the small four-bit GHASH multiplication table is used. The larger
eight-bit table is faster per byte but enlarges the GCM context by roughly
3.8 KB of RAM. The small table was chosen because it represents a genuinely
lightweight configuration of AES-GCM, which matches the constrained-device
framing of this work. As a consequence, the reported AES-GCM throughput
represents the memory-frugal end of what mbedTLS can achieve rather than its
speed ceiling. This point is revisited in the discussion.

Second, the AES lookup tables are placed in Flash rather than generated in RAM
at initialization. This shifts roughly 8 KB from RAM to Flash, which is the
realistic trade-off on a part with only 16 KB of SRAM. It affects the code-size
results but has no meaningful effect on runtime.

Third, only the 128-bit key length is compiled. The 192-bit and 256-bit key
schedules are removed. Because only AES-128 is benchmarked, this has no effect
on runtime and only a small effect on Flash size.

The cipher dispatch layer introduces a one-time indirection cost during key
setup. Key setup is performed once, outside the timed region, so this cost does
not enter the reported timings.

### 3.4.2 Ascon-AEAD128 (Reference Implementation)

Ascon-AEAD128 is provided by the official ASCON reference implementation in C
`[cite ASCON software repository; record exact commit hash]`. The reference
variant was chosen over the optimized variants for portability and because it
corresponds directly to the standardized specification, which matches the
framing of ASCON as the NIST Lightweight Cryptography winner. The implementation
uses a 16-byte key, a 16-byte nonce, and produces a 16-byte authentication tag,
with a rate of 16 bytes.

The choice of the reference variant rather than an optimized variant has a
visible effect on code size at high optimization levels. This is reported and
discussed rather than hidden, because it reflects what a developer integrating
the standard reference code would observe.

### 3.4.3 Uniform Wrapper Interface

Each implementation is reached through a thin wrapper with a matching
signature, so that the benchmark harness calls both algorithms the same way.
The AES wrapper separates key setup from encryption, so that the one-time key
schedule can be hoisted out of the timed region. The ASCON single-pass AEAD
interface has no separable key schedule, so its encryption call is timed in
full. This is the symmetric treatment of one-time setup described in
Section 3.6.4. Neither wrapper performs additional copying inside the timed
path beyond what the underlying library requires.

## 3.5 Correctness Verification

No timing measurement was trusted until the implementation producing it was
shown to be correct. Each algorithm was verified against published test vectors
before any benchmark was run.

AES-128-GCM was checked against a NIST Known Answer Test vector, confirming both
the ciphertext and the authentication tag for a known key, nonce, and input. It
was additionally checked with a round-trip test, where decryption of the
produced ciphertext returns the original plaintext, and with a forgery-rejection
test, where a modified tag is correctly rejected.

Ascon-AEAD128 was checked against a vector from the Lightweight Cryptography
Known Answer Test set, confirming the combined ciphertext and tag for a known
key and nonce. It was likewise checked with a round-trip test and a
forgery-rejection test.

Both verification routines run on the target hardware at startup, before the
benchmark begins, and print a pass result over the serial link. A failure halts
interpretation of any subsequent timing for that build.

## 3.6 Measurement Methodology

### 3.6.1 Timing Source

Both boards use the TIM2 timer as the timing source. TIM2 is a 32-bit timer on
both families, and it is configured identically on each board as a free-running
up-counter driven by the internal clock with the prescaler set to zero. With a
zero prescaler the counter increments once per processor clock cycle, so one
tick equals one cycle. At 48 MHz the 32-bit counter wraps approximately every 89
seconds, which is far longer than any single measurement. All elapsed-time
computations use unsigned 32-bit subtraction, which handles a single wrap during
a measurement correctly without special-case logic.

The Cortex-M0 on the F072 does not provide the Data Watchpoint and Trace cycle
counter that is available on the Cortex-M4F. Using TIM2 on both boards therefore
gives a comparison between identically configured peripherals rather than
between two architecturally different timing mechanisms, which would not be
directly comparable. TIM2 is the reported timing source on both boards.

### 3.6.2 Interrupt Masking and Warmup

The benchmark macro disables all maskable interrupts for the duration of the
measured region and re-enables them afterward. This prevents the periodic system
tick interrupt and any peripheral interrupts from polluting short measurements.
The effect was confirmed during validation, where masking reduced the
per-iteration variation from roughly 28 ticks to zero on a reference workload.

Each measurement runs the workload once before the timed iterations begin, and
the result of this first run is discarded. This warmup primes the L476 ART
accelerator and any related microarchitectural state. On the L476 the first run
differs from the steady state by roughly 1.5% at small sizes. On the
F072 there is no measurable warmup effect, because the Cortex-M0 has no
instruction cache or branch predictor that could be cold.

### 3.6.3 Defeating Dead-Code Elimination

At higher optimization levels the compiler can remove a computation whose result
is never used. If this happened, the benchmark would time an empty loop. To
prevent it, each workload writes one byte of its output into a `volatile`
variable. The `volatile` qualifier forces the compiler to produce the output,
because it cannot prove the write is unnecessary. This protection is verified
indirectly by checking that the smallest input size still records a non-zero
time at every optimization level, as described in Section 3.9.

### 3.6.4 Scope of the Timed Region

The timed region contains only the authenticated-encryption operation. For
AES-128-GCM the key schedule is performed once before the measurements begin and
is not included. For Ascon-AEAD128 the single-pass interface performs key setup
as part of the encryption call and cannot separate it, so the full call is
timed. This treats the one-time setup symmetrically, in that the repeated
per-call cost is what is measured for both, and the fixed setup that a real
deployment would perform once is excluded from both where the interface allows.

All measurements encrypt plaintext with no associated data. The comparison
therefore concerns the authenticated encryption of a message payload.

### 3.6.5 Output Format and Offline Statistics

Each measured iteration is streamed over the serial link as a row of
comma-separated values containing the algorithm, the board, the clock frequency,
the input size, the iteration index, and the measured ticks. A terminating line
marks the end of a run. Summary statistics, namely the median, minimum, maximum,
and interquartile range, are computed offline rather than on the device. This
keeps the on-device harness minimal and allows the analysis to be revised
without re-running the measurements.

Under interrupt masking the per-iteration variation was zero on both boards for
the workloads measured, so the median, minimum, and maximum coincide. This is a
consequence of the deterministic execution of these workloads once interrupts
are removed, and it is reported as a property of the measurement rather than
assumed.

## 3.7 Benchmark Parameters

### 3.7.1 Input Sizes

Message sizes are swept on a logarithmic scale. On the L476 the sizes are 1, 10,
100, 1000, and 10000 bytes. On the F072 the largest size is omitted, because the
buffers required for a 10000-byte message do not fit within the 16 KB of SRAM,
so the F072 sizes are 1, 10, 100, and 1000 bytes. The logarithmic spread
separates the fixed per-call cost, which dominates at small sizes, from the
per-byte cost, which dominates at large sizes.

Each size is measured for 100 iterations after the discarded warmup run.

### 3.7.2 Optimization-Level Matrix

Each algorithm on each board is compiled at five optimization levels, namely
`-O0`, `-O1`, `-O2`, `-O3`, and `-Os`. This sweep serves two purposes. It shows
how much of the measured performance depends on optimization rather than on the
algorithm itself, which is the subject of the third research question, and it
identifies the level at which each algorithm performs best, which differs by
algorithm and by architecture. Reporting only a single optimization level would
hide both effects.

## 3.8 Footprint Measurement

Code size is measured as a static property of the compiled binaries using
`arm-none-eabi-size`, which reports the size of the program text, the
initialized data, and the zero-initialized data sections. Flash usage is taken
as the sum of the text and initialized-data sections. RAM usage is taken as the
sum of the initialized-data and zero-initialized-data sections.

Because a single binary links both algorithms together with the common platform
and harness code, the size of one combined binary cannot attribute code to one
algorithm or the other. To obtain a per-algorithm figure, three build variants
are produced from the same source through a compile-time selection. A baseline
variant contains the platform and harness code with no cryptographic
implementation. An AES variant adds the AES-128-GCM implementation. An ASCON
variant adds the Ascon-AEAD128 implementation. The marginal cost of each
algorithm is the difference between its variant and the baseline. This isolates
the code and memory that each algorithm adds on top of the common overhead.

Footprint is reported primarily at the size-optimization level, because that is
the configuration a memory-constrained deployment would use, and it is the level
at which the code-size comparison is most relevant to the constrained-device
framing. Footprint at the other optimization levels is also recorded, because
the code size of the ASCON reference implementation varies considerably with
optimization, which is reported in the results.

The RAM figures include the fixed measurement buffers used by the benchmark,
which are identical across the crypto variants. The working memory of the
cryptographic contexts themselves is small relative to these buffers. This is
noted so that the RAM figures are not read as the working memory of the
algorithms alone. `[confirm final framing of the RAM caveat]`

## 3.9 Harness Validation

Before any cryptographic code was measured, the harness was validated with a
`memcpy` workload of known, simple behavior, measured at sizes 1, 10, 100, and
1000 bytes for 100 iterations each. Four checks were defined. The measured time
should grow roughly in proportion to the input size, allowing for a fixed
measurement overhead. The per-iteration variation should be at most a few ticks.
The smallest input size should record a non-zero time, which confirms the
workload was not eliminated by the compiler. The reported clock frequency should
read 48 MHz on both boards.

All four checks passed on both boards. The per-iteration variation was zero on
both boards after the warmup run. The measured ratio between the two boards for
this memory workload settled at approximately 2.8 to 1 at the largest size,
which is the architectural cost of the Cortex-M0 relative to the Cortex-M4F at
the same clock for this workload. This figure serves as a reference point for
interpreting the cryptographic ratios between the two boards.

## 3.10 Reproducibility and Known Limitations

For reproducibility, the exact mbedTLS configuration is committed to the
repository, and the commit hashes of mbedTLS and the ASCON reference
implementation are recorded `[record hashes]`. The compiler, CMake, Ninja, and
CubeCLT versions are recorded, as are the board hardware revisions and the
ST-LINK firmware versions. The two reference `memcpy` measurements are archived
as baselines, and any future change to the harness is validated by reproducing
them to within one tick.

Several limitations are disclosed for honesty of interpretation. The reported
times include a small fixed overhead from the timer read pair, the loop branch,
and the `volatile` store. At the largest size this overhead is on the order of
one percent of the total. At the smallest size it dominates, so the
smallest-size figures should be read as a measurement of fixed per-call cost
rather than of encryption work. The harness does not subtract this overhead, and
raw ticks are reported as measured. The AES-GCM measurements use the small GHASH
table, as disclosed in Section 3.4.1, and therefore represent the memory-frugal
end of AES-GCM rather than its fastest configuration. The ART accelerator is
left enabled on the L476, which is the realistic deployment configuration, and
cycle counts are reported so that the comparison does not depend on its effect.
Flash wait states are left at the values set by the generated initialization for
each board.
