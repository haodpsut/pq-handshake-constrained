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
| DTLS **fails to complete** past ~23 fragments | ⚠ **one implementation only** (GnuTLS 3.8.13). `m3` exists to test this against others. Do not cite until it reproduces. |
| DTLS 1.3 completes in 2 round trips | 📚 cited from RFC 9147, **not** measured here: no DTLS 1.3 implementation was available |
| Latency and energy on a real 802.15.4 mesh | ⛔ **not measured.** Round-trip counts here are transport-level, on loopback. |

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
