from pysnmp.hlapi import *
import threading

class SNMPManager:
    """
    JARVIS SNMP Module V1.0
    Supports SNMP v2c GET requests.
    """

    @staticmethod
    def get(ip, community, oid, port=161):
        """
        Fetch a single OID from a target.
        """
        errorIndication, errorStatus, errorIndex, varBinds = next(
            getCmd(SnmpEngine(),
                   CommunityData(community, mpModel=1), # v2c
                   UdpTransportTarget((ip, port), timeout=1, retries=1),
                   ContextData(),
                   ObjectType(ObjectIdentity(oid)))
        )

        if errorIndication:
            return False, str(errorIndication)
        elif errorStatus:
            return False, errorStatus.prettyPrint()
        else:
            # Return the value of the first variable binding
            for varBind in varBinds:
                return True, str(varBind[1])
            return False, "No Data"

    @staticmethod
    def quick_scan(ip, community="public"):
        # System Description OID
        return SNMPManager.get(ip, community, '1.3.6.1.2.1.1.1.0')