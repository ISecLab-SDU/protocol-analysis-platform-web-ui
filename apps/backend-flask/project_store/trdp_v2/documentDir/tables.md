## Train Real-Time Data Protocol (TRDP) -> A.2 Lower Layers

```plaintext
```
```

## Train Real-Time Data Protocol (TRDP) -> A.3 TRDP FCS computation -> Figure A.2 â FCS Computation

```plaintext
```
```

## Train Real-Time Data Protocol (TRDP) -> A.3 TRDP FCS computation

```plaintext
```
```

## Train Real-Time Data Protocol (TRDP) -> A.2 Lower Layers -> A.2.3 Transport Layer -> Table A.1 â UDP/TCP port assignments (well known ports)

```plaintext
Table A.1 â UDP/TCP port assignments (well known ports)
3564 **Protocol Destination Port** Process Data (UDP) 17224 Message Data (UDP/TCP) 17225 3565 For receiving UDP message data reply telegrams the port the related request was sent from 3568 IEC CD 61375-2-3 © IEC 2024 - 132 - 9/3102/CD For sending UDP message data reply telegrams any source port different from the one the 3573 TCP connections shall be established between a source port different from the well-known port 3575 Using different port numbers from those defined in Table A.1 may be allowed for project specific 3577 The used well-known port numbers should be given as a configuration parameter to the 3579 IEC CD 61375-2-3 © IEC 2024 - 133 - 9/3102/CD
```

## Train Real-Time Data Protocol (TRDP) -> A.5 Communication Identifier (ComId)

```plaintext
Derived: TRDP protocol layers
_IEC_ TRDP User (Application) TRDP Layer TRDP service TCP/UDP service user service provider IEC CD 61375-2-3 © IEC 2024 - 136 - 9/3102/CD
```

## Train Real-Time Data Protocol (TRDP) -> A.5 Communication Identifier (ComId) -> Table A.2 â Reserved ComIds

```plaintext
Table A.2 – Reserved ComIds
3715 **comId Description** 0 unspecified PDU service service service 3716 IEC CD 61375-2-3 © IEC 2024 - 137 - 9/3102/CD **comId Description** 104 TTDB – consist information request service service 3717 IEC CD 61375-2-3 © IEC 2024 - 138 - 9/3102/CD
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.5 PD-PDU -> Figure A.11 â PD-PDU

