# Chapter 5 — Discussion (Draft)

> Working draft. This chapter interprets the results from Chapter 4 in relation
> to the four research questions stated in Section 1.5, explains the mechanisms
> behind them, and draws practical conclusions. Citation placeholders use
> `[cite ...]`.

---

## 5.1 Performance (Research Question 1)

The first research question asks how the two algorithms compare in execution
time and throughput across message sizes on each platform. The measurements give
a clear answer. Ascon-AEAD128 was faster than AES-128-GCM at every measured
message size, on both boards, and at every optimization level. The advantage was
present both in the fixed per-call cost that dominates small messages and in the
per-byte cost that dominates large messages.

The two comparisions are worth separating, because the relevant one depends on the
message size a deployment actually handles. For short messages the fixed
per-call cost is decisive. At a single byte and `-O2`, Ascon-AEAD128 cost 7410
cycles against 25,185 cycles for AES-128-GCM on the Cortex-M0, and 4219 against
6470 cycles on the Cortex-M4F. For long messages the per-byte rate is decisive.
In the large-message region at `-O2`, Ascon-AEAD128 reached approximately 169
cycles per byte against 771 for AES-128-GCM on the Cortex-M0, and approximately
95 against 189 cycles per byte on the Cortex-M4F. Ascon-AEAD128 therefore leads
in both comparisions, so the conclusion does not depend on the message-size profile
of the application.

The reason for the difference lies in the structure of the two algorithms. AES
in software relies on table lookups for the substitution step, and the GCM
authentication step performs a multiplication in a binary field: This is built
from many smaller operations when no wide hardware multiplier is available.
Ascon-AEAD128 is built from a permutation of bitwise operations, namely
exclusive-or, bitwise-and, and rotation, applied to a small state held in
registers. These operations are native to both cores and require no table
memory. The single-pass duplex construction also avoids the separate encryption
and authentication passes that AES-128-GCM performs. The measured advantage is
the practical consequence of this design difference.

## 5.2 Memory (Research Question 2)

The second research question asks about the Flash and RAM footprint of each
implementation relative to the constraints of a small microcontroller. The
answer depends on the optimization level, and the size-optimized level is the
one relevant to a memory-constrained deployment.

At `-Os`, Ascon-AEAD128 added 4376 bytes of Flash on the Cortex-M0 and 4208
bytes on the Cortex-M4F, while AES-128-GCM added 16,500 and 15,776 bytes
respectively. AES-128-GCM therefore required approximately 3.8 times the code
space of Ascon-AEAD128, consistently on both boards. On the Cortex-M0, which has
128 KB of Flash, the difference between roughly 4 KB and roughly 16 KB is a
meaningful fraction of the budget once application code is also present. The
small code size of Ascon-AEAD128 follows from its single permutation and its
lack of any precomputed lookup tables, where AES-128-GCM brings the AES tables
and the field-multiplication code.

The RAM comparison is less sharp in these measurements, because the reported RAM
cost is dominated by the fixed measurement buffers rather than by the working
state of the algorithms. The cryptographic contexts themselves are small. The
AES-GCM context in the chosen configuration avoids the larger field
multiplication table, as disclosed in Section 3.4.1, so its working memory is
modest, and the Ascon-AEAD128 state is a few tens of bytes. The conclusion that
can be drawn safely from these measurements concerns Flash, where
Ascon-AEAD128 has a clear and reproducible advantage at the size-optimized
level.

It must be stated that this advantage at `-Os` does not hold at the
speed-oriented optimization levels, for reasons examined under Research Question
3. The footprint result is therefore reported at the optimization level that a
constrained deployment would actually choose, where Ascon-AEAD128 is both
smaller and, from the timing results, faster.

## 5.3 Optimization Sensitivity (Research Question 3)

The third research question asks how the compiler optimization level affects the
relative performance of the two algorithms. The measurements show that the
optimization level matters a great deal, in two distinct ways.

The first concerns execution time. The largest single improvement for both
algorithms came from enabling optimization at all, the step from `-O0` to `-O1`.
At 1000 bytes on the Cortex-M0 this step reduced the Ascon-AEAD128 time by a
factor of about eight and the AES-128-GCM time by a factor of about three. This
uneven response means the relative advantage of Ascon-AEAD128 is understated by
any measurement taken at `-O0`. A study that benchmarked only unoptimized code
would have reported the two algorithms as close, with a ratio of 1.16 on the
Cortex-M4F, and would have missed the larger advantage that appears under the
optimization a real build would use. The choice to sweep the optimization level,
rather than report a single level, is justified by this observation.

The behavior at the higher levels was not uniform. On the Cortex-M4F,
AES-128-GCM gained nothing from `-O3` over `-O2`, which is consistent with the
common observation that aggressive optimization yields little on these cores for
table-driven code, while Ascon-AEAD128 continued to improve at `-O3`. On the
Cortex-M0 the pattern was reversed, with AES-128-GCM improving substantially at
`-O3` and Ascon-AEAD128 improving only modestly. The `-Os` level was slower than
`-O2` for both algorithms on both boards, because size optimization disables the
inlining and loop unrolling that the cryptographic inner loops benefit from.

