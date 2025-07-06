> **Scope**: minimal stream that Perl's `Devel::NYTProf::Reader` accepts. We copy constants from
> NYTProf v5.0.

### Top-level layout

```
"NYTPROF\0" magic (8 bytes, ASCII)
u32 version = 5
u64 header_len
"H" chunk of header_len bytes (see below)
chunk[] (see below)
```

### Chunk wire format

| Field   | Size | Notes                 |
|---------|------|-----------------------|
| token   | u8   | ASCII letter          |
| length  | u32  | little-endian payload |
| payload | var  | chunk-specific        |

### Mandatory chunks for MVP

| Token | Payload struct                                               | What to fill                                                       |
|-------|--------------------------------------------------------------|-------------------------------------------------------------------|
| `H`   | key=value strings joined by NUL                              | always includes `ticks_per_sec`, `start_time`, `perl=python`       |
| `A`   | key=value NUL-joined string table                             | required keys: `ticks_per_sec`, `start_time`                      |
| `F`   | repeat `{u32 fid,u32 flags,u32 size,u32 mtime, zstr path}`   | at least your script = fid 0, set `flags |= 0x10` (HAS_SRC)       |
| `S`   | repeat `{u32 fid,u32 line, u32 calls, u64 inc_ticks, u64 exc_ticks}` | one record per executed line                                     |
| `E`   | empty                                                        | terminator                                                        |

Call-graph chunks (`C`,`D`) are included so that `nytprofhtml` can render call graphs.
If the reader complains, look for "File format error: token X".

### Tick units

`ticks_per_sec` must match the constant used in the writer. We default to 10,000,000 (100 ns)—the
same value as NYTProf's `TICKS_PER_SEC` macro.

### Endianness

Always little-endian; NYTProf refuses big-endian files.
