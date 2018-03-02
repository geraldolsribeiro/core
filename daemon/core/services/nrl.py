"""
nrl.py: defines services provided by NRL protolib tools hosted here:
    http://www.nrl.navy.mil/itd/ncs/products
"""

from core.misc import utils
from core.misc.ipaddress import Ipv4Prefix
from core.service import CoreService


class NrlService(CoreService):
    """
    Parent class for NRL services. Defines properties and methods
    common to NRL's routing daemons.
    """""
    _name = "Protean"
    _group = "ProtoSvc"
    _depends = ()
    _dirs = ()
    _configs = ()
    _startindex = 45
    _startup = ()
    _shutdown = ()

    @classmethod
    def generateconfig(cls, node, filename, services):
        return ""

    @staticmethod
    def firstipv4prefix(node, prefixlen=24):
        """
        Similar to QuaggaService.routerid(). Helper to return the first IPv4
        prefix of a node, using the supplied prefix length. This ignores the
        interface's prefix length, so e.g. '/32' can turn into '/24'.
        """
        for ifc in node.netifs():
            if hasattr(ifc, 'control') and ifc.control == True:
                continue
            for a in ifc.addrlist:
                if a.find(".") >= 0:
                    addr = a.split('/')[0]
                    pre = Ipv4Prefix("%s/%s" % (addr, prefixlen))
                    return str(pre)
        # raise ValueError,  "no IPv4 address found"
        return "0.0.0.0/%s" % prefixlen


class MgenSinkService(NrlService):
    _name = "MGEN_Sink"
    _configs = ("sink.mgen",)
    _startindex = 5
    _startup = ("mgen input sink.mgen",)
    _validate = ("pidof mgen",)
    _shutdown = ("killall mgen",)

    @classmethod
    def generateconfig(cls, node, filename, services):
        cfg = "0.0 LISTEN UDP 5000\n"
        for ifc in node.netifs():
            name = utils.sysctl_devname(ifc.name)
            cfg += "0.0 Join 224.225.1.2 INTERFACE %s\n" % name
        return cfg

    @classmethod
    def getstartup(cls, node, services):
        cmd = cls._startup[0]
        cmd += " output /tmp/mgen_%s.log" % node.name
        return cmd,


class NrlNhdp(NrlService):
    """
    NeighborHood Discovery Protocol for MANET networks.
    """
    _name = "NHDP"
    _startup = ("nrlnhdp",)
    _shutdown = ("killall nrlnhdp",)
    _validate = ("pidof nrlnhdp",)

    @classmethod
    def getstartup(cls, node, services):
        """
        Generate the appropriate command-line based on node interfaces.
        """
        cmd = cls._startup[0]
        cmd += " -l /var/log/nrlnhdp.log"
        cmd += " -rpipe %s_nhdp" % node.name

        servicenames = map(lambda x: x._name, services)
        if "SMF" in servicenames:
            cmd += " -flooding ecds"
            cmd += " -smfClient %s_smf" % node.name

        netifs = filter(lambda x: not getattr(x, 'control', False), \
                        node.netifs())
        if len(netifs) > 0:
            interfacenames = map(lambda x: x.name, netifs)
            cmd += " -i "
            cmd += " -i ".join(interfacenames)

        return cmd,


