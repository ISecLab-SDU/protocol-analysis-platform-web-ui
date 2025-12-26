## 8. Client/Server Message Formats

```plaintext
Figure 2: Client/Server Message Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| msg-type | transaction-id |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| |
. options .
. (variable number and length) .
| |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 11. DHCP Unique Identifier (DUID) -> 11.1. DUID Contents

```plaintext
Table 2: DUID Types
+------+------------------------------------------------------+
| Type | Description                                          |
+------+------------------------------------------------------+
| 1    | Link-layer address plus time                         |
| 2    | Vendor-assigned unique ID based on Enterprise Number |
| 3    | Link-layer address                                   |
| 4    | Universally Unique Identifier (UUID) [RFC6355"")]   |
+------+------------------------------------------------------+
```

## 9. Relay Agent/Server Message Formats

```plaintext
Figure 3: Relay Agent/Server Message Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|    msg-type   |   hop-count   |                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               |
|                                                               |
|                          link-address                         |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
|                          peer-address                         |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      options (variable number and length)                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 11. DHCP Unique Identifier (DUID) -> 11.2. DUID Based on Link-Layer Address Plus Time (DUID-LLT)

```plaintext
Figure 4: DUID-LLT Format
 0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| DUID-Type (1) | hardware type (16 bits)                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| time (32 bits)                                                |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
.                                                               .
.                 link-layer address (variable length)          .
.                                                               .
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 11. DHCP Unique Identifier (DUID) -> 11.4. DUID Based on Link-Layer Address (DUID-LL)

```plaintext
Figure 7: DUID-LL Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| DUID-Type (3) | hardware type (16 bits) |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
. . . link-layer address (variable length) . . .
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 6. Operational Models -> 6.3. DHCP for Prefix Delegation

```plaintext
Figure 1: Prefix Delegation Network
______________________ \ / \ \ | ISP core network | \ \\__________ ___________/ | | | +-------+-------+ | | Aggregation | | ISP | device | | network | (delegating | | | router) | | +-------+-------+ | | / |Network link to / |subscriber premises / | +------+------+ \ | CPE | \ | (requesting | \ | router) | | +----+---+----+ | | | | Subscriber \---+-------------+-----+ +-----+------ | network | | | | +----+-----+ +-----+----+ +----+-----+ | |Subscriber| |Subscriber| |Subscriber| / | PC | | PC | | PC | / +----------+ +----------+ +----------+ /
```

## 11. DHCP Unique Identifier (DUID) -> 11.3. DUID Assigned by Vendor Based on Enterprise Number (DUID-EN)

