## 2. Protocol Summary -> 2.1 Configuration parameters repository

```plaintext
```
```

## 3. The Client-Server Protocol

```plaintext
Table 1: BOOTP message format (from RFC 951)
<The exact table content is not provided in the given text>
```

```plaintext
Figure 1: BOOTP message format (from RFC 951)
<The exact figure content is not provided in the given text>
```

## 3. The Client-Server Protocol -> 3.4 Obtaining parameters with externally configured network address

```plaintext
```
```

## 3. The Client-Server Protocol -> 3.3 Interpretation and representation of time values

```plaintext
Derived: Time value representation
0xffffffff
```

## 4. Specification of the DHCP client-server protocol -> 4.1 Constructing and sending DHCP messages

```plaintext
Derived: DHCP message retransmission timing example
The delay between retransmissions SHOULD be chosen to allow sufficient time for replies from the server to be delivered based on the characteristics of the internetwork between the client and the server. For example, in a 10Mb/sec Ethernet internetwork, the delay before the first retransmission SHOULD be 4 seconds randomized by the value of a uniform random number chosen from the range -1 to +1. Clients with clocks that provide resolution granularity of less than one second may choose a non-integer randomization value. The delay before the next retransmission SHOULD be 8 seconds randomized by the value of a uniform number chosen from the range -1 to +1. The retransmission delay SHOULD be doubled with subsequent retransmissions up to a maximum of 64 seconds.
```

## 3. The Client-Server Protocol ->

```plaintext
Figure 4: Timeline diagram of messages exchanged between DHCP client and servers when reusing a previously allocated network address
 Server          Client          Server
     v              v              v
     |              |              |
     |    Begins    |              |
     | initialization              |
     |              |              |
     |              /|\            |
     |  _________ __/ | \__________|
     | /DHCPREQU EST | DHCPREQUEST\
     |/              |             \
     |               |              |
     |     Locates   |    Locates   |
     | configuration | configuration|
     |               |              |
     |\              |             /|
     | \ ___________/ | \ __________/|
     |  \/ DHCPACK    |  \/ DHCPACK  |
     |   \ _______    |    \ _______ |
     |    \       |   |     \       ||
     |     | Initialization |       ||
     |     | complete       |       ||
     |     |                |       ||
     |     | (Subsequent    |       ||
     |     |  DHCPACKS      |       ||
     |     |  ignored)      |       ||
     |     |                |       ||
     |     \|               |       ||
     |                      |       ||
     v                      v       v
```

## 4. Specification of the DHCP client-server protocol -> 4.3 DHCP server behavior -> 4.3.5 DHCPINFORM message

```plaintext
```
```

## 4. Specification of the DHCP client-server protocol -> 4.3 DHCP server behavior -> 4.3.6 Client messages

```plaintext
Table 4: Client messages from different states
---------------------------------------------------------------------
|                 |INIT-REBOOT |SELECTING |RENEWING |REBINDING      |
---------------------------------------------------------------------
|broad/unicast    |broadcast   |broadcast |unicast  |broadcast      |
|server-ip        |MUST NOT    |MUST      |MUST NOT |MUST NOT       |
|requested-ip     |MUST        |MUST      |MUST NOT |MUST NOT       |
|ciaddr           |zero        |zero      |IP address |IP address   |
---------------------------------------------------------------------
```

## 3. The Client-Server Protocol -> 3.1 Client-server interaction - allocating a network address

```plaintext
Table 2: DHCP messages
Message       Use
-------       ---
DHCPDISCOVER  - Client broadcast to locate available servers.
DHCPOFFER     - Server to client in response to DHCPDISCOVER with offer of configuration parameters.
DHCPREQUEST   - Client message to servers either (a) requesting offered parameters from one server and implicitly declining offers from all others, (b) confirming correctness of previously allocated address after, e.g., system reboot, or (c) extending the lease on a particular network address.
DHCPACK       - Server to client with configuration parameters, including committed network address.
DHCPNAK       - Server to client indicating client's notion of network address is incorrect (e.g., client has moved to new subnet) or client's lease as expired
DHCPDECLINE   - Client to server indicating network address is already in use.
DHCPRELEASE   - Client to server relinquishing network address and cancelling remaining lease.
DHCPINFORM    - Client to server, asking only for local configuration parameters; client already has externally configured network address.
```

```plaintext
Figure 3: Timeline diagram of messages exchanged between DHCP client and servers when allocating a new network address
Server Client Server (not selected) (selected)
 v      v      v
 |      |      |
 |      |      |
 | Begins initialization  |
 |      |      |
 |      |      |
 | _____________/|\____________ |
 |      |/DHCPDISCOVER | DHCPDISCOVER \|      |
 |      |      |      |
 | Determines  |      Determines configuration |
 |      |      |      |
 |      |\      |      |
 | ____________/ |      | \________ |
 | /DHCPOFFER |      | DHCPOFFER\ |      |
 |/      |      | \      |
 |      |      |      |
 | Collects replies |      |      |
 |      |      \|      |
 |      |      |      |
 | Selects configuration |      |      |
 |      |      |      |
 | _____________/|\____________ |
 |      |/ DHCPREQUEST | DHCPREQUEST\ |      |
 |      |      |      |
 |      |      |      |
 | Commits configuration |      |      |
 |      |      |      |
 | _____________/|      |      |
 |/ DHCPACK |      |      |
 |      |      |      |
 | Initialization complete |      |      |
 |      |      |      |
 .      .      .      .
 .      .      .      .
 |      |      |      |
 | Graceful shutdown  |      |      |
 |      |      |      |
 |      |\ ____________ |      |
 |      | | DHCPRELEASE \|      |
 |      |      |      |
 |      |      |      |
 | Discards lease |      |      |
 |      |      |      |
 v      v      v
