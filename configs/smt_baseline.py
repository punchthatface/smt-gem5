from m5.objects import *
import m5
import argparse
import shlex

def split_opts(s):
    if not s:
        return []
    return shlex.split(s)

parser = argparse.ArgumentParser()
parser.add_argument("--threads", type=int, default=2, choices=[1, 2])
parser.add_argument("--cmd1", required=True)
parser.add_argument("--opts1", default="")
parser.add_argument("--cmd2", default="")
parser.add_argument("--opts2", default="")
parser.add_argument("--mem-size", default="512MB")
parser.add_argument("--cpu-clock", default="2GHz")
args = parser.parse_args()

system = System()
system.multi_thread = args.threads > 1

system.clk_domain = SrcClockDomain()
system.clk_domain.clock = args.cpu_clock
system.clk_domain.voltage_domain = VoltageDomain()

system.mem_mode = "timing"
system.mem_ranges = [AddrRange(args.mem_size)]

system.cpu = O3CPU(numThreads=args.threads)

system.membus = SystemXBar()
system.system_port = system.membus.cpu_side_ports

system.cpu.createInterruptController()
system.cpu.connectBus(system.membus)

system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

system.workload = SEWorkload.init_compatible(args.cmd1)

p1 = Process(pid=100)
p1.cmd = [args.cmd1] + split_opts(args.opts1)

workloads = [p1]

if args.threads == 2:
    if not args.cmd2:
        raise RuntimeError("--threads=2 requires --cmd2")
    p2 = Process(pid=101)
    p2.cmd = [args.cmd2] + split_opts(args.opts2)
    workloads.append(p2)

system.cpu.workload = workloads
system.cpu.createThreads()

root = Root(full_system=False, system=system)
m5.instantiate()

print("Beginning SMT baseline simulation")
print(f"threads={args.threads}")
print(f"cmd1={p1.cmd}")
if args.threads == 2:
    print(f"cmd2={p2.cmd}")

exit_event = m5.simulate()
print(f"Exiting at tick {m5.curTick()} because {exit_event.getCause()}")
