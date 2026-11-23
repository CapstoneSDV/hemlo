## Module 1: The AUTOSAR XML Metamodel from Scratch

### Q1: What is an `.arxml` file, and what package structure organizes the file?
**Answer:**  
An `.arxml` (AUTOSAR XML) file is an industry-standard XML specification defined by the AUTOSAR development partnership. It serves as the primary machine-readable contract between automotive OEMs (e.g., Ford, BMW) and Tier-1 suppliers (e.g., Bosch, Continental) to specify software architectures, hardware topologies, and network communications.  
Every ARXML document begins with a root `<AUTOSAR>` element containing an `<AR-PACKAGES>` container. Inside, nested `<AR-PACKAGE>` elements form a hierarchical namespace (similar to directories or Java packages). Each package contains a `<SHORT-NAME>` and an `<ELEMENTS>` container holding architectural items. Standard schema revisions include Classic Platform R4.0, R4.2, and R20-11.

---

### Q2: What is the fundamental difference between `<APPLICATION-SW-COMPONENT-TYPE>` and `<SW-COMPONENT-PROTOTYPE>`?
**Answer:**  
* `<APPLICATION-SW-COMPONENT-TYPE>` is a **class / blueprint**. It defines what ports, interfaces, and internal behaviors a component has, but it does not represent an actual running instance in a car.
* `<SW-COMPONENT-PROTOTYPE>` is an **instantiated object**. It creates a specific, live instance of that blueprint inside a vehicle composition.  
For example, an engineer defines one blueprint called `DoorController_Type`, but instantiates two prototypes: `FrontLeftDoor_Prototype` and `FrontRightDoor_Prototype`.

---

### Q3: In raw XML, what is the exact difference between a `<P-PORT-PROTOTYPE>` and an `<R-PORT-PROTOTYPE>`?
**Answer:**  
* `<P-PORT-PROTOTYPE>` (Provide Port) is an **output / service provider**. It transmits data or provides an operation to other components.
* `<R-PORT-PROTOTYPE>` (Require Port) is an **input / service consumer**. It receives data or calls operations provided by other components.  
In raw XML, a P-Port encloses a `<PROVIDED-INTERFACE-TREF>`, whereas an R-Port encloses a `<REQUIRED-INTERFACE-TREF>`.

---

### Q4: What is a `<PROVIDED-INTERFACE-TREF>` versus a `<REQUIRED-INTERFACE-TREF>`, and why must both ports share the same interface?
**Answer:**  
These tags are typed references (`TREF`) that point to a shared interface definition (e.g., `<SENDER-RECEIVER-INTERFACE>` or `<CLIENT-SERVER-INTERFACE>`).  
Both ports must reference the identical interface so they agree on the structural data contract—namely, the data types, variable names, and argument order. Without a shared interface, the AUTOSAR compiler cannot bind the ports.

---

### Q5: Look at this raw XML snippet:
```xml
<SW-COMPONENT-PROTOTYPE>
  <SHORT-NAME>tel</SHORT-NAME>
  <TYPE-TREF DEST="APPLICATION-SW-COMPONENT-TYPE">/S01UCON/Swc/Types/TelematicsType</TYPE-TREF>
</SW-COMPONENT-PROTOTYPE>
```
What is the prototype's short name, what type does it instantiate, and what is its absolute AUTOSAR path inside `RootComposition`?
**Answer:**  
* **Short Name:** `tel`
* **Type Instantiated:** `/S01UCON/Swc/Types/TelematicsType` (an Application Software Component Type).
* **Absolute Path:** If declared inside a composition named `RootComposition` located in package `/S01UCON/Swc`, its absolute path is `/S01UCON/Swc/RootComposition/tel`.

---

### Q6: Inside an `<ASSEMBLY-SW-CONNECTOR>`, what exact child elements specify the connection endpoints?
**Answer:**  
An assembly connector requires two sub-elements:
1. `<PROVIDER-IREF>`: Points to the transmitting port via:
   * `<CONTEXT-COMPONENT-REF DEST="SW-COMPONENT-PROTOTYPE">`: Path to the providing component prototype.
   * `<TARGET-P-PORT-REF DEST="P-PORT-PROTOTYPE">`: Path to the providing P-Port.
2. `<REQUESTER-IREF>`: Points to the receiving port via:
   * `<CONTEXT-COMPONENT-REF DEST="SW-COMPONENT-PROTOTYPE">`: Path to the requiring component prototype.
   * `<TARGET-R-PORT-REF DEST="R-PORT-PROTOTYPE">`: Path to the requiring R-Port.

---

### Q7: Write out a 10-line valid ARXML snippet connecting component `tel` to component `bridge`.
**Answer:**  
```xml
<ASSEMBLY-SW-CONNECTOR>
  <SHORT-NAME>telToBridgeConn</SHORT-NAME>
  <PROVIDER-IREF>
    <CONTEXT-COMPONENT-REF DEST="SW-COMPONENT-PROTOTYPE">/S01UCON/Root/tel</CONTEXT-COMPONENT-REF>
    <TARGET-P-PORT-REF DEST="P-PORT-PROTOTYPE">/S01UCON/Types/TelType/p_data</TARGET-P-PORT-REF>
  </PROVIDER-IREF>
  <REQUESTER-IREF>
    <CONTEXT-COMPONENT-REF DEST="SW-COMPONENT-PROTOTYPE">/S01UCON/Root/bridge</CONTEXT-COMPONENT-REF>
    <TARGET-R-PORT-REF DEST="R-PORT-PROTOTYPE">/S01UCON/Types/BridgeType/r_data</TARGET-R-PORT-REF>
  </REQUESTER-IREF>
</ASSEMBLY-SW-CONNECTOR>
```

---

### Q8: What is an `<ECU-INSTANCE>` in ARXML, and what real-world hardware does it represent?
**Answer:**  
An `<ECU-INSTANCE>` represents a distinct, physical microcontroller or electronic computer module in the car (e.g., the Engine Control Module, Central Gateway, Infotainment Head Unit, or Electronic Power Steering ECU). It has its own processor, internal RAM/flash memory, and physical network transceivers.

---

### Q9: In `<SWC-TO-ECU-MAPPING>`, what exact tags link a software component prototype to its physical hardware ECU instance?
**Answer:**  
Inside `<SYSTEM-MAPPING>/<SWC-TO-ECU-MAPPING>`:
* `<COMPONENT-IREFS>/<COMPONENT-IREF>` specifies the target software prototype via `<TARGET-COMPONENT-REF>`.
* `<ECU-INSTANCE-REF>` points to the `<ECU-INSTANCE>` where that component's binary code will execute.

---

### Q10: If an ARXML file defines 10 software components, but only 8 have an entry in `<SWC-TO-ECU-MAPPING>`, what happens to the remaining 2 components?
**Answer:**  
The remaining 2 components are unmapped software entities. In a deployed vehicle, code cannot run without physical hardware; thus, unmapped components cannot be compiled into an ECU image. In ARXML SecDiff, their host is marked as `None` (unassigned virtual context), meaning they cannot communicate over physical vehicle buses.

---

## Module 2: Ports, Interfaces & Software Wiring

### Q11: What is a Port Prototype in AUTOSAR?
**Answer:**  
A Port Prototype is a formal communication portal on a software component. Software components are encapsulated "black boxes"; they cannot read or write global variables. All inputs and outputs must pass explicitly through declared Port Prototypes.

