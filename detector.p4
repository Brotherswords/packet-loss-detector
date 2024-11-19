/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

//My includes
#include "include/metadata.p4"
#include "include/headers.p4"
#include "include/parsers.p4"

/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply {  }
}


/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    /* TODO: Define the register array(s) that you will use in the ingress pipeline */
    register<bit<32>>(2) ingress_counters;


    action forward(bit<9> egress_port){
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
        /* TODO: This is where you need to increment the active counter */

        bit<1> index = meta.counter_index;
        ingress_counters[index].count(1);
        repeater.apply();
    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {

    /* TODO: Define the register array(s) that you will use in the egress pipeline */
    register<bit<32>>(2) egress_counters;

    apply {
        /* Read the active counter index from the register */
        bit<1> index;
        active_counter_index.read(index, 0);
        meta.counter_index = index;


        /* TODO: You also need to indicate the active counter in every data packet using the IPv4 ecn field */
        /* Set the ECN field to indicate the active counter index */
        if (hdr.ipv4.isValid()) {
            hdr.ipv4.ecn = meta.counter_index;
        }
        /* TODO: This is where you need to increment the active counter */
        /* Increment the appropriate egress counter */
        egress_counters[index].count(1);
    }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers  hdr, inout metadata meta) {
    apply { 

    }
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