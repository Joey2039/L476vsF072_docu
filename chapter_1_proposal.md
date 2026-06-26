# Chapter 1 — Introduction (Draft Proposal)

> Working draft — adjust freely. Placeholders are marked `[...]`.

---

## 1.1 Cryptography in the Automotive Domain

Modern vehicles are no longer purely mechanical systems. Today's cars contain upwards of `[N]` Electronic Control Units (ECUs) responsible for functions ranging from engine management and brake control. Also infotainment, over-the-air software updates, and vehicle-to-everything are all features relying on ECUs. Due to the shear amount of feature these systems become increasingly more connected. All these connections can be seprerated in two caterories. On the one hand there are internal ones, which are mostly bus protocols such as CAN, LIN, and Automotive Ethernet. On the other there are external connections (e.g.V2X and telematics interfaces). Those cirumstances increase parallel the attack surface exposed to adversaries. A successful intrusion into a safety-relevant ECU carries consequences that extend well beyond data loss. It can compromised brake controllers, manipulated steering actuators, or falsified sensor data, which directly can endanger human lives.

Cryptographic protection of ECU communication is therefore not optional. Standards such as AUTOSAR SecOC (Secure Onboard Communication) and the ISO/SAE 21434 are established requirements for message authentication and confidentiality across the vehicle network. In practice, the algorithm most common to fulfill these requirements is the Advanced Encryption Standard (AES). It has served as the global symmetric encryption standard since its NIST standardization in 2001 and is deeply embedded in automotive security stacks, ranging from hardware security modules (HSMs) to communication middleware.

## 1.2 Cryptographic Requirements of Modern ECUs

ECUs span a wide spectrum of computational capability. On the high end are domain controllers, which are managing ADAS functions or running an automotive-grade operating system for example.These may be equipped with multi-core processors, dedicated cryptographic co-processors, and several megabytes of RAM. At the other end of the spectrum are simple body control modules, sensor nodes, and actuator controllers. Those ECUs are built around low-cost 32-bit microcontrollers with RAM measured in tens of kilobytes, and no hardware cryptographic accelerator. Those devices are where the computational cost of cryptographic operations becomes a real concern.

For such limited ECUs, the cryptographic primitive must satisfy several requirements simultaneously: it must provide authenticated encryption with associated data (AEAD) to guarantee confidentiality, integrity, and authenticity in a single pass; it must execute within a time budget that does not interfere with real-time control tasks; and its implementation must fit within the available Flash and RAM without displacing application code. These requirements motivate a closer examination of whether AES-128-GCM — designed for general-purpose hardware — remains the most appropriate choice for every node in the vehicle network, or whether purpose-built lightweight alternatives deserve consideration.

## 1.3 The Limits of AES on Low-End Microcontrollers

AES-128-GCM is the dominant AEAD construction in modern security protocols and is well understood with respect to both security and implementation. On hardware that includes a dedicated AES accelerator, it executes efficiently and introduces negligible overhead. However, a large portion of automotive microcontrollers — particularly those in cost-sensitive, high-volume applications — are based on simple 32-bit cores such as the ARM Cortex-M0, which provide no hardware cryptographic acceleration. On these platforms, a software implementation of AES-128-GCM must perform the full AES key schedule and block cipher in software, and the GCM authentication step requires a 128-bit polynomial multiplication (GHASH) that maps poorly onto a minimal instruction set without hardware multiply-accumulate support. The result can be an implementation that is slower, larger in code size, or more energy-intensive than the available budget permits.

This raises a practical engineering question: for constrained ECUs where AES hardware acceleration is absent, is there a standardized alternative that offers better performance characteristics without sacrificing security?

## 1.4 The NIST Lightweight Cryptography Standardization Process

Recognizing the growing need for cryptographic primitives suited to constrained devices, the National Institute of Standards and Technology (NIST) initiated a Lightweight Cryptography (LWC) standardization project in 2018 `[cite NIST LWC call]`. The process evaluated `[N]` submissions across multiple rounds, assessing candidates for security, performance on constrained hardware, and implementation simplicity. In February 2023, NIST announced ASCON as the winner of the standardization effort `[cite NIST LWC announcement 2023]`. ASCON is a family of lightweight cryptographic algorithms based on a sponge construction, designed from the ground up for efficient software implementation on small processors. Its selection provides the embedded and automotive security community with a standardized, well-analyzed alternative to AES-GCM for use cases where resource constraints are the primary concern.

Despite this standardization, ASCON adoption in automotive and industrial embedded systems remains limited. AES continues to dominate deployed security stacks, in part due to inertia, existing hardware support, and a lack of quantitative performance data on representative automotive-class microcontrollers. This work aims to contribute directly to closing that gap.

## 1.5 Objective and Research Questions

This paper presents a quantitative benchmark comparing Ascon-AEAD128 and AES-128-GCM on two ARM Cortex-M microcontrollers representative of the low-to-mid range of the automotive ECU spectrum: the NUCLEO-F072RB (Cortex-M0, 48 MHz) and the NUCLEO-L476RG (Cortex-M4F, 80 MHz). Both boards serve as a simulation of the resource conditions found in constrained automotive ECUs. All measurements use software-only implementations to ensure a fair, hardware-accelerator-independent comparison applicable to the broadest range of real-world deployments.

The following research questions guide the study:

1. **Performance:** How do Ascon-AEAD128 and AES-128-GCM compare in execution time and throughput across a range of message sizes on each platform?
2. **Memory:** What are the Flash and RAM footprints of each implementation relative to the constraints of a typical automotive microcontroller?
3. **Optimization sensitivity:** How does compiler optimization level affect the relative performance of the two algorithms?
4. **Architecture dependence:** Does the performance gap between the two algorithms differ between the Cortex-M0 and Cortex-M4F, and what does this imply for ECU selection?

## 1.6 Structure of This Paper

The remainder of this paper is organized as follows. Chapter 2 provides the technical background on AES-128-GCM, the ASCON family, and the target hardware platforms. Chapter 3 describes the benchmark methodology, including the measurement setup, timing approach, library selection, and build configuration. Chapter 4 presents the measurement results. Chapter 5 discusses the findings in the context of the research questions and draws practical conclusions for algorithm selection on constrained automotive hardware. Chapter 6 concludes the paper and outlines directions for future work.
