from m5.objects import *
import m5
import argparse
import shlex


def split_opts(s):
    return shlex.split(s) if s else []


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


def safe_set_param(obj, name, value, applied, skipped):
    """Set a SimObject parameter if gem5 exposes it in this build."""
    if value is None or value == "":
        return
    try:
        setattr(obj, name, value)
        applied.append(f"{obj.path() if hasattr(obj, 'path') else obj}.{name}={value}")
    except Exception as e:
        skipped.append(f"{name}={value} ({e})")


def apply_smt_resource_policy(cpu, args, applied, skipped):
    """
    Expose gem5 O3 SMT resource-sharing knobs from the config.

    This is the closest 30-minute architecture-level improvement:
    it uses gem5's actual O3 SMT resource policies when available
    rather than only changing workload placement.
    """
    if args.smt_resource_policy == "fair":
        # Make shared SMT scheduling less arbitrary by preferring round-robin
        # thread selection in fetch/commit when supported.
        safe_set_param(cpu, "smtFetchPolicy", "RoundRobin", applied, skipped)
        safe_set_param(cpu, "smtCommitPolicy", "RoundRobin", applied, skipped)

    elif args.smt_resource_policy == "partitioned":
        # Partition shared O3 resources between SMT threads when supported.
        # This directly models restricted/constrained SMT resource sharing.
        safe_set_param(cpu, "smtFetchPolicy", "RoundRobin", applied, skipped)
        safe_set_param(cpu, "smtCommitPolicy", "RoundRobin", applied, skipped)
        safe_set_param(cpu, "smtROBPolicy", "Partitioned", applied, skipped)
        safe_set_param(cpu, "smtIQPolicy", "Partitioned", applied, skipped)
        safe_set_param(cpu, "smtLSQPolicy", "Partitioned", applied, skipped)

    # Manual overrides always win.
    safe_set_param(cpu, "smtFetchPolicy", args.smt_fetch_policy, applied, skipped)
    safe_set_param(cpu, "smtCommitPolicy", args.smt_commit_policy, applied, skipped)
    safe_set_param(cpu, "smtROBPolicy", args.smt_rob_policy, applied, skipped)
    safe_set_param(cpu, "smtIQPolicy", args.smt_iq_policy, applied, skipped)
    safe_set_param(cpu, "smtLSQPolicy", args.smt_lsq_policy, applied, skipped)

    if args.smt_num_fetching_threads is not None:
        safe_set_param(cpu, "smtNumFetchingThreads", args.smt_num_fetching_threads, applied, skipped)


def get_flush_target_cores(cpus, per_core, flush_scope, flush_core):
    if flush_scope == "all":
        return list(range(len(cpus)))
    if flush_scope == "active":
        return [cid for cid, jobs in enumerate(per_core) if jobs]
    return [flush_core]


def flush_l1d(cpus, target_cores):
    for cid in target_cores:
        dcache = cpus[cid].dcache
        dcache.memWriteback()
        dcache.memInvalidate()


parser = argparse.ArgumentParser()
parser.add_argument("--num-cores", type=int, default=1)
parser.add_argument("--threads-per-core", type=int, default=1)
parser.add_argument("--mem-size", default="512MB")
parser.add_argument("--cpu-clock", default="2GHz")
parser.add_argument("--l1i-size", default="32kB")
parser.add_argument("--l1d-size", default="32kB")
parser.add_argument("--l2-size", default="512kB")
parser.add_argument("--max-ticks", type=int, default=1000000000)

# Legacy marker-based path kept for compatibility with old configs.
parser.add_argument("--flush-on-workbegin", action="store_true")
parser.add_argument("--flush-all-cores", action="store_true")

# New benchmark-independent periodic cleanup path.
parser.add_argument("--flush-every-ticks", type=int, default=0)
parser.add_argument("--flush-scope", choices=["core0", "active", "all"], default="core0")
parser.add_argument("--flush-core", type=int, default=0)

# Architecture-aware SMT resource policy knobs.
parser.add_argument(
    "--smt-resource-policy",
    choices=["default", "fair", "partitioned"],
    default="default",
    help="Use gem5 O3 SMT resource policy knobs when available."
)
parser.add_argument("--smt-fetch-policy", default="")
parser.add_argument("--smt-commit-policy", default="")
parser.add_argument("--smt-rob-policy", default="")
parser.add_argument("--smt-iq-policy", default="")
parser.add_argument("--smt-lsq-policy", default="")
parser.add_argument("--smt-num-fetching-threads", type=int, default=None)