```

## 4. Specification of the DHCP client-server protocol -> 4.3 DHCP server behavior -> 4.3.4 DHCPRELEASE message

```plaintext
```
```

## 1. Introduction -> 1.4 Requirements

```plaintext
Derived: Requirement significance definitions
o "MUST" This word or the adjective "REQUIRED" means that the item is an absolute requirement of this specification.
o "MUST NOT" This phrase means that the item is an absolute prohibition of this specification.
o "SHOULD" This word or the adjective "RECOMMENDED" means that there may exist valid reasons in particular circumstances to ignore this item, but the full implications should be understood and the case carefully weighed before choosing a different course.
o "SHOULD NOT" This phrase means that there may exist valid reasons in particular circumstances when the listed behavior is acceptable or even useful, but the full implications should be understood and the case carefully weighed before implementing any behavior described with this label.
o "MAY" This word or the adjective "OPTIONAL" means that this item is truly optional. One vendor may choose to include the item because a particular marketplace requires it or because it enhances the product, for example; another vendor may omit the same item.
```

## 4. Specification of the DHCP client-server protocol -> 4.4 DHCP client behavior

```plaintext
Figure 5: State-transition diagram for DHCP clients
\-------- ------- 
|        | 
+-------------------------->|        |<\-------------------+ 
| INIT-  |                   | +-------------------->| INIT   |                   | 
| REBOOT |DHCPNAK/ +---------->|        |<\---+ 
|        |Restart|           | -------                   |        | 
\-------- |                   DHCPNAK/ | 
         | |                   | Discard offer | 
         | -/Send DHCPDISCOVER | 
         | -/Send DHCPREQUEST  | 
         | |                   | 
         | DHCPACK             v 
         | |                   \----------- 
         | (not accept.)/                   ----------- 
         | |                   | 
         | Send DHCPDECLINE    | 
         | |                   | REBOOTING  | 
         | |                   SELECTING |<\----+ 
         | |                   |        | 
         | /                   |        | 
         | |DHCPOFFER/         | 
         | \-----------        | 
         | /                   ----------- 
         | |Collect            | 
         | | replies           | DHCPACK/ 
         | /                   | / 
         | +----------------+  +-------+ 
         | Record lease, set|          | 
         v timers T1, T2    ------------ 
         send DHCPREQUEST   | 
         | |                   | 
         | +----->|        | 
         |        | REQUESTING | 
         | DHCPNAK, Lease expired/ | 
         | |        | Halt network   | 
         | DHCPOFFER/ | 
         | |        | Discard        ------------ 
         | |        | 
         | ----------- 
         | | 
         | +--------+ 
         | DHCPACK/ | 
         | |        | 
         | -----| REBINDING | 
         | |        | 
         | DHCPACK/ ----------- 
         | |        v Record lease, set ^ 
         | +----------------> \------- /timers T1,T2 | 
         | |                   +----->|        |<\---+ 
         | |                   |        | BOUND  |<\---+ 
         | DHCPOFFER, DHCPACK, |        | 
         | | T2 expires/ DHCPNAK/ DHCPNAK/Discard ------- 
         | Broadcast Halt network | 
         | |                   | DHCPREQUEST | 
         | +-------+ 
         | DHCPACK/ | 
         | T1 expires/ Record lease, set | 
         | Send DHCPREQUEST timers T1, T2 | 
         | to leasing server | 
         | | 
         | ---------- 
         | | 
         | |------------+ 
         | +->| RENEWING | 
         | | 
         | |----------------------------+ 
         \----------
```