---

### Q12: What is a `<P-PORT-PROTOTYPE>` (Provide Port), and what role does it play in transmitting data?
**Answer:**  
A Provide Port is an output interface. It indicates that the owning software component generates, publishes, or serves data. In the communication graph, dataflow influence originates from the component owning the P-Port.

---

### Q13: What is an `<R-PORT-PROTOTYPE>` (Require Port), and what role does it play in receiving data?
**Answer:**  
A Require Port is an input interface. It indicates that the owning software component consumes or subscribes to data, or invokes an external remote procedure. In the communication graph, dataflow terminates at the component owning the R-Port.

---

### Q14: What is a `<PR-PORT-PROTOTYPE>` (Provide-Require Port), and when is a bidirectional port used?
**Answer:**  
A PR-Port is a hybrid bidirectional port that can both send and receive data under the same interface. It is typically used for symmetric peer-to-peer data synchronization or bidirectional status handshakes between domain controllers.

---

### Q15: What is a `<SENDER-RECEIVER-INTERFACE>`, and what kind of data does it declare?
**Answer:**  
A Sender-Receiver interface models asynchronous, dataflow-oriented communication (such as periodic sensor values, wheel speeds, temperature readings, or status flags). It defines one or more `<VARIABLE-DATA-PROTOTYPE>` elements specifying the data types exchanged.

---

### Q16: What is a `<VARIABLE-DATA-PROTOTYPE>` inside a Sender-Receiver interface?
**Answer:**  
It represents an individual data field or variable inside the interface. For example, inside an interface named `VehicleSpeed_If`, there may be a variable data prototype named `Speed_kmh` of type `UInt16`.

---

### Q17: What is a `<CLIENT-SERVER-INTERFACE>`, and how does it declare operations with arguments?
**Answer:**  
A Client-Server interface models synchronous or asynchronous Remote Procedure Calls (RPC). Instead of variables, it contains one or more `<CLIENT-SERVER-OPERATION>` elements. Each operation specifies input, output, or error arguments (`<ARGUMENT-DATA-PROTOTYPE>`), defining a function that a client calls and a server executes.

---

### Q18: Why must an assembly connector connect a P-Port and an R-Port that share the exact same interface definition?
**Answer:**  
Because the interface defines the structural contract (number of variables, data types, payload sizes). If a P-Port provides a 16-bit integer but an R-Port expects a 64-bit floating point number, memory corruption or type mismatch would occur at the RTE level. AUTOSAR enforces interface equality to guarantee type safety.

---

### Q19: Write out the raw XML for an `<ASSEMBLY-SW-CONNECTOR>`.
**Answer:**  
```xml
<ASSEMBLY-SW-CONNECTOR>
  <SHORT-NAME>BcmToDoorLock_Conn</SHORT-NAME>
  <PROVIDER-IREF>
    <CONTEXT-COMPONENT-REF DEST="SW-COMPONENT-PROTOTYPE">/Veh/Composition/BCM</CONTEXT-COMPONENT-REF>
    <TARGET-P-PORT-REF DEST="P-PORT-PROTOTYPE">/Veh/Types/BcmType/P_DoorLockCmd</TARGET-P-PORT-REF>
  </PROVIDER-IREF>
  <REQUESTER-IREF>
    <CONTEXT-COMPONENT-REF DEST="SW-COMPONENT-PROTOTYPE">/Veh/Composition/DoorActuator</CONTEXT-COMPONENT-REF>
    <TARGET-R-PORT-REF DEST="R-PORT-PROTOTYPE">/Veh/Types/DoorType/R_DoorLockCmd</TARGET-R-PORT-REF>
  </REQUESTER-IREF>
</ASSEMBLY-SW-CONNECTOR>
```

---

### Q20: What is a Delegation Connector (`<DELEGATION-SW-CONNECTOR>`), and how does it pass a signal from a composition boundary to an inner prototype?
**Answer:**  
Compositions can be nested inside other compositions. When a signal arrives at an outer composition's external port, a `<DELEGATION-SW-CONNECTOR>` forwards that port directly down to a port on an internal software component prototype inside that composition. It bridges hierarchical boundaries.

---

### Q21: What is a Pass-Through connector, and how does it differ from an Assembly connector?
**Answer:**  
An Assembly connector joins two sibling components within the same composition. A Pass-Through connector directly connects an input port of a composition to an output port of the same composition without any intermediate processing, routing signals straight through a subsystem.

---

## Module 3: Physical Hardware, ECUs, Buses & Gateways

### Q22: What is an `<ECU-INSTANCE>`, and what physical hardware box in a car does it represent?
**Answer:**  
An `<ECU-INSTANCE>` represents an actual physical Electronic Control Unit hardware box—complete with its own microprocessor, RAM, flash memory, and bus transceiver chips. Examples include the Engine Control Module (ECM), Transmission Control Module (TCM), and Body Control Module (BCM).

---

### Q23: In raw XML, what does `<COMMUNICATION-CONTROLLER>` represent on an `<ECU-INSTANCE>`?
**Answer:**  
It models the physical communication hardware controller embedded in the ECU silicon—such as a CAN controller chip (e.g., Bosch CC770), an Ethernet MAC/PHY, or a LIN master UART—which physically drives signals onto a bus network.

---

### Q24: What is a `<CAN-CLUSTER>` versus an `<ETHERNET-CLUSTER>`, and how does it model a physical bus network?
**Answer:**  
* `<CAN-CLUSTER>` models a physical differential two-wire CAN or CAN-FD bus (CAN_H and CAN_L), operating at 500 kbps to 5 Mbps.
* `<ETHERNET-CLUSTER>` models an Automotive 100BASE-T1 or 1000BASE-T1 switched Ethernet network.  
Both clusters define network-wide physical parameters such as baud rate, bus protocol, and physical channels.

---

### Q25: What is a `<CAN-PHYSICAL-CHANNEL>`, and which ECUs connect to it via `<CAN-COMMUNICATION-CONNECTOR>`?
**Answer:**  
A `<CAN-PHYSICAL-CHANNEL>` represents the actual shared transmission medium. Every ECU wired to that specific bus references that channel through a `<CAN-COMMUNICATION-CONNECTOR>`. All ECUs on the same channel can broadcast and listen to electrical frames on that wire.

---

### Q26: What is a Central Gateway (CGW) ECU, and why does a car have multiple CAN buses connected to it?
**Answer:**  
Different vehicle subsystems have vastly different safety and bandwidth needs:
* Powertrain and Brakes require high-speed, real-time safety buses (CAN-FD).
* Infotainment requires high-bandwidth media networks (Ethernet).
* Door locks and mirrors use cheap, low-speed buses (LIN).  
The Central Gateway (CGW) is a multi-homed ECU connected to all of these buses. It acts as an automotive router, filtering and forwarding authorized messages between isolated domains.

---

### Q27: When an Infotainment ECU sends a message to the Brake ECU on another bus, what role does the Gateway ECU play in forwarding the frame?
**Answer:**  
The Infotainment ECU transmits a frame onto Bus A (Infotainment CAN). The Gateway receives it on its Bus A controller, parses the PDU, verifies routing rules, and re-transmits the signal inside a new PDU onto Bus B (Chassis CAN) where the Brake ECU receives it.