parser.add_argument("--job-cmd", action="append", default=[])
parser.add_argument("--job-opts", action="append", default=[])
parser.add_argument("--job-core", action="append", type=int, default=[])
args = parser.parse_args()

if not args.job_cmd:
    raise RuntimeError("Need at least one --job-cmd")
if not (len(args.job_cmd) == len(args.job_opts) == len(args.job_core)):
    raise RuntimeError("--job-cmd, --job-opts, and --job-core must have same length")
if args.flush_core < 0 or args.flush_core >= args.num_cores:
    raise RuntimeError(f"Invalid --flush-core {args.flush_core}")

system = System()
system.exit_on_work_items = True
system.work_begin_exit_count = 1
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

applied_smt_params = []
skipped_smt_params = []

cpus = []
for core_id in range(args.num_cores):
    cpu = O3CPU(cpu_id=core_id, numThreads=args.threads_per_core)
    cpu.clk_domain = system.clk_domain
    apply_smt_resource_policy(cpu, args, applied_smt_params, skipped_smt_params)
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
        raise RuntimeError(f"Invalid core id {core_id}")
    if len(per_core[core_id]) >= args.threads_per_core:
        raise RuntimeError(f"Core {core_id} has too many jobs for threads_per_core={args.threads_per_core}")
    p = Process(pid=100 + idx)
    p.cmd = [cmd] + split_opts(opts)
    per_core[core_id].append(p)

for core_id, jobs in enumerate(per_core):
    system.cpu[core_id].workload = jobs
    system.cpu[core_id].createThreads()

root = Root(full_system=False, system=system)
m5.instantiate()

flush_target_cores = get_flush_target_cores(system.cpu, per_core, args.flush_scope, args.flush_core)
if args.flush_all_cores:
    flush_target_cores = list(range(len(system.cpu)))

print("Beginning domain-switch flush simulation")
print(f"num_cores={args.num_cores}, threads_per_core={args.threads_per_core}")
print(f"flush_on_workbegin={args.flush_on_workbegin}, flush_all_cores={args.flush_all_cores}")
print(f"flush_every_ticks={args.flush_every_ticks}")
print(f"flush_scope={args.flush_scope}, flush_core={args.flush_core}")
print(f"flush_target_cores={flush_target_cores}")
print(f"smt_resource_policy={args.smt_resource_policy}")
print(f"applied_smt_params={applied_smt_params}")
print(f"skipped_smt_params={skipped_smt_params}")

for core_id, jobs in enumerate(per_core):
    print(f"core {core_id}:")
    for j, p in enumerate(jobs):
        print(f"  job{j}: {p.cmd}")

flush_count = 0
elapsed_since_periodic_flush = 0
last_cause = "not started"

while True:
    remaining = args.max_ticks - int(m5.curTick())
    if remaining <= 0:
        last_cause = "simulate() limit reached"
        break

    if args.flush_every_ticks > 0:
        run_ticks = min(args.flush_every_ticks, remaining)
    else:
        run_ticks = remaining

    exit_event = m5.simulate(run_ticks)
    cause = exit_event.getCause()
    last_cause = cause
    print(f"Exit at tick {m5.curTick()} because {cause}")
    lcause = str(cause).lower()

    if "workbegin" in lcause:
        if args.flush_on_workbegin:
            print("DOMAIN_FLUSH_BEGIN reason=workbegin")
            flush_l1d(system.cpu, flush_target_cores)
            flush_count += 1
            print("DOMAIN_FLUSH_END reason=workbegin")
        else:
            print("DOMAIN_SWITCH_NO_FLUSH")
        continue

    # If the workload exited naturally, stop immediately.
    if "exiting with last active thread context" in lcause or "exiting with last active thread" in lcause:
        break

    # If no non-tick exit happened and periodic flushing is enabled, this simulate()
    # returned because the requested quantum expired. Flush unless this was the final
    # max-tick boundary.
    if args.flush_every_ticks > 0 and int(m5.curTick()) < args.max_ticks:
        print("DOMAIN_FLUSH_BEGIN reason=periodic")
        flush_l1d(system.cpu, flush_target_cores)
        flush_count += 1
        print("DOMAIN_FLUSH_END reason=periodic")
        continue

    break

print(f"DOMAIN_FLUSH_COUNT {flush_count}")
print(f"Final tick {m5.curTick()} cause {last_cause}")
