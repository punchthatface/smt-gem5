# configs/smt_flush_cache.py
# Phase 2 gem5 config for cache-aware SMT experiments.
# Supports:
#   - solo victim: one core, one thread
#   - shared SMT: one core, two SMT threads
#   - split-core baseline: two cores, one thread per core
# Includes explicit L1I/L1D and shared L2 caches so CLFLUSH/cache effects are visible in stats.

import argparse
import shlex

import m5
from m5.objects import *


class L1ICache(Cache):
    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 20

    def __init__(self, size="32kB"):
        super().__init__()
        self.size = size


class L1DCache(Cache):
    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 8
    tgts_per_mshr = 20

    def __init__(self, size="32kB"):
        super().__init__()
        self.size = size


class L2Cache(Cache):
    assoc = 8
    tag_latency = 20
    data_latency = 20
    response_latency = 20
    mshrs = 16
    tgts_per_mshr = 20

    def __init__(self, size="512kB"):
        super().__init__()
        self.size = size


def split_opts(s):
    return shlex.split(s) if s else []


def add_x86_interrupt_wiring(cpu, membus):
    cpu.createInterruptController()

    for intr in cpu.interrupts:
        intr.pio = membus.mem_side_ports
        intr.int_requestor = membus.cpu_side_ports
        intr.int_responder = membus.mem_side_ports


def connect_cpu_caches(cpu, l2bus, l1i_size, l1d_size):
    cpu.icache = L1ICache(l1i_size)
    cpu.dcache = L1DCache(l1d_size)
    cpu.icache.cpu_side = cpu.icache_port
    cpu.dcache.cpu_side = cpu.dcache_port
    cpu.icache.mem_side = l2bus.cpu_side_ports
    cpu.dcache.mem_side = l2bus.cpu_side_ports


parser = argparse.ArgumentParser()
parser.add_argument("--num-cores", type=int, required=True)
parser.add_argument("--threads-per-core", type=int, required=True, choices=[1, 2])
parser.add_argument("--mem-size", default="512MB")
parser.add_argument("--cpu-clock", default="2GHz")
parser.add_argument("--max-ticks", type=int, default=0)
parser.add_argument("--l1i-size", default="32kB")
parser.add_argument("--l1d-size", default="32kB")
parser.add_argument("--l2-size", default="512kB")

# Repeated triples: --job-cmd X --job-opts Y --job-core Z
parser.add_argument("--job-cmd", action="append", default=[])
parser.add_argument("--job-opts", action="append", default=[])
parser.add_argument("--job-core", action="append", type=int, default=[])
args = parser.parse_args()

if not args.job_cmd:
    raise RuntimeError("At least one --job-cmd is required")
if not (len(args.job_cmd) == len(args.job_opts) == len(args.job_core)):
    raise RuntimeError("job-cmd, job-opts, and job-core counts must match")
if args.num_cores < 1:
    raise RuntimeError("--num-cores must be >= 1")

# Validate placement before constructing system.
per_core_jobs = [[] for _ in range(args.num_cores)]
for idx, core_id in enumerate(args.job_core):
    if core_id < 0 or core_id >= args.num_cores:
        raise RuntimeError(f"Invalid core id {core_id}")
    per_core_jobs[core_id].append(idx)

for core_id, jobs in enumerate(per_core_jobs):
    if len(jobs) > args.threads_per_core:
        raise RuntimeError(
            f"Core {core_id} has {len(jobs)} jobs but only {args.threads_per_core} thread slots"
        )
    # O3CPU SE mode is most robust when each instantiated CPU has at least one workload.
    if len(jobs) == 0:
        raise RuntimeError(
            f"Core {core_id} has no workload. Use fewer cores or place a job on every core."
        )

system = System()
system.multi_thread = args.threads_per_core > 1
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = args.cpu_clock
system.clk_domain.voltage_domain = VoltageDomain()

system.mem_mode = "timing"
system.mem_ranges = [AddrRange(args.mem_size)]

system.membus = SystemXBar()
system.l2bus = L2XBar()
system.system_port = system.membus.cpu_side_ports

cpus = []
for core_id in range(args.num_cores):
    cpu = O3CPU(cpu_id=core_id, numThreads=args.threads_per_core)
    cpu.clk_domain = system.clk_domain
    add_x86_interrupt_wiring(cpu, system.membus)
    connect_cpu_caches(cpu, system.l2bus, args.l1i_size, args.l1d_size)
    cpus.append(cpu)

system.cpu = cpus

system.l2cache = L2Cache(args.l2_size)
system.l2cache.cpu_side = system.l2bus.mem_side_ports
system.l2cache.mem_side = system.membus.cpu_side_ports

system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

system.workload = SEWorkload.init_compatible(args.job_cmd[0])

processes = []
for idx, (cmd, opts) in enumerate(zip(args.job_cmd, args.job_opts)):
    p = Process(pid=100 + idx)
    p.cmd = [cmd] + split_opts(opts)
    processes.append(p)

for core_id, cpu in enumerate(system.cpu):
    cpu.workload = [processes[idx] for idx in per_core_jobs[core_id]]
    cpu.createThreads()

root = Root(full_system=False, system=system)
m5.instantiate()

print("Beginning Phase 2 cache-aware SMT simulation")
print(f"num_cores={args.num_cores}, threads_per_core={args.threads_per_core}")
print(f"L1I={args.l1i_size}, L1D={args.l1d_size}, L2={args.l2_size}")
for core_id, jobs in enumerate(per_core_jobs):
    print(f"core {core_id}:")
    for idx in jobs:
        print(f"  job{idx}: {processes[idx].cmd}")

if args.max_ticks > 0:
    print(f"max_ticks={args.max_ticks}")
    exit_event = m5.simulate(args.max_ticks)
else:
    exit_event = m5.simulate()

print(f"Exiting at tick {m5.curTick()} because {exit_event.getCause()}")
