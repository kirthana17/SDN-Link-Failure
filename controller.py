from pox.core import core
from pox.lib.util import dpidToStr
import pox.openflow.libopenflow_01 as of
from pox.lib.packet import ethernet, ipv4, tcp, udp
from pox.lib.addresses import IPAddr

log = core.getLogger()

# Priority levels
HIGH_PRIORITY = 300    # VoIP/Video - UDP port 5001
MEDIUM_PRIORITY = 200  # HTTP - TCP port 80
LOW_PRIORITY = 100     # FTP - TCP port 21
DEFAULT_PRIORITY = 10  # Everything else

class QoSController(object):

    def __init__(self, connection):
        self.connection = connection
        self.mac_to_port = {}
        # Listen to events from this switch
        connection.addListeners(self)
        log.info("QoS Controller started on switch %s" % dpidToStr(connection.dpid))
        # Install default flow rules when switch connects
        self.install_qos_rules()

    def install_qos_rules(self):
        """Install QoS priority rules on switch startup"""

        # Rule 1: HIGH priority - VoIP/Video (UDP port 5001)
        msg = of.ofp_flow_mod()
        msg.priority = HIGH_PRIORITY
        msg.match.dl_type = 0x0800       # IPv4
        msg.match.nw_proto = 17          # UDP
        msg.match.tp_dst = 5001          # Port 5001
        msg.actions.append(of.ofp_action_output(port=of.OFPP_NORMAL))
        self.connection.send(msg)
        log.info("HIGH priority rule installed: UDP port 5001 (VoIP)")

        # Rule 2: MEDIUM priority - HTTP (TCP port 80)
        msg = of.ofp_flow_mod()
        msg.priority = MEDIUM_PRIORITY
        msg.match.dl_type = 0x0800       # IPv4
        msg.match.nw_proto = 6           # TCP
        msg.match.tp_dst = 80            # Port 80
        msg.actions.append(of.ofp_action_output(port=of.OFPP_NORMAL))
        self.connection.send(msg)
        log.info("MEDIUM priority rule installed: TCP port 80 (HTTP)")

        # Rule 3: LOW priority - FTP (TCP port 21)
        msg = of.ofp_flow_mod()
        msg.priority = LOW_PRIORITY
        msg.match.dl_type = 0x0800       # IPv4
        msg.match.nw_proto = 6           # TCP
        msg.match.tp_dst = 21            # Port 21
        msg.actions.append(of.ofp_action_output(port=of.OFPP_NORMAL))
        self.connection.send(msg)
        log.info("LOW priority rule installed: TCP port 21 (FTP)")

    def _handle_PacketIn(self, event):
        """Handle packet_in events from the switch"""

        packet = event.parsed
        if not packet.parsed:
            log.warning("Incomplete packet, ignoring")
            return

        dpid = event.dpid
        in_port = event.port

        # Learn MAC address to port mapping
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][packet.src] = in_port

        # Determine output port
        if packet.dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][packet.dst]
        else:
            out_port = of.OFPP_FLOOD

        # Check traffic type and log it
        ip_packet = packet.find('ipv4')
        if ip_packet:
            tcp_packet = packet.find('tcp')
            udp_packet = packet.find('udp')

            if udp_packet and udp_packet.dstport == 5001:
                log.info("HIGH priority traffic detected: VoIP/Video from port %s" % in_port)

            elif tcp_packet and tcp_packet.dstport == 80:
                log.info("MEDIUM priority traffic detected: HTTP from port %s" % in_port)

            elif tcp_packet and tcp_packet.dstport == 21:
                log.info("LOW priority traffic detected: FTP from port %s" % in_port)

            else:
                log.info("Normal traffic detected from port %s" % in_port)

        # Install flow rule if destination is known
        if out_port != of.OFPP_FLOOD:
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match.from_packet(packet, in_port)
            msg.priority = DEFAULT_PRIORITY
            msg.idle_timeout = 30
            msg.hard_timeout = 60
            msg.actions.append(of.ofp_action_output(port=out_port))
            self.connection.send(msg)

        # Send the current packet out
        msg = of.ofp_packet_out()
        msg.data = event.ofp
        msg.in_port = in_port
        msg.actions.append(of.ofp_action_output(port=out_port))
        self.connection.send(msg)


class QoSLaunch(object):
    def __init__(self):
        log.info("QoS Controller Launch - waiting for switches...")
        core.openflow.addListenerByName("ConnectionUp", self._handle_ConnectionUp)

    def _handle_ConnectionUp(self, event):
        log.info("Switch connected: %s" % dpidToStr(event.dpid))
        QoSController(event.connection)


def launch():
    """Entry point for POX"""
    log.info("Launching QoS Priority Controller (POX)")
    QoSLaunch()
