from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_p4runtime_API import (
    SimpleSwitchP4RuntimeAPI,
)  # Not needed anymore
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI

import time

topo = load_topo("topology.json")
controllers = {}

# Note: we now use the SimpleSwitchThriftAPI to communicate with the switches
# and not the P4RuntimeAPI anymore.
for p4switch in topo.get_p4switches():
    thrift_port = topo.get_thrift_port(p4switch)
    controllers[p4switch] = SimpleSwitchThriftAPI(thrift_port)

# The following lines enable the forwarding as required for assignment 0.
controllers["s1"].table_add("repeater", "forward", ["1"], ["2"])
controllers["s1"].table_add("repeater", "forward", ["3"], ["1"])

controllers["s2"].table_add("repeater", "forward", ["1"], ["2"])
controllers["s2"].table_add("repeater", "forward", ["2"], ["1"])

controllers["s4"].table_add("repeater", "forward", ["1"], ["2"])
controllers["s4"].table_add("repeater", "forward", ["2"], ["1"])

controllers["s3"].table_add("repeater", "forward", ["1"], ["2"])
controllers["s3"].table_add("repeater", "forward", ["2"], ["3"])


def print_link(s1, s2, egress_counts, ingress_counts):
    # We recommend to implement a function that prints the value of the
    # counters used for a particular link and direction.
    # It will help you to debug.
    # However, this is not mandatory. If you do not do it,
    # we won't deduct points.
    print(f"Link from {s1} to {s2}:")
    print(f"  {s1} egress_count: {egress_counts[s1]}")
    print(f"  {s2} ingress_count: {ingress_counts[s2]}")


import time

current_index = 0

while True:
    new_index = (current_index + 1) % 2

    # We first update the active counter index on all switches
    for controller in controllers.values():
        controller.register_write("active_counter_index", 0, new_index)

    # Then lait for packets to propagate -> we can optimize this part I think, this is just the upper bound time delay
    time.sleep(1)

    # Collect and reset inactive counters
    inactive_index = current_index
    ingress_counts = {}
    egress_counts = {}
    for name, controller in controllers.items():
        ingress_count = controller.register_read("ingress_counters", inactive_index)
        egress_count = controller.register_read("egress_counters", inactive_index)
        ingress_counts[name] = ingress_count
        egress_counts[name] = egress_count
        controller.register_write("ingress_counters", inactive_index, 0)
        controller.register_write("egress_counters", inactive_index, 0)

    # Define the links to monitor
    links = [
        ("s1", "s2"),
        ("s2", "s3"),
        ("s4", "s3"),
        ("s4", "s1"),
    ]

    # Compare counts and detect failures
    for src, dst in links:
        src_egress = egress_counts.get(src, 0)
        dst_ingress = ingress_counts.get(dst, 0)
        if src_egress != dst_ingress:
            print(f"Packet loss detected on link from {src} to {dst}")
            print(f"  {src} egress_count: {src_egress}")
            print(f"  {dst} ingress_count: {dst_ingress}")
        else:
            print(f"No packet loss on link from {src} to {dst}")

    current_index = new_index
    time.sleep(1)
