from m5.objects import *
import m5
import argparse
import shlex


def split_opts(s):
    if not s:
        return []
    return shlex.split(s)


class L1ICache(Cache):
    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 20


class L1DCache(Cache):
    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 8
    tgts_per_mshr = 20


class L2Cache(Cache):
    assoc = 8
    tag_latency = 20
    data_latency = 20
    response_latency = 20
    mshrs = 16
    tgts_per_mshr = 12


def add_x86_interrupt_wiring(cpu, membus):
    cpu.createInterruptController()

    for intr in cpu.interrupts:
        intr.pio = membus.mem_side_ports
        intr.int_requestor = membus.cpu_side_ports
        intr.int_responder = membus.mem_side_ports


def connect_cpu_caches(cpu, l2bus, l1i_size, l1d_size):
    cpu.icache = L1ICache(size=l1i_size)
    cpu.dcache = L1DCache(size=l1d_size)

    cpu.icache.cpu_side = cpu.icache_port
    cpu.dcache.cpu_side = cpu.dcache_port

    cpu.icache.mem_side = l2bus.cpu_side_ports
    cpu.dcache.mem_side = l2bus.cpu_side_ports


parser = argparse.ArgumentParser()

parser.add_argument("--num-cores", type=int, default=1)
parser.add_argument("--threads-per-core", type=int, default=1)
parser.add_argument("--mem-size", default="512MB")
parser.add_argument("--cpu-clock", default="2GHz")
parser.add_argument("--l1i-size", default="32kB")
parser.add_argument("--l1d-size", default="32kB")
parser.add_argument("--l2-size", default="512kB")
parser.add_argument("--max-ticks", type=int, default=1000000)

parser.add_argument("--job-cmd", action="append", default=[])
parser.add_argument("--job-opts", action="append", default=[])
parser.add_argument("--job-core", action="append", type=int, default=[])

args = parser.parse_args()

if not args.job_cmd:
    raise RuntimeError("Need at least one --job-cmd")

if not (len(args.job_cmd) == len(args.job_opts) == len(args.job_core)):
    raise RuntimeError("--job-cmd, --job-opts, and --job-core must have same length")

system = System()
system.multi_thread = args.threads_per_core > 1

system.clk_domain = SrcClockDomain()
system.clk_domain.clock = args.cpu_clock
system.clk_domain.voltage_domain = VoltageDomain()

system.mem_mode = "timing"
system.mem_ranges = [AddrRange(args.mem_size)]

system.membus = SystemXBar()
system.system_port = system.membus.cpu_side_ports

system.l2bus = L2XBar()

system.l2cache = L2Cache(size=args.l2_size)
system.l2cache.cpu_side = system.l2bus.mem_side_ports
system.l2cache.mem_side = system.membus.cpu_side_ports

cpus = []
for core_id in range(args.num_cores):
    cpu = O3CPU(cpu_id=core_id, numThreads=args.threads_per_core)
    cpu.clk_domain = system.clk_domain

    add_x86_interrupt_wiring(cpu, system.membus)
    connect_cpu_caches(cpu, system.l2bus, args.l1i_size, args.l1d_size)

    cpus.append(cpu)

system.cpu = cpus

system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

system.workload = SEWorkload.init_compatible(args.job_cmd[0])

per_core = [[] for _ in range(args.num_cores)]

for idx, (cmd, opts, core_id) in enumerate(zip(args.job_cmd, args.job_opts, args.job_core)):
    if core_id < 0 or core_id >= args.num_cores:
        raise RuntimeError(f"Invalid core id: {core_id}")

    if len(per_core[core_id]) >= args.threads_per_core:
        raise RuntimeError(
            f"Core {core_id} has too many jobs for threads_per_core={args.threads_per_core}"
        )

    p = Process(pid=100 + idx)
    p.cmd = [cmd] + split_opts(opts)
    per_core[core_id].append(p)

for core_id, jobs in enumerate(per_core):
    system.cpu[core_id].workload = jobs
    system.cpu[core_id].createThreads()

root = Root(full_system=False, system=system)
m5.instantiate()

print("Beginning debug cache flush method test")
print(f"num_cores={args.num_cores}, threads_per_core={args.threads_per_core}")
print(f"L1I={args.l1i_size}, L1D={args.l1d_size}, L2={args.l2_size}")

for core_id, jobs in enumerate(per_core):
    print(f"core {core_id}:")
    for j, p in enumerate(jobs):
        print(f"  job{j}: {p.cmd}")

dcache = system.cpu[0].dcache

print("DEBUG dcache object:", dcache)
print("DEBUG has memWriteback:", hasattr(dcache, "memWriteback"))
print("DEBUG has memInvalidate:", hasattr(dcache, "memInvalidate"))

if hasattr(dcache, "memWriteback"):
    print("DEBUG calling dcache.memWriteback()")
    dcache.memWriteback()
    print("DEBUG dcache.memWriteback() returned")

if hasattr(dcache, "memInvalidate"):
    print("DEBUG calling dcache.memInvalidate()")
    dcache.memInvalidate()
    print("DEBUG dcache.memInvalidate() returned")

print(f"max_ticks={args.max_ticks}")
exit_event = m5.simulate(args.max_ticks)

print(f"Exiting at tick {m5.curTick()} because {exit_event.getCause()}")