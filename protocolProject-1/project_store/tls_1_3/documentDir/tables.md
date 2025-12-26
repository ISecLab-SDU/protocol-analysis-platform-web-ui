## 3. Presentation Language -> 3.1. Basic Block Size

```plaintext
Derived: Multi-byte data item formation example
value = (byte[0] << 8*(n-1)) | (byte[1] << 8*(n-2)) | ... | byte[n-1];
```

## 1. Introduction -> 1.1. Conventions and Terminology

```plaintext
Derived: Key terms and their definitions
client: The endpoint initiating the TLS connection.
connection: A transport-layer connection between two endpoints.
endpoint: Either the client or server of the connection.
handshake: An initial negotiation between client and server that establishes the parameters of their subsequent interactions within TLS.
peer: An endpoint. When discussing a particular endpoint, "peer" refers to the endpoint that is not the primary subject of discussion.
receiver: An endpoint that is receiving records.
sender: An endpoint that is transmitting records.
server: The endpoint that did not initiate the TLS connection.
```

## 3. Presentation Language -> 3.3. Numbers

```plaintext
Derived: Predefined numeric types list
uint8 uint16[2];
uint8 uint24[3];
uint8 uint32[4];
uint8 uint64[8];
```

## 2. Protocol Overview -> 2.1. Incorrect DHE Share

```plaintext
Figure 2: Message Flow for a Full Handshake with Mismatched Parameters
Client Server
ClientHello
+ key_share -------->

HelloRetryRequest
<--------- + key_share

ClientHello
+ key_share -------->
                         ServerHello
                         + key_share
                         {EncryptedExtensions}
                         {CertificateRequest*}
                         {Certificate*}
                         {CertificateVerify*}
                         {Finished}
                         <--------
                         [Application Data*]
{Certificate*}
{CertificateVerify*}
{Finished}
-------->
[Application Data]
<------>
[Application Data]
```

## 3. Presentation Language -> 3.4. Vectors

```plaintext
Derived: Fixed-length vector example
opaque Datum[3]; /* three uninterpreted bytes */
Datum Data[9]; /* three consecutive 3-byte vectors */
```

```plaintext
Derived: Variable-length vector examples
opaque mandatory<300..400>; /* length field is two bytes, cannot be empty */
uint16 longer<0..800>; /* zero to 400 16-bit unsigned integers */
```

## 4. Handshake Protocol -> 4.1. Key Exchange Messages

```plaintext
```
```

## 3. Presentation Language -> 3.8. Variants

```plaintext
Derived: VariantRecord structure example
enum { apple(0), orange(1) } VariantTag;
struct {
  uint16 number;
  opaque string<0..10>; /* variable length */
} V1;
struct {
  uint32 number;
  opaque string[10]; /* fixed length */
} V2;
struct {
  VariantTag type;
  select (VariantRecord.type) {
    case apple: V1;
    case orange: V2;
  };
} VariantRecord;
```

## 3. Presentation Language -> 3.5. Enumerateds

```plaintext
Derived: Example of enumerated definition
enum { e1(v1), e2(v2), ... , en(vn) [[, (n)]] } Te;
```

```plaintext
Derived: Color enumerated example
enum { red(3), blue(5), white(7) } Color;
```

```plaintext
Derived: Taste enumerated example with width specification
enum { sweet(1), sour(2), bitter(4), (32000) } Taste;
```

```plaintext
Derived: Mood enumerated example with value ranges
enum { sad(0), meh(1..254), happy(255) } Mood;
```

## 4. Handshake Protocol -> 4.1. Key Exchange Messages -> 4.1.1. Cryptographic Negotiation

```plaintext
Derived: ClientHello Options
- A list of cipher suites which indicates the AEAD algorithm/HKDF hash pairs which the client supports.
- A "supported_groups" (Section 4.2.7) extension which indicates the (EC)DHE groups which the client supports and a "key_share" (Section 4.2.8) extension which contains (EC)DHE shares for some or all of these groups.
- A "signature_algorithms" (Section 4.2.3) extension which indicates the signature algorithms which the client can accept. A "signature_algorithms_cert" extension (Section 4.2.3) may also be added to indicate certificate-specific signature algorithms.
- A "pre_shared_key" (Section 4.2.11) extension which contains a list of symmetric key identities known to the client and a "psk_key_exchange_modes" (Section 4.2.9) extension which indicates the key exchange modes that may be used with PSKs.
```

```plaintext
Derived: Server Parameter Selection
- If PSK is being used, then the server will send a "pre_shared_key" extension indicating the selected key.
- When (EC)DHE is in use, the server will also provide a "key_share" extension. If PSK is not being used, then (EC)DHE and certificate-based authentication are always used.
- When authenticating via a certificate, the server will send the Certificate (Section 4.4.2) and CertificateVerify (Section 4.4.3) messages.
```

## 2. Protocol Overview -> 2.2. Resumption and Pre-Shared Key (PSK)

```plaintext
Figure 3: Message Flow for Resumption and PSK
Client Server
Initial Handshake:
ClientHello \+ key_share --------> 
ServerHello \+ key_share 
{EncryptedExtensions} 
{CertificateRequest*} 
{Certificate*} 
{CertificateVerify*} 
{Finished} 
<\-------- [Application Data*]
{Certificate*} 
{CertificateVerify*} 
{Finished} 
-------> 
<\-------- [NewSessionTicket]
[Application Data] 
<-------> [Application Data]

