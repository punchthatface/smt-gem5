# Swaptions Phase 2 patch

These files patch PARSEC `swaptions` so it can emit gem5 work markers for the Phase 2 domain-flush experiment.

## Files in this directory

Expected files:

```text
patches/swaptions/HJM_Securities.cpp
patches/swaptions/Makefile
```

The filenames are intentionally unchanged so they can be copied directly into the PARSEC swaptions source directory.

## What this patch adds

`HJM_Securities.cpp` adds a new command-line option:

```bash
-fi N
```

Meaning:

```text
-fi 0  = no gem5 markers / no flush
-fi 1  = emit marker every swaption
-fi 2  = emit marker every 2 swaptions
-fi 4  = emit marker every 4 swaptions
```

The benchmark itself does not directly flush cache lines. It only emits gem5 `m5_work_begin` markers.

The actual cleanup happens in gem5:

1. `swaptions` emits a marker.
2. gem5 exits at the marker.
3. The gem5 Python runner/config calls:
   - `dcache.memWriteback()`
   - `dcache.memInvalidate()`
4. gem5 simulation resumes.

## Where to copy the files

From the repo root:

```bash
cd /users/<NETID>/smt-gem5

cp patches/swaptions/HJM_Securities.cpp \
  parsec/pkgs/apps/swaptions/src/HJM_Securities.cpp

cp patches/swaptions/Makefile \
  parsec/pkgs/apps/swaptions/src/Makefile
```

Replace `/users/<NETID>/smt-gem5` with the local repo path.

## Important path note

The provided `Makefile` may contain absolute paths from the original development machine, such as:

```text
/users/akim2/smt-gem5
```

Before rebuilding on another account or node, replace that path with the local repo path.

Example:

```bash
sed -i "s#/users/akim2/smt-gem5#/users/<NETID>/smt-gem5#g" \
  parsec/pkgs/apps/swaptions/src/Makefile
```

## Build gem5 m5ops library

```bash
cd /users/<NETID>/smt-gem5/gem5/util/m5
scons build/x86/out/libm5.a
```

## Rebuild swaptions

```bash
cd /users/<NETID>/smt-gem5/parsec
. env.sh

rm -rf pkgs/apps/swaptions/obj/amd64-linux.gcc-pthreads
rm -rf pkgs/apps/swaptions/inst/amd64-linux.gcc-pthreads

parsecmgmt -a build -p parsec.swaptions -c gcc-pthreads
```

## Verify patched binary

```bash
file /users/<NETID>/smt-gem5/parsec/pkgs/apps/swaptions/inst/amd64-linux.gcc-pthreads/bin/swaptions
```

Expected output should include:

```text
statically linked
```

Native sanity check:

```bash
/users/<NETID>/smt-gem5/parsec/pkgs/apps/swaptions/inst/amd64-linux.gcc-pthreads/bin/swaptions \
  -ns 2 -sm 100 -nt 1 -fi 0
```

Expected output should include:

```text
Phase2 gem5 work marker interval: 0
```

Do not run `-fi 1`, `-fi 2`, or `-fi 4` natively on real hardware. Nonzero `-fi` emits gem5 pseudo-instructions and should be used inside gem5 only.
