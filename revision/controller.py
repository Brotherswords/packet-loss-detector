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

# Clear the 'repeater' table before adding entries
for switch in controllers.keys():
    controllers[switch].table_clear("repeater")

# The following lines enable the forwarding as required for assignment 0.
controllers["s1"].table_add("repeater", "forward", ["1"], ["2"])
controllers["s1"].table_add("repeater", "forward", ["3"], ["1"])

controllers["s2"].table_add("repeater", "forward", ["1"], ["2"])
controllers["s2"].table_add("repeater", "forward", ["2"], ["1"])

controllers["s3"].table_add("repeater", "forward", ["1"], ["2"])
controllers["s3"].table_add("repeater", "forward", ["2"], ["3"])

controllers["s4"].table_add("repeater", "forward", ["1"], ["2"])
controllers["s4"].table_add("repeater", "forward", ["2"], ["1"])

# Initialize the active_counter register in each switch to 0
for switch, controller in controllers.items():
    controller.register_write("active_counter", 0, 0)


# Debugging function to print counter values for a specific index
def print_link(switch, counter_type, index, value):
    if DEBUG:
        print(f"[DEBUG] {switch} - {counter_type}[{index}]: {value}")


def monitor_packet_loss():
    active_counter = 0
    initialized = False

    previous_counts = {}

    while True:
        print("\n[INFO] Starting counter monitoring iteration...")

        inactive_counter = 1 - active_counter

        current_counts = {}

        for switch, controller in controllers.items():
            # Read counters for the inactive counter index
            ingress_count = controller.register_read(
                "ingress_counters", index=inactive_counter
            )
            egress_count = controller.register_read(
                "egress_counters", index=inactive_counter
            )

            # Store current counts
            current_counts[switch] = {"ingress": ingress_count, "egress": egress_count}

            # Reset counters after reading
            controller.register_write("ingress_counters", inactive_counter, 0)
            controller.register_write("egress_counters", inactive_counter, 0)

            print_link(switch, "Ingress Count", inactive_counter, ingress_count)
            print_link(switch, "Egress Count", inactive_counter, egress_count)

        # If this is the first iteration, initialize previous_counts and skip packet loss detection
        if not initialized:
            for switch in current_counts.keys():
                previous_counts[switch] = {"ingress": 0, "egress": 0}
            initialized = True
            print(
                "[INFO] Initialization complete. Skipping packet loss detection in the first iteration."
            )
        else:
            links = [
                ("s1", "s2"),
                ("s2", "s3"),
            ]

            for switch1, switch2 in links:
                try:
                    # Compute deltas for the switches
                    delta_egress = (
                        current_counts[switch1]["egress"]
                        - previous_counts[switch1]["egress"]
                    )
                    delta_ingress = (
                        current_counts[switch2]["ingress"]
                        - previous_counts[switch2]["ingress"]
                    )

                    # Only consider positive deltas
                    if delta_egress > 0 or delta_ingress > 0:
                        if delta_egress > delta_ingress:
                            print(
                                f"[WARNING] Packet loss detected between {switch1} and {switch2}. "
                                f"Egress Delta: {delta_egress}, Ingress Delta: {delta_ingress}"
                            )
                except Exception as e:
                    print(
                        f"[ERROR] Unable to compare deltas between {switch1} and {switch2}: {e}"
                    )

        # Update previous counts
        previous_counts = current_counts.copy()

        # Switch the active_counter index in all switches
        active_counter = inactive_counter
        for switch, controller in controllers.items():
            controller.register_write("active_counter", 0, active_counter)

        print(f"[INFO] Switching active counter to {active_counter}")

        time.sleep(1)


if __name__ == "__main__":
    try:
        monitor_packet_loss()
    except KeyboardInterrupt:
        print("\n[INFO] Controller stopped by user.")