```plaintext
Figure 5: DUID-EN Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| DUID-Type (2) |               enterprise-number               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       enterprise-number (contd)               |
|                               +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                               |        identifier             |
.                               . (variable length)             .
.                               .                               .
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

```plaintext
Figure 6: DUID-EN Example
+---+---+---+---+---+---+---+---+
| 0 | 2 | 0 | 0 | 0 | 9| 12|192|
+---+---+---+---+---+---+---+---+
|132|211| 3 | 0 | 9 | 18|
+---+---+---+---+---+---+
```

## 11. DHCP Unique Identifier (DUID) -> 11.5. DUID Based on Universally Unique Identifier (DUID-UUID)

```plaintext
Figure 8: DUID-UUID Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ | DUID-Type (4) | UUID (128 bits) | +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ | | | | | | -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ | | +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-
```

## 9. Relay Agent/Server Message Formats -> 9.1. Relay-forward Message

```plaintext
Derived: Relay-forward message fields
msg-type RELAY-FORW (12). A 1-octet field. hop-count Number of relay agents that have already relayed this message. A 1-octet field. link-address An address that may be used by the server to identify the link on which the client is located. This is typically a globally scoped unicast address (i.e., GUA or ULA), but see the discussion inSection 19.1.1. A 16-octet field. peer-address The address of the client or relay agent from which the message to be relayed was received. A 16-octet field. options MUST include a Relay Message option (see Section 21.10); MAY include other options, such as the Interface-Id option (see Section 21.18), added by the relay agent. A variable-length field (34 octets less than the size of the message). See Section 13.1 for an explanation of how the link-address field is used.
```

## 7. DHCP Constants -> 7.6. Transmission and Retransmission Parameters

```plaintext
Table 1: Transmission and Retransmission Parameters
+-----------------+------------------+------------------------------+
| Parameter       | Default          | Description                  |
+-----------------+------------------+------------------------------+
| SOL_MAX_DELAY   | 1 sec            | Max delay of first Solicit   |
|                 |                  |                              |
| SOL_TIMEOUT     | 1 sec            | Initial Solicit timeout      |
|                 |                  |                              |
| SOL_MAX_RT      | 3600 secs        | Max Solicit timeout value    |
|                 |                  |                              |
| REQ_TIMEOUT     | 1 sec            | Initial Request timeout      |
|                 |                  |                              |
| REQ_MAX_RT      | 30 secs          | Max Request timeout value    |
|                 |                  |                              |
| REQ_MAX_RC      | 10               | Max Request retry attempts   |
|                 |                  |                              |
| CNF_MAX_DELAY   | 1 sec            | Max delay of first Confirm   |
|                 |                  |                              |
| CNF_TIMEOUT     | 1 sec            | Initial Confirm timeout      |
|                 |                  |                              |
| CNF_MAX_RT      | 4 secs           | Max Confirm timeout          |
|                 |                  |                              |
| CNF_MAX_RD      | 10 secs          | Max Confirm duration         |
|                 |                  |                              |
| REN_TIMEOUT     | 10 secs          | Initial Renew timeout        |
|                 |                  |                              |
| REN_MAX_RT      | 600 secs         | Max Renew timeout value      |
|                 |                  |                              |
| REB_TIMEOUT     | 10 secs          | Initial Rebind timeout       |
|                 |                  |                              |
| REB_MAX_RT      | 600 secs         | Max Rebind timeout value     |
|                 |                  |                              |
| INF_MAX_DELAY   | 1 sec            | Max delay of first           |
|                 |                  | Information-request          |
|                 |                  |                              |
| INF_TIMEOUT     | 1 sec            | Initial Information-request  |
|                 |                  | timeout                      |
|                 |                  |                              |
| INF_MAX_RT      | 3600 secs        | Max Information-request      |
|                 |                  | timeout value                |
|                 |                  |                              |
| REL_TIMEOUT     | 1 sec            | Initial Release timeout      |
|                 |                  |                              |
| REL_MAX_RC      | 4                | Max Release retry attempts   |
|                 |                  |                              |
| DEC_TIMEOUT     | 1 sec            | Initial Decline timeout      |
|                 |                  |                              |
| DEC_MAX_RC      | 4                | Max Decline retry attempts   |
|                 |                  |                              |
| REC_TIMEOUT     | 2 secs           | Initial Reconfigure timeout  |
|                 |                  |                              |
| REC_MAX_RC      | 8                | Max Reconfigure attempts     |
|                 |                  |                              |
| HOP_COUNT_LIMIT | 8                | Max hop count in a           |
|                 |                  | Relay-forward message        |
|                 |                  |                              |
| IRT_DEFAULT     | 86400 secs (24   | Default information refresh  |
|                 | hours)           | time                         |
|                 |                  |                              |
| IRT_MINIMUM     | 600 secs         | Min information refresh time |
|                 |                  |                              |
| MAX_WAIT_TIME   | 60 secs          | Max required time to wait    |
|                 |                  | for a response               |
+-----------------+------------------+------------------------------+
```

## 9. Relay Agent/Server Message Formats -> 9.2. Relay-reply Message

```plaintext
Derived: Relay-reply message fields
msg-type RELAY-REPL (13). A 1-octet field. hop-count Copied from the Relay-forward message. A 1-octet field. link-address Copied from the Relay-forward message. A 16-octet field. peer-address Copied from the Relay-forward message. A 16-octet field. options MUST include a Relay Message option (see Section 21.10); MAY include other options, such as the Interface-Id option (see Section 21.18). A variable-length field (34 octets less than the size of the message).
```

## 15. Reliability of Client-Initiated Message Exchanges

```plaintext
Derived: Retransmission parameters
RT Retransmission timeout IRT Initial retransmission time MRC Maximum retransmission count MRT Maximum retransmission time MRD Maximum retransmission duration RAND Randomization factor
```

## 18. DHCP Configuration Exchanges -> 18.2. Client Behavior -> 18.2.8. Creation and Transmission of Decline Messages

```plaintext
Derived: Decline message transmission parameters
IRT DEC_TIMEOUT MRT 0 MRC DEC_MAX_RC MRD 0
```

## 18. DHCP Configuration Exchanges -> 18.2. Client Behavior -> 18.2.3. Creation and Transmission of Confirm Messages

```plaintext
Derived: Confirm message transmission parameters
IRT CNF_TIMEOUT MRT CNF_MAX_RT MRC 0 MRD CNF_MAX_RD
```

## 18. DHCP Configuration Exchanges -> 18.2. Client Behavior -> 18.2.6. Creation and Transmission of Information-request Messages

```plaintext
Derived: Transmission Parameters
IRT INF_TIMEOUT MRT INF_MAX_RT MRC 0 MRD 0
```

## 18. DHCP Configuration Exchanges

```plaintext
Figure 9: Timeline Diagram of the Messages Exchanged between a Client and Two Servers for the Typical Lifecycle of One or More Leases
Server Server (not selected) Client (selected)
v v v
| | |
| | |
| Begins initialization |
| | |
| start of | _____________/|\_____________ |
4-message |/ Solicit | Solicit \|
exchange | | |
| Determines | Determines configuration |
configuration | | |
| |\ | ____________/| | \________ |
/Advertise | | Advertise\ |/
| | \ |
| | | Collects Advertises |
| | \ |
| | | Selects configuration |
| | | |
| _____________/|\_____________ |
|/ Request | Request \|
| | |
| Commits configuration |
| | |
end of | | _____________/|
4-message | |/ Reply |
exchange | | |
| Initialization complete |
| | |
| . . . . . . |
| T1 (renewal) timer expires |
| | |
| 2-message | _____________/|\_____________ |
exchange |/ Renew | Renew \|
| | |
| | Commits extended lease(s) |
| | |
| | _____________/|
| |/ Reply |
| . . . . . . |
| | |
| Graceful shutdown |
| | |
| 2-message | _____________/|\_____________ |
exchange |/ Release | Release \|
| | |
| | Discards lease(s) |
| | |
| | _____________/|
| |/ Reply |
| | |
v v v
Figure 9: Timeline Diagram of the Messages Exchanged between a Client and Two Servers for the Typical Lifecycle of One or More Leases
```

## 21. DHCP Options -> 21.2. Client Identifier Option

```plaintext
Figure 13: Client Identifier Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_CLIENTID | option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
. . . DUID . . (variable length) . . .
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 19. Relay Agent Behavior -> 19.3. Construction of Relay-reply Messages

