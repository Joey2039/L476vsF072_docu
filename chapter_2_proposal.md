# Chapter 2 — Background (Draft Proposal)

> Working draft — adjust freely. Placeholders are marked `[...]`.

---

## 2.1 Authenticated Encryption with Associated Data (AEAD)

Cryptographic protocols for embedded communication commonly require three security objectives at once: confidentiality (to prevent unauthorized reading of the message), integrity (to detect any modification while transmission) and authenticity (to verify that the message originates from a legitimate sender). Traditionally, these properties were achieved by combining a separate cipher
with a message authentication code (MAC). However, the secure composition of two independent primitives is non-trivial. The order of operations matters, and incorrect combinations can introduce vulnerabilities even when each primitive is individually sound. Authenticated Encryption with Associated Data (AEAD) addresses this by combining all three objectives into a single, unified primitive.

An AEAD scheme takes four inputs: a secret key `K`, a nonce `N` (a value that must be unique per encryption under a given key), a plaintext message `M`, and a block of associated data `AD`. The associated data is authenticated but not encrypted. It remains readable in the clear while being bound to the ciphertext via the authentication tag. The scheme produces a ciphertext `C` and an authentication tag `T`. Decryption takes the same key and nonce as wells as the ciphertext, tag, and associated data and it returns the recovered plaintext, but only if the tag verifies successfully. Otherwise it returns an explicit failure. This fail-closed behavior is essential, especially for embedded. The reason for that is when a receiver that processes unauthenticated data before the verification completes is vulnerable to plaintext-dependent side channels and fault injection.

For the constrained microcontroller setting considered in this work, two AEAD properties are of particular practical relevance. First the single-pass processing, which absorbs plaintext and produces the authentication tag in one sequential pass over the data. This minimizes RAM requirements by avoiding the need to buffer the full message. The second propertie is that a compact state and key schedule are reducing the code size and the initialization overhead. Both of which are essential on devices with a limited Flash. These properties will later serve as evaluation criteria when comparing AES-128-GCM and Ascon-AEAD128.

---

## 2.2 AES-128-GCM

### 2.2.1 The AES Block Cipher

The Advanced Encryption Standard (AES) is a substitution-permutation block cipher standardized by NIST in 2001 `[cite FIPS 197]`. It operates on a fixed block size of 128 bits and supports key lengths of 128, 192, or 256 bits. This work uses the 128-bit key variant excusivly, AES-128. It applies ten rounds of transformation to a 4×4 byte state matrix. Each round consists of four operations: `SubBytes` (a non-linear byte substitution via the AES S-box), `ShiftRows` (a cyclic shift of state rows), `MixColumns` (a linear diffusion step operating on state columns in GF(2⁸)), and `AddRoundKey` (XOR of the state with a round-specific subkey). The 128-bit key is expanded into eleven round keys before encryption begins. This process is known as the key schedule.

The security of AES rests on public cryptanalysis for more than two decades. No practical attack against the full cipher is known. That is part of the reason why it is so trusted. Whit hardware acceleration, a dedicated AES engine, the cipher executes at throughputs measured in gigabits per second. On a software-only Cortex-M0 implementation, however, the `MixColumns` step and the S-box lookups impose a considerable cycle cost. This is due to the fact, that the M0 lacks the wider data path as well as the lookup acceleration found on higher-end cores. This performance gap on a minimal instruction set architectures is the central motivation for evaluating a lightweight alternative.

### 2.2.2 Galois/Counter Mode (GCM)

AES alone is a block cipher and not an AEAD scheme, it encrypts exactly one 128-bit block and provides no authentication. Galois/Counter Mode (GCM) combines AES in counter mode (CTR) for encryption with a polynomial hash (GHASH) for authentication. This yields an AEAD construction `[cite NIST SP 800-38D]`.

In CTR mode, a counter value is encrypted by AES and the resulting keystream block is XORed with the plaintext. The counter is incremented for each successive block, which enables parallelized encryption independent from plaintext content. GHASH computes a 128-bit authentication tag using polynomial operations over the ciphertext blocks and associated data. It operates in GF(2¹²⁸), a finite field defined over 128-bit values. The hash key `H` is derived by encrypting a zero block under the session key at initialization.

