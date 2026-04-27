from m5.objects import *
import m5
import argparse
import shlex

def split_opts(s):
    if not s:
        return []
    return shlex.split(s)

parser = argparse.ArgumentParser()
parser.add_argument("--policy", required=True, choices=["no_smt", "unrestricted_smt", "constrained_smt", "flush_assisted"])
parser.add_argument("--cmd1", required=True)
parser.add_argument("--opts1", default="")
parser.add_argument("--cmd2", required=True)
parser.add_argument("--opts2", default="")
parser.add_argument("--num-cores", type=int, default=4)
parser.add_argument("--mem-size", default="2GB")
parser.add_argument("--cpu-clock", default="2GHz")
parser.add_argument("--max-ticks", type=int, default=0)
parser.add_argument("--flush-penalty", type=int, default=1000,
                    help="cycles to stall per domain switch (flush cost)")
parser.add_argument("--switch-interval", type=int, default=100000,
                    help="ticks between domain switch checks")
args = parser.parse_args()

NUM_CORES = args.num_cores

if args.policy == "no_smt":
    num_threads = 1
else:
    num_threads = 2

system = System()
system.multi_thread = (num_threads > 1)
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = args.cpu_clock
system.clk_domain.voltage_domain = VoltageDomain()
system.mem_mode = "timing"
system.mem_ranges = [AddrRange(args.mem_size)]
system.membus = SystemXBar()
system.system_port = system.membus.cpu_side_ports

system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

system.cpu = [O3CPU(cpu_id=i, numThreads=num_threads) for i in range(NUM_CORES)]

for cpu in system.cpu:
    cpu.createInterruptController()
    cpu.connectBus(system.membus)

system.workload = SEWorkload.init_compatible(args.cmd1)

pid = 100
workload_assignments = []

for i in range(NUM_CORES):
    if args.policy == "no_smt":
        p = Process(pid=pid); pid += 1
        if i < NUM_CORES // 2:
            p.cmd = [args.cmd1] + split_opts(args.opts1)
        else:
            p.cmd = [args.cmd2] + split_opts(args.opts2)
        workload_assignments.append([p])

    elif args.policy in ["unrestricted_smt", "flush_assisted"]:
        p1 = Process(pid=pid); pid += 1
        p1.cmd = [args.cmd1] + split_opts(args.opts1)
        p2 = Process(pid=pid); pid += 1
        p2.cmd = [args.cmd2] + split_opts(args.opts2)
        workload_assignments.append([p1, p2])

    elif args.policy == "constrained_smt":
        if i < NUM_CORES // 2:
            p1 = Process(pid=pid); pid += 1
            p1.cmd = [args.cmd1] + split_opts(args.opts1)
            p2 = Process(pid=pid); pid += 1
            p2.cmd = [args.cmd1] + split_opts(args.opts1)
        else:
            p1 = Process(pid=pid); pid += 1
            p1.cmd = [args.cmd2] + split_opts(args.opts2)
            p2 = Process(pid=pid); pid += 1
            p2.cmd = [args.cmd2] + split_opts(args.opts2)
        workload_assignments.append([p1, p2])

for cpu, procs in zip(system.cpu, workload_assignments):
    cpu.workload = procs
    cpu.createThreads()

root = Root(full_system=False, system=system)
m5.instantiate()

print(f"Policy: {args.policy}, cores: {NUM_CORES}, threads_per_core: {num_threads}")
if args.policy == "flush_assisted":
    print(f"flush_penalty={args.flush_penalty} cycles, switch_interval={args.switch_interval} ticks")

if args.policy == "flush_assisted":
    # simulate in chunks, inject flush penalty each interval
    max_ticks = args.max_ticks if args.max_ticks > 0 else 10**18
    interval = args.switch_interval
    total_flush_penalties = 0
    current_tick = 0

    while current_tick < max_ticks:
        remaining = max_ticks - current_tick
        run_for = min(interval, remaining)
        exit_event = m5.simulate(run_for)
        current_tick = m5.curTick()

        cause = exit_event.getCause()
        if "exiting" in cause or "exit" in cause.lower():
            break

        # inject flush penalty: stall each SMT core for flush_penalty cycles
        # modeled as additional simulate time
        penalty_ticks = args.flush_penalty * NUM_CORES
        m5.simulate(penalty_ticks)
        current_tick = m5.curTick()
        total_flush_penalties += 1

    print(f"Total flush penalties injected: {total_flush_penalties}")
else:
    if args.max_ticks > 0:
        exit_event = m5.simulate(args.max_ticks)
    else:
        exit_event = m5.simulate()

print(f"Exiting at tick {m5.curTick()} because {exit_event.getCause()}")
