## 4. Protocol Specification -> 4.2. PDU Processing -> 4.2.6. The SNMPv2-Trap-PDU

```plaintext
```
```

## 4. Protocol Specification -> 4.2. PDU Processing -> 4.2.2. The GetNextRequest-PDU -> 4.2.2.1. Example of Table Traversal

```plaintext
Derived: IP net-to-media table entries
Interface-Number Network-Address Physical-Address Type 1 10.0.0.51 00:00:10:01:23:45 static 1 9.2.3.4 00:00:10:54:32:10 dynamic 2 10.0.0.15 00:00:10:98:76:54 dynamic
```

## 4. Protocol Specification -> 4.2. PDU Processing -> 4.2.3. The GetBulkRequest-PDU -> 4.2.3.1. Another Example of Table Traversal

```plaintext
Derived: Initial GetBulkRequest PDU
GetBulkRequest [ non-repeaters = 1, max-repetitions = 2 ] ( sysUpTime, ipNetToMediaPhysAddress, ipNetToMediaType )
```

```plaintext
Derived: First Response PDU
Response (( sysUpTime.0 = "123456" ), ( ipNetToMediaPhysAddress.1.9.2.3.4 = "000010543210" ), ( ipNetToMediaType.1.9.2.3.4 = "dynamic" ), ( ipNetToMediaPhysAddress.1.10.0.0.51 = "000010012345" ), ( ipNetToMediaType.1.10.0.0.51 = "static" ))
```

```plaintext
Derived: Subsequent GetBulkRequest PDU
GetBulkRequest [ non-repeaters = 1, max-repetitions = 2 ] ( sysUpTime, ipNetToMediaPhysAddress.1.10.0.0.51, ipNetToMediaType.1.10.0.0.51 )
```

```plaintext
Derived: Second Response PDU
Response (( sysUpTime.0 = "123466" ), ( ipNetToMediaPhysAddress.2.10.0.0.15 = "000010987654" ), ( ipNetToMediaType.2.10.0.0.15 = "dynamic" ), ( ipNetToMediaNetAddress.1.9.2.3.4 = "9.2.3.4" ), ( ipRoutingDiscards.0 = "2" ))
```

