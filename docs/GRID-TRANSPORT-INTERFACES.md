# Grid Transport Interfaces — The Literal Contracts

**Status**: Interface design. Pseudo-code reference for implementation.

These are the traits/interfaces that forge-alloy requires from any grid transport. Implement these and your transport works with the grid. WebSocket, Unix socket, Reticulum, UDP, carrier pigeon — all the same contract.

---

## Core Traits

### GridTransport — The Pipe

```rust
/// The transport layer. Moves bytes between nodes.
/// Everything above this is protocol (events, commands, attestation).
/// Everything below this is wire (TCP, UDP, LoRa, IPC socket).
trait GridTransport: Send + Sync {
    /// Human-readable name for logging
    fn name(&self) -> &str;

    /// What this transport can do
    fn capabilities(&self) -> TransportCapabilities;

    /// Send bytes to a specific peer
    fn send(&self, peer: &PeerId, message: &[u8]) -> Result<(), TransportError>;

    /// Receive bytes from any peer (blocking or async)
    fn recv(&self) -> Result<(PeerId, Vec<u8>), TransportError>;

    /// List currently connected/reachable peers
    fn peers(&self) -> Vec<PeerId>;

    /// Connect to a peer (transport-specific addressing)
    fn connect(&mut self, address: &str) -> Result<PeerId, TransportError>;

    /// Disconnect from a peer
    fn disconnect(&mut self, peer: &PeerId);
}

struct TransportCapabilities {
    reliable: bool,           // TCP=true, UDP=false
    ordered: bool,            // TCP=true, UDP=false
    max_payload_bytes: usize, // MTU (UDP ~1400, TCP ~unlimited, LoRa ~200)
    typical_latency_ms: u32,  // WebSocket ~5, LoRa ~500
    encrypted: bool,          // Tailscale=true, raw TCP=false
    bidirectional: bool,      // WebSocket=true, HTTP=false
    supports_broadcast: bool, // UDP multicast=true, TCP=false
    max_peers: Option<u32>,   // LoRa mesh ~20, WebSocket ~1000
}
```

### GridProtocol — The Language

```rust
/// The protocol layer. Defines message types and routing.
/// Sits on top of any GridTransport.
trait GridProtocol {
    /// Route an event to interested peers
    fn emit_event(&self, topic: &str, payload: &[u8], priority: u8);

    /// Execute a command on a remote node
    fn execute_command(&self, node: &PeerId, command: &str, params: &[u8]) 
        -> Result<Vec<u8>, ProtocolError>;

    /// Subscribe to events from peers (tells peers what to forward)
    fn subscribe(&self, topic_pattern: &str);

    /// Unsubscribe
    fn unsubscribe(&self, topic_pattern: &str);
}
```

### GridNode — The Identity

```rust
/// A node on the grid. Has an identity and advertises capabilities.
trait GridNode {
    /// Cryptographic identity (derived from FIDO2 keypair)
    fn id(&self) -> &NodeId;

    /// What this node can do (for §10.5 capability matching)
    fn capabilities(&self) -> &NodeCapabilities;

    /// What this node needs (for §10.5 needs matching)
    fn needs(&self) -> &NodeNeeds;

    /// Register a command handler
    fn register_command(&mut self, name: &str, handler: Box<dyn CommandHandler>);

    /// Register an event handler
    fn subscribe(&mut self, topic: &str, handler: Box<dyn EventHandler>);
}

struct NodeCapabilities {
    /// Application-specific capabilities
    applications: Vec<ApplicationCapability>,
    /// Hardware capabilities
    compute: ComputeCapability,
    /// Network capabilities (what transports this node speaks)
    transports: Vec<TransportCapabilities>,
}

struct ApplicationCapability {
    name: String,           // "open-eyes", "forge", "inference", "search"
    version: String,
    commands: Vec<String>,  // commands this app handles
    events: Vec<String>,    // events this app emits
    resources: HashMap<String, String>,  // app-specific (vram_gb, cameras, etc.)
}
```