The second way the optimization level matters concerns code size, and it is the
more striking effect. The Flash cost of the Ascon-AEAD128 reference
implementation varied strongly with the optimization level, while the
AES-128-GCM cost was comparatively stable. The Ascon-AEAD128 cost rose from
`-O0` to a peak at `-O3`, reaching 43,024 bytes on the Cortex-M0 and 34,560
bytes on the Cortex-M4F, then fell sharply at `-Os` to roughly 4 KB. The cause
is the unrolling of the permutation. The permutation is a loop of rounds, and at
the speed-oriented levels the compiler unrolls these rounds into straight-line
code, which the authenticated-encryption routine then includes at several call
sites, so the code expands. At `-Os` the compiler keeps the rounds rolled, and
the code collapses to a small size. The same shape appeared on both boards,
which shows that the effect is a property of the implementation and the compiler
rather than of the processor.

This links the second and third research questions. The footprint advantage of
Ascon-AEAD128 is real but conditional on the optimization level. It exists at
`-Os` and is reversed at the speed-oriented levels. The advantage and the
condition should be reported together.

## 5.4 Architecture Dependence (Research Question 4)

The fourth research question asks whether the performance gap between the two
algorithms differs between the Cortex-M0 and the Cortex-M4F, and what this
implies for device selection. The measurements show that the gap is consistently
larger on the weaker core.

At equal clock frequency and at 1000 bytes, the ratio of AES-128-GCM time to
Ascon-AEAD128 time was about 4.6 at `-O1` and `-O2` on the Cortex-M0, against
about 2.0 at the same levels on the Cortex-M4F. At every optimized level the
ratio was larger on the Cortex-M0. The advantage of Ascon-AEAD128 therefore
grows as the processor becomes more constrained.

This can be read against the architectural baseline established in the harness
validation. For the plain memory workload the Cortex-M0 was about 2.8 times
slower than the Cortex-M4F at the same clock. If both algorithms simply scaled
with this architectural factor, their ratio to each other would be the same on
both boards. The fact that the AES-128-GCM disadvantage grows by more than this
factor on the Cortex-M0 indicates that AES-128-GCM contains operations that are
especially costly on the weaker core. The field multiplication in the GCM
authentication step is the principal example, because it must be synthesized
from many small operations when no wide hardware multiplier is present, which is
the case on the Cortex-M0. Ascon-AEAD128, built from operations the Cortex-M0
executes natively, stays closer to the architectural baseline.

The implication for device selection is direct. The more constrained the
processor, the stronger the case for Ascon-AEAD128 over AES-128-GCM. On the
lowest-end cores, which are also the most numerous and the most cost-sensitive,
the advantage is largest.

## 5.5 The Fairness of the Comparison

The comparison was designed to avoid handicapping either algorithm, and one
configuration choice deserves explicit defense. AES-128-GCM was measured with
the small field-multiplication table, as disclosed in Section 3.4.1. A larger
table exists that would improve the AES-128-GCM throughput, at a cost of roughly
3.8 KB of additional RAM that Ascon-AEAD128 does not require. The small table
was chosen because it represents a genuinely lightweight configuration of
AES-128-GCM, which matches the constrained-device setting of this work. On a
part with 16 KB of SRAM, spending close to 4 KB of RAM on an acceleration table
is exactly the kind of cost a constrained deployment may decline.

The reported AES-128-GCM figures therefore represent the memory-frugal end of
AES-128-GCM rather than its fastest possible configuration. Enabling the larger
table would narrow the throughput gap at large messages, at a RAM cost
Ascon-AEAD128 does not pay, and would not change the code-size or small-message
conclusions. The comparison is thus a fair one between two lightweight configurations. The configuration choice is named and justified, so the result cannot be read as a weakened AES-128-GCM.

## 5.6 Practical Conclusions

The results support a consistent practical recommendation for the class of
devices studied. For authenticated encryption on a constrained microcontroller
without hardware AES acceleration, Ascon-AEAD128 is the stronger choice on the
measured criteria. It was faster than AES-128-GCM at every message size and
optimization level, smaller in code at the size-optimized level that such a
device would use, and its advantage was largest on the most constrained
processor.

Two qualifications accompany this recommendation. First, the speed advantage and
the size advantage do not happen at the same optimization level for the
reference implementation. The size advantage holds at `-Os`, where
Ascon-AEAD128 is both smaller and faster than AES-128-GCM, so a deployment that
builds for size obtains both benefits at once. A deployment that builds for
speed at `-O2` or `-O3` obtains the speed advantage but accepts a larger
Ascon-AEAD128 code size than AES-128-GCM. This is due to the unrolling of the
permutation. Second, these conclusions concern software-only implementations.
On a device with a hardware AES accelerator the balance would differ, and that
case was deliberately outside the scope of this work in order to isolate the
software comparison.

Within those qualifications, the measurements give a quantitative basis for
preferring Ascon-AEAD128 on constrained, software-only targets, and they
quantify how the advantage grows as the device becomes more limited. This is the
gap in measurement-based data that the work set out to address.