## 4. Specification of the DHCP client-server protocol -> 4.4 DHCP client behavior -> 4.4.1 Initialization and allocation of network address

```plaintext
Table 5: Fields and options used by DHCP clients
Field DHCPDISCOVER DHCPREQUEST DHCPDECLINE, DHCPINFORM DHCPRELEASE 
----- ------------ ----------- ----------- 
'op' BOOTREQUEST BOOTREQUEST BOOTREQUEST 
'htype' (From "Assigned Numbers" RFC) 
'hlen' (Hardware address length in octets) 
'hops' 0 0 0 
'xid' selected by client 'xid' from server selected by DHCPOFFER message client 
'secs' 0 or seconds since 0 or seconds since 0 DHCP process started DHCP process started 
'flags' Set 'BROADCAST' Set 'BROADCAST' 0 flag if client flag if client requires broadcast requires broadcast reply reply 
'ciaddr' 0 (DHCPDISCOVER) 0 or client's 0 (DHCPDECLINE) client's network address client's network network address (BOUND/RENEW/REBIND) address (DHCPINFORM) (DHCPRELEASE) 
'yiaddr' 0 0 0 
'siaddr' 0 0 0 
'giaddr' 0 0 0 
'chaddr' client's hardware client's hardware client's hardware address address address 
'sname' options, if options, if (unused) indicated in indicated in 'sname/file' 'sname/file' option; otherwise option; otherwise unused unused 
'file' options, if options, if (unused) indicated in indicated in 'sname/file' 'sname/file' option; otherwise option; otherwise unused unused 
'options' options options (unused) 
Option DHCPDISCOVER DHCPREQUEST DHCPDECLINE, DHCPINFORM DHCPRELEASE 
------ ------------ ----------- ----------- 
Requested IP address MAY MUST (in MUST (DISCOVER) SELECTING or (DHCPDECLINE), MUST NOT INIT-REBOOT) MUST NOT (INFORM) MUST NOT (in (DHCPRELEASE) BOUND or RENEWING) 
IP address lease time MAY MAY MUST NOT (DISCOVER) MUST NOT (INFORM) 
Use 'file'/'sname' fields MAY MAY MAY 
DHCP message type DHCPDISCOVER/ DHCPREQUEST DHCPDECLINE/ DHCPINFORM DHCPRELEASE 
Client identifier MAY MAY MAY 
Vendor class identifier MAY MAY MUST NOT 
Server identifier MUST NOT MUST (after MUST SELECTING) MUST NOT (after INIT-REBOOT, BOUND, RENEWING or REBINDING) 
Parameter request list MAY MAY MUST NOT 
Maximum message size MAY MAY MUST NOT 
Message SHOULD NOT SHOULD NOT SHOULD 
Site-specific MAY MAY MUST NOT 
All others MAY MAY MUST NOT
```

## 4. Specification of the DHCP client-server protocol -> 4.3 DHCP server behavior

```plaintext
Table 3: Use of fields and options by a server
+----------------------+----------------------------------------------------+
| Field/Option         | Use by Server                                       |
+----------------------+----------------------------------------------------+
| op                   | Must be BOOTREQUEST.                                |
| htype, hlen          | Used to identify client's network hardware.         |
| xid                  | Used to match responses with requests.              |
| ciaddr               | Client's current IP address (if bound).            |
| yiaddr               | IP address offered/assigned to client.             |
| siaddr               | Next server in bootstrap (e.g., TFTP server).      |
| giaddr               | Relay agent IP address.                             |
| chaddr               | Client hardware address.                            |
| sname                | Optional server host name.                          |
| file                 | Boot file name.                                     |
| options              | Various protocol parameters (see option docs).      |
+----------------------+----------------------------------------------------+
```

## 4. Specification of the DHCP client-server protocol -> 4.3 DHCP server behavior -> 4.3.1 DHCPDISCOVER message