Subsequent Handshake:
ClientHello \+ key_share* \+ pre_shared_key --------> 
ServerHello \+ pre_shared_key \+ key_share* 
{EncryptedExtensions} 
{Finished} 
<\-------- [Application Data*]
{Finished} 
-------> 
[Application Data] 
<-------> [Application Data]
```

## 4. Handshake Protocol

```plaintext
Derived: HandshakeType values
enum { client_hello(1), server_hello(2), new_session_ticket(4), end_of_early_data(5), encrypted_extensions(8), certificate(11), certificate_request(13), certificate_verify(15), finished(20), key_update(24), message_hash(254), (255) } HandshakeType;
```

```plaintext
Derived: Handshake structure
struct {
    HandshakeType msg_type;    /* handshake type */
    uint24 length;             /* remaining bytes in message */
    select (Handshake.msg_type) {
        case client_hello:          ClientHello;
        case server_hello:          ServerHello;
        case end_of_early_data:     EndOfEarlyData;
        case encrypted_extensions:  EncryptedExtensions;
        case certificate_request:   CertificateRequest;
        case certificate:           Certificate;
        case certificate_verify:    CertificateVerify;
        case finished:              Finished;
        case new_session_ticket:    NewSessionTicket;
        case key_update:            KeyUpdate;
    };
} Handshake;
```

## 4. Handshake Protocol -> 4.1. Key Exchange Messages -> 4.1.2. Client Hello

```plaintext
Derived: ClientHello structure
struct {
    ProtocolVersion legacy_version = 0x0303;    /* TLS v1.2 */
    Random random;
    opaque legacy_session_id<0..32>;
    CipherSuite cipher_suites<2..2^16-2>;
    opaque legacy_compression_methods<1..2^8-1>;
    Extension extensions<8..2^16-1>;
} ClientHello;
```

## 3. Presentation Language -> 3.6. Constructed Types

```plaintext
Derived: Structure type definition example
struct { T1 f1; T2 f2; ... Tn fn; } T;
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.2. Cookie

```plaintext
Derived: Cookie structure definition
struct { opaque cookie<1..2^16-1>; } Cookie;
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.5. OID Filters

```plaintext
Derived: OIDFilter structure definition
struct {
    opaque certificate_extension_oid<1..2^8-1>;
    opaque certificate_extension_values<0..2^16-1>;
} OIDFilter;
```

```plaintext
Derived: OIDFilterExtension structure definition
struct {
    OIDFilter filters<0..2^16-1>;
} OIDFilterExtension;
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.4. Certificate Authorities

```plaintext
Derived: CertificateAuthoritiesExtension structure
opaque DistinguishedName<1..2^16-1>;
struct {
    DistinguishedName authorities<3..2^16-1>;
} CertificateAuthoritiesExtension;
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.1. Supported Versions

```plaintext
Derived: SupportedVersions struct definition
struct {
    select (Handshake.msg_type) {
        case client_hello: ProtocolVersion versions<2..254>;
        case server_hello: /* and HelloRetryRequest */ ProtocolVersion selected_version;
    };
} SupportedVersions;
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.8. Key Share -> 4.2.8.1. Diffie-Hellman Parameters

```plaintext
Derived: Diffie-Hellman Public Key Encoding
opaque key_exchange field of KeyShareEntry contains:
Y = g^X mod p (big-endian integer)
Left-padded with zeros to size of p in bytes
```

## 4. Handshake Protocol -> 4.1. Key Exchange Messages -> 4.1.3. Server Hello

```plaintext
Derived: ServerHello structure
struct {
  ProtocolVersion legacy_version = 0x0303;    /* TLS v1.2 */
  Random random;
  opaque legacy_session_id_echo<0..32>;
  CipherSuite cipher_suite;
  uint8 legacy_compression_method = 0;
  Extension extensions<6..2^16-1>;
} ServerHello;
```