class NrlSmf(NrlService):
    """
    Simplified Multicast Forwarding for MANET networks.
    """
    _name = "SMF"
    _startup = ("sh startsmf.sh",)
    _shutdown = ("killall nrlsmf",)
    _validate = ("pidof nrlsmf",)
    _configs = ("startsmf.sh",)

    @classmethod
    def generateconfig(cls, node, filename, services):
        """
        Generate a startup script for SMF. Because nrlsmf does not
        daemonize, it can cause problems in some situations when launched
        directly using vcmd.
        """
        cfg = "#!/bin/sh\n"
        cfg += "# auto-generated by nrl.py:NrlSmf.generateconfig()\n"
        comments = ""
        cmd = "nrlsmf instance %s_smf" % node.name

        servicenames = map(lambda x: x._name, services)
        netifs = filter(lambda x: not getattr(x, 'control', False), node.netifs())
        if len(netifs) == 0:
            return ()

        if "arouted" in servicenames:
            comments += "# arouted service is enabled\n"
            cmd += " tap %s_tap" % (node.name,)
            cmd += " unicast %s" % cls.firstipv4prefix(node, 24)
            cmd += " push lo,%s resequence on" % netifs[0].name
        if len(netifs) > 0:
            if "NHDP" in servicenames:
                comments += "# NHDP service is enabled\n"
                cmd += " ecds "
            elif "OLSR" in servicenames:
                comments += "# OLSR service is enabled\n"
                cmd += " smpr "
            else:
                cmd += " cf "
            interfacenames = map(lambda x: x.name, netifs)
            cmd += ",".join(interfacenames)

        cmd += " hash MD5"
        cmd += " log /var/log/nrlsmf.log"

        cfg += comments + cmd + " < /dev/null > /dev/null 2>&1 &\n\n"
        return cfg


class NrlOlsr(NrlService):
    """
    Optimized Link State Routing protocol for MANET networks.
    """
    _name = "OLSR"
    _startup = ("nrlolsrd",)
    _shutdown = ("killall nrlolsrd",)
    _validate = ("pidof nrlolsrd",)

    @classmethod
    def getstartup(cls, node, services):
        """
        Generate the appropriate command-line based on node interfaces.
        """
        cmd = cls._startup[0]
        # are multiple interfaces supported? No.
        netifs = list(node.netifs())
        if len(netifs) > 0:
            ifc = netifs[0]
            cmd += " -i %s" % ifc.name
        cmd += " -l /var/log/nrlolsrd.log"
        cmd += " -rpipe %s_olsr" % node.name

        servicenames = map(lambda x: x._name, services)
        if "SMF" in servicenames and not "NHDP" in servicenames:
            cmd += " -flooding s-mpr"
            cmd += " -smfClient %s_smf" % node.name
        if "zebra" in servicenames:
            cmd += " -z"

        return cmd,


class NrlOlsrv2(NrlService):
    """
    Optimized Link State Routing protocol version 2 for MANET networks.
    """
    _name = "OLSRv2"
    _startup = ("nrlolsrv2",)
    _shutdown = ("killall nrlolsrv2",)
    _validate = ("pidof nrlolsrv2",)

    @classmethod
    def getstartup(cls, node, services):
        """
        Generate the appropriate command-line based on node interfaces.
        """
        cmd = cls._startup[0]
        cmd += " -l /var/log/nrlolsrv2.log"
        cmd += " -rpipe %s_olsrv2" % node.name

        servicenames = map(lambda x: x._name, services)
        if "SMF" in servicenames:
            cmd += " -flooding ecds"
            cmd += " -smfClient %s_smf" % node.name

        cmd += " -p olsr"

        netifs = filter(lambda x: not getattr(x, 'control', False), node.netifs())
        if len(netifs) > 0:
            interfacenames = map(lambda x: x.name, netifs)
            cmd += " -i "
            cmd += " -i ".join(interfacenames)

        return cmd,