```plaintext
Figure 10: Relay-reply Example
msg-type: RELAY-REPL hop-count: 1 link-address: 0 peer-address: A Relay Message option containing the following: msg-type: RELAY-REPL hop-count: 0 link-address: address from link to which C is attached peer-address: C Relay Message option: <response from server>
```

## 21. DHCP Options -> 21.1. Format of DHCP Options

```plaintext
Figure 12: Option Format
  0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| option-code  | option-len   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| option-data                                                  |
|                       (option-len octets)                    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.7. Option Request Option

```plaintext
Figure 18: Option Request Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_ORO | option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| requested-option-code-1 | requested-option-code-2 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| ... |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.8. Preference Option

```plaintext
Figure 19: Preference Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_PREFERENCE | option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| pref-value |
+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.9. Elapsed Time Option

```plaintext
Figure 20: Elapsed Time Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   OPTION_ELAPSED_TIME         |          option-len           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          elapsed-time                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.11. Authentication Option

```plaintext
Figure 22: Authentication Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_AUTH | option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| protocol | algorithm | RDM | |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| |
| replay detection (64 bits) +-+-+-+-+-+-+-+-+
| |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| . authentication information . .
. (variable length) .
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.6. IA Address Option

```plaintext
Figure 17: IA Address Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          OPTION_IAADDR        |           option-len          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
|                          IPv6-address                        |
|                                                               |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      preferred-lifetime                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       valid-lifetime                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      IAaddr-options                           |
|                              ...                              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.12. Server Unicast Option

```plaintext
Figure 23: Server Unicast Option Format
  0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 | OPTION_UNICAST | option-len |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                                                               |
 |                       server-address                         |
 |                                                               |
 |                                                               |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.3. Server Identifier Option

```plaintext
Figure 14: Server Identifier Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ | OPTION_SERVERID | option-len | +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ . . . DUID . . (variable length) . . . +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.16. Vendor Class Option