---

### Q28: In raw XML, what is `<SWC-TO-ECU-MAPPING>`, and where does it live inside the `<SYSTEM-MAPPING>` tree?
**Answer:**  
`<SWC-TO-ECU-MAPPING>` resides under `<SYSTEM>` $ightarrow$ `<MAPPINGS>` $ightarrow$ `<SYSTEM-MAPPING>`. It binds software prototypes to physical hardware instances.

---

### Q29: Look at this snippet:
```xml
<SWC-TO-ECU-MAPPING>
  <SHORT-NAME>Map_Brake</SHORT-NAME>
  <COMPONENT-IREFS>
    <COMPONENT-IREF>
      <CONTEXT-COMPOSITION-REF DEST="ROOT-SW-COMPOSITION-PROTOTYPE">/S01UCON/Root</CONTEXT-COMPOSITION-REF>
      <TARGET-COMPONENT-REF DEST="SW-COMPONENT-PROTOTYPE">/S01UCON/Root/brake</TARGET-COMPONENT-REF>
    </COMPONENT-IREF>
  </COMPONENT-IREFS>
  <ECU-INSTANCE-REF DEST="ECU-INSTANCE">/S01UCON/Hardware/ECU_Brakes</ECU-INSTANCE-REF>
</SWC-TO-ECU-MAPPING>
```
Which software prototype is mapped to which physical hardware ECU?
**Answer:**  
Software prototype `/S01UCON/Root/brake` is mapped to execute on hardware ECU instance `/S01UCON/Hardware/ECU_Brakes`.

---

### Q30: If two components are mapped to the same `<ECU-INSTANCE>`, how does the pipeline determine that they are collocated?
**Answer:**  
In `ecu.py`, the function `host_of(model, swc_path)` looks up the component's host ECU. To evaluate a connection between Component A and Component B, `ecu.is_cross_ecu(model, u, v)` compares their hosts:
* If `host_of(A) == host_of(B)`: `cross_ecu = False` (collocated on the same chip).
* If `host_of(A) != host_of(B)`: `cross_ecu = True` (crosses an inter-ECU bus).
## Module 4: The 4-Tier Signal-to-PDU Deployment Chain

### Q31: What is the fundamental difference between a software-level port and a physical network frame?
**Answer:**  
A software port is a virtual programming abstraction in application code (e.g., an RTE API call like `Rte_Write_p_Speed(85)`). A physical network frame is a formatted bitstream transmitted across physical transceivers (containing arbitration IDs, CRC checksums, control bits, and payload bytes). A port has no concept of network timing, bus arbitration, or frame packing.

---

### Q32: What is a `<SYSTEM-SIGNAL>`, and why does it carry a system-wide semantic meaning?
**Answer:**  
A `<SYSTEM-SIGNAL>` represents a standardized vehicle variable across the entire OEM vehicle platform (e.g., `EngineTorque_Nm`). It exists independently of any single ECU or bus type so that multiple vehicle models can share the same functional definitions.

---

### Q33: What is an `<I-SIGNAL>`, and why is it called the "Interaction Layer Signal"?
**Answer:**  
An `<I-SIGNAL>` (Interaction Layer Signal) is the network-specific representation of a system signal. It defines how a system signal is packed into a specific message frame on a specific bus, including its bit length, endianness (Intel/Motorola), and transformation properties.

---

### Q34: How does an `<I-SIGNAL>` reference its parent `<SYSTEM-SIGNAL>` using `<SYSTEM-SIGNAL-REF>`?
**Answer:**  
Inside an `<I-SIGNAL>` element:
```xml
<I-SIGNAL>
  <SHORT-NAME>ISig_BrakeCmd</SHORT-NAME>
  <SYSTEM-SIGNAL-REF DEST="SYSTEM-SIGNAL">/S01UCON/Comm/Signals/Sys_BrakeCmd</SYSTEM-SIGNAL-REF>
</I-SIGNAL>
```
The `<SYSTEM-SIGNAL-REF>` tag contains the exact path to the system signal it implements.

---

### Q35: What is an `<I-SIGNAL-I-PDU>` (Interaction Layer Protocol Data Unit)?
**Answer:**  
An `<I-SIGNAL-I-PDU>` is the data payload container that the AUTOSAR COM stack hands down to the bus interface. It aggregates multiple I-Signals into a single contiguous byte array (e.g., 8 bytes for CAN, 64 bytes for CAN-FD) to be transmitted as a single frame.

---

### Q36: In raw XML, what does an `<I-SIGNAL-TO-I-PDU-MAPPING>` look like?
**Answer:**  
```xml
<I-SIGNAL-TO-I-PDU-MAPPING>
  <SHORT-NAME>Mapping_BrakeTorque</SHORT-NAME>
  <I-SIGNAL-REF DEST="I-SIGNAL">/S01UCON/Comm/Signals/ISig_BrakeTorque</I-SIGNAL-REF>
  <PACKING-BYTE-ORDER>MOST-SIGNIFICANT-BYTE-FIRST</PACKING-BYTE-ORDER>
  <START-POSITION>16</START-POSITION>
  <TRANSFER-PROPERTY>TRIGGERED</TRANSFER-PROPERTY>
</I-SIGNAL-TO-I-PDU-MAPPING>
```
* `<START-POSITION>`: Bit offset inside the PDU payload (e.g., bit 16).
* `<I-SIGNAL-REF>`: Points to the signal being packed.

---

### Q37: What is `<SENDER-RECEIVER-TO-SIGNAL-MAPPING>` inside `<SYSTEM-MAPPING>`?
**Answer:**  
It is the bridge element that connects a software port's data prototype to a network `<SYSTEM-SIGNAL>`. It tells the code generator: *"When component X writes to port Y, route that value to network signal Z."*

---

### Q38: How does `<DATA-ELEMENT-IREF>` specify the context port and target data prototype?
**Answer:**  
Inside `<SENDER-RECEIVER-TO-SIGNAL-MAPPING>`:
* `<CONTEXT-PORT-REF>`: The path to the specific Port Prototype.
* `<TARGET-DATA-PROTOTYPE-REF>`: The path to the specific Variable Data Prototype inside that port's interface.

---

### Q39: Write down the complete 4-step path from a software port to a physical wire in order.
**Answer:**  
$$\text{Port Prototype} \xrightarrow{\text{S/R Mapping}} \text{SYSTEM-SIGNAL} \xrightarrow{\text{ISignal Ref}} \text{I-SIGNAL} \xrightarrow{\text{PDU Mapping}} \text{I-SIGNAL-I-PDU}$$

---

### Q40: What is a `<PDU-TRIGGERING>`, and how does it represent the scheduled broadcast of a PDU on a physical channel?
**Answer:**  
A `<PDU-TRIGGERING>` resides under a physical channel's frame triggering list. It links an `<I-SIGNAL-I-PDU>` to a physical CAN frame ID (e.g., CAN ID `0x240`) and defines whether the frame is transmitted cyclically (e.g., every 20ms) or on event change.

---

### Q41: What is an unmapped signal, and can it reach a physical CAN bus?
**Answer:**  
An unmapped signal is a software port connection that has no corresponding entry in `DATA-MAPPINGS`. It never leaves the local ECU memory; it is handled strictly as an RTE internal RAM copy. It physically cannot reach a CAN bus transceiver.