```plaintext
Figure A.11 – PD-PDU
3776 PD_PDU::= RECORD 3777 _IEC_ **dataset** 0 15 16 317 8 23 24**sequenceCounter** **protocolVersion** **etbTopoCnt** **datasetLength** **replyComId** **msgType** 40 octets **reserved** **replyIpAddress** 24 octets **headerFCS** **opTrnTopoCnt** IEC CD 61375-2-3 © IEC 2024 - 145 - 9/3102/CD
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.5 PD-PDU -> Table A.3 â PD-PDU parameters

```plaintext
Table A.3 – PD-PDU parameters
3797 **Parameter Description Value** sequenceCounter The sequence counter: â¢ Shall be managed for sending process telegrams per â¢ Shall be managed (stored) for received process â¢ Shall be incremented with each sending of the process â¢ Can be used for communication layer surveillance (PD A surveillance that the application is still updating its process Computed, protocolVersion The protocol version shall consist of: incompatible changes compatible changes Fixed msgType Type of the telegram. â5072âH (âPrâ) comId Identifier of the user dataset. See also A.5. set by user â¢ shall be used (train addressing) as defined in IEC 61375- â¢ shall be set by the user not used. 0..232-1 set by user opTrnTopoCnt The operational train topography counter: use information from the operational train directory (e.g. â¢ shall be set when the source device used the operational â¢ optional in all other cases. Shall be set to 0 (= invalid) if datasetLength The dataset length: octets without padding octets. 0..1432 IEC CD 61375-2-3 © IEC 2024 - 146 - 9/3102/CD **Parameter Description Value** â¢ shall be the primary information about the user data NOTE In case of fixed size data sets this is redundant reserved â¢ Reserved for future use. set to 0 â¢ shall be used only in a PD request the reply 0, the reply shall be sent as an unspecified PDU. Set by user in replyIpAddress The reply IP address for PD: be used for the reply. set by user for headerFCS The header frame check sequence: Computed dataset The user data 3798
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.3 Communication pattern -> A.6.3.2 Pull communication pattern

```plaintext
Figure A.10
_IEC_ publisher subscriber PD-PDU (data) PD publish PD-PDU (data) PD-PDU (data) PD publish PD publish PD consumption _IEC_ subscribersubscriberpublisher subscriber PD-PDU (data) PD consumption PD publish PD-PDU (data) PD-PDU (data) PD publish PD publish PD consumption IEC CD 61375-2-3 © IEC 2024 - 140 - 9/3102/CD 3755
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.3 Communication pattern -> Figure A.7 â PD pull pattern (point to point, sink knows source)

```plaintext
Derived: PD pull pattern (point to point, sink knows source)
3756 _IEC_ publisher requester / PD-PDU(reply) PD-PDU(request) PD-PDU(reply) PD-PDU(request) PD-PDU(reply) PD-PDU(request) IEC CD 61375-2-3 © IEC 2024 - 141 - 9/3102/CD 3757
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.3 Communication pattern -> Figure A.9 â PD pull pattern (point to multipoint, sink knows source)

```plaintext
Derived: PD pull pattern (point to multipoint, sink knows source)
3760 _IEC_ subscriber publisher requester / PD-PDU(reply) PD-PDU(request) PD-PDU(reply) PD-PDU(request) PD-PDU(reply) PD-PDU(request) IEC CD 61375-2-3 © IEC 2024 - 143 - 9/3102/CD 3761
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.6 Interaction between application and TRDP protocol layer -> Table A.4 â TRDP service primitives

```plaintext
Table A.4 – TRDP service primitives
3805 **Role Service primitive Parameter Description** Publisher PD.publish TRDP user â' TRDP layer handle Handle for this publishing, returned userRef Optional user reference for call callBackFunction Optional call back function. Set to 0 reserved as defined in Table A.3 IEC CD 61375-2-3 © IEC 2024 - 147 - 9/3102/CD **Role Service primitive Parameter Description** sourceIpAddress Source IP Address of the PD. PD to. Set to 0 for application triggered PD datasetLength Actual user data length to be sent dataset Buffer with user data to be sent as redId Redundancy group ID. Set to 0 if PD.rePublish TRDP user â' TRDP layer handle Handle which has been given by the etbTopoCnt as defined in Table A.3 opTrnTopoCnt as defined in Table A.3 sourceIpAddress Source IP Address of the PD. destinationIpAddress Destination IP address to send the PD.unPublish TRDP user â' TRDP layer handle Handle which has been given by the PD.putData TRDP user â' TRDP layer handle Handle which has been given by the datasetLength Actual user data length to be sent dataset Buffer with user data to be sent as PD.setRed TRDP user â' TRDP layer IEC CD 61375-2-3 © IEC 2024 - 148 - 9/3102/CD **Role Service primitive Parameter Description** redId Selects the redundancy group to be leader If TRUE, the service activates PD.getRed TRDP user â' TRDP layer redId Selects the redundancy group to be leader If TRUE, publishing is activated for PD.putDataImmediate TRDP user â' TRDP layer handle Handle which has been given by the txTime Absolute time to transmit or 0 for datasetLength Actual user data length to be sent dataset Buffer with user data to be sent as Requester PD.request TRDP user â' TRDP layer handle handle for this subscription of the reserved as defined in Table A.3 comId ComId to be sent, as defined in etbTopoCnt as defined in Table A.3 sourceIpAddress Source IP address destinationIpAddress Destination IP address to send the redId Redundancy ID. Set to 0 if dataSet User data set to be sent, as defined datasetLength data set length to be sent, as IEC CD 61375-2-3 © IEC 2024 - 149 - 9/3102/CD **Role Service primitive Parameter Description** replyComId as defined in Table A.3 Subscriber PD.subscribe TRDP user â' TRDP layer handle handle for this subscription; userRef Optional user reference for call callBackFunction Optional call back function. Set to 0 reserved as defined in Table A.3 comId as defined in Table A.3 etbTopoCnt as defined in Table A.3 opTrnTopoCnt as defined in Table A.3 respective URIâs using DNS. sourceIpAddress2 Defines the upper IP address in destinationIpAddress IP destination address, generated timeout Timeout (rxTime) for PD to be timeoutBehaviour Optional behaviour in case of a PD_resubscribe TRDP user â' TRDP layer handle handle for this subscription; etbTopoCnt as defined in Table A.3 opTrnTopoCnt as defined in Table A.3 sourceIpAddress1 IP source address, generated out of IEC CD 61375-2-3 © IEC 2024 - 150 - 9/3102/CD **Role Service primitive Parameter Description** Defines the lower IP address in sourceIpAddress2 Defines the upper IP address in destinationIpAddress IP destination address, generated PD.unsubscribe TRDP user â' TRDP layer handle handle returned by the TRDP layer PD.indicate TRDP layer â' TRDP user handle handle returned by the TRDP layer sourceIpAddress Received source IP address destinationIpAddress Received destination IP address, as sequenceCounter Received sequence counter, as protocolVersion Received protocol version, as imsgType â¢ process data (âPdâ) comId Received ComId, as defined in etbTopoCnt Received topo count, as defined in opTrnTopoCnt Received topo count, as defined in replyIComId Received reply ComId, as defined in replyIpAddress Received reply IP address userRef User reference given in status 0 OK, != 0 NOK â¢ 1 â timeout IEC CD 61375-2-3 © IEC 2024 - 151 - 9/3102/CD **Role Service primitive Parameter Description** â¢ 6 â no subscription timeoutBehaviour Optional behaviour in case of a reserved as defined in Table A.3 dataset Received user data, as defined in datasetLength Received user data size, as defined PD.get TRDP user â' TRDP layer handle handle returned by the TRDP layer sourceIpAddress Received source IP address destinationIpAddress Received destination IP sequenceCounter Received sequence counter, as protocolVersion Received protocol version, as msgType â¢ process data (âPdâ) comId Received ComId, as defined in etbTopoCnt Received topo count, as defined in opTrnTopoCnt Received topo count, as defined in replyIComId Received reply ComId, as defined in replyIpAddress Received reply IP address userRef User reference given in status 0 OK, != 0 NOK â¢ 1 â timeout timeoutBehaviour Optional behaviour in case of a reserved as defined in Table A.3 IEC CD 61375-2-3 © IEC 2024 - 152 - 9/3102/CD **Role Service primitive Parameter Description** dataset Received user data, as defined in datasetLength Received user data size, as defined 3806
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.6 Interaction between application and TRDP protocol layer -> Figure A.13 â Interaction sequence chart for PD push pattern used for TRDP layer

```plaintext
Figure A.13 – Interaction sequence chart for PD push pattern used for TRDP layer
3869 **triggered PD cycle** 3870 3871
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.7 Topography counter check -> Table A.5 â Topography counter check

```plaintext
Table A.5 â Topography counter check
3902 **Publisher Actual topography counter values Locally stored topography counter values** **Subscriber Actual topography counter values Topography counter values of the received** **Topography counter values of the** **Locally stored topography counter values** **Case** etbTopoCnt opTrnTopoCnt etbTopoCnt opTrnTopoCnt 3 equal any equal 0 5 (3) 0 0 any any (3) Only relevant for the comparison of the topography counter values of the received telegram with the locally (4) Case applies only for subscriber comparing topography counter values of the received telegram with the locally Key: 0 = topography counter value set to 0 (donât care ) _IEC_ TRDP TRDP **publisher** TRDP TRDP **subscriber** IEC CD 61375-2-3 © IEC 2024 - 156 - 9/3102/CD
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.8 State Machine -> Table A.6 â PD publisher state diagram â guards

```plaintext
Table A.6 – PD publisher state diagram – guards
3921 **Guards Description** pattern configured communication pattern for the PD-PDU exchange Values: PUSH checkTopoCounts Check the locally stored topology counters submitted with the publish against 3922 _IEC_ [pattern == PUSH] PD.publish timeout CyclicOperation PolledOperation [pattern == PULL] PD.putData / restartTimer(txTime) PD.putData PD.unpublish requestReceived [OK] [ELSE] / stopPublishing [appTriggeredCycle == FALSE][appTriggeredCycle == TRUE] ApplicationTriggeredOperation / preparePd PD.putDataImmediate / preparePd IEC CD 61375-2-3 © IEC 2024 - 157 - 9/3102/CD
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.6 Interaction between application and TRDP protocol layer -> A.6.6.4 Interaction sequence â PD Push Pattern

```plaintext
Derived: Interaction sequence for PD Push Pattern
_IEC_ TRDP TRDP **publisher/subscriber** TRDP TRDP **requester/subscriber** request telegram process data telegram PD.putData PD.indicate(data) PD.request PD.subscribe PD.putData PD.subscribe PD.poll PD.indicate(timeout) PD.publish IEC CD 61375-2-3 © IEC 2024 - 154 - 9/3102/CD 3868
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.6 Interaction between application and TRDP protocol layer -> A.6.6.5 PD Redundancy Handling

```plaintext
Derived: sequence of service primitives for redundancy
_IEC_ TRDP TRDP **publisher** TRDP TRDP **subscriber** process data telegram PD.indicate(data) PD.publish PD.indicate(timeout) PD.subscribe PD.putData PD.poll PD.putData _IEC_ TRDP TRDP **publisher** TRDP TRDP **subscriber** IEC CD 61375-2-3 © IEC 2024 - 155 - 9/3102/CD 3889
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.8 State Machine -> Table A.7 â PD publisher state diagram â triggers

```plaintext
Table A.7 – PD publisher state diagram – triggers
3923 **Triggers Description** PD.publish User called PD.publish service primitive continue publishing train-wide PD. topo count change (service primitive PD.putData) immediately (service primitive PD.putDataImmediate) 3924
```

## Train Real-Time Data Protocol (TRDP) -> A.7 Message Data -> A.7.1 Communication model -> Figure A.19 â Message data transfer options

```plaintext
```
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.5 PD-PDU

```plaintext
Derived: PD-PDU diagram
_IEC_ subscribersubscriberpublisher requester / PD-PDU(reply) PD-PDU(request) publisher PD-PDU(reply)PD-PDU(reply) PD-PDU(reply) PD-PDU(request) PD-PDU(reply)PD-PDU(reply) PD-PDU(reply) PD-PDU(request) PD-PDU(reply)PD-PDU(reply) IEC CD 61375-2-3 © IEC 2024 - 144 - 9/3102/CD 3775
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.8 State Machine -> Table A.15 â PD subscriber state diagram â guards

```plaintext
Table A.15 – PD subscriber state diagram – guards
3951 **Guards Description** pattern configured communication pattern for the PD-PDU exchange checkTopoCounts Check the topography counters of the received telegram against the 3952 _IEC_ PD.subscribe WaitForPD PD.unsubscribe pdReceived [OK] [else] [pattern == PUSH] [pattern == PULL] [pattern == PUSH] [pattern == PULL] IEC CD 61375-2-3 © IEC 2024 - 160 - 9/3102/CD
```

## Train Real-Time Data Protocol (TRDP) -> A.7 Message Data -> A.7.6 Interaction between application and TRDP layer -> A.7.6.3 Filtering rules

```plaintext
```
```

## Train Real-Time Data Protocol (TRDP) -> A.7 Message Data -> A.7.6 Interaction between application and TRDP layer -> A.7.6.2 Interaction sequence

```plaintext
```
```

## Train Real-Time Data Protocol (TRDP) -> A.7 Message Data -> A.7.5 MD-PDU -> Figure A.20 â MD-PDU

```plaintext
Figure A.20 – MD-PDU
4014 **MD_PDU::= RECORD** 4015 request 4027
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.8 State Machine -> Table A.12 â PD requester state diagram â actions

```plaintext
Derived: Actions Description
3940 **Actions Description** prepareRequestTelegram prepare a request telegram to one or many publishers time = rxTime (timeout value given in PD.subscribe service primitive) 3941
```

## Train Real-Time Data Protocol (TRDP) -> A.6 Process Data -> A.6.8 State Machine -> Table A.16 â PD subscriber state diagram â actions

```plaintext
Table A.16 – PD subscriber state diagram – actions
3953 **Actions Description** indicate(data) Notify application about a new received process or request telegram (service primitive PD.indicate) Check filter criteria setDataInvalid Sets the PD to initialized/invalid time = rxTime (timeout value given in PD.subscribe service primitive) Discard Discard the telegram
```

## Train Real-Time Data Protocol (TRDP) -> A.7 Message Data -> A.7.6 Interaction between application and TRDP layer -> Table A.19 â TRDP service primitives â Caller

```plaintext
Table A.19 â TRDP service primitives â Caller
4041 **Service primitive Parameters Direction/Description** MD.request msgType â¢ send notification message (âMnâ) userReference Reference returned with the MD.indication. Used by user to callbackFunction Callback function for the incoming reply. sessionId session identifier used and returned by the TRDP layer. comId as defined in Table A.18 etbTopoCnt as defined in Table A.18 opTrnTopoCnt as defined in Table A.18 sourceIpAddr IP source address. destinationIpAddr IP destination address, generated out of respective URIâs using transProtocol UDP or TCP transport layer protocol number of repliers if the request message is sent to known replyTimeOut as defined in Table A.18 range 0..2. MD.indicate TRDP layer â' TRDP user userReference Reference which was submitted with MD.request â¢ reception of a query message (âMqâ) comId as defined in Table A.18 Set to 0 if unknown (error return) Set to 0 if unknown (error return) IEC CD 61375-2-3 © IEC 2024 - 167 - 9/3102/CD **Service primitive Parameters Direction/Description** userStatus User status or error code. MD.confirm TRDP user â' TRDP layer sessionId session identifier as returned by MD.indication. Used by the TRDP replyStatus as defined in Table A.18 TRDP user asks to abort an open session e.g because of a TCN sessionId session identifier used by the TRDP layer. 4042
```

## Train Real-Time Data Protocol (TRDP) -> A.7 Message Data -> A.7.6 Interaction between application and TRDP layer -> Table A.20 â TRDP service primitives â Replier

```plaintext
Table A.20 – TRDP service primitives – Replier
4043 **Service primitive Parameters Direction/Description** MD.addListener Handle Handle for this listener, returned by the TRDP layer associate the listener with the MD.indication DNS. sourceIpAddress2 Defines the upper IP address in case of an IP address range destinationIpAddress IP destination address, generated out of respective URIâs IEC CD 61375-2-3 © IEC 2024 - 168 - 9/3102/CD **Service primitive Parameters Direction/Description** sourceURI[] as defined in Table A.18, only notification/request from that destinationURI as defined in Table A.18, only notification/request with that MD.readdListener TRDP user â' TRDP layer Handle Handle for this listener etbTopoCnt actual etbTopoCnt value opTrnTopoCnt actual opTrnTopoCnt value sourceIpAddress IP source address, generated out of respective URIâs using sourceIpAddress2 Defines the upper IP address in case of an IP address range destinationIpAddress IP destination address, generated out of respective URIâs MD.delListener TRDP user â' TRDP layer Handle Handle returned by the TRDP layer in MD.addListener TRDP layer informs about an event userReference Reference which was submitted with MD.addListener â¢ reception of a request message (âMrâ) comId as defined in Table A.18 Set to 0 if unknown (error return) Set to 0 if unknown (error return) IEC CD 61375-2-3 © IEC 2024 - 169 - 9/3102/CD **Service primitive Parameters Direction/Description** sourceUri as defined in Table A.18 MD.reply TRDP user â' TRDP layer msgType â¢ send reply message (âMpâ) sessionId Session identifier as indicated with MD.indication. Used by comId as defined in Table A.18 MD.release TRDP layer â' TRDP user userReference Reference which was submitted with MD.addListener â¢ TRDP layer error (âMeâ) Set to 0 if unknown (error return) Set to 0 if unknown (error return) 4044
```

## Train Real-Time Data Protocol (TRDP) -> A.7 Message Data -> A.7.2 Roles

```plaintext
Derived: Roles in TRDP message data transfer
_IEC_ caller replier request request caller replier request reply processing the caller replier request reply confirm processing the processing the a) b) c) IEC CD 61375-2-3 © IEC 2024 - 162 - 9/3102/CD
```

## Train Real-Time Data Protocol (TRDP) -> A.7 Message Data -> A.7.7 Topography counter check -> Table A.21 â Topography counter check

```plaintext
Table A.21 – Topography counter check
4078 **Caller Actual topography counter values Topography counter values of the telegram to** **Replier Actual topography counter values Topography counter values of the received** **Topography counter values of the** **Locally stored topography counter values** **Case** etbTopoCnt opTrnTopoCnt etbTopoCnt opTrnTopoCnt 5(3) 0 0 any any (2) Only relevant for the comparison of the topography counter values of the received telegram with the locally (3) Case applies only for replier comparing topography counter values of the received telegram with the locally Key: 0 = topography counter value set to 0 (donât care) 4079
```

## Train Real-Time Data Protocol (TRDP) -> A.7 Message Data -> A.7.5 MD-PDU -> Table A.18 â MD-PDU parameters

```plaintext
Table A.18 – MD-PDU parameters
4034 **Parameter Description Value** sequenceCounter The sequence counter • shall be incremented with each repetition of the Computed _IEC_ 0 15 16 317 8 23 24**sequenceCounter** **protocolVersion** **etbTopoCnt** **datasetLength** **msgType** **sessionId** **sourceUri** **destinationUri** **replyTimeout** **dataset** 0..65388 octets **headerFcs** **opTrnTopoCnt** IEC CD 61375-2-3 © IEC 2024 - 164 - 9/3102/CD **Parameter Description Value** • shall be returned with the reply message protocolVersion The protocol version shall consist of: for incompatible changes, compatible changes Fixed msgType Type of the telegram. ‘4D6E‘H (‘Mn‘) comId Identifier of the user dataset. See also A.5. set by user etbTopoCnt The topography counter: standard part IEC 61375-2-5 (parameter • shall be set by the user if not used. 0..232-1 opTrnTopoCnt The topography counter: which use information from the operational train • shall be set when the source device used the • optional in all other cases. Shall be set to 0 (= invalid) datasetLength Length of the user data set in number of octets without 0 ..65388 Computed replyStatus The status value shall be set by the replier to report the • –1 – reserved < 0: NOK IEC CD 61375-2-3 © IEC 2024 - 165 - 9/3102/CD **Parameter Description Value** • –6 – no reply sessionId The session identification: confirm” session which is composed of a caller • shall identify a “request-error” session when the • shall be computed at caller side and reused at replier • shall be used at caller side to relate a reply or error • shall be used at replier side to identify a • shall be a UUID according to RFC 4122, time-based Computed replyTimeout The reply timeout value shall be set to define the expected 1 .. (232-1) sourceUri The source URI: and “@” destinationUri The destination URI: and “@” headerFcs The header frame check sequence: Computed according dataset The user data.
```

## Train Real-Time Data Protocol (TRDP) -> A.7 Message Data -> A.7.8 MD protocol state machine -> Figure A.24 â TRDP Layer MD telegram reception

```plaintext
Figure A.24 – TRDP Layer MD telegram reception
4219 _IEC_ CompositeStateReceiver mdMessageReceived / mdHandleReceived [exists == TRUE] Start (mdHandleReceived) [msgType == âMpâ] Start / checkMsgHeader [msgType == âMqâ] [msgType == âMcâ] [msgType == âMnâ] [msgType == âMrâ] [msgType == âMrâ] [ else] / discardMsg [else] [else] [else] [else] [else] [else] [OK] [else] / discardMsg [else] / discardMsg [else] [msgType == âMeâ] [exists == TRUE] IEC CD 61375-2-3 © IEC 2024 - 179 - 9/3102/CD
```

## Train Real-Time Data Protocol (TRDP) -> A.7 Message Data -> A.7.8 MD protocol state machine -> Table A.27 â MD replier state diagram â guards

```plaintext
Derived: MD replier state diagram guards
4210 **Guards Description** existsReplySession The reply session for a given session id exists existsListener A listener for the given request with fitting topography counters replyType Type of MD reply telegram as requested by the user in the stateReplySession(sessionId) replier session state for a given session id protocol type, length and topography counter (at least one of the checkTopoCounts Check the topopology counters of the received message against 4211
```

## Train Real-Time Data Protocol (TRDP) -> A.7 Message Data -> A.7.8 MD protocol state machine -> Table A.26 â MD replier state diagram â triggers

```plaintext
Table A.26 – MD replier state diagram – triggers
4208 **Triggers Description** MD.addListener User called MD.addListener service primitive replyTimeout) _IEC_ [msgType == âMrâ] [exists == TRUE] /filterForListener [exists == FALSE ] Start (mdHandleRequest) [msgType == âMrâ AND / mdIndicate(data) [exists == FALSE] [exists == TRUE ] StateWaitForApplReply [replyType == âMpâ] [replyType == âMqâ] entry / indicate(data) MD.reply / leave StateWaitForConfirm / openReplySession mcReceived / indicate(data); leave timeout / leave exit / release (data OR timeout OR abort) Start (mdReplySession) CompositeStateReplier MD.addListener / addListener Start (replier) [state == StateWaitForConfirm] [else] [repeated == TRUE] / discardMsg [mdAbort == TRUE] [else] [else] IEC CD 61375-2-3 © IEC 2024 - 177 - 9/3102/CD
```

## Train Real-Time Data Protocol (TRDP) -> A.7 Message Data -> A.7.8 MD protocol state machine -> Table A.23 â MD caller state diagram â guards

```plaintext
Derived: MD caller state diagram guards
CompositeStateCaller MD.request / mdCallSession [sendType == ‘Mr’] StateWaitForReply [sendType == ‘Mn’] [missingReplies == 0 AND missingConfirms == 0] / leave Start Start (caller) MD.confirm mpReceived Start (mdHandleCallerTimeout) [(maxTimeoutCnt != 0) AND [else] meReceived / closeCallSession
```