GCM's parallelizability is its primary advantage on general-purpose hardware with wide data paths. Its principal weakness on constrained processors is the GHASH step: multiplication in GF(2¹²⁸) requires either a hardware carry-less multiply instruction or a software implementation using multiple 32-bit operations. The Cortex-M0 provides only a 32-bit multiply without a carry-less variant, so a software GHASH implementation on that core requires a series of XOR and shift operations that contribute noticeably to the total cycle count. Additionally, GCM requires a unique nonce per encryption; nonce reuse under the same key is catastrophic, recovering both the hash key and the plaintext with a small number of observed ciphertexts.

### 2.2.3 Hardware Acceleration on ARM Cortex-M4

The STM32L476RG used in this work is built around an ARM Cortex-M4F core that provides optional hardware AES acceleration via a dedicated AES peripheral in the STM32 security subsystem. This peripheral can execute AES-128 encryption and decryption entirely in hardware, offloading the block cipher from the CPU and yielding throughputs far exceeding any software implementation on the same device.

For the purposes of this benchmark, the hardware AES peripheral is explicitly disabled. The goal of this study is to evaluate the software-only performance of each algorithm. On representative microcontroller cores, independent of any vendor-specific accelerator. Enabling the hardware peripheral would advantage AES-128-GCM on the L476RG in a way that is not reproducible on the majority of constrained 32-bit microcontrollers that ship without such a block. By holding the comparison to software implementations throughout, the results remain applicable to the broader class of devices the benchmark is intended to represent.

---

## 2.3 The ASCON Family

### 2.3.1 The ASCON Permutation

All ASCON variants use the same underlying permutation. It is written as p^a or p^b, depending on how many rounds are applied. The permutation operates on a 320-bit state organized as five 64-bit words `x0` through `x4`. Each round of the permutation applies three layers in sequence.

The first layer, `pC` (constant addition), XORs a round-specific constant into word `x2`, introducing asymmetry between rounds to prevent slide attacks. The second layer, `pS` (substitution), applies a 5-bit S-box in parallel to all 64 bit-sliced positions across the five state words. This S-box provides non-linearity with simple math. It was chosen for the efficiency of bitsliced implementation on processors with native 64-bit or 32-bit word operations. The third layer, `pL` (linear diffusion), applies independent linear transformations to each of the five state words using rotations and XOR, ensuring that differences propagate rapidly across the full state.

The combination of these three layers achieves the confusion and diffusion properties required for a secure permutation. The full ASCON permutation is build with twelve rounds (p¹²) for initialization and finalization. The internal process has either eight rounds (p⁸) or six rounds (p⁶), depending on the specific member of the family. On 32-bit microcontrollers the five 64-bit state words are held in pairs of 32-bit registers. So the rotation-and-XOR structure of the linear layer can efficiently mapped onto the available register file without memory traffic.

### 2.3.2 Sponge and Duplex Construction

ASCON uses a sponge-based construction, specifically the duplex variant, rather than the block-cipher-mode approach used by AES-GCM. The sponge model divides the register into two parts: the rate `r` (the part that interfaces with input and output) and the capacity `c` (the part that remains hidden from I/O, forming the security margin). For Ascon-AEAD128, the rate is 128 bits and the capacity is 192 bits, giving a total register of 320 bits.

In the duplex variant, used for AEAD, the plaintext is XORed into the rate portions of the register. One rate-sized block at a time is being absorped followed by the permutation. The ciphertext is extracted from the register after the absorption, mixing encryption and authentication in a single sequential pass. This single-pass property means that memory buffering of the full message is never required. This is a significant advantage over constructions that must process the ciphertext twice (once for decryption, once for authentication).

The capacity portion of the register is never directly observable by an attacker and provides the security guarantee. For Ascon-AEAD128, the 256-bit capacity yields a claimed security level of 128 bits against generic attacks on both confidentiality and integrity.

### 2.3.3 Ascon-AEAD128