---

## Module 5: The RTE (Run-Time Environment) & Memory Semantics

### Q42: What does RTE stand for, and what code does the AUTOSAR toolchain generate from the ARXML to implement it?
**Answer:**  
RTE stands for **Run-Time Environment**. The AUTOSAR toolchain parses the ARXML and generates C header and source files (`Rte.c`, `Rte_<swc>.h`) containing API macros like `Rte_Read()`, `Rte_Write()`, `Rte_Call()`, and `Rte_Result()`.

---

### Q43: What is the VFB (Virtual Functional Bus)?
**Answer:**  
The Virtual Functional Bus is an architectural abstraction. It allows software components to be designed and connected as if an unlimited virtual bus exists, completely hiding whether components will eventually be placed on the same ECU or on different ECUs across the vehicle.

---

### Q44: If Component A and Component B are on the same physical ECU, how does the RTE implement the connector between them?
**Answer:**  
The RTE generator realizes the connector as a direct C language pointer assignment, a shared global RAM memory buffer, or an in-memory ring buffer protected by OS spinlocks. No network stack or serial communication is invoked.

---

### Q45: In an intra-ECU connection, is any physical CAN frame transmitted? Is any Ethernet packet created?
**Answer:**  
**No.** Zero CAN frames and zero Ethernet packets are created. The communication never touches any physical transceiver pins.

---

### Q46: Can an attacker tapping the vehicle's OBD-II port or headlight CAN wiring sniff or inject a message that is strictly internal to an ECU's RTE? Why not?
**Answer:**  
**No.** An attacker on the physical CAN wire can only capture or inject frames that physically appear on the bus. Internal RTE communications remain entirely inside the microcontroller's internal silicon SRAM, which is physically inaccessible from external bus wires.

---

### Q47: What does the term `RTE_LOCAL` mean in ARXML SecDiff?
**Answer:**  
`RTE_LOCAL` designates a communication edge where both source and target software components reside on the same physical ECU. The pipeline sets `attrs["authenticated"] = None`, signifying that SecOC is **Not Applicable** because there is no physical wire to protect.

---

### Q48: What security threat exists for an `RTE_LOCAL` connection compared to a bus connection?
**Answer:**  
An `RTE_LOCAL` connection can only be compromised if an attacker already has local code execution (arbitrary memory write / kernel exploit) on that specific ECU microcontroller. A bus connection can be compromised remotely or physically by anyone with physical bus access tapping two wires, requiring zero code execution on the endpoints.

---

## Module 6: SecOC (Secure Onboard Communication) Architecture

### Q49: What is the exact title and standard number of the AUTOSAR SecOC specification?
**Answer:**  
**AUTOSAR Specification of Secure Onboard Communication (SWS SecOC)**, specification document ID **654** (AUTOSAR Classic Platform).

---

### Q50: What is the payload PDU (Authentic PDU) versus the Secured PDU?
**Answer:**  
* **Authentic (Payload) PDU:** The original, raw application data packet (e.g., 4 bytes containing steering torque commands).
* **Secured PDU:** The final network packet transmitted on the wire, which bundles the Authentic PDU together with the Freshness Value slice and the cryptographic MAC tag.

---

### Q51: What is a `<SECURED-I-PDU>` in ARXML?
**Answer:**  
A `<SECURED-I-PDU>` is the formal AUTOSAR metamodel element that defines a SecOC-protected message wrapper on a communication cluster.

---

### Q52: How does `<SECURED-I-PDU>` use `<PAYLOAD-REF>` to wrap an authentic `<I-SIGNAL-I-PDU>`?
**Answer:**  
Inside `<SECURED-I-PDU>`, the `<PAYLOAD-REF DEST="I-SIGNAL-I-PDU">` element contains the exact path of the unencrypted application PDU that it wraps and authenticates.

---

### Q53: What is an Authentication Tag / MAC (Message Authentication Code)?
**Answer:**  
A MAC is a cryptographic checksum generated by hashing the payload data combined with a secret symmetric key and a freshness counter. A receiver holding the shared key can verify that the message originated from the authorized ECU and was not altered in transit.

---

### Q54: What symmetric cipher is typically used in automotive HSMs to generate SecOC MACs?
**Answer:**  
**AES-128 CMAC** (Cipher-based Message Authentication Code using 128-bit Advanced Encryption Standard, specified in NIST SP 800-38B).

---

### Q55: In raw XML, what tag specifies how many bits of MAC are transmitted?
**Answer:**  
`<AUTH-INFO-TX-LENGTH>` (Authentication Information Transmission Length), located inside `<SECURED-I-PDU>` or `<SECURE-COMMUNICATION-PROPS>`.

---

### Q56: What is the Freshness Value Manager (FVM)?
**Answer:**  
The FVM is an AUTOSAR complex driver / software module that maintains dynamic, monotonic anti-replay counters across all participating ECUs to ensure each transmitted frame has a unique freshness state.

---

### Q57: What are the two components of a Freshness Value?
**Answer:**  
1. **Complete Freshness Value:** A large 64-bit internal counter (Trip Counter + Reset Counter + Message Counter) maintained in ECU memory.
2. **Truncated Freshness Value:** The lower 4 to 8 bits transmitted over the wire alongside the message to minimize bus load.

---

### Q58: In raw XML, what tag specifies the length of the freshness value?
**Answer:**  
`<FRESHNESS-VALUE-LENGTH>`, specifying the bit length of the freshness value.

---

### Q59: How does an ECU verify an incoming SecOC PDU?
**Answer:**  
1. The receiving ECU takes the incoming authentic payload and the truncated freshness bits.
2. It reconstructs the full 64-bit freshness counter using its internal FVM state.
3. It passes the payload, full freshness, and its shared AES-128 key into its hardware HSM to recompute the expected CMAC.
4. If the computed MAC matches the received MAC, the frame is authenticated and delivered to the RTE. If they differ, the frame is **silently dropped**, and a security event is logged.

---

### Q60: What is MAC Truncation, and why is it used on CAN-FD?
**Answer:**  
Standard AES-128 CMAC outputs a 128-bit (16-byte) tag. Transmitting 16 bytes of MAC on every 8-byte CAN message would consume 200% overhead and saturate the bus. Automotive engineers truncate the MAC to 24, 32, or 64 bits to fit comfortably inside CAN-FD payload limits while retaining high brute-force resistance.

---

### Q61: What is an unauthenticated wire? Show the exact ARXML difference.
**Answer:**  
An unauthenticated wire carries a raw `<I-SIGNAL-I-PDU>` directly inside a `<PDU-TRIGGERING>` without any `<SECURED-I-PDU>` referencing it.  
* **Protected:** `<PDU-TRIGGERING>` $\rightarrow$ points to `<SECURED-I-PDU>` $\rightarrow$ `<PAYLOAD-REF>` $\rightarrow$ points to `<I-SIGNAL-I-PDU>`.
* **Unprotected:** `<PDU-TRIGGERING>` $\rightarrow$ points directly to `<I-SIGNAL-I-PDU>` (raw, unencrypted).
## Module 7: Threat Boundary Modeling (roles.yaml)