## 4. Handshake Protocol -> 4.2. Extensions

```plaintext
Derived: TLS Extensions and Their Applicable Messages
+--------------------------------------------------+-------------+
| Extension                                        | TLS 1.3     |
+--------------------------------------------------+-------------+
| server_name [RFC6066 Extensions: Extension Definitions"")] | CH, EE      |
|                                                  |             |
| max_fragment_length [RFC6066 Extensions: Extension Definitions"")] | CH, EE      |
|                                                  |             |
| status_request [RFC6066 Extensions: Extension Definitions"")] | CH, CR, CT  |
|                                                  |             |
| supported_groups [RFC7919"")]                    | CH, EE      |
|                                                  |             |
| signature_algorithms (RFC 8446)                  | CH, CR      |
|                                                  |             |
| use_srtp [RFC5764 Extension to Establish Keys for the Secure Real-time Transport Protocol \(SRTP\)"")] | CH, EE      |
|                                                  |             |
| heartbeat [RFC6520 and Datagram Transport Layer Security \(DTLS\) Heartbeat Extension"")] | CH, EE      |
|                                                  |             |
| application_layer_protocol_negotiation [RFC7301 Application-Layer Protocol Negotiation Extension"")] | CH, EE      |
|                                                  |             |
| signed_certificate_timestamp [RFC6962]           | CH, CR, CT  |
|                                                  |             |
| client_certificate_type [RFC7250 and Datagram Transport Layer Security \(DTLS\)"")] | CH, EE      |
|                                                  |             |
| server_certificate_type [RFC7250 and Datagram Transport Layer Security \(DTLS\)"")] | CH, EE      |
|                                                  |             |
| padding [RFC7685 ClientHello Padding Extension"")] | CH          |
|                                                  |             |
| key_share (RFC 8446)                             | CH, SH, HRR |
|                                                  |             |
| pre_shared_key (RFC 8446)                        | CH, SH      |
|                                                  |             |
| psk_key_exchange_modes (RFC 8446)                | CH          |
|                                                  |             |
| early_data (RFC 8446)                            | CH, EE, NST |
|                                                  |             |
| cookie (RFC 8446)                                | CH, HRR     |
|                                                  |             |
| supported_versions (RFC 8446)                    | CH, SH, HRR |
|                                                  |             |
| certificate_authorities (RFC 8446)               | CH, CR      |
|                                                  |             |
| oid_filters (RFC 8446)                           | CR          |
|                                                  |             |
| post_handshake_auth (RFC 8446)                   | CH          |
|                                                  |             |
| signature_algorithms_cert (RFC 8446)             | CH, CR      |
+--------------------------------------------------+-------------+
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.8. Key Share -> 4.2.8.2. ECDHE Parameters

```plaintext
Derived: UncompressedPointRepresentation struct
struct {
   uint8 legacy_form = 4;
   opaque X[coordinate_length];
   opaque Y[coordinate_length];
} UncompressedPointRepresentation;
```

## 2. Protocol Overview -> 2.3. 0-RTT Data

```plaintext
Figure 4: Message Flow for a 0-RTT Handshake
Client Server
ClientHello \+ early_data \+ key_share* \+ psk_key_exchange_modes \+ pre_shared_key (Application Data*) --------> 
ServerHello \+ pre_shared_key \+ key_share* {EncryptedExtensions} \+ early_data* {Finished} <\-------- 
[Application Data*] (EndOfEarlyData) {Finished} --------> 
[Application Data] <\-------> [Application Data]

\+ Indicates noteworthy extensions sent in the previously noted message.
* Indicates optional or situation-dependent messages/extensions that are not always sent.
() Indicates messages protected using keys derived from a client_early_traffic_secret.
{} Indicates messages protected using keys derived from a [sender]_handshake_traffic_secret.
[] Indicates messages protected using keys derived from [sender]_application_traffic_secret_N.
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.9. Pre-Shared Key Exchange Modes

```plaintext
Derived: PskKeyExchangeMode enum and PskKeyExchangeModes struct
enum {
      psk_ke(0), psk_dhe_ke(1), (255)
} PskKeyExchangeMode;

struct {
      PskKeyExchangeMode ke_modes<1..255>;
} PskKeyExchangeModes;
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.11. Pre-Shared Key Extension -> 4.2.11.1. Ticket Age

```plaintext
Derived: Obfuscated Ticket Age Calculation
   The "obfuscated_ticket_age" field of each PskIdentity contains an obfuscated version of the ticket age formed by taking the age in milliseconds and adding the "ticket_age_add" value that was included with the ticket (see Section 4.6.1), modulo 2^32.
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.10. Early Data Indication