class OlsrOrg(NrlService):
    """
    Optimized Link State Routing protocol from olsr.org for MANET networks.
    """
    _name = "OLSRORG"
    _configs = ("/etc/olsrd/olsrd.conf",)
    _dirs = ("/etc/olsrd",)
    _startup = ("olsrd",)
    _shutdown = ("killall olsrd",)
    _validate = ("pidof olsrd",)

    @classmethod
    def getstartup(cls, node, services):
        """
        Generate the appropriate command-line based on node interfaces.
        """
        cmd = cls._startup[0]
        netifs = filter(lambda x: not getattr(x, 'control', False), node.netifs())
        if len(netifs) > 0:
            interfacenames = map(lambda x: x.name, netifs)
            cmd += " -i "
            cmd += " -i ".join(interfacenames)

        return cmd,

    @classmethod
    def generateconfig(cls, node, filename, services):
        """
        Generate a default olsrd config file to use the broadcast address of 255.255.255.255.
        """
        cfg = """\
#
# OLSR.org routing daemon config file
# This file contains the usual options for an ETX based
# stationary network without fisheye
# (for other options see olsrd.conf.default.full)
#
# Lines starting with a # are discarded
#

#### ATTENTION for IPv6 users ####
# Because of limitations in the parser IPv6 addresses must NOT
# begin with a ":", so please add a "0" as a prefix.

###########################
### Basic configuration ###
###########################
# keep this settings at the beginning of your first configuration file

# Debug level (0-9)
# If set to 0 the daemon runs in the background, unless "NoFork" is set to true
# (Default is 1)

# DebugLevel  1

# IP version to use (4 or 6)
# (Default is 4)

# IpVersion 4

#################################
### OLSRd agent configuration ###
#################################
# this parameters control the settings of the routing agent which are not
# related to the OLSR protocol and it's extensions

# FIBMetric controls the metric value of the host-routes OLSRd sets.
# - "flat" means that the metric value is always 2. This is the preferred value
#   because it helps the linux kernel routing to clean up older routes
# - "correct" use the hopcount as the metric value.
# - "approx" use the hopcount as the metric value too, but does only update the
#   hopcount if the nexthop changes too
# (Default is "flat")

# FIBMetric "flat"

#######################################
### Linux specific OLSRd extensions ###
#######################################
# these parameters are only working on linux at the moment, but might become
# useful on BSD in the future

# SrcIpRoutes tells OLSRd to set the Src flag of host routes to the originator-ip
# of the node. In addition to this an additional localhost device is created
# to make sure the returning traffic can be received.
# (Default is "no")

# SrcIpRoutes no

# Specify the proto tag to be used for routes olsr inserts into kernel
# currently only implemented for linux
# valid values under linux are 1 .. 254
# 1 gets remapped by olsrd to 0 UNSPECIFIED (1 is reserved for ICMP redirects)
# 2 KERNEL routes (not very wise to use)
# 3 BOOT (should in fact not be used by routing daemons)
# 4 STATIC
# 8 .. 15 various routing daemons (gated, zebra, bird, & co)
# (defaults to 0 which gets replaced by an OS-specific default value
# under linux 3 (BOOT) (for backward compatibility)

# RtProto 0

# Activates (in IPv6 mode) the automatic use of NIIT
# (see README-Olsr-Extensions)
# (default is "yes")

# UseNiit yes

# Activates the smartgateway ipip tunnel feature.
# See README-Olsr-Extensions for a description of smartgateways.
# (default is "no")

# SmartGateway no

# Signals that the server tunnel must always be removed on shutdown,
# irrespective of the interface up/down state during startup.
# (default is "no")

# SmartGatewayAlwaysRemoveServerTunnel no

# Determines the maximum number of gateways that can be in use at any given
# time. This setting is used to mitigate the effects of breaking connections
# (due to the selection of a new gateway) on a dynamic network.
# (default is 1)

# SmartGatewayUseCount 1

# Determines the take-down percentage for a non-current smart gateway tunnel.
# If the cost of the current smart gateway tunnel is less than this percentage
# of the cost of the non-current smart gateway tunnel, then the non-current smart
# gateway tunnel is taken down because it is then presumed to be 'too expensive'.
# This setting is only relevant when SmartGatewayUseCount is larger than 1;
# a value of 0 will result in the tunnels not being taken down proactively.
# (default is 0)

# SmartGatewayTakeDownPercentage 0

# Determines the policy routing script that is executed during startup and
# shutdown of olsrd. The script is only executed when SmartGatewayUseCount
# is set to a value larger than 1. The script must setup policy routing
# rules such that multi-gateway mode works. A sample script is included.
# (default is not set)

# SmartGatewayPolicyRoutingScript ""

# Determines the egress interfaces that are part of the multi-gateway setup and
# therefore only relevant when SmartGatewayUseCount is larger than 1 (in which
# case it must be explicitly set).
# (default is not set)

# SmartGatewayEgressInterfaces ""

# Determines the routing tables offset for multi-gateway policy routing tables
# See the policy routing script for an explanation.
# (default is 90)

# SmartGatewayTablesOffset 90

# Determines the policy routing rules offset for multi-gateway policy routing
# rules. See the policy routing script for an explanation.
# (default is 0, which indicates that the rules and tables should be aligned and
# puts this value at SmartGatewayTablesOffset - # egress interfaces -
# # olsr interfaces)

# SmartGatewayRulesOffset 87

# Allows the selection of a smartgateway with NAT (only for IPv4)
# (default is "yes")

# SmartGatewayAllowNAT yes

# Determines the period (in milliseconds) on which a new smart gateway
# selection is performed.
# (default is 10000 milliseconds)

# SmartGatewayPeriod 10000

# Determines the number of times the link state database must be stable
# before a new smart gateway is selected.
# (default is 6)

# SmartGatewayStableCount 6

# When another gateway than the current one has a cost of less than the cost
# of the current gateway multiplied by SmartGatewayThreshold then the smart
# gateway is switched to the other gateway. The unit is percentage.
# (defaults to 0)

# SmartGatewayThreshold 0

# The weighing factor for the gateway uplink bandwidth (exit link, uplink).
# See README-Olsr-Extensions for a description of smart gateways.
# (default is 1)

# SmartGatewayWeightExitLinkUp 1

# The weighing factor for the gateway downlink bandwidth (exit link, downlink).
# See README-Olsr-Extensions for a description of smart gateways.
# (default is 1)

# SmartGatewayWeightExitLinkDown 1

# The weighing factor for the ETX costs.
# See README-Olsr-Extensions for a description of smart gateways.
# (default is 1)

# SmartGatewayWeightEtx 1

# The divider for the ETX costs.
# See README-Olsr-Extensions for a description of smart gateways.
# (default is 0)

# SmartGatewayDividerEtx 0

# Defines what kind of Uplink this node will publish as a
# smartgateway. The existence of the uplink is detected by
# a route to 0.0.0.0/0, ::ffff:0:0/96 and/or 2000::/3.
# possible values are "none", "ipv4", "ipv6", "both"
# (default is "both")

# SmartGatewayUplink "both"

# Specifies if the local ipv4 uplink use NAT
# (default is "yes")

# SmartGatewayUplinkNAT yes

# Specifies the speed of the uplink in kilobit/s.
# First parameter is upstream, second parameter is downstream
# (default is 128/1024)

# SmartGatewaySpeed 128 1024

# Specifies the EXTERNAL ipv6 prefix of the uplink. A prefix
# length of more than 64 is not allowed.
# (default is 0::/0

# SmartGatewayPrefix 0::/0

##############################
### OLSR protocol settings ###
##############################

# HNA (Host network association) allows the OLSR to announce
# additional IPs or IP subnets to the net that are reachable
# through this node.
# Syntax for HNA4 is "network-address    network-mask"
# Syntax for HNA6 is "network-address    prefix-length"
# (default is no HNA)
Hna4
{
# Internet gateway
# 0.0.0.0   0.0.0.0
# specific small networks reachable through this node
# 15.15.0.0 255.255.255.0
}
Hna6
{
# Internet gateway
#   0::                     0
# specific small networks reachable through this node
#   fec0:2200:106:0:0:0:0:0 48
}

################################
### OLSR protocol extensions ###
################################

# Link quality algorithm (only for lq level 2)
# (see README-Olsr-Extensions)
# - "etx_float", a floating point  ETX with exponential aging
# - "etx_fpm", same as ext_float, but with integer arithmetic
# - "etx_ff" (ETX freifunk), an etx variant which use all OLSR
#   traffic (instead of only hellos) for ETX calculation
# - "etx_ffeth", an incompatible variant of etx_ff that allows
#   ethernet links with ETX 0.1.
# (defaults to "etx_ff")

# LinkQualityAlgorithm    "etx_ff"

# Fisheye mechanism for TCs (0 meansoff, 1 means on)
# (default is 1)

LinkQualityFishEye  0

#####################################
### Example plugin configurations ###
#####################################
# Olsrd plugins to load
# This must be the absolute path to the file
# or the loader will use the following scheme:
# - Try the paths in the LD_LIBRARY_PATH
#   environment variable.
# - The list of libraries cached in /etc/ld.so.cache
# - /lib, followed by /usr/lib
#
# the examples in this list are for linux, so check if the plugin is
# available if you use windows/BSD.
# each plugin should have a README file in it's lib subfolder

# LoadPlugin "olsrd_txtinfo.dll"
#LoadPlugin "olsrd_txtinfo.so.0.1"
#{
    # the default port is 2006 but you can change it like this:
    #PlParam     "port"   "8080"

    # You can set a "accept" single address to allow to connect to
    # txtinfo. If no address is specified, then localhost (127.0.0.1)
    # is allowed by default.  txtinfo will only use the first "accept"
    # parameter specified and will ignore the rest.

    # to allow a specific host:
    #PlParam      "accept" "172.29.44.23"
    # if you set it to 0.0.0.0, it will accept all connections
    #PlParam      "accept" "0.0.0.0"
#}

#############################################
### OLSRD default interface configuration ###
#############################################
# the default interface section can have the same values as the following
# interface configuration. It will allow you so set common options for all
# interfaces.

InterfaceDefaults {
    Ip4Broadcast      255.255.255.255
}

######################################
### OLSRd Interfaces configuration ###
######################################
# multiple interfaces can be specified for a single configuration block
# multiple configuration blocks can be specified

# WARNING, don't forget to insert your interface names here !
#Interface "<OLSRd-Interface1>" "<OLSRd-Interface2>"
#{
    # Interface Mode is used to prevent unnecessary
    # packet forwarding on switched ethernet interfaces
    # valid Modes are "mesh" and "ether"
    # (default is "mesh")

    # Mode "mesh"
#}
"""
        return cfg