```plaintext
Table 3: Fields and options used by DHCP servers
Field DHCPOFFER DHCPACK DHCPNAK 
----- --------- ------- ------- 
'op' BOOTREPLY BOOTREPLY BOOTREPLY 
'htype' (From "Assigned Numbers" RFC) 
'hlen' (Hardware address length in octets) 
'hops' 0 0 0 
'xid' 'xid' from client 'xid' from client 'xid' from client 
        DHCPDISCOVER DHCPREQUEST DHCPREQUEST 
        message message message 
'secs' 0 0 0 
'ciaddr' 0 'ciaddr' from 0 
        DHCPREQUEST 
        or 0 
'yiaddr' IP address offered IP address 0 
        to client assigned to client 
'siaddr' IP address of next IP address of next 0 
        bootstrap server bootstrap server 
'flags' 'flags' from 'flags' from 'flags' from 
        client DHCPDISCOVER client DHCPREQUEST client DHCPREQUEST 
        message message message 
'giaddr' 'giaddr' from 'giaddr' from 'giaddr' from 
        client DHCPDISCOVER client DHCPREQUEST client DHCPREQUEST 
        message message message 
'chaddr' 'chaddr' from 'chaddr' from 'chaddr' from 
        client DHCPDISCOVER client DHCPREQUEST client DHCPREQUEST 
        message message message 
'sname' Server host name Server host name (unused) 
        or options or options 
'file' Client boot file Client boot file (unused) 
        name or options name or options 
'options' options options 
Option DHCPOFFER DHCPACK DHCPNAK 
------ --------- ------- ------- 
Requested IP address MUST NOT MUST NOT MUST NOT 
IP address lease time MUST MUST (DHCPREQUEST) MUST NOT 
        MUST NOT (DHCPINFORM) 
Use 'file'/'sname' fields MAY MAY MUST NOT 
DHCP message type DHCPOFFER DHCPACK DHCPNAK 
Parameter request list MUST NOT MUST NOT MUST NOT 
Message SHOULD SHOULD SHOULD 
Client identifier MUST NOT MUST NOT MAY 
Vendor class identifier MAY MAY MAY 
Server identifier MUST MUST MUST 
Maximum message size MUST NOT MUST NOT MUST NOT 
All others MAY MAY MUST NOT
```

## 2. Protocol Summary

```plaintext
Figure 1: Format of a DHCP message
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     op (1)    |   htype (1)   |   hlen (1)    |   hops (1)    |
+---------------+---------------+---------------+---------------+
|                       xid (4)                                |
+-------------------------------+-------------------------------+
|           secs (2)            |           flags (2)           |
+-------------------------------+-------------------------------+
|                          ciaddr (4)                          |
+---------------------------------------------------------------+
|                          yiaddr (4)                          |
+---------------------------------------------------------------+
|                          siaddr (4)                          |
+---------------------------------------------------------------+
|                          giaddr (4)                          |
+---------------------------------------------------------------+
|                                                               |
|                          chaddr (16)                         |
|                                                               |
|                                                               |
+---------------------------------------------------------------+
|                                                               |
|                          sname (64)                          |
+---------------------------------------------------------------+
|                                                               |
|                          file (128)                          |
+---------------------------------------------------------------+
|                                                               |
|                       options (variable)                     |
+---------------------------------------------------------------+
```

```plaintext
Table 1: Description of fields in a DHCP message
FIELD OCTETS DESCRIPTION
----- ------ -----------
op      1     Message op code / message type. 1 = BOOTREQUEST, 2 = BOOTREPLY
htype   1     Hardware address type, see ARP section in "Assigned Numbers" RFC; e.g., '1' = 10mb ethernet.
hlen    1     Hardware address length (e.g. '6' for 10mb ethernet).
hops    1     Client sets to zero, optionally used by relay agents when booting via a relay agent.
xid     4     Transaction ID, a random number chosen by the client, used by the client and server to associate messages and responses between a client and a server.
secs    2     Filled in by client, seconds elapsed since client began address acquisition or renewal process.
flags   2     Flags (see figure 2).
ciaddr  4     Client IP address; only filled in if client is in BOUND, RENEW or REBINDING state and can respond to ARP requests.
yiaddr  4     'your' (client) IP address.
siaddr  4     IP address of next server to use in bootstrap; returned in DHCPOFFER, DHCPACK by server.
giaddr  4     Relay agent IP address, used in booting via a relay agent.
chaddr 16     Client hardware address.
sname  64     Optional server host name, null terminated string.
file  128     Boot file name, null terminated string; "generic" name or null in DHCPDISCOVER, fully qualified directory-path name in DHCPOFFER.
options var   Optional parameters field. See the options documents for a list of defined options.
```

```plaintext
Figure 2: Format of the 'flags' field
1 1 1 1 1 1 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|B|             MBZ            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
B: BROADCAST flag
MBZ: MUST BE ZERO (reserved for future use)
```

