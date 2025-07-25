FILE_FORMAT.md — NYTProf v5.0 stream as written by **Pynytprof**

Scope
-----
Pynytprof emits **uncompressed** NYTProf v5.0 profiles that load in
`Devel::NYTProf::Reader` (v5.0). The stream is little-endian; zlib will be
layered later.

──────────────────────────────────────────────────────────────────────
1  ASCII banner (text header)
──────────────────────────────────────────────────────────────────────

Each line ends in a single `\n`. The binary stream begins immediately after the
last banner line. Format:

```text
NYTProf <major> <minor>\n
# Perl profile database. Generated by Pynytprof on <RFC-2822 date>\n
:basetime=<epoch-seconds>\n
:application=<argv0 or -e>\n
:perl_version=<py_major.minor.patch>\n
:nv_size=<sizeof(double)>\n
:clock_mod=cpu\n
:ticks_per_sec=10000000\n
:osname=<platform.system().lower()>\n
:hz=<os.sysconf("SC_CLK_TCK") or 100>\n
!subs=1  (and other option lines – see below)
...last line `!evals=0\n`
```

**Immediately after the final `\n` comes the first binary byte.**

──────────────────────────────────────────────────────────────────────
2  Binary record stream
──────────────────────────────────────────────────────────────────────

Most records are **TLV** → `tag:u8` + `len:u32(le)` + `payload`.

**Sequence**
1. `P`  process-start (17 bytes total)
2. `S`  statement samples
3. `D`  sub-descriptors
4. `C`  call-graph edges
5. `E`  terminator (empty)

| Tag | Size field | Payload struct (little-endian)                                      | Notes                                               |
|-----|------------|---------------------------------------------------------------------|-----------------------------------------------------|
| `P` | no  | `u32 pid, u32 ppid, double start_time_sec` | tag `P` (0x50) with 16-byte payload |
| `S` | yes        | `u32 fid, u32 line, u32 calls, u64 inc_ticks, u64 exc_ticks` × M   | 100 ns ticks                                       |
| `D` | yes        | `u32 sid, u32 flags, zstr name` × K                                | flags=0 for now                                    |
| `C` | yes        | `u32 caller_sid, u32 callee_sid, u32 calls, u64 ticks, u64 sub_ticks` × L | Call-graph edges                                  |
| `E` | yes        | *empty*                                                            | stream terminator                                  |

The ASCII writer never emits `F`, `B`, or `A` records.

──────────────────────────────────────────────────────────────────────
3  Tick units
──────────────────────────────────────────────────────────────────────

One tick = 100 ns. `ticks_per_sec` is hard-wired to 10 000 000.

──────────────────────────────────────────────────────────────────────
4  Endianness
──────────────────────────────────────────────────────────────────────

All integers are little-endian. NYTProf rejects big-endian files.

──────────────────────────────────────────────────────────────────────
5  Version constants
──────────────────────────────────────────────────────────────────────

```c
#define NYTPROF_MAJOR 5
#define NYTPROF_MINOR 0
```

Update docs and writers in lock-step if these change.

──────────────────────────────────────────────────────────────────────
6  Reference dump
──────────────────────────────────────────────────────────────────────

`vendor/NYTProf_refs/sample_nytprof.out.uncompressed.xxd-dump.txt` is the
golden profile captured 2025-07-09. Except for time-dependent bytes, the first
64 bytes of any new profile must match it.

──────────────────────────────────────────────────────────────────────
7  XS reference
──────────────────────────────────────────────────────────────────────

`vendor/NYTProf_refs/NYTProf.xs` shows how NYTProf writes and reads the stream
(notably `NYTP_write_process_start` and `load_profile_to_hv`). Use it to keep
Pynytprof writers byte-for-byte compatible.

`vendor/NYTProf_refs/FileHandle.xs` contains the actual writing functions, but
the file is over 1500 lines, so use `grep` or similar to search for them.

---------------------------------------------------------------------