```plaintext
Derived: EarlyDataIndication struct definition
struct {} Empty;
struct {
    select (Handshake.msg_type) {
        case new_session_ticket: uint32 max_early_data_size;
        case client_hello: Empty;
        case encrypted_extensions: Empty;
    };
} EarlyDataIndication;
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.3. Signature Algorithms

```plaintext
Derived: SignatureScheme enum and SignatureSchemeList struct
enum {
   /* RSASSA-PKCS1-v1_5 algorithms */
   rsa_pkcs1_sha256(0x0401),
   rsa_pkcs1_sha384(0x0501),
   rsa_pkcs1_sha512(0x0601),
   /* ECDSA algorithms */
   ecdsa_secp256r1_sha256(0x0403),
   ecdsa_secp384r1_sha384(0x0503),
   ecdsa_secp521r1_sha512(0x0603),
   /* RSASSA-PSS algorithms with public key OID rsaEncryption */
   rsa_pss_rsae_sha256(0x0804),
   rsa_pss_rsae_sha384(0x0805),
   rsa_pss_rsae_sha512(0x0806),
   /* EdDSA algorithms */
   ed25519(0x0807),
   ed448(0x0808),
   /* RSASSA-PSS algorithms with public key OID RSASSA-PSS */
   rsa_pss_pss_sha256(0x0809),
   rsa_pss_pss_sha384(0x080a),
   rsa_pss_pss_sha512(0x080b),
   /* Legacy algorithms */
   rsa_pkcs1_sha1(0x0201),
   ecdsa_sha1(0x0203),
   /* Reserved Code Points */
   private_use(0xFE00..0xFFFF),
   (0xFFFF)
} SignatureScheme;

struct {
   SignatureScheme supported_signature_algorithms<2..2^16-2>;
} SignatureSchemeList;
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.11. Pre-Shared Key Extension -> 4.2.11.2. PSK Binder

```plaintext
Derived: Transcript hash computation for PSK binder
Transcript-Hash(Truncate(ClientHello1))
```

```plaintext
Derived: Transcript hash computation with HelloRetryRequest
Transcript-Hash(ClientHello1, HelloRetryRequest, Truncate(ClientHello2))
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.11. Pre-Shared Key Extension -> 4.2.11.3. Processing Order

```plaintext
Derived: Client and server message processing order for 0-RTT data
Clients are permitted to "stream" 0-RTT data until they receive the server's Finished, only then sending the EndOfEarlyData message, followed by the rest of the handshake. In order to avoid deadlocks, when accepting "early_data", servers MUST process the client's ClientHello and then immediately send their flight of messages, rather than waiting for the client's EndOfEarlyData message before sending its ServerHello.
```

## 4. Handshake Protocol -> 4.3. Server Parameters -> 4.3.1. Encrypted Extensions

```plaintext
Derived: EncryptedExtensions message structure
   struct {
      Extension extensions<0..2^16-1>;
   } EncryptedExtensions;
```

## 4. Handshake Protocol -> 4.4. Authentication Messages -> 4.4.1. The Transcript Hash

```plaintext
```
```

## 4. Handshake Protocol -> 4.4. Authentication Messages -> 4.4.2. Certificate -> 4.4.2.1. OCSP Status and SCT Extensions

```plaintext
```
```

## 2. Protocol Overview

```plaintext
Figure 1: Message Flow for Full TLS Handshake
Client Server
Key ^ ClientHello
Exch | + key_share*
     | + signature_algorithms*
     | + psk_key_exchange_modes*
     v + pre_shared_key*
     --------> ServerHello  ^ Key
             \+ key_share*   | Exch
             \+ pre_shared_key* v
             {EncryptedExtensions}  ^ Server
             {CertificateRequest*}  v Params
             {Certificate*}         ^
             {CertificateVerify*}   | Auth
             {Finished}             v
             <\-------- [Application Data*]
                       ^ {Certificate*}
                       Auth | {CertificateVerify*}
                           v {Finished}
                     --------> 
                     [Application Data]
                     <\-------> [Application Data]

\+ Indicates noteworthy extensions sent in the previously noted message.
* Indicates optional or situation-dependent messages/extensions that are not always sent.
{} Indicates messages protected using keys derived from a [sender]_handshake_traffic_secret.
[] Indicates messages protected using keys derived from [sender]_application_traffic_secret_N.
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.8. Key Share

```plaintext
Derived: KeyShareEntry struct
struct {
  NamedGroup group;
  opaque key_exchange<1..2^16-1>;
} KeyShareEntry;
```

