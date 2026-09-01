# pq-handshake-constrained

Reproduction package for a study of **post-quantum handshake cost on constrained links**,
comparing **EDHOC over CoAP** (RFC 9528 / RFC 9668) against **DTLS 1.3** (RFC 9147) when
credentials grow to ML-KEM / ML-DSA sizes.

Everything here runs on a laptop. **No quantum hardware, no GPU, and no PQC library is
needed**: the argument is about message *size*, so the experiments pad payloads and
certificates to post-quantum sizes rather than computing real post-quantum primitives.

## The question

RFC 9668 §1 states, of the EDHOC-over-CoAP optimisation:

> "The performance advantage of using this optimization **can be lost** when used in
> combination with Block-wise transfers [RFC7959] that rely on specific parameter values and
> block sizes."

and makes the two-round-trip minimum conditional on `message_3` being

> "**relatively small** ... thus allowing additional OSCORE-protected CoAP data **within
> target MTU sizes**."

Post-quantum credentials break exactly that size condition. This package measures what happens
when they do.

## Layout

```
analysis/   closed-form models (no network, instant)
  a1_size_ratio.py         byte ratio EDHOC vs DTLS, 9 NIST parameter sets
  a2_transport_mode.py     round trips: CoAP block-wise (lock-step) vs DTLS (flight)
  a3_blocksize_sweep.py    sweep every RFC 7959 block size; is there a setting that helps?
  a4_per_message.py        per-message split; floor of the argument

measure/    real network measurements
  m1_coap_blockwise.py     aiocoap over UDP, datagrams counted by a relay
  m2_dtls_flights.py       GnuTLS DTLS, datagrams AND direction changes counted
  m3_fragment_threshold.py ** the decisive one ** does DTLS complete at PQ sizes?

results/    JSON written by the scripts. Numbers quoted in the paper come from here,
            never typed by hand.
```

## Install

```bash
conda create -n pqhs python=3.11 -y && conda activate pqhs
pip install aiocoap
# DTLS: GnuTLS and/or OpenSSL must be on PATH
#   Debian/Ubuntu:  sudo apt install gnutls-bin openssl
#   macOS:          brew install gnutls    (Apple's LibreSSL does NOT work, see below)
```

## Run

```bash
bash scripts/run_all.sh
```

Each script prints its own reading of its own output, states what it does **not** establish,
and writes machine-readable JSON to `results/`.

## What is established, and what is not

| claim | status |
|---|---|
| CoAP block-wise costs one round trip per block | ✅ measured, aiocoap, 7/7 agreement with the model |
| DTLS round trips stay constant as the handshake grows | ✅ measured, GnuTLS, datagrams ×1.37 while round trips ×1.00 |
| DTLS **fails to complete** past ~23 fragments | ⛔ **RETRACTED.** It did not reproduce under a systematic sweep: GnuTLS fails at 10 fragments (MTU 600) yet succeeds at 22 (MTU 250), so no threshold exists. The original observation was an artefact of a broken harness, see below. |
| DTLS 1.3 completes in 2 round trips | 📚 cited from RFC 9147, **not** measured here: no available implementation offers DTLS 1.3 (OpenSSL 3.6.4's `s_server` still has no `-dtls1_3`) |
| Three implementations behave very differently on a constrained link | ✅ measured on Linux, see below |
| Latency and energy on a real 802.15.4 mesh | ⛔ **not measured.** Round-trip counts here are transport-level, on loopback. |

## Three implementations, three different limits

Measured on Ubuntu 24.04 at MTU 102, the payload an IEEE 802.15.4 frame carries after MAC and
AES-CCM*. Certificates of 1090, 3170 and 5600 bytes stand in for post-quantum credentials.

| implementation | at MTU 102 | what bounds it | cells completed |
|---|---|---|---|
| **mbedTLS 3.6.2** | completes, including 32 fragments | nothing found in range | 14/14 |
| **GnuTLS 3.8.13** | completes to ~23 fragments | **fragment count**, 23 ok / 28 fails | 17/21 |
| **OpenSSL 3.6.4** | never completes | **MTU floor at 256** (`DTLS1_MIN_MTU`), 250 fails / 300 ok | 9/21 |

The axes are orthogonal and each separates its own implementation cleanly: OpenSSL fails with
five fragments at MTU 250 and completes with nineteen at MTU 300, so fragment count explains
nothing there; GnuTLS completes at MTU 102, so an MTU floor explains nothing there.

This inverts the expectation the work started from. The search was for evidence that DTLS
breaks under post-quantum credential sizes. What breaks is the *server-side* software:
OpenSSL cannot run DTLS on an 802.15.4 link at any credential size, classical ones included.
The implementation actually deployed on constrained devices handles the constrained link.

Because the three differ so widely, none of this supports a statement about DTLS the protocol.
It is a statement about three implementations, and the script says so in its own verdict.

**One pair is excluded rather than reported as a failure.** mbedTLS cannot load the 15360-bit
key at all (`mbedtls_x509_crt_parse_file` returns -0x3b00, exceeding `MBEDTLS_MPI_MAX_SIZE`).
Its seven cells for that certificate read as "fails at every MTU including 600 with ten
fragments", which looks like a link result; the library never reached the link. The positive
control runs per (implementation, credential) pair to catch exactly this.

## A retracted finding, kept on the record

An earlier version of `m2` appeared to show that DTLS handshakes fail once a handshake message
exceeds roughly 23 fragments, which would have been a striking result at post-quantum sizes.
It was wrong, and the way it was wrong is worth stating.

The probe ran `echo q | gnutls-cli ...` through `subprocess.run(shell=True, timeout=...)`. On
timeout Python kills the *shell*, but the client process survives holding the pipe, so the
read blocks indefinitely. The tell was in the data: a timeout set to 120 s recorded elapsed
times of up to **12,593 s**, longer than the entire run. Cases where the harness gave up were
being recorded as handshake failures.

`m3` now separates three outcomes rather than two (`ok`, `timed_out`, genuine failure), runs
probes without a shell pipeline, and kills the whole process group on timeout. Collapsing
"timed out" into "failed" is how a convincing but non-existent threshold gets manufactured.

What survives untouched is the flight-versus-block-wise comparison, because it is measured by
counting datagrams at a relay rather than through that harness.

## Known environment traps

Documented because each one produced a wrong result before it was found.

- **Apple's LibreSSL (3.3.6) cannot complete a DTLS handshake against itself.** The client
  writes the ClientHello and then reports `CONNECT_CR_SRVR_HELLO: read timeout expired`. Use
  GnuTLS, or a real OpenSSL build.
- **Do not detect handshake success by grepping for `cipher`.** A *failed* OpenSSL handshake
  also prints `New, (NONE), Cipher is (NONE)`. Success must be evidence only a successful run
  can produce.
- **aiocoap: patching `numbers.constants.MAX_REGULAR_BLOCK_SIZE_EXP` has no effect** after
  import. `interfaces.py` binds it to a class attribute at import time; patch the class.
- **aiocoap decides whether to use block-wise via `maximum_payload_size` (default 1124)**, not
  via the block size. Lower it to the frame payload or block-wise never engages.
- **Counting server-side handler invocations does not count round trips.** aiocoap's
  `Block2Cache` calls the resource handler once and slices the body from cache. Count
  datagrams on the wire instead.

## Licence

Code MIT. Paper text is not included here.
