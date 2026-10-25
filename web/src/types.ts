export type EccLevel = "L" | "M" | "Q" | "H";

/** Session metadata, as produced by the sender and carried in sync frames. */
export type BroadcastMetadata = {
  v: number;
  block_size: number;
  k: number;
  /** Bytes on the wire (after compression). */
  orig_len: number;
  integrity_check: boolean;
  session_id: string;
  codec: "deflate" | "none";
  raw_len: number;
  sha256: string;
  ecc: EccLevel;
  frame_interval_ms: number;
  frames_per_loop: number;
  symbols_per_loop: number;
};

export type SyncInfo = BroadcastMetadata & {
  ordinal: number;
  total: number;
  confirmation_required: number;
};

export type BroadcastFrame =
  | {
      sequence: number;
      type: "sync";
      ordinal: number;
      total: number;
      qr_value: string;
    }
  | {
      sequence: number;
      type: "symbol";
      esi: number;
      indices: number[];
      degree: number;
      systematic: boolean;
      qr_value: string;
    };

export type BroadcastPackage = {
  payload_text: string;
  payload_is_base64: boolean;
  metadata: BroadcastMetadata;
  frames: BroadcastFrame[];
  total_frames: number;
  systematic_count: number;
  redundant_count: number;
};

export type ReceiverStatus = {
  newly_added: boolean;
  k: number;
  rank: number;
  progress: number;
  unique_frames: number;
  duplicate_frames: number;
  redundant_symbols: number;
  rejected: Record<string, number>;
  /** One char per source block: 0 pending, 1 received directly, 2 recovered via repair. */
  blocks: string;
  phase: "collecting" | "done" | "error";
  decode_complete: boolean;
  recovered_is_base64: boolean;
  codec: string;
  raw_len: number | null;
  wire_len: number;
  finalize_error: string | null;
  decode_ms: number;
  elapsed_s: number | null;
  frames_expected: number | null;
  capture_rate: number | null;
};

export type CallPythonJson = (
  fnName: string,
  ...args: unknown[]
) => Promise<any>;