```plaintext
Derived: KeyShareClientHello struct
struct {
  KeyShareEntry client_shares<0..2^16-1>;
} KeyShareClientHello;
```

```plaintext
Derived: KeyShareHelloRetryRequest struct
struct {
  NamedGroup selected_group;
} KeyShareHelloRetryRequest;
```

```plaintext
Derived: KeyShareServerHello struct
struct {
  KeyShareEntry server_share;
} KeyShareServerHello;
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.6. Post-Handshake Client Authentication

```plaintext
Derived: PostHandshakeAuth structure definition
struct {} PostHandshakeAuth;
```

## 4. Handshake Protocol -> 4.5. End of Early Data

```plaintext
```
```

## 4. Handshake Protocol -> 4.4. Authentication Messages -> 4.4.2. Certificate

```plaintext
Derived: Certificate and CertificateEntry structures
enum { X509(0), RawPublicKey(2), (255) } CertificateType;
struct {
    select (certificate_type) {
        case RawPublicKey:
            /* From RFC 7250 ASN.1_subjectPublicKeyInfo */
            opaque ASN1_subjectPublicKeyInfo<1..2^24-1>;
        case X509:
            opaque cert_data<1..2^24-1>;
    };
    Extension extensions<0..2^16-1>;
} CertificateEntry;
struct {
    opaque certificate_request_context<0..2^8-1>;
    CertificateEntry certificate_list<0..2^24-1>;
} Certificate;
```

## 4. Handshake Protocol -> 4.3. Server Parameters -> 4.3.2. Certificate Request

```plaintext
Derived: CertificateRequest structure
struct {
    opaque certificate_request_context<0..2^8-1>;
    Extension extensions<2..2^16-1>;
} CertificateRequest;
```

## 4. Handshake Protocol -> 4.4. Authentication Messages -> 4.4.4. Finished

```plaintext
Derived: Finished message structure
struct {
   opaque verify_data[Hash.length];
} Finished;
```

## 4. Handshake Protocol -> 4.6. Post-Handshake Messages -> 4.6.1. New Session Ticket Message

```plaintext
Derived: NewSessionTicket message structure
struct {
    uint32 ticket_lifetime;
    uint32 ticket_age_add;
    opaque ticket_nonce<0..255>;
    opaque ticket<1..2^16-1>;
    Extension extensions<0..2^16-2>;
} NewSessionTicket;
```

## 5. Record Protocol -> 5.3. Per-Record Nonce

```plaintext
Derived: Per-record nonce formation
1. The 64-bit record sequence number is encoded in network byte order and padded to the left with zeros to iv_length.
2. The padded sequence number is XORed with either the static client_write_iv or server_write_iv (depending on the role).
```

## 5. Record Protocol -> 5.2. Record Payload Protection

```plaintext
Derived: TLSInnerPlaintext structure
struct {
  opaque content[TLSPlaintext.length];
  ContentType type;
  uint8 zeros[length_of_padding];
} TLSInnerPlaintext;
```

```plaintext
Derived: TLSCiphertext structure
struct {
  ContentType opaque_type = application_data; /* 23 */
  ProtocolVersion legacy_record_version = 0x0303; /* TLS v1.2 */
  uint16 length;
  opaque encrypted_record[TLSCiphertext.length];
} TLSCiphertext;
```

## 5. Record Protocol -> 5.5. Limits on Key Usage

```plaintext
Derived: Key Usage Limits for AES-GCM and ChaCha20/Poly1305
There are cryptographic limits on the amount of plaintext which can be safely encrypted under a given set of keys. [AEAD-LIMITS] provides an analysis of these limits under the assumption that the underlying primitive (AES or ChaCha20) has no weaknesses. Implementations SHOULD do a key update as described in Section 4.6.3 prior to reaching these limits. For AES-GCM, up to 2^24.5 full-size records (about 24 million) may be encrypted on a given connection while keeping a safety margin of approximately 2^-57 for Authenticated Encryption (AE) security. For ChaCha20/Poly1305, the record sequence number would wrap before the safety limit is reached.
```

## 6. Alert Protocol

```plaintext
Derived: AlertLevel values
enum { warning(1), fatal(2), (255) } AlertLevel;
```