```plaintext
Figure 28: Vendor Class Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_VENDOR_CLASS | option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| enterprise-number |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
. . . vendor-class-data . . . . . .
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

```plaintext
Figure 29: Format of vendor-class-data Field
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-...-+-+-+-+-+-+-+
| vendor-class-len | opaque-data |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-...-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.18. Interface-Id Option

```plaintext
Figure 32: Interface-Id Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_INTERFACE_ID | option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
. . . interface-id . . .
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.14. Rapid Commit Option

```plaintext
Figure 25: Rapid Commit Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ | OPTION_RAPID_COMMIT | option-len | +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.15. User Class Option

```plaintext
Figure 26: User Class Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_USER_CLASS | option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
. . . user-class-data . . .
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

```plaintext
Figure 27: Format of user-class-data Field
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-...-+-+-+-+-+-+-+
| user-class-len | opaque-data |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-...-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.5. Identity Association for Temporary Addresses Option

```plaintext
Figure 16: Identity Association for Temporary Addresses Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_IA_TA  |  option-len   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          IAID (4 octets)                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
.                       IA_TA-options                          .
.                                                               .
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.10. Relay Message Option

```plaintext
Figure 21: Relay Message Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ | OPTION_RELAY_MSG | option-len | +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ | | . DHCP-relay-message . . . . . +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.17. Vendor-specific Information Option

```plaintext
Figure 30: Vendor-specific Information Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_VENDOR_OPTS | option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| enterprise-number |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
. . . vendor-option-data . . .
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

```plaintext
Figure 31: Vendor-specific Options Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| sub-opt-code | sub-option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
. . . sub-option-data . . .
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.13. Status Code Option

```plaintext
Figure 24: Status Code Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_STATUS_CODE | option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| status-code | |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ |
. . . status-message . . . 
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

```plaintext
Table 3: Status Code Definitions
+---------------+------+--------------------------------------------+
| Name          | Code | Description                                |
+---------------+------+--------------------------------------------+
| Success       | 0    | Success.                                   |
|               |      |                                            |
| UnspecFail    | 1    | Failure, reason unspecified; this status   |
|               |      | code is sent by either a client or a       |
|               |      | server to indicate a failure not           |
|               |      | explicitly specified in this document.     |
|               |      |                                            |
| NoAddrsAvail  | 2    | The server has no addresses available to   |
|               |      | assign to the IA(s).                       |
|               |      |                                            |
| NoBinding     | 3    | Client record (binding) unavailable.       |
|               |      |                                            |
| NotOnLink     | 4    | The prefix for the address is not          |
|               |      | appropriate for the link to which the      |
|               |      | client is attached.                        |
|               |      |                                            |
| UseMulticast  | 5    | Sent by a server to a client to force the  |
|               |      | client to send messages to the server      |
|               |      | using the                                 |
|               |      | All_DHCP_Relay_Agents_and_Servers         |
|               |      | multicast address.                         |
|               |      |                                            |
| NoPrefixAvail | 6    | The server has no prefixes available to    |
|               |      | assign to the IA_PD(s).                    |
+---------------+------+--------------------------------------------+
```

## 21. DHCP Options -> 21.21. Identity Association for Prefix Delegation Option

```plaintext
Figure 35: Identity Association for Prefix Delegation Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_IA_PD  | option-len    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| IAID (4 octets)               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| T1                            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| T2                            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
.                                                               .
.                         IA_PD-options                        .
.                                                               .
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.19. Reconfigure Message Option

```plaintext
Figure 33: Reconfigure Message Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_RECONF_MSG | option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| msg-type |
+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.4. Identity Association for Non-temporary Addresses Option

```plaintext
Figure 15: Identity Association for Non-temporary Addresses Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_IA_NA | option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| IAID (4 octets) |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| T1 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| T2 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| |
. IA_NA-options .
. .
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.20. Reconfigure Accept Option

```plaintext
Figure 34: Reconfigure Accept Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_RECONF_ACCEPT | option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.23. Information Refresh Time Option

```plaintext
Figure 37: Information Refresh Time Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|OPTION_INFORMATION_REFRESH_TIME| option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| information-refresh-time |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.22. IA Prefix Option

