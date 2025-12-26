[ ![OASIS logo](./MQTT%20Version%205.0_files/OASISLogo-v2.0.jpg)](https://www.oasis-open.org/)

MQTT Version 5.0

OASIS Standard

07 March 2019

Specification URIs

This version:

<https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.docx> (Authoritative)

<https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html>

<https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.pdf>

Previous version:

<http://docs.oasis-open.org/mqtt/mqtt/v5.0/cos01/mqtt-v5.0-cos01.docx> (Authoritative)

<http://docs.oasis-open.org/mqtt/mqtt/v5.0/cos01/mqtt-v5.0-cos01.html>

<http://docs.oasis-open.org/mqtt/mqtt/v5.0/cos01/mqtt-v5.0-cos01.pdf>

Latest version:

<https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.docx> (Authoritative)

<https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html>

<https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.pdf>

Technical Committee:

[OASIS Message Queuing Telemetry Transport (MQTT) TC](https://www.oasis-open.org/committees/mqtt/)

Chairs:

Richard Coppen ([coppen@uk.ibm.com](mailto:coppen@uk.ibm.com)), [IBM](http://www.ibm.com/)

Editors:

Andrew Banks ([andrew_banks@uk.ibm.com](mailto:andrew_banks@uk.ibm.com)), [IBM](http://www.ibm.com/)

Ed Briggs ([edbriggs@microsoft.com](mailto:edbriggs@microsoft.com)), [Microsoft](http://www.microsoft.com/)

Ken Borgendale ([kwb@us.ibm.com](mailto:kwb@us.ibm.com)), [IBM](http://www.ibm.com/)

Rahul Gupta ([rahul.gupta@us.ibm.com](mailto:rahul.gupta@us.ibm.com)), [IBM](http://www.ibm.com/)

Related work:

This specification replaces or supersedes:

Â Â Â Â Â Â Â Â _MQTT Version 3.1.1_. Edited by Andrew Banks and Rahul Gupta. 29 October 2014. OASIS Standard. <http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html>. Latest version: <http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html>.

This specification is related to:

Â Â Â Â Â Â Â Â _MQTT and the NIST Cybersecurity Framework Version 1.0_. Edited by Geoff Brown and Louis-Philippe Lamoureux. Latest version: [http://docs.oasis-open.org/mqtt/mqtt-nist-cybersecurity/v1.0/mqtt-nist-cybersecurity-v1.0.html](http://docs.oasis-open.org/mqtt/mqtt-nist-cybersecurity/v1.0/mqtt-nist-cybersecurity-v1.0.html).

Abstract:

MQTT is a Client Server publish/subscribe messaging transport protocol. It is light weight, open, simple, and designed to be easy to implement. These characteristics make it ideal for use in many situations, including constrained environments such as for communication in Machine to Machine (M2M) and Internet of Things (IoT) contexts where a small code footprint is required and/or network bandwidth is at a premium.

The protocol runs over TCP/IP, or over other network protocols that provide ordered, lossless, bi-directional connections. Its features include:

Â Â Â Â Â Â Â Â Use of the publish/subscribe message pattern which provides one-to-many message distribution and decoupling of applications.

Â Â Â Â Â Â Â Â A messaging transport that is agnostic to the content of the payload. 

Â Â Â Â Â Â Â Â Three qualities of service for message delivery:

oÂ Â Â "At most once", where messages are delivered according to the best efforts of the operating environment. Message loss can occur. This level could be used, for example, with ambient sensor data where it does not matter if an individual reading is lost as the next one will be published soon after.

oÂ Â Â "At least once", where messages are assured to arrive but duplicates can occur.

oÂ Â Â "Exactly once", where messages are assured to arrive exactly once. This level could be used, for example, with billing systems where duplicate or lost messages could lead to incorrect charges being applied.

Â Â Â Â Â Â Â Â A small transport overhead and protocol exchanges minimized to reduce network traffic.

Â Â Â Â Â Â Â Â A mechanism to notify interested parties when an abnormal disconnection occurs.

Status:

This document was last revised or approved by the membership of OASIS on the above date. The level of approval is also listed above. Check the Latest version location noted above for possible later revisions of this document. Any other numbered Versions and other technical work produced by the Technical Committee (TC) are listed at <https://www.oasis-open.org/committees/tc_home.php?wg_abbrev=mqtt#technical>.

TC members should send comments on this document to the TC s email list. Others should send comments to the TC s public comment list, after subscribing to it by following the instructions at the [Send A Comment](https://www.oasis-open.org/committees/comments/index.php?wg_abbrev=mqtt) button on the TC s web page at <https://www.oasis-open.org/committees/mqtt/>.

This specification is provided under the [Non-Assertion](https://www.oasis-open.org/policies-guidelines/ipr#Non-Assertion-Mode) Mode of the [OASIS IPR Policy](https://www.oasis-open.org/policies-guidelines/ipr), the mode chosen when the Technical Committee was established. For information on whether any patents have been disclosed that may be essential to implementing this specification, and any offers of patent licensing terms, please refer to the Intellectual Property Rights section of the TC s web page (<https://www.oasis-open.org/committees/mqtt/ipr.php>).

Note that any machine-readable content ([Computer Language Definitions](https://www.oasis-open.org/policies-guidelines/tc-process#wpComponentsCompLang)) declared Normative for this Work Product is provided in separate plain text files. In the event of a discrepancy between any such plain text file and display content in the Work Product's prose narrative document(s), the content in the separate plain text file prevails.

Citation format:

When referencing this specification the following citation format should be used:

[mqtt-v5.0]

_MQTT Version 5.0_. Edited by Andrew Banks, Ed Briggs, Ken Borgendale, and Rahul Gupta. 07 March 2019. OASIS Standard. <https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html>. Latest version: <https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html>.

Notices

Copyright OASIS Open 2019. All Rights Reserved.

All capitalized terms in the following text have the meanings assigned to them in the OASIS Intellectual Property Rights Policy (the "OASIS IPR Policy"). The full [Policy](https://www.oasis-open.org/policies-guidelines/ipr) may be found at the OASIS website.

This document and translations of it may be copied and furnished to others, and derivative works that comment on or otherwise explain it or assist in its implementation may be prepared, copied, published, and distributed, in whole or in part, without restriction of any kind, provided that the above copyright notice and this section are included on all such copies and derivative works. However, this document itself may not be modified in any way, including by removing the copyright notice or references to OASIS, except as needed for the purpose of developing any document or deliverable produced by an OASIS Technical Committee (in which case the rules applicable to copyrights, as set forth in the OASIS IPR Policy, must be followed) or as required to translate it into languages other than English.

The limited permissions granted above are perpetual and will not be revoked by OASIS or its successors or assigns.

This document and the information contained herein is provided on an "AS IS" basis and OASIS DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTY THAT THE USE OF THE INFORMATION HEREIN WILL NOT INFRINGE ANY OWNERSHIP RIGHTS OR ANY IMPLIED WARRANTIES OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.

OASIS requests that any OASIS Party or any other party that believes it has patent claims that would necessarily be infringed by implementations of this OASIS Committee Specification or OASIS Standard, to notify OASIS TC Administrator and provide an indication of its willingness to grant patent licenses to such patent claims in a manner consistent with the IPR Mode of the OASIS Technical Committee that produced this specification.

OASIS invites any party to contact the OASIS TC Administrator if it is aware of a claim of ownership of any patent claims that would necessarily be infringed by implementations of this specification by a patent holder that is not willing to provide a license to such patent claims in a manner consistent with the IPR Mode of the OASIS Technical Committee that produced this specification. OASIS may include such claims on its website, but disclaims any obligation to do so.

OASIS takes no position regarding the validity or scope of any intellectual property or other rights that might be claimed to pertain to the implementation or use of the technology described in this document or the extent to which any license under such rights might or might not be available; neither does it represent that it has made any effort to identify any such rights. Information on OASIS' procedures with respect to rights in any document or deliverable produced by an OASIS Technical Committee can be found on the OASIS website. Copies of claims of rights made available for publication and any assurances of licenses to be made available, or the result of an attempt made to obtain a general license or permission for the use of such proprietary rights by implementers or users of this OASIS Committee Specification or OASIS Standard, can be obtained from the OASIS TC Administrator. OASIS makes no representation that any information or list of intellectual property rights will at any time be complete, or that any claims in such list are, in fact, Essential Claims.

The name "OASIS" is a trademark of [OASIS](https://www.oasis-open.org/), the owner and developer of this specification, and should be used only to refer to the organization and its official outputs. OASIS welcomes reference to, and implementation and use of, specifications, while reserving the right to enforce its marks against misleading uses. Please see <https://www.oasis-open.org/policies-guidelines/trademark> for above guidance.

Table of Contents

[1Â Â Â Â Â Â Â Introduction. 11](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901000)

[1.0 Intellectual property rights policy. 11](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901001)

[1.1 Organization of the MQTT specification. 11](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901002)

[1.2 Terminology. 11](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901003)

[1.3 Normative references. 13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901004)

[1.4 Non-normative references. 13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901005)

[1.5 Data representation. 16](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901006)

[1.5.1 Bits. 16](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901007)

[1.5.2 Two Byte Integer 16](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901008)

[1.5.3 Four Byte Integer 16](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901009)

[1.5.4 UTF-8 Encoded String. 16](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901010)

[1.5.5 Variable Byte Integer 18](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901011)

[1.5.6 Binary Data. 19](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901012)

[1.5.7 UTF-8 String Pair 19](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901013)

[1.6 Security. 19](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901014)

[1.7 Editing convention. 20](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901015)

[1.8 Change history. 20](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901016)

[1.8.1 MQTT v3.1.1. 20](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901017)

[1.8.2 MQTT v5.0. 20](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901018)

[2Â Â Â Â Â Â Â MQTT Control Packet format 21](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901019)

[2.1 Structure of an MQTT Control Packet 21](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901020)

[2.1.1 Fixed Header 21](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901021)

[2.1.2 MQTT Control Packet type. 21](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901022)

[2.1.3 Flags. 22](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901023)

[2.1.4 Remaining Length. 23](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901024)

[2.2 Variable Header 23](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901025)

[2.2.1 Packet Identifier 23](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901026)

[2.2.2 Properties. 25](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901027)

[2.2.2.1 Property Length. 25](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901028)

[2.2.2.2 Property. 25](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901029)

[2.3 Payload. 26](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901030)

[2.4 Reason Code. 27](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901031)

[3Â Â Â Â Â Â Â MQTT Control Packets. 30](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901032)

[3.1 CONNECT Connection Request 30](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901033)

[3.1.1 CONNECT Fixed Header 30](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901034)

[3.1.2 CONNECT Variable Header 30](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901035)

[3.1.2.1 Protocol Name. 30](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901036)

[3.1.2.2 Protocol Version. 31](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901037)

[3.1.2.3 Connect Flags. 31](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901038)

[3.1.2.4 Clean Start 32](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901039)

[3.1.2.5 Will Flag. 32](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901040)

[3.1.2.6 Will QoS.. 33](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901041)

[3.1.2.7 Will Retain. 33](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901042)

[3.1.2.8 User Name Flag. 33](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901043)

[3.1.2.9 Password Flag. 33](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901044)

[3.1.2.10 Keep Alive. 34](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901045)

[3.1.2.11 CONNECT Properties. 34](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901046)

[3.1.2.11.1 Property Length. 34](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901047)

[3.1.2.11.2 Session Expiry Interval 35](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901048)

[3.1.2.11.3 Receive Maximum... 36](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901049)

[3.1.2.11.4 Maximum Packet Size. 36](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901050)

[3.1.2.11.5 Topic Alias Maximum... 37](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901051)

[3.1.2.11.6 Request Response Information. 37](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901052)

[3.1.2.11.7 Request Problem Information. 37](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901053)

[3.1.2.11.8 User Property. 38](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901054)

[3.1.2.11.9 Authentication Method. 38](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901055)

[3.1.2.11.10 Authentication Data. 38](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901056)

[3.1.2.12 Variable Header non-normative example. 39](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901057)

[3.1.3 CONNECT Payload. 40](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901058)

[3.1.3.1 Client Identifier (ClientID) 40](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901059)

[3.1.3.2 Will Properties. 40](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901060)

[3.1.3.2.1 Property Length. 40](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901061)

[3.1.3.2.2 Will Delay Interval 41](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901062)

[3.1.3.2.3 Payload Format Indicator 41](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901063)

[3.1.3.2.4 Message Expiry Interval 41](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901064)

[3.1.3.2.5 Content Type. 42](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901065)

[3.1.3.2.6 Response Topic. 42](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901066)

[3.1.3.2.7 Correlation Data. 42](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901067)

[3.1.3.2.8 User Property. 42](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901068)

[3.1.3.3 Will Topic. 42](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901069)

[3.1.3.4 Will Payload. 43](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901070)

[3.1.3.5 User Name. 43](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901071)

[3.1.3.6 Password. 43](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901072)

[3.1.4 CONNECT Actions. 43](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901073)

[3.2 CONNACK Connect acknowledgement 44](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901074)

[3.2.1 CONNACK Fixed Header 45](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901075)

[3.2.2 CONNACK Variable Header 45](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901076)

[3.2.2.1 Connect Acknowledge Flags. 45](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901077)

[3.2.2.1.1 Session Present 45](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901078)

[3.2.2.2 Connect Reason Code. 46](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901079)

[3.2.2.3 CONNACK Properties. 47](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901080)

[3.2.2.3.1 Property Length. 47](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901081)

[3.2.2.3.2 Session Expiry Interval 47](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901082)

[3.2.2.3.3 Receive Maximum... 48](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901083)

[3.2.2.3.4 Maximum QoS.. 48](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901084)

[3.2.2.3.5 Retain Available. 49](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901085)

[3.2.2.3.6 Maximum Packet Size. 49](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901086)

[3.2.2.3.7 Assigned Client Identifier 49](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901087)

[3.2.2.3.8 Topic Alias Maximum... 50](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901088)

[3.2.2.3.9 Reason String. 50](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901089)

[3.2.2.3.10 User Property. 50](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901090)

[3.2.2.3.11 Wildcard Subscription Available. 50](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901091)

[3.2.2.3.12 Subscription Identifiers Available. 51](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901092)

[3.2.2.3.13 Shared Subscription Available. 51](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901093)

[3.2.2.3.14 Server Keep Alive. 51](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901094)

[3.2.2.3.15 Response Information. 52](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901095)

[3.2.2.3.16 Server Reference. 52](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901096)

[3.2.2.3.17 Authentication Method. 52](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901097)

[3.2.2.3.18 Authentication Data. 52](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901098)

[3.2.3 CONNACK Payload. 53](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901099)

[3.3 PUBLISH Publish message. 53](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901100)

[3.3.1 PUBLISH Fixed Header 53](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901101)

[3.3.1.1 DUP.. 53](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901102)

[3.3.1.2 QoS.. 54](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901103)

[3.3.1.3 RETAIN.. 54](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901104)

[3.3.1.4 Remaining Length. 55](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901105)

[3.3.2 PUBLISH Variable Header 55](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901106)

[3.3.2.1 Topic Name. 55](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901107)

[3.3.2.2 Packet Identifier 56](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901108)

[3.3.2.3 PUBLISH Properties. 56](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901109)

[3.3.2.3.1 Property Length. 56](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901110)

[3.3.2.3.2 Payload Format Indicator 56](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901111)

[3.3.2.3.3 Message Expiry Interval` 56](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901112)

[3.3.2.3.4 Topic Alias. 57](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901113)

[3.3.2.3.5 Response Topic. 58](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901114)

[3.3.2.3.6 Correlation Data. 58](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901115)

[3.3.2.3.7 User Property. 58](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901116)

[3.3.2.3.8 Subscription Identifier 59](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901117)

[3.3.2.3.9 Content Type. 59](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901118)

[3.3.3 PUBLISH Payload. 60](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901119)

[3.3.4 PUBLISH Actions. 60](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901120)

[3.4 PUBACK Publish acknowledgement 62](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901121)

[3.4.1 PUBACK Fixed Header 63](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901122)

[3.4.2 PUBACK Variable Header 63](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901123)

[3.4.2.1 PUBACK Reason Code. 63](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901124)

[3.4.2.2 PUBACK Properties. 64](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901125)

[3.4.2.2.1 Property Length. 64](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901126)

[3.4.2.2.2 Reason String. 64](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901127)

[3.4.2.2.3 User Property. 64](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901128)

[3.4.3 PUBACK Payload. 65](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901129)

[3.4.4 PUBACK Actions. 65](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901130)

[3.5 PUBREC Publish received (QoS 2 delivery part 1) 65](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901131)

[3.5.1 PUBREC Fixed Header 65](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901132)

[3.5.2 PUBREC Variable Header 65](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901133)

[3.5.2.1 PUBREC Reason Code. 65](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901134)

[3.5.2.2 PUBREC Properties. 66](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901135)

[3.5.2.2.1 Property Length. 66](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901136)

[3.5.2.2.2 Reason String. 66](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901137)

[3.5.2.2.3 User Property. 67](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901138)

[3.5.3 PUBREC Payload. 67](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901139)

[3.5.4 PUBREC Actions. 67](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901140)

[3.6 PUBREL Publish release (QoS 2 delivery part 2) 67](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901141)

[3.6.1 PUBREL Fixed Header 67](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901142)

[3.6.2 PUBREL Variable Header 67](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901143)

[3.6.2.1 PUBREL Reason Code. 68](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901144)

[3.6.2.2 PUBREL Properties. 68](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901145)

[3.6.2.2.1 Property Length. 68](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901146)

[3.6.2.2.2 Reason String. 68](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901147)

[3.6.2.2.3 User Property. 69](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901148)

[3.6.3 PUBREL Payload. 69](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901149)

[3.6.4 PUBREL Actions. 69](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901150)

[3.7 PUBCOMP Publish complete (QoS 2 delivery part 3) 69](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901151)

[3.7.1 PUBCOMP Fixed Header 69](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901152)

[3.7.2 PUBCOMP Variable Header 69](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901153)

[3.7.2.1 PUBCOMP Reason Code. 70](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901154)

[3.7.2.2 PUBCOMP Properties. 70](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901155)

[3.7.2.2.1 Property Length. 70](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901156)

[3.7.2.2.2 Reason String. 70](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901157)

[3.7.2.2.3 User Property. 70](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901158)

[3.7.3 PUBCOMP Payload. 71](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901159)

[3.7.4 PUBCOMP Actions. 71](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901160)

[3.8 SUBSCRIBE \- Subscribe request 71](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901161)

[3.8.1 SUBSCRIBE Fixed Header 71](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901162)

[3.8.2 SUBSCRIBE Variable Header 71](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901163)

[3.8.2.1 SUBSCRIBE Properties. 72](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901164)

[3.8.2.1.1 Property Length. 72](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901165)

[3.8.2.1.2 Subscription Identifier 72](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901166)

[3.8.2.1.3 User Property. 72](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901167)

[3.8.3 SUBSCRIBE Payload. 72](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901168)

[3.8.3.1 Subscription Options. 73](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901169)

[3.8.4 SUBSCRIBE Actions. 75](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901170)

[3.9 SUBACK Subscribe acknowledgement 77](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901171)

[3.9.1 SUBACK Fixed Header 77](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901172)

[3.9.2 SUBACK Variable Header 77](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901173)

[3.9.2.1 SUBACK Properties. 77](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901174)

[3.9.2.1.1 Property Length. 77](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901175)

[3.9.2.1.2 Reason String. 78](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901176)

[3.9.2.1.3 User Property. 78](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901177)

[3.9.3 SUBACK Payload. 78](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901178)

[3.10 UNSUBSCRIBE Unsubscribe request 79](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901179)

[3.10.1 UNSUBSCRIBE Fixed Header 79](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901180)

[3.10.2 UNSUBSCRIBE Variable Header 80](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901181)

[3.10.2.1 UNSUBSCRIBE Properties. 80](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901182)

[3.10.2.1.1 Property Length. 80](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901183)

[3.10.2.1.2 User Property. 80](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901184)

[3.10.3 UNSUBSCRIBE Payload. 80](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901185)

[3.10.4 UNSUBSCRIBE Actions. 81](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901186)

[3.11 UNSUBACK Unsubscribe acknowledgement 81](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901187)

[3.11.1 UNSUBACK Fixed Header 82](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901188)

[3.11.2 UNSUBACK Variable Header 82](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901189)

[3.11.2.1 UNSUBACK Properties. 82](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901190)

[3.11.2.1.1 Property Length. 82](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901191)

[3.11.2.1.2 Reason String. 82](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901192)

[3.11.2.1.3 User Property. 83](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901193)

[3.11.3 UNSUBACK Payload. 83](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901194)

[3.12 PINGREQ PING request 83](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901195)

[3.12.1 PINGREQ Fixed Header 84](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901196)

[3.12.2 PINGREQ Variable Header 84](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901197)

[3.12.3 PINGREQ Payload. 84](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901198)

[3.12.4 PINGREQ Actions. 84](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901199)

[3.13 PINGRESP PING response. 84](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901200)

[3.13.1 PINGRESP Fixed Header 84](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901201)

[3.13.2 PINGRESP Variable Header 85](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901202)

[3.13.3 PINGRESP Payload. 85](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901203)

[3.13.4 PINGRESP Actions. 85](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901204)

[3.14 DISCONNECT Disconnect notification. 85](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901205)

[3.14.1 DISCONNECT Fixed Header 85](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901206)

[3.14.2 DISCONNECT Variable Header 85](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901207)

[3.14.2.1 Disconnect Reason Code. 86](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901208)

[3.14.2.2 DISCONNECT Properties. 88](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901209)

[3.14.2.2.1 Property Length. 88](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901210)

[3.14.2.2.2 Session Expiry Interval 88](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901211)

[3.14.2.2.3 Reason String. 88](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901212)

[3.14.2.2.4 User Property. 88](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901213)

[3.14.2.2.5 Server Reference. 88](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901214)

[3.14.3 DISCONNECT Payload. 89](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901215)

[3.14.4 DISCONNECT Actions. 89](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901216)

[3.15 AUTH Authentication exchange. 89](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901217)

[3.15.1 AUTH Fixed Header 90](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901218)

[3.15.2 AUTH Variable Header 90](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901219)

[3.15.2.1 Authenticate Reason Code. 90](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901220)

[3.15.2.2 AUTH Properties. 90](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901221)

[3.15.2.2.1 Property Length. 90](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901222)

[3.15.2.2.2 Authentication Method. 91](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901223)

[3.15.2.2.3 Authentication Data. 91](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901224)

[3.15.2.2.4 Reason String. 91](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901225)

[3.15.2.2.5 User Property. 91](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901226)

[3.15.3 AUTH Payload. 91](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901227)

[3.15.4 AUTH Actions. 91](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901228)

[4Â Â Â Â Â Â Â Operational behavior 92](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901229)

[4.1 Session State. 92](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901230)

[4.1.1 Storing Session State. 92](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901231)

[4.1.2 Session State non-normative examples. 93](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901232)

[4.2 Network Connections. 93](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901233)

[4.3 Quality of Service levels and protocol flows. 93](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901234)

[4.3.1 QoS 0: At most once delivery. 94](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901235)

[4.3.2 QoS 1: At least once delivery. 94](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901236)

[4.3.3 QoS 2: Exactly once delivery. 95](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901237)

[4.4 Message delivery retry. 96](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901238)

[4.5 Message receipt 97](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901239)

[4.6 Message ordering. 97](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901240)

[4.7 Topic Names and Topic Filters. 98](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901241)

[4.7.1 Topic wildcards. 98](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901242)

[4.7.1.1 Topic level separator 98](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901243)

[4.7.1.2 Multi-level wildcard. 98](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901244)

[4.7.1.3 Single-level wildcard. 99](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901245)

[4.7.2 Topics beginning with $. 99](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901246)

[4.7.3 Topic semantic and usage. 100](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901247)

[4.8 Subscriptions. 101](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901248)

[4.8.1 Nonâshared Subscriptions. 101](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901249)

[4.8.2 Shared Subscriptions. 101](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901250)

[4.9 Flow Control 103](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901251)

[4.10 Request / Response. 104](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901252)

[4.10.1 Basic Request Response (non-normative) 104](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901253)

[4.10.2 Determining a Response Topic value (non-normative) 105](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901254)

[4.11 Server redirection. 106](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901255)

[4.12 Enhanced authentication. 106](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901256)

[4.12.1 Re-authentication. 108](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901257)

[4.13 Handling errors. 109](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901258)

[4.13.1 Malformed Packet and Protocol Errors. 109](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901259)

[4.13.2 Other errors. 110](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901260)

[5Â Â Â Â Â Â Â Security (non-normative) 111](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901261)

[5.1 Introduction. 111](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901262)

[5.2 MQTT solutions: security and certification. 111](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901263)

[5.3 Lightweight crytography and constrained devices. 112](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901264)

[5.4 Implementation notes. 112](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901265)

[5.4.1 Authentication of Clients by the Server 112](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901266)

[5.4.2 Authorization of Clients by the Server 112](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901267)

[5.4.3 Authentication of the Server by the Client 113](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901268)

[5.4.4 Integrity of Application Messages and MQTT Control Packets. 113](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901269)

[5.4.5 Privacy of Application Messages and MQTT Control Packets. 113](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901270)

[5.4.6 Non-repudiation of message transmission. 114](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901271)

[5.4.7 Detecting compromise of Clients and Servers. 114](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901272)

[5.4.8 Detecting abnormal behaviors. 114](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901273)

[5.4.9 Handling of Disallowed Unicode code points. 115](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901274)

[5.4.9.1 Considerations for the use of Disallowed Unicode code points. 115](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901275)

[5.4.9.2 Interactions between Publishers and Subscribers. 115](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901276)

[5.4.9.3 Remedies. 116](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901277)

[5.4.10 Other security considerations. 116](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901278)

[5.4.11 Use of SOCKS. 116](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901279)

[5.4.12 Security profiles. 117](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901280)

[5.4.12.1 Clear communication profile. 117](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901281)

[5.4.12.2 Secured network communication profile. 117](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901282)

[5.4.12.3 Secured transport profile. 117](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901283)

[5.4.12.4 Industry specific security profiles. 117](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901284)

[6Â Â Â Â Â Â Â Using WebSocket as a network transport 118](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901285)

[6.1 IANA considerations. 118](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901286)

[7Â Â Â Â Â Â Â Conformance. 119](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901287)

[7.1 Conformance clauses. 119](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901288)

[7.1.1 MQTT Server conformance clause. 119](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901289)

[7.1.2 MQTT Client conformance clause. 119](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901290)

[Appendix A. Acknowledgments. 120](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901291)

[Appendix B. Mandatory normative statement (non-normative) 121](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901292)

[Appendix C. Summary of new features in MQTT v5.0 (non-normative) 136](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901293)

Â 

Â 

#  1Â Â Â Â Â Introduction

##  1.0 Intellectual property rights policy

This specification is provided under the [Non-Assertion](https://www.oasis-open.org/policies-guidelines/ipr#Non-Assertion-Mode) Mode of the [OASIS IPR Policy](https://www.oasis-open.org/policies-guidelines/ipr), the mode chosen when the Technical Committee was established. For information on whether any patents have been disclosed that may be essential to implementing this specification, and any offers of patent licensing terms, please refer to the Intellectual Property Rights section of the TC s web page (<https://www.oasis-open.org/committees/mqtt/ipr.php>).

##  1.1 Organization of the MQTT specification

The specification is split into seven chapters:

Â Â Â Â Â Â Â Â [Chapter 1 - Introduction](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Introduction)

Â Â Â Â Â Â Â Â [Chapter 2 - MQTT Control Packet format](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_MQTT_Control_Packet)

Â Â Â Â Â Â Â Â [Chapter 3 - MQTT Control Packets](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_MQTT_Control_Packets)

Â Â Â Â Â Â Â Â [Chapter 4 - Operational behavior](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Operational_behavior)

Â Â Â Â Â Â Â Â [Chapter 5 - Security](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Security)

Â Â Â Â Â Â Â Â [Chapter 6 - Using WebSocket as a network transport](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Using_WebSocket_as)

Â Â Â Â Â Â Â Â [Chapter 7 - Conformance Targets](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Conformance)

Â 

##  1.2 Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this specification are to be interpreted as described in IETF RFC 2119 [[RFC2119]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC2119), except where they appear in text that is marked as non-normative.

Â 

Network Connection:

A construct provided by the underlying transport protocol that is being used by MQTT. 

Â Â Â Â Â Â Â Â It connects the Client to the Server.

Â Â Â Â Â Â Â Â It provides the means to send an ordered, lossless, stream of bytes in both directions.

Refer to [section 4.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Network_Connections) Network Connection for non-normative examples.

Â 

Application Message:

The data carried by the MQTT protocol across the network for the application. When an Application Message is transported by MQTT it contains payload data, a Quality of Service (QoS), a collection of Properties, and a Topic Name.

Â 

**Client:**

A program or device that uses MQTT. A Client:

Â Â Â Â Â Â Â Â opens the Network Connection to the Server

Â Â Â Â Â Â Â Â publishes Application Messages that other Clients might be interested in.

Â Â Â Â Â Â Â Â subscribes to request Application Messages that it is interested in receiving.

Â Â Â Â Â Â Â Â unsubscribes to remove a request for Application Messages.

Â Â Â Â Â Â Â Â closes the Network Connection to the Server.

Â 

**Server:**

A program or device that acts as an intermediary between Clients which publish Application Messages and Clients which have made Subscriptions. A Server:

Â Â Â Â Â Â Â Â accepts Network Connections from Clients.

Â Â Â Â Â Â Â Â accepts Application Messages published by Clients.

Â Â Â Â Â Â Â Â processes Subscribe and Unsubscribe requests from Clients.

Â Â Â Â Â Â Â Â forwards Application Messages that match Client Subscriptions.

Â Â Â Â Â Â Â Â closes the Network Connection from the Client.

Â 

**Session:**

A stateful interaction between a Client and a Server. Some Sessions last only as long as the Network Connection, others can span multiple consecutive Network Connections between a Client and a Server.

Â 

**Subscription:**

A Subscription comprises a Topic Filter and a maximum QoS. A Subscription is associated with a single Session. A Session can contain more than one Subscription. Each Subscription within a Session has a different Topic Filter.

Â 

**Shared Subscription:**

A Shared Subscription comprises a Topic Filter and a maximum QoS. A Shared Subscription can be associated with more than one Session to allow a wider range of message exchange patterns. An Application Message that matches a Shared Subscription is only sent to the Client associated with one of these Sessions. A Session can subscribe to more than one Shared Subscription and can contain both Shared Subscriptions and Subscriptions which are not shared.

Â 

**Wildcard Subscription:**

A Wildcard Subscription is a Subscription with a Topic Filter containing one or more wildcard characters. This allows the subscription to match more than one Topic Name. Refer to [section 4.7](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Topic_Names_and) for a description of wildcard characters in a Topic Filter.

Â 

**Topic Name:**

The label attached to an Application Message which is matched against the Subscriptions known to the Server.

Â 

**Topic Filter:**

An expression contained in a Subscription to indicate an interest in one or more topics. A Topic Filter can include wildcard characters.

Â 

**MQTT Control Packet:**

A packet of information that is sent across the Network Connection. The MQTT specification defines fifteen different types of MQTT Control Packet, for example the PUBLISH packet is used to convey Application Messages.

Â 

**Malformed Packet:**

A control packet that cannot be parsed according to this specification. Refer to [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Handling_errors) for information about error handling.

Â 

**Protocol Error:**

An error that is detected after the packet has been parsed and found to contain data that is not allowed by the protocol or is inconsistent with the state of the Client or Server. Refer to [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) for information about error handling.

Â 

**Will Message:**

An Application Message which is published by the Server after the Network Connection is closed in cases where the Network Connection is not closed normally. Refer to [section 3.1.2.5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc479576982) for information about Will Messages.

Â 

**Disallowed Unicode code point:**

The set of Unicode Control Codes and Unicode Noncharacters which should not be included in a UTF-8 Encoded String. Refer to [section 1.5.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_UTF-8_Encoded_String) for more information about the Disallowed Unicode code points.

Â 

##  1.3 Normative references

_**[RFC2119]**_

Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, DOI 10.17487/RFC2119, March 1997, 

<http://www.rfc-editor.org/info/rfc2119>

Â 

**[RFC3629]**

Yergeau, F., "UTF-8, a transformation format of ISO 10646", STD 63, RFC 3629, DOI 10.17487/RFC3629, November 2003,

<http://www.rfc-editor.org/info/rfc3629>

Â 

**[****RFC6455]**

Fette, I. and A. Melnikov, "The WebSocket Protocol", RFC 6455, DOI 10.17487/RFC6455, December 2011,

<http://www.rfc-editor.org/info/rfc6455>

Â 

**[Unicode]**

The Unicode Consortium. The Unicode Standard, 

<http://www.unicode.org/versions/latest/>

Â 

##  1.4 Non-normative references

**[RFC0793]**

Postel, J., "Transmission Control Protocol", STD 7, RFC 793, DOI 10.17487/RFC0793, September 1981, <http://www.rfc-editor.org/info/rfc793>

Â 

**[RFC5246]**

Dierks, T. and E. Rescorla, "The Transport Layer Security (TLS) Protocol Version 1.2", RFC 5246, DOI 10.17487/RFC5246, August 2008, 

<http://www.rfc-editor.org/info/rfc5246>

Â 

**[AES]**

Advanced Encryption Standard (AES) (FIPS PUB 197).

<https://csrc.nist.gov/csrc/media/publications/fips/197/final/documents/fips-197.pdf>

Â 

**[CHACHA20]**

ChaCha20 and Poly1305 for IETF Protocols

[https://tools.ietf.org/html/rfc7539](https://tools.ietf.org/html/rfc7539)

Â 

**[FIPS1402]**

Security Requirements for Cryptographic Modules (FIPS PUB 140-2)

<https://csrc.nist.gov/csrc/media/publications/fips/140/2/final/documents/fips1402.pdf>

Â 

**[IEEE 802.1AR]**

IEEE Standard for Local and metropolitan area networks - Secure Device Identity

<http://standards.ieee.org/findstds/standard/802.1AR-2009.html>

Â 

**[ISO29192]**

ISO/IEC 29192-1:2012 Information technology -- Security techniques -- Lightweight cryptography -- Part 1: General

<https://www.iso.org/standard/56425.html>

Â 

**[MQTT NIST]**

MQTT supplemental publication, MQTT and the NIST Framework for Improving Critical Infrastructure Cybersecurity

<http://docs.oasis-open.org/mqtt/mqtt-nist-cybersecurity/v1.0/mqtt-nist-cybersecurity-v1.0.html>

Â 

**[MQTTV311****]**

MQTT V3.1.1 Protocol Specification

<http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html>

**Â**

**[ISO20922]**

MQTT V3.1.1 ISO Standard (ISO/IEC 20922:2016)

<https://www.iso.org/standard/69466.html>

Â 

**[NISTCSF]**

Improving Critical Infrastructure Cybersecurity Executive Order 13636

<https://www.nist.gov/sites/default/files/documents/itl/preliminary-cybersecurity-framework.pdf>

Â 

**[NIST7628]**

NISTIR 7628 Guidelines for Smart Grid Cyber Security Catalogue

<https://www.nist.gov/sites/default/files/documents/smartgrid/nistir-7628_total.pdf>

Â 

**[NSAB]**

NSA Suite B Cryptography

<http://www.nsa.gov/ia/programs/suiteb_cryptography/>

Â 

**[PCIDSS]**

PCI-DSS Payment Card Industry Data Security Standard

<https://www.pcisecuritystandards.org/pci_security/>

Â 

**[RFC1928]**

Leech, M., Ganis, M., Lee, Y., Kuris, R., Koblas, D., and L. Jones, "SOCKS Protocol Version 5", RFC 1928, DOI 10.17487/RFC1928, March 1996, 

<http://www.rfc-editor.org/info/rfc1928>

Â 

**[RFC4511]**

Sermersheim, J., Ed., "Lightweight Directory Access Protocol (LDAP): The Protocol", RFC 4511, DOI 10.17487/RFC4511, June 2006, 

<http://www.rfc-editor.org/info/rfc4511>

Â 

**[RFC5280]**

Cooper, D., Santesson, S., Farrell, S., Boeyen, S., Housley, R., and W. Polk, "Internet X.509 Public Key Infrastructure Certificate and Certificate Revocation List (CRL) Profile", RFC 5280, DOI 10.17487/RFC5280, May 2008, 

<http://www.rfc-editor.org/info/rfc5280>

Â 

**[RFC6066]**

Eastlake 3rd, D., "Transport Layer Security (TLS) Extensions: Extension Definitions", RFC 6066, DOI 10.17487/RFC6066, January 2011,

<http://www.rfc-editor.org/info/rfc6066>

Â 

**[RFC6749]**

Hardt, D., Ed., "The OAuth 2.0 Authorization Framework", RFC 6749, DOI 10.17487/RFC6749, October 2012, 

<http://www.rfc-editor.org/info/rfc6749>

Â 

**[RFC6960]**

Santesson, S., Myers, M., Ankney, R., Malpani, A., Galperin, S., and C. Adams, "X.509 Internet Public Key Infrastructure Online Certificate Status Protocol - OCSP", RFC 6960, DOI 10.17487/RFC6960, June 2013,

<http://www.rfc-editor.org/info/rfc6960>

Â 

**[SARBANES]**

Sarbanes-Oxley Act of 2002.

<http://www.gpo.gov/fdsys/pkg/PLAW-107publ204/html/PLAW-107publ204.htm>

Â 

**[USEUPRIVSH]**

U.S.-EU Privacy Shield Framework

[https://www.privacyshield.gov](https://www.privacyshield.gov/)

Â 

**[RFC3986]**

Berners-Lee, T., Fielding, R., and L. Masinter, "Uniform Resource Identifier (URI): Generic Syntax", STD 66, RFC 3986, DOI 10.17487/RFC3986, January 2005, 

<http://www.rfc-editor.org/info/rfc3986>

Â 

**[RFC1035]**

Mockapetris, P., "Domain names - implementation and specification", STD 13, RFC 1035, DOI 10.17487/RFC1035, November 1987,

<http://www.rfc-editor.org/info/rfc1035>

Â 

**[RFC2782]**

Gulbrandsen, A., Vixie, P., and L. Esibov, "A DNS RR for specifying the location of services (DNS SRV)", RFC 2782, DOI 10.17487/RFC2782, February 2000,

<http://www.rfc-editor.org/info/rfc2782>

Â 

##  1.5 Data representation

###  1.5.1 Bits

Bits in a byte are labelled 7 to 0. Bit number 7 is the most significant bit, the least significant bit is assigned bit number 0.

Â 

###  1.5.2 Two Byte Integer

Two Byte Integer data values are 16-bit unsigned integers in big-endian order: the high order byte precedes the lower order byte. This means that a 16-bit word is presented on the network as Most Significant Byte (MSB), followed by Least Significant Byte (LSB).

Â 

###  1.5.3 Four Byte Integer

Four Byte Integer data values are 32-bit unsigned integers in big-endian order: the high order byte precedes the successively lower order bytes. This means that a 32-bit word is presented on the network as Most Significant Byte (MSB), followed by the next most Significant Byte (MSB), followed by the next most Significant Byte (MSB), followed by Least Significant Byte (LSB). 

Â 

###  1.5.4 UTF-8 Encoded String

Text fields within the MQTT Control Packets described later are encoded as UTF-8 strings. UTF-8 [[RFC3629]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC3629) is an efficient encoding of Unicode [[Unicode]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#Unicode) characters that optimizes the encoding of ASCII characters in support of text-based communications.[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC3629)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#Unicode)

Â 

Each of these strings is prefixed with a Two Byte Integer length field that gives the number of bytes in a UTF-8 encoded string itself, as illustrated in Figure 1.1 Structure of UTF-8 Encoded Strings below. Consequently, the maximum size of a UTF-8 Encoded String is 65,535 bytes.[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Figure_1.1_Structure)

Â 

Unless stated otherwise all UTF-8 encoded strings can have any length in the range 0 to 65,535 bytes.

Â 

Figure 1â1 Structure of UTF-8 Encoded Strings

Â 

The character data in a UTF-8 Encoded String MUST be well-formed UTF-8 as defined by the Unicode specification [[Unicode]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#Unicode) and restated in RFC 3629 [[RFC3629]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC3629). In particular, the character data MUST NOT include encodings of code points between U+D800 and U+DFFF [MQTT-1.5.4-1]. If the Client or Server receives an MQTT Control Packet containing ill-formed UTF-8 it is a Malformed Packet. Refer to [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) for information about handling errors.[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#Unicode)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC3629)

Â 

A UTF-8 Encoded String MUST NOT include an encoding of the null character U+0000. [MQTT-1.5.4-2]. If a receiver (Server or Client) receives an MQTT Control Packet containing U+0000 it is a Malformed Packet. Refer to[ section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) for information about handling errors.

Â 

The data SHOULD NOT include encodings of the Unicode [Unicode] code points listed below. If a receiver (Server or Client) receives an MQTT Control Packet containing any of them it MAY treat it as a Malformed Packet. These are the Disallowed Unicode code points. Refer to [section ](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors)5.4.9 for more information about handling Disallowed Unicode code points.[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#Unicode)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC3629)

Â 

Â Â Â Â Â Â Â Â U+0001..U+001F control characters 

Â Â Â Â Â Â Â Â U+007F..U+009F control characters 

Â Â Â Â Â Â Â Â Code points defined in the Unicode specification [[Unicode]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#Unicode) to be non-characters (for example U+0FFFF) 

Â 

A UTF-8 encoded sequence 0xEF 0xBB 0xBF is always interpreted as U+FEFF ("ZERO WIDTH NO-BREAK SPACE") wherever it appears in a string and MUST NOT be skipped over or stripped off by a packet receiver [MQTT-1.5.4-3].

Â 

**Non-normative example**

For example, the string Aðª which is LATIN CAPITAL Letter A followed by the code point U+2A6D4 (which represents a CJK IDEOGRAPH EXTENSION B character) is encoded as follows: 

Â 

Figure 1â2 UTF-8 Encoded String non-normative example

Â 

###  1.5.5 Variable Byte Integer

The Variable Byte Integer is encoded using an encoding scheme which uses a single byte for values up to 127. Larger values are handled as follows. The least significant seven bits of each byte encode the data, and the most significant bit is used to indicate whether there are bytes following in the representation. Thus, each byte encodes 128 values and a "continuation bit". The maximum number of bytes in the Variable Byte Integer field is four. The encoded value MUST use the minimum number of bytes necessary to represent the value [MQTT-1.5.5-1]. This is shown in Table 1â1 Size of Variable Byte Integer.

Â 

Table 1â1 Size of Variable Byte Integer

Â 

**Non-normative comment**

The algorithm for encoding a non-negative integer (X) into the Variable Byte Integer encoding scheme is as follows:

Â 

do

Â Â encodedByte = X MOD 128

Â Â X = X DIV 128

Â Â // if there are more data to encode, set the top bit of this byte

Â Â if (X > 0)

Â Â Â Â Â encodedByte = encodedByte OR 128

Â Â endif

Â Â 'output' encodedByte

while (X > 0)

Â 

Where MOD is the modulo operator (% in C), DIV is integer division (/ in C), and OR is bit-wise or (| in C).

Â 

**Non-normative comment**

The algorithm for decoding a Variable Byte Integer type is as follows:

Â Â 

multiplier = 1

value = 0

do

Â Â encodedByte = 'next byte from stream' 

Â Â Â value += (encodedByte AND 127) * multiplier

Â Â if (multiplier > 128*128*128)

Â Â Â Â Â throw Error(Malformed Variable Byte Integer)

Â Â multiplier *= 128

while ((encodedByte AND 128) != 0)

Â 

where AND is the bit-wise and operator (& in C).

Â 

When this algorithm terminates, value contains the Variable Byte Integer value.

Â 

###  1.5.6 Binary Data

Binary Data is represented by a Two Byte Integer length which indicates the number of data bytes, followed by that number of bytes. Thus, the length of Binary Data is limited to the range of 0 to 65,535 Bytes. 

Â 

###  1.5.7 UTF-8 String Pair

A UTF-8 String Pair consists of two UTF-8 Encoded Strings. This data type is used to hold name-value pairs. The first string serves as the name, and the second string contains the value.

Â 

Both strings MUST comply with the requirements for UTF-8 Encoded Strings [MQTT-1.5.7-1]. If a receiver (Client or Server) receives a string pair which does not meet these requirements it is a Malformed Packet. Refer to [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) for information about handling errors.

Â 

##  1.6 Security

MQTT Client and Server implementations SHOULD offer Authentication, Authorization and secure communication options, such as those discussed in Chapter 5. Applications concerned with critical infrastructure, personally identifiable information, or other personal or sensitive information are strongly advised to use these security capabilities.

Â 

##  _1.7_ _Editing convention_

Text highlighted in Yellow within this specification identifies conformance statements. Each conformance statement has been assigned a reference in the format [MQTT-x.x.x-y] where x.x.x is the section number and y is a statement counter within the section.

Â 

##  1.8 Change history

###  1.8.1 MQTT v3.1.1

MQTT v3.1.1 was the first OASIS standard version of MQTT **[MQTTV311****]**.

MQTT v3.1.1 is also standardized as ISO/IEC 20922:2016[ **[ISO20922]**.](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#ISO20922)

Â 

###  1.8.2 MQTT v5.0

MQTT v5.0 adds a significant number of new features to MQTT while keeping much of the core in place. The major functional objectives are: 

Â Â Â Â Â Â Â Â Enhancements for scalability and large scale systems

Â Â Â Â Â Â Â Â Improved error reporting

Â Â Â Â Â Â Â Â Formalize common patterns including capability discovery and request response

Â Â Â Â Â Â Â Â Extensibility mechanisms including user properties

Â Â Â Â Â Â Â Â Performance improvements and support for small clients

Â 

Refer to [Appendix C](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#AppendixC) for a summary of changes in MQTT v5.0.

Â 

#  2Â Â Â Â Â MQTT Control Packet format

##  2.1 Structure of an MQTT Control Packet

The MQTT protocol operates by exchanging a series of MQTT Control Packets in a defined way. This section describes the format of these packets. 

Â 

An MQTT Control Packet consists of up to three parts, always in the following order as shown below. [](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Figure_2.1_-)

Â 

Figure 2â1 Structure of an MQTT Control Packet

Â 

###  2.1.1 Fixed Header

Each MQTT Control Packet contains a Fixed Header as shown below.

Â 

Figure 2â2 Fixed Header format

Â 

###  2.1.2 MQTT Control Packet type

**Position:** byte 1, bits 7-4.

Represented as a 4-bit unsigned value, the values are shown below.

Â 

Table 2â1 MQTT Control Packet types

Â 

###  2.1.3 Flags

The remaining bits [3-0] of byte 1 in the Fixed Header contain flags specific to each MQTT Control Packet type as shown below. Where a flag bit is marked as Reserved , it is reserved for future use and MUST be set to the value listed [MQTT-2.1.3-1]. If invalid flags are received it is a Malformed Packet. Refer to [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) for details about handling errors.

Â 

Table 2â2 Flag Bits

Â 

DUP = Duplicate delivery of a PUBLISH packet

QoS = PUBLISH Quality of Service

RETAIN = PUBLISH retained message flag 

Refer to [section 3.3.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_CONNECT_Fixed_Header) for a description of the DUP, QoS, and RETAIN flags in the PUBLISH packet.

Â 

###  2.1.4 Remaining Length

**Position:** starts at byte 2.

Â 

The Remaining Length is a Variable Byte Integer that represents the number of bytes remaining within the current Control Packet, including data in the Variable Header and the Payload. The Remaining Length does not include the bytes used to encode the Remaining Length. The packet size is the total number of bytes in an MQTT Control Packet, this is equal to the length of the Fixed Header plus the Remaining Length. 

Â 

##  2.2 Variable Header

Some types of MQTT Control Packet contain a Variable Header component. It resides between the Fixed Header and the Payload. The content of the Variable Header varies depending on the packet type. The Packet Identifier field of Variable Header is common in several packet types. 

Â 

###  2.2.1 Packet Identifier

The Variable Header component of many of the MQTT Control Packet types includes a Two Byte Integer Packet Identifier field. These MQTT Control Packets are PUBLISH (where QoS > 0), PUBACK, PUBREC, PUBREL, PUBCOMP, SUBSCRIBE, SUBACK, UNSUBSCRIBE, UNSUBACK.

Â 

MQTT Control Packets that require a Packet Identifier are shown below:

Â 

Table 2â3 MQTT Control Packets that contain a Packet Identifier

Â 

A PUBLISH packet MUST NOT contain a Packet Identifier if its QoS value is set to 0 [MQTT-2.2.1-2].

Â 

Each time a Client sends a new SUBSCRIBE, UNSUBSCRIBE,or PUBLISH (where QoS > 0) MQTT Control Packet it MUST assign it a non-zero Packet Identifier that is currently unused [MQTT-2.2.1-3].

Â 

Each time a Server sends a new PUBLISH (with QoS > 0) MQTT Control Packet it MUST assign it a non zero Packet Identifier that is currently unused [MQTT-2.2.1-4]. 

Â 

The Packet Identifier becomes available for reuse after the sender has processed the corresponding acknowledgement packet, defined as follows. In the case of a QoS 1 PUBLISH, this is the corresponding PUBACK; in the case of QoS 2 PUBLISH it is PUBCOMP or a PUBREC with a Reason Code of 128 or greater. For SUBSCRIBE or UNSUBSCRIBE it is the corresponding SUBACK or UNSUBACK. 

Â 

Packet Identifiers used with PUBLISH, SUBSCRIBE and UNSUBSCRIBE packets form a single, unified set of identifiers separately for the Client and the Server in a Session. A Packet Identifier cannot be used by more than one command at any time.

Â 

A PUBACK, PUBREC , PUBREL, or PUBCOMP packet MUST contain the same Packet Identifier as the PUBLISH packet that was originally sent [MQTT-2.2.1-5]. A SUBACK and UNSUBACK MUST contain the Packet Identifier that was used in the corresponding SUBSCRIBE and UNSUBSCRIBE packet respectively [MQTT-2.2.1-6].

Â 

The Client and Server assign Packet Identifiers independently of each other. As a result, Client-Server pairs can participate in concurrent message exchanges using the same Packet Identifiers. 

Â 

**Non-normative comment**

It is possible for a Client to send a PUBLISH packet with Packet Identifier 0x1234 and then receive a different PUBLISH packet with Packet Identifier 0x1234 from its Server before it receives a PUBACK for the PUBLISH packet that it sent.

Â 

Â ClientÂ Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Server

PUBLISH Packet Identifier=0x1234 ââ

Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â ââ PUBLISH Packet Identifier=0x1234

PUBACK Packet Identifier=0x1234 ââ

Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â ââ PUBACK Packet Identifier=0x1234

Â 

Â 

###  2.2.2 Properties

The last field in the Variable Header of the CONNECT, CONNACK, PUBLISH, PUBACK, PUBREC, PUBREL, PUBCOMP, SUBSCRIBE, SUBACK, UNSUBSCRIBE, UNSUBACK, DISCONNECT, and AUTH packet is a set of Properties. In the CONNECT packet there is also an optional set of Properties in the Will Properties field with the Payload.

Â 

The set of Properties is composed of a Property Length followed by the Properties.

Â 

####  2.2.2.1 Property Length

The Property Length is encoded as a Variable Byte Integer. The Property Length does not include the bytes used to encode itself, but includes the length of the Properties. If there are no properties, this MUST be indicated by including a Property Length of zero [MQTT-2.2.2-1].

Â 

####  2.2.2.2 Property

A Property consists of an Identifier which defines its usage and data type, followed by a value. The Identifier is encoded as a Variable Byte Integer. A Control Packet which contains an Identifier which is not valid for its packet type, or contains a value not of the specified data type, is a Malformed Packet. If received, use a CONNACK or DISCONNECT packet with Reason Code 0x81 (Malformed Packet) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) Handling errors. There is no significance in the order of Properties with different Identifiers.

**Â**

Table 2â4 \- Properties

**Â**

**Non-normative comment**

Although the Property Identifier is defined as a Variable Byte Integer, in this version of the specification all of the Property Identifiers are one byte long.

Â 

##  2.3 Payload

Some MQTT Control Packets contain a Payload as the final part of the packet. In the PUBLISH packet this is the Application Message 

Â 

Table 2â5 - MQTT Control Packets that contain a Payload

Â 

##  2.4 Reason Code

A Reason Code is a one byte unsigned value that indicates the result of an operation. Reason Codes less than 0x80 indicate successful completion of an operation. The normal Reason Code for success is 0. Reason Code values of 0x80 or greater indicate failure.

Â 

The CONNACK, PUBACK, PUBREC, PUBREL, PUBCOMP, DISCONNECT and AUTH Control Packets have a single Reason Code as part of the Variable Header. The SUBACK and UNSUBACK packets contain a list of one or more Reason Codes in the Payload.

Â 

The Reason Codes share a common set of values as shown below.

Â 

Table 2â6 - Reason Codes

Â 

**Non-normative comment**

For Reason Code 0x91 (Packet identifier in use), the response to this is either to try to fix the state, or to reset the Session state by connecting using Clean Start set to 1, or to decide if the Client or Server implementations are defective.

Â 

#  3Â Â Â Â Â MQTT Control Packets

Â 

##  3.1 CONNECT Connection Request 

After a Network Connection is established by a Client to a Server, the first packet sent from the Client to the Server MUST be a CONNECT packet [MQTT-3.1.0-1].

Â 

A Client can only send the CONNECT packet once over a Network Connection. The Server MUST process a second CONNECT packet sent from a Client as a Protocol Error and close the Network Connection [MQTT-3.1.0-2]. Refer to [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) for information about handling errors.

Â 

The Payload contains one or more encoded fields. They specify a unique Client identifier for the Client, a Will Topic, Will Payload, User Name and Password. All but the Client identifier can be omitted and their presence is determined based on flags in the Variable Header.

Â 

###  3.1.1 CONNECT Fixed Header

Figure 3â1 \- CONNECT packet Fixed Header

Â 

**Remaining Length field**

This is the length of the Variable Header plus the length of the Payload. It is encoded as a Variable Byte Integer.

Â 

###  3.1.2 CONNECT Variable Header

The Variable Header for the CONNECT Packet contains the following fields in this order: Protocol Name, Protocol Level, Connect Flags, Keep Alive, and Properties. The rules for encoding Properties are described in [section 2.2.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Properties).

Â 

####  3.1.2.1 Protocol Name

Figure 3â2 \- Protocol Name bytes

Â 

The Protocol Name is a UTF-8 Encoded String that represents the protocol name MQTT , capitalized as shown. The string, its offset and length will not be changed by future versions of the MQTT specification.

Â 

A Server which support multiple protocols uses the Protocol Name to determine whether the data is MQTT. The protocol name MUST be the UTF-8 String "MQTT". If the Server does not want to accept the CONNECT, and wishes to reveal that it is an MQTT Server it MAY send a CONNACK packet with Reason Code of 0x84 (Unsupported Protocol Version), and then it MUST close the Network Connection [MQTT-3.1.2-1].

Â 

**Non-normative comment******

Packet inspectors, such as firewalls, could use the Protocol Name to identify MQTT traffic.

Â 

####  3.1.2.2 Protocol Version

Figure 3â3 \- Protocol Version byte

Â 

The one byte unsigned value that represents the revision level of the protocol used by the Client. The value of the Protocol Version field for version 5.0 of the protocol is 5 (0x05). 

Â 

A Server which supports multiple versions of the MQTT protocol uses the Protocol Version to determine which version of MQTT the Client is using. If the Protocol Version is not 5 and the Server does not want to accept the CONNECT packet, the Server MAY send a CONNACK packet with Reason Code 0x84 (Unsupported Protocol Version) and then MUST close the Network Connection [MQTT-3.1.2-2].

Â 

####  3.1.2.3 Connect Flags

The Connect Flags byte contains several parameters specifying the behavior of the MQTT connection. It also indicates the presence or absence of fields in the Payload.

Figure 3â4 \- Connect Flag bits

The Server MUST validate that the reserved flag in the CONNECT packet is set to 0 [MQTT-3.1.2-3]. If the reserved flag is not 0 it is a Malformed Packet. Refer to [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) for information about handling errors.

Â 

####  3.1.2.4 Clean Start

**Position:** bit 1 of the Connect Flags byte.

Â 

This bit specifies whether the Connection starts a new Session or is a continuation of an existing Session. Refer to [section 4.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Session_State) for a definition of the Session State.

Â 

If a CONNECT packet is received with Clean Start is set to 1, the Client and Server MUST discard any existing Session and start a new Session [MQTT-3.1.2-4]. Consequently, the Session Present flag in CONNACK is always set to 0 if Clean Start is set to 1.

Â 

If a CONNECT packet is received with Clean Start set to 0 and there is a Session associated with the Client Identifier, the Server MUST resume communications with the Client based on state from the existing Session [MQTT-3.1.2-5]. If a CONNECT packet is received with Clean Start set to 0 and there is no Session associated with the Client Identifier, the Server MUST create a new Session [MQTT-3.1.2-6].

Â 

####  3.1.2.5 Will Flag

**Position:** bit 2 of the Connect Flags.

Â 

If the Will Flag is set to 1 this indicates that a Will Message MUST be stored on the Server and associated with the Session [MQTT-3.1.2-7]. The Will Message consists of the Will Properties, Will Topic, and Will Payload fields in the CONNECT Payload. The Will Message MUST be published after the Network Connection is subsequently closed and either the Will Delay Interval has elapsed or the Session ends, unless the Will Message has been deleted by the Server on receipt of a DISCONNECT packet with Reason Code 0x00 (Normal disconnection) or a new Network Connection for the ClientID is opened before the Will Delay Interval has elapsed [MQTT-3.1.2-8].

Situations in which the Will Message is published include, but are not limited to:

  * An I/O error or network failure detected by the Server.
  * The Client fails to communicate within the Keep Alive time.
  * The Client closes the Network Connection without first sending a DISCONNECT packet with a Reason Code 0x00 (Normal disconnection).
  * The Server closes the Network Connection without first receiving a DISCONNECT packet with a Reason Code 0x00 (Normal disconnection).



Â 

If the Will Flag is set to 1, the Will Properties, Will Topic, and Will Payload fields MUST be present in the Payload [MQTT-3.1.2-9]. The Will Message MUST be removed from the stored Session State in the Server once it has been published or the Server has received a DISCONNECT packet with a Reason Code of 0x00 (Normal disconnection) from the Client [MQTT-3.1.2-10].

Â 

The Server SHOULD publish Will Messages promptly after the Network Connection is closed and the Will Delay Interval has passed, or when the Session ends, whichever occurs first. In the case of a Server shutdown or failure, the Server MAY defer publication of Will Messages until a subsequent restart. If this happens, there might be a delay between the time the Server experienced failure and when the Will Message is published.

Â 

Refer to [section 3.1.3.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Will_Delay_Interval_1) for information about the Will Delay Interval.

Â 

**Non-normative comment**

The Client can arrange for the Will Message to notify that Session Expiry has occurred by setting the Will Delay Interval to be longer than the Session Expiry Interval and sending DISCONNECT with Reason Code 0x04 (Disconnect with Will Message).

Â 

####  3.1.2.6 Will QoS

**Position:** bits 4 and 3 of the Connect Flags.

Â 

These two bits specify the QoS level to be used when publishing the Will Message. 

Â 

If the Will Flag is set to 0, then the Will QoS MUST be set to 0 (0x00) [MQTT-3.1.2-11].

If the Will Flag is set to 1, the value of Will QoS can be 0 (0x00), 1 (0x01), or 2 (0x02) [MQTT-3.1.2-12]. A value of 3 (0x03) is a Malformed Packet. Refer to [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) for information about handling errors.

Â 

####  3.1.2.7 Will Retain

**Position:** bit 5 of the Connect Flags.

Â 

This bit specifies if the Will Message is to be retained when it is published.

Â 

If the Will Flag is set to 0, then Will Retain MUST be set to 0 [MQTT-3.1.2-13]. If the Will Flag is set to 1 and Will Retain is set to 0, the Server MUST publish the Will Message as a non-retained message [MQTT-3.1.2-14]. If the Will Flag is set to 1 and Will Retain is set to 1, the Server MUST publish the Will Message as a retained message [MQTT-3.1.2-15].

Â 

####  3.1.2.8 User Name Flag

**Position:** bit 7 of the Connect Flags.

Â 

If the User Name Flag is set to 0, a User Name MUST NOT be present in the Payload [MQTT-3.1.2-16]. If the User Name Flag is set to 1, a User Name MUST be present in the Payload [MQTT-3.1.2-17].

Â 

####  3.1.2.9 Password Flag

**Position:** bit 6 of the Connect Flags.

Â 

If the Password Flag is set to 0, a Password MUST NOT be present in the Payload [MQTT-3.1.2-18]. If the Password Flag is set to 1, a Password MUST be present in the Payload [MQTT-3.1.2-19].

**Â**

**Non-normative comment**

This version of the protocol allows the sending of a Password with no User Name, where MQTT v3.1.1 did not. This reflects the common use of Password for credentials other than a password.

Â 

####  3.1.2.10 Keep Alive

Figure 3â5 \- Keep Alive bytes

Â 

The Keep Alive is a Two Byte Integer which is a time interval measured in seconds. It is the maximum time interval that is permitted to elapse between the point at which the Client finishes transmitting one MQTT Control Packet and the point it starts sending the next. It is the responsibility of the Client to ensure that the interval between MQTT Control Packets being sent does not exceed the Keep Alive value. If Keep Alive is non-zero and in the absence of sending any other MQTT Control Packets, the Client MUST send a PINGREQ packet [MQTT-3.1.2-20].

Â 

If the Server returns a Server Keep Alive on the CONNACK packet, the Client MUST use that value instead of the value it sent as the Keep Alive [MQTT-3.1.2-21].

Â 

The Client can send PINGREQ at any time, irrespective of the Keep Alive value, and check for a corresponding PINGRESP to determine that the network and the Server are available. 

Â 

If the Keep Alive value is non-zero and the Server does not receive an MQTT Control Packet from the Client within one and a half times the Keep Alive time period, it MUST close the Network Connection to the Client as if the network had failed [MQTT-3.1.2-22].

Â 

If a Client does not receive a PINGRESP packet within a reasonable amount of time after it has sent a PINGREQ, it SHOULD close the Network Connection to the Server.

Â 

A Keep Alive value of 0 has the effect of turning off the Keep Alive mechanism. If Keep Alive is 0 the Client is not obliged to send MQTT Control Packets on any particular schedule.

Â 

**Non-normative comment**

The Server may have other reasons to disconnect the Client, for instance because it is shutting down. Setting Keep Alive does not guarantee that the Client will remain connected. 

Â 

**Non-normative comment**

The actual value of the Keep Alive is application specific; typically, this is a few minutes. The maximum value of 65,535 is 18 hours 12 minutes and 15 seconds. 

Â 

####  3.1.2.11 CONNECT Properties

#####  3.1.2.11.1 Property Length

The length of the Properties in the CONNECT packet Variable Header encoded as a Variable Byte Integer.

Â 

#####  3.1.2.11.2 Session Expiry Interval

**17 (0x11) Byte,** Identifier of the Session Expiry Interval.

Followed by the Four Byte Integer representing the Session Expiry Interval in seconds. It is a Protocol Error to include the Session Expiry Interval more than once.

Â 

If the Session Expiry Interval is absent the value 0 is used. If it is set to 0, or is absent, the Session ends when the Network Connection is closed. 

Â 

If the Session Expiry Interval is 0xFFFFFFFF (UINT_MAX), the Session does not expire. 

Â 

The Client and Server MUST store the Session State after the Network Connection is closed if the Session Expiry Interval is greater than 0 [MQTT-3.1.2-23].

**Â**

**Non-normative comment**

The clock in the Client or Server may not be running for part of the time interval, for instance because the Client or Server are not running. This might cause the deletion of the state to be delayed. 

Â 

Refer to [section 4.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Session_State) for more information about Sessions. Refer to [section 4.1.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Storing_Session_State) for details and limitations of stored state.

Â 

When the Session expires the Client and Server need not process the deletion of state atomically.

**Â**

**Non-normative comment**

Setting Clean Start to 1 and a Session Expiry Interval of 0, is equivalent to setting CleanSession to 1 in the MQTT Specification Version 3.1.1. Setting Clean Start to 0 and no Session Expiry Interval, is equivalent to setting CleanSession to 0 in the MQTT Specification Version 3.1.1. 

Â 

**Non-normative comment**

A Client that only wants to process messages while connected will set the Clean Start to 1 and set the Session Expiry Interval to 0. It will not receive Application Messages published before it connected and has to subscribe afresh to any topics that it is interested in each time it connects.

Â 

**Non-normative comment**

A Client might be connecting to a Server using a network that provides intermittent connectivity. This Client can use a short Session Expiry Interval so that it can reconnect when the network is available again and continue reliable message delivery. If the Client does not reconnect, allowing the Session to expire, then Application Messages will be lost.

Â 

**Non-normative comment**

When a Client connects with a long Session Expiry Interval, it is requesting that the Server maintain its MQTT session state after it disconnects for an extended period. Clients should only connect with a long Session Expiry Interval if they intend to reconnect to the Server at some later point in time. When a Client has determined that it has no further use for the Session it should disconnect with a Session Expiry Interval set to 0.

Â 

**Non-normative comment**

The Client should always use the Session Present flag in the CONNACK to determine whether the Server has a Session State for this Client. 

Â 

**Non-normative comment**

The Client can avoid implementing its own Session expiry and instead rely on the Session Present flag returned from the Server to determine if the Session had expired. If the Client does implement its own Session expiry, it needs to store the time at which the Session State will be deleted as part of its Session State.

Â 

#####  3.1.2.11.3 Receive Maximum

**33 (0x21) Byte,** Identifier of the Receive Maximum. 

Followed by the Two Byte Integer representing the Receive Maximum value. It is a Protocol Error to include the Receive Maximum value more than once or for it to have the value 0.

Â 

The Client uses this value to limit the number of QoS 1 and QoS 2 publications that it is willing to process concurrently. There is no mechanism to limit the QoS 0 publications that the Server might try to send.

Â 

The value of Receive Maximum applies only to the current Network Connection. If the Receive Maximum value is absent then its value defaults to 65,535.

Â 

Refer to [section 4.9](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Flow_Control) Flow Control for details of how the Receive Maximum is used.

Â 

#####  3.1.2.11.4 Maximum Packet Size

**39 (0x27) Byte** , Identifier of the Maximum Packet Size. 

Followed by a Four Byte Integer representing the Maximum Packet Size the Client is willing to accept. If the Maximum Packet Size is not present, no limit on the packet size is imposed beyond the limitations in the protocol as a result of the remaining length encoding and the protocol header sizes.

Â 

It is a Protocol Error to include the Maximum Packet Size more than once, or for the value to be set to zero.

Â 

Â Â Â Â Â Â Â Â Â Â Â **Non-normative comment**

It is the responsibility of the application to select a suitable Maximum Packet Size value if it chooses to restrict the Maximum Packet Size.

Â 

The packet size is the total number of bytes in an MQTT Control Packet, as defined in [section 2.1.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Remaining_Length). The Client uses the Maximum Packet Size to inform the Server that it will not process packets exceeding this limit.

Â 

The Server MUST NOT send packets exceeding Maximum Packet Size to the Client [MQTT-3.1.2-24]. If a Client receives a packet whose size exceeds this limit, this is a Protocol Error, the Client uses DISCONNECT with Reason Code 0x95 (Packet too large), as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors).

Â 

Where a Packet is too large to send, the Server MUST discard it without sending it and then behave as if it had completed sending that Application Message [MQTT-3.1.2-25]. 

Â 

In the case of a Shared Subscription where the message is too large to send to one or more of the Clients but other Clients can receive it, the Server can choose either discard the message without sending the message to any of the Clients, or to send the message to one of the Clients that can receive it.

Â 

**Non-normative comment**

Where a packet is discarded without being sent, the Server could place the discarded packet on a dead letter queue or perform other diagnostic action. Such actions are outside the scope of this specification.

Â 

#####  3.1.2.11.5 Topic Alias Maximum

**34 (0x22) Byte,** Identifier of the Topic Alias Maximum. 

Followed by the Two Byte Integer representing the Topic Alias Maximum value. It is a Protocol Error to include the Topic Alias Maximum value more than once. If the Topic Alias Maximum property is absent, the default value is 0.

Â 

This value indicates the highest value that the Client will accept as a Topic Alias sent by the Server. The Client uses this value to limit the number of Topic Aliases that it is willing to hold on this Connection. The Server MUST NOT send a Topic Alias in a PUBLISH packet to the Client greater than Topic Alias Maximum [MQTT-3.1.2-26]. A value of 0 indicates that the Client does not accept any Topic Aliases on this connection. If Topic Alias Maximum is absent or zero, the Server MUST NOT send any Topic Aliases to the Client [MQTT-3.1.2-27].

Â 

#####  3.1.2.11.6 Request Response Information

**25 (0x19) Byte,** Identifier of the Request Response Information. 

Followed by a Byte with a value of either 0 or 1. It is Protocol Error to include the Request Response Information more than once, or to have a value other than 0 or 1. If the Request Response Information is absent, the value of 0 is used.

Â 

The Client uses this value to request the Server to return Response Information in the CONNACK. A value of 0 indicates that the Server MUST NOT return Response Information [MQTT-3.1.2-28]. If the value is 1 the Server MAY return Response Information in the CONNACK packet.

Â 

Non-normative comment

The Server can choose not to include Response Information in the CONNACK, even if the Client requested it.

Â 

Refer to [section 4.10](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Request_/_Response) for more information about Request / Response.

Â 

#####  3.1.2.11.7 Request Problem Information

**23 (0x17) Byte,** Identifier of the Request Problem Information. 

Followed by a Byte with a value of either 0 or 1. It is a Protocol Error to include Request Problem Information more than once, or to have a value other than 0 or 1. If the Request Problem Information is absent, the value of 1 is used. 

Â 

The Client uses this value to indicate whether the Reason String or User Properties are sent in the case of failures. 

Â 

If the value of Request Problem Information is 0, the Server MAY return a Reason String or User Properties on a CONNACK or DISCONNECT packet, but MUST NOT send a Reason String or User Properties on any packet other than PUBLISH, CONNACK, or DISCONNECT [MQTT-3.1.2-29]. If the value is 0 and the Client receives a Reason String or User Properties in a packet other than PUBLISH, CONNACK, or DISCONNECT, it uses a DISCONNECT packet with Reason Code 0x82 (Protocol Error) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) Handling errors.

Â 

If this value is 1, the Server MAY return a Reason String or User Properties on any packet where it is allowed.

Â 

#####  3.1.2.11.8 User Property

**38 (0x26) Byte** , Identifier of the User Property. 

Followed by a UTF-8 String Pair. 

Â 

The User Property is allowed to appear multiple times to represent multiple name, value pairs. The same name is allowed to appear more than once.

Â 

**Non-normative comment**

User Properties on the CONNECT packet can be used to send connection related properties from the Client to the Server. The meaning of these properties is not defined by this specification.

Â 

#####  3.1.2.11.9 Authentication Method

**21 (0x15) Byte,** Identifier of the Authentication Method. 

Followed by a UTF-8 Encoded String containing the name of the authentication method used for extended authentication .It is a Protocol Error to include Authentication Method more than once.

If Authentication Method is absent, extended authentication is not performed. Refer to [section 4.12](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Enhanced_authentication).

Â 

If a Client sets an Authentication Method in the CONNECT, the Client MUST NOT send any packets other than AUTH or DISCONNECT packets until it has received a CONNACK packet [MQTT-3.1.2-30].

Â 

#####  3.1.2.11.10 Authentication Data

**22 (0x16) Byte,** Identifier of the Authentication Data. 

Followed by Binary Data containing authentication data. It is a Protocol Error to include Authentication Data if there is no Authentication Method. It is a Protocol Error to include Authentication Data more than once. 

Â 

The contents of this data are defined by the authentication method. Refer to [section 4.12](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Enhanced_authentication) for more information about extended authentication.

Â 

####  3.1.2.12 Variable Header non-normative example

Figure 3â6 \- Variable Header example

**Â**

###  3.1.3 CONNECT Payload

The Payload of the CONNECT packet contains one or more length-prefixed fields, whose presence is determined by the flags in the Variable Header. These fields, if present, MUST appear in the order Client Identifier, Will Properties, Will Topic, Will Payload, User Name, Password [MQTT-3.1.3-1].

Â 

####  3.1.3.1 Client Identifier (ClientID)

The Client Identifier (ClientID) identifies the Client to the Server. Each Client connecting to the Server has a unique ClientID. The ClientID MUST be used by Clients and by Servers to identify state that they hold relating to this MQTT Session between the Client and the Server [MQTT-3.1.3-2]. Refer to [section 4.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Session_State) for more information about Session State.

Â 

The ClientID MUST be present and is the first field in the CONNECT packet Payload [MQTT-3.1.3-3].

Â 

The ClientID MUST be a UTF-8 Encoded String as defined in [section 1.5.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_UTF-8_Encoded_String) [MQTT-3.1.3-4].

Â 

The Server MUST allow ClientID s which are between 1 and 23 UTF-8 encoded bytes in length, and that contain only the characters

"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" [MQTT-3.1.3-5].

Â 

The Server MAY allow ClientID s that contain more than 23 encoded bytes. The Server MAY allow ClientID s that contain characters not included in the list given above. 

Â 

A Server MAY allow a Client to supply a ClientID that has a length of zero bytes, however if it does so the Server MUST treat this as a special case and assign a unique ClientID to that Client [MQTT-3.1.3-6]. It MUST then process the CONNECT packet as if the Client had provided that unique ClientID, and MUST return the Assigned Client Identifier in the CONNACK packet [MQTT-3.1.3-7].

Â 

If the Server rejects the ClientID it MAY respond to the CONNECT packet with a CONNACK using Reason Code 0x85 (Client Identifier not valid) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) Handling errors, and then it MUST close the Network Connection [MQTT-3.1.3-8].

Â 

**Non-normative comment**

A Client implementation could provide a convenience method to generate a random ClientID. Clients using this method should take care to avoid creating long-lived orphaned Sessions.

Â 

####  3.1.3.2 Will Properties

If the Will Flag is set to 1, the Will Properties is the next field in the Payload. The Will Properties field defines the Application Message properties to be sent with the Will Message when it is published, and properties which define when to publish the Will Message. The Will Properties consists of a Property Length and the Properties.

Â 

#####  3.1.3.2.1 Property Length

The length of the Properties in the Will Properties encoded as a Variable Byte Integer.

Â 

#####  3.1.3.2.2 Will Delay Interval

**24 (0x18) Byte,** Identifier of the Will Delay Interval.

Followed by the Four Byte Integer representing the Will Delay Interval in seconds. It is a Protocol Error to include the Will Delay Interval more than once. If the Will Delay Interval is absent, the default value is 0 and there is no delay before the Will Message is published.

Â 

The Server delays publishing the Client s Will Message until the Will Delay Interval has passed or the Session ends, whichever happens first. If a new Network Connection to this Session is made before the Will Delay Interval has passed, the Server MUST NOT send the Will Message [MQTT-3.1.3-9].

Â 

**Non-normative comment**

One use of this is to avoid publishing Will Messages if there is a temporary network disconnection and the Client succeeds in reconnecting and continuing its Session before the Will Message is published.

Â 

**Non-normative comment**

If a Network Connection uses a Client Identifier of an existing Network Connection to the Server, the Will Message for the exiting connection is sent unless the new connection specifies Clean Start of 0 and the Will Delay is greater than zero. If the Will Delay is 0 the Will Message is sent at the close of the existing Network Connection, and if Clean Start is 1 the Will Message is sent because the Session ends.

Â 

#####  3.1.3.2.3 Payload Format Indicator

**1 (0x01) Byte,** Identifier of the Payload Format Indicator. 

Followed by the value of the Payload Format Indicator, either of: 

Â Â Â Â Â Â Â Â 0 (0x00) Byte Indicates that the Will Message is unspecified bytes, which is equivalent to not sending a Payload Format Indicator.

Â Â Â Â Â Â Â Â 1 (0x01) Byte Indicates that the Will Message is UTF-8 Encoded Character Data. The UTF-8 data in the Payload MUST be well-formed UTF-8 as defined by the Unicode specification [[Unicode] ](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#Unicode)and restated in RFC 3629 [[RFC3629]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC3629). 

Â 

It is a Protocol Error to include the Payload Format Indicator more than once. The Server MAY validate that the Will Message is of the format indicated, and if it is not send a CONNACK with the Reason Code of 0x99 (Payload format invalid) as described in section 4.13.

Â 

#####  3.1.3.2.4 Message Expiry Interval

**2 (0x02) Byte,** Identifier of the Message Expiry Interval. 

Followed by the Four Byte Integer representing the Message Expiry Interval. It is a Protocol Error to include the Message Expiry Interval more than once.

Â 

If present, the Four Byte value is the lifetime of the Will Message in seconds and is sent as the Publication Expiry Interval when the Server publishes the Will Message.

Â 

If absent, no Message Expiry Interval is sent when the Server publishes the Will Message. 

Â 

#####  3.1.3.2.5 Content Type

**3 (0x03)** Identifier of the Content Type. 

Followed by a UTF-8 Encoded String describing the content of the Will Message. It is a Protocol Error to include the Content Type more than once. The value of the Content Type is defined by the sending and receiving application. 

Â 

#####  3.1.3.2.6 Response Topic

**8 (0x08) Byte** , Identifier of the Response Topic. 

Followed by a UTF-8 Encoded String which is used as the Topic Name for a response message. It is a Protocol Error to include the Response Topic more than once. The presence of a Response Topic identifies the Will Message as a Request. 

Â 

Refer to [section 4.10](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Request_/_Response) for more information about Request / Response.

**Â**

#####  3.1.3.2.7 Correlation Data

**9 (0x09) Byte,** Identifier of the Correlation Data. 

Followed by Binary Data. The Correlation Data is used by the sender of the Request Message to identify which request the Response Message is for when it is received. It is a Protocol Error to include Correlation Data more than once. If the Correlation Data is not present, the Requester does not require any correlation data.

Â 

The value of the Correlation Data only has meaning to the sender of the Request Message and receiver of the Response Message.

Â 

Refer to [section 4.10](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Request_/_Response) for more information about Request / Response

Â 

#####  3.1.3.2.8 User Property

**38 (0x26) Byte** , Identifier of the User Property.

Followed by a UTF-8 String Pair. The User Property is allowed to appear multiple times to represent multiple name, value pairs. The same name is allowed to appear more than once.

Â 

The Server MUST maintain the order of User Properties when publishing the Will Message [MQTT-3.1.3-10].

Â 

**Non-normative comment**

This property is intended to provide a means of transferring application layer name-value tags whose meaning and interpretation are known only by the application programs responsible for sending and receiving them.

Â 

####  3.1.3.3 Will Topic

If the Will Flag is set to 1, the Will Topic is the next field in the Payload. The Will Topic MUST be a UTF-8 Encoded String as defined in [section 1.5.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_UTF-8_Encoded_String) [MQTT-3.1.3-11].

Â 

####  3.1.3.4 Will Payload

If the Will Flag is set to 1 the Will Payload is the next field in the Payload. The Will Payload defines the Application Message Payload that is to be published to the Will Topic as described in [section 3.1.2.5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc479576982). This field consists of Binary Data.

Â 

####  3.1.3.5 User Name

If the User Name Flag is set to 1, the User Name is the next field in the Payload. The User Name MUST be a UTF-8 Encoded String as defined in [section 1.5.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_UTF-8_Encoded_String) [MQTT-3.1.3-12]. It can be used by the Server for authentication and authorization. 

Â 

####  3.1.3.6 Password

If the Password Flag is set to 1, the Password is the next field in the Payload. The Password field is Binary Data. Although this field is called Password, it can be used to carry any credential information.

Â 

###  3.1.4 CONNECT Actions

Note that a Server MAY support multiple protocols (including other versions of the MQTT protocol) on the same TCP port or other network endpoint. If the Server determines that the protocol is MQTT v5.0 then it validates the connection attempt as follows. 

Â 

1.Â Â Â Â If the Server does not receive a CONNECT packet within a reasonable amount of time after the Network Connection is established, the Server SHOULD close the Network Connection.

2.Â Â Â Â The Server MUST validate that the CONNECT packet matches the format described in [section 3.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_CONNECT_%E2%80%93_Connection) and close the Network Connection if it does not match [MQTT-3.1.4-1]. The Server MAY send a CONNACK with a Reason Code of 0x80 or greater as described in section 4.13 before closing the Network Connection. 

  3. The Server MAY check that the contents of the CONNECT packet meet any further restrictions and SHOULD perform authentication and authorization checks. If any of these checks fail, it MUST close the Network Connection [MQTT-3.1.4-2]. Before closing the Network Connection, it MAY send an appropriate CONNACK response with a Reason Code of 0x80 or greater as described in [section 3.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_CONNACK_%E2%80%93_Connect) and [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors).



Â 

If validation is successful, the Server performs the following steps.

Â 

1.Â Â Â Â If the ClientID represents a Client already connected to the Server, the Server sends a DISCONNECT packet to the existing Client with Reason Code of 0x8E (Session taken over) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) and MUST close the Network Connection of the existing Client [MQTT-3.1.4-3]. If the existing Client has a Will Message, that Will Message is published as described in section 3.1.2.5.

Â 

**Non-normative comment**

If the Will Delay Interval of the existing Network Connection is 0 and there is a Will Message, it will be sent because the Network Connection is closed. If the Session Expiry Interval of the existing Network Connection is 0, or the new Network Connection has Clean Start set to 1 then if the existing Network Connection has a Will Message it will be sent because the original Session is ended on the takeover.

Â 

2.Â Â Â Â The Server MUST perform the processing of Clean Start that is described in [section 3.1.2.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Clean_Start) [MQTT-3.1.4-4].

Â 

3.Â Â Â Â The Server MUST acknowledge the CONNECT packet with a CONNACK packet containing a 0x00 (Success) Reason Code [MQTT-3.1.4-5].

Â 

**Non-normative comment**

It is recommended that authentication and authorization checks be performed if the Server is being used to process any form of business critical data. If these checks succeed, the Server responds by sending CONNACK with a 0x00 (Success) Reason Code. If they fail, it is suggested that the Server does not send a CONNACK at all, as this could alert a potential attacker to the presence of the MQTT Server and encourage such an attacker to launch a denial of service or password-guessing attack.

Â 

4.Â Â Â Â Start message delivery and Keep Alive monitoring.

Â 

Clients are allowed to send further MQTT Control Packets immediately after sending a CONNECT packet; Clients need not wait for a CONNACK packet to arrive from the Server. If the Server rejects the CONNECT, it MUST NOT process any data sent by the Client after the CONNECT packet except AUTH packets [MQTT-3.1.4-6].

Â 

**Non-normative comment**

Clients typically wait for a CONNACK packet, However, if the Client exploits its freedom to send MQTT Control Packets before it receives a CONNACK, it might simplify the Client implementation as it does not have to police the connected state. The Client accepts that any data that it sends before it receives a CONNACK packet from the Server will not be processed if the Server rejects the connection.

Â 

**Non-normative comment**

Clients that send MQTT Control Packets before they receive CONNACK will be unaware of the Server constraints and whether any existing Session is being used. 

Â 

**Non-normative comment**

The Server can limit reading from the Network Connection or close the Network Connection if the Client sends too much data before authentication is complete. This is suggested as a way of avoiding denial of service attacks.

Â 

##  3.2 CONNACK Connect acknowledgement

The CONNACK packet is the packet sent by the Server in response to a CONNECT packet received from a Client. The Server MUST send a CONNACK with a 0x00 (Success) Reason Code before sending any Packet other than AUTH [MQTT-3.2.0-1]. The Server MUST NOT send more than one CONNACK in a Network Connection [MQTT-3.2.0-2].

Â 

If the Client does not receive a CONNACK packet from the Server within a reasonable amount of time, the Client SHOULD close the Network Connection. A "reasonable" amount of time depends on the type of application and the communications infrastructure.

Â 

###  3.2.1 CONNACK Fixed Header

The Fixed Header format is illustrated in Figure 3-7.[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Figure_3.8_%E2%80%93)

Figure 3â7 CONNACK packet Fixed Header

Â 

**Remaining Length field**

This is the length of the Variable Header encoded as a Variable Byte Integer.

Â 

###  3.2.2 CONNACK Variable Header

The Variable Header of the CONNACK Packet contains the following fields in the order: Connect Acknowledge Flags, Connect Reason Code, and Properties. The rules for encoding Properties are described in [section 2.2.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Properties).

Â 

####  3.2.2.1 Connect Acknowledge Flags

Byte 1 is the "Connect Acknowledge Flags". Bits 7-1 are reserved and MUST be set to 0 [MQTT-3.2.2-1].

Â 

Bit 0 is the Session Present Flag.

Â 

#####  3.2.2.1.1 Session Present

Position: bit 0 of the Connect Acknowledge Flags.

Â 

The Session Present flag informs the Client whether the Server is using Session State from a previous connection for this ClientID. This allows the Client and Server to have a consistent view of the Session State.

Â 

If the Server accepts a connection with Clean Start set to 1, the Server MUST set Session Present to 0 in the CONNACK packet in addition to setting a 0x00 (Success) Reason Code in the CONNACK packet [MQTT-3.2.2-2].

Â 

If the Server accepts a connection with Clean Start set to 0 and the Server has Session State for the ClientID, it MUST set Session Present to 1 in the CONNACK packet, otherwise it MUST set Session Present to 0 in the CONNACK packet. In both cases it MUST set a 0x00 (Success) Reason Code in the CONNACK packet [MQTT-3.2.2-3].

Â 

If the value of Session Present received by the Client from the Server is not as expected, the Client proceeds as follows:

Â Â Â Â Â Â Â Â If the Client does not have Session State and receives Session Present set to 1 it MUST close the Network Connection [MQTT-3.2.2-4]. If it wishes to restart with a new Session the Client can reconnect using Clean Start set to 1.

Â Â Â Â Â Â Â Â If the Client does have Session State and receives Session Present set to 0 it MUST discard its Session State if it continues with the Network Connection [MQTT-3.2.2-5].

Â 

Â 

If a Server sends a CONNACK packet containing a non-zero Reason Code it MUST set Session Present to 0 [MQTT-3.2.2-6].

Â 

####  3.2.2.2 Connect Reason Code

Byte 2 in the Variable Header is the Connect Reason Code.

Â 

The values the Connect Reason Code are shown below. If a well formed CONNECT packet is received by the Server, but the Server is unable to complete the Connection the Server MAY send a CONNACK packet containing the appropriate Connect Reason code from this table. If a Server sends a CONNACK packet containing a Reason code of 128 or greater it MUST then close the Network Connection [MQTT-3.2.2-7].

[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Table_3.1_-)

Table 3â1 - Connect Reason Code values

Â 

The Server sending the CONNACK packet MUST use one of the Connect Reason Code valuesT-3.2.2-8].

Â 

**Non-normative comment**

Reason Code 0x80 (Unspecified error) may be used where the Server knows the reason for the failure but does not wish to reveal it to the Client, or when none of the other Reason Code values applies.

Â 

The Server may choose to close the Network Connection without sending a CONNACK to enhance security in the case where an error is found on the CONNECT. For instance, when on a public network and the connection has not been authorized it might be unwise to indicate that this is an MQTT Server.

Â 

####  3.2.2.3 CONNACK Properties

#####  3.2.2.3.1 Property Length

This is the length of the Properties in the CONNACK packet Variable Header encoded as a Variable Byte Integer.

Â 

#####  3.2.2.3.2 Session Expiry Interval

**17 (0x11) Byte,** Identifier of the Session Expiry Interval.

Followed by the Four Byte Integer representing the Session Expiry Interval in seconds. It is a Protocol Error to include the Session Expiry Interval more than once.

Â 

If the Session Expiry Interval is absent the value in the CONNECT Packet used. The server uses this property to inform the Client that it is using a value other than that sent by the Client in the CONNACK. Refer to section 3.1.2.11.2 for a description of the use of Session Expiry Interval.

Â 

#####  3.2.2.3.3 Receive Maximum

**33 (0x21) Byte,** Identifier of the Receive Maximum. 

Followed by the Two Byte Integer representing the Receive Maximum value. It is a Protocol Error to include the Receive Maximum value more than once or for it to have the value 0.

Â 

The Server uses this value to limit the number of QoS 1 and QoS 2 publications that it is willing to process concurrently for the Client. It does not provide a mechanism to limit the QoS 0 publications that the Client might try to send.

Â 

If the Receive Maximum value is absent, then its value defaults to 65,535.

Â 

Refer to [section 4.9](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Flow_Control) Flow Control for details of how the Receive Maximum is used.

Â 

#####  3.2.2.3.4 Maximum QoS

**36 (0x24) Byte,** Identifier of the Maximum QoS. 

Followed by a Byte with a value of either 0 or 1. It is a Protocol Error to include Maximum QoS more than once, or to have a value other than 0 or 1. If the Maximum QoS is absent, the Client uses a Maximum QoS of 2.

Â 

If a Server does not support QoS 1 or QoS 2 PUBLISH packets it MUST send a Maximum QoS in the CONNACK packet specifying the highest QoS it supports [MQTT-3.2.2-9]. A Server that does not support QoS 1 or QoS 2 PUBLISH packets MUST still accept SUBSCRIBE packets containing a Requested QoS of 0, 1 or 2 [MQTT-3.2.2-10].

Â 

If a Client receives a Maximum QoS from a Server, it MUST NOT send PUBLISH packets at a QoS level exceeding the Maximum QoS level specified [MQTT-3.2.2-11]. It is a Protocol Error if the Server receives a PUBLISH packet with a QoS greater than the Maximum QoS it specified. In this case use DISCONNECT with Reason Code 0x9B (QoS not supported) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) Handling errors.

Â 

If a Server receives a CONNECT packet containing a Will QoS that exceeds its capabilities, it MUST reject the connection. It SHOULD use a CONNACK packet with Reason Code 0x9B (QoS not supported) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) Handling errors, and MUST close the Network Connection [MQTT-3.2.2-12].

Â 

**Non-normative comment**

A Client does not need to support QoS 1 or QoS 2 PUBLISH packets. If this is the case, the Client simply restricts the maximum QoS field in any SUBSCRIBE commands it sends to a value it can support.

Â 

#####  3.2.2.3.5 Retain Available

**37 (0x25) Byte** , Identifier of Retain Available.

Followed by a Byte field. If present, this byte declares whether the Server supports retained messages. A value of 0 means that retained messages are not supported. A value of 1 means retained messages are supported. If not present, then retained messages are supported. It is a Protocol Error to include Retain Available more than once or to use a value other than 0 or 1.

Â 

If a Server receives a CONNECT packet containing a Will Message with the Will Retain set to 1, and it does not support retained messages, the Server MUST reject the connection request. It SHOULD send CONNACK with Reason Code 0x9A (Retain not supported) and then it MUST close the Network Connection [MQTT-3.2.2-13]. 

Â 

A Client receiving Retain Available set to 0 from the Server MUST NOT send a PUBLISH packet with the RETAIN flag set to 1 [MQTT-3.2.2-14]. If the Server receives such a packet, this is a Protocol Error. The Server SHOULD send a DISCONNECT with Reason Code of 0x9A (Retain not supported) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors).

Â 

#####  3.2.2.3.6 Maximum Packet Size

**39 (0x27) Byte** , Identifier of the Maximum Packet Size. 

Followed by a Four Byte Integer representing the Maximum Packet Size the Server is willing to accept. If the Maximum Packet Size is not present, there is no limit on the packet size imposed beyond the limitations in the protocol as a result of the remaining length encoding and the protocol header sizes.

Â 

It is a Protocol Error to include the Maximum Packet Size more than once, or for the value to be set to zero.

Â 

The packet size is the total number of bytes in an MQTT Control Packet, as defined in [section 2.1.](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Dup)4\. The Server uses the Maximum Packet Size to inform the Client that it will not process packets whose size exceeds this limit.

Â 

The Client MUST NOT send packets exceeding Maximum Packet Size to the Server [MQTT-3.2.2-15]. If a Server receives a packet whose size exceeds this limit, this is a Protocol Error, the Server uses DISCONNECT with Reason Code 0x95 (Packet too large), as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors).

Â 

#####  3.2.2.3.7 Assigned Client Identifier

**18 (0x12) Byte** , Identifier of the Assigned Client Identifier. 

Followed by the UTF-8 string which is the Assigned Client Identifier. It is a Protocol Error to include the Assigned Client Identifier more than once.

Â 

The Client Identifier which was assigned by the Server because a zero length Client Identifier was found in the CONNECT packet.

Â 

If the Client connects using a zero length Client Identifier, the Server MUST respond with a CONNACK containing an Assigned Client Identifier. The Assigned Client Identifier MUST be a new Client Identifier not used by any other Session currently in the Server [MQTT-3.2.2-16].

Â 

#####  3.2.2.3.8 Topic Alias Maximum

**34 (0x22) Byte** , Identifier of the Topic Alias Maximum. 

Followed by the Two Byte Integer representing the Topic Alias Maximum value. It is a Protocol Error to include the Topic Alias Maximum value more than once. If the Topic Alias Maximum property is absent, the default value is 0.

Â 

This value indicates the highest value that the Server will accept as a Topic Alias sent by the Client. The Server uses this value to limit the number of Topic Aliases that it is willing to hold on this Connection. The Client MUST NOT send a Topic Alias in a PUBLISH packet to the Server greater than this value [MQTT-3.2.2-17]. A value of 0 indicates that the Server does not accept any Topic Aliases on this connection. If Topic Alias Maximum is absent or 0, the Client MUST NOT send any Topic Aliases on to the Server [MQTT-3.2.2-18].

Â 

#####  3.2.2.3.9 Reason String

**31 (0x1F) Byte** Identifier of the Reason String. 

Followed by the UTF-8 Encoded String representing the reason associated with this response. This Reason String is a human readable string designed for diagnostics and SHOULD NOT be parsed by the Client. 

Â 

The Server uses this value to give additional information to the Client. The Server MUST NOT send this property if it would increase the size of the CONNACK packet beyond the Maximum Packet Size specified by the Client [MQTT-3.2.2-19]. It is a Protocol Error to include the Reason String more than once.

Â 

**Non-normative comment**

Proper uses for the reason string in the Client would include using this information in an exception thrown by the Client code, or writing this string to a log.

Â 

#####  3.2.2.3.10 User Property

**38 (0x26) Byte,** Identifier of User Property.

Followed by a UTF-8 String Pair. This property can be used to provide additional information to the Client including diagnostic information. The Server MUST NOT send this property if it would increase the size of the CONNACK packet beyond the Maximum Packet Size specified by the Client [MQTT-3.2.2-20]. The User Property is allowed to appear multiple times to represent multiple name, value pairs. The same name is allowed to appear more than once.

Â 

The content and meaning of this property is not defined by this specification. The receiver of a CONNACK containing this property MAY ignore it.

Â 

#####  3.2.2.3.11 Wildcard Subscription Available

**40 (0x28) Byte,** Identifier of Wildcard Subscription Available.

Followed by a Byte field. If present, this byte declares whether the Server supports Wildcard Subscriptions. A value is 0 means that Wildcard Subscriptions are not supported. A value of 1 means Wildcard Subscriptions are supported. If not present, then Wildcard Subscriptions are supported. It is a Protocol Error to include the Wildcard Subscription Available more than once or to send a value other than 0 or 1.

Â 

If the Server receives a SUBSCRIBE packet containing a Wildcard Subscription and it does not support Wildcard Subscriptions, this is a Protocol Error. The Server uses DISCONNECT with Reason Code 0xA2 (Wildcard Subscriptions not supported) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors).

Â 

If a Server supports Wildcard Subscriptions, it can still reject a particular subscribe request containing a Wildcard Subscription. In this case the Server MAY send a SUBACK Control Packet with a Reason Code 0xA2 (Wildcard Subscriptions not supported).

Â 

#####  3.2.2.3.12 Subscription Identifiers Available

**41 (0x29) Byte** , Identifier of Subscription Identifier Available.

Followed by a Byte field. If present, this byte declares whether the Server supports Subscription Identifiers. A value is 0 means that Subscription Identifiers are not supported. A value of 1 means Subscription Identifiers are supported. If not present, then Subscription Identifiers are supported. It is a Protocol Error to include the Subscription Identifier Available more than once, or to send a value other than 0 or 1.

Â 

If the Server receives a SUBSCRIBE packet containing Subscription Identifier and it does not support Subscription Identifiers, this is a Protocol Error. The Server uses DISCONNECT with Reason Code of 0xA1 (Subscription Identifiers not supported) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors).

Â 

#####  3.2.2.3.13 Shared Subscription Available

**42 (0x2A) Byte** , Identifier of Shared Subscription Available.

Followed by a Byte field. If present, this byte declares whether the Server supports Shared Subscriptions. A value is 0 means that Shared Subscriptions are not supported. A value of 1 means Shared Subscriptions are supported. If not present, then Shared Subscriptions are supported. It is a Protocol Error to include the Shared Subscription Available more than once or to send a value other than 0 or 1.

Â 

If the Server receives a SUBSCRIBE packet containing Shared Subscriptions and it does not support Shared Subscriptions, this is a Protocol Error. The Server uses DISCONNECT with Reason Code 0x9E (Shared Subscriptions not supported) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors).

Â 

#####  3.2.2.3.14 Server Keep Alive

**19 (0x13) Byte** , Identifier of the Server Keep Alive. 

Followed by a Two Byte Integer with the Keep Alive time assigned by the Server. If the Server sends a Server Keep Alive on the CONNACK packet, the Client MUST use this value instead of the Keep Alive value the Client sent on CONNECT [MQTT-3.2.2-21]. If the Server does not send the Server Keep Alive, the Server MUST use the Keep Alive value set by the Client on CONNECT [MQTT-3.2.2-22]. It is a Protocol Error to include the Server Keep Alive more than once.

Â 

**Non-normative comment**

The primary use of the Server Keep Alive is for the Server to inform the Client that it will disconnect the Client for inactivity sooner than the Keep Alive specified by the Client.

Â 

#####  3.2.2.3.15 Response Information

**26 (0x1A) Byte** , Identifier of the Response Information. 

Followed by a UTF-8 Encoded String which is used as the basis for creating a Response Topic. The way in which the Client creates a Response Topic from the Response Information is not defined by this specification. It is a Protocol Error to include the Response Information more than once.

Â 

If the Client sends a Request Response Information with a value 1, it is OPTIONAL for the Server to send the Response Information in the CONNACK.

Â 

**Non-normative comment**

A common use of this is to pass a globally unique portion of the topic tree which is reserved for this Client for at least the lifetime of its Session. This often cannot just be a random name as both the requesting Client and the responding Client need to be authorized to use it. It is normal to use this as the root of a topic tree for a particular Client. For the Server to return this information, it normally needs to be correctly configured. Using this mechanism allows this configuration to be done once in the Server rather than in each Client.

Â 

Refer to [section 4.10](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Request_/_Response) for more information about Request / Response.

Â 

#####  3.2.2.3.16 Server Reference

**28 (0x1C) Byte** , Identifier of the Server Reference. 

Followed by a UTF-8 Encoded String which can be used by the Client to identify another Server to use. It is a Protocol Error to include the Server Reference more than once.

Â 

The Server uses a Server Reference in either a CONNACK or DISCONNECT packet with Reason code of 0x9C (Use another server) or Reason Code 0x9D (Server moved) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors).

Â 

Refer to[ section 4.11](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Server_redirection) Server redirection for information about how Server Reference is used.

Â 

#####  3.2.2.3.17 Authentication Method

**21 (0x15) Byte,** Identifier of the Authentication Method. 

Followed by a UTF-8 Encoded String containing the name of the authentication method. It is a Protocol Error to include the Authentication Method more than once. Refer to [section 4.12](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Enhanced_authentication) for more information about extended authentication.

Â 

#####  3.2.2.3.18 Authentication Data

**22 (0x16) Byte,** Identifier of the Authentication Data. 

Followed by Binary Data containing authentication data. The contents of this data are defined by the authentication method and the state of already exchanged authentication data. It is a Protocol Error to include the Authentication Data more than once. Refer to [section 4.12](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Enhanced_authentication) for more information about extended authentication.

Â 

###  3.2.3 CONNACK Payload

The CONNACK packet has no Payload.

Â 

##  3.3 PUBLISH Publish message

A PUBLISH packet is sent from a Client to a Server or from a Server to a Client to transport an Application Message.

Â 

###  3.3.1 PUBLISH Fixed Header

Figure 3â8 PUBLISH packet Fixed Header

Â 

####  3.3.1.1 DUP

**Position:** byte 1, bit 3.

If the DUP flag is set to 0, it indicates that this is the first occasion that the Client or Server has attempted to send this PUBLISH packet. If the DUP flag is set to 1, it indicates that this might be re-delivery of an earlier attempt to send the packet.

Â 

The DUP flag MUST be set to 1 by the Client or Server when it attempts to re-deliver a PUBLISH packet [MQTT-3.3.1-1]. The DUP flag MUST be set to 0 for all QoS 0 messages [MQTT-3.3.1-2]. 

Â 

The value of the DUP flag from an incoming PUBLISH packet is not propagated when the PUBLISH packet is sent to subscribers by the Server. The DUP flag in the outgoing PUBLISH packet is set independently to the incoming PUBLISH packet, its value MUST be determined solely by whether the outgoing PUBLISH packet is a retransmission [MQTT-3.3.1-3].

Â 

**Non-normative comment**

The receiver of an MQTT Control Packet that contains the DUP flag set to 1 cannot assume that it has seen an earlier copy of this packet. 

**Â**

**Non-normative comment******

It is important to note that the DUP flag refers to the MQTT Control Packet itself and not to the Application Message that it contains. When using QoS 1, it is possible for a Client to receive a PUBLISH packet with DUP flag set to 0 that contains a repetition of an Application Message that it received earlier, but with a different Packet Identifier.[ Section 2.2.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc358219870) provides more information about Packet Identifiers.

Â 

####  3.3.1.2 QoS

**Position:** byte 1, bits 2-1.

This field indicates the level of assurance for delivery of an Application Message. The QoS levels are shown below. [](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Table_3.11_-)

Â 

Table 3â2 - QoS definitions

Â 

If the Server included a Maximum QoS in its CONNACK response to a Client and it receives a PUBLISH packet with a QoS greater than this, then it uses DISCONNECT with Reason Code 0x9B (QoS not supported) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) Handling errors.

Â 

A PUBLISH Packet MUST NOT have both QoS bits set to 1 [MQTT-3.3.1-4]. If a Server or Client receives a PUBLISH packet which has both QoS bits set to 1 it is a Malformed Packet. Use DISCONNECT with Reason Code 0x81 (Malformed Packet) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors).

Â 

####  3.3.1.3 RETAIN

**Position:** byte 1, bit 0.

Â 

If the RETAIN flag is set to 1 in a PUBLISH packet sent by a Client to a Server, the Server MUST replace any existing retained message for this topic and store the Application Message [MQTT-3.3.1-5], so that it can be delivered to future subscribers whose subscriptions match its Topic Name. If the Payload contains zero bytes it is processed normally by the Server but any retained message with the same topic name MUST be removed and any future subscribers for the topic will not receive a retained message [MQTT-3.3.1-6]. A retained message with a Payload containing zero bytes MUST NOT be stored as a retained message on the Server [MQTT-3.3.1-7].

Â 

If the RETAIN flag is 0 in a PUBLISH packet sent by a Client to a Server, the Server MUST NOT store the message as a retained message and MUST NOT remove or replace any existing retained message [MQTT-3.3.1-8].

Â 

If the Server included Retain Available in its CONNACK response to a Client with its value set to 0 and it receives a PUBLISH packet with the RETAIN flag is set to 1, then it uses the DISCONNECT Reason Code of 0x9A (Retain not supported) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors).

Â 

When a new Nonâshared Subscription is made, the last retained message, if any, on each matching topic name is sent to the Client as directed by the Retain Handling Subscription Option. These messages are sent with the RETAIN flag set to 1. Which retained messages are sent is controlled by the Retain Handling Subscription Option. At the time of the Subscription:

Â Â Â Â Â Â Â Â If Retain Handling is set to 0 the Server MUST send the retained messages matching the Topic Filter of the subscription to the Client [MQTT-3.3.1-9].

Â Â Â Â Â Â Â Â If Retain Handling is set to 1 then if the subscription did not already exist, the Server MUST send all retained message matching the Topic Filter of the subscription to the Client, and if the subscription did exist the Server MUST NOT send the retained messages. [MQTT-3.3.1-10].

Â Â Â Â Â Â Â Â If Retain Handling is set to 2, the Server MUST NOT send the retained messages [MQTT-3.3.1-11].

Â 

Refer to [section 3.8.3.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Subscription_Options) for a definition of the Subscription Options.

Â 

If the Server receives a PUBLISH packet with the RETAIN flag set to 1, and QoS 0 it SHOULD store the new QoS 0 message as the new retained message for that topic, but MAY choose to discard it at any time. If this happens there will be no retained message for that topic. 

Â 

If the current retained message for a Topic expires, it is discarded and there will be no retained message for that topic.

Â 

The setting of the RETAIN flag in an Application Message forwarded by the Server from an established connection is controlled by the Retain As Published subscription option. Refer to [section 3.8.3.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Subscription_Options) for a definition of the Subscription Options.

Â 

Â Â Â Â Â Â Â Â If the value of Retain As Published subscription option is set to 0, the Server MUST set the RETAIN flag to 0 when forwarding an Application Message regardless of how the RETAIN flag was set in the received PUBLISH packet [MQTT-3.3.1-12].

Â Â Â Â Â Â Â Â If the value of Retain As Published subscription option is set to 1, the Server MUST set the RETAIN flag equal to the RETAIN flag in the received PUBLISH packet [MQTT-3.3.1-13].

Â 

**Non-normative comment**

Retained messages are useful where publishers send state messages on an irregular basis. A new non-shared subscriber will receive the most recent state.

Â 

####  3.3.1.4 Remaining Length

This is the length of Variable Header plus the length of the Payload, encoded as a Variable Byte Integer.

Â 

###  3.3.2 PUBLISH Variable Header

The Variable Header of the PUBLISH Packet contains the following fields in the order: Topic Name, Packet Identifier, and Properties. The rules for encoding Properties are described in [section 2.2.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Properties).

**Â**

####  3.3.2.1 Topic Name

The Topic Name identifies the information channel to which Payload data is published. 

Â 

The Topic Name MUST be present as the first field in the PUBLISH packet Variable Header. It MUST be a UTF-8 Encoded String as defined in [section 1.5.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_UTF-8_Encoded_String) [MQTT-3.3.2-1].

Â 

The Topic Name in the PUBLISH packet MUST NOT contain wildcard characters [MQTT-3.3.2-2].

Â 

The Topic Name in a PUBLISH packet sent by a Server to a subscribing Client MUST match the Subscription s Topic Filter according to the matching process defined in [section 4.7](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Topic_Names_and) [MQTT-3.3.2-3]. However, as the Server is permitted to map the Topic Name to another name, it might not be the same as the Topic Name in the original PUBLISH packet.

Â 

To reduce the size of the PUBLISH packet the sender can use a Topic Alias. The Topic Alias is described in [section 3.3.2.3.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Topic_Alias). It is a Protocol Error if the Topic Name is zero length and there is no Topic Alias.

Â 

####  3.3.2.2 Packet Identifier

The Packet Identifier field is only present in PUBLISH packets where the QoS level is 1 or 2. [Section 2.2.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc358219870) provides more information about Packet Identifiers.

Â 

####  3.3.2.3 PUBLISH Properties

#####  3.3.2.3.1 Property Length

The length of the Properties in the PUBLISH packet Variable Header encoded as a Variable Byte Integer.

Â 

#####  3.3.2.3.2 Payload Format Indicator

**1 (0x01) Byte,** Identifier of the Payload Format Indicator. 

Followed by the value of the Payload Forma t Indicator, either of: 

Â Â Â Â Â Â Â Â 0 (0x00) Byte Indicates that the Payload is unspecified bytes, which is equivalent to not sending a Payload Format Indicator.

Â Â Â Â Â Â Â Â 1 (0x01) Byte Indicates that the Payload is UTF-8 Encoded Character Data. The UTF-8 data in the Payload MUST be well-formed UTF-8 as defined by the Unicode specification [[Unicode](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#Unicode)] and restated in RFC 3629 [[RFC3629]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC3629). 

Â 

A Server MUST send the Payload Format Indicator unaltered to all subscribers receiving the Application Message [MQTT-3.3.2-4]. The receiver MAY validate that the Payload is of the format indicated, and if it is not send a PUBACK, PUBREC, or DISCONNECT with Reason Code of 0x99 (Payload format invalid) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors).Â Refer to [section 5.4.9](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Handling_of_Disallowed) for information about security issues in validating the payload format.[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#Unicode)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC3629)

Â 

#####  3.3.2.3.3 Message Expiry Interval`

**2 (0x02) Byte,** Identifier of the Message Expiry Interval. 

Followed by the Four Byte Integer representing the Message Expiry Interval.

Â 

If present, the Four Byte value is the lifetime of the Application Message in seconds. If the Message Expiry Interval has passed and the Server has not managed to start onward delivery to a matching subscriber, then it MUST delete the copy of the message for that subscriber [MQTT-3.3.2-5].

Â 

If absent, the Application Message does not expire.

Â 

The PUBLISH packet sent to a Client by the Server MUST contain a Message Expiry Interval set to the received value minus the time that the Application Message has been waiting in the Server [MQTT-3.3.2-6]. Refer to [section 4.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Session_State) for details and limitations of stored state. 

Â 

#####  3.3.2.3.4 Topic Alias

**35 (0x23) Byte** , Identifier of the Topic Alias. 

Followed by the Two Byte integer representing the Topic Alias value. It is a Protocol Error to include the Topic Alias value more than once.

Â 

A Topic Alias is an integer value that is used to identify the Topic instead of using the Topic Name. This reduces the size of the PUBLISH packet, and is useful when the Topic Names are long and the same Topic Names are used repetitively within a Network Connection.

Â 

The sender decides whether to use a Topic Alias and chooses the value. It sets a Topic Alias mapping by including a non-zero length Topic Name and a Topic Alias in the PUBLISH packet. The receiver processes the PUBLISH as normal but also sets the specified Topic Alias mapping to this Topic Name.

Â 

If a Topic Alias mapping has been set at the receiver, a sender can send a PUBLISH packet that contains that Topic Alias and a zero length Topic Name. The receiver then treats the incoming PUBLISH as if it had contained the Topic Name of the Topic Alias.

Â 

A sender can modify the Topic Alias mapping by sending another PUBLISH in the same Network Connection with the same Topic Alias value and a different non-zero length Topic Name.

Â 

Topic Alias mappings exist only within a Network Connection and last only for the lifetime of that Network Connection. A receiver MUST NOT carry forward any Topic Alias mappings from one Network Connection to another [MQTT-3.3.2-7].

Â 

A Topic Alias of 0 is not permitted. A sender MUST NOT send a PUBLISH packet containing a Topic Alias which has the value 0 [MQTT-3.3.2-8].

Â 

A Client MUST NOT send a PUBLISH packet with a Topic Alias greater than the Topic Alias Maximum value returned by the Server in the CONNACK packet [MQTT-3.3.2-9]. A Client MUST accept all Topic Alias values greater than 0 and less than or equal to the Topic Alias Maximum value that it sent in the CONNECT packet [MQTT-3.3.2-10]. 

Â 

A Server MUST NOT send a PUBLISH packet with a Topic Alias greater than the Topic Alias Maximum value sent by the Client in the CONNECT packet [MQTT-3.3.2-11]. A Server MUST accept all Topic Alias values greater than 0 and less than or equal to the Topic Alias Maximum value that it returned in the CONNACK packet [MQTT-3.3.2-12]. 

Â 

The Topic Alias mappings used by the Client and Server are independent from each other. Thus, when a Client sends a PUBLISH containing a Topic Alias value of 1 to a Server and the Server sends a PUBLISH with a Topic Alias value of 1 to that Client they will in general be referring to different Topics.

Â 

#####  3.3.2.3.5 Response Topic

**8 (0x08) Byte** , Identifier of the Response Topic. 

Followed by a UTF-8 Encoded String which is used as the Topic Name for a response message. The Response Topic MUST be a UTF-8 Encoded String as defined in [section 1.5.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_UTF-8_Encoded_String) [MQTT-3.3.2-13]. The Response Topic MUST NOT contain wildcard characters [MQTT-3.3.2-14]. It is a Protocol Error to include the Response Topic more than once. The presence of a Response Topic identifies the Message as a Request. 

Â 

Refer to [section 4.10](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Request_/_Response) for more information about Request / Response.

Â 

The Server MUST send the Response Topic unaltered to all subscribers receiving the Application Message [MQTT-3.3.2-15].

Â 

**Non-normative comment:**

The receiver of an Application Message with a Response Topic sends a response by using the Response Topic as the Topic Name of a PUBLISH. If the Request Message contains a Correlation Data, the receiver of the Request Message should also include this Correlation Data as a property in the PUBLISH packet of the Response Message.

Â 

#####  3.3.2.3.6 Correlation Data

**9 (0x09) Byte,** Identifier of the Correlation Data. 

Followed by Binary Data. The Correlation Data is used by the sender of the Request Message to identify which request the Response Message is for when it is received. It is a Protocol Error to include Correlation Data more than once. If the Correlation Data is not present, the Requester does not require any correlation data.

Â 

The Server MUST send the Correlation Data unaltered to all subscribers receiving the Application Message [MQTT-3.3.2-16]. The value of the Correlation Data only has meaning to the sender of the Request Message and receiver of the Response Message.

Â 

**Non-normative comment**

The receiver of an Application Message which contains both a Response Topic and a Correlation Data sends a response by using the Response Topic as the Topic Name of a PUBLISH. The Client should also send the Correlation Data unaltered as part of the PUBLISH of the responses.

Â 

**Non-normative comment**

If the Correlation Data contains information which can cause application failures if modified by the Client responding to the request, it should be encrypted and/or hashed to allow any alteration to be detected.

Â 

Refer to [section 4.10](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Request_/_Response) for more information about Request / Response

Â 

#####  3.3.2.3.7 User Property

**38 (0x26) Byte** , Identifier of the User Property.

Followed by a UTF-8 String Pair. The User Property is allowed to appear multiple times to represent multiple name, value pairs. The same name is allowed to appear more than once.

Â 

The Server MUST send all User Properties unaltered in a PUBLISH packet when forwarding the Application Message to a Client [MQTT-3.3.2-17]. The Server MUST maintain the order of User Properties when forwarding the Application Message [MQTT-3.3.2-18].

Â 

**Non-normative comment**

This property is intended to provide a means of transferring application layer name-value tags whose meaning and interpretation are known only by the application programs responsible for sending and receiving them.

Â 

#####  3.3.2.3.8 Subscription Identifier

**11 (0x0B)** , Identifier of the Subscription Identifier.

Followed by a Variable Byte Integer representing the identifier of the subscription. 

Â 

The Subscription Identifier can have the value of 1 to 268,435,455. It is a Protocol Error if the Subscription Identifier has a value of 0. Multiple Subscription Identifiers will be included if the publication is the result of a match to more than one subscription, in this case their order is not significant.

Â 

#####  3.3.2.3.9 Content Type

**3 (0x03)** Identifier of the Content Type. 

Followed by a UTF-8 Encoded String describing the content of the Application Message. The Content Type MUST be a UTF-8 Encoded String as defined in [section 1.5.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_UTF-8_Encoded_String) [MQTT-3.3.2-19]. 

It is a Protocol Error to include the Content Type more than once. The value of the Content Type is defined by the sending and receiving application. 

Â 

A Server MUST send the Content Type unaltered to all subscribers receiving the Application Message [MQTT-3.3.2-20]. 

**Â**

**Non-normative comment**

The UTF-8 Encoded String may use a MIME content type string to describe the contents of the Application message. However, since the sending and receiving applications are responsible for the definition and interpretation of the string, MQTT performs no validation of the string except to insure it is a valid UTF-8 Encoded String.

Â 

**Non-normative example**

Figure 3-9 shows an example of a PUBLISH packet with the Topic Name set to a/b , the Packet Identifier set to 10, and having no properties.

Â 

Figure 3â9 \- PUBLISH packet Variable Header non-normative example

Â 

###  3.3.3 PUBLISH Payload

The Payload contains the Application Message that is being published. The content and format of the data is application specific. The length of the Payload can be calculated by subtracting the length of the Variable Header from the Remaining Length field that is in the Fixed Header. It is valid for a PUBLISH packet to contain a zero length Payload.

Â 

###  3.3.4 PUBLISH Actions

The receiver of a PUBLISH Packet MUST respond with the packet as determined by the QoS in the PUBLISH Packet [MQTT-3.3.4-1].

Â 

Table 3â3 Expected PUBLISH packet response

Â 

The Client uses a PUBLISH packet to send an Application Message to the Server, for distribution to Clients with matching subscriptions.

Â 

The Server uses a PUBLISH packet to send an Application Message to each Client which has a matching subscription. The PUBLISH packet includes the Subscription Identifier carried in the SUBSCRIBE packet, if there was one.

Â 

When Clients make subscriptions with Topic Filters that include wildcards, it is possible for a Client s subscriptions to overlap so that a published message might match multiple filters. In this case the Server MUST deliver the message to the Client respecting the maximum QoS of all the matching subscriptions [MQTT-3.3.4-2]. In addition, the Server MAY deliver further copies of the message, one for each additional matching subscription and respecting the subscription s QoS in each case.

Â 

If a Client receives an unsolicited Application Message (not resulting from a subscription) which has a QoS greater than Maximum QoS, it uses a DISCONNECT packet with Reason Code 0x9B (QoS not supported ) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) Handling errors.

Â 

If the Client specified a Subscription Identifier for any of the overlapping subscriptions the Server MUST send those Subscription Identifiers in the message which is published as the result of the subscriptions [MQTT-3.3.4-3]. If the Server sends a single copy of the message it MUST include in the PUBLISH packet the Subscription Identifiers for all matching subscriptions which have a Subscription Identifiers, their order is not significant [MQTT-3.3.4-4]. If the Server sends multiple PUBLISH packets it MUST send, in each of them, the Subscription Identifier of the matching subscription if it has a Subscription Identifier [MQTT-3.3.4-5].

Â 

It is possible that the Client made several subscriptions which match a publication and that it used the same identifier for more than one of them. In this case the PUBLISH packet will carry multiple identical Subscription Identifiers.

Â 

It is a Protocol Error for a PUBLISH packet to contain any Subscription Identifier other than those received in SUBSCRIBE packet which caused it to flow. A PUBLISH packet sent from a Client to a Server MUST NOT contain a Subscription Identifier [MQTT-3.3.4-6].

Â 

If the subscription was shared, then only the Subscription Identifiers that were present in the SUBSCRIBE packet from the Client which is receiving the message are returned in the PUBLISH packet.

Â 

The action of the recipient when it receives a PUBLISH packet depends on the QoS level as described in [section 4.3.](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Quality_of_Service)

Â 

If the PUBLISH packet contains a Topic Alias, the receiver processes it as follows: 

1)Â Â Â A Topic Alias value of 0 or greater than the Maximum Topic Alias is a Protocol Error, the receiver uses DISCONNECT with Reason Code of 0x94 (Topic Alias invalid) as described in [section 4.13.](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors)

2)Â Â Â If the receiver has already established a mapping for the Topic Alias, then

a)Â Â Â If the packet has a zero length Topic Name, the receiver processes it using the Topic Name that corresponds to the Topic Alias

b)Â Â Â If the packet contains a non-zero length Topic Name, the receiver processes the packet using that Topic Name and updates its mapping for the Topic Alias to the Topic Name from the incoming packet

3)Â Â Â If the receiver does not already have a mapping for this Topic Alias

a)Â Â Â If the packet has a zero length Topic Name field it is a Protocol Error and the receiver uses DISCONNECT with Reason Code of 0x82 (Protocol Error) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors).

b)Â Â Â If the packet contains a Topic Name with a non-zero length, the receiver processes the packet using that Topic Name and sets its mappings for the Topic Alias to Topic Name from the incoming packet.

Â 

**Non-normative Comment**

If the Server distributes Application Messages to Clients at different protocol levels (such as MQTT V3.1.1) which do not support properties or other features provided by this specification, some information in the Application Message can be lost, and applications which depend on this information might not work correctly.

Â 

The Client MUST NOT send more than Receive Maximum QoS 1 and QoS 2 PUBLISH packets for which it has not received PUBACK, PUBCOMP, or PUBREC with a Reason Code of 128 or greater from the Server [MQTT-3.3.4-7]. If it receives more than Receive Maximum QoS 1 and QoS 2 PUBLISH packets where it has not sent a PUBACK or PUBCOMP in response, the Server uses a DISCONNECT packet with Reason Code 0x93 (Receive Maximum exceeded) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) Handling errors. Refer to [section 4.9](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Flow_Control) for more information about flow control.

Â 

The Client MUST NOT delay the sending of any packets other than PUBLISH packets due to having sent Receive Maximum PUBLISH packets without receiving acknowledgements for them [MQTT-3.3.4-8]. The value of Receive Maximum applies only to the current Network Connection.

Â 

**Non-normative comment**

The Client might choose to send fewer than Receive Maximum messages to the Server without receiving acknowledgement, even if it has more than this number of messages available to send. 

Â 

**Non-normative comment**

The Client might choose to suspend the sending of QoS 0 PUBLISH packets when it suspends the sending of QoS 1 and QoS 2 PUBLISH packets. 

Â 

**Non-normative comment**

If the Client sends QoS 1 or QoS 2 PUBLISH packets before it has received a CONNACK packet, it risks being disconnected because it has sent more than Receive Maximum publications.

**Â**

The Server MUST NOT send more than Receive Maximum QoS 1 and QoS 2 PUBLISH packets for which it has not received PUBACK, PUBCOMP, or PUBREC with a Reason Code of 128 or greater from the Client [MQTT-3.3.4-9]. If it receives more than Receive Maximum QoS 1 and QoS 2 PUBLISH packets where it has not sent a PUBACK or PUBCOMP in response, the Client uses DISCONNECT with Reason Code 0x93 (Receive Maximum exceeded) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) Handling errors. Refer to [section 4.9](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Flow_Control) for more information about flow control.

Â 

The Server MUST NOT delay the sending of any packets other than PUBLISH packets due to having sent Receive Maximum PUBLISH packets without receiving acknowledgements for them [MQTT-3.3.4-10]. 

Â 

**Non-normative comment**

The Server might choose to send fewer than Receive Maximum messages to the Client without receiving acknowledgement, even if it has more than this number of messages available to send. 

Â 

**Non-normative comment**

The Server might choose to suspend the sending of QoS 0 PUBLISH packets when it suspends the sending of QoS 1 and QoS 2 PUBLISH packets.

Â 

##  3.4 PUBACK Publish acknowledgement 

A PUBACK packet is the response to a PUBLISH packet with QoS 1.

Â 

###  3.4.1 PUBACK Fixed Header

Figure 3â10 - PUBACK packet Fixed Header

Â 

**Remaining Length field**

This is the length of the Variable Header, encoded as a Variable Byte Integer.

Â 

###  3.4.2 PUBACK Variable Header

The Variable Header of the PUBACK Packet contains the following fields in the order: Packet Identifier from the PUBLISH packet that is being acknowledged, PUBACK Reason Code, Property Length, and the Properties. The rules for encoding Properties are described in [section 2.2.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Properties). 

Â 

Figure 3â11 PUBACK packet Variable Header

Â 

####  3.4.2.1 PUBACK Reason Code

Byte 3 in the Variable Header is the PUBACK Reason Code. If the Remaining Length is 2, then there is no Reason Code and the value of 0x00 (Success) is used.

Â 

Table 3â4 - PUBACK Reason Codes

Â 

The Client or Server sending the PUBACK packet MUST use one of the PUBACK Reason Codes [MQTT-3.4.2-1]. The Reason Code and Property Length can be omitted if the Reason Code is 0x00 (Success) and there are no Properties. In this case the PUBACK has a Remaining Length of 2.

Â 

####  3.4.2.2 PUBACK Properties

#####  3.4.2.2.1 Property Length

The length of the Properties in the PUBACK packet Variable Header encoded as a Variable Byte Integer. If the Remaining Length is less than 4 there is no Property Length and the value of 0 is used.

Â 

#####  3.4.2.2.2 Reason String

**31 (0x1F) Byte** , Identifier of the Reason String. 

Followed by the UTF-8 Encoded String representing the reason associated with this response. This Reason String is a human readable string designed for diagnostics and is not intended to be parsed by the receiver. 

Â 

The sender uses this value to give additional information to the receiver. The sender MUST NOT send this property if it would increase the size of the PUBACK packet beyond the Maximum Packet Size specified by the receiver [MQTT-3.4.2-2]. It is a Protocol Error to include the Reason String more than once.

Â 

#####  3.4.2.2.3 User Property

**38 (0x26) Byte,** Identifier of the User Property.

Followed by UTF-8 String Pair. This property can be used to provide additional diagnostic or other information. The sender MUST NOT send this property if it would increase the size of the PUBACK packet beyond the Maximum Packet Size specified by the receiver [MQTT-3.4.2-3]. The User Property is allowed to appear multiple times to represent multiple name, value pairs. The same name is allowed to appear more than once.

Â 

###  3.4.3 PUBACK Payload

The PUBACK packet has no Payload.

Â 

###  3.4.4 PUBACK Actions

This is described in [section 4.3.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_QoS_1:_At).

Â 

##  3.5 PUBREC Publish received (QoS 2 delivery part 1)

A PUBREC packet is the response to a PUBLISH packet with QoS 2\. It is the second packet of the QoS 2 protocol exchange.

Â 

###  3.5.1 PUBREC Fixed Header

Figure 3â12 \- PUBREC packet Fixed Header

Â 

**Remaining Length field**

This is the length of the Variable Header, encoded as a Variable Byte Integer.

Â 

###  3.5.2 PUBREC Variable Header

The Variable Header of the PUBREC Packet consists of the following fields in the order: the Packet Identifier from the PUBLISH packet that is being acknowledged, PUBREC Reason Code, and Properties. The rules for encoding Properties are described in[ section 2.2.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Properties). 

Â 

Â Figure 3â13 - PUBREC packet Variable Header

Â 

####  3.5.2.1 PUBREC Reason Code

Byte 3 in the Variable Header is the PUBREC Reason Code. If the Remaining Length is 2, then the Publish Reason Code has the value 0x00 (Success).

Â 

Table 3â5 PUBREC Reason Codes

Â 

The Client or Server sending the PUBREC packet MUST use one of the PUBREC Reason Code values. [MQTT-3.5.2-1]. The Reason Code and Property Length can be omitted if the Reason Code is 0x00 (Success) and there are no Properties. In this case the PUBREC has a Remaining Length of 2.

Â 

####  3.5.2.2 PUBREC Properties

#####  3.5.2.2.1 Property Length

The length of the Properties in the PUBREC packet Variable Header encoded as a Variable Byte Integer. If the Remaining Length is less than 4 there is no Property Length and the value of 0 is used.

Â 

#####  3.5.2.2.2 Reason String

**31 (0x1F) Byte** , Identifier of the Reason String.

Followed by the UTF-8 Encoded String representing the reason associated with this response. This Reason String is human readable, designed for diagnostics and SHOULD NOT be parsed by the receiver. 

Â 

The sender uses this value to give additional information to the receiver. The sender MUST NOT send this property if it would increase the size of the PUBREC packet beyond the Maximum Packet Size specified by the receiver [MQTT-3.5.2-2]. It is a Protocol Error to include the Reason String more than once.

Â 

#####  3.5.2.2.3 User Property

**38 (0x26) Byte,** Identifier of the User Property.

Followed by UTF-8 String Pair. This property can be used to provide additional diagnostic or other information. The sender MUST NOT send this property if it would increase the size of the PUBREC packet beyond the Maximum Packet Size specified by the receiver [MQTT-3.5.2-3]. The User Property is allowed to appear multiple times to represent multiple name, value pairs. The same name is allowed to appear more than once.

Â 

###  3.5.3 PUBREC Payload

The PUBREC packet has no Payload.

###  3.5.4 PUBREC Actions

This is described in[ section 4.3.3](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_QoS_2:_Exactly).

Â 

##  3.6 PUBREL Publish release (QoS 2 delivery part 2)

A PUBREL packet is the response to a PUBREC packet. It is the third packet of the QoS 2 protocol exchange.

Â 

###  3.6.1 PUBREL Fixed Header

Figure 3â14 PUBREL packet Fixed Header

**Â**

Bits 3,2,1 and 0 of the Fixed Header in the PUBREL packet are reserved and MUST be set to 0,0,1 and 0 respectively. The Server MUST treat any other value as malformed and close the Network Connection [MQTT-3.6.1-1].

Â 

**Remaining Length field**

This is the length of the Variable Header, encoded as a Variable Byte Integer.

Â 

###  3.6.2 PUBREL Variable Header

The Variable Header of the PUBREL Packet contains the following fields in the order: the Packet Identifier from the PUBREC packet that is being acknowledged, PUBREL Reason Code, and Properties. The rules for encoding Properties are described in [section 2.2.2.](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Properties)

Â 

Â Figure 3â15 PUBREL packet Variable Header

Â 

####  3.6.2.1 PUBREL Reason Code

Byte 3 in the Variable Header is the PUBREL Reason Code. If the Remaining Length is 2, the value of 0x00 (Success) is used.

Â 

Table 3â6 - PUBREL Reason Codes

Â 

The Client or Server sending the PUBREL packet MUST use one of the PUBREL Reason Code values [MQTT-3.6.2-1]. The Reason Code and Property Length can be omitted if the Reason Code is 0x00 (Success) and there are no Properties. In this case the PUBREL has a Remaining Length of 2.

Â 

####  3.6.2.2 PUBREL Properties

#####  3.6.2.2.1 Property Length

The length of the Properties in the PUBREL packet Variable Header encoded as a Variable Byte Integer. If the Remaining Length is less than 4 there is no Property Length and the value of 0 is used.

Â 

#####  3.6.2.2.2 Reason String

**31 (0x1F) Byte** , Identifier of the Reason String. 

Followed by the UTF-8 Encoded String representing the reason associated with this response. This Reason String is human readable, designed for diagnostics and SHOULD NOT be parsed by the receiver. 

Â 

The sender uses this value to give additional information to the receiver. The sender MUST NOT send this Property if it would increase the size of the PUBREL packet beyond the Maximum Packet Size specified by the receiver [MQTT-3.6.2-2]. It is a Protocol Error to include the Reason String more than once.

Â 

#####  3.6.2.2.3 User Property

**38 (0x26) Byte,** Identifier of the User Property.

Followed by UTF-8 String Pair. This property can be used to provide additional diagnostic or other information for the PUBREL. The sender MUST NOT send this property if it would increase the size of the PUBREL packet beyond the Maximum Packet Size specified by the receiver [MQTT-3.6.2-3]. The User Property is allowed to appear multiple times to represent multiple name, value pairs. The same name is allowed to appear more than once.

Â 

###  3.6.3 PUBREL Payload

The PUBREL packet has no Payload.

Â 

###  3.6.4 PUBREL Actions

This is described in [section 4.3.3](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_QoS_2:_Exactly).

Â 

##  3.7 PUBCOMP Publish complete (QoS 2 delivery part 3)

The PUBCOMP packet is the response to a PUBREL packet. It is the fourth and final packet of the QoS 2 protocol exchange.

Â 

###  3.7.1 PUBCOMP Fixed Header

Figure 3â16 PUBCOMP packet Fixed Header

Â 

**Remaining Length field**

This is the length of the Variable Header, encoded as a Variable Byte Integer.

Â 

###  3.7.2 PUBCOMP Variable Header

The Variable Header of the PUBCOMP Packet contains the following fields in the order: Packet Identifier from the PUBREL packet that is being acknowledged, PUBCOMP Reason Code, and Properties. The rules for encoding Properties are described in [section 2.2.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Properties). 

Â 

Figure 3â17 - PUBCOMP packet Variable Header

Â 

####  3.7.2.1 PUBCOMP Reason Code

Byte 3 in the Variable Header is the PUBCOMP Reason Code. If the Remaining Length is 2, then the value 0x00 (Success) is used.

Â 

Table 3â7 PUBCOMP Reason Codes

Â 

The Client or Server sending the PUBCOMP packet MUST use one of the PUBCOMP Reason Code values [MQTT-3.7.2-1]. The Reason Code and Property Length can be omitted if the Reason Code is 0x00 (Success) and there are no Properties. In this case the PUBCOMP has a Remaining Length of 2.

Â 

####  3.7.2.2 PUBCOMP Properties

#####  3.7.2.2.1 Property Length

The length of the Properties in the PUBCOMP packet Variable Header encoded as a Variable Byte Integer. If the Remaining Length is less than 4 there is no Property Length and the value of 0 is used.

Â 

#####  3.7.2.2.2 Reason String

**31 (0x1F) Byte** , Identifier of the Reason String. 

Followed by the UTF-8 Encoded String representing the reason associated with this response. This Reason String is a human readable string designed for diagnostics and SHOULD NOT be parsed by the receiver. 

Â 

The sender uses this value to give additional information to the receiver. The sender MUST NOT send this Property if it would increase the size of the PUBCOMP packet beyond the Maximum Packet Size specified by the receiver [MQTT-3.7.2-2]. It is a Protocol Error to include the Reason String more than once.

Â 

#####  3.7.2.2.3 User Property

**38 (0x26) Byte,** Identifier of the User Property.

Followed by UTF-8 String Pair. This property can be used to provide additional diagnostic or other information. The sender MUST NOT send this property if it would increase the size of the PUBCOMP packet beyond the Maximum Packet Size specified by the receiver [MQTT-3.7.2-3]. The User Property is allowed to appear multiple times to represent multiple name, value pairs. The same name is allowed to appear more than once.

Â 

###  3.7.3 PUBCOMP Payload

The PUBCOMP packet has no Payload.

Â 

###  3.7.4 PUBCOMP Actions

This is described in [section 4.3.3](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_QoS_2:_Exactly).

Â 

##  3.8 SUBSCRIBE - Subscribe request

The SUBSCRIBE packet is sent from the Client to the Server to create one or more Subscriptions. Each Subscription registers a Client s interest in one or more Topics. The Server sends PUBLISH packets to the Client to forward Application Messages that were published to Topics that match these Subscriptions. The SUBSCRIBE packet also specifies (for each Subscription) the maximum QoS with which the Server can send Application Messages to the Client.

Â 

###  3.8.1 SUBSCRIBE Fixed Header

Figure 3â18 SUBSCRIBE packet Fixed Header

Â 

Bits 3,2,1 and 0 of the Fixed Header of the SUBSCRIBE packet are reserved and MUST be set to 0,0,1 and 0 respectively. The Server MUST treat any other value as malformed and close the Network Connection [MQTT-3.8.1-1].

Â 

**Remaining Length field**

This is the length of Variable Header plus the length of the Payload, encoded as a Variable Byte Integer.

Â 

###  3.8.2 SUBSCRIBE Variable Header

The Variable Header of the SUBSCRIBE Packet contains the following fields in the order: Packet Identifier, and Properties. [Section 2.2.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc358219870) provides more information about Packet Identifiers. The rules for encoding Properties are described in [section 2.2.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Properties).

Â 

**Non-normative example**

Figure 3-19 shows an example of a SUBSCRIBE variable header with a Packet Identifier of 10 and no properties.

**Â**

Figure 3â19 SUBSCRIBE Variable Header example

Â 

####  3.8.2.1 SUBSCRIBE Properties

#####  3.8.2.1.1 Property Length

The length of Properties in the SUBSCRIBE packet Variable Header encoded as a Variable Byte Integer.

Â 

#####  3.8.2.1.2 Subscription Identifier

**11 (0x0B) Byte,** Identifier of the Subscription Identifier. 

Followed by a Variable Byte Integer representing the identifier of the subscription. The Subscription Identifier can have the value of 1 to 268,435,455. It is a Protocol Error if the Subscription Identifier has a value of 0. It is a Protocol Error to include the Subscription Identifier more than once.

Â 

The Subscription Identifier is associated with any subscription created or modified as the result of this SUBSCRIBE packet. If there is a Subscription Identifier, it is stored with the subscription. If this property is not specified, then the absence of a Subscription Identifier is stored with the subscription.

Â 

Refer to [section 3.8.3.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Subscription_Options) for more information about the handling of Subscription Identifiers.

Â 

#####  3.8.2.1.3 User Property

**38 (0x26) Byte** , Identifier of the User Property. 

Followed by a UTF-8 String Pair. 

Â 

The User Property is allowed to appear multiple times to represent multiple name, value pairs. The same name is allowed to appear more than once. 

Â 

**Non-normative comment**

User Properties on the SUBSCRIBE packet can be used to send subscription related properties from the Client to the Server. The meaning of these properties is not defined by this specification.

Â 

###  3.8.3 SUBSCRIBE Payload

The Payload of a SUBSCRIBE packet contains a list of Topic Filters indicating the Topics to which the Client wants to subscribe. The Topic Filters MUST be a UTF-8 Encoded String [MQTT-3.8.3-1]. Each Topic Filter is followed by a Subscription Options byte. 

Â 

The Payload MUST contain at least one Topic Filter and Subscription Options pair [MQTT-3.8.3-2]. A SUBSCRIBE packet with no Payload is a Protocol Error. Refer to [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) for information about handling errors. 

Â 

####  3.8.3.1 Subscription Options

Bits 0 and 1 of the Subscription Options represent Maximum QoS field. This gives the maximum QoS level at which the Server can send Application Messages to the Client. It is a Protocol Error if the Maximum QoS field has the value 3.

Â 

Bit 2 of the Subscription Options represents the No Local option. If the value is 1, Application Messages MUST NOT be forwarded to a connection with a ClientID equal to the ClientID of the publishing connection [MQTT-3.8.3-3]. It is a Protocol Error to set the No Local bit to 1 on a Shared Subscription [MQTT-3.8.3-4].

Â 

Bit 3 of the Subscription Options represents the Retain As Published option. If 1, Application Messages forwarded using this subscription keep the RETAIN flag they were published with. If 0, Application Messages forwarded using this subscription have the RETAIN flag set to 0. Retained messages sent when the subscription is established have the RETAIN flag set to 1.

Â 

Bits 4 and 5 of the Subscription Options represent the Retain Handling option. This option specifies whether retained messages are sent when the subscription is established. This does not affect the sending of retained messages at any point after the subscribe. If there are no retained messages matching the Topic Filter, all of these values act the same. The values are:

0 = Send retained messages at the time of the subscribe

1 = Send retained messages at subscribe only if the subscription does not currently exist

2 = Do not send retained messages at the time of the subscribe

It is a Protocol Error to send a Retain Handling value of 3.

Â 

Bits 6 and 7 of the Subscription Options byte are reserved for future use. The Server MUST treat a SUBSCRIBE packet as malformed if any of Reserved bits in the Payload are non-zero [MQTT-3.8.3-5].

Â 

**Non-normative comment**

The No Local and Retain As Published subscription options can be used to implement bridging where the Client is sending the message on to another Server.

Â 

**Non-normative comment**

Not sending retained messages for an existing subscription is useful when a reconnect is done and the Client is not certain whether the subscriptions were completed in the previous connection to the Session.

Â 

**Non-normative comment**

Not sending stored retained messages because of a new subscription is useful where a Client wishes to receive change notifications and does not need to know the initial state.

Â 

**Non-normative comment**

For a Server that indicates it does not support retained messages, all valid values of Retain As Published and Retain Handling give the same result which is to not send any retained messages at subscribe and to set the RETAIN flag to 0 for all messages.

Â 

Figure 3â20 SUBSCRIBE packet Payload format

RAP means Retain as Published.

NL means No Local.

Â 

**Non-normative example**

Figure 3.21 show the SUBSCRIBE Payload example with two Topic Filters. The first is a/b with QoS 1, and the second is c/d with QoS 2. 

[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Table_3.4_-)

Figure 3â21 \- Payload byte format non-normative example

Â 

###  3.8.4 SUBSCRIBE Actions

When the Server receives a SUBSCRIBE packet from a Client, the Server MUST respond with a SUBACK packet [MQTT-3.8.4-1]. The SUBACK packet MUST have the same Packet Identifier as the SUBSCRIBE packet that it is acknowledging [MQTT-3.8.4-2].

Â 

The Server is permitted to start sending PUBLISH packets matching the Subscription before the Server sends the SUBACK packet.

Â 

If a Server receives a SUBSCRIBE packet containing a Topic Filter that is identical to a Nonâshared Subscription s Topic Filter for the current Session, then it MUST replace that existing Subscription with a new Subscription [MQTT-3.8.4-3]. The Topic Filter in the new Subscription will be identical to that in the previous Subscription, although its Subscription Options could be different. If the Retain Handling option is 0, any existing retained messages matching the Topic Filter MUST be re-sent, but Applicaton Messages MUST NOT be lost due to replacing the Subscription [MQTT-3.8.4-4]. 

Â 

If a Server receives a Nonâshared Topic Filter that is not identical to any Topic Filter for the current Session, a new Non-shared Subscription is created. If the Retain Handling option is not 2, all matching retained messages are sent to the Client. 

Â 

If a Server receives a Topic Filter that is identical to the Topic Filter for a Shared Subscription that already exists on the Server, the Session is added as a subscriber to that Shared Subscription. No retained messages are sent. 

Â 

If a Server receives a Shared Subscription Topic Filter that is not identical to any existing Shared Subscription s Topic Filter, a new Shared Subscription is created. The Session is added as a subscriber to that Shared Subscription. No retained messages are sent. 

Â 

Refer to [section 4.8](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Shared_Subscriptions) for more details on Shared Subscriptions.

Â 

If a Server receives a SUBSCRIBE packet that contains multiple Topic Filters it MUST handle that packet as if it had received a sequence of multiple SUBSCRIBE packets, except that it combines their responses into a single SUBACK response [MQTT-3.8.4-5].

Â 

The SUBACK packet sent by the Server to the Client MUST contain a Reason Code for each Topic Filter/Subscription Option pair [MQTT-3.8.4-6]. This Reason Code MUST either show the maximum QoS that was granted for that Subscription or indicate that the subscription failed [MQTT-3.8.4-7]. The Server might grant a lower Maximum QoS than the subscriber requested. The QoS of Application Messages sent in response to a Subscription MUST be the minimum of the QoS of the originally published message and the Maximum QoS granted by the Server [MQTT-3.8.4-8]. The server is permitted to send duplicate copies of a message to a subscriber in the case where the original message was published with QoS 1 and the maximum QoS granted was QoS 0.

Â 

**Non-normative comment**

If a subscribing Client has been granted maximum QoS 1 for a particular Topic Filter, then a QoS 0 Application Message matching the filter is delivered to the Client at QoS 0. This means that at most one copy of the message is received by the Client. On the other hand, a QoS 2 Message published to the same topic is downgraded by the Server to QoS 1 for delivery to the Client, so that Client might receive duplicate copies of the Message.

Â 

**Non-normative comment**

If the subscribing Client has been granted maximum QoS 0, then an Application Message originally published as QoS 2 might get lost on the hop to the Client, but the Server should never send a duplicate of that Message. A QoS 1 Message published to the same topic might either get lost or duplicated on its transmission to that Client.

Â 

**Non-normative comment**

Subscribing to a Topic Filter at QoS 2 is equivalent to saying "I would like to receive Messages matching this filter at the QoS with which they were published". This means a publisher is responsible for determining the maximum QoS a Message can be delivered at, but a subscriber is able to require that the Server downgrades the QoS to one more suitable for its usage.

Â 

The Subscription Identifiers are part of the Session State in the Server and are returned to the Client receiving a matching PUBLISH packet. They are removed from the Server s Session State when the Server receives an UNSUBSCRIBE packet, when the Server receives a SUBSCRIBE packet from the Client for the same Topic Filter but with a different Subscription Identifier or with no Subscription Identifier, or when the Server sends Session Present 0 in a CONNACK packet.

Â 

The Subscription Identifiers do not form part of the Client s Session State in the Client. In a useful implementation, a Client will associate the Subscription Identifiers with other Client side state, this state is typically removed when the Client unsubscribes, when the Client subscribes for the same Topic Filter with a different identifier or no identifier, or when the Client receives Session Present 0 in a CONNACK packet.

Â 

The Server need not use the same set of Subscription Identifiers in the retransmitted PUBLISH packet. The Client can remake a Subscription by sending a SUBSCRIBE packet containing a Topic Filter that is identical to the Topic Filter of an existing Subscription in the current Session. If the Client remade a subscription after the initial transmission of a PUBLISH packet and used a different Subscription Identifier, then the Server is allowed to use the identifiers from the first transmission in any retransmission. Alternatively, the Server is allowed to use the new identifiers during a retransmission. The Server is not allowed to revert to the old identifier after it has sent a PUBLISH packet containing the new one.

**Â**

**Non-normative comment**

Usage scenarios, for illustration of Subscription Identifiers.

Â Â Â Â Â Â Â Â The Client implementation indicates via its programming interface that a publication matched more than one subscription. The Client implementation generates a new identifier each time a subscription is made. If the returned publication carries more than one Subscription Identifier, then the publication matched more than one subscription.

Â Â Â Â Â Â Â Â The Client implementation allows the subscriber to direct messages to a callback associated with the subscription. The Client implementation generates an identifier which uniquely maps the identifier to the callback. When a publication is received it uses the Subscription Identifier to determine which callback is driven.

Â Â Â Â Â Â Â Â The Client implementation returns the topic string used to make the subscription to the application when it delivers the published message. To achieve this the Client generates an identifier which uniquely identifies the Topic Filter. When a publication is received the Client implementation uses the identifiers to look up the original Topic Filters and return them to the Client application.

Â Â Â Â Â Â Â Â A gateway forwards publications received from a Server to Clients that have made subscriptions to the gateway. The gateway implementation maintains a map of each unique Topic Filter it receives to the set of ClientID, Subscription Identifier pairs that it also received. It generates a unique identifier for each Topic Filter that it forwards to the Server. When a publication is received, the gateway uses the Subscription Identifiers it received from the Server to look up the Client Identifier, Subscription Identifier pairs associated with them. It adds these to the PUBLISH packets it sends to the Clients. If the upstream Server sent multiple PUBLISH packets because the message matched multiple subscriptions, then this behavior is mirrored to the Clients.

Â 

##  3.9 SUBACK Subscribe acknowledgement

A SUBACK packet is sent by the Server to the Client to confirm receipt and processing of a SUBSCRIBE packet.

Â 

A SUBACK packet contains a list of Reason Codes, that specify the maximum QoS level that was granted or the error which was found for each Subscription that was requested by the SUBSCRIBE.

Â 

###  3.9.1 SUBACK Fixed Header

Figure 3â22 \- SUBACK Packet Fixed Header

Â 

**Remaining Length field**

This is the length of Variable Header plus the length of the Payload, encoded as a Variable Byte Integer.

Â 

###  3.9.2 SUBACK Variable Header

The Variable Header of the SUBACK Packet contains the following fields in the order: the Packet Identifier from the SUBSCRIBE Packet that is being acknowledged, and Properties. 

Â 

####  3.9.2.1 SUBACK Properties

#####  3.9.2.1.1 Property Length

The length of Properties in the SUBACK packet Variable Header encoded as a Variable Byte Integer

Â 

#####  3.9.2.1.2 Reason String

**31 (0x1F) Byte,** Identifier of the Reason String. 

Followed by the UTF-8 Encoded String representing the reason associated with this response. This Reason String is a human readable string designed for diagnostics and SHOULD NOT be parsed by the Client. 

Â 

The Server uses this value to give additional information to the Client. The Server MUST NOT send this Property if it would increase the size of the SUBACK packet beyond the Maximum Packet Size specified by the Client [MQTT-3.9.2-1]. It is a Protocol Error to include the Reason String more than once.

Â 

#####  3.9.2.1.3 User Property

**38 (0x26) Byte,** Identifier of the User Property.

Followed by UTF-8 String Pair. This property can be used to provide additional diagnostic or other information. The Server MUST NOT send this property if it would increase the size of the SUBACK packet beyond the Maximum Packet Size specified by Client [MQTT-3.9.2-2]. The User Property is allowed to appear multiple times to represent multiple name, value pairs. The same name is allowed to appear more than once.

[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Figure_3.25_-)

Figure 3â23 SUBACK packet Variable Header

Â 

###  3.9.3 SUBACK Payload

The Payload contains a list of Reason Codes. Each Reason Code corresponds to a Topic Filter in the SUBSCRIBE packet being acknowledged. The order of Reason Codes in the SUBACK packet MUST match the order of Topic Filters in the SUBSCRIBE packet [MQTT-3.9.3-1].

Â 

Table 3â8 - Subscribe Reason Codes

Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â Â 

The Server sending a SUBACK packet MUST use one of the Subscribe Reason Codes for each Topic Filter received [MQTT-3.9.3-2].

Â 

**Non-normative comment**

There is always one Reason Code for each Topic Filter in the corresponding SUBSCRIBE packet. If the Reason Code is not specific to a Topic Filters (such as 0x91 (Packet Identifier in use)) it is set for each Topic Filter.

Â 

##  3.10 UNSUBSCRIBE Unsubscribe request

An UNSUBSCRIBE packet is sent by the Client to the Server, to unsubscribe from topics.

Â 

###  3.10.1 UNSUBSCRIBE Fixed Header

Figure 3.28 UNSUBSCRIBE packet Fixed Header

Â 

Bits 3,2,1 and 0 of the Fixed Header of the UNSUBSCRIBE packet are reserved and MUST be set to 0,0,1 and 0 respectively. The Server MUST treat any other value as malformed and close the Network Connection [MQTT-3.10.1-1].

Â 

**Remaining Length field**

This is the length of Variable Header (2 bytes) plus the length of the Payload, encoded as a Variable Byte Integer.

Â 

###  3.10.2 UNSUBSCRIBE Variable Header

The Variable Header of the UNSUBSCRIBE Packet contains the following fields in the order: Packet Identifier, and Properties. [Section 2.2.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc358219870) provides more information about Packet Identifiers. The rules for encoding Properties are described in [section 2.2.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Properties).

Â 

####  3.10.2.1 UNSUBSCRIBE Properties

#####  3.10.2.1.1 Property Length

The length of Properties in the UNSUBSCRIBE packet Variable Header encoded as a Variable Byte Integer.

Â 

#####  3.10.2.1.2 User Property

**38 (0x26) Byte** , Identifier of the User Property. 

Followed by a UTF-8 String Pair. 

Â 

The User Property is allowed to appear multiple times to represent multiple name, value pairs. The same name is allowed to appear more than once. 

Â 

**Non-normative comment**

User Properties on the UNSUBSCRIBE packet can be used to send subscription related properties from the Client to the Server. The meaning of these properties is not defined by this specification.

Â 

###  3.10.3 UNSUBSCRIBE Payload

The Payload for the UNSUBSCRIBE packet contains the list of Topic Filters that the Client wishes to unsubscribe from. The Topic Filters in an UNSUBSCRIBE packet MUST be UTF-8 Encoded Strings [MQTT-3.10.3-1] as defined in [section 1.5.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_UTF-8_Encoded_String), packed contiguously.

Â 

The Payload of an UNSUBSCRIBE packet MUST contain at least one Topic Filter [MQTT-3.10.3-2]. An UNSUBSCRIBE packet with no Payload is a Protocol Error. Refer to [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) for information about handling errors. 

Â 

**Non-normative example**

Figure 3.30 shows the Payload for an UNSUBSCRIBE packet with two Topic Filters a/b and c/d .[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Table3.6_-_Payload)

Â 

Figure 3.30 - Payload byte format non-normative example

Â 

###  3.10.4 UNSUBSCRIBE Actions

The Topic Filters (whether they contain wildcards or not) supplied in an UNSUBSCRIBE packet MUST be compared character-by-character with the current set of Topic Filters held by the Server for the Client. If any filter matches exactly then its owning Subscription MUST be deleted [MQTT-3.10.4-1], otherwise no additional processing occurs.

Â 

When a Server receives UNSUBSCRIBE :

  * It MUST stop adding any new messages which match the Topic Filters, for delivery to the Client [MQTT-3.10.4-2].
  * It MUST complete the delivery of any QoS 1 or QoS 2 messages which match the Topic Filters and it has started to send to the Client [MQTT-3.10.4-3].
  * It MAY continue to deliver any existing messages buffered for delivery to the Client.



Â 

The Server MUST respond to an UNSUBSCRIBE request by sending an UNSUBACK packet [MQTT-3.10.4-4]. The UNSUBACK packet MUST have the same Packet Identifier as the UNSUBSCRIBE packet. Even where no Topic Subscriptions are deleted, the Server MUST respond with an UNSUBACK [MQTT-3.10.4-5].

Â 

If a Server receives an UNSUBSCRIBE packet that contains multiple Topic Filters, it MUST process that packet as if it had received a sequence of multiple UNSUBSCRIBE packets, except that it sends just one UNSUBACK response [MQTT-3.10.4-6].

Â 

If a Topic Filter represents a Shared Subscription, this Session is detached from the Shared Subscription.Â If this Session was the only Session that the Shared Subscription was associated with, the Shared Subscription is deleted. Refer to [section 4.8.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Shared_Subscriptions) for a description of Shared Subscription handling.

Â 

##  3.11 UNSUBACK Unsubscribe acknowledgement

The UNSUBACK packet is sent by the Server to the Client to confirm receipt of an UNSUBSCRIBE packet.

Â 

###  3.11.1 UNSUBACK Fixed Header

Figure 3.31 UNSUBACK packet Fixed Header

**Â**

**Remaining Length field**

This is the length of the Variable Header plus the length of the Payload, encoded as a Variable Byte Integer.

Â 

###  3.11.2 UNSUBACK Variable Header

The Variable Header of the UNSUBACK Packet the following fields in the order: the Packet Identifier from the UNSUBSCRIBE Packet that is being acknowledged, and Properties. The rules for encoding Properties are described in [section 2.2.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Properties).

Â [](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Figure_3.32_%E2%80%93)

Figure 3.32 UNSUBACK packet Variable Header

Â 

####  3.11.2.1 UNSUBACK Properties

#####  3.11.2.1.1 Property Length

The length of the Properties in the UNSUBACK packet Variable Header encoded as a Variable Byte Integer.

Â 

#####  3.11.2.1.2 Reason String

**31 (0x1F) Byte,** Identifier of the Reason String. 

Followed by the UTF-8 Encoded String representing the reason associated with this response. This Reason String is a human readable string designed for diagnostics and SHOULD NOT be parsed by the Client. 

Â 

The Server uses this value to give additional information to the Client. The Server MUST NOT send this Property if it would increase the size of the UNSUBACK packet beyond the Maximum Packet Size specified by the Client [MQTT-3.11.2-1]. It is a Protocol Error to include the Reason String more than once.

Â 

#####  3.11.2.1.3 User Property

**38 (0x26) Byte,** Identifier of the User Property.

Followed by UTF-8 String Pair. This property can be used to provide additional diagnostic or other information. The Server MUST NOT send this property if it would increase the size of the UNSUBACK packet beyond the Maximum Packet Size specified by the Client [MQTT-3.11.2-2]. The User Property is allowed to appear multiple times to represent multiple name, value pairs. The same name is allowed to appear more than once.

Â 

###  3.11.3 UNSUBACK Payload

The Payload contains a list of Reason Codes. Each Reason Code corresponds to a Topic Filter in the UNSUBSCRIBE packet being acknowledged. The order of Reason Codes in the UNSUBACK packet MUST match the order of Topic Filters in the UNSUBSCRIBE packet [MQTT-3.11.3-1].

Â 

The values for the one byte unsigned Unsubscribe Reason Codes are shown below. The Server sending an UNSUBACK packet MUST use one of the Unsubscribe Reason Code values for each Topic Filter received [MQTT-3.11.3-2].

Â 

Table 3â9 - Unsubscribe Reason Codes

Â 

**Non-normative comment**

There is always one Reason Code for each Topic Filter in the corresponding UNSUBSCRIBE packet. If the Reason Code is not specific to a Topic Filters (such as 0x91 (Packet Identifier in use)) it is set for each Topic Filter.

Â 

##  3.12 PINGREQ PING request

The PINGREQ packet is sent from a Client to the Server. It can be used to: 

Â Â Â Â Â Â Â Â Indicate to the Server that the Client is alive in the absence of any other MQTT Control Packets being sent from the Client to the Server.

Â Â Â Â Â Â Â Â Request that the Server responds to confirm that it is alive.

Â Â Â Â Â Â Â Â Exercise the network to indicate that the Network Connection is active.

Â 

This packet is used in Keep Alive processing. Refer to [section 3.1.2.10](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Keep_Alive_1) for more details.

Â 

###  3.12.1 PINGREQ Fixed Header

Figure 3.33 PINGREQ packet Fixed Header

Â 

###  3.12.2 PINGREQ Variable Header

The PINGREQ packet has no Variable Header.

Â 

###  3.12.3 PINGREQ Payload

The PINGREQ packet has no Payload.

Â 

###  3.12.4 PINGREQ Actions

The Server MUST send a PINGRESP packet in response to a PINGREQ packet [MQTT-3.12.4-1].

Â 

##  3.13 PINGRESP PING response

A PINGRESP Packet is sent by the Server to the Client in response to a PINGREQ packet. It indicates that the Server is alive.

Â 

This packet is used in Keep Alive processing. Refer to [section 3.1.2.10](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Keep_Alive_1) for more details.

Â 

###  3.13.1 PINGRESP Fixed Header

Figure 3.34 PINGRESP packet Fixed Header

Â 

###  3.13.2 PINGRESP Variable Header

The PINGRESP packet has no Variable Header.

Â 

###  3.13.3 PINGRESP Payload

The PINGRESP packet has no Payload.

Â 

###  3.13.4 PINGRESP Actions

The Client takes no action on receiving this packet

Â 

##  3.14 DISCONNECT Disconnect notification

The DISCONNECT packet is the final MQTT Control Packet sent from the Client or the Server. It indicates the reason why the Network Connection is being closed. The Client or Server MAY send a DISCONNECT packet before closing the Network Connection. If the Network Connection is closed without the Client first sending a DISCONNECT packet with Reason Code 0x00 (Normal disconnection) and the Connection has a Will Message, the Will Message is published. Refer to [section 3.1.2.5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc479576982) for further details.

Â 

A Server MUST NOT send a DISCONNECT until after it has sent a CONNACK with Reason Code of less than 0x80 [MQTT-3.14.0-1].

Â 

###  3.14.1 DISCONNECT Fixed Header

Figure 3.35 DISCONNECT packet Fixed Header

The Client or Server MUST validate that reserved bits are set to 0. If they are not zero it sends a DISCONNECT packet with a Reason code of 0x81 (Malformed Packet) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) [MQTT-3.14.1-1].

Â 

**Remaining Length field**

This is the length of the Variable Header encoded as a Variable Byte Integer.

Â 

###  3.14.2 DISCONNECT Variable Header

The Variable Header of the DISCONNECT Packet contains the following fields in the order: Disconnect Reason Code, and Properties. The rules for encoding Properties are described in [section 2.2.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Properties).

Â 

####  3.14.2.1 Disconnect Reason Code

Byte 1 in the Variable Header is the Disconnect Reason Code. If the Remaining Length is less than 1 the value of 0x00 (Normal disconnection) is used.

Â 

The values for the one byte unsigned Disconnect Reason Code field are shown below.

Â 

Table 3â10 Disconnect Reason Code values

Â 

The Client or Server sending the DISCONNECT packet MUST use one of the DISCONNECT Reason Code values [MQTT-3.14.2-1]. The Reason Code and Property Length can be omitted if the Reason Code is 0x00 (Normal disconnecton) and there are no Properties. In this case the DISCONNECT has a Remaining Length of 0.

Â 

**Non-normative comment**

The DISCONNECT packet is used to indicate the reason for a disconnect for cases where there is no acknowledge packet (such as a QoS 0 publish) or when the Client or Server is unable to continue processing the Connection. 

Â 

**Non-normative comment**

The information can be used by the Client to decide whether to retry the connection, and how long it should wait before retrying the connection.

Â 

####  3.14.2.2 DISCONNECT Properties

#####  3.14.2.2.1 Property Length

The length of Properties in the DISCONNECT packet Variable Header encoded as a Variable Byte Integer. If the Remaining Length is less than 2, a value of 0 is used.

Â 

#####  3.14.2.2.2 Session Expiry Interval

**17 (0x11) Byte,** Identifier of the Session Expiry Interval.

Followed by the Four Byte Integer representing the Session Expiry Interval in seconds. It is a Protocol Error to include the Session Expiry Interval more than once.

Â 

If the Session Expiry Interval is absent, the Session Expiry Interval in the CONNECT packet is used.

Â 

The Session Expiry Interval MUST NOT be sent on a DISCONNECT by the Server [MQTT-3.14.2-2].

Â 

If the Session Expiry Interval in the CONNECT packet was zero, then it is a Protocol Error to set a non-zero Session Expiry Interval in the DISCONNECT packet sent by the Client. If such a non-zero Session Expiry Interval is received by the Server, it does not treat it as a valid DISCONNECT packet. The Server uses DISCONNECT with Reason Code 0x82 (Protocol Error) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors). 

Â 

#####  3.14.2.2.3 Reason String

**31 (0x1F) Byte,** Identifier of the Reason String. 

Followed by the UTF-8 Encoded String representing the reason for the disconnect. This Reason String is human readable, designed for diagnostics and SHOULD NOT be parsed by the receiver. 

Â 

The sender MUST NOT send this Property if it would increase the size of the DISCONNECT packet beyond the Maximum Packet Size specified by the receiver [MQTT-3.14.2-3]. It is a Protocol Error to include the Reason String more than once.

Â 

#####  3.14.2.2.4 User Property

**38 (0x26) Byte,** Identifier of the User Property.****

Followed by UTF-8 String Pair. This property may be used to provide additional diagnostic or other information. The sender MUST NOT send this property if it would increase the size of the DISCONNECT packet beyond the Maximum Packet Size specified by the receiver [MQTT-3.14.2-4]. The User Property is allowed to appear multiple times to represent multiple name, value pairs. The same name is allowed to appear more than once.

Â 

#####  3.14.2.2.5 Server Reference

**28 (0x1C) Byte,** Identifier of the Server Reference. 

Followed by a UTF-8 Encoded String which can be used by the Client to identify another Server to use. It is a Protocol Error to include the Server Reference more than once.

Â 

The Server sends DISCONNECT including a Server Reference and Reason Code 0x9C (Use another server) or 0x9D (Server moved) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors).

Â 

Refer to [section 4.11](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Server_redirection) Server Redirection for information about how Server Reference is used.

Â 

Figure 3â24 DISCONNECT packet Variable Header non-normative example

Â 

###  3.14.3 DISCONNECT Payload

The DISCONNECT packet has no Payload.

Â 

###  3.14.4 DISCONNECT Actions

After sending a DISCONNECT packet the sender:

  * MUST NOT send any more MQTT Control Packets on that Network Connection [MQTT-3.14.4-1].
  * MUST close the Network Connection [MQTT-3.14.4-2].



Â 

On receipt of DISCONNECT with a Reason Code of 0x00 (Success) the Server:

  * MUST discard any Will Message associated with the current Connection without publishing it [MQTT-3.14.4-3], as described in [section 3.1.2.5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc479576982).



Â 

On receipt of DISCONNECT, the receiver:

  * SHOULD close the Network Connection.



Â 

##  3.15 AUTH Authentication exchange

An AUTH packet is sent from Client to Server or Server to Client as part of an extended authentication exchange, such as challenge / response authentication. It is a Protocol Error for the Client or Server to send an AUTH packet if the CONNECT packet did not contain the same Authentication Method.

Â 

###  3.15.1 AUTH Fixed Header

Figure 3.35 AUTH packet Fixed Header

Â 

Bits 3,2,1 and 0 of the Fixed Header of the AUTH packet are reserved and MUST all be set to 0. The Client or Server MUST treat any other value as malformed and close the Network Connection [MQTT-3.15.1-1].

Â 

**Remaining Length field**

This is the length of the Variable Header encoded as a Variable Byte Integer.

Â 

###  3.15.2 AUTH Variable Header

The Variable Header of the AUTH Packet contains the following fields in the order: Authenticate Reason Code, and Properties. The rules for encoding Properties are described in [section 2.2.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Properties).

Â 

####  3.15.2.1 Authenticate Reason Code

Byte 0 in the Variable Header is the Authenticate Reason Code. The values for the one byte unsigned Authenticate Reason Code field are shown below. The sender of the AUTH Packet MUST use one of the Authenticate Reason Codes [MQTT-3.15.2-1].

Â 

Table 3â11 Authenticate Reason Codes

The Reason Code and Property Length can be omitted if the Reason Code is 0x00 (Success) and there are no Properties. In this case the AUTH has a Remaining Length of 0.

Â 

####  3.15.2.2 AUTH Properties

#####  3.15.2.2.1 Property Length

The length of Properties in the AUTH packet Variable Header encoded as a Variable Byte Integer.

Â 

#####  3.15.2.2.2 Authentication Method

**21 (0x15) Byte** , Identifier of the Authentication Method. 

Followed by a UTF-8 Encoded String containing the name of the authentication method. It is a Protocol Error to omit the Authentication Method or to include it more than once. Refer to [section 4.12](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Enhanced_authentication) for more information about extended authentication.

Â 

#####  3.15.2.2.3 Authentication Data

**22 (0x16) Byte** , Identifier of the Authentication Data. 

Followed by Binary Data containing authentication data. It is a Protocol Error to include Authentication Data more than once. The contents of this data are defined by the authentication method. Refer to [section 4.12](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Enhanced_authentication) for more information about extended authentication.

Â 

#####  3.15.2.2.4 Reason String

**31 (0x1F) Byte,** Identifier of the Reason String. 

Followed by the UTF-8 Encoded String representing the reason for the disconnect. This Reason String is human readable, designed for diagnostics and SHOULD NOT be parsed by the receiver. 

Â 

The sender MUST NOT send this property if it would increase the size of the AUTH packet beyond the Maximum Packet Size specified by the receiver [MQTT-3.15.2-2]. It is a Protocol Error to include the Reason String more than once.

Â 

#####  3.15.2.2.5 User Property

**38 (0x26) Byte,** Identifier of the User Property.

Followed by UTF-8 String Pair. This property may be used to provide additional diagnostic or other information. The sender MUST NOT send this property if it would increase the size of the AUTH packet beyond the Maximum Packet Size specified by the receiver [MQTT-3.15.2-3]. The User Property is allowed to appear multiple times to represent multiple name, value pairs. The same name is allowed to appear more than once.

Â 

###  3.15.3 AUTH Payload

The AUTH packet has no Payload.

Â 

###  3.15.4 AUTH Actions

Refer to [section 4.12](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Enhanced_authentication) for more information about extended authentication.

#  4Â Â Â Â Â Operational behavior

##  4.1 Session State

In order to implement QoS 1 and QoS 2 protocol flows the Client and Server need to associate state with the Client Identifier, this is referred to as the Session State. The Server also stores the subscriptions as part of the Session State.

Â 

The session can continue across a sequence of Network Connections. It lasts as long as the latest Network Connection plus the Session Expiry Interval.

Â 

The Session State in the Client consists of:

Â Â Â Â Â Â Â Â QoS 1 and QoS 2 messages which have been sent to the Server, but have not been completely acknowledged.

Â Â Â Â Â Â Â Â QoS 2 messages which have been received from the Server, but have not been completely acknowledged.

Â 

The Session State in the Server consists of:

Â Â Â Â Â Â Â Â The existence of a Session, even if the rest of the Session State is empty.

Â Â Â Â Â Â Â Â The Clients subscriptions, including any Subscription Identifiers.

Â Â Â Â Â Â Â Â QoS 1 and QoS 2 messages which have been sent to the Client, but have not been completely acknowledged.

Â Â Â Â Â Â Â Â QoS 1 and QoS 2 messages pending transmission to the Client and OPTIONALLY QoS 0 messages pending transmission to the Client.

Â Â Â Â Â Â Â Â QoS 2 messages which have been received from the Client, but have not been completely acknowledged.The Will Message and the Will Delay Interval

Â Â Â Â Â Â Â Â If the Session is currently not connected, the time at which the Session will end and Session State will be discarded.

Â 

Retained messages do not form part of the Session State in the Server, they are not deleted as a result of a Session ending.

Â 

###  4.1.1 Storing Session State

The Client and Server MUST NOT discard the Session State while the Network Connection is open [MQTT-4.1.0-1]. The Server MUST discard the Session State when the Network Connection is closed and the Session Expiry Interval has passed [MQTT-4.1.0-2].

Â 

**Non-normative comment**

The storage capabilities of Client and Server implementations will of course have limits in terms of capacity and may be subject to administrative policies. Stored Session State can be discarded as a result of an administrator action, including an automated response to defined conditions. This has the effect of terminating the Session. These actions might be prompted by resource constraints or for other operational reasons. It is possible that hardware or software failures may result in loss or corruption of Session State stored by the Client or Server. It is prudent to evaluate the storage capabilities of the Client and Server to ensure that they are sufficient.

**Â**

###  4.1.2 Session State non-normative examples

For example, an electricity meter reading solution might use QoS 1 messages to protect the readings against loss over the network. The solution developer might have determined that the power supply is sufficiently reliable that, in this case, the data in the Client and Server can be stored in volatile memory without too much risk of its loss.

Â 

Conversely a parking meter payment application provider might decide that the payment messages should never be lost due to a network or Client failure. Thus, they require that all data be written to non-volatile memory before it is transmitted across the network.

Â 

##  4.2 Network Connections

The MQTT protocol requires an underlying transport that provides an ordered, lossless, stream of bytes from the Client to Server and Server to Client. This specification does not require the support of any specific transport protocol. A Client or Server MAY support any of the transport protocols listed here, or any other transport protocol that meets the requirements of this [section](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Network_Connections).

Â 

A Client or Server MUST support the use of one or more underlying transport protocols that provide an ordered, lossless, stream of bytes from the Client to Server and Server to Client [MQTT-4.2-1].

**Â**

**Non-normative comment**

TCP/IP as defined in [[RFC0793]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC793) can be used for MQTT v5.0. The following transport protocols are also suitable:

Â Â Â Â Â Â Â Â TLS [[RFC5246]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246)

Â Â Â Â Â Â Â Â WebSocket [[RFC6455]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC6455) [](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC6455)

Â 

**Non-normative comment**

TCP ports 8883 and 1883 are registered with IANA for MQTT TLS and non-TLS communication respectively.

Â 

**Non-normative comment**

Connectionless network transports such as [User Datagram Protocol](https://en.wikipedia.org/wiki/User_Datagram_Protocol) (UDP) are not suitable on their own because they might lose or reorder data. 

Â 

##  4.3 Quality of Service levels and protocol flows

MQTT delivers Application Messages according to the Quality of Service (QoS) levels defined in the following sections. The delivery protocol is symmetric, in the description below the Client and Server can each take the role of either sender or receiver. The delivery protocol is concerned solely with the delivery of an application message from a single sender to a single receiver. When the Server is delivering an Application Message to more than one Client, each Client is treated independently. The QoS level used to deliver an Application Message outbound to the Client could differ from that of the inbound Application Message.

Â 

###  4.3.1 QoS 0: At most once delivery

The message is delivered according to the capabilities of the underlying network. No response is sent by the receiver and no retry is performed by the sender. The message arrives at the receiver either once or not at all. 

Â 

In the QoS 0 delivery protocol, the sender

Â Â Â Â Â Â Â Â MUST send a PUBLISH packet with QoS 0 and DUP flag set to 0 [MQTT-4.3.1-1].

Â 

In the QoS 0 delivery protocol, the receiver

Â Â Â Â Â Â Â Â Accepts ownership of the message when it receives the PUBLISH packet.

Â 

Figure 4.1 QoS 0 protocol flow diagram, non-normative example

Â 

###  4.3.2 QoS 1: At least once delivery

This Quality of Service level ensures that the message arrives at the receiver at least once. A QoS 1 PUBLISH packet has a Packet Identifier in its Variable Header and is acknowledged by a PUBACK packet. [Section 2.2.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc358219870) provides more information about Packet Identifiers.

**Â**

In the QoS 1 delivery protocol, the sender

Â Â Â Â Â Â Â Â MUST assign an unused Packet Identifier each time it has a new Application Message to publish [MQTT-4.3.2-1]. 

Â Â Â Â Â Â Â Â MUST send a PUBLISH packet containing this Packet Identifier with QoS 1 and DUP flag set to 0 [MQTT-4.3.2-2].

Â Â Â Â Â Â Â Â MUST treat the PUBLISH packet as unacknowledged until it has received the corresponding PUBACK packet from the receiver. Refer to [section 4.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Message_delivery_retry) for a discussion of unacknowledged messages [MQTT-4.3.2-3].

Â 

The Packet Identifier becomes available for reuse once the sender has received the PUBACK packet.

Â 

Note that a sender is permitted to send further PUBLISH packets with different Packet Identifiers while it is waiting to receive acknowledgements.

Â 

In the QoS 1 delivery protocol, the receiver

  * MUST respond with a PUBACK packet containing the Packet Identifier from the incoming PUBLISH packet, having accepted ownership of the Application Message [MQTT-4.3.2-4]. 
  * After it has sent a PUBACK packet the receiver MUST treat any incoming PUBLISH packet that contains the same Packet Identifier as being a new Application Message, irrespective of the setting of its DUP flag [MQTT-4.3.2-5].



Â 

Figure 4.2 QoS 1 protocol flow diagram, non-normative example

Â 

1 The receiver does not need to complete delivery of the Application Message before sending the PUBACK. When its original sender receives the PUBACK packet, ownership of the Application Message is transferred to the receiver.

Â 

###  4.3.3 QoS 2: Exactly once delivery

This is the highest Quality of Service level, for use when neither loss nor duplication of messages are acceptable. There is an increased overhead associated with QoS 2.

Â 

A QoS 2 message has a Packet Identifier in its Variable Header. [Section 2.2.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc358219870) provides more information about Packet Identifiers. The receiver of a QoS 2 PUBLISH packet acknowledges receipt with a two-step acknowledgement process. 

Â 

In the QoS 2 delivery protocol, the sender:

  * MUST assign an unused Packet Identifier when it has a new Application Message to publish [MQTT-4.3.3-1].
  * MUST send a PUBLISH packet containing this Packet Identifier with QoS 2 and DUP flag set to 0 [MQTT-4.3.3-2].
  * MUST treat the PUBLISH packet as unacknowledged until it has received the corresponding PUBREC packet from the receiver [MQTT-4.3.3-3]. Refer to [section 4.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Figure_4.3_%E2%80%93) for a discussion of unacknowledged messages.
  * MUST send a PUBREL packet when it receives a PUBREC packet from the receiver with a Reason Code value less than 0x80. This PUBREL packet MUST contain the same Packet Identifier as the original PUBLISH packet [MQTT-4.3.3-4].
  * MUST treat the PUBREL packet as unacknowledged until it has received the corresponding PUBCOMP packet from the receiver [MQTT-4.3.3-5].
  * MUST NOT re-send the PUBLISH once it has sent the corresponding PUBREL packet [MQTT-4.3.3-6].
  * MUST NOT apply Message expiry if a PUBLISH packet has been sent [MQTT-4.3.3-7].



Â 

The Packet Identifier becomes available for reuse once the sender has received the PUBCOMP packet or a PUBREC with a Reason Code of 0x80 or greater. 

Â 

Note that a sender is permitted to send further PUBLISH packets with different Packet Identifiers while it is waiting to receive acknowledgements, subject to flow control as described in [section 4.9](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Flow_Control).

Â 

In the QoS 2 delivery protocol, the receiver:

  * MUST respond with a PUBREC containing the Packet Identifier from the incoming PUBLISH packet, having accepted ownership of the Application Message [MQTT-4.3.3-8].
  * If it has sent a PUBREC with a Reason Code of 0x80 or greater, the receiver MUST treat any subsequent PUBLISH packet that contains that Packet Identifier as being a new Application Message [MQTT-4.3.3-9].
  * Until it has received the corresponding PUBREL packet, the receiver MUST acknowledge any subsequent PUBLISH packet with the same Packet Identifier by sending a PUBREC. It MUST NOT cause duplicate messages to be delivered to any onward recipients in this case [MQTT-4.3.3-10]. 
  * MUST respond to a PUBREL packet by sending a PUBCOMP packet containing the same Packet Identifier as the PUBREL [MQTT-4.3.3-11].
  * After it has sent a PUBCOMP, the receiver MUST treat any subsequent PUBLISH packet that contains that Packet Identifier as being a new Application Message [MQTT-4.3.3-12].
  * MUST continue the QoS 2 acknowledgement sequence even if it has applied message expiry [MQTT-4.3.3-13].



Â 

##  4.4 Message delivery retry

When a Client reconnects with Clean Start set to 0 and a session is present, both the Client and Server MUST resend any unacknowledged PUBLISH packets (where QoS > 0) and PUBREL packets using their original Packet Identifiers. This is the only circumstance where a Client or Server is REQUIRED to resend messages. Clients and Servers MUST NOT resend messages at any other time [MQTT-4.4.0-1].

Â 

If PUBACK or PUBREC is received containing a Reason Code of 0x80 or greater the corresponding PUBLISH packet is treated as acknowledged, and MUST NOT be retransmitted [MQTT-4.4.0-2]. 

Â 

Figure 4.3 QoS 2 protocol flow diagram, non-normative example

Â 

1 The receiver does not need to complete delivery of the Application Message before sending the PUBREC or PUBCOMP. When its original sender receives the PUBREC packet, ownership of the Application Message is transferred to the receiver. However, the receiver needs to perform all checks for conditions which might result in a forwarding failure (e.g. quota exceeded, authorization, etc.) before accepting ownership. The receiver indicates success or failure using the appropriate Reason Code in the PUBREC.

Â 

##  4.5 Message receipt

When a Server takes ownership of an incoming Application Message it MUST add it to the Session State for those Clients that have matching Subscriptions [MQTT-4.5.0-1]. Matching rules are defined in [section 4.7.](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Topic_Names_and)

Â 

Under normal circumstances Clients receive messages in response to Subscriptions they have created. A Client could also receive messages that do not match any of its explicit Subscriptions. This can happen if the Server automatically assigned a subscription to the Client. A Client could also receive messages while an UNSUBSCRIBE operation is in progress. The Client MUST acknowledge any Publish packet it receives according to the applicable QoS rules regardless of whether it elects to process the Application Message that it contains [MQTT-4.5.0-2].

Â 

##  4.6 Message ordering

The following these rules apply to the Client when implementing the protocol flows defined in [section 4.3.](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Quality_of_Service)

  * When the Client re-sends any PUBLISH packets, it MUST re-send them in the order in which the original PUBLISH packets were sent (this applies to QoS 1 and QoS 2 messages) [MQTT-4.6.0-1]
  * The Client MUST send PUBACK packets in the order in which the corresponding PUBLISH packets were received (QoS 1 messages) [MQTT-4.6.0-2]
  * The Client MUST send PUBREC packets in the order in which the corresponding PUBLISH packets were received (QoS 2 messages) [MQTT-4.6.0-3]
  * The Client MUST send PUBREL packets in the order in which the corresponding PUBREC packets were received (QoS 2 messages) [MQTT-4.6.0-4]



Â 

An Ordered Topic is a Topic where the Client can be certain that the Application Messages in that Topic from the same Client and at the same QoS are received are in the order they were published. When a Server processes a message that has been published to an Ordered Topic, it MUST send PUBLISH packets to consumers (for the same Topic and QoS) in the order that they were received from any given Client [MQTT-4.6.0-5]. This is addition to the rules listed above.

Â 

By default, a Server MUST treat every Topic as an Ordered Topic when it is forwarding messages on Nonâshared Subscriptions. [MQTT-4.6.0-6]. A Server MAY provide an administrative or other mechanism to allow one or more Topics to not be treated as an Ordered Topic.

Â 

**Non-normative comment**

The rules listed above ensure that when a stream of messages is published and subscribed to an Ordered Topic with QoS 1, the final copy of each message received by the subscribers will be in the order that they were published. If the message is re-sent the duplicate message can be received after one of the earlier messages is received. For example, a publisher might send messages in the order 1,2,3,4 but the subscriber might receive them in the order 1,2,3,2,3,4 if there is a network disconnection after message 3 has been sent.

Â 

If both Client and Server set Receive Maximum to 1, they make sure that no more than one message is in-flight at any one time. In this case no QoS 1 message will be received after any later one even on re-connection. For example a subscriber might receive them in the order 1,2,3,3,4 but not 1,2,3,2,3,4. Refer to [section 4.9](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Flow_Control) Flow Control for details of how the Receive Maximum is used.

Â 

##  4.7 Topic Names and Topic Filters

###  4.7.1 Topic wildcards

The topic level separator is used to introduce structure into the Topic Name. If present, it divides the Topic Name into multiple topic levels .

A subscription s Topic Filter can contain special wildcard characters, which allow a Client to subscribe to multiple topics at once.

The wildcard characters can be used in Topic Filters, but MUST NOT be used within a Topic Name [MQTT-4.7.0-1].

Â 

####  4.7.1.1 Topic level separator

The forward slash ( / U+002F) is used to separate each level within a topic tree and provide a hierarchical structure to the Topic Names. The use of the topic level separator is significant when either of the two wildcard characters is encountered in Topic Filters specified by subscribing Clients. Topic level separators can appear anywhere in a Topic Filter or Topic Name. Adjacent Topic level separators indicate a zero-length topic level. 

Â 

####  4.7.1.2 Multi-level wildcard

The number sign ( # U+0023) is a wildcard character that matches any number of levels within a topic. The multi-level wildcard represents the parent and any number of child levels. The multi-level wildcard character MUST be specified either on its own or following a topic level separator. In either case it MUST be the last character specified in the Topic Filter [MQTT-4.7.1-1].

Â 

**Non-normative comment**

For example, if a Client subscribes to sport/tennis/player1/# , it would receive messages published using these Topic Names:

Â Â Â Â Â Â Â Â  sport/tennis/player1 

Â Â Â Â Â Â Â Â  sport/tennis/player1/ranking

Â Â Â Â Â Â Â Â  sport/tennis/player1/score/wimbledon 

Â 

**Non-normative comment**

Â Â Â Â Â Â Â Â  sport/# also matches the singular sport , since # includes the parent level. 

Â Â Â Â Â Â Â Â  # is valid and will receive every Application Message

Â Â Â Â Â Â Â Â  sport/tennis/# is valid 

Â Â Â Â Â Â Â Â  sport/tennis# is not valid

Â Â Â Â Â Â Â Â  sport/tennis/#/ranking is not valid

Â 

####  4.7.1.3 Single-level wildcard

The plus sign ( + U+002B) is a wildcard character that matches only one topic level. 

Â 

The single-level wildcard can be used at any level in the Topic Filter, including first and last levels. Where it is used, it MUST occupy an entire level of the filter [MQTT-4.7.1-2]. It can be used at more than one level in the Topic Filter and can be used in conjunction with the multi-level wildcard.

Â 

**Non-normative comment**

For example, sport/tennis/+ matches sport/tennis/player1 and sport/tennis/player2 , but not sport/tennis/player1/ranking . Also, because the single-level wildcard matches only a single level, sport/+ does not match sport but it does match sport/ .

Â Â Â Â Â Â Â Â Â + is valid

Â Â Â Â Â Â Â Â  +/tennis/# is valid

Â Â Â Â Â Â Â Â  sport+ is not valid

Â Â Â Â Â Â Â Â  sport/+/player1 is valid

Â Â Â Â Â Â Â Â  /finance matches +/+ and /+ , but not + 

Â 

### 4.7.2 Â Topics beginning with $

The Server MUST NOT match Topic Filters starting with a wildcard character (# or +) with Topic Names beginning with a $ character [MQTT-4.7.2-1]. The Server SHOULD prevent Clients from using such Topic Names to exchange messages with other Clients. Server implementations MAY use Topic Names that start with a leading $ character for other purposes.

Â 

**Non-normative comment**

Â Â Â Â Â Â Â Â $SYS/ has been widely adopted as a prefix to topics that contain Server-specific information or control APIs

Â Â Â Â Â Â Â Â Applications cannot use a topic with a leading $ character for their own purposes

Â 

**Non-normative comment**

Â Â Â Â Â Â Â Â A subscription to # will not receive any messages published to a topic beginning with a $

Â Â Â Â Â Â Â Â A subscription to +/monitor/Clients will not receive any messages published to $SYS/monitor/Clients 

Â Â Â Â Â Â Â Â A subscription to $SYS/# will receive messages published to topics beginning with $SYS/ 

Â Â Â Â Â Â Â Â A subscription to $SYS/monitor/+ will receive messages published to $SYS/monitor/Clients 

Â Â Â Â Â Â Â Â For a Client to receive messages from topics that begin with $SYS/ and from topics that don t begin with a $, it has to subscribe to both # and $SYS/# 

Â 

###  4.7.3 Topic semantic and usage

The following rules apply to Topic Names and Topic Filters:

Â Â Â Â Â Â Â Â All Topic Names and Topic Filters MUST be at least one character long [MQTT-4.7.3-1]

Â Â Â Â Â Â Â Â Topic Names and Topic Filters are case sensitive 

Â Â Â Â Â Â Â Â Topic Names and Topic Filters can include the space character

Â Â Â Â Â Â Â Â A leading or trailing / creates a distinct Topic Name or Topic Filter 

Â Â Â Â Â Â Â Â A Topic Name or Topic Filter consisting only of the / character is valid

Â Â Â Â Â Â Â Â Topic Names and Topic Filters MUST NOT include the null character (Unicode U+0000) [[Unicode]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#Unicode) [MQTT-4.7.3-2][](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#Unicode)

Â Â Â Â Â Â Â Â Topic Names and Topic Filters are UTF-8 Encoded Strings; they MUST NOT encode to more than 65,535 bytes [MQTT-4.7.3-3]. Refer to [section 1.5.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_UTF-8_Encoded_String).

Â 

There is no limit to the number of levels in a Topic Name or Topic Filter, other than that imposed by the overall length of a UTF-8 Encoded String.

Â 

When it performs subscription matching the Server MUST NOT perform any normalization of Topic Names or Topic Filters, or any modification or substitution of unrecognized characters [MQTT-4.7.3-4]. Each non-wildcarded level in the Topic Filter has to match the corresponding level in the Topic Name character for character for the match to succeed.

Â 

**Non-normative comment**

The UTF-8 encoding rules mean that the comparison of Topic Filter and Topic Name could be performed either by comparing the encoded UTF-8 bytes, or by comparing decoded Unicode characters

Â 

**Non-normative comment**

Â Â Â Â Â Â Â Â  ACCOUNTS and Accounts are two different Topic Names

Â Â Â Â Â Â Â Â  Accounts payable is a valid Topic Name

Â Â Â Â Â Â Â Â  /finance is different from finance 

**Â**

An Application Message is sent to each Client Subscription whose Topic Filter matches the Topic Name attached to an Application Message. The topic resource MAY be either predefined in the Server by an administrator or it MAY be dynamically created by the Server when it receives the first subscription or an Application Message with that Topic Name. The Server MAY also use a security component to authorize particular actions on the topic resource for a given Client.

Â 

##  4.8 Subscriptions

MQTT provides two kinds of Subscription, Shared and Nonâshared.

Â 

**Non-normative comment**

In earlier versions of MQTT all Subscriptions are Nonâshared.

Â 

###  4.8.1 Nonâshared Subscriptions

A Nonâshared Subscription is associated only with the MQTT Session that created it. Each Subscription includes a Topic Filter, indicating the topic(s) for which messages are to be delivered on that Session, and Subscription Options. The Server is responsible for collecting messages that match the filter and transmitting them on the Session's MQTT connection if and when that connection is active.

Â 

A Session cannot have more than one Nonâshared Subscription with the same Topic Filter, so the Topic Filter can be used as a key to identify the subscription within that Session.

Â 

If there are multiple Clients, each with its own Nonâshared Subscription to the same Topic, each Client gets its own copy of the Application Messages that are published on that Topic. This means that the Nonâshared Subscriptions cannot be used to load-balance Application Messages across multiple consuming Clients as in such cases every message is delivered to every subscribing Client.

Â 

###  4.8.2 Shared Subscriptions

A Shared Subscription can be associated with multiple subscribing MQTT Sessions. Like a Nonâshared Subscription, it has a Topic Filter and Subscription Options; however, a publication that matches its Topic Filter is only sent to one of its subscribing Sessions. Shared Subscriptions are useful where several consuming Clients share the processing of the publications in parallel.

Â 

A Shared Subscription is identified using a special style of Topic Filter. The format of this filter is:

Â 

$share/{ShareName}/{filter}

Â Â Â Â Â Â Â Â Â $share is a literal string that marks the Topic Filter as being a Shared Subscription Topic Filter.

Â Â Â Â Â Â Â Â Â {ShareName} is a character string that does not include "/", "+" or "#"

Â Â Â Â Â Â Â Â Â {filter} The remainder of the string has the same syntax and semantics as a Topic Filter in a non-shared subscription. Refer to [section 4.7](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Topic_Names_and).

Â Â Â Â Â Â Â Â Â 

A Shared Subscription's Topic Filter MUST start with $share/ and MUST contain a ShareName that is at least one character long [MQTT-4.8.2-1]. The ShareName MUST NOT contain the characters "/", "+" or "#", but MUST be followed by a "/" character. This "/" character MUST be followed by a Topic Filter [MQTT-4.8.2-2] as described in [section 4.7](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Topic_Names_and).

Â 

**Non-normative comment**

Shared Subscriptions are defined at the scope of the MQTT Server, rather than of a Session. A ShareName is included in the Shared Subscription's Topic Filter so that there can be more than one Shared Subscription on a Server that has the same {filter} component. Typically, applications use the ShareName to represent the group of subscribing Sessions that are sharing the subscription.

Â 

Examples:

Â Â Â Â Â Â Â Â Shared subscriptions "$share/consumer1/sport/tennis/+" and "$share/consumer2/sport/tennis/+" are distinct shared subscriptions and so can be associated with different groups of Sessions. Both of them match the same topics as a non-shared subscription to sport/tennis/+ .

Â 

If a message were to be published that matches sport/tennis/+ then a copy would be sent to exactly one of the Sessions subscribed to $share/consumer1/sport/tennis/+ , a separate copy of the message would be sent to exactly one of the Sessions subscribed to $share/consumer2/sport/tennis/+ and further copies would be sent to any Clients with non-shared subscriptions to sport/tennis/+

Â 

Â Â Â Â Â Â Â Â Shared subscription "$share/consumer1//finance" matches the same topics as a non-shared subscription to /finance.

Â 

A Shared Subscription is created by using a Shared Subscription Topic Filter in a SUBSCRIBE request. So long as only one Session subscribes to a particular Shared Subscription, the shared subscription behaves like a non-shared subscription, except that:

Â 

Â Â Â Â Â Â Â Â The $share and {ShareName} portions of the Topic Filter are not taken into account when matching against publications.

Â 

Â Â Â Â Â Â Â Â No Retained Messages are sent to the Session when it first subscribes. It will be sent other matching messages as they are published.

Â 

Once a Shared Subscription exists, it is possible for other Sessions to subscribe with the same Shared Subscription Topic Filter. The new Session is associated with the Shared Subscription as an additional subscriber. Retained messages are not sent to this new subscriber. Each subsequent Application Message that matches the Shared Subscription is now sent to one and only one of the Sessions that are subscribed to the Shared Subscription.

Â 

A Session can explicitly detach itself from a Shared Subscription by sending an UNSUBSCRIBE Packet that contains the full Shared Subscription Topic Filter. Sessions are also detached from the Shared Subscription when they terminate.

Â 

A Shared Subscription lasts for as long as it is associated with at least one Session (i.e. a Session that has issued a successful SUBSCRIBE request to its Topic Filter and that has not completed a corresponding UNSUBSCRIBE). A Shared Subscription survives when the Session that originally created it unsubscribes, unless there are no other Sessions left when this happens. A Shared Subscription ends, and any undelivered messages associated with it are deleted, when there are no longer any Sessions subscribed to it.

Â 

Notes on Shared Subscriptions

Â Â Â Â Â Â Â Â If there's more than one Session subscribed to the Shared Subscription, the Server implementation is free to choose, on a message by message basis, which Session to use and what criteria it uses to make this selection.

Â Â Â Â Â Â Â Â Different subscribing Clients are permitted to ask for different Requested QoS levels in their SUBSCRIBE packets. The Server decides which Maximum QoS to grant to each Client, and it is permitted to grant different Maximum QoS levels to different subscribers. When sending an Application Message to a Client, the Server MUST respect the granted QoS for the Client's subscription [MQTT-4.8.2-3], in the same that it does when sending a message to a âSubscriber.

Â Â Â Â Â Â Â Â If the Server is in the process of sending a QoS 2 message to its chosen subscribing Client and the connection to the Client breaks before delivery is complete, the Server MUST complete the delivery of the message to that Client when it reconnects [MQTT-4.8.2-4] as described in [section 4.3.3](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_QoS_2:_Exactly). If the Client's Session terminates before the Client reconnects, the Server MUST NOT send the Application Message to any other subscribed Client [MQTT-4.8.2-5].

Â Â Â Â Â Â Â Â If the Server is in the process of sending a QoS 1 message to its chosen subscribing Client and the connection to that Client breaks before the Server has received an acknowledgement from the Client, the Server MAY wait for the Client to reconnect and retransmit the message to that Client. If the Client'sSession terminates before the Client reconnects, the Server SHOULD send the Application Message to another Client that is subscribed to the same Shared Subscription. It MAY attempt to send the message to another Client as soon as it loses its connection to the first Client.

Â Â Â Â Â Â Â Â If a Client responds with a PUBACK or PUBREC containing a Reason Code of 0x80 or greater to a PUBLISH packet from the Server, the Server MUST discard the Application Message and not attempt to send it to any other Subscriber [MQTT-4.8.2-6].

Â Â Â Â Â Â Â Â A Client is permitted to submit a second SUBSCRIBE request to a Shared Subscription on a Session that's already subscribed to that Shared Subscription. For example, it might do this to change the Requested QoS for its subscription or because it was uncertain that the previous subscribe completed before the previous connection was closed. This does not increase the number of times that the Session is associated with the Shared Subscription, so the Session will leave the Shared Subscription on its first UNSUBSCRIBE.

Â Â Â Â Â Â Â Â Each Shared Subscription is independent from any other. It is possible to have two Shared Subscriptions with overlapping filters. In such cases a message that matches both Shared Subscriptions will be processed separately by both of them. If a Client has a Shared Subscription and a Nonâshared Subscription and a message matches both of them, the Client will receive a copy of the message by virtue of it having the Nonâshared Subscription. A second copy of the message will be delivered to one of the subscribers to the Shared Subscription, and this could result in a second copy being sent to this Client.

Â 

##  4.9 Flow Control

Clients and Servers control the number of unacknowledged PUBLISH packets they receive by using a Receive Maximum value as described in [section 3.1.2.11.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Receive_Maximum) and [section 3.2.2.3.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Receive_Maximum_1). The Receive Maximum establishes a send quota which is used to limit the number of PUBLISH QOS > 0 packets which can be sent without receiving an PUBACK (for QoS 1) or PUBCOMP (for QoS 2). The PUBACK and PUBCOMP replenish the quota in the manner described below. 

Â 

The Client or Server MUST set its initial send quota to a non-zero value not exceeding the Receive Maximum [MQTT-4.9.0-1]. 

Â 

Each time the Client or Server sends a PUBLISH packet at QoS > 0, it decrements the send quota. If the send quota reaches zero, the Client or Server MUST NOT send any more PUBLISH packets with QoS > 0 [MQTT-4.9.0-2]. It MAY continue to send PUBLISH packets with QoS 0, or it MAY choose to suspend sending these as well. The Client and Server MUST continue to process and respond to all other MQTT Control Packets even if the quota is zero [MQTT-4.9.0-3]. 

Â 

The send quota is incremented by 1: 

Â Â Â Â Â Â Â Â Each time a PUBACK or PUBCOMP packet is received, regardless of whether the PUBACK or PUBCOMP carried an error code. 

Â Â Â Â Â Â Â Â Each time a PUBREC packet is received with a Return Code of 0x80 or greater. 

Â 

The send quota is not incremented if it is already equal to the initial send quota. The attempt to increment above the initial send quota might be caused by the re-transmission of a PUBREL packet after a new Network Connection is established. 

Â 

Refer to [section 3.3.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_PUBLISH_Actions) for a description of how Clients and Servers react if they are sent more PUBLISH packets than the Receive Maximum allows. 

Â 

The send quota and Receive Maximum value are not preserved across Network Connections, and are re-initialized with each new Network Connection as described above. They are not part of the session state.

Â 

##  4.10 Request / Response

Some applications or standards might wish to run a Request/Response interaction over MQTT. This version of MQTT includes three properties that can be used for this purpose:

Â Â Â Â Â Â Â Â Response Topic, described in [section 3.3.2.3.5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Response_Topic)

Â Â Â Â Â Â Â Â Correlation Data, described in [section 3.3.2.3.6](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Correlation_Data)

Â Â Â Â Â Â Â Â Request Response Information, described in [section 3.1.2.11.7](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Request_Response_Information)

Â Â Â Â Â Â Â Â Response Information, described in [section 3.2.2.3.14](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Response_Information)

The following non-normative sections describe how these properties can be used. 

Â 

A Client sends a Request Message by publishing an Application Message which has a Response Topic set as described in [section 3.3.2.3.5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc463595993). The Request can include a Correlation Data property as described in [section 3.3.2.3.6](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Correlation_Data).

Â 

###  4.10.1 Basic Request Response (non-normative)

Â Request/Response interaction proceeds as follows:

1.Â Â Â Â An MQTT Client (the Requester) publishes a Request Message to a topic. A Request Message is an Application Message with a Response Topic.

2.Â Â Â Â Another MQTT Client (the Responder) has subscribed to a Topic Filter which matches the Topic Name used when the Request Message was published. As a result, it receives the Request Message. There could be multiple Responders subscribed to this Topic Name or there could be none.

3.Â Â Â Â The Responder takes the appropriate action based on the Request Message, and then publishes a Response Message to the Topic Name in the Response Topic property that was carried in the Request Message.

4.Â Â Â Â In typical usage the Requester has subscribed to the Response Topic and thereby receives the Response Message. However, some other Client might be subscribed to the Response Topic in which case the Response Message will also be received and processed by that Client. As with the Request Message, the topic on which the Response Message is sent could be subscribed to by multiple Clients, or by none.

Â 

If the Request Message contains a Correlation Data property, the Responder copies this property into the Response Message and this is used by the receiver of the Response Message to associate the Response Message with the original request. The Response Message does not include a Response Topic property.

Â 

The MQTT Server forwards the Response Topic and Correlation Data Property in the Request Message and the Correlation Data in the Response Message. The Server treats the Request Message and the Response Message like any other Application Message.

Â 

The Requester normally subscribes to the Response Topic before publishing a Request Message. If there are no subscribers to the Response Topic when the Response Message is sent, the Response Message will not be delivered to any Client.

Â 

The Request Message and Response Message can be of any QoS, and the Responder can be using a Session with a non-zero Session Expiry Interval. It is common to send Request Messages at QoS 0 and only when the Responder is expected to be connected. However, this is not necessary.

Â 

The Responder can use a Shared Subscription to allow for a pool of responding Clients. Note however that when using Shared Subscriptions that the order of message delivery is not guaranteed between multiple Clients.

Â 

It is the responsibility of the Requester to make sure it has the necessary authority to publish to the request topic, and to subscribe to the Topic Name that it sets in the Response Topic property. It is the responsibility of the Responder to make sure it has the authority to subscribe to the request topic and publish to the Response Topic. While topic authorization is outside of this specification, it is recommended that Servers implement such authorization. 

Â 

###  4.10.2 Determining a Response Topic value (non-normative)

Requesters can determine a Topic Name to use as their Response Topic in any manner they choose including via local configuration. To avoid clashes between different Requesters, it is desirable that the Response Topic used by a Requester Client be unique to that Client. As the Requester and Responder commonly need to be authorized to these topics, it can be an authorization challenge to use a random Topic Name.

Â 

To help with this problem, this specification defines a property in the CONNACK packet called Response Information. The Server can use this property to guide the Client in its choice for the Response Topic to use. This mechanism is optional for both the Client and the Server. At connect time, the Client requests that the Server send a Response Information by setting the Request Response Information property in the CONNECT packet. This causes the Server to insert a Response Information property (a UTF-8 Encoded String) sent in the CONNACK packet. 

Â 

This specification does not define the contents of the Response Information but it could be used to pass a globally unique portion of the topic tree which is reserved for that Client for at least the lifetime of its Session. Using this mechanism allows this configuration to be done once in the Server rather than in each Client.

Â 

Refer to [section 3.1.2.11.7](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Response_Information) for the definition of the Response Information.

Â 

##  4.11 Server redirection

A Server can request that the Client uses another Server by sending CONNACK or DISCONNECT with Reason Codes 0x9C (Use another server), or 0x9D (Server moved) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors). When sending one of these Reason Codes, the Server MAY also include a Server Reference property to indicate the location of the Server or Servers the Client SHOULD use.

Â 

The Reason Code 0x9C (Use another server) specifies that the Client SHOULD temporarily switch to using another Server. The other Server is either already known to the Client, or is specified using a Server Reference.

Â 

The Reason Code 0x9D (Server moved) specifies that the Client SHOULD permanently switch to using another Server. The other Server is either already known to the Client, or is specified using a Server Reference.

Â 

The Server Reference is a UTF-8 Encoded String. The value of this string is a space separated list of references. The format of references is not specified here. 

Â 

**Non-normative comment**

It is recommended that each reference consists of a name optionally followed by a colon and a port number. If the name contains a colon the name string can be enclosed within square brackets ( [ and ] ). A name enclosed by square brackets cannot contain the right square bracket ( ] ) character. This is used to represent an IPv6 literal address which uses colon separators. This is a simplified version of an URI authority as described in [[RFC3986]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC3986).

Â 

**Non-normative comment**

The name within a Server Reference commonly represents a host name, DNS name [[RFC1035]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC1035), SRV name [[RFC2782]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC2782) , or literal IP address. The value following the colon separator is commonly a port number in decimal. This is not needed where the port information comes from the name resolution (such as with SRV) or is defaulted.

Â 

**Non-normative comment**

If multiple references are given, the expectation is that that Client will choose one of them.

Â 

**Non-normative comment**

Examples of the Server Reference are:

Â myserver.xyz.org 

Â myserver.xyz.org:8883

Â 10.10.151.22:8883 [fe80::9610:3eff:fe1c]:1883

Â 

The Server is allowed to not ever send a Server Reference, and the Client is allowed to ignore a Server Reference. This feature can be used to allow for load balancing, Server relocation, and Client provisioning to a Server.

Â 

##  4.12 Enhanced authentication

The MQTT CONNECT packet supports basic authentication of a Network Connection using the User Name and Password fields. While these fields are named for a simple password authentication, they can be used to carry other forms of authentication such as passing a token as the Password.

Â 

Enhanced authentication extends this basic authentication to include challenge / response style authentication. It might involve the exchange of AUTH packets between the Client and the Server after the CONNECT and before the CONNACK packets.

Â 

To begin an enhanced authentication, the Client includes an Authentication Method in the CONNECT packet. This specifies the authentication method to use. If the Server does not support the Authentication Method supplied by the Client, it MAY send a CONNACK with a Reason Code of 0x8C (Bad authentication method) or 0x87 (Not Authorized) as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors) and MUST close the Network Connection [MQTT-4.12.0-1].

Â 

The Authentication Method is an agreement between the Client and Server about the meaning of the data sent in the Authentication Data and any of the other fields in CONNECT, and the exchanges and processing needed by the Client and Server to complete the authentication.

Â 

**Non-normative comment**

The Authentication Method is commonly a SASL mechanism, and using such a registered name aids interchange. However, the Authentication Method is not constrained to using registered SASL mechanisms.

Â 

If the Authentication Method selected by the Client specifies that the Client sends data first, the Client SHOULD include an Authentication Data property in the CONNECT packet. This property can be used to provide data as specified by the Authentication Method. The contents of the Authentication Data are defined by the authentication method.

Â 

If the Server requires additional information to complete the authentication, it can send an AUTH packet to the Client. This packet MUST contain a Reason Code of 0x18 (Continue authentication) [MQTT-4.12.0-2]. If the authentication method requires the Server to send authentication data to the Client, it is sent in the Authentication Data.

Â 

The Client responds to an AUTH packet from the Server by sending a further AUTH packet. This packet MUST contain a Reason Code of 0x18 (Continue authentication) [MQTT-4.12.0-3]. If the authentication method requires the Client to send authentication data for the Server, it is sent in the Authentication Data. 

Â 

The Client and Server exchange AUTH packets as needed until the Server accepts the authentication by sending a CONNACK with a Reason Code of 0. If the acceptance of the authentication requires data to be sent to the Client, it is sent in the Authentication Data. 

Â 

The Client can close the connection at any point in this process. It MAY send a DISCONNECT packet before doing so. The Server can reject the authentication at any point in this process. It MAY send a CONNACK with a Reason Code of 0x80 or above as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors), and MUST close the Network Connection [MQTT-4.12.0-4].

Â 

If the initial CONNECT packet included an Authentication Method property then all AUTH packets, and any successful CONNACK packet MUST include an Authentication Method Property with the same value as in the CONNECT packet [MQTT-4.12.0-5].

Â 

The implementation of enhanced authentication is OPTIONAL for both Clients and Servers. If the Client does not include an Authentication Method in the CONNECT, the Server MUST NOT send an AUTH packet, and it MUST NOT send an Authentication Method in the CONNACK packet [MQTT-4.12.0-6]. If the Client does not include an Authentication Method in the CONNECT, the Client MUST NOT send an AUTH packet to the Server [MQTT-4.12.0-7]. 

Â 

If the Client does not include an Authentication Method in the CONNECT packet, the Server SHOULD authenticate using some or all of the information in the CONNECT packet, TLS session, and Network Connection.

**Â**

**Non-normative example showing a SCRAM challenge******

Â Â Â Â Â Â Â Â Client to Server: CONNECT Authentication Method="SCRAM-SHA-1" Authentication Data=client-first-data 

Â Â Â Â Â Â Â Â Server to Client: AUTH rc=0x18 Authentication Method="SCRAM-SHA-1" Authentication Data=server-first-data

Â Â Â Â Â Â Â Â Client to Server AUTH rc=0x18 Authentication Method="SCRAM-SHA-1" Authentication Data=client-final-data

Â Â Â Â Â Â Â Â Server to Client CONNACK rc=0 Authentication Method="SCRAM-SHA-1" Authentication Data=server-final-data

Â 

**Non-normative example showing a Kerberos challenge******

Â Â Â Â Â Â Â Â Client to Server CONNECT Authentication Method="GS2-KRB5" 

Â Â Â Â Â Â Â Â Server to Client AUTH rc=0x18 Authentication Method="GS2-KRB5" 

Â Â Â Â Â Â Â Â Client to Server AUTH rc=0x18 Authentication Method="GS2-KRB5" Authentication Data=initial context token

Â Â Â Â Â Â Â Â Server to Client AUTH rc=0x18 Authentication Method="GS2-KRB5" Authentication Data=reply context token

Â Â Â Â Â Â Â Â Client to Server AUTH rc=0x18 Authentication Method="GS2-KRB5" 

Â Â Â Â Â Â Â Â Server to Client CONNACK rc=0 Authentication Method="GS2-KRB5" Authentication Data=outcome of authentication

Â 

###  4.12.1 Re-authentication

If the Client supplied an Authentication Method in the CONNECT packet it can initiate a re-authentication at any time after receiving a CONNACK. It does this by sending an AUTH packet with a Reason Code of 0x19 (Re-authentication). The Client MUST set the Authentication Method to the same value as the Authentication Method originally used to authenticate the Network Connection [MQTT-4.12.1-1]. If the authentication method requires Client data first, this AUTH packet contains the first piece of authentication data as the Authentication Data. 

Â 

The Server responds to this re-authentication request by sending an AUTH packet to the Client with a Reason Code of 0x00 (Success) to indicate that the re-authentication is complete, or a Reason Code of 0x18 (Continue authentication) to indicate that more authentication data is needed. The Client can respond with additional authentication data by sending an AUTH packet with a Reason Code of 0x18 (Continue authentication). This flow continues as with the original authentication until the re-authentication is complete or the re-authentication fails.

Â 

If the re-authentication fails, the Client or Server SHOULD send DISCONNECT with an appropriate Reason Code as described in [section 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#S4_13_Errors), and MUST close the Network Connection [MQTT-4.12.1-2]. 

Â 

During this re-authentication sequence, the flow of other packets between the Client and Server can continue using the previous authentication.

Â 

**Non-normative comment**

The Server might limit the scope of the changes the Client can attempt in a re-authentication by rejecting the re-authentication. For instance, if the Server does not allow the User Name to be changed it can fail any re-authentication attempt which changes the User Name.

Â 

##  4.13 Handling errors

###  4.13.1 Malformed Packet and Protocol Errors

Definitions of Malformed Packet and Protocol Errors are contained in [section 1.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Terminology) Terminology, some but not all, of these error cases are noted throughout the specification. The rigor with which a Client or Server checks an MQTT Control Packet it has received will be a compromise between: 

Â Â Â Â Â Â Â Â The size of the Client or Server implementation. 

Â Â Â Â Â Â Â Â The capabilities that the implementation supports.

Â Â Â Â Â Â Â Â The degree to which the receiver trusts the sender to send correct MQTT Control Packets.

Â Â Â Â Â Â Â Â The degree to which the receiver trusts the network to deliver MQTT Control Packets correctly.

Â Â Â Â Â Â Â Â The consequences of continuing to process a packet that is incorrect. 

Â 

If the sender is compliant with this specification it will not send Malformed Packets or cause Protocol Errors. However, if a Client sends MQTT Control Packets before it receives CONNACK, it might cause a Protocol Error because it made an incorrect assumption about the Server capabilities. Refer [to section 3.1.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_CONNECT_Actions) CONNECT Actions.

Â 

The Reason Codes used for Malformed Packet and Protocol Errors are: 

Â Â Â Â Â Â Â Â 0x81Â Â Â Â Â Â Â Â Â Â Malformed Packet

Â Â Â Â Â Â Â Â 0x82Â Â Â Â Â Â Â Â Â Â Protocol Error

Â Â Â Â Â Â Â Â 0x93Â Â Â Â Â Â Â Â Â Â Receive Maximum exceeded

Â Â Â Â Â Â Â Â 0x95Â Â Â Â Â Â Â Â Â Â Packet too large

Â Â Â Â Â Â Â Â 0x9AÂ Â Â Â Â Â Â Â Â Â Retain not supported

Â Â Â Â Â Â Â Â 0x9BÂ Â Â Â Â Â Â Â Â Â QoS not supported

Â Â Â Â Â Â Â Â 0x9EÂ Â Â Â Â Â Â Â Â Â Shared Subscriptions not supported

Â Â Â Â Â Â Â Â 0xA1Â Â Â Â Â Â Â Â Â Â Subscription Identifiers not supported

Â Â Â Â Â Â Â Â 0xA2Â Â Â Â Â Â Â Â Â Â Wildcard Subscriptions not supported

Â 

When a Client detects a Malformed Packet or Protocol Error, and a Reason Code is given in the specification, it SHOULD close the Network Connection. In the case of an error in a AUTH packet it MAY send a DISCONNECT packet containing the reason code, before closing the Network Connection. In the case of an error in any other packet it SHOULD send a DISCONNECT packet containing the reason code before closing the Network Connection. Use Reason Code 0x81 (Malformed Packet) or 0x82 (Protocol Error) unless a more specific Reason Code has been defined in section 3.14.2.1 [Disconnect Reason Code](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Disconnect_Reason_Code).

Â 

When a Server detects a Malformed Packet or Protocol Error, and a Reason Code is given in the specification, it MUST close the Network Connection [MQTT-4.13.1-1]. In the case of an error in a CONNECT packet it MAY send a CONNACK packet containing the Reason Code, before closing the Network Connection. In the case of an error in any other packet it SHOULD send a DISCONNECT packet containing the Reason Code before closing the Network Connection. Use Reason Code 0x81 (Malformed Packet) or 0x82 (Protocol Error) unless a more specific Reason Code has been defined in[ section 3.2.2.2 - Connect Reason Code](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Connect_Reason_Code) or in section [3.14.2.1 Disconnect Reason Code](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Disconnect_Return_codes). There are no consequences for other Sessions.

Â 

If either the Server or Client omits to check some feature of an MQTT Control Packet, it might fail to detect an error, consequently it might allow data to be damaged.

Â 

###  4.13.2 Other errors

Errors other than Malformed Packet and Protocol Errors cannot be anticipated by the sender because the receiver might have constraints which it has not communicated to the sender. A receiving Client or Server might encounter a transient error, such as a shortage of memory, that prevents successful processing of an individual MQTT Control Packet. 

Â 

Acknowledgment packets PUBACK, PUBREC, PUBREL, PUBCOMP, SUBACK, UNSUBACK with a Reason Code of 0x80 or greater indicate that the received packet, identified by a Packet Identifier, was in error. There are no consequences for other Sessions or other Packets flowing on the same Session. 

Â 

The CONNACK and DISCONNECT packets allow a Reason Code of 0x80 or greater to indicate that the Network Connection will be closed. If a Reason Code of 0x80 or greater is specified, then the Network Connection MUST be closed whether or not the CONNACK or DISCONNECT is sent [MQTT-4.13.2-1]. Sending of one of these Reason Codes does not have consequence for any other Session.

Â 

If the Control Packet contains multiple errors the receiver of the Packet can validate the Packet in any order and take the appropriate action for any of the errors found.

Â 

Refer to section 5.4.9 for information about handling Disallowed Unicode code points.

#  5Â Â Â Â Â Security (non-normative)

##  5.1 Introduction

MQTT is a transport protocol specification for message transmission, allowing implementers a choice of network, privacy, authentication and authorization technologies. Since the exact security technologies chosen will be context specific, it is the implementer's responsibility to include the appropriate features as part of their design.

Â 

MQTT Implementations will likely need to keep pace with an evolving security landscape.

Â 

This Chapter provides general implementation guidance so as not to restrict choices available and is therefore non-normative. This should not detract from its importance.

Â 

It is strongly recommended that Server implementations that offer TLS [[RFC5246]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246) should use TCP port 8883 (IANA service name: secure-mqtt).

Â 

There are a number of threats that solution providers should consider. For example:

  * Devices could be compromised
  * Data at rest in Clients and Servers might be accessible
  * Protocol behaviors could have side effects (e.g. timing attacks )
  * Denial of Service (DoS) attacks
  * Communications could be intercepted, altered, re-routed or disclosed
  * Injection of spoofed MQTT Control Packets



Â 

MQTT solutions are often deployed in hostile communication environments. In such cases, implementations will often need to provide mechanisms for:

  * Authentication of users and devices
  * Authorization of access to Server resources
  * Integrity of MQTT Control Packets and application data contained therein
  * Privacy of MQTT Control Packets and application data contained therein



Â 

In addition to technical security issues there could also be geographic (e.g. U.S.-EU Privacy Shield Framework [[USEUPRIVSH]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#USEUPRIVSH)), industry specific (e.g. PCI DSS [[PCIDSS]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#PCIDSS)) and regulatory considerations (e.g. Sarbanes-Oxley [[SARBANES]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#SARBANES)).

[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#USEUSAFEHARB)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#PCIDSS)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#SARBANES)

##  5.2 MQTT solutions: security and certification

An implementation might want to provide conformance with specific industry security standards such as NIST Cyber Security Framework [[NISTCSF]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#NISTCSF), PCI-DSS [[PCIDSS]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#PCIDSS)), FIPS-140-2 [[FIPS1402]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#FIPS1402) and NSA Suite B [[NSAB]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#NSAB).

[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#NISTCSF)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#PCIDSS)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#FIPS1402)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#NSAB)

Guidance on using MQTT within the NIST Cyber Security Framework [[NISTCSF]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#NISTCSF) can be found in the MQTT supplemental publication, MQTT and the NIST Framework for Improving Critical Infrastructure Cybersecurity [[MQTTNIST]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#MQTTNIST). The use of industry proven, independently verified and certified technologies will help meet compliance requirements.

Â 

##  5.3 Lightweight crytography and constrained devices

Advanced Encryption Standard [[AES]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#AES) is the most widely adopted encryption algorithm. There is hardware support for AES in many processors, but not commonly for embedded processors. The encryption algorithm ChaCha20 [[CHACHA20](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#CHACHA20)] encrypts and decrypts much faster in software, but is not as widely available as AES.

Â 

ISO 29192 [[ISO29192]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#ISO29192) makes recommendations for cryptographic primitives specifically tuned to perform on constrained low end devices.

[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#ISO29192)

##  5.4 Implementation notes

There are many security concerns to consider when implementing or using MQTT. The following section should not be considered a check list . 

Â 

An implementation might want to achieve some, or all, of the following:

Â 

###  5.4.1 Authentication of Clients by the Server

The CONNECT packet contains User Name and Password fields. Implementations can choose how to make use of the content of these fields. They may provide their own authentication mechanism, use an external authentication system such as LDAP [[RFC4511]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC4511) or OAuth [[RFC6749]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC6749) tokens, or leverage operating system authentication mechanisms.

Â 

MQTT v5.0 provides an enhanced authentication mechanism as described in [section 4.12](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Enhanced_authentication). Using this requires support for it in both the Client and Server.[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC4511)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC6749)

Â 

Implementations passing authentication data in clear text, obfuscating such data elements or requiring no authentication data should be aware this can give rise to Man-in-the-Middle and replay attacks. [Section 5.4.5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Privacy_of_Application) introduces approaches to ensure data privacy.

Â 

A Virtual Private Network (VPN) between the Clients and Servers can provide confidence that data is only being received from authorized Clients.

Â 

Where TLS [[RFC5246]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246) is used, TLS Certificates sent from the Client can be used by the Server to authenticate the Client.[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246)

Â 

An implementation might allow for authentication where the credentials are sent in an Application Message from the Client to the Server.

Â 

###  5.4.2 Authorization of Clients by the Server

If a Client has been successfully authenticated, a Server implementation should check that it is authorized before accepting its connection. 

Â 

Authorization may be based on information provided by the Client such as User Name, the hostname/IP address of the Client, or the outcome of authentication mechanisms. 

Â 

In particular, the implementation should check that the Client is authorized to use the Client Identifier as this gives access to the MQTT Session State (described in [section 4.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Session_State)). This authorization check is to protect against the case where one Client, accidentally or maliciously, provides a Client Identifier that is already being used by some other Client. 

Â 

An implementation should provide access controls that take place after CONNECT to restrict the Clients ability to publish to particular Topics or to subscribe using particular Topic Filters. An implementation should consider limiting access to Topic Filters that have broad scope, such as the # Topic Filter.

Â 

###  5.4.3 Authentication of the Server by the Client

The MQTT protocol is not trust symmetrical. When using basic authentication, there is no mechanism for the Client to authenticate the Server. Some forms of extended authentication do allow for mutual authentication.

Â 

Where TLS [[RFC5246]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246) is used, TLS Certificates sent from the Server can be used by the Client to authenticate the Server. Implementations providing MQTT service for multiple hostnames from a single IP address should be aware of the Server Name Indication extension to TLS defined in section 3 of [[RFC6066]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC6066).This allows a Client to tell the Server the hostname of the Server it is trying to connect to.[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC6066)

Â 

An implementation might allow for authentication where the credentials are sent in an Application Message from the Server to the Client. MQTT v5.0 provides an enhanced authentication mechanism as described in [section 4.12](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Enhanced_authentication)., which can be used to Authenticate the Server to the Client. Using this requires support for it in both the Client and Server.

Â 

A VPN between Clients and Servers can provide confidence that Clients are connecting to the intended Server.

Â 

###  5.4.4 Integrity of Application Messages and MQTT Control Packets

Applications can independently include hash values in their Application Messages. This can provide integrity of the contents of Publish packets across the network and at rest. 

Â 

TLS [[RFC5246]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246) provides hash algorithms to verify the integrity of data sent over the network.[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246)

Â 

The use of VPNs to connect Clients and Servers can provide integrity of data across the section of the network covered by a VPN.

Â 

###  5.4.5 Privacy of Application Messages and MQTT Control Packets

TLS [[RFC5246]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246) can provide encryption of data sent over the network. There are valid TLS cipher suites that include a NULL encryption algorithm that does not encrypt data. To ensure privacy Clients and Servers should avoid these cipher suites.[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246)

Â 

An application might independently encrypt the contents of its Application Messages. This could provide privacy of the Application Message both over the network and at rest. This would not provide privacy for other Properties of the Application Message such as Topic Name. 

Â 

Client and Server implementations can provide encrypted storage for data at rest such as Application Messages stored as part of a Session.

Â 

The use of VPNs to connect Clients and Servers can provide privacy of data across the section of the network covered by a VPN.

Â 

### 5.4.6 Â Non-repudiation of message transmission

Application designers might need to consider appropriate strategies to achieve end to end non-repudiation.

Â 

###  5.4.7 Detecting compromise of Clients and Servers

Client and Server implementations using TLS [[RFC5246]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246) should provide capabilities to ensure that any TLS certificates provided when initiating a TLS connection are associated with the hostname of the Client connecting or Server being connected to.[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246)

Â 

Client and Server implementations using TLS can choose to provide capabilities to check Certificate Revocation Lists (CRLs [[RFC5280]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5280)) and Online Certificate Status Protocol (OSCP) [[RFC6960]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC6960) to prevent revoked certificates from being used.[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5280)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC6960)

Â 

Physical deployments might combine tamper-proof hardware with the transmission of specific data in Application Messages. For example, a meter might have an embedded GPS to ensure it is not used in an unauthorized location. [[IEEE8021AR]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#IEEE8021AR) is a standard for implementing mechanisms to authenticate a device s identity using a cryptographically bound identifier.

[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#IEEE8021AR)

###  5.4.8 Detecting abnormal behaviors

Server implementations might monitor Client behavior to detect potential security incidents. For example:

Â Â Â Â Â Â Â Â Repeated connection attempts

Â Â Â Â Â Â Â Â Repeated authentication attempts

Â Â Â Â Â Â Â Â Abnormal termination of connections

Â Â Â Â Â Â Â Â Topic scanning (attempts to send or subscribe to many topics)

Â Â Â Â Â Â Â Â Sending undeliverable messages (no subscribers to the topics)

Â Â Â Â Â Â Â Â Clients that connect but do not send data

Â 

Server implementations might close the Network Connection of Clients that breach its security rules.

Â 

Server implementations detecting unwelcome behavior might implement a dynamic block list based on identifiers such as IP address or Client Identifier.

Â 

Deployments might use network-level controls (where available) to implement rate limiting or blocking based on IP address or other information.

Â 

###  5.4.9 Handling of Disallowed Unicode code points

Section 1.5.4 describes the Disallowed Unicode code points, which should not be included in a UTF-8 Encoded String. A Client or Server implementation can choose whether to validate that these code points are not used in UTF-8 Encoded Strings such as the Topic Name or Properties.

Â 

If the Server does not validate the code points in a UTF-8 Encoded String but a subscribing Client does, then a second Client might be able to cause the subscribing Client to close the Network Connection by publishing on a Topic Name or using Properties that contain a Disallowed Unicode code point. This section recommends some steps that can be taken to prevent this problem.

Â 

A similar problem can occur when the Client validates that the payload matches the Payload Format Indicator and the Server does not.Â The considerations and remedies for this are similar to those for handling Disallowed Unicode code points.

Â 

####  5.4.9.1 Considerations for the use of Disallowed Unicode code points

An implementation would normally choose to validate UTF-8 Encoded strings, checking that the Disallowed Unicode code points are not used. This avoids implementation difficulties such as the use of libraries that are sensitive to these code points, it also protects applications from having to process them. 

Â 

Validating that these code points are not used removes some security exposures. There are possible security exploits which use control characters in log files to mask entries in the logs or confuse the tools which process log files.Â The Unicode Noncharacters are commonly used as special markers and allowing them into UTF-8 Encoded Strings could permit such exploits.Â 

Â 

####  5.4.9.2 Interactions between Publishers and Subscribers

The publisher of an Application Message normally expects that the Servers will forward the message to subscribers, and that these subscribers are capable of processing the messages.

These are some conditions under which a publishing Client can cause the subscribing Client to close the Network Connection. Consider a situation where: 

Â Â Â Â Â Â Â Â A Client publishes an Application Message using a Topic Name containing one of the Disallowed Unicode code points. 

Â Â Â Â Â Â Â Â The publishing Client library allows the Disallowed Unicode code point to be used in a Topic Name rather than rejecting it.

Â Â Â Â Â Â Â Â The publishing Client is authorized to send the publication.

Â Â Â Â Â Â Â Â A subscribing Client is authorized to use a Topic Filter which matches the Topic Name. Note that the Disallowed Unicode code point might occur in a part of the Topic Name matching a wildcard character in the Topic Filter.

Â Â Â Â Â Â Â Â The Server forwards the message to the matching subscriber rather than disconnecting the publisher. 

Â Â Â Â Â Â Â Â In this case the subscribing Client might: 

oÂ Â Â Close the Network Connection because it does not allow the use of Disallowed Unicode code points, possibly sending a DISCONNECT before doing so.Â For QoS 1 and QoS 2 messages this might cause the Server to send the message again, causing the Client to close the Network Connection again.

oÂ Â Â Reject the Application Message by sending a Reason Code greater than or equal to 0x80 in a PUBACK (QoS 1) or PUBREC (QoS 2). 

oÂ Â Â Accept the Application Message but fail to process it because it contains one of the Disallowed Unicode code points. 

oÂ Â Â Successfully process the Application Message.

Â 

The potential for the Client to close the Network Connection might go unnoticed until a publisher uses one of the Disallowed Unicode code points. 

Â 

#### 5.4.9.3 Â Remedies

If there is a possibility that a Disallowed Unicode code point could be included in a Topic Name or other Properties delivered to a Client, the solution owner can adopt one of the following suggestions:

1)Â Â Â Change the Server implementation to one that rejects UTF-8 Encoded Strings containing a Disallowed Unicode code point either by sending a Reason Code greater than or equal to 0x80 or closing the Network Connection.

2)Â Â Â Change the Client library used by the subscribers to one that tolerates the use of Disallowed Code points. The client can either process or discard messages with UTF-8 Encoded Strings that contain Disallowed Unicode code points so long as it continues the protocol.

Â 

###  5.4.10 Other security considerations

If Client or Server TLS certificates are lost or it is considered that they might be compromised they should be revoked (utilizing CRLs [[RFC5280]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5280) and/or OSCP [[RFC6960]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC6960)).[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5280)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC6960)

Â 

Client or Server authentication credentials, such as User Name and Password, that are lost or considered compromised should be revoked and/or reissued.

Â 

In the case of long lasting connections:

Â Â Â Â Â Â Â Â Client and Server implementations using TLS [[RFC5246]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246) should allow for session renegotiation to establish new cryptographic parameters (replace session keys, change cipher suites, change authentication credentials).[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246)

Â Â Â Â Â Â Â Â Servers may close the Network Connection of Clients and require them to re-authenticate with new credentials. 

Â Â Â Â Â Â Â Â Servers may require their Client to reauthenticate periodically using the mechanism described in [section 4.12.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Re-authentication).

Â 

Constrained devices and Clients on constrained networks can make use of TLS [[RFC5246]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246) session resumption, in order to reduce the costs of reconnecting TLS [[RFC5246]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246) sessions.

Â 

Clients connected to a Server have a transitive trust relationship with other Clients connected to the same Server and who have authority to publish data on the same topics.

Â 

###  5.4.11 Use of SOCKS

Implementations of Clients should be aware that some environments will require the use of SOCKSv5 [[RFC1928]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC1928) proxies to make outbound Network Connections. Some MQTT implementations could make use of alternative secured tunnels (e.g. SSH) through the use of SOCKS. Where implementations choose to use SOCKS, they should support both anonymous and User Name, Password authenticating SOCKS proxies. In the latter case, implementations should be aware that SOCKS authentication might occur in plain-text and so should avoid using the same credentials for connection to a MQTT Server.

[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC1928)

###  5.4.12 Security profiles

Implementers and solution designers might wish to consider security as a set of profiles which can be applied to the MQTT protocol. An example of a layered security hierarchy is presented below.

Â 

####  5.4.12.1 Clear communication profile

When using the clear communication profile, the MQTT protocol runs over an open network with no additional secure communication mechanisms in place.

Â 

####  5.4.12.2 Secured network communication profile

When using the secured network communication profile, the MQTT protocol runs over a physical or virtual network which has security controls e.g., VPNs or physically secure network.

Â 

####  5.4.12.3 Secured transport profile

When using the secured transport profile, the MQTT protocol runs over a physical or virtual network and using TLS [[RFC5246]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246) which provides authentication, integrity and privacy.[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246)

Â 

TLS [[RFC5246]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246) Client authentication can be used in addition to or in place of MQTT Client authentication as provided by the User Name and Password fields.

[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC5246)

####  5.4.12.4 Industry specific security profiles

It is anticipated that the MQTT protocol will be designed into industry specific application profiles, each defining a threat model and the specific security mechanisms to be used to address these threats. Recommendations for specific security mechanisms will often be taken from existing works including:

Â 

[[NISTCSF]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#NISTCSF) NIST Cyber Security Framework

[[NIST7628]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#NIST7628) NISTIR 7628 Guidelines for Smart Grid Cyber Security

[[FIPS1402]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#FIPS1402) Security Requirements for Cryptographic Modules (FIPS PUB 140-2)

[[PCIDSS]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#PCIDSS) PCI-DSS Payment Card Industry Data Security Standard

[[NSAB]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#NSAB) NSA Suite B Cryptography[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#NIST7628)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#FIPS1402)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#PCIDSS)[](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#NSAB)

Â 

#  6Â Â Â Â Â Using WebSocket as a network transport

If MQTT is transported over a WebSocket [[RFC6455]](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#RFC6455) connection, the following conditions apply: 

Â Â Â Â Â Â Â Â MQTT Control Packets MUST be sent in WebSocket binary data frames. If any other type of data frame is received the recipient MUST close the Network Connection [MQTT-6.0.0-1].

Â Â Â Â Â Â Â Â A single WebSocket data frame can contain multiple or partial MQTT Control Packets. The receiver MUST NOT assume that MQTT Control Packets are aligned on WebSocket frame boundaries [MQTT-6.0.0-2].

Â Â Â Â Â Â Â Â The Client MUST include mqtt in the list of WebSocket Sub Protocols it offers [MQTT-6.0.0-3]. 

Â Â Â Â Â Â Â Â The WebSocket Subprotocol name selected and returned by the Server MUST be mqtt  [MQTT-6.0.0-4].

Â Â Â Â Â Â Â Â The WebSocket URI used to connect the Client and Server has no impact on the MQTT protocol. 

Â 

## 6.1 Â IANA considerations

This specification requests IANA to modify the registration of the WebSocket MQTT sub-protocol under the WebSocket Subprotocol Name registry with the following data:

Â 

Figure 6.6â1 \- IANA WebSocket Identifier

Â 

#  7Â Â Â Â Â Conformance

The MQTT specification defines conformance for MQTT Client implementations and MQTT Server implementations. An MQTT implementation can conform as both an MQTT Client and an MQTT Server.

Â 

##  7.1 Conformance clauses

###  7.1.1 MQTT Server conformance clause

Refer to [Server](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#Server) in the Terminology section for a definition of Server.

Â 

An MQTT Server conforms to this specification only if it satisfies all the statements below:

1.Â Â Â Â The format of all MQTT Control Packets that the Server sends matches the format described in [Chapter 2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_MQTT_Control_Packet) and [Chapter 3](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_MQTT_Control_Packets).

2.Â Â Â Â It follows the Topic matching rules described in [section 4.7](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Topic_Names_and) and the Subscription rules in [section 4.8](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Subscriptions).

3.Â Â Â Â It satisfies the MUST level requirements in the following chapters that are identified except for those that only apply to the Client:

Â Â Â Â Â Â Â Â [Chapter 1 - Introduction](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Introduction)

Â Â Â Â Â Â Â Â [Chapter 2 - MQTT Control Packet format](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_MQTT_Control_Packet)

Â Â Â Â Â Â Â Â [Chapter 3 - MQTT Control Packets](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_MQTT_Control_Packets)

Â Â Â Â Â Â Â Â [Chapter 4 - Operational behavior](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Operational_behavior)

Â Â Â Â Â Â Â Â [Chapter 6 - Using WebSocket as a network transport](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Using_WebSocket_as)

4.Â Â Â Â It does not require the use of any extensions defined outside of the specification in order to interoperate with any other conformant implementation.

Â 

###  7.1.2 MQTT Client conformance clause

Refer to [Client](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#Client) in the Terminology section for a definition of Client.

Â 

An MQTT Client conforms to this specification only if it satisfies all the statements below:

1.Â Â Â Â The format of all MQTT Control Packets that the Client sends matches the format described in [Chapter 2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_MQTT_Control_Packet) and [Chapter 3](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_MQTT_Control_Packets).

2.Â Â Â Â It satisfies the MUST level requirements in the following chapters that are identified except for those that only apply to the Server:

Â Â Â Â Â Â Â Â [Chapter 1 - Introduction](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Introduction)

Â Â Â Â Â Â Â Â [Chapter 2 - MQTT Control Packet format](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_MQTT_Control_Packet)

Â Â Â Â Â Â Â Â [Chapter 3 - MQTT Control Packets](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_MQTT_Control_Packets)

Â Â Â Â Â Â Â Â [Chapter 4 - Operational behavior](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Operational_behavior)

Â Â Â Â Â Â Â Â [Chapter 6 - Using WebSocket as a network](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Using_WebSocket_as) transport 

3.Â Â Â Â It does not require the use of any extensions defined outside of the specification in order to interoperate with any other conformant implementation.

Â 

Appendix A. Acknowledgments

The TC owes special thanks to Dr. Andy Stanford-Clark and Arlen Nipper as the original inventors of the MQTT protocol and for their continued support with the standardization process.

Â 

The TC wishes to thank Brian Raymor (formerly of Microsoft) for his work as co-chairman of the MQTT TC during much of the development of the version 5.0 standard.

Â 

The following individuals were members of the OASIS Technical Committee during the creation of this standard and their contributions are gratefully acknowledged:

Â 

**Participants:**

Â Â Â Â Â Â Â Â Senthil Nathan Balasubramaniam (Infiswift)

Â Â Â Â Â Â Â Â Dr. Andrew Banks, editor (IBM)

Â Â Â Â Â Â Â Â Ken Borgendale, editor (IBM)

Â Â Â Â Â Â Â Â Ed Briggs, editor (Microsoft)

Â Â Â Â Â Â Â Â Raphael Cohn (Individual)

Â Â Â Â Â Â Â Â Richard Coppen, chairman (IBM)

Â Â Â Â Â Â Â Â William Cox (Individual)

Â Â Â Â Â Â Â Â Ian Craggs , secretary (IBM)

Â Â Â Â Â Â Â Â Konstantin Dotchkoff (Microsoft)

Â Â Â Â Â Â Â Â Derek Fu (IBM)

Â Â Â Â Â Â Â Â Rahul Gupta, editor (IBM)

Â Â Â Â Â Â Â Â Stefan Hagen (Individual)

Â Â Â Â Â Â Â Â David Horton (Solace Systems)

Â Â Â Â Â Â Â Â Alex Kritikos (Software AG, Inc.)

Â Â Â Â Â Â Â Â Jonathan Levell (IBM)

Â Â Â Â Â Â Â Â Shawn McAllister (Solace Systems)

Â Â Â Â Â Â Â Â William McLane (TIBCO Software Inc.)

Â Â Â Â Â Â Â Â Peter Niblett (IBM)

Â Â Â Â Â Â Â Â Dominik Obermaier (dc-square GmbH)

Â Â Â Â Â Â Â Â Nicholas O'Leary (IBM)

Â Â Â Â Â Â Â Â Brian Raymor (Microsoft)

Â Â Â Â Â Â Â Â Andrew Schofield (IBM)

Â Â Â Â Â Â Â Â Tobias Sommer (Cumulocity)

Â Â Â Â Â Â Â Â Joe Speed (IBM)

Â Â Â Â Â Â Â Â Dr Andy Stanford-Clark (IBM)

Â Â Â Â Â Â Â Â Allan Stockdill-Mander (IBM)

Â Â Â Â Â Â Â Â Stehan Vaillant (Cumulocity)

Â 

For a list of those who contributed to earlier versions of MQTT refer to Appendix A in the MQTT v3.1.1 specification **[MQTTV311****]**. 

Â 

Appendix B. Mandatory normative statement (non-normative)

This Appendix is non-normative and is provided as a convenient summary of the numbered conformance statements found in the main body of this document. Refer to [Chapter 7](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Conformance) for a definitive list of conformance requirements.

Â 

Â 

Appendix C. Summary of new features in MQTT v5.0 (non-normative)

The following new features are added to MQTT v5.0

Â 

Â Â Â Â Â Â Â Â Session expiry

Split the Clean Session flag into a Clean Start flag which indicates that the session should start without using an existing session, and a Session Expiry interval which says how long to retain the session after a disconnect. The session expiry interval can be modified at disconnect. Setting of Clean Start to 1 and Session Expiry Interval to 0 is equivalent in MQTT v3.1.1 of setting Clean Session to 1.

Â 

Â Â Â Â Â Â Â Â Message expiry

Allow an expiry interval to be set when a message is published.

Â 

Â Â Â Â Â Â Â Â Reason code on all ACKs

Change all response packets to contain a reason code. This include CONNACK, PUBACK, PUBREC, PUBREL, PUBCOMP, SUBACK, UNSUBACK, DISCONNECT, and AUTH. This allows the invoker to determine whether the requested function succeeded.

Â 

Â Â Â Â Â Â Â Â Reason string on all ACKs

Change most packets with a reason code to also allow an optional reason string. This is designed for problem determination and is not intended to be parsed by the receiver.

Â 

Â Â Â Â Â Â Â Â Server disconnect

Allow DISCONNECT to be sent by the Server to indicate the reason the connection is closed. 

Â 

Â Â Â Â Â Â Â Â Payload format and content type

Allow the payload format (binary, text) and a MIME style content type to be specified when a message is published. These are forwarded on to the receiver of the message.

Â 

Â Â Â Â Â Â Â Â Request / Response

Formalize the request/response pattern within MQTT and provide the Response Topic and Correlation Data properties to allow response messages to be routed back to the publisher of a request. Also, add the ability for the Client to get configuration information from the Server about how to construct the response topics.

Â 

Â Â Â Â Â Â Â Â Shared Subscriptions

Add shared subscription support allowing for load balanced consumers of a subscription

Â 

Â Â Â Â Â Â Â Â Subscription ID

Allow a numeric subscription identifier to be specified on a SUBSCRIBE, and returned on the message when it is delivered. This allows the Client to determine which subscription or subscriptions caused the message to be delivered.

Â 

Â Â Â Â Â Â Â Â Topic Alias

Decrease the size of the MQTT packet overhead by allowing the topic name to be abbreviated to a small integer. The Client and Server independently specify how many topic aliases they allow.

Â 

Â Â Â Â Â Â Â Â Flow control

Allow the Client and Server to independently specify the number of outstanding reliable messages (QoS>0) they allow. The sender pauses sending such messages to stay below this quota. This is used to limit the rate of reliable messages, and to limit how many are in flight at one time.

Â 

Â Â Â Â Â Â Â Â User properties

Add User Properties to most packets. User properties on PUBLISH are included with the message and are defined by the Client applications. The user properties on PUBLISH and Will Properties are forwarded by the Server to the receiver of the message. User properties on the CONNECT, SUBSCRIBE, and UNSUBSCRIBE packets are defined by the Server implementation. The user properties on CONNACK PUBACK, PUBREC, PUBREL, PUBCOMP, SUBACK, UNSUBACK and AUTH packets are defined by the sender, and are unique to the sender implementation. The meaning of user properties is not defined by MQTT.

Â 

Â Â Â Â Â Â Â Â Maximum Packet Size

Allow the Client and Server to independently specify the maximum packet size they support. It is an error for the session partner to send a larger packet.

Â 

Â Â Â Â Â Â Â Â Optional Server feature availability

Define a set of features which the Server does not allow and provide a mechanism for the Server to specify this to the Client. The features which can be specified in this way are: Maximum QoS, Retain Available, Wildcard Subscription Available, Subscription Identifier Available, and Shared Subscription Available. It is an error for the Client to use features that the Server has declared are not available. 

Â 

It is possible in earlier versions of MQTT for a Server to not implement a feature by declaring that the Client is not authorized for that function. This feature allows such optional behavior to be declared and adds specific Reason Codes when the Client uses one of these features anyway.

Â 

Â Â Â Â Â Â Â Â Enhanced authentication

Provide a mechanism to enable challenge/response style authentication including mutual authentication. This allows SASL style authentication to be used if supported by both Client and Server, and includes the ability for a Client to re-authenticate within a connection.

Â 

Â Â Â Â Â Â Â Â Subscription options

Provide subscription options primarily defined to allow for message bridge applications. These include an option to not send messages originating on this Client (noLocal), and options for handling retained messages on subscribe.

Â 

Â Â Â Â Â Â Â Â Will delay

Add the ability to specify a delay between the end of the connection and sending the will message. This is designed so that if a connection to the session is re-established then the will message is not sent. This allows for brief interruptions of the connection without notification to others.

Â 

Â Â Â Â Â Â Â Â Server Keep Alive

Allow the Server to specify the value it wishes the Client to use as a keep alive. This allows the Server to set a maximum allowed keepalive and still have the Client honor it.

Â 

Â Â Â Â Â Â Â Â Assigned ClientID

In cases where the ClientID is assigned by the Server, return the assigned ClientID. This also lifts the restriction that Server assigned ClientIDs can only be used with Clean Session=1 connections.

Â 

Â Â Â Â Â Â Â Â Server reference 

Allow the Server to specify an alternate Server to use on CONNACK or DISCONNECT. This can be used as a redirect or to do provisioning.

Â 

![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAMAAADXqc3KAAAA51BMVEUAAABRT2tSUGpRT2tQUHBQUGjwtcxRT2tRUGtST2tSTmrvsMnvt89QUHDqTIpkXHhST2zQobmfdpPrTYrGVoHqS4nwtszvtMzvtc3vr89RT2vwtczASHb09vnIXYbt4OncqMDqTInGVoBbVnHqp8GqiKJlXHfz2+bsrsfkmrfIm7SggpvScZfKaY/q1uDtgKvRiKaNdY/MY4vy7fLy5Ozxydrxw9bhtcjnobzVlK/diam0j6jYfqHVeJyXfJWcd5TrXJOCb4l5aYNvYn3DUXzxzd3kwNDSorrth6/CjqnAeZnNdJaDb4nDaCDkAAAAGnRSTlMA73C/ICDv37+ff3AgEL+AgO/v7+/fr6BgELJb3PQAAAE/SURBVCjPXZHnUsMwEIRlOySkhw66k+24YScx6b0XOu//PJw0mozh+6Efu6ddzYlpqiWrwLlhmTmW5cLiZ4oZyzR4BsNkmhL/R0nPcx6FR6357ZbPuanyKefT62yjn37/cJwPbjeUJnuKNPeFuAaFjXhNgkUXONHDdR6CJIkh8HArlSo1UIUbx6sTEt4CZlfSaLBLOl2YeaixA2irLKrey4AzA4jpXQVG7hI6mCGBPonSaIF9StMUMe0hzrGjslhBGp7tDIUzfRPTnvhWhiHLQxjYQrwIoQ5nAXtZ3uD8AAkKYTsk0sAocNVSqqpkRaK+MYYNSTkms3wXXodCMZpAKD9FLzF6Bxg/ExMgXS+RluKHkGEZUYOi7sIf3DrTlPNAfOx2XSDyj+xM5QGg2yTIua+wLJVy7abZvKuVn7TwCyKmN+3PjJblAAAAAElFTkSuQmCC)å·²ç»å½åçº§

ä¸è½½ææº APP

åæè¯­è¨èªå¨æ£æµ ç®ä½ä¸­æ ç¹ä½ä¸­æ-å°æ¹¾ (ç¹é«ä¸­æ-å°æ¹¾) ç¹ä½ä¸­æ-é¦æ¸¯ (ç¹é«ä¸­æ-é¦æ¸¯) è±è¯­ (English) æ¥è¯­ (æ¥æ¬èª) é©è¯­ (íêµ­ì´) è¥¿ç­çè¯­ (Espa ol) å¾·è¯­ (Deutsch) æ³è¯­ (Fran ais) è¡èçè¯­ (Portugu s) è¡èçè¯­ï¼å·´è¥¿ï¼ (Portugu s (Brasil)) é¿å°å·´å°¼äºè¯­ (Shqip) é¿æä¼¯è¯­ (Ø§ÙØ¹Ø±Ø¨ÙØ©) é¿å§åæè¯­ (á áá­á) é¿å¡æçè¯­ (AzÉrbaycanca) ç±å°å °è¯­ (Gaeilge) ç±æ²å°¼äºè¯­ (Eesti) å·´æ¯å è¯­ (Euskara) ç½ä¿ç½æ¯è¯­ (ÐÐµÐ»Ð°ÑÑÑÐºÐ°Ñ) ç½èè¯­ (Hmong Daw) ç­å¾è¯­ (isiXhosa) ä¿å å©äºè¯­ (ÐÑÐ»Ð³Ð°ÑÑÐºÐ¸) å°å²è¯­ ( slenska) æ³¢å °è¯­ (Polski) æ³¢æ¯å°¼äºè¯­ (Bosanski) æ³¢æ¯è¯­ (ÙØ§Ø±Ø³Û) èè¯­ (à½à½¼à½à¼à½¡à½²à½) ä¸¹éº¦è¯­ (Dansk) ä¸åè¯ (æ±åå®è©±) ä¿è¯­ (Ð ÑÑÑÐºÐ¸Ð¹) æ¢µè¯­ (à¤¸à¤à¤¸à¥à¤à¥à¤¤à¤®à¥) è²å¾å®¾è¯­ (Filipino) ææµè¯­ (Na Vosa Vakaviti) è¬å °è¯­ (Suomi) å¼éæ¯å °è¯­ (Frysk) é«æ£è¯­ (áá¶áá¶ááááá) æ ¼é²åäºè¯­ (á¥áá áá£áá) å¤åæç¹è¯­ (àªà«àªàª°àª¾àª¤à«) åè¨å è¯­ (ÒÐ°Ð·Ð°Ò Ð¢ÑÐ»Ñ) æµ·å°å éå¥¥å°è¯­ (Krey l Ayisyen) è±ªè¨è¯­ (Hausa) è·å °è¯­ (Nederlands) åå°åæ¯è¯­ (ÐÑÑÐ³ÑÐ·ÑÐ°) å å©è¥¿äºè¯­ (Galego) å æ³°ç½å°¼äºè¯­ (Catal ) æ·å è¯­ (Äe tina) å¡çº³è¾¾è¯­ (à²à²¨à³à²¨à²¡) ç§è¥¿åè¯­ (Corsu) å é·å¡ç½å¥¥æç±³è¯­ (H h u) å æè´¡è¯­ (tlhIngan Hol) å æè´¡è¯­ï¼piqaDï¼ (tlhIngan Hol (pIqaD)) å ç½å°äºè¯­ (Hrvatski) åºå°å¾·è¯­ (Kurd ) æä¸è¯­ (Latina) æè±ç»´äºè¯­ (Latvie u) èæè¯­ (àº¥àº²àº§) ç«é¶å®è¯­ (LietuviÅ³) å¢æ£®å ¡è¯­ (L tzebuergesch) ç½é©¬å°¼äºè¯­ (Rom nÄ) ç½é©¬ä¹å°é½è¯­ (Roman Urdu) é©¬è³ä»è¯­ (Malti) é©¬æå°è¯­ (à¤®à¤°à¤¾à¤ à¥) é©¬æå æ¯è¯­ (Malagasy) é©¬æé æå§è¯­ (à´®à´²à´¯à´¾à´³à´) é©¬æ¥è¯­ (Bahasa Melayu) é©¬å ¶é¡¿è¯­ (ÐÐ°ÐºÐµÐ´Ð¾Ð½ÑÐºÐ¸) æ¯å©è¯­ (MÄori) èå¤è¯­ (ÐÐ¾Ð½Ð³Ð¾Ð») å­å æè¯­ (à¦¬à¦¾à¦à¦²à¦¾) ç¼ ç¸è¯­ (áá¼ááºáá¬á á¬) èè¯­ (Hmoob) åéè·å °è¯­ (Afrikaans) å°¼æ³å°è¯­ (à¤¨à¥à¤ªà¤¾à¤²à¥) æªå¨è¯­ (Norsk) æé®æ®è¯­ (à¨ªà©°à¨à¨¾à¨¬à©) æ®ä»å¾è¯­ (Ù¾ÚØªÙ) é½åç¦è¯­ï¼å°¼æ¬è´¾è¯­ï¼ (Chichewa) çå ¸è¯­ (Svenska) è¨æ©äºè¯­ (Gagana Samoa) å¡å°ç»´äºè¯­ (Ð¡ÑÐ¿ÑÐºÐ¸) å¡å°ç»´äºè¯­ï¼æä¸æï¼ (Srpski (Latinica)) å¡å°ç»´äºè¯­ï¼è¥¿éå°æï¼ (Ð¡ÑÐ¿ÑÐºÐ¸ (ÐÐ¸ÑÐ¸Ð»Ð¸ÑÐ°)) å¡ç´¢æè¯­ (Sesotho) å§ä¼½ç½è¯­ (à·à·à¶à·à¶½) ä¸çè¯­ (Esperanto) æ¯æ´ä¼å è¯­ (SlovenÄina) æ¯æ´æå°¼äºè¯­ (Sloven Äina) æ¯ç¦å¸éè¯­ (Kiswahili) èæ ¼å °çå°è¯­ (G idhlig) å®¿å¡è¯­ (Binisaya) ç´¢é©¬éè¯­ (Soomaali) å¡åå è¯­ (Ð¢Ð¾Ò·Ð¸ÐºÓ£) å¡å¸æè¯­ (Reo Tahiti) æ³°å¢åºè¯­ (à°¤à±à°²à±à°à±) æ³°ç±³å°è¯­ (à®¤à®®à®¿à®´à¯) æ³°è¯­ (à¹à¸à¸¢) æ±¤å è¯­ (lea fakatonga) åè³å ¶è¯­ (T rk e) å¨å°å£«è¯­ (Cymraeg) ç»´å¾å°è¯­ (Ø¦ÛÙØºÛØ±ÚÛ) æè¨æ (æè¨æ) ä¹å°é½è¯­ (Ø§Ø±Ø¯Ù) ä¹å å °è¯­ (Ð£ÐºÑÐ°ÑÐ½ÑÑÐºÐ°) ä¹å ¹å«å è¯­ (OÊ»zbek) å¸ä¼¯æ¥è¯­ (×¢××¨××ª) å¸è è¯­ (ÎÎ»Î»Î·Î½Î¹ÎºÎ¬) å¤å¨å¤·è¯­ (Ê»Ålelo HawaiÊ»i) ä¿¡å¾·è¯­ (Ø³ÙÚÙ) åçå©è¯­ (Magyar) ä¿®çº³è¯­ (ChiShona) å·½ä»è¯­ (Basa Sunda) äºç¾å°¼äºè¯­ (ÕÕ¡ÕµÕ¥ÖÕ¥Õ¶) ä¼åè¯­ (Asá»¥sá»¥ Igbo) æå¤§å©è¯­ (Italiano) æç¬¬ç»ªè¯­ (××Ö´×××©) å°å°è¯­ (à¤¹à¤¿à¤¨à¥à¤¦à¥) å°åº¦å°¼è¥¿äºè¯­ (Bahasa Indonesia) å°¤å¡å¦çé è¯­ (M aya T' an) çº¦é²å·´è¯­ ( d Yor b ) ç²¤è¯­ (ç²µèª) è¶åè¯­ (Tiáº¿ng Viá»t) çªåè¯­ (Basa Jawa) ç¥é²è¯­ (isiZulu)

![](data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGcgaWQ9IkZyYW1lIj4KPHBhdGggaWQ9IlZlY3RvciIgZD0iTTguNzEwMjMgMTMuMzg3NkwxMy4yODkzIDguODA4NkwxNC4wOTc3IDguMDAwMjJMMTMuMjg5NyA3LjE5MjIyTDguNzEwMjMgMi42MTI3OUw3LjkwMjIzIDMuNDIwNzlMMTEuOTA5NSA3LjQyODc5SDEuOTA1NjZWOC41NzE2NUgxMS45MDk1TDcuOTAxODUgMTIuNTc5M0w4LjcxMDIzIDEzLjM4NzZaIiBmaWxsPSIjODM4MzgzIi8+CjwvZz4KPC9zdmc+Cg==)

ç®æ è¯­è¨ç®ä½ä¸­æ ç¹ä½ä¸­æ-å°æ¹¾ (ç¹é«ä¸­æ-å°æ¹¾) è±è¯­ (English) æ¥è¯­ (æ¥æ¬èª) é©è¯­ (íêµ­ì´) è¥¿ç­çè¯­ (Espa ol) å¾·è¯­ (Deutsch) æ³è¯­ (Fran ais) è¡èçè¯­ (Portugu s) è¡èçè¯­ï¼å·´è¥¿ï¼ (Portugu s (Brasil)) ä¿è¯­ (Ð ÑÑÑÐºÐ¸Ð¹) ç²¤è¯­ (ç²µèª) é¿æä¼¯è¯­ (Ø§ÙØ¹Ø±Ø¨ÙØ©) ç±å°å °è¯­ (Gaeilge) ç±æ²å°¼äºè¯­ (Eesti) ä¿å å©äºè¯­ (ÐÑÐ»Ð³Ð°ÑÑÐºÐ¸) å°å²è¯­ ( slenska) æ³¢å °è¯­ (Polski) æ³¢æ¯å°¼äºè¯­ (Bosanski) æ³¢æ¯è¯­ (ÙØ§Ø±Ø³Û) èè¯­ (à½à½¼à½à¼à½¡à½²à½) ä¸¹éº¦è¯­ (Dansk) è²å¾å®¾è¯­ (Filipino) ææµè¯­ (Na Vosa Vakaviti) è¬å °è¯­ (Suomi) é«æ£è¯­ (áá¶áá¶ááááá) å¤åæç¹è¯­ (àªà«àªàª°àª¾àª¤à«) åè¨å è¯­ (ÒÐ°Ð·Ð°Ò Ð¢ÑÐ»Ñ) æµ·å°å éå¥¥å°è¯­ (Krey l Ayisyen) è·å °è¯­ (Nederlands) å æ³°ç½å°¼äºè¯­ (Catal ) æ·å è¯­ (Äe tina) å¡çº³è¾¾è¯­ (à²à²¨à³à²¨à²¡) å é·å¡ç½å¥¥æç±³è¯­ (H h u) å æè´¡è¯­ (tlhIngan Hol) å ç½å°äºè¯­ (Hrvatski) æè±ç»´äºè¯­ (Latvie u) ç«é¶å®è¯­ (LietuviÅ³) ç½é©¬å°¼äºè¯­ (Rom nÄ) é©¬è³ä»è¯­ (Malti) é©¬æå°è¯­ (à¤®à¤°à¤¾à¤ à¥) é©¬æå æ¯è¯­ (Malagasy) é©¬æé æå§è¯­ (à´®à´²à´¯à´¾à´³à´) é©¬æ¥è¯­ (Bahasa Melayu) æ¯å©è¯­ (MÄori) å­å æè¯­ (à¦¬à¦¾à¦à¦²à¦¾) èè¯­ (Hmoob) åéè·å °è¯­ (Afrikaans) æªå¨è¯­ (Norsk) æé®æ®è¯­ (à¨ªà©°à¨à¨¾à¨¬à©) æ®ä»å¾è¯­ (Ù¾ÚØªÙ) çå ¸è¯­ (Svenska) è¨æ©äºè¯­ (Gagana Samoa) å¡å°ç»´äºè¯­ï¼æä¸æï¼ (Srpski (Latinica)) å¡å°ç»´äºè¯­ï¼è¥¿éå°æï¼ (Ð¡ÑÐ¿ÑÐºÐ¸ (ÐÐ¸ÑÐ¸Ð»Ð¸ÑÐ°)) æ¯æ´ä¼å è¯­ (SlovenÄina) æ¯æ´æå°¼äºè¯­ (Sloven Äina) æ¯ç¦å¸éè¯­ (Kiswahili) å¡å¸æè¯­ (Reo Tahiti) æ³°å¢åºè¯­ (à°¤à±à°²à±à°à±) æ³°ç±³å°è¯­ (à®¤à®®à®¿à®´à¯) æ³°è¯­ (à¹à¸à¸¢) æ±¤å è¯­ (lea fakatonga) åè³å ¶è¯­ (T rk e) å¨å°å£«è¯­ (Cymraeg) ç»´å¾å°è¯­ (Ø¦ÛÙØºÛØ±ÚÛ) æè¨æ (æè¨æ) ä¹å°é½è¯­ (Ø§Ø±Ø¯Ù) ä¹å å °è¯­ (Ð£ÐºÑÐ°ÑÐ½ÑÑÐºÐ°) å¸ä¼¯æ¥è¯­ (×¢××¨××ª) å¸è è¯­ (ÎÎ»Î»Î·Î½Î¹ÎºÎ¬) åçå©è¯­ (Magyar) æå¤§å©è¯­ (Italiano) å°å°è¯­ (à¤¹à¤¿à¤¨à¥à¤¦à¥) å°åº¦å°¼è¥¿äºè¯­ (Bahasa Indonesia) å°¤å¡å¦çé è¯­ (M aya T' an) è¶åè¯­ (Tiáº¿ng Viá»t)

ç¿»è¯æå¡ï¼

![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAMAAABHPGVmAAAAqFBMVEUAAADn5+fm5ubm5ubm5ubm5ubm5ubq6urf39/k5OTn5+fm5ubm5ubm5ubn5+fk5OTl5eXm5ubm5ubo6Oj////z8/MFpvDzUyX/ugiBvAbm5ubv7+/9/f1JvPH8ykvzgGD9wimRwyjp6ens7Oz6+vonsfEnsfChzEmhy0nzakPzakL39/f19fVfw/HzkHT70GF4zPLzoYn61nu513mu0mXzf16q0Fyhy0fx7mQ8AAAAFHRSTlMAIN/vcL+fMBCQQI+vz2Bgz4BQb5vSjyAAAAM8SURBVGje1doHctswEAVQEOykmh0g5RNuBFNJ2+m5/81iWcrs2AJlFqyT/Au8WX4MLWMphiY7jcrFRoYAEMo4LqMiEz4TRImEI3KxTv0IRbkDbKXbxhh1F2OaVld2ByXFXCE7WQJA1RnlSNNV9dZZBzOItAy3QqOOpLl3kqlMEAOwJPSmraYyWQmgMmpQzDTmRUjEUEauRz8pS8RgJg5GjVG3anS6GmE0uA16UuOHKYc9qg2g1cRoQAYDDInaqMkx9QAlDanxaYpFmD5pVGpmKlKOGLxKQMZcJejvnIyZSn/7ElZ5isUmcxql4+zOOMml810CkDFfASJn6Vp5jHaVH1PpvsqPHxsrKsRfLdHB6e0ejTsh6kFahNkDJEGlfCPKonwwCGAOkC8Xrtxo/f29K98OEAME7kEIuXjlyketr9648kHrnu5pEA7EAKljEE8IjZI/GoQBMXTAVqgUD6IsTvaIRMuFNFjujAK14kIUUFDtPAhVL9HwIQ3k1khRKz5EAQGdLS6kun8XL9BxIh0SqoQLMdtSMtSKE1FAJgpYXsTiVESouBBqPofmRTRyEaPlRVos7pCGC6F3pIThQugMh/xIKADVg9x8cuWH1r+uXPnZgyigHxmdfxe5fuvKmdbnl67c9iNHij976co7rS9fu3J+pHjJj0ixRMOLNIjFAi0v0t4hOTQXQi/ICBUXQq/6U1hexKKgP79cCJCJ7RnmQujXXYKOE+mwEIKa50EqrO+QADUnUiOlH9zeEapkmxwVH1IhoX+CuJAa+/XKEg0X0kKKXU5guRCL9R7JQhgGhC4+qHr/CNW+/4/OeEdoELq2Y0BokP6rqM9nrlxrfXvuytfeqyhqxXr/3UWD0AFrfSPdwTV3xHHRuX7+K1v+y2d6YGzX6JTc70Igd6/+lj5XG/LZlzT86yb34ux/WM9tjb+/zORfy5IyZ8G8IeNY8jmr8jwTwxKFqLvxRktL/yEJ4vHDGEufLwzMSo7+EIPGGJwgGfdJCbUxgWmfJhoLelLTmPqpz3wAhHkqpidYyXunc0Km2wrYnGRiZork+KdXeSG8JF0tJByRSRQIn8mKKI/jP5/DLRd5dDr4If0GDemh5W2BeAQAAAAASUVORK5CYII=)å¾®è½¯ç¿»è¯

å è´¹æ¨¡å

![](data:image/png;base64,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)è°·æ­ç¿»è¯

![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAMAAABHPGVmAAAAqFBMVEUAAADn5+fm5ubm5ubm5ubm5ubm5ubq6urf39/k5OTn5+fm5ubm5ubm5ubn5+fk5OTl5eXm5ubm5ubo6Oj////z8/MFpvDzUyX/ugiBvAbm5ubv7+/9/f1JvPH8ykvzgGD9wimRwyjp6ens7Oz6+vonsfEnsfChzEmhy0nzakPzakL39/f19fVfw/HzkHT70GF4zPLzoYn61nu513mu0mXzf16q0Fyhy0fx7mQ8AAAAFHRSTlMAIN/vcL+fMBCQQI+vz2Bgz4BQb5vSjyAAAAM8SURBVGje1doHctswEAVQEOykmh0g5RNuBFNJ2+m5/81iWcrs2AJlFqyT/Au8WX4MLWMphiY7jcrFRoYAEMo4LqMiEz4TRImEI3KxTv0IRbkDbKXbxhh1F2OaVld2ByXFXCE7WQJA1RnlSNNV9dZZBzOItAy3QqOOpLl3kqlMEAOwJPSmraYyWQmgMmpQzDTmRUjEUEauRz8pS8RgJg5GjVG3anS6GmE0uA16UuOHKYc9qg2g1cRoQAYDDInaqMkx9QAlDanxaYpFmD5pVGpmKlKOGLxKQMZcJejvnIyZSn/7ElZ5isUmcxql4+zOOMml810CkDFfASJn6Vp5jHaVH1PpvsqPHxsrKsRfLdHB6e0ejTsh6kFahNkDJEGlfCPKonwwCGAOkC8Xrtxo/f29K98OEAME7kEIuXjlyketr9648kHrnu5pEA7EAKljEE8IjZI/GoQBMXTAVqgUD6IsTvaIRMuFNFjujAK14kIUUFDtPAhVL9HwIQ3k1khRKz5EAQGdLS6kun8XL9BxIh0SqoQLMdtSMtSKE1FAJgpYXsTiVESouBBqPofmRTRyEaPlRVos7pCGC6F3pIThQugMh/xIKADVg9x8cuWH1r+uXPnZgyigHxmdfxe5fuvKmdbnl67c9iNHij976co7rS9fu3J+pHjJj0ixRMOLNIjFAi0v0t4hOTQXQi/ICBUXQq/6U1hexKKgP79cCJCJ7RnmQujXXYKOE+mwEIKa50EqrO+QADUnUiOlH9zeEapkmxwVH1IhoX+CuJAa+/XKEg0X0kKKXU5guRCL9R7JQhgGhC4+qHr/CNW+/4/OeEdoELq2Y0BokP6rqM9nrlxrfXvuytfeqyhqxXr/3UWD0AFrfSPdwTV3xHHRuX7+K1v+y2d6YGzX6JTc70Igd6/+lj5XG/LZlzT86yb34ux/WM9tjb+/zORfy5IyZ8G8IeNY8jmr8jwTwxKFqLvxRktL/yEJ4vHDGEufLwzMSo7+EIPGGJwgGfdJCbUxgWmfJhoLelLTmPqpz3wAhHkqpidYyXunc0Km2wrYnGRiZork+KdXeSG8JF0tJByRSRQIn8mKKI/jP5/DLRd5dDr4If0GDemh5W2BeAQAAAAASUVORK5CYII=)å¾®è½¯ç¿»è¯

![](data:image/png;base64,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)GLM-4 Flash

![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAMAAABHPGVmAAAAbFBMVEUAAADn5+fm5ubm5ubn5+fm5ubm5ubf39/k5OTq6urm5ubn5+fm5ubm5ubm5ubl5eXm5ubm5ubk5OT///9uKfXm5ub8/Pzw8PDbyf339/fp6en19fXs7OzSvPzt5P6kefmSX/eARPZ3N/b28f5a33/2AAAAE3RSTlMAIN/vcL+fEJAwYECPr8/PgFAwyaKKbwAAAwxJREFUaN7VmoF2ojAQRZMQIICgNk4wJNra/v8/rtjtzukaKYGMe/b+wD0zLyJkhs2l3MtNuxUZXMlEnm9kU7KUcFkICCDaukpjaDafAt87a4zRV4yx1vX+U1Q0aw3lroMrvTM6gHH9MHpqvkJRbbLRYPUE9uYplmp4PjYJDY89fqmm3IxFGD0L0y/SyAwVczWiju6UR8VsTc6jyhisjsYNkMmINLBTscVs5rVqC+D0QhyA4DMcAgajF2OGGZYqw8SXWTxk1Y+OXq+kR8uEg9bC0bHWwicyR8c6y+P0BXidCA/bMujY4NldjRnCv0oJYHQyDIAMhu50Qlwo/BxDTxV+/rejxkDSxSLvTq/TibGQfT9hBfQ6Of77CeN4shJiADhhIZg9YSFYSkVXCJaiqApBDB6wGrwmwsPuz9PXaiIsdOxGA4MmA6AhjB2jp+sW9kuMjpfYbp0uh4e8ne/7xcezFdmt8/thgrf7fsmrpI18/h4Pk9z/eRW3SAylxIyhlBgJiUQDlKwBTyvxsGcSeioJJq/A0UocKJaDpZVYaOklBjo8wXQSwbJYyWu0JGMAOsTHMcwJHdMSBOCB5PR+WMYlQnJZ6Hg/RUgO07yejmE+dFASDv4HR+QbCxMLJMc4iWAdtcRCzlqw9BIFjlbiQOGjPr0EH/V78LQSDw3+/VJJAEp8kUgvwRcJVoCjlDhoGQsn/zb5gDpH5V5fJTwUynnCcjnpCAaonvXCzRTtp0NB/xE0QMNudDT9wm6N7Cg/TOvfkjLwx5X04oMyeox95AUvu6gKwWs7qkLor6IQhQeMoBA8YDa1w91dc0uKi876+Ve29JfP2DCya3REpR0IKBai7FKONsTThzT046bw4Ox/GM+Njn8/zKQfy6JlzYB5y9kc1JpRuSojhv4LirE49J8Dz+OLMR7XF2ZSi+hFDCxjNryIWynBNCI1Ecsx2KlFmuGnNR8AyFTFlsNrMXoeLyzBle2uZCtpCly9sl+rVwZXr1TDklDVbXiJrJCcpaRspMrzr3W4rlVyP7tJvwCZPk/t1KobQwAAAABJRU5ErkJggg==)ç¡ åºæµå¨ç¿»è¯

é«çº§æ¨¡å

![](data:image/png;base64,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)GLM-4.5 Air![](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgZmlsbD0ibm9uZSI+PHBhdGggZmlsbD0iI0ZGQzczNiIgZD0iTTMgN2gxN3YxMEgzeiIvPjxwYXRoIGZpbGw9InVybCgjYSkiIGQ9Ik02Ljg5NyA5LjI0MmMuNDE1IDAgLjcyLjExMS45MjguMzQ3LjIwNy4yMzUuMzE4LjUyNy4zMTguODczcy0uMTEuNjIzLS4zMTguODQ1Yy0uMjA4LjIyMi0uNTI3LjMzMy0uOTI4LjMzM2gtMS4zM1Y5LjI0MmgxLjMzWm05Ljg0NiAxLjc4OGMuMzg4IDAgLjY2NS4xNTIuODQ1LjQ1Ny4xNTIuMjY0LjIzNS41ODIuMjYzLjk4NHYuMzE5YzAgLjQ5OS0uMDgzLjg4Ny0uMjYzIDEuMTkyLS4xOC4zMDQtLjQ1Ny40NTctLjgzLjQ1Ny0uMzg5IDAtLjY2Ni0uMTUzLS44NDYtLjQ0NC0uMTUyLS4yNjMtLjIzNS0uNTk1LS4yNjMtMS4wMTF2LS4yOTFjMC0uNDg1LjA4My0uODczLjI2My0xLjE3OC4xOC0uMzA1LjQ0My0uNDg1LjgzMS0uNDg1Wm0tMy40MDctMS4xMzZhMS4xNyAxLjE3IDAgMCAwLS43MDYuMjM1IDEuNDgyIDEuNDgyIDAgMCAwLS40MTUuNWwtLjA4My4xNjUtLjA3LS44MDNoLTEuMzU3djUuNDMyaDEuNDU0di0zLjY1OWEuODguODggMCAwIDEgLjMxOS0uMzg4Yy4xMS0uMDY5LjI1LS4xMS40MTUtLjEyNGguMTI1bC41NC4wMTQuMTY2LTEuMzE3Yy0uMDctLjAxNC0uMTI0LS4wMjgtLjE5NC0uMDQxLS4wNTUtLjAxNC0uMTI0LS4wMTQtLjE5NC0uMDE0Wk02Ljg5NiA4LjEySDQuMTE0djcuMzE3aDEuNDY4VjEyLjc5aDEuMzNjLjg0NCAwIDEuNDk1LS4yMDggMS45OC0uNjM4LjQ4NS0uNDMuNzItLjk4My43Mi0xLjY5cy0uMjM1LTEuMjYxLS43Mi0xLjY5Yy0uNDQzLS4zODktMS4wMzktLjYxLTEuNzczLS42MzhsLS4yMjEtLjAxNFptOS44NDcgMS43NzRjLS44MDMgMC0xLjQyNi4yNjMtMS44ODMuNzc2LS40MTYuNDctLjYzNyAxLjA2Ny0uNjc5IDEuNzczdi4zMzNjMCAuODE4LjIyMiAxLjQ4My42NzkgMS45OTUuNDU3LjUxMyAxLjA4Ljc3NiAxLjg4My43NzYuODA0IDAgMS40MjctLjI2MyAxLjg4NC0uNzc2LjQxNS0uNDcuNjM3LTEuMDUzLjY3OC0xLjc3M3YtLjMzM2MwLS44MTctLjIyMS0xLjQ4Mi0uNjc4LTEuOTk1LS40NTctLjUxMy0xLjA4LS43NzYtMS44ODQtLjc3NlpNMTguMDAzIDZhNiA2IDAgMCAxIDAgMTJIMFY5LjQyM0EzLjQyIDMuNDIgMCAwIDEgMy40MiA2aDE0LjU4M1oiLz48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9ImEiIHgxPSI3LjUiIHgyPSIyMiIgeTE9IjE5IiB5Mj0iNiIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPjxzdG9wIHN0b3AtY29sb3I9IiMyMjIiLz48c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiM2OTY5NjkiLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48L3N2Zz4=)

![](data:image/png;base64,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)DeepSeek V3![](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgZmlsbD0ibm9uZSI+PHBhdGggZmlsbD0iI0ZGQzczNiIgZD0iTTMgN2gxN3YxMEgzeiIvPjxwYXRoIGZpbGw9InVybCgjYSkiIGQ9Ik02Ljg5NyA5LjI0MmMuNDE1IDAgLjcyLjExMS45MjguMzQ3LjIwNy4yMzUuMzE4LjUyNy4zMTguODczcy0uMTEuNjIzLS4zMTguODQ1Yy0uMjA4LjIyMi0uNTI3LjMzMy0uOTI4LjMzM2gtMS4zM1Y5LjI0MmgxLjMzWm05Ljg0NiAxLjc4OGMuMzg4IDAgLjY2NS4xNTIuODQ1LjQ1Ny4xNTIuMjY0LjIzNS41ODIuMjYzLjk4NHYuMzE5YzAgLjQ5OS0uMDgzLjg4Ny0uMjYzIDEuMTkyLS4xOC4zMDQtLjQ1Ny40NTctLjgzLjQ1Ny0uMzg5IDAtLjY2Ni0uMTUzLS44NDYtLjQ0NC0uMTUyLS4yNjMtLjIzNS0uNTk1LS4yNjMtMS4wMTF2LS4yOTFjMC0uNDg1LjA4My0uODczLjI2My0xLjE3OC4xOC0uMzA1LjQ0My0uNDg1LjgzMS0uNDg1Wm0tMy40MDctMS4xMzZhMS4xNyAxLjE3IDAgMCAwLS43MDYuMjM1IDEuNDgyIDEuNDgyIDAgMCAwLS40MTUuNWwtLjA4My4xNjUtLjA3LS44MDNoLTEuMzU3djUuNDMyaDEuNDU0di0zLjY1OWEuODguODggMCAwIDEgLjMxOS0uMzg4Yy4xMS0uMDY5LjI1LS4xMS40MTUtLjEyNGguMTI1bC41NC4wMTQuMTY2LTEuMzE3Yy0uMDctLjAxNC0uMTI0LS4wMjgtLjE5NC0uMDQxLS4wNTUtLjAxNC0uMTI0LS4wMTQtLjE5NC0uMDE0Wk02Ljg5NiA4LjEySDQuMTE0djcuMzE3aDEuNDY4VjEyLjc5aDEuMzNjLjg0NCAwIDEuNDk1LS4yMDggMS45OC0uNjM4LjQ4NS0uNDMuNzItLjk4My43Mi0xLjY5cy0uMjM1LTEuMjYxLS43Mi0xLjY5Yy0uNDQzLS4zODktMS4wMzktLjYxLTEuNzczLS42MzhsLS4yMjEtLjAxNFptOS44NDcgMS43NzRjLS44MDMgMC0xLjQyNi4yNjMtMS44ODMuNzc2LS40MTYuNDctLjYzNyAxLjA2Ny0uNjc5IDEuNzczdi4zMzNjMCAuODE4LjIyMiAxLjQ4My42NzkgMS45OTUuNDU3LjUxMyAxLjA4Ljc3NiAxLjg4My43NzYuODA0IDAgMS40MjctLjI2MyAxLjg4NC0uNzc2LjQxNS0uNDcuNjM3LTEuMDUzLjY3OC0xLjc3M3YtLjMzM2MwLS44MTctLjIyMS0xLjQ4Mi0uNjc4LTEuOTk1LS40NTctLjUxMy0xLjA4LS43NzYtMS44ODQtLjc3NlpNMTguMDAzIDZhNiA2IDAgMCAxIDAgMTJIMFY5LjQyM0EzLjQyIDMuNDIgMCAwIDEgMy40MiA2aDE0LjU4M1oiLz48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9ImEiIHgxPSI3LjUiIHgyPSIyMiIgeTE9IjE5IiB5Mj0iNiIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPjxzdG9wIHN0b3AtY29sb3I9IiMyMjIiLz48c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiM2OTY5NjkiLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48L3N2Zz4=)

![](data:image/png;base64,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)GPT-5 mini![](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgZmlsbD0ibm9uZSI+PHBhdGggZmlsbD0iI0ZGQzczNiIgZD0iTTMgN2gxN3YxMEgzeiIvPjxwYXRoIGZpbGw9InVybCgjYSkiIGQ9Ik02Ljg5NyA5LjI0MmMuNDE1IDAgLjcyLjExMS45MjguMzQ3LjIwNy4yMzUuMzE4LjUyNy4zMTguODczcy0uMTEuNjIzLS4zMTguODQ1Yy0uMjA4LjIyMi0uNTI3LjMzMy0uOTI4LjMzM2gtMS4zM1Y5LjI0MmgxLjMzWm05Ljg0NiAxLjc4OGMuMzg4IDAgLjY2NS4xNTIuODQ1LjQ1Ny4xNTIuMjY0LjIzNS41ODIuMjYzLjk4NHYuMzE5YzAgLjQ5OS0uMDgzLjg4Ny0uMjYzIDEuMTkyLS4xOC4zMDQtLjQ1Ny40NTctLjgzLjQ1Ny0uMzg5IDAtLjY2Ni0uMTUzLS44NDYtLjQ0NC0uMTUyLS4yNjMtLjIzNS0uNTk1LS4yNjMtMS4wMTF2LS4yOTFjMC0uNDg1LjA4My0uODczLjI2My0xLjE3OC4xOC0uMzA1LjQ0My0uNDg1LjgzMS0uNDg1Wm0tMy40MDctMS4xMzZhMS4xNyAxLjE3IDAgMCAwLS43MDYuMjM1IDEuNDgyIDEuNDgyIDAgMCAwLS40MTUuNWwtLjA4My4xNjUtLjA3LS44MDNoLTEuMzU3djUuNDMyaDEuNDU0di0zLjY1OWEuODguODggMCAwIDEgLjMxOS0uMzg4Yy4xMS0uMDY5LjI1LS4xMS40MTUtLjEyNGguMTI1bC41NC4wMTQuMTY2LTEuMzE3Yy0uMDctLjAxNC0uMTI0LS4wMjgtLjE5NC0uMDQxLS4wNTUtLjAxNC0uMTI0LS4wMTQtLjE5NC0uMDE0Wk02Ljg5NiA4LjEySDQuMTE0djcuMzE3aDEuNDY4VjEyLjc5aDEuMzNjLjg0NCAwIDEuNDk1LS4yMDggMS45OC0uNjM4LjQ4NS0uNDMuNzItLjk4My43Mi0xLjY5cy0uMjM1LTEuMjYxLS43Mi0xLjY5Yy0uNDQzLS4zODktMS4wMzktLjYxLTEuNzczLS42MzhsLS4yMjEtLjAxNFptOS44NDcgMS43NzRjLS44MDMgMC0xLjQyNi4yNjMtMS44ODMuNzc2LS40MTYuNDctLjYzNyAxLjA2Ny0uNjc5IDEuNzczdi4zMzNjMCAuODE4LjIyMiAxLjQ4My42NzkgMS45OTUuNDU3LjUxMyAxLjA4Ljc3NiAxLjg4My43NzYuODA0IDAgMS40MjctLjI2MyAxLjg4NC0uNzc2LjQxNS0uNDcuNjM3LTEuMDUzLjY3OC0xLjc3M3YtLjMzM2MwLS44MTctLjIyMS0xLjQ4Mi0uNjc4LTEuOTk1LS40NTctLjUxMy0xLjA4LS43NzYtMS44ODQtLjc3NlpNMTguMDAzIDZhNiA2IDAgMCAxIDAgMTJIMFY5LjQyM0EzLjQyIDMuNDIgMCAwIDEgMy40MiA2aDE0LjU4M1oiLz48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9ImEiIHgxPSI3LjUiIHgyPSIyMiIgeTE9IjE5IiB5Mj0iNiIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPjxzdG9wIHN0b3AtY29sb3I9IiMyMjIiLz48c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiM2OTY5NjkiLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48L3N2Zz4=)

![](data:image/png;base64,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)Claude 4.5 Haiku![](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgZmlsbD0ibm9uZSI+PHBhdGggZmlsbD0iI0ZGQzczNiIgZD0iTTMgN2gxN3YxMEgzeiIvPjxwYXRoIGZpbGw9InVybCgjYSkiIGQ9Ik02Ljg5NyA5LjI0MmMuNDE1IDAgLjcyLjExMS45MjguMzQ3LjIwNy4yMzUuMzE4LjUyNy4zMTguODczcy0uMTEuNjIzLS4zMTguODQ1Yy0uMjA4LjIyMi0uNTI3LjMzMy0uOTI4LjMzM2gtMS4zM1Y5LjI0MmgxLjMzWm05Ljg0NiAxLjc4OGMuMzg4IDAgLjY2NS4xNTIuODQ1LjQ1Ny4xNTIuMjY0LjIzNS41ODIuMjYzLjk4NHYuMzE5YzAgLjQ5OS0uMDgzLjg4Ny0uMjYzIDEuMTkyLS4xOC4zMDQtLjQ1Ny40NTctLjgzLjQ1Ny0uMzg5IDAtLjY2Ni0uMTUzLS44NDYtLjQ0NC0uMTUyLS4yNjMtLjIzNS0uNTk1LS4yNjMtMS4wMTF2LS4yOTFjMC0uNDg1LjA4My0uODczLjI2My0xLjE3OC4xOC0uMzA1LjQ0My0uNDg1LjgzMS0uNDg1Wm0tMy40MDctMS4xMzZhMS4xNyAxLjE3IDAgMCAwLS43MDYuMjM1IDEuNDgyIDEuNDgyIDAgMCAwLS40MTUuNWwtLjA4My4xNjUtLjA3LS44MDNoLTEuMzU3djUuNDMyaDEuNDU0di0zLjY1OWEuODguODggMCAwIDEgLjMxOS0uMzg4Yy4xMS0uMDY5LjI1LS4xMS40MTUtLjEyNGguMTI1bC41NC4wMTQuMTY2LTEuMzE3Yy0uMDctLjAxNC0uMTI0LS4wMjgtLjE5NC0uMDQxLS4wNTUtLjAxNC0uMTI0LS4wMTQtLjE5NC0uMDE0Wk02Ljg5NiA4LjEySDQuMTE0djcuMzE3aDEuNDY4VjEyLjc5aDEuMzNjLjg0NCAwIDEuNDk1LS4yMDggMS45OC0uNjM4LjQ4NS0uNDMuNzItLjk4My43Mi0xLjY5cy0uMjM1LTEuMjYxLS43Mi0xLjY5Yy0uNDQzLS4zODktMS4wMzktLjYxLTEuNzczLS42MzhsLS4yMjEtLjAxNFptOS44NDcgMS43NzRjLS44MDMgMC0xLjQyNi4yNjMtMS44ODMuNzc2LS40MTYuNDctLjYzNyAxLjA2Ny0uNjc5IDEuNzczdi4zMzNjMCAuODE4LjIyMiAxLjQ4My42NzkgMS45OTUuNDU3LjUxMyAxLjA4Ljc3NiAxLjg4My43NzYuODA0IDAgMS40MjctLjI2MyAxLjg4NC0uNzc2LjQxNS0uNDcuNjM3LTEuMDUzLjY3OC0xLjc3M3YtLjMzM2MwLS44MTctLjIyMS0xLjQ4Mi0uNjc4LTEuOTk1LS40NTctLjUxMy0xLjA4LS43NzYtMS44ODQtLjc3NlpNMTguMDAzIDZhNiA2IDAgMCAxIDAgMTJIMFY5LjQyM0EzLjQyIDMuNDIgMCAwIDEgMy40MiA2aDE0LjU4M1oiLz48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9ImEiIHgxPSI3LjUiIHgyPSIyMiIgeTE9IjE5IiB5Mj0iNiIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPjxzdG9wIHN0b3AtY29sb3I9IiMyMjIiLz48c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiM2OTY5NjkiLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48L3N2Zz4=)

![](data:image/png;base64,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)Gemini 2.5 Flash![](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgZmlsbD0ibm9uZSI+PHBhdGggZmlsbD0iI0ZGQzczNiIgZD0iTTMgN2gxN3YxMEgzeiIvPjxwYXRoIGZpbGw9InVybCgjYSkiIGQ9Ik02Ljg5NyA5LjI0MmMuNDE1IDAgLjcyLjExMS45MjguMzQ3LjIwNy4yMzUuMzE4LjUyNy4zMTguODczcy0uMTEuNjIzLS4zMTguODQ1Yy0uMjA4LjIyMi0uNTI3LjMzMy0uOTI4LjMzM2gtMS4zM1Y5LjI0MmgxLjMzWm05Ljg0NiAxLjc4OGMuMzg4IDAgLjY2NS4xNTIuODQ1LjQ1Ny4xNTIuMjY0LjIzNS41ODIuMjYzLjk4NHYuMzE5YzAgLjQ5OS0uMDgzLjg4Ny0uMjYzIDEuMTkyLS4xOC4zMDQtLjQ1Ny40NTctLjgzLjQ1Ny0uMzg5IDAtLjY2Ni0uMTUzLS44NDYtLjQ0NC0uMTUyLS4yNjMtLjIzNS0uNTk1LS4yNjMtMS4wMTF2LS4yOTFjMC0uNDg1LjA4My0uODczLjI2My0xLjE3OC4xOC0uMzA1LjQ0My0uNDg1LjgzMS0uNDg1Wm0tMy40MDctMS4xMzZhMS4xNyAxLjE3IDAgMCAwLS43MDYuMjM1IDEuNDgyIDEuNDgyIDAgMCAwLS40MTUuNWwtLjA4My4xNjUtLjA3LS44MDNoLTEuMzU3djUuNDMyaDEuNDU0di0zLjY1OWEuODguODggMCAwIDEgLjMxOS0uMzg4Yy4xMS0uMDY5LjI1LS4xMS40MTUtLjEyNGguMTI1bC41NC4wMTQuMTY2LTEuMzE3Yy0uMDctLjAxNC0uMTI0LS4wMjgtLjE5NC0uMDQxLS4wNTUtLjAxNC0uMTI0LS4wMTQtLjE5NC0uMDE0Wk02Ljg5NiA4LjEySDQuMTE0djcuMzE3aDEuNDY4VjEyLjc5aDEuMzNjLjg0NCAwIDEuNDk1LS4yMDggMS45OC0uNjM4LjQ4NS0uNDMuNzItLjk4My43Mi0xLjY5cy0uMjM1LTEuMjYxLS43Mi0xLjY5Yy0uNDQzLS4zODktMS4wMzktLjYxLTEuNzczLS42MzhsLS4yMjEtLjAxNFptOS44NDcgMS43NzRjLS44MDMgMC0xLjQyNi4yNjMtMS44ODMuNzc2LS40MTYuNDctLjYzNyAxLjA2Ny0uNjc5IDEuNzczdi4zMzNjMCAuODE4LjIyMiAxLjQ4My42NzkgMS45OTUuNDU3LjUxMyAxLjA4Ljc3NiAxLjg4My43NzYuODA0IDAgMS40MjctLjI2MyAxLjg4NC0uNzc2LjQxNS0uNDcuNjM3LTEuMDUzLjY3OC0xLjc3M3YtLjMzM2MwLS44MTctLjIyMS0xLjQ4Mi0uNjc4LTEuOTk1LS40NTctLjUxMy0xLjA4LS43NzYtMS44ODQtLjc3NlpNMTguMDAzIDZhNiA2IDAgMCAxIDAgMTJIMFY5LjQyM0EzLjQyIDMuNDIgMCAwIDEgMy40MiA2aDE0LjU4M1oiLz48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9ImEiIHgxPSI3LjUiIHgyPSIyMiIgeTE9IjE5IiB5Mj0iNiIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPjxzdG9wIHN0b3AtY29sb3I9IiMyMjIiLz48c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiM2OTY5NjkiLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48L3N2Zz4=)

![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAMAAABHPGVmAAAC9FBMVEUAAADn5+fm5ubm5ubm5ubm5ubm5ubq6urf39/k5OTn5+fm5ubm5ubm5ubn5+fk5OTl5eXm5ubm5ubo6Oj////m5uZvevRidPB8gfhXbu1AYuYjVN5MaOo9n+b8/PwwXOJNoutsqPWLrv5cpfDv7++Mifzr7/5ji/Jahe96q/pPfuxCdujp6enx8fFrkfV0l/f6+vrs7OwybOP9/f33+f9/nfv39/f09PX6+//z9v78/f9qePNSgO319fZnp/Roj/Q8Z+JzqvdDZOc0XePw9P5Zpe9ZcO5LfOuIh/tch/BQa+tIZukrWeHt8fyGhvp6gPdldvFecu9VpO5EeOk1buXo7f3Q3ft8m/pylfZ3f/ZOautDoOg7cubu8v7k6/3U3/3b5PzI1fp0ffVnd/FtgPBWg+5Ube1Lous6YOXP2PzM2vuBrfu/0fqyyPlwqfZzfPVkpvNipvJhc/BPo+xIoeo/Yub09//e5fy8zvuMp/u2zPqlvfp4qvmDovi1xPd4mfesvvaHk/Ztk/V6ifRsefNykvJkjPJfiPFTo+09YeU3XuMxYeIoV+CFrf2nx/uprPt/q/uTlfuIkfvC0fqBhPmbuPimsPiFsveMtvaUr/aEpfZ7nfVuk/V2f/WKqPOIn/NomvOAnu9Zg+5bc+5pjO1HeepLZ+lGb+bp7v7g6v6Xtv7d4fzV2fzHy/u9wvuevPmTnPmuw/eao/eBj/eAoPaEjPZxe/WjtvN0mvJsk/KcrvFfpfFlfO/u7u5WgO5zlOxJeepdgehUeudAdeeRsf7l6P2uwvylwfyPq/zf5vvN0fuws/t7q/vW4PqWoPqgqPm6xvi30/ebsPefrfeKnPfS3Pa9y/a2xvWjuvWgsvVxn/WOmfWBuPSnuvOUrfOEmfNqovJurPFprPBuju58lO1ReuxihOlAn+dFauY2ZuTF0Pq0uvrD3Pmaq/jv8faWvPaQqfZ7ovZ9svN2kfPB0e+vxO9ie+1eh+tmhetJcupzkOhQcudWxvkSAAAAFHRSTlMAIN/vcL+fMBCQQI+vz2Bgz4BQb5vSjyAAAAjmSURBVGjezZp1WFNRGMZdwgD7ng1rKkwMQDeGgylDUcTEQjBRUezA7u7u7u7u7u7u7u72H7/v3CHGzt3d2PPo++d8Hn/P+73f+c7hnJtGrNwzyT29MkhlBCSTKhSecg/3NK6URK6UEhuSeqV3cw3Bw5MHGAJDTHqtkQMZtXpTSKCBByk9Uktwz5iWgHQWLWdDeosuADnpJalAuHliBIF6TkB6ylE6i5EosEhAsCfTTmcx7p5oQsuJklbnFCazDBA0ZbEYzMbhShmYLtgYhcQhGwEmzmFZAohM7kAaOkal7JvxFFeqDISEcE4qBJKRiGBISYCWc1raABEUNxkxYKmcpxiIzM0uQ8elUjqkCDMCuVQrUJAioQyXUCQCmes4l0jHTl9KDJyLZCAZbO+bnti7LpIxwPaqzEwIMFwlLSFym6GHcC5UiK3wFSJDj547sHukuPAVfzLSiQpE+6rPo+I7xo5uGVlETCzyv7rXwtmT/ujNb/tKZqucJ8+p0c2iQ+3uykT2e4cpRRQr8uK2Rzlz5qzQME+eMt6nz9Q32+9jz9+M2O8sc+fLcxfnRBXNU6ait/f688/qxtvtMIljRuIWPMnalIcAAtSg/5sEu+NF4YCR4LjZWa0qaYUkqdUDGs72E0zGSIibWCOmi9sS55cvXwIQHUs2LUkhDdTqopUrJ/btUz9Y0IpKpJH62x58yg5CSsemHb/2H+ddqYEaIBqNJirx9uZmAqmkNFg6spNjqUh83NXELI3LleMpoHmz13hXUmOxNJoqWbI03jE7IVagwTL+nL6s809ofP1e7+dnQdWiFMAMnPiyUk1gVNZo2tHfy325epK1avQkLc/wIAEcQ7G9bmuytIuyUkCLsmad1W0SGgEGQmrRH/eOj2b8D4R4CMce0vKCeoAGVYWnoEr08luJkGQj4A977v4ls2D0UmL75N5s3fqZap7SDimNG2Mwu+JCV/RVqzGQKJ5RAiFP9j3oZbFZLyky3FjVWgMIbCKrFxRQptbl/I4jA38qRxkdhw2DaTN8r82S8as+Hata3g0aNEgCSsOGWP+oKEppnGDmgpv1RwY0BJYvK0BwpGUr7md74uMs9iIWBgRUkzeDFM18xPSPxH6YBBWMggJC6GBk6FCAjGBALETJR2IPklKyHS1hgYMVcIYMagQQyGBAtBiKO7OB8yClktp7E+VQTOIk69RfVzQKA8kOmQtDMBR3WCUGQUilXyCV+x60DszlG6skQ5qWBAQwWBADyZRGzjw0wrZRcQKWrCadVKDrx0KTR8Gx/lG1sFjIwNTZkEBIXsU8pMAGCLsTauamJDSzcVVwyvB/nlhuUXmoFUIqCEFCYDkqiIkJqVixzATqZWbNJHVS31W/nlL8JiVisUo2hf4FAhtiIl4A0TMhVLTJkrzVlVZQHymU81EAAR/CEDojpUQrBCnjDRTUutjfT0GY/nWAYB6CEOxhGTGyIUiBZCZsPL3y4J8Mrkhw517lcaAIQ4xEloYQjgUZO5bnjB29crnZ5o5mPnPr/mJhCC4UAcj6C33HjRu3ZvTxVSsAwVDdLrd27/3+9Onw4cMXOwOZA7p2bcrZuCWdirC3507R9fucylt2V1jYAmcgOawKHyVwIulUr9XEwry6MiEYvCAEVftuN0YmLY/0LgRCRs9lzOCxhYUhHTp0aFLq3o24v92Ym0/dUKgGMKr3RsoRdgunZS5GK6N2k1ygITdaxof+kXm3aTMKFuwHlN7Ve1dnlktPFLBnmYQgj3MhpP2QIb6Tuy39jbKk1bS8xQoWLDgDKNULsSEmgLAHJB8H2mhftZSvr2/rUUt/6bL4VtPz5s1brBh6QUz16l3ZA5I96nkGqmrV9gAJjxjVKeVfu2wZnBcEZkAYfu+u7FGfiblp/WSUqjrEFyG5J3fhktVqa758ZVMgqJ6sTctDYPuFzK2QUqWQ0TY8Yko9654Vt6VsPqAAZtAgrBjG35O9/bJ7OEeTDk1orUrxPsLDc0ccDqbrw29ao7BGQEkxAxSAME93SmJhQagPX2RsbxueG9R6cj3sMHNC2bACYY3mAQWCwfixyWxDLMQLIHLW4e4xhbT3HQKUtrm3IySixcRIMNJ5VukCoLB8yZRBSNnAONzhRa6EFUoungECBlVE/vz56xbhzOMH+/OQZEpBpEy3CQkgbkIHbmvvgtqEo48eEQjpFsnFXokpEANeQPmoaMkAwogEpWKslBev71WlfdWmDU2kdUQPgCyryzUv5h/jX7o0YsLmJcc/8BzEZataSsE/goKXnp1yBxlt29DUgQHyqee3trS/v39MzB5aMtplZQdO7dI51Ha1PCiEPSPjE1a/u+ObmzIikHFiTH6f8c2n7q+DlD18+rvAzIYrzSMZgwurhcrIvrHzSzh3l2bemtoYM3KMz6HuW+pUA8jChTFYMVgwW+c2C2GsNQP2FpW7jLUecd11j0BG/tzAACs+Pqun5QtCCBV6GbQ2UMzFB0bPVnSryQBBtfABrZ4eVm1/0H5ExBTwLz2wT2eOl0Ds1r/ojBxTodHNJ74FxMgWFHJg68KgakHVqtFc/Gcl+AWLvMFRoBW2zEfHd4dAWoz0QZWtExQUVAchC3d/PIkIYSPib3DqjZqCDFSjIAqp5v951iWTUfRVFKZisHel1vLwMh4SFkQppXdvxiOMaCO0wUycPUwXHvJwOEL23YzlhGX565pbjtnbU2wrhOypAIy18SJeUtI7c2UbvCTu0AGfhzkXz/0QHSriytbJy+dOdZt3X7Bgc3290fHLZ5Rc3FW9uV6fy7HOXaOjVBiLa4SBqGw//aV15dOG9B890rj+uemfPpy5/gmQTTFoU4MwGoDxPzzL8pTUPDBnEMGgq5LonDJj1BGiEvvJjBwe/S2OM0ziH/1REoXjZrQGxucLbKWTOoYxBhK2DbYZJRGP0QKCT8MpzE6TfYTeQBiVEo0J0OkFCWhCpqLrz1kMZIMci02Q1qIjoAwZ3VP96ZVS+NMrlUcal8gtnZftj8iUckjChXL3kKsUiuTP4dJ6qeSZRBfpB0lhGlCNRficAAAAAElFTkSuQmCC)GLM-4.5![](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgZmlsbD0ibm9uZSI+PHBhdGggZmlsbD0iI0ZGQzczNiIgZD0iTTMgN2gxN3YxMEgzeiIvPjxwYXRoIGZpbGw9InVybCgjYSkiIGQ9Ik02Ljg5NyA5LjI0MmMuNDE1IDAgLjcyLjExMS45MjguMzQ3LjIwNy4yMzUuMzE4LjUyNy4zMTguODczcy0uMTEuNjIzLS4zMTguODQ1Yy0uMjA4LjIyMi0uNTI3LjMzMy0uOTI4LjMzM2gtMS4zM1Y5LjI0MmgxLjMzWm05Ljg0NiAxLjc4OGMuMzg4IDAgLjY2NS4xNTIuODQ1LjQ1Ny4xNTIuMjY0LjIzNS41ODIuMjYzLjk4NHYuMzE5YzAgLjQ5OS0uMDgzLjg4Ny0uMjYzIDEuMTkyLS4xOC4zMDQtLjQ1Ny40NTctLjgzLjQ1Ny0uMzg5IDAtLjY2Ni0uMTUzLS44NDYtLjQ0NC0uMTUyLS4yNjMtLjIzNS0uNTk1LS4yNjMtMS4wMTF2LS4yOTFjMC0uNDg1LjA4My0uODczLjI2My0xLjE3OC4xOC0uMzA1LjQ0My0uNDg1LjgzMS0uNDg1Wm0tMy40MDctMS4xMzZhMS4xNyAxLjE3IDAgMCAwLS43MDYuMjM1IDEuNDgyIDEuNDgyIDAgMCAwLS40MTUuNWwtLjA4My4xNjUtLjA3LS44MDNoLTEuMzU3djUuNDMyaDEuNDU0di0zLjY1OWEuODguODggMCAwIDEgLjMxOS0uMzg4Yy4xMS0uMDY5LjI1LS4xMS40MTUtLjEyNGguMTI1bC41NC4wMTQuMTY2LTEuMzE3Yy0uMDctLjAxNC0uMTI0LS4wMjgtLjE5NC0uMDQxLS4wNTUtLjAxNC0uMTI0LS4wMTQtLjE5NC0uMDE0Wk02Ljg5NiA4LjEySDQuMTE0djcuMzE3aDEuNDY4VjEyLjc5aDEuMzNjLjg0NCAwIDEuNDk1LS4yMDggMS45OC0uNjM4LjQ4NS0uNDMuNzItLjk4My43Mi0xLjY5cy0uMjM1LTEuMjYxLS43Mi0xLjY5Yy0uNDQzLS4zODktMS4wMzktLjYxLTEuNzczLS42MzhsLS4yMjEtLjAxNFptOS44NDcgMS43NzRjLS44MDMgMC0xLjQyNi4yNjMtMS44ODMuNzc2LS40MTYuNDctLjYzNyAxLjA2Ny0uNjc5IDEuNzczdi4zMzNjMCAuODE4LjIyMiAxLjQ4My42NzkgMS45OTUuNDU3LjUxMyAxLjA4Ljc3NiAxLjg4My43NzYuODA0IDAgMS40MjctLjI2MyAxLjg4NC0uNzc2LjQxNS0uNDcuNjM3LTEuMDUzLjY3OC0xLjc3M3YtLjMzM2MwLS44MTctLjIyMS0xLjQ4Mi0uNjc4LTEuOTk1LS40NTctLjUxMy0xLjA4LS43NzYtMS44ODQtLjc3NlpNMTguMDAzIDZhNiA2IDAgMCAxIDAgMTJIMFY5LjQyM0EzLjQyIDMuNDIgMCAwIDEgMy40MiA2aDE0LjU4M1oiLz48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9ImEiIHgxPSI3LjUiIHgyPSIyMiIgeTE9IjE5IiB5Mj0iNiIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPjxzdG9wIHN0b3AtY29sb3I9IiMyMjIiLz48c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiM2OTY5NjkiLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48L3N2Zz4=)

![](data:image/png;base64,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)DeepL Pro![](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgZmlsbD0ibm9uZSI+PHBhdGggZmlsbD0iI0ZGQzczNiIgZD0iTTMgN2gxN3YxMEgzeiIvPjxwYXRoIGZpbGw9InVybCgjYSkiIGQ9Ik02Ljg5NyA5LjI0MmMuNDE1IDAgLjcyLjExMS45MjguMzQ3LjIwNy4yMzUuMzE4LjUyNy4zMTguODczcy0uMTEuNjIzLS4zMTguODQ1Yy0uMjA4LjIyMi0uNTI3LjMzMy0uOTI4LjMzM2gtMS4zM1Y5LjI0MmgxLjMzWm05Ljg0NiAxLjc4OGMuMzg4IDAgLjY2NS4xNTIuODQ1LjQ1Ny4xNTIuMjY0LjIzNS41ODIuMjYzLjk4NHYuMzE5YzAgLjQ5OS0uMDgzLjg4Ny0uMjYzIDEuMTkyLS4xOC4zMDQtLjQ1Ny40NTctLjgzLjQ1Ny0uMzg5IDAtLjY2Ni0uMTUzLS44NDYtLjQ0NC0uMTUyLS4yNjMtLjIzNS0uNTk1LS4yNjMtMS4wMTF2LS4yOTFjMC0uNDg1LjA4My0uODczLjI2My0xLjE3OC4xOC0uMzA1LjQ0My0uNDg1LjgzMS0uNDg1Wm0tMy40MDctMS4xMzZhMS4xNyAxLjE3IDAgMCAwLS43MDYuMjM1IDEuNDgyIDEuNDgyIDAgMCAwLS40MTUuNWwtLjA4My4xNjUtLjA3LS44MDNoLTEuMzU3djUuNDMyaDEuNDU0di0zLjY1OWEuODguODggMCAwIDEgLjMxOS0uMzg4Yy4xMS0uMDY5LjI1LS4xMS40MTUtLjEyNGguMTI1bC41NC4wMTQuMTY2LTEuMzE3Yy0uMDctLjAxNC0uMTI0LS4wMjgtLjE5NC0uMDQxLS4wNTUtLjAxNC0uMTI0LS4wMTQtLjE5NC0uMDE0Wk02Ljg5NiA4LjEySDQuMTE0djcuMzE3aDEuNDY4VjEyLjc5aDEuMzNjLjg0NCAwIDEuNDk1LS4yMDggMS45OC0uNjM4LjQ4NS0uNDMuNzItLjk4My43Mi0xLjY5cy0uMjM1LTEuMjYxLS43Mi0xLjY5Yy0uNDQzLS4zODktMS4wMzktLjYxLTEuNzczLS42MzhsLS4yMjEtLjAxNFptOS44NDcgMS43NzRjLS44MDMgMC0xLjQyNi4yNjMtMS44ODMuNzc2LS40MTYuNDctLjYzNyAxLjA2Ny0uNjc5IDEuNzczdi4zMzNjMCAuODE4LjIyMiAxLjQ4My42NzkgMS45OTUuNDU3LjUxMyAxLjA4Ljc3NiAxLjg4My43NzYuODA0IDAgMS40MjctLjI2MyAxLjg4NC0uNzc2LjQxNS0uNDcuNjM3LTEuMDUzLjY3OC0xLjc3M3YtLjMzM2MwLS44MTctLjIyMS0xLjQ4Mi0uNjc4LTEuOTk1LS40NTctLjUxMy0xLjA4LS43NzYtMS44ODQtLjc3NlpNMTguMDAzIDZhNiA2IDAgMCAxIDAgMTJIMFY5LjQyM0EzLjQyIDMuNDIgMCAwIDEgMy40MiA2aDE0LjU4M1oiLz48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9ImEiIHgxPSI3LjUiIHgyPSIyMiIgeTE9IjE5IiB5Mj0iNiIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPjxzdG9wIHN0b3AtY29sb3I9IiMyMjIiLz48c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiM2OTY5NjkiLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48L3N2Zz4=)

![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAMAAABHPGVmAAAAjVBMVEUAAADn5+fm5ubm5ubl5eXn5+fm5ubm5ubq6urf39/m5ubn5+fm5ubn5+fk5OTm5ubm5ub///98Vuvm5ube1fr8/Pzw8PDv6v3OwPeMa+339/fp6emtlfP19fXs7Oz39f6dgPC9qvWMbO2EYe22oPStlvPWy/mli/GVdu/m3/zGtfa+q/WdgfCEYu3FtfY8OLe9AAAAEXRSTlMAIN/vkHC/nzAQz0CvYGCAUGOTB44AAATYSURBVGje1Vprc6JAEOSNgDFhhzcKikbNXZL///NOUYcizD4Aq1LXH+6qkqq0Pd07O+6upgrvzbaWvmHCBabhOJYdeNozoduuAQSM5WrxHIbAuhFUyaaI4zi8II6LYpNUNyI3mMvgvfpwQbKJQwLxJimvPCt9BsXCMq8MRShA0fK4U2l051okZBDwVFNpPOsqIg6VECeTaGwTKZRpjNXoSlVIoU7j6KNklEU4GpsSTFvdDazUeDGWWql8gE04ERsAQ1fgMKCMw8mISwWWhYmOT2SpwFxIOZJwJhJkmcoxn0VHjtksOt9z5JjLwnffgCp8Eirw6X3TGmR3VpItspcACDnqqEV2jJRYAGzKdMk6z9kDf5XWPmW+IzH9LzsjS6pmvvOT40ViSLrP6/2DZKtoiz1Ir7hYa5aF3yhFyZYCzH7CXEmxUna6/Lt9kJwVc2z1hEiSFZ5bHyKU8kcxYfoIIRlbt/+jlP36gfcWf6Tey4XkeXq3n3EQcaQs5EIwvt+4WDhoOFIsVSEpy7FsXOxoKRiwF6ik8W1R53ySr5oO2Ct230ISXyybAAd6rfg3jgBKSdNKH2wUxM0GIBDZnmY3HNgayybEp8h6ulpdWu/xDT+YBBFZL6MdHqCk3d5GN3yEd5JIiE+W0fXS22wllBAssiLSpknJerW9eEn23zN2dEW8s4yzebmtJTHRrJQ7OipvOF3yaooHJXevzdVJTqy1jjTF0wJquf9V7uio/J2/q7xpNiT8+O5rRZIGU0I6bxG+H7teoerIWTC2WJpDLMV6P+wVH3m+5/eRAzvyt/olSRLu2GAwGTaVde9jNTV3E/YxwTwpEfEz7DYddrihUBk2+ySD3Snvy+vw/cP6r5pHYmoA5K+2w8EEtyxyDUXcEAOQJDj9YIzxZ4hBE/lkkYhEIuVA/Iydurynj4/wOZokJWIcEfFNm5MkxgBovFKMD8P4HjCA9VdT08ZjhEfFOO+E4L6LMSYi7CPJiBjveksUJyYyxgU42hJXvHqM8x9drqkxxiQJNsgxMe7im6MyjDHRILHVU9jTMd4OK9rc8MUistW/4aZFbV1kjDvXc4W5u4KA3n7xT1Ax7sX3B4709ktnGINDxLgTMuB45wwSmjtwnvwTufBTYFEJ35eaxnX+xBD0UHEUC0HfV+1XoFKc3/O2xYkYm/ogR8gSFjhw80m2soaAyPgDt2ZBIvI9lWbvtGuR0QORK/oSlO6x31I4EE6Q1Qq0Fj4U3F6f84SQkaKr1eJ1sOixGXJnkLWakApWdxKPs3Ed+SP3cRAp0cEHWk/3+lPWRz2IL9otsv3+jS4WrhXEYbifSYTIj+3SqI8z+8D4qgpRP8FBadt+fNdyIR0sImB0qKJhfOVCMGC4ViRHkRhfmZDN4Jjblp4849hzJAZ7+qBzNfbIFlfoXtl1R/nwWbCL5CqHz9MKFmV3HGvJMfpvXQhonv/Mqw3jly5pnn/dJLs4+x+u564cv3+Z+bxrWTnLnAtmHzmEmHdV7ilf+k8SU+ClvxJ0Z7yYuMLnC6p4McY/xEAZ6mLccU9K0I2xNOqPY7BSE2lK2TMfADCthTYd+ovR8nAfLMEF/qunzUTgdk+visfTq7h7emUF2lOweFnSj8hcW9eeCS+wLcd5PIfzl5b9plykfyzdKISafIeqAAAAAElFTkSuQmCC)Qwen Plus![](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgZmlsbD0ibm9uZSI+PHBhdGggZmlsbD0iI0ZGQzczNiIgZD0iTTMgN2gxN3YxMEgzeiIvPjxwYXRoIGZpbGw9InVybCgjYSkiIGQ9Ik02Ljg5NyA5LjI0MmMuNDE1IDAgLjcyLjExMS45MjguMzQ3LjIwNy4yMzUuMzE4LjUyNy4zMTguODczcy0uMTEuNjIzLS4zMTguODQ1Yy0uMjA4LjIyMi0uNTI3LjMzMy0uOTI4LjMzM2gtMS4zM1Y5LjI0MmgxLjMzWm05Ljg0NiAxLjc4OGMuMzg4IDAgLjY2NS4xNTIuODQ1LjQ1Ny4xNTIuMjY0LjIzNS41ODIuMjYzLjk4NHYuMzE5YzAgLjQ5OS0uMDgzLjg4Ny0uMjYzIDEuMTkyLS4xOC4zMDQtLjQ1Ny40NTctLjgzLjQ1Ny0uMzg5IDAtLjY2Ni0uMTUzLS44NDYtLjQ0NC0uMTUyLS4yNjMtLjIzNS0uNTk1LS4yNjMtMS4wMTF2LS4yOTFjMC0uNDg1LjA4My0uODczLjI2My0xLjE3OC4xOC0uMzA1LjQ0My0uNDg1LjgzMS0uNDg1Wm0tMy40MDctMS4xMzZhMS4xNyAxLjE3IDAgMCAwLS43MDYuMjM1IDEuNDgyIDEuNDgyIDAgMCAwLS40MTUuNWwtLjA4My4xNjUtLjA3LS44MDNoLTEuMzU3djUuNDMyaDEuNDU0di0zLjY1OWEuODguODggMCAwIDEgLjMxOS0uMzg4Yy4xMS0uMDY5LjI1LS4xMS40MTUtLjEyNGguMTI1bC41NC4wMTQuMTY2LTEuMzE3Yy0uMDctLjAxNC0uMTI0LS4wMjgtLjE5NC0uMDQxLS4wNTUtLjAxNC0uMTI0LS4wMTQtLjE5NC0uMDE0Wk02Ljg5NiA4LjEySDQuMTE0djcuMzE3aDEuNDY4VjEyLjc5aDEuMzNjLjg0NCAwIDEuNDk1LS4yMDggMS45OC0uNjM4LjQ4NS0uNDMuNzItLjk4My43Mi0xLjY5cy0uMjM1LTEuMjYxLS43Mi0xLjY5Yy0uNDQzLS4zODktMS4wMzktLjYxLTEuNzczLS42MzhsLS4yMjEtLjAxNFptOS44NDcgMS43NzRjLS44MDMgMC0xLjQyNi4yNjMtMS44ODMuNzc2LS40MTYuNDctLjYzNyAxLjA2Ny0uNjc5IDEuNzczdi4zMzNjMCAuODE4LjIyMiAxLjQ4My42NzkgMS45OTUuNDU3LjUxMyAxLjA4Ljc3NiAxLjg4My43NzYuODA0IDAgMS40MjctLjI2MyAxLjg4NC0uNzc2LjQxNS0uNDcuNjM3LTEuMDUzLjY3OC0xLjc3M3YtLjMzM2MwLS44MTctLjIyMS0xLjQ4Mi0uNjc4LTEuOTk1LS40NTctLjUxMy0xLjA4LS43NzYtMS44ODQtLjc3NlpNMTguMDAzIDZhNiA2IDAgMCAxIDAgMTJIMFY5LjQyM0EzLjQyIDMuNDIgMCAwIDEgMy40MiA2aDE0LjU4M1oiLz48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9ImEiIHgxPSI3LjUiIHgyPSIyMiIgeTE9IjE5IiB5Mj0iNiIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPjxzdG9wIHN0b3AtY29sb3I9IiMyMjIiLz48c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiM2OTY5NjkiLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48L3N2Zz4=)

é¡¶çº§æ¨¡å

![](data:image/png;base64,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)GPT-5![](data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyMCAyMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTE1LjAwMjkgNUMxNy43NjExIDUgMjAgNy4yNDAxOCAyMCAxMEMyMCAxMi43NTk4IDE3Ljc2MTEgMTUgMTUuMDAyOSAxNUgwVjcuODUyMTlDMCA2LjI3MDIxIDEuMjgxMDIgNSAyLjg1MDU1IDVIMTUuMDAyOVoiIGZpbGw9InVybCgjcGFpbnQwX2xpbmVhcl8zMTkyMV8yNDQ2OSkiLz4KPHBhdGggZD0iTTEwLjUxOTQgOC40Mjk5M0MxMC44ODkxIDguNDI5OTMgMTEuMTk5IDguNTAyNjkgMTEuNDQ5IDguNjQ4NDRDMTEuNjk5IDguNzk0MjcgMTEuODg2NyA5LjAxMDc4IDEyLjAxMTcgOS4yOTcyNEMxMi4xMzY2IDkuNTgzNjEgMTIuMTk5MSA5LjkzNzU5IDEyLjE5OTEgMTAuMzU5M1YxMi45MTQySDExLjI2MTZMMTEuMTgzNSAxMi40NDU0SDExLjE0NDRDMTAuOTU3IDEyLjYxMiAxMC43NTM5IDEyLjc0OTkgMTAuNTM1MyAxMi44NTkzQzEwLjMxNjUgMTIuOTY4NiAxMC4wNzk0IDEzLjAyMzQgOS44MjQyMiAxMy4wMjM0QzkuNTY5MDEgMTMuMDIzNCA5LjM0MjIgMTIuOTY4NiA5LjE0NDI5IDEyLjg1OTNDOC45NTE3MSAxMi43NDQ3IDguODAwNzMgMTIuNTg4MyA4LjY5MTQxIDEyLjM5MDVDOC41ODczNCAxMi4xOTI3IDguNTM1MTkgMTEuOTY4OSA4LjUzNTE2IDExLjcxOTFDOC41MzUxNiAxMS4yNTU2IDguNzM1OTIgMTAuODk1OCA5LjEzNjk2IDEwLjY0MDZDOS41MzgwMiAxMC4zODAzIDEwLjE3NjIgMTAuMjAzNCAxMS4wNTEgMTAuMTA5NkMxMS4wNDU4IDkuOTYzOTMgMTEuMDE5NyA5LjgzNjIzIDEwLjk3MjkgOS43MjY5M0MxMC45MjYxIDkuNjEyNDUgMTAuODQ3NyA5LjUyMTE4IDEwLjczODUgOS40NTM0OUMxMC42MzQ0IDkuMzg1ODEgMTAuNDkxIDkuMzUxNTkgMTAuMzA4OCA5LjM1MTU2QzEwLjEwNTcgOS4zNTE1NiA5LjkwNDk0IDkuMzkwNjMgOS43MDcwMyA5LjQ2ODc1QzkuNTA5MTEgOS41NDY4OCA5LjMwODM1IDkuNjQ4MzIgOS4xMDUyMiA5Ljc3MzMyTDguNjk5MzQgOS4wMDc5M0M4Ljg3MTE5IDguODk4NTggOS4wNTM1MyA4LjgwMTk1IDkuMjQ2MjIgOC43MTg2M0M5LjQzODgyIDguNjM1MzUgOS42NDE5NCA4LjU2ODA1IDkuODU1MzUgOC41MTU5OUMxMC4wNjg5IDguNDU4NzEgMTAuMjkwMyA4LjQyOTk0IDEwLjUxOTQgOC40Mjk5M1pNNC43NjU2MiA5Ljg0NDEyQzQuODI4MSAxMC4wMTU5IDQuODg3OCAxMC4xOTg0IDQuOTQ1MDcgMTAuMzkxQzUuMDAyMzIgMTAuNTc4NCA1LjA1OTk0IDEwLjc2MyA1LjExNzE5IDEwLjk0NTJINS4xNTYyNUM1LjIxODY5IDEwLjc2MzEgNS4yNzg0NSAxMC41NzgzIDUuMzM1NjkgMTAuMzkxQzUuMzkyOTYgMTAuMTk4NCA1LjQ0NzgyIDEwLjAxNTkgNS40OTk4OCA5Ljg0NDEyTDYuNDY4NTEgNy4xMjVINy43NTAyNFYxMi45MTQySDYuNjk1NTZWMTAuNTAwMkM2LjY5NTU2IDEwLjMxMjggNi43MDMxMyAxMC4xMDcxIDYuNzE4NzUgOS44ODMxOEM2LjczNDM3IDkuNjU5MjQgNi43NTI4NSA5LjQzNTEyIDYuNzczNjggOS4yMTExOEM2Ljc5OTcyIDguOTgyMDIgNi44MjMwNCA4Ljc3ODUyIDYuODQzODcgOC42MDE0NEg2LjgxMjc0TDYuMzM2MDYgOS45NjEzTDUuNDQ1NTYgMTIuMzkwNUg0Ljc4MTQ5TDMuODgzMDYgOS45NjEzTDMuNDIxNjMgOC42MDE0NEgzLjM5MDVDMy40MTEzNCA4Ljc3ODUyIDMuNDMyNTQgOC45ODIwMiAzLjQ1MzM3IDkuMjExMThDMy40NzQyIDkuNDM1MSAzLjQ5MjA3IDkuNjU5MjYgMy41MDc2OSA5Ljg4MzE4QzMuNTI4NTEgMTAuMTA3MSAzLjUzODgyIDEwLjMxMjggMy41Mzg4MiAxMC41MDAyVjEyLjkxNDJIMi41VjcuMTI1SDMuNzgxMTNMNC43NjU2MiA5Ljg0NDEyWk0xNC4zMjMxIDkuMzEyNUMxNC4zODU2IDkuNDM3NSAxNC40NDggOS41NjI4NyAxNC41MTA1IDkuNjg3ODdDMTQuNTc4MiA5LjgxMjc5IDE0LjY0NjEgOS45MzQ5NyAxNC43MTM3IDEwLjA1NDdIMTQuNzQ0OUMxNC43OTY5IDkuOTM0OTkgMTQuODQ5MSA5LjgxMjc2IDE0LjkwMTEgOS42ODc4N0MxNC45NTg0IDkuNTYyODcgMTUuMDE2IDkuNDM3NSAxNS4wNzMyIDkuMzEyNUwxNS40MzI3IDguNTM5MThIMTYuNjE5OUwxNS4zMzg3IDEwLjc2NTdMMTYuNzA1OSAxMi45MTQySDE1LjQ3MThMMTQuOTg3MiAxMi4xMDk3QzE0LjkxOTUgMTEuOTc5NSAxNC44NDg5IDExLjg1MTQgMTQuNzc2IDExLjcyNjRDMTQuNzA4MyAxMS41OTY0IDE0LjYzODMgMTEuNDcxNCAxNC41NjU0IDExLjM1MTdIMTQuNTI2NEMxNC40NjM5IDExLjQ3MTQgMTQuNDAxNCAxMS41OTYzIDE0LjMzOSAxMS43MjY0QzE0LjI4MTcgMTEuODUxNCAxNC4yMjE0IDExLjk3OTUgMTQuMTU4OSAxMi4xMDk3TDEzLjc2MDQgMTIuOTE0MkgxMi41NjUzTDEzLjkzMjUgMTAuNjQwNkwxMi42NTE0IDguNTM5MThIMTMuODg1NUwxNC4zMjMxIDkuMzEyNVpNMTEuMDUxIDEwLjgyMDdDMTAuNjk2OSAxMC44NjIzIDEwLjQxNTIgMTAuOTIyIDEwLjIwNjkgMTEuMDAwMUM5Ljk5ODY1IDExLjA3ODIgOS44NTA0OSAxMS4xNzIyIDkuNzYxOTYgMTEuMjgxNUM5LjY3MzQyIDExLjM4NTcgOS42Mjg5MSAxMS41MDI4IDkuNjI4OTEgMTEuNjMzMUM5LjYyODk0IDExLjgwNDggOS42ODEwNSAxMS45Mjk3IDkuNzg1MTYgMTIuMDA3OEM5Ljg5NDUxIDEyLjA4NTkgMTAuMDM1MSAxMi4xMjUgMTAuMjA2OSAxMi4xMjVDMTAuMzY4NCAxMi4xMjUgMTAuNTE0MyAxMi4wODg3IDEwLjY0NDUgMTIuMDE1N0MxMC43Nzk5IDExLjkzNzYgMTAuOTE1NiAxMS44MzA3IDExLjA1MSAxMS42OTUzVjEwLjgyMDdaIiBmaWxsPSJ1cmwoI3BhaW50MV9saW5lYXJfMzE5MjFfMjQ0NjkpIi8+CjxkZWZzPgo8bGluZWFyR3JhZGllbnQgaWQ9InBhaW50MF9saW5lYXJfMzE5MjFfMjQ0NjkiIHgxPSI2LjI1IiB5MT0iMTUuODMzMyIgeDI9IjE4LjMzMzMiIHkyPSI1IiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+CjxzdG9wIHN0b3AtY29sb3I9IiMyMjIyMjIiLz4KPHN0b3Agb2Zmc2V0PSIxIiBzdG9wLWNvbG9yPSIjNjk2OTY5Ii8+CjwvbGluZWFyR3JhZGllbnQ+CjxsaW5lYXJHcmFkaWVudCBpZD0icGFpbnQxX2xpbmVhcl8zMTkyMV8yNDQ2OSIgeDE9IjIuNSIgeTE9IjEwLjA3NDIiIHgyPSIxNi43MDU5IiB5Mj0iMTAuMDc0MiIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPgo8c3RvcCBzdG9wLWNvbG9yPSIjRkZGMUNFIi8+CjxzdG9wIG9mZnNldD0iMC4yNDAzODUiIHN0b3AtY29sb3I9IndoaXRlIi8+CjxzdG9wIG9mZnNldD0iMC40OTk0NDkiIHN0b3AtY29sb3I9IiNDOUZGRkIiLz4KPHN0b3Agb2Zmc2V0PSIwLjc2NTAxNyIgc3RvcC1jb2xvcj0iI0UxRTNGRiIvPgo8c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiNGRkUxRTciLz4KPC9saW5lYXJHcmFkaWVudD4KPC9kZWZzPgo8L3N2Zz4K)

![](data:image/png;base64,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)Claude 4.5 Sonnet![](data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyMCAyMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTE1LjAwMjkgNUMxNy43NjExIDUgMjAgNy4yNDAxOCAyMCAxMEMyMCAxMi43NTk4IDE3Ljc2MTEgMTUgMTUuMDAyOSAxNUgwVjcuODUyMTlDMCA2LjI3MDIxIDEuMjgxMDIgNSAyLjg1MDU1IDVIMTUuMDAyOVoiIGZpbGw9InVybCgjcGFpbnQwX2xpbmVhcl8zMTkyMV8yNDQ2OSkiLz4KPHBhdGggZD0iTTEwLjUxOTQgOC40Mjk5M0MxMC44ODkxIDguNDI5OTMgMTEuMTk5IDguNTAyNjkgMTEuNDQ5IDguNjQ4NDRDMTEuNjk5IDguNzk0MjcgMTEuODg2NyA5LjAxMDc4IDEyLjAxMTcgOS4yOTcyNEMxMi4xMzY2IDkuNTgzNjEgMTIuMTk5MSA5LjkzNzU5IDEyLjE5OTEgMTAuMzU5M1YxMi45MTQySDExLjI2MTZMMTEuMTgzNSAxMi40NDU0SDExLjE0NDRDMTAuOTU3IDEyLjYxMiAxMC43NTM5IDEyLjc0OTkgMTAuNTM1MyAxMi44NTkzQzEwLjMxNjUgMTIuOTY4NiAxMC4wNzk0IDEzLjAyMzQgOS44MjQyMiAxMy4wMjM0QzkuNTY5MDEgMTMuMDIzNCA5LjM0MjIgMTIuOTY4NiA5LjE0NDI5IDEyLjg1OTNDOC45NTE3MSAxMi43NDQ3IDguODAwNzMgMTIuNTg4MyA4LjY5MTQxIDEyLjM5MDVDOC41ODczNCAxMi4xOTI3IDguNTM1MTkgMTEuOTY4OSA4LjUzNTE2IDExLjcxOTFDOC41MzUxNiAxMS4yNTU2IDguNzM1OTIgMTAuODk1OCA5LjEzNjk2IDEwLjY0MDZDOS41MzgwMiAxMC4zODAzIDEwLjE3NjIgMTAuMjAzNCAxMS4wNTEgMTAuMTA5NkMxMS4wNDU4IDkuOTYzOTMgMTEuMDE5NyA5LjgzNjIzIDEwLjk3MjkgOS43MjY5M0MxMC45MjYxIDkuNjEyNDUgMTAuODQ3NyA5LjUyMTE4IDEwLjczODUgOS40NTM0OUMxMC42MzQ0IDkuMzg1ODEgMTAuNDkxIDkuMzUxNTkgMTAuMzA4OCA5LjM1MTU2QzEwLjEwNTcgOS4zNTE1NiA5LjkwNDk0IDkuMzkwNjMgOS43MDcwMyA5LjQ2ODc1QzkuNTA5MTEgOS41NDY4OCA5LjMwODM1IDkuNjQ4MzIgOS4xMDUyMiA5Ljc3MzMyTDguNjk5MzQgOS4wMDc5M0M4Ljg3MTE5IDguODk4NTggOS4wNTM1MyA4LjgwMTk1IDkuMjQ2MjIgOC43MTg2M0M5LjQzODgyIDguNjM1MzUgOS42NDE5NCA4LjU2ODA1IDkuODU1MzUgOC41MTU5OUMxMC4wNjg5IDguNDU4NzEgMTAuMjkwMyA4LjQyOTk0IDEwLjUxOTQgOC40Mjk5M1pNNC43NjU2MiA5Ljg0NDEyQzQuODI4MSAxMC4wMTU5IDQuODg3OCAxMC4xOTg0IDQuOTQ1MDcgMTAuMzkxQzUuMDAyMzIgMTAuNTc4NCA1LjA1OTk0IDEwLjc2MyA1LjExNzE5IDEwLjk0NTJINS4xNTYyNUM1LjIxODY5IDEwLjc2MzEgNS4yNzg0NSAxMC41NzgzIDUuMzM1NjkgMTAuMzkxQzUuMzkyOTYgMTAuMTk4NCA1LjQ0NzgyIDEwLjAxNTkgNS40OTk4OCA5Ljg0NDEyTDYuNDY4NTEgNy4xMjVINy43NTAyNFYxMi45MTQySDYuNjk1NTZWMTAuNTAwMkM2LjY5NTU2IDEwLjMxMjggNi43MDMxMyAxMC4xMDcxIDYuNzE4NzUgOS44ODMxOEM2LjczNDM3IDkuNjU5MjQgNi43NTI4NSA5LjQzNTEyIDYuNzczNjggOS4yMTExOEM2Ljc5OTcyIDguOTgyMDIgNi44MjMwNCA4Ljc3ODUyIDYuODQzODcgOC42MDE0NEg2LjgxMjc0TDYuMzM2MDYgOS45NjEzTDUuNDQ1NTYgMTIuMzkwNUg0Ljc4MTQ5TDMuODgzMDYgOS45NjEzTDMuNDIxNjMgOC42MDE0NEgzLjM5MDVDMy40MTEzNCA4Ljc3ODUyIDMuNDMyNTQgOC45ODIwMiAzLjQ1MzM3IDkuMjExMThDMy40NzQyIDkuNDM1MSAzLjQ5MjA3IDkuNjU5MjYgMy41MDc2OSA5Ljg4MzE4QzMuNTI4NTEgMTAuMTA3MSAzLjUzODgyIDEwLjMxMjggMy41Mzg4MiAxMC41MDAyVjEyLjkxNDJIMi41VjcuMTI1SDMuNzgxMTNMNC43NjU2MiA5Ljg0NDEyWk0xNC4zMjMxIDkuMzEyNUMxNC4zODU2IDkuNDM3NSAxNC40NDggOS41NjI4NyAxNC41MTA1IDkuNjg3ODdDMTQuNTc4MiA5LjgxMjc5IDE0LjY0NjEgOS45MzQ5NyAxNC43MTM3IDEwLjA1NDdIMTQuNzQ0OUMxNC43OTY5IDkuOTM0OTkgMTQuODQ5MSA5LjgxMjc2IDE0LjkwMTEgOS42ODc4N0MxNC45NTg0IDkuNTYyODcgMTUuMDE2IDkuNDM3NSAxNS4wNzMyIDkuMzEyNUwxNS40MzI3IDguNTM5MThIMTYuNjE5OUwxNS4zMzg3IDEwLjc2NTdMMTYuNzA1OSAxMi45MTQySDE1LjQ3MThMMTQuOTg3MiAxMi4xMDk3QzE0LjkxOTUgMTEuOTc5NSAxNC44NDg5IDExLjg1MTQgMTQuNzc2IDExLjcyNjRDMTQuNzA4MyAxMS41OTY0IDE0LjYzODMgMTEuNDcxNCAxNC41NjU0IDExLjM1MTdIMTQuNTI2NEMxNC40NjM5IDExLjQ3MTQgMTQuNDAxNCAxMS41OTYzIDE0LjMzOSAxMS43MjY0QzE0LjI4MTcgMTEuODUxNCAxNC4yMjE0IDExLjk3OTUgMTQuMTU4OSAxMi4xMDk3TDEzLjc2MDQgMTIuOTE0MkgxMi41NjUzTDEzLjkzMjUgMTAuNjQwNkwxMi42NTE0IDguNTM5MThIMTMuODg1NUwxNC4zMjMxIDkuMzEyNVpNMTEuMDUxIDEwLjgyMDdDMTAuNjk2OSAxMC44NjIzIDEwLjQxNTIgMTAuOTIyIDEwLjIwNjkgMTEuMDAwMUM5Ljk5ODY1IDExLjA3ODIgOS44NTA0OSAxMS4xNzIyIDkuNzYxOTYgMTEuMjgxNUM5LjY3MzQyIDExLjM4NTcgOS42Mjg5MSAxMS41MDI4IDkuNjI4OTEgMTEuNjMzMUM5LjYyODk0IDExLjgwNDggOS42ODEwNSAxMS45Mjk3IDkuNzg1MTYgMTIuMDA3OEM5Ljg5NDUxIDEyLjA4NTkgMTAuMDM1MSAxMi4xMjUgMTAuMjA2OSAxMi4xMjVDMTAuMzY4NCAxMi4xMjUgMTAuNTE0MyAxMi4wODg3IDEwLjY0NDUgMTIuMDE1N0MxMC43Nzk5IDExLjkzNzYgMTAuOTE1NiAxMS44MzA3IDExLjA1MSAxMS42OTUzVjEwLjgyMDdaIiBmaWxsPSJ1cmwoI3BhaW50MV9saW5lYXJfMzE5MjFfMjQ0NjkpIi8+CjxkZWZzPgo8bGluZWFyR3JhZGllbnQgaWQ9InBhaW50MF9saW5lYXJfMzE5MjFfMjQ0NjkiIHgxPSI2LjI1IiB5MT0iMTUuODMzMyIgeDI9IjE4LjMzMzMiIHkyPSI1IiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+CjxzdG9wIHN0b3AtY29sb3I9IiMyMjIyMjIiLz4KPHN0b3Agb2Zmc2V0PSIxIiBzdG9wLWNvbG9yPSIjNjk2OTY5Ii8+CjwvbGluZWFyR3JhZGllbnQ+CjxsaW5lYXJHcmFkaWVudCBpZD0icGFpbnQxX2xpbmVhcl8zMTkyMV8yNDQ2OSIgeDE9IjIuNSIgeTE9IjEwLjA3NDIiIHgyPSIxNi43MDU5IiB5Mj0iMTAuMDc0MiIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPgo8c3RvcCBzdG9wLWNvbG9yPSIjRkZGMUNFIi8+CjxzdG9wIG9mZnNldD0iMC4yNDAzODUiIHN0b3AtY29sb3I9IndoaXRlIi8+CjxzdG9wIG9mZnNldD0iMC40OTk0NDkiIHN0b3AtY29sb3I9IiNDOUZGRkIiLz4KPHN0b3Agb2Zmc2V0PSIwLjc2NTAxNyIgc3RvcC1jb2xvcj0iI0UxRTNGRiIvPgo8c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiNGRkUxRTciLz4KPC9saW5lYXJHcmFkaWVudD4KPC9kZWZzPgo8L3N2Zz4K)

![](data:image/png;base64,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)Gemini 2.5 Pro![](data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyMCAyMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTE1LjAwMjkgNUMxNy43NjExIDUgMjAgNy4yNDAxOCAyMCAxMEMyMCAxMi43NTk4IDE3Ljc2MTEgMTUgMTUuMDAyOSAxNUgwVjcuODUyMTlDMCA2LjI3MDIxIDEuMjgxMDIgNSAyLjg1MDU1IDVIMTUuMDAyOVoiIGZpbGw9InVybCgjcGFpbnQwX2xpbmVhcl8zMTkyMV8yNDQ2OSkiLz4KPHBhdGggZD0iTTEwLjUxOTQgOC40Mjk5M0MxMC44ODkxIDguNDI5OTMgMTEuMTk5IDguNTAyNjkgMTEuNDQ5IDguNjQ4NDRDMTEuNjk5IDguNzk0MjcgMTEuODg2NyA5LjAxMDc4IDEyLjAxMTcgOS4yOTcyNEMxMi4xMzY2IDkuNTgzNjEgMTIuMTk5MSA5LjkzNzU5IDEyLjE5OTEgMTAuMzU5M1YxMi45MTQySDExLjI2MTZMMTEuMTgzNSAxMi40NDU0SDExLjE0NDRDMTAuOTU3IDEyLjYxMiAxMC43NTM5IDEyLjc0OTkgMTAuNTM1MyAxMi44NTkzQzEwLjMxNjUgMTIuOTY4NiAxMC4wNzk0IDEzLjAyMzQgOS44MjQyMiAxMy4wMjM0QzkuNTY5MDEgMTMuMDIzNCA5LjM0MjIgMTIuOTY4NiA5LjE0NDI5IDEyLjg1OTNDOC45NTE3MSAxMi43NDQ3IDguODAwNzMgMTIuNTg4MyA4LjY5MTQxIDEyLjM5MDVDOC41ODczNCAxMi4xOTI3IDguNTM1MTkgMTEuOTY4OSA4LjUzNTE2IDExLjcxOTFDOC41MzUxNiAxMS4yNTU2IDguNzM1OTIgMTAuODk1OCA5LjEzNjk2IDEwLjY0MDZDOS41MzgwMiAxMC4zODAzIDEwLjE3NjIgMTAuMjAzNCAxMS4wNTEgMTAuMTA5NkMxMS4wNDU4IDkuOTYzOTMgMTEuMDE5NyA5LjgzNjIzIDEwLjk3MjkgOS43MjY5M0MxMC45MjYxIDkuNjEyNDUgMTAuODQ3NyA5LjUyMTE4IDEwLjczODUgOS40NTM0OUMxMC42MzQ0IDkuMzg1ODEgMTAuNDkxIDkuMzUxNTkgMTAuMzA4OCA5LjM1MTU2QzEwLjEwNTcgOS4zNTE1NiA5LjkwNDk0IDkuMzkwNjMgOS43MDcwMyA5LjQ2ODc1QzkuNTA5MTEgOS41NDY4OCA5LjMwODM1IDkuNjQ4MzIgOS4xMDUyMiA5Ljc3MzMyTDguNjk5MzQgOS4wMDc5M0M4Ljg3MTE5IDguODk4NTggOS4wNTM1MyA4LjgwMTk1IDkuMjQ2MjIgOC43MTg2M0M5LjQzODgyIDguNjM1MzUgOS42NDE5NCA4LjU2ODA1IDkuODU1MzUgOC41MTU5OUMxMC4wNjg5IDguNDU4NzEgMTAuMjkwMyA4LjQyOTk0IDEwLjUxOTQgOC40Mjk5M1pNNC43NjU2MiA5Ljg0NDEyQzQuODI4MSAxMC4wMTU5IDQuODg3OCAxMC4xOTg0IDQuOTQ1MDcgMTAuMzkxQzUuMDAyMzIgMTAuNTc4NCA1LjA1OTk0IDEwLjc2MyA1LjExNzE5IDEwLjk0NTJINS4xNTYyNUM1LjIxODY5IDEwLjc2MzEgNS4yNzg0NSAxMC41NzgzIDUuMzM1NjkgMTAuMzkxQzUuMzkyOTYgMTAuMTk4NCA1LjQ0NzgyIDEwLjAxNTkgNS40OTk4OCA5Ljg0NDEyTDYuNDY4NTEgNy4xMjVINy43NTAyNFYxMi45MTQySDYuNjk1NTZWMTAuNTAwMkM2LjY5NTU2IDEwLjMxMjggNi43MDMxMyAxMC4xMDcxIDYuNzE4NzUgOS44ODMxOEM2LjczNDM3IDkuNjU5MjQgNi43NTI4NSA5LjQzNTEyIDYuNzczNjggOS4yMTExOEM2Ljc5OTcyIDguOTgyMDIgNi44MjMwNCA4Ljc3ODUyIDYuODQzODcgOC42MDE0NEg2LjgxMjc0TDYuMzM2MDYgOS45NjEzTDUuNDQ1NTYgMTIuMzkwNUg0Ljc4MTQ5TDMuODgzMDYgOS45NjEzTDMuNDIxNjMgOC42MDE0NEgzLjM5MDVDMy40MTEzNCA4Ljc3ODUyIDMuNDMyNTQgOC45ODIwMiAzLjQ1MzM3IDkuMjExMThDMy40NzQyIDkuNDM1MSAzLjQ5MjA3IDkuNjU5MjYgMy41MDc2OSA5Ljg4MzE4QzMuNTI4NTEgMTAuMTA3MSAzLjUzODgyIDEwLjMxMjggMy41Mzg4MiAxMC41MDAyVjEyLjkxNDJIMi41VjcuMTI1SDMuNzgxMTNMNC43NjU2MiA5Ljg0NDEyWk0xNC4zMjMxIDkuMzEyNUMxNC4zODU2IDkuNDM3NSAxNC40NDggOS41NjI4NyAxNC41MTA1IDkuNjg3ODdDMTQuNTc4MiA5LjgxMjc5IDE0LjY0NjEgOS45MzQ5NyAxNC43MTM3IDEwLjA1NDdIMTQuNzQ0OUMxNC43OTY5IDkuOTM0OTkgMTQuODQ5MSA5LjgxMjc2IDE0LjkwMTEgOS42ODc4N0MxNC45NTg0IDkuNTYyODcgMTUuMDE2IDkuNDM3NSAxNS4wNzMyIDkuMzEyNUwxNS40MzI3IDguNTM5MThIMTYuNjE5OUwxNS4zMzg3IDEwLjc2NTdMMTYuNzA1OSAxMi45MTQySDE1LjQ3MThMMTQuOTg3MiAxMi4xMDk3QzE0LjkxOTUgMTEuOTc5NSAxNC44NDg5IDExLjg1MTQgMTQuNzc2IDExLjcyNjRDMTQuNzA4MyAxMS41OTY0IDE0LjYzODMgMTEuNDcxNCAxNC41NjU0IDExLjM1MTdIMTQuNTI2NEMxNC40NjM5IDExLjQ3MTQgMTQuNDAxNCAxMS41OTYzIDE0LjMzOSAxMS43MjY0QzE0LjI4MTcgMTEuODUxNCAxNC4yMjE0IDExLjk3OTUgMTQuMTU4OSAxMi4xMDk3TDEzLjc2MDQgMTIuOTE0MkgxMi41NjUzTDEzLjkzMjUgMTAuNjQwNkwxMi42NTE0IDguNTM5MThIMTMuODg1NUwxNC4zMjMxIDkuMzEyNVpNMTEuMDUxIDEwLjgyMDdDMTAuNjk2OSAxMC44NjIzIDEwLjQxNTIgMTAuOTIyIDEwLjIwNjkgMTEuMDAwMUM5Ljk5ODY1IDExLjA3ODIgOS44NTA0OSAxMS4xNzIyIDkuNzYxOTYgMTEuMjgxNUM5LjY3MzQyIDExLjM4NTcgOS42Mjg5MSAxMS41MDI4IDkuNjI4OTEgMTEuNjMzMUM5LjYyODk0IDExLjgwNDggOS42ODEwNSAxMS45Mjk3IDkuNzg1MTYgMTIuMDA3OEM5Ljg5NDUxIDEyLjA4NTkgMTAuMDM1MSAxMi4xMjUgMTAuMjA2OSAxMi4xMjVDMTAuMzY4NCAxMi4xMjUgMTAuNTE0MyAxMi4wODg3IDEwLjY0NDUgMTIuMDE1N0MxMC43Nzk5IDExLjkzNzYgMTAuOTE1NiAxMS44MzA3IDExLjA1MSAxMS42OTUzVjEwLjgyMDdaIiBmaWxsPSJ1cmwoI3BhaW50MV9saW5lYXJfMzE5MjFfMjQ0NjkpIi8+CjxkZWZzPgo8bGluZWFyR3JhZGllbnQgaWQ9InBhaW50MF9saW5lYXJfMzE5MjFfMjQ0NjkiIHgxPSI2LjI1IiB5MT0iMTUuODMzMyIgeDI9IjE4LjMzMzMiIHkyPSI1IiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+CjxzdG9wIHN0b3AtY29sb3I9IiMyMjIyMjIiLz4KPHN0b3Agb2Zmc2V0PSIxIiBzdG9wLWNvbG9yPSIjNjk2OTY5Ii8+CjwvbGluZWFyR3JhZGllbnQ+CjxsaW5lYXJHcmFkaWVudCBpZD0icGFpbnQxX2xpbmVhcl8zMTkyMV8yNDQ2OSIgeDE9IjIuNSIgeTE9IjEwLjA3NDIiIHgyPSIxNi43MDU5IiB5Mj0iMTAuMDc0MiIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPgo8c3RvcCBzdG9wLWNvbG9yPSIjRkZGMUNFIi8+CjxzdG9wIG9mZnNldD0iMC4yNDAzODUiIHN0b3AtY29sb3I9IndoaXRlIi8+CjxzdG9wIG9mZnNldD0iMC40OTk0NDkiIHN0b3AtY29sb3I9IiNDOUZGRkIiLz4KPHN0b3Agb2Zmc2V0PSIwLjc2NTAxNyIgc3RvcC1jb2xvcj0iI0UxRTNGRiIvPgo8c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiNGRkUxRTciLz4KPC9saW5lYXJHcmFkaWVudD4KPC9kZWZzPgo8L3N2Zz4K)

![](data:image/png;base64,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)Kimi K2![](data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyMCAyMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTE1LjAwMjkgNUMxNy43NjExIDUgMjAgNy4yNDAxOCAyMCAxMEMyMCAxMi43NTk4IDE3Ljc2MTEgMTUgMTUuMDAyOSAxNUgwVjcuODUyMTlDMCA2LjI3MDIxIDEuMjgxMDIgNSAyLjg1MDU1IDVIMTUuMDAyOVoiIGZpbGw9InVybCgjcGFpbnQwX2xpbmVhcl8zMTkyMV8yNDQ2OSkiLz4KPHBhdGggZD0iTTEwLjUxOTQgOC40Mjk5M0MxMC44ODkxIDguNDI5OTMgMTEuMTk5IDguNTAyNjkgMTEuNDQ5IDguNjQ4NDRDMTEuNjk5IDguNzk0MjcgMTEuODg2NyA5LjAxMDc4IDEyLjAxMTcgOS4yOTcyNEMxMi4xMzY2IDkuNTgzNjEgMTIuMTk5MSA5LjkzNzU5IDEyLjE5OTEgMTAuMzU5M1YxMi45MTQySDExLjI2MTZMMTEuMTgzNSAxMi40NDU0SDExLjE0NDRDMTAuOTU3IDEyLjYxMiAxMC43NTM5IDEyLjc0OTkgMTAuNTM1MyAxMi44NTkzQzEwLjMxNjUgMTIuOTY4NiAxMC4wNzk0IDEzLjAyMzQgOS44MjQyMiAxMy4wMjM0QzkuNTY5MDEgMTMuMDIzNCA5LjM0MjIgMTIuOTY4NiA5LjE0NDI5IDEyLjg1OTNDOC45NTE3MSAxMi43NDQ3IDguODAwNzMgMTIuNTg4MyA4LjY5MTQxIDEyLjM5MDVDOC41ODczNCAxMi4xOTI3IDguNTM1MTkgMTEuOTY4OSA4LjUzNTE2IDExLjcxOTFDOC41MzUxNiAxMS4yNTU2IDguNzM1OTIgMTAuODk1OCA5LjEzNjk2IDEwLjY0MDZDOS41MzgwMiAxMC4zODAzIDEwLjE3NjIgMTAuMjAzNCAxMS4wNTEgMTAuMTA5NkMxMS4wNDU4IDkuOTYzOTMgMTEuMDE5NyA5LjgzNjIzIDEwLjk3MjkgOS43MjY5M0MxMC45MjYxIDkuNjEyNDUgMTAuODQ3NyA5LjUyMTE4IDEwLjczODUgOS40NTM0OUMxMC42MzQ0IDkuMzg1ODEgMTAuNDkxIDkuMzUxNTkgMTAuMzA4OCA5LjM1MTU2QzEwLjEwNTcgOS4zNTE1NiA5LjkwNDk0IDkuMzkwNjMgOS43MDcwMyA5LjQ2ODc1QzkuNTA5MTEgOS41NDY4OCA5LjMwODM1IDkuNjQ4MzIgOS4xMDUyMiA5Ljc3MzMyTDguNjk5MzQgOS4wMDc5M0M4Ljg3MTE5IDguODk4NTggOS4wNTM1MyA4LjgwMTk1IDkuMjQ2MjIgOC43MTg2M0M5LjQzODgyIDguNjM1MzUgOS42NDE5NCA4LjU2ODA1IDkuODU1MzUgOC41MTU5OUMxMC4wNjg5IDguNDU4NzEgMTAuMjkwMyA4LjQyOTk0IDEwLjUxOTQgOC40Mjk5M1pNNC43NjU2MiA5Ljg0NDEyQzQuODI4MSAxMC4wMTU5IDQuODg3OCAxMC4xOTg0IDQuOTQ1MDcgMTAuMzkxQzUuMDAyMzIgMTAuNTc4NCA1LjA1OTk0IDEwLjc2MyA1LjExNzE5IDEwLjk0NTJINS4xNTYyNUM1LjIxODY5IDEwLjc2MzEgNS4yNzg0NSAxMC41NzgzIDUuMzM1NjkgMTAuMzkxQzUuMzkyOTYgMTAuMTk4NCA1LjQ0NzgyIDEwLjAxNTkgNS40OTk4OCA5Ljg0NDEyTDYuNDY4NTEgNy4xMjVINy43NTAyNFYxMi45MTQySDYuNjk1NTZWMTAuNTAwMkM2LjY5NTU2IDEwLjMxMjggNi43MDMxMyAxMC4xMDcxIDYuNzE4NzUgOS44ODMxOEM2LjczNDM3IDkuNjU5MjQgNi43NTI4NSA5LjQzNTEyIDYuNzczNjggOS4yMTExOEM2Ljc5OTcyIDguOTgyMDIgNi44MjMwNCA4Ljc3ODUyIDYuODQzODcgOC42MDE0NEg2LjgxMjc0TDYuMzM2MDYgOS45NjEzTDUuNDQ1NTYgMTIuMzkwNUg0Ljc4MTQ5TDMuODgzMDYgOS45NjEzTDMuNDIxNjMgOC42MDE0NEgzLjM5MDVDMy40MTEzNCA4Ljc3ODUyIDMuNDMyNTQgOC45ODIwMiAzLjQ1MzM3IDkuMjExMThDMy40NzQyIDkuNDM1MSAzLjQ5MjA3IDkuNjU5MjYgMy41MDc2OSA5Ljg4MzE4QzMuNTI4NTEgMTAuMTA3MSAzLjUzODgyIDEwLjMxMjggMy41Mzg4MiAxMC41MDAyVjEyLjkxNDJIMi41VjcuMTI1SDMuNzgxMTNMNC43NjU2MiA5Ljg0NDEyWk0xNC4zMjMxIDkuMzEyNUMxNC4zODU2IDkuNDM3NSAxNC40NDggOS41NjI4NyAxNC41MTA1IDkuNjg3ODdDMTQuNTc4MiA5LjgxMjc5IDE0LjY0NjEgOS45MzQ5NyAxNC43MTM3IDEwLjA1NDdIMTQuNzQ0OUMxNC43OTY5IDkuOTM0OTkgMTQuODQ5MSA5LjgxMjc2IDE0LjkwMTEgOS42ODc4N0MxNC45NTg0IDkuNTYyODcgMTUuMDE2IDkuNDM3NSAxNS4wNzMyIDkuMzEyNUwxNS40MzI3IDguNTM5MThIMTYuNjE5OUwxNS4zMzg3IDEwLjc2NTdMMTYuNzA1OSAxMi45MTQySDE1LjQ3MThMMTQuOTg3MiAxMi4xMDk3QzE0LjkxOTUgMTEuOTc5NSAxNC44NDg5IDExLjg1MTQgMTQuNzc2IDExLjcyNjRDMTQuNzA4MyAxMS41OTY0IDE0LjYzODMgMTEuNDcxNCAxNC41NjU0IDExLjM1MTdIMTQuNTI2NEMxNC40NjM5IDExLjQ3MTQgMTQuNDAxNCAxMS41OTYzIDE0LjMzOSAxMS43MjY0QzE0LjI4MTcgMTEuODUxNCAxNC4yMjE0IDExLjk3OTUgMTQuMTU4OSAxMi4xMDk3TDEzLjc2MDQgMTIuOTE0MkgxMi41NjUzTDEzLjkzMjUgMTAuNjQwNkwxMi42NTE0IDguNTM5MThIMTMuODg1NUwxNC4zMjMxIDkuMzEyNVpNMTEuMDUxIDEwLjgyMDdDMTAuNjk2OSAxMC44NjIzIDEwLjQxNTIgMTAuOTIyIDEwLjIwNjkgMTEuMDAwMUM5Ljk5ODY1IDExLjA3ODIgOS44NTA0OSAxMS4xNzIyIDkuNzYxOTYgMTEuMjgxNUM5LjY3MzQyIDExLjM4NTcgOS42Mjg5MSAxMS41MDI4IDkuNjI4OTEgMTEuNjMzMUM5LjYyODk0IDExLjgwNDggOS42ODEwNSAxMS45Mjk3IDkuNzg1MTYgMTIuMDA3OEM5Ljg5NDUxIDEyLjA4NTkgMTAuMDM1MSAxMi4xMjUgMTAuMjA2OSAxMi4xMjVDMTAuMzY4NCAxMi4xMjUgMTAuNTE0MyAxMi4wODg3IDEwLjY0NDUgMTIuMDE1N0MxMC43Nzk5IDExLjkzNzYgMTAuOTE1NiAxMS44MzA3IDExLjA1MSAxMS42OTUzVjEwLjgyMDdaIiBmaWxsPSJ1cmwoI3BhaW50MV9saW5lYXJfMzE5MjFfMjQ0NjkpIi8+CjxkZWZzPgo8bGluZWFyR3JhZGllbnQgaWQ9InBhaW50MF9saW5lYXJfMzE5MjFfMjQ0NjkiIHgxPSI2LjI1IiB5MT0iMTUuODMzMyIgeDI9IjE4LjMzMzMiIHkyPSI1IiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+CjxzdG9wIHN0b3AtY29sb3I9IiMyMjIyMjIiLz4KPHN0b3Agb2Zmc2V0PSIxIiBzdG9wLWNvbG9yPSIjNjk2OTY5Ii8+CjwvbGluZWFyR3JhZGllbnQ+CjxsaW5lYXJHcmFkaWVudCBpZD0icGFpbnQxX2xpbmVhcl8zMTkyMV8yNDQ2OSIgeDE9IjIuNSIgeTE9IjEwLjA3NDIiIHgyPSIxNi43MDU5IiB5Mj0iMTAuMDc0MiIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPgo8c3RvcCBzdG9wLWNvbG9yPSIjRkZGMUNFIi8+CjxzdG9wIG9mZnNldD0iMC4yNDAzODUiIHN0b3AtY29sb3I9IndoaXRlIi8+CjxzdG9wIG9mZnNldD0iMC40OTk0NDkiIHN0b3AtY29sb3I9IiNDOUZGRkIiLz4KPHN0b3Agb2Zmc2V0PSIwLjc2NTAxNyIgc3RvcC1jb2xvcj0iI0UxRTNGRiIvPgo8c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiNGRkUxRTciLz4KPC9saW5lYXJHcmFkaWVudD4KPC9kZWZzPgo8L3N2Zz4K)

å ¶ä»/èªå®ä¹

![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAABQCAMAAAC5zwKfAAAAclBMVEUAAADm5ubn5+ff39/m5ubm5ubm5ubm5ubm5ubl5eXl5eXm5ubn5+fn5+fk5OTn5+fn5+f///8zMzPm5uZNTU35+fns7Oz19fXy8vJAQEDp6emAgIBmZmaZmZnMzMzZ2dmzs7NZWVmmpqZzc3O/v7+MjIwtOcgWAAAAEXRSTlMA3yAQ759Qz7+QgK9wYGBAfzNtP58AAAQESURBVFjDzVntlpowFAQJgmhrcfgIAirqvv8rNiHbZGOuV13bczo/ejj0MDvJ3I/kGj1AstykeRxDQWR5WmyTiAdPtooRIE6X3yPdrgUUGtm2dV1q1HUrG2iky5fF/RKarK3LAHWrSeOfi1fp9tJyhJx7Rfnrab4fsRJXlyzaRqt8im6Rs3ROplK5fmLdGwG05VNQCxePRCYrJa98FrUEVvxys1AeLxLIFgxfjD21e/xOxguGj3SDZ2wsI8VXfgO0Rp6Pxx2NGc/Ha8zCerHy/HjZmVWQboDie4Nxc7OBIoy/1+JR+Nu4dhv4XWNyb8HcBsqPqZoGjR73GYGvaR0zC0a1s+iOzKJj5/Qv7Mu76HdfMHCLLlxIcw5PSlg1o1OMjNMQid1BzpHK6uo1ISuR30HjwHnnEVYnTqLhW5I7OHa7bpTHaucRasrj2NG8e2xnwpQSOJqPjRW9eXetdg4HIr6wnqs+lXT46qz79jrYtxXRZY0tSzR0rAzmQ1/KSavs9D8jZcvyzopPmglQtP2tEPXygoNmBRHcuuhQQagVnDTxuQyhs+VD7yzhc6y2kPD4rAWWHGRH+gIk0RYNKfDofX8Yx/FwGwUDuYkFArsOt+s5d8afE/dHTeBsKE+O+uuRKg/uJQZqzS3SKKc88fSMO4dPk+Q4a5YhYR5lBKFOOCsAJrhxmHSsGI6T0UvaLEDVhXmV+n9MhHzMTxcr8ai5qZBShAgI7cfmabDUUj1drOqebgQhoaPx66F5nMzTW4QuyLs/3PJlQjlYEy/WnqulOZp9JQnJfnKYbYbLQ/xpf1cb+hXppiAJr197ppzJ+/HSuQw/3+mpNbIoJ6qXoZAucQxcycKF7qk1cir1pKurfumvnKZTp+VSqbdBWMu7m/KJfq7To/R7xER0lSLsAHT5xE00TGTqNdjaAsuWT7pHlGSBtTZT5RM9wo/OtkeQLSBaETabD6Tira632nSXH80OEp7ca6NzWzN12oq08WKAe200ESBz2cJRHuxbMpVrIDHHYeoQMMvrKhN/Xuk29Rz0ijW2vs+uaXQDyrFzhP3O1NXT5TJK8rD0OYoQzmdKqkf4IblDcWRQ8AdOjxDMgdMe2xNGoskJdyRmJhv6xsdLtFY4TNyFr3CDAe5aIZ++VvgXH8aWflCYqmrqj9xtz5tn5O9ezSTW//byGG1euC6TSffzr17AG2J8k7wxImiQ3R1i/A9jkSbge38Q9LdHVewwbf/mMC2MnleW3QCr5NG8VPgieXli88TIdA23k7wbyBfPD3Xbh3T+UJdHEUMtnBnl7AFRvDJwX/yI2cE4TcdjmeJzdO8m95+je7HefvPHhZT6cWG1fOsXi22R5pmYmeI83Twk+w2VbF9Avb3n0wAAAABJRU5ErkJggg==)æ´å¤ç¿»è¯æå¡

å¯ç¨ AI ç²¾ç¿»![](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgZmlsbD0ibm9uZSI+PHBhdGggZmlsbD0iI0ZGQzczNiIgZD0iTTMgN2gxN3YxMEgzeiIvPjxwYXRoIGZpbGw9InVybCgjYSkiIGQ9Ik02Ljg5NyA5LjI0MmMuNDE1IDAgLjcyLjExMS45MjguMzQ3LjIwNy4yMzUuMzE4LjUyNy4zMTguODczcy0uMTEuNjIzLS4zMTguODQ1Yy0uMjA4LjIyMi0uNTI3LjMzMy0uOTI4LjMzM2gtMS4zM1Y5LjI0MmgxLjMzWm05Ljg0NiAxLjc4OGMuMzg4IDAgLjY2NS4xNTIuODQ1LjQ1Ny4xNTIuMjY0LjIzNS41ODIuMjYzLjk4NHYuMzE5YzAgLjQ5OS0uMDgzLjg4Ny0uMjYzIDEuMTkyLS4xOC4zMDQtLjQ1Ny40NTctLjgzLjQ1Ny0uMzg5IDAtLjY2Ni0uMTUzLS44NDYtLjQ0NC0uMTUyLS4yNjMtLjIzNS0uNTk1LS4yNjMtMS4wMTF2LS4yOTFjMC0uNDg1LjA4My0uODczLjI2My0xLjE3OC4xOC0uMzA1LjQ0My0uNDg1LjgzMS0uNDg1Wm0tMy40MDctMS4xMzZhMS4xNyAxLjE3IDAgMCAwLS43MDYuMjM1IDEuNDgyIDEuNDgyIDAgMCAwLS40MTUuNWwtLjA4My4xNjUtLjA3LS44MDNoLTEuMzU3djUuNDMyaDEuNDU0di0zLjY1OWEuODguODggMCAwIDEgLjMxOS0uMzg4Yy4xMS0uMDY5LjI1LS4xMS40MTUtLjEyNGguMTI1bC41NC4wMTQuMTY2LTEuMzE3Yy0uMDctLjAxNC0uMTI0LS4wMjgtLjE5NC0uMDQxLS4wNTUtLjAxNC0uMTI0LS4wMTQtLjE5NC0uMDE0Wk02Ljg5NiA4LjEySDQuMTE0djcuMzE3aDEuNDY4VjEyLjc5aDEuMzNjLjg0NCAwIDEuNDk1LS4yMDggMS45OC0uNjM4LjQ4NS0uNDMuNzItLjk4My43Mi0xLjY5cy0uMjM1LTEuMjYxLS43Mi0xLjY5Yy0uNDQzLS4zODktMS4wMzktLjYxLTEuNzczLS42MzhsLS4yMjEtLjAxNFptOS44NDcgMS43NzRjLS44MDMgMC0xLjQyNi4yNjMtMS44ODMuNzc2LS40MTYuNDctLjYzNyAxLjA2Ny0uNjc5IDEuNzczdi4zMzNjMCAuODE4LjIyMiAxLjQ4My42NzkgMS45OTUuNDU3LjUxMyAxLjA4Ljc3NiAxLjg4My43NzYuODA0IDAgMS40MjctLjI2MyAxLjg4NC0uNzc2LjQxNS0uNDcuNjM3LTEuMDUzLjY3OC0xLjc3M3YtLjMzM2MwLS44MTctLjIyMS0xLjQ4Mi0uNjc4LTEuOTk1LS40NTctLjUxMy0xLjA4LS43NzYtMS44ODQtLjc3NlpNMTguMDAzIDZhNiA2IDAgMCAxIDAgMTJIMFY5LjQyM0EzLjQyIDMuNDIgMCAwIDEgMy40MiA2aDE0LjU4M1oiLz48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9ImEiIHgxPSI3LjUiIHgyPSIyMiIgeTE9IjE5IiB5Mj0iNiIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPjxzdG9wIHN0b3AtY29sb3I9IiMyMjIiLz48c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiM2OTY5NjkiLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48L3N2Zz4=)

ç¿»è¯ (Alt+A)

æ»æ¯ç¿»è¯è¯¥ç½ç« ä¸èªå¨ç¿»è¯è¯¥ç½ç«

é¼ æ æ¬å:\+ Ctrl ç¿»è¯/è¿åè¯¥æ®µ \+ Shift ç¿»è¯/è¿åè¯¥æ®µ \+ Alt ç¿»è¯/è¿åè¯¥æ®µ \+ é¿æé¼ æ å·¦é® ç´æ¥ç¿»è¯è¯¥æ®µ èªå®ä¹å¿«æ·é®(æå¼è®¾ç½®)

åè¯ç¿»è¯:ç´æ¥è§¦å æ¾ç¤ºå¾æ  æ¾ç¤ºå°åç¹ æ Ctrl è§¦å æ Alt è§¦å æ Shift è§¦å

ææ¡£ç¿»è¯

Tææ¬ç¿»è¯

å¥å±ä¸­å¿

è®¾ç½®

1.22.7

æ´å¤ ð ä½¿ç¨è¯´æ ð¤ ä¸´æ¶åæ¢é»è®¤è¯ææ¨¡å¼ä¸ºä» æ¾ç¤ºè¯æ ð åæ¢ä¸ºç¿»è¯ææåºå ðª å ³é­ä¾§è¾¹æ ç¿»è¯ â¡ ç«å³ç¿»è¯å°é¡µé¢åºé¨ ð é è¯»æ¬å°çµå­ä¹¦ ð å¶ä½åè¯­ EPUB çµå­ä¹¦ ð BabelDOC ä¿çæç PDF ç¿»è¯ ð ç¿»è¯æ¬å° PDF æä»¶ âï¸ AI é©±å¨ç PDF Pro ç¿»è¯ ð ç¿»è¯ HTML/txt æä»¶ ðº ç¿»è¯æ¬å°å­å¹æä»¶ â­ ç¦ç¨æ¬æµ®ç ðï¸ ä¸´æ¶å¼å¯è¯æç¼è¾ ð å è´¹è¯ç¨ Pro ä¼å ð§¹ æ¸ é¤ç¼å­ ð¬ åé¦å½åé¡µé¢ç¿»è¯é®é¢ ð å»ååºè¯ä»· â¤ï¸ å ³äº - åé¦