```plaintext
Derived: AlertDescription values
enum { close_notify(0), unexpected_message(10), bad_record_mac(20), record_overflow(22), handshake_failure(40), bad_certificate(42), unsupported_certificate(43), certificate_revoked(44), certificate_expired(45), certificate_unknown(46), illegal_parameter(47), unknown_ca(48), access_denied(49), decode_error(50), decrypt_error(51), protocol_version(70), insufficient_security(71), internal_error(80), inappropriate_fallback(86), user_canceled(90), missing_extension(109), unsupported_extension(110), unrecognized_name(112), bad_certificate_status_response(113), unknown_psk_identity(115), certificate_required(116), no_application_protocol(120), (255) } AlertDescription;
```

## 7. Cryptographic Computations -> 7.2. Updating Traffic Secrets

```plaintext
Derived: Traffic secret update formula
application_traffic_secret_N+1 = HKDF-Expand-Label(application_traffic_secret_N, "traffic upd", "", Hash.length)
```

## 7. Cryptographic Computations

```plaintext
Nothing to output.
```

## 5. Record Protocol -> 5.1. Record Layer

```plaintext
Derived: ContentType enum definition
enum { invalid(0), change_cipher_spec(20), alert(21), handshake(22), application_data(23), (255) } ContentType;
```

```plaintext
Derived: TLSPlaintext struct definition
struct {
    ContentType type;
    ProtocolVersion legacy_record_version;
    uint16 length;
    opaque fragment[TLSPlaintext.length];
} TLSPlaintext;
```

## 7. Cryptographic Computations -> 7.3. Traffic Key Calculation

```plaintext
Derived: Record Types and Their Secrets
+-------------------+---------------------------------------+
| Record Type       | Secret                                |
+-------------------+---------------------------------------+
| 0-RTT Application | client_early_traffic_secret           |
|                   |                                       |
| Handshake         | [sender]_handshake_traffic_secret     |
|                   |                                       |
| Application Data  | [sender]_application_traffic_secret_N |
+-------------------+---------------------------------------+
```

## 7. Cryptographic Computations -> 7.1. Key Schedule

```plaintext
Derived: Key derivation schedule diagram
0
|
v
PSK -> HKDF-Extract = Early Secret
|
+-----> Derive-Secret(., "ext binder" | "res binder", "")
|        = binder_key
|
+-----> Derive-Secret(., "c e traffic", ClientHello)
|        = client_early_traffic_secret
|
+-----> Derive-Secret(., "e exp master", ClientHello)
|        = early_exporter_master_secret
v
Derive-Secret(., "derived", "")
|
v
(EC)DHE -> HKDF-Extract = Handshake Secret
|
+-----> Derive-Secret(., "c hs traffic",
|        ClientHello...ServerHello)
|        = client_handshake_traffic_secret
|
+-----> Derive-Secret(., "s hs traffic",
|        ClientHello...ServerHello)
|        = server_handshake_traffic_secret
v
Derive-Secret(., "derived", "")
|
v
0 -> HKDF-Extract = Master Secret
|
+-----> Derive-Secret(., "c ap traffic",
|        ClientHello...server Finished)
|        = client_application_traffic_secret_0
|
+-----> Derive-Secret(., "s ap traffic",
|        ClientHello...server Finished)
|        = server_application_traffic_secret_0
|
+-----> Derive-Secret(., "exp master",
|        ClientHello...server Finished)
|        = exporter_master_secret
|
+-----> Derive-Secret(., "res master", ClientHello...client Finished)
         = resumption_master_secret
```

## 8. 0-RTT and Anti-Replay -> 8.3. Freshness Checks

```plaintext
Derived: Adjusted creation time and expected arrival time formulas
adjusted_creation_time = creation_time + estimated_RTT
expected_arrival_time = adjusted_creation_time + clients_ticket_age
```

## 11. IANA Considerations

```plaintext
```
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.11. Pre-Shared Key Extension

```plaintext
Derived: PskIdentity structure
struct {
    opaque identity<1..2^16-1>;
    uint32 obfuscated_ticket_age;
} PskIdentity;
```

```plaintext
Derived: PskBinderEntry definition
opaque PskBinderEntry<32..255>;
```

```plaintext
Derived: OfferedPsks structure
struct {
    PskIdentity identities<7..2^16-1>;
    PskBinderEntry binders<33..2^16-1>;
} OfferedPsks;
```

```plaintext
Derived: PreSharedKeyExtension structure
struct {
    select (Handshake.msg_type) {
        case client_hello: OfferedPsks;
        case server_hello: uint16 selected_identity;
    };
} PreSharedKeyExtension;
```

## 8. 0-RTT and Anti-Replay -> 8.2. Client Hello Recording