```plaintext
Figure 36: IA Prefix Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          OPTION_IAPREFIX      |           option-len          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      preferred-lifetime                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         valid-lifetime                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| prefix-length |                                               |
+-+-+-+-+-+-+-+-+-+-+-+         IPv6-prefix                     |
|                        (16 octets)                            |
|                                                               |
|                                                               |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+         IAprefix-options                |
|                        ...                                    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 20. Authentication of DHCP Messages -> 20.4. Reconfiguration Key Authentication Protocol (RKAP) -> 20.4.1. Use of the Authentication Option in RKAP

```plaintext
Figure 11: RKAP Authentication Information Type
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Type | Value (128 bits) |
+-+-+-+-+-+-+-+
| . . . . .
+-+-+-+-+-+-+-+
|
|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

```plaintext
Derived: Type Field Values
1 Reconfigure key value (used in the Reply message). 2 HMAC-MD5 digest of the message (used in the Reconfigure message). A 1-octet field. Value Data as defined by the Type field. A 16-octet field.
```

## 21. DHCP Options -> 21.25. INF_MAX_RT Option

```plaintext
Figure 39: INF_MAX_RT Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_INF_MAX_RT | option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| INF_MAX_RT value |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## 21. DHCP Options -> 21.24. SOL_MAX_RT Option

```plaintext
Figure 38: SOL_MAX_RT Option Format
0 1 2 3 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| OPTION_SOL_MAX_RT | option-len |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| SOL_MAX_RT value |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## Appendix C. Appearance of Options in the "options" Field of DHCP

```plaintext
Derived: Appearance of Options in DHCP Options Field
Top- IA_NA/ RELAY- RELAY-
Level IA_TA IAADDR IA_PD IAPREFIX FORW REPL
Client ID *
Server ID *
IA_NA/IA_TA *
IAADDR *
IA_PD *
IAPREFIX *
ORO *
Preference *
Elapsed Time *
Relay Message *
* Authentic.
Server Uni.
Status Code *
* *
Rapid Comm.
User Class *
Vendor Class *
Vendor Info.
* *
Interf. ID *
* Reconf. MSG.
Reconf. Accept *
Info Refresh Time *
SOL_MAX_RT *
INF_MAX_RT *
```

## Appendix B. Appearance of Options in Message Types

```plaintext
Derived: Options in message types part 1
Client Server IA_NA/ Elap. Relay Server ID ID IA_TA IA_PD ORO Pref Time Msg. Auth. Unicast Solicit * * * * * Advert. * * * * * Request * * * * * * Confirm * * * Renew * * * * * * Rebind * * * * * Decline * * * * * Release * * * * * Reply * * * * * * Reconf. * * * Inform. * (see note) * * R-forw. * R-repl. * NOTE: The Server Identifier option (seeSection 21.3) is only included in Information-request messages that are sent in response to a Reconfigure (see Section 18.2.6).
```

```plaintext
Derived: Options in message types part 2
Info Status Rap. User Vendor Vendor Inter. Recon. Recon. Refresh Code Comm. Class Class Spec. ID Msg. Accept Time Solicit * * * * * Advert. * * * * * Request * * * * Confirm * * * Renew * * * * Rebind * * * * Decline * * * Release * * * Reply * * * * * * * Reconf. * Inform. * * * * R-forw. * * R-repl. * *
```

```plaintext
Derived: SOL_MAX_RT and INF_MAX_RT options
SOL_MAX_RT INF_MAX_RT Solicit Advert. * Request Confirm Renew Rebind Decline Release Reply * * Reconf. Inform. R-forw. R-repl.
```

## 24. IANA Considerations

