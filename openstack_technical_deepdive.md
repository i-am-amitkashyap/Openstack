# OpenStack Networking Deep-Dive: PEX-Stage vs. Game-01

This document provides a technical breakdown of the networking models used in **PEX-Stage** and **Game-01**, focusing on OpenStack primitives: **Networks**, **Subnets**, **Ports**, and **Routers**.

---

## 2. Technical Component Breakdown

### A. Network (The L2 Layer)
**Think of it as:** A virtual switch or a VLAN.
*   **Role:** Defines a broadcast domain. VMs attached to the same "Network" can talk to each other directly using MAC addresses (Layer 2).
*   **In PEX-Stage:** We have many networks (e.g., `TA-LAN`, `IA-LAN`) to separate broadcast traffic relative to departments.
*   **In Game-01:** We have networks like `Game-LAN`, but they act more like "cables" plugging into the Firewall.

### B. Subnet (The L3 Layer)
**Think of it as:** The IP Addressing rules for that Network.
*   **Role:** Defines the IP range (e.g., `172.16.17.0/24`) and the Gateway IP.
*   **Key Detail:** A "Network" can have multiple "Subnets", but usually it's 1-to-1.
*   **DHCP:** OpenStack often provides a DHCP server on the Subnet to give IPs to VMs automatically.

### C. Port (The Connection Point)
**Think of it as:** A virtual network interface card (NIC) or a switch port.
*   **Role:** Every connection is a "Port".
    *   A VM has a Port.
    *   A Router has a Port (its interface).
    *   A DHCP server has a Port.
*   **Importance:** Security Groups (Firewall rules) are applied **per Port**.

### D. Router (The Gateway)
This is where the architectures differ significantly.

#### Model 1: PEX-Stage (Neutron Router)
*   **Object:** Native OpenStack Router resource.
*   **Mechanism:** OpenStack creates a Linux Network Namespace on the underlying host. It uses `iptables` and Linux routing tables.
*   **Traffic Flow:**
    1.  VM sends packet to Gateway IP (Standard Linux Route).
    2.  Packet hits the OpenStack Router Namespace.
    3.  Router performs **SNAT** (Source NAT) if going to the internet.
    4.  Packet leaves via the External Network.

#### Model 2: Game-01 (VM as Router)
*   **Object:** A standard VM (Nova Instance) with packet forwarding enabled.
*   **Mechanism:** The VM runs an OS like **pfSense**. It acts as a gateway for other VMs.
*   **Traffic Flow:**
    1.  Game Server VM sends packet to Gateway IP (which is the **Private IP of the Firewall VM**).
    2.  OpenStack Switch layer (L2) delivers packet to the Firewall VM's Port.
    3.  **Inside the Firewall VM:**
        *   The OS (pfSense) receives the packet.
        *   It consults its *own* internal routing table and firewall rules.
        *   It decides whether to drop it or forward it.
    4.  If allowed, the Firewall VM sends it out its *Warning: WAN Interface* (another Port attached to the External Network).

---

## 3. Step-by-Step Traffic Walkthrough

Let's trace a packet going from a Server to the Internet.

### Scenario A: PEX-Stage (Standard)
**Path:** `VM` -> `Neutron Router` -> `Internet`

1.  **VM (172.16.17.10)** sends packet to **8.8.8.8**.
2.  VM checks OS route: "Gateway is **172.16.17.1**".
3.  **L2 Layer:** VM sends packet to the MAC address of the Gateway.
4.  **OpenStack:** The "Gateway Port" (172.16.17.1) is owned by `RTR-TA-STAGE`.
5.  **Router Action:** `RTR-TA-STAGE` receives packet. It looks at its route table. "To reach Internet, go via `PEX-EXT-RTR-1`".
6.  **Next Hop:** Packet moves to Central Router `PEX-EXT-RTR-1`.
7.  **Final NAT:** Central Router applies SNAT (changes Source IP to Public IP `192.168.40.197`) and sends it to the Provider Network.

### Scenario B: Game-01 (Custom Firewall)
**Path:** `Game Server` -> `GameFW1 (VM)` -> `Internet`

1.  **Server (10.251.0.100)** sends packet to **8.8.8.8**.
2.  Server checks OS route: "Gateway is **10.251.0.9**".
3.  **L2 Layer:** Server sends packet to MAC address of **10.251.0.9**.
4.  **OpenStack:** See's destination is just another VM Port (`GameFW1`). It delivers the packet like any normal local traffic.
5.  **Firewall VM Action:** `GameFW1` (pfSense) OS receives the packet on its LAN interface.
6.  **Inspection:** pfSense checks rules: "Is strict mode on? Yes. Is this traffic allowed? Yes."
7.  **Routing:** pfSense routes packet out its **WAN Interface** (e.g., `10.251.0.2`).
8.  **Next Hop:** The WAN interface connects to the `isp-rtr` (standard router) which finally handles the exit.

---

## 4. Why different flows?

*   **PEX-Stage** optimizes for **speed and simplicity**. OpenStack handles the routing logic efficiently in the kernel.
*   **Game-01** optimizes for **security depth**. By forcing traffic into a VM, you can run Intrusion Detection Systems (IDS), complex VPNs, and live-monitoring that standard OpenStack routers can't do.
