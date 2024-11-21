from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
import time

DEBUG = False

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

controllers["s3"].table_add("repeater", "forward", ["1"], ["2"])
controllers["s3"].table_add("repeater", "forward", ["2"], ["3"])

controllers["s4"].table_add("repeater", "forward", ["1"], ["2"])
controllers["s4"].table_add("repeater", "forward", ["2"], ["1"])

# Track previous counter values for delta calculations
previous_counters = {}


# Debugging function to print counter values for a specific link
def print_link(switch, counter_type, port, value):
    if DEBUG:
        print(f"[DEBUG] {switch} - {counter_type}[{port}]: {value}")


def monitor_packet_loss():
    global previous_counters
    active_counter = 0
    initialized = False

    while True:
        print("\n[INFO] Starting counter monitoring iteration...")

        current_counters = {}

        # Read all counter values and compute deltas
        for switch, controller in controllers.items():
            current_counters[switch] = {"ingress": [], "egress": []}
            for port in range(2):  # Assuming two ports per switch
                ingress_count = controller.register_read("ingress_counters", index=port)
                egress_count = controller.register_read("egress_counters", index=port)

                # If this is the first iteration, initialize previous_counters
                if not initialized:
                    if switch not in previous_counters:
                        previous_counters[switch] = {
                            "ingress": [0, 0],
                            "egress": [0, 0],
                        }
                    previous_counters[switch]["ingress"][port] = ingress_count
                    previous_counters[switch]["egress"][port] = egress_count

                # Compute deltas & store deltas
                delta_ingress = (
                    ingress_count - previous_counters[switch]["ingress"][port]
                )
                delta_egress = egress_count - previous_counters[switch]["egress"][port]

                current_counters[switch]["ingress"].append(delta_ingress)
                current_counters[switch]["egress"].append(delta_egress)

                print_link(switch, "ingress_counters", port, delta_ingress)
                print_link(switch, "egress_counters", port, delta_egress)

        # Compare deltas between adjacent switches on the upper path
        if initialized:  # Only perform comparisons after the first iteration
            for switch1, switch2 in [("s1", "s2"), ("s2", "s3")]:
                for port in range(2):  # Assuming two ports per switch
                    try:
                        egress_delta = current_counters[switch1]["egress"][port]
                        ingress_delta = current_counters[switch2]["ingress"][port]

                        if egress_delta != ingress_delta:
                            print(
                                f"[WARNING] Packet loss detected between {switch1} and {switch2}. "
                                f"Egress Delta: {egress_delta}, Ingress Delta: {ingress_delta}"
                            )
                    except Exception as e:
                        print(
                            f"[ERROR] Unable to compare deltas between {switch1} and {switch2}: {e}"
                        )

        # Update previous counters for the next iteration
        for switch in controllers.keys():
            for port in range(2):
                previous_counters[switch]["ingress"][port] = controllers[
                    switch
                ].register_read("ingress_counters", index=port)
                previous_counters[switch]["egress"][port] = controllers[
                    switch
                ].register_read("egress_counters", index=port)

        # Mark as initialized after the first iteration
        if not initialized:
            initialized = True

        active_counter = 1 - active_counter  # Switch between 0 and 1
        print(f"[DEBUG] Switching active counter to {active_counter}")

        time.sleep(1)


while True:
    try:
        monitor_packet_loss()
    except KeyboardInterrupt:
        print("\n[INFO] Controller stopped by user.")
        break
