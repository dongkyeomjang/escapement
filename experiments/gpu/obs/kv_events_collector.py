#!/usr/bin/env python3
"""KV cache event collector (GPU directive G-02 2.2, patch-free).

Subscribes to vLLM's ZMQ KV-event publisher (``--kv-events-config``) and
writes one JSON line per engine-step batch. It does not import vllm: batches
are decoded as plain msgpack. The wire layout (vllm/distributed/kv_events.py,
0.22.0) is multipart ``(topic, seq[8 bytes big endian], payload)`` where the
payload is ``KVEventBatch`` encoded ``array_like`` -> ``[ts, events, dp_rank?]``
and each event is a tagged array ``[tag, field1, field2, ...]``:

* ``BlockStored``  -> [tag, block_hashes, parent_block_hash, token_ids,
                       block_size, lora_id, medium, lora_name, extra_keys?,
                       group_idx?, kv_cache_spec_kind?, kv_cache_spec_sliding_window?]
* ``BlockRemoved`` -> [tag, block_hashes, medium, group_idx?]
* ``AllBlocksCleared`` -> [tag]

Trailing fields equal to their default are omitted (``omit_defaults``).
Block hashes are bytes on the wire and are written as hex.

Session attribution is by token content: synthetic prompts differ per
request, so a stored block's ``token_ids`` identify whose prefix it holds.
"""

from __future__ import annotations

import argparse
import json
import signal
import time

import msgspec
import zmq

STORED_FIELDS = ("block_hashes", "parent_block_hash", "token_ids", "block_size",
                 "lora_id", "medium", "lora_name", "extra_keys", "group_idx",
                 "kv_cache_spec_kind", "kv_cache_spec_sliding_window")
REMOVED_FIELDS = ("block_hashes", "medium", "group_idx")


def _h(x):
    if isinstance(x, (bytes, bytearray)):
        return x.hex()
    if isinstance(x, list):
        return [_h(v) for v in x]
    return x


def decode_event(raw) -> dict:
    tag, rest = raw[0], raw[1:]
    names = {"BlockStored": STORED_FIELDS, "BlockRemoved": REMOVED_FIELDS}.get(tag, ())
    ev = {"type": tag}
    for name, value in zip(names, rest):
        ev[name] = _h(value)
    if len(rest) > len(names):
        ev["_unparsed"] = _h(rest[len(names):])
    return ev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="tcp://127.0.0.1:5557")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    stop = False

    def _stop(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    ctx = zmq.Context()
    sub = ctx.socket(zmq.SUB)
    sub.connect(args.endpoint)
    sub.setsockopt(zmq.SUBSCRIBE, b"")
    dec = msgspec.msgpack.Decoder()
    n_batches = n_events = 0
    last_seq = None
    gaps = 0
    with open(args.out, "w") as f:
        while not stop:
            if not sub.poll(200):
                continue
            topic, seq_b, payload = sub.recv_multipart()
            recv_wall = time.time()
            seq = int.from_bytes(seq_b, "big")
            if last_seq is not None and seq != last_seq + 1:
                gaps += 1
            last_seq = seq
            batch = dec.decode(payload)
            ts, events = batch[0], batch[1]
            rec = {"seq": seq, "ts": ts, "recv_wall": recv_wall,
                   "events": [decode_event(e) for e in events]}
            f.write(json.dumps(rec) + "\n")
            f.flush()
            n_batches += 1
            n_events += len(events)
    print(json.dumps({"batches": n_batches, "events": n_events, "seq_gaps": gaps,
                      "first_seq_seen": None if last_seq is None else last_seq - n_batches + 1 + gaps}))
    sub.close(0)
    ctx.term()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
