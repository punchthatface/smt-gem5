from m5.objects import *
import m5
import argparse
import shlex

def split_opts(s):
    if not s:
        return []
    return shlex.split(s)

parser = argparse.ArgumentParser()
parser.add_argument("--policy", required=True, choices=["no_smt", "unrestricted_smt", "constrained_smt"])
parser.add_argument("--cmd1", required=True)
parser.add_argument("--opts1", default="")
parser.add_argument("--cmd2", required=True)
parser.add_argument("--opts2", default="")
parser.add_argument("--num-cores", type=int, default=4)
parser.add_argument("--mem-size", default="512MB")
parser.add_argument("--cpu-clock", default="2GHz")
parser.add_argument("--max-ticks", type=int, default=0)
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

    elif args.policy == "unrestricted_smt":
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
if args.max_ticks > 0:
    exit_event = m5.simulate(args.max_ticks)
else:
    exit_event = m5.simulate()

print(f"Exiting at tick {m5.curTick()} because {exit_event.getCause()}")