```plaintext
Table 4: Updated Options
+---------+--------------------------+------------------+-----------+
| Option  | Option Name ("OPTION"    | Client ORO (1)   | Singleton |
|         | prefix removed)          |                 | Option    |
+---------+--------------------------+------------------+-----------+
| 1      | CLIENTID                | No               | Yes       |
| 2      | SERVERID                | No               | Yes       |
| 3      | IA_NA                   | No               | No        |
| 4      | IA_TA                   | No               | No        |
| 5      | IAADDR                  | No               | No        |
| 6      | ORO                     | No               | Yes       |
| 7      | PREFERENCE              | No               | Yes       |
| 8      | ELAPSED_TIME            | No               | Yes       |
| 9      | RELAY_MSG               | No               | Yes       |
| 11     | AUTH                    | No               | Yes       |
| 12     | UNICAST                 | No               | Yes       |
| 13     | STATUS_CODE             | No               | Yes       |
| 14     | RAPID_COMMIT            | No               | Yes       |
| 15     | USER_CLASS              | No               | Yes       |
| 16     | VENDOR_CLASS            | No               | No (2)    |
| 17     | VENDOR_OPTS             | Optional         | No (2)    |
| 18     | INTERFACE_ID            | No               | Yes       |
| 19     | RECONF_MSG              | No               | Yes       |
| 20     | RECONF_ACCEPT           | No               | Yes       |
| 21     | SIP_SERVER_D            | Yes              | Yes       |
| 22     | SIP_SERVER_A            | Yes              | Yes       |
| 23     | DNS_SERVERS             | Yes              | Yes       |
| 24     | DOMAIN_LIST             | Yes              | Yes       |
| 25     | IA_PD                   | No               | No        |
| 26     | IAPREFIX                | No               | No        |
| 27     | NIS_SERVERS             | Yes              | Yes       |
| 28     | NISP_SERVERS            | Yes              | Yes       |
| 29     | NIS_DOMAIN_NAME         | Yes              | Yes       |
| 30     | NISP_DOMAIN_NAME        | Yes              | Yes       |
| 31     | SNTP_SERVERS            | Yes              | Yes       |
| 32     | INFORMATION_REFRESH_TIME| Required for     | Yes       |
|        |                          | Information-     |           |
|        |                          | request          |           |
| 33     | BCMCS_SERVER_D          | Yes              | Yes       |
| 34     | BCMCS_SERVER_A          | Yes              | Yes       |
| 36     | GEOCONF_CIVIC           | Yes              | Yes       |
| 37     | REMOTE_ID               | No               | Yes       |
| 38     | SUBSCRIBER_ID           | No               | Yes       |
| 39     | CLIENT_FQDN             | Yes              | Yes       |
| 40     | PANA_AGENT              | Yes              | Yes       |
| 41     | NEW_POSIX_TIMEZONE      | Yes              | Yes       |
| 42     | NEW_TZDB_TIMEZONE       | Yes              | Yes       |
| 43     | ERO                     | No               | Yes       |
| 44     | LQ_QUERY                | No               | Yes       |
| 45     | CLIENT_DATA             | No               | Yes       |
| 46     | CLT_TIME                | No               | Yes       |
| 47     | LQ_RELAY_DATA           | No               | Yes       |
| 48     | LQ_CLIENT_LINK          | No               | Yes       |
| 49     | MIP6_HNIDF              | Yes              | Yes       |
| 50     | MIP6_VDINF              | Yes              | Yes       |
| 51     | V6_LOST                 | Yes              | Yes       |
| 52     | CAPWAP_AC_V6            | Yes              | Yes       |
| 53     | RELAY_ID                | No               | Yes       |
| 54     | IPv6_Address-MoS        | Yes              | Yes       |
| 55     | IPv6_FQDN-MoS           | Yes              | Yes       |
| 56     | NTP_SERVER              | Yes              | Yes       |
| 57     | V6_ACCESS_DOMAIN        | Yes              | Yes       |
| 58     | SIP_UA_CS_LIST          | Yes              | Yes       |
| 59     | OPT_BOOTFILE_URL        | Yes              | Yes       |
| 60     | OPT_BOOTFILE_PARAM      | Yes              | Yes       |
| 61     | CLIENT_ARCH_TYPE        | No               | Yes       |
| 62     | NII                     | Yes              | Yes       |
| 63     | GEOLOCATION             | Yes              | Yes       |
| 64     | AFTR_NAME               | Yes              | Yes       |
| 65     | ERP_LOCAL_DOMAIN_NAME   | Yes              | Yes       |
| 66     | RSOO                    | No               | Yes       |
| 67     | PD_EXCLUDE              | Yes              | Yes       |
| 68     | VSS                     | No               | Yes       |
| 69     | MIP6_IDINF              | Yes              | Yes       |
| 70     | MIP6_UDINF              | Yes              | Yes       |
| 71     | MIP6_HNP                | Yes              | Yes       |
| 72     | MIP6_HAA                | Yes              | Yes       |
| 73     | MIP6_HAF                | Yes              | Yes       |
| 74     | RDNSS_SELECTION         | Yes              | No        |
| 75     | KRB_PRINCIPAL_NAME      | Yes              | Yes       |
| 76     | KRB_REALM_NAME          | Yes              | Yes       |
| 77     | KRB_DEFAULT_REALM_NAME  | Yes              | Yes       |
| 78     | KRB_KDC                 | Yes              | Yes       |
| 79     | CLIENT_LINKLAYER_ADDR   | No               | Yes       |
| 80     | LINK_ADDRESS            | No               | Yes       |
| 81     | RADIUS                  | No               | Yes       |
| 82     | SOL_MAX_RT              | Required for     | Yes       |
|        |                          | Solicit          |           |
| 83     | INF_MAX_RT              | Required for     | Yes       |
|        |                          | Information-     |           |
|        |                          | request          |           |
| 84     | ADDRSEL                 | Yes              | Yes       |
| 85     | ADDRSEL_TABLE           | Yes              | Yes       |
| 86     | V6_PCP_SERVER           | Yes              | No        |
| 87     | DHCPV4_MSG              | No               | Yes       |
| 88     | DHCP4_O_DHCP6_SERVER    | Yes              | Yes       |
| 89     | S46_RULE                | No               | No (3)    |
| 90     | S46_BR                  | No               | No        |
| 91     | S46_DMR                 | No               | Yes       |
| 92     | S46_V4V6BIND            | No               | Yes       |
| 93     | S46_PORTPARAMS          | No               | Yes       |
| 94     | S46_CONT_MAPE           | Yes              | No        |
| 95     | S46_CONT_MAPT           | Yes              | Yes       |
| 96     | S46_CONT_LW             | Yes              | Yes       |
| 97     | 4RD                     | Yes              | Yes       |
| 98     | 4RD_MAP_RULE            | Yes              | Yes       |
| 99     | 4RD_NON_MAP_RULE        | Yes              | Yes       |
| 100    | LQ_BASE_TIME            | No               | Yes       |
| 101    | LQ_START_TIME           | No               | Yes       |
| 102    | LQ_END_TIME             | No               | Yes       |
| 103    | DHCP Captive-Portal     | Yes              | Yes       |
| 104    | MPL_PARAMETERS          | Yes              | No        |
| 105    | ANI_ATT                 | No               | Yes       |
| 106    | ANI_NETWORK_NAME        | No               | Yes       |
| 107    | ANI_AP_NAME             | No               | Yes       |
| 108    | ANI_AP_BSSID            | No               | Yes       |
| 109    | ANI_OPERATOR_ID         | No               | Yes       |
| 110    | ANI_OPERATOR_REALM      | No               | Yes       |
| 111    | S46_PRIORITY            | Yes              | Yes       |
| 112    | MUD_URL_V6              | No               | Yes       |
| 113    | V6_PREFIX64             | Yes              | No        |
| 114    | F_BINDING_STATUS        | No               | Yes       |
| 115    | F_CONNECT_FLAGS         | No               | Yes       |
| 116    | F_DNS_REMOVAL_INFO      | No               | Yes       |
| 117    | F_DNS_HOST_NAME         | No               | Yes       |
| 118    | F_DNS_ZONE_NAME         | No               | Yes       |
| 119    | F_DNS_FLAGS             | No               | Yes       |
| 120    | F_EXPIRATION_TIME       | No               | Yes       |
| 121    | F_MAX_UNACKED_BNDUPD    | No               | Yes       |
| 122    | F_MCLT                  | No               | Yes       |
| 123    | F_PARTNER_LIFETIME      | No               | Yes       |
| 124    | F_PARTNER_LIFETIME_SENT | No               | Yes       |
| 125    | F_PARTNER_DOWN_TIME     | No               | Yes       |
| 126    | F_PARTNER_RAW_CLT_TIME  | No               | Yes       |
| 127    | F_PROTOCOL_VERSION      | No               | Yes       |
| 128    | F_KEEPALIVE_TIME        | No               | Yes       |
| 129    | F_RECONFIGURE_DATA      | No               | Yes       |
| 130    | F_RELATIONSHIP_NAME     | No               | Yes       |
| 131    | F_SERVER_FLAGS          | No               | Yes       |
| 132    | F_SERVER_STATE          | No               | Yes       |
| 133    | F_START_TIME_OF_STATE   | No               | Yes       |
| 134    | F_STATE_EXPIRATION_TIME | No               | Yes       |
| 135    | RELAY_PORT              | No               | Yes       |
| 143    | IPv6_Address-ANDSF      | Yes              | Yes       |
+---------+--------------------------+------------------+-----------+
```

