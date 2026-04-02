from m5.objects import *
import m5

system = System()
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = "2GHz"
system.clk_domain.voltage_domain = VoltageDomain()

system.mem_mode = "timing"
system.mem_ranges = [AddrRange("512MB")]

system.cpu = O3CPU(numThreads=2)

system.membus = SystemXBar()
system.system_port = system.membus.cpu_side_ports

system.cpu.createInterruptController()

system.cpu.icache_port = system.membus.cpu_side_ports
system.cpu.dcache_port = system.membus.cpu_side_ports

system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

binary = "/bin/echo"

p1 = Process()
p1.cmd = [binary, "thread0"]

p2 = Process()
p2.cmd = [binary, "thread1"]

system.cpu.workload = [p1, p2]
system.cpu.createThreads()

root = Root(full_system=False, system=system)
m5.instantiate()

print("Beginning SMT baseline simulation")
exit_event = m5.simulate()
print(f"Exiting at tick {m5.curTick()} because {exit_event.getCause()}")