```plaintext
Derived: ClientHello Recording Flow
An alternative form of anti-replay is to record a unique value derived from the ClientHello (generally either the random value or the PSK binder) and reject duplicates. Recording all ClientHellos causes state to grow without bound, but a server can instead record ClientHellos within a given time window and use the "obfuscated_ticket_age" to ensure that tickets aren't reused outside that window. In order to implement this, when a ClientHello is received, the server first verifies the PSK binder as described inSection 4.2.11. It then computes the expected_arrival_time as described in the next section and rejects 0-RTT if it is outside the recording window, falling back to the 1-RTT handshake. If the expected_arrival_time is in the window, then the server checks to see if it has recorded a matching ClientHello. If one is found, it either aborts the handshake with an "illegal_parameter" alert or accepts the PSK but rejects 0-RTT. If no matching ClientHello is found, then it accepts 0-RTT and then stores the ClientHello for as long as the expected_arrival_time is inside the window. Servers MAY also implement data stores with false positives, such as Bloom filters, in which case they MUST respond to apparent replay by rejecting 0-RTT but MUST NOT abort the handshake. The server MUST derive the storage key only from validated sections of the ClientHello. If the ClientHello contains multiple PSK identities, then an attacker can create multiple ClientHellos with different binder values for the less-preferred identity on the assumption that the server will not verify it (as recommended by Section 4.2.11). I.e., if the client sends PSKs A and B but the server prefers A, then the attacker can change the binder for B without affecting the binder for A. If the binder for B is part of the storage key, then this ClientHello will not appear as a duplicate, which will cause the ClientHello to be accepted, and may cause side effects such as replay cache pollution, although any 0-RTT data will not be decryptable because it will use different keys. If the validated binder or the ClientHello.random is used as the storage key, then this attack is not possible. Because this mechanism does not require storing all outstanding tickets, it may be easier to implement in distributed systems with high rates of resumption and 0-RTT, at the cost of potentially weaker anti-replay defense because of the difficulty of reliably storing and retrieving the received ClientHello messages. In many such systems, it is impractical to have globally consistent storage of all the received ClientHellos. In this case, the best anti-replay protection is provided by having a single storage zone be authoritative for a given ticket and refusing 0-RTT for that ticket in any other zone. This approach prevents simple replay by the attacker because only one zone will accept 0-RTT data. A weaker design is to implement separate storage for each zone but allow 0-RTT in any zone. This approach limits the number of replays to once per zone. Application message duplication of course remains possible with either design. When implementations are freshly started, they SHOULD reject 0-RTT as long as any portion of their recording window overlaps the startup time. Otherwise, they run the risk of accepting replays which were originally sent during that period. Note: If the client's clock is running much faster than the server's, then a ClientHello may be received that is outside the window in the future, in which case it might be accepted for 1-RTT, causing a client retry, and then acceptable later for 0-RTT. This is another variant of the second form of attack described in Section 8.
```

## 4. Handshake Protocol -> 4.6. Post-Handshake Messages -> 4.6.3. Key and Initialization Vector Update

```plaintext
Derived: KeyUpdate message format
enum { update_not_requested(0), update_requested(1), (255) } KeyUpdateRequest;
struct {
    KeyUpdateRequest request_update;
} KeyUpdate;
```

## 4. Handshake Protocol -> 4.2. Extensions -> 4.2.7. Supported Groups

```plaintext
Derived: NamedGroup enum definition
enum { /* Elliptic Curve Groups (ECDHE) */ secp256r1(0x0017), secp384r1(0x0018), secp521r1(0x0019), x25519(0x001D), x448(0x001E), /* Finite Field Groups (DHE) */ ffdhe2048(0x0100), ffdhe3072(0x0101), ffdhe4096(0x0102), ffdhe6144(0x0103), ffdhe8192(0x0104), /* Reserved Code Points */ ffdhe_private_use(0x01FC..0x01FF), ecdhe_private_use(0xFE00..0xFEFF), (0xFFFF) } NamedGroup;
```

```plaintext
Derived: NamedGroupList struct definition
struct { NamedGroup named_group_list<2..2^16-1>; } NamedGroupList;
```

## 4. Handshake Protocol -> 4.4. Authentication Messages

```plaintext
Derived: Handshake Context and MAC Base Key for each scenario
+-----------+-------------------------+-----------------------------+
| Mode      | Handshake Context       | Base Key                    |
+-----------+-------------------------+-----------------------------+
| Server    | ClientHello ... later   | server_handshake_traffic_   |
|           | of EncryptedExtensions/ | secret                      |
|           | CertificateRequest      |                             |
|           |                         |                             |
| Client    | ClientHello ... later   | client_handshake_traffic_   |
|           | of server               | secret                      |
|           | Finished/EndOfEarlyData |                             |
|           |                         |                             |
| Post-     | ClientHello ... client  | client_application_traffic_ |
| Handshake | Finished +              | secret_N                    |
|           | CertificateRequest      |                             |
+-----------+-------------------------+-----------------------------+
```