Ascon-AEAD128 is the primary AEAD member of the ASCON family and the algorithm selected as the NIST Lightweight Cryptography standard `[cite NIST LWC announcement 2023]`. It accepts a 128-bit key, a 128-bit nonce, associated data of arbitrary length, and a plaintext of arbitrary length, and produces a ciphertext of the same length as the plaintext together with a 128-bit authentication tag.

The processing pipeline proceeds in four phases. In the initialization phase, the 320-bit register is assembled from the key, nonce, and algorithm-specific initialization vector, then transformed by p¹². In the associated data phase, the associated data is absorbed into the rate in 64-bit blocks, each followed by p⁶. The last block is padded, additonally a domain separation constant is XORed into the register at the end of this phase. In the encryption phase, plaintext blocks are absorbed and ciphertext blocks are extracted in the same pass, each followed by p⁶. In the finalization phase, the key is XORed into the register. Also p¹² is applied and the authentication tag is extracted from the last 128 bits of the register.

For the benchmark in this work, Ascon-AEAD128 is evaluated using the official ASCON reference implementation and the optimized 32-bit implementation provided by the ASCON team `[cite ASCON software]`. Both implementation variants will be benchmarked to distinguish the effect of algorithmic complexity from low-level implementation quality.

### 2.3.4 Ascon-Hash256

Ascon-Hash256 is the hash function member of the ASCON family. It produces a 256-bit digest from an input of variable length using the same p¹² permutation as Ascon-AEAD128. The message absorption proceeds in 64-bit rate blocks, each followed by p¹², and the digest is squeezed in two 64-bit output blocks after all input has been absorbed.

While the primary benchmark focus of this work is the AEAD comparison, Ascon-Hash256 is included as an optional extension for completeness. A secondary hash comparison against SHA2-256 would illustrate whether ASCON's performance advantage, if observed in AEAD, extends to hashing workloads as well.

### 2.3.5 Ascon-80pq and the Post-Quantum Outlook

Ascon-80pq is a variant of Ascon-AEAD128 that extends the key length from 128 to 160 bits while keeping the nonce at 128 bits and the tag at 128 bits. The longer key is a precautionary measure against Grover's algorithm, a quantum search algorithm that effectively halves the security level of a symmetric key in bits against an adversary with a large-scale quantum computer. A 128-bit key offers approximately 64-bit post-quantum security under Grover's model, while the 160-bit key of Ascon-80pq provides approximately 80-bit post-quantum security — a modest but meaningful margin increase at negligible additional cost.

The performance overhead of the 160-bit key variant relative to Ascon-AEAD128 is limited to initialization, where the additional 32 bits are incorporated into the state setup. The permutation rounds and data processing phases are identical. Ascon-80pq is therefore of interest as a forward-compatible migration path for automotive security architectures that must account for long vehicle service lifetimes, during which the practical capabilities of quantum computing may evolve.

---

## 2.4 Architectural Comparison: Sponge vs. Block Cipher + GCM

The structural differences between AES-128-GCM and Ascon-AEAD128 have concrete implications for software performance on constrained microcontrollers, which are worth making explicit before the benchmark results are presented.

AES-128-GCM is built from two largely independent components: the AES block cipher and the GHASH authenticator. Each has its own state, key material, and processing requirements. The AES key schedule expands 128 bits into 176 bytes of round keys that must either be precomputed and stored in RAM or recomputed for each execution. The GHASH state requires an additional 128-bit accumulator and the hash key `H`. On a Cortex-M0 without hardware multiply, GHASH is the performance bottleneck for short messages, since its initialization cost (one AES block encryption) is spread poorly at small input sizes.

Ascon-AEAD128 holds its entire state in the 320-bit permutation input. There is no separate key schedule: the key is absorbed directly into the state during initialization. The permutation is defined entirely by bitwise rotations and XOR, operations that are cheap on any 32-bit or 64-bit processor without specialized hardware. The absence of S-box table lookups also eliminates a class of cache-timing side channels that must be considered when deploying AES on processors without constant-time hardware support.

One relevant trade-off is that the ASCON rate is only 64 bits per permutation execution for Ascon-AEAD128, compared to 128 bits per block for AES. For large messages, this narrower rate means more permutation calls per byte of data processed. Whether Ascon-AEAD128 or AES-128-GCM requires fewer cycles on a given platform cannot be determined theoretically. This is a practical question, and answering it is the central goal of this benchmark.

