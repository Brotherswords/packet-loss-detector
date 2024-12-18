#include <core.p4>
#include <v1model.p4>

// My includes
#include "include/metadata.p4"
#include "include/headers.p4"
#include "include/parsers.p4"

/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    // Define register arrays for ingress counters
    register<bit<32>>(2) ingress_counters;

    action forward(bit<9> egress_port) {
        standard_metadata.egress_spec = egress_port;
    }

    table repeater {
        key = {
            standard_metadata.ingress_port: exact;
        }
        actions = {
            forward;
            NoAction;
        }
        size = 2;
        default_action = NoAction;
    }

    apply {
        // Read the active counter index (from ECN field)
        bit<32> active_index = (bit<32>) hdr.ipv4.ecn;  // Cast to bit<32>

        // Increment the active ingress counter
        ingress_counters.read(meta.counter, active_index);
        meta.counter = meta.counter + 1;
        ingress_counters.write(active_index, meta.counter);

        repeater.apply();
    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {

    // Define register arrays for egress counters
    register<bit<32>>(2) egress_counters;

    apply {
        // Read the active counter index (from ECN field)
        bit<32> active_index = (bit<32>) hdr.ipv4.ecn;  // Cast to bit<32>

        // Increment the active egress counter
        egress_counters.read(meta.counter, active_index);
        meta.counter = meta.counter + 1;
        egress_counters.write(active_index, meta.counter);

        // Indicate the active counter in the ECN field
        hdr.ipv4.ecn = (bit<2>) active_index;  // Set ECN field (back to bit<2>)
    }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;