### Attestation — The Proof

```rust
/// Attestation for any stage output.
/// Same structure whether it's a forge stage, a CV eval, or a camera deployment.
trait StageAttestation {
    /// Hash of the stage's input artifacts
    fn input_hashes(&self) -> &HashMap<String, String>;

    /// Hash of the stage's output artifact
    fn output_hash(&self) -> &str;

    /// Git commit of the code that produced this output
    fn code_commit(&self) -> &str;

    /// Timestamp of completion
    fn completed_at(&self) -> &str;

    /// Verify: does the output on disk match the attested hash?
    fn verify(&self, artifact_path: &Path) -> bool;
}

/// A chain of attestations — one per stage.
/// The chain is the alloy's proof of work.
struct AttestationChain {
    stages: Vec<Box<dyn StageAttestation>>,
}

impl AttestationChain {
    /// Verify the entire chain: each stage's output hash matches
    /// the next stage's input hash. Breaks at any tampered link.
    fn verify_chain(&self) -> Result<(), AttestationError> {
        for window in self.stages.windows(2) {
            let prev_output = window[0].output_hash();
            let next_inputs = window[1].input_hashes();
            // The previous stage's output must appear in the next stage's inputs
            if !next_inputs.values().any(|h| h == prev_output) {
                return Err(AttestationError::BrokenChain {
                    stage: window[1].code_commit().into(),
                    expected: prev_output.into(),
                });
            }
        }
        Ok(())
    }
}
```

### EventRouter — The Bridge

```rust
/// Routes events between local subscribers and remote peers.
/// Hooks into Events.emit() transparently.
trait EventRouter {
    /// Called when a local event fires. Forward to interested peers.
    fn on_local_event(&self, topic: &str, payload: &[u8], event_id: &str);

    /// Called when a remote event arrives. Re-emit locally.
    fn on_remote_event(&self, topic: &str, payload: &[u8], source_node: &NodeId, event_id: &str);

    /// Register interest in a topic (tells peers to forward matching events)
    fn subscribe_remote(&self, topic_pattern: &str);

    /// Check if a topic matches any peer's subscription
    fn has_remote_interest(&self, topic: &str) -> bool;
}
```

---

## Transport Implementations (Planned)

| Transport | Trait impl | Reliable | Latency | Use case |
|---|---|---|---|---|
| **WebSocketTransport** | `GridTransport` | Yes | ~5ms | Inter-node events + commands |
| **UnixSocketTransport** | `GridTransport` | Yes | <1ms | Rust IPC (same machine) |
| **UdpTransport** | `GridTransport` | No | ~2ms | Sensor data, telemetry |
| **ReticulumTransport** | `GridTransport` | Yes | ~500ms | LoRa mesh, off-grid cameras |
| **TailscaleTransport** | `GridTransport` | Yes | ~10ms | Encrypted inter-node (wraps WS/UDP) |

Each implements the same `GridTransport` trait. The `GridProtocol` layer picks the right transport based on `TransportCapabilities` vs message requirements.

---

## forge-alloy Integration

The alloy recipe can specify transport preferences:

```json
{
  "stages": [
    {
      "type": "cv-eval",
      "transport": {
        "events": "reliable",      // TCP tier for eval results
        "telemetry": "best-effort" // UDP tier for GPU stats during eval
      }
    }
  ]
}
```

The stage executor reads the transport preference and configures the `EventRouter` accordingly. Default is "reliable" for everything. "best-effort" opts into UDP for high-frequency data.

---

## Language Bindings

One definition, three projections:

| Language | Source | Generated from |
|---|---|---|
| **Rust** | `forge-alloy/rust/src/transport.rs` | Source of truth |
| **TypeScript** | `forge-alloy/typescript/transport.ts` | ts-rs from Rust |
| **Python** | `forge-alloy/python/forge_alloy/transport.py` | Pydantic mirror |

Change the Rust definition → TypeScript and Python follow automatically. No drift. No duplicate types. Single source of truth, three projections.