---

## 2.5 Target Platforms

### 2.5.1 ARM Cortex-M0 — NUCLEO-F072RB

The NUCLEO-F072RB board is built around the STM32F072RB microcontroller, which integrates an ARM Cortex-M0 core clocked at up to 48 MHz in this benchmark configuration. The Cortex-M0 is the smallest and most constrained member of the ARM Cortex-M family. It implements the ARMv6-M instruction set architecture, a minimal 16/32-bit Thumb instruction set without the DSP extensions, floating-point unit, or hardware divide instruction present in larger M-class cores. The core has no instruction or data caches. Flash wait states are determined by the operating frequency and the internal flash controller configuration.

Relevant characteristics for this benchmark are the absence of a hardware multiply-accumulate that would accelerate GHASH. Also absente are the two-cycle multiply latency for the available 32×32-bit multiply (which produces a 32-bit result), as well as the lack of a Data Watchpoint and Trace (DWT) unit with a cycle counter. Because the DWT cycle counter is not present on the M0, cycle-accurate measurement on this board uses TIM2. It is configured as a 32-bit free-running counter driven by the system clock, providing microsecond-resolution timing without external hardware.

The F072RB is representative of the lowest tier of 32-bit microcontrollers found in automotive body and sensor applications, where unit cost and power consumption are the dominant design constraints.

### 2.5.2 ARM Cortex-M4F — NUCLEO-L476RG

The NUCLEO-L476RG board is built around the STM32L476RG microcontroller, which integrates an ARM Cortex-M4F core clocked at up to 80 MHz in this benchmark configuration. The Cortex-M4F implements the ARMv7E-M instruction set architecture, which extends the ARMv6-M. It adds DSP-oriented instructions including a single-cycle 32×32-bit multiply with 64-bit accumulate (`MLA`, `SMLAL`), single-instruction saturating arithmetic, and a single-precision floating-point unit (FPU). The core also includes an Adaptive Real-Time (ART) memory accelerator, which implements an instruction prefetch buffer as well as a branch cache to reduce Flash access latency at high operating frequencies.

For timing, the Cortex-M4F provides a DWT unit including the `DWT->CYCCNT` cycle counter, which is a 32-bit register incremented on every processor clock. This counter can be read with a single memory-mapped register access and provides cycle-accurate measurement without consuming a hardware timer peripheral.

The L476RG additionally incorporates a hardware AES peripheral. As noted in Section 2.2.3, this peripheral is disabled in the benchmark build to ensure that all measurements reflect software-only performance. The ART accelerator state is documented as part of the build configuration, as instruction prefetching can affect cycle counts depending on the branch structure of the executed code.

The L476RG is representative of a mid-range automotive microcontroller, suitable for body control modules and sensor fusion nodes with moderate processing requirements. Together with the F072RB, the two boards span a performance range relevant to the lower half of the automotive ECU spectrum.

---

## 2.6 Related Work

Performance comparisons between ASCON and AES-GCM on embedded hardware have appeared in several contexts since ASCON's selection as the NIST LWC standard. Benchmarks conducted on AVR 8-bit and MSP430 16-bit platforms during the NIST LWC competition evaluation process demonstrated ASCON's advantage on ultra-constrained targets, but these results are not directly applicable to 32-bit ARM Cortex-M deployments that represent the current generation of automotive microcontrollers.

Work targeting ARM Cortex-M platforms specifically has been published both by the ASCON team and by independent researchers. The ASCON team provides cycle counts for their reference and optimized implementations on several Cortex-M targets `[cite ASCON software / ASCON performance data]`. However, published figures often report single-point measurements at a fixed message length rather than the throughput curves across a logarithmic range of input sizes that are needed to characterize behavior for the short messages typical in automotive CAN frames and sensor update packets.

To the authors' knowledge, no published work directly compares AES-128-GCM and Ascon-AEAD128 across both a Cortex-M0 and a Cortex-M4F target with a controlled, software-only methodology that includes compiler optimization level as an explicit variable. This work aims to fill that gap by providing reproducible benchmark data for both platforms under a unified measurement framework.
