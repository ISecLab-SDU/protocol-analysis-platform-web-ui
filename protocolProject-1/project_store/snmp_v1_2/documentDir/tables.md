## 3. The SNMP Architecture -> 3.2. Elements of the Architecture -> 3.2.4. Form and Meaning of Protocol Exchanges

```plaintext
```
```

## 4. Protocol Specification -> 4.1. Elements of Procedure -> 4.1.3. The GetNextRequest-PDU

```plaintext
Derived: ASN.1 definition of GetNextRequest-PDU
GetNextRequest-PDU ::= [1] IMPLICIT SEQUENCE { request-id RequestID, error-status -- always 0 ErrorStatus, error-index -- always 0 ErrorIndex, variable-bindings VarBindList }
```

## 4. Protocol Specification -> 4.1. Elements of Procedure -> 4.1.3. The GetNextRequest-PDU -> 4.1.3.1. Example of Table Traversal

```plaintext
Derived: Routing table example
Destination NextHop Metric 10.0.0.99 89.1.1.42 5 9.1.2.3 99.0.0.3 3 10.0.0.51 89.1.1.42 5
```

## 4. Protocol Specification -> 4.1. Elements of Procedure -> 4.1.1. Common Constructs

```plaintext
Derived: ASN.1 constructs for request/response information
-- request/response information
RequestID ::= INTEGER
ErrorStatus ::= INTEGER { noError(0), tooBig(1), noSuchName(2), badValue(3), readOnly(4) genErr(5) }
ErrorIndex ::= INTEGER
```

```plaintext
Derived: ASN.1 constructs for variable bindings
-- variable bindings
VarBind ::= SEQUENCE { name ObjectName, value ObjectSyntax }
VarBindList ::= SEQUENCE OF VarBind
```

## 4. Protocol Specification -> 4.1. Elements of Procedure -> 4.1.6. The Trap-PDU

```plaintext
Derived: Trap-PDU structure
Trap-PDU ::= [4] IMPLICIT SEQUENCE { enterprise -- type of object generating \-- trap, see sysObjectID in [5] OBJECT IDENTIFIER, agent-addr -- address of object generating NetworkAddress, -- trap generic-trap -- generic trap type INTEGER { coldStart(0), warmStart(1), linkDown(2), linkUp(3), authenticationFailure(4), egpNeighborLoss(5), enterpriseSpecific(6) }, specific-trap -- specific code, present even INTEGER, -- if generic-trap is not \-- enterpriseSpecific time-stamp -- time elapsed between the last TimeTicks, -- (re)initialization of the network \-- entity and the generation of the trap variable-bindings -- "interesting" information VarBindList }
```

## 3. The SNMP Architecture -> 3.2. Elements of the Architecture -> 3.2.5. Definition of Administrative Relationships

```plaintext
Figure 1 Example Network Management Configuration
+------------------+                 +----------------+                 +----------------+
| Region #1 INOC   |                 |Region #2 INOC  |                 |PC in Region #3 |
|                  |                 |                |                 |                |
|Domain=Region #1  |                 |Domain=Region #2|                 |Domain=Region #3|
|CPU=super-mini-1  |                 |CPU=super-mini-1|                 |CPU=Clone-1     |
|PCommunity=pub    |                 |PCommunity=pub  |                 |PCommunity=slate|
|                  |                 |                |                 |                |
+------------------+                 +----------------+                 +----------------+
     /|\                                   /|\                                   /|\
      |                                     |                                     |
      |                                     |                                     |
     \|/                                    |                                    \|/
+-----------------+                         |                         +-----------------+
| Region #3 INOC  |<\-------------+         |         +-------------+ |Domain=Region#3  |
|                 |               |         |         |             | |CPU=router-1     |
|Domain=Region #3 |               |         |         |             | |DCommunity=secret|
|CPU=super-mini-2 |               |         |         |             | +-----------------+
|PCommunity=pub,  |               |         |         |             |
| slate           |               |         |         |             |
|DCommunity=secret|               |         |         |             |
+-------------->|                 |<\-------------+   |             |
                +-----------------+               |   |             |
                     /|\                          |   |             |
                      |                           |   |             |
                     \|/                         \|/ \|/           \|/
                +-----------------+         +-----------------+ +-----------------+
                |Domain=Region#3  |         |Domain=Region#3  | |Domain=Region#3  |
                |CPU=router-1     |         |CPU=mainframe-1  | |CPU=modem-1      |
                |DCommunity=secret|         |DCommunity=secret| |DCommunity=secret|
                +-----------------+         +-----------------+ +-----------------+
Domain: the administrative domain of the element
PCommunity: the name of a community utilizing a proxy agent
DCommunity: the name of a direct community
```

## 4. Protocol Specification

```plaintext
Derived: ASN.1 Message and PDU Definitions
RFC1157-SNMP DEFINITIONS ::= BEGIN IMPORTS ObjectName, ObjectSyntax, NetworkAddress, IpAddress, TimeTicks FROM RFC1155-SMI; \-- top-level message Message ::= SEQUENCE { version -- version-1 for this RFC INTEGER { version-1(0) }, community -- community name OCTET STRING, data -- e.g., PDUs if trivial ANY -- authentication is being used } \-- protocol data units PDUs ::= CHOICE { get-request GetRequest-PDU, get-next-request GetNextRequest-PDU, get-response GetResponse-PDU, set-request SetRequest-PDU, trap Trap-PDU } \-- the individual PDUs and commonly used \-- data types will be defined later END
```

