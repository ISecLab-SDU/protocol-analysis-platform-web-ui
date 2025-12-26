## 9. State Diagrams

```plaintext
Derived: State diagram for FTP authentication and authorization
,------------------,
USER __\| Unauthenticated |_________\ | /| (new connection) | /| | `------------------' | | | | | | AUTH | | V | | / \ | | 4yz,5yz / \ 234 | |<\--------< >\------------->. | | \ / | | | \\_/ | | | | | | | | 334 | | | V | | | ,--------------------, | | | | Need Security Data |<\--. | | | `--------------------' | | | | | | | | | | ADAT | | | | V | | | | / \ | | | | 4yz,5yz / \ 335 | | | `<\--------< >\-----------' | | \ / | | \\_/ | | | | | | 235 | | V | | ,---------------. | | ,--->| Authenticated |<\--------' | After the client and server | `---------------' | have completed authenti- | | | cation, command must be | | USER | integrity-protected if | | | integrity is available. The | |<\-------------------' CCC command may be issued to | V relax this restriction. | / \ | 4yz,5yz / \ 2yz |<\--------< >\------------->. | \ / | | \\_/ | | | | | | 3yz | | V | | ,---------------. | | | Need Password | | | `---------------' | | | | | | PASS | | V | | / \ | | 4yz,5yz / \ 2yz | |<\--------< >\------------->| | \ / | | \\_/ | | | | | | 3yz | | V | | ,--------------. | | | Need Account | | | `--------------' | | | | | | ACCT | | V | | / \ | | 4yz,5yz / \ 2yz | `<\--------< >\------------->| \ / | \\_/ | | | | 3yz | V | ,-------------. | | Authorized |/________| | (Logged in) |\ `-------------'
```

## 8. Declarative specifications

```plaintext
Derived: FTP Security commands syntax
AUTH <SP> <mechanism-name> <CRLF> ADAT <SP> <base64data> <CRLF> PROT <SP> <prot-code> <CRLF> PBSZ <SP> <decimal-integer> <CRLF> MIC <SP> <base64data> <CRLF> CONF <SP> <base64data> <CRLF> ENC <SP> <base64data> <CRLF> <mechanism-name> ::= <string> <base64data> ::= <string> ; must be formatted as described in section 9 <prot-code> ::= C | S | E | P <decimal-integer> ::= any decimal integer from 1 to (2^32)-1
```

```plaintext
Derived: Security Association Setup command-reply sequences
AUTH 234 334 502, 504, 534, 431 500, 501, 421 ADAT 235 335 503, 501, 535 500, 501, 421
```

```plaintext
Derived: Data protection negotiation command-reply sequences
PBSZ 200 503 500, 501, 421, 530 PROT 200 504, 536, 503, 534, 431 500, 501, 421, 530
```

```plaintext
Derived: Command channel protection command-reply sequences
MIC 535, 533 500, 501, 421 CONF 535, 533 500, 501, 421 ENC 535, 533 500, 501, 421
```

```plaintext
Derived: Security-Enhanced login command-reply sequences
USER 232 336
```

```plaintext
Derived: Data channel command-reply sequences
STOR 534, 535 STOU 534, 535 RETR 534, 535 LIST 534, 535 NLST 534, 535 APPE 534, 535
```