class MgenActor(NrlService):
    """
    ZpcMgenActor.
    """

    # a unique name is required, without spaces
    _name = "MgenActor"
    # you can create your own group here
    _group = "ProtoSvc"
    # list of other services this service depends on
    _depends = ()
    # per-node directories
    _dirs = ()
    # generated files (without a full path this file goes in the node's dir,
    #  e.g. /tmp/pycore.12345/n1.conf/)
    _configs = ('start_mgen_actor.sh',)
    # this controls the starting order vs other enabled services
    _startindex = 50
    # list of startup commands, also may be generated during startup
    _startup = ("sh start_mgen_actor.sh",)
    # list of validation commands
    _validate = ("pidof mgen",)
    # list of shutdown commands
    _shutdown = ("killall mgen",)

    @classmethod
    def generateconfig(cls, node, filename, services):
        """
        Generate a startup script for MgenActor. Because mgenActor does not
        daemonize, it can cause problems in some situations when launched
        directly using vcmd.
        """
        cfg = "#!/bin/sh\n"
        cfg += "# auto-generated by nrl.py:MgenActor.generateconfig()\n"
        comments = ""
        cmd = "mgenBasicActor.py -n %s -a 0.0.0.0" % node.name

        servicenames = map(lambda x: x._name, services)
        netifs = filter(lambda x: not getattr(x, 'control', False), node.netifs())
        if len(netifs) == 0:
            return ()

        cfg += comments + cmd + " < /dev/null > /dev/null 2>&1 &\n\n"
        return cfg


class Arouted(NrlService):
    """
    Adaptive Routing
    """
    _name = "arouted"
    _configs = ("startarouted.sh",)
    _startindex = NrlService._startindex + 10
    _startup = ("sh startarouted.sh",)
    _shutdown = ("pkill arouted",)
    _validate = ("pidof arouted",)

    @classmethod
    def generateconfig(cls, node, filename, services):
        """
        Return the Quagga.conf or quaggaboot.sh file contents.
        """
        cfg = """
#!/bin/sh
for f in "/tmp/%s_smf"; do
    count=1
    until [ -e "$f" ]; do
        if [ $count -eq 10 ]; then
            echo "ERROR: nrlmsf pipe not found: $f" >&2
            exit 1
        fi
        sleep 0.1
        count=$(($count + 1))
    done
done

""" % node.name
        cfg += "ip route add %s dev lo\n" % cls.firstipv4prefix(node, 24)
        cfg += "arouted instance %s_smf tap %s_tap" % (node.name, node.name)
        # seconds to consider a new route valid
        cfg += " stability 10"
        cfg += " 2>&1 > /var/log/arouted.log &\n\n"
        return cfg