## 4. Handshake Protocol -> 4.4. Authentication Messages -> 4.4.3. Certificate Verify

```plaintext
Derived: CertificateVerify structure
struct {
  SignatureScheme algorithm;
  opaque signature<0..2^16-1>;
} CertificateVerify;
```

```plaintext
Derived: Example content covered by digital signature
2020202020202020202020202020202020202020202020202020202020202020
2020202020202020202020202020202020202020202020202020202020202020
544c5320312e332c207365727665722043657274696669636174655665726966
79 00 0101010101010101010101010101010101010101010101010101010101010101
```

## 6. Alert Protocol -> 6.2. Error Alerts

```plaintext
Derived: TLS Error Alerts
unexpected_message: An inappropriate message (e.g., the wrong handshake message, premature Application Data, etc.) was received. This alert should never be observed in communication between proper implementations. bad_record_mac: This alert is returned if a record is received which cannot be deprotected. Because AEAD algorithms combine decryption and verification, and also to avoid side-channel attacks, this alert is used for all deprotection failures. This alert should never be observed in communication between proper implementations, except when messages were corrupted in the network. record_overflow: A TLSCiphertext record was received that had a length more than 2^14 + 256 bytes, or a record decrypted to a TLSPlaintext record with more than 2^14 bytes (or some other negotiated limit). This alert should never be observed in communication between proper implementations, except when messages were corrupted in the network. handshake_failure: Receipt of a "handshake_failure" alert message indicates that the sender was unable to negotiate an acceptable set of security parameters given the options available. bad_certificate: A certificate was corrupt, contained signatures that did not verify correctly, etc. unsupported_certificate: A certificate was of an unsupported type. certificate_revoked: A certificate was revoked by its signer. certificate_expired: A certificate has expired or is not currently valid. certificate_unknown: Some other (unspecified) issue arose in processing the certificate, rendering it unacceptable. illegal_parameter: A field in the handshake was incorrect or inconsistent with other fields. This alert is used for errors which conform to the formal protocol syntax but are otherwise incorrect. unknown_ca: A valid certificate chain or partial chain was received, but the certificate was not accepted because the CA certificate could not be located or could not be matched with a known trust anchor. access_denied: A valid certificate or PSK was received, but when access control was applied, the sender decided not to proceed with negotiation. decode_error: A message could not be decoded because some field was out of the specified range or the length of the message was incorrect. This alert is used for errors where the message does not conform to the formal protocol syntax. This alert should never be observed in communication between proper implementations, except when messages were corrupted in the network. decrypt_error: A handshake (not record layer) cryptographic operation failed, including being unable to correctly verify a signature or validate a Finished message or a PSK binder. protocol_version: The protocol version the peer has attempted to negotiate is recognized but not supported (see Appendix D). insufficient_security: Returned instead of "handshake_failure" when a negotiation has failed specifically because the server requires parameters more secure than those supported by the client. internal_error: An internal error unrelated to the peer or the correctness of the protocol (such as a memory allocation failure) makes it impossible to continue. inappropriate_fallback: Sent by a server in response to an invalid connection retry attempt from a client (see [RFC7507 for Preventing Protocol Downgrade Attacks"")]). missing_extension: Sent by endpoints that receive a handshake message not containing an extension that is mandatory to send for the offered TLS version or other negotiated parameters. unsupported_extension: Sent by endpoints receiving any handshake message containing an extension known to be prohibited for inclusion in the given handshake message, or including any extensions in a ServerHello or Certificate not first offered in the corresponding ClientHello or CertificateRequest. unrecognized_name: Sent by servers when no server exists identified by the name provided by the client via the "server_name" extension (see [RFC6066 Extensions: Extension Definitions"")]). bad_certificate_status_response: Sent by clients when an invalid or unacceptable OCSP response is provided by the server via the "status_request" extension (see [RFC6066 Extensions: Extension Definitions"")]). unknown_psk_identity: Sent by servers when PSK key establishment is desired but no acceptable PSK identity is provided by the client. Sending this alert is OPTIONAL; servers MAY instead choose to send a "decrypt_error" alert to merely indicate an invalid PSK identity. certificate_required: Sent by servers when a client certificate is desired but none was provided by the client. no_application_protocol: Sent by servers when a client "application_layer_protocol_negotiation" extension advertises only protocols that the server does not support (see [RFC7301 Application-Layer Protocol Negotiation Extension"")]).
```