### Q62: What is the file format of `roles.yaml`?
**Answer:**  
Standard YAML (YAML Ain't Markup Language). It is parsed in Python using `PyYAML` (`yaml.safe_load`).

---

### Q63: Why does ARXML SecDiff use an external `roles.yaml` file instead of expecting threat metadata inside the `.arxml` file?
**Answer:**  
AUTOSAR XML is strictly an architectural deployment specification; its standard schema does not define threat boundary tags like `<ATTACKER-ENTRY-POINT>` or `<SAFETY-TARGET>`. Threat boundaries and ASIL ratings originate from external engineering processes: HARA (ISO 26262) and TARA (ISO/SAE 21434). Storing this context in `roles.yaml` provides **Security-as-Code**, keeping the threat model version-controlled alongside the architecture.

---

### Q64: What is a HARA (Hazard Analysis and Risk Assessment under ISO 26262)?
**Answer:**  
HARA is the mandatory safety engineering process that identifies operational hazards resulting from system failures (e.g., unintended steering torque, loss of braking) and assigns an **ASIL** (Automotive Safety Integrity Level) from QM to ASIL-D based on Severity, Exposure, and Controllability.

---

### Q65: What is a TARA (Threat Analysis and Risk Assessment under ISO/SAE 21434)?
**Answer:**  
TARA is the cybersecurity risk engineering process that identifies threat scenarios, assets, damage scenarios, and attack paths originating from external communication interfaces (cellular, Wi-Fi, BLE, diagnostic ports).

---

### Q66: In `roles.yaml`, what is the structure of the `entry_points` list?
**Answer:**  
```yaml
entry_points:
  - node: /S01UCON/Swc/Root/tel
    reason: cellular telematics unit (CVE-2015-5611 attack surface)
  - node: /S01UCON/Swc/Root/ivi
    reason: in-vehicle infotainment / Wi-Fi / Bluetooth
```
* `node`: The exact AUTOSAR path (or glob pattern) matching the component prototype.
* `reason`: The engineering justification explaining the external attack surface.

---

### Q67: In `roles.yaml`, what is the structure of the `critical` list?
**Answer:**  
```yaml
critical:
  - node: /S01UCON/Swc/Root/steer
    asil: D
    reason: electric power steering torque actuator
```
* `node`: The target component prototype path.
* `asil`: The ISO 26262 safety rating (`D`, `C`, `B`, `A`, or `QM`).
* `reason`: Description of the physical hazard.

---

### Q68: What are the 5 ISO 26262 safety integrity levels, and which is the most critical?
**Answer:**  
1. **ASIL-D**: Highest criticality (life-threatening, e.g., steering, braking).
2. **ASIL-C**: High criticality (e.g., electronic suspension, ACC).
3. **ASIL-B**: Medium criticality (e.g., brake lights, cluster display).
4. **ASIL-A**: Low criticality (e.g., rear fog lamps, cabin lighting).
5. **QM**: Quality Management (non-safety, e.g., radio, infotainment).  
**ASIL-D is the most critical.**

---

### Q69: What are three standard examples of untrusted entry points in a modern connected car?
**Answer:**  
1. **Telematics Control Unit (TCU):** Embedded 4G/5G cellular modem.
2. **In-Vehicle Infotainment (IVI):** Bluetooth and Wi-Fi chipsets.
3. **On-Board Diagnostics (OBD-II):** Physical 16-pin diagnostic port under the dashboard.

---

### Q70: What are three standard examples of ASIL-D safety-critical targets in a car?
**Answer:**  
1. **Electronic Power Steering (EPS)**: Steer-by-wire torque actuator.
2. **Electronic Stability Control (ESC) / ABS**: Hydraulic brake pressure modulator.
3. **Powertrain / Inverter Controller**: High-voltage traction torque delivery.

---

### Q71: What happens if an entry point path in `roles.yaml` has a typo?
**Answer:**  
In `roles.py`, the classification function checks whether every pattern matches at least one node in the graph. Unmatched entries are appended to `Roles.unmatched` and reported as warnings, preventing typos from silently disabling security checks.

---

## Module 8: Stage 1 — AST Parsing & Ingestion (xmlutil.py & parser.py)

### Q72: What external Python XML parsing library is used?
**Answer:**  
`lxml.etree` (a high-performance, C-based libxml2 wrapper).

---

### Q73: What is an XML namespace, and why do raw ARXML tags look like `{http://autosar.org/schema/r4.0}SHORT-NAME`?
**Answer:**  
XML namespaces prevent tag collisions by prefixing tags with a URI. In raw `lxml`, elements are qualified as `{URI}tag`. Because different OEMs use different AUTOSAR release URIs (e.g., R4.0 vs R4.3), hardcoding tag names causes parsing failures.

---

### Q74: How does `xmlutil.py` strip namespaces?
**Answer:**  
`xmlutil.py` iterates over all elements and reassigns each tag to its local name using `tag.split("}")[-1]`, or uses an XSLT/iterative tag renamer to produce namespace-agnostic elements that can be queried cleanly as `el.tag == "SHORT-NAME"`.

---

### Q75: What is the input to `parser.parse()`, and what Python object is its output?
**Answer:**  
* **Input:** A list of file paths to `.arxml` documents.
* **Output:** An instance of the `arxml_secdiff.model.Model` dataclass.

---

### Q76: How does `parser.py` recursively construct the absolute path of every XML element from root to leaf?
**Answer:**  
As `parser.py` traverses down the XML tree, it checks if an element has a `<SHORT-NAME>`. If it does, it appends `f"/{short_name}"` to the running context string. This builds canonical paths like `/S01UCON/Swc/Root/tel`.

---

### Q77: What is `model.index` in Python?
**Answer:**  
It is a flat hash dictionary (`dict[str, lxml.etree._Element]`) mapping absolute AUTOSAR path strings directly to their in-memory XML DOM elements.

---

### Q78: Why is querying `model.index[path]` an $\mathcal{O}(1)$ operation compared to $\mathcal{O}(N)$ XPath queries?
**Answer:**  
`model.index` is a Python hash map with constant-time lookup. An XPath query (`tree.xpath("//SW-COMPONENT-PROTOTYPE[SHORT-NAME='tel']")`) must walk the entire tree of 100,000+ elements sequentially every time, which is computationally prohibitive.

---

### Q79: What dataclasses are stored inside the `Model` object?
**Answer:**  
* `model.prototypes`: `dict[str, Prototype]`
* `model.assembly_connectors`: `dict[str, AssemblyConnector]`
* `model.pdus`: `dict[str, Pdu]`
* `model.ecus`: `dict[str, EcuInstance]`
* `model.system_signals`: `dict[str, SystemSignal]`
* `model.isignals`: `dict[str, ISignal]`
* `model.routes`: `list[SignalRoute]`

---

### Q80: How does `parser.py` populate `model.prototypes`?
**Answer:**  
It iterates through `model.index`, finds all elements with tag `SW-COMPONENT-PROTOTYPE`, extracts `short_name`, `type_ref` (from `<TYPE-TREF>`), and parent `composition`, and stores them in `Prototype` dataclasses.

---

### Q81: How does `parser.py` populate `model.assembly_connectors`?
**Answer:**  
It finds all `ASSEMBLY-SW-CONNECTOR` elements, extracts `<PROVIDER-IREF>` (component and port) and `<REQUESTER-IREF>` (component and port), and stores them in `AssemblyConnector` dataclasses.

---

### Q82: What does `parser.py` do when a reference tag fails to resolve?
**Answer:**  
If a target path does not exist in `model.index`, `parser.py` records an unresolved reference error. When the GUI displays `Unresolved References: 0`, it proves the model is syntactically closed and self-contained.

---

## Module 9: Stage 2 — Topological Multigraph Construction (graph.py & signals.py)

### Q83: What Python graph library is used in `graph.py`?
**Answer:**  
`networkx` (`import networkx as nx`).

---

### Q84: What is a directed multigraph (`nx.MultiDiGraph`), and how does it differ from a standard directed graph (`nx.DiGraph`)?
**Answer:**  
`nx.DiGraph` allows at most one directed edge from node $u$ to node $v$. If you add another edge, it overwrites the first. `nx.MultiDiGraph` allows multiple parallel edges between the same two nodes, distinguished by unique keys (`key=f"{conn.path}#data"`).

---

### Q85: In `graph.py`, what is the unique identifier (key) of a node?
**Answer:**  
The full absolute AUTOSAR path string of the component prototype (e.g., `/S01UCON/Swc/Root/tel`).

---

### Q86: Why is node identity the Prototype path rather than the Component Type?
**Answer:**  
If node identity were the Component Type, all prototypes sharing that type (e.g., 4 wheel sensors) would collapse into a single node. A reachability walk reaching Front-Left Wheel could falsely traverse out of Rear-Right Wheel, creating nonexistent phantom attack paths.

---

### Q87: In `graph.py`, what attributes are stored on each node?
**Answer:**  
* `short_name`: Leaf name string.
* `kind`: `"prototype"`, `"composition"`, or `"unresolved"`.
* `type_ref`: Path to component blueprint.
* `host`: The physical ECU name (from `ecu.host_of()`).
* `provided_ports`: Tuple of output port names.
* `required_ports`: Tuple of input port names.

---

### Q88: What does the direction of an edge in the graph represent?
**Answer:**  
It represents **dataflow influence**: the ability of the source component to transmit data or commands that alter the internal state or execution behavior of the target component.

---

### Q89: How are Sender-Receiver connectors converted into graph edges?
**Answer:**  
They produce **1 directed edge** pointing from Provider to Requester:
```python
graph.add_edge(provider, requester, key=f"{conn.path}#data", influence="data")
```

---

### Q90: How are Client-Server connectors converted into graph edges?
**Answer:**  
They produce **2 directed edges**:
```python
graph.add_edge(requester, provider, key=f"{conn.path}#request", influence="request")
graph.add_edge(provider, requester, key=f"{conn.path}#response", influence="response")
```

---

### Q91: Why does a Client-Server connector need two edges?
**Answer:**  
The client initiates the call (request), allowing an attacker controlling the client to pass malformed arguments or flood the server. The server then computes and returns data (response), influencing the client. Modeling both directions captures client-to-server and server-to-client exploit vectors.

---

### Q92: In `signals.py`, how does `_resolve_routes()` join Data Mappings $\rightarrow$ System Signals $\rightarrow$ ISignals $\rightarrow$ PDUs?
**Answer:**  
It builds indexing dictionaries (`isignals_by_signal` and `pdus_by_isignal`). For every data mapping from a port to a system signal, it traverses through the matching I-Signals to find all carrying PDUs, creating a list of `SignalRoute` objects.

---

### Q93: What does `signals.pdus_for_port(model, port)` return?
**Answer:**  
A Python set (`set[str]`) containing the paths of all physical PDUs that carry signals originating from or received by that port.

---

### Q94: What does `signals.is_bus_visible(model, port)` return?
**Answer:**  
It returns `bool(pdus_for_port(model, port))`. If `False`, the port has no PDU and is strictly internal to ECU RAM.

---

### Q95: In `graph.py`, what does the edge attribute `cross_ecu` store?
**Answer:**  
A boolean: `True` if the source and target components reside on different physical hardware ECUs; `False` if both components share the same physical ECU.
## Module 10: Stage 3 — 3-Valued SecOC Wire Annotation (secoc.py)

### Q96: What are the three states of the `attrs["authenticated"]` edge attribute?
**Answer:**  
1. `None`: SecOC is **Not Applicable** (`RTE_LOCAL`).
2. `False`: SecOC is **Applicable but Absent** (`UNPROTECTED`).
3. `True`: SecOC is **Present and Active** (`AUTHENTICATED`).

---

### Q97: Explain the physical reality of each state.
**Answer:**  
* `None`: Data stays inside ECU RAM pointers; there is no physical network wire to tap or protect.
* `False`: Data travels over a physical bus wire (CAN/CAN-FD/Ethernet) in raw, unencrypted frames vulnerable to sniffing and injection.
* `True`: Data travels over a physical bus wire wrapped in a `SECURED-I-PDU` with cryptographic MAC and Freshness protection.

---

### Q98: What catastrophe occurs in an automotive security report if you replace `None` with `False`?
**Answer:**  
In a vehicle architecture with 10,000 internal function calls between software components on the same ECU, replacing `None` with `False` would falsely mark all 10,000 internal RAM calls as "unencrypted network vulnerabilities." This massive false-positive flood drowns real issues and causes engineers to ignore the tool.

---

### Q99: How does `secoc.from_arxml()` build a dictionary of `SecOcProfile` objects?
**Answer:**  
It loops through all PDUs in `model.pdus`, filters for `pdu.kind == "SECURED-I-PDU"`, follows `<PAYLOAD-REF>` to find the protected PDU, extracts `<FRESHNESS-VALUE-LENGTH>` and `<AUTH-INFO-TX-LENGTH>`, and stores a `SecOcProfile(authenticated=True)` keyed by the authentic payload PDU path.

---

### Q100: Why does having zero carrier PDUs mean authentication is `None`?
**Answer:**  
In `secoc.annotate()`, `carriers` is the set of PDUs transporting the connector's signals. If `len(carriers) == 0`, the signal never touches a network stack—it is internal memory. SecOC is an inter-ECU bus protocol, so it cannot be applied. Thus, `authenticated = None`.

---

### Q101: What is the "weakest link" rule in `secoc.annotate()`?
**Answer:**  
If a software connector multiplexes multiple signals carried by several PDUs, an attacker only needs to forge or tamper with **one** unprotected PDU to compromise the data stream. Therefore, if *any* carrier PDU lacks SecOC, the entire edge is marked `authenticated = False`.

---

### Q102: What is an overlay file (`load_overlay()`), and why does ARXML evidence always take precedence?
**Answer:**  
An overlay file is a YAML document where teams manually declare SecOC configurations if their Tier-1 suppliers withheld confidential PDU configurations. In `secoc.profiles()`, ARXML-derived profiles overwrite overlay entries because an explicit `<SECURED-I-PDU>` in the architecture file is verifiable ground truth.

---

### Q103: What does `secoc.unprotected_edges(graph)` return?
**Answer:**  
A list of edge tuples `(u, v, key)` for all edges where `authenticated == False`. It filters out `None` (`RTE_LOCAL`) and `True` (`AUTHENTICATED`), isolating only the physical bus wires exposed to attack.

---

## Module 11: Stage 4 — Dual-Graph Diff & Pruned DFS Reachability (diff.py & reach.py)

### Q104: What does `diff.py` take as input?
**Answer:**  
The baseline multigraph $G_{\text{before}}$ and the candidate multigraph $G_{\text{after}}$.

---

### Q105: How does `diff.py` compute structural edge differences?
**Answer:**  
It compares edge keys between the two graphs:
* $\Delta E^+ = E_{\text{after}} \setminus E_{\text{before}}$: Added edges (new connectors or new Client-Server operations).
* $\Delta E^- = E_{\text{before}} \setminus E_{\text{after}}$: Removed edges (deprecated or disconnected connectors).

---

### Q106: What is a "re-hosted component" in `diff.py`, and why does changing a component's ECU mapping trigger a security check?
**Answer:**  
A re-hosted component is a prototype that exists in both graphs but whose host ECU changed ($\text{ECU}_{\text{before}}(v) \neq \text{ECU}_{\text{after}}(v)$). If a component was previously on an isolated internal ECU and is moved to an ECU connected to the cellular modem, its connections transition from safe internal memory (`RTE_LOCAL`) to exposed bus wires (`UNPROTECTED`).

---

### Q107: What is the goal of `reach.py`?
**Answer:**  
To discover whether an untrusted entry point $s \in S$ can transitively influence an ASIL-D critical target $t \in T$ through a sequence of unauthenticated hops.

---

### Q108: What search algorithm does `reach.py` implement?
**Answer:**  
A custom, recursively constrained **Depth-First Search (DFS)** with cryptographic boundary pruning.

---

### Q109: Why does `reach.py` use `graph.successors(current_node)` instead of `graph.neighbors(current_node)`?
**Answer:**  
In a directed multigraph, `neighbors()` returns both incoming and outgoing adjacent nodes. Attack influence can only propagate **forward** along outgoing edges. `graph.successors()` ensures the traversal strictly follows dataflow influence direction.

---

### Q110: How does `reach.py` prevent infinite recursion in cyclic graphs?
**Answer:**  
It maintains an active recursion set `visited: set[str]`. Before traversing an edge $(u, v)$, it checks `if v in visited: continue`. When backtracking, it removes the node, allowing alternative acyclic simple paths to be explored while killing infinite loops.

---

### Q111: What is the Cryptographic Pruning Rule in `reach.py`?
**Answer:**  
If an edge has `attrs["authenticated"] == True`, the DFS **does not traverse across it**. Because SecOC verifies MACs and freshness, an attacker on the source side cannot forge frames that the receiver will accept. The cryptographic barrier stops the exploit chain.

---

### Q112: What is `cutoff = 12` in `reach.py`?
**Answer:**  
It is the maximum path depth limit. In production vehicle architectures, functional call chains rarely exceed 4 to 6 ECU hops. Setting a cutoff of 12 hops prevents combinatorial path explosion in large models while comfortably capturing all realistic exploit chains.

---

### Q113: What is the definition of reachable paths in the baseline graph: $R(G_{\text{before}})$?
**Answer:**  
The set of all valid unauthenticated paths connecting any seed $s \in S$ to any target $t \in T$ in the baseline release.

---

### Q114: What is the definition of reachable paths in the update graph: $R(G_{\text{after}})$?
**Answer:**  
The set of all valid unauthenticated paths connecting any seed $s \in S$ to any target $t \in T$ in the proposed update candidate.

---

### Q115: How is the newly opened attack path delta calculated?
**Answer:**  
$$\Delta R = R(G_{\text{after}}) \setminus R(G_{\text{before}})$$
It is the set difference containing paths present in the update candidate that did not exist in the baseline.

---

### Q116: If an unauthenticated attack path existed in $G_{\text{before}}$ and remains in $G_{\text{after}}$, is it in $\Delta R$?
**Answer:**  
**No.** Pre-existing paths cancel out in the set difference. Focusing strictly on $\Delta R$ ensures the release gate reports only regressions introduced by the current software commit, preventing developers from being blocked by legacy technical debt.

---

## Module 12: Stage 5 — ISO/SAE 21434 Risk Scoring (severity.py)

### Q117: What standard defines the automotive cybersecurity risk scoring framework?
**Answer:**  
**ISO/SAE 21434:2021** ("Road vehicles — Cybersecurity engineering"), specifically the worked example in **Annex H**.

---

### Q118: What are the two axes of the 2D risk matrix?
**Answer:**  
1. **Safety Impact ($I$):** Severity of harm if the target component is manipulated.
2. **Attack Feasibility ($F$):** Ease of exploiting the communication path.

---

### Q119: In `severity.py`, how is Safety Impact mapped from ISO 26262 ASIL ratings?
**Answer:**  
* `ASIL-D` $\rightarrow$ `severe`
* `ASIL-C` $\rightarrow$ `major`
* `ASIL-B` / `ASIL-A` $\rightarrow$ `moderate`
* `QM` $\rightarrow$ `negligible`

---

### Q120: In `severity.py`, how is Attack Feasibility evaluated?
**Answer:**  
* **`high`**: Path contains unauthenticated physical bus hops (CAN/CAN-FD). Commodity hardware ($<\$20$) can inject frames with zero cryptographic keys.
* **`medium`**: Partially isolated or gateway-filtered bus.
* **`low`**: SecOC cryptographic protection present.
* **`very-low`**: Intra-ECU memory path (`RTE_LOCAL`).

---

### Q121: What is the Remote Surface Feasibility Boost?
**Answer:**  
If an attack path originates from an externally accessible wireless interface (`cellular`, `wifi`, `bluetooth`, `radio`), `severity.py` increments the base feasibility by +1 level (e.g., from `medium` to `high`), recognizing that remote attacks require no physical vehicle access.

---

### Q122: Write down the 2D matrix lookup table:
$$\text{Risk} = \text{RISK\_MATRIX}[(\text{Impact}, \text{Feasibility})]$$
**Answer:**  
```
               FEASIBILITY
IMPACT         Very-Low   Low     Medium   High
───────────────────────────────────────────────
Severe            2        3        4       5   <-- BLOCK
Major             1        2        3       4   <-- FLAG
Moderate          1        2        2       3
Negligible        1        1        1       1
```

---

### Q123: What is Downstream Impact Inheritance?
**Answer:**  
When scoring an intermediate connector (e.g., Modem $\rightarrow$ Gateway), the Gateway itself is non-safety (QM / Negligible). If scored in isolation, the risk would be negligible. In `severity.py`, `BuiltinScorer` walks downstream along reachable paths in $G_{\text{after}}$, finds the reachable ASIL-D Brake target, and elevates the intermediate connector's impact to **`severe`**. The rationale records: `"inherited severe impact from downstream target /Brake"`.

---

### Q124: What is Assumed Input Tainting (`Score.assumed = True`)?
**Answer:**  
When `roles.yaml` is missing, `roles.py` guesses entry points and targets using substring heuristics (e.g., `"brake"`, `"telematic"`). To prevent false alarms from blocking builds, `severity.py` stamps `assumed = True` on the score. By default, `gate.py` downgrades assumed blocking findings to `FLAG`.

---

### Q125: What is the `ExternalScorer` class?
**Answer:**  
A pluggable IPC interface. It sends finding payloads as JSON over `stdin` to an external process (e.g., corporate TARA tool, VERA) and reads back `{"impact": "severe", "feasibility": "high", "risk": 5}` over `stdout`, enabling custom enterprise risk algorithms.
## Module 13: Stage 5 — Release Gate Decisions & Policy (gate.py)

### Q126: What are the four release gate verdicts in `gate.py`, and what are their exit codes?
**Answer:**  
1. **`PASS`** (Exit Code **`0`**): All checks clean; release approved.
2. **`FLAG`** (Exit Code **`1`**): Medium risk or assumed findings; human review required.
3. **`INCONCLUSIVE`** (Exit Code **`2`**): Analysis could not run (missing roles); cannot release unverified software.
4. **`BLOCK`** (Exit Code **`3`**): Actionable critical vulnerability ($\text{Risk} \ge 5$); release blocked.

---

### Q127: What is the exact precedence order of verdicts in `gate.py`?
**Answer:**  
$$\text{BLOCK} > \text{INCONCLUSIVE} > \text{FLAG} > \text{PASS}$$

---

### Q128: Why does `BLOCK` outrank `INCONCLUSIVE`?
**Answer:**  
If an architecture has 10 subsystems, and Subsystem 10 was missing configuration (yielding inconclusive), but Subsystem 1 contains a confirmed, unencrypted attack path from cellular telemetry to the electric power steering, that release **must be stopped immediately**. A confirmed critical vulnerability is immediately actionable regardless of incomplete data elsewhere.

---

### Q129: Why does `INCONCLUSIVE` outrank `PASS`?
**Answer:**  
Because **absence of evidence is not evidence of absence**. A tool that finds zero bugs because the security test was never executed must never report a clean `PASS`. Claiming a software release is secure when it was simply untested violates automotive safety compliance (UN ECE R155 / R156).

---

### Q130: What happens if an engineer runs the pipeline with zero entry points defined?
**Answer:**  
`reach.py` generates finding `findings_mod.NOT_ANALYSED`. In `gate.py`, this category automatically evaluates to **`INCONCLUSIVE` (Exit Code 2)**, preventing unconfigured builds from passing.

---

### Q131: In `gate.py`, what are the default thresholds for `block_at` and `flag_at`?
**Answer:**  
* `block_at = 5` (Risk 5 findings block the build).
* `flag_at = 3` (Risk 3 and 4 findings trigger a flag/warning).

---

### Q132: What is the default policy for assumed findings?
**Answer:**  
If `policy.block_on_assumed == False` (the default), any finding that scored Risk 5 but whose inputs were guessed (`score.assumed == True`) is downgraded to **`FLAG`**. This prevents blocking a factory build on a regex guess while still alerting security engineers to provide verified `roles.yaml` configurations.

---

### Q133: What are policy waivers (`policy.accepted`), and how does an engineering team accept a known risk?
**Answer:**  
A team can add finding IDs (e.g., `rehosted-component:/V/Swc/ambientLight`) to the `accepted` list in `policy.yaml`. During evaluation, `gate.py` filters out accepted findings before applying thresholds, allowing documented, risk-accepted items to pass.

---

### Q134: What is `UNWAIVABLE = frozenset({NOT_ANALYSED})`?
**Answer:**  
It is an immutable set of finding categories that the gate refuses to suppress. If a developer attempts to add `not-analysed` to the accepted list, `gate.py` refuses the waiver, records a `refused_acceptance`, and maintains the `INCONCLUSIVE` verdict.

---

### Q135: What is `Decision.stale_acceptances`?
**Answer:**  
It tracks waivers in `policy.yaml` whose corresponding findings no longer exist in the architecture. It alerts security teams that a previously accepted vulnerability has been refactored or deleted, preventing obsolete waivers from cluttering the configuration.

---

## Module 14: Step-by-Step Hand-Worked Trace of 01_jeep_uconnect

### Q136: In `01_jeep_uconnect/roles.yaml`, what are the entry points and target?
**Answer:**  
* **Entry Points ($S$):** `/S01UCON/Swc/Root/tel` (Cellular) and `/S01UCON/Swc/Root/ivi` (Infotainment).
* **Critical Target ($T$):** `/S01UCON/Swc/Root/steer` (Electric Power Steering, rated **ASIL-D**).

---

### Q137: In `01_jeep_uconnect/before.arxml`, what are the baseline statistics?
**Answer:**  
* **Nodes:** 28 Component Prototypes across 11 physical ECUs.
* **Edges:** 23 Communication Connectors.
* **Reachable paths from $S \to T$:** Exactly **0 paths**. The head unit has no connection to the chassis bus.

---

### Q138: In `01_jeep_uconnect/after.arxml`, what two assembly connectors are added, and what carrying PDUs are assigned to them?
**Answer:**  
1. `huToBridge`: Connects Infotainment (`ivi`) $\rightarrow$ Microcontroller (`bridge`). Carries PDU `huToBridgeIPdu`.
2. `bridgeToSteer`: Connects Microcontroller (`bridge`) $\rightarrow$ Steering (`steer`). Carries PDU `bridgeToSteerIPdu`.  
**SecOC State:** Neither PDU has a `<SECURED-I-PDU>` wrapper; both are raw and **unauthenticated**.

---

### Q139: In Stage 4, write out the exact node sequences of the two newly opened attack paths ($\Delta R$).
**Answer:**  
1. **Path 1 (2 hops):**
   $$\text{ivi} \xrightarrow{\text{huToBridge}} \text{bridge} \xrightarrow{\text{bridgeToSteer}} \text{steer}$$
2. **Path 2 (3 hops):**
   $$\text{tel} \xrightarrow{\text{telToIvi}} \text{ivi} \xrightarrow{\text{huToBridge}} \text{bridge} \xrightarrow{\text{bridgeToSteer}} \text{steer}$$

---

### Q140: In Stage 5, write out the exact four findings generated, their risk calculations, and the final verdict.
**Answer:**  
1. **Finding 1 (`newly-reachable`):**  
   * **Title:** `ivi can now reach steer`
   * **Score:** **Risk 5** [Impact: `severe` / Feasibility: `high`]
   * **Rationale:** `steer is ASIL D -> severe impact; 2 of 2 hops cross an unauthenticated bus.`
2. **Finding 2 (`newly-reachable`):**  
   * **Title:** `tel can now reach steer`
   * **Score:** **Risk 5** [Impact: `severe` / Feasibility: `high`]
   * **Rationale:** `steer is ASIL D -> severe impact; 2 of 3 hops cross an unauthenticated bus.`
3. **Finding 3 (`unprotected-new-hop`):**  
   * **Title:** `Unauthenticated bus traffic on bridgeToSteer`
   * **Score:** **Risk 5** [Impact: `severe` / Feasibility: `high`]
   * **Rationale:** `this hop lies on a route to steer, so it inherits that target's severe impact; raw CAN frame needs no keys.` (Downstream Impact Inheritance)
4. **Finding 4 (`unprotected-new-hop`):**  
   * **Title:** `Unauthenticated bus traffic on huToBridge`
   * **Score:** **Risk 5** [Impact: `severe` / Feasibility: `high`]
   * **Rationale:** `this hop lies on a route to steer, so it inherits that target's severe impact; raw CAN frame needs no keys.` (Downstream Impact Inheritance)  
* **Final Verdict:** **`BLOCK`** (Exit Code **`3`**).  
* **Outcome:** The pull request is rejected, preventing the remote steering vulnerability from entering production.
